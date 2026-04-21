"""
config.models.llm
=================
Modell-Namen für die 3-Layer Pipeline (Thinking / Control / Output).

Alle Getter lesen zur Laufzeit aus dem settings-Store, damit Änderungen
über die Admin-UI ohne Neustart wirksam werden.

Backward-compat Konstanten (THINKING_MODEL, CONTROL_MODEL, OUTPUT_MODEL)
werden beim Import einmal eingefroren — für Code der noch keine Getter nutzt.
"""
import os

from config.infra.adapter import settings


def get_thinking_model() -> str:
    return settings.get("THINKING_MODEL", os.getenv("THINKING_MODEL", "ministral-3:8b"))


def get_control_model() -> str:
    return settings.get("CONTROL_MODEL", os.getenv("CONTROL_MODEL", "ministral-3:8b"))


def get_control_model_deep() -> str:
    """
    Optionales dediziertes Control-Modell für Deep-Mode-Anfragen.
    Fällt auf CONTROL_MODEL zurück wenn nicht gesetzt.
    """
    val = str(settings.get("CONTROL_MODEL_DEEP", os.getenv("CONTROL_MODEL_DEEP", ""))).strip()
    return val or get_control_model()


def get_output_model() -> str:
    return settings.get("OUTPUT_MODEL", os.getenv("OUTPUT_MODEL", "ministral-3:3b"))


# Backward-compat — beim Import eingefroren, Getter bevorzugen
THINKING_MODEL = get_thinking_model()
CONTROL_MODEL = get_control_model()
OUTPUT_MODEL = get_output_model()
