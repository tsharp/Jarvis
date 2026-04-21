from __future__ import annotations

from typing import Any

from core.task_loop.capability_policy import requested_capability_from_tools
from core.task_loop.capabilities.container.discovery_policy import (
    has_mixed_container_flow,
    preferred_container_discovery_tools,
    split_container_tools,
)
from core.task_loop.contracts import RiskLevel, TaskLoopStepType


def build_container_step_blueprints(
    *,
    intent: str,
    objective: str,
    risk_level: RiskLevel,
    suggested_tools: list[str],
    capability_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    context = dict(capability_context or {})
    query_tools, action_tools = split_container_tools(suggested_tools)
    preferred_query_tools = preferred_container_discovery_tools(
        capability_context=context,
        suggested_tools=suggested_tools,
    )
    if preferred_query_tools:
        query_tools = preferred_query_tools
    if has_mixed_container_flow(query_tools + action_tools):
        return [
            {
                "title": f"Container-Anforderungsziel klaeren: {intent}",
                "goal": f"Festlegen, welcher Container-/Blueprint-Bedarf vorliegt: {objective}",
                "done_criteria": "Container-Ziel und Erfolgskriterium sind als sichtbarer Arbeitsauftrag formuliert.",
                "risk_level": RiskLevel.SAFE,
                "step_type": TaskLoopStepType.ANALYSIS,
                "suggested_tools": [],
                "requested_capability": {},
                "capability_context": context,
            },
            {
                "title": "Verfuegbare Blueprints oder Container-Basis pruefen",
                "goal": "Die passende Container-Basis oder Blueprint-Auswahl mit einem sicheren Query-Tool sichtbar pruefen.",
                "done_criteria": "Ein verifizierter Discovery-Befund zu verfuegbaren Blueprints oder Container-Grundlagen liegt vor.",
                "risk_level": RiskLevel.SAFE,
                "step_type": TaskLoopStepType.TOOL_EXECUTION,
                "suggested_tools": query_tools,
                "requested_capability": requested_capability_from_tools(query_tools),
                "capability_context": context,
            },
            {
                "title": "Container-Anfrage zur Freigabe vorbereiten",
                "goal": "Die eigentliche Container-Anfrage mit Ziel, Parametern und Risiken so konkret vorbereiten, dass sie bestaetigt werden kann.",
                "done_criteria": "Die Container-Anfrage ist als sichtbarer Freigabe-Schritt vorbereitet, ohne sie schon auszufuehren.",
                "risk_level": risk_level,
                "step_type": TaskLoopStepType.TOOL_REQUEST,
                "suggested_tools": action_tools,
                "requested_capability": requested_capability_from_tools(action_tools),
                "capability_context": context,
            },
            {
                "title": "Container-Anfrage ausfuehren",
                "goal": "Die freigegebene Container-Anfrage ueber den Orchestrator kontrolliert ausfuehren.",
                "done_criteria": "Ein verifizierter Tool-Befund fuer die Container-Anfrage liegt vor.",
                "risk_level": RiskLevel.SAFE,
                "step_type": TaskLoopStepType.TOOL_EXECUTION,
                "suggested_tools": action_tools,
                "requested_capability": requested_capability_from_tools(action_tools),
                "capability_context": context,
            },
            {
                "title": "Rueckfrage oder naechsten Container-Pfad zusammenfassen",
                "goal": "Den verifizierten Zwischenstand, offene Parameter und den naechsten sicheren Container-Pfad knapp zusammenfassen.",
                "done_criteria": "User sieht klar, ob Rueckfrage, Freigabe oder Ausfuehrung als naechstes ansteht.",
                "risk_level": RiskLevel.SAFE,
                "step_type": TaskLoopStepType.RESPONSE,
                "suggested_tools": [],
                "requested_capability": {},
                "capability_context": context,
            },
        ]
    return []


__all__ = ["build_container_step_blueprints"]
