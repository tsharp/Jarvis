"""Zentrale Service-Flaeche fuer Laden/Mergen/Schreiben des Work Context."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Optional

from core.task_loop.contracts import TaskLoopSnapshot
from core.work_context.contracts import WorkContext, WorkContextFact
from core.work_context.readers.task_loop import build_work_context_from_task_loop_snapshot
from core.work_context.readers.workspace_events import build_work_context_from_workspace_events


def _merge_facts(
    primary: tuple[WorkContextFact, ...],
    secondary: tuple[WorkContextFact, ...],
) -> tuple[WorkContextFact, ...]:
    out = []
    seen = set()
    for item in list(primary or []) + list(secondary or []):
        key = (item.key, item.value)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return tuple(out)


def merge_work_context(
    primary: Optional[WorkContext],
    secondary: Optional[WorkContext],
) -> Optional[WorkContext]:
    if primary is None:
        return secondary
    if secondary is None:
        return primary

    topic = primary.topic or secondary.topic
    updated_at = primary.updated_at or secondary.updated_at
    last_step = primary.last_step or secondary.last_step
    next_step = primary.next_step or secondary.next_step
    blocker = primary.blocker or secondary.blocker

    missing = []
    seen_missing = set()
    for item in list(primary.missing_facts or ()) + list(secondary.missing_facts or ()):
        if item in seen_missing:
            continue
        seen_missing.add(item)
        missing.append(item)

    capability_context = dict(secondary.capability_context)
    capability_context.update(dict(primary.capability_context))

    metadata = dict(secondary.metadata)
    metadata.update(dict(primary.metadata))

    status = primary.status
    if str(status.value or "").strip() == "unknown":
        status = secondary.status

    return replace(
        primary,
        topic=topic,
        status=status,
        updated_at=updated_at,
        last_step=last_step,
        next_step=next_step,
        blocker=blocker,
        verified_facts=_merge_facts(primary.verified_facts, secondary.verified_facts),
        missing_facts=tuple(missing),
        capability_context=capability_context,
        metadata=metadata,
    )


def load_work_context(
    *,
    conversation_id: str = "",
    task_loop_snapshot: Optional[TaskLoopSnapshot] = None,
    workspace_events: Optional[Iterable[dict]] = None,
) -> Optional[WorkContext]:
    from_task_loop = build_work_context_from_task_loop_snapshot(task_loop_snapshot)
    from_events = build_work_context_from_workspace_events(
        workspace_events or [],
        conversation_id=conversation_id,
    )
    return merge_work_context(from_task_loop, from_events)


__all__ = [
    "load_work_context",
    "merge_work_context",
]
