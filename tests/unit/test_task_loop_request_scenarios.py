import pytest

from core.task_loop.contracts import RiskLevel, TaskLoopSnapshot, TaskLoopStepType
from core.task_loop.planner import build_task_loop_steps
from core.task_loop.step_runtime import execute_task_loop_step


PYTHON_CONTAINER_REQUEST = """Bitte plane und bearbeite die folgende Aufgabe sichtbar in mehreren Schritten:
  Pruefe, wie du einen python-Container anfordern wuerdest, nenne erst den aktuellen Schritt, zeige Zwischenstaende, und
  frage nach fehlenden Angaben, falls du fuer die Anfrage noch Parameter brauchst."""


SCENARIOS = [
    {
        "id": "basis",
        "prompt": PYTHON_CONTAINER_REQUEST,
        "thinking_plan": {
            "intent": "Python-Container kontrolliert anfordern",
            "hallucination_risk": "low",
            "suggested_tools": ["request_container"],
        },
        "route_kind": "read_first",
    },
    {
        "id": "anti_halluzination",
        "prompt": (
            "Bearbeite die Aufgabe nur mit Informationen, die du tatsaechlich pruefen kannst. "
            "Trenne strikt zwischen geprueft, unklar und angenommener Default-Option. "
            "Ich moechte einen neuen Python-Container fuer Datenanalyse vorbereiten."
        ),
        "thinking_plan": {
            "intent": "Python-Container fuer Datenanalyse kontrolliert vorbereiten",
            "hallucination_risk": "low",
            "suggested_tools": ["request_container"],
        },
        "route_kind": "read_first",
    },
    {
        "id": "read_first_blueprint_check",
        "prompt": (
            "Bevor du einen neuen Python-Container anforderst, pruefe zuerst sichtbar, "
            "ob bereits ein geeigneter Container oder Blueprint existiert."
        ),
        "thinking_plan": {
            "intent": "Vorhandene Python-Container-Optionen zuerst pruefen",
            "hallucination_risk": "low",
            "suggested_tools": ["blueprint_list", "request_container"],
        },
        "route_kind": "read_first",
    },
    {
        "id": "security_review",
        "prompt": (
            "Ich moechte einen Python-Container mit erweiterten Rechten. "
            "Plane die Anfrage sichtbar, aber pruefe zuerst, ob die Rechte wirklich noetig "
            "und vertretbar sind."
        ),
        "thinking_plan": {
            "intent": "Python-Container mit Rechten kontrolliert anfragen",
            "hallucination_risk": "medium",
            "suggested_tools": ["request_container"],
        },
        "route_kind": "read_first",
    },
    {
        "id": "conflict_detection",
        "prompt": (
            "Ich brauche einen minimalen Python-Container, der gleichzeitig GPU, Jupyter, GUI "
            "und maximale Isolation bietet. Analysiere zuerst die Zielkonflikte, bevor du etwas vorschlaegst."
        ),
        "thinking_plan": {
            "intent": "Widerspruechliche Python-Container-Anforderungen klaeren",
            "hallucination_risk": "medium",
            "suggested_tools": ["request_container"],
        },
        "route_kind": "read_first",
    },
    {
        "id": "approval_gate",
        "prompt": (
            "Arbeite die Aufgabe autonom vor, aber stoppe an dem Punkt, an dem eine echte Anforderung "
            "ausgeloest wuerde, und zeige stattdessen einen finalen Entwurf zur Freigabe."
        ),
        "thinking_plan": {
            "intent": "Python-Container bis zum Freigabepunkt vorbereiten",
            "hallucination_risk": "low",
            "suggested_tools": ["request_container"],
        },
        "route_kind": "read_first",
    },
    {
        "id": "tool_routing",
        "prompt": (
            "Zeige zuerst, welche Informationen ueber laufende Container, installierbare Container "
            "oder Blueprints du pruefen wuerdest, bevor du einen Python-Container beantragst."
        ),
        "thinking_plan": {
            "intent": "Laufende Container und Blueprints vor Python-Anfrage pruefen",
            "hallucination_risk": "low",
            "suggested_tools": ["blueprint_list", "request_container"],
        },
        "route_kind": "read_first",
    },
    {
        "id": "context_stability",
        "prompt": (
            "Bearbeite die Aufgabe in vier Phasen: Bedarf klaeren, vorhandene Optionen pruefen, "
            "sicheren Vorschlag vorbereiten, offene Fragen zusammenfassen. "
            "Bleibe in jeder Phase bei den bereits festgestellten Fakten."
        ),
        "thinking_plan": {
            "intent": "Python-Container phasenweise und faktenbasiert vorbereiten",
            "hallucination_risk": "low",
            "suggested_tools": ["blueprint_list", "request_container"],
        },
        "route_kind": "read_first",
    },
]


