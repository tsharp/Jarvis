"""
config.context.retrieval
=========================
JIT-Retrieval-Budget & Context-Trace-Dryrun.

JIT-Retrieval steuert wie viele workspace_event_list-Fetches pro Turn
erlaubt sind. Bei Fehlern wird das Budget automatisch erhöht (on_failure).

Context-Trace-Dryrun ist ein Diagnose-Schalter: wenn aktiv, werden
sowohl der neue als auch der Legacy-Kontext-Pfad gebaut, das Diff geloggt,
aber das Legacy-Ergebnis zurückgegeben — kein Verhalten geändert.
"""
import os

from config.infra.adapter import settings


def get_jit_retrieval_max() -> int:
    """Max. workspace_event_list-Fetches pro Turn im Normalbetrieb."""
    return int(settings.get("JIT_RETRIEVAL_MAX", os.getenv("JIT_RETRIEVAL_MAX", "1")))


def get_jit_retrieval_max_on_failure() -> int:
    """Erhöhtes Fetch-Budget wenn ein JIT-Retrieval-Fehler aufgetreten ist."""
    return int(settings.get(
        "JIT_RETRIEVAL_MAX_ON_FAILURE",
        os.getenv("JIT_RETRIEVAL_MAX_ON_FAILURE", "2"),
    ))


def get_context_trace_dryrun() -> bool:
    """
    Context-Trace-Dryrun aktivieren:
    Beide Kontext-Pfade (neu + legacy) werden gebaut und geloggt,
    aber nur das Legacy-Ergebnis wird zurückgegeben.
    Default: false.
    """
    return settings.get(
        "CONTEXT_TRACE_DRYRUN",
        os.getenv("CONTEXT_TRACE_DRYRUN", "false"),
    ).lower() == "true"


# Backward-compat — beim Import eingefroren, Getter bevorzugen
JIT_RETRIEVAL_MAX = get_jit_retrieval_max()
JIT_RETRIEVAL_MAX_ON_FAILURE = get_jit_retrieval_max_on_failure()
CONTEXT_TRACE_DRYRUN = get_context_trace_dryrun()
