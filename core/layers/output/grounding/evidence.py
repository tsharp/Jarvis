"""
core.layers.output.grounding.evidence
========================================
Evidence-Sammlung und -Summarisierung für das Grounding-System.

Sammelt Tool-Evidence aus Plan, Carryover und memory_data,
prüft ob Items verwertbaren Inhalt haben und fasst sie zusammen.
"""
from typing import Any, Dict, List

from core.layers.output.analysis.evidence_summary import (
    summarize_list_skills_evidence,
    summarize_skill_registry_snapshot_evidence,
    summarize_skill_addons_evidence,
)
from core.layers.output.analysis.qualitative import summarize_structured_output


def collect_grounding_evidence(
    verified_plan: Dict[str, Any],
    memory_data: str,
) -> List[Dict[str, Any]]:
    """
    Sammelt alle Evidence-Items aus:
      - plan._grounding_evidence (via get_runtime_grounding_evidence)
      - plan._carryover_grounding_evidence
      - plan._execution_result.tool_statuses (Fallback)
      - TOOL-CARD Zeilen in memory_data (Fallback-Parser)
    Dedupliziert via (tool_name, ref_id, status, len(key_facts)).
    """
    from core.plan_runtime_bridge import (
        get_runtime_grounding_evidence,
        get_runtime_carryover_grounding_evidence,
    )

    evidence: List[Dict[str, Any]] = []
    seen = set()

    def _push(item: Any) -> None:
        if not isinstance(item, dict):
            return
        tool_name = str(item.get("tool_name", "")).strip()
        ref_id = str(item.get("ref_id", "")).strip()
        status = str(item.get("status", "")).strip().lower()
        sig = (
            tool_name,
            ref_id,
            status,
            len(item.get("key_facts", []) if isinstance(item.get("key_facts"), list) else []),
        )
        if sig in seen:
            return
        seen.add(sig)
        evidence.append(item)

    from_plan = get_runtime_grounding_evidence(verified_plan)
    if isinstance(from_plan, list):
        for item in from_plan:
            _push(item)

    carryover = get_runtime_carryover_grounding_evidence(verified_plan)
    if isinstance(carryover, list):
        for item in carryover:
            _push(item)

    exec_result = (verified_plan or {}).get("_execution_result") or {}
    for ts in exec_result.get("tool_statuses", []):
        if isinstance(ts, dict):
            _push(ts)

    if memory_data:
        for line in str(memory_data).splitlines():
            stripped = line.strip()
            if not stripped.startswith("[TOOL-CARD:") or "|" not in stripped:
                continue
            body = stripped[len("[TOOL-CARD:"):].rstrip("]").strip()
            parts = [p.strip() for p in body.split("|")]
            if len(parts) < 3:
                continue
            status_part = parts[1].lower()
            status = "unknown"
            if " ok" in status_part or status_part.endswith("ok"):
                status = "ok"
            elif "error" in status_part:
                status = "error"
            elif "partial" in status_part:
                status = "partial"
            ref_part = parts[2].lower()
            ref_id = ""
            if ref_part.startswith("ref:"):
                ref_id = ref_part.split("ref:", 1)[1].strip()
            _push({"tool_name": parts[0], "status": status, "ref_id": ref_id, "key_facts": []})

    return evidence


def evidence_item_has_extractable_content(item: Dict[str, Any]) -> bool:
    """Prüft ob ein Evidence-Item verwertbaren Inhalt hat (facts / structured / metrics)."""
    if not isinstance(item, dict):
        return False
    facts = item.get("key_facts")
    if isinstance(facts, list):
        for entry in facts:
            if str(entry or "").strip():
                return True
    structured = item.get("structured")
    if isinstance(structured, dict):
        output_text = str(
            structured.get("output") or structured.get("result") or ""
        ).strip()
        if output_text:
            return True
    metrics = item.get("metrics")
    if isinstance(metrics, dict):
        return bool(metrics)
    if isinstance(metrics, list):
        return any(
            isinstance(metric, dict)
            and str(metric.get("key") or metric.get("name") or "").strip()
            for metric in metrics
        )
    return False


def summarize_evidence_item(item: Dict[str, Any]) -> str:
    """
    Fasst ein Evidence-Item zu einem lesbaren String zusammen.
    Delegiert an tool-spezifische Summarizer, fällt auf structured/metrics/key_facts zurück.
    """
    if not isinstance(item, dict):
        return ""
    tool = str(item.get("tool_name", "tool")).strip()
    fact = ""

    if tool == "list_skills":
        fact = summarize_list_skills_evidence(item)
    elif tool == "skill_registry_snapshot":
        fact = summarize_skill_registry_snapshot_evidence(item)
    elif tool == "skill_addons":
        fact = summarize_skill_addons_evidence(item)

    structured = item.get("structured")
    if isinstance(structured, dict):
        output_text = str(
            structured.get("output") or structured.get("result") or ""
        ).strip()
        if output_text:
            fact = summarize_structured_output(output_text, max_lines=4)
        if not fact:
            err_text = str(
                structured.get("error")
                or structured.get("message")
                or structured.get("reason")
                or ""
            ).strip()
            if err_text:
                fact = summarize_structured_output(err_text, max_lines=4)

    if not fact:
        metrics = item.get("metrics")
        if isinstance(metrics, dict) and metrics:
            fact = ", ".join(f"{k}={v}" for k, v in list(metrics.items())[:4])
        elif isinstance(metrics, list):
            chunks = []
            for metric in metrics[:4]:
                if not isinstance(metric, dict):
                    continue
                key = str(metric.get("key") or metric.get("name") or "").strip()
                if not key:
                    continue
                chunks.append(f"{key}={metric.get('value')}{metric.get('unit') or ''}")
            if chunks:
                fact = ", ".join(chunks)

    if not fact:
        facts = item.get("key_facts")
        if isinstance(facts, list) and facts:
            import json
            fact = summarize_structured_output(
                "\n".join(str(f or "").strip() for f in facts[:8] if str(f or "").strip()),
                max_lines=4,
            )
            if fact.startswith("{") and fact.endswith("}"):
                try:
                    parsed_fact = json.loads(fact)
                    if isinstance(parsed_fact, dict):
                        out_text = str(
                            parsed_fact.get("output")
                            or parsed_fact.get("result")
                            or parsed_fact.get("error")
                            or parsed_fact.get("message")
                            or ""
                        ).strip()
                        if out_text:
                            fact = summarize_structured_output(out_text, max_lines=4)
                except Exception:
                    pass

    if not fact:
        fact = str(item.get("reason") or "").strip()
    return fact


def collect_evidence_text_parts(evidence: List[Dict[str, Any]]) -> List[str]:
    """
    Flacht alle Evidence-Items zu einer flachen Liste von Strings ab.
    Wird vom qualitative-Novelty-Check als Evidence-Blob verwendet.
    """
    evidence_text_parts: List[str] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        facts = item.get("key_facts")
        if isinstance(facts, list):
            evidence_text_parts.extend(str(x) for x in facts if str(x).strip())
        metrics = item.get("metrics")
        if isinstance(metrics, dict):
            evidence_text_parts.extend(str(v) for v in metrics.values())
        elif isinstance(metrics, list):
            for metric in metrics:
                if not isinstance(metric, dict):
                    continue
                val = metric.get("value")
                unit = metric.get("unit")
                if val is not None:
                    evidence_text_parts.append(f"{val}{unit or ''}")
        structured = item.get("structured")
        if isinstance(structured, dict):
            for val in structured.values():
                if isinstance(val, (str, int, float)):
                    evidence_text_parts.append(str(val))
    return evidence_text_parts
