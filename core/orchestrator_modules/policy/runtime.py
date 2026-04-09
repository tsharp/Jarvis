from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from core.orchestrator_policy_signal_utils import (
    apply_query_budget_to_plan,
    ensure_dialogue_controls,
    should_force_query_budget_factual_memory,
    should_skip_thinking_from_query_budget,
)
from core.orchestrator_precontrol_policy_utils import (
    resolve_precontrol_policy_conflicts,
)
from core.orchestrator_query_budget_tool_policy_utils import (
    apply_query_budget_tool_policy,
)


async def classify_tone_signal(
    *,
    tone_hybrid: Any,
    user_text: str,
    messages: Optional[List[Any]] = None,
    sanitize_tone_signal_fn: Callable[[Optional[Dict[str, Any]]], Dict[str, Any]],
    log_warn_fn: Callable[[str], None],
) -> Dict[str, Any]:
    try:
        signal = await tone_hybrid.classify(user_text, messages=messages)
        return sanitize_tone_signal_fn(signal)
    except Exception as exc:
        log_warn_fn(f"[Orchestrator] ToneHybrid fallback: {exc}")
        return sanitize_tone_signal_fn(None)


async def classify_query_budget_signal(
    *,
    query_budget: Any,
    user_text: str,
    selected_tools: Optional[List[Any]] = None,
    tone_signal: Optional[Dict[str, Any]] = None,
    query_budget_enabled: bool,
    log_info_fn: Callable[[str], None],
    log_warn_fn: Callable[[str], None],
) -> Dict[str, Any]:
    if not query_budget_enabled:
        return {}
    try:
        signal = await query_budget.classify(
            user_text,
            selected_tools=selected_tools,
            tone_signal=tone_signal,
        )
        if isinstance(signal, dict) and signal:
            log_info_fn(
                "[Orchestrator] query_budget "
                f"type={signal.get('query_type')} "
                f"intent={signal.get('intent_hint')} "
                f"complexity={signal.get('complexity_signal')} "
                f"budget={signal.get('response_budget')} "
                f"tool_hint={signal.get('tool_hint') or '-'} "
                f"skip_candidate={bool(signal.get('skip_thinking_candidate'))} "
                f"conf={signal.get('confidence')} src={signal.get('source')}"
            )
        return signal if isinstance(signal, dict) else {}
    except Exception as exc:
        log_warn_fn(f"[Orchestrator] QueryBudget fallback: {exc}")
        return {}


async def classify_domain_signal(
    *,
    domain_router: Any,
    user_text: str,
    selected_tools: Optional[List[Any]] = None,
    domain_router_enabled: bool,
    maybe_downgrade_cron_create_signal_fn: Callable[[str, Optional[Dict[str, Any]]], Dict[str, Any]],
    log_info_fn: Callable[[str], None],
    log_warn_fn: Callable[[str], None],
) -> Dict[str, Any]:
    if not domain_router_enabled:
        return {}
    try:
        signal = await domain_router.classify(
            user_text,
            selected_tools=selected_tools,
        )
        if isinstance(signal, dict) and signal:
            signal = maybe_downgrade_cron_create_signal_fn(user_text, signal)
            log_info_fn(
                "[Orchestrator] domain_router "
                f"tag={signal.get('domain_tag')} "
                f"locked={bool(signal.get('domain_locked'))} "
                f"operation={signal.get('operation')} "
                f"conf={signal.get('confidence')} src={signal.get('source')}"
            )
            if bool(signal.get("cron_create_downgraded")):
                log_info_fn(
                    "[Orchestrator] domain_router cron create downgraded to status "
                    "(meta/no-schedule guard)"
                )
        return signal if isinstance(signal, dict) else {}
    except Exception as exc:
        log_warn_fn(f"[Orchestrator] DomainRouter fallback: {exc}")
        return {}


def should_skip_thinking_from_query_budget_runtime(
    signal: Optional[Dict[str, Any]],
    *,
    user_text: str,
    forced_mode: str,
    skip_enabled: bool,
    min_confidence: float,
    is_explicit_deep_request_fn: Callable[[str], bool],
    contains_explicit_tool_intent_fn: Callable[[str], bool],
) -> bool:
    return should_skip_thinking_from_query_budget(
        signal,
        user_text=user_text,
        forced_mode=forced_mode,
        skip_enabled=skip_enabled,
        min_confidence=min_confidence,
        is_explicit_deep_request=is_explicit_deep_request_fn,
        contains_explicit_tool_intent=contains_explicit_tool_intent_fn,
    )


def apply_query_budget_to_plan_runtime(
    thinking_plan: Dict[str, Any],
    signal: Optional[Dict[str, Any]],
    *,
    user_text: str,
    query_budget_enabled: bool,
    should_force_query_budget_factual_memory_fn: Callable[[str, Dict[str, Any], Dict[str, Any]], bool],
) -> Dict[str, Any]:
    return apply_query_budget_to_plan(
        thinking_plan,
        signal,
        user_text=user_text,
        query_budget_enabled=query_budget_enabled,
        should_force_factual_memory=should_force_query_budget_factual_memory_fn,
    )


