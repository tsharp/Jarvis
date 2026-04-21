from core.task_loop.capabilities.container.recovery import (
    DISCOVERY_STEP_TITLE,
    RECOVERY_ARTIFACT_TYPE,
    RUNTIME_DISCOVERY_STEP_TITLE,
)
from core.task_loop.contracts import RiskLevel, TaskLoopSnapshot, TaskLoopStepType
from core.task_loop.recovery_policy import derive_recovery_hint, maybe_apply_recovery_replan


def _snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        objective_id="obj-recovery-policy",
        conversation_id="conv-recovery-policy",
        plan_id="plan-recovery-policy",
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


def test_derive_recovery_hint_prefers_known_container_artifact():
    hint = derive_recovery_hint(
        [
            {
                "artifact_type": RECOVERY_ARTIFACT_TYPE,
                "recovery_mode": "replan_with_tools",
                "replan_step_title": "Laufende oder vorhandene Container pruefen",
                "next_tools": ["container_list"],
            }
        ]
    )

    assert hint["artifact_type"] == RECOVERY_ARTIFACT_TYPE
    assert hint["next_tools"] == ["container_list"]


def test_maybe_apply_recovery_replan_dispatches_container_hint():
    updated = maybe_apply_recovery_replan(
        _snapshot(),
        current_step_title="Container-Anfrage ausfuehren",
        current_step_meta={
            "step_id": "step-4",
            "task_kind": "implementation",
            "objective": "Container fuer Host-Runtime kontrolliert nutzen",
            "capability_context": {},
        },
        recovery_hint={
            "artifact_type": RECOVERY_ARTIFACT_TYPE,
            "recovery_mode": "replan_with_tools",
            "next_tools": ["container_list"],
            "replan_step_title": "Laufende oder vorhandene Container pruefen",
        },
    )

    assert updated.current_plan[3] == "Laufende oder vorhandene Container pruefen"
    assert updated.current_plan[4] == "Container-Anfrage ausfuehren"
    assert updated.plan_steps[3]["suggested_tools"] == ["container_list"]


