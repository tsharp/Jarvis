"""
config.digest.schedule
=======================
Digest-Pipeline Scheduling — wann und wie der Digest läuft.

Alle Sub-Toggles (daily/weekly/archive) sind von DIGEST_ENABLE abhängig —
wenn der Master-Toggle false ist, sind alle Sub-Toggles automatisch false.

Run-Modi:
  off     → kein automatischer Digest (default)
  sidecar → externer Prozess übernimmt das Scheduling
  inline  → Scheduling läuft im Haupt-Prozess

Rollback: DIGEST_ENABLE=false deaktiviert alle Digest-Features ohne Code-Revert.
"""
import os

from config.infra.adapter import settings


def get_digest_enable() -> bool:
    """Master-Toggle für alle Digest-Pipeline-Features (default: false)."""
    return settings.get(
        "DIGEST_ENABLE",
        os.getenv("DIGEST_ENABLE", "false"),
    ).lower() == "true"


def get_digest_daily_enable() -> bool:
    """Täglichen 04:00-Komprimierungs-Job aktivieren (benötigt DIGEST_ENABLE=true)."""
    return get_digest_enable() and settings.get(
        "DIGEST_DAILY_ENABLE",
        os.getenv("DIGEST_DAILY_ENABLE", "false"),
    ).lower() == "true"


def get_digest_weekly_enable() -> bool:
    """Rollenden 7-Tage-Weekly-Digest aus daily_digests aktivieren (benötigt DIGEST_ENABLE=true)."""
    return get_digest_enable() and settings.get(
        "DIGEST_WEEKLY_ENABLE",
        os.getenv("DIGEST_WEEKLY_ENABLE", "false"),
    ).lower() == "true"


def get_digest_archive_enable() -> bool:
    """Archive-Digest in Graph nach 14 Tagen aktivieren (benötigt DIGEST_ENABLE=true)."""
    return get_digest_enable() and settings.get(
        "DIGEST_ARCHIVE_ENABLE",
        os.getenv("DIGEST_ARCHIVE_ENABLE", "false"),
    ).lower() == "true"


def get_digest_tz() -> str:
    """IANA-Zeitzonenname für das Digest-Scheduling. Default: Europe/Berlin."""
    return settings.get("DIGEST_TZ", os.getenv("DIGEST_TZ", "Europe/Berlin"))


def get_digest_run_mode() -> str:
    """Digest-Scheduling-Modus: off | sidecar | inline. Default: off."""
    return settings.get(
        "DIGEST_RUN_MODE",
        os.getenv("DIGEST_RUN_MODE", "off"),
    ).lower()


def get_digest_catchup_max_days() -> int:
    """Max. Tage für Catch-Up nach Neustart. 0 = kein Catch-Up. Default: 7."""
    try:
        return int(settings.get(
            "DIGEST_CATCHUP_MAX_DAYS",
            os.getenv("DIGEST_CATCHUP_MAX_DAYS", "7"),
        ))
    except Exception:
        return 7
