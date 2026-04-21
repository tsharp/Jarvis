"""
config.digest.policy
=====================
Digest-Pipeline Policy — Qualität, Filter, Dedupe, JIT-Fenster & API-Hardening.

Qualitätsschwellen: Wie viele Events / Daily-Digests müssen vorliegen
                    bevor ein Digest produziert wird?
Filter & Dedupe:    Zeitfenster-Filterung und Conversation-Scope-Deduplizierung.
JIT-Fenster:        Wie weit reichen die Zeitfenster für JIT-Trigger zurück?
API & Hardening:    Frontend-Panel, API-Shape-Version, Startup-Warnings, Key-Versioning.
"""
import os

from config.infra.adapter import settings


def get_digest_min_events_daily() -> int:
    """Min. Raw-Events für einen Daily-Digest. 0 = kein Minimum. Default: 0."""
    try:
        return int(settings.get(
            "DIGEST_MIN_EVENTS_DAILY",
            os.getenv("DIGEST_MIN_EVENTS_DAILY", "0"),
        ))
    except Exception:
        return 0


def get_digest_min_daily_per_week() -> int:
    """Min. Daily-Digests für einen Weekly-Digest. 0 = kein Minimum. Default: 0."""
    try:
        return int(settings.get(
            "DIGEST_MIN_DAILY_PER_WEEK",
            os.getenv("DIGEST_MIN_DAILY_PER_WEEK", "0"),
        ))
    except Exception:
        return 0


def get_digest_filters_enable() -> bool:
    """Zeitfenster- und Conversation-Scope-Filterung beim CSV-Laden aktivieren. Default: false."""
    return settings.get(
        "DIGEST_FILTERS_ENABLE",
        os.getenv("DIGEST_FILTERS_ENABLE", "false"),
    ).lower() == "true"


def get_digest_dedupe_include_conv() -> bool:
    """
    True (default): Dedupe-Key enthält conversation_id (cross-conversation-sicher).
    False: Dedupe nur über Inhalt — kann Duplikate über Conversations hinweg zulassen.
    """
    return settings.get(
        "DIGEST_DEDUPE_INCLUDE_CONV",
        os.getenv("DIGEST_DEDUPE_INCLUDE_CONV", "true"),
    ).lower() == "true"


def get_jit_window_time_reference_h() -> int:
    """Stunden-Fenster für time_reference JIT-Trigger (gestern+heute). Default: 48."""
    try:
        return int(settings.get(
            "JIT_WINDOW_TIME_REFERENCE_H",
            os.getenv("JIT_WINDOW_TIME_REFERENCE_H", "48"),
        ))
    except Exception:
        return 48


def get_jit_window_fact_recall_h() -> int:
    """Stunden-Fenster für fact_recall JIT-Trigger (7 Tage). Default: 168."""
    try:
        return int(settings.get(
            "JIT_WINDOW_FACT_RECALL_H",
            os.getenv("JIT_WINDOW_FACT_RECALL_H", "168"),
        ))
    except Exception:
        return 168


def get_jit_window_remember_h() -> int:
    """Stunden-Fenster für remember JIT-Trigger (14 Tage). Default: 336."""
    try:
        return int(settings.get(
            "JIT_WINDOW_REMEMBER_H",
            os.getenv("JIT_WINDOW_REMEMBER_H", "336"),
        ))
    except Exception:
        return 336


def get_digest_ui_enable() -> bool:
    """Digest-Status-Panel im Frontend anzeigen. Default: false."""
    return settings.get(
        "DIGEST_UI_ENABLE",
        os.getenv("DIGEST_UI_ENABLE", "false"),
    ).lower() == "true"


def get_digest_runtime_api_v2() -> bool:
    """
    Flaches API-v2-Response-Shape von /api/runtime/digest-state liefern. Default: true.
    False → Legacy-Shape {state, flags, lock}.
    """
    return settings.get(
        "DIGEST_RUNTIME_API_V2",
        os.getenv("DIGEST_RUNTIME_API_V2", "true"),
    ).lower() == "true"


def get_digest_jit_warn_on_disabled() -> bool:
    """Startup-Warning wenn JIT_ONLY=false bei aktiver Digest-Pipeline. Default: true."""
    return settings.get(
        "DIGEST_JIT_WARN_ON_DISABLED",
        os.getenv("DIGEST_JIT_WARN_ON_DISABLED", "true"),
    ).lower() == "true"


def get_digest_key_version() -> str:
    """
    Digest-Key-Version:
      v1 (default) → rückwärtskompatibel
      v2           → explizite Fenstergrenzen (erster Run re-erstellt bestehende Digests, idempotent)
    """
    return settings.get(
        "DIGEST_KEY_VERSION",
        os.getenv("DIGEST_KEY_VERSION", "v1"),
    ).lower()
