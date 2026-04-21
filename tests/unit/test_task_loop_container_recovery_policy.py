from core.task_loop.capabilities.container.recovery import (
    CONTAINER_INSPECT_STEP_TITLE,
    DISCOVERY_STEP_TITLE,
    RUNTIME_DISCOVERY_STEP_TITLE,
)
from core.task_loop.capabilities.container.replan_policy import (
    apply_container_recovery_replan,
    build_container_recovery_hint,
)
from core.task_loop.contracts import RiskLevel, TaskLoopSnapshot, TaskLoopStepType


def test_build_container_recovery_hint_prefers_blueprint_list_for_no_match():
    hint = build_container_recovery_hint(
        requested_capability={
            "capability_type": "container_manager",
            "capability_target": "request_container",
            "capability_action": "request_container",
        },
        capability_context={"request_family": "python_container", "known_fields": {}},
        execution_result={
            "done_reason": "routing_block",
            "tool_statuses": [
                {"tool_name": "request_container", "status": "routing_block", "reason": "no_jit_match"}
            ],
        },
        resolved_tools=[{"name": "request_container", "arguments": {}}],
    )

    assert hint["recovery_mode"] == "replan_with_tools"
    assert hint["next_tools"] == ["blueprint_list"]
    assert hint["replan_step_title"] == DISCOVERY_STEP_TITLE


def test_build_container_recovery_hint_prefers_container_list_for_runtime_inventory_gap():
    hint = build_container_recovery_hint(
        requested_capability={
            "capability_type": "container_manager",
            "capability_target": "request_container",
            "capability_action": "request_container",
        },
        capability_context={"request_family": "generic_container", "known_fields": {}},
        execution_result={
            "done_reason": "routing_block",
            "tool_statuses": [
                {"tool_name": "request_container", "status": "routing_block", "reason": "missing_container_id:auto_resolve_failed"}
            ],
        },
        resolved_tools=[{"name": "request_container", "arguments": {}}],
    )

    assert hint["recovery_mode"] == "replan_with_tools"
    assert hint["next_tools"] == ["container_list"]
    assert hint["replan_step_title"] == RUNTIME_DISCOVERY_STEP_TITLE


def test_build_container_recovery_hint_prefers_container_inspect_for_known_target_binding_gap():
    hint = build_container_recovery_hint(
        requested_capability={
            "capability_type": "container_manager",
            "capability_target": "request_container",
            "capability_action": "request_container",
        },
        capability_context={
            "request_family": "generic_container",
            "known_fields": {"container_id": "ctr-1"},
        },
        execution_result={
            "done_reason": "routing_block",
            "tool_statuses": [
                {"tool_name": "request_container", "status": "routing_block", "reason": "binding requires inspect"}
            ],
        },
        resolved_tools=[{"name": "request_container", "arguments": {}}],
    )

    assert hint["recovery_mode"] == "replan_with_tools"
    assert hint["next_tools"] == ["container_inspect"]
    assert hint["replan_step_title"] == CONTAINER_INSPECT_STEP_TITLE


def test_apply_container_recovery_replan_inserts_runtime_discovery_step_before_current_step():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-recovery",
        conversation_id="conv-recovery",
        plan_id="plan-recovery",
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

    updated = apply_container_recovery_replan(
        snapshot,
        current_step_title="Container-Anfrage ausfuehren",
        current_step_meta={
            "step_id": "step-4",
            "task_kind": "implementation",
            "objective": "Container fuer Host-Runtime kontrolliert nutzen",
            "capability_context": {},
        },
        recovery_hint={
            "recovery_mode": "replan_with_tools",
            "next_tools": ["container_list"],
            "replan_step_title": RUNTIME_DISCOVERY_STEP_TITLE,
        },
    )

    assert updated.current_plan[3] == RUNTIME_DISCOVERY_STEP_TITLE
    assert updated.current_plan[4] == "Container-Anfrage ausfuehren"
    assert updated.plan_steps[3]["suggested_tools"] == ["container_list"]
    assert updated.plan_steps[3]["step_type"] == TaskLoopStepType.TOOL_EXECUTION.value
