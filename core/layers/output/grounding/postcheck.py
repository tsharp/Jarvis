"""
core.layers.output.grounding.postcheck
=========================================
Grounding-Postcheck — läuft NACH der LLM-Generierung.

Prüft die fertige Antwort auf:
  - Numerische Claims ohne Evidence-Nachweis
  - Skill-Catalog-Kontrakt-Verletzungen
  - Container-Kontrakt-Verletzungen
  - Qualitative Novelty (zu viele neue Wörter ohne Evidence)
  - Analysis-Turn-Guard (konzeptionelle Turns ohne Runtime-Belege)

Bei Verletzung: einmaliger Reparaturversuch, dann Fallback.
"""
from typing import Any, Dict, List, Optional

from utils.logger import log_info, log_warning

from core.layers.output.grounding.evidence import collect_evidence_text_parts
from core.layers.output.grounding.fallback import build_grounding_fallback
from core.layers.output.grounding.state import set_runtime_grounding_value
from core.layers.output.analysis.numeric import extract_numeric_tokens
from core.layers.output.analysis.qualitative import evaluate_qualitative_grounding
from core.layers.output.analysis.numeric import extract_word_tokens
from core.layers.output.contracts.skill_catalog import (
    is_skill_catalog_context_plan,
    update_skill_catalog_trace,
    evaluate_skill_catalog_semantic_leakage,
    build_skill_catalog_safe_fallback,
)
from core.layers.output.contracts.container import (
    is_container_query_contract_plan,
    build_container_safe_fallback,
    evaluate_container_contract_leakage,
)
from core.output_analysis_guard import (
    evaluate_analysis_turn_answer,
    build_analysis_turn_safe_fallback,
    is_analysis_turn_guard_applicable,
)
from core.plan_runtime_bridge import get_runtime_grounding_value


def attempt_grounding_repair_once(
    *,
    verified_plan: Dict[str, Any],
    execution_result: Optional[Dict[str, Any]],
    evidence: List[Dict[str, Any]],
    output_cfg: Dict[str, Any],
    reason: str,
) -> str:
    """
    Einmaliger Reparaturversuch nach einer Grounding-Verletzung.
    Container-Pläne bekommen einen strukturierten Container-Fallback,
    alle anderen einen summarize_evidence-Fallback.
    Gibt leeren String zurück wenn keine Reparatur möglich.
    """
    if not bool(output_cfg.get("enable_postcheck_repair_once", True)):
        return ""
    if not isinstance(verified_plan, dict):
        return ""
    if bool(get_runtime_grounding_value(verified_plan, key="repair_attempted", default=False)):
        return ""

    set_runtime_grounding_value(verified_plan, execution_result, "repair_attempted", True)

    if is_container_query_contract_plan(verified_plan):
        repaired = build_container_safe_fallback(verified_plan, evidence)
        repaired_text = str(repaired or "").strip()
        if repaired_text:
            set_runtime_grounding_value(verified_plan, execution_result, "repair_used", True)
            log_warning(f"[OutputLayer] Container postcheck repair used: reason={reason}")
            return repaired_text

    repaired = build_grounding_fallback(evidence, mode="summarize_evidence")
    repaired_text = str(repaired or "").strip()
    if not repaired_text or "keinen verifizierten tool-nachweis" in repaired_text.lower():
        return ""

    set_runtime_grounding_value(verified_plan, execution_result, "repair_used", True)
    log_warning(f"[OutputLayer] Grounding postcheck repair used: reason={reason} mode=summarize_evidence")
    return repaired_text


