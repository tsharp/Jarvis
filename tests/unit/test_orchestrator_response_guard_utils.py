import threading
import time

import pytest

from core.orchestrator_response_guard_utils import (
    apply_conversation_consistency_guard,
    get_recent_consistency_entries,
    maybe_auto_recover_grounding_once,
    remember_consistency_entries,
)


def test_get_and_remember_consistency_entries_prune_and_roundtrip():
    state = {}
    lock = threading.Lock()

    def _policy():
        return {
            "history_ttl_s": 3600,
            "max_entries_per_conversation": 2,
        }

    def _prune(entries, *, now_ts, ttl_s, max_entries):
        fresh = [dict(item) for item in entries if now_ts - float(item.get("ts") or 0.0) <= ttl_s]
        return fresh[-max_entries:]

    now = time.time()
    remember_consistency_entries(
        consistency_state=state,
        consistency_lock=lock,
        conversation_id="conv-a",
        entries=[
            {"topic": "a", "stance": "deny", "snippet": "old", "ts": now - 10},
            {"topic": "a", "stance": "allow", "snippet": "newer", "ts": now - 5},
            {"topic": "b", "stance": "deny", "snippet": "latest", "ts": now},
        ],
        load_policy_fn=_policy,
        prune_entries_fn=_prune,
    )

    out = get_recent_consistency_entries(
        consistency_state=state,
        consistency_lock=lock,
        conversation_id="conv-a",
        load_policy_fn=_policy,
        prune_entries_fn=_prune,
    )

    assert [item["snippet"] for item in out] == ["newer", "latest"]


@pytest.mark.asyncio
async def test_apply_conversation_consistency_guard_direct_utility_path():
    remembered = []
    verified_plan = {"_execution_result": {"grounding": {"successful_evidence": 0}}}

    def _signals(text):
        lower = str(text or "").lower()
        if "nicht sicher" in lower:
            return [{
                "topic": "host_runtime_ip_disclosure",
                "stance": "deny",
                "snippet": "Ich kann das nicht sicher bestaetigen.",
            }]
        return [{
            "topic": "host_runtime_ip_disclosure",
            "stance": "allow",
            "snippet": "Ich kann die Host-IP nennen.",
        }]

    out = await apply_conversation_consistency_guard(
        conversation_id="conv-guard",
        verified_plan=verified_plan,
        answer="Ich kann die Host-IP nennen.",
        load_policy_fn=lambda: {
            "enabled": True,
            "embedding_enable": True,
            "embedding_similarity_threshold": 0.7,
            "require_evidence_on_stance_change": True,
            "min_successful_evidence_on_stance_change": 1,
            "fallback_mode": "explicit_uncertainty",
        },
        extract_stance_signals_fn=_signals,
        get_recent_consistency_entries_fn=lambda _conv: [{
            "topic": "host_runtime_ip_disclosure",
            "stance": "deny",
            "snippet": "Ich kann die Host-IP nicht nennen.",
            "embedding": [1.0, 0.0],
        }],
        embed_text_fn=lambda _text, timeout_s: [1.0, 0.0],
        detect_conflicts_fn=lambda **_kwargs: [{"topic": "host_runtime_ip_disclosure"}],
        make_stance_entries_fn=lambda **kwargs: [{"signals": kwargs["signals"], "embedding": kwargs["embedding"]}],
        remember_consistency_entries_fn=lambda _conv, entries: remembered.extend(entries),
        get_runtime_grounding_value_fn=lambda _plan, key, default=0: 0 if key == "successful_evidence" else default,
        get_runtime_grounding_evidence_fn=lambda _plan: [{"tool_name": "run_skill", "status": "ok"}],
        build_grounding_fallback_fn=lambda evidence, mode: "Ich kann das nicht sicher bestaetigen.",
        log_warn_fn=lambda _msg: None,
    )

    assert "nicht sicher" in out
    assert verified_plan["_consistency_conflict_detected"] is True
    assert verified_plan["_grounded_fallback_used"] is True
    assert remembered


@pytest.mark.asyncio
async def test_maybe_auto_recover_grounding_once_direct_utility_path():
    calls = []
    verified_plan = {"is_fact_query": True}

    def _execute_tools_sync(specs, user_text, _tool_context, **kwargs):
        calls.append((specs, user_text, kwargs))
        return "\n[TOOL-CARD: run_skill | ok | ref:run-skill-ref]\n"

    out = await maybe_auto_recover_grounding_once(
        conversation_id="conv-recovery",
        user_text="Und welche GPU genau?",
        verified_plan=verified_plan,
        thinking_plan={"suggested_tools": ["run_skill"]},
        history_len=8,
        session_id="conv-recovery",
        get_grounding_auto_recovery_enable_fn=lambda: True,
        get_grounding_auto_recovery_timeout_s_fn=lambda: 1.0,
        get_grounding_auto_recovery_whitelist_fn=lambda: ["run_skill"],
        has_usable_grounding_evidence_fn=lambda _plan: False,
        get_recent_grounding_state_fn=lambda _conv, _hist: {
            "tool_runs": [{"tool_name": "run_skill", "args": {"name": "system_hardware_info"}}],
        },
        select_first_whitelisted_tool_run_fn=lambda state, whitelist: state["tool_runs"][0],
        sanitize_tool_args_fn=lambda value: dict(value or {}),
        execute_tools_sync_fn=_execute_tools_sync,
        control_decision_from_plan_fn=lambda _plan, default_approved=False: {
            "approved": default_approved,
        },
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
    )

    assert "TOOL-CARD" in out
    assert verified_plan["_grounding_auto_recovery_attempted"] is True
    assert verified_plan["_grounding_auto_recovery_used"] is True
    assert verified_plan["needs_chat_history"] is True
    assert calls[0][0][0]["tool"] == "run_skill"
