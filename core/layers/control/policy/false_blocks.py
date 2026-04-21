"""False-block recovery helpers for ControlLayer policy flows."""

from __future__ import annotations

import re
from typing import Any


def looks_like_capability_mismatch_for_policy(
    verification: dict[str, Any],
    *,
    looks_like_capability_mismatch_fn,
) -> bool:
    """Delegate capability-mismatch detection through the policy module."""
    return bool(looks_like_capability_mismatch_fn(verification))


def is_cron_tool_name_for_policy(
    tool_name: str,
    *,
    is_cron_tool_name_fn,
) -> bool:
    """Delegate cron-tool classification through the policy module."""
    return bool(is_cron_tool_name_fn(tool_name))


def looks_like_spurious_policy_block_for_policy(
    verification: dict[str, Any],
    *,
    looks_like_spurious_policy_block_fn,
) -> bool:
    """Delegate spurious-policy-block detection through the policy module."""
    return bool(looks_like_spurious_policy_block_fn(verification))


def has_cron_context(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    tool_names_fn,
    is_cron_tool_name_fn,
) -> bool:
    """Detect whether the current plan is clearly in the cron domain."""
    route = (thinking_plan or {}).get("_domain_route", {}) if isinstance(thinking_plan, dict) else {}
    domain_tag = str((route or {}).get("domain_tag") or "").strip().upper()
    if domain_tag == "CRONJOB":
        return True

    suggested_plan = tool_names_fn((thinking_plan or {}).get("suggested_tools", []), limit=12)
    suggested_verify = tool_names_fn((verification or {}).get("suggested_tools", []), limit=12)
    combined = suggested_plan + [name for name in suggested_verify if name not in suggested_plan]
    if any(is_cron_tool_name_fn(name) for name in combined):
        return True

    intent = str((thinking_plan or {}).get("intent") or "").strip().lower()
    return any(token in intent for token in ("cron", "cronjob", "schedule", "zeitplan"))


def should_lift_cron_false_block(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    has_hard_safety_markers_fn,
    has_cron_context_fn,
    looks_like_capability_mismatch_fn,
    looks_like_spurious_policy_block_fn,
) -> bool:
    """Lift spurious cron-domain false blocks when deterministic signals allow it."""
    if has_hard_safety_markers_fn(verification):
        return False
    if not has_cron_context_fn(verification, thinking_plan):
        return False

    route = (thinking_plan or {}).get("_domain_route", {}) if isinstance(thinking_plan, dict) else {}
    domain_tag = str((route or {}).get("domain_tag") or "").strip().upper()
    domain_locked = bool((route or {}).get("domain_locked"))
    if domain_locked and domain_tag == "CRONJOB":
        return True

    return (
        looks_like_capability_mismatch_fn(verification)
        or looks_like_spurious_policy_block_fn(verification)
    )


def has_container_context(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    tool_names_fn,
) -> bool:
    """Detect whether the current plan is clearly in the container domain."""
    route = (thinking_plan or {}).get("_domain_route", {}) if isinstance(thinking_plan, dict) else {}
    domain_tag = str((route or {}).get("domain_tag") or "").strip().upper()
    if domain_tag == "CONTAINER":
        return True

    suggested_plan = tool_names_fn((thinking_plan or {}).get("suggested_tools", []), limit=12)
    suggested_verify = tool_names_fn((verification or {}).get("suggested_tools", []), limit=12)
    combined = suggested_plan + [name for name in suggested_verify if name not in suggested_plan]
    container_tools = {
        "request_container",
        "stop_container",
        "exec_in_container",
        "container_logs",
        "container_stats",
        "container_list",
        "container_inspect",
        "blueprint_list",
        "blueprint_get",
        "blueprint_create",
    }
    if any(str(name or "").strip().lower() in container_tools for name in combined):
        return True

    intent = str((thinking_plan or {}).get("intent") or "").strip().lower()
    return any(token in intent for token in ("container", "docker", "blueprint", "host server", "ip"))


