"""
config
======
Modulares Konfigurations-Package für TRION.

Alle `import config` und `from config import X` Aufrufe im System
werden über diesen __init__.py aufgelöst — Rückwärtskompatibilität
ist vollständig gewährleistet.

Neue Module sollen direkt aus dem Sub-Package importieren:
  from config.infra import OLLAMA_BASE
  from config.models import get_thinking_model
  from config.pipeline import get_query_budget_enable

Sub-Packages:
  config.infra      → Infrastruktur: Endpoints, CORS, Pfade, Logging
  config.models     → LLM-Modelle & Provider
  config.pipeline   → Pipeline-Thresholds, Query-Budget, Layer-Steuerung
  config.output     → Output-Caps, Timeouts, Deep-Jobs
  config.autonomy   → Autonomie-Cron, Hardware-Guard
  config.context    → Chunking, Small-Model-Mode, JIT-Retrieval
  config.features   → Feature-Flags & laufende Migrationen
  config.digest     → Digest-Pipeline (Phase 8)
  config.skills     → Skill-Management, Secrets, Autosave-Dedupe
"""

# ── Infra ────────────────────────────────────────────────────────────────────
from config.infra.adapter import settings  # noqa: F401
from config.infra.cors import (  # noqa: F401
    ALLOW_ORIGINS,
    ALLOWED_ORIGINS,
    ENABLE_CORS,
)
from config.infra.services import (  # noqa: F401
    OLLAMA_BASE,
    MCP_BASE,
    VALIDATOR_URL,
    DB_PATH,
)
from config.infra.paths import (  # noqa: F401
    WORKSPACE_BASE,
    LOG_LEVEL,
)

# ── Models ───────────────────────────────────────────────────────────────────
from config.models.llm import (  # noqa: F401
    get_thinking_model,
    get_control_model,
    get_control_model_deep,
    get_output_model,
    THINKING_MODEL,
    CONTROL_MODEL,
    OUTPUT_MODEL,
)
from config.models.providers import (  # noqa: F401
    get_thinking_provider,
    get_control_provider,
    get_output_provider,
    _normalize_provider,
)
from config.models.embedding import (  # noqa: F401
    get_embedding_model,
    get_embedding_execution_mode,
    get_embedding_fallback_policy,
    get_embedding_gpu_endpoint,
    get_embedding_cpu_endpoint,
    get_embedding_endpoint_mode,
    get_embedding_runtime_policy,
    EMBEDDING_MODEL,
)
from config.models.tool_selector import (  # noqa: F401
    get_tool_selector_model,
    get_tool_selector_candidate_limit,
    get_tool_selector_min_similarity,
    TOOL_SELECTOR_MODEL,
    TOOL_SELECTOR_CANDIDATE_LIMIT,
    TOOL_SELECTOR_MIN_SIMILARITY,
    ENABLE_TOOL_SELECTOR,
)

