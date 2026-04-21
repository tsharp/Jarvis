"""
config.output.jobs
==================
Job-Kapazitäten auf API-Ebene — Deep-Jobs & Autonomy-Jobs.

Beide Job-Typen teilen dasselbe Kapazitäts-Problem:
wie viele schwere parallele Jobs darf das System gleichzeitig ausführen?

Deep-Jobs    : /api/chat/deep-jobs — schwere sequenzielle Analyse-Anfragen
Autonomy-Jobs: /api/autonomous/jobs — autonome Ausführungs-Jobs

Default-Concurrency ist konservativ (1) für Single-GPU-Setups.
"""
import os

from config.infra.adapter import settings


def get_deep_job_timeout_s() -> int:
    """Hard-Timeout für /api/chat/deep-jobs Worker-Ausführung (Sekunden)."""
    val = int(settings.get(
        "DEEP_JOB_TIMEOUT_S",
        os.getenv("DEEP_JOB_TIMEOUT_S", "210"),
    ))
    return max(30, min(1800, val))


def get_deep_job_max_concurrency() -> int:
    """Max. parallele Deep-Jobs auf API-Ebene (konservativ: 1 für Single-GPU)."""
    val = int(settings.get(
        "DEEP_JOB_MAX_CONCURRENCY",
        os.getenv("DEEP_JOB_MAX_CONCURRENCY", "1"),
    ))
    return max(1, min(8, val))


def get_autonomy_job_timeout_s() -> int:
    """Hard-Timeout für /api/autonomous/jobs Worker-Ausführung (Sekunden)."""
    val = int(settings.get(
        "AUTONOMY_JOB_TIMEOUT_S",
        os.getenv("AUTONOMY_JOB_TIMEOUT_S", "300"),
    ))
    return max(30, min(3600, val))


def get_autonomy_job_max_concurrency() -> int:
    """Max. parallele Autonomy-Jobs auf API-Ebene."""
    val = int(settings.get(
        "AUTONOMY_JOB_MAX_CONCURRENCY",
        os.getenv("AUTONOMY_JOB_MAX_CONCURRENCY", "1"),
    ))
    return max(1, min(8, val))
