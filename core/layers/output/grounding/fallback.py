"""
core.layers.output.grounding.fallback
========================================
Generische Fallback-Antworten wenn Evidence fehlt oder Tools fehlschlagen.

Zwei Modi:
  explicit_uncertainty  → "Ich habe keinen verifizierten Nachweis …"
  summarize_evidence    → "Verifizierte Ergebnisse: tool: fact …"
"""
from typing import Any, Dict, List

from core.layers.output.grounding.evidence import summarize_evidence_item


def build_grounding_fallback(
    evidence: List[Dict[str, Any]],
    *,
    mode: str = "explicit_uncertainty",
) -> str:
    """
    Baut eine generische Fallback-Antwort aus verfügbarer Evidence.

    mode='explicit_uncertainty' → nennt verifizierte Facts + Disclaimer
    mode='summarize_evidence'   → reine Fact-Liste ohne Disclaimer
    """
    mode = str(mode or "explicit_uncertainty").strip().lower()
    usable = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "")).strip().lower() != "ok":
            continue
        tool = str(item.get("tool_name", "tool")).strip()
        fact = summarize_evidence_item(item)
        if fact:
            usable.append((tool, fact))
        if len(usable) >= 3:
            break

    if mode == "summarize_evidence" and usable:
        lines = [f"- {tool}: {fact}" for tool, fact in usable]
        return "Verifizierte Ergebnisse:\n" + "\n".join(lines)

    if usable:
        lines = [f"- {tool}: {fact}" for tool, fact in usable]
        return (
            "Ich kann nur verifizierte Fakten aus den Tool-Ergebnissen ausgeben.\n"
            + "\n".join(lines)
            + "\nNicht belegbare Zusatzangaben lasse ich weg."
        )

    return (
        "Ich habe aktuell keinen verifizierten Tool-Nachweis für eine belastbare Faktenantwort. "
        "Bitte Tool-Abfrage erneut ausführen."
    )


def build_tool_failure_fallback(evidence: List[Dict[str, Any]]) -> str:
    """
    Baut eine Fallback-Antwort speziell für error/skip/partial Tool-Status.
    Listet die fehlgeschlagenen Tools mit Fehlermeldung auf.
    """
    issues = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "")).strip().lower()
        if status not in {"error", "skip", "partial", "unavailable", "routing_block"}:
            continue
        if status == "routing_block":
            continue
        tool = str(item.get("tool_name", "tool")).strip()
        fact = summarize_evidence_item(item)
        if not fact:
            continue
        issues.append((tool, status, fact))
        if len(issues) >= 3:
            break

    if not issues:
        return (
            "Tool-Ausführung war nicht erfolgreich, aber die Fehlermeldung ist unvollständig. "
            "Bitte Anfrage mit denselben Parametern erneut ausführen."
        )

    lines = [f"- {tool} [{status}]: {fact}" for tool, status, fact in issues]
    return (
        "Tool-Ausführung fehlgeschlagen:\n"
        + "\n".join(lines)
        + "\nBitte Parameter korrigieren oder den vorgeschlagenen sicheren Fallback bestätigen."
    )
