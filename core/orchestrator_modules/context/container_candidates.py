from __future__ import annotations

import re
from typing import Any, Callable, Dict, Iterable, List, Optional


_BLUEPRINT_HINT_PATTERN = re.compile(r"\b([a-z][a-z0-9]*(?:-[a-z0-9]+)+)\b")
_BLUEPRINT_HINT_SKIP = {
    "follow-up",
    "step-by-step",
    "well-known",
    "real-time",
    "up-to-date",
    "built-in",
}


def extract_blueprint_hint_from_history(
    messages: Optional[Iterable[Any]],
    current_user_text: str,
    *,
    message_content_fn: Callable[[Any], str],
) -> str:
    history = list(messages or [])
    if not history:
        return ""

    current_lower = str(current_user_text or "").lower()
    for msg in reversed(history[-6:]):
        content = message_content_fn(msg)
        if not content:
            continue
        for candidate in _BLUEPRINT_HINT_PATTERN.findall(content.lower()):
            if candidate in _BLUEPRINT_HINT_SKIP:
                continue
            if candidate in current_lower:
                continue
            return candidate
    return ""


def materialize_container_resolution(decision: Any) -> Dict[str, Any]:
    resolution: Dict[str, Any] = {
        "decision": "no_blueprint",
        "blueprint_id": "",
        "score": 0.0,
        "reason": "",
        "candidates": [],
    }

    if not isinstance(decision, dict):
        return resolution

    if decision.get("blocked"):
        resolution["decision"] = "resolver_error"
        resolution["reason"] = str(decision.get("reason") or "blueprint_router_unavailable")
        return resolution

    resolution["decision"] = "suggest_blueprint" if decision.get("suggest") else "use_blueprint"
    resolution["blueprint_id"] = str(decision.get("blueprint_id") or "").strip()
    try:
        resolution["score"] = float(decision.get("score") or 0.0)
    except Exception:
        resolution["score"] = 0.0
    resolution["reason"] = str(decision.get("reason") or "").strip()
    resolution["candidates"] = list(decision.get("candidates") or [])

    if not resolution["candidates"] and resolution["blueprint_id"]:
        resolution["candidates"] = [
            {
                "id": resolution["blueprint_id"],
                "score": float(resolution.get("score") or 0.0),
            }
        ]

    return resolution


def prepare_container_candidate_evidence(
    user_text: str,
    thinking_plan: Dict[str, Any],
    *,
    chat_history: Optional[Iterable[Any]] = None,
    message_content_fn: Callable[[Any], str],
    route_blueprint_request_fn: Callable[[str, Dict[str, Any]], Any],
    log_info_fn: Callable[[str], None],
) -> None:
    if not isinstance(thinking_plan, dict):
        return

    suggested = list(thinking_plan.get("suggested_tools") or [])
    if "request_container" not in suggested:
        return

    thinking_plan["needs_chat_history"] = True

    blueprint_hint = extract_blueprint_hint_from_history(
        chat_history,
        user_text,
        message_content_fn=message_content_fn,
    )
    if blueprint_hint and blueprint_hint.lower() not in str(thinking_plan.get("intent") or "").lower():
        current_intent = str(thinking_plan.get("intent") or "").strip()
        thinking_plan["intent"] = f"{current_intent} {blueprint_hint}".strip()
        log_info_fn(f"[Orchestrator] Container candidate hint injected: '{blueprint_hint}'")

    resolution = materialize_container_resolution(
        route_blueprint_request_fn(user_text, thinking_plan)
    )
    thinking_plan["_container_resolution"] = resolution
    thinking_plan["_container_candidates"] = list(resolution.get("candidates") or [])
    log_info_fn(
        "[Orchestrator] Container candidate evidence prepared: "
        f"decision={resolution['decision']} "
        f"candidates={[c.get('id') for c in resolution.get('candidates', []) if isinstance(c, dict)]}"
    )
