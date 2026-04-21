"""
config.digest
=============
Digest-Pipeline (Phase 8) — Daily/Weekly/Archive-Komprimierung für Langzeit-Memory.

Module:
  schedule → Wann/wie der Digest läuft: Toggles, Zeitzone, Run-Mode, Catchup
  storage  → Wo Daten liegen: Store-, State-, Lock-Pfade + Lock-Timeout
  policy   → Qualität, Filter, Dedupe, JIT-Fenster, API & Hardening-Flags

Re-Exports für bequemen Zugriff via `from config.digest import ...`:
"""
from config.digest.schedule import (
    get_digest_enable,
    get_digest_daily_enable,
    get_digest_weekly_enable,
    get_digest_archive_enable,
    get_digest_tz,
    get_digest_run_mode,
    get_digest_catchup_max_days,
)

from config.digest.storage import (
    get_digest_store_path,
    get_digest_state_path,
    get_digest_lock_path,
    get_digest_lock_timeout_s,
)

from config.digest.policy import (
    get_digest_min_events_daily,
    get_digest_min_daily_per_week,
    get_digest_filters_enable,
    get_digest_dedupe_include_conv,
    get_jit_window_time_reference_h,
    get_jit_window_fact_recall_h,
    get_jit_window_remember_h,
    get_digest_ui_enable,
    get_digest_runtime_api_v2,
    get_digest_jit_warn_on_disabled,
    get_digest_key_version,
)

__all__ = [
    # schedule
    "get_digest_enable", "get_digest_daily_enable", "get_digest_weekly_enable",
    "get_digest_archive_enable", "get_digest_tz", "get_digest_run_mode",
    "get_digest_catchup_max_days",
    # storage
    "get_digest_store_path", "get_digest_state_path",
    "get_digest_lock_path", "get_digest_lock_timeout_s",
    # policy
    "get_digest_min_events_daily", "get_digest_min_daily_per_week",
    "get_digest_filters_enable", "get_digest_dedupe_include_conv",
    "get_jit_window_time_reference_h", "get_jit_window_fact_recall_h",
    "get_jit_window_remember_h", "get_digest_ui_enable",
    "get_digest_runtime_api_v2", "get_digest_jit_warn_on_disabled",
    "get_digest_key_version",
]
