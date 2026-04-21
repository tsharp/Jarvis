"""Verification-result stabilization helpers for ControlLayer."""

from __future__ import annotations

from typing import Any


def stabilize_verification_result(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    user_text: str = "",
    default_verification_fn,
    sanitize_warning_messages_fn,
    enforce_block_authority_fn,
    has_hard_safety_markers_fn,
    user_text_has_hard_safety_keywords_fn,
    user_text_has_malicious_intent_fn,
    tool_names_fn,
    is_tool_available_fn,
    looks_like_capability_mismatch_fn,
    should_lift_cron_false_block_fn,
    should_lift_container_false_block_fn,
    should_lift_query_budget_fast_path_false_block_fn,
    should_lift_solution_oriented_false_block_fn,
    apply_container_candidate_resolution_fn,
    apply_resolution_strategy_authority_fn,
    log_warning_fn,
) -> dict[str, Any]:
    """Normalize and deterministically stabilize verification output."""
    if not isinstance(verification, dict):
        return default_verification_fn(thinking_plan)

    if not isinstance(verification.get("corrections"), dict):
        verification["corrections"] = {}
    if not isinstance(verification.get("warnings"), list):
        verification["warnings"] = []
    if not isinstance(verification.get("suggested_tools"), list):
        verification["suggested_tools"] = []
    if verification.get("final_instruction") is None:
        verification["final_instruction"] = ""

    if verification.get("_light_cim"):
        verification["warnings"] = sanitize_warning_messages_fn(verification.get("warnings", []))
        return enforce_block_authority_fn(
            verification,
            thinking_plan,
            user_text=user_text,
        )

    if verification.get("approved") is False:
        if (
            (
                bool((thinking_plan or {}).get("_skill_gate_blocked"))
                or bool((thinking_plan or {}).get("_blueprint_gate_blocked"))
            )
            and not has_hard_safety_markers_fn(verification)
            and not user_text_has_hard_safety_keywords_fn(user_text)
            and not user_text_has_malicious_intent_fn(user_text)
        ):
            warnings = verification.get("warnings")
            if not isinstance(warnings, list):
                warnings = [str(warnings)] if warnings else []
            warnings.append(
                "Deterministic override: tool gate denial is treated as tool-level soft deny, not chat-level block."
            )
            verification["warnings"] = warnings
            verification["approved"] = True
            verification["reason"] = "tool_gate_soft_deny_auto_corrected"

        suggested = tool_names_fn((thinking_plan or {}).get("suggested_tools", []), limit=8)
        if suggested:
            unavailable = [name for name in suggested if not is_tool_available_fn(name)]
            if not unavailable and looks_like_capability_mismatch_fn(verification):
                warnings = verification.get("warnings")
                if not isinstance(warnings, list):
                    warnings = [str(warnings)] if warnings else []
                warnings.append(
                    "Deterministic override: suggested tools are runtime-available; "
                    "control capability mismatch block was lifted."
                )
                verification["warnings"] = warnings
                verification["approved"] = True
                verification["reason"] = "tool_availability_mismatch_auto_corrected"
                log_warning_fn(
                    "[ControlLayer] Auto-corrected false unavailable-tool block "
                    f"for suggested_tools={suggested}"
                )
        if verification.get("approved") is False and should_lift_cron_false_block_fn(verification, thinking_plan):
            warnings = verification.get("warnings")
            if not isinstance(warnings, list):
                warnings = [str(warnings)] if warnings else []
            warnings.append(
                "Deterministic override: cron-domain request with runtime-available cron tools "
                "was blocked by a spurious policy response and has been unblocked."
            )
            verification["warnings"] = warnings
            verification["approved"] = True
            verification["reason"] = "cron_domain_false_block_auto_corrected"
            log_warning_fn(
                "[ControlLayer] Auto-corrected false cron-domain block "
                f"for intent={str((thinking_plan or {}).get('intent') or '')[:120]}"
            )
        if (
            verification.get("approved") is False
            and should_lift_container_false_block_fn(verification, thinking_plan)
        ):
            warnings = verification.get("warnings")
            if not isinstance(warnings, list):
                warnings = [str(warnings)] if warnings else []
            warnings.append(
                "Deterministic override: container-domain request was blocked by a spurious "
                "policy/memory mismatch response and has been unblocked."
            )
            verification["warnings"] = warnings
            verification["approved"] = True
            verification["reason"] = "container_domain_false_block_auto_corrected"
            log_warning_fn(
                "[ControlLayer] Auto-corrected false container-domain block "
                f"for intent={str((thinking_plan or {}).get('intent') or '')[:120]}"
            )
        if (
            verification.get("approved") is False
            and should_lift_query_budget_fast_path_false_block_fn(
                verification,
                thinking_plan,
                user_text=user_text,
            )
        ):
            warnings = verification.get("warnings")
            if not isinstance(warnings, list):
                warnings = [str(warnings)] if warnings else []
            warnings.append(
                "Deterministic override: benign query_budget_fast_path prompt "
                "was blocked by a spurious policy response and has been unblocked."
            )
            verification["warnings"] = warnings
            verification["approved"] = True
            verification["reason"] = "query_budget_fast_path_false_block_auto_corrected"
            log_warning_fn(
                "[ControlLayer] Auto-corrected false query_budget_fast_path block "
                f"for user_text={str(user_text or '')[:120]}"
            )
    if (
        verification.get("approved") is False
        and should_lift_solution_oriented_false_block_fn(
            verification,
            thinking_plan,
            user_text=user_text,
        )
    ):
        warnings = verification.get("warnings")
        if not isinstance(warnings, list):
            warnings = [str(warnings)] if warnings else []
        warnings.append(
            "Deterministic override: solution-oriented runtime/tool execution path exists; "
            "spurious policy block was lifted."
        )
        verification["warnings"] = warnings
        verification["approved"] = True
        verification["reason"] = "solution_oriented_false_block_auto_corrected"
        log_warning_fn(
            "[ControlLayer] Auto-corrected spurious policy block via solution-oriented path "
            f"for intent={str((thinking_plan or {}).get('intent') or '')[:120]}"
        )
    verification = apply_container_candidate_resolution_fn(
        verification,
        thinking_plan,
        user_text=user_text,
    )
    verification = apply_resolution_strategy_authority_fn(
        verification,
        thinking_plan,
        user_text=user_text,
    )
    verification["warnings"] = sanitize_warning_messages_fn(verification.get("warnings", []))
    return enforce_block_authority_fn(
        verification,
        thinking_plan,
        user_text=user_text,
    )
