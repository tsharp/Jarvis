from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.orchestrator_modules.task_loop import (
    ACTIVE_TASK_LOOP_REASON_CANCEL,
    ACTIVE_TASK_LOOP_REASON_CONTEXT_ONLY,
    ACTIVE_TASK_LOOP_REASON_CONTINUE,
    ACTIVE_TASK_LOOP_REASON_MODE_SHIFT,
    explain_active_task_loop_routing,
    classify_active_task_loop_routing,
    inject_active_task_loop_context,
    maybe_build_task_loop_stream_events,
    maybe_handle_task_loop_sync,
)
from core.orchestrator_modules.task_loop_routing import decide_task_loop_routing
from core.task_loop.contracts import (
    TaskLoopSnapshot,
    TaskLoopState,
    TaskLoopStepExecutionSource,
    TaskLoopStepStatus,
    TaskLoopStepType,
)
from core.task_loop.chat_runtime import start_chat_task_loop
from core.task_loop.store import TaskLoopStore


@pytest.mark.asyncio
async def test_maybe_handle_task_loop_sync_returns_none_for_normal_turn(monkeypatch):
    store = TaskLoopStore()

    monkeypatch.setattr(
        "core.orchestrator_modules.task_loop.get_task_loop_store",
        lambda: store,
    )

    out = await maybe_handle_task_loop_sync(
        SimpleNamespace(
            _save_workspace_entry=lambda **_kwargs: None,
            thinking=SimpleNamespace(analyze=AsyncMock(return_value={"intent": "unused"})),
        ),
        SimpleNamespace(model="m", raw_request={}),
        "was ist 2+2?",
        "conv-loop",
        core_chat_response_cls=lambda **kwargs: kwargs,
        log_info_fn=lambda _msg: None,
    )

    assert out is None


@pytest.mark.asyncio
async def test_maybe_handle_task_loop_sync_builds_response_for_candidate(monkeypatch):
    store = TaskLoopStore()

    monkeypatch.setattr(
        "core.orchestrator_modules.task_loop.get_task_loop_store",
        lambda: store,
    )

    logs = []
    out = await maybe_handle_task_loop_sync(
        SimpleNamespace(
            _save_workspace_entry=lambda **_kwargs: None,
            thinking=SimpleNamespace(
                analyze=AsyncMock(
                    return_value={
                        "intent": "Multistep Loop pruefen",
                        "hallucination_risk": "low",
                        "suggested_tools": [],
                        "reasoning": "Chat-only Test",
                    }
                )
            ),
        ),
        SimpleNamespace(model="m", raw_request={}),
        "Task-Loop: Bitte schrittweise bearbeiten",
        "conv-loop",
        core_chat_response_cls=lambda **kwargs: kwargs,
        log_info_fn=logs.append,
    )

    assert out["done_reason"] == "task_loop_completed"
    assert out["conversation_id"] == "conv-loop"
    assert "Pruefziel festlegen: Multistep Loop pruefen" in out["content"]
    assert "Pruefziel: Multistep Loop pruefen" in out["content"]
    assert "konkreten Befund statt nur eine Statusfloskel" in out["content"]
    assert logs


@pytest.mark.asyncio
async def test_maybe_handle_task_loop_sync_force_starts_from_authoritative_plan(monkeypatch):
    store = TaskLoopStore()

    monkeypatch.setattr(
        "core.orchestrator_modules.task_loop.get_task_loop_store",
        lambda: store,
    )

    out = await maybe_handle_task_loop_sync(
        SimpleNamespace(
            _save_workspace_entry=lambda **_kwargs: None,
            thinking=SimpleNamespace(analyze=AsyncMock(return_value={"intent": "unused"})),
        ),
        SimpleNamespace(model="m", raw_request={}),
        "Bitte pruefe den neuen Loop mit sichtbaren Zwischenstaenden",
        "conv-loop-force",
        core_chat_response_cls=lambda **kwargs: kwargs,
        log_info_fn=lambda _msg: None,
        thinking_plan={
            "intent": "Loop pruefen",
            "hallucination_risk": "low",
            "suggested_tools": [],
            "_authoritative_turn_mode": "task_loop",
        },
        force_start=True,
    )

    assert out is not None
    assert out["done_reason"] == "task_loop_completed"
    assert out["content"]  # has non-empty content


