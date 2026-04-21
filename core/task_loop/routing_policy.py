from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def normalize_runtime_execution_mode(value: Any) -> str:
    mode = str(value or "").strip().lower()
    if mode in {"direct", "task_loop", "interactive_defer"}:
        return mode
    return ""


def normalize_runtime_turn_mode(value: Any) -> str:
    mode = str(value or "").strip().lower()
    if mode in {"single_turn", "task_loop", "interactive_defer"}:
        return mode
    return ""


def execution_mode_from_turn_mode(turn_mode: Any) -> str:
    normalized = normalize_runtime_turn_mode(turn_mode)
    if normalized == "task_loop":
        return "task_loop"
    if normalized == "interactive_defer":
        return "interactive_defer"
    if normalized == "single_turn":
        return "direct"
    return ""


def turn_mode_from_execution_mode(execution_mode: Any) -> str:
    normalized = normalize_runtime_execution_mode(execution_mode)
    if normalized == "task_loop":
        return "task_loop"
    if normalized == "interactive_defer":
        return "interactive_defer"
    if normalized == "direct":
        return "single_turn"
    return ""


def resolve_runtime_execution_mode(plan: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    if not isinstance(plan, dict):
        return "", ""
    execution_mode = normalize_runtime_execution_mode(
        plan.get("_authoritative_execution_mode")
        or plan.get("execution_mode")
    )
    if execution_mode:
        return execution_mode, "execution_mode"
    turn_mode = normalize_runtime_turn_mode(
        plan.get("_authoritative_turn_mode")
        or plan.get("turn_mode")
    )
    compat_mode = execution_mode_from_turn_mode(turn_mode)
    if compat_mode:
        return compat_mode, "turn_mode_compat"
    return "", ""


def resolve_runtime_turn_mode(plan: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    if not isinstance(plan, dict):
        return "", ""
    execution_mode, source = resolve_runtime_execution_mode(plan)
    derived_turn_mode = turn_mode_from_execution_mode(execution_mode)
    if derived_turn_mode:
        return derived_turn_mode, source or "execution_mode"
    turn_mode = normalize_runtime_turn_mode(
        plan.get("_authoritative_turn_mode")
        or plan.get("turn_mode")
    )
    if turn_mode:
        return turn_mode, "turn_mode_compat"
    return "", ""


def is_authoritative_task_loop_execution(plan: Optional[Dict[str, Any]]) -> bool:
    execution_mode, _source = resolve_runtime_execution_mode(plan)
    return execution_mode == "task_loop"


__all__ = [
    "execution_mode_from_turn_mode",
    "is_authoritative_task_loop_execution",
    "normalize_runtime_execution_mode",
    "normalize_runtime_turn_mode",
    "resolve_runtime_execution_mode",
    "resolve_runtime_turn_mode",
    "turn_mode_from_execution_mode",
]
