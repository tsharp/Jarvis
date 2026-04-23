from core.task_loop.contracts import (
    TaskLoopSnapshot,
    TaskLoopState,
    TaskLoopStepExecutionSource,
    TaskLoopStepStatus,
    TaskLoopStepType,
)
from core.work_context.contracts import WorkContext, WorkContextSource, WorkContextStatus
from core.work_context.service import load_work_context, merge_work_context


def _task_loop_snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        state=TaskLoopState.COMPLETED,
        step_index=3,
        current_step_id="step-3",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_step_status=TaskLoopStepStatus.COMPLETED,
        step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
        current_plan=["Ziel klaeren", "Blueprints pruefen", "Container starten"],
        completed_steps=["Ziel klaeren", "Blueprints pruefen", "Container starten"],
        objective_summary="Python-Entwicklungscontainer starten",
        verified_artifacts=[
            {
                "artifact_type": "container_capability_context",
                "context": {
                    "request_family": "python_container",
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
                                    {"id": "python-sandbox", "name": "Python Sandbox"},
                                ]
                            },
                        }
                    ]
                },
            },
            {
                "artifact_type": "container_recovery_hint",
                "replan_step_title": "Verfuegbare Blueprints oder Container-Basis pruefen",
            },
        ],
        last_step_result={
            "execution_result": {
                "tool_statuses": [
                    {
                        "tool_name": "request_container",
                        "status": "routing_block",
                        "reason": "no_jit_match",
                    }
                ]
            }
        },
    )


def _workspace_events() -> list[dict]:
    return [
        {
            "id": "evt-1",
            "event_type": "task_loop_completed",
            "created_at": "2026-04-22T06:00:00.000000Z",
            "event_data": {
                "conversation_id": "conv-1",
                "state": "completed",
                "objective_summary": "Python-Entwicklungscontainer starten",
                "verified_artifacts": [
                    {
                        "artifact_type": "container_recovery_hint",
                        "replan_step_title": "Verfuegbare Blueprints oder Container-Basis pruefen",
                    }
                ],
            },
        }
    ]


def test_merge_work_context_prefers_primary_but_backfills_missing_fields():
    primary = WorkContext(
        conversation_id="conv-1",
        topic="Python-Entwicklungscontainer starten",
        status=WorkContextStatus.BLOCKED,
        source=WorkContextSource.TASK_LOOP,
        blocker="request_container:no_jit_match",
        capability_context={"request_family": "python_container"},
        metadata={"primary": True},
    )
    secondary = WorkContext(
        conversation_id="conv-1",
        topic="",
        status=WorkContextStatus.COMPLETED,
        source=WorkContextSource.WORKSPACE_EVENTS,
        updated_at="2026-04-22T06:00:00.000000Z",
        next_step="Verfuegbare Blueprints oder Container-Basis pruefen",
        metadata={"event_type": "task_loop_completed"},
    )

    merged = merge_work_context(primary, secondary)

    assert merged is not None
    assert merged.topic == "Python-Entwicklungscontainer starten"
    assert merged.status == WorkContextStatus.BLOCKED
    assert merged.updated_at == "2026-04-22T06:00:00.000000Z"
    assert merged.next_step == "Verfuegbare Blueprints oder Container-Basis pruefen"
    assert merged.blocker == "request_container:no_jit_match"
    assert dict(merged.metadata)["primary"] is True
    assert dict(merged.metadata)["event_type"] == "task_loop_completed"


def test_load_work_context_prefers_task_loop_snapshot_and_backfills_from_events():
    ctx = load_work_context(
        conversation_id="conv-1",
        task_loop_snapshot=_task_loop_snapshot(),
        workspace_events=_workspace_events(),
    )

    assert ctx is not None
    assert ctx.conversation_id == "conv-1"
    assert ctx.source == WorkContextSource.TASK_LOOP
    assert ctx.topic == "Python-Entwicklungscontainer starten"
    assert ctx.status == WorkContextStatus.COMPLETED
    assert ctx.next_step == "Verfuegbare Blueprints oder Container-Basis pruefen"
    assert ctx.blocker == "request_container:no_jit_match"
    assert dict(ctx.capability_context)["request_family"] == "python_container"
    assert dict(ctx.metadata)["event_type"] == "task_loop_completed"


def test_load_work_context_returns_event_context_when_snapshot_missing():
    ctx = load_work_context(
        conversation_id="conv-1",
        task_loop_snapshot=None,
        workspace_events=_workspace_events(),
    )

    assert ctx is not None
    assert ctx.source == WorkContextSource.WORKSPACE_EVENTS
    assert ctx.status == WorkContextStatus.COMPLETED
    assert ctx.topic == "Python-Entwicklungscontainer starten"
