"""
config.pipeline.domain_router
==============================
Domain-Routing & Tool-Injection-Konfiguration.

Der Domain-Router entscheidet deterministisch vor der Tool-Ausführung,
ob eine Anfrage zu CRON, SKILL oder einem anderen Domain-Handler gehört.
Der Policy-Conflict-Resolver löst Widersprüche zwischen Routing-Entscheidungen
auf bevor die Control-Layer sie sieht.
"""
import os

from config.infra.adapter import settings


def get_domain_router_enable() -> bool:
    """Deterministisches CRON/SKILL-Routing vor Tool-Ausführung aktivieren."""
    return str(settings.get(
        "DOMAIN_ROUTER_ENABLE",
        os.getenv("DOMAIN_ROUTER_ENABLE", "true"),
    )).lower() == "true"


def get_domain_router_embedding_enable() -> bool:
    """Embedding-Refinement für uneindeutige Domain-Routing-Entscheidungen."""
    return str(settings.get(
        "DOMAIN_ROUTER_EMBEDDING_ENABLE",
        os.getenv("DOMAIN_ROUTER_EMBEDDING_ENABLE", "true"),
    )).lower() == "true"


def get_domain_router_lock_min_confidence() -> float:
    """Minimum Confidence um eine Nicht-Generic-Domain-Entscheidung zu sperren."""
    try:
        val = float(settings.get(
            "DOMAIN_ROUTER_LOCK_MIN_CONFIDENCE",
            os.getenv("DOMAIN_ROUTER_LOCK_MIN_CONFIDENCE", "0.72"),
        ))
    except Exception:
        val = 0.72
    return max(0.0, min(1.0, val))


def get_policy_conflict_resolver_enable() -> bool:
    """Deterministischen Pre-Control-Policy-Conflict-Resolver aktivieren."""
    return str(settings.get(
        "POLICY_CONFLICT_RESOLVER_ENABLE",
        os.getenv("POLICY_CONFLICT_RESOLVER_ENABLE", "true"),
    )).lower() == "true"


def get_policy_conflict_resolver_rollout_pct() -> int:
    """Rollout-Prozentsatz (0–100) für den Policy-Conflict-Resolver."""
    try:
        val = int(settings.get(
            "POLICY_CONFLICT_RESOLVER_ROLLOUT_PCT",
            os.getenv("POLICY_CONFLICT_RESOLVER_ROLLOUT_PCT", "100"),
        ))
    except Exception:
        val = 100
    return max(0, min(100, val))


def get_output_tool_injection_mode() -> str:
    """
    Steuert welche Tools in den Output-System-Prompt injiziert werden:
      - selected: nur für diese Anfrage ausgewählte Tools (default)
      - all:      alle aktivierten Tools (legacy)
      - none:     Tool-Listen-Injection deaktivieren
    """
    mode = str(settings.get(
        "OUTPUT_TOOL_INJECTION_MODE",
        os.getenv("OUTPUT_TOOL_INJECTION_MODE", "selected"),
    )).strip().lower()
    return mode if mode in {"selected", "all", "none"} else "selected"


def get_output_tool_prompt_limit() -> int:
    """Obergrenze für die Anzahl der in den Output-Prompt injizierten Tools."""
    val = int(settings.get(
        "OUTPUT_TOOL_PROMPT_LIMIT",
        os.getenv("OUTPUT_TOOL_PROMPT_LIMIT", "10"),
    ))
    return max(1, min(50, val))
