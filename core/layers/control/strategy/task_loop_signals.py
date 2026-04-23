"""Deterministic task-loop signal hardening for ControlLayer.

Control bleibt hier bewusst dumm:
- keine Planung
- keine Tool-/Prompt-Ausführung
- nur robuste, strukturierte Mehrschritt-Signale aus User-Text + Plan
"""

from __future__ import annotations

from typing import Any


_PHASE_MARKERS = (
    " zuerst ",
    " erst ",
    " dann ",
    " danach ",
    " anschliessend ",
    " anschließend ",
    " schritt ",
    " schritte ",
    " step ",
    " schrittweise ",
)

_DISCOVERY_MARKERS = (
    "pruef",
    "prüf",
    "check",
    "find",
    "suche",
    "such",
    "waehl",
    "wähl",
    "waehle",
    "wähle",
    "auswahl",
    "passend",
    "beste option",
    "richtige",
    "verfuegbar",
    "verfügbar",
)

_ACTION_MARKERS = (
    "starte",
    "start",
    "deploy",
    "bereitstell",
    "aufsetz",
    "aufbau",
    "einricht",
    "konfigurier",
    "erstelle",
    "anlegen",
    "bring",
    "startklar",
    "fertig",
)

_CONTAINER_DOMAIN_MARKERS = (
    "container",
    "sandbox",
    "blueprint",
    "runtime",
    "entwicklungsumgebung",
    "dev-umgebung",
    "python-umgebung",
)

_EXPLAIN_ONLY_MARKERS = (
    "was fehlt",
    "warum",
    "welcher blocker",
    "welcher block",
    "status",
)


def _normalized_text(value: Any) -> str:
    return f" {str(value or '').strip().lower()} "


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _container_context(plan: dict[str, Any]) -> dict[str, Any]:
    ctx = plan.get("_container_capability_context")
    if isinstance(ctx, dict):
        return dict(ctx)
    ctx = plan.get("capability_context")
    if isinstance(ctx, dict):
        return dict(ctx)
    unresolved = plan.get("_unresolved_task_context")
    if isinstance(unresolved, dict):
        nested = unresolved.get("capability_context")
        if isinstance(nested, dict):
            return dict(nested)
    return {}


def _known_fields(plan: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    known = ctx.get("known_fields")
    if isinstance(known, dict):
        return {str(k): v for k, v in known.items() if v not in (None, "", [], {})}
    unresolved = plan.get("_unresolved_task_context")
    if isinstance(unresolved, dict):
        nested = unresolved.get("capability_context")
        if isinstance(nested, dict) and isinstance(nested.get("known_fields"), dict):
            return {
                str(k): v
                for k, v in nested.get("known_fields", {}).items()
                if v not in (None, "", [], {})
            }
    return {}


def _has_unresolved_actionable_context(plan: dict[str, Any]) -> bool:
    unresolved = plan.get("_unresolved_task_context")
    if not isinstance(unresolved, dict):
        return False
    if str(unresolved.get("task_topic") or "").strip():
        return True
    if str(unresolved.get("next_step") or "").strip():
        return True
    if str(unresolved.get("blocker") or "").strip():
        return True
    return False


def prepare_task_loop_signals(user_text: str, thinking_plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(thinking_plan, dict):
        return {}

    plan = dict(thinking_plan)
    text = _normalized_text(user_text)
    ctx = _container_context(plan)
    known_fields = _known_fields(plan, ctx)
    request_family = str(ctx.get("request_family") or "").strip().lower()
    resolution_strategy = str(
        plan.get("_authoritative_resolution_strategy")
        or plan.get("resolution_strategy")
        or ""
    ).strip().lower()
    dialogue_act = str(plan.get("dialogue_act") or "").strip().lower()
    is_fact_query = bool(plan.get("is_fact_query"))

    has_domain_signal = bool(request_family) or _contains_any(text, _CONTAINER_DOMAIN_MARKERS)
    has_phase_signal = _contains_any(text, _PHASE_MARKERS)
    has_discovery_signal = _contains_any(text, _DISCOVERY_MARKERS)
    has_action_signal = _contains_any(text, _ACTION_MARKERS)
    explain_only = _contains_any(text, _EXPLAIN_ONLY_MARKERS)

    reasons: list[str] = []

    if _has_unresolved_actionable_context(plan) and has_action_signal and not explain_only:
        reasons.append("open_work_context_execute")

    if (
        resolution_strategy == "container_request"
        and has_domain_signal
        and has_action_signal
        and not is_fact_query
        and dialogue_act in {"", "request", "analysis", "question"}
    ):
        reasons.append("container_request_action")

    if (
        resolution_strategy == "container_blueprint_catalog"
        and has_domain_signal
        and has_action_signal
        and not explain_only
    ):
        reasons.append("blueprint_catalog_followed_by_action")

    if has_domain_signal and has_discovery_signal and has_action_signal and not explain_only:
        reasons.append("discovery_then_action_chain")

    if request_family == "python_container" and "blueprint" not in known_fields:
        if has_action_signal or has_discovery_signal or resolution_strategy == "container_request":
            reasons.append("python_container_requires_blueprint_selection")

    if has_phase_signal and has_domain_signal and (has_discovery_signal or has_action_signal):
        reasons.append("explicit_phase_markers")

    deduped: list[str] = []
    seen = set()
    for item in reasons:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)

    strong = bool(deduped)
    plan["_task_loop_signal_strong"] = strong
    if deduped:
        plan["_task_loop_signal_reasons"] = list(deduped)

    if strong:
        if not plan.get("task_loop_candidate"):
            plan["task_loop_candidate"] = True
        if str(plan.get("task_loop_kind") or "").strip().lower() in {"", "none"}:
            plan["task_loop_kind"] = "visible_multistep"
        try:
            confidence = float(plan.get("task_loop_confidence", 0.0) or 0.0)
        except Exception:
            confidence = 0.0
        if confidence < 0.78:
            plan["task_loop_confidence"] = 0.78
        if not plan.get("task_loop_reason"):
            plan["task_loop_reason"] = deduped[0]

    return plan


__all__ = ["prepare_task_loop_signals"]
