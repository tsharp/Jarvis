from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional


def build_container_event_content(
    tool_name: str,
    result: Dict[str, Any],
    user_text: str,
    tool_args: Dict[str, Any],
    *,
    session_id: str = "",
    utcnow_fn: Callable[[], datetime],
    resolve_exec_blueprint_id_fn: Callable[[str, Dict[str, Any]], str],
) -> Optional[Dict[str, Any]]:
    if tool_name in {"request_container", "home_start"} and isinstance(result, dict):
        container_id = result.get("container_id", "")
        if result.get("status") == "running" and container_id:
            return {
                "event_type": "container_started",
                "event_data": {
                    "container_id": container_id,
                    "blueprint_id": (
                        tool_args.get("blueprint_id")
                        or result.get("blueprint_id")
                        or "unknown"
                    ),
                    "name": result.get("name", ""),
                    "purpose": user_text[:200],
                    "ttl_seconds": result.get("ttl_seconds"),
                    "session_id": session_id,
                    "started_at": utcnow_fn().isoformat() + "Z",
                },
            }
    elif tool_name == "stop_container" and isinstance(result, dict):
        container_id = result.get("container_id", "")
        if result.get("stopped") and container_id:
            return {
                "event_type": "container_stopped",
                "event_data": {
                    "container_id": container_id,
                    "blueprint_id": result.get("blueprint_id", "unknown"),
                    "session_id": session_id,
                    "stopped_at": utcnow_fn().isoformat() + "Z",
                    "reason": "user_stopped",
                },
            }
    elif tool_name == "exec_in_container" and isinstance(result, dict):
        container_id = result.get("container_id", tool_args.get("container_id", ""))
        if container_id and "error" not in result:
            return {
                "event_type": "container_exec",
                "event_data": {
                    "container_id": container_id,
                    "blueprint_id": resolve_exec_blueprint_id_fn(container_id, tool_args),
                    "command": tool_args.get("command", "")[:500],
                    "exit_code": result.get("exit_code"),
                    "session_id": session_id,
                    "executed_at": utcnow_fn().isoformat() + "Z",
                },
            }
    return None


def save_workspace_entry(
    conversation_id: str,
    content: str,
    *,
    entry_type: str = "observation",
    source_layer: str = "thinking",
    get_workspace_emitter_fn: Callable[[], Any],
) -> Optional[Dict[str, Any]]:
    return get_workspace_emitter_fn().persist(
        conversation_id=conversation_id,
        content=content,
        entry_type=entry_type,
        source_layer=source_layer,
    ).sse_dict


def save_container_event(
    conversation_id: str,
    container_evt: Dict[str, Any],
    *,
    get_workspace_emitter_fn: Callable[[], Any],
) -> Optional[Dict[str, Any]]:
    return get_workspace_emitter_fn().persist_container(
        conversation_id=conversation_id,
        container_evt=container_evt,
    ).sse_dict
