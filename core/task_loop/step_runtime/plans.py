from __future__ import annotations

from typing import Any, Dict

from core.task_loop.contracts import TaskLoopSnapshot
from core.task_loop.runtime_policy import apply_task_loop_runtime_policy
from core.task_loop.step_runtime.prompting import (
    _requested_capability,
    _step_type_from_meta,
    _suggested_tools,
)
from core.task_loop.step_runtime.capability_hint import suggest_capability_for_step
from core.task_loop.action_resolution.tool_utility_policy.tool_catalog import suggest_tools_for_step


def build_task_loop_step_plan(
    step_title: str,
    step_meta: Dict[str, Any],
    snapshot: TaskLoopSnapshot,
    *,
    user_reply: str = "",
) -> Dict[str, Any]:
    objective = str(step_meta.get("objective") or "").strip() or snapshot.pending_step.strip() or "Aufgabe"
    step_type = _step_type_from_meta(step_meta)
    suggested_tools = _suggested_tools(step_meta)
    requested_capability = _requested_capability(step_meta)

    # Phase 1: Capability aus Intent ableiten wenn nicht explizit gesetzt
    if not requested_capability:
        cap_hint = suggest_capability_for_step(step_title, step_meta)
        if cap_hint:
            requested_capability = cap_hint

    # Phase 2: Tools vorschlagen wenn noch keine gesetzt und Capability bekannt
    if not suggested_tools and requested_capability:
        intent_text = " ".join(filter(None, [
            step_title,
            str(step_meta.get("goal") or ""),
            str(step_meta.get("objective") or ""),
        ]))
        catalog_tools = suggest_tools_for_step(
            requested_capability.get("capability_type", ""),
            intent_text,
        )
        if catalog_tools:
            suggested_tools = catalog_tools

    plan = {
        "intent": f"{step_title}: {objective}",
        "needs_sequential_thinking": True,
        "_loop_trace_mode": "internal_loop_analysis",
        "_task_loop_step_runtime": True,
        "_response_mode": "interactive",
        "response_length_hint": "short",
        "needs_memory": False,
        "memory_keys": [],
        "needs_chat_history": False,
        "is_fact_query": False,
        "hallucination_risk": "low",
        "step_title": step_title,
        "step_goal": str(step_meta.get("goal") or "").strip(),
        "step_done_criteria": str(step_meta.get("done_criteria") or "").strip(),
        "step_type": step_type.value,
        "suggested_tools": suggested_tools or None,
        "requested_capability": requested_capability,
        "capability_context": dict(step_meta.get("capability_context") or {}),
        "_task_loop_user_reply": str(user_reply or "").strip(),
    }
    return apply_task_loop_runtime_policy(plan)


__all__ = ["build_task_loop_step_plan"]
