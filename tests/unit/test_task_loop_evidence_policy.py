from core.task_loop.contracts import (
    TaskLoopSnapshot,
    TaskLoopStepExecutionSource,
    TaskLoopStepType,
)
from core.task_loop.evidence_policy import assess_task_loop_evidence


def test_evidence_policy_scores_grounded_execution_result_against_output_standard():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        pending_step="",
        completed_steps=["calc result"],
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
        verified_artifacts=[
            {
                "artifact_type": "execution_result",
                "result": 120,
                "input": 5,
                "grounding": {"source": "tool"},
                "tool_statuses": [{"status": "ok"}],
                "metadata": {"template_id": "TMPL-MATH-01"},
            }
        ],
        last_step_result={
            "status": "completed",
            "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
            "step_execution_source": TaskLoopStepExecutionSource.ORCHESTRATOR.value,
            "execution_result": {
                "result": 120,
                "input": 5,
                "grounding": {"source": "tool"},
                "tool_statuses": [{"status": "ok"}],
                "metadata": {"template_id": "TMPL-MATH-01"},
            },
        },
    )

    assessment = assess_task_loop_evidence(snapshot)

    assert assessment.evidence_score >= 0.55
    assert assessment.completion_confidence >= 0.75
    assert assessment.requires_verification is False
    assert assessment.matched_standard_id == "OUT-01"
    assert assessment.matched_template_id == "TMPL-MATH-01"


def test_evidence_policy_requires_verification_for_tool_completion_without_supporting_evidence():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        pending_step="",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
        last_step_result={
            "status": "completed",
            "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
            "step_execution_source": TaskLoopStepExecutionSource.ORCHESTRATOR.value,
        },
    )

    assessment = assess_task_loop_evidence(snapshot)

    assert assessment.evidence_score < 0.55
    assert assessment.requires_verification is True
