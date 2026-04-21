from __future__ import annotations

from typing import Any, Dict, Optional


TASK_LOOP_OUTPUT_TIMEOUT_S = 300.0


def apply_task_loop_runtime_policy(step_plan: Dict[str, Any]) -> Dict[str, Any]:
    plan = dict(step_plan or {})
    if not bool(plan.get("_task_loop_step_runtime")):
        return plan
    plan["_task_loop_disable_output_budget"] = True
    plan.pop("_output_time_budget_s", None)
    return plan


def task_loop_output_timeout_override(verified_plan: Optional[Dict[str, Any]]) -> Optional[float]:
    plan = verified_plan if isinstance(verified_plan, dict) else {}
    if not bool(plan.get("_task_loop_step_runtime")):
        return None
    if not bool(plan.get("_task_loop_disable_output_budget", False)):
        return None
    return float(TASK_LOOP_OUTPUT_TIMEOUT_S)
