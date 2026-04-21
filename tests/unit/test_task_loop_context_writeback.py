from core.task_loop.context_writeback import persist_context_only_turn
from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopState


def test_persist_context_only_turn_updates_snapshot_and_workspace():
    calls = []

    def save_workspace_entry(**kwargs):
        calls.append(kwargs)
        return {"type": "workspace_update", "entry_id": "evt-context"}

    snapshot = TaskLoopSnapshot(
        objective_id="obj-ctx",
        conversation_id="conv-ctx",
        plan_id="plan-ctx",
        state=TaskLoopState.WAITING_FOR_USER,
        pending_step="Rueckfrage beantworten",
    )

    updated, event, workspace_updates, event_ids = persist_context_only_turn(
        snapshot,
        "Das ist der normale Meta-Turn ausserhalb des separaten Loop-Runners.",
        done_reason="stop",
        save_workspace_entry_fn=save_workspace_entry,
    )

    assert updated.last_user_visible_answer.startswith("Das ist der normale Meta-Turn")
    assert updated.verified_artifacts[-1]["artifact_type"] == "context_only_turn"
    assert updated.workspace_event_ids == ["evt-context"]
    assert event["type"] == "task_loop_context_updated"
    assert workspace_updates == [{"type": "workspace_update", "entry_id": "evt-context"}]
    assert event_ids == ["evt-context"]
    assert calls[0]["entry_type"] == "task_loop_context_updated"
