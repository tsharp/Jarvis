from core.task_loop.contracts import RiskLevel, TaskLoopStepType
from core.task_loop.tool_step_policy import (
    infer_planned_step_type,
    normalize_runtime_step_type,
    step_tools_for_spec,
)


def test_step_tools_for_spec_keeps_safe_query_tools_on_tool_step():
    tools = step_tools_for_spec(
        index=3,
        total_steps=4,
        step_risk=RiskLevel.SAFE,
        suggested_tools=["blueprint_list"],
    )

    assert tools == ["blueprint_list"]


def test_infer_planned_step_type_marks_safe_tool_step_as_execution():
    step_type = infer_planned_step_type(
        "Container-Blueprints kontrolliert abrufen",
        index=3,
        total_steps=4,
        step_risk=RiskLevel.SAFE,
        suggested_tools=["blueprint_list"],
    )

    assert step_type is TaskLoopStepType.TOOL_EXECUTION


def test_normalize_runtime_step_type_preserves_planned_request_type():
    assert normalize_runtime_step_type(TaskLoopStepType.TOOL_REQUEST) is TaskLoopStepType.TOOL_REQUEST
