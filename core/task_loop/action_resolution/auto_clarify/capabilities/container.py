"""Container-specific auto-clarify handler."""

from __future__ import annotations

from typing import Any, Dict, List

from core.task_loop.action_resolution.auto_clarify.capabilities.generic import (
    build_generic_auto_clarify_proposal,
)
from core.task_loop.action_resolution.auto_clarify.contracts import (
    AutoClarifyAction,
    AutoClarifyMode,
    AutoClarifyValueSource,
    MissingField,
    ResolvedField,
)
from core.task_loop.action_resolution.auto_clarify.parameter_completion import (
    complete_container_parameters,
)
from core.task_loop.action_resolution.auto_clarify.safety_gates import (
    AutonomyCandidateScore,
)
from core.task_loop.capabilities.container.parameter_policy import (
    build_container_parameter_context,
)
from core.task_loop.contracts import TaskLoopStepType


def _step_type_value(step_request: Any) -> str:
    step_type = getattr(step_request, "step_type", "")
    return str(getattr(step_type, "value", step_type) or TaskLoopStepType.TOOL_EXECUTION.value)


def _latest_user_reply(snapshot: Any) -> str:
    for artifact in reversed(list(getattr(snapshot, "verified_artifacts", []) or [])):
        if str(artifact.get("artifact_type") or "").strip().lower() != "user_reply":
            continue
        return str(artifact.get("content") or "").strip()
    return ""


def _missing_fields(parameter_context: Dict[str, Any]) -> List[MissingField]:
    items: List[MissingField] = []
    for name in list(parameter_context.get("missing_fields") or []):
        field_name = str(name or "").strip()
        if not field_name:
            continue
        items.append(
            MissingField(
                name=field_name,
                reason="container_parameter_missing",
            )
        )
    return items


def _resolved_fields(
    parameter_context: Dict[str, Any],
    *,
    skip_names: set[str] | None = None,
) -> List[ResolvedField]:
    skip = {str(name or "").strip() for name in (skip_names or set()) if str(name or "").strip()}
    items: List[ResolvedField] = []
    for key, value in dict(parameter_context.get("params") or {}).items():
        field_name = str(key or "").strip()
        if not field_name or field_name in skip:
            continue
        items.append(
            ResolvedField(
                name=field_name,
                value=value,
                source=AutoClarifyValueSource.EXISTING_CONTEXT,
                confidence=0.90,
            )
        )
    return items


def build_container_auto_clarify_proposal(
    snapshot: Any,
    step_request: Any,
    *,
    step_result: Any | None = None,
) -> Dict[str, Any]:
    _ = step_result

    requested_capability = dict(getattr(step_request, "requested_capability", {}) or {})
    capability_context = dict(getattr(step_request, "capability_context", {}) or {})
    capability_action = str(requested_capability.get("capability_action") or "").strip().lower()
    if capability_action != "request_container":
        return build_generic_auto_clarify_proposal(
            snapshot,
            step_request,
            step_result=step_result,
            capability_family="container_manager",
        )

    parameter_context = build_container_parameter_context(
        snapshot,
        requested_capability=requested_capability,
        capability_context=capability_context,
        user_reply=_latest_user_reply(snapshot),
    )
    completion = complete_container_parameters(
        snapshot,
        requested_capability=requested_capability,
        capability_context=capability_context,
        user_reply=_latest_user_reply(snapshot),
    )
    completed_context = dict(completion.get("capability_context") or capability_context)
    if completion.get("parameter_context"):
        parameter_context = dict(completion.get("parameter_context") or parameter_context)
    completion_fields = list(completion.get("resolved_fields") or [])
    missing_fields = _missing_fields(parameter_context)
    resolved_fields = completion_fields + _resolved_fields(
        parameter_context,
        skip_names={field.name for field in completion_fields},
    )
    existing_tools = [str(item or "").strip() for item in list(getattr(step_request, "suggested_tools", []) or []) if str(item or "").strip()]
    discovery_tools = [tool for tool in existing_tools if tool in {"blueprint_list", "container_list"}]
    if "blueprint_list" not in discovery_tools:
        discovery_tools.append("blueprint_list")
    step_type = _step_type_value(step_request)
    candidates: List[AutonomyCandidateScore] = []

    if not missing_fields:
        candidates.append(
            AutonomyCandidateScore(
                key="container_request_ready",
                score=0.91,
                action=AutoClarifyAction(
                    mode=AutoClarifyMode.SELF_COMPLETE,
                    title="Container-Anfrage autonom weiterfuehren",
                    step_type=step_type,
                    capability_family="container_manager",
                    suggested_tools=existing_tools,
                    requested_capability=requested_capability,
                    capability_context=completed_context,
                ),
                rationale=["container_parameters_are_sufficient"],
            )
        )

    if missing_fields:
        score = 0.86 if {item.name for item in missing_fields} == {"blueprint"} else 0.68
        candidates.append(
            AutonomyCandidateScore(
                key="container_discovery_before_user_prompt",
                score=score,
                action=AutoClarifyAction(
                    mode=AutoClarifyMode.SELF_DISCOVER,
                    title="Container-Blueprints und Basisdaten zuerst selbst pruefen",
                    step_type=step_type,
                    capability_family="container_manager",
                    suggested_tools=discovery_tools,
                    requested_capability=requested_capability,
                    capability_context=completed_context,
                    fields_to_resolve=[item.name for item in missing_fields],
                ),
                rationale=["container_missing_fields_require_discovery"],
            )
        )

    return {
        "capability_family": "container_manager",
        "candidates": candidates,
        "missing_fields": missing_fields,
        "resolved_fields": resolved_fields,
        "blockers": [],
        "rationale": ["container_auto_clarify_proposal", *list(completion.get("rationale") or [])],
        "ask_user_message": str(parameter_context.get("waiting_message") or "").strip(),
        "detail": "container_auto_clarify_proposal",
    }


__all__ = ["build_container_auto_clarify_proposal"]
