from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from core.control_contract import ControlDecision
from core.host_runtime_policy import enforce_host_runtime_exec_first


async def collect_control_tool_decisions(
    *,
    control: Any,
    user_text: str,
    verified_plan: Dict[str, Any],
    build_tool_args_fn: Callable[[str, str, Optional[Dict[str, Any]]], Dict[str, Any]],
    tool_allowed_by_control_decision_fn: Callable[[Optional[ControlDecision], str], bool],
    control_decision: Optional[ControlDecision] = None,
    stream: bool = False,
    log_info_fn: Callable[[str], None],
    log_warn_fn: Callable[[str], None],
    log_error_fn: Callable[[str], None],
) -> Dict[str, Dict[str, Any]]:
    prefix = "[Orchestrator-Stream]" if stream else "[Orchestrator]"
    decisions: Dict[str, Dict[str, Any]] = {}

    gate_override = verified_plan.get("_gate_tools_override")
    if gate_override:
        log_info_fn(f"{prefix} Gate override active — skipping decide_tools(): {gate_override}")
        for tool_name in gate_override:
            if not tool_allowed_by_control_decision_fn(control_decision, tool_name):
                log_warn_fn(f"{prefix} Gate override tool blocked by control_decision: {tool_name}")
                continue
            decisions[tool_name] = build_tool_args_fn(tool_name, user_text, verified_plan)
        return decisions

    try:
        raw_decisions = await control.decide_tools(user_text, verified_plan)
        for item in raw_decisions or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            if not tool_allowed_by_control_decision_fn(control_decision, name):
                log_warn_fn(f"{prefix} decide_tools emitted non-allowed tool; dropped: {name}")
                continue
            args = item.get("arguments", {})
            decisions[name] = args if isinstance(args, dict) else {}
        if decisions:
            log_info_fn(f"{prefix} ControlLayer tool args: {list(decisions.keys())}")
    except Exception as exc:
        log_error_fn(f"{prefix} decide_tools error: {exc}")

    return decisions


