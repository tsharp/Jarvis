from core.task_loop.capabilities.container.recovery import (
    CONTAINER_INSPECT_STEP_TITLE,
    DISCOVERY_STEP_TITLE,
    RUNTIME_DISCOVERY_STEP_TITLE,
    build_container_recovery_hint,
)


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
