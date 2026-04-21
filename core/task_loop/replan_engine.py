"""Generic task-loop replan engine.

Ziel:
- Recovery- oder Verify-Hinweise in neue Plan-Schritte uebersetzen
- keine domain-spezifische Container-/Skill-/Cron-Policy enthalten
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict

from core.task_loop.contracts import TaskLoopSnapshot


def apply_replan_hint(
    snapshot: TaskLoopSnapshot,
    *,
    current_step_title: str,
    current_step_meta: Dict[str, Any],
    replan_hint: Dict[str, Any],
) -> TaskLoopSnapshot:
    if str(replan_hint.get("recovery_mode") or "").strip().lower() != "replan_with_tools":
        return snapshot

    replan_title = str(replan_hint.get("replan_step_title") or "").strip()
    if not replan_title:
        return snapshot

    recovery_step = dict(replan_hint.get("replan_step") or {})
    if not recovery_step:
        return snapshot

    current_plan = list(snapshot.current_plan)
    plan_steps = [dict(step) for step in list(snapshot.plan_steps or []) if isinstance(step, dict)]

    try:
        current_index = current_plan.index(current_step_title)
    except ValueError:
        current_index = len(list(snapshot.completed_steps or []))

    if replan_title in current_plan:
        existing_index = current_plan.index(replan_title)
        if existing_index > current_index:
            current_plan.pop(existing_index)
            current_plan.insert(current_index, replan_title)
            if existing_index < len(plan_steps):
                existing_step = plan_steps.pop(existing_index)
                plan_steps.insert(current_index, existing_step)
            return replace(snapshot, current_plan=current_plan, plan_steps=plan_steps)
        recovery_title = f"{replan_title} (Recovery)"
        recovery_step["title"] = recovery_title
        current_plan.insert(current_index, recovery_title)
        plan_steps.insert(current_index, recovery_step)
        return replace(snapshot, current_plan=current_plan, plan_steps=plan_steps)

    current_plan.insert(current_index, replan_title)
    plan_steps.insert(current_index, recovery_step)
    return replace(snapshot, current_plan=current_plan, plan_steps=plan_steps)


__all__ = ["apply_replan_hint"]
