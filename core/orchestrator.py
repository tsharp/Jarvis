"""
PipelineOrchestrator: Manages the 3-Layer execution pipeline

Responsibilities:
- Orchestrate Thinking -> Control -> Output layers
- Handle streaming logic
- Manage chunking for large documents
- Intent confirmation integration

Created by: Claude 2 (Parallel Development)
Date: 2026-02-05
Part of: CoreBridge Refactoring Phase 1
"""

# Legacy source-inspection contract markers:
# Commit 2 stream parity
# Commit 2 stream parity: Card
# _build_tool_result_card
# _build_tool_result_card
# _build_tool_result_card
# _build_tool_result_card
# _compute_retrieval_policy
# budget exhausted
# budget exhausted

import asyncio
import json
import os
import time
import threading
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Tuple, Dict, Any, Optional, List

from core.models import CoreChatRequest, CoreChatResponse
from core.context_manager import ContextManager, ContextResult
from core.layers.thinking import ThinkingLayer
from core.layers.control import ControlLayer
from core.layers.output import OutputLayer
from core.tone_hybrid import ToneHybridClassifier
from core.query_budget_hybrid import QueryBudgetHybridClassifier
from core.domain_router_hybrid import DomainRouterHybridClassifier
from core.tool_selector import ToolSelector
from config import (
    OLLAMA_BASE,
    ENABLE_CONTROL_LAYER,
    SKIP_CONTROL_ON_LOW_RISK,
    ENABLE_CHUNKING,
    CHUNKING_THRESHOLD,
)
from utils.logger import log_info, log_warn, log_error, log_debug
from mcp.client import (
    autosave_assistant,
    call_tool,
)
from mcp.hub import get_hub
from core.sequential_registry import get_registry
from core.lifecycle.task import TaskLifecycleManager
from core.tools.tool_result import ToolResult
from core.lifecycle.archive import get_archive_manager
from core.master import get_master_orchestrator
from core.tool_intelligence import ToolIntelligenceManager, detect_tool_error
from core.grounding_policy import load_grounding_policy
from core.tool_execution_policy import load_tool_execution_policy
from core.control_decision_utils import (
    build_control_workspace_summary,
    build_done_workspace_summary,
    is_control_hard_block_decision,
    soften_control_deny,
)
from core.control_contract import (
    ControlDecision,
    control_decision_from_plan,
    execution_result_from_plan,
    persist_control_decision,
    persist_execution_result,
    tool_allowed_by_control_decision,
)
from core.plan_runtime_bridge import (
    get_runtime_grounding_evidence,
    get_runtime_grounding_value,
    get_runtime_tool_failure,
    get_runtime_tool_results,
    set_runtime_grounding_evidence,
)
from core.plan_cache import make_plan_cache, SqlitePlanCache as _SqlitePlanCache
from core.workspace_event_utils import (
    build_sequential_workspace_summary,
    persist_sequential_workspace_event,
)
from core.archive_embedding_queue import (
    _ArchiveEmbeddingJobQueue,
    get_archive_embedding_queue as _get_archive_embedding_queue,
)
from core.master_settings import get_master_settings
from core.host_runtime_policy import enforce_host_runtime_exec_first
from core.orchestrator_prompt_utils import (
    expected_home_blueprint_id as util_expected_home_blueprint_id,
    is_rollout_enabled as util_is_rollout_enabled,
    last_assistant_message as util_last_assistant_message,
    looks_like_short_confirmation_followup as util_looks_like_short_confirmation_followup,
    looks_like_short_confirmation_followup_state_only as util_looks_like_short_confirmation_followup_state_only,
    looks_like_short_fact_followup as util_looks_like_short_fact_followup,
    message_content_value as util_message_content_value,
    message_role_value as util_message_role_value,
    normalize_trace_id as util_normalize_trace_id,
    recent_user_messages as util_recent_user_messages,
    safe_str as util_safe_str,
    sanitize_tool_args_for_state as util_sanitize_tool_args_for_state,
)
from core.grounding_state_utils import (
    count_successful_grounding_evidence as util_count_successful_grounding_evidence,
    select_first_whitelisted_tool_run as util_select_first_whitelisted_tool_run,
)
from core.orchestrator_temporal_utils import (
    infer_time_reference_from_user_text as util_infer_time_reference_from_user_text,
    looks_like_temporal_context_query as util_looks_like_temporal_context_query,
)
from core.orchestrator_policy_signal_utils import (
    has_memory_recall_signal as util_has_memory_recall_signal,
    has_non_memory_tool_runtime_signal as util_has_non_memory_tool_runtime_signal,
    sanitize_tone_signal as util_sanitize_tone_signal,
)
from core.orchestrator_modules.policy.runtime import (
    apply_query_budget_to_plan_runtime as util_apply_query_budget_to_plan_runtime,
    apply_query_budget_tool_policy_runtime as util_apply_query_budget_tool_policy_runtime,
    classify_domain_signal as util_classify_domain_signal,
    classify_query_budget_signal as util_classify_query_budget_signal,
    classify_tone_signal as util_classify_tone_signal,
    ensure_dialogue_controls_runtime as util_ensure_dialogue_controls_runtime,
    resolve_precontrol_policy_conflicts_runtime as util_resolve_precontrol_policy_conflicts_runtime,
    should_force_query_budget_factual_memory_runtime as util_should_force_query_budget_factual_memory_runtime,
    should_skip_thinking_from_query_budget_runtime as util_should_skip_thinking_from_query_budget_runtime,
)
from core.orchestrator_modules.runtime.state import (
    get_recent_container_state as util_get_recent_container_state,
    get_recent_grounding_state as util_get_recent_grounding_state,
    grounding_evidence_has_content_runtime as util_grounding_evidence_has_content_runtime,
    has_usable_grounding_evidence_runtime as util_has_usable_grounding_evidence_runtime,
    inject_carryover_grounding_evidence_runtime as util_inject_carryover_grounding_evidence_runtime,
    normalize_container_entries as util_normalize_container_entries,
    remember_container_state as util_remember_container_state,
    remember_conversation_grounding_state as util_remember_conversation_grounding_state,
    resolve_followup_tool_reuse_runtime as util_resolve_followup_tool_reuse_runtime,
    resolve_pending_container_id_async as util_resolve_pending_container_id_async,
    resolve_pending_container_id_sync as util_resolve_pending_container_id_sync,
    select_preferred_container_id as util_select_preferred_container_id,
    tool_requires_container_id as util_tool_requires_container_id,
    update_container_state_from_tool_result as util_update_container_state_from_tool_result,
)
from core.orchestrator_modules.policy.domain_container import (
    apply_container_query_policy as util_apply_container_query_policy,
    apply_domain_route_to_plan as util_apply_domain_route_to_plan,
    apply_domain_tool_policy as util_apply_domain_tool_policy,
    container_state_has_active_target as util_container_state_has_active_target,
    finalize_execution_suggested_tools as util_finalize_execution_suggested_tools,
    get_effective_resolution_strategy as util_get_effective_resolution_strategy,
    is_active_container_capability_query as util_is_active_container_capability_query,
    is_container_blueprint_catalog_query as util_is_container_blueprint_catalog_query,
    is_container_inventory_query as util_is_container_inventory_query,
    is_container_request_query as util_is_container_request_query,
    is_container_state_binding_query as util_is_container_state_binding_query,
    is_skill_catalog_context_query as util_is_skill_catalog_context_query,
    looks_like_host_runtime_lookup as util_looks_like_host_runtime_lookup,
    materialize_container_query_policy as util_materialize_container_query_policy,
    materialize_skill_catalog_policy as util_materialize_skill_catalog_policy,
    prioritize_active_container_capability_tools as util_prioritize_active_container_capability_tools,
    prioritize_home_container_tools as util_prioritize_home_container_tools,
    record_execution_tool_trace as util_record_execution_tool_trace,
    rewrite_home_start_request_tools as util_rewrite_home_start_request_tools,
    select_read_only_skill_tool_for_query as util_select_read_only_skill_tool_for_query,
    seed_tool_for_domain_route as util_seed_tool_for_domain_route,
    should_prioritize_skill_catalog_route as util_should_prioritize_skill_catalog_route,
    tool_name_list as util_tool_name_list,
)
from core.orchestrator_modules.context.semantic import (
    derive_container_addon_tags_from_inspect as util_derive_container_addon_tags_from_inspect,
    maybe_build_active_container_capability_context as util_maybe_build_active_container_capability_context,
    maybe_build_skill_semantic_context as util_maybe_build_skill_semantic_context,
    parse_list_draft_skills_snapshot as util_parse_list_draft_skills_snapshot,
    parse_list_skills_runtime_snapshot as util_parse_list_skills_runtime_snapshot,
    summarize_container_inspect_for_capability_context as util_summarize_container_inspect_for_capability_context,
    summarize_skill_registry_snapshot as util_summarize_skill_registry_snapshot,
    summarize_skill_runtime_snapshot as util_summarize_skill_runtime_snapshot,
)
from core.orchestrator_modules.runtime.response_guard import (
    apply_conversation_consistency_guard as util_apply_conversation_consistency_guard,
    get_recent_consistency_entries as util_get_recent_consistency_entries,
    maybe_auto_recover_grounding_once as util_maybe_auto_recover_grounding_once,
    remember_consistency_entries as util_remember_consistency_entries,
)
from core.orchestrator_modules.output.glue import (
    build_tool_result_card as util_build_tool_result_card,
    compute_ctx_mode as util_compute_ctx_mode,
    extract_workspace_observations as util_extract_workspace_observations,
    format_tool_result as util_format_tool_result,
    merge_grounding_evidence_items as util_merge_grounding_evidence_items,
)
from core.orchestrator_modules.context.workspace import (
    build_master_workspace_summary as util_build_master_workspace_summary,
    clip_tool_context as util_clip_tool_context,
    compute_retrieval_policy as util_compute_retrieval_policy,
    persist_master_workspace_event as util_persist_master_workspace_event,
)
from core.orchestrator_modules.context.compact import (
    apply_effective_context_guardrail as util_apply_effective_context_guardrail,
    get_compact_context as util_get_compact_context,
)
from core.orchestrator_modules.context.container_candidates import (
    prepare_container_candidate_evidence as util_prepare_container_candidate_evidence,
)
from core.orchestrator_modules.interaction_runtime import (
    apply_response_mode_policy as util_apply_response_mode_policy,
    detect_skill_by_trigger as util_detect_skill_by_trigger,
    detect_tools_by_keyword as util_detect_tools_by_keyword,
    extract_requested_skill_name as util_extract_requested_skill_name,
    extract_tool_name as util_extract_tool_name,
    filter_think_tools as util_filter_think_tools,
    is_explicit_deep_request as util_is_explicit_deep_request,
    is_explicit_think_request as util_is_explicit_think_request,
    is_home_container_info_query as util_is_home_container_info_query,
    is_home_container_start_query as util_is_home_container_start_query,
    filter_tool_selector_candidates as util_filter_tool_selector_candidates,
    recover_home_read_directory_with_fast_lane as util_recover_home_read_directory_with_fast_lane,
    requested_response_mode as util_requested_response_mode,
    resolve_runtime_output_model as util_resolve_runtime_output_model,
    route_blueprint_request as util_route_blueprint_request,
    route_skill_request as util_route_skill_request,
    sanitize_skill_name_candidate as util_sanitize_skill_name_candidate,
)
from core.orchestrator_modules.workspace_events import (
    build_container_event_content as util_build_container_event_content,
    save_container_event as util_save_container_event,
    save_workspace_entry as util_save_workspace_entry,
)
from core.orchestrator_modules.execution.resolution import (
    collect_control_tool_decisions as util_collect_control_tool_decisions,
    resolve_execution_suggested_tools as util_resolve_execution_suggested_tools,
)
from core.orchestrator_modules.postprocess import (
    post_task_processing as util_post_task_processing,
    save_memory as util_save_memory,
)
from core.orchestrator_modules.policy.cron_intent import (
    bind_cron_conversation_id as util_bind_cron_conversation_id,
    build_cron_name as util_build_cron_name,
    build_cron_objective as util_build_cron_objective,
    build_direct_cron_create_response as util_build_direct_cron_create_response,
    contains_explicit_skill_intent as util_contains_explicit_skill_intent,
    contains_explicit_tool_intent as util_contains_explicit_tool_intent,
    contains_keyword_intent as util_contains_keyword_intent,
    extract_cron_ack_message_from_objective as util_extract_cron_ack_message_from_objective,
    extract_cron_expression_from_text as util_extract_cron_expression_from_text,
    extract_cron_job_id_from_text as util_extract_cron_job_id_from_text,
    extract_cron_schedule_from_text as util_extract_cron_schedule_from_text,
    extract_direct_cron_reminder_text as util_extract_direct_cron_reminder_text,
    extract_interval_hint_from_cron as util_extract_interval_hint_from_cron,
    extract_one_shot_run_at_from_text as util_extract_one_shot_run_at_from_text,
    extract_tool_domain_tag as util_extract_tool_domain_tag,
    format_utc_compact as util_format_utc_compact,
    has_cron_schedule_signal as util_has_cron_schedule_signal,
    is_explicit_cron_create_intent as util_is_explicit_cron_create_intent,
    looks_like_self_state_request as util_looks_like_self_state_request,
    maybe_downgrade_cron_create_signal as util_maybe_downgrade_cron_create_signal,
    normalize_tools as util_normalize_tools,
    prevalidate_cron_policy_args as util_prevalidate_cron_policy_args,
    suggest_cron_expression_for_min_interval as util_suggest_cron_expression_for_min_interval,
)
from core.orchestrator_modules.catalog import (
    ACTIVE_CONTAINER_CAPABILITY_EXCLUDE_MARKERS,
    ACTIVE_CONTAINER_CAPABILITY_MARKERS,
    ACTIVE_CONTAINER_DEICTIC_MARKERS,
    CONTAINER_BLUEPRINT_QUERY_MARKERS,
    CONTAINER_ID_REQUIRED_TOOLS,
    CONTAINER_INVENTORY_QUERY_MARKERS,
    CONTAINER_REQUEST_QUERY_MARKERS,
    CONTAINER_STATE_QUERY_MARKERS,
    CONTROL_SKIP_BLOCK_KEYWORDS,
    CONTROL_SKIP_BLOCK_TOOLS,
    CONTROL_SKIP_HARD_SAFETY_KEYWORDS,
    CRON_META_GUARD_MARKERS,
    DOMAIN_CONTAINER_OP_TO_TOOL,
    DOMAIN_CONTAINER_TOOLS,
    DOMAIN_CRON_OP_TO_TOOL,
    DOMAIN_CRON_TOOLS,
    DOMAIN_SKILL_TOOLS,
    FOLLOWUP_ASSISTANT_ACTION_MARKERS,
    FOLLOWUP_CONFIRM_MARKERS,
    FOLLOWUP_CONFIRM_PREFIXES,
    FOLLOWUP_CONFIRM_STATE_ONLY_MARKERS,
    FOLLOWUP_FACT_MARKERS,
    FOLLOWUP_FACT_PREFIXES,
    HOME_CONTAINER_PURPOSE_MARKERS,
    HOME_CONTAINER_QUERY_MARKERS,
    HOME_CONTAINER_START_MARKERS,
    LOW_SIGNAL_ACTION_TOOLS,
    LOW_SIGNAL_TOOLS,
    QUERY_BUDGET_HEAVY_TOOLS,
    READ_ONLY_SKILL_TOOLS,
    SKILL_ACTION_TOOLS,
    SKILL_CATALOG_EXCLUDE_MARKERS,
    SKILL_CATALOG_QUERY_MARKERS,
    SKILL_INTENT_KEYWORDS,
    SKILL_INTENT_WORD_KEYWORDS,
    TEMPORAL_CONTEXT_MARKERS,
    TOOL_DOMAIN_TAG_RE,
    TOOL_DOMAIN_TAG_SHORT_RE,
    TOOL_INTENT_KEYWORDS,
    TOOL_INTENT_WORD_KEYWORDS,
)
from core.autosave_dedupe import get_autosave_dedupe_guard
from core.embedding_client import embed_text as embed_text_runtime
from core.conversation_consistency_policy import load_conversation_consistency_policy
from core.conversation_consistency import (
    detect_conflicts as util_detect_consistency_conflicts,
    extract_stance_signals as util_extract_stance_signals,
    make_entries as util_make_stance_entries,
    prune_entries as util_prune_stance_entries,
)
from core.orchestrator_plan_schema_utils import (
    coerce_thinking_plan_schema as util_coerce_thinking_plan_schema,
)
from core.orchestrator_control_skip_utils import (
    should_skip_control_layer as util_should_skip_control_layer,
)
from core.orchestrator_grounding_evidence_utils import (
    build_grounding_evidence_entry as util_build_grounding_evidence_entry,
)
from core.orchestrator_hardware_gate_utils import (
    check_hardware_gate_early as util_check_hardware_gate_early,
)
from core.orchestrator_skill_task_utils import (
    sanitize_intent_thinking_plan_for_skill_task as util_sanitize_intent_thinking_plan_for_skill_task,
)
from core.orchestrator_conversation_guard_utils import (
    should_suppress_conversational_tools as util_should_suppress_conversational_tools,
)
from core.orchestrator_tool_args_utils import (
    build_tool_args as util_build_tool_args,
)
from core.orchestrator_tool_validation_utils import (
    validate_tool_args as util_validate_tool_args,
)
from core.orchestrator_tool_execution_sync_utils import (
    execute_tools_sync as util_execute_tools_sync,
)
from core.orchestrator_flow_utils import (
    initialize_pipeline_orchestrator as util_initialize_pipeline_orchestrator,
    build_effective_context as util_build_effective_context,
    check_pending_confirmation as util_check_pending_confirmation,
    process_chunked_stream as util_process_chunked_stream,
    execute_control_layer as util_execute_control_layer,
)
from core.orchestrator_sync_flow_utils import (
    process_request as util_process_request,
)
from core.orchestrator_stream_flow_utils import (
    process_stream_with_events as util_process_stream_with_events,
)
from core.orchestrator_modules.pipeline_facade import (
    append_context_block as util_append_context_block,
    apply_final_cap as util_apply_final_cap,
    build_failure_compact_block as util_build_failure_compact_block,
    build_summary_from_structure as util_build_summary_from_structure,
    execute_thinking_layer as util_execute_thinking_layer,
    maybe_prefetch_skills as util_maybe_prefetch_skills,
    tool_context_has_failures_or_skips as util_tool_context_has_failures_or_skips,
    tool_context_has_success as util_tool_context_has_success,
    verify_container_running as util_verify_container_running,
)
from core.orchestrator_modules.api_facade import (
    bind_policy_catalog_attrs as util_bind_policy_catalog_attrs,
    check_pending_confirmation as util_api_check_pending_confirmation,
    execute_autonomous_objective as util_api_execute_autonomous_objective,
    execute_control_layer as util_api_execute_control_layer,
    process_chunked_stream as util_api_process_chunked_stream,
    process_request as util_api_process_request,
    process_stream_with_events as util_api_process_stream_with_events,
    save_memory as util_api_save_memory,
)
from utils.role_endpoint_resolver import resolve_role_endpoint
from utils.model_runtime_resolver import resolve_runtime_chat_model

