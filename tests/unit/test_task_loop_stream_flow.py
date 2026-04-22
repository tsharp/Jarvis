from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.orchestrator_modules.task_loop import stream_task_loop_events
from core.task_loop.contracts import (
    TaskLoopSnapshot,
    TaskLoopState,
    TaskLoopStepExecutionSource,
    TaskLoopStepStatus,
    TaskLoopStepType,
)
from core.task_loop.chat_runtime import start_chat_task_loop
from core.orchestrator_stream_flow_utils import process_stream_with_events
from core.task_loop.store import get_task_loop_store


@pytest.mark.asyncio
async def test_stream_task_loop_events_yield_incremental_updates_and_content():
    conversation_id = "conv-task-loop-stream-events"
    get_task_loop_store().clear(conversation_id)

    orch = MagicMock()
    orch._save_workspace_entry = MagicMock(
        side_effect=lambda **kwargs: {
            "type": "workspace_update",
            "entry_id": kwargs["entry_type"],
            "content": kwargs["content"],
        }
    )
    orch.thinking = MagicMock()
    orch.thinking.analyze = AsyncMock(return_value={})

    request = SimpleNamespace(
        model="test-model",
        conversation_id=conversation_id,
        raw_request={},
    )

    out = []
    async for item in stream_task_loop_events(
        orch,
        request,
        "Task-Loop: Bitte schrittweise einen Plan machen",
        conversation_id,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
        tone_signal=None,
    ):
        out.append(item)

    content_events = [item for item in out if item[2].get("type") == "content"]
    update_events = [item for item in out if item[2].get("type") == "task_loop_update"]

    assert len(content_events) >= 2
    assert content_events[0][0]  # first content event is non-empty step answer
    assert content_events[1][0]  # second content event is non-empty
    assert len(update_events) >= 2
    assert update_events[0][2]["is_final"] is False
    assert update_events[-1][2]["is_final"] is True
    assert out[-1][1] is True
    assert out[-1][2]["done_reason"] == "task_loop_completed"


@pytest.mark.asyncio
async def test_stream_task_loop_events_force_start_uses_authoritative_plan():
    conversation_id = "conv-task-loop-force-start"
    get_task_loop_store().clear(conversation_id)

    orch = MagicMock()
    orch._save_workspace_entry = MagicMock(
        side_effect=lambda **kwargs: {
            "type": "workspace_update",
            "entry_id": kwargs["entry_type"],
            "content": kwargs["content"],
        }
    )
    orch.control = MagicMock()
    orch.output = MagicMock()

    request = SimpleNamespace(
        model="test-model",
        conversation_id=conversation_id,
        raw_request={},
    )

    out = []
    async for item in stream_task_loop_events(
        orch,
        request,
        "Bitte pruefe den neuen Ablauf mit sichtbaren Zwischenstaenden",
        conversation_id,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
        tone_signal=None,
        thinking_plan={
            "intent": "Ablauf pruefen",
            "hallucination_risk": "low",
            "suggested_tools": [],
            "_authoritative_turn_mode": "task_loop",
        },
        force_start=True,
    ):
        out.append(item)

    assert any(item[2].get("type") == "task_loop_update" for item in out)
    assert any(item[2].get("type") == "content" and item[0] for item in out)
    assert out[-1][1] is True
    assert out[-1][2]["done_reason"] == "task_loop_completed"


@pytest.mark.asyncio
async def test_process_stream_with_events_uses_incremental_task_loop_streaming_for_active_loop(monkeypatch):
    conversation_id = "conv-task-loop-stream-process"
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
                "context_chars_final": 0,
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
            "content": kwargs.get("content") or (args[1] if len(args) > 1 else ""),
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

    content_events = [item for item in out if item[2].get("type") == "content"]
    assert len(content_events) >= 1
    assert any(item[2].get("type") == "thinking_done" for item in out)
    assert any(item[2].get("type") == "task_loop_update" for item in out)
    assert out[-1][1] is True
    assert out[-1][2]["done_reason"] in {"task_loop_completed", "task_loop_waiting_for_user"}


