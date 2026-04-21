from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from core.control_contract import ControlDecision, persist_control_decision
from core.task_loop.capabilities.system_knowledge.context import (
    is_system_knowledge_intent,
    load_system_knowledge_context,
)
from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopStepRequest
from core.task_loop.step_runtime.plans import build_task_loop_step_plan
from core.task_loop.step_runtime.prompting import build_task_loop_step_prompt
from core.task_loop.step_runtime.requests import build_task_loop_step_request


@dataclass(frozen=True)
class PreparedTaskLoopStepRuntime:
    prompt: str
    fallback_text: str
    control_decision: ControlDecision
    verified_plan: Dict[str, Any]
    step_request: TaskLoopStepRequest


async def prepare_task_loop_step_runtime(
    step_title: str,
    step_meta: Dict[str, Any],
    snapshot: TaskLoopSnapshot,
    *,
    control_layer: Any,
    user_reply: str = "",
    fallback_fn: Callable[[int, str, Dict[str, Any], List[str]], str],
) -> PreparedTaskLoopStepRuntime:
    fallback_text = fallback_fn(
        int(snapshot.step_index or 0) + 1,
        step_title,
        step_meta,
        list(snapshot.completed_steps),
    )
    step_plan = build_task_loop_step_plan(step_title, step_meta, snapshot, user_reply=user_reply)

    # System-Knowledge-Trigger: addon context laden wenn passend
    _cap_type = str((step_plan.get("requested_capability") or {}).get("capability_type") or "").strip()
    _step_intent = " ".join(filter(None, [
        step_title,
        str(step_meta.get("goal") or ""),
        str(step_meta.get("objective") or ""),
    ]))
    if _cap_type == "system_knowledge" or (not _cap_type and is_system_knowledge_intent(_step_intent)):
        _sys_ctx = await load_system_knowledge_context(_step_intent)
        if _sys_ctx:
            _cap_ctx = {**dict(step_plan.get("capability_context") or {}), **_sys_ctx}
            step_plan = {**step_plan, "capability_context": _cap_ctx}

    step_request = build_task_loop_step_request(
        step_title,
        step_meta,
        snapshot,
        step_plan,
        user_reply=user_reply,
    )
    prompt = build_task_loop_step_prompt(
        step_title,
        step_meta,
        snapshot,
        user_reply=user_reply,
        step_request=step_request,
    )

    verification: Dict[str, Any] = {"approved": True, "decision_class": "allow"}
    if control_layer is not None:
        try:
            verification = await control_layer.verify(
                prompt,
                step_plan,
                retrieved_memory="",
                response_mode="interactive",
            )
        except Exception:
            verification = {"approved": True, "decision_class": "allow"}

    control_decision = ControlDecision.from_verification(
        verification,
        default_approved=True,
    )
    persist_control_decision(step_plan, control_decision)
    return PreparedTaskLoopStepRuntime(
        prompt=prompt,
        fallback_text=fallback_text,
        control_decision=control_decision,
        verified_plan=step_plan,
        step_request=step_request,
    )


__all__ = [
    "PreparedTaskLoopStepRuntime",
    "prepare_task_loop_step_runtime",
]
