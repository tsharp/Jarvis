from __future__ import annotations

from dataclasses import replace
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
from core.task_loop.failure_policy import handle_failed_step_result
from core.task_loop.recovery_policy import (
    derive_recovery_hint,
    maybe_apply_recovery_replan,
)
from core.task_loop.reflection import ReflectionAction, reflect_after_chat_step
from core.task_loop.runner.chat_sync import (
    TaskLoopRunResult,
    _TaskLoopStepResult,
    _effective_max_steps,
)
from core.task_loop.runner.messages import (
    _msg_control_soft_block,
    _msg_hard_block,
    _msg_risk_gate,
    _msg_verify_before_complete,
    _msg_waiting,
)
from core.task_loop.runner.snapshot_state import (
    _append_visible_content,
    _done_reason_for_stop,
    _inject_follow_up_step,
    _merge_verified_artifacts,
    _prime_next_step,
    _risk_for_step,
    _set_step_running,
    _step_meta,
)
from core.task_loop.step_answers import answer_for_chat_step
from core.task_loop.step_runtime import execute_task_loop_step


async def run_chat_auto_loop_async(
    initial_snapshot: TaskLoopSnapshot,
    *,
    initial_events: List[Dict[str, Any]] | None = None,
    max_steps: int | None = None,
    max_errors: int = 4,
    max_no_progress: int = 2,
    control_layer: Any = None,
    output_layer: Any = None,
    orchestrator_bridge: Any = None,
    emit_header: bool = True,
    resume_user_text: str = "",
) -> TaskLoopRunResult:
    events: List[Dict[str, Any]] = list(initial_events or [])
    snapshot = initial_snapshot
    _max_steps = _effective_max_steps(snapshot, max_steps)
    content = str(snapshot.last_user_visible_answer or "")
    current_resume_user_text = str(resume_user_text or "")
    if emit_header:
        content = ""
        snapshot = replace(snapshot, last_user_visible_answer=content)

    while True:
        step_result = await _run_chat_auto_loop_step_async(
            snapshot,
            max_steps=_max_steps,
            max_errors=max_errors,
            max_no_progress=max_no_progress,
            current_content=content,
            control_layer=control_layer,
            output_layer=output_layer,
            orchestrator_bridge=orchestrator_bridge,
            resume_user_text=current_resume_user_text,
        )
        events.extend(step_result.events)
        content = step_result.snapshot.last_user_visible_answer
        snapshot = step_result.snapshot
        current_resume_user_text = ""
        if step_result.is_final:
            return TaskLoopRunResult(
                snapshot=snapshot,
                events=events,
                content=content,
                done_reason=step_result.done_reason,
            )


