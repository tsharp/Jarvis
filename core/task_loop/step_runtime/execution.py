from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Dict, List

from core.control_contract import ControlDecision, DoneReason, execution_result_from_plan
from core.task_loop.action_resolution import resolve_next_loop_action
from core.task_loop.action_resolution.contracts import (
    ActionResolutionDecision,
    ActionResolutionMode,
)
from core.task_loop.capabilities.container.parameter_policy import build_container_parameter_context
from core.task_loop.capabilities.container.recovery import RECOVERY_ARTIFACT_TYPE
from core.task_loop.capabilities.container.request_policy import build_container_request_context
from core.task_loop.capabilities.container.replan_policy import build_container_recovery_hint
from core.task_loop.capability_policy import requested_capability_from_tools
from core.task_loop.contracts import (
    RiskLevel,
    TaskLoopSnapshot,
    TaskLoopStepExecutionSource,
    TaskLoopStepRequest,
    TaskLoopStepResult,
    TaskLoopStepStatus,
    TaskLoopStepType,
)
from core.task_loop.step_runtime.prepare import (
    PreparedTaskLoopStepRuntime,
    prepare_task_loop_step_runtime,
)
from core.task_loop.step_runtime.prompting import _clip, _effective_step_status
from core.task_loop.tool_step_policy import (
    normalize_runtime_step_type,
    should_execute_tool_via_orchestrator,
)


@dataclass(frozen=True)
class TaskLoopStepRuntimeResult:
    visible_text: str
    control_decision: ControlDecision
    verified_plan: Dict[str, Any]
    step_result: TaskLoopStepResult
    used_fallback: bool = False


