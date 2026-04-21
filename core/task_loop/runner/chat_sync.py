from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, List

from core.task_loop.completion_policy import build_completion_message
from core.task_loop.contracts import (
    RiskLevel,
    StopReason,
    TaskLoopSnapshot,
    TaskLoopState,
    TaskLoopStepExecutionSource,
    TaskLoopStepStatus,
    transition_task_loop,
    transition_task_loop_step,
)
from core.task_loop.events import TaskLoopEventType, make_task_loop_event
from core.task_loop.reflection import ReflectionAction, reflect_after_chat_step
from core.task_loop.runner.messages import (
    _msg_hard_block,
    _msg_risk_gate,
    _msg_verify_before_complete,
    _msg_waiting,
)
from core.task_loop.runner.snapshot_state import (
    _append_visible_content,
    _done_reason_for_stop,
    _inject_follow_up_step,
    _prime_next_step,
    _risk_for_step,
    _set_step_running,
    _step_meta,
    _step_type_for_step,
)
from core.task_loop.step_answers import answer_for_chat_step


@dataclass(frozen=True)
class TaskLoopRunResult:
    snapshot: TaskLoopSnapshot
    events: List[Dict[str, Any]]
    content: str
    done_reason: str


@dataclass(frozen=True)
class _TaskLoopStepResult:
    snapshot: TaskLoopSnapshot
    events: List[Dict[str, Any]]
    content_delta: str
    is_final: bool
    done_reason: str


def _run_chat_auto_loop_step(
    snapshot: TaskLoopSnapshot,
    *,
    max_steps: int,
    max_errors: int,
    max_no_progress: int,
    current_content: str,
    resume_user_text: str = "",
) -> _TaskLoopStepResult:
    events: List[Dict[str, Any]] = []
    working_snapshot = snapshot

    if working_snapshot.state != TaskLoopState.EXECUTING:
        working_snapshot = transition_task_loop(working_snapshot, TaskLoopState.EXECUTING)
    if working_snapshot.pending_step.strip():
        working_snapshot = _set_step_running(working_snapshot, working_snapshot.pending_step.strip())
    events.append(make_task_loop_event(TaskLoopEventType.STEP_STARTED, working_snapshot))

    completed_step = working_snapshot.pending_step.strip()
    if not completed_step:
        completed = transition_task_loop(working_snapshot, TaskLoopState.COMPLETED)
        events.append(make_task_loop_event(TaskLoopEventType.COMPLETED, completed))
        delta = "Alle Schritte abgeschlossen."
        return _TaskLoopStepResult(
            snapshot=replace(
                completed,
                last_user_visible_answer=_append_visible_content(current_content, delta),
            ),
            events=events,
            content_delta=delta,
            is_final=True,
            done_reason="task_loop_completed",
        )

    completed_steps = list(working_snapshot.completed_steps)
    if completed_step not in completed_steps:
        completed_steps.append(completed_step)
    next_index = len(completed_steps)
    next_step = (
        working_snapshot.current_plan[next_index]
        if next_index < len(working_snapshot.current_plan)
        else ""
    )
    step_answer = answer_for_chat_step(
        next_index,
        completed_step,
        _step_meta(working_snapshot, completed_step),
        completed_steps[:-1],
    )
    next_risk = _risk_for_step(working_snapshot, next_step) if next_step else RiskLevel.SAFE
    answered = transition_task_loop_step(
        replace(
            working_snapshot,
            step_index=next_index,
            completed_steps=completed_steps,
            pending_step=next_step,
            last_user_visible_answer=step_answer,
            risk_level=next_risk,
        ),
        next_step_type=_step_type_for_step(working_snapshot, completed_step),
        next_step_status=TaskLoopStepStatus.COMPLETED,
        step_execution_source=TaskLoopStepExecutionSource.LOOP,
        last_step_result={
            "status": TaskLoopStepStatus.COMPLETED.value,
            "trace_reason": "task_loop_chat_answer",
            "step_execution_source": TaskLoopStepExecutionSource.LOOP.value,
        },
    )
    events.append(make_task_loop_event(TaskLoopEventType.STEP_ANSWERED, answered))
    events.append(make_task_loop_event(TaskLoopEventType.STEP_COMPLETED, answered))
    step_delta = step_answer

    reflecting = transition_task_loop(
        _prime_next_step(answered, next_step),
        TaskLoopState.REFLECTING,
    )
    decision = reflect_after_chat_step(
        reflecting,
        max_steps=max_steps,
        max_errors=max_errors,
        max_no_progress=max_no_progress,
    )
    events.append(
        make_task_loop_event(
            TaskLoopEventType.REFLECTION,
            reflecting,
            event_data={
                "reflection": {
                    "action": decision.action.value,
                    "reason": decision.reason.value if decision.reason else None,
                    "detail": decision.detail,
                    "progress_made": decision.progress_made,
                    "next_step_override": decision.next_step_override,
                }
            },
        )
    )

    step_content = step_delta
    if decision.action is ReflectionAction.CONTINUE:
        continued_snapshot = (
            _inject_follow_up_step(reflecting, decision.next_step_override)
            if decision.next_step_override
            else reflecting
        )
        if decision.next_step_override:
            step_content += _msg_verify_before_complete(decision.detail)
        continued = replace(
            continued_snapshot,
            last_user_visible_answer=_append_visible_content(current_content, step_content),
        )
        return _TaskLoopStepResult(
            snapshot=continued,
            events=events,
            content_delta=step_content,
            is_final=False,
            done_reason="",
        )

    if decision.action is ReflectionAction.COMPLETED:
        completed = transition_task_loop(reflecting, TaskLoopState.COMPLETED)
        events.append(make_task_loop_event(TaskLoopEventType.COMPLETED, completed))
        step_content += build_completion_message(completed)
        return _TaskLoopStepResult(
            snapshot=replace(
                completed,
                last_user_visible_answer=_append_visible_content(current_content, step_content),
            ),
            events=events,
            content_delta=step_content,
            is_final=True,
            done_reason="task_loop_completed",
        )

    stop_reason = decision.reason or StopReason.NO_CONCRETE_NEXT_STEP
    if decision.action is ReflectionAction.WAITING_FOR_USER:
        waiting = transition_task_loop(
            reflecting,
            TaskLoopState.WAITING_FOR_USER,
            stop_reason=stop_reason,
        )
        events.append(make_task_loop_event(TaskLoopEventType.WAITING_FOR_USER, waiting))
        if stop_reason is StopReason.RISK_GATE_REQUIRED:
            next_pending = reflecting.pending_step.strip()
            step_content += _msg_risk_gate(next_pending or completed_step)
        else:
            step_content += _msg_waiting(decision.detail)
        return _TaskLoopStepResult(
            snapshot=replace(
                waiting,
                last_user_visible_answer=_append_visible_content(current_content, step_content),
            ),
            events=events,
            content_delta=step_content,
            is_final=True,
            done_reason=_done_reason_for_stop(stop_reason),
        )

    blocked = transition_task_loop(
        reflecting,
        TaskLoopState.BLOCKED,
        stop_reason=stop_reason,
    )
    events.append(make_task_loop_event(TaskLoopEventType.BLOCKED, blocked))
    step_content += _msg_hard_block(decision.detail)
    return _TaskLoopStepResult(
        snapshot=replace(
            blocked,
            last_user_visible_answer=_append_visible_content(current_content, step_content),
        ),
        events=events,
        content_delta=step_content,
        is_final=True,
        done_reason=_done_reason_for_stop(stop_reason),
    )


