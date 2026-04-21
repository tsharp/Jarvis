"""Tool availability helpers for ControlLayer."""

from __future__ import annotations


def set_mcp_hub(hub, *, log_info_fn) -> object:
    """Assign the MCP hub and emit the existing control-layer log."""
    log_info_fn("[ControlLayer] MCP Hub connected")
    return hub


def is_tool_available(
    tool_name: str,
    *,
    mcp_hub,
    get_hub_fn,
    log_info_fn,
    log_warning_fn,
    get_available_skills_fn,
) -> bool:
    """
    Runtime check for tool availability.
    Fail-closed for non-native tools when hub/discovery is unavailable.
    Native/direct tools stay available.
    """
    if not tool_name:
        return False

    native_tools = {
        "request_container", "home_start", "stop_container", "exec_in_container",
        "blueprint_list", "container_list", "container_inspect", "container_stats", "container_logs",
        "home_read", "home_write", "home_list",
        "autonomous_skill_task", "run_skill", "create_skill",
        "list_skills", "get_skill_info", "validate_skill_code",
        "get_system_info", "get_system_overview",
        "list_secret_names",
    }
    if tool_name in native_tools:
        return True

    hub = mcp_hub
    if hub is None:
        try:
            hub = get_hub_fn()
            hub.initialize()
        except Exception as exc:
            log_warning_fn(
                f"[ControlLayer] Tool availability check failed (hub init) "
                f"for '{tool_name}' - fail-closed: {exc}"
            )
            return False

    try:
        if hub.get_mcp_for_tool(tool_name):
            return True
        tool_def = getattr(hub, "_tool_definitions", {}).get(tool_name, {})
        if tool_def.get("execution") == "direct":
            return True
    except Exception as exc:
        log_warning_fn(
            f"[ControlLayer] Tool availability check failed (discovery) "
            f"for '{tool_name}' - fail-closed: {exc}"
        )
        return False

    try:
        installed_skills = get_available_skills_fn()
        if tool_name in installed_skills:
            log_info_fn(
                f"[ControlLayer] '{tool_name}' resolved as installed skill → available"
            )
            return True
    except Exception:
        pass

    return False
