from __future__ import annotations

from typing import Any, AsyncGenerator, Callable, Dict, Optional, Tuple


def bind_policy_catalog_attrs(cls: Any, source_globals: Dict[str, Any]) -> None:
    for attr in (
        "_CONTROL_SKIP_BLOCK_TOOLS",
        "_CONTROL_SKIP_BLOCK_KEYWORDS",
        "_CONTROL_SKIP_HARD_SAFETY_KEYWORDS",
        "_TOOL_INTENT_KEYWORDS",
        "_TOOL_INTENT_WORD_KEYWORDS",
        "_TOOL_DOMAIN_TAG_RE",
        "_TOOL_DOMAIN_TAG_SHORT_RE",
        "_CRON_META_GUARD_MARKERS",
        "_FOLLOWUP_FACT_PREFIXES",
        "_FOLLOWUP_FACT_MARKERS",
        "_FOLLOWUP_CONFIRM_PREFIXES",
        "_FOLLOWUP_CONFIRM_MARKERS",
        "_FOLLOWUP_CONFIRM_STATE_ONLY_MARKERS",
        "_FOLLOWUP_ASSISTANT_ACTION_MARKERS",
        "_TEMPORAL_CONTEXT_MARKERS",
        "_HOME_CONTAINER_QUERY_MARKERS",
        "_HOME_CONTAINER_PURPOSE_MARKERS",
        "_HOME_CONTAINER_START_MARKERS",
        "_ACTIVE_CONTAINER_DEICTIC_MARKERS",
        "_ACTIVE_CONTAINER_CAPABILITY_MARKERS",
        "_ACTIVE_CONTAINER_CAPABILITY_EXCLUDE_MARKERS",
        "_CONTAINER_INVENTORY_QUERY_MARKERS",
        "_CONTAINER_BLUEPRINT_QUERY_MARKERS",
        "_CONTAINER_STATE_QUERY_MARKERS",
        "_CONTAINER_REQUEST_QUERY_MARKERS",
        "_SKILL_CATALOG_QUERY_MARKERS",
        "_SKILL_CATALOG_EXCLUDE_MARKERS",
        "_LOW_SIGNAL_ACTION_TOOLS",
        "_QUERY_BUDGET_HEAVY_TOOLS",
        "_SKILL_INTENT_KEYWORDS",
        "_SKILL_INTENT_WORD_KEYWORDS",
        "_DOMAIN_CRON_TOOLS",
        "_READ_ONLY_SKILL_TOOLS",
        "_SKILL_ACTION_TOOLS",
        "_DOMAIN_SKILL_TOOLS",
        "_DOMAIN_CONTAINER_TOOLS",
        "_CONTAINER_ID_REQUIRED_TOOLS",
        "_DOMAIN_CRON_OP_TO_TOOL",
        "_DOMAIN_CONTAINER_OP_TO_TOOL",
        "_LOW_SIGNAL_TOOLS",
    ):
        setattr(cls, attr, source_globals[attr[1:]])


async def check_pending_confirmation(
    orch: Any,
    user_text: str,
    conversation_id: str,
    *,
    intent_system_available: bool,
    get_intent_store_fn: Callable[[], Any],
    get_hub_fn: Callable[[], Any],
    intent_state_cls: Any,
    core_chat_response_cls: Any,
    util_check_pending_confirmation_fn: Callable[..., Any],
    log_info_fn: Callable[[str], None],
    log_warn_fn: Callable[[str], None],
    log_error_fn: Callable[[str], None],
) -> Optional[Any]:
    return await util_check_pending_confirmation_fn(
        orch,
        user_text,
        conversation_id,
        intent_system_available=intent_system_available,
        get_intent_store_fn=get_intent_store_fn,
        get_hub_fn=get_hub_fn,
        intent_state_cls=intent_state_cls,
        core_chat_response_cls=core_chat_response_cls,
        log_info_fn=log_info_fn,
        log_warn_fn=log_warn_fn,
        log_error_fn=log_error_fn,
    )


async def execute_autonomous_objective(
    objective: str,
    conversation_id: str,
    *,
    master: Any,
    max_loops: int,
    log_info_fn: Callable[[str], None],
) -> Dict[str, Any]:
    log_info_fn(f"[Pipeline] Starting autonomous objective: {objective}")
    result = await master.execute_objective(
        objective=objective,
        conversation_id=conversation_id,
        max_loops=max_loops,
    )
    log_info_fn(f"[Pipeline] Autonomous objective completed: {result['success']}")
    return result


async def process_request(
    orch: Any,
    request: Any,
    *,
    core_chat_response_cls: Any,
    intent_system_available: bool,
    get_master_settings_fn: Callable[[], Any],
    thinking_plan_cache: Any,
    soften_control_deny_fn: Callable[..., Any],
    util_process_request_fn: Callable[..., Any],
    log_info_fn: Callable[[str], None],
    log_warn_fn: Callable[[str], None],
    log_warning_fn: Callable[[str], None],
) -> Any:
    return await util_process_request_fn(
        orch,
        request,
        core_chat_response_cls=core_chat_response_cls,
        intent_system_available=intent_system_available,
        get_master_settings_fn=get_master_settings_fn,
        thinking_plan_cache=thinking_plan_cache,
        soften_control_deny_fn=soften_control_deny_fn,
        log_info_fn=log_info_fn,
        log_warn_fn=log_warn_fn,
        log_warning_fn=log_warning_fn,
    )