@pytest.mark.asyncio
async def test_process_stream_with_events_keeps_active_loop_as_context_for_meta_turn(monkeypatch):
    conversation_id = "conv-task-loop-context-only"
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
    orch._should_skip_control_layer = MagicMock(return_value=(False, "control_required"))
    orch._save_workspace_entry = MagicMock(
        side_effect=lambda *args, **kwargs: {
            "type": "workspace_update",
            "entry_id": kwargs.get("entry_type") or (args[2] if len(args) > 2 else "ws"),
            "content": kwargs.get("content") or (args[1] if len(args) > 1 else ""),
        }
    )
    orch.build_effective_context = MagicMock(
        return_value=(
            "",
            {
                "memory_used": False,
                "small_model_mode": False,
                "context_chars": 0,
                "context_chars_final": 0,
                "retrieval_count": 0,
                "context_sources": [],
            },
            None,
        )
    )
    orch._post_task_processing = MagicMock()
    orch._resolve_execution_suggested_tools = MagicMock(return_value=[])
    orch._clip_tool_context = MagicMock(side_effect=lambda text, _smm: text)
    orch._tool_context_has_failures_or_skips = MagicMock(return_value=False)
    orch._tool_context_has_success = MagicMock(return_value=False)
    orch._append_context_block = MagicMock(side_effect=lambda base, extra, _source, _trace: f"{base}{extra}")
    orch._maybe_build_active_container_capability_context = AsyncMock(return_value={})
    orch._maybe_build_skill_semantic_context = AsyncMock(return_value={})
    orch._maybe_build_system_knowledge_context = AsyncMock(return_value={})
    orch._inject_carryover_grounding_evidence = MagicMock()
    orch._maybe_auto_recover_grounding_once = AsyncMock(return_value="")
    orch._remember_conversation_grounding_state = MagicMock()
    orch._apply_final_cap = MagicMock(side_effect=lambda text, _trace, _smm, _path: text)
    orch._apply_effective_context_guardrail = MagicMock(side_effect=lambda text, _trace, _smm, _path: text)
    orch._compute_ctx_mode = MagicMock(return_value="normal")
    orch._apply_conversation_consistency_guard = AsyncMock(side_effect=lambda **kwargs: kwargs["answer"])
    orch._save_memory = MagicMock()
    orch._build_done_workspace_summary = MagicMock(return_value="done")

    thinking = MagicMock()

    async def _analyze_stream(*_args, **_kwargs):
        yield ("", True, {"intent": "Loop Meta-Frage", "suggested_tools": [], "needs_sequential_thinking": False})

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

    output = MagicMock()

    async def _generate_stream(**_kwargs):
        yield "Das war ein Timeout im vorherigen Schritt."

    output.generate_stream = _generate_stream
    orch.output = output

    request = SimpleNamespace(
        model="test-model",
        conversation_id=conversation_id,
        messages=[],
        raw_request={},
        source_adapter="test",
        get_last_user_message=lambda: "was ist passiert?",
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
    monkeypatch.setattr(
        "core.orchestrator_pipeline_stages.prepare_output_invocation",
        lambda orch, request, verified_plan, mem_res, response_mode="interactive": ("test-model", False),
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

    content_events = [item for item in out if item[2].get("type") == "content"]
    task_loop_updates = [item for item in out if item[2].get("type") == "task_loop_update"]
    thinking_traces = [item[2] for item in out if item[2].get("type") == "thinking_trace"]

    assert any("Das war ein Timeout" in item[0] for item in content_events)
    assert any(item[2].get("context_only") is True for item in task_loop_updates)
    assert any(item[2].get("background_loop_preserved") is True for item in task_loop_updates)
    assert any(item[2].get("background_loop_topic") for item in task_loop_updates)
    assert any(event.get("thinking", {}).get("source") == "trace" for event in thinking_traces)
    assert any(event.get("thinking", {}).get("source") == "trace_final" for event in thinking_traces)
    assert any(event.get("thinking", {}).get("authoritative_turn_mode") == "task_loop" for event in thinking_traces)
    assert any(event.get("thinking", {}).get("task_loop_active_reason") == "active_task_loop_context_only" for event in thinking_traces)
    assert any(event.get("thinking", {}).get("task_loop_active_reason_detail") == "authoritative_task_loop_non_resume_background" for event in thinking_traces)
    assert any(event.get("thinking", {}).get("task_loop_routing_branch") == "task_loop_context_only" for event in thinking_traces)
    snapshot = get_task_loop_store().get_active(conversation_id)
    assert snapshot is not None
    assert snapshot.last_user_visible_answer == "Das war ein Timeout im vorherigen Schritt."


@pytest.mark.asyncio
async def test_stream_task_loop_events_runtime_resumes_waiting_approval_tool_step(monkeypatch):
    conversation_id = "conv-task-loop-stream-resume"
    get_task_loop_store().clear(conversation_id)
    snapshot = TaskLoopSnapshot(
        objective_id="obj-tool",
        conversation_id=conversation_id,
        plan_id="plan-tool",
        state=TaskLoopState.WAITING_FOR_USER,
        current_step_id="step-tool-1",
        current_step_type=TaskLoopStepType.TOOL_REQUEST,
        current_step_status=TaskLoopStepStatus.WAITING_FOR_APPROVAL,
        step_execution_source=TaskLoopStepExecutionSource.APPROVAL,
        current_plan=[
            "Container-Anfrage zur Freigabe vorbereiten",
            "Container-Anfrage ausfuehren",
        ],
        plan_steps=[
            {
                "step_id": "step-tool-1",
                "title": "Container-Anfrage zur Freigabe vorbereiten",
                "goal": "Die Container-Anfrage sichtbar vorbereiten und zur Freigabe stellen.",
                "done_criteria": "Freigabe, Ziel und Risiko sind sichtbar vorbereitet.",
                "risk_level": "needs_confirmation",
                "requires_user": True,
                "suggested_tools": ["request_container"],
                "task_kind": "implementation",
                "objective": "Gaming-Container kontrolliert starten",
                "step_type": TaskLoopStepType.TOOL_REQUEST.value,
                "requested_capability": {
                    "capability_type": "container_manager",
                    "capability_target": "request_container",
                    "capability_action": "request_container",
                },
            },
            {
                "step_id": "step-tool-2",
                "title": "Container-Anfrage ausfuehren",
                "goal": "Die freigegebene Container-Anfrage ausfuehren.",
                "done_criteria": "Ein verifizierter Tool-Befund liegt vor.",
                "risk_level": "safe",
                "requires_user": False,
                "suggested_tools": ["request_container"],
                "task_kind": "implementation",
                "objective": "Gaming-Container kontrolliert starten",
                "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
                "requested_capability": {
                    "capability_type": "container_manager",
                    "capability_target": "request_container",
                    "capability_action": "request_container",
                },
            }
        ],
        pending_step="Container-Anfrage zur Freigabe vorbereiten",
        last_step_result={
            "status": TaskLoopStepStatus.WAITING_FOR_APPROVAL.value,
            "step_type": TaskLoopStepType.TOOL_REQUEST.value,
            "step_execution_source": TaskLoopStepExecutionSource.APPROVAL.value,
        },
    )
    get_task_loop_store().put(snapshot)

    class _Control:
        async def verify(self, user_text, thinking_plan, retrieved_memory="", response_mode="interactive"):
            return {
                "approved": True,
                "decision_class": "allow",
                "warnings": [],
                "final_instruction": "",
            }

    class _Output:
        async def generate_stream(
            self,
            user_text,
            verified_plan,
            memory_data="",
            model=None,
            memory_required_but_missing=False,
            chat_history=None,
            control_decision=None,
            execution_result=None,
        ):
            yield "unused"

    orch = MagicMock()
    orch._save_workspace_entry = MagicMock(
        side_effect=lambda **kwargs: {
            "type": "workspace_update",
            "entry_id": kwargs["entry_type"],
            "content": kwargs["content"],
        }
    )
    orch.control = _Control()
    orch.output = _Output()
    orch._collect_control_tool_decisions = AsyncMock(return_value={"request_container": {"blueprint_id": "gaming-station"}})
    orch._resolve_execution_suggested_tools = MagicMock(
        return_value=[{"name": "request_container", "arguments": {"blueprint_id": "gaming-station"}}]
    )

    def _execute_tools_sync(
        suggested_tools,
        user_text,
        control_tool_decisions=None,
        **kwargs,
    ):
        verified_plan = kwargs["verified_plan"]
        verified_plan["_execution_result"] = {
            "done_reason": "success",
            "tool_statuses": [{"tool_name": "request_container", "status": "ok", "reason": ""}],
            "grounding": {"tool_name": "request_container"},
            "direct_response": "Container-Anfrage wurde erfolgreich ausgefuehrt.",
            "metadata": {"bridge": "task_loop"},
        }
        return "Container-Anfrage wurde erfolgreich ausgefuehrt."

    orch._execute_tools_sync = MagicMock(side_effect=_execute_tools_sync)

    request = SimpleNamespace(
        model="test-model",
        conversation_id=conversation_id,
        raw_request={},
    )

    out = []
    async for item in stream_task_loop_events(
        orch,
        request,
        "weiter",
        conversation_id,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
        tone_signal=None,
    ):
        out.append(item)

    assert any(item[2].get("type") == "task_loop_update" for item in out)
    assert any(
        item[2].get("type") == "content"
        and "Container-Anfrage wurde erfolgreich ausgefuehrt." in item[0]
        for item in out
    )
    assert not any(
        item[2].get("type") == "content" and "Task-Loop gestartet." in item[0]
        for item in out
    )


@pytest.mark.asyncio
async def test_stream_task_loop_events_runtime_resumes_waiting_user_tool_step_with_user_reply():
    conversation_id = "conv-task-loop-stream-user-resume"
    get_task_loop_store().clear(conversation_id)
    snapshot = TaskLoopSnapshot(
        objective_id="obj-tool-user",
        conversation_id=conversation_id,
        plan_id="plan-tool-user",
        state=TaskLoopState.WAITING_FOR_USER,
        current_step_id="step-tool-user-1",
        current_step_type=TaskLoopStepType.TOOL_REQUEST,
        current_step_status=TaskLoopStepStatus.WAITING_FOR_USER,
        step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
        current_plan=[
            "Container-Anfrage zur Freigabe vorbereiten",
            "Container-Anfrage ausfuehren",
        ],
        plan_steps=[
            {
                "step_id": "step-tool-user-1",
                "title": "Container-Anfrage zur Freigabe vorbereiten",
                "goal": "Die Container-Anfrage sichtbar vorbereiten und offene Angaben sammeln.",
                "done_criteria": "Freigabe, Ziel und fehlende Angaben sind sichtbar vorbereitet.",
                "risk_level": "needs_confirmation",
                "requires_user": True,
                "suggested_tools": ["request_container"],
                "task_kind": "implementation",
                "objective": "Gaming-Container kontrolliert starten",
                "step_type": TaskLoopStepType.TOOL_REQUEST.value,
                "requested_capability": {
                    "capability_type": "container_manager",
                    "capability_target": "request_container",
                    "capability_action": "request_container",
                },
            },
            {
                "step_id": "step-tool-user-2",
                "title": "Container-Anfrage ausfuehren",
                "goal": "Die vorbereitete Container-Anfrage ausfuehren.",
                "done_criteria": "Ein verifizierter Tool-Befund liegt vor.",
                "risk_level": "safe",
                "requires_user": False,
                "suggested_tools": ["request_container"],
                "task_kind": "implementation",
                "objective": "Gaming-Container kontrolliert starten",
                "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
                "requested_capability": {
                    "capability_type": "container_manager",
                    "capability_target": "request_container",
                    "capability_action": "request_container",
                },
            }
        ],
        pending_step="Container-Anfrage zur Freigabe vorbereiten",
        last_step_result={
            "status": TaskLoopStepStatus.WAITING_FOR_USER.value,
            "step_type": TaskLoopStepType.TOOL_REQUEST.value,
            "step_execution_source": TaskLoopStepExecutionSource.ORCHESTRATOR.value,
        },
    )
    get_task_loop_store().put(snapshot)

    class _Control:
        async def verify(self, user_text, thinking_plan, retrieved_memory="", response_mode="interactive"):
            return {
                "approved": True,
                "decision_class": "allow",
                "warnings": [],
                "final_instruction": "",
            }

    class _Output:
        async def generate_stream(
            self,
            user_text,
            verified_plan,
            memory_data="",
            model=None,
            memory_required_but_missing=False,
            chat_history=None,
            control_decision=None,
            execution_result=None,
        ):
            yield "unused"

    orch = MagicMock()
    orch._save_workspace_entry = MagicMock(
        side_effect=lambda **kwargs: {
            "type": "workspace_update",
            "entry_id": kwargs["entry_type"],
            "content": kwargs["content"],
        }
    )
    orch.control = _Control()
    orch.output = _Output()
    orch.calls = []

    async def _collect_control_tool_decisions(user_text, verified_plan, *, control_decision=None, stream=False):
        orch.calls.append(("collect", user_text))
        return {"request_container": {"blueprint_id": "gaming-station"}}

    def _resolve_execution_suggested_tools(
        user_text,
        verified_plan,
        control_tool_decisions,
        *,
        control_decision=None,
        stream=False,
        enable_skill_trigger_router=False,
        conversation_id="",
        chat_history=None,
    ):
        orch.calls.append(("resolve", user_text))
        return [{"name": "request_container", "arguments": {"blueprint_id": "gaming-station"}}]

    def _execute_tools_sync(
        suggested_tools,
        user_text,
        control_tool_decisions=None,
        **kwargs,
    ):
        orch.calls.append(("execute", user_text))
        verified_plan = kwargs["verified_plan"]
        verified_plan["_execution_result"] = {
            "done_reason": "success",
            "tool_statuses": [{"tool_name": "request_container", "status": "ok", "reason": ""}],
            "grounding": {"tool_name": "request_container"},
            "direct_response": "Container-Anfrage mit User-Parametern wurde erfolgreich ausgefuehrt.",
            "metadata": {"bridge": "task_loop"},
        }
        return "Container-Anfrage mit User-Parametern wurde erfolgreich ausgefuehrt."

    orch._collect_control_tool_decisions = AsyncMock(side_effect=_collect_control_tool_decisions)
    orch._resolve_execution_suggested_tools = MagicMock(side_effect=_resolve_execution_suggested_tools)
    orch._execute_tools_sync = MagicMock(side_effect=_execute_tools_sync)

    request = SimpleNamespace(
        model="test-model",
        conversation_id=conversation_id,
        raw_request={},
    )

    out = []
    async for item in stream_task_loop_events(
        orch,
        request,
        "nimm bitte gaming-station",
        conversation_id,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
        tone_signal=None,
    ):
        out.append(item)

    assert any(item[2].get("type") == "task_loop_update" for item in out)
    assert any(
        item[2].get("type") == "content"
        and "Container-Anfrage mit User-Parametern wurde erfolgreich ausgefuehrt." in item[0]
        for item in out
    )
    assert not any(
        item[2].get("type") == "content" and "Task-Loop gestartet." in item[0]
        for item in out
    )
    assert any(call[0] == "execute" for call in orch.calls)
