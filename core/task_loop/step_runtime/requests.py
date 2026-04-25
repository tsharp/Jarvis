from __future__ import annotations

from typing import Any, Dict

from core.task_loop.action_resolution.auto_clarify.parameter_completion import (
    complete_container_parameters,
)
from core.task_loop.action_resolution.auto_clarify.policy import (
    evaluate_auto_clarify,
)
from core.task_loop.capabilities.container.context import merge_container_context
from core.task_loop.capabilities.container.parameter_policy import build_container_parameter_context
from core.task_loop.capabilities.container.request_policy import build_container_request_context
from core.task_loop.action_resolution.tool_utility_policy.tool_catalog import is_discovery_only
from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopStepRequest, TaskLoopStepType
from core.task_loop.step_runtime.prompting import _step_type_from_meta, _suggested_tools


def build_task_loop_step_request(
    step_title: str,
    step_meta: Dict[str, Any],
    snapshot: TaskLoopSnapshot,
    step_plan: Dict[str, Any],
    *,
    user_reply: str = "",
) -> TaskLoopStepRequest:
    objective = str(step_meta.get("objective") or "").strip() or snapshot.pending_step.strip() or "Aufgabe"
    step_type = _step_type_from_meta(step_meta)
    suggested_tools = _suggested_tools(step_meta)

    # Fallback: step_plan kann Tools via capability_hint + tool_catalog enthalten
    if not suggested_tools:
        suggested_tools = [
            str(t).strip()
            for t in (step_plan.get("suggested_tools") or [])
            if str(t or "").strip()
        ]

    # ANALYSIS → TOOL_EXECUTION upgraden wenn Tools bekannt und kein Risiko
    if suggested_tools and step_type is TaskLoopStepType.ANALYSIS:
        step_type = TaskLoopStepType.TOOL_EXECUTION

    requested_capability = dict(step_plan.get("requested_capability") or {})
    raw_capability_context = dict(step_plan.get("capability_context") or step_meta.get("capability_context") or {})
    request_capability_context = dict(raw_capability_context)
    for key in ("_container_resolution", "_container_candidates"):
        if key in step_plan:
            request_capability_context[key] = step_plan.get(key)
    container_context = build_container_request_context(
        snapshot,
        requested_capability=requested_capability,
        user_reply=user_reply,
        capability_context=request_capability_context,
    )
    selected_blueprint = container_context.get("selected_blueprint") if isinstance(container_context.get("selected_blueprint"), dict) else {}
    merged_capability_context = merge_container_context(
        request_capability_context,
        snapshot=snapshot,
        user_reply=user_reply,
        selected_blueprint=selected_blueprint,
    )
    completion = complete_container_parameters(
        snapshot,
        requested_capability=requested_capability,
        capability_context=merged_capability_context,
        user_reply=user_reply,
    )
    capability_context = dict(completion.get("capability_context") or merged_capability_context)
    parameter_context = build_container_parameter_context(
        snapshot,
        requested_capability=requested_capability,
        selected_blueprint=selected_blueprint,
        capability_context=capability_context,
        user_reply=user_reply,
    )
    parameter_context = dict(completion.get("parameter_context") or parameter_context)
    base_reasoning_context = {
        "done_criteria": str(step_meta.get("done_criteria") or "").strip(),
        "task_kind": str(step_meta.get("task_kind") or "").strip(),
        "user_reply": str(user_reply or "").strip(),
        "selected_blueprint_id": str(selected_blueprint.get("blueprint_id") or "").strip(),
        "selected_blueprint_label": str(selected_blueprint.get("label") or "").strip(),
        "requires_blueprint_choice": bool(container_context.get("requires_user_choice")),
        "container_capability_context": capability_context,
        "container_resolution": (
            dict(request_capability_context.get("_container_resolution"))
            if isinstance(request_capability_context.get("_container_resolution"), dict)
            else {}
        ),
        "container_candidates": (
            list(request_capability_context.get("_container_candidates"))
            if isinstance(request_capability_context.get("_container_candidates"), list)
            else []
        ),
        "container_request_params": dict(parameter_context.get("params") or {}),
        "missing_container_fields": list(parameter_context.get("missing_fields") or []),
    }
    provisional_request = TaskLoopStepRequest(
        turn_id=snapshot.conversation_id,
        loop_id=snapshot.plan_id,
        step_id=str(step_meta.get("step_id") or snapshot.current_step_id or f"step-{int(snapshot.step_index or 0) + 1}"),
        step_index=int(snapshot.step_index or 0) + 1,
        step_type=step_type,
        objective=objective,
        step_goal=str(step_meta.get("goal") or "").strip(),
        step_title=step_title,
        artifacts_so_far=list(snapshot.verified_artifacts),
        requested_capability=requested_capability,
        capability_context=capability_context,
        suggested_tools=suggested_tools,
        requires_control=True,
        requires_approval=bool(step_meta.get("requires_user")) or (
            bool(suggested_tools) and not is_discovery_only(suggested_tools)
        ),
        risk_context={
            "risk_level": str(step_meta.get("risk_level") or snapshot.risk_level.value),
        },
        reasoning_context=base_reasoning_context,
        user_visible_context=(
            f"{step_title}: {objective}"
            + (
                f"\nUser-Antwort: {str(user_reply).strip()}"
                if str(user_reply or "").strip()
                else ""
            )
        ),
        allowed_tool_scope=suggested_tools,
        timeout_hint_s=(
            float(step_plan.get("_output_time_budget_s"))
            if step_plan.get("_output_time_budget_s") is not None
            else None
        ),
    )
    reasoning_context = dict(base_reasoning_context)
    if suggested_tools or requested_capability:
        auto_clarify = evaluate_auto_clarify(
            snapshot=snapshot,
            step_request=provisional_request,
        )
        reasoning_context.update(
            {
                "auto_clarify_mode": auto_clarify.mode.value,
                "auto_clarify_resolved": bool(auto_clarify.resolved),
                "auto_clarify_ask_user_message": str(auto_clarify.ask_user_message or "").strip(),
                "auto_clarify_rationale": list(auto_clarify.rationale),
                "auto_clarify_missing_fields": [item.name for item in auto_clarify.missing_fields],
                "auto_clarify_resolved_fields": [
                    {
                        "name": item.name,
                        "value": item.value,
                        "source": item.source.value,
                    }
                    for item in auto_clarify.resolved_fields
                ],
                "auto_clarify_action_mode": (
                    auto_clarify.action.mode.value if auto_clarify.action is not None else ""
                ),
                "auto_clarify_action_title": (
                    str(auto_clarify.action.title or "").strip()
                    if auto_clarify.action is not None
                    else ""
                ),
                "auto_clarify_next_tools": (
                    list(auto_clarify.action.suggested_tools)
                    if auto_clarify.action is not None
                    else []
                ),
            }
        )
    return TaskLoopStepRequest(
        turn_id=provisional_request.turn_id,
        loop_id=provisional_request.loop_id,
        step_id=provisional_request.step_id,
        step_index=provisional_request.step_index,
        step_type=provisional_request.step_type,
        objective=provisional_request.objective,
        step_goal=provisional_request.step_goal,
        step_title=provisional_request.step_title,
        artifacts_so_far=provisional_request.artifacts_so_far,
        requested_capability=provisional_request.requested_capability,
        capability_context=provisional_request.capability_context,
        suggested_tools=provisional_request.suggested_tools,
        requires_control=provisional_request.requires_control,
        requires_approval=provisional_request.requires_approval,
        risk_context=provisional_request.risk_context,
        reasoning_context=reasoning_context,
        user_visible_context=provisional_request.user_visible_context,
        allowed_tool_scope=provisional_request.allowed_tool_scope,
        timeout_hint_s=provisional_request.timeout_hint_s,
        origin=provisional_request.origin,
    )


__all__ = ["build_task_loop_step_request"]
