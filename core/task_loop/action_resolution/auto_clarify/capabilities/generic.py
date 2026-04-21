"""Generic fallback auto-clarify handler."""

from __future__ import annotations

from typing import Any, Dict, List

from core.task_loop.action_resolution.auto_clarify.contracts import (
    AutoClarifyAction,
    AutoClarifyMode,
    AutoClarifyValueSource,
    MissingField,
    ResolvedField,
)
from core.task_loop.action_resolution.auto_clarify.safety_gates import (
    AutonomyCandidateScore,
)
from core.task_loop.capability_policy import (
    CONTAINER_QUERY_TOOLS,
    capability_type_from_tools,
    normalized_tools,
)
from core.task_loop.contracts import TaskLoopStepType

SKILL_QUERY_TOOLS = frozenset({"list_skills", "get_skill_info"})
CRON_QUERY_TOOLS = frozenset({"autonomy_cron_status", "autonomy_cron_list"})


def _step_type_value(step_request: Any) -> str:
    step_type = getattr(step_request, "step_type", "")
    return str(getattr(step_type, "value", step_type) or TaskLoopStepType.TOOL_EXECUTION.value)


def _capability_family(step_request: Any) -> str:
    requested_capability = dict(getattr(step_request, "requested_capability", {}) or {})
    family = str(requested_capability.get("capability_type") or "").strip().lower()
    if family:
        return family
    return capability_type_from_tools(list(getattr(step_request, "suggested_tools", []) or []))


def _missing_fields(step_request: Any) -> List[MissingField]:
    capability_context = dict(getattr(step_request, "capability_context", {}) or {})
    raw_missing = capability_context.get("missing_fields") or []
    items: List[MissingField] = []
    for entry in raw_missing:
        if isinstance(entry, dict):
            name = str(entry.get("name") or "").strip()
            if not name:
                continue
            items.append(
                MissingField(
                    name=name,
                    reason=str(entry.get("reason") or "").strip(),
                    expected_type=str(entry.get("expected_type") or "").strip(),
                    required=bool(entry.get("required", True)),
                    current_value=entry.get("current_value"),
                    metadata=dict(entry.get("metadata") or {}),
                )
            )
            continue
        name = str(entry or "").strip()
        if name:
            items.append(MissingField(name=name))
    return items


def _resolved_fields(step_request: Any) -> List[ResolvedField]:
    capability_context = dict(getattr(step_request, "capability_context", {}) or {})
    known_fields = dict(capability_context.get("known_fields") or {})
    items: List[ResolvedField] = []
    for key, value in known_fields.items():
        field_name = str(key or "").strip()
        if not field_name:
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


def _query_tools(tools: List[str]) -> List[str]:
    query_tools: List[str] = []
    for tool in tools:
        if (
            tool in CONTAINER_QUERY_TOOLS
            or tool in SKILL_QUERY_TOOLS
            or tool in CRON_QUERY_TOOLS
            or tool.startswith("mcp_list")
            or tool.startswith("mcp_get")
        ):
            query_tools.append(tool)
    return query_tools


def build_generic_auto_clarify_proposal(
    snapshot: Any,
    step_request: Any,
    *,
    step_result: Any | None = None,
    capability_family: str = "",
) -> Dict[str, Any]:
    _ = snapshot
    _ = step_result

    family = str(capability_family or _capability_family(step_request) or "generic").strip().lower()
    tools = normalized_tools(list(getattr(step_request, "suggested_tools", []) or []))
    requested_capability = dict(getattr(step_request, "requested_capability", {}) or {})
    capability_context = dict(getattr(step_request, "capability_context", {}) or {})
    missing_fields = _missing_fields(step_request)
    resolved_fields = _resolved_fields(step_request)
    candidates: List[AutonomyCandidateScore] = []
    query_tools = _query_tools(tools)
    step_type = _step_type_value(step_request)

    if query_tools:
        candidates.append(
            AutonomyCandidateScore(
                key="generic_read_first_discovery",
                score=0.85,
                action=AutoClarifyAction(
                    mode=AutoClarifyMode.SELF_DISCOVER,
                    title="Sichere Discovery zuerst ausfuehren",
                    step_type=step_type,
                    capability_family=family,
                    suggested_tools=query_tools,
                    requested_capability=requested_capability,
                    capability_context=capability_context,
                    fields_to_resolve=[item.name for item in missing_fields],
                ),
                rationale=["read_only_query_tools_available"],
            )
        )

    if (tools or requested_capability) and not missing_fields:
        candidates.append(
            AutonomyCandidateScore(
                key="generic_existing_action_ready",
                score=0.82,
                action=AutoClarifyAction(
                    mode=AutoClarifyMode.SELF_COMPLETE,
                    title="Vorhandene Aktion autonom weiterfuehren",
                    step_type=step_type,
                    capability_family=family,
                    suggested_tools=tools,
                    requested_capability=requested_capability,
                    capability_context=capability_context,
                ),
                rationale=["step_has_action_metadata_without_missing_fields"],
            )
        )

    if (tools or requested_capability) and missing_fields:
        candidates.append(
            AutonomyCandidateScore(
                key="generic_partial_self_discovery",
                score=0.60,
                action=AutoClarifyAction(
                    mode=AutoClarifyMode.SELF_DISCOVER,
                    title="Zuerst fehlende Felder weiter eingrenzen",
                    step_type=step_type,
                    capability_family=family,
                    suggested_tools=query_tools or tools,
                    requested_capability=requested_capability,
                    capability_context=capability_context,
                    fields_to_resolve=[item.name for item in missing_fields],
                ),
                rationale=["action_metadata_available_but_missing_fields_remain"],
            )
        )

    ask_user_message = ""
    if missing_fields:
        ask_user_message = (
            "Ich brauche noch Angaben zu: "
            + ", ".join(item.name for item in missing_fields)
            + "."
        )

    return {
        "capability_family": family,
        "candidates": candidates,
        "missing_fields": missing_fields,
        "resolved_fields": resolved_fields,
        "blockers": [],
        "rationale": ["generic_auto_clarify_fallback"],
        "ask_user_message": ask_user_message,
        "detail": "generic_auto_clarify_proposal",
    }


__all__ = ["build_generic_auto_clarify_proposal"]
