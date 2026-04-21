"""
config.output.char_limits
==========================
Char-Caps (Hard-Limits) & Soft-Targets für alle Output-Modi.

Hard-Caps  : Absolute Zeichengrenzen — Antworten werden abgeschnitten wenn überschritten.
             0 deaktiviert den jeweiligen Cap.
Soft-Targets: Prompt-Empfehlungen an das LLM — darf überschritten werden, hält aber
              die Ausgabe in der Regel kürzer. Wird automatisch unter den Hard-Cap gedrückt.

Modi:
  interactive           → Standard-Modus, niedrige Latenz
  interactive_long      → Entspannter Cap wenn length_hint=long gesetzt
  interactive_analytical→ Engerer Cap für analytische Turns (Tabellen, Code-Reviews)
  deep                  → Kein Latenz-Ziel, maximale Ausgabe erlaubt
"""
import os

from config.infra.adapter import settings


def get_output_char_cap_interactive() -> int:
    """Hard-Cap im Interactive-Mode (0 deaktiviert)."""
    val = int(settings.get(
        "OUTPUT_CHAR_CAP_INTERACTIVE",
        os.getenv("OUTPUT_CHAR_CAP_INTERACTIVE", "2600"),
    ))
    return max(0, min(50000, val))


def get_output_char_cap_interactive_long() -> int:
    """Entspannter Hard-Cap wenn length_hint=long im Interactive-Mode."""
    val = int(settings.get(
        "OUTPUT_CHAR_CAP_INTERACTIVE_LONG",
        os.getenv("OUTPUT_CHAR_CAP_INTERACTIVE_LONG", "3600"),
    ))
    return max(400, min(50000, val))


def get_output_char_cap_interactive_analytical() -> int:
    """Engerer Hard-Cap für analytische Turns im Interactive-Mode."""
    val = int(settings.get(
        "OUTPUT_CHAR_CAP_INTERACTIVE_ANALYTICAL",
        os.getenv("OUTPUT_CHAR_CAP_INTERACTIVE_ANALYTICAL", "1400"),
    ))
    return max(300, min(50000, val))


def get_output_char_cap_deep() -> int:
    """Hard-Cap im Deep-Mode (0 deaktiviert)."""
    val = int(settings.get(
        "OUTPUT_CHAR_CAP_DEEP",
        os.getenv("OUTPUT_CHAR_CAP_DEEP", "12000"),
    ))
    return max(0, min(200000, val))


def get_output_char_target_interactive() -> int:
    """
    Soft-Target für Interactive-Mode (Prompt-Empfehlung).
    Wird automatisch unter den Hard-Cap gedrückt wenn dieser aktiv ist.
    """
    val = int(settings.get(
        "OUTPUT_CHAR_TARGET_INTERACTIVE",
        os.getenv("OUTPUT_CHAR_TARGET_INTERACTIVE", "1600"),
    ))
    hard_cap = get_output_char_cap_interactive()
    if hard_cap > 0:
        val = min(val, max(200, hard_cap - 120))
    return max(200, min(50000, val))


def get_output_char_target_interactive_analytical() -> int:
    """Soft-Target für analytische Turns im Interactive-Mode."""
    val = int(settings.get(
        "OUTPUT_CHAR_TARGET_INTERACTIVE_ANALYTICAL",
        os.getenv("OUTPUT_CHAR_TARGET_INTERACTIVE_ANALYTICAL", "1000"),
    ))
    hard_cap = get_output_char_cap_interactive_analytical()
    if hard_cap > 0:
        val = min(val, max(180, hard_cap - 120))
    return max(180, min(50000, val))


def get_output_char_target_deep() -> int:
    """Soft-Target für Deep-Mode (Prompt-Empfehlung)."""
    val = int(settings.get(
        "OUTPUT_CHAR_TARGET_DEEP",
        os.getenv("OUTPUT_CHAR_TARGET_DEEP", "9000"),
    ))
    hard_cap = get_output_char_cap_deep()
    if hard_cap > 0:
        val = min(val, max(400, hard_cap - 200))
    return max(400, min(200000, val))
