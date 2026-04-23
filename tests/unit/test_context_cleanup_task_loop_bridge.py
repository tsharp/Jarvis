from __future__ import annotations

from core.context_cleanup import build_compact_context, format_compact_context


def _event(event_type: str, event_data: dict, *, created_at: str = "2026-04-22T05:01:04.000000Z") -> dict:
    return {
        "id": f"evt-{event_type}",
        "event_type": event_type,
        "created_at": created_at,
        "event_data": event_data,
    }


def test_task_loop_completed_with_recovery_hint_surfaces_context_and_next_step():
    ctx = build_compact_context(
        [
            _event(
                "task_loop_completed",
                {
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
            )
        ]
    )

    rendered = format_compact_context(ctx)

    assert "TASK_CONTEXT Python-Entwicklungscontainer starten state=completed" in rendered
    assert "blocker=request_container:no_jit_match" in rendered
    assert "Follow up on task context: Verfuegbare Blueprints oder Container-Basis pruefen" in rendered


def test_task_loop_context_updated_surfaces_background_topic_for_normal_chat():
    ctx = build_compact_context(
        [
            _event(
                "task_loop_context_updated",
                {
                    "state": "waiting_for_user",
                    "background_loop_preserved": True,
                    "background_loop_state": "waiting_for_user",
                    "background_loop_topic": "Container-Auswahl abschliessen",
                    "background_loop_pending_step": "Rueckfrage beantworten",
                },
            )
        ]
    )

    rendered = format_compact_context(ctx)

    assert "TASK_CONTEXT Container-Auswahl abschliessen state=waiting_for_user pending=Rueckfrage beantworten" in rendered
    assert "Resume task context: Rueckfrage beantworten" in rendered