# ── Pipeline ─────────────────────────────────────────────────────────────────
from config.pipeline.query_budget import (  # noqa: F401
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
from config.pipeline.domain_router import (  # noqa: F401
    get_domain_router_enable,
    get_domain_router_embedding_enable,
    get_domain_router_lock_min_confidence,
    get_policy_conflict_resolver_enable,
    get_policy_conflict_resolver_rollout_pct,
    get_output_tool_injection_mode,
    get_output_tool_prompt_limit,
)
from config.pipeline.grounding import (  # noqa: F401
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
from config.pipeline.control_layer import (  # noqa: F401
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
from config.pipeline.loop_engine import (  # noqa: F401
    get_loop_engine_trigger_complexity,
    get_loop_engine_min_tools,
    get_loop_engine_output_char_cap,
    get_loop_engine_max_predict,
)

# ── Output ───────────────────────────────────────────────────────────────────
from config.output.char_limits import (  # noqa: F401
    get_output_char_cap_interactive,
    get_output_char_cap_interactive_long,
    get_output_char_cap_interactive_analytical,
    get_output_char_cap_deep,
    get_output_char_target_interactive,
    get_output_char_target_interactive_analytical,
    get_output_char_target_deep,
)
from config.output.streaming import (  # noqa: F401
    get_output_timeout_interactive_s,
    get_output_timeout_deep_s,
    get_output_stream_postcheck_mode,
)
from config.output.jobs import (  # noqa: F401
    get_deep_job_timeout_s,
    get_deep_job_max_concurrency,
    get_autonomy_job_timeout_s,
    get_autonomy_job_max_concurrency,
)

# ── Autonomy ─────────────────────────────────────────────────────────────────
from config.autonomy.scheduler import (  # noqa: F401
    get_autonomy_cron_state_path,
    get_autonomy_cron_tick_s,
    get_autonomy_cron_max_concurrency,
    get_autonomy_cron_max_jobs,
    get_autonomy_cron_max_jobs_per_conversation,
    get_autonomy_cron_min_interval_s,
    get_autonomy_cron_max_pending_runs,
    get_autonomy_cron_max_pending_runs_per_job,
    get_autonomy_cron_manual_run_cooldown_s,
)
from config.autonomy.trion_policy import (  # noqa: F401
    get_autonomy_cron_trion_safe_mode,
    get_autonomy_cron_trion_min_interval_s,
    get_autonomy_cron_trion_max_loops,
    get_autonomy_cron_trion_require_approval_for_risky,
)
from config.autonomy.hardware_guard import (  # noqa: F401
    get_autonomy_cron_hardware_guard_enabled,
    get_autonomy_cron_hardware_cpu_max_percent,
    get_autonomy_cron_hardware_mem_max_percent,
)

# ── Context ──────────────────────────────────────────────────────────────────
from config.context.chunking import (  # noqa: F401
    CHUNKING_THRESHOLD,
    CHUNK_MAX_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    ENABLE_CHUNKING,
)
from config.context.small_model import (  # noqa: F401
    get_small_model_mode,
    get_small_model_now_max,
    get_small_model_rules_max,
    get_small_model_next_max,
    get_small_model_char_cap,
    get_small_model_skill_prefetch_policy,
    get_small_model_skill_prefetch_thin_cap,
    get_small_model_detection_rules_policy,
    get_small_model_detection_rules_thin_lines,
    get_small_model_detection_rules_thin_chars,
    get_small_model_final_cap,
    get_small_model_tool_ctx_cap,
    SMALL_MODEL_MODE,
    SMALL_MODEL_NOW_MAX,
    SMALL_MODEL_RULES_MAX,
    SMALL_MODEL_NEXT_MAX,
    SMALL_MODEL_CHAR_CAP,
    SMALL_MODEL_SKILL_PREFETCH_POLICY,
    SMALL_MODEL_SKILL_PREFETCH_THIN_CAP,
    SMALL_MODEL_DETECTION_RULES_POLICY,
)
from config.context.retrieval import (  # noqa: F401
    get_jit_retrieval_max,
    get_jit_retrieval_max_on_failure,
    get_context_trace_dryrun,
    JIT_RETRIEVAL_MAX,
    JIT_RETRIEVAL_MAX_ON_FAILURE,
    CONTEXT_TRACE_DRYRUN,
)

# ── Features ─────────────────────────────────────────────────────────────────
from config.features.typedstate import (  # noqa: F401
    get_typedstate_mode,
    get_typedstate_enable_small_only,
    get_typedstate_csv_path,
    get_typedstate_csv_enable,
    get_typedstate_csv_jit_only,
    get_typedstate_skills_mode,
    TYPEDSTATE_MODE,
    TYPEDSTATE_ENABLE_SMALL_ONLY,
)
from config.features.security import (  # noqa: F401
    get_signature_verify_mode,
    SIGNATURE_VERIFY_MODE,
)

# ── Digest ───────────────────────────────────────────────────────────────────
from config.digest.schedule import (  # noqa: F401
    get_digest_enable,
    get_digest_daily_enable,
    get_digest_weekly_enable,
    get_digest_archive_enable,
    get_digest_tz,
    get_digest_run_mode,
    get_digest_catchup_max_days,
)
from config.digest.storage import (  # noqa: F401
    get_digest_store_path,
    get_digest_state_path,
    get_digest_lock_path,
    get_digest_lock_timeout_s,
)
from config.digest.policy import (  # noqa: F401
    get_digest_min_events_daily,
    get_digest_min_daily_per_week,
    get_digest_filters_enable,
    get_digest_dedupe_include_conv,
    get_jit_window_time_reference_h,
    get_jit_window_fact_recall_h,
    get_jit_window_remember_h,
    get_digest_ui_enable,
    get_digest_runtime_api_v2,
    get_digest_jit_warn_on_disabled,
    get_digest_key_version,
)

# ── Skills ───────────────────────────────────────────────────────────────────
from config.skills.registry import (  # noqa: F401
    get_skill_graph_reconcile,
    get_skill_key_mode,
    get_skill_control_authority,
    get_skill_package_install_mode,
    get_skill_discovery_enable,
    get_skill_auto_create_on_low_risk,
    get_autosave_dedupe_enable,
    get_autosave_dedupe_window_s,
    get_autosave_dedupe_max_entries,
)
from config.skills.rendering import (  # noqa: F401
    get_skill_context_renderer,
    get_skill_selection_mode,
    get_skill_selection_top_k,
    get_skill_selection_char_cap,
)
from config.skills.secrets import (  # noqa: F401
    get_skill_secret_enforcement,
    get_secret_resolve_token,
    get_secret_rate_limit,
    get_secret_resolve_miss_ttl_s,
    get_secret_resolve_not_found_ttl_s,
)
