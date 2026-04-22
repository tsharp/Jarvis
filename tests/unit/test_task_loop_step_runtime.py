from core.task_loop.contracts import (
    RiskLevel,
    TaskLoopSnapshot,
    TaskLoopStepStatus,
    TaskLoopStepType,
)
from core.task_loop.step_runtime import (
    build_task_loop_step_prompt,
    build_task_loop_step_request,
    execute_task_loop_step,
)


class _Control:
    async def verify(self, user_text, thinking_plan, retrieved_memory="", response_mode="interactive"):
        return {
            "approved": True,
            "decision_class": "allow",
            "warnings": [],
            "final_instruction": "",
        }


class _Bridge:
    async def _collect_control_tool_decisions(self, user_text, verified_plan, *, control_decision=None, stream=False):
        return {"request_container": {"blueprint_id": "gaming-station"}}

    def _resolve_execution_suggested_tools(
        self,
        user_text,
        verified_plan,
        control_tool_decisions,
        *,
        control_decision=None,
        stream=False,
        enable_skill_trigger_router=False,
        conversation_id="",
        chat_history=None,
    ):
        return [{"name": "request_container", "arguments": {"blueprint_id": "gaming-station"}}]

    def _execute_tools_sync(
        self,
        suggested_tools,
        user_text,
        control_tool_decisions=None,
        *,
        last_assistant_msg="",
        control_decision=None,
        time_reference=None,
        thinking_suggested_tools=None,
        blueprint_gate_blocked=False,
        blueprint_router_id=None,
        blueprint_suggest_msg="",
        session_id="",
        verified_plan=None,
    ):
        verified_plan["_execution_result"] = {
            "done_reason": "success",
            "tool_statuses": [{"tool_name": "request_container", "status": "ok", "reason": ""}],
            "grounding": {"tool_name": "request_container"},
            "direct_response": "Container-Anfrage wurde erfolgreich ausgefuehrt.",
            "metadata": {"bridge": "task_loop"},
        }
        return "Container-Anfrage wurde erfolgreich ausgefuehrt."


async def _fallback_fn(step_index, step_title, step_meta, completed_steps):
    return f"Fallback {step_index}: {step_title}"


def _snapshot(step_type: TaskLoopStepType) -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        objective_id="obj-step-runtime",
        conversation_id="conv-step-runtime",
        plan_id="plan-step-runtime",
        current_step_id="step-1",
        current_step_type=step_type,
        current_plan=["Container kontrolliert anfragen"],
        plan_steps=[],
        pending_step="Container kontrolliert anfragen",
        risk_level=RiskLevel.SAFE,
    )


async def _run(step_type: TaskLoopStepType):
    return await execute_task_loop_step(
        "Container kontrolliert anfragen",
        {
            "step_id": "step-1",
            "title": "Container kontrolliert anfragen",
            "goal": "Den Container kontrolliert anfragen.",
            "done_criteria": "Ein verifizierter Tool-Befund liegt vor.",
            "risk_level": "safe",
            "requires_user": False,
            "suggested_tools": ["request_container"],
            "task_kind": "implementation",
            "objective": "Gaming-Container kontrolliert starten",
            "step_type": step_type.value,
            "requested_capability": {
                "capability_type": "container_manager",
                "capability_target": "request_container",
                "capability_action": "request_container",
            },
        },
        _snapshot(step_type),
        control_layer=_Control(),
        output_layer=None,
        orchestrator_bridge=_Bridge(),
        fallback_fn=lambda *args, **kwargs: "fallback",
    )


import pytest


@pytest.mark.asyncio
async def test_execute_task_loop_step_preserves_tool_request_type_in_runtime_result():
    result = await _run(TaskLoopStepType.TOOL_REQUEST)

    assert result.step_result.step_type is TaskLoopStepType.TOOL_REQUEST


@pytest.mark.asyncio
async def test_execute_task_loop_step_preserves_tool_execution_type_in_runtime_result():
    result = await _run(TaskLoopStepType.TOOL_EXECUTION)

    assert result.step_result.step_type is TaskLoopStepType.TOOL_EXECUTION


