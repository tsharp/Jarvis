from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from core.embedding_client import cosine_similarity, embed_text


ADDONS_ROOT = Path(__file__).resolve().parent

_EMBED_CACHE: Dict[str, List[float] | None] = {}
_EMBED_LOCK = threading.Lock()

_SUPPORTED_QUERY_CLASSES = {
    "system_topology",
    "data_locations",
    "auth_model",
    "tool_surface",
    "self_extension",
}

_QUERY_CLASS_CONFIG: Dict[str, Dict[str, Any]] = {
    "system_topology": {
        "allowed_dirs": {"topology"},
        "preferred_scopes": {"topology"},
        "preferred_tags": {"services", "ports", "docker", "urls", "netzwerk"},
    },
    "data_locations": {
        "allowed_dirs": {"topology"},
        "preferred_scopes": {"data_locations"},
        "preferred_tags": {"secrets", "blueprints", "skills", "workspace", "memory", "api-keys"},
    },
    "auth_model": {
        "allowed_dirs": {"topology"},
        "preferred_scopes": {"auth_model"},
        "preferred_tags": {"auth", "token", "credentials", "secrets", "bearer"},
    },
    "tool_surface": {
        "allowed_dirs": {"topology"},
        "preferred_scopes": {"tool_surface"},
        "preferred_tags": {"tools", "endpoints", "mcp"},
    },
    "self_extension": {
        "allowed_dirs": {"self_extension"},
        "preferred_scopes": {"skill_lifecycle", "safe_paths", "alias_model"},
        "preferred_tags": {"skill", "lifecycle", "selbsterweiterung", "autonomie", "alias"},
    },
}


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _tokenize(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9:_./+-]{2,}", _norm(value)) if token}


def _parse_frontmatter(raw: str) -> Tuple[Dict[str, Any], str]:
    text = str(raw or "")
    if not text.startswith("---\n"):
        return {}, text.strip()
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text.strip()
    frontmatter = text[4:end]
    body = text[end + 5:].strip()
    try:
        meta = yaml.safe_load(frontmatter) or {}
    except Exception:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, body