class _Control:
    async def verify(
        self,
        user_text,
        thinking_plan,
        retrieved_memory="",
        response_mode="interactive",
    ):
        return {
            "approved": True,
            "decision_class": "allow",
            "warnings": [],
            "final_instruction": "",
        }


def _find_step(steps, title):
    for step in steps:
        if step.title == title:
            return step
    raise AssertionError(f"Missing task-loop step: {title}")


def test_python_container_request_plans_visible_request_before_execution():
    steps = build_task_loop_steps(
        PYTHON_CONTAINER_REQUEST,
        thinking_plan={
            "intent": "Python-Container kontrolliert anfordern",
            "hallucination_risk": "low",
            "suggested_tools": ["request_container"],
        },
    )

    assert steps[0].title == (
        "Container-Anforderungsziel klaeren: Python-Container kontrolliert anfordern"
    )
    assert steps[1].title == "Verfuegbare Blueprints oder Container-Basis pruefen"
    assert steps[1].suggested_tools == ["blueprint_list"]
    assert steps[2].title == "Container-Anfrage zur Freigabe vorbereiten"
    assert steps[3].title == "Container-Anfrage ausfuehren"
    assert steps[2].step_type is TaskLoopStepType.TOOL_REQUEST
    assert steps[3].step_type is TaskLoopStepType.TOOL_EXECUTION
    assert steps[2].requires_user is True
    assert steps[2].risk_level is RiskLevel.NEEDS_CONFIRMATION
    assert steps[2].suggested_tools == ["request_container"]
    assert steps[3].suggested_tools == ["request_container"]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[item["id"] for item in SCENARIOS])
def test_container_request_prompt_matrix_keeps_visible_planning_and_safe_tool_order(scenario):
    steps = build_task_loop_steps(
        scenario["prompt"],
        thinking_plan=scenario["thinking_plan"],
    )

    assert steps[0].title.startswith("Container-Anforderungsziel klaeren:")
    assert steps[-1].step_type is TaskLoopStepType.RESPONSE

    if scenario["route_kind"] == "request_first":
        assert steps[1].title == "Fehlende Container-Angaben sammeln"
        request_step = _find_step(steps, "Container-Anfrage zur Freigabe vorbereiten")
        execution_step = _find_step(steps, "Container-Anfrage ausfuehren")

        assert request_step.step_type is TaskLoopStepType.TOOL_REQUEST
        assert execution_step.step_type is TaskLoopStepType.TOOL_EXECUTION
        assert request_step.requires_user is True
        assert request_step.risk_level is RiskLevel.NEEDS_CONFIRMATION
        assert request_step.suggested_tools == ["request_container"]
        assert execution_step.suggested_tools == ["request_container"]
    else:
        discovery_step = _find_step(steps, "Verfuegbare Blueprints oder Container-Basis pruefen")
        request_step = _find_step(steps, "Container-Anfrage zur Freigabe vorbereiten")
        execution_step = _find_step(steps, "Container-Anfrage ausfuehren")

        assert steps[1].title == discovery_step.title
        assert discovery_step.step_type is TaskLoopStepType.TOOL_EXECUTION
        assert discovery_step.suggested_tools == ["blueprint_list"]
        assert request_step.step_id == "step-3"
        assert request_step.step_type is TaskLoopStepType.TOOL_REQUEST
        assert request_step.suggested_tools == ["request_container"]
        assert execution_step.step_type is TaskLoopStepType.TOOL_EXECUTION
        assert execution_step.suggested_tools == ["request_container"]