@pytest.mark.asyncio
async def test_execute_task_loop_step_waits_for_user_when_multiple_blueprints_are_discovered():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-step-runtime",
        conversation_id="conv-step-runtime",
        plan_id="plan-step-runtime",
        current_step_id="step-1",
        current_step_type=TaskLoopStepType.TOOL_REQUEST,
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

    result = await execute_task_loop_step(
        "Container-Anfrage zur Freigabe vorbereiten",
        {
            "step_id": "step-1",
            "title": "Container-Anfrage zur Freigabe vorbereiten",
            "goal": "Die eigentliche Container-Anfrage fuer einen gewaehlten Blueprint vorbereiten.",
            "done_criteria": "Die Anfrage ist als sichtbarer Freigabe-Schritt vorbereitet.",
            "risk_level": "needs_confirmation",
            "requires_user": True,
            "suggested_tools": ["request_container"],
            "task_kind": "implementation",
            "objective": "Gaming-Container kontrolliert starten",
            "step_type": TaskLoopStepType.TOOL_REQUEST.value,
            "requested_capability": {
                "capability_type": "container_manager",
                "capability_target": "request_container",
                "capability_action": "request_container",
            },
        },
        snapshot,
        control_layer=_Control(),
        output_layer=None,
        orchestrator_bridge=None,
        fallback_fn=lambda *args, **kwargs: "fallback",
    )

    assert result.step_result.status.value == "waiting_for_user"
    assert "Gaming Station" in result.visible_text
    assert "Gaming Lite" in result.visible_text


@pytest.mark.asyncio
async def test_execute_task_loop_step_waits_for_user_when_container_request_params_are_missing():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-step-runtime",
        conversation_id="conv-step-runtime",
        plan_id="plan-step-runtime",
        current_step_id="step-1",
        current_step_type=TaskLoopStepType.TOOL_REQUEST,
        current_plan=["Container-Anfrage zur Freigabe vorbereiten"],
        plan_steps=[],
        pending_step="Container-Anfrage zur Freigabe vorbereiten",
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        verified_artifacts=[],
    )

    result = await execute_task_loop_step(
        "Container-Anfrage zur Freigabe vorbereiten",
        {
            "step_id": "step-1",
            "title": "Container-Anfrage zur Freigabe vorbereiten",
            "goal": "Die eigentliche Container-Anfrage fuer einen gewaehlten Blueprint vorbereiten.",
            "done_criteria": "Die Anfrage ist als sichtbarer Freigabe-Schritt vorbereitet.",
            "risk_level": "needs_confirmation",
            "requires_user": True,
            "suggested_tools": ["request_container"],
            "task_kind": "implementation",
            "objective": "Gaming-Container kontrolliert starten",
            "step_type": TaskLoopStepType.TOOL_REQUEST.value,
            "requested_capability": {
                "capability_type": "container_manager",
                "capability_target": "request_container",
                "capability_action": "request_container",
            },
        },
        snapshot,
        control_layer=_Control(),
        output_layer=None,
        orchestrator_bridge=None,
        fallback_fn=lambda *args, **kwargs: "fallback",
    )

    assert result.step_result.status.value == "waiting_for_user"
    assert "Blueprint" in result.visible_text
    assert "CPU" in result.visible_text or "RAM" in result.visible_text or "GPU" in result.visible_text


