"""
config.pipeline.query_budget
=============================
Query-Klassifikation & Response-Mode-Steuerung.

Bestimmt wie aufwändig eine Anfrage verarbeitet wird:
- Darf der ThinkingLayer übersprungen werden?
- Ist die Anfrage "interactive" oder "deep"?
- Wie viele Tools sind für einfache Factual-Turns erlaubt?

Der Tone-Override-Wert gehört hier rein, weil er ebenfalls auf dem
Classifier-Confidence-Signal basiert.
"""
import os

from config.infra.adapter import settings


def get_default_response_mode() -> str:
    """
    Laufzeit-Default für den Response-Mode:
      - interactive: niedrige Latenz, begrenzte Ausgabe
      - deep:        erlaubt schwere sequenzielle Analyse
    """
    mode = str(settings.get(
        "DEFAULT_RESPONSE_MODE",
        os.getenv("DEFAULT_RESPONSE_MODE", "interactive"),
    )).strip().lower()
    return mode if mode in {"interactive", "deep"} else "interactive"


def get_response_mode_sequential_threshold() -> int:
    """
    Sequenzielle Komplexitätsschwelle, ab der interactive-Mode
    sequenzielles Thinking zurückstellt.
    """
    val = int(settings.get(
        "RESPONSE_MODE_SEQUENTIAL_THRESHOLD",
        os.getenv("RESPONSE_MODE_SEQUENTIAL_THRESHOLD", "6"),
    ))
    return max(1, min(10, val))


def get_sequential_timeout_s() -> int:
    """Max. Laufzeit für einen nicht-stream sequenziellen Call (Sekunden)."""
    val = int(settings.get(
        "SEQUENTIAL_TIMEOUT_S",
        os.getenv("SEQUENTIAL_TIMEOUT_S", "25"),
    ))
    return max(5, min(300, val))


def get_query_budget_enable() -> bool:
    """Leichte Query-Vorklassifikation + Budget-Policy aktivieren."""
    return str(settings.get(
        "QUERY_BUDGET_ENABLE",
        os.getenv("QUERY_BUDGET_ENABLE", "true"),
    )).lower() == "true"


def get_query_budget_embedding_enable() -> bool:
    """Optionales Embedding-Refinement für unsichere Query-Klassifikation."""
    return str(settings.get(
        "QUERY_BUDGET_EMBEDDING_ENABLE",
        os.getenv("QUERY_BUDGET_EMBEDDING_ENABLE", "true"),
    )).lower() == "true"


def get_query_budget_skip_thinking_enable() -> bool:
    """
    Erlaubt dem Classifier, den ThinkingLayer bei einfachen Turns zu überspringen.
    Nur aktiv hinter einem hohen Confidence-Schwellenwert.
    """
    return str(settings.get(
        "QUERY_BUDGET_SKIP_THINKING_ENABLE",
        os.getenv("QUERY_BUDGET_SKIP_THINKING_ENABLE", "true"),
    )).lower() == "true"


def get_query_budget_skip_thinking_min_confidence() -> float:
    """Minimum Classifier-Confidence für Skip-Thinking-Kandidaten."""
    try:
        val = float(settings.get(
            "QUERY_BUDGET_SKIP_THINKING_MIN_CONFIDENCE",
            os.getenv("QUERY_BUDGET_SKIP_THINKING_MIN_CONFIDENCE", "0.90"),
        ))
    except Exception:
        val = 0.90
    return max(0.0, min(1.0, val))


def get_query_budget_max_tools_factual_low() -> int:
    """Tool-Cap für einfache Factual-Turns mit niedrigem Komplexitäts-Score."""
    try:
        val = int(settings.get(
            "QUERY_BUDGET_MAX_TOOLS_FACTUAL_LOW",
            os.getenv("QUERY_BUDGET_MAX_TOOLS_FACTUAL_LOW", "1"),
        ))
    except Exception:
        val = 1
    return max(0, min(5, val))


def get_tone_signal_override_confidence() -> float:
    """
    Minimum Classifier-Confidence um veraltete ThinkingLayer-Tone-Felder
    zu überschreiben.
    """
    try:
        val = float(settings.get(
            "TONE_SIGNAL_OVERRIDE_CONFIDENCE",
            os.getenv("TONE_SIGNAL_OVERRIDE_CONFIDENCE", "0.82"),
        ))
    except Exception:
        val = 0.82
    return max(0.0, min(1.0, val))
