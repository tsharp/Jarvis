import json

from core.orchestrator_context_workspace_utils import (
    clip_tool_context,
    compute_retrieval_policy,
    persist_master_workspace_event,
)


def test_compute_retrieval_policy_switches_to_failure_budget():
    out = compute_retrieval_policy(
        {"time_reference": "today"},
        {"_verified": True},
        current_tool_context="TOOL-FEHLER: boom",
        get_jit_retrieval_max_fn=lambda: 1,
        get_jit_retrieval_max_on_failure_fn=lambda: 2,
    )

    assert out["max_retrievals"] == 2
    assert out["tool_failure"] is True
    assert out["time_reference"] == "today"


def test_clip_tool_context_keeps_valid_json_and_failure_marker():
    payload = {
        "tool": "memory_graph_search",
        "results": [{"id": idx, "text": "x" * 400} for idx in range(10)],
    }
    clipped_json = clip_tool_context(
        json.dumps(payload, ensure_ascii=False),
        small_model_mode=True,
        get_small_model_tool_ctx_cap_fn=lambda: 220,
        tool_context_has_failures_or_skips_fn=lambda text: "TOOL-FEHLER" in text,
        log_warn_fn=lambda _msg: None,
    )
    assert len(clipped_json) <= 220
    assert isinstance(json.loads(clipped_json), (dict, list))

    failing = "\n### TOOL-FEHLER (run_skill): x\n" + ("A" * 800)
    clipped_fail = clip_tool_context(
        failing,
        small_model_mode=True,
        get_small_model_tool_ctx_cap_fn=lambda: 180,
        tool_context_has_failures_or_skips_fn=lambda text: "TOOL-FEHLER" in text,
        log_warn_fn=lambda _msg: None,
    )
    assert len(clipped_fail) <= 180
    assert "TOOL-FEHLER" in clipped_fail


def test_persist_master_workspace_event_filters_unknown_types_and_formats_payload():
    saved = []

    out = persist_master_workspace_event(
        conversation_id="conv-master",
        event_type="planning_step",
        payload={"phase": "planning", "next_action": "Analyze logs"},
        build_master_workspace_summary_fn=lambda event_type, payload: f"{event_type}:{payload['phase']}",
        save_workspace_entry_fn=lambda **kwargs: saved.append(kwargs) or {"type": "workspace_update"},
    )

    assert out == {"type": "workspace_update"}
    assert saved[0]["entry_type"] == "planning_step"
    assert saved[0]["source_layer"] == "master"

    ignored = persist_master_workspace_event(
        conversation_id="conv-master",
        event_type="unknown",
        payload={},
        build_master_workspace_summary_fn=lambda *_args, **_kwargs: "",
        save_workspace_entry_fn=lambda **_kwargs: {"should": "not-run"},
    )
    assert ignored is None