@pytest.mark.asyncio
async def test_execute_task_loop_step_emits_container_recovery_hint_for_request_container_routing_block():
    class _RecoveryBridge:
        async def _collect_control_tool_decisions(self, user_text, verified_plan, *, control_decision=None, stream=False):
            return {}

        def _resolve_execution_suggested_tools(
            self,
            user_text,
            verified_plan,
            control_tool_decisions,
            *,
            control_decision=None,
            stream=False,
            enable_skill_trigger_router=False,
            conversation_id="",
            chat_history=None,
        ):
            return [{"name": "request_container", "arguments": {}}]

        def _execute_tools_sync(
            self,
            suggested_tools,
            user_text,
            control_tool_decisions=None,
            *,
            last_assistant_msg="",
            control_decision=None,
            time_reference=None,
            thinking_suggested_tools=None,
            blueprint_gate_blocked=False,
            blueprint_router_id=None,
            blueprint_suggest_msg="",
            session_id="",
            verified_plan=None,
        ):
            verified_plan["_execution_result"] = {
                "done_reason": "routing_block",
                "tool_statuses": [
                    {
                        "tool_name": "request_container",
                        "status": "routing_block",
                        "reason": "no_jit_match",
                    }
                ],
                "grounding": {},
                "direct_response": "",
                "metadata": {"bridge": "task_loop"},
            }
            return ""

    result = await execute_task_loop_step(
        "Container-Anfrage ausfuehren",
        {
            "step_id": "step-4",
            "title": "Container-Anfrage ausfuehren",
            "goal": "Die freigegebene Container-Anfrage ueber den Orchestrator kontrolliert ausfuehren.",
            "done_criteria": "Ein verifizierter Tool-Befund fuer die Container-Anfrage liegt vor.",
            "risk_level": "safe",
            "requires_user": False,
            "suggested_tools": ["request_container"],
            "task_kind": "implementation",
            "objective": "Python-Container kontrolliert anfordern",
            "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
            "requested_capability": {
                "capability_type": "container_manager",
                "capability_target": "request_container",
                "capability_action": "request_container",
            },
            "capability_context": {
                "request_family": "python_container",
                "python_requested": True,
                "known_fields": {},
            },
        },
        TaskLoopSnapshot(
            objective_id="obj-step-runtime-recovery",
            conversation_id="conv-step-runtime-recovery",
            plan_id="plan-step-runtime-recovery",
            current_step_id="step-4",
            current_step_type=TaskLoopStepType.TOOL_EXECUTION,
            current_plan=["Container-Anfrage ausfuehren"],
            plan_steps=[],
            pending_step="Container-Anfrage ausfuehren",
            risk_level=RiskLevel.SAFE,
        ),
        control_layer=_Control(),
        output_layer=None,
        orchestrator_bridge=_RecoveryBridge(),
        fallback_fn=lambda *args, **kwargs: "fallback",
    )

    assert result.step_result.status.value == "completed"
    assert result.step_result.next_action == "replan_recovery"
    recovery_artifacts = [
        artifact
        for artifact in result.step_result.verified_artifacts
        if artifact.get("artifact_type") == "container_recovery_hint"
    ]
    assert recovery_artifacts
    assert recovery_artifacts[-1]["recovery_mode"] == "replan_with_tools"
    assert recovery_artifacts[-1]["next_tools"] == ["blueprint_list"]
    assert "Blueprint" in result.visible_text or "Container-Basen" in result.visible_text


@pytest.mark.asyncio
async def test_execute_task_loop_step_uses_action_resolution_when_no_resolved_tools_exist():
    class _NoResolvedToolsBridge:
        async def _collect_control_tool_decisions(self, user_text, verified_plan, *, control_decision=None, stream=False):
            return {}

        def _resolve_execution_suggested_tools(
            self,
            user_text,
            verified_plan,
            control_tool_decisions,
            *,
            control_decision=None,
            stream=False,
            enable_skill_trigger_router=False,
            conversation_id="",
            chat_history=None,
        ):
            return []

    result = await execute_task_loop_step(
        "Container-Anfrage ausfuehren",
        {
            "step_id": "step-4",
            "title": "Container-Anfrage ausfuehren",
            "goal": "Die freigegebene Container-Anfrage ueber den Orchestrator kontrolliert ausfuehren.",
            "done_criteria": "Ein verifizierter Tool-Befund fuer die Container-Anfrage liegt vor.",
            "risk_level": "safe",
            "requires_user": False,
            "suggested_tools": ["request_container"],
            "task_kind": "implementation",
            "objective": "Python-Container kontrolliert anfordern",
            "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
            "requested_capability": {
                "capability_type": "container_manager",
                "capability_target": "request_container",
                "capability_action": "request_container",
            },
            "capability_context": {
                "request_family": "python_container",
                "known_fields": {
                    "python_version": "3.11",
                    "dependency_spec": "requirements.txt",
                    "build_or_runtime": "runtime",
                },
                "missing_fields": ["blueprint"],
            },
        },
        TaskLoopSnapshot(
            objective_id="obj-step-runtime-auto-clarify",
            conversation_id="conv-step-runtime-auto-clarify",
            plan_id="plan-step-runtime-auto-clarify",
            current_step_id="step-4",
            current_step_type=TaskLoopStepType.TOOL_EXECUTION,
            current_plan=["Container-Anfrage ausfuehren"],
            plan_steps=[],
            pending_step="Container-Anfrage ausfuehren",
            risk_level=RiskLevel.SAFE,
        ),
        control_layer=_Control(),
        output_layer=None,
        orchestrator_bridge=_NoResolvedToolsBridge(),
        fallback_fn=lambda *args, **kwargs: "fallback",
    )

    assert result.step_result.status is TaskLoopStepStatus.COMPLETED
    assert result.step_result.next_action == "replan_recovery"
    recovery_artifacts = [
        artifact
        for artifact in result.step_result.verified_artifacts
        if artifact.get("artifact_type") == "container_recovery_hint"
    ]
    assert recovery_artifacts
    assert recovery_artifacts[-1]["recovery_mode"] == "replan_with_tools"
    assert recovery_artifacts[-1]["next_tools"] == ["blueprint_list"]


