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
        "TRION_SKILL_ADDONS_RUNTIME_DIR",
        os.path.join(os.environ.get("MARKETPLACE_DIR", "/app/data/marketplace"), "skill_addons"),
    )
)
_EMBED_CACHE: Dict[str, List[float] | None] = {}
_EMBED_LOCK = threading.Lock()


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
    }


def _iter_markdown_files() -> List[Path]:
    candidates: List[Path] = []
    seen: set[str] = set()
    for root in (RUNTIME_ADDONS_ROOT, ADDONS_ROOT):
        taxonomy_root = root / "taxonomy"
        if not taxonomy_root.exists():
            continue
        for path in sorted(p for p in taxonomy_root.rglob("*.md") if p.is_file() and p.name.lower() != "readme.md"):
            rel = path.relative_to(root).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            candidates.append(path)
    return candidates


def _query_variants(query_text: str) -> set[str]:
    norm = _norm(query_text)
    variants = {norm}
    expansions = {
        "skills": "skill runtime draft tools session",
        "faehigkeiten": "skills tools capabilities",
        "codex": "session skills skill.md",
        "skill.md": "session skills codex skills",
        "installiert": "installed runtime skills",
        "entwurf": "draft skills",
    }
    for needle, replacement in expansions.items():
        if needle in norm:
            variants.add(_norm(norm.replace(needle, replacement)))
    return {item for item in variants if item}


def _runtime_snapshot_flags(runtime_snapshot: Dict[str, Any] | None) -> Dict[str, Any]:
    data = runtime_snapshot if isinstance(runtime_snapshot, dict) else {}
    installed = data.get("installed")
    active = data.get("active")
    drafts = data.get("drafts")
    flags = {
        "has_runtime_skills": bool(installed or active or int(data.get("installed_count") or 0) > 0 or int(data.get("active_count") or 0) > 0),
        "has_drafts": bool(drafts or int(data.get("draft_count") or 0) > 0 or int(data.get("drafts_count") or 0) > 0),
        "has_available": bool(data.get("available") or int(data.get("available_count") or 0) > 0),
    }
    return flags


def _infer_query_tags(query_text: str, requested_tags: List[str] | None, runtime_snapshot: Dict[str, Any] | None) -> List[str]:
    norm = _norm(query_text)
    tags = {str(item).strip().lower() for item in list(requested_tags or []) if str(item).strip()}
    if norm:
        tags.add("skill_taxonomy")
        tags.add("answering_rules")

    if any(token in norm for token in ("welche skills", "skills hast", "installiert", "installed", "runtime skill", "aktive skills")):
        tags.add("runtime_skills")
    if any(token in norm for token in ("draft", "entwurf", "noch nicht aktiv", "nicht aktiv", "fehlt dir an skills", "fehlende skills")):
        tags.add("draft_skills")
    if any(token in norm for token in ("tool", "tools", "faehigkeiten", "fähigkeiten", "unterschied", "list_skills nicht", "warum zeigt list_skills nicht")):
        tags.add("tools_vs_skills")
    if any(token in norm for token in ("session", "codex", "skill.md", "system skill", "system skills")):
        tags.add("session_skills")
    if any(token in norm for token in ("arten von skills", "skill arten", "kategorien", "taxonomy", "taxonomie")):
        tags.add("overview")

    flags = _runtime_snapshot_flags(runtime_snapshot)
    if flags.get("has_drafts") and any(token in norm for token in ("fehlt", "nicht aktiv", "pipeline", "entwurf")):
        tags.add("draft_skills")
    if flags.get("has_runtime_skills") and any(token in norm for token in ("welche skills", "installiert", "active", "aktiv")):
        tags.add("runtime_skills")

    return sorted(tags)


def _scope_hint_score(scope: str, query_tags: List[str], query_text: str) -> float:
    lower_scope = str(scope or "").strip().lower()
    lower_tags = {str(item).strip().lower() for item in list(query_tags or []) if str(item).strip()}
    query_norm = _norm(query_text)
    score = 0.0
    if not lower_scope:
        return score
    if lower_scope in lower_tags:
        score += 6.0
    if lower_scope == "overview" and ("skill_taxonomy" in lower_tags or "overview" in lower_tags):
        score += 5.0
    if lower_scope == "answering_rules" and "answering_rules" in lower_tags:
        score += 5.0
    if lower_scope == "runtime_skills" and "runtime_skills" in lower_tags:
        score += 4.0
    if lower_scope == "draft_skills" and "draft_skills" in lower_tags:
        score += 4.0
    if lower_scope == "tools_vs_skills" and "tools_vs_skills" in lower_tags:
        score += 4.0
    if lower_scope == "session_skills" and "session_skills" in lower_tags:
        score += 4.0
    if any(token in query_norm for token in ("welche skills", "skills hast", "installiert")) and lower_scope == "runtime_skills":
        score += 3.5
    if any(token in query_norm for token in ("draft", "entwurf", "nicht aktiv")) and lower_scope == "draft_skills":
        score += 3.5
    if any(token in query_norm for token in ("tool", "tools", "faehigkeiten", "fähigkeiten", "unterschied")) and lower_scope == "tools_vs_skills":
        score += 3.5
    if any(token in query_norm for token in ("session", "codex", "skill.md")) and lower_scope == "session_skills":
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
        result.append(
            {
                "addon": addon,
                "section_index": idx,
                "title": str(section.get("title") or title).strip(),
                "text": text,
            }
        )
    return result


