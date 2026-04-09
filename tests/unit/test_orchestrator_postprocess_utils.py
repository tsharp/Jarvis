from unittest.mock import MagicMock

from core.orchestrator_postprocess_utils import (
    post_task_processing,
    save_memory,
)


def test_post_task_processing_enqueues_job_and_falls_back_inline():
    queue = MagicMock()
    queue.enqueue.return_value = 42
    queue.pending_count.return_value = 1
    archive_manager = MagicMock()

    post_task_processing(
        get_archive_embedding_queue_fn=lambda: queue,
        archive_manager=archive_manager,
        log_debug_fn=lambda _msg: None,
        log_info_fn=lambda _msg: None,
        log_error_fn=lambda _msg: None,
    )

    queue.ensure_worker_running.assert_called_once()
    queue.enqueue.assert_called_once()

    archive_manager = MagicMock()
    post_task_processing(
        get_archive_embedding_queue_fn=lambda: (_ for _ in ()).throw(RuntimeError("queue down")),
        archive_manager=archive_manager,
        log_debug_fn=lambda _msg: None,
        log_info_fn=lambda _msg: None,
        log_error_fn=lambda _msg: None,
    )
    archive_manager.process_pending_embeddings.assert_called_once_with(batch_size=5)


def test_save_memory_saves_fact_and_skips_or_autosaves_as_expected():
    fact_calls = []
    autosave_calls = []

    save_memory(
        conversation_id="conv-1",
        verified_plan={
            "is_new_fact": True,
            "new_fact_key": "favorite_color",
            "new_fact_value": "blue",
            "_pending_intent": {"id": "intent-1"},
        },
        answer="Antwort",
        call_tool_fn=lambda tool_name, args: fact_calls.append((tool_name, args)),
        autosave_assistant_fn=lambda **kwargs: autosave_calls.append(kwargs),
        load_grounding_policy_fn=lambda: {},
        get_runtime_tool_results_fn=lambda _plan: "",
        count_successful_grounding_evidence_fn=lambda _plan, allowed_statuses=None: 0,
        extract_suggested_tool_names_fn=lambda _plan: [],
        get_runtime_tool_failure_fn=lambda _plan: False,
        tool_context_has_failures_or_skips_fn=lambda _ctx: False,
        get_runtime_grounding_value_fn=lambda _plan, key, default=False: default,
        get_autosave_dedupe_guard_fn=lambda: None,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
        log_error_fn=lambda _msg: None,
    )

    assert fact_calls[0][0] == "memory_fact_save"
    assert autosave_calls == []

    save_memory(
        conversation_id="conv-2",
        verified_plan={"_tool_results": "### TOOL-SKIP (...)", "is_fact_query": False},
        answer="Hier ist trotz Tool-Skip eine sinnvolle Antwort.",
        call_tool_fn=lambda *_args, **_kwargs: None,
        autosave_assistant_fn=lambda **kwargs: autosave_calls.append(kwargs),
        load_grounding_policy_fn=lambda: {},
        get_runtime_tool_results_fn=lambda plan: plan.get("_tool_results", ""),
        count_successful_grounding_evidence_fn=lambda _plan, allowed_statuses=None: 0,
        extract_suggested_tool_names_fn=lambda _plan: [],
        get_runtime_tool_failure_fn=lambda _plan: False,
        tool_context_has_failures_or_skips_fn=lambda ctx: "TOOL-SKIP" in ctx,
        get_runtime_grounding_value_fn=lambda _plan, key, default=False: default,
        get_autosave_dedupe_guard_fn=lambda: None,
        log_info_fn=lambda _msg: None,
        log_warn_fn=lambda _msg: None,
        log_error_fn=lambda _msg: None,
    )

    assert autosave_calls[-1]["conversation_id"] == "conv-2"