def _effective_max_steps(snapshot: TaskLoopSnapshot, explicit: int | None) -> int:
    """Derive a sensible step cap from the plan length.

    The natural end of the loop is always ``pending_step == ""`` (plan_complete).
    This cap is only a safety net for stuck loops — it should never fire during
    normal execution. We give 3x the plan length as buffer for retries, capped
    at 50 to prevent runaway loops.
    """
    if explicit is not None:
        return explicit
    plan_len = len(snapshot.current_plan or [])
    return min(max(plan_len * 3, 20), 50)


def run_chat_auto_loop(
    initial_snapshot: TaskLoopSnapshot,
    *,
    initial_events: List[Dict[str, Any]] | None = None,
    max_steps: int | None = None,
    max_errors: int = 4,
    max_no_progress: int = 2,
    resume_user_text: str = "",
) -> TaskLoopRunResult:
    events: List[Dict[str, Any]] = list(initial_events or [])
    snapshot = initial_snapshot
    _max_steps = _effective_max_steps(snapshot, max_steps)
    content = str(snapshot.last_user_visible_answer or "")
    current_resume_user_text = str(resume_user_text or "")

    while True:
        step_result = _run_chat_auto_loop_step(
            snapshot,
            max_steps=_max_steps,
            max_errors=max_errors,
            max_no_progress=max_no_progress,
            current_content=content,
            resume_user_text=current_resume_user_text,
        )
        current_resume_user_text = ""
        events.extend(step_result.events)
        content = step_result.snapshot.last_user_visible_answer
        snapshot = step_result.snapshot
        if step_result.is_final:
            return TaskLoopRunResult(
                snapshot=snapshot,
                events=events,
                content=content,
                done_reason=step_result.done_reason,
            )


__all__ = [
    "TaskLoopRunResult",
    "_TaskLoopStepResult",
    "_effective_max_steps",
    "_run_chat_auto_loop_step",
    "run_chat_auto_loop",
]
