from core.task_loop.contracts import (
    RiskLevel,
    TaskLoopSnapshot,
    TaskLoopState,
    TaskLoopStepExecutionSource,
    TaskLoopStepStatus,
    TaskLoopStepType,
)
from core.work_context.contracts import WorkContextStatus
from core.work_context.readers.task_loop import build_work_context_from_task_loop_snapshot


def _make_terminal_snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        state=TaskLoopState.COMPLETED,
        step_index=5,
        current_step_id="step-5",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_step_status=TaskLoopStepStatus.COMPLETED,
        step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
        current_plan=[
            "Ziel klaeren",
            "Blueprints pruefen",
            "Container starten",
        ],
        completed_steps=[
            "Ziel klaeren",
            "Blueprints pruefen",
            "Container starten",
        ],
        pending_step="",
        last_user_visible_answer="Container-Anfrage blockiert.",
        risk_level=RiskLevel.SAFE,
        objective_summary="Python-Entwicklungscontainer starten",
        verified_artifacts=[
            {
                "artifact_type": "container_capability_context",
                "context": {
                    "request_family": "python_container",
                    "python_requested": True,
                    "known_fields": {"python_version": "3.11"},
                },
            },
            {
                "artifact_type": "execution_result",
                "metadata": {
                    "grounding_evidence": [
                        {
                            "tool_name": "blueprint_list",
                            "structured": {
                                "blueprints": [
                                    {
                                        "id": "db-sandbox",
                                        "name": "Database Sandbox",
                                        "description": "SQLite/PostgreSQL",
                                    },
                                    {
                                        "id": "python-sandbox",
                                        "name": "Python Sandbox",
                                        "description": "Python 3.11 Runtime",
                                    },
                                ]
                            },
                        }
                    ]
                },
            },
            {
                "artifact_type": "container_recovery_hint",
                "replan_step_title": "Verfuegbare Blueprints oder Container-Basis pruefen",
                "next_tools": ["blueprint_list"],
            },
        ],
        last_step_result={
            "execution_result": {
                "done_reason": "routing_block",
                "tool_statuses": [
                    {
                        "tool_name": "request_container",
                        "status": "routing_block",
                        "reason": "no_jit_match",
                    }
                ],
            }
        },
        workspace_event_ids=["evt-1", "evt-2"],
    )


def _make_active_snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        objective_id="obj-2",
        conversation_id="conv-2",
        plan_id="plan-2",
        state=TaskLoopState.WAITING_FOR_USER,
        step_index=2,
        current_step_id="step-2",
        current_step_type=TaskLoopStepType.TOOL_REQUEST,
        current_step_status=TaskLoopStepStatus.WAITING_FOR_USER,
        step_execution_source=TaskLoopStepExecutionSource.LOOP,
        current_plan=["Ziel klaeren", "Rueckfrage beantworten", "Container starten"],
        completed_steps=["Ziel klaeren"],
        pending_step="Rueckfrage beantworten",
        objective_summary="Container-Auswahl abschliessen",
        workspace_event_ids=["evt-1"],
    )


def test_task_loop_reader_maps_terminal_snapshot_to_work_context():
    ctx = build_work_context_from_task_loop_snapshot(_make_terminal_snapshot())

    assert ctx is not None
    assert ctx.conversation_id == "conv-1"
    assert ctx.topic == "Python-Entwicklungscontainer starten"
    assert ctx.status == WorkContextStatus.COMPLETED
    assert ctx.last_step == "Container starten"
    assert ctx.next_step == "Verfuegbare Blueprints oder Container-Basis pruefen"
    assert ctx.blocker == "request_container:no_jit_match"
    assert dict(ctx.capability_context)["request_family"] == "python_container"
    assert "selected_blueprint" in ctx.missing_facts
    assert "block_reason" in ctx.missing_facts
    assert any(fact.key == "discovered_blueprints" for fact in ctx.verified_facts)
    assert ctx.metadata["workspace_event_count"] == 2


def test_task_loop_reader_maps_active_snapshot_to_waiting_work_context():
    ctx = build_work_context_from_task_loop_snapshot(_make_active_snapshot())

    assert ctx is not None
    assert ctx.conversation_id == "conv-2"
    assert ctx.topic == "Container-Auswahl abschliessen"
    assert ctx.status == WorkContextStatus.WAITING
    assert ctx.last_step == "Ziel klaeren"
    assert ctx.next_step == "Rueckfrage beantworten"
    assert ctx.blocker == ""
    assert ctx.verified_facts == tuple()
    assert ctx.missing_facts == tuple()
    assert ctx.metadata["task_loop_state"] == "waiting_for_user"


def test_task_loop_reader_returns_none_for_missing_snapshot():
    assert build_work_context_from_task_loop_snapshot(None) is None
