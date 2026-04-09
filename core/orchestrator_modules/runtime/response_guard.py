from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional


def get_recent_consistency_entries(
    *,
    consistency_state: Dict[str, List[Dict[str, Any]]],
    consistency_lock: Any,
    conversation_id: str,
    load_policy_fn: Callable[[], Dict[str, Any]],
    prune_entries_fn: Callable[..., List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    conv_id = str(conversation_id or "").strip()
    if not conv_id:
        return []
    policy = load_policy_fn()
    ttl_s = int(policy.get("history_ttl_s", 3600) or 3600)
    max_entries = int(policy.get("max_entries_per_conversation", 24) or 24)
    with consistency_lock:
        existing = consistency_state.get(conv_id, [])
        pruned = prune_entries_fn(
            existing,
            now_ts=time.time(),
            ttl_s=ttl_s,
            max_entries=max_entries,
        )
        if pruned:
            consistency_state[conv_id] = pruned
        else:
            consistency_state.pop(conv_id, None)
        return [dict(x) for x in pruned]


def remember_consistency_entries(
    *,
    consistency_state: Dict[str, List[Dict[str, Any]]],
    consistency_lock: Any,
    conversation_id: str,
    entries: List[Dict[str, Any]],
    load_policy_fn: Callable[[], Dict[str, Any]],
    prune_entries_fn: Callable[..., List[Dict[str, Any]]],
) -> None:
    conv_id = str(conversation_id or "").strip()
    if not conv_id or not entries:
        return
    policy = load_policy_fn()
    ttl_s = int(policy.get("history_ttl_s", 3600) or 3600)
    max_entries = int(policy.get("max_entries_per_conversation", 24) or 24)
    with consistency_lock:
        merged = list(consistency_state.get(conv_id, [])) + list(entries)
        consistency_state[conv_id] = prune_entries_fn(
            merged,
            now_ts=time.time(),
            ttl_s=ttl_s,
            max_entries=max_entries,
        )


async def apply_conversation_consistency_guard(
    *,
    conversation_id: str,
    verified_plan: Dict[str, Any],
    answer: str,
    load_policy_fn: Callable[[], Dict[str, Any]],
    extract_stance_signals_fn: Callable[[str], List[Dict[str, str]]],
    get_recent_consistency_entries_fn: Callable[[str], List[Dict[str, Any]]],
    embed_text_fn: Callable[..., Any],
    detect_conflicts_fn: Callable[..., List[Dict[str, Any]]],
    make_stance_entries_fn: Callable[..., List[Dict[str, Any]]],
    remember_consistency_entries_fn: Callable[[str, List[Dict[str, Any]]], None],
    get_runtime_grounding_value_fn: Callable[..., Any],
    get_runtime_grounding_evidence_fn: Callable[[Dict[str, Any]], Any],
    build_grounding_fallback_fn: Callable[[List[Dict[str, Any]], str], Any],
    log_warn_fn: Callable[[str], None],
) -> str:
    policy = load_policy_fn()
    if not bool(policy.get("enabled", True)):
        return answer
    answer_text = str(answer or "")
    if not answer_text.strip():
        return answer_text

    current_signals = extract_stance_signals_fn(answer_text)
    if not current_signals:
        return answer_text

    prior_entries = get_recent_consistency_entries_fn(conversation_id)
    current_embedding: Optional[List[float]] = None
    if bool(policy.get("embedding_enable", True)):
        try:
            current_embedding = await embed_text_fn(answer_text, timeout_s=2.4)
        except Exception:
            current_embedding = None

    conflicts = detect_conflicts_fn(
        prior_entries=prior_entries,
        current_signals=current_signals,
        current_embedding=current_embedding,
        similarity_threshold=float(policy.get("embedding_similarity_threshold", 0.78) or 0.78),
    )
    if not conflicts:
        remember_consistency_entries_fn(
            conversation_id,
            make_stance_entries_fn(
                signals=current_signals,
                embedding=current_embedding,
                now_ts=time.time(),
            ),
        )
        return answer_text

    evidence_count = int(
        get_runtime_grounding_value_fn(
            verified_plan,
            key="successful_evidence",
            default=0,
        )
        or 0
    )
    min_evidence = int(policy.get("min_successful_evidence_on_stance_change", 1) or 1)
    requires_evidence = bool(policy.get("require_evidence_on_stance_change", True))
    if requires_evidence and evidence_count < min_evidence:
        evidence = get_runtime_grounding_evidence_fn(verified_plan)
        fallback_mode = str(policy.get("fallback_mode", "explicit_uncertainty") or "explicit_uncertainty")
        fallback = build_grounding_fallback_fn(
            evidence if isinstance(evidence, list) else [],
            fallback_mode,
        )
        repaired = str(fallback or "").strip()
        if repaired:
            verified_plan["_consistency_conflict_detected"] = True
            verified_plan["_consistency_conflicts"] = conflicts[:4]
            verified_plan["_grounding_violation_detected"] = True
            verified_plan["_grounded_fallback_used"] = True
            log_warn_fn(
                "[Orchestrator] Consistency guard fallback: "
                f"conflicts={len(conflicts)} evidence={evidence_count}<{min_evidence}"
            )
            repaired_signals = extract_stance_signals_fn(repaired)
            repaired_embedding: Optional[List[float]] = None
            if bool(policy.get("embedding_enable", True)):
                try:
                    repaired_embedding = await embed_text_fn(repaired, timeout_s=2.4)
                except Exception:
                    repaired_embedding = None
            remember_consistency_entries_fn(
                conversation_id,
                make_stance_entries_fn(
                    signals=repaired_signals,
                    embedding=repaired_embedding,
                    now_ts=time.time(),
                ),
            )
            return repaired

    remember_consistency_entries_fn(
        conversation_id,
        make_stance_entries_fn(
            signals=current_signals,
            embedding=current_embedding,
            now_ts=time.time(),
        ),
    )
    return answer_text


async def maybe_auto_recover_grounding_once(
    *,
    conversation_id: str,
    user_text: str,
    verified_plan: Dict[str, Any],
    thinking_plan: Dict[str, Any],
    history_len: int,
    session_id: str,
    get_grounding_auto_recovery_enable_fn: Callable[[], bool],
    get_grounding_auto_recovery_timeout_s_fn: Callable[[], float],
    get_grounding_auto_recovery_whitelist_fn: Callable[[], List[str]],
    has_usable_grounding_evidence_fn: Callable[[Dict[str, Any]], bool],
    get_recent_grounding_state_fn: Callable[[str, int], Optional[Dict[str, Any]]],
    select_first_whitelisted_tool_run_fn: Callable[[Optional[Dict[str, Any]], Any], Optional[Dict[str, Any]]],
    sanitize_tool_args_fn: Callable[[Any], Dict[str, Any]],
    execute_tools_sync_fn: Callable[..., Any],
    control_decision_from_plan_fn: Callable[..., Any],
    log_info_fn: Callable[[str], None],
    log_warn_fn: Callable[[str], None],
) -> str:
    if not get_grounding_auto_recovery_enable_fn():
        return ""
    if not isinstance(verified_plan, dict):
        return ""
    if verified_plan.get("_grounding_auto_recovery_attempted"):
        return ""
    if not bool(verified_plan.get("is_fact_query", False)):
        return ""
    if has_usable_grounding_evidence_fn(verified_plan):
        return ""

    state = get_recent_grounding_state_fn(conversation_id, history_len)
    if not state:
        return ""
    whitelist = {str(x).strip() for x in get_grounding_auto_recovery_whitelist_fn() if str(x).strip()}
    if not whitelist:
        return ""

    candidate = select_first_whitelisted_tool_run_fn(state, whitelist)
    if not candidate:
        return ""

    tool_name = str(candidate.get("tool_name", "")).strip()
    tool_args = sanitize_tool_args_fn(candidate.get("args") or {})
    if not tool_name:
        return ""

    spec = {"tool": tool_name, "args": tool_args}
    verified_plan["_grounding_auto_recovery_attempted"] = True
    verified_plan["needs_chat_history"] = True
    log_info_fn(f"[Orchestrator] Auto-recovery grounding re-run: tool={tool_name}")
    timeout_s = float(get_grounding_auto_recovery_timeout_s_fn())
    try:
        recovery_ctx = await asyncio.wait_for(
            asyncio.to_thread(
                execute_tools_sync_fn,
                [spec],
                user_text,
                {},
                control_decision=control_decision_from_plan_fn(
                    verified_plan,
                    default_approved=False,
                ),
                time_reference=thinking_plan.get("time_reference"),
                thinking_suggested_tools=thinking_plan.get("suggested_tools", []),
                blueprint_gate_blocked=False,
                blueprint_router_id=None,
                blueprint_suggest_msg="",
                session_id=session_id or "",
                verified_plan=verified_plan,
            ),
            timeout=timeout_s,
        )
        if recovery_ctx:
            verified_plan["_grounding_auto_recovery_used"] = True
            return str(recovery_ctx)
    except asyncio.TimeoutError:
        log_warn_fn(
            f"[Orchestrator] Auto-recovery skipped (timeout after {timeout_s:.1f}s) tool={tool_name}"
        )
    except Exception as exc:
        log_warn_fn(f"[Orchestrator] Auto-recovery failed tool={tool_name}: {exc}")
    return ""