def test_build_task_loop_step_prompt_carries_forward_last_confirmed_user_reply():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-step-runtime",
        conversation_id="conv-step-runtime",
        plan_id="plan-step-runtime",
        current_step_id="step-2",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_plan=[
            "Container-Anfrage zur Freigabe vorbereiten",
            "Container-Anfrage ausfuehren",
        ],
        plan_steps=[],
        pending_step="Container-Anfrage ausfuehren",
        risk_level=RiskLevel.SAFE,
        verified_artifacts=[
            {
                "artifact_type": "user_reply",
                "content": "nimm bitte gaming-station",
            }
        ],
    )

    prompt = build_task_loop_step_prompt(
        "Container-Anfrage ausfuehren",
        {
            "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
            "goal": "Den angefragten Container ausfuehren.",
            "done_criteria": "Ein verifizierter Ausfuehrungsbefund liegt vor.",
            "suggested_tools": ["request_container"],
            "objective": "Gaming-Container kontrolliert starten",
        },
        snapshot,
    )

    assert "Zuletzt bestaetigte User-Angabe: nimm bitte gaming-station" in prompt


def test_build_task_loop_step_prompt_carries_forward_selected_blueprint():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-step-runtime",
        conversation_id="conv-step-runtime",
        plan_id="plan-step-runtime",
        current_step_id="step-2",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_plan=[
            "Container-Anfrage zur Freigabe vorbereiten",
            "Container-Anfrage ausfuehren",
        ],
        plan_steps=[],
        pending_step="Container-Anfrage ausfuehren",
        risk_level=RiskLevel.SAFE,
        verified_artifacts=[
            {
                "artifact_type": "blueprint_selection",
                "blueprint_id": "gaming-station",
                "content": "Gaming Station",
            }
        ],
    )

    prompt = build_task_loop_step_prompt(
        "Container-Anfrage ausfuehren",
        {
            "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
            "goal": "Den angefragten Container ausfuehren.",
            "done_criteria": "Ein verifizierter Ausfuehrungsbefund liegt vor.",
            "suggested_tools": ["request_container"],
            "objective": "Gaming-Container kontrolliert starten",
            "requested_capability": {
                "capability_type": "container_manager",
                "capability_target": "request_container",
                "capability_action": "request_container",
            },
        },
        snapshot,
    )

    assert "Aktuell gewaehlter Blueprint: Gaming Station" in prompt


def test_build_task_loop_step_prompt_carries_forward_container_request_params():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-step-runtime",
        conversation_id="conv-step-runtime",
        plan_id="plan-step-runtime",
        current_step_id="step-2",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_plan=[
            "Container-Anfrage zur Freigabe vorbereiten",
            "Container-Anfrage ausfuehren",
        ],
        plan_steps=[],
        pending_step="Container-Anfrage ausfuehren",
        risk_level=RiskLevel.SAFE,
        verified_artifacts=[
            {
                "artifact_type": "blueprint_selection",
                "blueprint_id": "gaming-station",
                "content": "Gaming Station",
            },
            {
                "artifact_type": "container_request_params",
                "params": {
                    "cpu_cores": 8,
                    "ram": "16 GB",
                    "runtime": "nvidia",
                },
            },
        ],
    )

    prompt = build_task_loop_step_prompt(
        "Container-Anfrage ausfuehren",
        {
            "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
            "goal": "Den angefragten Container ausfuehren.",
            "done_criteria": "Ein verifizierter Ausfuehrungsbefund liegt vor.",
            "suggested_tools": ["request_container"],
            "objective": "Gaming-Container kontrolliert starten",
            "requested_capability": {
                "capability_type": "container_manager",
                "capability_target": "request_container",
                "capability_action": "request_container",
            },
        },
        snapshot,
    )

    assert "Erkannte Request-Parameter: cpu_cores=8, ram=16 GB, runtime=nvidia" in prompt


