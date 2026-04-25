from __future__ import annotations

import unicodedata
from typing import Any

from core.task_loop.contracts import TaskLoopSnapshot
from intelligence_modules.prompt_manager import load_prompt


_AUTO_SELECT_MIN_SCORE = 0.80
_AUTO_SELECT_MIN_MARGIN = 0.10
_SUGGEST_MIN_SCORE = 0.68


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.lower().split())


def _blueprint_fields(row: dict[str, Any]) -> tuple[str, str]:
    blueprint_id = str(row.get("blueprint_id") or row.get("id") or row.get("name") or "").strip()
    label = str(row.get("name") or row.get("blueprint_id") or row.get("id") or "").strip() or blueprint_id
    return blueprint_id, label


def _row_search_blob(row: dict[str, Any]) -> str:
    tags = row.get("tags")
    tag_text = " ".join(str(item or "") for item in tags) if isinstance(tags, list) else str(tags or "")
    return _normalize(
        " ".join(
            [
                str(row.get("blueprint_id") or row.get("id") or ""),
                str(row.get("name") or ""),
                str(row.get("description") or ""),
                tag_text,
            ]
        )
    )


def _snapshot_selection_text(snapshot: TaskLoopSnapshot) -> str:
    parts: list[str] = []
    for value in (
        getattr(snapshot, "objective_summary", ""),
        getattr(snapshot, "pending_step", ""),
    ):
        text = str(value or "").strip()
        if text and text not in parts:
            parts.append(text)
    for step in list(getattr(snapshot, "current_plan", []) or []):
        text = str(step or "").strip()
        if text and text not in parts:
            parts.append(text)
    return " ".join(parts)


def _context_blueprint_hint(capability_context: dict[str, Any] | None) -> str:
    context = capability_context if isinstance(capability_context, dict) else {}
    known_fields = context.get("known_fields")
    if isinstance(known_fields, dict):
        value = str(known_fields.get("blueprint") or "").strip()
        if value:
            return value
    for key in ("blueprint", "blueprint_id", "requested_blueprint"):
        value = str(context.get(key) or "").strip()
        if value:
            return value
    return ""


def _match_blueprint_by_text(candidates: list[dict[str, Any]], text: str) -> dict[str, str]:
    query = _normalize(text)
    if not query:
        return {}
    exact_matches: dict[str, dict[str, str]] = {}
    token_matches: dict[str, dict[str, str]] = {}
    query_tokens = {token for token in query.split() if len(token) >= 3}
    for row in candidates:
        blueprint_id, label = _blueprint_fields(row)
        if not blueprint_id:
            continue
        normalized_id = _normalize(blueprint_id)
        normalized_label = _normalize(label)
        aliases = {
            normalized_id,
            normalized_id.replace("-", " "),
            normalized_label,
            normalized_label.replace("-", " "),
        }
        for alias in {item for item in aliases if item}:
            if alias and (alias in query or query in alias):
                exact_matches[blueprint_id] = {"blueprint_id": blueprint_id, "label": label}
                break
        if blueprint_id in exact_matches:
            continue
        blob = _row_search_blob(row)
        row_tokens = {token for token in blob.split() if len(token) >= 3}
        if query_tokens and row_tokens and query_tokens.issubset(row_tokens):
            token_matches[blueprint_id] = {"blueprint_id": blueprint_id, "label": label}

    if len(exact_matches) == 1:
        return next(iter(exact_matches.values()))
    if len(token_matches) == 1:
        return next(iter(token_matches.values()))
    return {}


def _candidate_blueprint_id(row: dict[str, Any]) -> str:
    return str(row.get("blueprint_id") or row.get("id") or row.get("name") or "").strip()


def _candidate_score(row: dict[str, Any]) -> float:
    try:
        return float(row.get("score") or row.get("confidence") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _candidate_rows_from_mapping(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    rows = mapping.get("_container_candidates")
    if not isinstance(rows, list):
        rows = mapping.get("container_candidates")
    if not isinstance(rows, list):
        resolution = mapping.get("_container_resolution") or mapping.get("container_resolution")
        rows = resolution.get("candidates") if isinstance(resolution, dict) else None
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, dict)]


def _resolution_from_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    resolution = mapping.get("_container_resolution") or mapping.get("container_resolution")
    return dict(resolution) if isinstance(resolution, dict) else {}


def _normalize_candidate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        blueprint_id = _candidate_blueprint_id(row)
        if not blueprint_id:
            continue
        normalized = dict(row)
        normalized["blueprint_id"] = blueprint_id
        normalized["score"] = _candidate_score(row)
        previous = by_id.get(blueprint_id)
        if previous is None or float(normalized["score"]) > float(previous.get("score") or 0.0):
            by_id[blueprint_id] = normalized
    return sorted(by_id.values(), key=lambda item: float(item.get("score") or 0.0), reverse=True)


