from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List

from core.task_loop.contracts import (
    RiskLevel,
    StopReason,
    TaskLoopSnapshot,
    TaskLoopStepExecutionSource,
    TaskLoopStepStatus,
    TaskLoopStepType,
    transition_task_loop_step,
)
from core.task_loop.tool_step_policy import should_execute_tool_via_orchestrator


def _format_plan(snapshot: TaskLoopSnapshot) -> str:
    completed = set(snapshot.completed_steps)
    lines = []
    for idx, step in enumerate(snapshot.current_plan, start=1):
        marker = (
            "erledigt"
            if step in completed
            else "naechstes"
            if step == snapshot.pending_step
            else "offen"
        )
        lines.append(f"{idx}. [{marker}] {step}")
    return "\n".join(lines)


def _step_meta(snapshot: TaskLoopSnapshot, title: str) -> Dict[str, Any]:
    for step in snapshot.plan_steps:
        if isinstance(step, dict) and str(step.get("title") or "") == title:
            return step
    return {}


def _risk_for_step(snapshot: TaskLoopSnapshot, title: str) -> RiskLevel:
    meta = _step_meta(snapshot, title)
    raw = str(meta.get("risk_level") or RiskLevel.SAFE.value).strip().lower()
    try:
        return RiskLevel(raw)
    except Exception:
        return RiskLevel.SAFE


def _step_type_for_step(snapshot: TaskLoopSnapshot, title: str) -> TaskLoopStepType:
    meta = _step_meta(snapshot, title)
    raw = str(meta.get("step_type") or "").strip().lower()
    try:
        return TaskLoopStepType(raw)
    except Exception:
        return TaskLoopStepType.ANALYSIS


def _step_id_for_step(snapshot: TaskLoopSnapshot, title: str) -> str:
    meta = _step_meta(snapshot, title)
    raw = str(meta.get("step_id") or "").strip()
    if raw:
        return raw
    if snapshot.current_step_id:
        return snapshot.current_step_id
    return f"step-{int(snapshot.step_index or 0) + 1}"


def _default_execution_source(step_type: TaskLoopStepType) -> TaskLoopStepExecutionSource:
    if should_execute_tool_via_orchestrator(step_type):
        return TaskLoopStepExecutionSource.ORCHESTRATOR
    return TaskLoopStepExecutionSource.LOOP


def _merge_verified_artifacts(
    snapshot: TaskLoopSnapshot,
    new_artifacts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged = list(snapshot.verified_artifacts)
    for artifact in new_artifacts or []:
        if isinstance(artifact, dict):
            merged.append(dict(artifact))
    return merged


def _set_step_running(snapshot: TaskLoopSnapshot, title: str) -> TaskLoopSnapshot:
    step_type = _step_type_for_step(snapshot, title)
    step_id = _step_id_for_step(snapshot, title)
    reset = step_id != str(snapshot.current_step_id or "")
    return transition_task_loop_step(
        snapshot,
        next_step_id=step_id,
        next_step_type=step_type,
        next_step_status=TaskLoopStepStatus.RUNNING,
        step_execution_source=_default_execution_source(step_type),
        reset_for_new_step=reset,
    )


def _prime_next_step(snapshot: TaskLoopSnapshot, next_step: str) -> TaskLoopSnapshot:
    if not next_step:
        return snapshot
    next_type = _step_type_for_step(snapshot, next_step)
    next_id = _step_id_for_step(snapshot, next_step)
    return transition_task_loop_step(
        snapshot,
        next_step_id=next_id,
        next_step_type=next_type,
        next_step_status=TaskLoopStepStatus.PENDING,
        step_execution_source=_default_execution_source(next_type),
        reset_for_new_step=True,
    )


def _inject_follow_up_step(snapshot: TaskLoopSnapshot, next_step: str) -> TaskLoopSnapshot:
    next_title = str(next_step or "").strip()
    if not next_title:
        return snapshot

    current_plan = list(snapshot.current_plan or [])
    if next_title not in current_plan:
        current_plan.append(next_title)

    plan_steps = list(snapshot.plan_steps or [])
    if not any(str(step.get("title") or "") == next_title for step in plan_steps if isinstance(step, dict)):
        plan_steps.append(
            {
                "title": next_title,
                "step_type": TaskLoopStepType.ANALYSIS.value,
                "risk_level": RiskLevel.SAFE.value,
                "step_id": f"step-{len(current_plan)}",
            }
        )

    updated = replace(
        snapshot,
        current_plan=current_plan,
        plan_steps=plan_steps,
        pending_step=next_title,
        risk_level=RiskLevel.SAFE,
    )
    return _prime_next_step(updated, next_title)


def _done_reason_for_stop(reason: StopReason) -> str:
    return f"task_loop_{reason.value}"


def _append_visible_content(current: str, delta: str) -> str:
    if not delta:
        return current
    if not current:
        return delta
    if current.endswith("\n") or delta.startswith("\n"):
        return current + delta
    return current + "\n" + delta


__all__ = [
    "_append_visible_content",
    "_default_execution_source",
    "_done_reason_for_stop",
    "_format_plan",
    "_inject_follow_up_step",
    "_merge_verified_artifacts",
    "_prime_next_step",
    "_risk_for_step",
    "_set_step_running",
    "_step_id_for_step",
    "_step_meta",
    "_step_type_for_step",
]
