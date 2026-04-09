import threading
import time

from core.orchestrator_state_runtime_utils import (
    get_recent_container_state,
    get_recent_grounding_state,
    inject_carryover_grounding_evidence_runtime,
    remember_container_state,
    remember_conversation_grounding_state,
    resolve_followup_tool_reuse_runtime,
    resolve_pending_container_id_sync,
)
from core.plan_runtime_bridge import (
    get_runtime_carryover_grounding_evidence,
    set_runtime_grounding_evidence,
    set_runtime_successful_tool_runs,
)


class _ContainerStateStore:
    def __init__(self):
        self.state = {}
        self.updated = []

    def get_recent(self, conversation_id, history_len):
        return self.state.get((conversation_id, history_len))

    def remember(
        self,
        conversation_id,
        *,
        last_active_container_id="",
        home_container_id="",
        known_containers=None,
        history_len=0,
    ):
        self.state[(conversation_id, history_len)] = {
            "last_active_container_id": last_active_container_id,
            "home_container_id": home_container_id,
            "known_containers": list(known_containers or []),
        }

    def update_from_tool_result(self, conversation_id, tool_name, tool_args, result, *, history_len=0):
        self.updated.append((conversation_id, tool_name, tool_args, result, history_len))


class _Hub:
    def call_tool(self, name, args):
        assert name == "container_list"
        assert args == {}
        return {
            "containers": [
                {"container_id": "stopped1", "status": "stopped", "blueprint_id": "other"},
                {"container_id": "home2", "status": "running", "blueprint_id": "trion-home"},
            ]
        }


def test_container_state_roundtrip_and_pending_resolution_sync():
    store = _ContainerStateStore()
    remember_container_state(
        container_state_store=store,
        conversation_id="conv-a",
        last_active_container_id="abc",
        home_container_id="home1",
        known_containers=[{"container_id": "abc"}],
        history_len=4,
    )

    snap = get_recent_container_state(
        container_state_store=store,
        conversation_id="conv-a",
        history_len=4,
    )
    assert snap["last_active_container_id"] == "abc"

    selected, err = resolve_pending_container_id_sync(
        tool_hub=_Hub(),
        conversation_id="conv-a",
        preferred_ids=["missing"],
        history_len=4,
        safe_str_fn=lambda value, max_len: str(value)[:max_len],
        update_container_state_from_tool_result_fn=lambda *args, **kwargs: store.update_from_tool_result(*args, **kwargs),
        expected_home_blueprint_id="trion-home",
    )

    assert selected == "home2"
    assert err == ""
    assert store.updated[0][1] == "container_list"


def test_get_recent_grounding_state_prunes_expired_snapshot():
    state = {
        "conv-expired": {
            "updated_at": time.time() - 200,
            "history_len": 2,
            "tool_runs": [{"tool_name": "run_skill"}],
            "evidence": [{"status": "ok", "key_facts": ["x"]}],
        }
    }
    lock = threading.Lock()

    snap = get_recent_grounding_state(
        conversation_grounding_state=state,
        conversation_grounding_lock=lock,
        conversation_id="conv-expired",
        history_len=2,
        ttl_s=30,
        ttl_turns=2,
    )

    assert snap is None
    assert "conv-expired" not in state