def extract_container_candidate_resolution(
    snapshot: TaskLoopSnapshot,
    *,
    capability_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    resolution: dict[str, Any] = {}
    context = capability_context if isinstance(capability_context, dict) else {}
    if context:
        resolution = _resolution_from_mapping(context)
        rows.extend(_candidate_rows_from_mapping(context))

    for artifact in reversed(list(snapshot.verified_artifacts or [])):
        if not isinstance(artifact, dict):
            continue
        artifact_type = str(artifact.get("artifact_type") or "").strip().lower()
        if artifact_type == "container_candidate_resolution":
            if not resolution:
                resolution = _resolution_from_mapping(artifact)
            rows.extend(_candidate_rows_from_mapping(artifact))
            break
        if artifact_type == "container_capability_context":
            artifact_context = artifact.get("context")
            if isinstance(artifact_context, dict):
                if not resolution:
                    resolution = _resolution_from_mapping(artifact_context)
                rows.extend(_candidate_rows_from_mapping(artifact_context))
                break

    return {
        "resolution": resolution,
        "candidates": _normalize_candidate_rows(rows),
    }


def _discovered_by_id(discovered: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in discovered:
        blueprint_id, _label = _blueprint_fields(row)
        if blueprint_id:
            by_id[blueprint_id] = row
    return by_id


def _selection_from_candidate(row: dict[str, Any], discovered: list[dict[str, Any]]) -> dict[str, str]:
    blueprint_id = _candidate_blueprint_id(row)
    if not blueprint_id:
        return {}
    discovered_row = _discovered_by_id(discovered).get(blueprint_id, row)
    discovered_id, label = _blueprint_fields(discovered_row)
    return {"blueprint_id": discovered_id or blueprint_id, "label": label or blueprint_id}


def _candidate_explicit_selection(
    resolution: dict[str, Any],
    ranked_candidates: list[dict[str, Any]],
    discovered: list[dict[str, Any]],
) -> dict[str, str]:
    decision = str(resolution.get("decision") or resolution.get("action") or "").strip().lower()
    blueprint_id = str(
        resolution.get("blueprint_id")
        or resolution.get("selected_blueprint_id")
        or resolution.get("selected_id")
        or ""
    ).strip()
    if decision in {"use_blueprint", "selected", "auto_select"} and blueprint_id:
        return _selection_from_candidate({"blueprint_id": blueprint_id}, discovered)
    if len(ranked_candidates) == 1:
        return _selection_from_candidate(ranked_candidates[0], discovered)
    return {}


def _candidate_confident_selection(
    ranked_candidates: list[dict[str, Any]],
    discovered: list[dict[str, Any]],
) -> dict[str, str]:
    if not ranked_candidates:
        return {}
    top = ranked_candidates[0]
    top_score = _candidate_score(top)
    second_score = _candidate_score(ranked_candidates[1]) if len(ranked_candidates) > 1 else 0.0
    if top_score >= _AUTO_SELECT_MIN_SCORE and (top_score - second_score) >= _AUTO_SELECT_MIN_MARGIN:
        return _selection_from_candidate(top, discovered)
    return {}


def _ranked_candidate_options(
    ranked_candidates: list[dict[str, Any]],
    discovered: list[dict[str, Any]],
) -> list[str]:
    labels: list[str] = []
    for row in ranked_candidates:
        if _candidate_score(row) < _SUGGEST_MIN_SCORE:
            continue
        selected = _selection_from_candidate(row, discovered)
        label = str(selected.get("label") or selected.get("blueprint_id") or "").strip()
        if label and label not in labels:
            labels.append(label)
        if len(labels) >= 3:
            break
    return labels


def extract_discovered_blueprints(snapshot: TaskLoopSnapshot) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []
    for artifact in reversed(list(snapshot.verified_artifacts or [])):
        if not isinstance(artifact, dict):
            continue
        if str(artifact.get("artifact_type") or "").strip().lower() != "execution_result":
            continue
        metadata = artifact.get("metadata")
        if not isinstance(metadata, dict):
            continue
        evidence = metadata.get("grounding_evidence")
        if not isinstance(evidence, list):
            continue
        for item in evidence:
            if not isinstance(item, dict):
                continue
            if str(item.get("tool_name") or "").strip().lower() != "blueprint_list":
                continue
            structured = item.get("structured")
            rows = structured.get("blueprints") if isinstance(structured, dict) else None
            if isinstance(rows, list):
                discovered = [row for row in rows if isinstance(row, dict)]
                if discovered:
                    return discovered
    return discovered


def extract_selected_blueprint(snapshot: TaskLoopSnapshot) -> dict[str, str]:
    for artifact in reversed(list(snapshot.verified_artifacts or [])):
        if not isinstance(artifact, dict):
            continue
        if str(artifact.get("artifact_type") or "").strip().lower() != "blueprint_selection":
            continue
        blueprint_id = str(artifact.get("blueprint_id") or "").strip()
        label = str(artifact.get("content") or blueprint_id).strip()
        if blueprint_id:
            return {"blueprint_id": blueprint_id, "label": label}
    return {}


def resolve_blueprint_selection(
    snapshot: TaskLoopSnapshot,
    *,
    user_reply: str = "",
    capability_context: dict[str, Any] | None = None,
) -> dict[str, str]:
    selected = extract_selected_blueprint(snapshot)
    if selected:
        return selected
    candidates = extract_discovered_blueprints(snapshot)
    if not candidates:
        return {}
    selection_sources = [
        user_reply,
        _context_blueprint_hint(capability_context),
        _snapshot_selection_text(snapshot),
    ]
    for source in selection_sources:
        matched = _match_blueprint_by_text(candidates, source)
        if matched:
            return matched
    request_family = str((capability_context or {}).get("request_family") or "").strip().lower()
    if request_family == "python_container":
        python_matches: list[dict[str, str]] = []
        for row in candidates:
            blueprint_id, label = _blueprint_fields(row)
            if not blueprint_id:
                continue
            blob = _row_search_blob(row)
            if "python" in blob:
                python_matches.append({"blueprint_id": blueprint_id, "label": label})
        unique_python_matches = {
            item["blueprint_id"]: item for item in python_matches if str(item.get("blueprint_id") or "").strip()
        }
        if len(unique_python_matches) == 1:
            return next(iter(unique_python_matches.values()))
    candidate_evidence = extract_container_candidate_resolution(snapshot, capability_context=capability_context)
    resolution = candidate_evidence["resolution"]
    ranked_candidates = candidate_evidence["candidates"]
    selected_from_resolution = _candidate_explicit_selection(resolution, ranked_candidates, candidates)
    if selected_from_resolution:
        return selected_from_resolution
    selected_from_candidates = _candidate_confident_selection(ranked_candidates, candidates)
    if selected_from_candidates:
        return selected_from_candidates
    if len(candidates) == 1:
        blueprint_id, label = _blueprint_fields(candidates[0])
        if blueprint_id:
            return {"blueprint_id": blueprint_id, "label": label}
    return {}


def build_container_request_context(
    snapshot: TaskLoopSnapshot,
    *,
    requested_capability: dict[str, Any],
    user_reply: str = "",
    capability_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    capability_action = str(requested_capability.get("capability_action") or "").strip().lower()
    if capability_action != "request_container":
        return {
            "discovered_blueprints": [],
            "selected_blueprint": {},
            "requires_user_choice": False,
            "waiting_message": "",
        }
    discovered = extract_discovered_blueprints(snapshot)
    selected = resolve_blueprint_selection(
        snapshot,
        user_reply=user_reply,
        capability_context=capability_context,
    )
    # Pausieren wenn Blueprints bekannt aber keine eindeutige Auswahl:
    # - mehrere Optionen und keine Auswahl → User soll wählen
    # - genau eine Option aber kein Match (z.B. kein Python-Blueprint) → User informieren
    requires_user_choice = bool(discovered) and not selected
    if requires_user_choice:
        candidate_evidence = extract_container_candidate_resolution(snapshot, capability_context=capability_context)
        ranked_options = _ranked_candidate_options(candidate_evidence["candidates"], discovered)
        fallback_options = [
            label
            for label in (_blueprint_fields(row)[1] for row in discovered[:6])
            if label
        ]
        options = ", ".join(ranked_options or fallback_options)
        if len(discovered) > 1:
            waiting_message = load_prompt(
                "task_loop",
                "container_blueprint_choice",
                options=options,
            )
        else:
            waiting_message = load_prompt(
                "task_loop",
                "container_single_blueprint_choice",
                options=options,
            )
    else:
        waiting_message = ""
    return {
        "discovered_blueprints": discovered,
        "selected_blueprint": selected,
        "requires_user_choice": requires_user_choice,
        "waiting_message": waiting_message,
    }


__all__ = [
    "build_container_request_context",
    "extract_discovered_blueprints",
    "extract_selected_blueprint",
    "resolve_blueprint_selection",
]