def _load_addon(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(raw)
    return {
        "path": str(path),
        "name": path.name,
        "meta": meta,
        "body": body,
        "dir_kind": _addon_dir_kind(path),
    }


def _addon_dir_kind(path: Path) -> str:
    try:
        rel = path.relative_to(ADDONS_ROOT)
    except ValueError:
        return ""
    parts = rel.parts
    return str(parts[0]).strip().lower() if parts else ""


def _iter_markdown_files() -> List[Path]:
    candidates: List[Path] = []
    for subdir in ("topology", "self_extension"):
        current = ADDONS_ROOT / subdir
        if not current.exists():
            continue
        for path in sorted(p for p in current.rglob("*.md") if p.is_file() and p.name.lower() not in ("readme.md",)):
            candidates.append(path)
    return candidates


def _normalize_query_class(query_class: str) -> str:
    value = str(query_class or "").strip().lower()
    return value if value in _SUPPORTED_QUERY_CLASSES else ""


def _query_class_config(query_class: str) -> Dict[str, Any]:
    return dict(_QUERY_CLASS_CONFIG.get(_normalize_query_class(query_class)) or {})


def _query_class_allows_addon(addon: Dict[str, Any], query_class: str) -> bool:
    config = _query_class_config(query_class)
    if not config:
        return True
    dir_kind = str(addon.get("dir_kind") or "").strip().lower()
    allowed_dirs = {str(d).strip().lower() for d in list(config.get("allowed_dirs") or []) if str(d).strip()}
    if allowed_dirs and dir_kind not in allowed_dirs:
        return False
    return True


def _query_class_score_adjustment(addon: Dict[str, Any], meta: Dict[str, Any], query_class: str) -> float:
    config = _query_class_config(query_class)
    if not config:
        return 0.0
    scope = str(meta.get("scope") or "").strip().lower()
    tags = {str(t).strip().lower() for t in list(meta.get("tags") or []) if str(t).strip()}
    preferred_scopes = {str(s).strip().lower() for s in list(config.get("preferred_scopes") or []) if str(s).strip()}
    preferred_tags = {str(t).strip().lower() for t in list(config.get("preferred_tags") or []) if str(t).strip()}

    score = 0.0
    if scope and scope in preferred_scopes:
        score += 6.0
    score += float(len(tags.intersection(preferred_tags)) * 2.5)
    return score


def _split_sections(body: str) -> List[Dict[str, str]]:
    text = str(body or "").strip()
    if not text:
        return []
    sections: List[Dict[str, str]] = []
    current_title = ""
    current_lines: List[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append({"title": current_title, "text": "\n".join(current_lines).strip()})
                current_lines = []
            current_title = line.strip("# ").strip()
            current_lines = [line]
            continue
        current_lines.append(line)
    if current_lines:
        sections.append({"title": current_title, "text": "\n".join(current_lines).strip()})
    return sections


def _collect_section_candidates(addon: Dict[str, Any]) -> List[Dict[str, Any]]:
    meta = addon.get("meta") or {}
    title = str(meta.get("title") or addon.get("name") or "").strip()
    sections = _split_sections(str(addon.get("body") or ""))
    if not sections:
        sections = [{"title": title, "text": str(addon.get("body") or "").strip()}]
    result: List[Dict[str, Any]] = []
    for idx, section in enumerate(sections):
        text = str(section.get("text") or "").strip()
        if not text:
            continue
        result.append({
            "addon": addon,
            "section_index": idx,
            "title": str(section.get("title") or title).strip(),
            "text": text,
        })
    return result


def _lexical_score_section(
    section: Dict[str, Any],
    query_text: str,
    query_class: str = "",
) -> float:
    addon = section.get("addon") or {}
    meta = addon.get("meta") or {}

    if not _query_class_allows_addon(addon, query_class):
        return -1.0

    query_norm = _norm(query_text)
    query_tokens = _tokenize(query_text)
    title_tokens = _tokenize(str(section.get("title") or ""))
    section_tokens = _tokenize(str(section.get("text") or ""))
    tags = [str(t).strip().lower() for t in list(meta.get("tags") or []) if str(t).strip()]
    hints = [str(h).strip().lower() for h in list(meta.get("retrieval_hints") or []) if str(h).strip()]

    score = float(meta.get("priority", 0) or 0) / 12.0
    score += _query_class_score_adjustment(addon, meta, query_class)
    score += float(len(query_tokens.intersection(title_tokens)) * 2.5)
    score += float(len(query_tokens.intersection(section_tokens)) * 0.45)
    score += sum(4.0 for hint in hints if hint and hint in query_norm)
    score += sum(1.25 for tag in tags if tag and tag in query_tokens)

    if section.get("section_index", 0) == 0:
        score += 1.5
    return score


async def _get_embedding_cached(text: str) -> List[float] | None:
    key = str(text or "").strip()
    if not key:
        return None
    with _EMBED_LOCK:
        if key in _EMBED_CACHE:
            return _EMBED_CACHE[key]
    vec = await embed_text(key, timeout_s=1.8)
    with _EMBED_LOCK:
        _EMBED_CACHE[key] = vec
    return vec


async def _embedding_refine_sections(query_text: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not query_text or not candidates:
        return candidates
    query_vec = await _get_embedding_cached(query_text[:4000])
    if not query_vec:
        return candidates
    refined: List[Dict[str, Any]] = []
    for candidate in candidates:
        section_text = f"{candidate.get('title')}\n{candidate.get('text')}"
        section_vec = await _get_embedding_cached(section_text[:4000])
        emb_score = max(0.0, cosine_similarity(query_vec, section_vec or []))
        candidate["embedding_score"] = round(emb_score, 4)
        candidate["final_score"] = float(candidate.get("score", 0.0)) + emb_score * 6.0
        refined.append(candidate)
    refined.sort(key=lambda c: float(c.get("final_score", c.get("score", 0.0))), reverse=True)
    return refined


async def load_system_addon_context(
    *,
    intent: str,
    query_class: str = "",
    max_docs: int = 3,
    max_chars: int = 4000,
    use_embeddings: bool = True,
) -> Dict[str, Any]:
    normalized_query_class = _normalize_query_class(query_class)

    section_candidates: List[Dict[str, Any]] = []
    for path in _iter_markdown_files():
        addon = _load_addon(path)
        for section in _collect_section_candidates(addon):
            score = _lexical_score_section(section, intent, normalized_query_class)
            if score < 0:
                continue
            section_candidates.append({**section, "score": round(score, 4)})

    section_candidates.sort(key=lambda c: float(c.get("score", 0.0)), reverse=True)
    section_candidates = section_candidates[:10]

    if use_embeddings and len(section_candidates) > 1:
        section_candidates = await _embedding_refine_sections(intent, section_candidates)

    selected_docs: List[Dict[str, Any]] = []
    context_blocks: List[str] = []
    seen_ids: set[str] = set()

    for candidate in section_candidates:
        addon = candidate.get("addon") or {}
        meta = addon.get("meta") or {}
        doc_id = str(meta.get("id") or addon.get("name") or "").strip()
        if not doc_id or doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)
        selected_docs.append({
            "id": doc_id,
            "title": str(meta.get("title") or addon.get("name") or "").strip(),
            "scope": str(meta.get("scope") or "").strip(),
            "path": str(addon.get("path") or ""),
            "score": round(float(candidate.get("final_score", candidate.get("score", 0.0))), 2),
            "embedding_score": round(float(candidate.get("embedding_score", 0.0)), 4),
        })
        context_blocks.append(
            "\n".join([
                f"Addon: {str(meta.get('title') or addon.get('name') or '').strip()}",
                f"Scope: {str(meta.get('scope') or '').strip()}",
                str(candidate.get("text") or "").strip(),
            ]).strip()
        )
        if len(selected_docs) >= max_docs:
            break

    context_text = "\n\n---\n\n".join(block for block in context_blocks if block).strip()
    if len(context_text) > max_chars:
        context_text = context_text[:max_chars].rstrip()

    return {
        "selected_docs": selected_docs,
        "context_text": context_text,
        "query_class": normalized_query_class,
    }


__all__ = ["load_system_addon_context"]