def test_build_task_loop_step_prompt_carries_forward_verified_tool_answer():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-step-runtime",
        conversation_id="conv-step-runtime",
        plan_id="plan-step-runtime",
        current_step_id="step-2",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_plan=[
            "Container-Anfrage zur Freigabe vorbereiten",
            "Container-Anfrage ausfuehren",
        ],
        plan_steps=[],
        pending_step="Container-Anfrage ausfuehren",
        risk_level=RiskLevel.SAFE,
        verified_artifacts=[
            {
                "artifact_type": "execution_result",
                "done_reason": "success",
                "direct_response": "Container-Anfrage wurde erfolgreich ausgefuehrt.",
                "tool_statuses": [{"tool_name": "request_container", "status": "ok", "reason": ""}],
                "grounding": {"tool_name": "request_container"},
                "metadata": {},
            }
        ],
    )

    prompt = build_task_loop_step_prompt(
        "Container-Anfrage ausfuehren",
        {
            "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
            "goal": "Den angefragten Container ausfuehren.",
            "done_criteria": "Ein verifizierter Ausfuehrungsbefund liegt vor.",
            "suggested_tools": ["request_container"],
            "objective": "Gaming-Container kontrolliert starten",
        },
        snapshot,
    )

    assert "Zuletzt verifizierte Tool-Antwort: Container-Anfrage wurde erfolgreich ausgefuehrt." in prompt
    assert "Letzte Tool-Statuses: request_container=ok" in prompt


def test_build_task_loop_step_prompt_carries_forward_grounding_evidence_facts():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-step-runtime",
        conversation_id="conv-step-runtime",
        plan_id="plan-step-runtime",
        current_step_id="step-2",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_plan=[
            "Blueprints pruefen",
            "Container-Anfrage ausfuehren",
        ],
        plan_steps=[],
        pending_step="Container-Anfrage ausfuehren",
        risk_level=RiskLevel.SAFE,
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
                            "key_facts": [
                                "installed_count: 2",
                                "installed_names: Gaming Station, Gaming Lite",
                            ],
                        }
                    ]
                },
            }
        ],
    )

    prompt = build_task_loop_step_prompt(
        "Container-Anfrage ausfuehren",
        {
            "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
            "goal": "Den angefragten Container ausfuehren.",
            "done_criteria": "Ein verifizierter Ausfuehrungsbefund liegt vor.",
            "suggested_tools": ["request_container"],
            "objective": "Gaming-Container kontrolliert starten",
        },
        snapshot,
    )

    assert "Verifizierte Tool-Fakten:" in prompt
    assert "- blueprint_list [ok]: installed_count: 2; installed_names: Gaming Station, Gaming Lite" in prompt


def _simple_snapshot() -> TaskLoopSnapshot:
    return TaskLoopSnapshot(
        objective_id="obj-approval",
        conversation_id="conv-approval",
        plan_id="plan-approval",
        current_step_id="step-1",
        current_step_type=TaskLoopStepType.TOOL_EXECUTION,
        current_plan=["Skills pruefen"],
        plan_steps=[],
        pending_step="Skills pruefen",
        risk_level=RiskLevel.SAFE,
    )


def test_requires_approval_false_for_discovery_only_tools():
    from core.task_loop.step_runtime import build_task_loop_step_request

    request = build_task_loop_step_request(
        "Verfuegbare Skills auflisten",
        {"step_type": "tool_execution", "suggested_tools": ["list_skills"]},
        _simple_snapshot(),
        {"suggested_tools": ["list_skills"]},
    )

    assert request.requires_approval is False


def test_requires_approval_false_for_cron_discovery_tools():
    from core.task_loop.step_runtime import build_task_loop_step_request

    request = build_task_loop_step_request(
        "Cron-Status pruefen",
        {"step_type": "tool_execution", "suggested_tools": ["autonomy_cron_status", "autonomy_cron_list_jobs"]},
        _simple_snapshot(),
        {"suggested_tools": ["autonomy_cron_status", "autonomy_cron_list_jobs"]},
    )

    assert request.requires_approval is False


def test_requires_approval_true_for_action_tools():
    from core.task_loop.step_runtime import build_task_loop_step_request

    request = build_task_loop_step_request(
        "Skill ausfuehren",
        {"step_type": "tool_execution", "suggested_tools": ["run_skill"]},
        _simple_snapshot(),
        {"suggested_tools": ["run_skill"]},
    )

    assert request.requires_approval is True


def test_requires_approval_true_when_requires_user_set_even_for_discovery():
    from core.task_loop.step_runtime import build_task_loop_step_request

    request = build_task_loop_step_request(
        "Skills bestätigen",
        {"step_type": "tool_execution", "suggested_tools": ["list_skills"], "requires_user": True},
        _simple_snapshot(),
        {"suggested_tools": ["list_skills"]},
    )

    assert request.requires_approval is True


