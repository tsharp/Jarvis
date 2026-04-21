"""
config.autonomy.scheduler
==========================
Scheduler-Grundbetrieb & Kapazitätslimits für den Autonomy-Cron.

Steuert wie der Cron-Scheduler läuft und wie viele Jobs er verwalten darf:
- Wo liegt der persistente State?
- Wie oft schlägt der Tick zu?
- Wie viele Jobs / Pending-Runs sind erlaubt?
- Wie lang ist der Cooldown nach einem manuellen Run-Now?
"""
import os

from config.infra.adapter import settings


def get_autonomy_cron_state_path() -> str:
    """Persistenter State-Pfad für Autonomy-Cron-Jobs und Run-Historie."""
    return str(settings.get(
        "AUTONOMY_CRON_STATE_PATH",
        os.getenv("AUTONOMY_CRON_STATE_PATH", "memory_speicher/autonomy_cron_state.json"),
    ))


def get_autonomy_cron_tick_s() -> int:
    """Scheduler-Tick-Interval in Sekunden für den Cron-Matching-Loop."""
    val = int(settings.get(
        "AUTONOMY_CRON_TICK_S",
        os.getenv("AUTONOMY_CRON_TICK_S", "10"),
    ))
    return max(5, min(60, val))


def get_autonomy_cron_max_concurrency() -> int:
    """Max. parallele Cron-Dispatch-Worker (Dispatch in die Autonomy-Queue)."""
    val = int(settings.get(
        "AUTONOMY_CRON_MAX_CONCURRENCY",
        os.getenv("AUTONOMY_CRON_MAX_CONCURRENCY", "1"),
    ))
    return max(1, min(4, val))


def get_autonomy_cron_max_jobs() -> int:
    """Hard-Cap für gespeicherte Cron-Job-Definitionen gesamt."""
    val = int(settings.get(
        "AUTONOMY_CRON_MAX_JOBS",
        os.getenv("AUTONOMY_CRON_MAX_JOBS", "200"),
    ))
    return max(1, min(2000, val))


def get_autonomy_cron_max_jobs_per_conversation() -> int:
    """Hard-Cap für Cron-Jobs pro conversation_id."""
    val = int(settings.get(
        "AUTONOMY_CRON_MAX_JOBS_PER_CONVERSATION",
        os.getenv("AUTONOMY_CRON_MAX_JOBS_PER_CONVERSATION", "30"),
    ))
    return max(1, min(500, val))


def get_autonomy_cron_min_interval_s() -> int:
    """Minimal erlaubtes Schedule-Interval in Sekunden."""
    val = int(settings.get(
        "AUTONOMY_CRON_MIN_INTERVAL_S",
        os.getenv("AUTONOMY_CRON_MIN_INTERVAL_S", "60"),
    ))
    return max(60, min(86400, val))


def get_autonomy_cron_max_pending_runs() -> int:
    """Max. Anzahl pending+running Cron-Dispatches in der Scheduler-Queue gesamt."""
    val = int(settings.get(
        "AUTONOMY_CRON_MAX_PENDING_RUNS",
        os.getenv("AUTONOMY_CRON_MAX_PENDING_RUNS", "500"),
    ))
    return max(1, min(5000, val))


def get_autonomy_cron_max_pending_runs_per_job() -> int:
    """Per-Job-Cap für pending+running Cron-Dispatches."""
    val = int(settings.get(
        "AUTONOMY_CRON_MAX_PENDING_RUNS_PER_JOB",
        os.getenv("AUTONOMY_CRON_MAX_PENDING_RUNS_PER_JOB", "2"),
    ))
    return max(1, min(100, val))


def get_autonomy_cron_manual_run_cooldown_s() -> int:
    """Cooldown in Sekunden für manuelle Run-Now-Aktionen pro Cron-Job."""
    val = int(settings.get(
        "AUTONOMY_CRON_MANUAL_RUN_COOLDOWN_S",
        os.getenv("AUTONOMY_CRON_MANUAL_RUN_COOLDOWN_S", "30"),
    ))
    return max(0, min(3600, val))
