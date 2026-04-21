"""
config.context
==============
Kontext-Aufbau & Komprimierung — wie viel Kontext gebaut wird und in welcher Form.

Module:
  chunking    → Long-Context Chunking (Threshold, Max-Tokens, Overlap, Toggle)
  small_model → Small-Model-Mode: Compact-Context für kleine Modelle
  retrieval   → JIT-Retrieval-Budget & Context-Trace-Dryrun

Re-Exports für bequemen Zugriff via `from config.context import ...`:
"""
from config.context.chunking import (
    CHUNKING_THRESHOLD,
    CHUNK_MAX_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    ENABLE_CHUNKING,
)

from config.context.small_model import (
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

from config.context.retrieval import (
    get_jit_retrieval_max,
    get_jit_retrieval_max_on_failure,
    get_context_trace_dryrun,
    JIT_RETRIEVAL_MAX,
    JIT_RETRIEVAL_MAX_ON_FAILURE,
    CONTEXT_TRACE_DRYRUN,
)

__all__ = [
    # chunking
    "CHUNKING_THRESHOLD", "CHUNK_MAX_TOKENS", "CHUNK_OVERLAP_TOKENS", "ENABLE_CHUNKING",
    # small_model
    "get_small_model_mode", "get_small_model_now_max", "get_small_model_rules_max",
    "get_small_model_next_max", "get_small_model_char_cap",
    "get_small_model_skill_prefetch_policy", "get_small_model_skill_prefetch_thin_cap",
    "get_small_model_detection_rules_policy", "get_small_model_detection_rules_thin_lines",
    "get_small_model_detection_rules_thin_chars", "get_small_model_final_cap",
    "get_small_model_tool_ctx_cap",
    "SMALL_MODEL_MODE", "SMALL_MODEL_NOW_MAX", "SMALL_MODEL_RULES_MAX", "SMALL_MODEL_NEXT_MAX",
    "SMALL_MODEL_CHAR_CAP", "SMALL_MODEL_SKILL_PREFETCH_POLICY",
    "SMALL_MODEL_SKILL_PREFETCH_THIN_CAP", "SMALL_MODEL_DETECTION_RULES_POLICY",
    # retrieval
    "get_jit_retrieval_max", "get_jit_retrieval_max_on_failure", "get_context_trace_dryrun",
    "JIT_RETRIEVAL_MAX", "JIT_RETRIEVAL_MAX_ON_FAILURE", "CONTEXT_TRACE_DRYRUN",
]
