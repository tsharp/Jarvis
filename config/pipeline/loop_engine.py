"""
config.pipeline.loop_engine
============================
Loop-Engine Schwellenwerte — wann und wie läuft der Task-Loop.

Der LoopEngine wird aktiviert wenn eine Anfrage eine hohe sequenzielle
Komplexität hat und mindestens N Tools vorschlägt. Er hat eigene
Output-Caps und Token-Budgets unabhängig vom normalen Output-Layer.
"""
import os

from config.infra.adapter import settings


def get_loop_engine_trigger_complexity() -> int:
    """
    Minimale sequenzielle Komplexität um den LoopEngine zu aktivieren.
    Skala 1–10, Default 8.
    """
    val = int(settings.get(
        "LOOP_ENGINE_TRIGGER_COMPLEXITY",
        os.getenv("LOOP_ENGINE_TRIGGER_COMPLEXITY", "8"),
    ))
    return max(1, min(10, val))


def get_loop_engine_min_tools() -> int:
    """Minimale Anzahl vorgeschlagener Tools bevor der LoopEngine starten darf."""
    val = int(settings.get(
        "LOOP_ENGINE_MIN_TOOLS",
        os.getenv("LOOP_ENGINE_MIN_TOOLS", "1"),
    ))
    return max(0, min(10, val))


def get_loop_engine_output_char_cap() -> int:
    """Hard-Output-Char-Cap für LoopEngine-Antworten (0 deaktiviert)."""
    val = int(settings.get(
        "LOOP_ENGINE_OUTPUT_CHAR_CAP",
        os.getenv("LOOP_ENGINE_OUTPUT_CHAR_CAP", "2400"),
    ))
    return max(0, min(200000, val))


def get_loop_engine_max_predict() -> int:
    """Max. Token-Prediction-Budget pro LoopEngine-Modell-Runde (0 deaktiviert)."""
    val = int(settings.get(
        "LOOP_ENGINE_MAX_PREDICT",
        os.getenv("LOOP_ENGINE_MAX_PREDICT", "700"),
    ))
    return max(0, min(8192, val))
