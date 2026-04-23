from core.work_context.contracts import WorkContext, WorkContextSource, WorkContextStatus
from core.work_context.writers.workspace_events import build_workspace_event_from_work_context


def test_build_workspace_event_from_work_context_projects_task_loop_shape():
    context = WorkContext(
        conversation_id="conv-1",
        topic="Python-Entwicklungscontainer starten",
        status=WorkContextStatus.BLOCKED,
        source=WorkContextSource.TASK_LOOP,
        last_step="Blueprints pruefen",
        next_step="Verfuegbare Blueprints oder Container-Basis pruefen",
        blocker="request_container:no_jit_match",
    )

    event = build_workspace_event_from_work_context(
        context,
        created_at="2026-04-23T02:30:00.000000Z",
    )

    assert event is not None
    assert event["event_type"] == "task_loop_context_updated"
    assert event["event_data"]["conversation_id"] == "conv-1"
    assert event["event_data"]["background_loop_topic"] == "Python-Entwicklungscontainer starten"
    assert event["event_data"]["pending_step"] == "Verfuegbare Blueprints oder Container-Basis pruefen"
    assert event["event_data"]["last_step_result"]["blockers"] == ["request_container:no_jit_match"]
    assert "background_loop_pending_step" not in event["event_data"]
