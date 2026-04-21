"""
core.layers.output.analysis.evidence_summary
=============================================
Formatierte Zusammenfassungen spezifischer Tool-Ergebnisse.

Liest rohe Tool-Evidence-Items und erzeugt daraus kompakte,
menschenlesbare Strings für die Grounding-Ausgabe.

Unterstützte Tools:
  list_skills              → "Runtime-Skills: 3 installiert (skill-a, skill-b)"
  skill_registry_snapshot  → "Skill-Registry: 2 aktiv, 1 Draft"
  skill_addons             → "Skill-Semantik: Docs: xyz; ..."
"""
import ast
import json
from typing import Any, Dict, List, Optional

from core.layers.output.analysis.qualitative import summarize_structured_output, to_int


def summarize_list_skills_evidence(item: Dict[str, Any]) -> str:
    """
    Liest ein `list_skills` Evidence-Item und gibt eine kompakte
    Runtime-Skills-Zusammenfassung zurück.
    """
    if not isinstance(item, dict):
        return ""

    structured = item.get("structured")
    installed_count: Optional[int] = None
    available_count: Optional[int] = None
    installed_names: List[str] = []

    if isinstance(structured, dict):
        installed_count = to_int(structured.get("installed_count"))
        available_count = to_int(structured.get("available_count"))
        raw_names = structured.get("installed_names")
        if isinstance(raw_names, list):
            for raw in raw_names:
                name = str(raw or "").strip()
                if name:
                    installed_names.append(name)

    if not installed_names or installed_count is None or available_count is None:
        facts = item.get("key_facts")
        if isinstance(facts, list):
            for raw in facts:
                line = str(raw or "").strip()
                if not line:
                    continue
                low = line.lower()
                if low.startswith("installed_count:"):
                    installed_count = to_int(line.split(":", 1)[1].strip())
                elif low.startswith("available_count:"):
                    available_count = to_int(line.split(":", 1)[1].strip())
                elif low.startswith("installed_names:"):
                    rhs = line.split(":", 1)[1].strip()
                    if rhs:
                        installed_names = [
                            part.strip()
                            for part in rhs.split(",")
                            if str(part or "").strip()
                        ]
                else:
                    candidate = line
                    if ":" in line and low.startswith("list_skills"):
                        candidate = line.split(":", 1)[1].strip()
                    parsed = None
                    if candidate.startswith("{") and candidate.endswith("}"):
                        try:
                            parsed = json.loads(candidate)
                        except Exception:
                            try:
                                parsed = ast.literal_eval(candidate)
                            except Exception:
                                parsed = None
                    if isinstance(parsed, dict) and (
                        "installed_count" in parsed
                        or "installed" in parsed
                        or "available_count" in parsed
                    ):
                        rows = parsed.get("installed")
                        installed_rows = rows if isinstance(rows, list) else []
                        avail_rows = parsed.get("available")
                        available_rows = avail_rows if isinstance(avail_rows, list) else []
                        if installed_count is None:
                            try:
                                installed_count = int(parsed.get("installed_count"))
                            except Exception:
                                installed_count = len(installed_rows)
                        if available_count is None:
                            try:
                                available_count = int(parsed.get("available_count"))
                            except Exception:
                                available_count = len(available_rows)
                        if not installed_names:
                            for row in installed_rows:
                                if not isinstance(row, dict):
                                    continue
                                name = str(row.get("name") or "").strip()
                                if name:
                                    installed_names.append(name)
                                if len(installed_names) >= 8:
                                    break

    if installed_count is None and installed_names:
        installed_count = len(installed_names)

    if installed_count is None and available_count is None and not installed_names:
        return ""

    parts = []
    if installed_count is not None:
        if installed_names:
            shown = ", ".join(installed_names[:6])
            if installed_count > len(installed_names):
                shown = f"{shown} (+{installed_count - len(installed_names)} weitere)"
            parts.append(f"{installed_count} installiert ({shown})")
        else:
            parts.append(f"{installed_count} installiert")
    elif installed_names:
        parts.append("installiert: " + ", ".join(installed_names[:6]))

    if available_count is not None:
        parts.append(f"{available_count} verfügbar")

    if not parts:
        return ""
    return "Runtime-Skills: " + "; ".join(parts)


