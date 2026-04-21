import pytest

from core.task_loop.contracts import (
    RiskLevel,
    StopReason,
    TaskLoopSnapshot,
    TaskLoopState,
    TaskLoopStepStatus,
    TaskLoopStepType,
    TaskLoopTransitionError,
    transition_task_loop,
    transition_task_loop_step,
)


def test_task_loop_snapshot_serializes_stable_contract():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        current_plan=["Plan", "Execute"],
        pending_step="Plan",
    )

    out = snapshot.to_dict()

    assert out["objective_id"] == "obj-1"
    assert out["state"] == "planning"
    assert out["risk_level"] == "safe"
    assert out["stop_reason"] is None
    assert out["current_plan"] == ["Plan", "Execute"]
    assert out["current_step_type"] == "analysis_step"
    assert out["current_step_status"] == "pending"


def test_stop_reason_includes_max_errors_contract():
    assert StopReason.MAX_ERRORS_REACHED.value == "max_errors_reached"


def test_transition_requires_stop_reason_for_blocked_state():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        pending_step="Plan",
    )

    with pytest.raises(TaskLoopTransitionError):
        transition_task_loop(snapshot, TaskLoopState.BLOCKED)


def test_transition_to_waiting_for_user_carries_stop_reason_and_risk():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        pending_step="Check risk",
    )

    next_snapshot = transition_task_loop(
        snapshot,
        TaskLoopState.WAITING_FOR_USER,
        stop_reason=StopReason.RISK_GATE_REQUIRED,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
    )

    assert next_snapshot.state is TaskLoopState.WAITING_FOR_USER
    assert next_snapshot.stop_reason is StopReason.RISK_GATE_REQUIRED
    assert next_snapshot.risk_level is RiskLevel.NEEDS_CONFIRMATION


def test_terminal_state_cannot_transition():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        state=TaskLoopState.COMPLETED,
    )

    with pytest.raises(TaskLoopTransitionError):
        transition_task_loop(snapshot, TaskLoopState.PLANNING)


def test_completed_state_must_not_carry_stop_reason():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        state=TaskLoopState.EXECUTING,
    )

    with pytest.raises(TaskLoopTransitionError):
        transition_task_loop(
            snapshot,
            TaskLoopState.COMPLETED,
            stop_reason=StopReason.MAX_STEPS_REACHED,
        )


def test_step_transition_allows_analysis_to_tool_execution_upgrade_when_runtime_resolves_tools():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        current_step_id="step-1",
    )

    running = transition_task_loop_step(
        snapshot,
        next_step_status=TaskLoopStepStatus.RUNNING,
    )

    upgraded = transition_task_loop_step(
        running,
        next_step_type=TaskLoopStepType.TOOL_EXECUTION,
    )

    assert upgraded.current_step_type is TaskLoopStepType.TOOL_EXECUTION
    assert upgraded.current_step_status is TaskLoopStepStatus.RUNNING


def test_step_transition_allows_reset_for_new_step_after_completion():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        current_step_id="step-1",
    )
    running = transition_task_loop_step(snapshot, next_step_status=TaskLoopStepStatus.RUNNING)
    completed = transition_task_loop_step(running, next_step_status=TaskLoopStepStatus.COMPLETED)

    next_snapshot = transition_task_loop_step(
        completed,
        next_step_id="step-2",
        next_step_type=TaskLoopStepType.RESPONSE,
        next_step_status=TaskLoopStepStatus.PENDING,
        reset_for_new_step=True,
    )

    assert next_snapshot.current_step_id == "step-2"
    assert next_snapshot.current_step_type is TaskLoopStepType.RESPONSE
    assert next_snapshot.current_step_status is TaskLoopStepStatus.PENDING
