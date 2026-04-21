"""
config.models.tool_selector
============================
Konfiguration des Tool-Selectors (Layer 0 — semantisches Vorfiltern).

Der Tool-Selector ist ein eigenständiges Lightweight-Modell (z.B. qwen2.5:1.5b),
das vor dem Thinking-Layer aus allen verfügbaren Tools die relevantesten
Kandidaten herausfiltert, um Prompt-Bloat zu vermeiden.

TOOL_SELECTOR_CANDIDATE_LIMIT : Max. Anzahl Kandidaten die weitergereicht werden.
TOOL_SELECTOR_MIN_SIMILARITY  : Minimum Ähnlichkeits-Score (0.0–0.95).
ENABLE_TOOL_SELECTOR           : Master-Toggle zum Deaktivieren des gesamten Selektors.
"""
import os

from config.infra.adapter import settings


def get_tool_selector_model() -> str:
    return settings.get(
        "TOOL_SELECTOR_MODEL",
        os.getenv("TOOL_SELECTOR_MODEL", "qwen2.5:1.5b-instruct"),
    )


def get_tool_selector_candidate_limit() -> int:
    """
    Max. Kandidaten-Anzahl aus dem semantischen Vorfilter.
    Begrenzt auf 3–25 um Prompt-Bloat zu vermeiden.
    """
    val = int(settings.get(
        "TOOL_SELECTOR_CANDIDATE_LIMIT",
        os.getenv("TOOL_SELECTOR_CANDIDATE_LIMIT", "10"),
    ))
    return max(3, min(25, val))


def get_tool_selector_min_similarity() -> float:
    """
    Minimaler Ähnlichkeits-Score für den semantischen Vorfilter.
    Höhere Werte reduzieren Over-Selection-Rauschen.
    """
    try:
        val = float(settings.get(
            "TOOL_SELECTOR_MIN_SIMILARITY",
            os.getenv("TOOL_SELECTOR_MIN_SIMILARITY", "0.45"),
        ))
    except Exception:
        val = 0.45
    return max(0.0, min(0.95, val))


# Backward-compat — beim Import eingefroren, Getter bevorzugen
TOOL_SELECTOR_MODEL = get_tool_selector_model()
TOOL_SELECTOR_CANDIDATE_LIMIT = get_tool_selector_candidate_limit()
TOOL_SELECTOR_MIN_SIMILARITY = get_tool_selector_min_similarity()
ENABLE_TOOL_SELECTOR = settings.get(
    "ENABLE_TOOL_SELECTOR",
    os.getenv("ENABLE_TOOL_SELECTOR", "true").lower() == "true",
)
