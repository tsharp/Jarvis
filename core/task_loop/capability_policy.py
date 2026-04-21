from __future__ import annotations

from typing import Any

from core.task_loop.contracts import TaskLoopStepType


SYSTEM_KNOWLEDGE_TOOLS: frozenset[str] = frozenset({
    "get_system_info",
    "get_system_overview",
})

CONTAINER_ACTION_TOOLS: frozenset[str] = frozenset({
    "request_container",
    "stop_container",
    "exec_in_container",
    "blueprint_create",
    "home_start",
})

CONTAINER_QUERY_TOOLS: frozenset[str] = frozenset({
    "blueprint_list",
    "container_list",
    "container_inspect",
    "container_stats",
    "container_logs",
})

SKILL_CRON_TOOLS: frozenset[str] = frozenset({
    "autonomous_skill_task",
    "create_skill",
    "run_skill",
    "list_skills",
    "get_skill_info",
})

WRITE_LIKE_TOOLS: frozenset[str] = CONTAINER_ACTION_TOOLS | frozenset({
    "memory_save",
    "home_write",
    "create_skill",
    "autonomous_skill_task",
})


def normalized_tools(suggested_tools: list[str]) -> list[str]:
    return [
        str(item or "").strip()
        for item in suggested_tools or []
        if str(item or "").strip()
    ]


def capability_type_from_tools(suggested_tools: list[str]) -> str:
    tools = normalized_tools(suggested_tools)
    if not tools:
        return ""
    tool_set = set(tools)
    if tool_set.intersection(CONTAINER_ACTION_TOOLS | CONTAINER_QUERY_TOOLS):
        return "container_manager"
    if tool_set.intersection(SKILL_CRON_TOOLS):
        return "skill_cron"
    if tool_set.intersection(SYSTEM_KNOWLEDGE_TOOLS):
        return "system_knowledge"
    if any(tool.startswith("mcp_") for tool in tools):
        return "mcp"
    return "tool"


def _primary_tool_for_capability(suggested_tools: list[str], capability_type: str) -> str:
    tools = normalized_tools(suggested_tools)
    if not tools:
        return ""
    if capability_type == "container_manager":
        action_tools = [tool for tool in tools if tool in CONTAINER_ACTION_TOOLS]
        if action_tools:
            return action_tools[0]
        query_tools = [tool for tool in tools if tool in CONTAINER_QUERY_TOOLS]
        if query_tools:
            return query_tools[0]
    return tools[0]


def requested_capability_from_tools(suggested_tools: list[str]) -> dict[str, Any]:
    tools = normalized_tools(suggested_tools)
    capability_type = capability_type_from_tools(tools)
    primary_tool = _primary_tool_for_capability(tools, capability_type)
    if not primary_tool:
        return {}
    return {
        "capability_type": capability_type or "tool",
        "capability_target": primary_tool,
        "capability_action": primary_tool,
    }


def scoped_tools_for_step(
    suggested_tools: list[str],
    *,
    step_type: TaskLoopStepType,
) -> list[str]:
    tools = normalized_tools(suggested_tools)
    if not tools:
        return []
    capability_type = capability_type_from_tools(tools)
    if capability_type != "container_manager":
        return tools
    query_tools = [tool for tool in tools if tool in CONTAINER_QUERY_TOOLS]
    action_tools = [tool for tool in tools if tool in CONTAINER_ACTION_TOOLS]
    if query_tools and action_tools and step_type is TaskLoopStepType.TOOL_REQUEST:
        return action_tools
    return tools
