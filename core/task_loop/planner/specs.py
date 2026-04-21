from __future__ import annotations

from typing import List

from core.task_loop.capability_policy import CONTAINER_ACTION_TOOLS, capability_type_from_tools
from core.task_loop.contracts import RiskLevel
from core.task_loop.planner.objective import _clip
from core.task_loop.tool_step_policy import should_split_tool_execution


def _step3_risk_for_container(suggested_tools: List[str]) -> RiskLevel:
    """Step 3 of the container template needs confirmation only if action tools are present."""
    tool_set = set(suggested_tools)
    if CONTAINER_ACTION_TOOLS.intersection(tool_set):
        return RiskLevel.NEEDS_CONFIRMATION
    return RiskLevel.SAFE


def _is_collection_step(title: str) -> bool:
    return "angaben sammeln" in title.lower()


def _tool_focused_specs(
    *,
    intent: str,
    objective: str,
    risk_level: RiskLevel,
    suggested_tools: List[str],
) -> tuple[tuple[str, str, str, RiskLevel], ...]:
    focus = _clip(intent, 120)
    clipped_subject = _clip(objective, 180)
    capability_type = capability_type_from_tools(suggested_tools)

    if capability_type == "container_manager":
        step3_risk = _step3_risk_for_container(suggested_tools)
        if should_split_tool_execution(risk_level=step3_risk, suggested_tools=suggested_tools):
            return (
                (
                    f"Container-Anforderungsziel klaeren: {focus}",
                    f"Festlegen, welcher Container-/Blueprint-Bedarf vorliegt: {clipped_subject}",
                    "Container-Ziel und Erfolgskriterium sind als sichtbarer Arbeitsauftrag formuliert.",
                    RiskLevel.SAFE,
                ),
                (
                    "Fehlende Container-Angaben sammeln",
                    "Fehlende Angaben zu Blueprint, GPU, RAM, Laufzeit, Ports oder Freigaben gezielt herausarbeiten.",
                    "Es ist klar, welche Angaben schon vorliegen und welche Rueckfrage noch noetig ist.",
                    RiskLevel.SAFE,
                ),
                (
                    "Container-Anfrage zur Freigabe vorbereiten",
                    "Die eigentliche Container-Anfrage so konkret vorbereiten, dass Freigabe, Ziel und Risiken sichtbar und bestaetigbar sind.",
                    "Die Anfrage ist als sichtbarer Freigabe-Schritt vorbereitet, ohne sie schon auszufuehren.",
                    step3_risk,
                ),
                (
                    "Container-Anfrage ausfuehren",
                    "Die freigegebene Container-Anfrage ueber den Orchestrator kontrolliert ausfuehren.",
                    "Ein verifizierter Tool-Befund fuer die Container-Anfrage liegt vor.",
                    RiskLevel.SAFE,
                ),
                (
                    "Rueckfrage oder naechsten Container-Pfad zusammenfassen",
                    "Den verifizierten Zwischenstand, offene Parameter und den naechsten sicheren Container-Pfad knapp zusammenfassen.",
                    "User sieht klar, ob Rueckfrage, Freigabe oder Ausfuehrung als naechstes ansteht.",
                    RiskLevel.SAFE,
                ),
            )
        return (
            (
                f"Container-Anforderungsziel klaeren: {focus}",
                f"Festlegen, welcher Container-/Blueprint-Bedarf vorliegt: {clipped_subject}",
                "Container-Ziel und Erfolgskriterium sind als sichtbarer Arbeitsauftrag formuliert.",
                RiskLevel.SAFE,
            ),
            (
                "Fehlende Container-Angaben sammeln",
                "Fehlende Angaben zu Blueprint, GPU, RAM, Laufzeit, Ports oder Freigaben gezielt herausarbeiten.",
                "Es ist klar, welche Angaben schon vorliegen und welche Rueckfrage noch noetig ist.",
                RiskLevel.SAFE,
            ),
            (
                "Container-Anfrage kontrolliert vorbereiten",
                "Die eigentliche Container-Anfrage so vorbereiten, dass sie ueber den Orchestrator kontrolliert ausgefuehrt oder gezielt angehalten werden kann.",
                "Der Schritt ist als kontrollierbarer Tool-Pfad oder als konkrete Rueckfrage materialisiert.",
                step3_risk,
            ),
            (
                "Rueckfrage oder naechsten Container-Pfad zusammenfassen",
                "Den verifizierten Zwischenstand, offene Parameter und den naechsten sicheren Container-Pfad knapp zusammenfassen.",
                "User sieht klar, ob Rueckfrage, Freigabe oder Ausfuehrung als naechstes ansteht.",
                RiskLevel.SAFE,
            ),
        )

    if capability_type == "skill_cron":
        if should_split_tool_execution(risk_level=risk_level, suggested_tools=suggested_tools):
            return (
                (
                    f"Skill-/Cron-Ziel klaeren: {focus}",
                    f"Festlegen, welcher Skill- oder Cron-Bedarf vorliegt: {clipped_subject}",
                    "Skill-/Cron-Ziel und Erfolgskriterium sind sichtbar formuliert.",
                    RiskLevel.SAFE,
                ),
                (
                    "Fehlende Skill-/Cron-Angaben sammeln",
                    "Fehlende Angaben zu Skill, Schedule, Zielsystem oder Parametern gezielt herausarbeiten.",
                    "Es ist klar, welche Angaben fehlen und ob Rueckfragen noetig sind.",
                    RiskLevel.SAFE,
                ),
                (
                    "Skill-/Cron-Schritt zur Freigabe vorbereiten",
                    "Die konkrete Skill-/Cron-Aktion so vorbereiten, dass sie bestaetigt werden kann, ohne sie schon auszufuehren.",
                    "Freigabe, Ziel und Risiko des Skill-/Cron-Schritts sind sichtbar vorbereitet.",
                    risk_level,
                ),
                (
                    "Skill-/Cron-Schritt ausfuehren",
                    "Die freigegebene Skill-/Cron-Aktion ueber den Orchestrator kontrolliert ausfuehren.",
                    "Ein verifizierter Ausfuehrungsbefund liegt vor.",
                    RiskLevel.SAFE,
                ),
                (
                    "Rueckfrage oder naechsten Skill-/Cron-Pfad zusammenfassen",
                    "Den verifizierten Zwischenstand, offene Parameter und den naechsten sicheren Skill-/Cron-Pfad knapp zusammenfassen.",
                    "User sieht klar, ob Rueckfrage, Freigabe oder Ausfuehrung als naechstes ansteht.",
                    RiskLevel.SAFE,
                ),
            )
        return (
            (
                f"Skill-/Cron-Ziel klaeren: {focus}",
                f"Festlegen, welcher Skill- oder Cron-Bedarf vorliegt: {clipped_subject}",
                "Skill-/Cron-Ziel und Erfolgskriterium sind sichtbar formuliert.",
                RiskLevel.SAFE,
            ),
            (
                "Fehlende Skill-/Cron-Angaben sammeln",
                "Fehlende Angaben zu Skill, Schedule, Zielsystem oder Parametern gezielt herausarbeiten.",
                "Es ist klar, welche Angaben fehlen und ob Rueckfragen noetig sind.",
                RiskLevel.SAFE,
            ),
            (
                "Skill-/Cron-Schritt kontrolliert vorbereiten",
                "Die konkrete Skill-/Cron-Aktion so vorbereiten, dass sie ueber den Orchestrator kontrolliert ausgefuehrt oder angehalten werden kann.",
                "Der Schritt ist als kontrollierbarer Tool-Pfad oder als konkrete Rueckfrage materialisiert.",
                risk_level,
            ),
            (
                "Rueckfrage oder naechsten Skill-/Cron-Pfad zusammenfassen",
                "Den verifizierten Zwischenstand, offene Parameter und den naechsten sicheren Skill-/Cron-Pfad knapp zusammenfassen.",
                "User sieht klar, ob Rueckfrage, Freigabe oder Ausfuehrung als naechstes ansteht.",
                RiskLevel.SAFE,
            ),
        )

    if capability_type == "mcp":
        if should_split_tool_execution(risk_level=risk_level, suggested_tools=suggested_tools):
            return (
                (
                    f"MCP-Ziel klaeren: {focus}",
                    f"Festlegen, welche MCP-Capability gefragt ist: {clipped_subject}",
                    "MCP-Ziel und Erfolgskriterium sind sichtbar formuliert.",
                    RiskLevel.SAFE,
                ),
                (
                    "Fehlende MCP-Angaben sammeln",
                    "Fehlende Angaben zu Ziel, Scope, Parametern oder Sicherheitsgrenzen gezielt herausarbeiten.",
                    "Es ist klar, welche Angaben fehlen und ob Rueckfragen noetig sind.",
                    RiskLevel.SAFE,
                ),
                (
                    "MCP-Schritt zur Freigabe vorbereiten",
                    "Die konkrete MCP-Aktion so vorbereiten, dass sie bestaetigt werden kann, ohne sie schon auszufuehren.",
                    "Freigabe, Ziel und Risiko des MCP-Schritts sind sichtbar vorbereitet.",
                    risk_level,
                ),
                (
                    "MCP-Schritt ausfuehren",
                    "Die freigegebene MCP-Aktion ueber den Orchestrator kontrolliert ausfuehren.",
                    "Ein verifizierter MCP-Ausfuehrungsbefund liegt vor.",
                    RiskLevel.SAFE,
                ),
                (
                    "Rueckfrage oder naechsten MCP-Pfad zusammenfassen",
                    "Den verifizierten Zwischenstand, offene Parameter und den naechsten sicheren MCP-Pfad knapp zusammenfassen.",
                    "User sieht klar, ob Rueckfrage, Freigabe oder Ausfuehrung als naechstes ansteht.",
                    RiskLevel.SAFE,
                ),
            )
        return (
            (
                f"MCP-Ziel klaeren: {focus}",
                f"Festlegen, welche MCP-Capability gefragt ist: {clipped_subject}",
                "MCP-Ziel und Erfolgskriterium sind sichtbar formuliert.",
                RiskLevel.SAFE,
            ),
            (
                "Fehlende MCP-Angaben sammeln",
                "Fehlende Angaben zu Ziel, Scope, Parametern oder Sicherheitsgrenzen gezielt herausarbeiten.",
                "Es ist klar, welche Angaben fehlen und ob Rueckfragen noetig sind.",
                RiskLevel.SAFE,
            ),
            (
                "MCP-Schritt kontrolliert vorbereiten",
                "Die konkrete MCP-Aktion so vorbereiten, dass sie ueber den Orchestrator kontrolliert ausgefuehrt oder angehalten werden kann.",
                "Der Schritt ist als kontrollierbarer Tool-Pfad oder als konkrete Rueckfrage materialisiert.",
                risk_level,
            ),
            (
                "Rueckfrage oder naechsten MCP-Pfad zusammenfassen",
                "Den verifizierten Zwischenstand, offene Parameter und den naechsten sicheren MCP-Pfad knapp zusammenfassen.",
                "User sieht klar, ob Rueckfrage, Freigabe oder Ausfuehrung als naechstes ansteht.",
                RiskLevel.SAFE,
            ),
        )

    if should_split_tool_execution(risk_level=risk_level, suggested_tools=suggested_tools):
        return (
            (
                f"Tool-Ziel klaeren: {focus}",
                f"Festlegen, welcher Tool-Bedarf vorliegt: {clipped_subject}",
                "Tool-Ziel und Erfolgskriterium sind sichtbar formuliert.",
                RiskLevel.SAFE,
            ),
            (
                "Fehlende Tool-Angaben sammeln",
                "Fehlende Angaben zu Ziel, Parametern, Grenzen oder Freigaben gezielt herausarbeiten.",
                "Es ist klar, welche Angaben fehlen und ob Rueckfragen noetig sind.",
                RiskLevel.SAFE,
            ),
            (
                "Tool-Schritt zur Freigabe vorbereiten",
                "Die konkrete Tool-Aktion so vorbereiten, dass sie bestaetigt werden kann, ohne sie schon auszufuehren.",
                "Freigabe, Ziel und Risiko des Tool-Schritts sind sichtbar vorbereitet.",
                risk_level,
            ),
            (
                "Tool-Schritt ausfuehren",
                "Die freigegebene Tool-Aktion ueber den Orchestrator kontrolliert ausfuehren.",
                "Ein verifizierter Tool-Befund liegt vor.",
                RiskLevel.SAFE,
            ),
            (
                "Rueckfrage oder naechsten Tool-Pfad zusammenfassen",
                "Den verifizierten Zwischenstand, offene Parameter und den naechsten sicheren Tool-Pfad knapp zusammenfassen.",
                "User sieht klar, ob Rueckfrage, Freigabe oder Ausfuehrung als naechstes ansteht.",
                RiskLevel.SAFE,
            ),
        )
    return (
        (
            f"Tool-Ziel klaeren: {focus}",
            f"Festlegen, welcher Tool-Bedarf vorliegt: {clipped_subject}",
            "Tool-Ziel und Erfolgskriterium sind sichtbar formuliert.",
            RiskLevel.SAFE,
        ),
        (
            "Fehlende Tool-Angaben sammeln",
            "Fehlende Angaben zu Ziel, Parametern, Grenzen oder Freigaben gezielt herausarbeiten.",
            "Es ist klar, welche Angaben fehlen und ob Rueckfragen noetig sind.",
            RiskLevel.SAFE,
        ),
        (
            "Tool-Schritt kontrolliert vorbereiten",
            "Die konkrete Tool-Aktion so vorbereiten, dass sie ueber den Orchestrator kontrolliert ausgefuehrt oder angehalten werden kann.",
            "Der Schritt ist als kontrollierbarer Tool-Pfad oder als konkrete Rueckfrage materialisiert.",
            risk_level,
        ),
        (
            "Rueckfrage oder naechsten Tool-Pfad zusammenfassen",
            "Den verifizierten Zwischenstand, offene Parameter und den naechsten sicheren Tool-Pfad knapp zusammenfassen.",
            "User sieht klar, ob Rueckfrage, Freigabe oder Ausfuehrung als naechstes ansteht.",
            RiskLevel.SAFE,
        ),
    )


__all__ = [
    "_is_collection_step",
    "_step3_risk_for_container",
    "_tool_focused_specs",
]
