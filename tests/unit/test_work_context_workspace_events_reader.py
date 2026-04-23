from core.work_context.contracts import WorkContextStatus
from core.work_context.readers.workspace_events import build_work_context_from_workspace_events


def _event(event_type: str, event_data: dict, *, created_at: str, event_id: str = "") -> dict:
    return {
        "id": event_id or f"evt-{event_type}",
        "event_type": event_type,
        "created_at": created_at,
        "event_data": event_data,
    }


def test_workspace_events_reader_maps_completed_task_loop_context():
    ctx = build_work_context_from_workspace_events(
        [
            _event(
                "task_loop_completed",
                {
                    "conversation_id": "conv-1",
                    "state": "completed",
                    "objective_summary": "Python-Entwicklungscontainer starten",
                    "pending_step": "",
                    "last_step_result": {
                        "status": "completed",
                        "execution_result": {
                            "done_reason": "routing_block",
                            "tool_statuses": [
                                {
                                    "tool_name": "request_container",
                                    "status": "routing_block",
                                    "reason": "no_jit_match",
                                }
                            ],
                        },
                    },
                    "verified_artifacts": [
                        {
                            "artifact_type": "container_recovery_hint",
                            "replan_step_title": "Verfuegbare Blueprints oder Container-Basis pruefen",
                        }
                    ],
                },
                created_at="2026-04-22T05:01:04.000000Z",
            )
        ]
    )

    assert ctx is not None
    assert ctx.conversation_id == "conv-1"
    assert ctx.topic == "Python-Entwicklungscontainer starten"
    assert ctx.status == WorkContextStatus.COMPLETED
    assert ctx.blocker == "request_container:no_jit_match"
    assert ctx.next_step == "Verfuegbare Blueprints oder Container-Basis pruefen"
    assert ctx.metadata["event_type"] == "task_loop_completed"


def test_workspace_events_reader_maps_background_context_update():
    ctx = build_work_context_from_workspace_events(
        [
            _event(
                "task_loop_context_updated",
                {
                    "conversation_id": "conv-2",
                    "state": "waiting_for_user",
                    "background_loop_preserved": True,
                    "background_loop_state": "waiting_for_user",
                    "background_loop_topic": "Container-Auswahl abschliessen",
                    "background_loop_pending_step": "Rueckfrage beantworten",
                },
                created_at="2026-04-22T05:01:10.000000Z",
            )
        ]
    )

    assert ctx is not None
    assert ctx.conversation_id == "conv-2"
    assert ctx.topic == "Container-Auswahl abschliessen"
    assert ctx.status == WorkContextStatus.WAITING
    assert ctx.last_step == "Rueckfrage beantworten"
    assert ctx.next_step == "Rueckfrage beantworten"
    assert ctx.blocker == ""


def test_workspace_events_reader_prefers_latest_relevant_task_loop_event():
    ctx = build_work_context_from_workspace_events(
        [
            _event(
                "task_loop_context_updated",
                {
                    "conversation_id": "conv-3",
                    "background_loop_state": "waiting_for_user",
                    "background_loop_topic": "Altes Thema",
                    "background_loop_pending_step": "Alte Rueckfrage",
                },
                created_at="2026-04-22T05:01:00.000000Z",
            ),
            _event(
                "task_loop_completed",
                {
                    "conversation_id": "conv-3",
                    "state": "completed",
                    "objective_summary": "Neues Thema",
                    "verified_artifacts": [
                        {
                            "artifact_type": "container_recovery_hint",
                            "replan_step_title": "Neuen Schritt pruefen",
                        }
                    ],
                },
                created_at="2026-04-22T05:02:00.000000Z",
            ),
        ]
    )

    assert ctx is not None
    assert ctx.topic == "Neues Thema"
    assert ctx.status == WorkContextStatus.COMPLETED
    assert ctx.next_step == "Neuen Schritt pruefen"
    assert ctx.metadata["event_count"] == 2


def test_workspace_events_reader_returns_none_without_task_loop_events():
    assert (
        build_work_context_from_workspace_events(
            [
                {
                    "id": "evt-note",
                    "event_type": "note",
                    "created_at": "2026-04-22T05:02:00.000000Z",
                    "event_data": {"content": "irrelevant"},
                }
            ]
        )
        is None
    )
