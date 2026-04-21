"""
config.pipeline.control_layer
==============================
Control-Layer Konfiguration — die Polizei-KI der Pipeline.

Steuert:
- Timeouts (interactive vs. deep mode)
- Prompt-Sizing (wie viel User-Text / Plan / Memory bekommt Control zu sehen)
- Endpoint-Overrides (optionaler dedizierter Control-Endpunkt)
- Layer-Toggles (Control komplett deaktivieren oder bei low-risk überspringen)
- Legacy-Validator-Service (standardmäßig deaktiviert, nur für Debugging)
"""
import os

from config.infra.adapter import settings


def get_control_timeout_interactive_s() -> int:
    """HTTP-Timeout für den ControlLayer im Interactive-Mode (Sekunden)."""
    val = int(settings.get(
        "CONTROL_TIMEOUT_INTERACTIVE_S",
        os.getenv("CONTROL_TIMEOUT_INTERACTIVE_S", "30"),
    ))
    return max(5, min(300, val))


def get_control_timeout_deep_s() -> int:
    """HTTP-Timeout für den ControlLayer im Deep-Mode (Sekunden)."""
    val = int(settings.get(
        "CONTROL_TIMEOUT_DEEP_S",
        os.getenv("CONTROL_TIMEOUT_DEEP_S", "60"),
    ))
    return max(5, min(600, val))


def get_control_corrections_memory_keys_max() -> int:
    """Hard-Cap für Correction-getriebene Extra-Memory-Lookups im ControlLayer."""
    try:
        val = int(settings.get(
            "CONTROL_CORRECTIONS_MEMORY_KEYS_MAX",
            os.getenv("CONTROL_CORRECTIONS_MEMORY_KEYS_MAX", "2"),
        ))
    except Exception:
        val = 2
    return max(0, min(10, val))


def get_control_prompt_user_chars() -> int:
    """Max. Zeichen des User-Requests die in den Control-Verify-Prompt injiziert werden."""
    try:
        val = int(settings.get(
            "CONTROL_PROMPT_USER_CHARS",
            os.getenv("CONTROL_PROMPT_USER_CHARS", "700"),
        ))
    except Exception:
        val = 700
    return max(120, min(8000, val))


def get_control_prompt_plan_chars() -> int:
    """Max. Zeichen für den kompakten serialisierten Thinking-Plan im Control-Prompt."""
    try:
        val = int(settings.get(
            "CONTROL_PROMPT_PLAN_CHARS",
            os.getenv("CONTROL_PROMPT_PLAN_CHARS", "2400"),
        ))
    except Exception:
        val = 2400
    return max(300, min(30000, val))


def get_control_prompt_memory_chars() -> int:
    """Max. Zeichen des Memory-Kontexts der in den Control-Verify-Prompt injiziert wird."""
    try:
        val = int(settings.get(
            "CONTROL_PROMPT_MEMORY_CHARS",
            os.getenv("CONTROL_PROMPT_MEMORY_CHARS", "1600"),
        ))
    except Exception:
        val = 1600
    return max(0, min(30000, val))


def get_control_endpoint_override(response_mode: str = "interactive") -> str:
    """
    Optionaler Endpoint-Override für den ControlLayer.
    Lookup-Reihenfolge:
      1. CONTROL_ENDPOINT_DEEP  (nur bei response_mode=deep)
      2. CONTROL_ENDPOINT
      3. Leerer String (deaktiviert)
    """
    mode = str(response_mode or "").strip().lower()
    if mode == "deep":
        deep_val = str(settings.get(
            "CONTROL_ENDPOINT_DEEP",
            os.getenv("CONTROL_ENDPOINT_DEEP", ""),
        )).strip()
        if deep_val:
            return deep_val.rstrip("/")

    val = str(settings.get(
        "CONTROL_ENDPOINT",
        os.getenv("CONTROL_ENDPOINT", ""),
    )).strip()
    return val.rstrip("/")


# Layer-Toggles — beim Import eingefroren
ENABLE_CONTROL_LAYER = settings.get(
    "ENABLE_CONTROL_LAYER",
    os.getenv("ENABLE_CONTROL_LAYER", "true").lower() == "true",
)

SKIP_CONTROL_ON_LOW_RISK = settings.get(
    "SKIP_CONTROL_ON_LOW_RISK",
    os.getenv("SKIP_CONTROL_ON_LOW_RISK", "false").lower() == "true",
)

# Legacy-Validator-Service
# Default false — der /ollama/chat-Validator ist vom Orchestrator isoliert.
# Bei aktivem ControlLayer verursacht doppelte Validation unvorhersehbare HARD FAILs.
# Nur für Debugging aktivieren.
ENABLE_VALIDATION = settings.get(
    "ENABLE_VALIDATION",
    os.getenv("ENABLE_VALIDATION", "false").lower() == "true",
)
VALIDATION_THRESHOLD = float(settings.get(
    "VALIDATION_THRESHOLD",
    os.getenv("VALIDATION_THRESHOLD", "0.70"),
))
VALIDATION_HARD_FAIL = settings.get(
    "VALIDATION_HARD_FAIL",
    os.getenv("VALIDATION_HARD_FAIL", "false").lower() == "true",
)