def resolve_execution_suggested_tools(
    *,
    user_text: str,
    verified_plan: Dict[str, Any],
    control_tool_decisions: Optional[Dict[str, Dict[str, Any]]],
    tool_execution_policy: Optional[Dict[str, Any]],
    low_signal_action_tools: List[str],
    control_decision: Optional[ControlDecision] = None,
    stream: bool = False,
    enable_skill_trigger_router: bool = False,
    conversation_id: str = "",
    chat_history: Optional[list] = None,
    finalize_execution_suggested_tools_fn: Callable[[Dict[str, Any], List[Any]], List[Any]],
    should_suppress_conversational_tools_fn: Callable[[str, Dict[str, Any]], bool],
    looks_like_short_confirmation_followup_fn: Callable[[str, Optional[list]], bool],
    resolve_followup_tool_reuse_fn: Callable[..., List[Any]],
    normalize_tools_fn: Callable[[List[Any]], List[Any]],
    extract_tool_name_fn: Callable[[Any], str],
    get_effective_resolution_strategy_fn: Callable[[Optional[Dict[str, Any]]], str],
    prioritize_home_container_tools_fn: Callable[..., List[Any]],
    rewrite_home_start_request_tools_fn: Callable[..., List[Any]],
    prioritize_active_container_capability_tools_fn: Callable[..., List[Any]],
    apply_container_query_policy_fn: Callable[..., List[Any]],
    apply_query_budget_tool_policy_fn: Callable[..., List[Any]],
    apply_domain_tool_policy_fn: Callable[..., List[Any]],
    detect_tools_by_keyword_fn: Callable[[str], List[Any]],
    contains_explicit_skill_intent_fn: Callable[[str], bool],
    detect_skill_by_trigger_fn: Callable[[str], List[Any]],
    looks_like_host_runtime_lookup_fn: Callable[[str], bool],
    tool_allowed_by_control_decision_fn: Callable[[Optional[ControlDecision], str], bool],
    log_info_fn: Callable[[str], None],
) -> List[Any]:
    prefix = "[Orchestrator-Stream]" if stream else "[Orchestrator]"
    decisions = control_tool_decisions or {}
    has_control_decisions = bool(decisions)
    authoritative_suggested_tools = list(
        verified_plan.get("_authoritative_suggested_tools") or []
    )
    control_allowed_tools = list(
        control_decision.tools_allowed
        if isinstance(control_decision, ControlDecision) and control_decision.tools_allowed
        else []
    )
    has_control_authority = bool(
        has_control_decisions or authoritative_suggested_tools or control_allowed_tools
    )
    if isinstance(control_decision, ControlDecision) and not control_decision.approved:
        log_info_fn(f"{prefix} Tool execution suppressed (control_decision.approved=false)")
        return finalize_execution_suggested_tools_fn(verified_plan, [])
    suppress_low_signal_tools = should_suppress_conversational_tools_fn(user_text, verified_plan)

    if decisions:
        suggested_tools: List[Any] = list(decisions.keys())
        log_info_fn(f"{prefix} ControlLayer tools (authoritative): {suggested_tools}")
    elif authoritative_suggested_tools:
        suggested_tools = list(authoritative_suggested_tools)
        log_info_fn(f"{prefix} Authoritative control suggested_tools: {suggested_tools}")
    elif control_allowed_tools:
        suggested_tools = list(control_allowed_tools)
        log_info_fn(f"{prefix} ControlLayer tools_allowed fallback: {suggested_tools}")
    else:
        suggested_tools = verified_plan.get("suggested_tools", [])
        if suggested_tools:
            log_info_fn(f"{prefix} Fallback: ThinkingLayer suggested_tools: {suggested_tools}")

        if looks_like_short_confirmation_followup_fn(user_text, chat_history):
            followup_tools = resolve_followup_tool_reuse_fn(
                user_text,
                verified_plan,
                conversation_id=conversation_id,
                chat_history=chat_history,
            )
            if followup_tools:
                suggested_tools = normalize_tools_fn(followup_tools)
                if isinstance(control_decision, ControlDecision):
                    suggested_tools = [
                        tool
                        for tool in suggested_tools
                        if tool_allowed_by_control_decision_fn(control_decision, extract_tool_name_fn(tool))
                    ]
                log_info_fn(f"{prefix} Confirmation follow-up reuse: {suggested_tools}")
                verified_plan["needs_chat_history"] = True
                return finalize_execution_suggested_tools_fn(verified_plan, suggested_tools)

    suggested_tools = normalize_tools_fn(suggested_tools)
    if isinstance(control_decision, ControlDecision):
        suggested_tools = [
            tool
            for tool in suggested_tools
            if tool_allowed_by_control_decision_fn(control_decision, extract_tool_name_fn(tool))
        ]
    resolution_strategy = get_effective_resolution_strategy_fn(verified_plan)
    if resolution_strategy:
        log_info_fn(f"{prefix} Effective resolution_strategy={resolution_strategy}")
    suggested_tools = prioritize_home_container_tools_fn(
        user_text,
        verified_plan,
        suggested_tools,
        prefix=prefix,
    )
    suggested_tools = rewrite_home_start_request_tools_fn(
        user_text,
        verified_plan,
        suggested_tools,
        prefix=prefix,
    )
    suggested_tools = prioritize_active_container_capability_tools_fn(
        user_text,
        verified_plan,
        suggested_tools,
        conversation_id=conversation_id,
        force=resolution_strategy == "active_container_capability",
        prefix=prefix,
    )
    suggested_tools = apply_container_query_policy_fn(
        user_text,
        verified_plan,
        suggested_tools,
        conversation_id=conversation_id,
        prefix=prefix,
    )
    if has_control_authority:
        log_info_fn(f"{prefix} Post-control tool policies bypassed (Control authority)")
    else:
        suggested_tools = apply_query_budget_tool_policy_fn(
            user_text,
            verified_plan,
            suggested_tools,
            prefix=prefix,
        )
        suggested_tools = apply_domain_tool_policy_fn(
            verified_plan,
            suggested_tools,
            user_text=user_text,
            prefix=prefix,
        )

    if suppress_low_signal_tools and suggested_tools and not has_control_authority:
        policy = tool_execution_policy or {}
        conv_cfg = policy.get("conversational_guard", {}) if isinstance(policy, dict) else {}
        suppressed_exec_tools = {
            str(name).strip().lower()
            for name in conv_cfg.get("suppress_tools", [])
            if str(name).strip()
        }
        suppressed_tools = {
            str(name).strip().lower() for name in low_signal_action_tools
        }.union(suppressed_exec_tools)
        before = len(suggested_tools)
        suggested_tools = [
            tool
            for tool in suggested_tools
            if extract_tool_name_fn(tool).lower() not in suppressed_tools
        ]
        dropped = before - len(suggested_tools)
        if dropped:
            log_info_fn(f"{prefix} Suppressed conversational tools for turn: dropped={dropped}")
    elif suppress_low_signal_tools and suggested_tools and has_control_authority:
        log_info_fn(f"{prefix} Conversational suppress bypassed (Control authority)")

    if not suggested_tools:
        followup_tools = resolve_followup_tool_reuse_fn(
            user_text,
            verified_plan,
            conversation_id=conversation_id,
            chat_history=chat_history,
        )
        if followup_tools:
            suggested_tools = normalize_tools_fn(followup_tools)
            if isinstance(control_decision, ControlDecision):
                suggested_tools = [
                    tool
                    for tool in suggested_tools
                    if tool_allowed_by_control_decision_fn(control_decision, extract_tool_name_fn(tool))
                ]
            log_info_fn(f"{prefix} Follow-up tool reuse: {suggested_tools}")
            verified_plan["needs_chat_history"] = True
            return finalize_execution_suggested_tools_fn(verified_plan, suggested_tools)
        if suppress_low_signal_tools:
            log_info_fn(f"{prefix} Tool fallback suppressed for conversational turn")
            return finalize_execution_suggested_tools_fn(verified_plan, [])
        suggested_tools = detect_tools_by_keyword_fn(user_text)
        if suggested_tools:
            suggested_tools = normalize_tools_fn(suggested_tools)
            if isinstance(control_decision, ControlDecision):
                suggested_tools = [
                    tool
                    for tool in suggested_tools
                    if tool_allowed_by_control_decision_fn(control_decision, extract_tool_name_fn(tool))
                ]
            log_info_fn(f"{prefix} Last-resort keyword fallback: {suggested_tools}")

    if enable_skill_trigger_router and not suggested_tools:
        if contains_explicit_skill_intent_fn(user_text):
            trigger_matches = detect_skill_by_trigger_fn(user_text)
            if trigger_matches:
                suggested_tools = normalize_tools_fn(trigger_matches)
                if isinstance(control_decision, ControlDecision):
                    suggested_tools = [
                        tool
                        for tool in suggested_tools
                        if tool_allowed_by_control_decision_fn(control_decision, extract_tool_name_fn(tool))
                    ]
                log_info_fn(f"[Orchestrator] Skill Trigger Router: {trigger_matches}")
        else:
            log_info_fn("[Orchestrator] Skill Trigger Router skipped (no explicit skill intent)")

    if not has_control_authority:
        suggested_tools = apply_domain_tool_policy_fn(
            verified_plan,
            suggested_tools,
            user_text=user_text,
            prefix=prefix,
        )

    host_runtime_requested = looks_like_host_runtime_lookup_fn(user_text)
    if not has_control_authority:
        host_tools = enforce_host_runtime_exec_first(
            user_text=user_text,
            suggested_tools=suggested_tools,
            looks_like_host_runtime_lookup_fn=looks_like_host_runtime_lookup_fn,
            extract_tool_name_fn=extract_tool_name_fn,
        )
        if host_runtime_requested:
            verified_plan["_host_runtime_chain_applied"] = True
        if host_tools != list(suggested_tools or []):
            log_info_fn(
                f"{prefix} Host-runtime deterministic chain applied: "
                f"{[extract_tool_name_fn(tool) for tool in host_tools]}"
            )
            suggested_tools = host_tools

    return finalize_execution_suggested_tools_fn(verified_plan, suggested_tools)
