from core.task_loop.action_resolution.contracts import (
    ActionResolutionMode,
    ActionResolutionSource,
)
from core.task_loop.action_resolution.resolver import resolve_next_loop_action
from core.task_loop.contracts import (
    TaskLoopSnapshot,
    TaskLoopStepRequest,
    TaskLoopStepType,
)


def _snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        objective_id="obj-action-resolution",
        conversation_id="conv-action-resolution",
        plan_id="plan-action-resolution",
    )


def test_resolver_uses_auto_clarify_for_container_discovery():
    step_request = TaskLoopStepRequest(
        turn_id="turn-1",
        loop_id="loop-1",
        step_id="step-1",
        step_index=0,
        step_type=TaskLoopStepType.TOOL_EXECUTION,
        objective="Python-Container anfordern",
        step_goal="Fehlende Container-Parameter selbst klaeren",
        step_title="Container-Anfrage vorbereiten",
        requested_capability={
            "capability_type": "container_manager",
            "capability_action": "request_container",
            "capability_target": "request_container",
        },
        capability_context={
            "request_family": "python_container",
            "known_fields": {
                "python_version": "3.11",
                "dependency_spec": "requirements.txt",
                "build_or_runtime": "runtime",
            },
            "missing_fields": ["blueprint"],
        },
        suggested_tools=[],
    )

    decision = resolve_next_loop_action(
        snapshot=_snapshot(),
        step_request=step_request,
    )

    assert decision.resolved is True
    assert decision.source is ActionResolutionSource.AUTO_CLARIFY_POLICY
    assert decision.action is not None
    assert decision.action.mode is ActionResolutionMode.INSERT_DISCOVERY_STEP
    assert decision.action.suggested_tools == ["blueprint_list"]


def test_resolver_uses_auto_clarify_ask_user_when_no_candidate_exists():
    step_request = TaskLoopStepRequest(
        turn_id="turn-2",
        loop_id="loop-2",
        step_id="step-2",
        step_index=1,
        step_type=TaskLoopStepType.ANALYSIS,
        objective="Unklare Folgeaktion klaeren",
        step_goal="Naechsten Schritt bestimmen",
        step_title="Weitere Angaben klaeren",
    )

    decision = resolve_next_loop_action(
        snapshot=_snapshot(),
        step_request=step_request,
    )

    assert decision.resolved is True
    assert decision.source is ActionResolutionSource.AUTO_CLARIFY_POLICY
    assert decision.action is not None
    assert decision.action.mode is ActionResolutionMode.ASK_USER
    assert "ask_user_message" in decision.action.metadata


def test_resolver_applies_safe_python_container_defaults_before_discovery():
    step_request = TaskLoopStepRequest(
        turn_id="turn-3",
        loop_id="loop-3",
        step_id="step-3",
        step_index=2,
        step_type=TaskLoopStepType.TOOL_EXECUTION,
        objective="Python-Container anfordern",
        step_goal="Fehlende Parameter so weit wie sicher selbst ergaenzen",
        step_title="Python-Container vorbereiten",
        requested_capability={
            "capability_type": "container_manager",
            "capability_action": "request_container",
            "capability_target": "request_container",
        },
        capability_context={
            "request_family": "python_container",
            "known_fields": {},
            "missing_fields": [
                "blueprint",
                "python_version",
                "dependency_spec",
                "build_or_runtime",
            ],
        },
        suggested_tools=[],
    )

    decision = resolve_next_loop_action(
        snapshot=_snapshot(),
        step_request=step_request,
    )

    assert decision.resolved is True
    assert decision.source is ActionResolutionSource.AUTO_CLARIFY_POLICY
    assert decision.action is not None
    assert decision.action.mode is ActionResolutionMode.INSERT_DISCOVERY_STEP
    assert decision.action.suggested_tools == ["blueprint_list"]
    known_fields = dict((decision.action.capability_context or {}).get("known_fields") or {})
    assert known_fields["python_version"] == "3.11"
    assert known_fields["dependency_spec"] == "none"
    assert known_fields["build_or_runtime"] == "runtime"