async def process_stream_with_events(
    orch: Any,
    request: Any,
    *,
    intent_system_available: bool,
    enable_chunking: bool,
    chunking_threshold: int,
    get_master_settings_fn: Callable[[], Any],
    thinking_plan_cache: Any,
    sequential_result_cache: Any,
    soften_control_deny_fn: Callable[..., Any],
    skill_creation_intent_cls: Any,
    intent_origin_cls: Any,
    get_intent_store_fn: Callable[[], Any],
    util_process_stream_with_events_fn: Callable[..., AsyncGenerator[Tuple[str, bool, Dict], None]],
    log_info_fn: Callable[[str], None],
    log_warn_fn: Callable[[str], None],
    log_error_fn: Callable[[str], None],
    log_debug_fn: Callable[[str], None],
    log_warning_fn: Callable[[str], None],
) -> AsyncGenerator[Tuple[str, bool, Dict], None]:
    async for item in util_process_stream_with_events_fn(
        orch,
        request,
        intent_system_available=intent_system_available,
        enable_chunking=enable_chunking,
        chunking_threshold=chunking_threshold,
        get_master_settings_fn=get_master_settings_fn,
        thinking_plan_cache=thinking_plan_cache,
        sequential_result_cache=sequential_result_cache,
        soften_control_deny_fn=soften_control_deny_fn,
        skill_creation_intent_cls=skill_creation_intent_cls,
        intent_origin_cls=intent_origin_cls,
        get_intent_store_fn=get_intent_store_fn,
        log_info_fn=log_info_fn,
        log_warn_fn=log_warn_fn,
        log_error_fn=log_error_fn,
        log_debug_fn=log_debug_fn,
        log_warning_fn=log_warning_fn,
    ):
        yield item


async def process_chunked_stream(
    orch: Any,
    user_text: str,
    conversation_id: str,
    request: Any,
    *,
    util_process_chunked_stream_fn: Callable[..., AsyncGenerator[Tuple[str, bool, Dict], None]],
    get_hub_fn: Callable[[], Any],
    log_info_fn: Callable[[str], None],
    log_error_fn: Callable[[str], None],
) -> AsyncGenerator[Tuple[str, bool, Dict], None]:
    async for chunk in util_process_chunked_stream_fn(
        orch,
        user_text,
        conversation_id,
        request,
        get_hub_fn=get_hub_fn,
        log_info_fn=log_info_fn,
        log_error_fn=log_error_fn,
    ):
        yield chunk


async def execute_control_layer(
    orch: Any,
    user_text: str,
    thinking_plan: Dict[str, Any],
    memory_data: str,
    conversation_id: str,
    *,
    response_mode: str,
    intent_system_available: bool,
    skill_creation_intent_cls: Any,
    intent_origin_cls: Any,
    get_intent_store_fn: Callable[[], Any],
    util_execute_control_layer_fn: Callable[..., Any],
    log_info_fn: Callable[[str], None],
    log_warn_fn: Callable[[str], None],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    return await util_execute_control_layer_fn(
        orch,
        user_text,
        thinking_plan,
        memory_data,
        conversation_id,
        response_mode=response_mode,
        intent_system_available=intent_system_available,
        skill_creation_intent_cls=skill_creation_intent_cls,
        intent_origin_cls=intent_origin_cls,
        get_intent_store_fn=get_intent_store_fn,
        log_info_fn=log_info_fn,
        log_warn_fn=log_warn_fn,
    )


def save_memory(
    conversation_id: str,
    verified_plan: Dict[str, Any],
    answer: str,
    *,
    util_save_memory_fn: Callable[..., Any],
    call_tool_fn: Callable[..., Any],
    autosave_assistant_fn: Callable[..., Any],
    load_grounding_policy_fn: Callable[..., Any],
    get_runtime_tool_results_fn: Callable[..., Any],
    count_successful_grounding_evidence_fn: Callable[..., Any],
    extract_suggested_tool_names_fn: Callable[..., Any],
    get_runtime_tool_failure_fn: Callable[..., Any],
    tool_context_has_failures_or_skips_fn: Callable[..., Any],
    get_runtime_grounding_value_fn: Callable[..., Any],
    get_autosave_dedupe_guard_fn: Callable[..., Any],
    log_info_fn: Callable[[str], None],
    log_warn_fn: Callable[[str], None],
    log_error_fn: Callable[[str], None],
) -> None:
    util_save_memory_fn(
        conversation_id=conversation_id,
        verified_plan=verified_plan,
        answer=answer,
        call_tool_fn=call_tool_fn,
        autosave_assistant_fn=autosave_assistant_fn,
        load_grounding_policy_fn=load_grounding_policy_fn,
        get_runtime_tool_results_fn=get_runtime_tool_results_fn,
        count_successful_grounding_evidence_fn=count_successful_grounding_evidence_fn,
        extract_suggested_tool_names_fn=extract_suggested_tool_names_fn,
        get_runtime_tool_failure_fn=get_runtime_tool_failure_fn,
        tool_context_has_failures_or_skips_fn=tool_context_has_failures_or_skips_fn,
        get_runtime_grounding_value_fn=get_runtime_grounding_value_fn,
        get_autosave_dedupe_guard_fn=get_autosave_dedupe_guard_fn,
        log_info_fn=log_info_fn,
        log_warn_fn=log_warn_fn,
        log_error_fn=log_error_fn,
    )
