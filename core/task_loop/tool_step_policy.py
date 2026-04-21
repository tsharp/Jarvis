from __future__ import annotations

from core.task_loop.contracts import RiskLevel, TaskLoopStepType


def should_split_tool_execution(
    *,
    risk_level: RiskLevel,
    suggested_tools: list[str],
) -> bool:
    tools = [str(item or "").strip() for item in suggested_tools or [] if str(item or "").strip()]
    return bool(tools) and risk_level is not RiskLevel.SAFE


def step_tools_for_spec(
    *,
    index: int,
    total_steps: int,
    step_risk: RiskLevel,
    suggested_tools: list[str],
) -> list[str]:
    tools = [str(item or "").strip() for item in suggested_tools or [] if str(item or "").strip()]
    if not tools:
        return []
    if total_steps >= 5:
        if index in {3, 4}:
            return list(tools)
        return []
    tool_step_index = min(3, max(1, total_steps - 1))
    if index == tool_step_index:
        return list(tools)
    return []


def infer_planned_step_type(
    title: str,
    *,
    index: int,
    total_steps: int,
    step_risk: RiskLevel,
    suggested_tools: list[str],
) -> TaskLoopStepType:
    lower = " ".join(str(title or "").strip().lower().split())
    if suggested_tools and total_steps >= 5 and index == 4:
        return TaskLoopStepType.TOOL_EXECUTION
    if suggested_tools:
        if step_risk is not RiskLevel.SAFE:
            return TaskLoopStepType.TOOL_REQUEST
        return TaskLoopStepType.TOOL_EXECUTION
    if index == total_steps or any(
        phrase in lower
        for phrase in (
            "zusammenfassen",
            "zwischenfazit",
            "befund und naechsten produktpfad",
            "folgepfad zusammenfassen",
        )
    ):
        return TaskLoopStepType.RESPONSE
    return TaskLoopStepType.ANALYSIS


def normalize_runtime_step_type(planned_step_type: TaskLoopStepType) -> TaskLoopStepType:
    if planned_step_type in {TaskLoopStepType.TOOL_REQUEST, TaskLoopStepType.TOOL_EXECUTION}:
        return planned_step_type
    return planned_step_type


def should_execute_tool_via_orchestrator(step_type: TaskLoopStepType) -> bool:
    return step_type is TaskLoopStepType.TOOL_EXECUTION