def test_remember_grounding_state_and_inject_carryover():
    state = {}
    lock = threading.Lock()
    plan = {"is_fact_query": True}
    set_runtime_grounding_evidence(plan, [{"status": "ok", "key_facts": ["GPU: RTX"], "tool_name": "run_skill"}])
    set_runtime_successful_tool_runs(plan, [{"tool_name": "run_skill", "args": {"name": "system_hardware_info"}}])

    remember_conversation_grounding_state(
        conversation_grounding_state=state,
        conversation_grounding_lock=lock,
        conversation_id="conv-ground",
        verified_plan=plan,
        history_len=5,
        sanitize_tool_args_fn=lambda value: dict(value or {}),
        evidence_has_content_fn=lambda item: bool(item.get("key_facts")),
    )

    assert state["conv-ground"]["tool_runs"][0]["tool_name"] == "run_skill"

    fresh_plan = {"is_fact_query": True}
    logs = []
    inject_carryover_grounding_evidence_runtime(
        conversation_id="conv-ground",
        verified_plan=fresh_plan,
        history_len=5,
        get_recent_grounding_state_fn=lambda conv_id, hist_len: get_recent_grounding_state(
            conversation_grounding_state=state,
            conversation_grounding_lock=lock,
            conversation_id=conv_id,
            history_len=hist_len,
            ttl_s=60,
            ttl_turns=2,
        ),
        evidence_has_content_fn=lambda item: bool(item.get("key_facts")),
        log_info_fn=logs.append,
    )

    assert get_runtime_carryover_grounding_evidence(fresh_plan)
    assert fresh_plan["_selected_tools_for_prompt"] == ["run_skill"]
    assert logs


def test_resolve_followup_tool_reuse_runtime_fact_followup_marks_plan():
    logs = []
    verified_plan = {"is_fact_query": True, "dialogue_act": "request"}

    out = resolve_followup_tool_reuse_runtime(
        user_text="und welche grafikkarte genau?",
        verified_plan=verified_plan,
        conversation_id="conv-followup",
        chat_history=[{"role": "assistant", "content": "GPU: NVIDIA"}],
        followup_enabled=True,
        contains_explicit_tool_intent_fn=lambda _text: False,
        looks_like_short_fact_followup_fn=lambda _text, _hist: True,
        looks_like_short_confirmation_followup_fn=lambda _text, _hist: False,
        looks_like_short_confirmation_followup_state_only_fn=lambda _text: False,
        get_recent_grounding_state_fn=lambda _conv, _hist: {
            "tool_runs": [{"tool_name": "run_skill", "args": {"name": "system_hardware_info"}}],
            "evidence": [{"status": "ok", "key_facts": ["GPU: NVIDIA"]}],
        },
        sanitize_tool_args_fn=lambda value: dict(value or {}),
        log_info_fn=logs.append,
    )

    assert out == [{"tool": "run_skill", "args": {"name": "system_hardware_info"}}]
    assert verified_plan["_followup_tool_reuse_active"] is True
    assert verified_plan["needs_chat_history"] is True
    assert any("Follow-up tool reuse active" in line for line in logs)


def test_resolve_followup_tool_reuse_runtime_state_only_fallback_sets_marker():
    logs = []
    verified_plan = {"suggested_tools": [], "is_fact_query": False, "dialogue_act": "smalltalk"}

    out = resolve_followup_tool_reuse_runtime(
        user_text="okey mach das bitte",
        verified_plan=verified_plan,
        conversation_id="conv-state-only",
        chat_history=[],
        followup_enabled=True,
        contains_explicit_tool_intent_fn=lambda _text: False,
        looks_like_short_fact_followup_fn=lambda _text, _hist: False,
        looks_like_short_confirmation_followup_fn=lambda _text, _hist: False,
        looks_like_short_confirmation_followup_state_only_fn=lambda _text: True,
        get_recent_grounding_state_fn=lambda _conv, _hist: {
            "tool_runs": [{"tool_name": "exec_in_container", "args": {"container_id": "home001"}}],
            "evidence": [{"status": "ok", "key_facts": ["stdout: ok"]}],
        },
        sanitize_tool_args_fn=lambda value: dict(value or {}),
        log_info_fn=logs.append,
    )

    assert out == [{"tool": "exec_in_container", "args": {"container_id": "home001"}}]
    assert verified_plan["_followup_tool_reuse_state_fallback"] is True
    assert verified_plan["_followup_tool_reuse_active"] is True
    assert any("state-only confirmation" in line for line in logs)
