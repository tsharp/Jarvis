"""Dispatch generic action resolution into capability-specific resolvers.

Wenn ein Step kein explizites requested_capability traegt, bewertet
assess_tool_utility() den Intent-Text und befuellt requested_capability
automatisch. Ergebnis ist eine ActionResolutionDecision mit
source=DOMAIN_DISPATCH und dem Assessment als Metadata.
"""
from __future__ import annotations

from typing import Any

from core.task_loop.action_resolution.contracts import (
    ActionResolutionDecision,
    ActionResolutionMode,
    ActionResolutionSource,
    ResolvedLoopAction,
)
from core.task_loop.action_resolution.tool_utility_policy import (
    CapabilityFamily,
    ExecutionMode,
    ToolUtilityAssessment,
    assess_tool_utility,
)

_MIN_CONFIDENCE = 0.1

# Capability-family → capability_type key (matching existing auto_clarify convention)
_CAPABILITY_TYPE_MAP: dict[CapabilityFamily, str] = {
    CapabilityFamily.container: "container_manager",
    CapabilityFamily.skill: "skill",
    CapabilityFamily.cron: "cron",
    CapabilityFamily.mcp: "mcp",
    CapabilityFamily.direct: "direct",
}


def _extract_intent(step_request: Any) -> str:
    parts: list[str] = []
    title = str(getattr(step_request, "step_title", "") or "").strip()
    description = str(getattr(step_request, "step_description", "") or "").strip()
    objective = str(getattr(step_request, "objective", "") or "").strip()
    if title:
        parts.append(title)
    if description and description != title:
        parts.append(description)
    if objective and objective not in parts:
        parts.append(objective)
    return " ".join(parts)


def _build_decision(
    step_request: Any,
    assessment: ToolUtilityAssessment,
) -> ActionResolutionDecision:
    step_title = str(getattr(step_request, "step_title", "") or "").strip()
    step_type = str(
        getattr(getattr(step_request, "step_type", None), "value",
                getattr(step_request, "step_type", "")) or ""
    ).strip()
    suggested_tools = list(getattr(step_request, "suggested_tools", []) or [])

    cap = assessment.capability
    cap_type = _CAPABILITY_TYPE_MAP[cap]

    requested_capability: dict[str, Any] = {
        "capability_type": cap_type,
        "execution_mode": assessment.mode.value,
    }

    # direct → einfache Chat-Antwort, kein Tool-Einsatz
    if cap is CapabilityFamily.direct:
        effective_step_type = step_type or "chat"
        effective_tools: list[str] = []
    else:
        effective_step_type = step_type or cap_type
        effective_tools = suggested_tools

    mode = ActionResolutionMode.EXECUTE_EXISTING_STEP

    return ActionResolutionDecision(
        resolved=True,
        action=ResolvedLoopAction(
            mode=mode,
            title=step_title,
            step_type=effective_step_type,
            suggested_tools=effective_tools,
            requested_capability=requested_capability,
            capability_context=dict(
                getattr(step_request, "capability_context", {}) or {}
            ),
            metadata={
                "tool_utility_assessment": {
                    "capability": cap.value,
                    "mode": assessment.mode.value,
                    "confidence": assessment.confidence,
                    "rationale": assessment.rationale,
                    "scores": assessment.scores,
                }
            },
        ),
        source=ActionResolutionSource.DOMAIN_DISPATCH,
        rationale=[
            f"tool_utility_policy:capability={cap.value}",
            f"tool_utility_policy:confidence={assessment.confidence:.3f}",
            f"tool_utility_policy:mode={assessment.mode.value}",
        ],
        detail=f"domain_dispatch:{cap.value}",
    )


def dispatch_by_capability(
    step_request: Any,
    context: dict | None = None,
) -> ActionResolutionDecision | None:
    """Bewertet den Intent des step_request und gibt eine Capability-Entscheidung zurueck.

    Gibt None zurueck wenn der Intent-Text leer ist oder die Confidence zu niedrig.
    """
    intent = _extract_intent(step_request)
    if not intent:
        return None

    assessment = assess_tool_utility(intent, context=context)

    if assessment.confidence < _MIN_CONFIDENCE:
        return None

    return _build_decision(step_request, assessment)


__all__ = ["dispatch_by_capability"]
