"""Correction-application helpers for ControlLayer."""

from __future__ import annotations

from typing import Any


def apply_corrections(
    thinking_plan: dict[str, Any],
    verification: dict[str, Any],
    *,
    sanitize_warning_messages_fn,
    tool_names_fn,
    normalize_resolution_strategy_fn,
    derive_authoritative_execution_mode_fn,
    derive_authoritative_turn_mode_fn,
) -> dict[str, Any]:
    """Merge verification corrections back into the thinking plan."""
    corrected = thinking_plan.copy()
    for key, value in verification.get("corrections", {}).items():
        if value is not None:
            corrected[key] = value
    corrected["_verified"] = True
    corrected["_final_instruction"] = verification.get("final_instruction", "")
    corrected["_warnings"] = sanitize_warning_messages_fn(verification.get("warnings", []))
    authoritative_tools = tool_names_fn(
        verification.get("_authoritative_suggested_tools", []),
        limit=16,
    )
    if authoritative_tools:
        corrected["_authoritative_suggested_tools"] = authoritative_tools
        corrected["suggested_tools"] = list(authoritative_tools)
    elif verification.get("suggested_tools"):
        existing = tool_names_fn(corrected.get("suggested_tools", []), limit=16)
        merged = []
        seen = set()
        for name in existing + tool_names_fn(verification.get("suggested_tools", []), limit=16):
            if not name or name in seen:
                continue
            seen.add(name)
            merged.append(name)
        corrected["suggested_tools"] = merged
    authoritative_strategy = normalize_resolution_strategy_fn(
        verification.get("_authoritative_resolution_strategy")
        or corrected.get("_authoritative_resolution_strategy")
        or corrected.get("resolution_strategy")
    )
    if authoritative_strategy:
        corrected["_authoritative_resolution_strategy"] = authoritative_strategy
        corrected["resolution_strategy"] = authoritative_strategy
    authoritative_execution_mode, execution_mode_reasons, execution_mode_blockers = (
        derive_authoritative_execution_mode_fn(
            verification,
            corrected,
        )
    )
    corrected["_authoritative_execution_mode"] = authoritative_execution_mode
    corrected["execution_mode"] = authoritative_execution_mode
    corrected["_authoritative_execution_mode_reasons"] = list(execution_mode_reasons)
    corrected["_authoritative_execution_mode_reason"] = (
        str(execution_mode_reasons[0]) if execution_mode_reasons else authoritative_execution_mode
    )
    corrected["_authoritative_execution_mode_blockers"] = list(execution_mode_blockers)
    explicit_turn_mode_requested = any(
        str(value or "").strip()
        for value in (
            verification.get("_authoritative_turn_mode"),
            corrected.get("_authoritative_turn_mode"),
            corrected.get("turn_mode"),
        )
    )
    if explicit_turn_mode_requested:
        authoritative_turn_mode, turn_mode_reasons, turn_mode_blockers = (
            derive_authoritative_turn_mode_fn(
                verification,
                corrected,
            )
        )
    else:
        authoritative_turn_mode = {
            "task_loop": "task_loop",
            "interactive_defer": "interactive_defer",
        }.get(authoritative_execution_mode, "single_turn")
        turn_mode_reasons = list(execution_mode_reasons)
        turn_mode_blockers = list(execution_mode_blockers)
    corrected["_authoritative_turn_mode"] = authoritative_turn_mode
    corrected["turn_mode"] = authoritative_turn_mode
    corrected["_authoritative_turn_mode_reasons"] = list(turn_mode_reasons)
    corrected["_authoritative_turn_mode_reason"] = (
        str(turn_mode_reasons[0]) if turn_mode_reasons else authoritative_turn_mode
    )
    corrected["_authoritative_turn_mode_blockers"] = list(turn_mode_blockers)
    if verification.get("_cim_decision"):
        corrected["_cim_decision"] = verification["_cim_decision"]
    return corrected
