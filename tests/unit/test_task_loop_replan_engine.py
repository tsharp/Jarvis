from core.task_loop.contracts import RiskLevel, TaskLoopSnapshot, TaskLoopStepType
from core.task_loop.replan_engine import apply_replan_hint


def test_apply_replan_hint_inserts_recovery_step_before_current_step():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-replan",
        conversation_id="conv-replan",
        plan_id="plan-replan",
        current_step_id="step-4",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_plan=[
            "Ziel klaeren",
            "Angaben sammeln",
            "Freigabe vorbereiten",
            "Container-Anfrage ausfuehren",
            "Antwort zusammenfassen",
        ],
        plan_steps=[
            {"step_id": "step-1", "title": "Ziel klaeren", "step_type": "analysis_step"},
            {"step_id": "step-2", "title": "Angaben sammeln", "step_type": "analysis_step"},
            {"step_id": "step-3", "title": "Freigabe vorbereiten", "step_type": "tool_request_step"},
            {"step_id": "step-4", "title": "Container-Anfrage ausfuehren", "step_type": "tool_execution_step"},
            {"step_id": "step-5", "title": "Antwort zusammenfassen", "step_type": "response_step"},
        ],
        completed_steps=["Ziel klaeren", "Angaben sammeln", "Freigabe vorbereiten"],
        pending_step="Container-Anfrage ausfuehren",
        risk_level=RiskLevel.SAFE,
    )

    updated = apply_replan_hint(
        snapshot,
        current_step_title="Container-Anfrage ausfuehren",
        current_step_meta={},
        replan_hint={
            "recovery_mode": "replan_with_tools",
            "replan_step_title": "Laufende oder vorhandene Container pruefen",
            "replan_step": {
                "step_id": "step-4-recovery",
                "title": "Laufende oder vorhandene Container pruefen",
                "goal": "Runtime-Inventar pruefen",
                "done_criteria": "Runtime-Inventar liegt vor.",
                "risk_level": RiskLevel.SAFE.value,
                "requires_user": False,
                "suggested_tools": ["container_list"],
                "task_kind": "implementation",
                "objective": "Container fuer Host-Runtime kontrolliert nutzen",
                "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
                "requested_capability": {
                    "capability_type": "container_manager",
                    "capability_action": "container_list",
                },
                "capability_context": {},
            },
        },
    )

    assert updated.current_plan[3] == "Laufende oder vorhandene Container pruefen"
    assert updated.current_plan[4] == "Container-Anfrage ausfuehren"
    assert updated.plan_steps[3]["suggested_tools"] == ["container_list"]
