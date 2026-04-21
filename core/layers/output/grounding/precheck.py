"""
core.layers.output.grounding.precheck
========================================
Grounding-Precheck — läuft VOR der LLM-Generierung.

Entscheidet ob Evidence vorhanden und ausreichend ist.
Gibt bei fehlendem Evidence sofort einen Fallback zurück,
ansonsten ein 'pass'-Dict das die Generierung freigibt.
"""
from typing import Any, Dict, List, Optional

from core.layers.output.grounding.evidence import (
    collect_grounding_evidence,
    evidence_item_has_extractable_content,
)
from core.layers.output.grounding.fallback import (
    build_grounding_fallback,
    build_tool_failure_fallback,
)
from core.layers.output.grounding.state import set_runtime_grounding_value
from core.layers.output.contracts.skill_catalog import (
    is_skill_catalog_context_plan,
    update_skill_catalog_trace,
)
from core.grounding_policy import load_grounding_policy
from core.control_contract import is_interactive_tool_status
from core.plan_runtime_bridge import get_runtime_tool_results


def grounding_precheck(
    verified_plan: Dict[str, Any],
    memory_data: str,
    extract_selected_tool_names_fn,
    execution_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Prüft vor der Generierung ob ausreichend Evidence vorhanden ist.

    Returns ein Dict mit:
      blocked        → immer False (Blocking wurde entfernt)
      blocked_reason → Grund warum kein normaler Generate-Pfad
      mode           → 'pass' | 'missing_evidence_fallback' | 'tool_execution_failed_fallback' | ...
      response       → vorgefertigte Antwort wenn mode != 'pass'
      evidence       → gesammelte Evidence-Items
      policy         → output-Policy aus grounding_policy.json
    """
    policy = load_grounding_policy()
    output_cfg = (policy or {}).get("output") or {}
    is_fact_query = bool((verified_plan or {}).get("is_fact_query", False))
    conversation_mode = str((verified_plan or {}).get("conversation_mode") or "").strip().lower()
    is_conversational_mode = conversation_mode == "conversational"
    has_tool_usage = bool(str(get_runtime_tool_results(verified_plan) or "").strip())
    has_tool_suggestions = bool(extract_selected_tool_names_fn(verified_plan))
    evidence = collect_grounding_evidence(verified_plan, memory_data)

    allowed = output_cfg.get("allowed_evidence_statuses", ["ok"])
    allowed_statuses = {
        str(x).strip().lower()
        for x in (allowed if isinstance(allowed, list) else ["ok"])
        if str(x).strip()
    } or {"ok"}
    min_successful = int(output_cfg.get("min_successful_evidence", 1) or 1)
    successful = 0
    successful_extractable = 0
    for item in evidence:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "")).strip().lower()
        if status in allowed_statuses:
            successful += 1
            if evidence_item_has_extractable_content(item):
                successful_extractable += 1

    require_evidence = bool(
        (
            is_fact_query
            and bool(output_cfg.get("enforce_evidence_for_fact_query", True))
            and (has_tool_usage or has_tool_suggestions)
        )
        or (has_tool_usage and bool(output_cfg.get("enforce_evidence_when_tools_used", True)))
        or (
            has_tool_suggestions
            and not is_conversational_mode
            and bool(output_cfg.get("enforce_evidence_when_tools_suggested", True))
        )
    )

    # Alle Flags zurücksetzen
    for key, val in [
        ("missing_evidence", False), ("violation_detected", False),
        ("fallback_used", False), ("repair_attempted", False),
        ("repair_used", False), ("analysis_guard_evaluation", {}),
        ("analysis_guard_violation", {}), ("hybrid_mode", False),
        ("block_reason", ""), ("tool_execution_failed", False),
    ]:
        set_runtime_grounding_value(verified_plan, execution_result, key, val)

    set_runtime_grounding_value(verified_plan, execution_result, "successful_evidence", successful_extractable)
    set_runtime_grounding_value(verified_plan, execution_result, "successful_evidence_status_only", successful)
    set_runtime_grounding_value(verified_plan, execution_result, "evidence_total", len(evidence))

    if is_skill_catalog_context_plan(verified_plan):
        skill_ctx = verified_plan.get("_skill_catalog_context")
        skill_ctx = skill_ctx if isinstance(skill_ctx, dict) else {}
        selected_doc_ids = list(skill_ctx.get("selected_doc_ids") or [])
        if not selected_doc_ids and str(skill_ctx.get("selected_docs") or "").strip():
            selected_doc_ids = [
                part.strip()
                for part in str(skill_ctx.get("selected_docs") or "").split(",")
                if str(part or "").strip()
            ]
        update_skill_catalog_trace(
            verified_plan,
            selected_hints=list(verified_plan.get("strategy_hints") or []),
            selected_docs=selected_doc_ids,
            strict_mode="answer_schema+semantic_postcheck",
            postcheck="pending",
        )

    # Gate-Block: Blueprint-/Policy-Gates sind keine Tech-Failures
    _gate_blocked = bool((verified_plan or {}).get("_blueprint_gate_blocked"))
    if _gate_blocked and require_evidence and successful_extractable < min_successful:
        return {
            "blocked": False, "blocked_reason": "routing_gate_block",
            "mode": "pass", "response": "",
            "evidence": evidence, "is_fact_query": is_fact_query,
            "has_tool_usage": has_tool_usage,
            "verified_plan": verified_plan, "policy": output_cfg,
        }

    # Interaktive Stati (pending_approval, needs_clarification) sind keine Failures
    _interactive_statuses = [
        str((e or {}).get("status") or "").strip().lower()
        for e in (evidence or [])
        if isinstance(e, dict) and is_interactive_tool_status((e or {}).get("status"))
    ]
    _all_failed_are_interactive = bool(_interactive_statuses) and all(
        str((e or {}).get("status") or "").strip().lower() == "ok"
        or is_interactive_tool_status((e or {}).get("status"))
        for e in (evidence or [])
        if isinstance(e, dict)
    )
    if _all_failed_are_interactive and require_evidence and successful_extractable < min_successful:
        blocked_reason = "routing_block"
        if "needs_clarification" in _interactive_statuses:
            blocked_reason = "needs_clarification"
        elif "pending_approval" in _interactive_statuses:
            blocked_reason = "pending_approval"
        return {
            "blocked": False, "blocked_reason": blocked_reason,
            "mode": "pass", "response": "",
            "evidence": evidence, "is_fact_query": is_fact_query,
            "has_tool_usage": has_tool_usage,
            "verified_plan": verified_plan, "policy": output_cfg,
        }

    if require_evidence and successful_extractable < min_successful:
        set_runtime_grounding_value(verified_plan, execution_result, "missing_evidence", True)
        has_tool_failures = any(
            str((item or {}).get("status", "")).strip().lower() in {"error", "skip", "partial", "unavailable"}
            for item in evidence if isinstance(item, dict)
        )
        if has_tool_failures and successful_extractable == 0:
            set_runtime_grounding_value(verified_plan, execution_result, "tool_execution_failed", True)
            set_runtime_grounding_value(verified_plan, execution_result, "block_reason", "tool_execution_failed")
            return {
                "blocked": False, "blocked_reason": "tool_execution_failed",
                "mode": "tool_execution_failed_fallback",
                "response": build_tool_failure_fallback(evidence),
                "evidence": evidence, "is_fact_query": is_fact_query,
                "has_tool_usage": has_tool_usage,
                "verified_plan": verified_plan, "policy": output_cfg,
            }
        fallback_mode = str(output_cfg.get("fallback_mode", "explicit_uncertainty"))
        set_runtime_grounding_value(verified_plan, execution_result, "block_reason", "missing_evidence")
        return {
            "blocked": False, "blocked_reason": "missing_evidence",
            "mode": "missing_evidence_fallback",
            "response": build_grounding_fallback(evidence, mode=fallback_mode),
            "evidence": evidence, "is_fact_query": is_fact_query,
            "has_tool_usage": has_tool_usage,
            "verified_plan": verified_plan, "policy": output_cfg,
        }

    strict_mode = str(output_cfg.get("fact_query_response_mode", "model")).strip().lower()
    if is_fact_query and has_tool_usage and strict_mode == "evidence_summary":
        set_runtime_grounding_value(verified_plan, execution_result, "block_reason", "evidence_summary_mode")
        return {
            "blocked": False, "blocked_reason": "evidence_summary_mode",
            "mode": "evidence_summary_fallback",
            "response": build_grounding_fallback(evidence, mode="summarize_evidence"),
            "evidence": evidence, "is_fact_query": is_fact_query,
            "has_tool_usage": has_tool_usage,
            "verified_plan": verified_plan, "policy": output_cfg,
        }
    if strict_mode in {"hybrid", "hybrid_model"}:
        set_runtime_grounding_value(verified_plan, execution_result, "hybrid_mode", True)

    return {
        "blocked": False, "mode": "pass", "response": "",
        "evidence": evidence, "is_fact_query": is_fact_query,
        "has_tool_usage": has_tool_usage,
        "verified_plan": verified_plan, "policy": output_cfg,
    }
