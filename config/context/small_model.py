"""
config.context.small_model
===========================
Small-Model-Mode — Compact-Context für kleine / speicherbeschränkte Modelle.

Wenn SMALL_MODEL_MODE aktiv ist, wird der Kontext radikal komprimiert:
- Section-Limits (NOW / RULES / NEXT) begrenzen wie viele Einträge injiziert werden.
- Ein harter Char-Cap (1800–2200) schneidet den Gesamtkontext ab.
- Skill-Prefetch und Detection-Rules werden auf "thin" oder "off" gedrosselt.
- Finale Caps (final_cap, tool_ctx_cap) verhindern Overflow nach allen Appends.

Alle Konstanten werden beim Import eingefroren (Backward-Compat).
Getter bevorzugen — sie lesen zur Laufzeit aus dem Settings-Store.

Skill-Prefetch-Policy  : off | thin
Detection-Rules-Policy : off | thin | full
"""
import os

from config.infra.adapter import settings


def get_small_model_mode() -> bool:
    """Master-Toggle: Compact-Context-Injection für kleine Modelle aktivieren."""
    return settings.get(
        "SMALL_MODEL_MODE",
        os.getenv("SMALL_MODEL_MODE", "false"),
    ).lower() == "true"


def get_small_model_now_max() -> int:
    """Max. Einträge im NOW-Abschnitt des Compact-Kontexts."""
    return int(settings.get("SMALL_MODEL_NOW_MAX", os.getenv("SMALL_MODEL_NOW_MAX", "5")))


def get_small_model_rules_max() -> int:
    """Max. Einträge im RULES-Abschnitt des Compact-Kontexts."""
    return int(settings.get("SMALL_MODEL_RULES_MAX", os.getenv("SMALL_MODEL_RULES_MAX", "3")))


def get_small_model_next_max() -> int:
    """Max. Einträge im NEXT-Abschnitt des Compact-Kontexts."""
    return int(settings.get("SMALL_MODEL_NEXT_MAX", os.getenv("SMALL_MODEL_NEXT_MAX", "2")))


def get_small_model_char_cap() -> int:
    """
    Hard-Char-Cap für den effektiven Kontext im Small-Mode.
    Erlaubtes Band: 1800–2200 — Werte außerhalb werden geclamped.
    """
    val = int(settings.get("SMALL_MODEL_CHAR_CAP", os.getenv("SMALL_MODEL_CHAR_CAP", "2000")))
    return max(1800, min(2200, val))


def get_small_model_skill_prefetch_policy() -> str:
    """
    Skill-Prefetch-Policy im Small-Mode:
      off  → kein Skill-Kontext vor ThinkingLayer (default)
      thin → nur bei explizitem Skill-Intent-Signal, gedeckelt auf thin_cap Zeichen
    """
    return settings.get(
        "SMALL_MODEL_SKILL_PREFETCH_POLICY",
        os.getenv("SMALL_MODEL_SKILL_PREFETCH_POLICY", "off"),
    ).lower()


def get_small_model_skill_prefetch_thin_cap() -> int:
    """Char-Budget für Thin-Skill-Prefetch (entspricht ca. Top-1-Skill)."""
    return int(settings.get(
        "SMALL_MODEL_SKILL_PREFETCH_THIN_CAP",
        os.getenv("SMALL_MODEL_SKILL_PREFETCH_THIN_CAP", "400"),
    ))


def get_small_model_detection_rules_policy() -> str:
    """
    Detection-Rules-Injection-Policy im Small-Mode:
      off  → keine Detection-Rules (maximale Strenge)
      thin → nur sicherheitskritische Regeln (Memory + Container), harter Line+Char-Cap
      full → alle Core + Custom MCP-Regeln (aktuelles Verhalten)
    """
    return settings.get(
        "SMALL_MODEL_DETECTION_RULES_POLICY",
        os.getenv("SMALL_MODEL_DETECTION_RULES_POLICY", "thin"),
    ).lower()


def get_small_model_detection_rules_thin_lines() -> int:
    """Max. Zeilen für Thin-Detection-Rules-Injection."""
    return int(settings.get(
        "SMALL_MODEL_DETECTION_RULES_THIN_LINES",
        os.getenv("SMALL_MODEL_DETECTION_RULES_THIN_LINES", "12"),
    ))


def get_small_model_detection_rules_thin_chars() -> int:
    """Max. Zeichen für Thin-Detection-Rules-Injection."""
    return int(settings.get(
        "SMALL_MODEL_DETECTION_RULES_THIN_CHARS",
        os.getenv("SMALL_MODEL_DETECTION_RULES_THIN_CHARS", "600"),
    ))


def get_small_model_final_cap() -> int:
    """
    Hard-Cap für den gesamten Kontext-String nach ALLEN Appends.
    0 = deaktiviert (default). Aktivieren z.B. mit SMALL_MODEL_FINAL_CAP=4096.
    """
    return int(settings.get(
        "SMALL_MODEL_FINAL_CAP",
        os.getenv("SMALL_MODEL_FINAL_CAP", "0"),
    ))


def get_small_model_tool_ctx_cap() -> int:
    """
    Cap für tool_context-String VOR dem Append zum Kontext (Tool-Delta-Summary).
    0 = deaktiviert (default). Bei Überschreitung: Truncation mit '[...truncated: N chars]'.
    """
    return int(settings.get(
        "SMALL_MODEL_TOOL_CTX_CAP",
        os.getenv("SMALL_MODEL_TOOL_CTX_CAP", "0"),
    ))


# Backward-compat — beim Import eingefroren, Getter bevorzugen
SMALL_MODEL_MODE = get_small_model_mode()
SMALL_MODEL_NOW_MAX = get_small_model_now_max()
SMALL_MODEL_RULES_MAX = get_small_model_rules_max()
SMALL_MODEL_NEXT_MAX = get_small_model_next_max()
SMALL_MODEL_CHAR_CAP = get_small_model_char_cap()
SMALL_MODEL_SKILL_PREFETCH_POLICY = get_small_model_skill_prefetch_policy()
SMALL_MODEL_SKILL_PREFETCH_THIN_CAP = get_small_model_skill_prefetch_thin_cap()
SMALL_MODEL_DETECTION_RULES_POLICY = get_small_model_detection_rules_policy()
