from core.task_loop.runtime_policy import (
    TASK_LOOP_OUTPUT_TIMEOUT_S,
    apply_task_loop_runtime_policy,
    task_loop_output_timeout_override,
)


def test_apply_task_loop_runtime_policy_disables_output_budget():
    plan = apply_task_loop_runtime_policy(
        {
            "_task_loop_step_runtime": True,
            "_output_time_budget_s": 8.0,
        }
    )

    assert plan["_task_loop_disable_output_budget"] is True
    assert "_output_time_budget_s" not in plan


def test_task_loop_output_timeout_override_returns_long_timeout_for_loop_steps():
    timeout_s = task_loop_output_timeout_override(
        {
            "_task_loop_step_runtime": True,
            "_task_loop_disable_output_budget": True,
        }
    )

    assert timeout_s == TASK_LOOP_OUTPUT_TIMEOUT_S
