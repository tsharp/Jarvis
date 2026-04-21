from core.task_loop.contracts import TaskLoopSnapshot
from core.task_loop.progress_policy import assess_task_loop_progress


def test_progress_policy_matches_critical_anti_pattern_in_causal_reasoning_text():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        pending_step="Why does X cause Y after the rollout?",
        last_user_visible_answer="X happened before Y, therefore X causes Y.",
    )

    assessment = assess_task_loop_progress(snapshot)

    assert "AP001" in assessment.matched_anti_pattern_ids
    assert assessment.hard_blocked is True
    assert assessment.requires_recovery is True
    assert assessment.blocker_burden >= 0.9


def test_progress_policy_uses_error_patterns_for_retryable_failures():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        pending_step="retry request",
        last_step_result={
            "status": "failed",
            "trace_reason": "network timed out while calling upstream",
            "execution_result": {
                "error": "Request timed out",
                "done_reason": "timeout",
            },
        },
    )

    assessment = assess_task_loop_progress(snapshot)

    assert "TIMEOUT" in assessment.matched_error_pattern_ids
    assert assessment.requires_recovery is True
    assert assessment.blocker_burden >= 0.65
