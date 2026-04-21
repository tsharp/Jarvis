from core.task_loop.active_turn_policy import is_runtime_resume_candidate
from core.task_loop.contracts import (
    TaskLoopSnapshot,
    TaskLoopState,
    TaskLoopStepExecutionSource,
    TaskLoopStepStatus,
    TaskLoopStepType,
)


def _runtime_waiting_snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        objective_id="obj-runtime",
        conversation_id="conv-runtime",
        plan_id="plan-runtime",
        state=TaskLoopState.WAITING_FOR_USER,
        current_step_id="step-1",
        current_step_type=TaskLoopStepType.TOOL_REQUEST,
        current_step_status=TaskLoopStepStatus.WAITING_FOR_USER,
        step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
        current_plan=["Container kontrolliert anfragen"],
        plan_steps=[],
        pending_step="Container kontrolliert anfragen",
        last_step_result={
            "status": TaskLoopStepStatus.WAITING_FOR_USER.value,
            "step_type": TaskLoopStepType.TOOL_REQUEST.value,
            "step_execution_source": TaskLoopStepExecutionSource.ORCHESTRATOR.value,
        },
    )


def test_is_runtime_resume_candidate_accepts_parameter_reply():
    snapshot = _runtime_waiting_snapshot()

    assert is_runtime_resume_candidate(snapshot, "python:3.11-slim", raw_request={}) is True


def test_is_runtime_resume_candidate_rejects_meta_question():
    snapshot = _runtime_waiting_snapshot()

    assert is_runtime_resume_candidate(snapshot, "was ist passiert?", raw_request={}) is False
