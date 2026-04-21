"""
config.models
=============
LLM-Modelle, Provider & Embedding-Konfiguration.

Module:
  llm           → Modell-Namen für Thinking / Control / Output
  providers     → Provider-Auflösung (ollama / openai / anthropic)
  embedding     → Embedding-Modell, Runtime-Policy, GPU/CPU-Routing
  tool_selector → Tool-Selector Modell & Schwellenwerte

Re-Exports für bequemen Zugriff via `from config.models import ...`:
"""
from config.models.llm import (
    get_thinking_model,
    get_control_model,
    get_control_model_deep,
    get_output_model,
    THINKING_MODEL,
    CONTROL_MODEL,
    OUTPUT_MODEL,
)

from config.models.providers import (
    get_output_provider,
    get_thinking_provider,
    get_control_provider,
    _normalize_provider,
)

from config.models.embedding import (
    get_embedding_model,
    get_embedding_execution_mode,
    get_embedding_fallback_policy,
    get_embedding_gpu_endpoint,
    get_embedding_cpu_endpoint,
    get_embedding_endpoint_mode,
    get_embedding_runtime_policy,
    EMBEDDING_MODEL,
)

from config.models.tool_selector import (
    get_tool_selector_model,
    get_tool_selector_candidate_limit,
    get_tool_selector_min_similarity,
    TOOL_SELECTOR_MODEL,
    TOOL_SELECTOR_CANDIDATE_LIMIT,
    TOOL_SELECTOR_MIN_SIMILARITY,
    ENABLE_TOOL_SELECTOR,
)

__all__ = [
    # llm
    "get_thinking_model", "get_control_model", "get_control_model_deep", "get_output_model",
    "THINKING_MODEL", "CONTROL_MODEL", "OUTPUT_MODEL",
    # providers
    "get_output_provider", "get_thinking_provider", "get_control_provider", "_normalize_provider",
    # embedding
    "get_embedding_model", "get_embedding_execution_mode", "get_embedding_fallback_policy",
    "get_embedding_gpu_endpoint", "get_embedding_cpu_endpoint", "get_embedding_endpoint_mode",
    "get_embedding_runtime_policy", "EMBEDDING_MODEL",
    # tool_selector
    "get_tool_selector_model", "get_tool_selector_candidate_limit", "get_tool_selector_min_similarity",
    "TOOL_SELECTOR_MODEL", "TOOL_SELECTOR_CANDIDATE_LIMIT", "TOOL_SELECTOR_MIN_SIMILARITY",
    "ENABLE_TOOL_SELECTOR",
]
