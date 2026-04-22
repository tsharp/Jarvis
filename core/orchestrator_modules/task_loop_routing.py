from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.task_loop.active_turn_policy import (
    ACTIVE_TASK_LOOP_REASON_BLOCKED,
    ACTIVE_TASK_LOOP_REASON_CANCEL,
    ACTIVE_TASK_LOOP_REASON_CONTEXT_ONLY,
    ACTIVE_TASK_LOOP_REASON_CONTINUE,
    ACTIVE_TASK_LOOP_REASON_MODE_SHIFT,
    ACTIVE_TASK_LOOP_REASON_RESTART,
    classify_active_task_loop_routing,
    explain_active_task_loop_routing,
)
from core.task_loop.routing_policy import (
    is_authoritative_task_loop_execution,
    resolve_runtime_execution_mode,
    resolve_runtime_turn_mode,
)


@dataclass(frozen=True)
class TaskLoopRoutingDecision:
    execution_mode: str
    turn_mode: str
    authority_source: str
    active_task_loop_reason: str
    active_task_loop_detail: str
    branch: str
    is_authoritative_task_loop_turn: bool
    use_task_loop: bool
    force_start: bool
    clear_active_loop: bool
    context_only: bool
    runtime_resume_candidate: bool
    background_preservable: bool
    meta_turn: bool
    independent_tool_turn: bool


def decide_task_loop_routing(
    user_text: str,
    snapshot: Optional[Any],
    verified_plan: Optional[Dict[str, Any]],
    *,
    raw_request: Optional[Dict[str, Any]] = None,
) -> TaskLoopRoutingDecision:
    execution_mode, authority_source = resolve_runtime_execution_mode(verified_plan)
    turn_mode, turn_mode_source = resolve_runtime_turn_mode(verified_plan)
    if not authority_source:
        authority_source = turn_mode_source

    active_loop_explanation = explain_active_task_loop_routing(
        user_text,
        snapshot,
        verified_plan,
        raw_request=raw_request,
    )
    active_task_loop_reason = str(active_loop_explanation.get("reason") or "").strip()
    authoritative_task_loop = is_authoritative_task_loop_execution(verified_plan)

    branch = "direct_response"
    use_task_loop = False
    force_start = False
    clear_active_loop = False
    context_only = False

    if active_task_loop_reason in {
        ACTIVE_TASK_LOOP_REASON_CONTINUE,
        ACTIVE_TASK_LOOP_REASON_CANCEL,
    }:
        branch = "active_task_loop"
        use_task_loop = True
    elif active_task_loop_reason == ACTIVE_TASK_LOOP_REASON_RESTART:
        branch = "active_task_loop"
        use_task_loop = True
        force_start = True
    elif active_task_loop_reason == ACTIVE_TASK_LOOP_REASON_CONTEXT_ONLY:
        branch = "task_loop_context_only"
        context_only = True
    elif active_task_loop_reason in {
        ACTIVE_TASK_LOOP_REASON_MODE_SHIFT,
        ACTIVE_TASK_LOOP_REASON_BLOCKED,
    }:
        branch = "direct_after_active_loop_clear"
        clear_active_loop = True
    elif authoritative_task_loop:
        branch = "authoritative_task_loop_start"
        use_task_loop = True
        force_start = True

    return TaskLoopRoutingDecision(
        execution_mode=execution_mode,
        turn_mode=turn_mode,
        authority_source=authority_source,
        active_task_loop_reason=active_task_loop_reason,
        active_task_loop_detail=str(active_loop_explanation.get("detail") or "").strip(),
        branch=branch,
        is_authoritative_task_loop_turn=authoritative_task_loop,
        use_task_loop=use_task_loop,
        force_start=force_start,
        clear_active_loop=clear_active_loop,
        context_only=context_only,
        runtime_resume_candidate=bool(active_loop_explanation.get("runtime_resume_candidate")),
        background_preservable=bool(active_loop_explanation.get("background_preservable")),
        meta_turn=bool(active_loop_explanation.get("meta_turn")),
        independent_tool_turn=bool(active_loop_explanation.get("independent_tool_turn")),
    )


__all__ = [
    "TaskLoopRoutingDecision",
    "decide_task_loop_routing",
]