def should_lift_container_false_block(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    has_hard_safety_markers_fn,
    has_container_context_fn,
    verification_text_fn,
    looks_like_capability_mismatch_fn,
    looks_like_spurious_policy_block_fn,
) -> bool:
    """Lift spurious container-domain false blocks when deterministic signals allow it."""
    if has_hard_safety_markers_fn(verification):
        return False
    if not has_container_context_fn(verification, thinking_plan):
        return False

    route = (thinking_plan or {}).get("_domain_route", {}) if isinstance(thinking_plan, dict) else {}
    domain_tag = str((route or {}).get("domain_tag") or "").strip().upper()
    domain_locked = bool((route or {}).get("domain_locked"))
    if domain_locked and domain_tag == "CONTAINER":
        return True

    text = verification_text_fn(verification)
    if "needs memory but no keys specified" in text:
        return True
    return (
        looks_like_capability_mismatch_fn(verification)
        or looks_like_spurious_policy_block_fn(verification)
    )


def combined_suggested_tools(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    tool_names_fn,
    limit: int = 16,
) -> list[str]:
    """Merge suggested tools from plan and verification while preserving order."""
    from_plan = tool_names_fn((thinking_plan or {}).get("suggested_tools", []), limit=limit)
    from_verify = tool_names_fn((verification or {}).get("suggested_tools", []), limit=limit)
    combined: list[str] = list(from_plan)
    for name in from_verify:
        if name not in combined:
            combined.append(name)
        if len(combined) >= limit:
            break
    return combined


def is_runtime_operation_tool_for_policy(
    tool_name: str,
    *,
    is_runtime_operation_tool_fn,
) -> bool:
    """Delegate runtime-operation classification through the policy module."""
    return bool(is_runtime_operation_tool_fn(tool_name))


def has_solution_oriented_action_signal(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    user_text: str = "",
    combined_suggested_tools_fn,
    is_runtime_operation_tool_fn,
) -> bool:
    """Detect whether a benign runtime/action path exists for the current turn."""
    route = (thinking_plan or {}).get("_domain_route", {}) if isinstance(thinking_plan, dict) else {}
    domain_tag = str((route or {}).get("domain_tag") or "").strip().upper()
    domain_locked = bool((route or {}).get("domain_locked"))
    if domain_locked and domain_tag in {"CONTAINER", "CRONJOB", "SKILL"}:
        return True

    combined_tools = combined_suggested_tools_fn(verification, thinking_plan)
    if any(is_runtime_operation_tool_fn(name) for name in combined_tools):
        return True

    merged_text = " ".join(
        part
        for part in (
            str((thinking_plan or {}).get("intent") or "").strip(),
            str(user_text or "").strip(),
        )
        if part
    ).lower()
    if not merged_text:
        return False
    has_domain = bool(
        re.search(
            r"\b(container|docker|blueprint|cron|cronjob|schedule|zeitplan|skill|server|host|ip|runtime|tool|mcp)\b",
            merged_text,
        )
    )
    has_action = bool(
        re.search(
            r"\b(create|erstell\w*|start\w*|run\b|führe?\w*|fuehr\w*|execute|deploy|stop\w*|delete\w*|lösch\w*|loesch\w*|check\w*|prüf\w*|pruef\w*|find\w*|ermittel\w*|list\w*|status|logs?|inspect|update|pause|resume)\b",
            merged_text,
        )
    )
    return has_domain and has_action