def test_requires_approval_true_for_mixed_discovery_and_action_tools():
    from core.task_loop.step_runtime import build_task_loop_step_request

    request = build_task_loop_step_request(
        "Skills pruefen und ausfuehren",
        {"step_type": "tool_execution", "suggested_tools": ["list_skills", "run_skill"]},
        _simple_snapshot(),
        {"suggested_tools": ["list_skills", "run_skill"]},
    )

    assert request.requires_approval is True


def test_build_task_loop_step_request_includes_auto_clarify_defaults_for_python_container():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-step-runtime",
        conversation_id="conv-step-runtime",
        plan_id="plan-step-runtime",
        current_step_id="step-3",
        current_step_type=TaskLoopStepType.TOOL_REQUEST,
        current_plan=["Container-Anfrage zur Freigabe vorbereiten"],
        plan_steps=[],
        pending_step="Container-Anfrage zur Freigabe vorbereiten",
        risk_level=RiskLevel.SAFE,
    )

    request = build_task_loop_step_request(
        "Container-Anfrage zur Freigabe vorbereiten",
        {
            "step_id": "step-3",
            "title": "Container-Anfrage zur Freigabe vorbereiten",
            "goal": "Die eigentliche Container-Anfrage vorbereiten.",
            "done_criteria": "Die Anfrage ist konkret vorbereitet.",
            "risk_level": "safe",
            "requires_user": False,
            "suggested_tools": ["request_container"],
            "task_kind": "implementation",
            "objective": "Python-Container kontrolliert anfordern",
            "step_type": TaskLoopStepType.TOOL_REQUEST.value,
            "requested_capability": {
                "capability_type": "container_manager",
                "capability_target": "request_container",
                "capability_action": "request_container",
            },
            "capability_context": {
                "request_family": "python_container",
                "known_fields": {},
            },
        },
        snapshot,
        {
            "requested_capability": {
                "capability_type": "container_manager",
                "capability_target": "request_container",
                "capability_action": "request_container",
            },
            "capability_context": {
                "request_family": "python_container",
                "known_fields": {},
            },
        },
    )

    assert request.reasoning_context["auto_clarify_mode"] == "self_discover"
    resolved = {
        entry["name"]: entry["value"]
        for entry in request.reasoning_context["auto_clarify_resolved_fields"]
    }
    assert resolved["python_version"] == "3.11"
    assert resolved["dependency_spec"] == "none"
    assert resolved["build_or_runtime"] == "runtime"


def test_build_task_loop_step_prompt_warns_to_run_safe_discovery_before_user_question():
    snapshot = TaskLoopSnapshot(
        objective_id="obj-step-runtime",
        conversation_id="conv-step-runtime",
        plan_id="plan-step-runtime",
        current_step_id="step-1",
        current_step_type=TaskLoopStepType.ANALYSIS,
        current_plan=[
            "Container-Anforderungsziel klaeren",
            "Verfuegbare Blueprints oder Container-Basis pruefen",
            "Container-Anfrage zur Freigabe vorbereiten",
        ],
        plan_steps=[
            {
                "step_id": "step-1",
                "title": "Container-Anforderungsziel klaeren",
                "step_type": TaskLoopStepType.ANALYSIS.value,
                "suggested_tools": [],
            },
            {
                "step_id": "step-2",
                "title": "Verfuegbare Blueprints oder Container-Basis pruefen",
                "step_type": TaskLoopStepType.TOOL_EXECUTION.value,
                "suggested_tools": ["blueprint_list"],
            },
            {
                "step_id": "step-3",
                "title": "Container-Anfrage zur Freigabe vorbereiten",
                "step_type": TaskLoopStepType.TOOL_REQUEST.value,
                "suggested_tools": ["request_container"],
            },
        ],
        pending_step="Container-Anforderungsziel klaeren",
        risk_level=RiskLevel.SAFE,
    )

    prompt = build_task_loop_step_prompt(
        "Container-Anforderungsziel klaeren",
        {
            "step_type": TaskLoopStepType.ANALYSIS.value,
            "goal": "Ziel und Bedarf sichtbar eingrenzen.",
            "done_criteria": "Der Container-Bedarf ist klar formuliert.",
            "objective": "Python-Container anfordern",
        },
        snapshot,
    )

    assert "Geplanter Folgeschritt: Verfuegbare Blueprints oder Container-Basis pruefen" in prompt
    assert "Vor einer User-Rueckfrage wird zuerst dieser sichere Discovery-Schritt ausgefuehrt." in prompt
