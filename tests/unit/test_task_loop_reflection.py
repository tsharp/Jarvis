from core.task_loop.contracts import RiskLevel, TaskLoopSnapshot
from core.task_loop.reflection import ReflectionAction, reflect_after_chat_step


def test_reflection_continues_safe_pending_step():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        step_index=1,
        pending_step="next",
    )

    decision = reflect_after_chat_step(snapshot, max_steps=4)

    assert decision.action is ReflectionAction.CONTINUE
    assert decision.reason is None


def test_reflection_completes_without_pending_step():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        step_index=2,
        pending_step="",
    )

    decision = reflect_after_chat_step(snapshot, max_steps=4)

    assert decision.action is ReflectionAction.COMPLETED


def test_reflection_stops_at_max_steps():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        step_index=4,
        pending_step="another safe step",
    )

    decision = reflect_after_chat_step(snapshot, max_steps=4)

    assert decision.action is ReflectionAction.WAITING_FOR_USER
    assert decision.reason.value == "max_steps_reached"


def test_reflection_stops_at_max_errors():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        pending_step="next",
        error_count=4,
    )

    decision = reflect_after_chat_step(snapshot, max_errors=4)

    assert decision.action is ReflectionAction.BLOCKED
    assert decision.reason.value == "max_errors_reached"


def test_reflection_waits_on_risk_gate():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        pending_step="write file",
        risk_level=RiskLevel.RISKY,
    )

    decision = reflect_after_chat_step(snapshot)

    assert decision.action is ReflectionAction.WAITING_FOR_USER
    assert decision.reason.value == "risk_gate_required"


def test_reflection_inserts_verification_step_before_completion_for_weak_tool_evidence():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        current_plan=["Container-Aktion ausführen"],
        completed_steps=["Container-Aktion ausführen"],
        pending_step="",
        last_step_result={
            "status": "completed",
            "step_type": "tool_execution_step",
            "step_execution_source": "orchestrator",
        },
    )

    decision = reflect_after_chat_step(snapshot, max_steps=4)

    assert decision.action is ReflectionAction.CONTINUE
    assert decision.next_step_override == "Ergebnis verifizieren und Abschluss absichern"
    assert "verify_before_complete" in decision.detail


def test_reflection_waits_for_user_when_verification_step_still_has_weak_evidence():
    verify_step = "Ergebnis verifizieren und Abschluss absichern"
    snapshot = TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        current_plan=["Container-Aktion ausführen", verify_step],
        completed_steps=["Container-Aktion ausführen", verify_step],
        pending_step="",
        verified_artifacts=[
            {
                "artifact_type": "execution_result",
                "metadata": {},
            }
        ],
        last_step_result={
            "status": "completed",
            "step_type": "analysis_step",
            "step_execution_source": "loop",
        },
    )

    decision = reflect_after_chat_step(snapshot, max_steps=4)

    assert decision.action is ReflectionAction.WAITING_FOR_USER
    assert decision.reason.value == "user_decision_required"