@pytest.mark.asyncio
async def test_maybe_build_task_loop_stream_events_emits_workspace_content_and_done(monkeypatch):
    store = TaskLoopStore()

    monkeypatch.setattr(
        "core.orchestrator_modules.task_loop.get_task_loop_store",
        lambda: store,
    )

    workspace_calls = []

    def save_workspace_entry(**kwargs):
        workspace_calls.append(kwargs)
        return {"type": "workspace_update", "entry_id": f"evt-{len(workspace_calls)}"}

    events = await maybe_build_task_loop_stream_events(
        SimpleNamespace(
            _save_workspace_entry=save_workspace_entry,
            thinking=SimpleNamespace(
                analyze=AsyncMock(
                    return_value={
                        "intent": "Stream Loop pruefen",
                        "hallucination_risk": "low",
                        "suggested_tools": [],
                    }
                )
            ),
        ),
        SimpleNamespace(model="m", raw_request={}),
        "Task-Loop: Bitte schrittweise bearbeiten",
        "conv-loop-stream",
        log_info_fn=lambda _msg: None,
    )

    assert events is not None
    assert events[0][2]["type"] == "task_loop_update"
    assert any(item[2].get("type") == "workspace_update" for item in events)
    assert any(item[2].get("type") == "content" and item[0] for item in events)
    assert events[-1][1] is True
    assert events[-1][2]["done_reason"] == "task_loop_completed"
    assert workspace_calls


def test_inject_active_task_loop_context_marks_continue_and_state():
    store = TaskLoopStore()
    started = start_chat_task_loop(
        "Task-Loop: Bitte schrittweise arbeiten",
        "conv-active",
        store=store,
        auto_continue=False,
    )

    plan = inject_active_task_loop_context(
        {"intent": "weiterfuehren"},
        started.snapshot,
        user_text="weiter",
        raw_request={},
    )

    assert plan["_task_loop_active"] is True
    assert plan["_task_loop_active_state"] == "waiting_for_user"
    assert plan["_task_loop_continue_requested"] is True
    assert plan["_task_loop_cancel_requested"] is False
    assert plan["_task_loop_runtime_resume_candidate"] is False
    assert plan["_task_loop_active_reason_detail"] == "background_loop_preserved"


def test_classify_active_task_loop_routing_returns_reason_codes():
    store = TaskLoopStore()
    started = start_chat_task_loop(
        "Task-Loop: Bitte schrittweise arbeiten",
        "conv-active",
        store=store,
        auto_continue=False,
    )

    assert (
        classify_active_task_loop_routing(
            "weiter",
            started.snapshot,
            {"_authoritative_turn_mode": "task_loop"},
            raw_request={},
        )
        == ACTIVE_TASK_LOOP_REASON_CONTINUE
    )
    assert (
        classify_active_task_loop_routing(
            "stoppen",
            started.snapshot,
            {"_authoritative_turn_mode": "single_turn"},
            raw_request={},
        )
        == ACTIVE_TASK_LOOP_REASON_CANCEL
    )
    assert (
        classify_active_task_loop_routing(
            "was ist 2+2?",
            started.snapshot,
            {"_authoritative_turn_mode": "single_turn"},
            raw_request={},
        )
        == ACTIVE_TASK_LOOP_REASON_CONTEXT_ONLY
    )


def test_classify_active_task_loop_routing_keeps_waiting_loop_for_independent_tool_turn():
    store = TaskLoopStore()
    started = start_chat_task_loop(
        "Task-Loop: Bitte schrittweise arbeiten",
        "conv-active-tool-turn",
        store=store,
        auto_continue=False,
    )

    assert (
        classify_active_task_loop_routing(
            "zeig mir die skills",
            started.snapshot,
            {
                "_authoritative_turn_mode": "task_loop",
                "suggested_tools": ["list_skills"],
                "requested_capability": {"capability_type": "skill_management"},
            },
            raw_request={},
        )
        == ACTIVE_TASK_LOOP_REASON_CONTEXT_ONLY
    )


def test_classify_active_task_loop_routing_uses_context_only_for_meta_turns():
    store = TaskLoopStore()
    started = start_chat_task_loop(
        "Task-Loop: Bitte schrittweise arbeiten",
        "conv-active-meta",
        store=store,
        auto_continue=False,
    )

    assert (
        classify_active_task_loop_routing(
            "was ist passiert?",
            started.snapshot,
            {"_authoritative_turn_mode": "task_loop"},
            raw_request={},
        )
        == ACTIVE_TASK_LOOP_REASON_CONTEXT_ONLY
    )

    explanation = explain_active_task_loop_routing(
        "was ist passiert?",
        started.snapshot,
        {"_authoritative_turn_mode": "single_turn"},
        raw_request={},
    )
    assert explanation["detail"] == "meta_turn_background_preserved"
    assert explanation["meta_turn"] is True