@pytest.mark.asyncio
async def test_python_container_request_waits_for_missing_parameters_before_execution():
    steps = build_task_loop_steps(
        PYTHON_CONTAINER_REQUEST,
        thinking_plan={
            "intent": "Python-Container kontrolliert anfordern",
            "hallucination_risk": "low",
            "suggested_tools": ["request_container"],
        },
    )
    request_step = steps[2]
    snapshot = TaskLoopSnapshot(
        objective_id="obj-python-container",
        conversation_id="conv-python-container",
        plan_id="plan-python-container",
        current_step_id=request_step.step_id,
        current_step_type=request_step.step_type,
        current_plan=[step.title for step in steps],
        plan_steps=[step.to_dict() for step in steps],
        pending_step=request_step.title,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        verified_artifacts=[],
    )

    result = await execute_task_loop_step(
        request_step.title,
        request_step.to_dict(),
        snapshot,
        control_layer=_Control(),
        output_layer=None,
        orchestrator_bridge=None,
        fallback_fn=lambda *args, **kwargs: "fallback",
    )

    assert result.step_result.step_type is TaskLoopStepType.TOOL_REQUEST
    assert result.step_result.status.value == "waiting_for_user"
    assert "Bitte nenne mindestens den gewuenschten Blueprint" in result.visible_text
    assert "Python-Version" in result.visible_text or "Python-Version" in result.visible_text
    assert "requirements.txt" in result.visible_text or "Abhaengigkeiten" in result.visible_text
    assert "Build" in result.visible_text or "Runtime" in result.visible_text


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", SCENARIOS, ids=[item["id"] for item in SCENARIOS])
async def test_container_scenarios_request_step_stops_for_missing_parameters(scenario):
    steps = build_task_loop_steps(
        scenario["prompt"],
        thinking_plan=scenario["thinking_plan"],
    )
    request_step = _find_step(steps, "Container-Anfrage zur Freigabe vorbereiten")
    snapshot = TaskLoopSnapshot(
        objective_id=f"obj-{scenario['id']}",
        conversation_id=f"conv-{scenario['id']}",
        plan_id=f"plan-{scenario['id']}",
        current_step_id=request_step.step_id,
        current_step_type=request_step.step_type,
        current_plan=[step.title for step in steps],
        plan_steps=[step.to_dict() for step in steps],
        pending_step=request_step.title,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        verified_artifacts=[],
    )

    result = await execute_task_loop_step(
        request_step.title,
        request_step.to_dict(),
        snapshot,
        control_layer=_Control(),
        output_layer=None,
        orchestrator_bridge=None,
        fallback_fn=lambda *args, **kwargs: "fallback",
    )

    assert result.step_result.step_type is TaskLoopStepType.TOOL_REQUEST
    assert result.step_result.status.value == "waiting_for_user"
    assert "Bitte nenne mindestens den gewuenschten Blueprint" in result.visible_text


@pytest.mark.asyncio
async def test_python_container_request_asks_for_python_specific_required_fields():
    steps = build_task_loop_steps(
        PYTHON_CONTAINER_REQUEST,
        thinking_plan={
            "intent": "Python-Container kontrolliert anfordern",
            "hallucination_risk": "low",
            "suggested_tools": ["request_container"],
            "_container_capability_context": {
                "request_family": "python_container",
                "python_requested": True,
                "known_fields": {},
            },
        },
    )
    request_step = _find_step(steps, "Container-Anfrage zur Freigabe vorbereiten")
    snapshot = TaskLoopSnapshot(
        objective_id="obj-python-contract-gap",
        conversation_id="conv-python-contract-gap",
        plan_id="plan-python-contract-gap",
        current_step_id=request_step.step_id,
        current_step_type=request_step.step_type,
        current_plan=[step.title for step in steps],
        plan_steps=[step.to_dict() for step in steps],
        pending_step=request_step.title,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        verified_artifacts=[],
    )

    result = await execute_task_loop_step(
        request_step.title,
        request_step.to_dict(),
        snapshot,
        control_layer=_Control(),
        output_layer=None,
        orchestrator_bridge=None,
        fallback_fn=lambda *args, **kwargs: "fallback",
    )

    assert result.step_result.step_type is TaskLoopStepType.TOOL_REQUEST
    assert result.step_result.status.value == "waiting_for_user"
    assert "Python-Version" in result.visible_text or "Python version" in result.visible_text
    assert "requirements.txt" in result.visible_text or "Abhaengigkeiten" in result.visible_text
    assert "Build" in result.visible_text or "Runtime" in result.visible_text
