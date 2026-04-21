"""
config.autonomy
===============
Autonomie-Cron-System — zeitgesteuerte autonome Aufgaben.

Module:
  scheduler      → Grundbetrieb: State-Pfad, Tick, Kapazitätslimits
  trion_policy   → TRION-Safe-Mode: strengere Policy für TRION-erstellte Jobs
  hardware_guard → Hardware-Preflight: CPU/RAM-Check vor jedem Dispatch

Re-Exports für bequemen Zugriff via `from config.autonomy import ...`:
"""
from config.autonomy.scheduler import (
    get_autonomy_cron_state_path,
    get_autonomy_cron_tick_s,
    get_autonomy_cron_max_concurrency,
    get_autonomy_cron_max_jobs,
    get_autonomy_cron_max_jobs_per_conversation,
    get_autonomy_cron_min_interval_s,
    get_autonomy_cron_max_pending_runs,
    get_autonomy_cron_max_pending_runs_per_job,
    get_autonomy_cron_manual_run_cooldown_s,
)

from config.autonomy.trion_policy import (
    get_autonomy_cron_trion_safe_mode,
    get_autonomy_cron_trion_min_interval_s,
    get_autonomy_cron_trion_max_loops,
    get_autonomy_cron_trion_require_approval_for_risky,
)

from config.autonomy.hardware_guard import (
    get_autonomy_cron_hardware_guard_enabled,
    get_autonomy_cron_hardware_cpu_max_percent,
    get_autonomy_cron_hardware_mem_max_percent,
)

__all__ = [
    # scheduler
    "get_autonomy_cron_state_path", "get_autonomy_cron_tick_s",
    "get_autonomy_cron_max_concurrency", "get_autonomy_cron_max_jobs",
    "get_autonomy_cron_max_jobs_per_conversation", "get_autonomy_cron_min_interval_s",
    "get_autonomy_cron_max_pending_runs", "get_autonomy_cron_max_pending_runs_per_job",
    "get_autonomy_cron_manual_run_cooldown_s",
    # trion_policy
    "get_autonomy_cron_trion_safe_mode", "get_autonomy_cron_trion_min_interval_s",
    "get_autonomy_cron_trion_max_loops", "get_autonomy_cron_trion_require_approval_for_risky",
    # hardware_guard
    "get_autonomy_cron_hardware_guard_enabled", "get_autonomy_cron_hardware_cpu_max_percent",
    "get_autonomy_cron_hardware_mem_max_percent",
]