def _build_verified_artifacts(
    prepared: PreparedTaskLoopStepRuntime,
    *,
    execution_result: Dict[str, Any] | None = None,
    recovery_hint: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    artifacts: List[Dict[str, Any]] = []
    if prepared.step_request.requested_capability:
        artifacts.append(
            {
                "artifact_type": "requested_capability",
                **dict(prepared.step_request.requested_capability),
            }
        )
    if prepared.step_request.capability_context:
        artifacts.append(
            {
                "artifact_type": "container_capability_context",
                "context": dict(prepared.step_request.capability_context),
            }
        )
    user_reply = str((prepared.step_request.reasoning_context or {}).get("user_reply") or "").strip()
    if user_reply:
        artifacts.append(
            {
                "artifact_type": "user_reply",
                "content": user_reply,
            }
        )
    selected_blueprint_id = str((prepared.step_request.reasoning_context or {}).get("selected_blueprint_id") or "").strip()
    selected_blueprint_label = str((prepared.step_request.reasoning_context or {}).get("selected_blueprint_label") or "").strip()
    if selected_blueprint_id:
        artifacts.append(
            {
                "artifact_type": "blueprint_selection",
                "blueprint_id": selected_blueprint_id,
                "content": selected_blueprint_label or selected_blueprint_id,
            }
        )
    container_request_params = (prepared.step_request.reasoning_context or {}).get("container_request_params")
    if isinstance(container_request_params, dict) and container_request_params:
        artifacts.append(
            {
                "artifact_type": "container_request_params",
                "params": dict(container_request_params),
            }
        )
    if isinstance(execution_result, dict) and execution_result:
        artifacts.append(
            {
                "artifact_type": "execution_result",
                "done_reason": str(execution_result.get("done_reason") or ""),
                "direct_response": str(execution_result.get("direct_response") or ""),
                "tool_statuses": list(execution_result.get("tool_statuses") or []),
                "grounding": dict(execution_result.get("grounding") or {}),
                "metadata": dict(execution_result.get("metadata") or {}),
            }
        )
    if isinstance(recovery_hint, dict) and recovery_hint:
        artifacts.append(
            {
                "artifact_type": RECOVERY_ARTIFACT_TYPE,
                **dict(recovery_hint),
            }
        )
    return artifacts


def check_tool_request_preconditions(
    snapshot: TaskLoopSnapshot,
    step_request: "TaskLoopStepRequest",
    *,
    user_reply: str = "",
    resume_completed: bool = False,
) -> tuple[TaskLoopStepStatus | None, str]:
    """Prüft Blueprint- und Parameter-Vorabgates für TOOL_REQUEST-Schritte.

    Gibt (status, message) zurück wenn der Schritt pausieren muss, sonst (None, "").
    Muss sowohl im Stream-Pfad als auch im Sync/Async-Pfad aufgerufen werden.
    """
    if resume_completed:
        return None, ""
    requested_capability = dict(step_request.requested_capability or {})
    if str(requested_capability.get("capability_action") or "").strip().lower() != "request_container":
        return None, ""
    request_ctx = build_container_request_context(
        snapshot,
        requested_capability=requested_capability,
        user_reply=user_reply,
        capability_context=step_request.capability_context,
    )
    if request_ctx.get("requires_user_choice"):
        msg = str(request_ctx.get("waiting_message") or "").strip()
        return TaskLoopStepStatus.WAITING_FOR_USER, msg
    selected_blueprint = request_ctx.get("selected_blueprint")
    if not isinstance(selected_blueprint, dict):
        selected_blueprint = {}
    parameter_ctx = build_container_parameter_context(
        snapshot,
        requested_capability=requested_capability,
        selected_blueprint=selected_blueprint,
        capability_context=step_request.capability_context,
        user_reply=user_reply,
    )
    if parameter_ctx.get("requires_user_input"):
        msg = str(parameter_ctx.get("waiting_message") or "").strip()
        return TaskLoopStepStatus.WAITING_FOR_USER, msg
    return None, ""


def _next_action_for_status(status: TaskLoopStepStatus) -> str:
    if status is TaskLoopStepStatus.COMPLETED:
        return "analyze_artifacts"
    if status is TaskLoopStepStatus.WAITING_FOR_APPROVAL:
        return "request_approval"
    if status is TaskLoopStepStatus.WAITING_FOR_USER:
        return "ask_user"
    if status is TaskLoopStepStatus.FAILED:
        return "analyze_failure"
    return "stop_blocked"


def _replan_hint_from_resolution(
    prepared: PreparedTaskLoopStepRuntime,
    decision: ActionResolutionDecision,
) -> Dict[str, Any]:
    action = decision.action
    if action is None or action.mode not in {
        ActionResolutionMode.INSERT_DISCOVERY_STEP,
        ActionResolutionMode.REPLAN_WITH_ACTION,
    }:
        return {}

    next_tools = list(action.suggested_tools or [])
    requested_capability = dict(action.requested_capability or {})
    if not requested_capability and next_tools:
        requested_capability = requested_capability_from_tools(next_tools)
    capability_context = dict(action.capability_context or prepared.step_request.capability_context)
    step_title = str(action.title or prepared.step_request.step_title or "Folgeschritt").strip() or "Folgeschritt"
    step_type = str(action.step_type or TaskLoopStepType.TOOL_EXECUTION.value).strip() or TaskLoopStepType.TOOL_EXECUTION.value
    detail = str(decision.detail or "").strip()
    replan_step = {
        "step_id": f"{prepared.step_request.step_id}-resolved-next",
        "title": step_title,
        "goal": detail or "Den naechsten sicheren Schritt fuer die Aufgabenfortsetzung sichtbar und verifiziert ausfuehren.",
        "done_criteria": "Ein verifizierter Befund oder eine konkretisierte Folgeaktion liegt vor.",
        "risk_level": RiskLevel.SAFE.value,
        "requires_user": False,
        "suggested_tools": next_tools,
        "task_kind": str(prepared.verified_plan.get("task_kind") or "implementation"),
        "objective": str(prepared.step_request.objective or ""),
        "step_type": step_type,
        "requested_capability": requested_capability,
        "capability_context": capability_context,
    }
    return {
        "artifact_type": RECOVERY_ARTIFACT_TYPE,
        "recovery_mode": "replan_with_tools",
        "reason": "action_resolution",
        "next_tools": next_tools,
        "replan_step_title": step_title,
        "replan_step": replan_step,
        "summary": detail or f"Ich fuehre zuerst den sicheren Folgeschritt `{step_title}` aus.",
    }


def _runtime_result_from_action_resolution(
    prepared: PreparedTaskLoopStepRuntime,
    decision: ActionResolutionDecision,
    *,
    trace_reason: str,
) -> TaskLoopStepRuntimeResult | None:
    action = decision.action
    if action is None:
        return None

    if action.mode in {
        ActionResolutionMode.INSERT_DISCOVERY_STEP,
        ActionResolutionMode.REPLAN_WITH_ACTION,
    }:
        recovery_hint = _replan_hint_from_resolution(prepared, decision)
        if not recovery_hint:
            return None
        summary = str(recovery_hint.get("summary") or "").strip() or prepared.fallback_text
        step_result = TaskLoopStepResult(
            turn_id=prepared.step_request.turn_id,
            loop_id=prepared.step_request.loop_id,
            step_id=prepared.step_request.step_id,
            step_type=normalize_runtime_step_type(prepared.step_request.step_type),
            status=TaskLoopStepStatus.COMPLETED,
            control_decision=prepared.control_decision.to_dict(),
            execution_result={},
            verified_artifacts=_build_verified_artifacts(prepared, recovery_hint=recovery_hint),
            user_visible_summary=summary,
            next_action="replan_recovery",
            warnings=list(prepared.control_decision.warnings),
            blockers=list(decision.blockers),
            trace_reason=trace_reason,
            step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
        )
        return TaskLoopStepRuntimeResult(
            visible_text=summary,
            control_decision=prepared.control_decision,
            verified_plan=prepared.verified_plan,
            step_result=step_result,
            used_fallback=False,
        )

    if action.mode is ActionResolutionMode.ASK_USER:
        summary = str(action.metadata.get("ask_user_message") or decision.detail or prepared.fallback_text).strip()
        step_result = TaskLoopStepResult(
            turn_id=prepared.step_request.turn_id,
            loop_id=prepared.step_request.loop_id,
            step_id=prepared.step_request.step_id,
            step_type=normalize_runtime_step_type(prepared.step_request.step_type),
            status=TaskLoopStepStatus.WAITING_FOR_USER,
            control_decision=prepared.control_decision.to_dict(),
            execution_result={},
            verified_artifacts=_build_verified_artifacts(prepared),
            user_visible_summary=summary,
            next_action="ask_user",
            warnings=list(prepared.control_decision.warnings),
            blockers=list(decision.blockers),
            trace_reason=trace_reason,
            step_execution_source=TaskLoopStepExecutionSource.LOOP,
        )
        return TaskLoopStepRuntimeResult(
            visible_text=summary,
            control_decision=prepared.control_decision,
            verified_plan=prepared.verified_plan,
            step_result=step_result,
            used_fallback=False,
        )

    if action.mode is ActionResolutionMode.BLOCK:
        summary = str(decision.detail or prepared.fallback_text).strip()
        step_result = TaskLoopStepResult(
            turn_id=prepared.step_request.turn_id,
            loop_id=prepared.step_request.loop_id,
            step_id=prepared.step_request.step_id,
            step_type=normalize_runtime_step_type(prepared.step_request.step_type),
            status=TaskLoopStepStatus.BLOCKED,
            control_decision=prepared.control_decision.to_dict(),
            execution_result={},
            verified_artifacts=_build_verified_artifacts(prepared),
            user_visible_summary=summary,
            next_action="stop_blocked",
            warnings=list(prepared.control_decision.warnings),
            blockers=list(decision.blockers),
            trace_reason=trace_reason,
            step_execution_source=TaskLoopStepExecutionSource.BLOCKED,
        )
        return TaskLoopStepRuntimeResult(
            visible_text=summary,
            control_decision=prepared.control_decision,
            verified_plan=prepared.verified_plan,
            step_result=step_result,
            used_fallback=False,
        )

    return None


def _step_result_from_text(
    prepared: PreparedTaskLoopStepRuntime,
    *,
    visible_text: str,
    source: TaskLoopStepExecutionSource,
    trace_reason: str,
    used_fallback: bool,
    waiting_for_user: bool = False,
    status_override: TaskLoopStepStatus | None = None,
    recovery_hint: Dict[str, Any] | None = None,
) -> TaskLoopStepResult:
    status = status_override or (
        TaskLoopStepStatus.WAITING_FOR_USER if waiting_for_user else TaskLoopStepStatus.COMPLETED
    )
    return TaskLoopStepResult(
        turn_id=prepared.step_request.turn_id,
        loop_id=prepared.step_request.loop_id,
        step_id=prepared.step_request.step_id,
        step_type=prepared.step_request.step_type,
        status=status,
        control_decision=prepared.control_decision.to_dict(),
        execution_result={},
        verified_artifacts=_build_verified_artifacts(prepared, recovery_hint=recovery_hint),
        user_visible_summary=visible_text,
        next_action=_next_action_for_status(status),
        warnings=list(prepared.control_decision.warnings),
        trace_reason=trace_reason,
        step_execution_source=source,
    )


def _map_orchestrator_status(execution_result: Dict[str, Any]) -> TaskLoopStepStatus:
    statuses = {
        str((row or {}).get("status") or "").strip().lower()
        for row in execution_result.get("tool_statuses") or []
        if isinstance(row, dict)
    }
    if "pending_approval" in statuses:
        return TaskLoopStepStatus.WAITING_FOR_APPROVAL
    if "needs_clarification" in statuses:
        return TaskLoopStepStatus.WAITING_FOR_USER
    done_reason = str(execution_result.get("done_reason") or "").strip().lower()
    if done_reason == DoneReason.SUCCESS.value or "ok" in statuses:
        return TaskLoopStepStatus.COMPLETED
    if done_reason in {DoneReason.ROUTING_BLOCK.value, DoneReason.UNAVAILABLE.value}:
        return TaskLoopStepStatus.BLOCKED
    if done_reason in {DoneReason.TECH_FAIL.value, DoneReason.TIMEOUT.value}:
        return TaskLoopStepStatus.FAILED
    return TaskLoopStepStatus.BLOCKED


async def _execute_orchestrator_step(
    prepared: PreparedTaskLoopStepRuntime,
    snapshot: TaskLoopSnapshot,
    *,
    orchestrator_bridge: Any,
) -> TaskLoopStepRuntimeResult:
    control_tool_decisions: Dict[str, Dict[str, Any]] = {}
    if hasattr(orchestrator_bridge, "_collect_control_tool_decisions"):
        control_tool_decisions = await orchestrator_bridge._collect_control_tool_decisions(
            prepared.prompt,
            prepared.verified_plan,
            control_decision=prepared.control_decision,
            stream=False,
        )
    if hasattr(orchestrator_bridge, "_resolve_execution_suggested_tools"):
        resolved_tools = orchestrator_bridge._resolve_execution_suggested_tools(
            prepared.prompt,
            prepared.verified_plan,
            control_tool_decisions,
            control_decision=prepared.control_decision,
            stream=False,
            conversation_id=snapshot.conversation_id,
            chat_history=None,
        )
    else:
        resolved_tools = list(prepared.step_request.suggested_tools)

    if not resolved_tools:
        resolution = resolve_next_loop_action(
            snapshot=snapshot,
            step_request=prepared.step_request,
        )
        if (
            resolution.action is not None
            and resolution.action.mode is ActionResolutionMode.EXECUTE_EXISTING_STEP
            and resolution.action.suggested_tools
        ):
            resolved_tools = list(resolution.action.suggested_tools)
        else:
            resolved_runtime = _runtime_result_from_action_resolution(
                prepared,
                resolution,
                trace_reason="task_loop_action_resolution_no_resolved_tools",
            )
            if resolved_runtime is not None:
                return resolved_runtime
        recovery_hint = build_container_recovery_hint(
            requested_capability=prepared.step_request.requested_capability,
            capability_context=prepared.step_request.capability_context,
            resolved_tools=resolved_tools,
            no_resolved_tools=True,
        )
        if recovery_hint:
            summary = str(recovery_hint.get("summary") or "").strip() or (
                "Kein direkt ausfuehrbarer Container-Aktionspfad war verfuegbar. "
                "Ich pruefe zuerst lesende Container-/Blueprint-Informationen."
            )
            step_result = TaskLoopStepResult(
                turn_id=prepared.step_request.turn_id,
                loop_id=prepared.step_request.loop_id,
                step_id=prepared.step_request.step_id,
                step_type=normalize_runtime_step_type(prepared.step_request.step_type),
                status=TaskLoopStepStatus.COMPLETED,
                control_decision=prepared.control_decision.to_dict(),
                execution_result={},
                verified_artifacts=_build_verified_artifacts(prepared, recovery_hint=recovery_hint),
                user_visible_summary=summary,
                next_action="replan_recovery",
                warnings=list(prepared.control_decision.warnings),
                blockers=["no_resolved_tools"],
                trace_reason="task_loop_container_recovery_no_resolved_tools",
                step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
            )
            return TaskLoopStepRuntimeResult(
                visible_text=summary,
                control_decision=prepared.control_decision,
                verified_plan=prepared.verified_plan,
                step_result=step_result,
                used_fallback=False,
            )
        if prepared.step_request.suggested_tools:
            resolved_tools = list(prepared.step_request.suggested_tools)
        else:
            summary = "Kein zulassiger Tool-Schritt konnte fuer diesen Loop-Schritt materialisiert werden."
            step_result = TaskLoopStepResult(
                turn_id=prepared.step_request.turn_id,
                loop_id=prepared.step_request.loop_id,
                step_id=prepared.step_request.step_id,
                step_type=prepared.step_request.step_type,
                status=TaskLoopStepStatus.BLOCKED,
                control_decision=prepared.control_decision.to_dict(),
                execution_result={},
                verified_artifacts=_build_verified_artifacts(prepared),
                user_visible_summary=summary,
                next_action="stop_blocked",
                warnings=list(prepared.control_decision.warnings),
                blockers=["no_resolved_tools"],
                trace_reason="task_loop_no_resolved_tools",
                step_execution_source=TaskLoopStepExecutionSource.BLOCKED,
            )
            return TaskLoopStepRuntimeResult(
                visible_text=summary,
                control_decision=prepared.control_decision,
                verified_plan=prepared.verified_plan,
                step_result=step_result,
                used_fallback=False,
            )

    tool_context = await asyncio.to_thread(
        orchestrator_bridge._execute_tools_sync,
        resolved_tools,
        prepared.prompt,
        control_tool_decisions,
        control_decision=prepared.control_decision,
        thinking_suggested_tools=prepared.verified_plan.get("suggested_tools", []),
        session_id=snapshot.conversation_id,
        verified_plan=prepared.verified_plan,
    )
    execution_result = execution_result_from_plan(prepared.verified_plan).to_dict()
    status = _map_orchestrator_status(execution_result)
    recovery_hint = build_container_recovery_hint(
        requested_capability=prepared.step_request.requested_capability,
        capability_context=prepared.step_request.capability_context,
        execution_result=execution_result,
        resolved_tools=resolved_tools,
    )
    summary = (
        str(execution_result.get("direct_response") or "").strip()
        or _clip(tool_context)
        or prepared.fallback_text
    )
    if recovery_hint and str(recovery_hint.get("recovery_mode") or "").strip().lower() == "replan_with_tools":
        status = TaskLoopStepStatus.COMPLETED
        summary = str(recovery_hint.get("summary") or "").strip() or summary
    elif status is TaskLoopStepStatus.BLOCKED:
        resolution = resolve_next_loop_action(
            snapshot=snapshot,
            step_request=prepared.step_request,
            step_result={"execution_result": execution_result},
            recovery_hint={"recheck_attempted": True},
        )
        resolved_runtime = _runtime_result_from_action_resolution(
            prepared,
            resolution,
            trace_reason="task_loop_action_resolution_blocked_execution",
        )
        if resolved_runtime is not None:
            return resolved_runtime
    step_result = TaskLoopStepResult(
        turn_id=prepared.step_request.turn_id,
        loop_id=prepared.step_request.loop_id,
        step_id=prepared.step_request.step_id,
        step_type=normalize_runtime_step_type(prepared.step_request.step_type),
        status=status,
        control_decision=prepared.control_decision.to_dict(),
        execution_result=execution_result,
        verified_artifacts=_build_verified_artifacts(
            prepared,
            execution_result=execution_result,
            recovery_hint=recovery_hint,
        ),
        user_visible_summary=summary,
        next_action=(
            "replan_recovery"
            if recovery_hint and str(recovery_hint.get("recovery_mode") or "").strip().lower() == "replan_with_tools"
            else _next_action_for_status(status)
        ),
        warnings=list(prepared.control_decision.warnings),
        blockers=[
            str((row or {}).get("reason") or "").strip()
            for row in execution_result.get("tool_statuses") or []
            if isinstance(row, dict) and str((row or {}).get("status") or "").strip().lower() in {"routing_block", "unavailable"}
        ],
        trace_reason="task_loop_orchestrator_step",
        step_execution_source=TaskLoopStepExecutionSource.ORCHESTRATOR,
    )
    return TaskLoopStepRuntimeResult(
        visible_text=summary,
        control_decision=prepared.control_decision,
        verified_plan=prepared.verified_plan,
        step_result=step_result,
        used_fallback=False,
    )


async def execute_task_loop_step(
    step_title: str,
    step_meta: Dict[str, Any],
    snapshot: TaskLoopSnapshot,
    *,
    control_layer: Any,
    output_layer: Any,
    orchestrator_bridge: Any = None,
    resume_user_text: str = "",
    fallback_fn: Callable[[int, str, Dict[str, Any], List[str]], str],
) -> TaskLoopStepRuntimeResult:
    prepared = await prepare_task_loop_step_runtime(
        step_title,
        step_meta,
        snapshot,
        control_layer=control_layer,
        user_reply=resume_user_text,
        fallback_fn=fallback_fn,
    )
    step_type = prepared.step_request.step_type
    # requires_user aus dem Plan-Schritt — gilt nur fuer ANALYSIS/RESPONSE,
    # TOOL_REQUEST hat eine eigene Logik (request_container_context, parameter_context)
    step_requires_user = (
        bool(step_meta.get("requires_user"))
        and step_type not in {TaskLoopStepType.TOOL_REQUEST, TaskLoopStepType.TOOL_EXECUTION}
    )
    if (
        orchestrator_bridge is not None
        and should_execute_tool_via_orchestrator(step_type)
        and prepared.step_request.suggested_tools
    ):
        try:
            return await _execute_orchestrator_step(
                prepared,
                snapshot,
                orchestrator_bridge=orchestrator_bridge,
            )
        except Exception:
            fallback_text = _clip(prepared.fallback_text)
            return TaskLoopStepRuntimeResult(
                visible_text=fallback_text,
                control_decision=prepared.control_decision,
                verified_plan=prepared.verified_plan,
                step_result=_step_result_from_text(
                    prepared,
                    visible_text=fallback_text,
                    source=TaskLoopStepExecutionSource.FALLBACK,
                    trace_reason="task_loop_orchestrator_fallback",
                    used_fallback=True,
                ),
                used_fallback=True,
            )
    effective_status = _effective_step_status(snapshot, step_type)
    tool_request_resume_completed = (
        step_type is TaskLoopStepType.TOOL_REQUEST
        and effective_status in {
            TaskLoopStepStatus.WAITING_FOR_APPROVAL,
            TaskLoopStepStatus.WAITING_FOR_USER,
        }
    )
    if step_type is TaskLoopStepType.TOOL_REQUEST:
        gate_status, gate_msg = check_tool_request_preconditions(
            snapshot,
            prepared.step_request,
            user_reply=resume_user_text,
            resume_completed=tool_request_resume_completed,
        )
        if gate_status is not None:
            waiting_text = gate_msg or prepared.fallback_text
            return TaskLoopStepRuntimeResult(
                visible_text=waiting_text,
                control_decision=prepared.control_decision,
                verified_plan=prepared.verified_plan,
                step_result=_step_result_from_text(
                    prepared,
                    visible_text=waiting_text,
                    source=TaskLoopStepExecutionSource.LOOP,
                    trace_reason="task_loop_tool_request_precondition_gate",
                    used_fallback=False,
                    status_override=gate_status,
                ),
                used_fallback=False,
            )
    tool_request_status = (
        TaskLoopStepStatus.COMPLETED
        if tool_request_resume_completed
        else (
            TaskLoopStepStatus.WAITING_FOR_APPROVAL
            if step_type is TaskLoopStepType.TOOL_REQUEST and prepared.step_request.requires_approval
            else TaskLoopStepStatus.COMPLETED
        )
    )
    if output_layer is None:
        fallback_text = _clip(prepared.fallback_text)
        return TaskLoopStepRuntimeResult(
            visible_text=fallback_text,
            control_decision=prepared.control_decision,
            verified_plan=prepared.verified_plan,
            step_result=_step_result_from_text(
                prepared,
                visible_text=fallback_text,
                source=TaskLoopStepExecutionSource.FALLBACK,
                trace_reason="task_loop_no_output_layer",
                used_fallback=True,
                waiting_for_user=False,
                status_override=tool_request_status if step_type is TaskLoopStepType.TOOL_REQUEST else None,
            ),
            used_fallback=True,
        )

    try:
        chunks: List[str] = []
        async for chunk in stream_task_loop_step_output(prepared, output_layer=output_layer):
            if chunk:
                chunks.append(str(chunk))
        visible_text = _clip("".join(chunks).strip())
        if not visible_text:
            raise ValueError("empty_step_output")
        return TaskLoopStepRuntimeResult(
            visible_text=visible_text,
            control_decision=prepared.control_decision,
            verified_plan=prepared.verified_plan,
            step_result=_step_result_from_text(
                prepared,
                visible_text=visible_text,
                source=TaskLoopStepExecutionSource.LOOP,
                trace_reason="task_loop_output_stream",
                used_fallback=False,
                waiting_for_user=step_requires_user,
                status_override=tool_request_status if step_type is TaskLoopStepType.TOOL_REQUEST else None,
            ),
            used_fallback=False,
        )
    except Exception:
        fallback_text = _clip(prepared.fallback_text)
        return TaskLoopStepRuntimeResult(
            visible_text=fallback_text,
            control_decision=prepared.control_decision,
            verified_plan=prepared.verified_plan,
            step_result=_step_result_from_text(
                prepared,
                visible_text=fallback_text,
                source=TaskLoopStepExecutionSource.FALLBACK,
                trace_reason="task_loop_stream_fallback",
                used_fallback=True,
                waiting_for_user=False,
                status_override=tool_request_status if step_type is TaskLoopStepType.TOOL_REQUEST else None,
            ),
            used_fallback=True,
        )


async def stream_task_loop_step_output(
    prepared: PreparedTaskLoopStepRuntime,
    *,
    output_layer: Any,
) -> AsyncGenerator[str, None]:
    async for chunk in output_layer.generate_stream(
        user_text=prepared.prompt,
        verified_plan=prepared.verified_plan,
        memory_data="",
        control_decision=prepared.control_decision,
        execution_result=prepared.verified_plan.get("_execution_result"),
    ):
        if chunk:
            yield str(chunk)


__all__ = [
    "TaskLoopStepRuntimeResult",
    "_build_verified_artifacts",
    "_execute_orchestrator_step",
    "_map_orchestrator_status",
    "_next_action_for_status",
    "_step_result_from_text",
    "check_tool_request_preconditions",
    "execute_task_loop_step",
    "stream_task_loop_step_output",
]
