"""
config.autonomy.hardware_guard
================================
Hardware-Preflight-Guard — Sicherheitsnetz vor jedem Cron-Dispatch.

Bevor ein autonomer Job dispatcht wird, prüft der Guard ob CPU und RAM
des Hosts im grünen Bereich sind. Ist die Last zu hoch, wird der Dispatch
verschoben statt das System zu überlasten.

Schwellenwerte beziehen sich auf normalisierte Host-Prozent-Werte (0–99).
"""
import os

from config.infra.adapter import settings


def get_autonomy_cron_hardware_guard_enabled() -> bool:
    """Hardware-Preflight-Guard vor Cron-Dispatch-Ausführung aktivieren."""
    return str(settings.get(
        "AUTONOMY_CRON_HARDWARE_GUARD_ENABLED",
        os.getenv("AUTONOMY_CRON_HARDWARE_GUARD_ENABLED", "true"),
    )).lower() == "true"


def get_autonomy_cron_hardware_cpu_max_percent() -> int:
    """Max. normalisierter CPU-Last-Prozentsatz bevor ein Cron-Run verschoben wird."""
    val = int(settings.get(
        "AUTONOMY_CRON_HARDWARE_CPU_MAX_PERCENT",
        os.getenv("AUTONOMY_CRON_HARDWARE_CPU_MAX_PERCENT", "90"),
    ))
    return max(50, min(99, val))


def get_autonomy_cron_hardware_mem_max_percent() -> int:
    """Max. Host-RAM-Auslastung in Prozent bevor ein Cron-Run verschoben wird."""
    val = int(settings.get(
        "AUTONOMY_CRON_HARDWARE_MEM_MAX_PERCENT",
        os.getenv("AUTONOMY_CRON_HARDWARE_MEM_MAX_PERCENT", "92"),
    ))
    return max(50, min(99, val))