def _lexical_score_section(section: Dict[str, Any], query_text: str, query_tags: List[str]) -> float:
    addon = section.get("addon") or {}
    meta = addon.get("meta") or {}

    query_variants = _query_variants(query_text)
    query_tokens = set().union(*(_tokenize(item) for item in query_variants)) if query_variants else set()
    query_norm = max(query_variants, key=len) if query_variants else ""
    title = str(section.get("title") or "").strip()
    text = str(section.get("text") or "").strip()
    title_tokens = _tokenize(title)
    section_tokens = _tokenize(text)
    tags = [str(item).strip().lower() for item in list(meta.get("tags") or []) if str(item).strip()]
    hints = [str(item).strip().lower() for item in list(meta.get("retrieval_hints") or []) if str(item).strip()]
    question_types = [str(item).strip().lower() for item in list(meta.get("question_types") or []) if str(item).strip()]
    scope = str(meta.get("scope") or "").strip().lower()
    query_tag_set = {str(item).strip().lower() for item in list(query_tags or []) if str(item).strip()}

    score = float(meta.get("priority", 0) or 0) / 10.0
    score += _scope_hint_score(scope, query_tags, query_text)
    score += float(len(query_tokens.intersection(title_tokens)) * 2.5)
    score += float(len(query_tokens.intersection(section_tokens)) * 0.4)
    score += float(len(query_tag_set.intersection(tags)) * 3.0)
    score += sum(4.0 for question in question_types if question and question in _norm(query_text))
    score += sum(2.5 for hint in hints if hint and any(hint in variant for variant in query_variants))
    if section.get("section_index", 0) == 0:
        score += 1.0
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
        candidate["final_score"] = float(candidate.get("score", 0.0)) + emb_score * 5.0
        refined.append(candidate)
    refined.sort(key=lambda item: float(item.get("final_score", item.get("score", 0.0))), reverse=True)
    return refined


async def load_skill_addon_context(
    *,
    query: str,
    tags: List[str] | None = None,
    runtime_snapshot: Dict[str, Any] | None = None,
    max_docs: int = 3,
    max_chars: int = 5000,
    use_embeddings: bool = True,
) -> Dict[str, Any]:
    query_text = str(query or "").strip()
    inferred_tags = _infer_query_tags(query_text, tags, runtime_snapshot)
    runtime_flags = _runtime_snapshot_flags(runtime_snapshot)

    section_candidates: List[Dict[str, Any]] = []
    for path in _iter_markdown_files():
        addon = _load_addon(path)
        for section in _collect_section_candidates(addon):
            score = _lexical_score_section(section, query_text, inferred_tags)
            if score <= 0:
                continue
            section_candidates.append({**section, "score": round(score, 4)})

    section_candidates.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    section_candidates = section_candidates[:10]
    if use_embeddings and len(section_candidates) > 1:
        section_candidates = await _embedding_refine_sections(query_text, section_candidates)

    selected_docs: List[Dict[str, Any]] = []
    context_blocks: List[str] = []
    seen_doc_ids: set[str] = set()
    for candidate in section_candidates:
        addon = candidate.get("addon") or {}
        meta = addon.get("meta") or {}
        doc_id = str(meta.get("id") or addon.get("name") or "").strip()
        if not doc_id or doc_id in seen_doc_ids:
            continue
        seen_doc_ids.add(doc_id)
        selected_docs.append(
            {
                "id": doc_id,
                "title": str(meta.get("title") or addon.get("name") or "").strip(),
                "scope": str(meta.get("scope") or "").strip(),
                "path": str(addon.get("path") or ""),
                "score": round(float(candidate.get("final_score", candidate.get("score", 0.0))), 2),
                "embedding_score": round(float(candidate.get("embedding_score", 0.0)), 4),
            }
        )
        context_blocks.append(
            "\n".join(
                [
                    f"Skill Addon: {str(meta.get('title') or addon.get('name') or '').strip()}",
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
        "inferred_tags": inferred_tags,
        "runtime_flags": runtime_flags,
    }
