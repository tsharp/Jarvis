from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.task_loop.pipeline_adapter import build_task_loop_planning_context


@pytest.mark.asyncio
async def test_build_task_loop_planning_context_uses_selected_tools_for_thinking():
    captured = {}

    async def _analyze(user_text, memory_context="", available_tools=None, tone_signal=None, tool_hints=None):
        captured["user_text"] = user_text
        captured["memory_context"] = memory_context
        captured["available_tools"] = list(available_tools or [])
        captured["tone_signal"] = tone_signal
        captured["tool_hints"] = tool_hints
        return {
            "intent": "Gaming-Container kontrolliert anfordern",
            "suggested_tools": ["request_container"],
        }

    orch = SimpleNamespace(
        tool_selector=SimpleNamespace(select_tools=AsyncMock(return_value=["request_container"])),
        _filter_tool_selector_candidates=lambda tools, _user_text, forced_mode=None: list(tools),
        _classify_query_budget_signal=AsyncMock(return_value={}),
        _classify_domain_signal=AsyncMock(return_value={}),
        _maybe_prefetch_skills=lambda _user_text, _selected_tools: ("skill-context", "off"),
        _ensure_dialogue_controls=lambda plan, *_args, **_kwargs: plan,
        thinking=SimpleNamespace(analyze=AsyncMock(side_effect=_analyze)),
    )

    plan = await build_task_loop_planning_context(
        orch,
        "Bitte fordere einen Gaming-Container an",
        request=SimpleNamespace(messages=[], raw_request={}),
        tone_signal={"dialogue_act": "request"},
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
    )

    assert plan["suggested_tools"] == ["request_container"]
    assert captured["available_tools"] == [
        {
            "name": "request_container",
            "mcp": "unknown",
            "server": "unknown",
            "description": "",
            "inputSchema": {},
            "transport": "",
            "execution_class": "unknown",
            "visibility": "default",
            "tags": [],
        }
    ]
    assert captured["memory_context"] == "skill-context"
    assert captured["tone_signal"] == {"dialogue_act": "request"}
    # tool_hints should be injected (base rules when no hub is set)
    assert captured["tool_hints"] is not None
    assert "MCP DETECTION RULES" in captured["tool_hints"]
    assert plan["_container_capability_context"]["request_family"] == "generic_container"


@pytest.mark.asyncio
async def test_build_task_loop_planning_context_enriches_python_container_capability_context():
    async def _analyze(user_text, memory_context="", available_tools=None, tone_signal=None, tool_hints=None):
        return {
            "intent": "Python-Container fuer Datenanalyse vorbereiten",
            "suggested_tools": ["request_container"],
        }

    orch = SimpleNamespace(
        tool_selector=SimpleNamespace(select_tools=AsyncMock(return_value=["request_container"])),
        _filter_tool_selector_candidates=lambda tools, _user_text, forced_mode=None: list(tools),
        _classify_query_budget_signal=AsyncMock(return_value={}),
        _classify_domain_signal=AsyncMock(return_value={}),
        _maybe_prefetch_skills=lambda _user_text, _selected_tools: ("", "off"),
        _ensure_dialogue_controls=lambda plan, *_args, **_kwargs: plan,
        thinking=SimpleNamespace(analyze=AsyncMock(side_effect=_analyze)),
    )

    plan = await build_task_loop_planning_context(
        orch,
        "Ich moechte einen Python-Container fuer Datenanalyse vorbereiten.",
        request=SimpleNamespace(messages=[], raw_request={}),
        tone_signal={"dialogue_act": "request"},
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
    )

    assert plan["_container_capability_context"]["request_family"] == "python_container"
    assert plan["_container_capability_context"]["python_requested"] is True
