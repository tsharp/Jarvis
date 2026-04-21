"""
core.layers.output.contracts.skill_catalog.snapshot
=====================================================
Evidence-Parsing für Skill-Catalog-Turns.

Extrahiert aus Tool-Evidence-Items einen strukturierten Snapshot:
installed_count, draft_count, names, session_skills_verified, draft_inventory_verified.
"""
from typing import Any, Dict, List

from core.layers.output.analysis.qualitative import normalize_semantic_text, to_int
from core.layers.output.contracts.skill_catalog.trace import is_skill_catalog_context_plan


def collect_skill_catalog_fact_lines(item: Dict[str, Any]) -> List[str]:
    """
    Extrahiert alle nicht-leeren Fact-Zeilen aus einem Evidence-Item
    (key_facts + structured output/result).
    """
    if not isinstance(item, dict):
        return []

    lines: List[str] = []
    key_facts = item.get("key_facts")
    if isinstance(key_facts, list):
        lines.extend(str(raw or "").strip() for raw in key_facts if str(raw or "").strip())

    structured = item.get("structured")
    if isinstance(structured, dict):
        output_text = str(structured.get("output") or structured.get("result") or "").strip()
        if output_text:
            lines.extend(
                str(raw or "").strip()
                for raw in output_text.splitlines()
                if str(raw or "").strip()
            )
    return lines


def extract_skill_catalog_snapshot(
    verified_plan: Dict[str, Any],
    evidence: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Baut einen vollständigen Skill-Catalog-Snapshot aus Plan-Kontext und Evidence.

    Liefert:
      installed_count, draft_count, available_count,
      installed_names, draft_names, selected_docs,
      session_skills_verified, draft_inventory_verified
    """
    ctx = (
        verified_plan.get("_skill_catalog_context")
        if isinstance(verified_plan, dict)
        else {}
    )
    ctx = ctx if isinstance(ctx, dict) else {}
    snapshot = {
        "installed_count": to_int(ctx.get("installed_count")),
        "draft_count": None,
        "available_count": to_int(ctx.get("available_count")),
        "installed_names": [],
        "draft_names": [],
        "selected_docs": str(ctx.get("selected_docs") or "").strip(),
        "session_skills_verified": bool(ctx.get("session_skills_verified")),
        "draft_inventory_verified": False,
    }

    for item in evidence:
        if not isinstance(item, dict):
            continue
        tool_name = str(item.get("tool_name") or "").strip()
        status = str(item.get("status") or "").strip().lower()
        structured = item.get("structured")

        if tool_name == "list_skills" and isinstance(structured, dict):
            if snapshot["installed_count"] is None:
                snapshot["installed_count"] = to_int(structured.get("installed_count"))
            if snapshot["available_count"] is None:
                snapshot["available_count"] = to_int(structured.get("available_count"))
            raw_names = structured.get("installed_names")
            if isinstance(raw_names, list) and not snapshot["installed_names"]:
                snapshot["installed_names"] = [
                    str(raw or "").strip()
                    for raw in raw_names
                    if str(raw or "").strip()
                ][:8]

        elif tool_name == "list_draft_skills" and status == "ok" and isinstance(structured, dict):
            snapshot["draft_inventory_verified"] = True
            if snapshot["draft_count"] is None:
                snapshot["draft_count"] = to_int(structured.get("draft_count"))
            raw_names = structured.get("draft_names")
            if isinstance(raw_names, list) and not snapshot["draft_names"]:
                snapshot["draft_names"] = [
                    str(raw or "").strip()
                    for raw in raw_names
                    if str(raw or "").strip()
                ][:8]

        for line in collect_skill_catalog_fact_lines(item):
            low = line.lower()
            if tool_name == "list_skills":
                if low.startswith("installed_count:") and snapshot["installed_count"] is None:
                    snapshot["installed_count"] = to_int(line.split(":", 1)[1].strip())
                elif low.startswith("available_count:") and snapshot["available_count"] is None:
                    snapshot["available_count"] = to_int(line.split(":", 1)[1].strip())
                elif low.startswith("installed_names:") and not snapshot["installed_names"]:
                    rhs = line.split(":", 1)[1].strip()
                    if rhs:
                        snapshot["installed_names"] = [
                            part.strip() for part in rhs.split(",") if str(part or "").strip()
                        ][:8]
            elif tool_name == "list_draft_skills" and status == "ok":
                snapshot["draft_inventory_verified"] = True
                if low.startswith("draft_count:") and snapshot["draft_count"] is None:
                    snapshot["draft_count"] = to_int(line.split(":", 1)[1].strip())
                elif low.startswith("draft_names:") and not snapshot["draft_names"]:
                    rhs = line.split(":", 1)[1].strip()
                    if rhs:
                        snapshot["draft_names"] = [
                            part.strip() for part in rhs.split(",") if str(part or "").strip()
                        ][:8]
            elif tool_name not in {"skill_addons"}:
                normalized = normalize_semantic_text(line)
                if "session-skill" in normalized or "system-skill" in normalized:
                    snapshot["session_skills_verified"] = True

    return snapshot
