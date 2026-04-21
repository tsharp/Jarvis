"""Sequential run helpers for non-streaming execution."""

from __future__ import annotations

from typing import Any


async def check_sequential_thinking(
    user_text: str,
    thinking_plan: dict[str, Any],
    *,
    mcp_hub,
    registry,
    asyncio_module,
    log_info_fn,
    log_error_fn,
) -> dict[str, Any] | None:
    """Run the non-streaming sequential MCP path."""
    if not thinking_plan.get("needs_sequential_thinking", False):
        return None
    if not mcp_hub:
        log_error_fn("[ControlLayer] MCP Hub not connected!")
        return None

    complexity = thinking_plan.get("sequential_complexity", 5)
    log_info_fn(f"[ControlLayer] Triggering Sequential (complexity={complexity})")
    try:
        # Offload synchronous MCP call so orchestrator-level timeouts can cancel cleanly.
        result = await asyncio_module.to_thread(
            mcp_hub.call_tool,
            "think",
            {"message": user_text, "steps": complexity},
        )
        if isinstance(result, dict) and "error" in result:
            log_error_fn(f"[ControlLayer] Sequential failed: {result['error']}")
            return None
        task_id = registry.create_task(user_text, complexity)
        registry.update_status(task_id, "running")
        registry.set_result(task_id, result)
        return result
    except Exception as exc:
        log_error_fn(f"[ControlLayer] Sequential failed: {exc}")
        return None
