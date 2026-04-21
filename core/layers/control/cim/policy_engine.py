"""CIM policy-engine helpers for ControlLayer."""

from __future__ import annotations

from typing import Any

from utils.logger import log_warning


try:
    from intelligence_modules.cim_policy.cim_policy_engine import process_cim as process_cim_policy

    CIM_POLICY_AVAILABLE = True
except ImportError:
    process_cim_policy = None
    CIM_POLICY_AVAILABLE = False
    log_warning("[ControlLayer] CIM Policy Engine not available")


async def run_cim_policy_engine(
    user_text: str,
    thinking_plan: dict[str, Any],
    *,
    cim_policy_available: bool,
    process_cim_policy_fn,
    get_available_skills_async_fn,
    user_text_has_malicious_intent_fn,
    is_skill_creation_sensitive_fn,
    extract_requested_skill_name_fn,
    make_hard_block_verification_fn,
    log_info_fn,
    log_warning_fn,
    log_error_fn,
) -> dict[str, Any] | None:
    """Evaluate CIM skill-policy paths and return an early verification when applicable."""
    domain_route = thinking_plan.get("_domain_route", {}) if isinstance(thinking_plan, dict) else {}
    domain_tag = str((domain_route or {}).get("domain_tag") or "").strip().upper()
    domain_locked = bool((domain_route or {}).get("domain_locked"))
    domain_blocks_skill_confirmation = bool(
        domain_locked and domain_tag == "CRONJOB"
    ) or bool((thinking_plan or {}).get("_domain_skill_confirmation_disabled"))
    keyword_match = False
    cim_decision = None

    if cim_policy_available and process_cim_policy_fn and not domain_blocks_skill_confirmation:
        intent = str(thinking_plan.get("intent", "")).lower()
        skill_keywords = ["skill", "erstelle", "create", "programmier", "bau", "neu"]
        keyword_match = any(keyword in intent or keyword in user_text.lower() for keyword in skill_keywords)
        log_info_fn(f"[ControlLayer-DEBUG] intent='{intent}', keyword_match={keyword_match}")
        if keyword_match:
            try:
                available_skills = await get_available_skills_async_fn()
                log_info_fn(
                    f"[ControlLayer-DEBUG] available_skills={available_skills[:5] if available_skills else []}"
                )
                cim_decision = process_cim_policy_fn(user_text, available_skills)
                log_info_fn(
                    f"[ControlLayer-DEBUG] cim_decision.matched={cim_decision.matched}, "
                    f"requires_confirmation={cim_decision.requires_confirmation}"
                )

                if cim_decision.matched:
                    log_info_fn(
                        f"[ControlLayer-CIM] Decision: {cim_decision.action.value} for '{cim_decision.skill_name}'"
                    )
                    cim_action = str(getattr(cim_decision.action, "value", cim_decision.action) or "").strip().lower()
                    cim_pattern_id = str(
                        getattr(getattr(cim_decision, "policy_match", None), "pattern_id", "") or ""
                    ).strip().lower()
                    cim_safety_raw = getattr(getattr(cim_decision, "policy_match", None), "safety_level", "")
                    cim_safety_level = str(
                        getattr(cim_safety_raw, "value", cim_safety_raw) or ""
                    ).strip().lower()
                    if (
                        user_text_has_malicious_intent_fn(user_text)
                        or cim_action in {"deny_autonomy", "policy_check"}
                        or cim_pattern_id == "policy_guard"
                        or cim_safety_level == "critical"
                    ):
                        return make_hard_block_verification_fn(
                            reason_code="critical_cim",
                            warnings=[
                                "Dangerous keyword detected: blocked by deterministic policy guard"
                            ],
                            reason="critical_cim",
                        )

                    safe_actions = ["list_skills", "get_skill_info", "list_draft_skills"]
                    if cim_decision.action.value in safe_actions:
                        log_info_fn(f"[ControlLayer-CIM] Safe read-only action: {cim_decision.action.value}")
                        return {
                            "approved": True,
                            "hard_block": False,
                            "decision_class": "allow",
                            "block_reason_code": "",
                            "reason": "cim_safe_action",
                            "corrections": {},
                            "warnings": [],
                            "final_instruction": f"Execute {cim_decision.action.value}",
                            "_cim_decision": {
                                "action": cim_decision.action.value,
                                "skill_name": cim_decision.skill_name,
                            },
                            "suggested_tools": [cim_decision.action.value],
                        }

                    if cim_decision.requires_confirmation:
                        log_info_fn(
                            f"[ControlLayer-CIM] Requires confirmation for skill '{cim_decision.skill_name}'"
                        )
                        return {
                            "approved": True,
                            "hard_block": False,
                            "decision_class": "allow",
                            "block_reason_code": "",
                            "reason": "skill_confirmation_required",
                            "corrections": {},
                            "warnings": [],
                            "final_instruction": "Skill creation requires user confirmation",
                            "_cim_decision": {
                                "action": cim_decision.action.value,
                                "skill_name": cim_decision.skill_name,
                                "pattern_id": (
                                    cim_decision.policy_match.pattern_id if cim_decision.policy_match else None
                                ),
                            },
                            "_needs_skill_confirmation": True,
                            "_skill_name": cim_decision.skill_name,
                        }
            except Exception as exc:
                log_error_fn(f"[ControlLayer-CIM] Error: {exc}")

    if (
        keyword_match
        and not domain_blocks_skill_confirmation
        and is_skill_creation_sensitive_fn(thinking_plan)
    ):
        if user_text_has_malicious_intent_fn(user_text):
            return make_hard_block_verification_fn(
                reason_code="malicious_intent",
                warnings=["Dangerous keyword detected: blocked by deterministic policy guard"],
            )
        matched = bool(cim_decision and getattr(cim_decision, "matched", False))
        requires_confirmation = bool(cim_decision and getattr(cim_decision, "requires_confirmation", False))
        if not (matched and requires_confirmation):
            fallback_name = extract_requested_skill_name_fn(user_text) or "pending_skill_creation"
            log_warning_fn(
                f"[ControlLayer-CIM] Fallback confirmation for skill creation "
                f"(matched={matched}, requires_confirmation={requires_confirmation}, skill={fallback_name})"
            )
            return {
                "approved": True,
                "hard_block": False,
                "decision_class": "allow",
                "block_reason_code": "",
                "reason": "skill_confirmation_required_fallback",
                "corrections": {},
                "warnings": [],
                "final_instruction": "Skill creation requires user confirmation (fallback)",
                "_cim_decision": {
                    "action": "force_create_skill",
                    "skill_name": fallback_name,
                    "pattern_id": "fallback_skill_confirmation",
                },
                "_needs_skill_confirmation": True,
                "_skill_name": fallback_name,
            }

    return None