def should_force_query_budget_factual_memory_runtime(
    *,
    user_text: str,
    thinking_plan: Dict[str, Any],
    signal: Dict[str, Any],
    extract_tool_domain_tag_fn: Callable[[str], str],
    has_non_memory_tool_runtime_signal_fn: Callable[[str], bool],
    has_memory_recall_signal_fn: Callable[[str], bool],
) -> bool:
    return should_force_query_budget_factual_memory(
        user_text=user_text,
        thinking_plan=thinking_plan,
        signal=signal,
        tool_domain_tag=extract_tool_domain_tag_fn(user_text),
        has_non_memory_tool_runtime_signal_fn=has_non_memory_tool_runtime_signal_fn,
        has_memory_recall_signal_fn=has_memory_recall_signal_fn,
    )


def resolve_precontrol_policy_conflicts_runtime(
    user_text: str,
    thinking_plan: Dict[str, Any],
    *,
    resolver_enabled: bool,
    rollout_enabled: bool,
    has_memory_recall_signal_fn: Callable[[str], bool],
    contains_explicit_tool_intent_fn: Callable[[str], bool],
    looks_like_host_runtime_lookup_fn: Callable[[str], bool],
    has_non_memory_tool_runtime_signal_fn: Callable[[str], bool],
    extract_tool_name_fn: Callable[[Any], str],
    log_info_fn: Callable[[str], None],
) -> Dict[str, Any]:
    out, meta = resolve_precontrol_policy_conflicts(
        user_text,
        thinking_plan,
        resolver_enabled=resolver_enabled,
        rollout_enabled=rollout_enabled,
        has_memory_recall_signal_fn=has_memory_recall_signal_fn,
        contains_explicit_tool_intent_fn=contains_explicit_tool_intent_fn,
        looks_like_host_runtime_lookup_fn=looks_like_host_runtime_lookup_fn,
        has_non_memory_tool_runtime_signal_fn=has_non_memory_tool_runtime_signal_fn,
        extract_tool_name_fn=extract_tool_name_fn,
    )
    if bool(meta.get("resolved")):
        log_info_fn(
            "[Orchestrator] Policy conflict resolved: "
            f"domain={meta.get('domain_tag') or '-'} reason={meta.get('reason') or '-'}"
        )
    return out


def apply_query_budget_tool_policy_runtime(
    user_text: str,
    verified_plan: Dict[str, Any],
    suggested_tools: List[Any],
    *,
    query_budget_enabled: bool,
    max_tools_factual_low: int,
    heavy_tools: List[str],
    contains_explicit_tool_intent_fn: Callable[[str], bool],
    is_explicit_deep_request_fn: Callable[[str], bool],
    is_explicit_think_request_fn: Callable[[str], bool],
    extract_tool_name_fn: Callable[[Any], str],
    prefix: str,
    log_info_fn: Callable[[str], None],
) -> List[Any]:
    filtered, policy = apply_query_budget_tool_policy(
        user_text,
        verified_plan,
        suggested_tools,
        query_budget_enabled=query_budget_enabled,
        max_tools_factual_low=max_tools_factual_low,
        heavy_tools=heavy_tools,
        contains_explicit_tool_intent_fn=contains_explicit_tool_intent_fn,
        is_explicit_deep_request_fn=is_explicit_deep_request_fn,
        is_explicit_think_request_fn=is_explicit_think_request_fn,
        extract_tool_name_fn=extract_tool_name_fn,
    )
    if isinstance(policy, dict):
        verified_plan["_query_budget_policy"] = dict(policy)
        query_type = str(policy.get("query_type") or "")
        complexity = str(policy.get("complexity_signal") or "")
        confidence = float(policy.get("confidence", 0.0) or 0.0)
        dropped = int(policy.get("dropped", 0) or 0)
        reasons = list(policy.get("reasons") or [])
        log_info_fn(
            f"{prefix} QueryBudget policy applied: "
            f"type={query_type} complexity={complexity} conf={confidence:.2f} "
            f"dropped={dropped} reasons={reasons}"
        )
    return filtered


def ensure_dialogue_controls_runtime(
    thinking_plan: Dict[str, Any],
    tone_signal: Optional[Dict[str, Any]],
    *,
    override_threshold: float,
    user_text: str,
    selected_tools: Optional[List[Any]],
    contains_explicit_tool_intent_fn: Callable[[str], bool],
    has_non_memory_tool_runtime_signal_fn: Callable[[str], bool],
) -> Dict[str, Any]:
    return ensure_dialogue_controls(
        thinking_plan,
        tone_signal,
        override_threshold=override_threshold,
        user_text=user_text,
        selected_tools=selected_tools,
        contains_explicit_tool_intent_fn=contains_explicit_tool_intent_fn,
        has_non_memory_tool_runtime_signal_fn=has_non_memory_tool_runtime_signal_fn,
    )
