import pytest

from core.orchestrator_policy_runtime_utils import (
    apply_query_budget_tool_policy_runtime,
    classify_query_budget_signal,
    resolve_precontrol_policy_conflicts_runtime,
)


class _BudgetClassifier:
    async def classify(self, user_text, *, selected_tools=None, tone_signal=None):
        assert user_text == "Wie ist das Wetter?"
        assert selected_tools == ["web_search"]
        assert tone_signal == {"response_tone": "neutral"}
        return {
            "query_type": "factual",
            "intent_hint": "status",
            "complexity_signal": "low",
            "response_budget": "short",
            "tool_hint": "web_search",
            "skip_thinking_candidate": True,
            "confidence": 0.91,
            "source": "test",
        }


@pytest.mark.asyncio
async def test_classify_query_budget_signal_returns_signal_and_logs_summary():
    logs = []

    out = await classify_query_budget_signal(
        query_budget=_BudgetClassifier(),
        user_text="Wie ist das Wetter?",
        selected_tools=["web_search"],
        tone_signal={"response_tone": "neutral"},
        query_budget_enabled=True,
        log_info_fn=logs.append,
        log_warn_fn=logs.append,
    )

    assert out["query_type"] == "factual"
    assert any("query_budget type=factual" in line for line in logs)


def test_apply_query_budget_tool_policy_runtime_persists_policy_and_returns_filtered_tools():
    logs = []
    verified_plan = {
        "_query_budget": {
            "query_type": "factual",
            "complexity_signal": "low",
            "confidence": 0.93,
        }
    }

    out = apply_query_budget_tool_policy_runtime(
        "nutze das web tool",
        verified_plan,
        ["web_search", "autonomous_skill_task"],
        query_budget_enabled=True,
        max_tools_factual_low=1,
        heavy_tools=["autonomous_skill_task"],
        contains_explicit_tool_intent_fn=lambda _text: False,
        is_explicit_deep_request_fn=lambda _text: False,
        is_explicit_think_request_fn=lambda _text: False,
        extract_tool_name_fn=lambda item: str(item),
        prefix="[Test]",
        log_info_fn=logs.append,
    )

    assert out == ["web_search"]
    assert verified_plan["_query_budget_policy"]["dropped"] == 1
    assert any("QueryBudget policy applied" in line for line in logs)


def test_resolve_precontrol_policy_conflicts_runtime_logs_on_resolution():
    logs = []
    plan = {
        "_query_budget_factual_memory_forced": True,
        "_query_budget": {"query_type": "factual", "confidence": 0.9},
        "_domain_route": {"domain_tag": "CONTAINER", "domain_locked": True},
        "suggested_tools": ["exec_in_container"],
        "needs_sequential_thinking": True,
        "needs_memory": True,
    }

    out = resolve_precontrol_policy_conflicts_runtime(
        "zeige mir den container status",
        plan,
        resolver_enabled=True,
        rollout_enabled=True,
        has_memory_recall_signal_fn=lambda _text: False,
        contains_explicit_tool_intent_fn=lambda _text: False,
        looks_like_host_runtime_lookup_fn=lambda _text: False,
        has_non_memory_tool_runtime_signal_fn=lambda _text: True,
        extract_tool_name_fn=lambda item: str(item),
        log_info_fn=logs.append,
    )

    assert out["_policy_conflict_resolved"] is True
    assert any("Policy conflict resolved" in line for line in logs)