def test_explain_active_task_loop_routing_marks_independent_tool_turn_background_preserve():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-independent",
        conversation_id="conv-active-independent",
        plan_id="plan-independent",
        state=TaskLoopState.WAITING_FOR_USER,
        current_step_id="step-container-1",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_step_status=TaskLoopStepStatus.WAITING_FOR_USER,
        step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
        current_plan=["Blueprints pruefen", "Container auswaehlen"],
        plan_steps=[
            {
                "step_id": "step-container-1",
                "title": "Blueprints pruefen",
                "suggested_tools": ["blueprint_list"],
                "requested_capability": {"capability_type": "container_manager"},
            }
        ],
        pending_step="Blueprints pruefen",
    )

    explanation = explain_active_task_loop_routing(
        "zeig mir die skills",
        snapshot,
        {
            "_authoritative_turn_mode": "single_turn",
            "suggested_tools": ["list_skills"],
            "requested_capability": {"capability_type": "skill_management"},
        },
        raw_request={},
    )

    assert explanation["reason"] == ACTIVE_TASK_LOOP_REASON_CONTEXT_ONLY
    assert explanation["detail"] == "independent_tool_turn_background_preserved"
    assert explanation["independent_tool_turn"] is True


def test_explain_active_task_loop_routing_marks_runtime_resume_detail():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-tool",
        conversation_id="conv-runtime-resume",
        plan_id="plan-runtime-resume",
        state=TaskLoopState.WAITING_FOR_USER,
        current_step_id="step-tool-1",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_step_status=TaskLoopStepStatus.WAITING_FOR_USER,
        step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
        current_plan=["Daten holen", "Ergebnis zusammenfassen"],
        plan_steps=[
            {
                "step_id": "step-tool-1",
                "title": "Daten holen",
                "suggested_tools": ["blueprint_list"],
                "requested_capability": {"capability_type": "container_manager"},
            }
        ],
        pending_step="Daten holen",
    )

    explanation = explain_active_task_loop_routing(
        "python-sandbox bitte",
        snapshot,
        {"_authoritative_turn_mode": "task_loop"},
        raw_request={},
    )

    assert explanation["reason"] == ACTIVE_TASK_LOOP_REASON_CONTINUE
    assert explanation["detail"] == "runtime_resume_candidate"
    assert explanation["runtime_resume_candidate"] is True


def test_decide_task_loop_routing_uses_single_authority_for_new_loop_start():
    decision = decide_task_loop_routing(
        "Bitte plane und bearbeite die Aufgabe sichtbar in mehreren Schritten",
        None,
        {
            "_authoritative_execution_mode": "task_loop",
            "_authoritative_turn_mode": "task_loop",
            "task_loop_candidate": True,
        },
        raw_request={},
    )

    assert decision.execution_mode == "task_loop"
    assert decision.turn_mode == "task_loop"
    assert decision.is_authoritative_task_loop_turn is True
    assert decision.use_task_loop is True
    assert decision.force_start is True
    assert decision.branch == "authoritative_task_loop_start"


def test_decide_task_loop_routing_uses_turn_mode_only_as_compat_fallback():
    decision = decide_task_loop_routing(
        "weiter",
        None,
        {
            "_authoritative_turn_mode": "task_loop",
        },
        raw_request={},
    )

    assert decision.execution_mode == "task_loop"
    assert decision.authority_source == "turn_mode_compat"


def test_decide_task_loop_routing_exposes_detail_flags_for_background_preserve():
    store = TaskLoopStore()
    started = start_chat_task_loop(
        "Task-Loop: Bitte schrittweise arbeiten",
        "conv-routing-detail",
        store=store,
        auto_continue=False,
    )

    decision = decide_task_loop_routing(
        "was ist passiert?",
        started.snapshot,
        {"_authoritative_turn_mode": "single_turn"},
        raw_request={},
    )

    assert decision.context_only is True
    assert decision.active_task_loop_reason == ACTIVE_TASK_LOOP_REASON_CONTEXT_ONLY
    assert decision.active_task_loop_detail == "meta_turn_background_preserved"
    assert decision.background_preservable is True
    assert decision.meta_turn is True


