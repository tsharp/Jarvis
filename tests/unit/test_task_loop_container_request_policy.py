from core.task_loop.capabilities.container.request_policy import (
    build_container_request_context,
    resolve_blueprint_selection,
)
from core.task_loop.contracts import RiskLevel, TaskLoopSnapshot


def _snapshot_with_blueprints() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        objective_id="obj-container-request-policy",
        conversation_id="conv-container-request-policy",
        plan_id="plan-container-request-policy",
        current_step_id="step-1",
        current_plan=["Container-Anfrage zur Freigabe vorbereiten"],
        plan_steps=[],
        pending_step="Container-Anfrage zur Freigabe vorbereiten",
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        verified_artifacts=[
            {
                "artifact_type": "execution_result",
                "done_reason": "success",
                "tool_statuses": [{"tool_name": "blueprint_list", "status": "ok", "reason": ""}],
                "grounding": {"tool_name": "blueprint_list"},
                "metadata": {
                    "grounding_evidence": [
                        {
                            "tool_name": "blueprint_list",
                            "status": "ok",
                            "structured": {
                                "blueprints": [
                                    {"blueprint_id": "gaming-station", "name": "Gaming Station"},
                                    {"blueprint_id": "gaming-lite", "name": "Gaming Lite"},
                                ]
                            },
                        }
                    ]
                },
            }
        ],
    )


def test_resolve_blueprint_selection_matches_user_reply_against_label():
    selected = resolve_blueprint_selection(
        _snapshot_with_blueprints(),
        user_reply="Bitte nimm Gaming Lite.",
    )

    assert selected == {"blueprint_id": "gaming-lite", "label": "Gaming Lite"}


def test_build_container_request_context_requires_user_choice_for_multiple_blueprints():
    context = build_container_request_context(
        _snapshot_with_blueprints(),
        requested_capability={
            "capability_type": "container_manager",
            "capability_action": "request_container",
        },
    )

    assert context["requires_user_choice"] is True
    assert "Gaming Station" in context["waiting_message"]
    assert "Gaming Lite" in context["waiting_message"]


def test_build_container_request_context_auto_selects_single_python_match():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-container-request-policy",
        conversation_id="conv-container-request-policy",
        plan_id="plan-container-request-policy",
        current_step_id="step-1",
        current_plan=["Container-Anfrage zur Freigabe vorbereiten"],
        plan_steps=[],
        pending_step="Container-Anfrage zur Freigabe vorbereiten",
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        verified_artifacts=[
            {
                "artifact_type": "execution_result",
                "done_reason": "success",
                "tool_statuses": [{"tool_name": "blueprint_list", "status": "ok", "reason": ""}],
                "grounding": {"tool_name": "blueprint_list"},
                "metadata": {
                    "grounding_evidence": [
                        {
                            "tool_name": "blueprint_list",
                            "status": "ok",
                            "structured": {
                                "blueprints": [
                                    {"blueprint_id": "db-sandbox", "name": "Database Sandbox", "tags": ["database"]},
                                    {"blueprint_id": "python-sandbox", "name": "Python Sandbox", "tags": ["python", "sandbox"]},
                                    {"blueprint_id": "shell-sandbox", "name": "Shell Sandbox", "tags": ["shell"]},
                                ]
                            },
                        }
                    ]
                },
            }
        ],
    )

    context = build_container_request_context(
        snapshot,
        requested_capability={
            "capability_type": "container_manager",
            "capability_action": "request_container",
        },
        capability_context={"request_family": "python_container"},
    )

    assert context["requires_user_choice"] is False
    assert context["selected_blueprint"] == {
        "blueprint_id": "python-sandbox",
        "label": "Python Sandbox",
    }
