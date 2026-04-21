"""Capability-Hint fuer Step-Planung.

Wenn ein geplanter Step kein explizites requested_capability traegt,
bestimmt suggest_capability_for_step() per assess_tool_utility() welche
Capability-Family passt und gibt ein fertiges requested_capability-Dict zurueck.

Mindestkonfidenz: 0.15 — bewusst niedrig, da der Planer bereits einen
Kontext-Step hat; ein schwaches Signal ist besser als keines.
"""
from __future__ import annotations

from typing import Any, Dict

from core.task_loop.action_resolution.tool_utility_policy import (
    CapabilityFamily,
    assess_tool_utility,
)

_MIN_CONFIDENCE = 0.15

_CAPABILITY_TYPE_MAP: dict[CapabilityFamily, str] = {
    CapabilityFamily.container: "container_manager",
    CapabilityFamily.skill: "skill",
    CapabilityFamily.cron: "cron",
    CapabilityFamily.mcp: "mcp",
    CapabilityFamily.direct: "direct",
}


def suggest_capability_for_step(
    step_title: str,
    step_meta: Dict[str, Any],
) -> Dict[str, Any] | None:
    """Schlaegt ein requested_capability-Dict vor wenn step_meta keines enthaelt.

    Gibt None zurueck wenn der Intent leer ist, die Konfidenz zu niedrig ist
    oder step_meta bereits ein requested_capability traegt.
    """
    existing = step_meta.get("requested_capability")
    if isinstance(existing, dict) and existing:
        return None

    intent = _extract_intent(step_title, step_meta)
    if not intent:
        return None

    assessment = assess_tool_utility(intent)
    if assessment.confidence < _MIN_CONFIDENCE:
        return None

    cap_type = _CAPABILITY_TYPE_MAP[assessment.capability]
    return {
        "capability_type": cap_type,
        "execution_mode": assessment.mode.value,
        "_hint_source": "capability_hint_policy",
        "_hint_confidence": round(assessment.confidence, 3),
    }


def _extract_intent(step_title: str, step_meta: Dict[str, Any]) -> str:
    parts: list[str] = []
    title = str(step_title or "").strip()
    goal = str(step_meta.get("goal") or "").strip()
    objective = str(step_meta.get("objective") or "").strip()
    if title:
        parts.append(title)
    if goal and goal != title:
        parts.append(goal)
    if objective and objective not in parts:
        parts.append(objective)
    return " ".join(parts)


__all__ = ["suggest_capability_for_step"]
