from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.task_loop.action_resolution.contracts import (
    ActionResolutionDecision,
    ActionResolutionMode,
    ActionResolutionSource,
    ResolvedLoopAction,
)
from core.task_loop.capability_policy import (
    CONTAINER_ACTION_TOOLS,
    CONTAINER_QUERY_TOOLS,
    capability_type_from_tools,
    normalized_tools,
)

SKILL_QUERY_TOOLS: frozenset[str] = frozenset({
    "list_skills",
    "get_skill_info",
})

SKILL_ACTION_TOOLS: frozenset[str] = frozenset({
    "run_skill",
    "create_skill",
    "autonomous_skill_task",
})

CRON_QUERY_TOOLS: frozenset[str] = frozenset({
    "autonomy_cron_status",
    "autonomy_cron_list_jobs",
    "autonomy_cron_queue",
    "autonomy_cron_validate",
    "cron_reference_links_list",
})

CRON_ACTION_TOOLS: frozenset[str] = frozenset({
    "autonomy_cron_create_job",
    "autonomy_cron_update_job",
    "autonomy_cron_run_now",
    "autonomy_cron_delete_job",
    "autonomy_cron_pause_job",
    "autonomy_cron_resume_job",
})


def _mcp_query_tools(tools: List[str]) -> List[str]:
    return [
        tool
        for tool in tools
        if tool.startswith("mcp_")
        and any(token in tool for token in ("list", "info", "inspect", "status", "search", "schema"))
    ]


def _mcp_action_tools(tools: List[str]) -> List[str]:
    return [tool for tool in tools if tool.startswith("mcp_") and tool not in set(_mcp_query_tools(tools))]


def split_read_vs_action_tools(
    suggested_tools: List[str] | None,
    *,
    capability_type: str = "",
) -> Tuple[List[str], List[str]]:
    tools = normalized_tools(suggested_tools or [])
    capability = str(capability_type or "").strip().lower() or capability_type_from_tools(tools)

    if capability == "container_manager":
        query_tools = [tool for tool in tools if tool in CONTAINER_QUERY_TOOLS]
        action_tools = [tool for tool in tools if tool in CONTAINER_ACTION_TOOLS]
        return query_tools, action_tools

    if capability == "skill_cron":
        query_tools = [tool for tool in tools if tool in (SKILL_QUERY_TOOLS | CRON_QUERY_TOOLS)]
        action_tools = [tool for tool in tools if tool in (SKILL_ACTION_TOOLS | CRON_ACTION_TOOLS)]
        return query_tools, action_tools

    if capability == "mcp":
        return _mcp_query_tools(tools), _mcp_action_tools(tools)

    query_tools = [
        tool
        for tool in tools
        if any(token in tool for token in ("list", "info", "inspect", "status", "search", "validate"))
    ]
    action_tools = [tool for tool in tools if tool not in set(query_tools)]
    return query_tools, action_tools


def preferred_read_first_tools(
    *,
    capability_type: str = "",
    suggested_tools: List[str] | None = None,
    capability_context: Dict[str, Any] | None = None,
) -> List[str]:
    tools = normalized_tools(suggested_tools or [])
    context = dict(capability_context or {})
    capability = str(capability_type or "").strip().lower() or capability_type_from_tools(tools)
    query_tools, action_tools = split_read_vs_action_tools(
        tools,
        capability_type=capability,
    )

    if query_tools:
        return query_tools

    if not action_tools:
        return []

    if capability == "container_manager":
        request_family = str(context.get("request_family") or "").strip().lower()
        if request_family == "python_container":
            return ["blueprint_list"]
        return ["container_list"]

    if capability == "skill_cron":
        if any(tool in CRON_ACTION_TOOLS for tool in action_tools):
            return ["autonomy_cron_status"]
        return ["list_skills"]

    if capability == "mcp":
        return []

    return []


def should_use_read_first(
    *,
    capability_type: str = "",
    suggested_tools: List[str] | None = None,
    capability_context: Dict[str, Any] | None = None,
) -> bool:
    tools = normalized_tools(suggested_tools or [])
    capability = str(capability_type or "").strip().lower() or capability_type_from_tools(tools)
    _query_tools, action_tools = split_read_vs_action_tools(
        tools,
        capability_type=capability,
    )
    preferred_tools = preferred_read_first_tools(
        capability_type=capability,
        suggested_tools=tools,
        capability_context=capability_context,
    )
    return bool(action_tools and preferred_tools)


def maybe_resolve_read_first_action(step_request: Any) -> ActionResolutionDecision | None:
    suggested_tools = list(getattr(step_request, "suggested_tools", []) or [])
    requested_capability = dict(getattr(step_request, "requested_capability", {}) or {})
    capability_context = dict(getattr(step_request, "capability_context", {}) or {})
    capability_type = str(requested_capability.get("capability_type") or "").strip().lower()

    if not should_use_read_first(
        capability_type=capability_type,
        suggested_tools=suggested_tools,
        capability_context=capability_context,
    ):
        return None

    read_tools = preferred_read_first_tools(
        capability_type=capability_type,
        suggested_tools=suggested_tools,
        capability_context=capability_context,
    )
    if not read_tools:
        return None

    step_title = str(getattr(step_request, "step_title", "") or "").strip()
    return ActionResolutionDecision(
        resolved=True,
        action=ResolvedLoopAction(
            mode=ActionResolutionMode.INSERT_DISCOVERY_STEP,
            title=step_title,
            step_type="tool_execution_step",
            suggested_tools=read_tools,
            requested_capability={
                "capability_type": capability_type or capability_type_from_tools(read_tools) or "tool",
                "capability_target": read_tools[0],
                "capability_action": read_tools[0],
            },
            capability_context=capability_context,
            metadata={
                "original_suggested_tools": list(suggested_tools),
                "policy": "read_first",
            },
        ),
        source=ActionResolutionSource.READ_FIRST_POLICY,
        rationale=[
            "mixed_or_action_only_flow_detected",
            "safe_discovery_preferred_before_action",
        ],
        detail=f"read_first:{','.join(read_tools)}",
    )


__all__ = [
    "CRON_ACTION_TOOLS",
    "CRON_QUERY_TOOLS",
    "SKILL_ACTION_TOOLS",
    "SKILL_QUERY_TOOLS",
    "maybe_resolve_read_first_action",
    "preferred_read_first_tools",
    "should_use_read_first",
    "split_read_vs_action_tools",
]
