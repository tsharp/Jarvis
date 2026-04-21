from __future__ import annotations

from dataclasses import dataclass

from core.task_loop.contracts import StopReason, TaskLoopStepResult, TaskLoopStepStatus


@dataclass(frozen=True)
class FailedStepHandling:
    next_step_status: TaskLoopStepStatus
    stop_reason: StopReason
    done_reason: str
    user_message: str


def _failure_message(step_result: TaskLoopStepResult) -> str:
    detail = (
        str(step_result.user_visible_summary or "").strip()
        or ", ".join(str(item or "").strip() for item in step_result.blockers or [] if str(item or "").strip())
        or "Der letzte Ausfuehrungsschritt ist technisch fehlgeschlagen."
    )
    return (
        f"\n{detail}\n\n"
        "Ich kann den Schritt erneut versuchen oder mit angepassten Angaben neu planen. "
        "Schreib mir kurz, ob ich wiederholen, anpassen oder einen alternativen Pfad nehmen soll."
    )


def handle_failed_step_result(step_result: TaskLoopStepResult) -> FailedStepHandling:
    return FailedStepHandling(
        next_step_status=TaskLoopStepStatus.WAITING_FOR_USER,
        stop_reason=StopReason.USER_DECISION_REQUIRED,
        done_reason="task_loop_user_decision_required",
        user_message=_failure_message(step_result),
    )
