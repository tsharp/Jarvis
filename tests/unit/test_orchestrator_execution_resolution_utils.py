import pytest

from core.control_contract import ControlDecision
from core.orchestrator_execution_resolution_utils import (
    collect_control_tool_decisions,
    resolve_execution_suggested_tools,
)


class _Control:
    async def decide_tools(self, user_text, verified_plan):
        assert user_text == "abc"
        assert verified_plan["suggested_tools"] == ["memory_graph_search"]
        return [{"name": "memory_graph_search", "arguments": {"query": "abc"}}]


@pytest.mark.asyncio
async def test_collect_control_tool_decisions_uses_gate_override_without_calling_control():
    class _BlockedControl:
        async def decide_tools(self, *_args, **_kwargs):
            raise AssertionError("must not be called")

    out = await collect_control_tool_decisions(
        control=_BlockedControl(),
        user_text="denke",
        verified_plan={"_gate_tools_override": ["think"]},
        build_tool_args_fn=lambda tool_name, _text, _plan: {"tool": tool_name},
        tool_allowed_by_control_decision_fn=lambda _decision, _tool: True,
        stream=True,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
        log_error_fn=lambda _msg: None,
    )

    assert out == {"think": {"tool": "think"}}


@pytest.mark.asyncio
async def test_collect_control_tool_decisions_uses_control_output():
    out = await collect_control_tool_decisions(
        control=_Control(),
        user_text="abc",
        verified_plan={"suggested_tools": ["memory_graph_search"]},
        build_tool_args_fn=lambda *_args, **_kwargs: {},
        tool_allowed_by_control_decision_fn=lambda _decision, _tool: True,
        stream=False,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
        log_error_fn=lambda _msg: None,
    )

    assert out == {"memory_graph_search": {"query": "abc"}}


def test_resolve_execution_suggested_tools_prefers_followup_confirmation_reuse():
    verified_plan = {"suggested_tools": ["run_skill"], "is_fact_query": False, "dialogue_act": "request"}

    out = resolve_execution_suggested_tools(
        user_text="ja bitte testen",
        verified_plan=verified_plan,
        control_tool_decisions={},
        tool_execution_policy={},
        low_signal_action_tools=["create_skill", "think"],
        stream=True,
        conversation_id="conv-confirm",
        chat_history=[{"role": "assistant", "content": "Soll ich das testen?"}],
        finalize_execution_suggested_tools_fn=lambda plan, tools: list(tools),
        should_suppress_conversational_tools_fn=lambda *_args, **_kwargs: False,
        looks_like_short_confirmation_followup_fn=lambda *_args, **_kwargs: True,
        resolve_followup_tool_reuse_fn=lambda *_args, **_kwargs: [{"tool": "exec_in_container", "args": {"container_id": "home001"}}],
        normalize_tools_fn=lambda tools: list(tools),
        extract_tool_name_fn=lambda item: item.get("tool", "") if isinstance(item, dict) else str(item),
        get_effective_resolution_strategy_fn=lambda _plan: "",
        prioritize_home_container_tools_fn=lambda *_args, **_kwargs: list(_args[2]),
        rewrite_home_start_request_tools_fn=lambda *_args, **_kwargs: list(_args[2]),
        prioritize_active_container_capability_tools_fn=lambda *_args, **_kwargs: list(_args[2]),
        apply_container_query_policy_fn=lambda *_args, **_kwargs: list(_args[2]),
        apply_query_budget_tool_policy_fn=lambda *_args, **_kwargs: list(_args[2]),
        apply_domain_tool_policy_fn=lambda *_args, **_kwargs: list(_args[1]),
        detect_tools_by_keyword_fn=lambda _text: [],
        contains_explicit_skill_intent_fn=lambda _text: False,
        detect_skill_by_trigger_fn=lambda _text: [],
        looks_like_host_runtime_lookup_fn=lambda _text: False,
        tool_allowed_by_control_decision_fn=lambda _decision, _tool: True,
        log_info_fn=lambda _msg: None,
    )

    assert out == [{"tool": "exec_in_container", "args": {"container_id": "home001"}}]
    assert verified_plan["needs_chat_history"] is True


def test_resolve_execution_suggested_tools_uses_keyword_fallback_and_control_filter():
    verified_plan = {"suggested_tools": []}
    decision = ControlDecision.from_verification(
        {
            "approved": True,
            "decision_class": "allow",
            "tools_allowed": ["list_skills"],
        }
    )

    out = resolve_execution_suggested_tools(
        user_text="zeige skills",
        verified_plan=verified_plan,
        control_tool_decisions={},
        tool_execution_policy={},
        low_signal_action_tools=["create_skill", "think"],
        control_decision=decision,
        finalize_execution_suggested_tools_fn=lambda plan, tools: plan.setdefault("_selected_tools_for_prompt", tools) or list(tools),
        should_suppress_conversational_tools_fn=lambda *_args, **_kwargs: False,
        looks_like_short_confirmation_followup_fn=lambda *_args, **_kwargs: False,
        resolve_followup_tool_reuse_fn=lambda *_args, **_kwargs: [],
        normalize_tools_fn=lambda tools: list(tools),
        extract_tool_name_fn=lambda item: item.get("tool", "") if isinstance(item, dict) else str(item),
        get_effective_resolution_strategy_fn=lambda _plan: "",
        prioritize_home_container_tools_fn=lambda *_args, **_kwargs: list(_args[2]),
        rewrite_home_start_request_tools_fn=lambda *_args, **_kwargs: list(_args[2]),
        prioritize_active_container_capability_tools_fn=lambda *_args, **_kwargs: list(_args[2]),
        apply_container_query_policy_fn=lambda *_args, **_kwargs: list(_args[2]),
        apply_query_budget_tool_policy_fn=lambda *_args, **_kwargs: list(_args[2]),
        apply_domain_tool_policy_fn=lambda *_args, **_kwargs: list(_args[1]),
        detect_tools_by_keyword_fn=lambda _text: ["list_skills", "exec_in_container"],
        contains_explicit_skill_intent_fn=lambda _text: False,
        detect_skill_by_trigger_fn=lambda _text: [],
        looks_like_host_runtime_lookup_fn=lambda _text: False,
        tool_allowed_by_control_decision_fn=lambda _decision, tool: tool == "list_skills",
        log_info_fn=lambda _msg: None,
    )

    assert out == ["list_skills"]
