"""
config.skills.registry
=======================
Skill-Registry & Verwaltung — wie Skills gespeichert, identifiziert und erstellt werden.

Steuert:
- Graph-Reconcile: Synchronisiert Graph-Nodes nach Registry-Writes
- Key-Mode: Wie Skills dedupliziert werden (name vs. legacy)
- Control-Authority: Wer die finale Entscheidung bei Skill-Erstellung hat
- Package-Install-Policy: Welche Pakete automatisch installiert werden dürfen
- Discovery: Ob TRION autonomes Read-Only-Skill-Discovery durchführt
- Auto-Create: Ob Low-Risk-Skills ohne User-Prompt erstellt werden
- Autosave-Dedupe: Schützt den Write-Pfad vor doppelten Speichervorgängen
"""
import os

from config.infra.adapter import settings


def get_skill_graph_reconcile() -> bool:
    """
    Graph-Index-Reconcile aktiv halten — Skill-Server synchronisiert
    Graph-Nodes nach Registry-Writes. Default: true.
    """
    return settings.get(
        "SKILL_GRAPH_RECONCILE",
        os.getenv("SKILL_GRAPH_RECONCILE", "true"),
    ).lower() == "true"


def get_skill_key_mode() -> str:
    """
    Skill-Key-Mode für Deduplizierung und Feld-Normalisierung:
      name   → nach Name deduplizieren (default)
      legacy → Rollback-Pfad
    """
    return settings.get(
        "SKILL_KEY_MODE",
        os.getenv("SKILL_KEY_MODE", "name"),
    ).lower()


def get_skill_control_authority() -> str:
    """
    Single Control Authority für Skill-Erstellungs-Entscheidungen:
      skill_server → Skill-Server entscheidet (default)
      legacy_dual  → Rollback-Pfad
    """
    return settings.get(
        "SKILL_CONTROL_AUTHORITY",
        os.getenv("SKILL_CONTROL_AUTHORITY", "skill_server"),
    ).lower()


def get_skill_package_install_mode() -> str:
    """
    Paket-Policy für Skill-Erstellung:
      allowlist_auto → Allowlist-Pakete werden automatisch installiert (default)
      manual_only    → Kein automatischer Package-Install
    """
    val = settings.get(
        "SKILL_PACKAGE_INSTALL_MODE",
        os.getenv("SKILL_PACKAGE_INSTALL_MODE", "allowlist_auto"),
    ).lower()
    return val if val in ("allowlist_auto", "manual_only") else "allowlist_auto"


def get_skill_discovery_enable() -> bool:
    """Autonomes Read-Only-Skill-Discovery aktivieren. Default: true."""
    return settings.get(
        "SKILL_DISCOVERY_ENABLE",
        os.getenv("SKILL_DISCOVERY_ENABLE", "true"),
    ).lower() == "true"


def get_skill_auto_create_on_low_risk() -> bool:
    """
    Pending-Intent-Bestätigung für Low-Risk-Skill-Erstellung umgehen.
    True: hallucination_risk==low UND needs_package_install==False → direkt erstellen.
    Default: false (sicher — immer User fragen).
    Rollback: SKILL_AUTO_CREATE_ON_LOW_RISK=false — kein Code-Revert nötig.
    """
    return settings.get(
        "SKILL_AUTO_CREATE_ON_LOW_RISK",
        os.getenv("SKILL_AUTO_CREATE_ON_LOW_RISK", "false"),
    ).lower() == "true"


def get_autosave_dedupe_enable() -> bool:
    """Kurz-Fenster-Dedupe für Assistant-Autosave aktivieren. Default: true."""
    return settings.get(
        "AUTOSAVE_DEDUPE_ENABLE",
        os.getenv("AUTOSAVE_DEDUPE_ENABLE", "true"),
    ).lower() == "true"


def get_autosave_dedupe_window_s() -> int:
    """Deduplizierungs-Fenster in Sekunden. Default: 90."""
    try:
        return int(settings.get(
            "AUTOSAVE_DEDUPE_WINDOW_S",
            os.getenv("AUTOSAVE_DEDUPE_WINDOW_S", "90"),
        ))
    except Exception:
        return 90


def get_autosave_dedupe_max_entries() -> int:
    """In-Memory-Dedupe-Key-Kapazität. Default: 8192."""
    try:
        return int(settings.get(
            "AUTOSAVE_DEDUPE_MAX_ENTRIES",
            os.getenv("AUTOSAVE_DEDUPE_MAX_ENTRIES", "8192"),
        ))
    except Exception:
        return 8192
