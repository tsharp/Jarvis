"""
config.models.embedding
=======================
Embedding-Modell & Routing-Konfiguration.

Unterstützt Single- und Dual-Endpoint-Modus (separate GPU/CPU-Endpunkte).
Die Runtime-Policy steuert, ob der Embedding-Prozess GPU oder CPU bevorzugt
und wie bei Ausfall verfahren wird.

Runtime-Policy Werte : auto | prefer_gpu | cpu_only
Fallback-Policy Werte: best_effort | strict
Endpoint-Mode Werte  : single | dual
"""
import os

from config.infra.adapter import settings


def get_embedding_model() -> str:
    return settings.get(
        "EMBEDDING_MODEL",
        os.getenv("EMBEDDING_MODEL", "hellord/mxbai-embed-large-v1:f16"),
    )


def get_embedding_execution_mode() -> str:
    """auto | prefer_gpu | cpu_only (default: auto)"""
    return settings.get(
        "EMBEDDING_EXECUTION_MODE",
        os.getenv("EMBEDDING_EXECUTION_MODE", "auto"),
    )


def get_embedding_fallback_policy() -> str:
    """best_effort | strict (default: best_effort)"""
    return settings.get(
        "EMBEDDING_FALLBACK_POLICY",
        os.getenv("EMBEDDING_FALLBACK_POLICY", "best_effort"),
    )


def get_embedding_gpu_endpoint() -> str:
    """Optionaler dedizierter GPU-Ollama-Endpunkt, z.B. http://ollama-gpu:11434"""
    return settings.get(
        "EMBEDDING_GPU_ENDPOINT",
        os.getenv("EMBEDDING_GPU_ENDPOINT", ""),
    )


def get_embedding_cpu_endpoint() -> str:
    """Optionaler dedizierter CPU-Ollama-Endpunkt, z.B. http://ollama-cpu:11434"""
    return settings.get(
        "EMBEDDING_CPU_ENDPOINT",
        os.getenv("EMBEDDING_CPU_ENDPOINT", ""),
    )


def get_embedding_endpoint_mode() -> str:
    """single | dual (default: single)"""
    return settings.get(
        "EMBEDDING_ENDPOINT_MODE",
        os.getenv("EMBEDDING_ENDPOINT_MODE", "single"),
    )


def get_embedding_runtime_policy() -> str:
    """
    Kanonische Embedding-Runtime-Policy: auto | prefer_gpu | cpu_only (default: auto).

    Liest zuerst den persistierten Key 'embedding_runtime_policy' aus dem Settings-Store,
    fällt dann auf EMBEDDING_EXECUTION_MODE zurück (Rückwärtskompatibilität).
    """
    persisted = settings.get("embedding_runtime_policy", "")
    if persisted:
        return str(persisted).strip().lower()
    return get_embedding_execution_mode()


# Backward-compat — beim Import eingefroren, Getter bevorzugen
EMBEDDING_MODEL = get_embedding_model()
