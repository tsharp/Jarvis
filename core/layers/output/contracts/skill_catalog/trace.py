"""
core.layers.output.contracts.skill_catalog.trace
==================================================
Erkennung und Trace-State für Skill-Catalog-Turns.

Beantwortet: Ist dieser Plan ein Skill-Catalog-Turn?
Schreibt/liest den observability trace unter verified_plan._ctx_trace.skill_catalog.
"""
from typing import Any, Dict, Optional


def is_skill_catalog_context_plan(verified_plan: Dict[str, Any]) -> bool:
    """
    Prüft ob der Plan ein Skill-Catalog-Turn ist.
    Kriterien: resolution_strategy == 'skill_catalog_context'
    ODER _skill_catalog_context / _skill_catalog_policy im Plan gesetzt.
    """
    if not isinstance(verified_plan, dict):
        return False
    resolution_strategy = str(
        verified_plan.get("_authoritative_resolution_strategy")
        or verified_plan.get("resolution_strategy")
        or ""
    ).strip().lower()
    return resolution_strategy == "skill_catalog_context" or bool(
        verified_plan.get("_skill_catalog_context")
    ) or bool(
        verified_plan.get("_skill_catalog_policy")
    )


def skill_catalog_trace_state(
    verified_plan: Dict[str, Any],
    *,
    create: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Liest (oder erstellt bei create=True) den Skill-Catalog-Trace-Dict
    unter verified_plan._ctx_trace.skill_catalog.
    Gibt None zurück wenn kein Skill-Catalog-Turn oder kein Trace vorhanden.
    """
    if not is_skill_catalog_context_plan(verified_plan):
        return None
    if not isinstance(verified_plan, dict):
        return None
    ctx_trace = verified_plan.get("_ctx_trace")
    if not isinstance(ctx_trace, dict):
        if not create:
            return None
        ctx_trace = {}
        verified_plan["_ctx_trace"] = ctx_trace
    skill_trace = ctx_trace.get("skill_catalog")
    if not isinstance(skill_trace, dict):
        if not create:
            return None
        skill_trace = {}
        ctx_trace["skill_catalog"] = skill_trace
    return skill_trace


def update_skill_catalog_trace(
    verified_plan: Dict[str, Any],
    **fields: Any,
) -> None:
    """
    Schreibt beliebige Felder in den Skill-Catalog-Trace.
    None-Werte werden übersprungen.
    """
    skill_trace = skill_catalog_trace_state(verified_plan, create=True)
    if not isinstance(skill_trace, dict):
        return
    for key, value in fields.items():
        if value is None:
            continue
        skill_trace[str(key)] = value
