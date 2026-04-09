import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.orchestrator_pipeline_facade_utils import (
    append_context_block,
    apply_final_cap,
    build_failure_compact_block,
    build_summary_from_structure,
    execute_thinking_layer,
    maybe_prefetch_skills,
    tool_context_has_failures_or_skips,
    tool_context_has_success,
    verify_container_running,
)


def test_append_context_block_updates_trace_and_supports_prepend():
    trace = {"context_sources": [], "context_chars_final": 0}

    out = append_context_block("world", "hello ", "greeting", trace, prepend=True)

    assert out == "hello world"
    assert trace["context_sources"] == ["greeting"]
    assert trace["context_chars_final"] == len("hello ")


def test_build_failure_compact_block_passes_single_truth_exclusion():
    captured = {}

    def _get_compact(conv_id, has_tool_failure=False, **kwargs):
        captured["conv_id"] = conv_id
        captured["has_tool_failure"] = has_tool_failure
        captured["kwargs"] = kwargs
        return "NOW:\n  - state"

    out = build_failure_compact_block(
        "conv-1",
        0,
        False,
        get_compact_context_fn=_get_compact,
    )

    assert "[COMPACT-CONTEXT-ON-FAILURE]" in out
    assert captured["conv_id"] == "conv-1"
    assert captured["has_tool_failure"] is True
    assert captured["kwargs"]["exclude_event_types"] == {"tool_result"}


def test_apply_final_cap_truncates_and_updates_trace():
    trace = {"context_chars_final": 999}
    with patch("config.get_small_model_final_cap", return_value=5), patch(
        "config.get_small_model_char_cap", return_value=10
    ):
        out = apply_final_cap(
            "abcdefghijk",
            trace,
            True,
            "unit",
            log_warn_fn=lambda _msg: None,
        )

    assert out == "abcde"
    assert trace["context_chars_final"] == 5


def test_tool_context_helpers_detect_failure_and_success_cards():
    fail_ctx = "[request_container]: FEHLER missing blueprint"
    ok_ctx = "[TOOL-CARD:ref | ✅ ok | payload]"

    assert tool_context_has_failures_or_skips(fail_ctx) is True
    assert tool_context_has_success(fail_ctx) is False
    assert tool_context_has_success(ok_ctx) is True


def test_maybe_prefetch_skills_returns_full_in_non_small_mode():
    with patch("config.get_small_model_mode", return_value=False), patch(
        "config.get_skill_context_renderer", return_value="typedstate"
    ):
        out = maybe_prefetch_skills(
            "list skills",
            ["list_skills"],
            get_skill_context_fn=lambda query: f"SKILLS:\n- {query}",
            read_only_skill_tools=["list_skills"],
            log_debug_fn=lambda _msg: None,
        )

    assert out == ("SKILLS:\n- list skills", "full")


def test_maybe_prefetch_skills_uses_legacy_thin_cap_for_small_mode():
    with patch("config.get_small_model_mode", return_value=True), patch(
        "config.get_small_model_skill_prefetch_policy", return_value="thin"
    ), patch("config.get_small_model_skill_prefetch_thin_cap", return_value=20), patch(
        "config.get_skill_context_renderer", return_value="legacy"
    ):
        out = maybe_prefetch_skills(
            "list skills",
            ["list_skills"],
            get_skill_context_fn=lambda _query: "HEADER\n- alpha\n- beta\n",
            read_only_skill_tools=["list_skills"],
            log_debug_fn=lambda _msg: None,
        )

    assert out == ("HEADER\n- alpha", "thin")


def test_verify_container_running_returns_false_on_tool_error():
    hub = MagicMock()
    hub.call_tool.return_value = {"error": "missing"}

    out = verify_container_running(
        "abcdef1234567890",
        get_hub_fn=lambda: hub,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
    )

    assert out is False
    hub.initialize.assert_called_once()


def test_build_summary_from_structure_renders_headings_keywords_and_intro():
    out = build_summary_from_structure(
        {
            "total_chars": 120,
            "total_tokens": 30,
            "complexity": 4,
            "headings": [{"level": 2, "text": "Intro"}],
            "keywords": ["docker", "gpu"],
            "intro": "hello world",
        }
    )

    assert "# Document Overview" in out
    assert "## Structure" in out
    assert "docker, gpu" in out
    assert "hello world" in out


@pytest.mark.asyncio
async def test_execute_thinking_layer_logs_and_returns_plan():
    thinking = MagicMock()
    thinking.analyze = AsyncMock(
        return_value={
            "intent": "question",
            "needs_memory": True,
            "memory_keys": ["foo"],
            "hallucination_risk": "low",
        }
    )
    seen = []

    out = await execute_thinking_layer(
        "what is foo",
        thinking_layer=thinking,
        log_info_fn=seen.append,
    )

    assert out["intent"] == "question"
    assert any("LAYER 1: THINKING" in msg for msg in seen)
    thinking.analyze.assert_awaited_once_with("what is foo")
