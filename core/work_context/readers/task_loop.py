"""Reader fuer Task-Loop-Snapshots und terminale Loop-Zustaende."""

from __future__ import annotations

from typing import Optional

from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopState
from core.work_context.contracts import (
    WorkContext,
    WorkContextFact,
    WorkContextSource,
    WorkContextStatus,
)
from core.work_context.normalization import build_terminal_task_loop_projection, build_terminal_task_loop_work_context


def _map_status(state: TaskLoopState) -> WorkContextStatus:
    if state == TaskLoopState.WAITING_FOR_USER:
        return WorkContextStatus.WAITING
    if state == TaskLoopState.BLOCKED:
        return WorkContextStatus.BLOCKED
    if state == TaskLoopState.COMPLETED:
        return WorkContextStatus.COMPLETED
    if state == TaskLoopState.CANCELLED:
        return WorkContextStatus.CANCELLED
    return WorkContextStatus.ACTIVE


def _topic(snapshot: TaskLoopSnapshot) -> str:
    return (
        str(snapshot.objective_summary or "").strip()
        or str(snapshot.pending_step or "").strip()
        or "Offene Aufgabe"
    )


def _last_step(snapshot: TaskLoopSnapshot) -> str:
    completed = [str(item or "").strip() for item in list(snapshot.completed_steps or []) if str(item or "").strip()]
    if completed:
        return completed[-1]
    if str(snapshot.pending_step or "").strip():
        return str(snapshot.pending_step).strip()
    if snapshot.current_step_type is not None:
        return str(snapshot.current_step_type.value or "").strip()
    return ""

def build_work_context_from_task_loop_snapshot(
    snapshot: Optional[TaskLoopSnapshot],
) -> Optional[WorkContext]:
    if snapshot is None:
        return None

    next_step = str(snapshot.pending_step or "").strip()
    blocker = ""
    capability_context = {}
    verified_facts: tuple[WorkContextFact, ...] = tuple()
    missing_facts: tuple[str, ...] = tuple()

    if snapshot.state in {TaskLoopState.COMPLETED, TaskLoopState.BLOCKED, TaskLoopState.CANCELLED}:
        terminal_projection = build_terminal_task_loop_projection(snapshot)
        if terminal_projection is not None:
            terminal_context = build_terminal_task_loop_work_context(
                conversation_id=terminal_projection.conversation_id,
                topic=terminal_projection.topic,
                source_state=terminal_projection.source_state,
                next_step=terminal_projection.next_step,
                blocker=terminal_projection.blocker,
                capability_context=terminal_projection.capability_context,
                selected_blueprint=terminal_projection.selected_blueprint,
                discovered_blueprints=terminal_projection.discovered_blueprints,
                next_tools=terminal_projection.next_tools,
            )
            verified_facts = terminal_context.verified_facts
            missing_facts = terminal_context.missing_facts
            if terminal_context.next_step:
                next_step = terminal_context.next_step
            if terminal_context.blocker:
                blocker = terminal_context.blocker
            if terminal_context.capability_context:
                capability_context = dict(terminal_context.capability_context)

    metadata = {
        "task_loop_state": snapshot.state.value,
        "step_index": int(snapshot.step_index),
        "plan_id": str(snapshot.plan_id or "").strip(),
        "objective_id": str(snapshot.objective_id or "").strip(),
        "current_step_type": str(snapshot.current_step_type.value or "").strip(),
        "current_step_status": str(snapshot.current_step_status.value or "").strip(),
        "workspace_event_count": len(list(snapshot.workspace_event_ids or [])),
    }
    if snapshot.stop_reason is not None:
        metadata["stop_reason"] = str(snapshot.stop_reason.value or "").strip()

    return WorkContext(
        conversation_id=str(snapshot.conversation_id or "").strip(),
        topic=_topic(snapshot),
        status=_map_status(snapshot.state),
        source=WorkContextSource.TASK_LOOP,
        last_step=_last_step(snapshot),
        next_step=next_step,
        blocker=blocker,
        verified_facts=verified_facts,
        missing_facts=missing_facts,
        capability_context=capability_context,
        metadata=metadata,
    )


__all__ = ["build_work_context_from_task_loop_snapshot"]
