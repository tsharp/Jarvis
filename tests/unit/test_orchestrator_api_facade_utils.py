import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from core.orchestrator_api_facade_utils import (
    check_pending_confirmation,
    execute_autonomous_objective,
    execute_control_layer,
    process_chunked_stream,
    process_request,
    process_stream_with_events,
    save_memory,
)


@pytest.mark.asyncio
async def test_check_pending_confirmation_delegates_to_underlying_util():
    util = AsyncMock(return_value="ok")

    out = await check_pending_confirmation(
        object(),
        "ja",
        "conv-1",
        intent_system_available=True,
        get_intent_store_fn=lambda: None,
        get_hub_fn=lambda: None,
        intent_state_cls=object,
        core_chat_response_cls=object,
        util_check_pending_confirmation_fn=util,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
        log_error_fn=lambda _msg: None,
    )

    assert out == "ok"
    util.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_autonomous_objective_logs_and_returns_result():
    master = SimpleNamespace(
        execute_objective=AsyncMock(return_value={"success": True, "loops": 1})
    )
    seen = []

    out = await execute_autonomous_objective(
        "Review code",
        "conv-1",
        master=master,
        max_loops=3,
        log_info_fn=seen.append,
    )

    assert out["success"] is True
    assert any("Starting autonomous objective" in msg for msg in seen)
    assert any("Autonomous objective completed" in msg for msg in seen)


@pytest.mark.asyncio
async def test_process_request_delegates_to_sync_flow_util():
    util = AsyncMock(return_value="response")

    out = await process_request(
        object(),
        object(),
        core_chat_response_cls=object,
        intent_system_available=False,
        get_master_settings_fn=lambda: {},
        thinking_plan_cache={},
        soften_control_deny_fn=lambda *args, **kwargs: None,
        util_process_request_fn=util,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
        log_warning_fn=lambda _msg: None,
    )

    assert out == "response"
    util.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_stream_with_events_reyields_items():
    async def _util(*_args, **_kwargs):
        yield ("a", False, {"type": "content"})
        yield ("", True, {"done_reason": "ok"})

    out = []
    async for item in process_stream_with_events(
        object(),
        object(),
        intent_system_available=False,
        enable_chunking=False,
        chunking_threshold=0,
        get_master_settings_fn=lambda: {},
        thinking_plan_cache={},
        sequential_result_cache={},
        soften_control_deny_fn=lambda *args, **kwargs: None,
        skill_creation_intent_cls=None,
        intent_origin_cls=None,
        get_intent_store_fn=lambda: None,
        util_process_stream_with_events_fn=_util,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
        log_error_fn=lambda _msg: None,
        log_debug_fn=lambda _msg: None,
        log_warning_fn=lambda _msg: None,
    ):
        out.append(item)

    assert out == [("a", False, {"type": "content"}), ("", True, {"done_reason": "ok"})]


@pytest.mark.asyncio
async def test_process_chunked_stream_reyields_items():
    async def _util(*_args, **_kwargs):
        yield ("chunk", False, {"type": "chunk"})

    out = []
    async for item in process_chunked_stream(
        object(),
        "text",
        "conv-1",
        object(),
        util_process_chunked_stream_fn=_util,
        get_hub_fn=lambda: None,
        log_info_fn=lambda _msg: None,
        log_error_fn=lambda _msg: None,
    ):
        out.append(item)

    assert out == [("chunk", False, {"type": "chunk"})]


@pytest.mark.asyncio
async def test_execute_control_layer_delegates_to_underlying_util():
    util = AsyncMock(return_value=({"approved": True}, {"_verified": True}))

    out = await execute_control_layer(
        object(),
        "hello",
        {"intent": "question"},
        "memory",
        "conv-1",
        response_mode="interactive",
        intent_system_available=False,
        skill_creation_intent_cls=None,
        intent_origin_cls=None,
        get_intent_store_fn=lambda: None,
        util_execute_control_layer_fn=util,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
    )

    assert out[0]["approved"] is True
    util.assert_awaited_once()


def test_save_memory_delegates_all_required_callbacks():
    util = MagicMock()

    save_memory(
        "conv-1",
        {"ok": True},
        "answer",
        util_save_memory_fn=util,
        call_tool_fn=lambda *_args, **_kwargs: None,
        autosave_assistant_fn=lambda *_args, **_kwargs: None,
        load_grounding_policy_fn=lambda: {},
        get_runtime_tool_results_fn=lambda *_args, **_kwargs: [],
        count_successful_grounding_evidence_fn=lambda *_args, **_kwargs: 0,
        extract_suggested_tool_names_fn=lambda *_args, **_kwargs: [],
        get_runtime_tool_failure_fn=lambda *_args, **_kwargs: None,
        tool_context_has_failures_or_skips_fn=lambda *_args, **_kwargs: False,
        get_runtime_grounding_value_fn=lambda *_args, **_kwargs: None,
        get_autosave_dedupe_guard_fn=lambda: None,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
        log_error_fn=lambda _msg: None,
    )

    util.assert_called_once()
    kwargs = util.call_args.kwargs
    assert kwargs["conversation_id"] == "conv-1"
    assert kwargs["answer"] == "answer"
