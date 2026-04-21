"""Container recovery policy.

Ziel:
- Outcome-Klassifikation innerhalb der Container-Capability
- naechsten sicheren Tool-Pfad vorschlagen
- keine Snapshot-Manipulation und keine User-Visible-Narration
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.control_contract import DoneReason

RECOVERY_ARTIFACT_TYPE = "container_recovery_hint"
DISCOVERY_STEP_TITLE = "Verfuegbare Blueprints oder Container-Basis pruefen"
RUNTIME_DISCOVERY_STEP_TITLE = "Laufende oder vorhandene Container pruefen"
CONTAINER_INSPECT_STEP_TITLE = "Konkreten Container-Zustand pruefen"


def _tool_rows(execution_result: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    return [
        row
        for row in list((execution_result or {}).get("tool_statuses") or [])
        if isinstance(row, dict)
    ]


def _normalized_statuses(execution_result: Dict[str, Any] | None) -> set[str]:
    return {
        str((row or {}).get("status") or "").strip().lower()
        for row in _tool_rows(execution_result)
        if str((row or {}).get("status") or "").strip()
    }


def _reason_text(execution_result: Dict[str, Any] | None) -> str:
    parts: List[str] = []
    for row in _tool_rows(execution_result):
        reason = str((row or {}).get("reason") or "").strip()
        if reason:
            parts.append(reason.lower())
    return " ".join(parts)


def classify_container_outcome(
    *,
    requested_capability: Dict[str, Any],
    execution_result: Dict[str, Any] | None = None,
    resolved_tools: list[Any] | None = None,
    no_resolved_tools: bool = False,
) -> str:
    capability_action = str(requested_capability.get("capability_action") or "").strip().lower()
    if capability_action != "request_container":
        return ""

    if no_resolved_tools:
        return "no_resolved_tools"

    done_reason = str((execution_result or {}).get("done_reason") or "").strip().lower()
    statuses = _normalized_statuses(execution_result)
    reason_text = _reason_text(execution_result)
    direct_response = str((execution_result or {}).get("direct_response") or "").strip()
    grounding = (execution_result or {}).get("grounding")

    if done_reason == DoneReason.NEEDS_CLARIFICATION.value or "needs_clarification" in statuses:
        return "missing_parameters"
    if done_reason in {DoneReason.ROUTING_BLOCK.value, DoneReason.UNAVAILABLE.value}:
        if any(
            token in reason_text
            for token in (
                "missing_container_id",
                "active_container",
                "active target",
                "active_target",
                "existing_container",
                "host runtime",
                "runtime probe",
                "running container",
                "container_list",
            )
        ):
            return "missing_runtime_inventory"
        if any(
            token in reason_text
            for token in (
                "binding",
                "inspect",
                "container_inspect",
                "known container",
                "selected container",
            )
        ):
            return "missing_container_binding"
        if any(token in reason_text for token in ("no_match", "jit_match", "blueprint", "catalog", "basis")):
            return "missing_blueprint_discovery"
        return "container_route_unavailable"
    if "routing_block" in statuses or "unavailable" in statuses:
        if any(
            token in reason_text
            for token in (
                "missing_container_id",
                "active_container",
                "active target",
                "active_target",
                "existing_container",
                "host runtime",
                "runtime probe",
                "running container",
                "container_list",
            )
        ):
            return "missing_runtime_inventory"
        if any(
            token in reason_text
            for token in (
                "binding",
                "inspect",
                "container_inspect",
                "known container",
                "selected container",
            )
        ):
            return "missing_container_binding"
        if any(token in reason_text for token in ("no_match", "jit_match", "blueprint", "catalog", "basis")):
            return "missing_blueprint_discovery"
        return "container_route_unavailable"
    if resolved_tools and not direct_response and not grounding and "ok" not in statuses:
        return "empty_result"
    return ""


def suggest_container_recovery_tools(
    *,
    outcome_code: str,
    requested_capability: Dict[str, Any],
    capability_context: Dict[str, Any] | None = None,
) -> List[str]:
    capability_action = str(requested_capability.get("capability_action") or "").strip().lower()
    if capability_action != "request_container":
        return []
    known_fields = dict((capability_context or {}).get("known_fields") or {})
    has_concrete_container_target = bool(
        str(known_fields.get("container_id") or "").strip()
        or str(known_fields.get("container_name") or "").strip()
    )
    if outcome_code == "missing_container_binding":
        return ["container_inspect"] if has_concrete_container_target else ["container_list"]
    if outcome_code == "missing_runtime_inventory":
        return ["container_list"]
    if outcome_code in {
        "no_resolved_tools",
        "missing_blueprint_discovery",
        "container_route_unavailable",
        "empty_result",
    }:
        return ["blueprint_list"]
    return []


def build_container_recovery_hint(
    *,
    requested_capability: Dict[str, Any],
    capability_context: Dict[str, Any] | None = None,
    execution_result: Dict[str, Any] | None = None,
    resolved_tools: list[Any] | None = None,
    no_resolved_tools: bool = False,
) -> Dict[str, Any]:
    outcome_code = classify_container_outcome(
        requested_capability=requested_capability,
        execution_result=execution_result,
        resolved_tools=resolved_tools,
        no_resolved_tools=no_resolved_tools,
    )
    if not outcome_code:
        return {}

    next_tools = suggest_container_recovery_tools(
        outcome_code=outcome_code,
        requested_capability=requested_capability,
        capability_context=capability_context,
    )
    request_family = str((capability_context or {}).get("request_family") or "generic_container").strip().lower()
    if next_tools:
        if next_tools == ["blueprint_list"]:
            step_title = DISCOVERY_STEP_TITLE
        elif next_tools == ["container_list"]:
            step_title = RUNTIME_DISCOVERY_STEP_TITLE
        else:
            step_title = CONTAINER_INSPECT_STEP_TITLE
        return {
            "outcome_code": outcome_code,
            "recovery_mode": "replan_with_tools",
            "reason": outcome_code,
            "next_tools": list(next_tools),
            "replan_step_title": step_title,
            "request_family": request_family,
        }

    if outcome_code == "missing_parameters":
        return {
            "outcome_code": outcome_code,
            "recovery_mode": "needs_user_input",
            "reason": outcome_code,
            "next_tools": [],
            "request_family": request_family,
        }
    return {}


def extract_container_recovery_hint(verified_artifacts: list[dict[str, Any]] | None) -> Dict[str, Any]:
    for artifact in reversed(list(verified_artifacts or [])):
        if not isinstance(artifact, dict):
            continue
        if str(artifact.get("artifact_type") or "").strip().lower() != RECOVERY_ARTIFACT_TYPE:
            continue
        return dict(artifact)
    return {}


__all__ = [
    "CONTAINER_INSPECT_STEP_TITLE",
    "DISCOVERY_STEP_TITLE",
    "RECOVERY_ARTIFACT_TYPE",
    "RUNTIME_DISCOVERY_STEP_TITLE",
    "build_container_recovery_hint",
    "classify_container_outcome",
    "extract_container_recovery_hint",
    "suggest_container_recovery_tools",
]
