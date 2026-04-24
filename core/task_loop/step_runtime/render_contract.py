"""Generic step-runtime rendering contract.

Ziel:
- festhalten, was ein Step-Typ sagen darf
- trennen zwischen Plan, Aktion, verifiziertem Ergebnis und offenem Punkt
- keine domain-spezifischen Container-/Skill-/Cron-Regeln hier
"""

from __future__ import annotations

from typing import Dict, List

from core.task_loop.contracts import TaskLoopStepType


def allowed_render_claims(
    *,
    step_type: TaskLoopStepType,
    has_verified_tool_result: bool = False,
    has_runtime_fact_context: bool = False,
) -> Dict[str, bool]:
    """Return generic per-step claim permissions."""
    return {
        "may_claim_plan_state": bool(step_type in {TaskLoopStepType.ANALYSIS, TaskLoopStepType.TOOL_REQUEST, TaskLoopStepType.RESPONSE}),
        "may_claim_missing_information": bool(step_type in {TaskLoopStepType.ANALYSIS, TaskLoopStepType.TOOL_REQUEST}),
        "may_claim_tool_execution": bool(
            step_type is TaskLoopStepType.TOOL_EXECUTION and has_verified_tool_result
        ),
        "may_claim_verified_result": bool(has_verified_tool_result),
        "may_claim_runtime_facts": bool(has_runtime_fact_context and has_verified_tool_result),
        "may_summarize_progress": bool(step_type in {TaskLoopStepType.RESPONSE, TaskLoopStepType.TOOL_EXECUTION}),
    }


def focus_block(step_type: TaskLoopStepType, suggested_tools: List[str]) -> str:
    capability_scope = ", ".join(suggested_tools) if suggested_tools else "keine"
    if step_type is TaskLoopStepType.TOOL_REQUEST:
        return (
            "Loop-Fokus:\n"
            "- Bearbeite nur den Vorbereitungs- oder Rueckfrage-Schritt.\n"
            "- Halte fehlende Angaben, bekannte Fakten und den naechsten sicheren Schritt getrennt.\n"
            f"- Betroffene Capability: {capability_scope}\n"
        )
    if step_type is TaskLoopStepType.TOOL_EXECUTION:
        return (
            "Loop-Fokus:\n"
            "- Bearbeite nur den aktuellen Ausfuehrungsschritt.\n"
            "- Berichte nur den fuer diesen Schritt verifizierten Befund.\n"
            f"- Betroffene Capability: {capability_scope}\n"
        )
    if step_type is TaskLoopStepType.RESPONSE:
        return (
            "Loop-Fokus:\n"
            "- Fasse nur den erreichten Zwischenstand dieses Loop-Pfads zusammen.\n"
            "- Ziehe keine neue Nebenaufgabe auf.\n"
        )
    return (
        "Loop-Fokus:\n"
        "- Bearbeite nur den aktuellen Analyseschritt.\n"
        "- Halte die Ursprungsaufgabe ueber den gesamten Loop stabil.\n"
    )


def output_shape_block(step_type: TaskLoopStepType) -> str:
    if step_type is TaskLoopStepType.TOOL_REQUEST:
        return (
            "Inhaltliche Bausteine fuer die Antwort:\n"
            "- gesicherter Zwischenstand\n"
            "- was fuer die Anfrage noch fehlt oder schon vorliegt\n"
            "- naechster sichtbarer Schritt\n"
            "Formuliere diese Bausteine natuerlich in 1-3 kurzen Saetzen. "
            "Nutze keine starren Labels wie `Aktueller Status`, `Offener Punkt` oder `Naechster Schritt`, "
            "ausser der User fragt explizit nach einer Checkliste.\n"
        )
    return (
        "Inhaltliche Bausteine fuer die Antwort:\n"
        "- konkreter Zwischenstand dieses Schritts\n"
        "- verbleibende Unsicherheit oder offener Punkt\n"
        "- naechster sinnvoller Schritt\n"
        "Formuliere diese Bausteine natuerlich in 1-3 kurzen Saetzen. "
        "Nutze keine starren Labels wie `Aktueller Status`, `Offener Punkt` oder `Naechster Schritt`, "
        "ausser der User fragt explizit nach einer Checkliste.\n"
    )


def response_style_block(step_type: TaskLoopStepType) -> str:
    _ = step_type
    return (
        "Antwortstil:\n"
        "- Schreibe wie ein pragmatischer Agent, nicht wie ein Formular.\n"
        "- Bleibe evidenzgebunden: nicht spekulieren, aber auch keine unnoetige Sicherheitsfloskel wiederholen.\n"
        "- Wenn etwas blockiert ist, sag direkt was blockiert und welchen konkreten Schritt du als naechstes brauchst.\n"
    )


def claim_guard_block(
    *,
    step_type: TaskLoopStepType,
    has_verified_tool_result: bool = False,
    has_runtime_fact_context: bool = False,
) -> str:
    claims = allowed_render_claims(
        step_type=step_type,
        has_verified_tool_result=has_verified_tool_result,
        has_runtime_fact_context=has_runtime_fact_context,
    )
    lines = ["Behauptungsrahmen:"]
    if claims["may_claim_plan_state"]:
        lines.append("- Beschreibe den aktiven Schritt, den gesicherten Zwischenstand und den naechsten Schritt.")
    if claims["may_claim_missing_information"]:
        lines.append("- Fehlende Informationen duerfen benannt werden, aber nicht als bereits bekannt dargestellt werden.")
    if not claims["may_claim_tool_execution"]:
        lines.append("- Behaupte keine Tool-Ausfuehrung in diesem Schritt.")
    if not claims["may_claim_verified_result"]:
        lines.append("- Behaupte kein Tool-Ergebnis oder keinen abgeschlossenen Runtime-Befund.")
    if not claims["may_claim_runtime_facts"]:
        lines.append("- Behaupte keine Runtime-, System- oder Memory-Fakten ohne verifizierten Befund.")
    if claims["may_summarize_progress"]:
        lines.append("- Fasse Fortschritt nur auf Basis verifizierter Ergebnisse zusammen.")
    return "\n".join(lines) + "\n"


__all__ = [
    "allowed_render_claims",
    "claim_guard_block",
    "focus_block",
    "output_shape_block",
    "response_style_block",
]