def test_maybe_apply_recovery_replan_applies_generic_hint_without_capability_dispatch():
    updated = maybe_apply_recovery_replan(
        _snapshot(),
        current_step_title="Container-Anfrage ausfuehren",
        current_step_meta={},
        recovery_hint={
            "recovery_mode": "replan_with_tools",
            "replan_step_title": "Generischen Recovery-Schritt einfuegen",
            "replan_step": {
                "step_id": "step-4-recovery",
                "title": "Generischen Recovery-Schritt einfuegen",
                "goal": "Generischen Befund sichtbar pruefen",
                "done_criteria": "Der generische Recovery-Befund liegt vor.",
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

    assert updated.current_plan[3] == "Generischen Recovery-Schritt einfuegen"
    assert updated.plan_steps[3]["suggested_tools"] == ["container_list"]


def _recovery_snapshot(recovery_title: str) -> TaskLoopSnapshot:
    """Snapshot, bei dem gerade ein eingefuegter Recovery-/Discovery-Step abgeschlossen wurde."""
    return TaskLoopSnapshot(
        objective_id="obj-loop-guard",
        conversation_id="conv-loop-guard",
        plan_id="plan-loop-guard",
        current_step_id="step-recovery",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_plan=[
            "Ziel klaeren",
            recovery_title,
            "Container-Anfrage ausfuehren",
            "Antwort zusammenfassen",
        ],
        plan_steps=[
            {"step_id": "step-1", "title": "Ziel klaeren", "step_type": "analysis_step"},
            {
                "step_id": "step-recovery",
                "title": recovery_title,
                "step_type": "tool_execution_step",
                "suggested_tools": ["blueprint_list"],
            },
            {"step_id": "step-3", "title": "Container-Anfrage ausfuehren", "step_type": "tool_execution_step"},
            {"step_id": "step-4", "title": "Antwort zusammenfassen", "step_type": "response_step"},
        ],
        completed_steps=["Ziel klaeren"],
        pending_step=recovery_title,
        risk_level=RiskLevel.SAFE,
    )


def test_maybe_apply_recovery_replan_skips_replan_when_step_is_discovery_title():
    # Exakter kanonischer Titel — kein weiterer Replan erlaubt
    unchanged = maybe_apply_recovery_replan(
        _recovery_snapshot(DISCOVERY_STEP_TITLE),
        current_step_title=DISCOVERY_STEP_TITLE,
        current_step_meta={"step_id": "step-recovery", "task_kind": "implementation", "objective": "", "capability_context": {}},
        recovery_hint={
            "artifact_type": RECOVERY_ARTIFACT_TYPE,
            "recovery_mode": "replan_with_tools",
            "next_tools": ["blueprint_list"],
            "replan_step_title": DISCOVERY_STEP_TITLE,
        },
    )
    assert unchanged.current_plan == _recovery_snapshot(DISCOVERY_STEP_TITLE).current_plan


def test_maybe_apply_recovery_replan_skips_replan_when_step_has_recovery_suffix():
    # apply_replan_hint haengt "(Recovery)" an — muss auch geblockt werden
    suffix_title = f"{DISCOVERY_STEP_TITLE} (Recovery)"
    unchanged = maybe_apply_recovery_replan(
        _recovery_snapshot(suffix_title),
        current_step_title=suffix_title,
        current_step_meta={"step_id": "step-recovery", "task_kind": "implementation", "objective": "", "capability_context": {}},
        recovery_hint={
            "artifact_type": RECOVERY_ARTIFACT_TYPE,
            "recovery_mode": "replan_with_tools",
            "next_tools": ["blueprint_list"],
            "replan_step_title": DISCOVERY_STEP_TITLE,
        },
    )
    assert unchanged.current_plan == _recovery_snapshot(suffix_title).current_plan


def test_maybe_apply_recovery_replan_still_applies_for_non_recovery_step():
    # Normaler Step → Replan wird wie gewohnt ausgefuehrt
    updated = maybe_apply_recovery_replan(
        _snapshot(),
        current_step_title="Container-Anfrage ausfuehren",
        current_step_meta={
            "step_id": "step-4",
            "task_kind": "implementation",
            "objective": "Container fuer Host-Runtime kontrolliert nutzen",
            "capability_context": {},
        },
        recovery_hint={
            "artifact_type": RECOVERY_ARTIFACT_TYPE,
            "recovery_mode": "replan_with_tools",
            "next_tools": ["container_list"],
            "replan_step_title": RUNTIME_DISCOVERY_STEP_TITLE,
        },
    )
    assert RUNTIME_DISCOVERY_STEP_TITLE in updated.current_plan


def _snapshot_after_discovery() -> TaskLoopSnapshot:
    """Snapshot: Discovery-Step bereits in completed_steps, Original-Step laeuft erneut."""
    return TaskLoopSnapshot(
        objective_id="obj-loop-guard-2",
        conversation_id="conv-loop-guard-2",
        plan_id="plan-loop-guard-2",
        current_step_id="step-container",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_plan=[
            DISCOVERY_STEP_TITLE,
            "Container-Anfrage ausfuehren",
            "Antwort zusammenfassen",
        ],
        plan_steps=[
            {
                "step_id": "step-discovery",
                "title": DISCOVERY_STEP_TITLE,
                "step_type": "tool_execution_step",
                "suggested_tools": ["blueprint_list"],
            },
            {"step_id": "step-container", "title": "Container-Anfrage ausfuehren", "step_type": "tool_execution_step"},
            {"step_id": "step-summary", "title": "Antwort zusammenfassen", "step_type": "response_step"},
        ],
        completed_steps=[DISCOVERY_STEP_TITLE],  # Discovery wurde bereits erfolgreich ausgefuehrt
        pending_step="Container-Anfrage ausfuehren",
        risk_level=RiskLevel.SAFE,
    )


def test_maybe_apply_recovery_replan_allows_replan_when_only_original_step_completed():
    # Nur der exakte Originaltitel (ohne "(Recovery)"-Suffix) ist in completed_steps —
    # das war ein geplanter Schritt, kein Recovery-Step. Ein Recovery-Versuch (mit "(Recovery)"-Suffix)
    # ist hier noch erlaubt: apply_replan_hint wuerde den "(Recovery)"-Suffix einfuegen,
    # weil der Originaltitel bereits im Plan steht (vor dem aktuellen Schritt).
    snap = _snapshot_after_discovery()
    updated = maybe_apply_recovery_replan(
        snap,
        current_step_title="Container-Anfrage ausfuehren",
        current_step_meta={"step_id": "step-container", "task_kind": "implementation", "objective": "", "capability_context": {}},
        recovery_hint={
            "artifact_type": RECOVERY_ARTIFACT_TYPE,
            "recovery_mode": "replan_with_tools",
            "next_tools": ["blueprint_list"],
            "replan_step_title": DISCOVERY_STEP_TITLE,
        },
    )
    # Replan sollte stattfinden (der (Recovery)-Schritt wird eingefuegt)
    assert updated is not snap
    assert any("Recovery" in title for title in updated.current_plan)


def test_maybe_apply_recovery_replan_skips_replan_when_recovery_variant_already_completed():
    # "(Recovery)"-Variante des Discovery-Steps ist in completed_steps.
    # Auch dann keinen weiteren Replan einfuegen.
    suffix_title = f"{DISCOVERY_STEP_TITLE} (Recovery)"
    snap = TaskLoopSnapshot(
        objective_id="obj-loop-guard-2b",
        conversation_id="conv-loop-guard-2b",
        plan_id="plan-loop-guard-2b",
        current_step_id="step-container",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_plan=[DISCOVERY_STEP_TITLE, suffix_title, "Container-Anfrage ausfuehren"],
        plan_steps=[],
        completed_steps=[DISCOVERY_STEP_TITLE, suffix_title],
        pending_step="Container-Anfrage ausfuehren",
        risk_level=RiskLevel.SAFE,
    )
    unchanged = maybe_apply_recovery_replan(
        snap,
        current_step_title="Container-Anfrage ausfuehren",
        current_step_meta={},
        recovery_hint={
            "artifact_type": RECOVERY_ARTIFACT_TYPE,
            "recovery_mode": "replan_with_tools",
            "next_tools": ["blueprint_list"],
            "replan_step_title": DISCOVERY_STEP_TITLE,
        },
    )
    assert unchanged.current_plan == snap.current_plan
