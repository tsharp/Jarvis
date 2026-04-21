import pytest

from core.control_contract import ControlDecision
from core.task_loop.contracts import RiskLevel, TaskLoopSnapshot, TaskLoopState, TaskLoopStepType
from core.task_loop.events import TaskLoopEventType, make_task_loop_event
from core.task_loop.planner import build_task_loop_steps, create_task_loop_snapshot_from_plan
from core.task_loop.runner import run_chat_auto_loop, run_chat_auto_loop_async, stream_chat_auto_loop
from core.task_loop.step_runtime.execution import TaskLoopStepRuntimeResult
from core.task_loop.contracts import TaskLoopStepExecutionSource, TaskLoopStepResult, TaskLoopStepStatus


def test_run_chat_auto_loop_completes_four_safe_steps():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        current_plan=["one", "two", "three", "four"],
        pending_step="one",
    )
    events = [make_task_loop_event(TaskLoopEventType.STARTED, snapshot)]

    result = run_chat_auto_loop(snapshot, initial_events=events, max_steps=4)

    assert result.done_reason == "task_loop_completed"
    assert result.snapshot.state.value == "completed"
    assert result.snapshot.step_index == 4
    assert result.content.count("[erledigt]") == 4
    assert [event["type"] for event in result.events].count("task_loop_reflection") == 4


def test_run_chat_auto_loop_stops_when_max_steps_reached_with_pending_step():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        current_plan=["one", "two", "three"],
        pending_step="one",
    )

    result = run_chat_auto_loop(snapshot, max_steps=2)

    assert result.done_reason == "task_loop_max_steps_reached"
    assert result.snapshot.state.value == "waiting_for_user"
    assert result.snapshot.stop_reason.value == "max_steps_reached"
    assert "max_steps" in result.content


def test_run_chat_auto_loop_uses_product_answers_for_validation_steps():
    snapshot = create_task_loop_snapshot_from_plan(
        "Bitte schrittweise arbeiten: Pruefe kurz den neuen Multistep Loop",
        "conv-1",
        thinking_plan={
            "intent": "unknown",
            "reasoning": "Fallback - Analyse fehlgeschlagen",
            "suggested_tools": [],
        },
    )

    result = run_chat_auto_loop(snapshot, max_steps=4)

    assert "Pruefziel: Pruefe kurz den neuen Multistep Loop" in result.content
    assert "Beobachtbare Kriterien:" in result.content
    assert "Befund: Der aktuelle Pfad bleibt sicher" in result.content
    assert "Ziel:" not in result.content
    assert "Erfuellt:" not in result.content
    assert "Fallback - Analyse fehlgeschlagen" not in result.content


def test_internal_loop_analysis_prompt_does_not_risk_gate_task_loop_from_raw_runtime_tool_drift():
    snapshot = create_task_loop_snapshot_from_plan(
        "Task-Loop: Pruefe kurz den neuen Multistep Loop und zeige mir sichere Zwischenstaende",
        "conv-1",
        thinking_plan={
            "intent": "Aktuellen Status des neuen Multistep Loop-Prozesses abfragen und sichere Zwischenstaende pruefen",
            "needs_memory": True,
            "memory_keys": [
                "multistep_loop_status",
                "current_iteration",
                "last_checkpoint",
                "loop_progress",
            ],
            "resolution_strategy": "active_container_capability",
            "strategy_hints": ["loop_validation", "intermediate_checkpoints", "runtime_state"],
            "suggested_tools": ["container_inspect", "exec_in_container", "container_logs"],
            "hallucination_risk": "medium",
            "needs_sequential_thinking": True,
            "sequential_complexity": 8,
        },
    )

    result = run_chat_auto_loop(snapshot, max_steps=4)

    assert result.done_reason == "task_loop_completed"
    assert result.snapshot.state.value == "completed"
    assert result.snapshot.stop_reason is None
    assert "Task-Loop pausiert." not in result.content
    assert "Stopgrund: risk_gate_required" not in result.content


