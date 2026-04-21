from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.task_loop.completion_policy import completion_detail
from core.task_loop.contracts import StopReason, TaskLoopSnapshot
from core.task_loop.evaluation_policy import evaluate_task_loop_iteration

_VERIFY_BEFORE_COMPLETE_STEP = "Ergebnis verifizieren und Abschluss absichern"


class ReflectionAction(str, Enum):
    CONTINUE = "continue"
    WAITING_FOR_USER = "waiting_for_user"
    BLOCKED = "blocked"
    COMPLETED = "completed"


@dataclass(frozen=True)
class ReflectionDecision:
    action: ReflectionAction
    reason: Optional[StopReason] = None
    detail: str = ""
    progress_made: bool = True
    next_step_override: str = ""


def reflect_after_chat_step(
    snapshot: TaskLoopSnapshot,
    *,
    max_steps: int = 4,
    max_errors: int = 4,
    max_no_progress: int = 2,
    repeated_action_threshold: int = 2,
) -> ReflectionDecision:
    evaluation = evaluate_task_loop_iteration(
        snapshot,
        max_steps=max_steps,
        max_errors=max_errors,
        max_no_progress=max_no_progress,
        repeated_action_threshold=repeated_action_threshold,
    )
    if evaluation.is_complete:
        evidence = evaluation.evidence_assessment
        if evidence is not None and evidence.requires_verification:
            detail = (
                "verify_before_complete "
                f"evidence={evidence.evidence_score:.2f} "
                f"completion_confidence={evidence.completion_confidence:.2f}"
            )
            if _VERIFY_BEFORE_COMPLETE_STEP in set(snapshot.completed_steps or []):
                return ReflectionDecision(
                    ReflectionAction.WAITING_FOR_USER,
                    StopReason.USER_DECISION_REQUIRED,
                    detail,
                    progress_made=evaluation.progress_made,
                )
            return ReflectionDecision(
                ReflectionAction.CONTINUE,
                None,
                detail,
                progress_made=evaluation.progress_made,
                next_step_override=_VERIFY_BEFORE_COMPLETE_STEP,
            )
        return ReflectionDecision(
            ReflectionAction.COMPLETED,
            None,
            completion_detail(snapshot),
            progress_made=evaluation.progress_made,
        )

    if evaluation.stop_decision.should_stop:
        reason = evaluation.stop_decision.reason or StopReason.NO_CONCRETE_NEXT_STEP
        if reason in {StopReason.RISK_GATE_REQUIRED, StopReason.MAX_STEPS_REACHED}:
            return ReflectionDecision(
                ReflectionAction.WAITING_FOR_USER,
                reason,
                evaluation.detail or evaluation.stop_decision.detail,
                progress_made=evaluation.progress_made,
            )
        return ReflectionDecision(
            ReflectionAction.BLOCKED,
            reason,
            evaluation.detail or evaluation.stop_decision.detail,
            progress_made=evaluation.progress_made,
        )

    return ReflectionDecision(
        ReflectionAction.CONTINUE,
        None,
        evaluation.detail,
        progress_made=evaluation.progress_made,
    )


__all__ = [
    "ReflectionAction",
    "ReflectionDecision",
    "reflect_after_chat_step",
]