def summarize_skill_registry_snapshot_evidence(item: Dict[str, Any]) -> str:
    """
    Liest ein `skill_registry_snapshot` Evidence-Item und gibt eine kompakte
    Skill-Registry-Zusammenfassung zurück.
    """
    if not isinstance(item, dict):
        return ""

    active_count: Optional[int] = None
    draft_count: Optional[int] = None
    active_names: List[str] = []
    draft_names: List[str] = []

    structured = item.get("structured")
    if isinstance(structured, dict):
        output_text = str(structured.get("output") or structured.get("result") or "").strip()
        if output_text:
            facts = [line.strip() for line in output_text.splitlines() if line.strip()]
        else:
            facts = []
    else:
        facts = []

    raw_facts = item.get("key_facts")
    if isinstance(raw_facts, list):
        facts.extend(str(x or "").strip() for x in raw_facts if str(x or "").strip())

    for line in facts:
        low = line.lower()
        if low.startswith("active_count:"):
            active_count = to_int(line.split(":", 1)[1].strip())
        elif low.startswith("draft_count:"):
            draft_count = to_int(line.split(":", 1)[1].strip())
        elif low.startswith("active_names:"):
            rhs = line.split(":", 1)[1].strip()
            if rhs:
                active_names = [part.strip() for part in rhs.split(",") if str(part or "").strip()]
        elif low.startswith("draft_names:"):
            rhs = line.split(":", 1)[1].strip()
            if rhs:
                draft_names = [part.strip() for part in rhs.split(",") if str(part or "").strip()]

    if active_count is None and draft_count is None and not draft_names and not active_names:
        return ""

    parts = []
    if active_count is not None:
        if active_names:
            shown = ", ".join(active_names[:6])
            if active_count > len(active_names):
                shown = f"{shown} (+{active_count - len(active_names)} weitere)"
            parts.append(f"{active_count} aktiv ({shown})")
        else:
            parts.append(f"{active_count} aktiv")
    if draft_count is not None:
        if draft_names:
            shown = ", ".join(draft_names[:6])
            if draft_count > len(draft_names):
                shown = f"{shown} (+{draft_count - len(draft_names)} weitere)"
            parts.append(f"{draft_count} Drafts ({shown})")
        else:
            parts.append(f"{draft_count} Drafts")
    if not parts:
        return ""
    return "Skill-Registry: " + "; ".join(parts)


def summarize_skill_addons_evidence(item: Dict[str, Any]) -> str:
    """
    Liest ein `skill_addons` Evidence-Item und gibt eine kompakte
    Skill-Semantik-Zusammenfassung zurück.
    """
    if not isinstance(item, dict):
        return ""

    selected_docs = ""
    context_lines: List[str] = []
    facts = item.get("key_facts")
    if isinstance(facts, list):
        for raw in facts:
            line = str(raw or "").strip()
            if not line:
                continue
            low = line.lower()
            if low.startswith("selected_docs:"):
                selected_docs = line.split(":", 1)[1].strip()
                continue
            if line.startswith("Skill Addon:") or line.startswith("Scope:"):
                continue
            context_lines.append(line)

    if not context_lines:
        structured = item.get("structured")
        if isinstance(structured, dict):
            output_text = str(structured.get("output") or structured.get("result") or "").strip()
            for raw in output_text.splitlines():
                line = str(raw or "").strip()
                if not line or line.startswith("Skill Addon:") or line.startswith("Scope:"):
                    continue
                if line.lower().startswith("selected_docs:"):
                    selected_docs = line.split(":", 1)[1].strip()
                    continue
                context_lines.append(line)

    if not context_lines and not selected_docs:
        return ""

    parts: List[str] = []
    if selected_docs:
        parts.append(f"Docs: {selected_docs}")
    if context_lines:
        summary = summarize_structured_output("\n".join(context_lines), max_lines=3)
        if summary:
            parts.append(summary)
    if not parts:
        return ""
    return "Skill-Semantik: " + "; ".join(parts)