async def _run_chat_auto_loop_step_async(
    snapshot: TaskLoopSnapshot,
    *,
    max_steps: int,
    max_errors: int,
    max_no_progress: int,
    current_content: str,
    control_layer: Any = None,
    output_layer: Any = None,
    orchestrator_bridge: Any = None,
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

    step_meta = _step_meta(working_snapshot, completed_step)
    runtime_result = await execute_task_loop_step(
        completed_step,
        step_meta,
        working_snapshot,
        control_layer=control_layer,
        output_layer=output_layer,
        orchestrator_bridge=orchestrator_bridge,
        resume_user_text=resume_user_text,
        fallback_fn=answer_for_chat_step,
    )
    if not runtime_result.control_decision.approved:
        detail = (
            runtime_result.control_decision.final_instruction
            or runtime_result.control_decision.reason
            or ", ".join(str(item) for item in runtime_result.control_decision.warnings)
            or "step_control_denied"
        )
        if runtime_result.control_decision.hard_block:
            blocked_snapshot = transition_task_loop_step(
                working_snapshot,
                next_step_status=TaskLoopStepStatus.BLOCKED,
                step_execution_source=TaskLoopStepExecutionSource.BLOCKED,
                last_step_result={
                    "status": TaskLoopStepStatus.BLOCKED.value,
                    "trace_reason": "step_control_denied",
                    "detail": detail,
                },
            )
            blocked = transition_task_loop(
                blocked_snapshot,
                TaskLoopState.BLOCKED,
                stop_reason=StopReason.RISK_GATE_REQUIRED,
            )
            events.append(make_task_loop_event(TaskLoopEventType.BLOCKED, blocked))
            delta = _msg_hard_block(detail)
            return _TaskLoopStepResult(
                snapshot=replace(
                    blocked,
                    last_user_visible_answer=_append_visible_content(current_content, delta),
                ),
                events=events,
                content_delta=delta,
                is_final=True,
                done_reason="task_loop_risk_gate_required",
            )
        waiting = transition_task_loop(
            transition_task_loop_step(
                working_snapshot,
                next_step_status=TaskLoopStepStatus.WAITING_FOR_APPROVAL,
                step_execution_source=TaskLoopStepExecutionSource.APPROVAL,
                last_step_result={
                    "status": TaskLoopStepStatus.WAITING_FOR_APPROVAL.value,
                    "trace_reason": "step_control_denied",
                    "detail": detail,
                },
            ),
            TaskLoopState.WAITING_FOR_USER,
            stop_reason=StopReason.RISK_GATE_REQUIRED,
        )
        events.append(make_task_loop_event(TaskLoopEventType.WAITING_FOR_USER, waiting))
        delta = _msg_control_soft_block(detail)
        return _TaskLoopStepResult(
            snapshot=replace(
                waiting,
                last_user_visible_answer=_append_visible_content(current_content, delta),
            ),
            events=events,
            content_delta=delta,
            is_final=True,
            done_reason="task_loop_risk_gate_required",
        )

    step_result = runtime_result.step_result
    if step_result.status is not TaskLoopStepStatus.COMPLETED:
        if step_result.status is TaskLoopStepStatus.FAILED:
            failed = handle_failed_step_result(step_result)
            failed_snapshot = transition_task_loop_step(
                working_snapshot,
                next_step_type=step_result.step_type,
                next_step_status=failed.next_step_status,
                step_execution_source=step_result.step_execution_source,
                verified_artifacts=_merge_verified_artifacts(
                    working_snapshot,
                    step_result.verified_artifacts,
                ),
                last_step_result=step_result.to_dict(),
            )
            waiting = transition_task_loop(
                failed_snapshot,
                TaskLoopState.WAITING_FOR_USER,
                stop_reason=failed.stop_reason,
            )
            events.append(make_task_loop_event(TaskLoopEventType.WAITING_FOR_USER, waiting))
            delta = failed.user_message
            return _TaskLoopStepResult(
                snapshot=replace(
                    waiting,
                    last_user_visible_answer=_append_visible_content(current_content, delta),
                ),
                events=events,
                content_delta=delta,
                is_final=True,
                done_reason=failed.done_reason,
            )
        updated_snapshot = transition_task_loop_step(
            working_snapshot,
            next_step_type=step_result.step_type,
            next_step_status=step_result.status,
            step_execution_source=step_result.step_execution_source,
            verified_artifacts=_merge_verified_artifacts(
                working_snapshot,
                step_result.verified_artifacts,
            ),
            last_step_result=step_result.to_dict(),
        )
        delta = ""
        if step_result.status is TaskLoopStepStatus.WAITING_FOR_APPROVAL:
            waiting = transition_task_loop(
                updated_snapshot,
                TaskLoopState.WAITING_FOR_USER,
                stop_reason=StopReason.RISK_GATE_REQUIRED,
            )
            events.append(make_task_loop_event(TaskLoopEventType.WAITING_FOR_USER, waiting))
            return _TaskLoopStepResult(
                snapshot=replace(
                    waiting,
                    last_user_visible_answer=_append_visible_content(current_content, delta),
                ),
                events=events,
                content_delta=delta,
                is_final=True,
                done_reason="task_loop_risk_gate_required",
            )
        if step_result.status is TaskLoopStepStatus.WAITING_FOR_USER:
            waiting = transition_task_loop(
                updated_snapshot,
                TaskLoopState.WAITING_FOR_USER,
                stop_reason=StopReason.USER_DECISION_REQUIRED,
            )
            events.append(make_task_loop_event(TaskLoopEventType.WAITING_FOR_USER, waiting))
            return _TaskLoopStepResult(
                snapshot=replace(
                    waiting,
                    last_user_visible_answer=_append_visible_content(current_content, delta),
                ),
                events=events,
                content_delta=delta,
                is_final=True,
                done_reason="task_loop_user_decision_required",
            )
        blocked = transition_task_loop(
            updated_snapshot,
            TaskLoopState.BLOCKED,
            stop_reason=StopReason.NO_CONCRETE_NEXT_STEP,
        )
        events.append(make_task_loop_event(TaskLoopEventType.BLOCKED, blocked))
        return _TaskLoopStepResult(
            snapshot=replace(
                blocked,
                last_user_visible_answer=_append_visible_content(current_content, delta),
            ),
            events=events,
            content_delta=delta,
            is_final=True,
            done_reason=_done_reason_for_stop(blocked.stop_reason or StopReason.NO_CONCRETE_NEXT_STEP),
        )

    completed_steps = list(working_snapshot.completed_steps)
    replanned_snapshot = working_snapshot
    recovery_hint = derive_recovery_hint(step_result.verified_artifacts)
    replanned_snapshot = maybe_apply_recovery_replan(
        working_snapshot,
        current_step_title=completed_step,
        current_step_meta=step_meta,
        recovery_hint=recovery_hint,
    )
    if replanned_snapshot is working_snapshot:
        if completed_step not in completed_steps:
            completed_steps.append(completed_step)
    else:
        # Recovery replan keeps the current step pending in the visible plan,
        # so completed_steps must not advance past the inserted recovery step.
        completed_steps = list(completed_steps)
    next_index = len(completed_steps)
    next_step = (
        replanned_snapshot.current_plan[next_index]
        if next_index < len(replanned_snapshot.current_plan)
        else ""
    )
    next_risk = _risk_for_step(replanned_snapshot, next_step) if next_step else RiskLevel.SAFE
    answered = transition_task_loop_step(
        replace(
            replanned_snapshot,
            step_index=next_index,
            completed_steps=completed_steps,
            pending_step=next_step,
            last_user_visible_answer=runtime_result.visible_text,
            risk_level=next_risk,
        ),
        next_step_type=step_result.step_type,
        next_step_status=TaskLoopStepStatus.COMPLETED,
        step_execution_source=step_result.step_execution_source,
        verified_artifacts=_merge_verified_artifacts(
            replanned_snapshot,
            step_result.verified_artifacts,
        ),
        last_step_result=step_result.to_dict(),
    )
    events.append(make_task_loop_event(TaskLoopEventType.STEP_ANSWERED, answered))
    events.append(make_task_loop_event(TaskLoopEventType.STEP_COMPLETED, answered))
    step_delta = runtime_result.visible_text or ""

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
                    "used_fallback": runtime_result.used_fallback,
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


__all__ = [
    "_run_chat_auto_loop_step_async",
    "run_chat_auto_loop_async",
]
