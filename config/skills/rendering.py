"""
config.skills.rendering
========================
Skill-Kontext-Rendering & Selektion — wie Skills dem LLM präsentiert werden.

Steuert den "Output-Layer" des Skill-Systems:
- Welcher Renderer wird genutzt? (TypedState vs. Legacy)
- Wie viele Skills werden selektiert? (budgeted vs. legacy)
- Wie groß ist das Char-Budget für den Skill-Kontext?

Renderer-Werte   : typedstate | legacy
Selection-Modi   : budgeted | legacy
"""
import os

from config.infra.adapter import settings


def get_skill_context_renderer() -> str:
    """
    Single-Truth-Channel-Renderer für Skill-Kontext:
      typedstate → TypedState-Rendering (default)
      legacy     → Legacy-Renderer (Rollback)
    """
    return settings.get(
        "SKILL_CONTEXT_RENDERER",
        os.getenv("SKILL_CONTEXT_RENDERER", "typedstate"),
    ).lower()


def get_skill_selection_mode() -> str:
    """
    Skill-Selektions-Strategie:
      budgeted → Char-Budget-gesteuerte Selektion (default)
      legacy   → Legacy-Selektion (Rollback)
    """
    mode = settings.get(
        "SKILL_SELECTION_MODE",
        os.getenv("SKILL_SELECTION_MODE", "budgeted"),
    ).lower()
    return mode if mode in {"budgeted", "legacy"} else "budgeted"


def get_skill_selection_top_k() -> int:
    """Obere Schranke für selektierte Skills vor finalem Rendering. Default: 10."""
    val = int(settings.get(
        "SKILL_SELECTION_TOP_K",
        os.getenv("SKILL_SELECTION_TOP_K", "10"),
    ))
    return max(1, min(50, val))


def get_skill_selection_char_cap() -> int:
    """Char-Budget für TypedState Skill-Kontext-Rendering. Default: 2000."""
    val = int(settings.get(
        "SKILL_SELECTION_CHAR_CAP",
        os.getenv("SKILL_SELECTION_CHAR_CAP", "2000"),
    ))
    return max(200, min(8000, val))
