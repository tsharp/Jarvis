from core.task_loop.capabilities.container.context import (
    build_container_context,
    capability_request_params,
    merge_container_context,
)
from core.task_loop.capabilities.container.extractors import extract_container_identity_fields
from core.task_loop.contracts import RiskLevel, TaskLoopSnapshot


def test_extract_container_identity_fields_does_not_treat_anfordern_as_identity():
    out = extract_container_identity_fields(
        "Bitte plane, wie du einen python-Container anfordern wuerdest."
    )

    assert out == {}


def test_extract_container_identity_fields_keeps_explicit_identity_markers():
    out = extract_container_identity_fields(
        "Bitte pruefe container_id=abc-123 und container_name=python-sandbox."
    )

    assert out["container_id"] == "abc-123"
    assert out["container_name"] == "python-sandbox"


def test_build_container_context_marks_python_request_and_extracts_fields():
    out = build_container_context(
        "Ich brauche einen Python 3.11 Container mit requirements.txt",
        thinking_plan={
            "intent": "Python-Container fuer Datenanalyse vorbereiten",
            "suggested_tools": ["request_container"],
        },
        selected_tools=["request_container"],
    )

    assert out["request_family"] == "python_container"
    assert out["python_requested"] is True
    assert out["known_fields"]["python_version"] == "3.11"
    assert out["known_fields"]["dependency_spec"] == "requirements.txt"


def test_merge_container_context_keeps_selected_blueprint_and_filters_request_params():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-container-context",
        conversation_id="conv-container-context",
        plan_id="plan-container-context",
        current_step_id="step-2",
        current_plan=["Container-Anfrage ausfuehren"],
        plan_steps=[],
        pending_step="Container-Anfrage ausfuehren",
        risk_level=RiskLevel.SAFE,
        verified_artifacts=[
            {
                "artifact_type": "container_capability_context",
                "context": {
                    "request_family": "python_container",
                    "python_requested": True,
                    "known_fields": {"python_version": "3.11"},
                },
            },
            {
                "artifact_type": "container_request_params",
                "params": {"runtime": "nvidia", "cpu_cores": 8},
            },
        ],
    )

    merged = merge_container_context(
        {"request_family": "python_container", "python_requested": True, "known_fields": {}},
        snapshot=snapshot,
        selected_blueprint={"blueprint_id": "python-sandbox"},
    )

    params = capability_request_params(merged)

    assert merged["known_fields"]["blueprint"] == "python-sandbox"
    assert params == {
        "python_version": "3.11",
        "runtime": "nvidia",
        "cpu_cores": 8,
    }