def should_lift_solution_oriented_false_block(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    user_text: str = "",
    has_hard_safety_markers_fn,
    user_text_has_hard_safety_keywords_fn,
    user_text_has_malicious_intent_fn,
    verification_text_fn,
    looks_like_capability_mismatch_fn,
    looks_like_spurious_policy_block_fn,
    has_solution_oriented_action_signal_fn,
    combined_suggested_tools_fn,
    is_tool_available_fn,
) -> bool:
    """Lift spurious runtime/path blocks when a benign action path exists."""
    if has_hard_safety_markers_fn(verification):
        return False
    if user_text_has_hard_safety_keywords_fn(user_text):
        return False
    if user_text_has_malicious_intent_fn(user_text):
        return False

    text = verification_text_fn(verification)
    has_spurious_signal = (
        looks_like_capability_mismatch_fn(verification)
        or looks_like_spurious_policy_block_fn(verification)
        or "needs memory but no keys specified" in text
    )
    if not has_spurious_signal:
        return False
    if not has_solution_oriented_action_signal_fn(
        verification,
        thinking_plan,
        user_text=user_text,
    ):
        return False

    route = (thinking_plan or {}).get("_domain_route", {}) if isinstance(thinking_plan, dict) else {}
    domain_tag = str((route or {}).get("domain_tag") or "").strip().upper()
    domain_locked = bool((route or {}).get("domain_locked"))
    if domain_locked and domain_tag in {"CONTAINER", "CRONJOB", "SKILL"}:
        return True

    combined_tools = combined_suggested_tools_fn(verification, thinking_plan)
    if not combined_tools:
        return False
    available = [name for name in combined_tools if is_tool_available_fn(name)]
    return bool(available)


def should_lift_query_budget_fast_path_false_block(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    user_text: str = "",
    has_hard_safety_markers_fn,
    user_text_has_hard_safety_keywords_fn,
    verification_text_fn,
    looks_like_spurious_policy_block_fn,
    has_cron_context_fn,
    user_text_has_malicious_intent_fn,
) -> bool:
    """Lift benign query-budget fast-path false blocks when safe deterministic signals allow it."""
    if has_hard_safety_markers_fn(verification):
        return False
    if user_text_has_hard_safety_keywords_fn(user_text):
        return False
    text = verification_text_fn(verification)
    benign_false_block_markers = (
        "keine notwendigkeit für tool",
        "keine notwendigkeit fuer tool",
        "direkte berechnung möglich",
        "direkte berechnung moeglich",
        "irrelevant für",
        "irrelevant fuer",
        "falsche intent-klassifizierung",
        "rechnerische_operation",
        "container-hinweis irrelevant",
        "container hinweis irrelevant",
        "no tool required",
        "direct calculation",
    )
    looks_like_spurious_block = looks_like_spurious_policy_block_fn(verification) or any(
        marker in text for marker in benign_false_block_markers
    )

    intent = str((thinking_plan or {}).get("intent") or "").strip().lower()
    query_budget_signal = (
        (thinking_plan or {}).get("_query_budget", {})
        if isinstance(thinking_plan, dict)
        else {}
    )
    query_budget_skip_candidate = bool(
        isinstance(query_budget_signal, dict)
        and query_budget_signal.get("skip_thinking_candidate")
    )
    if intent != "query_budget_fast_path" and not query_budget_skip_candidate:
        return False

    if has_cron_context_fn(verification, thinking_plan):
        return False
    user_low = str(user_text or "").strip().lower()
    has_domain_or_tool_markers = bool(
        re.search(
            r"\b(cron|cronjob|schedule|zeitplan|container|blueprint|docker|skill|run_skill|create_skill|autonomous_skill_task|mcp)\b",
            user_low,
        )
    )
    has_execution_markers = bool(
        re.search(
            r"\b(erstell\w*|create|starte?\b|start\b|fuehr\w*|führe?\w*|execute|deploy|run\b|lösch\w*|loesch\w*|delete)\b",
            user_low,
        )
    )
    if has_domain_or_tool_markers or has_execution_markers:
        return False
    if user_text_has_malicious_intent_fn(user_text):
        return False
    if len(user_low) < 3:
        return False
    if not looks_like_spurious_block:
        return True
    if re.search(r"\b\d+\s*(?:[\+\-\*/]|x|×)\s*\d+\b", str(user_text or "").lower()):
        return True
    return True
