"""Execution-mode helpers for ControlLayer."""

from __future__ import annotations

from typing import Any


ACTIVE_TASK_LOOP_PRESENT_REASON = "active_task_loop_present"


def normalize_execution_mode(value: Any) -> str:
    """Normalize execution-mode values to the supported control states."""
    execution_mode = str(value or "").strip().lower()
    if execution_mode in {"direct", "task_loop", "interactive_defer"}:
        return execution_mode
    return ""


def execution_mode_to_turn_mode(execution_mode: Any) -> str:
    normalized = normalize_execution_mode(execution_mode)
    if normalized == "task_loop":
        return "task_loop"
    if normalized == "interactive_defer":
        return "interactive_defer"
    return "single_turn"


def turn_mode_to_execution_mode(turn_mode: Any, *, normalize_turn_mode_fn) -> str:
    normalized = normalize_turn_mode_fn(turn_mode)
    if normalized == "task_loop":
        return "task_loop"
    if normalized == "interactive_defer":
        return "interactive_defer"
    if normalized == "single_turn":
        return "direct"
    return ""


def derive_authoritative_execution_mode(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    normalize_execution_mode_fn,
    normalize_turn_mode_fn,
) -> tuple[str, list[str], list[str]]:
    """Derive the authoritative execution mode from verified plan state."""
    if not isinstance(thinking_plan, dict):
        return "direct", ["default_direct"], []

    requested = normalize_execution_mode_fn(
        verification.get("_authoritative_execution_mode")
        or thinking_plan.get("_authoritative_execution_mode")
        or thinking_plan.get("execution_mode")
    )
    # A bare/default direct marker must not suppress stronger task-loop
    # signals from the verified plan. Only non-default execution modes act
    # as explicit overrides here.
    if requested in {"task_loop", "interactive_defer"}:
        return requested, [f"explicit_execution_mode:{requested}"], []

    requested_turn_mode = normalize_turn_mode_fn(
        verification.get("_authoritative_turn_mode")
        or thinking_plan.get("_authoritative_turn_mode")
        or thinking_plan.get("turn_mode")
    )
    # A bare/default single_turn marker must not suppress stronger task-loop
    # signals from the verified plan. Only non-default turn modes act as
    # explicit execution-mode overrides here.
    if requested_turn_mode in {"task_loop", "interactive_defer"}:
        requested_via_turn_mode = turn_mode_to_execution_mode(
            requested_turn_mode,
            normalize_turn_mode_fn=normalize_turn_mode_fn,
        )
        if requested_via_turn_mode:
            return requested_via_turn_mode, [f"explicit_turn_mode:{requested_via_turn_mode}"], []

    blockers: list[str] = []
    if verification.get("approved") is False:
        blockers.append(str(verification.get("block_reason_code") or "control_denied"))
        return "direct", ["control_denied"], blockers
    if verification.get("_needs_skill_confirmation") or thinking_plan.get("_pending_intent"):
        return "interactive_defer", ["confirmation_pending"], []
    if bool(thinking_plan.get("_task_loop_active")):
        return "task_loop", [ACTIVE_TASK_LOOP_PRESENT_REASON], []

    candidate = bool(thinking_plan.get("task_loop_candidate"))
    strong_signal = bool(thinking_plan.get("_task_loop_signal_strong"))
    strong_reasons = [
        str(item).strip()
        for item in list(thinking_plan.get("_task_loop_signal_reasons") or [])
        if str(item).strip()
    ]
    explicit_signal = bool(thinking_plan.get("_task_loop_explicit_signal"))
    needs_visible_progress = bool(thinking_plan.get("needs_visible_progress"))
    complexity = int(thinking_plan.get("sequential_complexity", 0) or 0)

    if candidate and (explicit_signal or strong_signal or needs_visible_progress or complexity >= 7):
        reasons: list[str] = []
        if explicit_signal:
            reasons.append("explicit_task_loop_signal")
        if strong_signal:
            reasons.extend(strong_reasons or ["strong_task_loop_signal"])
        if needs_visible_progress:
            reasons.append("needs_visible_progress")
        if complexity >= 7:
            reasons.append(f"sequential_complexity_{complexity}")
        if not reasons:
            reasons.append("task_loop_candidate")
        return "task_loop", reasons, []

    if strong_signal:
        return "task_loop", (strong_reasons or ["strong_task_loop_signal"]), []

    return "direct", ["default_direct"], []


__all__ = [
    "ACTIVE_TASK_LOOP_PRESENT_REASON",
    "derive_authoritative_execution_mode",
    "execution_mode_to_turn_mode",
    "normalize_execution_mode",
    "turn_mode_to_execution_mode",
]
