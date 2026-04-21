from core.task_loop.contracts import RiskLevel, StopReason, TaskLoopSnapshot
from core.task_loop.evaluation_policy import evaluate_task_loop_iteration


def test_evaluation_policy_marks_completion_when_pending_step_is_empty():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        step_index=2,
        pending_step="",
    )

    evaluation = evaluate_task_loop_iteration(snapshot, max_steps=4)

    assert evaluation.is_complete is True
    assert evaluation.stop_decision.should_stop is False
    assert evaluation.progress_made is True
    assert evaluation.evidence_assessment is not None
    assert evaluation.progress_assessment is not None
    assert "completion_confidence=" in evaluation.detail


def test_evaluation_policy_waits_on_max_steps_after_progress():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        step_index=4,
        pending_step="another safe step",
    )

    evaluation = evaluate_task_loop_iteration(snapshot, max_steps=4)

    assert evaluation.is_complete is False
    assert evaluation.stop_decision.should_stop is True
    assert evaluation.stop_decision.reason is StopReason.MAX_STEPS_REACHED
    assert evaluation.progress_made is True
    assert "completion_confidence=" in evaluation.detail


def test_evaluation_policy_blocks_on_no_progress_and_risk_block():
    no_progress = evaluate_task_loop_iteration(
        TaskLoopSnapshot(
            objective_id="obj-1",
            conversation_id="conv-1",
            plan_id="plan-1",
            pending_step="next",
            no_progress_count=2,
        ),
        max_no_progress=2,
    )
    blocked = evaluate_task_loop_iteration(
        TaskLoopSnapshot(
            objective_id="obj-1",
            conversation_id="conv-1",
            plan_id="plan-1",
            pending_step="next",
            risk_level=RiskLevel.BLOCKED,
        )
    )

    assert no_progress.stop_decision.reason is StopReason.NO_PROGRESS
    assert no_progress.progress_made is False
    assert blocked.stop_decision.reason is StopReason.NO_CONCRETE_NEXT_STEP
    assert blocked.progress_made is False
