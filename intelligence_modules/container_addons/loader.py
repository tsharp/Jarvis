from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from core.embedding_client import cosine_similarity, embed_text


ADDONS_ROOT = Path(__file__).resolve().parent
RUNTIME_ADDONS_ROOT = Path(
    os.environ.get(
        "TRION_CONTAINER_ADDONS_RUNTIME_DIR",
        os.path.join(os.environ.get("MARKETPLACE_DIR", "/app/data/marketplace"), "container_addons"),
    )
)
_EMBED_CACHE: Dict[str, List[float] | None] = {}
_EMBED_LOCK = threading.Lock()
_SUPPORTED_QUERY_CLASSES = {
    "container_inventory",
    "container_blueprint_catalog",
    "container_state_binding",
    "container_request",
    "active_container_capability",
}
_QUERY_CLASS_CONFIG: Dict[str, Dict[str, Any]] = {
    "container_inventory": {
        "allowed_roots": {"taxonomy"},
        "preferred_scopes": {"inventory", "overview", "answering_rules"},
        "preferred_tags": {"inventory"},
    },
    "container_blueprint_catalog": {
        "allowed_roots": {"taxonomy"},
        "preferred_scopes": {"inventory", "overview", "answering_rules"},
        "preferred_tags": {"blueprint"},
    },
    "container_state_binding": {
        "allowed_roots": {"taxonomy"},
        "preferred_scopes": {"inventory", "overview", "answering_rules", "state_binding"},
        "preferred_tags": {"state-binding", "binding"},
    },
    "container_request": {
        "allowed_roots": {"taxonomy"},
        "preferred_scopes": {"overview", "answering_rules"},
        "preferred_tags": {"request", "approval", "deploy"},
    },
    "active_container_capability": {
        "allowed_roots": {"taxonomy", "profiles"},
        "preferred_scopes": {
            "container_profile",
            "runtime",
            "diagnostics",
            "safety",
            "known_issues",
            "overview",
            "answering_rules",
            "capability_rules",
        },
        "preferred_tags": {"capability", "runtime", "tooling", "workspace"},
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
        "root_kind": _addon_root_kind(path),
    }


def _iter_markdown_files() -> List[Path]:
    candidates: List[Path] = []
    seen: set[str] = set()
    for root in (RUNTIME_ADDONS_ROOT, ADDONS_ROOT):
        for subdir in ("taxonomy", "profiles"):
            current_root = root / subdir
            if not current_root.exists():
                continue
            for path in sorted(p for p in current_root.rglob("*.md") if p.is_file() and p.name.lower() != "readme.md"):
                rel = path.relative_to(root).as_posix()
                if rel in seen:
                    continue
                seen.add(rel)
                candidates.append(path)
    return candidates


def _addon_root_kind(path: Path) -> str:
    for root in (RUNTIME_ADDONS_ROOT, ADDONS_ROOT):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        parts = rel.parts
        if parts:
            return str(parts[0]).strip().lower()
    return ""


def _normalize_query_class(query_class: str) -> str:
    value = str(query_class or "").strip().lower()
    if value in _SUPPORTED_QUERY_CLASSES:
        return value
    return ""


def _query_class_config(query_class: str) -> Dict[str, Any]:
    return dict(_QUERY_CLASS_CONFIG.get(_normalize_query_class(query_class)) or {})


def _query_class_allows_addon(addon: Dict[str, Any], query_class: str) -> bool:
    config = _query_class_config(query_class)
    if not config:
        return True
    root_kind = str(addon.get("root_kind") or "").strip().lower()
    allowed_roots = {
        str(item).strip().lower()
        for item in list(config.get("allowed_roots") or [])
        if str(item).strip()
    }
    if allowed_roots and root_kind not in allowed_roots:
        return False
    return True


def _query_class_score_adjustment(addon: Dict[str, Any], meta: Dict[str, Any], query_class: str) -> float:
    config = _query_class_config(query_class)
    if not config:
        return 0.0

    score = 0.0
    root_kind = str(addon.get("root_kind") or "").strip().lower()
    scope = str(meta.get("scope") or "").strip().lower()
    tags = {str(item).strip().lower() for item in list(meta.get("tags") or []) if str(item).strip()}
    preferred_scopes = {
        str(item).strip().lower()
        for item in list(config.get("preferred_scopes") or [])
        if str(item).strip()
    }
    preferred_tags = {
        str(item).strip().lower()
        for item in list(config.get("preferred_tags") or [])
        if str(item).strip()
    }

    if root_kind == "taxonomy":
        score += 3.0
    elif root_kind == "profiles":
        score += 4.0

    if scope and scope in preferred_scopes:
        score += 6.0
    score += float(len(tags.intersection(preferred_tags)) * 2.5)
    return score


def _query_variants(query_text: str) -> set[str]:
    norm = _norm(query_text)
    variants = {norm}
    expansions = {
        "blackscreen": "black screen",
        "blackscreen": "black screen",
        "novnc": "noVNC",
        "sunshine webui": "sunshine web ui",
        "systemctl": "systemd service management",
        "supervisor": "supervisord supervisorctl",
        "steam installer": "zenity steam installer",
    }
    for needle, replacement in expansions.items():
        if needle in norm:
            variants.add(_norm(norm.replace(needle, replacement)))
    return {item for item in variants if item}


def _matches_container(meta: Dict[str, Any], blueprint_id: str, image_ref: str, container_tags: List[str]) -> bool:
    applies = meta.get("applies_to") if isinstance(meta.get("applies_to"), dict) else {}
    bp_ids = {str(item).strip().lower() for item in list(applies.get("blueprint_ids") or []) if str(item).strip()}
    image_refs = {str(item).strip().lower() for item in list(applies.get("image_refs") or []) if str(item).strip()}
    required_tags = {str(item).strip().lower() for item in list(applies.get("container_tags") or []) if str(item).strip()}

    lower_bp = str(blueprint_id or "").strip().lower()
    lower_image = str(image_ref or "").strip().lower()
    lower_tags = {str(item).strip().lower() for item in list(container_tags or []) if str(item).strip()}

    matched = False
    if bp_ids and lower_bp in bp_ids:
        matched = True
    if image_refs and lower_image and any(ref and ref in lower_image for ref in image_refs):
        matched = True
    if required_tags and lower_tags and required_tags.intersection(lower_tags):
        matched = True
    if any((bp_ids, image_refs, required_tags)):
        return matched
    return True


def _scope_hint_score(scope: str, query_text: str) -> float:
    query_norm = _norm(query_text)
    lower_scope = str(scope or "").strip().lower()
    score = 0.0
    if not lower_scope:
        return score
    if any(token in query_norm for token in ("welche container", "which containers", "container inventory", "container liste", "list containers", "running containers", "laufende container", "gestoppte container", "installed containers", "installierte container")):
        if lower_scope in {"inventory", "overview"}:
            score += 4.0
    if any(token in query_norm for token in ("blueprint", "blueprints", "katalog", "catalog", "installable", "installierbar", "verfuegbar", "verfugbar", "available containers", "startbar")):
        if lower_scope in {"inventory", "overview"}:
            score += 4.0
    if any(token in query_norm for token in ("active container", "aktiver container", "current container", "session container", "binding", "gebunden", "container status", "runtime status")):
        if lower_scope in {"state_binding", "overview"}:
            score += 4.0
    if any(token in query_norm for token in ("capability", "capabilities", "kann dieser container", "was kannst du in diesem container", "tooling", "features")):
        if lower_scope in {"capability_rules", "overview"}:
            score += 4.0
    if any(token in query_norm for token in ("antwort", "answer", "sauber trennen", "nicht vermischen", "never mix", "dont mix", "truth source", "wahrheitsquelle")):
        if lower_scope in {"answering_rules", "overview"}:
            score += 4.0
    if any(token in query_norm for token in ("black screen", "blackscreen", "crash", "not reachable", "nicht erreichbar", "fehler", "issue", "problem")):
        if lower_scope in {"diagnostics", "known_issues"}:
            score += 3.0
        if lower_scope == "runtime":
            score += 1.5
    if any(token in query_norm for token in ("port", "display", "xorg", "novnc", "sunshine", "steam installer", "supervisord", "supervisorctl")):
        if lower_scope in {"runtime", "diagnostics"}:
            score += 2.5
    if any(token in query_norm for token in ("what container", "welcher container", "was ist das", "profil", "profile")):
        if lower_scope == "container_profile":
            score += 3.5
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
                sections.append({
                    "title": current_title,
                    "text": "\n".join(current_lines).strip(),
                })
                current_lines = []
            current_title = line.strip("# ").strip()
            current_lines = [line]
            continue
        current_lines.append(line)
    if current_lines:
        sections.append({
            "title": current_title,
            "text": "\n".join(current_lines).strip(),
        })
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
        result.append(
            {
                "addon": addon,
                "section_index": idx,
                "title": str(section.get("title") or title).strip(),
                "text": text,
            }
        )
    return result


def _lexical_score_section(
    section: Dict[str, Any],
    query_text: str,
    blueprint_id: str,
    image_ref: str,
    container_tags: List[str],
    query_class: str = "",
) -> float:
    addon = section.get("addon") or {}
    meta = addon.get("meta") or {}
    if not _query_class_allows_addon(addon, query_class):
        return -1.0
    if not _matches_container(meta, blueprint_id, image_ref, container_tags):
        return -1.0

    query_variants = _query_variants(query_text)
    query_tokens = set().union(*(_tokenize(item) for item in query_variants)) if query_variants else set()
    query_norm = max(query_variants, key=len) if query_variants else ""
    title = str(section.get("title") or "").strip()
    text = str(section.get("text") or "").strip()
    title_tokens = _tokenize(title)
    section_tokens = _tokenize(text)
    tags = [str(item).strip().lower() for item in list(meta.get("tags") or []) if str(item).strip()]
    hints = [str(item).strip().lower() for item in list(meta.get("retrieval_hints") or []) if str(item).strip()]
    commands = [str(item).strip().lower() for item in list(meta.get("commands_available") or []) if str(item).strip()]
    scope = str(meta.get("scope") or "").strip()

    score = float(meta.get("priority", 0) or 0) / 12.0
    score += _query_class_score_adjustment(addon, meta, query_class)
    score += _scope_hint_score(scope, query_text)
    if str(blueprint_id or "").strip().lower() in {str(item).strip().lower() for item in list((meta.get("applies_to") or {}).get("blueprint_ids") or [])}:
        score += 8.0
    if image_ref and any(ref and ref in str(image_ref).lower() for ref in list((meta.get("applies_to") or {}).get("image_refs") or [])):
        score += 4.0
    score += float(len(query_tokens.intersection(title_tokens)) * 2.5)
    score += float(len(query_tokens.intersection(section_tokens)) * 0.45)
    score += sum(4.0 for hint in hints if hint and any(hint in variant for variant in query_variants))
    score += sum(1.25 for tag in tags if tag and tag in query_tokens)
    score += sum(1.75 for command in commands if command and command in query_norm)

    lower_tags = {str(item).strip().lower() for item in list(container_tags or []) if str(item).strip()}
    required_tags = {str(item).strip().lower() for item in list((meta.get("applies_to") or {}).get("container_tags") or []) if str(item).strip()}
    score += float(len(required_tags.intersection(lower_tags)) * 1.5)

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
    refined.sort(key=lambda item: float(item.get("final_score", item.get("score", 0.0))), reverse=True)
    return refined


async def load_container_addon_context(
    *,
    blueprint_id: str,
    image_ref: str,
    instruction: str,
    query_class: str = "",
    shell_tail: str = "",
    container_tags: List[str] | None = None,
    max_docs: int = 4,
    max_chars: int = 6500,
    use_embeddings: bool = True,
) -> Dict[str, Any]:
    query_text = "\n".join(part for part in (instruction, shell_tail) if str(part or "").strip())
    lower_tags = [str(item).strip().lower() for item in list(container_tags or []) if str(item).strip()]
    normalized_query_class = _normalize_query_class(query_class)

    section_candidates: List[Dict[str, Any]] = []
    for path in _iter_markdown_files():
        addon = _load_addon(path)
        for section in _collect_section_candidates(addon):
            score = _lexical_score_section(
                section,
                query_text,
                blueprint_id,
                image_ref,
                lower_tags,
                normalized_query_class,
            )
            if score < 0:
                continue
            section_candidates.append(
                {
                    **section,
                    "score": round(score, 4),
                }
            )
    section_candidates.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    section_candidates = section_candidates[:10]
    if use_embeddings and len(section_candidates) > 1:
        section_candidates = await _embedding_refine_sections(query_text, section_candidates)

    selected_docs = []
    context_blocks: List[str] = []
    seen_doc_ids: set[str] = set()
    for candidate in section_candidates:
        addon = candidate.get("addon") or {}
        meta = addon.get("meta") or {}
        doc_id = str(meta.get("id") or addon.get("name") or "").strip()
        if not doc_id or doc_id in seen_doc_ids:
            continue
        seen_doc_ids.add(doc_id)
        selected_docs.append({
            "id": doc_id,
            "title": str(meta.get("title") or addon.get("name") or "").strip(),
            "scope": str(meta.get("scope") or "").strip(),
            "path": str(addon.get("path") or ""),
            "score": round(float(candidate.get("final_score", candidate.get("score", 0.0))), 2),
            "embedding_score": round(float(candidate.get("embedding_score", 0.0)), 4),
        })
        context_blocks.append(
            "\n".join(
                [
                    f"Addon: {str(meta.get('title') or addon.get('name') or '').strip()}",
                    f"Scope: {str(meta.get('scope') or '').strip()}",
                    str(candidate.get("text") or "").strip(),
                ]
            ).strip()
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
