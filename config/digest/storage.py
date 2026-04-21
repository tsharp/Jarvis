"""
config.digest.storage
======================
Digest-Pipeline Storage — wo die Daten liegen.

Drei Pfade + Lock:
  store_path  → CSV mit allen Daily/Weekly/Archive-Digest-Records
  state_path  → JSON mit Runtime-State (letzter Run, nächster geplanter Run)
  lock_path   → File-Lock verhindert parallele Digest-Runs
  lock_timeout→ Stale-Lock-Übernahme-Schwelle in Sekunden
"""
import os

from config.infra.adapter import settings


def get_digest_store_path() -> str:
    """Pfad zur Digest-Store-CSV (Daily/Weekly/Archive-Records). Relative Pfade ab Project-Root."""
    return settings.get(
        "DIGEST_STORE_PATH",
        os.getenv("DIGEST_STORE_PATH", "memory_speicher/digest_store.csv"),
    )


def get_digest_state_path() -> str:
    """Pfad zum Digest-Runtime-State-JSON. Default: memory_speicher/digest_state.json"""
    return settings.get(
        "DIGEST_STATE_PATH",
        os.getenv("DIGEST_STATE_PATH", "memory_speicher/digest_state.json"),
    )


def get_digest_lock_path() -> str:
    """Pfad zum Digest-File-Lock. Default: memory_speicher/digest.lock"""
    return settings.get(
        "DIGEST_LOCK_PATH",
        os.getenv("DIGEST_LOCK_PATH", "memory_speicher/digest.lock"),
    )


def get_digest_lock_timeout_s() -> int:
    """Stale-Lock-Übernahme-Schwelle in Sekunden. Default: 300."""
    try:
        return int(settings.get(
            "DIGEST_LOCK_TIMEOUT_S",
            os.getenv("DIGEST_LOCK_TIMEOUT_S", "300"),
        ))
    except Exception:
        return 300