def grounding_postcheck(
    answer: str,
    verified_plan: Dict[str, Any],
    precheck: Dict[str, Any],
    execution_result: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Prüft die fertige LLM-Antwort gegen alle Grounding-Invarianten.
    Gibt die (ggf. reparierte) Antwort zurück.
    """
    if not answer:
        return answer

    output_cfg = (precheck or {}).get("policy") or {}
    evidence = (precheck or {}).get("evidence") or []
    is_fact_query = bool((precheck or {}).get("is_fact_query", False))

    evidence_text_parts = collect_evidence_text_parts(evidence)
    evidence_blob = "\n".join(evidence_text_parts)
    fallback_mode = str(output_cfg.get("fallback_mode", "explicit_uncertainty"))

    # Analysis-Turn-Guard
    analysis_guard_result = evaluate_analysis_turn_answer(
        answer,
        verified_plan=verified_plan,
        output_cfg=output_cfg,
        user_text=str(get_runtime_grounding_value(verified_plan, key="analysis_guard_user_text", default="") or ""),
        memory_data_present=bool(get_runtime_grounding_value(verified_plan, key="analysis_guard_memory_present", default=False)),
        evidence_text=evidence_blob,
        has_tool_usage=bool((precheck or {}).get("has_tool_usage", False)),
        is_fact_query=is_fact_query,
    )
    set_runtime_grounding_value(verified_plan, execution_result, "analysis_guard_evaluation", analysis_guard_result)

    if analysis_guard_result.get("applicable") or str(verified_plan.get("_loop_trace_mode") or "").strip():
        log_info(
            "[OutputLayer] Analysis turn guard evaluated: "
            f"applicable={bool(analysis_guard_result.get('applicable'))} "
            f"trigger={analysis_guard_result.get('trigger_source') or 'none'} "
            f"skipped_reason={analysis_guard_result.get('skipped_reason') or 'none'} "
            f"violated={bool(analysis_guard_result.get('violated'))} "
            f"checked_chars={int(analysis_guard_result.get('checked_chars') or 0)}"
        )

    if analysis_guard_result.get("violated"):
        for key, val in [
            ("violation_detected", True), ("fallback_used", True),
            ("repair_attempted", True), ("repair_used", True),
        ]:
            set_runtime_grounding_value(verified_plan, execution_result, key, val)
        set_runtime_grounding_value(verified_plan, execution_result, "analysis_guard_violation", analysis_guard_result)
        log_warning(f"[OutputLayer] Analysis turn guard repair used: reasons={analysis_guard_result.get('reasons')}")
        return build_analysis_turn_safe_fallback(
            verified_plan,
            user_text=str(get_runtime_grounding_value(verified_plan, key="analysis_guard_user_text", default="") or ""),
            reasons=list(analysis_guard_result.get("reasons") or []),
        )

    if not (is_fact_query and evidence):
        return answer

    _strict_no_content = bool(evidence and not evidence_text_parts)
    if _strict_no_content:
        log_warning(
            "[OutputLayer] Grounding postcheck strict mode: "
            f"fact_query evidence present but no extractable content; "
            f"tools={[e.get('tool_name') for e in evidence]}"
        )

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
        )

    # Numerische Claims prüfen
    if bool(output_cfg.get("forbid_new_numeric_claims", True)):
        answer_nums = set(extract_numeric_tokens(answer))
        evidence_nums = set(extract_numeric_tokens(evidence_blob))
        unknown = sorted(tok for tok in answer_nums if tok not in evidence_nums)
        if unknown:
            set_runtime_grounding_value(verified_plan, execution_result, "violation_detected", True)
            set_runtime_grounding_value(verified_plan, execution_result, "fallback_used", True)
            log_warning(f"[OutputLayer] Grounding postcheck fallback: unknown numeric claims={unknown[:6]}")
            repaired = attempt_grounding_repair_once(
                verified_plan=verified_plan, execution_result=execution_result,
                evidence=evidence, output_cfg=output_cfg, reason="unknown_numeric_claims",
            )
            if repaired:
                return repaired
            return build_grounding_fallback(evidence, mode=fallback_mode)

    # Skill-Catalog-Kontrakt
    skill_catalog_result = evaluate_skill_catalog_semantic_leakage(
        answer=answer, verified_plan=verified_plan, evidence=evidence,
    )
    if skill_catalog_result.get("violated"):
        set_runtime_grounding_value(verified_plan, execution_result, "violation_detected", True)
        set_runtime_grounding_value(verified_plan, execution_result, "fallback_used", True)
        set_runtime_grounding_value(verified_plan, execution_result, "skill_catalog_violation", skill_catalog_result)
        update_skill_catalog_trace(verified_plan, postcheck=f"repaired:{skill_catalog_result.get('reason')}")
        repaired = build_skill_catalog_safe_fallback(verified_plan, evidence)
        repaired_text = str(repaired or "").strip()
        if repaired_text:
            set_runtime_grounding_value(verified_plan, execution_result, "repair_attempted", True)
            set_runtime_grounding_value(verified_plan, execution_result, "repair_used", True)
            log_warning(f"[OutputLayer] Skill catalog postcheck repair used: reason={skill_catalog_result.get('reason')}")
            return repaired_text
        update_skill_catalog_trace(verified_plan, postcheck="fallback_summary")
        return build_grounding_fallback(evidence, mode="summarize_evidence")

    # Container-Kontrakt
    container_result = evaluate_container_contract_leakage(
        answer=answer, verified_plan=verified_plan, evidence=evidence,
    )
    if container_result.get("violated"):
        set_runtime_grounding_value(verified_plan, execution_result, "violation_detected", True)
        set_runtime_grounding_value(verified_plan, execution_result, "fallback_used", True)
        repaired = build_container_safe_fallback(verified_plan, evidence)
        repaired_text = str(repaired or "").strip()
        if repaired_text:
            set_runtime_grounding_value(verified_plan, execution_result, "repair_attempted", True)
            set_runtime_grounding_value(verified_plan, execution_result, "repair_used", True)
            log_warning(f"[OutputLayer] Container contract repair used: reason={container_result.get('reason')}")
            return repaired_text
        return build_grounding_fallback(evidence, mode="summarize_evidence")

    # Qualitative Novelty
    qualitative_guard = output_cfg.get("qualitative_claim_guard", {})
    if bool(output_cfg.get("forbid_unverified_qualitative_claims", True)):
        _effective_guard = dict(qualitative_guard)
        if _strict_no_content:
            _effective_guard["min_assertive_sentence_violations"] = 0
            _effective_guard["max_overall_novelty_ratio"] = 0.5
        qualitative_result = evaluate_qualitative_grounding(
            answer=answer,
            evidence_blob=evidence_blob,
            guard_cfg=_effective_guard,
            extract_word_tokens_fn=extract_word_tokens,
        )
        if qualitative_result.get("violated"):
            set_runtime_grounding_value(verified_plan, execution_result, "violation_detected", True)
            set_runtime_grounding_value(verified_plan, execution_result, "fallback_used", True)
            set_runtime_grounding_value(verified_plan, execution_result, "qualitative_violation", qualitative_result)
            log_warning(
                f"[OutputLayer] Grounding postcheck fallback: "
                f"qualitative novelty ratio={qualitative_result.get('overall_novelty_ratio')}"
            )
            repaired = attempt_grounding_repair_once(
                verified_plan=verified_plan, execution_result=execution_result,
                evidence=evidence, output_cfg=output_cfg, reason="qualitative_novelty",
            )
            if repaired:
                return repaired
            return build_grounding_fallback(evidence, mode=fallback_mode)

    if is_skill_catalog_context_plan(verified_plan):
        update_skill_catalog_trace(verified_plan, postcheck="passed")

    return answer
