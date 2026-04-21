"""
config.features.typedstate
===========================
TypedState V1 Migration-Flags — VERGÄNGLICH.

TypedState V1 führt ein typisiertes State-Schema für Rendering-Entscheidungen ein.
Die Migration läuft in Commits: off → shadow → active.

  off    → V1-Felder existieren im Schema, aber der Flow ist nicht verdrahtet (default, sicher)
  shadow → V1-Felder werden im Hintergrund befüllt, Ergebnis nicht für Rendering genutzt
  active → V1-Felder steuern Rendering-Entscheidungen (Commit 2+, Zukunft)

Sobald die Migration abgeschlossen ist, wandern die stabilen Werte in ihre
Heimat-Module und diese Datei wird gelöscht.

Rollback: jeweiligen Mode auf 'off' setzen — kein Code-Revert nötig.
"""
import os

from config.infra.adapter import settings


def get_typedstate_mode() -> str:
    """
    TypedState V1 Schema-Aktivierungs-Mode:
      off    → nicht verdrahtet (default)
      shadow → Hintergrund-Befüllung, kein Rendering-Einfluss
      active → steuert Rendering (Commit 2+)
    """
    return settings.get(
        "TYPEDSTATE_MODE",
        os.getenv("TYPEDSTATE_MODE", "off"),
    ).lower()


def get_typedstate_enable_small_only() -> bool:
    """
    True (default): TypedState shadow/active nur im Small-Model-Mode aktiv.
    False: gilt in allen Modi — nicht empfohlen bis stabil.
    """
    return settings.get(
        "TYPEDSTATE_ENABLE_SMALL_ONLY",
        os.getenv("TYPEDSTATE_ENABLE_SMALL_ONLY", "true"),
    ).lower() == "true"


def get_typedstate_csv_path() -> str:
    """Pfad zur CSV-Datei als ergänzende Fakt/Event-Quelle (Commit 3)."""
    return settings.get(
        "TYPEDSTATE_CSV_PATH",
        os.getenv("TYPEDSTATE_CSV_PATH", "memory_speicher/memory_150_rows.csv"),
    )


def get_typedstate_csv_enable() -> bool:
    """
    CSV-Event-Source aktivieren.
    Default: false — CSV wird nicht geladen, solange nicht explizit aktiviert.
    """
    return settings.get(
        "TYPEDSTATE_CSV_ENABLE",
        os.getenv("TYPEDSTATE_CSV_ENABLE", "false"),
    ).lower() == "true"


def get_typedstate_csv_jit_only() -> bool:
    """
    True: CSV-Events nur bei expliziten JIT-Triggern laden
          (time_reference / remember / fact_recall).
    False: bei jedem build_small_model_context-Call laden (default).
    """
    return settings.get(
        "TYPEDSTATE_CSV_JIT_ONLY",
        os.getenv("TYPEDSTATE_CSV_JIT_ONLY", "false"),
    ).lower() == "true"


def get_typedstate_skills_mode() -> str:
    """
    TypedState Skills-Entity Rendering-Mode:
      off | shadow | active
    """
    return settings.get(
        "TYPEDSTATE_SKILLS_MODE",
        os.getenv("TYPEDSTATE_SKILLS_MODE", "off"),
    ).lower()


# Backward-compat — beim Import eingefroren, Getter bevorzugen
TYPEDSTATE_MODE = get_typedstate_mode()
TYPEDSTATE_ENABLE_SMALL_ONLY = get_typedstate_enable_small_only()