@pytest.mark.asyncio
async def test_stream_chat_auto_loop_yields_plan_header_then_step_deltas():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        current_plan=["one", "two"],
        pending_step="one",
    )
    initial_events = [make_task_loop_event(TaskLoopEventType.STARTED, snapshot)]

    chunks = [
        chunk
        async for chunk in stream_chat_auto_loop(
            snapshot,
            initial_events=initial_events,
            max_steps=4,
        )
    ]

    assert chunks[0].content_delta == ""  # header removed; first chunk is empty placeholder
    assert chunks[0].events == initial_events
    assert chunks[0].is_final is False
    assert "one" in chunks[1].content_delta  # first step answer contains step title
    assert chunks[1].content_delta != chunks[0].snapshot.last_user_visible_answer
    assert chunks[-1].is_final is True
    assert chunks[-1].done_reason == "task_loop_completed"
    assert "Finaler Planstatus:" in chunks[-1].content_delta


@pytest.mark.asyncio
async def test_stream_chat_auto_loop_uses_control_and_output_runtime_when_provided():
    class _Control:
        def __init__(self) -> None:
            self.calls = []

        async def verify(self, user_text, thinking_plan, retrieved_memory="", response_mode="interactive"):
            self.calls.append((user_text, thinking_plan, retrieved_memory, response_mode))
            return {
                "approved": True,
                "decision_class": "allow",
                "warnings": [],
                "final_instruction": "Bleibe konkret und kurz.",
            }

    class _Output:
        def __init__(self) -> None:
            self.calls = []

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
            self.calls.append((user_text, verified_plan, memory_data, control_decision))
            yield "Konkreter Befund fuer diesen Schritt."

    snapshot = create_task_loop_snapshot_from_plan(
        "Task-Loop: Pruefe kurz den neuen Multistep Loop und zeige mir sichere Zwischenstaende",
        "conv-1",
        thinking_plan={
            "intent": "Multistep Loop pruefen",
            "hallucination_risk": "low",
            "suggested_tools": [],
        },
    )
    control = _Control()
    output = _Output()

    chunks = [
        chunk
        async for chunk in stream_chat_auto_loop(
            snapshot,
            initial_events=[make_task_loop_event(TaskLoopEventType.STARTED, snapshot)],
            control_layer=control,
            output_layer=output,
        )
    ]

    assert control.calls
    assert output.calls
    output_prompt, step_plan, _, control_decision = output.calls[0]
    assert "Task-Loop Schritt 1/" in output_prompt
    assert step_plan.get("_loop_trace_mode") == "internal_loop_analysis"
    assert step_plan.get("_task_loop_step_runtime") is True
    assert step_plan.get("_task_loop_disable_output_budget") is True
    assert "_output_time_budget_s" not in step_plan
    assert step_plan.get("needs_memory") is False
    assert step_plan.get("suggested_tools") is None
    assert step_plan.get("response_length_hint") == "short"
    assert control_decision is not None
    streamed_contents = [chunk.content_delta for chunk in chunks if chunk.content_delta]
    assert any(
        "Konkreter Befund fuer diesen Schritt." in content for content in streamed_contents
    )
    assert all("Pruefziel:" not in content for content in streamed_contents)


@pytest.mark.asyncio
async def test_stream_chat_auto_loop_exposes_step_runtime_fallback_diagnostics():
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
            raise RuntimeError("boom")
            yield ""

    snapshot = create_task_loop_snapshot_from_plan(
        "Task-Loop: Analysiere kurz warum der Multistep Loop jetzt besser funktioniert",
        "conv-1",
        thinking_plan={
            "intent": "Analyse des Grundes, warum der Multistep Loop jetzt besser funktioniert",
            "hallucination_risk": "low",
            "suggested_tools": [],
        },
    )

    chunks = [
        chunk
        async for chunk in stream_chat_auto_loop(
            snapshot,
            initial_events=[make_task_loop_event(TaskLoopEventType.STARTED, snapshot)],
            control_layer=_Control(),
            output_layer=_Output(),
        )
    ]

    runtime_updates = [chunk.step_runtime or {} for chunk in chunks if chunk.step_runtime]
    assert runtime_updates
    assert any(update.get("used_fallback") is True for update in runtime_updates)
    assert any("stream_exception:RuntimeError:boom" in str(update.get("fallback_reason") or "") for update in runtime_updates)


