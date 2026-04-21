"""Cron-Mode-Guard: Policy-basierte Validierung von Cron-Intents.

Bevor ein autonomy_cron_create_job ausgefuehrt wird, prueft dieser Guard
ob der Intent wirklich persistent/recurring ist — oder ob es sich um einen
one_shot-Auftrag handelt der faelschlicherweise als Cronjob eingeplant wird.

Typischer Anwendungsfall:
    confirmation = assess_cron_mode(user_text)
    if not confirmation.is_persistent and confirmation.confidence >= 0.3:
        # User meinte wahrscheinlich einen Einmal-Auftrag
        ...
"""
from __future__ import annotations

from dataclasses import dataclass

from core.task_loop.action_resolution.tool_utility_policy import (
    CapabilityFamily,
    ExecutionMode,
    assess_tool_utility,
)


@dataclass(frozen=True)
class CronModeConfirmation:
    is_persistent: bool
    is_cron_intent: bool
    execution_mode: str
    confidence: float
    rationale: str


def assess_cron_mode(user_text: str) -> CronModeConfirmation:
    """Bewertet ob user_text ein persistent/cron-wuerdiger Intent ist.

    is_persistent=True  → Policy bestaetigt recurring/persistent-Charakter
    is_cron_intent=True → Policy erkennt Cron als beste Capability
    confidence          → Wie sicher die Einschaetzung ist (0..1)
    """
    if not str(user_text or "").strip():
        return CronModeConfirmation(
            is_persistent=False,
            is_cron_intent=False,
            execution_mode=ExecutionMode.one_shot.value,
            confidence=0.0,
            rationale="empty_intent",
        )

    assessment = assess_tool_utility(user_text)
    is_cron = assessment.capability == CapabilityFamily.cron
    is_persistent = assessment.mode == ExecutionMode.persistent

    return CronModeConfirmation(
        is_persistent=is_persistent,
        is_cron_intent=is_cron,
        execution_mode=assessment.mode.value,
        confidence=assessment.confidence,
        rationale=assessment.rationale,
    )


__all__ = ["CronModeConfirmation", "assess_cron_mode"]
