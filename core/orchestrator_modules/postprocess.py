from __future__ import annotations

from typing import Any, Callable, Dict


def post_task_processing(
    *,
    get_archive_embedding_queue_fn: Callable[[], Any],
    archive_manager: Any,
    log_debug_fn: Callable[[str], None],
    log_info_fn: Callable[[str], None],
    log_error_fn: Callable[[str], None],
) -> None:
    try:
        queue = get_archive_embedding_queue_fn()
        queue.ensure_worker_running(
            lambda: archive_manager.process_pending_embeddings(batch_size=5)
        )
        job_id = queue.enqueue()
        log_debug_fn(
            f"[PostTask] queued archive-embedding job_id={job_id} pending={queue.pending_count()}"
        )
    except Exception as exc:
        log_error_fn(f"[PostTask] queue enqueue failed, fallback inline processing: {exc}")
        try:
            processed = archive_manager.process_pending_embeddings(batch_size=5)
            if processed > 0:
                log_info_fn(f"[PostTask] Processed {processed} archive embeddings (inline fallback)")
        except Exception as inner:
            log_error_fn(f"[PostTask] Inline fallback embedding processing failed: {inner}")


def save_memory(
    *,
    conversation_id: str,
    verified_plan: Dict[str, Any],
    answer: str,
    call_tool_fn: Callable[[str, Dict[str, Any]], Any],
    autosave_assistant_fn: Callable[..., Any],
    load_grounding_policy_fn: Callable[[], Dict[str, Any]],
    get_runtime_tool_results_fn: Callable[[Dict[str, Any]], Any],
    count_successful_grounding_evidence_fn: Callable[[Dict[str, Any], Any], int],
    extract_suggested_tool_names_fn: Callable[[Dict[str, Any]], Any],
    get_runtime_tool_failure_fn: Callable[[Dict[str, Any]], Any],
    tool_context_has_failures_or_skips_fn: Callable[[str], bool],
    get_runtime_grounding_value_fn: Callable[..., Any],
    get_autosave_dedupe_guard_fn: Callable[[], Any],
    log_info_fn: Callable[[str], None],
    log_warn_fn: Callable[[str], None],
    log_error_fn: Callable[[str], None],
) -> None:
    if verified_plan.get("is_new_fact"):
        fact_key = verified_plan.get("new_fact_key")
        fact_value = verified_plan.get("new_fact_value")
        if fact_key and fact_value:
            log_info_fn(f"[Orchestrator-Save] Saving fact: {fact_key}={fact_value}")
            try:
                fact_args = {
                    "conversation_id": conversation_id,
                    "subject": "Danny",
                    "key": fact_key,
                    "value": fact_value,
                    "layer": "ltm",
                }
                call_tool_fn("memory_fact_save", fact_args)
            except Exception as exc:
                log_error_fn(f"[Orchestrator-Save] Error: {exc}")

    tool_ctx = str(get_runtime_tool_results_fn(verified_plan) or "")
    grounding_policy = load_grounding_policy_fn()
    output_grounding = (grounding_policy or {}).get("output") or {}
    memory_grounding = (grounding_policy or {}).get("memory") or {}
    allowed_statuses = output_grounding.get("allowed_evidence_statuses", ["ok"])
    min_successful_evidence = int(output_grounding.get("min_successful_evidence", 1) or 1)
    successful_evidence = count_successful_grounding_evidence_fn(
        verified_plan,
        allowed_statuses=allowed_statuses,
    )
    is_fact_query = bool(verified_plan.get("is_fact_query", False))
    has_tool_usage = bool(tool_ctx.strip())
    has_tool_suggestions = bool(extract_suggested_tool_names_fn(verified_plan))
    require_evidence_for_autosave = bool(
        memory_grounding.get("autosave_requires_evidence_for_fact_query", True)
        and is_fact_query
        and (
            (
                bool(output_grounding.get("enforce_evidence_for_fact_query", True))
                and (has_tool_usage or has_tool_suggestions)
            )
            or (
                bool(output_grounding.get("enforce_evidence_when_tools_used", True))
                and has_tool_usage
            )
            or (
                bool(output_grounding.get("enforce_evidence_when_tools_suggested", True))
                and has_tool_suggestions
            )
        )
    )
    skip_autosave = False
    skip_reason = ""
    if verified_plan.get("_pending_intent"):
        skip_autosave = True
        skip_reason = "pending_intent_confirmation"
    elif (
        (get_runtime_tool_failure_fn(verified_plan) or tool_context_has_failures_or_skips_fn(tool_ctx))
        and not (answer or "").strip()
    ):
        skip_autosave = True
        skip_reason = "tool_failure_with_empty_answer"
    elif bool(get_runtime_grounding_value_fn(verified_plan, key="missing_evidence", default=False)):
        skip_autosave = True
        skip_reason = "grounding_missing_evidence"
    elif bool(get_runtime_grounding_value_fn(verified_plan, key="violation_detected", default=False)):
        skip_autosave = True
        skip_reason = "grounding_violation_detected"
    elif require_evidence_for_autosave and successful_evidence < min_successful_evidence:
        skip_autosave = True
        skip_reason = "insufficient_grounding_evidence"

    if skip_autosave:
        log_warn_fn(f"[Orchestrator-Autosave] Skipped assistant autosave ({skip_reason})")
        return

    dedupe_guard = get_autosave_dedupe_guard_fn()
    if dedupe_guard is not None:
        try:
            if dedupe_guard.should_skip(conversation_id=conversation_id, content=answer):
                log_warn_fn("[Orchestrator-Autosave] Skipped assistant autosave (duplicate_window)")
                return
        except Exception as dedupe_err:
            log_warn_fn(f"[Orchestrator-Autosave] Dedupe guard fallback: {dedupe_err}")

    try:
        autosave_assistant_fn(
            conversation_id=conversation_id,
            content=answer,
            layer="stm",
        )
    except Exception as exc:
        log_error_fn(f"[Orchestrator-Autosave] Error: {exc}")
