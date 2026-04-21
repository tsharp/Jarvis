"""Container discovery policy.

Ziel:
- read-first Strategie je nach Zielbild
- Auswahl zwischen `blueprint_list`, `container_list`, `container_inspect`
- keine User-Text-Ausgabe, keine Recovery-Texte
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.task_loop.capability_policy import (
    CONTAINER_ACTION_TOOLS,
    CONTAINER_QUERY_TOOLS,
    normalized_tools,
)


def split_container_tools(suggested_tools: List[str] | None) -> tuple[List[str], List[str]]:
    tools = normalized_tools(suggested_tools or [])
    query_tools = [tool for tool in tools if tool in CONTAINER_QUERY_TOOLS]
    action_tools = [tool for tool in tools if tool in CONTAINER_ACTION_TOOLS]
    return query_tools, action_tools


def has_mixed_container_flow(suggested_tools: List[str] | None) -> bool:
    query_tools, action_tools = split_container_tools(suggested_tools)
    return bool(query_tools and action_tools)


def preferred_container_discovery_tools(
    *,
    capability_context: Dict[str, Any] | None = None,
    suggested_tools: List[str] | None = None,
) -> List[str]:
    context = dict(capability_context or {})
    query_tools, action_tools = split_container_tools(suggested_tools)
    request_family = str(context.get("request_family") or "").strip().lower()

    if query_tools:
        return query_tools
    if action_tools and request_family == "python_container":
        return ["blueprint_list"]
    return []


def should_use_read_first(
    *,
    capability_context: Dict[str, Any] | None = None,
    suggested_tools: List[str] | None = None,
) -> bool:
    _query_tools, action_tools = split_container_tools(suggested_tools)
    preferred_query_tools = preferred_container_discovery_tools(
        capability_context=capability_context,
        suggested_tools=suggested_tools,
    )
    return bool(action_tools and preferred_query_tools)


__all__ = [
    "has_mixed_container_flow",
    "preferred_container_discovery_tools",
    "split_container_tools",
    "should_use_read_first",
]
