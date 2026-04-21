"""
config.pipeline
===============
Pipeline-Steuerung & Laufzeit-Thresholds — das Orchestrierungs-Wissen.

Module:
  query_budget   → Query-Klassifikation, Response-Mode, Tone-Override
  domain_router  → Domain-Routing, Policy-Conflict-Resolver, Tool-Injection
  grounding      → Grounding-Recovery, Memory-Retrieval, Followup-Reuse
  control_layer  → Control-Timeouts, Prompt-Sizing, Layer-Toggles, Validation
  loop_engine    → Loop-Engine Trigger, Min-Tools, Char-Cap, Token-Budget

Re-Exports für bequemen Zugriff via `from config.pipeline import ...`:
"""
from config.pipeline.query_budget import (
    get_default_response_mode,
    get_response_mode_sequential_threshold,
    get_sequential_timeout_s,
    get_query_budget_enable,
    get_query_budget_embedding_enable,
    get_query_budget_skip_thinking_enable,
    get_query_budget_skip_thinking_min_confidence,
    get_query_budget_max_tools_factual_low,
    get_tone_signal_override_confidence,
)

from config.pipeline.domain_router import (
    get_domain_router_enable,
    get_domain_router_embedding_enable,
    get_domain_router_lock_min_confidence,
    get_policy_conflict_resolver_enable,
    get_policy_conflict_resolver_rollout_pct,
    get_output_tool_injection_mode,
    get_output_tool_prompt_limit,
)

from config.pipeline.grounding import (
    get_grounding_auto_recovery_enable,
    get_grounding_auto_recovery_timeout_s,
    get_grounding_auto_recovery_whitelist,
    get_followup_tool_reuse_enable,
    get_followup_tool_reuse_ttl_turns,
    get_followup_tool_reuse_ttl_s,
    get_daily_context_followup_enable,
    get_context_memory_fallback_recall_only_enable,
    get_context_memory_fallback_recall_only_rollout_pct,
    get_memory_lookup_timeout_s,
    get_memory_keys_max_per_request,
    get_context_retrieval_budget_s,
    get_effective_context_guardrail_chars,
)

from config.pipeline.control_layer import (
    get_control_timeout_interactive_s,
    get_control_timeout_deep_s,
    get_control_corrections_memory_keys_max,
    get_control_prompt_user_chars,
    get_control_prompt_plan_chars,
    get_control_prompt_memory_chars,
    get_control_endpoint_override,
    ENABLE_CONTROL_LAYER,
    SKIP_CONTROL_ON_LOW_RISK,
    ENABLE_VALIDATION,
    VALIDATION_THRESHOLD,
    VALIDATION_HARD_FAIL,
)

from config.pipeline.loop_engine import (
    get_loop_engine_trigger_complexity,
    get_loop_engine_min_tools,
    get_loop_engine_output_char_cap,
    get_loop_engine_max_predict,
)

__all__ = [
    # query_budget
    "get_default_response_mode", "get_response_mode_sequential_threshold",
    "get_sequential_timeout_s", "get_query_budget_enable",
    "get_query_budget_embedding_enable", "get_query_budget_skip_thinking_enable",
    "get_query_budget_skip_thinking_min_confidence", "get_query_budget_max_tools_factual_low",
    "get_tone_signal_override_confidence",
    # domain_router
    "get_domain_router_enable", "get_domain_router_embedding_enable",
    "get_domain_router_lock_min_confidence", "get_policy_conflict_resolver_enable",
    "get_policy_conflict_resolver_rollout_pct", "get_output_tool_injection_mode",
    "get_output_tool_prompt_limit",
    # grounding
    "get_grounding_auto_recovery_enable", "get_grounding_auto_recovery_timeout_s",
    "get_grounding_auto_recovery_whitelist", "get_followup_tool_reuse_enable",
    "get_followup_tool_reuse_ttl_turns", "get_followup_tool_reuse_ttl_s",
    "get_daily_context_followup_enable", "get_context_memory_fallback_recall_only_enable",
    "get_context_memory_fallback_recall_only_rollout_pct", "get_memory_lookup_timeout_s",
    "get_memory_keys_max_per_request", "get_context_retrieval_budget_s",
    "get_effective_context_guardrail_chars",
    # control_layer
    "get_control_timeout_interactive_s", "get_control_timeout_deep_s",
    "get_control_corrections_memory_keys_max", "get_control_prompt_user_chars",
    "get_control_prompt_plan_chars", "get_control_prompt_memory_chars",
    "get_control_endpoint_override", "ENABLE_CONTROL_LAYER", "SKIP_CONTROL_ON_LOW_RISK",
    "ENABLE_VALIDATION", "VALIDATION_THRESHOLD", "VALIDATION_HARD_FAIL",
    # loop_engine
    "get_loop_engine_trigger_complexity", "get_loop_engine_min_tools",
    "get_loop_engine_output_char_cap", "get_loop_engine_max_predict",
]