@pytest.mark.asyncio
async def test_stream_chat_auto_loop_executes_tool_step_via_orchestrator_bridge():
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
            yield "Analyse-Zwischenstand."

    class _Orchestrator:
        def __init__(self) -> None:
            self.collect_calls = []
            self.resolve_calls = []
            self.execute_calls = []

        async def _collect_control_tool_decisions(
            self,
            user_text,
            verified_plan,
            *,
            control_decision=None,
            stream=False,
        ):
            self.collect_calls.append((user_text, verified_plan, control_decision, stream))
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
            self.resolve_calls.append((user_text, verified_plan, control_tool_decisions, conversation_id))
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
            self.execute_calls.append((suggested_tools, user_text, control_tool_decisions, session_id))
            verified_plan["_execution_result"] = {
                "done_reason": "success",
                "tool_statuses": [{"tool_name": "request_container", "status": "ok", "reason": ""}],
                "grounding": {"tool_name": "request_container"},
                "direct_response": "Container-Anfrage wurde erfolgreich ausgefuehrt.",
                "metadata": {"bridge": "task_loop"},
            }
            return "Container-Anfrage wurde erfolgreich ausgefuehrt."

    snapshot = TaskLoopSnapshot(
        objective_id="obj-tool",
        conversation_id="conv-1",
        plan_id="plan-tool",
        current_step_id="step-tool-1",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_plan=["Container kontrolliert anfragen"],
        plan_steps=[
            {
                "step_id": "step-tool-1",
                "title": "Container kontrolliert anfragen",
                "goal": "Den passenden Container kontrolliert ueber den Orchestrator anfragen.",
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
        pending_step="Container kontrolliert anfragen",
    )

    chunks = [
        chunk
        async for chunk in stream_chat_auto_loop(
            snapshot,
            initial_events=[make_task_loop_event(TaskLoopEventType.STARTED, snapshot)],
            control_layer=_Control(),
            output_layer=_Output(),
            orchestrator_bridge=_Orchestrator(),
        )
    ]

    runtime_updates = [chunk.step_runtime or {} for chunk in chunks if chunk.step_runtime]
    assert any(update.get("step_execution_source") == "orchestrator" for update in runtime_updates)
    assert any("Container-Anfrage wurde erfolgreich ausgefuehrt." in chunk.content_delta for chunk in chunks)


@pytest.mark.asyncio
async def test_stream_chat_auto_loop_failed_tool_step_enters_waiting_for_user_retry_path():
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
            yield "Analyse-Zwischenstand."

    class _Orchestrator:
        async def _collect_control_tool_decisions(
            self,
            user_text,
            verified_plan,
            *,
            control_decision=None,
            stream=False,
        ):
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
            verified_plan["_execution_result"] = {
                "done_reason": "tech_fail",
                "tool_statuses": [{"tool_name": "request_container", "status": "error", "reason": "daemon offline"}],
                "grounding": {"tool_name": "request_container"},
                "direct_response": "Container-Anfrage konnte gerade nicht ausgefuehrt werden.",
                "metadata": {"bridge": "task_loop"},
            }
            return "Container-Anfrage konnte gerade nicht ausgefuehrt werden."

    snapshot = TaskLoopSnapshot(
        objective_id="obj-tool-fail",
        conversation_id="conv-fail",
        plan_id="plan-tool-fail",
        current_step_id="step-tool-1",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_plan=["Container-Anfrage ausfuehren"],
        plan_steps=[
            {
                "step_id": "step-tool-1",
                "title": "Container-Anfrage ausfuehren",
                "goal": "Die Container-Anfrage kontrolliert ausfuehren.",
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
        pending_step="Container-Anfrage ausfuehren",
    )

    chunks = [
        chunk
        async for chunk in stream_chat_auto_loop(
            snapshot,
            initial_events=[make_task_loop_event(TaskLoopEventType.STARTED, snapshot)],
            control_layer=_Control(),
            output_layer=_Output(),
            orchestrator_bridge=_Orchestrator(),
        )
    ]

    final_chunk = chunks[-1]
    assert final_chunk.is_final is True
    assert final_chunk.done_reason == "task_loop_user_decision_required"
    assert final_chunk.snapshot.state.value == "waiting_for_user"
    assert final_chunk.snapshot.current_step_status.value == "waiting_for_user"
    assert final_chunk.snapshot.last_step_result.get("status") == "failed"
    assert "erneut versuchen" in final_chunk.content_delta


@pytest.mark.asyncio
async def test_stream_chat_auto_loop_collection_step_runs_autonomously():
    """Collection steps no longer pause — the AI fills gaps with sensible defaults."""
    class _Control:
        async def verify(self, user_text, thinking_plan, retrieved_memory="", response_mode="interactive"):
            return {"approved": True, "decision_class": "allow", "warnings": [], "final_instruction": ""}

    class _Output:
        async def generate_stream(self, user_text, verified_plan, memory_data="", model=None,
                                   memory_required_but_missing=False, chat_history=None,
                                   control_decision=None, execution_result=None):
            yield "Keine spezifischen Angaben vorhanden — verwende python:3.11-slim als sicheren Default."

    snapshot = create_task_loop_snapshot_from_plan(
        "Bitte schrittweise arbeiten: Starte einen Container",
        "conv-coll",
        thinking_plan={
            "intent": "Container starten",
            "hallucination_risk": "low",
            "suggested_tools": ["request_container"],
        },
    )
    from dataclasses import replace
    collection_step = snapshot.current_plan[1]
    snapshot = replace(
        snapshot,
        pending_step=collection_step,
        completed_steps=[snapshot.current_plan[0]],
        step_index=1,
    )

    chunks = [
        chunk
        async for chunk in stream_chat_auto_loop(
            snapshot,
            max_steps=4,
            control_layer=_Control(),
            output_layer=_Output(),
        )
    ]

    # Collection step must complete, not pause
    final_chunk = chunks[-1]
    assert final_chunk.is_final is True
    assert final_chunk.done_reason != "task_loop_user_decision_required"
    statuses = [
        (chunk.snapshot.current_step_status.value if chunk.snapshot else None)
        for chunk in chunks
    ]
    assert "waiting_for_user" not in statuses


@pytest.mark.asyncio
async def test_run_chat_auto_loop_async_replans_request_container_into_blueprint_discovery_before_retry():
    class _Control:
        async def verify(self, user_text, thinking_plan, retrieved_memory="", response_mode="interactive"):
            return {
                "approved": True,
                "decision_class": "allow",
                "warnings": [],
                "final_instruction": "",
            }

    class _Orchestrator:
        def __init__(self) -> None:
            self.calls = []
            self.request_container_calls = 0

        async def _collect_control_tool_decisions(self, user_text, verified_plan, *, control_decision=None, stream=False):
            return {}

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
            tools = list(verified_plan.get("suggested_tools") or [])
            if "blueprint_list" in tools:
                return [{"name": "blueprint_list", "arguments": {}}]
            return [{"name": "request_container", "arguments": {}}]

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
            tool_name = str((suggested_tools or [{}])[0].get("name") or "")
            self.calls.append(tool_name)
            if tool_name == "request_container":
                self.request_container_calls += 1
                if self.request_container_calls == 1:
                    verified_plan["_execution_result"] = {
                        "done_reason": "routing_block",
                        "tool_statuses": [
                            {"tool_name": "request_container", "status": "routing_block", "reason": "no_jit_match"}
                        ],
                        "grounding": {},
                        "direct_response": "",
                        "metadata": {},
                    }
                    return ""
                verified_plan["_execution_result"] = {
                    "done_reason": "success",
                    "tool_statuses": [
                        {"tool_name": "request_container", "status": "ok", "reason": ""}
                    ],
                    "grounding": {"tool_name": "request_container"},
                    "direct_response": "Container-Anfrage erfolgreich ausgefuehrt.",
                    "metadata": {},
                }
                return "Container-Anfrage erfolgreich ausgefuehrt."

            verified_plan["_execution_result"] = {
                "done_reason": "success",
                "tool_statuses": [
                    {"tool_name": "blueprint_list", "status": "ok", "reason": ""}
                ],
                "grounding": {"tool_name": "blueprint_list"},
                "direct_response": "Blueprints geprueft.",
                "metadata": {
                    "grounding_evidence": [
                        {
                            "tool_name": "blueprint_list",
                            "status": "ok",
                            "structured": {
                                "blueprints": [
                                    {"blueprint_id": "py-data", "name": "Python Data"}
                                ]
                            },
                        }
                    ]
                },
            }
            return "Blueprints geprueft."

    steps = build_task_loop_steps(
        "Bitte plane und bearbeite die folgende Aufgabe sichtbar in mehreren Schritten: "
        "Pruefe, wie du einen python-Container anfordern wuerdest.",
        thinking_plan={
            "intent": "Python-Container kontrolliert anfordern",
            "hallucination_risk": "low",
            "suggested_tools": ["request_container"],
            "_container_capability_context": {
                "request_family": "python_container",
                "python_requested": True,
                "known_fields": {
                    "blueprint": "py-data",
                    "python_version": "3.11",
                    "dependency_spec": "requirements.txt",
                    "build_or_runtime": "runtime",
                },
            },
        },
    )
    execute_step = steps[3]
    snapshot = TaskLoopSnapshot(
        objective_id="obj-container-recovery",
        conversation_id="conv-container-recovery",
        plan_id="plan-container-recovery",
        state=TaskLoopState.PLANNING,
        step_index=3,
        current_step_id=execute_step.step_id,
        current_step_type=execute_step.step_type,
        current_plan=[step.title for step in steps],
        plan_steps=[step.to_dict() for step in steps],
        completed_steps=[step.title for step in steps[:3]],
        pending_step=execute_step.title,
        risk_level=RiskLevel.SAFE,
        verified_artifacts=[],
    )

    orch = _Orchestrator()
    result = await run_chat_auto_loop_async(
        snapshot,
        max_steps=6,
        control_layer=_Control(),
        output_layer=None,
        orchestrator_bridge=orch,
    )

    assert orch.calls[:3] == ["request_container", "blueprint_list", "request_container"]
    assert "Verfuegbare Blueprints oder Container-Basis pruefen" in result.snapshot.current_plan
    assert result.snapshot.completed_steps.count("Container-Anfrage ausfuehren") == 1
    assert result.snapshot.state.value in {"completed", "waiting_for_user"}


@pytest.mark.asyncio
async def test_run_chat_auto_loop_async_replans_request_container_into_container_list_before_retry():
    class _Control:
        async def verify(self, user_text, thinking_plan, retrieved_memory="", response_mode="interactive"):
            return {
                "approved": True,
                "decision_class": "allow",
                "warnings": [],
                "final_instruction": "",
            }

    class _Orchestrator:
        def __init__(self) -> None:
            self.calls = []
            self.request_container_calls = 0

        async def _collect_control_tool_decisions(self, user_text, verified_plan, *, control_decision=None, stream=False):
            return {}

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
            tools = list(verified_plan.get("suggested_tools") or [])
            if "container_list" in tools:
                return [{"name": "container_list", "arguments": {}}]
            return [{"name": "request_container", "arguments": {}}]

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
            tool_name = str((suggested_tools or [{}])[0].get("name") or "")
            self.calls.append(tool_name)
            if tool_name == "request_container":
                self.request_container_calls += 1
                if self.request_container_calls == 1:
                    verified_plan["_execution_result"] = {
                        "done_reason": "routing_block",
                        "tool_statuses": [
                            {
                                "tool_name": "request_container",
                                "status": "routing_block",
                                "reason": "missing_container_id:auto_resolve_failed",
                            }
                        ],
                        "grounding": {},
                        "direct_response": "",
                        "metadata": {},
                    }
                    return ""
                verified_plan["_execution_result"] = {
                    "done_reason": "success",
                    "tool_statuses": [
                        {"tool_name": "request_container", "status": "ok", "reason": ""}
                    ],
                    "grounding": {"tool_name": "request_container"},
                    "direct_response": "Container-Anfrage erfolgreich ausgefuehrt.",
                    "metadata": {},
                }
                return "Container-Anfrage erfolgreich ausgefuehrt."

            verified_plan["_execution_result"] = {
                "done_reason": "success",
                "tool_statuses": [
                    {"tool_name": "container_list", "status": "ok", "reason": ""}
                ],
                "grounding": {"tool_name": "container_list"},
                "direct_response": "Container-Inventar geprueft.",
                "metadata": {},
            }
            return "Container-Inventar geprueft."

    steps = build_task_loop_steps(
        "Bitte nutze einen bestehenden Container, wenn bereits einer passend laeuft, "
        "und fordere sonst kontrolliert einen neuen an.",
        thinking_plan={
            "intent": "Bestehenden Container bevorzugen oder kontrolliert neuen anfordern",
            "hallucination_risk": "low",
            "suggested_tools": ["request_container"],
            "_container_capability_context": {
                "request_family": "generic_container",
                "python_requested": False,
                "known_fields": {},
            },
        },
    )
    execute_step = steps[3]
    snapshot = TaskLoopSnapshot(
        objective_id="obj-container-runtime-recovery",
        conversation_id="conv-container-runtime-recovery",
        plan_id="plan-container-runtime-recovery",
        state=TaskLoopState.PLANNING,
        step_index=3,
        current_step_id=execute_step.step_id,
        current_step_type=execute_step.step_type,
        current_plan=[step.title for step in steps],
        plan_steps=[step.to_dict() for step in steps],
        completed_steps=[step.title for step in steps[:3]],
        pending_step=execute_step.title,
        risk_level=RiskLevel.SAFE,
        verified_artifacts=[],
    )

    orch = _Orchestrator()
    result = await run_chat_auto_loop_async(
        snapshot,
        max_steps=6,
        control_layer=_Control(),
        output_layer=None,
        orchestrator_bridge=orch,
    )

    assert orch.calls[:3] == ["request_container", "container_list", "request_container"]
    assert "Laufende oder vorhandene Container pruefen" in result.snapshot.current_plan
    assert result.snapshot.completed_steps.count("Container-Anfrage ausfuehren") == 1
    assert result.snapshot.state.value in {"completed", "waiting_for_user"}


@pytest.mark.asyncio
async def test_run_chat_auto_loop_async_inserts_verification_step_before_completion_for_weak_tool_evidence(
    monkeypatch,
):
    verify_step = "Ergebnis verifizieren und Abschluss absichern"

    async def _fake_execute_task_loop_step(
        completed_step,
        step_meta,
        snapshot,
        *,
        control_layer=None,
        output_layer=None,
        orchestrator_bridge=None,
        resume_user_text="",
        fallback_fn=None,
    ):
        if completed_step == "Container-Aktion ausführen":
            step_result = TaskLoopStepResult(
                turn_id="turn-1",
                loop_id="loop-1",
                step_id="step-1",
                step_type=TaskLoopStepType.TOOL_EXECUTION,
                status=TaskLoopStepStatus.COMPLETED,
                control_decision={},
                execution_result={},
                verified_artifacts=[],
                user_visible_summary="Container-Aktion ausgeführt.",
                next_action="analyze_artifacts",
                trace_reason="test_tool_execution",
                step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
            )
            return TaskLoopStepRuntimeResult(
                visible_text="Container-Aktion ausgeführt.",
                control_decision=ControlDecision.from_verification({"approved": True}),
                verified_plan={},
                step_result=step_result,
                used_fallback=False,
            )

        assert completed_step == verify_step
        step_result = TaskLoopStepResult(
            turn_id="turn-1",
            loop_id="loop-1",
            step_id="step-2",
            step_type=TaskLoopStepType.ANALYSIS,
            status=TaskLoopStepStatus.COMPLETED,
            control_decision={},
            execution_result={},
            verified_artifacts=[],
            user_visible_summary="Ergebnis verifiziert.",
            next_action="analyze_artifacts",
            trace_reason="test_verify_step",
            step_execution_source=TaskLoopStepExecutionSource.LOOP,
        )
        return TaskLoopStepRuntimeResult(
            visible_text="Ergebnis verifiziert.",
            control_decision=ControlDecision.from_verification({"approved": True}),
            verified_plan={},
            step_result=step_result,
            used_fallback=False,
        )

    monkeypatch.setattr(
        "core.task_loop.runner.chat_async.execute_task_loop_step",
        _fake_execute_task_loop_step,
    )

    snapshot = TaskLoopSnapshot(
        objective_id="obj-verify",
        conversation_id="conv-verify",
        plan_id="plan-verify",
        current_plan=["Container-Aktion ausführen"],
        plan_steps=[
            {
                "title": "Container-Aktion ausführen",
                "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
                "risk_level": RiskLevel.SAFE.value,
                "step_id": "step-1",
            }
        ],
        pending_step="Container-Aktion ausführen",
    )

    result = await run_chat_auto_loop_async(snapshot, max_steps=6)

    assert result.done_reason == "task_loop_completed"
    assert result.snapshot.state.value == "completed"
    assert verify_step in result.snapshot.current_plan
    assert verify_step in result.snapshot.completed_steps
    assert "Ich prüfe das Ergebnis noch kurz gegen belastbare Hinweise" in result.content