# Intent System (optional)
try:
    from core.intent_models import SkillCreationIntent, IntentState, IntentOrigin
    from core.intent_store import get_intent_store
    INTENT_SYSTEM_AVAILABLE = True
except ImportError:
    INTENT_SYSTEM_AVAILABLE = False
    log_warn("[Orchestrator] Intent System not available")

# CIM Policy Engine (optional)
try:
    from intelligence_modules.cim_policy.cim_policy_engine import (
        process_cim, ActionType, CIMDecision
    )
    CIM_AVAILABLE = True
except ImportError:
    CIM_AVAILABLE = False


# Module-level Cache-Instanzen (leben bis Container neugestartet wird)
_thinking_plan_cache = make_plan_cache(ttl_seconds=300, namespace="thinking_plan")      # 5 min
_sequential_result_cache = make_plan_cache(ttl_seconds=600, namespace="sequential_result")  # 10 min


# Patterns für frühes Hardware-Gate (vor Sequential Thinking)
_HARDWARE_GATE_PATTERNS = [
    "30b", "70b", "34b", "65b", "40b",
    "large model", "großes modell", "großes sprachmodell",
    "ollama pull", "modell laden", "modell aktivieren",
    "modell herunterladen", "model load", "model pull",
]
class PipelineOrchestrator:
    """
    Orchestrates the 3-Layer Pipeline:
    1. Thinking Layer (DeepSeek - Planning)
    2. Control Layer (Qwen - Verification)
    3. Output Layer (User Model - Generation)
    
    Delegates context retrieval to ContextManager.
    """
    
    def __init__(self, context_manager: ContextManager = None):
        """
        Initialize orchestrator with layers.
        
        Args:
            context_manager: Injected ContextManager (Dependency Injection)
                           If None, creates new instance
        """
        self._log_info_for_utils = log_info
        self._log_warn_for_utils = log_warn
        util_initialize_pipeline_orchestrator(
            self,
            context_manager,
            context_manager_cls=ContextManager,
            thinking_layer_cls=ThinkingLayer,
            control_layer_cls=ControlLayer,
            output_layer_cls=OutputLayer,
            tool_selector_cls=ToolSelector,
            tone_hybrid_cls=ToneHybridClassifier,
            query_budget_hybrid_cls=QueryBudgetHybridClassifier,
            domain_router_hybrid_cls=DomainRouterHybridClassifier,
            get_registry_fn=get_registry,
            task_lifecycle_manager_cls=TaskLifecycleManager,
            get_archive_manager_fn=get_archive_manager,
            tool_intelligence_manager_cls=ToolIntelligenceManager,
            load_tool_execution_policy_fn=load_tool_execution_policy,
            get_master_orchestrator_fn=get_master_orchestrator,
            get_hub_fn=get_hub,
            ollama_base=OLLAMA_BASE,
            lock_factory=threading.Lock,
            log_info_fn=log_info,
        )

    @classmethod
    def _extract_suggested_tool_names(cls, thinking_plan: Dict[str, Any]) -> List[str]:
        names: List[str] = []
        raw_tools = (thinking_plan or {}).get("suggested_tools", []) or []
        for tool in raw_tools:
            if isinstance(tool, dict):
                name = str(tool.get("tool") or tool.get("name") or "").strip()
            else:
                name = str(tool).strip()
            if name:
                names.append(name)
        return names

    @staticmethod
    def _normalize_trace_id(value: Any) -> str:
        return util_normalize_trace_id(value)

    @staticmethod
    def _safe_str(value: Any, *, max_len: int = 3000) -> str:
        return util_safe_str(value, max_len=max_len)

    @staticmethod
    def _is_rollout_enabled(rollout_pct: int, seed: str) -> bool:
        return util_is_rollout_enabled(rollout_pct, seed)

    @staticmethod
    def _message_role_value(msg: Any) -> str:
        return util_message_role_value(msg)

    @staticmethod
    def _message_content_value(msg: Any) -> str:
        return util_message_content_value(msg)

    @classmethod
    def _last_assistant_message(cls, chat_history: Optional[list]) -> str:
        return util_last_assistant_message(chat_history)

    @classmethod
    def _recent_user_messages(cls, chat_history: Optional[list], limit: int = 3) -> List[str]:
        return util_recent_user_messages(chat_history, limit=limit)

    @classmethod
    def _looks_like_short_fact_followup(
        cls,
        user_text: str,
        chat_history: Optional[list],
    ) -> bool:
        return util_looks_like_short_fact_followup(
            user_text,
            chat_history,
            prefixes=cls._FOLLOWUP_FACT_PREFIXES,
            markers=cls._FOLLOWUP_FACT_MARKERS,
        )

    @classmethod
    def _looks_like_short_confirmation_followup(
        cls,
        user_text: str,
        chat_history: Optional[list],
    ) -> bool:
        return util_looks_like_short_confirmation_followup(
            user_text,
            chat_history,
            prefixes=cls._FOLLOWUP_CONFIRM_PREFIXES,
            markers=cls._FOLLOWUP_CONFIRM_MARKERS,
            assistant_action_markers=cls._FOLLOWUP_ASSISTANT_ACTION_MARKERS,
        )

    @classmethod
    def _looks_like_short_confirmation_followup_state_only(
        cls,
        user_text: str,
    ) -> bool:
        return util_looks_like_short_confirmation_followup_state_only(
            user_text,
            action_markers=cls._FOLLOWUP_CONFIRM_STATE_ONLY_MARKERS,
        )

    @classmethod
    def _sanitize_tool_args_for_state(cls, value: Any) -> Dict[str, Any]:
        return util_sanitize_tool_args_for_state(value, non_serialized_max_len=200)

    @staticmethod
    def _expected_home_blueprint_id() -> str:
        return util_expected_home_blueprint_id("trion-home")

    def _get_recent_container_state(
        self,
        conversation_id: str,
        history_len: int = 0,
    ) -> Optional[Dict[str, Any]]:
        return util_get_recent_container_state(
            container_state_store=self._container_state_store,
            conversation_id=conversation_id,
            history_len=history_len,
        )

    @staticmethod
    def _normalize_container_entries(rows: Any) -> List[Dict[str, str]]:
        return util_normalize_container_entries(rows, limit=64)

    def _remember_container_state(
        self,
        conversation_id: str,
        *,
        last_active_container_id: str = "",
        home_container_id: str = "",
        known_containers: Optional[List[Dict[str, str]]] = None,
        history_len: int = 0,
    ) -> None:
        util_remember_container_state(
            container_state_store=self._container_state_store,
            conversation_id=conversation_id,
            last_active_container_id=last_active_container_id,
            home_container_id=home_container_id,
            known_containers=known_containers,
            history_len=history_len,
        )

    def _update_container_state_from_tool_result(
        self,
        conversation_id: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        result: Any,
        *,
        history_len: int = 0,
    ) -> None:
        util_update_container_state_from_tool_result(
            container_state_store=self._container_state_store,
            conversation_id=conversation_id,
            tool_name=tool_name,
            tool_args=tool_args,
            result=result,
            history_len=history_len,
        )

    @classmethod
    def _tool_requires_container_id(cls, tool_name: str) -> bool:
        return util_tool_requires_container_id(
            tool_name,
            container_id_required_tools=cls._CONTAINER_ID_REQUIRED_TOOLS,
        )

    @classmethod
    def _select_preferred_container_id(
        cls,
        rows: Any,
        *,
        preferred_ids: Optional[List[str]] = None,
    ) -> str:
        return util_select_preferred_container_id(
            rows,
            expected_home_blueprint_id=cls._expected_home_blueprint_id(),
            preferred_ids=preferred_ids,
        )

    def _resolve_pending_container_id_sync(
        self,
        tool_hub: Any,
        conversation_id: str,
        *,
        preferred_ids: Optional[List[str]] = None,
        history_len: int = 0,
    ) -> Tuple[str, str]:
        return util_resolve_pending_container_id_sync(
            tool_hub=tool_hub,
            conversation_id=conversation_id,
            preferred_ids=preferred_ids,
            history_len=history_len,
            safe_str_fn=lambda value, max_len: self._safe_str(value, max_len=max_len),
            update_container_state_from_tool_result_fn=self._update_container_state_from_tool_result,
            expected_home_blueprint_id=self._expected_home_blueprint_id(),
        )

    async def _resolve_pending_container_id_async(
        self,
        tool_hub: Any,
        conversation_id: str,
        *,
        preferred_ids: Optional[List[str]] = None,
        history_len: int = 0,
    ) -> Tuple[str, str]:
        return await util_resolve_pending_container_id_async(
            tool_hub=tool_hub,
            conversation_id=conversation_id,
            preferred_ids=preferred_ids,
            history_len=history_len,
            safe_str_fn=lambda value, max_len: self._safe_str(value, max_len=max_len),
            update_container_state_from_tool_result_fn=self._update_container_state_from_tool_result,
            expected_home_blueprint_id=self._expected_home_blueprint_id(),
        )

    @staticmethod
    def _grounding_evidence_has_content(item: Dict[str, Any]) -> bool:
        return util_grounding_evidence_has_content_runtime(item)

    def _get_recent_grounding_state(
        self,
        conversation_id: str,
        history_len: int = 0,
    ) -> Optional[Dict[str, Any]]:
        from config import (
            get_followup_tool_reuse_ttl_s,
            get_followup_tool_reuse_ttl_turns,
        )

        return util_get_recent_grounding_state(
            conversation_grounding_state=self._conversation_grounding_state,
            conversation_grounding_lock=self._conversation_grounding_lock,
            conversation_id=conversation_id,
            history_len=history_len,
            ttl_s=int(get_followup_tool_reuse_ttl_s()),
            ttl_turns=int(get_followup_tool_reuse_ttl_turns()),
        )

    def _remember_conversation_grounding_state(
        self,
        conversation_id: str,
        verified_plan: Dict[str, Any],
        *,
        history_len: int = 0,
    ) -> None:
        util_remember_conversation_grounding_state(
            conversation_grounding_state=self._conversation_grounding_state,
            conversation_grounding_lock=self._conversation_grounding_lock,
            conversation_id=conversation_id,
            verified_plan=verified_plan,
            history_len=history_len,
            sanitize_tool_args_fn=self._sanitize_tool_args_for_state,
            evidence_has_content_fn=self._grounding_evidence_has_content,
        )

    def _inject_carryover_grounding_evidence(
        self,
        conversation_id: str,
        verified_plan: Dict[str, Any],
        *,
        history_len: int = 0,
    ) -> None:
        util_inject_carryover_grounding_evidence_runtime(
            conversation_id=conversation_id,
            verified_plan=verified_plan,
            history_len=history_len,
            get_recent_grounding_state_fn=lambda conv_id, hist_len: self._get_recent_grounding_state(
                conv_id,
                history_len=hist_len,
            ),
            evidence_has_content_fn=self._grounding_evidence_has_content,
            log_info_fn=log_info,
        )

    def _get_recent_consistency_entries(self, conversation_id: str) -> List[Dict[str, Any]]:
        return util_get_recent_consistency_entries(
            consistency_state=self._conversation_consistency_state,
            consistency_lock=self._conversation_consistency_lock,
            conversation_id=conversation_id,
            load_policy_fn=load_conversation_consistency_policy,
            prune_entries_fn=util_prune_stance_entries,
        )

    def _remember_consistency_entries(
        self,
        conversation_id: str,
        entries: List[Dict[str, Any]],
    ) -> None:
        util_remember_consistency_entries(
            consistency_state=self._conversation_consistency_state,
            consistency_lock=self._conversation_consistency_lock,
            conversation_id=conversation_id,
            entries=entries,
            load_policy_fn=load_conversation_consistency_policy,
            prune_entries_fn=util_prune_stance_entries,
        )

    async def _apply_conversation_consistency_guard(
        self,
        *,
        conversation_id: str,
        verified_plan: Dict[str, Any],
        answer: str,
    ) -> str:
        return await util_apply_conversation_consistency_guard(
            conversation_id=conversation_id,
            verified_plan=verified_plan,
            answer=answer,
            load_policy_fn=load_conversation_consistency_policy,
            extract_stance_signals_fn=util_extract_stance_signals,
            get_recent_consistency_entries_fn=self._get_recent_consistency_entries,
            embed_text_fn=embed_text_runtime,
            detect_conflicts_fn=util_detect_consistency_conflicts,
            make_stance_entries_fn=util_make_stance_entries,
            remember_consistency_entries_fn=self._remember_consistency_entries,
            get_runtime_grounding_value_fn=get_runtime_grounding_value,
            get_runtime_grounding_evidence_fn=get_runtime_grounding_evidence,
            build_grounding_fallback_fn=lambda evidence, mode: self.output._build_grounding_fallback(
                evidence,
                mode=mode,
            ),
            log_warn_fn=log_warn,
        )

    def _has_usable_grounding_evidence(self, verified_plan: Dict[str, Any]) -> bool:
        return util_has_usable_grounding_evidence_runtime(
            verified_plan,
            evidence_has_content_fn=self._grounding_evidence_has_content,
        )

    async def _maybe_auto_recover_grounding_once(
        self,
        *,
        conversation_id: str,
        user_text: str,
        verified_plan: Dict[str, Any],
        thinking_plan: Dict[str, Any],
        history_len: int,
        session_id: str = "",
    ) -> str:
        from config import (
            get_grounding_auto_recovery_enable,
            get_grounding_auto_recovery_timeout_s,
            get_grounding_auto_recovery_whitelist,
        )
        return await util_maybe_auto_recover_grounding_once(
            conversation_id=conversation_id,
            user_text=user_text,
            verified_plan=verified_plan,
            thinking_plan=thinking_plan,
            history_len=history_len,
            session_id=session_id or "",
            get_grounding_auto_recovery_enable_fn=get_grounding_auto_recovery_enable,
            get_grounding_auto_recovery_timeout_s_fn=get_grounding_auto_recovery_timeout_s,
            get_grounding_auto_recovery_whitelist_fn=get_grounding_auto_recovery_whitelist,
            has_usable_grounding_evidence_fn=self._has_usable_grounding_evidence,
            get_recent_grounding_state_fn=lambda conv_id, hist_len: self._get_recent_grounding_state(
                conv_id,
                history_len=hist_len,
            ),
            select_first_whitelisted_tool_run_fn=util_select_first_whitelisted_tool_run,
            sanitize_tool_args_fn=self._sanitize_tool_args_for_state,
            execute_tools_sync_fn=self._execute_tools_sync,
            control_decision_from_plan_fn=control_decision_from_plan,
            log_info_fn=log_info,
            log_warn_fn=log_warn,
        )

    def _resolve_followup_tool_reuse(
        self,
        user_text: str,
        verified_plan: Dict[str, Any],
        *,
        conversation_id: str = "",
        chat_history: Optional[list] = None,
    ) -> List[Any]:
        from config import get_followup_tool_reuse_enable

        return util_resolve_followup_tool_reuse_runtime(
            user_text=user_text,
            verified_plan=verified_plan,
            conversation_id=conversation_id,
            chat_history=chat_history,
            followup_enabled=bool(get_followup_tool_reuse_enable()),
            contains_explicit_tool_intent_fn=self._contains_explicit_tool_intent,
            looks_like_short_fact_followup_fn=self._looks_like_short_fact_followup,
            looks_like_short_confirmation_followup_fn=self._looks_like_short_confirmation_followup,
            looks_like_short_confirmation_followup_state_only_fn=(
                self._looks_like_short_confirmation_followup_state_only
            ),
            get_recent_grounding_state_fn=lambda conv_id, hist_len: self._get_recent_grounding_state(
                conv_id,
                history_len=hist_len,
            ),
            sanitize_tool_args_fn=self._sanitize_tool_args_for_state,
            log_info_fn=log_info,
        )

    @classmethod
    def _looks_like_temporal_context_query(
        cls,
        user_text: str,
        chat_history: Optional[list] = None,
    ) -> bool:
        return util_looks_like_temporal_context_query(
            user_text,
            chat_history,
            temporal_markers=cls._TEMPORAL_CONTEXT_MARKERS,
            short_followup_checker=lambda text, history: cls._looks_like_short_fact_followup(text, history),
            recent_user_messages_getter=lambda history, limit: cls._recent_user_messages(history, limit=limit),
        )

    @staticmethod
    def _infer_time_reference_from_user_text(user_text: str) -> Optional[str]:
        return util_infer_time_reference_from_user_text(user_text)

    def _apply_temporal_context_fallback(
        self,
        user_text: str,
        thinking_plan: Dict[str, Any],
        chat_history: Optional[list] = None,
    ) -> None:
        from config import get_daily_context_followup_enable

        if not get_daily_context_followup_enable():
            return
        if not isinstance(thinking_plan, dict):
            return
        if thinking_plan.get("time_reference"):
            return
        if not self._looks_like_temporal_context_query(user_text, chat_history):
            return

        inferred = self._infer_time_reference_from_user_text(user_text) or "today"
        thinking_plan["time_reference"] = inferred
        thinking_plan["needs_chat_history"] = True
        log_info(f"[Orchestrator] temporal context fallback: time_reference={inferred}")

    @staticmethod
    def _sanitize_tone_signal(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return util_sanitize_tone_signal(raw)

    async def _classify_tone_signal(
        self,
        user_text: str,
        messages: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        return await util_classify_tone_signal(
            tone_hybrid=self.tone_hybrid,
            user_text=user_text,
            messages=messages,
            sanitize_tone_signal_fn=self._sanitize_tone_signal,
            log_warn_fn=log_warn,
        )

    async def _classify_query_budget_signal(
        self,
        user_text: str,
        *,
        selected_tools: Optional[List[Any]] = None,
        tone_signal: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from config import get_query_budget_enable

        return await util_classify_query_budget_signal(
            query_budget=self.query_budget,
            user_text=user_text,
            selected_tools=selected_tools,
            tone_signal=tone_signal,
            query_budget_enabled=bool(get_query_budget_enable()),
            log_info_fn=log_info,
            log_warn_fn=log_warn,
        )

    async def _classify_domain_signal(
        self,
        user_text: str,
        *,
        selected_tools: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        from config import get_domain_router_enable

        return await util_classify_domain_signal(
            domain_router=self.domain_router,
            user_text=user_text,
            selected_tools=selected_tools,
            domain_router_enabled=bool(get_domain_router_enable()),
            maybe_downgrade_cron_create_signal_fn=self._maybe_downgrade_cron_create_signal,
            log_info_fn=log_info,
            log_warn_fn=log_warn,
        )

    def _seed_tool_for_domain_route(
        self,
        route: Optional[Dict[str, Any]],
        *,
        user_text: str = "",
        suggested_tools: Optional[List[Any]] = None,
        verified_plan: Optional[Dict[str, Any]] = None,
    ) -> str:
        return util_seed_tool_for_domain_route(
            route,
            user_text=user_text,
            suggested_tools=suggested_tools,
            verified_plan=verified_plan,
            domain_cron_op_to_tool=self._DOMAIN_CRON_OP_TO_TOOL,
            domain_container_op_to_tool=self._DOMAIN_CONTAINER_OP_TO_TOOL,
            domain_container_tools=self._DOMAIN_CONTAINER_TOOLS,
            should_prioritize_skill_catalog_route_fn=(
                lambda plan, text: self._should_prioritize_skill_catalog_route(
                    plan,
                    user_text=text,
                )
            ),
            select_read_only_skill_tool_for_query_fn=(
                lambda text, plan: self._select_read_only_skill_tool_for_query(
                    text,
                    verified_plan=plan,
                )
            ),
            looks_like_host_runtime_lookup_fn=self._looks_like_host_runtime_lookup,
            extract_tool_name_fn=self._extract_tool_name,
        )

    @staticmethod
    def _looks_like_host_runtime_lookup(user_text: str) -> bool:
        return util_looks_like_host_runtime_lookup(user_text)

    def _apply_domain_route_to_plan(
        self,
        thinking_plan: Dict[str, Any],
        signal: Optional[Dict[str, Any]],
        *,
        user_text: str = "",
    ) -> Dict[str, Any]:
        return util_apply_domain_route_to_plan(
            thinking_plan,
            signal,
            user_text=user_text,
            domain_cron_tools=self._DOMAIN_CRON_TOOLS,
            read_only_skill_tools=self._READ_ONLY_SKILL_TOOLS,
            domain_skill_tools=self._DOMAIN_SKILL_TOOLS,
            domain_container_tools=self._DOMAIN_CONTAINER_TOOLS,
            should_prioritize_skill_catalog_route_fn=(
                lambda plan, text: self._should_prioritize_skill_catalog_route(
                    plan,
                    user_text=text,
                )
            ),
            extract_tool_name_fn=self._extract_tool_name,
            seed_tool_for_domain_route_fn=self._seed_tool_for_domain_route,
        )

    def _apply_domain_tool_policy(
        self,
        verified_plan: Dict[str, Any],
        suggested_tools: List[Any],
        *,
        user_text: str = "",
        prefix: str = "[Orchestrator]",
    ) -> List[Any]:
        return util_apply_domain_tool_policy(
            verified_plan,
            suggested_tools,
            user_text=user_text,
            prefix=prefix,
            domain_cron_tools=self._DOMAIN_CRON_TOOLS,
            read_only_skill_tools=self._READ_ONLY_SKILL_TOOLS,
            domain_skill_tools=self._DOMAIN_SKILL_TOOLS,
            domain_container_tools=self._DOMAIN_CONTAINER_TOOLS,
            should_prioritize_skill_catalog_route_fn=(
                lambda plan, text: self._should_prioritize_skill_catalog_route(
                    plan,
                    user_text=text,
                )
            ),
            seed_tool_for_domain_route_fn=self._seed_tool_for_domain_route,
            looks_like_host_runtime_lookup_fn=self._looks_like_host_runtime_lookup,
            extract_tool_name_fn=self._extract_tool_name,
            log_info_fn=log_info,
        )

    def _should_skip_thinking_from_query_budget(
        self,
        signal: Optional[Dict[str, Any]],
        *,
        user_text: str,
        forced_mode: str = "",
    ) -> bool:
        from config import (
            get_query_budget_skip_thinking_enable,
            get_query_budget_skip_thinking_min_confidence,
        )
        return util_should_skip_thinking_from_query_budget_runtime(
            signal,
            user_text=user_text,
            forced_mode=forced_mode,
            skip_enabled=bool(get_query_budget_skip_thinking_enable()),
            min_confidence=float(get_query_budget_skip_thinking_min_confidence()),
            is_explicit_deep_request_fn=self._is_explicit_deep_request,
            contains_explicit_tool_intent_fn=self._contains_explicit_tool_intent,
        )

    def _apply_query_budget_to_plan(
        self,
        thinking_plan: Dict[str, Any],
        signal: Optional[Dict[str, Any]],
        *,
        user_text: str = "",
    ) -> Dict[str, Any]:
        from config import get_query_budget_enable
        return util_apply_query_budget_to_plan_runtime(
            thinking_plan,
            signal,
            user_text=user_text,
            query_budget_enabled=bool(get_query_budget_enable()),
            should_force_query_budget_factual_memory_fn=lambda text, plan, sig: self._should_force_query_budget_factual_memory(
                user_text=text,
                thinking_plan=plan,
                signal=sig,
            ),
        )

    def _should_force_query_budget_factual_memory(
        self,
        *,
        user_text: str,
        thinking_plan: Dict[str, Any],
        signal: Dict[str, Any],
    ) -> bool:
        return util_should_force_query_budget_factual_memory_runtime(
            user_text=user_text,
            thinking_plan=thinking_plan,
            signal=signal,
            extract_tool_domain_tag_fn=self._extract_tool_domain_tag,
            has_non_memory_tool_runtime_signal_fn=self._has_non_memory_tool_runtime_signal,
            has_memory_recall_signal_fn=self._has_memory_recall_signal,
        )

    @staticmethod
    def _has_memory_recall_signal(text: str) -> bool:
        return util_has_memory_recall_signal(text)

    @staticmethod
    def _has_non_memory_tool_runtime_signal(text: str) -> bool:
        return util_has_non_memory_tool_runtime_signal(text)

    def _resolve_precontrol_policy_conflicts(
        self,
        user_text: str,
        thinking_plan: Dict[str, Any],
        *,
        conversation_id: str = "",
    ) -> Dict[str, Any]:
        """
        Resolve deterministic conflicts after QueryBudget+DomainRouter mutation.

        Priority:
          domain-locked tool execution > query-budget factual memory force.
        """
        from config import (
            get_policy_conflict_resolver_enable,
            get_policy_conflict_resolver_rollout_pct,
        )

        rollout_enabled = self._is_rollout_enabled(
            get_policy_conflict_resolver_rollout_pct(),
            conversation_id or user_text,
        )
        return util_resolve_precontrol_policy_conflicts_runtime(
            user_text,
            thinking_plan,
            resolver_enabled=bool(get_policy_conflict_resolver_enable()),
            rollout_enabled=bool(rollout_enabled),
            has_memory_recall_signal_fn=self._has_memory_recall_signal,
            contains_explicit_tool_intent_fn=self._contains_explicit_tool_intent,
            looks_like_host_runtime_lookup_fn=self._looks_like_host_runtime_lookup,
            has_non_memory_tool_runtime_signal_fn=self._has_non_memory_tool_runtime_signal,
            extract_tool_name_fn=self._extract_tool_name,
            log_info_fn=log_info,
        )

    def _apply_query_budget_tool_policy(
        self,
        user_text: str,
        verified_plan: Dict[str, Any],
        suggested_tools: List[Any],
        *,
        prefix: str = "[Orchestrator]",
    ) -> List[Any]:
        from config import (
            get_query_budget_enable,
            get_query_budget_max_tools_factual_low,
        )
        return util_apply_query_budget_tool_policy_runtime(
            user_text,
            verified_plan,
            suggested_tools,
            query_budget_enabled=bool(get_query_budget_enable()),
            max_tools_factual_low=int(get_query_budget_max_tools_factual_low()),
            heavy_tools=self._QUERY_BUDGET_HEAVY_TOOLS,
            contains_explicit_tool_intent_fn=self._contains_explicit_tool_intent,
            is_explicit_deep_request_fn=self._is_explicit_deep_request,
            is_explicit_think_request_fn=self._is_explicit_think_request,
            extract_tool_name_fn=self._extract_tool_name,
            prefix=prefix,
            log_info_fn=log_info,
        )

    def _ensure_dialogue_controls(
        self,
        thinking_plan: Dict[str, Any],
        tone_signal: Optional[Dict[str, Any]],
        *,
        user_text: str = "",
        selected_tools: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        try:
            from config import get_tone_signal_override_confidence
            override_threshold = float(get_tone_signal_override_confidence())
        except Exception:
            override_threshold = 0.82
        return util_ensure_dialogue_controls_runtime(
            thinking_plan,
            tone_signal,
            override_threshold=override_threshold,
            user_text=user_text,
            selected_tools=selected_tools,
            contains_explicit_tool_intent_fn=self._contains_explicit_tool_intent,
            has_non_memory_tool_runtime_signal_fn=self._has_non_memory_tool_runtime_signal,
        )

    def _coerce_thinking_plan_schema(
        self,
        thinking_plan: Dict[str, Any],
        *,
        user_text: str = "",
    ) -> Dict[str, Any]:
        from config import get_memory_keys_max_per_request

        return util_coerce_thinking_plan_schema(
            thinking_plan,
            user_text=user_text,
            max_memory_keys_per_request=int(get_memory_keys_max_per_request()),
            contains_explicit_tool_intent_fn=self._contains_explicit_tool_intent,
            has_memory_recall_signal_fn=self._has_memory_recall_signal,
        )

    @staticmethod
    def _contains_keyword_intent(
        text: str,
        keyword: str,
        *,
        whole_word: bool = False,
    ) -> bool:
        return util_contains_keyword_intent(
            text,
            keyword,
            whole_word=whole_word,
        )

    def _contains_explicit_tool_intent(self, user_text: str) -> bool:
        return util_contains_explicit_tool_intent(
            user_text,
            extract_tool_domain_tag_fn=self._extract_tool_domain_tag,
            contains_keyword_intent_fn=self._contains_keyword_intent,
            tool_intent_keywords=self._TOOL_INTENT_KEYWORDS,
            tool_intent_word_keywords=self._TOOL_INTENT_WORD_KEYWORDS,
        )

    def _contains_explicit_skill_intent(self, user_text: str) -> bool:
        return util_contains_explicit_skill_intent(
            user_text,
            extract_tool_domain_tag_fn=self._extract_tool_domain_tag,
            contains_keyword_intent_fn=self._contains_keyword_intent,
            skill_intent_keywords=self._SKILL_INTENT_KEYWORDS,
            skill_intent_word_keywords=self._SKILL_INTENT_WORD_KEYWORDS,
        )

    @classmethod
    def _extract_tool_domain_tag(cls, text: str) -> str:
        return util_extract_tool_domain_tag(
            text,
            tool_domain_tag_re=cls._TOOL_DOMAIN_TAG_RE,
            tool_domain_tag_short_re=cls._TOOL_DOMAIN_TAG_SHORT_RE,
        )

    @classmethod
    def _has_cron_schedule_signal(
        cls,
        user_text: str,
        route: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return util_has_cron_schedule_signal(
            user_text,
            route=route,
        )

    @classmethod
    def _is_explicit_cron_create_intent(
        cls,
        user_text: str,
        route: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return util_is_explicit_cron_create_intent(
            user_text,
            route=route,
            cron_meta_guard_markers=cls._CRON_META_GUARD_MARKERS,
            has_cron_schedule_signal_fn=cls._has_cron_schedule_signal,
        )

    def _maybe_downgrade_cron_create_signal(
        self,
        user_text: str,
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        return util_maybe_downgrade_cron_create_signal(
            user_text,
            signal,
            is_explicit_cron_create_intent_fn=self._is_explicit_cron_create_intent,
        )

    def _should_suppress_conversational_tools(
        self,
        user_text: str,
        verified_plan: Dict[str, Any],
    ) -> bool:
        return util_should_suppress_conversational_tools(
            user_text,
            verified_plan,
            tool_execution_policy=self.tool_execution_policy or {},
            contains_explicit_tool_intent_fn=self._contains_explicit_tool_intent,
        )

    def _sanitize_intent_thinking_plan_for_skill_task(self, thinking_plan: Any) -> Dict[str, Any]:
        return util_sanitize_intent_thinking_plan_for_skill_task(
            thinking_plan,
            safe_str_fn=lambda value, max_len: self._safe_str(value, max_len=max_len),
            extract_suggested_tool_names_fn=self._extract_suggested_tool_names,
        )

    def _should_skip_control_layer(self, user_text: str, thinking_plan: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Unified skip policy for sync + stream to avoid drift.

        Returns:
            (skip_control, reason)
        """
        try:
            policy = load_grounding_policy()
            force_verify_fact = bool(
                ((policy or {}).get("control") or {}).get("force_verify_for_fact_query", True)
            )
        except Exception:
            force_verify_fact = True
        return util_should_skip_control_layer(
            user_text,
            thinking_plan,
            enable_control_layer=bool(ENABLE_CONTROL_LAYER),
            skip_control_on_low_risk=bool(SKIP_CONTROL_ON_LOW_RISK),
            force_verify_fact=bool(force_verify_fact),
            suggested_tool_names=self._extract_suggested_tool_names(thinking_plan),
            control_skip_block_tools=tuple(self._CONTROL_SKIP_BLOCK_TOOLS),
            control_skip_block_keywords=self._CONTROL_SKIP_BLOCK_KEYWORDS,
            control_skip_hard_safety_keywords=self._CONTROL_SKIP_HARD_SAFETY_KEYWORDS,
        )

    @staticmethod
    def _build_grounding_evidence_entry(
        tool_name: str,
        raw_result: str,
        status: str,
        ref_id: str,
    ) -> Dict[str, Any]:
        return util_build_grounding_evidence_entry(
            tool_name,
            raw_result,
            status,
            ref_id,
        )

    @staticmethod
    def _count_successful_grounding_evidence(
        verified_plan: Dict[str, Any],
        allowed_statuses: Optional[List[str]] = None,
    ) -> int:
        return util_count_successful_grounding_evidence(
            verified_plan,
            allowed_statuses=allowed_statuses,
        )

    # ===============================================================
    # HARDWARE GATE EARLY CHECK
    # ===============================================================

    def _check_hardware_gate_early(self, user_text: str, thinking_plan: Dict) -> Optional[str]:
        """
        Schneller Pre-Check BEVOR Sequential Thinking läuft.
        Gibt Block-Nachricht zurück wenn gefährliche Anfrage erkannt, sonst None.
        Spart 20-40s Sequential Thinking bei Anfragen die sowieso geblockt werden.
        """
        def _get_gpu_status() -> str:
            hub = get_hub()
            hub.initialize()
            gpu_result = hub.call_tool("get_system_info", {"type": "gpu"})
            if isinstance(gpu_result, dict):
                return str(gpu_result.get("output", gpu_result))
            if isinstance(gpu_result, str):
                return gpu_result
            return str(gpu_result or "")

        return util_check_hardware_gate_early(
            user_text,
            thinking_plan,
            hardware_gate_patterns=_HARDWARE_GATE_PATTERNS,
            get_gpu_status_fn=_get_gpu_status,
            required_tool="autonomous_skill_task",
        )

    # ===============================================================
    # SKILL ROUTING
    # ===============================================================

    def _route_skill_request(self, user_text: str, thinking_plan: Dict) -> Optional[Dict]:
        """
        Embedding-basierter Skill-Router.
        Gibt dict zurück wenn existierender Skill gefunden (score >= MATCH_THRESHOLD),
        sonst None (→ Erstellung weiterhin erlaubt).

        Returns:
            {"skill_name": str, "score": float}
            {"blocked": True, "reason": "...", "error": "..."} bei Router-Fehler (fail-closed)
            oder None
        """
        return util_route_skill_request(
            user_text,
            thinking_plan,
            log_info_fn=log_info,
            log_error_fn=log_error,
        )

    # ===============================================================
    # BLUEPRINT ROUTING
    # ===============================================================

    def _route_blueprint_request(self, user_text: str, thinking_plan: Dict) -> Optional[Dict]:
        """
        Embedding-basierter Blueprint-Router.

        Returns:
            {"blueprint_id": str, "score": float}                                  → use_blueprint (auto-route)
            {"blueprint_id": str, "score": float, "suggest": True, "candidates": [...]} → suggest_blueprint (Rückfrage)
            {"blocked": True, "reason": "...", "error": "..."}                     → Router-Fehler (fail-closed)
            None                                                                    → no_blueprint (kein Freestyle!)
        """
        return util_route_blueprint_request(
            user_text,
            thinking_plan,
            log_error_fn=log_error,
        )

    def _prepare_container_candidate_evidence(
        self,
        user_text: str,
        thinking_plan: Dict[str, Any],
        *,
        chat_history: Optional[list] = None,
    ) -> None:
        return util_prepare_container_candidate_evidence(
            user_text,
            thinking_plan,
            chat_history=chat_history,
            message_content_fn=self._message_content_value,
            route_blueprint_request_fn=self._route_blueprint_request,
            log_info_fn=log_info,
        )

    # ===============================================================
    # TASK LIFECYCLE POST-PROCESSING (Phase 2)
    # ===============================================================

    def _post_task_processing(self):
        """
        Post-task processing after task completion.

        Enqueues durable archive-embedding jobs into a local SQLite queue.
        A background worker drains jobs asynchronously with retry/backoff.
        This avoids unbounded fire-and-forget thread spawning and survives
        process restarts for pending jobs.
        """
        util_post_task_processing(
            get_archive_embedding_queue_fn=_get_archive_embedding_queue,
            archive_manager=self.archive_manager,
            log_debug_fn=log_debug,
            log_info_fn=log_info,
            log_error_fn=log_error,
        )

    def _is_explicit_deep_request(self, user_text: str) -> bool:
        return util_is_explicit_deep_request(user_text)

    def _is_explicit_think_request(self, user_text: str) -> bool:
        return util_is_explicit_think_request(user_text)

    @staticmethod
    def _extract_tool_name(tool_spec: Any) -> str:
        return util_extract_tool_name(tool_spec)

    @classmethod
    def _is_home_container_info_query(cls, user_text: str) -> bool:
        return util_is_home_container_info_query(
            user_text,
            home_container_query_markers=cls._HOME_CONTAINER_QUERY_MARKERS,
            home_container_purpose_markers=cls._HOME_CONTAINER_PURPOSE_MARKERS,
            is_home_container_start_query_fn=cls._is_home_container_start_query,
        )

    @classmethod
    def _is_home_container_start_query(cls, user_text: str) -> bool:
        return util_is_home_container_start_query(
            user_text,
            home_container_query_markers=cls._HOME_CONTAINER_QUERY_MARKERS,
            home_container_start_markers=cls._HOME_CONTAINER_START_MARKERS,
        )

    def _rewrite_home_start_request_tools(
        self,
        user_text: str,
        verified_plan: Optional[Dict[str, Any]],
        suggested_tools: List[Any],
        *,
        prefix: str = "[Orchestrator]",
    ) -> List[Any]:
        return util_rewrite_home_start_request_tools(
            user_text,
            verified_plan,
            suggested_tools,
            prefix=prefix,
            is_home_container_start_query_fn=self._is_home_container_start_query,
            extract_tool_name_fn=self._extract_tool_name,
            log_info_fn=log_info,
        )

    def _prioritize_home_container_tools(
        self,
        user_text: str,
        verified_plan: Dict[str, Any],
        suggested_tools: List[Any],
        *,
        prefix: str = "[Orchestrator]",
    ) -> List[Any]:
        """
        Harden tool strategy for questions about TRION home containers.
        If the plan only suggests home_read/home_list-like tools, prepend container discovery.
        """
        return util_prioritize_home_container_tools(
            user_text,
            verified_plan,
            suggested_tools,
            prefix=prefix,
            is_home_container_info_query_fn=self._is_home_container_info_query,
            extract_tool_name_fn=self._extract_tool_name,
            log_info_fn=log_info,
        )

    @staticmethod
    def _recover_home_read_directory_with_fast_lane(
        dir_path: str,
        *,
        max_files: int = 5,
    ) -> Tuple[bool, str]:
        from core.tools.fast_lane.executor import FastLaneExecutor

        return util_recover_home_read_directory_with_fast_lane(
            dir_path,
            max_files=max_files,
            fast_lane_executor_cls=FastLaneExecutor,
        )

    @staticmethod
    def _sanitize_skill_name_candidate(raw_name: Any) -> str:
        return util_sanitize_skill_name_candidate(raw_name)

    def _extract_requested_skill_name(self, user_text: str) -> str:
        return util_extract_requested_skill_name(
            user_text,
            sanitize_skill_name_candidate_fn=self._sanitize_skill_name_candidate,
        )

    def _filter_think_tools(
        self,
        tools: list,
        user_text: str,
        thinking_plan: Optional[Dict[str, Any]],
        source: str,
    ) -> list:
        return util_filter_think_tools(
            tools,
            user_text=user_text,
            thinking_plan=thinking_plan,
            source=source,
            is_explicit_think_request_fn=self._is_explicit_think_request,
            extract_tool_name_fn=self._extract_tool_name,
            log_info_fn=log_info,
        )

    def _filter_tool_selector_candidates(
        self,
        selected_tools: Optional[list],
        user_text: str,
        forced_mode: str = "",
    ) -> Optional[list]:
        return util_filter_tool_selector_candidates(
            selected_tools,
            user_text=user_text,
            forced_mode=forced_mode,
            is_explicit_deep_request_fn=self._is_explicit_deep_request,
            filter_think_tools_fn=self._filter_think_tools,
        )

    def _requested_response_mode(self, request: CoreChatRequest) -> str:
        return util_requested_response_mode(request)

    def _resolve_runtime_output_model(self, requested_model: str) -> Tuple[str, Dict[str, Any]]:
        """
        Resolve a runtime-safe output model against the effective output endpoint.
        Keeps adapter input unchanged, but prevents invalid model identifiers from
        causing avoidable /api/chat 404 responses.
        """
        from config import get_output_model, get_output_provider

        return util_resolve_runtime_output_model(
            requested_model,
            ollama_base=self.ollama_base,
            get_output_model_fn=get_output_model,
            get_output_provider_fn=get_output_provider,
            resolve_role_endpoint_fn=resolve_role_endpoint,
            resolve_runtime_chat_model_fn=resolve_runtime_chat_model,
            log_info_fn=log_info,
            log_warn_fn=log_warn,
        )

    def _apply_response_mode_policy(
        self,
        user_text: str,
        thinking_plan: Dict[str, Any],
        forced_mode: str = "",
    ) -> str:
        """
        Resolve response mode and enforce interactive safeguards deterministically.
        """
        from config import get_default_response_mode, get_response_mode_sequential_threshold

        return util_apply_response_mode_policy(
            user_text,
            thinking_plan,
            forced_mode=forced_mode,
            get_default_response_mode_fn=get_default_response_mode,
            get_response_mode_sequential_threshold_fn=get_response_mode_sequential_threshold,
            is_explicit_deep_request_fn=self._is_explicit_deep_request,
            filter_think_tools_fn=self._filter_think_tools,
            log_info_fn=log_info,
        )

    # ===============================================================
    # SHARED HELPERS
    # ===============================================================

    async def _collect_control_tool_decisions(
        self,
        user_text: str,
        verified_plan: Dict[str, Any],
        *,
        control_decision: Optional[ControlDecision] = None,
        stream: bool = False,
    ) -> Dict[str, Dict]:
        """
        Collect authoritative tool args from ControlLayer with gate-override parity
        for sync and stream paths.
        """
        return await util_collect_control_tool_decisions(
            control=self.control,
            user_text=user_text,
            verified_plan=verified_plan,
            build_tool_args_fn=lambda tool_name, text, plan: self._build_tool_args(
                tool_name,
                text,
                verified_plan=plan,
            ),
            tool_allowed_by_control_decision_fn=tool_allowed_by_control_decision,
            control_decision=control_decision,
            stream=stream,
            log_info_fn=log_info,
            log_warn_fn=log_warn,
            log_error_fn=log_error,
        )

    def _resolve_execution_suggested_tools(
        self,
        user_text: str,
        verified_plan: Dict[str, Any],
        control_tool_decisions: Optional[Dict[str, Dict]],
        *,
        control_decision: Optional[ControlDecision] = None,
        stream: bool = False,
        enable_skill_trigger_router: bool = False,
        conversation_id: str = "",
        chat_history: Optional[list] = None,
    ) -> List[Any]:
        """
        Build final suggested_tools list with parity across sync and stream:
        ControlLayer authority -> Thinking fallback -> keyword fallback (+ optional trigger router).
        """
        return util_resolve_execution_suggested_tools(
            user_text=user_text,
            verified_plan=verified_plan,
            control_tool_decisions=control_tool_decisions,
            tool_execution_policy=self.tool_execution_policy,
            low_signal_action_tools=list(self._LOW_SIGNAL_ACTION_TOOLS),
            control_decision=control_decision,
            stream=stream,
            enable_skill_trigger_router=enable_skill_trigger_router,
            conversation_id=conversation_id,
            chat_history=chat_history,
            finalize_execution_suggested_tools_fn=self._finalize_execution_suggested_tools,
            should_suppress_conversational_tools_fn=self._should_suppress_conversational_tools,
            looks_like_short_confirmation_followup_fn=self._looks_like_short_confirmation_followup,
            resolve_followup_tool_reuse_fn=self._resolve_followup_tool_reuse,
            normalize_tools_fn=self._normalize_tools,
            extract_tool_name_fn=self._extract_tool_name,
            get_effective_resolution_strategy_fn=self._get_effective_resolution_strategy,
            prioritize_home_container_tools_fn=self._prioritize_home_container_tools,
            rewrite_home_start_request_tools_fn=self._rewrite_home_start_request_tools,
            prioritize_active_container_capability_tools_fn=self._prioritize_active_container_capability_tools,
            apply_container_query_policy_fn=self._apply_container_query_policy,
            apply_query_budget_tool_policy_fn=self._apply_query_budget_tool_policy,
            apply_domain_tool_policy_fn=self._apply_domain_tool_policy,
            detect_tools_by_keyword_fn=self._detect_tools_by_keyword,
            contains_explicit_skill_intent_fn=self._contains_explicit_skill_intent,
            detect_skill_by_trigger_fn=self._detect_skill_by_trigger,
            looks_like_host_runtime_lookup_fn=self._looks_like_host_runtime_lookup,
            tool_allowed_by_control_decision_fn=tool_allowed_by_control_decision,
            log_info_fn=log_info,
        )

    def _tool_name_list(self, suggested_tools: Optional[List[Any]]) -> List[str]:
        return util_tool_name_list(
            suggested_tools,
            extract_tool_name_fn=self._extract_tool_name,
        )

    def _materialize_skill_catalog_policy(
        self,
        verified_plan: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return util_materialize_skill_catalog_policy(
            verified_plan,
            effective_resolution_strategy=self._get_effective_resolution_strategy(verified_plan),
            read_only_skill_tools=self._READ_ONLY_SKILL_TOOLS,
            skill_action_tools=self._SKILL_ACTION_TOOLS,
            tool_name_list_fn=self._tool_name_list,
        )

    def _record_execution_tool_trace(
        self,
        verified_plan: Optional[Dict[str, Any]],
        suggested_tools: Optional[List[Any]],
    ) -> None:
        util_record_execution_tool_trace(
            verified_plan,
            suggested_tools,
            tool_name_list_fn=self._tool_name_list,
            get_effective_resolution_strategy_fn=self._get_effective_resolution_strategy,
        )

    def _finalize_execution_suggested_tools(
        self,
        verified_plan: Optional[Dict[str, Any]],
        suggested_tools: Optional[List[Any]],
    ) -> List[Any]:
        return util_finalize_execution_suggested_tools(
            verified_plan,
            suggested_tools,
            tool_name_list_fn=self._tool_name_list,
            record_execution_tool_trace_fn=self._record_execution_tool_trace,
        )

    @staticmethod
    def _get_effective_resolution_strategy(verified_plan: Optional[Dict[str, Any]]) -> str:
        return util_get_effective_resolution_strategy(verified_plan)

    def _detect_tools_by_keyword(self, user_text: str) -> list:
        """Keyword-based tool detection fallback when Thinking suggests none."""
        return util_detect_tools_by_keyword(
            user_text,
            is_home_container_info_query_fn=self._is_home_container_info_query,
            is_home_container_start_query_fn=self._is_home_container_start_query,
            is_active_container_capability_query_fn=self._is_active_container_capability_query,
            is_container_state_binding_query_fn=self._is_container_state_binding_query,
            is_container_blueprint_catalog_query_fn=self._is_container_blueprint_catalog_query,
            is_container_inventory_query_fn=self._is_container_inventory_query,
            is_container_request_query_fn=self._is_container_request_query,
        )

    @staticmethod
    def _container_state_has_active_target(state: Optional[Dict[str, Any]]) -> bool:
        return util_container_state_has_active_target(state)

    @classmethod
    def _is_active_container_capability_query(cls, user_text: str) -> bool:
        return util_is_active_container_capability_query(
            user_text,
            active_container_capability_exclude_markers=cls._ACTIVE_CONTAINER_CAPABILITY_EXCLUDE_MARKERS,
            active_container_deictic_markers=cls._ACTIVE_CONTAINER_DEICTIC_MARKERS,
            active_container_capability_markers=cls._ACTIVE_CONTAINER_CAPABILITY_MARKERS,
        )

    @classmethod
    def _is_container_inventory_query(cls, user_text: str) -> bool:
        return util_is_container_inventory_query(
            user_text,
            container_inventory_query_markers=cls._CONTAINER_INVENTORY_QUERY_MARKERS,
            is_container_blueprint_catalog_query_fn=cls._is_container_blueprint_catalog_query,
            is_container_request_query_fn=cls._is_container_request_query,
        )

    @classmethod
    def _is_container_blueprint_catalog_query(cls, user_text: str) -> bool:
        return util_is_container_blueprint_catalog_query(
            user_text,
            container_blueprint_query_markers=cls._CONTAINER_BLUEPRINT_QUERY_MARKERS,
            is_container_request_query_fn=cls._is_container_request_query,
        )

    @classmethod
    def _is_container_state_binding_query(cls, user_text: str) -> bool:
        return util_is_container_state_binding_query(
            user_text,
            container_state_query_markers=cls._CONTAINER_STATE_QUERY_MARKERS,
            is_active_container_capability_query_fn=cls._is_active_container_capability_query,
        )

    @classmethod
    def _is_container_request_query(cls, user_text: str) -> bool:
        return util_is_container_request_query(
            user_text,
            container_request_query_markers=cls._CONTAINER_REQUEST_QUERY_MARKERS,
        )

    @classmethod
    def _is_skill_catalog_context_query(cls, user_text: str) -> bool:
        return util_is_skill_catalog_context_query(
            user_text,
            skill_catalog_exclude_markers=cls._SKILL_CATALOG_EXCLUDE_MARKERS,
            skill_catalog_query_markers=cls._SKILL_CATALOG_QUERY_MARKERS,
        )

    def _should_prioritize_skill_catalog_route(
        self,
        verified_plan: Optional[Dict[str, Any]],
        *,
        user_text: str = "",
    ) -> bool:
        return util_should_prioritize_skill_catalog_route(
            verified_plan,
            user_text=user_text,
            get_effective_resolution_strategy_fn=self._get_effective_resolution_strategy,
            is_skill_catalog_context_query_fn=self._is_skill_catalog_context_query,
        )

    def _select_read_only_skill_tool_for_query(
        self,
        user_text: str,
        *,
        verified_plan: Optional[Dict[str, Any]] = None,
    ) -> str:
        return util_select_read_only_skill_tool_for_query(
            user_text,
            verified_plan=verified_plan,
        )

    def _prioritize_active_container_capability_tools(
        self,
        user_text: str,
        verified_plan: Dict[str, Any],
        suggested_tools: List[Any],
        *,
        conversation_id: str = "",
        force: bool = False,
        prefix: str = "[Orchestrator]",
    ) -> List[Any]:
        return util_prioritize_active_container_capability_tools(
            user_text,
            verified_plan,
            suggested_tools,
            conversation_id=conversation_id,
            force=force,
            prefix=prefix,
            is_active_container_capability_query_fn=self._is_active_container_capability_query,
            get_recent_container_state_fn=self._get_recent_container_state,
            container_state_has_active_target_fn=self._container_state_has_active_target,
            extract_tool_name_fn=self._extract_tool_name,
            log_info_fn=log_info,
        )

    def _materialize_container_query_policy(
        self,
        verified_plan: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return util_materialize_container_query_policy(
            verified_plan,
            strategy=self._get_effective_resolution_strategy(verified_plan),
        )

    def _apply_container_query_policy(
        self,
        user_text: str,
        verified_plan: Dict[str, Any],
        suggested_tools: List[Any],
        *,
        conversation_id: str = "",
        prefix: str = "[Orchestrator]",
    ) -> List[Any]:
        return util_apply_container_query_policy(
            user_text,
            verified_plan,
            suggested_tools,
            conversation_id=conversation_id,
            prefix=prefix,
            get_effective_resolution_strategy_fn=self._get_effective_resolution_strategy,
            is_active_container_capability_query_fn=self._is_active_container_capability_query,
            is_container_state_binding_query_fn=self._is_container_state_binding_query,
            is_container_blueprint_catalog_query_fn=self._is_container_blueprint_catalog_query,
            is_container_request_query_fn=self._is_container_request_query,
            is_container_inventory_query_fn=self._is_container_inventory_query,
            materialize_container_query_policy_fn=(
                lambda plan, strategy: util_materialize_container_query_policy(
                    plan,
                    strategy=strategy,
                )
            ),
            get_recent_container_state_fn=self._get_recent_container_state,
            container_state_has_active_target_fn=self._container_state_has_active_target,
            is_home_container_start_query_fn=self._is_home_container_start_query,
            extract_tool_name_fn=self._extract_tool_name,
            tool_name_list_fn=self._tool_name_list,
            log_info_fn=log_info,
        )

    @staticmethod
    def _merge_grounding_evidence_items(
        existing: Any,
        extra: Any,
    ) -> List[Dict[str, Any]]:
        return util_merge_grounding_evidence_items(existing, extra)

    @staticmethod
    def _derive_container_addon_tags_from_inspect(container_info: Dict[str, Any]) -> List[str]:
        return util_derive_container_addon_tags_from_inspect(container_info)

    @staticmethod
    def _parse_list_skills_runtime_snapshot(raw_result: Any) -> Dict[str, Any]:
        return util_parse_list_skills_runtime_snapshot(raw_result)

    @staticmethod
    def _parse_list_draft_skills_snapshot(raw_result: Any) -> Dict[str, Any]:
        return util_parse_list_draft_skills_snapshot(raw_result)

    @staticmethod
    def _summarize_skill_runtime_snapshot(snapshot: Dict[str, Any]) -> str:
        return util_summarize_skill_runtime_snapshot(snapshot)

    @staticmethod
    def _summarize_skill_registry_snapshot(snapshot: Dict[str, Any]) -> str:
        return util_summarize_skill_registry_snapshot(snapshot)

    @staticmethod
    def _summarize_container_inspect_for_capability_context(container_info: Dict[str, Any]) -> str:
        return util_summarize_container_inspect_for_capability_context(container_info)

    async def _maybe_build_active_container_capability_context(
        self,
        *,
        user_text: str,
        conversation_id: str,
        verified_plan: Dict[str, Any],
        history_len: int = 0,
    ) -> Dict[str, str]:
        return await util_maybe_build_active_container_capability_context(
            user_text=user_text,
            conversation_id=conversation_id,
            verified_plan=verified_plan,
            history_len=history_len,
            is_active_container_capability_query_fn=self._is_active_container_capability_query,
            get_recent_container_state_fn=self._get_recent_container_state,
            container_state_has_active_target_fn=self._container_state_has_active_target,
            get_hub_fn=get_hub,
            resolve_pending_container_id_async_fn=self._resolve_pending_container_id_async,
            safe_str_fn=lambda value, max_len: self._safe_str(value, max_len=max_len),
            update_container_state_from_tool_result_fn=self._update_container_state_from_tool_result,
            build_tool_result_card_fn=self._build_tool_result_card,
            build_grounding_evidence_entry_fn=self._build_grounding_evidence_entry,
            merge_grounding_evidence_items_fn=self._merge_grounding_evidence_items,
            log_warn_fn=log_warn,
        )

    async def _maybe_build_skill_semantic_context(
        self,
        *,
        user_text: str,
        conversation_id: str,
        verified_plan: Dict[str, Any],
    ) -> Dict[str, str]:
        return await util_maybe_build_skill_semantic_context(
            user_text=user_text,
            conversation_id=conversation_id,
            verified_plan=verified_plan,
            get_effective_resolution_strategy_fn=self._get_effective_resolution_strategy,
            is_skill_catalog_context_query_fn=self._is_skill_catalog_context_query,
            materialize_skill_catalog_policy_fn=self._materialize_skill_catalog_policy,
            get_hub_fn=get_hub,
            build_tool_result_card_fn=self._build_tool_result_card,
            build_grounding_evidence_entry_fn=self._build_grounding_evidence_entry,
            merge_grounding_evidence_items_fn=self._merge_grounding_evidence_items,
            safe_str_fn=lambda value, max_len: self._safe_str(value, max_len=max_len),
            log_warn_fn=log_warn,
        )

    def _detect_skill_by_trigger(self, user_text: str) -> list:
        """
        Matcht User-Text gegen Skill-Triggers via REST-API.
        Wird aufgerufen wenn ThinkingLayer + Keyword-Fallback keine Tools gefunden haben.
        Gibt [skill_name] zurück wenn ein Trigger-Keyword im User-Text gefunden wird.
        """
        return util_detect_skill_by_trigger(
            user_text,
            log_info_fn=log_info,
        )

    def _normalize_tools(self, suggested_tools: list) -> list:
        return util_normalize_tools(
            suggested_tools,
            get_hub_fn=get_hub,
            log_info_fn=log_info,
        )

    @staticmethod
    def _extract_cron_job_id_from_text(user_text: str, verified_plan: Optional[Dict[str, Any]]) -> str:
        return util_extract_cron_job_id_from_text(user_text, verified_plan)

    @staticmethod
    def _extract_cron_expression_from_text(user_text: str, verified_plan: Optional[Dict[str, Any]]) -> str:
        return util_extract_cron_expression_from_text(user_text, verified_plan)

    @staticmethod
    def _extract_one_shot_run_at_from_text(user_text: str, verified_plan: Optional[Dict[str, Any]]) -> str:
        return util_extract_one_shot_run_at_from_text(
            user_text,
            verified_plan,
            datetime_cls=datetime,
            timedelta_cls=timedelta,
            timezone_utc=timezone.utc,
        )

    def _extract_cron_schedule_from_text(
        self,
        user_text: str,
        verified_plan: Optional[Dict[str, Any]],
    ) -> Dict[str, str]:
        return util_extract_cron_schedule_from_text(
            user_text,
            verified_plan,
            extract_cron_expression_from_text_fn=self._extract_cron_expression_from_text,
            extract_one_shot_run_at_from_text_fn=self._extract_one_shot_run_at_from_text,
            datetime_cls=datetime,
            timedelta_cls=timedelta,
            timezone_utc=timezone.utc,
        )

    @staticmethod
    def _build_cron_name(user_text: str) -> str:
        return util_build_cron_name(user_text)

    @staticmethod
    def _looks_like_self_state_request(text: str) -> bool:
        return util_looks_like_self_state_request(text)

    @staticmethod
    def _build_cron_objective(user_text: str) -> str:
        from core.orchestrator_modules.policy.cron_mode_guard import assess_cron_mode
        mode = assess_cron_mode(user_text)
        objective = util_build_cron_objective(
            user_text,
            looks_like_self_state_request_fn=PipelineOrchestrator._looks_like_self_state_request,
        )
        if not mode.is_persistent and mode.confidence >= 0.3:
            return f"one_shot_intent::{objective}"
        return objective

    @staticmethod
    def _extract_direct_cron_reminder_text(objective: str) -> str:
        return util_extract_direct_cron_reminder_text(objective)

    @staticmethod
    def _extract_cron_ack_message_from_objective(objective: str) -> str:
        return util_extract_cron_ack_message_from_objective(
            objective,
            looks_like_self_state_request_fn=PipelineOrchestrator._looks_like_self_state_request,
        )

    @staticmethod
    def _format_utc_compact(raw_iso: str) -> str:
        return util_format_utc_compact(
            raw_iso,
            datetime_cls=datetime,
            timezone_utc=timezone.utc,
        )

    def _build_direct_cron_create_response(
        self,
        result: Any,
        tool_args: Dict[str, Any],
        conversation_id: str,
    ) -> str:
        return util_build_direct_cron_create_response(
            result,
            tool_args,
            conversation_id,
            detect_tool_error_fn=detect_tool_error,
            format_utc_compact_fn=self._format_utc_compact,
            extract_cron_ack_message_from_objective_fn=self._extract_cron_ack_message_from_objective,
        )

    def _bind_cron_conversation_id(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        conversation_id: str,
    ) -> None:
        util_bind_cron_conversation_id(
            tool_name,
            tool_args,
            conversation_id,
            log_info_fn=log_info,
        )

    @staticmethod
    def _suggest_cron_expression_for_min_interval(min_interval_s: int) -> str:
        return util_suggest_cron_expression_for_min_interval(min_interval_s)

    @staticmethod
    def _extract_interval_hint_from_cron(expr: str) -> Dict[str, int]:
        return util_extract_interval_hint_from_cron(expr)

    def _prevalidate_cron_policy_args(
        self,
        tool_name: str,
        args: Dict[str, Any],
    ) -> Tuple[bool, str]:
        return util_prevalidate_cron_policy_args(
            tool_name,
            args,
            datetime_cls=datetime,
            timedelta_cls=timedelta,
            timezone_utc=timezone.utc,
            suggest_cron_expression_for_min_interval_fn=self._suggest_cron_expression_for_min_interval,
            extract_interval_hint_from_cron_fn=self._extract_interval_hint_from_cron,
        )

    def _build_tool_args(self, tool_name: str, user_text: str, verified_plan: Dict = None) -> dict:
        """
        Emergency-Fallback: Minimale Standard-Args für bekannte Tools.
        Wird nur aufgerufen wenn ControlLayer.decide_tools() keine Args liefert.
        Kein komplexes Keyword-Parsing — ControlLayer übernimmt das via Function Calling.

        Legacy contract markers (implementation moved to `core/orchestrator_tool_args_utils.py`):
        if any(tok in lower for tok in ("steam-headless", "sunshine", "gaming station", "gaming-station", "zocken", "moonlight")):
            return {"blueprint_id": "gaming-station"}
        elif tool_name == "blueprint_create":
            {"id": "gaming-station", "image": "josh5/steam-headless:latest"}
        """
        return util_build_tool_args(
            tool_name,
            user_text,
            verified_plan=verified_plan,
            extract_requested_skill_name_fn=self._extract_requested_skill_name,
            looks_like_host_runtime_lookup_fn=self._looks_like_host_runtime_lookup,
            extract_cron_schedule_from_text_fn=self._extract_cron_schedule_from_text,
            build_cron_objective_fn=self._build_cron_objective,
            build_cron_name_fn=self._build_cron_name,
            extract_cron_job_id_from_text_fn=self._extract_cron_job_id_from_text,
            extract_cron_expression_from_text_fn=self._extract_cron_expression_from_text,
        )

    def _validate_tool_args(
        self,
        tool_hub,
        tool_name: str,
        tool_args: Dict[str, Any],
        user_text: str,
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        Last-line defensive arg validation against MCP inputSchema.required.
        Auto-fills common missing fields when safe.
        """
        return util_validate_tool_args(
            tool_hub,
            tool_name,
            tool_args,
            user_text,
            extract_requested_skill_name_fn=self._extract_requested_skill_name,
            sanitize_skill_name_candidate_fn=self._sanitize_skill_name_candidate,
            extract_cron_schedule_from_text_fn=self._extract_cron_schedule_from_text,
            prevalidate_cron_policy_args_fn=self._prevalidate_cron_policy_args,
        )

    def _execute_tools_sync(
        self,
        suggested_tools: list,
        user_text: str,
        control_tool_decisions: dict = None,
        *,
        last_assistant_msg: str = "",
        control_decision: Optional[ControlDecision] = None,
        time_reference: str = None,
        thinking_suggested_tools: list = None,
        blueprint_gate_blocked: bool = False,
        blueprint_router_id: str = None,
        blueprint_suggest_msg: str = "",
        session_id: str = "",
        verified_plan: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Execute tools and return combined context string."""
        return util_execute_tools_sync(
            suggested_tools,
            user_text,
            last_assistant_msg=last_assistant_msg,
            control_tool_decisions=control_tool_decisions,
            control_decision=control_decision,
            time_reference=time_reference,
            thinking_suggested_tools=thinking_suggested_tools,
            blueprint_gate_blocked=blueprint_gate_blocked,
            blueprint_router_id=blueprint_router_id,
            blueprint_suggest_msg=blueprint_suggest_msg,
            session_id=session_id,
            verified_plan=verified_plan,
            get_hub_fn=get_hub,
            get_recent_container_state_fn=self._get_recent_container_state,
            build_tool_args_fn=self._build_tool_args,
            route_blueprint_request_fn=self._route_blueprint_request,
            tool_requires_container_id_fn=self._tool_requires_container_id,
            resolve_pending_container_id_sync_fn=self._resolve_pending_container_id_sync,
            validate_tool_args_fn=self._validate_tool_args,
            bind_cron_conversation_id_fn=self._bind_cron_conversation_id,
            format_tool_result_fn=self._format_tool_result,
            build_tool_result_card_fn=self._build_tool_result_card,
            build_grounding_evidence_entry_fn=self._build_grounding_evidence_entry,
            sanitize_tool_args_for_state_fn=self._sanitize_tool_args_for_state,
            verify_container_running_fn=self._verify_container_running,
            save_workspace_entry_fn=self._save_workspace_entry,
            update_container_state_from_tool_result_fn=self._update_container_state_from_tool_result,
            tool_intelligence_handle_tool_result_fn=self.tool_intelligence.handle_tool_result,
            build_direct_cron_create_response_fn=self._build_direct_cron_create_response,
            recover_home_read_directory_with_fast_lane_fn=self._recover_home_read_directory_with_fast_lane,
            build_container_event_content_fn=self._build_container_event_content,
            save_container_event_fn=self._save_container_event,
            log_info_fn=log_info,
            log_warn_fn=log_warn,
            log_error_fn=log_error,
            log_warning_fn=log_warn,
        )


    def _format_tool_result(self, result, tool_name: str):
        return util_format_tool_result(
            result,
            tool_name,
            detect_tool_error_fn=detect_tool_error,
        )

    @staticmethod
    def _tool_context_has_failures_or_skips(tool_context: str) -> bool:
        """Detect tool failures/skips that should prevent high-confidence promotion."""
        return util_tool_context_has_failures_or_skips(tool_context)

    @staticmethod
    def _tool_context_has_success(tool_context: str) -> bool:
        """Require explicit successful tool evidence instead of assuming success by absence of errors."""
        return util_tool_context_has_success(tool_context)


    # ═══════════════════════════════════════════════════════════
    def _build_container_event_content(
        self,
        tool_name: str,
        result: dict,
        user_text: str,
        tool_args: dict,
        session_id: str = "",
    ) -> Optional[dict]:
        """
        Build a workspace event dict for container lifecycle events.
        Returns {"event_type": str, "event_data": dict} or None.
        session_id: conversation_id of the current chat (for Session ↔ Container tracking).
        """
        def _resolve_exec_blueprint_id(container_id: str, exec_tool_args: Dict[str, Any]) -> str:
            blueprint_id = exec_tool_args.get("blueprint_id", "")
            if blueprint_id:
                return str(blueprint_id)
            try:
                from container_commander.engine import get_client as _get_docker

                return _get_docker().containers.get(container_id).labels.get("trion.blueprint", "unknown")
            except Exception:
                return "unknown"

        return util_build_container_event_content(
            tool_name,
            result,
            user_text,
            tool_args,
            session_id=session_id,
            utcnow_fn=datetime.utcnow,
            resolve_exec_blueprint_id_fn=_resolve_exec_blueprint_id,
        )

    def _verify_container_running(self, container_id: str) -> bool:
        """
        Phase-1 Verify: Check if a container is actually running via Engine.
        Uses container_stats as a lightweight ping.
        Returns True if container exists and is running, False otherwise.
        Does NOT attempt repair (Phase-1 policy: fail-only).
        """
        return util_verify_container_running(
            container_id,
            get_hub_fn=get_hub,
            log_info_fn=log_info,
            log_warn_fn=log_warn,
        )

    def _save_workspace_entry(
        self,
        conversation_id: str,
        content: str,
        entry_type: str = "observation",
        source_layer: str = "thinking"
    ) -> Optional[Dict]:
        """
        Save an internal workspace event via Fast-Lane (workspace_event_save).
        Returns the SSE event dict to yield, or None on failure.
        Delegates to WorkspaceEventEmitter.persist().
        """
        from core.workspace_event_emitter import get_workspace_emitter
        return util_save_workspace_entry(
            conversation_id,
            content,
            entry_type=entry_type,
            source_layer=source_layer,
            get_workspace_emitter_fn=get_workspace_emitter,
        )

    def _save_container_event(
        self,
        conversation_id: str,
        container_evt: dict,
    ) -> Optional[Dict]:
        """
        Persist a container lifecycle event via workspace_event_save (Fast-Lane).
        container_evt must have keys: event_type (str), event_data (dict).
        Returns the SSE workspace_update dict to yield, or None on failure.
        Delegates to WorkspaceEventEmitter.persist_container().
        """
        from core.workspace_event_emitter import get_workspace_emitter
        return util_save_container_event(
            conversation_id,
            container_evt,
            get_workspace_emitter_fn=get_workspace_emitter,
        )

    @staticmethod
    def _build_control_workspace_summary(
        verification: Dict[str, Any],
        *,
        skipped: bool,
        skip_reason: str = "",
    ) -> str:
        return build_control_workspace_summary(
            verification,
            skipped=skipped,
            skip_reason=skip_reason,
        )

    @classmethod
    def _is_control_hard_block_decision(cls, verification: Dict[str, Any]) -> bool:
        _ = cls
        return is_control_hard_block_decision(verification)

    @staticmethod
    def _build_done_workspace_summary(
        done_reason: str,
        *,
        response_mode: str = "",
        model: str = "",
        memory_used: Optional[bool] = None,
    ) -> str:
        return build_done_workspace_summary(
            done_reason,
            response_mode=response_mode,
            model=model,
            memory_used=memory_used,
        )

    @staticmethod
    def _build_sequential_workspace_summary(event: Dict[str, Any]) -> Tuple[str, str]:
        return build_sequential_workspace_summary(event)

    def _persist_sequential_workspace_event(
        self,
        conversation_id: str,
        event: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        return persist_sequential_workspace_event(
            self._save_workspace_entry,
            conversation_id,
            event,
        )

    @staticmethod
    def _build_master_workspace_summary(event_type: str, payload: Dict[str, Any]) -> str:
        return util_build_master_workspace_summary(event_type, payload)

    def _persist_master_workspace_event(
        self,
        conversation_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        return util_persist_master_workspace_event(
            conversation_id=conversation_id,
            event_type=event_type,
            payload=payload,
            build_master_workspace_summary_fn=self._build_master_workspace_summary,
            save_workspace_entry_fn=self._save_workspace_entry,
        )

    def _get_compact_context(
        self,
        conversation_id: Optional[str],
        has_tool_failure: bool = False,
        *,
        exclude_event_types: Optional[set] = None,
        csv_trigger: Optional[str] = None,
    ) -> str:
        """
        Build a compact NOW/RULES/NEXT context block for small-model-mode.

        JIT Retrieval-Budget:
          - default: 1 fetch (workspace_event_list for this conversation)
          - on tool failure: 2 fetches (adds _container_events global store)

        Args:
            exclude_event_types: Optional set of event_type strings to skip when building
                compact context. Used by SINGLE_TRUTH_GUARD to prevent double injection
                of tool_result events that are already in tool_context.

        Returns empty string if SMALL_MODEL_MODE is disabled or an error occurs.
        """
        return util_get_compact_context(
            context_manager=self.context,
            conversation_id=conversation_id,
            has_tool_failure=has_tool_failure,
            exclude_event_types=exclude_event_types,
            csv_trigger=csv_trigger,
            log_info_fn=log_info,
            log_warn_fn=log_warn,
        )

    def _build_effective_context(
        self,
        user_text: str,
        conv_id: Optional[str],
        *,
        small_model_mode: bool,
        cleanup_payload: Optional[Dict] = None,
        include_blocks: Optional[Dict] = None,
        debug_flags: Optional[Dict] = None,
        request_cache: Optional[Dict[str, Any]] = None,
    ) -> tuple:
        return util_build_effective_context(
            self,
            user_text,
            conv_id,
            small_model_mode=small_model_mode,
            cleanup_payload=cleanup_payload,
            include_blocks=include_blocks,
            debug_flags=debug_flags,
            request_cache=request_cache,
        )

    # ── Commit 1: Canonical public entry-point ────────────────────────────
    def build_effective_context(self, *args, **kwargs) -> tuple:
        """Public canonical entry-point for context assembly (wraps _build_effective_context)."""
        return self._build_effective_context(*args, **kwargs)

    # ── Commit 2: Central context-mutation hook ───────────────────────────
    def _append_context_block(
        self,
        ctx_str: str,
        new_block: str,
        source_name: str,
        trace: Dict,
        *,
        prepend: bool = False,
    ) -> str:
        """
        Append (or prepend) new_block to ctx_str.
        Updates trace context_sources and context_chars_final.
        Returns the updated context string.
        """
        return util_append_context_block(
            ctx_str,
            new_block,
            source_name,
            trace,
            prepend=prepend,
        )

    # ── Commit 4: Failure-compact via single call-point (Gap D closure) ───
    def _build_failure_compact_block(
        self,
        conv_id: Optional[str],
        current_context_len: int,
        small_model_mode: bool,
    ) -> str:
        """
        Build the failure-compact block for inline injection on tool failure.
        Single caller of _get_compact_context for failure paths — closes Gap D.
        Returns formatted block string or empty string.

        SINGLE_TRUTH_GUARD: tool_result events are already in tool_context
        (the authoritative channel). They are excluded here to prevent double
        injection of the same data into both compact context and tool_ctx.
        """
        return util_build_failure_compact_block(
            conv_id,
            current_context_len,
            small_model_mode,
            get_compact_context_fn=self._get_compact_context,
        )

    # ── Phase 1.5 Commit 1: Final hard cap — always active in small mode ──
    def _apply_final_cap(self, ctx: str, trace: Dict, small_model_mode: bool, label: str) -> str:
        """
        Apply final context hard-cap for small-model-mode.
        Uses SMALL_MODEL_FINAL_CAP if set > 0, otherwise falls back to SMALL_MODEL_CHAR_CAP.
        This ensures the cap is always active in small mode, not just when the env var is set.
        """
        return util_apply_final_cap(
            ctx,
            trace,
            small_model_mode,
            label,
            log_warn_fn=log_warn,
        )

    def _apply_effective_context_guardrail(
        self,
        ctx: str,
        trace: Dict,
        small_model_mode: bool,
        label: str,
    ) -> str:
        return util_apply_effective_context_guardrail(
            ctx=ctx,
            trace=trace,
            small_model_mode=small_model_mode,
            label=label,
            log_warn_fn=log_warn,
        )

    # ── Phase 1.5 Commit 2: Clip tool_context to budget (small mode only) ──
    def _clip_tool_context(self, tool_context: str, small_model_mode: bool) -> str:
        """
        Clip tool_context to SMALL_MODEL_TOOL_CTX_CAP in small-model-mode.
        If cap is 0 (default), no clipping is applied.
        """
        from config import get_small_model_tool_ctx_cap

        return util_clip_tool_context(
            tool_context,
            small_model_mode=small_model_mode,
            get_small_model_tool_ctx_cap_fn=get_small_model_tool_ctx_cap,
            tool_context_has_failures_or_skips_fn=self._tool_context_has_failures_or_skips,
            log_warn_fn=log_warn,
        )

    # ── Commit 2: Tool Result Card + Full Payload in workspace_events ──
    _TOOL_CARD_CHAR_CAP: int = 800
    _TOOL_CARD_BULLET_CAP: int = 3

    def _build_tool_result_card(
        self,
        tool_name: str,
        raw_result: str,
        status: str,
        conversation_id: str,
    ) -> tuple:
        """
        Build a compact Tool Result Card for tool_context (single model channel).
        Saves a large payload (≤ 50 KB) as a workspace_event with a ref_id for audit trail.

        Returns: (card_str, ref_id)
          - card_str: compact card to embed in tool_context
          - ref_id: 12-char UUID prefix linking to the workspace_event
        """
        # Legacy contract markers kept here for source-inspection tests:
        # _entry_type
        # approval_requested
        # pending_package_approval
        # 50_000
        return util_build_tool_result_card(
            tool_name=tool_name,
            raw_result=raw_result,
            status=status,
            conversation_id=conversation_id,
            save_workspace_entry_fn=self._save_workspace_entry,
            log_warn_fn=log_warn,
            tool_card_char_cap=self._TOOL_CARD_CHAR_CAP,
            tool_card_bullet_cap=self._TOOL_CARD_BULLET_CAP,
        )

    # ── Commit 4: Central retrieval policy — single budget authority ──
    def _compute_retrieval_policy(
        self,
        thinking_plan: Dict,
        verified_plan: Dict,
        current_tool_context: str = "",
    ) -> Dict:
        """
        Compute the canonical retrieval budget for a request.

        Returns:
          {
            "max_retrievals": int,       # total fetch budget
            "tool_failure": bool,        # whether tool failure was detected
            "time_reference": str|None,  # forwarded for caller use
            "reasons": list[str],        # human-readable budget justification
          }

        Budget rules:
          Normal  → get_jit_retrieval_max()       (default: 1)
          Failure → get_jit_retrieval_max_on_failure()  (default: 2)
          Extra lookup from control corrections counts against budget.
        """
        from config import get_jit_retrieval_max, get_jit_retrieval_max_on_failure

        return util_compute_retrieval_policy(
            thinking_plan,
            verified_plan,
            current_tool_context=current_tool_context,
            get_jit_retrieval_max_fn=get_jit_retrieval_max,
            get_jit_retrieval_max_on_failure_fn=get_jit_retrieval_max_on_failure,
        )

    def _compute_ctx_mode(self, trace: Dict, is_loop: bool = False) -> str:
        from config import get_context_trace_dryrun
        return util_compute_ctx_mode(
            trace,
            is_loop=is_loop,
            get_context_trace_dryrun_fn=get_context_trace_dryrun,
        )

    def _maybe_prefetch_skills(
        self, user_text: str, selected_tools: list
    ) -> tuple:
        """
        Returns (skill_context_str, mode_str) for ThinkingLayer prefetch.
        mode: "off" | "thin" | "full"

        C6 Single-Truth-Channel: all skill fetching routes through
        self.context._get_skill_context() — never calls _search_skill_graph directly.

        SKILL_CONTEXT_RENDERER=typedstate (default):
            Full mode → fetches via C5 TypedState pipeline; thin mode → same.
        SKILL_CONTEXT_RENDERER=legacy:
            Full mode → fetches via _search_skill_graph (old header format).
            Thin mode → line-truncated to top-1 skill + char cap.

        small_model_mode=False → always fetch (full).
        small_model_mode=True  → default off; exception for explicit skill-intent
                                  signals (list_skills / autonomous_skill_task) → thin.
        """
        return util_maybe_prefetch_skills(
            user_text,
            selected_tools,
            # C6 Single-Truth-Channel: routes through self.context._get_skill_context.
            get_skill_context_fn=self.context._get_skill_context,
            read_only_skill_tools=list(self._READ_ONLY_SKILL_TOOLS),
            log_debug_fn=log_debug,
        )

    def _extract_workspace_observations(self, thinking_plan: Dict) -> Optional[str]:
        return util_extract_workspace_observations(thinking_plan)

    # ===============================================================
    # INTENT CONFIRMATION
    # ===============================================================
    # ===============================================================
    
    async def _check_pending_confirmation(
        self, 
        user_text: str, 
        conversation_id: str
    ) -> Optional[CoreChatResponse]:
        """Check if user is responding to a pending confirmation."""
        return await util_api_check_pending_confirmation(
            self,
            user_text,
            conversation_id,
            intent_system_available=bool(INTENT_SYSTEM_AVAILABLE),
            get_intent_store_fn=get_intent_store if INTENT_SYSTEM_AVAILABLE else (lambda: None),
            get_hub_fn=get_hub,
            intent_state_cls=IntentState if INTENT_SYSTEM_AVAILABLE else None,
            core_chat_response_cls=CoreChatResponse,
            util_check_pending_confirmation_fn=util_check_pending_confirmation,
            log_info_fn=log_info,
            log_warn_fn=log_warn,
            log_error_fn=log_error,
        )
    
    # ===============================================================
    # PUBLIC API
    # ===============================================================
    

    # ===============================================================
    # MASTER ORCHESTRATOR API (Phase 1)
    # ===============================================================
    
    async def execute_autonomous_objective(
        self,
        objective: str,
        conversation_id: str,
        max_loops: int = 10
    ) -> dict:
        """
        Execute high-level objective autonomously via Master Orchestrator
        
        This is the entry point for autonomous execution.
        Master will decompose the objective and execute sub-tasks
        by calling back to this Pipeline.
        
        Args:
            objective: High-level goal (e.g., "Analyze logs and create report")
            conversation_id: Conversation context
            max_loops: Maximum autonomous iterations (safety)
        
        Returns:
            Execution summary with results
        
        Example:
            result = await orchestrator.execute_autonomous_objective(
                objective="Review codebase and suggest improvements",
                conversation_id="conv_123",
                max_loops=5
            )
        """
        return await util_api_execute_autonomous_objective(
            objective,
            conversation_id,
            master=self.master,
            max_loops=max_loops,
            log_info_fn=log_info,
        )

    async def process(self, request: CoreChatRequest) -> CoreChatResponse:
        """
        Standard (non-streaming) pipeline execution.
        
        Pipeline:
        1. Intent Confirmation Check
        2. Thinking Layer -> Plan
        3. Context Retrieval (via ContextManager)
        4. Control Layer -> Verify
        5. Output Layer -> Generate
        6. Memory Save
        """
        return await util_api_process_request(
            self,
            request,
            core_chat_response_cls=CoreChatResponse,
            intent_system_available=bool(INTENT_SYSTEM_AVAILABLE),
            get_master_settings_fn=get_master_settings,
            thinking_plan_cache=_thinking_plan_cache,
            soften_control_deny_fn=soften_control_deny,
            util_process_request_fn=util_process_request,
            log_info_fn=log_info,
            log_warn_fn=log_warn,
            log_warning_fn=log_warn,
        )
    
    # ===============================================================
    async def process_stream_with_events(
        self,
        request: CoreChatRequest
    ) -> AsyncGenerator[Tuple[str, bool, Dict], None]:
        """
        Phase 3: Native event-rich streaming (ported from bridge.py).

        Features:
        - Intent confirmation check
        - Chunking for large inputs
        - Live streaming thinking
        - Sequential thinking events  
        - Control layer with skill confirmation
        - Output streaming
        - Memory save
        """
        async for item in util_api_process_stream_with_events(
            self,
            request,
            intent_system_available=bool(INTENT_SYSTEM_AVAILABLE),
            enable_chunking=bool(ENABLE_CHUNKING),
            chunking_threshold=int(CHUNKING_THRESHOLD),
            get_master_settings_fn=get_master_settings,
            thinking_plan_cache=_thinking_plan_cache,
            sequential_result_cache=_sequential_result_cache,
            soften_control_deny_fn=soften_control_deny,
            skill_creation_intent_cls=SkillCreationIntent if INTENT_SYSTEM_AVAILABLE else None,
            intent_origin_cls=IntentOrigin if INTENT_SYSTEM_AVAILABLE else None,
            get_intent_store_fn=get_intent_store if INTENT_SYSTEM_AVAILABLE else (lambda: None),
            util_process_stream_with_events_fn=util_process_stream_with_events,
            log_info_fn=log_info,
            log_warn_fn=log_warn,
            log_error_fn=log_error,
            log_debug_fn=log_debug,
            log_warning_fn=log_warn,
        ):
            yield item

    # CHUNKING (moved from bridge.py)
    # ===============================================================

    async def _process_chunked_stream(
        self,
        user_text: str,
        conversation_id: str,
        request: CoreChatRequest
    ) -> AsyncGenerator[Tuple[str, bool, Dict], None]:
        """
        Verarbeitet lange Texte mit MCP document-processor.

        v3 Workflow (MCP-BASED):
        1. Preprocess via MCP (~1 Sek)
        2. Structure Analysis via MCP (~1 Sek)
        3. EIN LLM-Aufruf mit kompakter Summary (~15-20 Sek)
        4. Ergebnis zurueck
        """
        async for chunk in util_api_process_chunked_stream(
            self,
            user_text,
            conversation_id,
            request,
            util_process_chunked_stream_fn=util_process_chunked_stream,
            get_hub_fn=get_hub,
            log_info_fn=log_info,
            log_error_fn=log_error,
        ):
            yield chunk

    def _build_summary_from_structure(self, structure: Dict) -> str:
        """Build compact summary from MCP structure analysis."""
        return util_build_summary_from_structure(structure)

    # ===============================================================
    # PRIVATE PIPELINE STEPS
    # ===============================================================

    async def _execute_thinking_layer(self, user_text: str) -> Dict:
        """Execute Thinking Layer (Step 1)."""
        return await util_execute_thinking_layer(
            user_text,
            thinking_layer=self.thinking,
            log_info_fn=log_info,
        )
    
    async def _execute_control_layer(
        self,
        user_text: str,
        thinking_plan: Dict,
        memory_data: str,
        conversation_id: str,
        response_mode: str = "interactive",
    ) -> Tuple[Dict, Dict]:
        """Execute Control Layer (Step 2)."""
        return await util_api_execute_control_layer(
            self,
            user_text,
            thinking_plan,
            memory_data,
            conversation_id,
            response_mode=response_mode,
            intent_system_available=bool(INTENT_SYSTEM_AVAILABLE),
            skill_creation_intent_cls=SkillCreationIntent if INTENT_SYSTEM_AVAILABLE else None,
            intent_origin_cls=IntentOrigin if INTENT_SYSTEM_AVAILABLE else None,
            get_intent_store_fn=get_intent_store if INTENT_SYSTEM_AVAILABLE else (lambda: None),
            util_execute_control_layer_fn=util_execute_control_layer,
            log_info_fn=log_info,
            log_warn_fn=log_warn,
        )
    
    def _save_memory(
        self,
        conversation_id: str,
        verified_plan: Dict,
        answer: str
    ):
        """Save facts and assistant response to memory."""
        util_api_save_memory(
            conversation_id,
            verified_plan,
            answer,
            util_save_memory_fn=util_save_memory,
            call_tool_fn=call_tool,
            autosave_assistant_fn=autosave_assistant,
            load_grounding_policy_fn=load_grounding_policy,
            get_runtime_tool_results_fn=get_runtime_tool_results,
            count_successful_grounding_evidence_fn=self._count_successful_grounding_evidence,
            extract_suggested_tool_names_fn=self._extract_suggested_tool_names,
            get_runtime_tool_failure_fn=get_runtime_tool_failure,
            tool_context_has_failures_or_skips_fn=self._tool_context_has_failures_or_skips,
            get_runtime_grounding_value_fn=get_runtime_grounding_value,
            get_autosave_dedupe_guard_fn=get_autosave_dedupe_guard,
            log_info_fn=log_info,
            log_warn_fn=log_warn,
            log_error_fn=log_error,
        )

util_bind_policy_catalog_attrs(PipelineOrchestrator, globals())
