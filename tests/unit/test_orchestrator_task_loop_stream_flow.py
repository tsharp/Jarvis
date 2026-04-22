from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.orchestrator_stream_flow_utils import process_stream_with_events
from core.task_loop.chat_runtime import start_chat_task_loop
from core.task_loop.store import get_task_loop_store


@pytest.mark.asyncio
async def test_stream_path_active_task_loop_routes_after_control_with_reason_code(monkeypatch):
    conversation_id = "conv-stream-task-loop"
    get_task_loop_store().clear(conversation_id)
    start_chat_task_loop(
        "Task-Loop: Bitte schrittweise einen Plan machen",
        conversation_id,
        store=get_task_loop_store(),
        auto_continue=False,
    )

    orch = MagicMock()
    orch.lifecycle = MagicMock()
    orch._requested_response_mode = MagicMock(return_value=None)
    orch._classify_tone_signal = AsyncMock(return_value=None)
    orch._ensure_dialogue_controls = MagicMock(side_effect=lambda plan, *_args, **_kwargs: plan)
    orch._maybe_prefetch_skills = MagicMock(return_value=("", "off"))
    orch._extract_workspace_observations = MagicMock(return_value="")
    orch._collect_control_tool_decisions = AsyncMock(return_value={})
    orch._should_skip_thinking_from_query_budget = MagicMock(return_value=False)
    orch._is_control_hard_block_decision = MagicMock(return_value=False)
    orch.build_effective_context = MagicMock(
        return_value=(
            "",
            {
                "memory_used": False,
                "small_model_mode": False,
                "context_chars": 0,
                "retrieval_count": 0,
                "context_sources": [],
            },
            None,
        )
    )
    orch._should_skip_control_layer = MagicMock(return_value=(False, "control_required"))
    orch._save_workspace_entry = MagicMock(
        side_effect=lambda *args, **kwargs: {
            "type": "workspace_update",
            "entry_id": kwargs.get("entry_type") or (args[2] if len(args) > 2 else "ws"),
        }
    )
    orch._post_task_processing = MagicMock()
    thinking = MagicMock()

    async def _analyze_stream(*_args, **_kwargs):
        yield ("", True, {"intent": "Loop fortsetzen", "suggested_tools": [], "needs_sequential_thinking": False})

    thinking.analyze_stream = _analyze_stream
    orch.thinking = thinking
    control = MagicMock()
    control.verify = AsyncMock(
        return_value={
            "approved": True,
            "decision_class": "allow",
            "warnings": [],
            "final_instruction": "",
        }
    )
    control.apply_corrections = MagicMock(
        side_effect=lambda plan, verification: {
            **plan,
            "_authoritative_turn_mode": "task_loop",
            "_authoritative_turn_mode_reason": "continue_active_task_loop",
            "_authoritative_turn_mode_reasons": ["continue_active_task_loop"],
            "_authoritative_turn_mode_blockers": [],
            "_control_decision": verification,
        }
    )
    orch.control = control
    orch.output = MagicMock()

    request = SimpleNamespace(
        model="test-model",
        conversation_id=conversation_id,
        messages=[],
        raw_request={},
        source_adapter="test",
        get_last_user_message=lambda: "weiter",
    )

    monkeypatch.setattr(
        "core.orchestrator_pipeline_stages.run_tool_selection_stage",
        AsyncMock(return_value=([], {}, {}, "")),
    )
    monkeypatch.setattr(
        "core.orchestrator_pipeline_stages.run_plan_finalization",
        lambda orch, user_text, request, thinking_plan, selected_tools, query_budget_signal, domain_route_signal, forced_response_mode, conversation_id, log_info_fn: (
            thinking_plan,
            "interactive",
        ),
    )
    monkeypatch.setattr(
        "core.orchestrator_pipeline_stages.run_pre_control_gates",
        lambda *args, **kwargs: (None, ""),
    )

    out = []
    async for item in process_stream_with_events(
        orch,
        request,
        intent_system_available=False,
        enable_chunking=False,
        chunking_threshold=100000,
        get_master_settings_fn=lambda: {},
        thinking_plan_cache=MagicMock(),
        sequential_result_cache=MagicMock(),
        soften_control_deny_fn=MagicMock(),
        skill_creation_intent_cls=None,
        intent_origin_cls=None,
        get_intent_store_fn=lambda: None,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
        log_error_fn=lambda _msg: None,
        log_debug_fn=lambda _msg: None,
        log_warning_fn=lambda _msg: None,
    ):
        out.append(item)

    assert any(item[2].get("type") == "thinking_done" for item in out)
    assert any(item[2].get("type") == "control" for item in out)
    routing_events = [item[2] for item in out if item[2].get("type") == "task_loop_routing"]
    assert routing_events
    assert routing_events[0]["branch"] == "active_task_loop"
    assert routing_events[0]["active_task_loop_detail"] == "explicit_continue_request"
    assert routing_events[0]["runtime_resume_candidate"] is False
    assert routing_events[0]["is_authoritative_task_loop_turn"] is True
    assert any(item[2].get("type") == "task_loop_update" for item in out)
    assert any(item[2].get("type") == "workspace_update" for item in out)
    assert out[-1][1] is True
    assert out[-1][2]["done_reason"] in {"task_loop_completed", "task_loop_waiting_for_user"}
    assert orch.control.verify.await_count >= 1  # pipeline + per-step task-loop control checks
    assert orch.lifecycle.finish_task.call_args[0][1]["active_loop_reason"] == "continue_active_task_loop"
    orch.lifecycle.finish_task.assert_called_once()
    orch._post_task_processing.assert_called_once()
