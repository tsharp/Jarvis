from core.task_loop.completion_policy import (
    build_completion_message,
    completion_detail,
    is_task_loop_complete,
)
from core.task_loop.contracts import TaskLoopSnapshot


def test_is_task_loop_complete_only_when_pending_step_is_empty():
    assert is_task_loop_complete(
        TaskLoopSnapshot(
            objective_id="obj-1",
            conversation_id="conv-1",
            plan_id="plan-1",
            pending_step="",
        )
    ) is True
    assert is_task_loop_complete(
        TaskLoopSnapshot(
            objective_id="obj-1",
            conversation_id="conv-1",
            plan_id="plan-1",
            pending_step="next",
        )
    ) is False


def test_completion_policy_builds_final_message_with_plan_status():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        current_plan=["one", "two"],
        completed_steps=["one"],
        pending_step="",
    )

    assert completion_detail(snapshot) == "plan_complete"
    message = build_completion_message(snapshot)

    assert "Finaler Planstatus:" in message
    assert "Task-Loop abgeschlossen." in message
