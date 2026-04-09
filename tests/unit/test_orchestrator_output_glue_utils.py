import json

from core.orchestrator_output_glue_utils import (
    build_tool_result_card,
    compute_ctx_mode,
    extract_workspace_observations,
    format_tool_result,
    merge_grounding_evidence_items,
)
from core.tools.tool_result import ToolResult


def test_merge_grounding_evidence_items_dedupes_by_signature():
    existing = [
        {"tool_name": "list_skills", "ref_id": "a", "status": "ok", "key_facts": ["x", "y"]},
    ]
    extra = [
        {"tool_name": "list_skills", "ref_id": "a", "status": "ok", "key_facts": ["x", "y"]},
        {"tool_name": "list_draft_skills", "ref_id": "b", "status": "ok", "key_facts": ["draft"]},
    ]

    out = merge_grounding_evidence_items(existing, extra)

    assert len(out) == 2
    assert out[0]["tool_name"] == "list_skills"
    assert out[1]["tool_name"] == "list_draft_skills"


def test_format_tool_result_handles_fast_lane_and_mcp_paths():
    fast_lane = ToolResult(tool_name="home_read", success=True, content={"ok": True}, latency_ms=12.5)
    formatted_fast, success_fast, meta_fast = format_tool_result(
        fast_lane,
        "home_read",
        detect_tool_error_fn=lambda _result: (False, ""),
    )
    assert success_fast is True
    assert "Fast Lane" in formatted_fast
    assert meta_fast["execution_mode"] == "fast_lane"

    formatted_mcp, success_mcp, meta_mcp = format_tool_result(
        {"error": "boom"},
        "run_skill",
        detect_tool_error_fn=lambda result: (True, "boom"),
    )
    assert success_mcp is False
    assert "FEHLER" in formatted_mcp
    assert meta_mcp["execution_mode"] == "mcp"
    assert meta_mcp["error"] == "boom"


def test_build_tool_result_card_promotes_approval_requested_event_type():
    saved = []

    card, ref_id = build_tool_result_card(
        tool_name="run_skill",
        raw_result=json.dumps(
            {
                "event_type": "approval_requested",
                "skill_name": "python_tool",
                "missing_packages": ["numpy"],
                "non_allowlisted_packages": ["numpy"],
            }
        ),
        status="partial",
        conversation_id="conv-approval",
        save_workspace_entry_fn=lambda conv_id, payload, entry_type, origin: saved.append(
            (conv_id, json.loads(payload), entry_type, origin)
        ),
        log_warn_fn=lambda _msg: None,
        tool_card_char_cap=800,
        tool_card_bullet_cap=3,
    )

    assert "TOOL-CARD" in card
    assert ref_id
    assert saved[0][0] == "conv-approval"
    assert saved[0][2] == "approval_requested"
    assert saved[0][1]["skill_name"] == "python_tool"
    assert saved[0][1]["payload"]


def test_compute_ctx_mode_and_extract_workspace_observations_emit_expected_shapes():
    mode = compute_ctx_mode(
        {"small_model_mode": True, "context_sources": ["failure_ctx"]},
        is_loop=True,
        get_context_trace_dryrun_fn=lambda: True,
    )
    obs = extract_workspace_observations(
        {
            "intent": "test_intent",
            "memory_keys": ["alpha"],
            "hallucination_risk": "high",
            "needs_sequential_thinking": True,
        }
    )

    assert mode == "small+failure+dryrun+loop"
    assert "**Intent:** test_intent" in obs
    assert "**Memory keys:** alpha" in obs
    assert "**Sequential thinking** required" in obs
