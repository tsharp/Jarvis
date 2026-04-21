"""
config.autonomy.trion_policy
=============================
TRION-Safe-Mode-Policy — strengere Regeln für TRION-erstellte Cron-Jobs.

Wenn TRION selbst einen Cron-Job anlegt (statt der User), gelten härtere
Einschränkungen: längere Mindestintervalle, begrenzte Loop-Tiefe und
Approval-Pflicht bei riskanten Zielen.

Rollback: AUTONOMY_CRON_TRION_SAFE_MODE=false deaktiviert alle TRION-spezifischen
          Checks ohne Code-Revert.
"""
import os

from config.infra.adapter import settings


def get_autonomy_cron_trion_safe_mode() -> bool:
    """Strengere Policy-Checks für TRION-erstellte Cron-Jobs aktivieren."""
    return str(settings.get(
        "AUTONOMY_CRON_TRION_SAFE_MODE",
        os.getenv("AUTONOMY_CRON_TRION_SAFE_MODE", "true"),
    )).lower() == "true"


def get_autonomy_cron_trion_min_interval_s() -> int:
    """Minimal erlaubtes Interval für TRION-erstellte Cron-Jobs (Sekunden)."""
    val = int(settings.get(
        "AUTONOMY_CRON_TRION_MIN_INTERVAL_S",
        os.getenv("AUTONOMY_CRON_TRION_MIN_INTERVAL_S", "300"),
    ))
    return max(60, min(86400, val))


def get_autonomy_cron_trion_max_loops() -> int:
    """Max. Autonomy-Loops pro TRION-erstellter Cron-Ausführung."""
    val = int(settings.get(
        "AUTONOMY_CRON_TRION_MAX_LOOPS",
        os.getenv("AUTONOMY_CRON_TRION_MAX_LOOPS", "50"),
    ))
    return max(1, min(200, val))


def get_autonomy_cron_trion_require_approval_for_risky() -> bool:
    """Explizite User-Approval für riskante TRION-Cron-Ziele verlangen."""
    return str(settings.get(
        "AUTONOMY_CRON_TRION_REQUIRE_APPROVAL_FOR_RISKY",
        os.getenv("AUTONOMY_CRON_TRION_REQUIRE_APPROVAL_FOR_RISKY", "true"),
    )).lower() == "true"