@pytest.mark.asyncio
async def test_maybe_handle_task_loop_sync_resumes_waiting_approval_tool_step(monkeypatch):
    store = TaskLoopStore()
    snapshot = TaskLoopSnapshot(
        objective_id="obj-tool",
        conversation_id="conv-tool-resume",
        plan_id="plan-tool-resume",
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
    store.put(snapshot)

    monkeypatch.setattr(
        "core.orchestrator_modules.task_loop.get_task_loop_store",
        lambda: store,
    )

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

    class _Orch:
        def __init__(self) -> None:
            self._save_workspace_entry = lambda **_kwargs: None
            self.control = _Control()
            self.output = _Output()
            self.calls = []

        async def _collect_control_tool_decisions(self, user_text, verified_plan, *, control_decision=None, stream=False):
            return {"request_container": {"blueprint_id": "gaming-station"}}

        def _resolve_execution_suggested_tools(
            self,
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
            return [{"name": "request_container", "arguments": {"blueprint_id": "gaming-station"}}]

        def _execute_tools_sync(
            self,
            suggested_tools,
            user_text,
            control_tool_decisions=None,
            *,
            last_assistant_msg="",
            control_decision=None,
            time_reference=None,
            thinking_suggested_tools=None,
            blueprint_gate_blocked=False,
            blueprint_router_id=None,
            blueprint_suggest_msg="",
            session_id="",
            verified_plan=None,
        ):
            self.calls.append((suggested_tools, user_text, session_id))
            verified_plan["_execution_result"] = {
                "done_reason": "success",
                "tool_statuses": [{"tool_name": "request_container", "status": "ok", "reason": ""}],
                "grounding": {"tool_name": "request_container"},
                "direct_response": "Container-Anfrage wurde erfolgreich ausgefuehrt.",
                "metadata": {"bridge": "task_loop"},
            }
            return "Container-Anfrage wurde erfolgreich ausgefuehrt."

    orch = _Orch()
    out = await maybe_handle_task_loop_sync(
        orch,
        SimpleNamespace(model="m", raw_request={}),
        "weiter",
        "conv-tool-resume",
        core_chat_response_cls=lambda **kwargs: kwargs,
        log_info_fn=lambda _msg: None,
    )

    assert out is not None
    assert out["done_reason"] == "task_loop_completed"
    assert "Container-Anfrage wurde erfolgreich ausgefuehrt." in out["content"]
    assert orch.calls


@pytest.mark.asyncio
async def test_maybe_handle_task_loop_sync_resumes_waiting_user_tool_step_with_user_reply(monkeypatch):
    store = TaskLoopStore()
    snapshot = TaskLoopSnapshot(
        objective_id="obj-tool-user",
        conversation_id="conv-tool-user-resume",
        plan_id="plan-tool-user-resume",
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
                "objective": "Den richtigen Gaming-Container kontrolliert starten",
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
                "objective": "Den richtigen Gaming-Container kontrolliert starten",
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
    store.put(snapshot)

    monkeypatch.setattr(
        "core.orchestrator_modules.task_loop.get_task_loop_store",
        lambda: store,
    )

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

    class _Orch:
        def __init__(self) -> None:
            self._save_workspace_entry = lambda **_kwargs: None
            self.control = _Control()
            self.output = _Output()
            self.calls = []

        async def _collect_control_tool_decisions(self, user_text, verified_plan, *, control_decision=None, stream=False):
            self.calls.append(("collect", user_text))
            return {"request_container": {"blueprint_id": "gaming-station"}}

        def _resolve_execution_suggested_tools(
            self,
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
            self.calls.append(("resolve", user_text))
            return [{"name": "request_container", "arguments": {"blueprint_id": "gaming-station"}}]

        def _execute_tools_sync(
            self,
            suggested_tools,
            user_text,
            control_tool_decisions=None,
            *,
            last_assistant_msg="",
            control_decision=None,
            time_reference=None,
            thinking_suggested_tools=None,
            blueprint_gate_blocked=False,
            blueprint_router_id=None,
            blueprint_suggest_msg="",
            session_id="",
            verified_plan=None,
        ):
            self.calls.append(("execute", user_text))
            verified_plan["_execution_result"] = {
                "done_reason": "success",
                "tool_statuses": [{"tool_name": "request_container", "status": "ok", "reason": ""}],
                "grounding": {"tool_name": "request_container"},
                "direct_response": "Container-Anfrage mit User-Parametern wurde erfolgreich ausgefuehrt.",
                "metadata": {"bridge": "task_loop"},
            }
            return "Container-Anfrage mit User-Parametern wurde erfolgreich ausgefuehrt."

    orch = _Orch()
    out = await maybe_handle_task_loop_sync(
        orch,
        SimpleNamespace(model="m", raw_request={}),
        "nimm bitte gaming-station",
        "conv-tool-user-resume",
        core_chat_response_cls=lambda **kwargs: kwargs,
        log_info_fn=lambda _msg: None,
    )

    assert out is not None
    assert out["done_reason"] == "task_loop_completed"
    assert "Container-Anfrage mit User-Parametern wurde erfolgreich ausgefuehrt." in out["content"]
    assert any("nimm bitte gaming-station" in call[1] for call in orch.calls)
