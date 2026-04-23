"""Turn-mode helpers for ControlLayer."""

from __future__ import annotations

from typing import Any

from .execution_mode import (
    ACTIVE_TASK_LOOP_PRESENT_REASON,
    execution_mode_to_turn_mode,
    turn_mode_to_execution_mode,
)


def normalize_turn_mode(value: Any) -> str:
    """Normalize turn-mode values to the supported control states."""
    turn_mode = str(value or "").strip().lower()
    if turn_mode in {"single_turn", "task_loop", "interactive_defer"}:
        return turn_mode
    return ""


def derive_authoritative_turn_mode(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    normalize_turn_mode_fn,
) -> tuple[str, list[str], list[str]]:
    """Derive the authoritative turn mode from verified plan state."""
    if not isinstance(thinking_plan, dict):
        return "single_turn", ["default_single_turn"], []

    requested_execution_mode = (
        verification.get("_authoritative_execution_mode")
        or thinking_plan.get("_authoritative_execution_mode")
        or thinking_plan.get("execution_mode")
    )
    requested_from_execution_mode = execution_mode_to_turn_mode(requested_execution_mode)
    # A bare/default direct execution mode should not suppress stronger
    # task-loop signals. Only non-default execution modes are explicit
    # turn-mode overrides here.
    if requested_from_execution_mode in {"task_loop", "interactive_defer"}:
        return requested_from_execution_mode, [f"explicit_execution_mode:{requested_from_execution_mode}"], []

    requested = normalize_turn_mode_fn(
        verification.get("_authoritative_turn_mode")
        or thinking_plan.get("_authoritative_turn_mode")
        or thinking_plan.get("turn_mode")
    )
    if requested:
        return requested, [f"explicit_turn_mode:{requested}"], []

    blockers: list[str] = []
    if verification.get("approved") is False:
        blockers.append(str(verification.get("block_reason_code") or "control_denied"))
        return "single_turn", ["control_denied"], blockers
    if verification.get("_needs_skill_confirmation") or thinking_plan.get("_pending_intent"):
        return "single_turn", ["confirmation_pending"], []
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

    if turn_mode_to_execution_mode("single_turn", normalize_turn_mode_fn=normalize_turn_mode_fn):
        return "single_turn", ["default_single_turn"], []
    return "single_turn", ["default_single_turn"], []
