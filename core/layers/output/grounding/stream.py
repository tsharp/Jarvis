"""
core.layers.output.grounding.stream
======================================
Stream-Postcheck-Steuerung.

Entscheidet ob und wie der Output-Stream für den Postcheck gepuffert wird:
  off         → kein Postcheck
  tail_repair → stream first, korrigiere am Ende falls nötig
  buffered    → puffere alles, gib erst nach Postcheck aus
"""
from typing import Any, Dict

from config.output.streaming import get_output_stream_postcheck_mode
from core.layers.output.contracts.skill_catalog import is_skill_catalog_context_plan
from core.layers.output.contracts.container import is_container_query_contract_plan
from core.output_analysis_guard import is_analysis_turn_guard_applicable
from core.plan_runtime_bridge import get_runtime_tool_results


def resolve_stream_postcheck_mode(precheck_policy: Dict[str, Any]) -> str:
    """
    Liest den Stream-Postcheck-Modus aus Policy oder Config.
    Gültige Werte: 'tail_repair' | 'buffered' | 'off'
    """
    mode = str((precheck_policy or {}).get("stream_postcheck_mode", "")).strip().lower()
    if mode in {"tail_repair", "buffered", "off"}:
        return mode
    return str(get_output_stream_postcheck_mode() or "tail_repair").strip().lower()


def should_buffer_stream_postcheck(
    verified_plan: Dict[str, Any],
    precheck_policy: Dict[str, Any],
    *,
    postcheck_enabled: bool,
) -> bool:
    """
    Entscheidet ob der Stream vollständig gepuffert werden soll.

    Puffern notwendig wenn:
      - mode == 'buffered' (explizit)
      - Skill-Catalog-Turn (Reparatur soll für User unsichtbar bleiben)
      - Container-Kontrakt-Turn (ebenfalls unsichtbar)
      - Analysis-Turn-Guard aktiv
    Task-Loop-Step-Runtime überspringt Puffering immer.
    """
    if not postcheck_enabled:
        return False
    if bool((verified_plan or {}).get("_task_loop_step_runtime")):
        return False
    mode = resolve_stream_postcheck_mode(precheck_policy)
    if mode == "off":
        return False
    if mode == "buffered":
        return True
    return (
        is_skill_catalog_context_plan(verified_plan)
        or is_container_query_contract_plan(verified_plan)
        or is_analysis_turn_guard_applicable(
            verified_plan,
            output_cfg=precheck_policy,
            has_tool_usage=bool(str(get_runtime_tool_results(verified_plan) or "").strip()),
            is_fact_query=bool(verified_plan.get("is_fact_query", False)),
        )
    )


def stream_postcheck_enabled(precheck: Dict[str, Any]) -> bool:
    """
    Prüft ob der Postcheck für diesen Request überhaupt aktiv ist.
    Deaktiviert wenn mode == 'off' oder kein relevanter Guard greift.
    """
    policy = (precheck or {}).get("policy") or {}
    if resolve_stream_postcheck_mode(policy) == "off":
        return False
    if is_analysis_turn_guard_applicable(
        (precheck or {}).get("verified_plan") or {},
        output_cfg=policy,
        has_tool_usage=bool((precheck or {}).get("has_tool_usage", False)),
        is_fact_query=bool((precheck or {}).get("is_fact_query", False)),
    ):
        return True
    return bool(
        precheck.get("is_fact_query")
        and (
            bool(policy.get("forbid_new_numeric_claims", True))
            or bool(policy.get("forbid_unverified_qualitative_claims", True))
        )
    )
