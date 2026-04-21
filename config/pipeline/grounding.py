"""
config.pipeline.grounding
==========================
Grounding, Memory-Retrieval & Followup-Reuse-Konfiguration.

Grounding stellt sicher, dass Antworten auf echten Tool-Ergebnissen basieren.
Dieses Modul kontrolliert:
- Auto-Recovery wenn Grounding fehlt (ein einmaliger Tool-Retry)
- Followup-Tool-Reuse (kurze Factual-Followups greifen auf vorherige Ergebnisse zurück)
- Memory-Retrieval-Budgets (wie lange, wie viele Keys)
- Context-Guardrails (maximale Kontextlänge vor der Pipeline)
"""
import os

from config.infra.adapter import settings


def get_grounding_auto_recovery_enable() -> bool:
    """One-Shot Auto-Recovery Tool-Retry aktivieren wenn Fact-Grounding fehlt."""
    return str(settings.get(
        "GROUNDING_AUTO_RECOVERY_ENABLE",
        os.getenv("GROUNDING_AUTO_RECOVERY_ENABLE", "true"),
    )).lower() == "true"


def get_grounding_auto_recovery_timeout_s() -> float:
    """Timeout-Budget in Sekunden für den einmaligen Grounding-Auto-Recovery."""
    try:
        val = float(settings.get(
            "GROUNDING_AUTO_RECOVERY_TIMEOUT_S",
            os.getenv("GROUNDING_AUTO_RECOVERY_TIMEOUT_S", "8"),
        ))
    except Exception:
        val = 8.0
    return max(1.0, min(60.0, val))


def get_grounding_auto_recovery_whitelist() -> list:
    """Tools die automatisch für Grounding-Recovery wiederholt werden dürfen."""
    raw = str(settings.get(
        "GROUNDING_AUTO_RECOVERY_WHITELIST",
        os.getenv(
            "GROUNDING_AUTO_RECOVERY_WHITELIST",
            "run_skill,get_system_info,memory_graph_search,list_skills",
        ),
    ))
    out = []
    seen = set()
    for item in raw.split(","):
        name = str(item or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def get_followup_tool_reuse_enable() -> bool:
    """Deterministischen Followup-Tool-Reuse für kurze Fact-Query-Followups aktivieren."""
    return str(settings.get(
        "FOLLOWUP_TOOL_REUSE_ENABLE",
        os.getenv("FOLLOWUP_TOOL_REUSE_ENABLE", "true"),
    )).lower() == "true"


def get_followup_tool_reuse_ttl_turns() -> int:
    """Max. Turn-Abstand (User+Assistant-Paare) für Followup-Tool-Reuse-State."""
    try:
        val = int(settings.get(
            "FOLLOWUP_TOOL_REUSE_TTL_TURNS",
            os.getenv("FOLLOWUP_TOOL_REUSE_TTL_TURNS", "3"),
        ))
    except Exception:
        val = 3
    return max(1, min(12, val))


def get_followup_tool_reuse_ttl_s() -> int:
    """TTL in Sekunden für den konversations-lokalen Followup-Grounding-State."""
    try:
        val = int(settings.get(
            "FOLLOWUP_TOOL_REUSE_TTL_S",
            os.getenv("FOLLOWUP_TOOL_REUSE_TTL_S", "1200"),
        ))
    except Exception:
        val = 1200
    return max(30, min(86400, val))


def get_daily_context_followup_enable() -> bool:
    """Leichten Daily-Context-Fallback für temporale Followup-Turns aktivieren."""
    return str(settings.get(
        "DAILY_CONTEXT_FOLLOWUP_ENABLE",
        os.getenv("DAILY_CONTEXT_FOLLOWUP_ENABLE", "true"),
    )).lower() == "true"


def get_context_memory_fallback_recall_only_enable() -> bool:
    """
    ContextManager Memory-Fallback auf explizite Recall/Personal-Memory-Turns
    beschränken.
    """
    return str(settings.get(
        "CONTEXT_MEMORY_FALLBACK_RECALL_ONLY_ENABLE",
        os.getenv("CONTEXT_MEMORY_FALLBACK_RECALL_ONLY_ENABLE", "true"),
    )).lower() == "true"


def get_context_memory_fallback_recall_only_rollout_pct() -> int:
    """Rollout-Prozentsatz (0–100) für Recall-Only Memory-Fallback."""
    try:
        val = int(settings.get(
            "CONTEXT_MEMORY_FALLBACK_RECALL_ONLY_ROLLOUT_PCT",
            os.getenv("CONTEXT_MEMORY_FALLBACK_RECALL_ONLY_ROLLOUT_PCT", "100"),
        ))
    except Exception:
        val = 100
    return max(0, min(100, val))


def get_memory_lookup_timeout_s() -> float:
    """Timeout pro Memory-Tool-Call in Retrieval-Helpers (Sekunden)."""
    try:
        val = float(settings.get(
            "MEMORY_LOOKUP_TIMEOUT_S",
            os.getenv("MEMORY_LOOKUP_TIMEOUT_S", "1.5"),
        ))
    except Exception:
        val = 1.5
    return max(0.2, min(10.0, val))


def get_memory_keys_max_per_request() -> int:
    """Hard-Cap für Memory-Key-Fan-out pro Request (nach Deduplizierung)."""
    try:
        val = int(settings.get(
            "MEMORY_KEYS_MAX_PER_REQUEST",
            os.getenv("MEMORY_KEYS_MAX_PER_REQUEST", "4"),
        ))
    except Exception:
        val = 4
    return max(1, min(20, val))


def get_context_retrieval_budget_s() -> float:
    """
    Gesamt-Budget für die Context-Retrieval-Phase (Sekunden).
    Hält den Retrieval-Fan-out unter degradierten Abhängigkeits-Zuständen begrenzt.
    """
    try:
        val = float(settings.get(
            "CONTEXT_RETRIEVAL_BUDGET_S",
            os.getenv("CONTEXT_RETRIEVAL_BUDGET_S", "6.0"),
        ))
    except Exception:
        val = 6.0
    return max(1.0, min(30.0, val))


def get_effective_context_guardrail_chars() -> int:
    """
    Soft-Guardrail für die effektive Kontextlänge im Full-Model-Mode.
    0 deaktiviert den Guardrail.
    """
    val = int(settings.get(
        "EFFECTIVE_CONTEXT_GUARDRAIL_CHARS",
        os.getenv("EFFECTIVE_CONTEXT_GUARDRAIL_CHARS", "9000"),
    ))
    return max(0, min(200000, val))
