from core.task_loop.contracts import (
    TaskLoopSnapshot,
    TaskLoopState,
    TaskLoopStepExecutionSource,
    TaskLoopStepStatus,
    TaskLoopStepType,
)
from core.task_loop.unresolved_context import (
    UnresolvedTaskContext,
    build_unresolved_task_response,
    is_actionable_unresolved_followup,
    is_explanatory_unresolved_followup,
    maybe_build_unresolved_task_context,
)


def _completed_snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        objective_id="obj-1",
        conversation_id="conv-1",
        plan_id="plan-1",
        state=TaskLoopState.COMPLETED,
        current_step_id="step-3",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_step_status=TaskLoopStepStatus.COMPLETED,
        step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
        current_plan=["Blueprints pruefen", "Container starten"],
        completed_steps=["Blueprints pruefen", "Container starten"],
        objective_summary="Python-Entwicklungscontainer starten",
        verified_artifacts=[
            {
                "artifact_type": "container_capability_context",
                "context": {
                    "request_family": "python_container",
                    "known_fields": {"python_version": "3.11"},
                },
            },
            {
                "artifact_type": "execution_result",
                "metadata": {
                    "grounding_evidence": [
                        {
                            "tool_name": "blueprint_list",
                            "structured": {
                                "blueprints": [
                                    {"id": "python-sandbox", "name": "Python Sandbox"},
                                ]
                            },
                        }
                    ]
                },
            },
        ],
        last_step_result={
            "execution_result": {
                "tool_statuses": [
                    {
                        "tool_name": "request_container",
                        "status": "routing_block",
                        "reason": "no_jit_match",
                    }
                ]
            }
        },
    )


def test_maybe_build_unresolved_task_context_for_terminal_snapshot():
    ctx = maybe_build_unresolved_task_context(_completed_snapshot())

    assert ctx is not None
    assert ctx.task_topic == "Python-Entwicklungscontainer starten"
    assert ctx.blocker == "request_container:no_jit_match"
    assert ctx.capability_context["request_family"] == "python_container"


def test_build_unresolved_task_response_uses_work_context_next_step_fallback():
    ctx = UnresolvedTaskContext(
        conversation_id="conv-1",
        source_state="completed",
        task_topic="Python-Entwicklungscontainer starten",
        blocker="request_container:no_jit_match",
        next_step="",
        capability_context={"request_family": "python_container"},
        selected_blueprint={},
        discovered_blueprints=[],
        next_tools=[],
    )

    response = build_unresolved_task_response(ctx)

    assert "Offen ist aktuell noch: Python-Entwicklungscontainer starten." in response
    assert "Naechster sinnvoller Schritt: Offenen technischen Blocker pruefen." in response


def test_unresolved_followup_marker_helpers_still_match_expected_intents():
    assert is_explanatory_unresolved_followup("was fehlt noch?") is True
    assert is_actionable_unresolved_followup("pruef die Blueprints jetzt") is True
    assert is_actionable_unresolved_followup("was fehlt noch?") is False
