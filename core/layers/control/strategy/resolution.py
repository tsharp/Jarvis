"""Resolution-strategy helpers for ControlLayer."""

from __future__ import annotations

from typing import Any


def normalize_resolution_strategy(value: Any) -> str:
    """Normalize a resolution strategy to the supported control values."""
    strategy = str(value or "").strip().lower()
    if strategy in {
        "container_inventory",
        "container_blueprint_catalog",
        "container_state_binding",
        "container_request",
        "active_container_capability",
        "home_container_info",
        "skill_catalog_context",
    }:
        return strategy
    return ""


def apply_resolution_strategy_authority(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    user_text: str = "",
    has_hard_safety_markers_fn,
    user_text_has_hard_safety_keywords_fn,
    user_text_has_malicious_intent_fn,
    normalize_resolution_strategy_fn,
    warning_list_fn,
    tool_names_fn,
) -> dict[str, Any]:
    """Promote a validated resolution strategy to authoritative control state."""
    if not isinstance(verification, dict) or not isinstance(thinking_plan, dict):
        return verification
    if verification.get("approved") is False:
        return verification
    if has_hard_safety_markers_fn(verification):
        return verification
    if user_text_has_hard_safety_keywords_fn(user_text):
        return verification
    if user_text_has_malicious_intent_fn(user_text):
        return verification

    corrections = verification.get("corrections", {})
    if not isinstance(corrections, dict):
        corrections = {}

    requested = normalize_resolution_strategy_fn(
        corrections.get("resolution_strategy") or thinking_plan.get("resolution_strategy")
    )
    if not requested:
        return verification

    authoritative = requested
    route = thinking_plan.get("_domain_route", {}) if isinstance(thinking_plan, dict) else {}
    domain_tag = str((route or {}).get("domain_tag") or "").strip().upper()
    if requested in {
        "container_inventory",
        "container_blueprint_catalog",
        "container_state_binding",
        "container_request",
        "active_container_capability",
    } and domain_tag not in {"", "CONTAINER"}:
        authoritative = ""
    if requested == "skill_catalog_context" and domain_tag not in {"", "SKILL"}:
        authoritative = ""

    if not authoritative:
        return verification

    corrections["resolution_strategy"] = authoritative
    corrections["_authoritative_resolution_strategy"] = authoritative
    verification["corrections"] = corrections
    verification["_authoritative_resolution_strategy"] = authoritative
    warnings = warning_list_fn(verification.get("warnings", []))
    suggested = tool_names_fn((thinking_plan or {}).get("suggested_tools", []), limit=12)
    if requested == "container_inventory":
        inventory_mixing_tools = {
            "blueprint_list",
            "request_container",
            "container_inspect",
        }
        if any(name in inventory_mixing_tools for name in suggested):
            warnings.append(
                "Control validated container_inventory as the authoritative resolution strategy; blueprint, request, and capability tools stay advisory."
            )
    if requested == "container_blueprint_catalog":
        catalog_mixing_tools = {
            "container_list",
            "container_inspect",
            "request_container",
        }
        if any(name in catalog_mixing_tools for name in suggested):
            warnings.append(
                "Control validated container_blueprint_catalog as the authoritative resolution strategy; runtime inventory and deploy intent stay advisory."
            )
    if requested == "container_state_binding":
        state_mixing_tools = {
            "blueprint_list",
            "request_container",
        }
        if any(name in state_mixing_tools for name in suggested):
            warnings.append(
                "Control validated container_state_binding as the authoritative resolution strategy; static catalog and deploy intent stay advisory."
            )
    if requested == "container_request":
        request_mixing_tools = {
            "blueprint_list",
            "container_list",
            "container_inspect",
        }
        if any(name in request_mixing_tools for name in suggested):
            warnings.append(
                "Control validated container_request as the authoritative resolution strategy; inventory and catalog evidence stay secondary."
            )
    if requested == "active_container_capability":
        generic_runtime = {
            "exec_in_container",
            "container_stats",
            "container_list",
            "query_skill_knowledge",
        }
        if any(name in generic_runtime for name in suggested):
            warnings.append(
                "Control validated active_container_capability as the authoritative resolution strategy; generic runtime probes stay advisory."
            )
    if requested == "skill_catalog_context":
        skill_inventory_tools = {
            "list_skills",
            "get_skill_info",
        }
        if any(name in skill_inventory_tools for name in suggested):
            warnings.append(
                "Control validated skill_catalog_context as the authoritative resolution strategy; runtime skill inventory stays evidence, not the full semantic category model."
            )
    verification["warnings"] = warnings
    if not verification.get("final_instruction"):
        verification["final_instruction"] = (
            f"Use the validated resolution strategy '{authoritative}' before generic tool fallbacks."
        )
    return verification
