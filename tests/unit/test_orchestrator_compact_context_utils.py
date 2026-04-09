from unittest.mock import MagicMock, patch

from core.orchestrator_compact_context_utils import (
    apply_effective_context_guardrail,
    get_compact_context,
)


def test_get_compact_context_budget_2_fetches_container_store_and_wires_retrieval_count():
    context_manager = MagicMock()
    calls = []

    def _capture(**kwargs):
        calls.append(kwargs)
        if kwargs.get("conversation_id") == "_container_events":
            return "NOW:\n  - container events"
        return "NOW:\n  - local state"

    context_manager.build_small_model_context.side_effect = _capture

    with patch("config.get_small_model_mode", return_value=True), \
         patch("config.get_jit_retrieval_max", return_value=1), \
         patch("config.get_jit_retrieval_max_on_failure", return_value=2), \
         patch("config.get_small_model_now_max", return_value=5), \
         patch("config.get_small_model_rules_max", return_value=3), \
         patch("config.get_small_model_next_max", return_value=2):
        result = get_compact_context(
            context_manager=context_manager,
            conversation_id="conv-1",
            has_tool_failure=True,
            exclude_event_types={"tool_result"},
            csv_trigger="csv",
            log_info_fn=lambda _msg: None,
            log_warn_fn=lambda _msg: None,
        )

    assert len(calls) == 2
    assert calls[0]["limits"]["retrieval_count"] == 2
    assert calls[0]["trigger"] == "csv"
    assert calls[1]["conversation_id"] == "_container_events"
    assert calls[1]["limits"]["retrieval_count"] == 2
    assert "local state" in result
    assert "container events" in result


def test_get_compact_context_returns_fail_closed_context_on_error():
    context_manager = MagicMock()
    context_manager.build_small_model_context.side_effect = RuntimeError("hub down")

    with patch("config.get_small_model_mode", return_value=True), \
         patch("config.get_jit_retrieval_max", return_value=1), \
         patch("config.get_jit_retrieval_max_on_failure", return_value=2), \
         patch("config.get_small_model_now_max", return_value=5), \
         patch("config.get_small_model_rules_max", return_value=3), \
         patch("config.get_small_model_next_max", return_value=2):
        result = get_compact_context(
            context_manager=context_manager,
            conversation_id="conv-2",
            log_info_fn=lambda _msg: None,
            log_warn_fn=lambda _msg: None,
        )

    assert result != ""
    assert "CONTEXT ERROR" in result
    assert "NEXT" in result


def test_apply_effective_context_guardrail_keeps_head_and_tail_with_marker():
    trace = {"context_sources": [], "context_chars_final": 0}
    ctx = "A" * 220 + "TAIL"

    with patch("config.get_effective_context_guardrail_chars", return_value=160):
        clipped = apply_effective_context_guardrail(
            ctx=ctx,
            trace=trace,
            small_model_mode=False,
            label="unit",
            log_warn_fn=lambda _msg: None,
        )

    assert clipped != ctx
    assert "[...context truncated by guardrail...]" in clipped
    assert clipped.startswith("A" * 112)
    assert clipped.endswith("TAIL")
    assert trace["context_chars_final"] == len(clipped)
    assert "guardrail_ctx" in trace["context_sources"]
