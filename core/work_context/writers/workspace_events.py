"""Writer fuer Work-Context-Projektionen in workspace_events."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from core.work_context.contracts import WorkContext, WorkContextStatus


def build_workspace_event_from_work_context(
    context: Optional[WorkContext],
    *,
    event_type: str = "task_loop_context_updated",
    event_id: str = "",
    created_at: str = "",
) -> Optional[dict[str, Any]]:
    """Projiziert einen WorkContext in ein task_loop-kompatibles Event.

    Der Output ist absichtlich klein und nutzt das bestehende Eventformat, damit
    bestehende Leser/Renderer ihn ohne Sonderpfad verarbeiten koennen.
    """

    if context is None:
        return None

    topic = str(context.topic or "").strip()
    raw_state = str(
        context.metadata.get("task_loop_state")
        or context.metadata.get("source_state")
        or context.status.value
        or ""
    ).strip()
    state = raw_state or str(context.status.value or "").strip()
    pending_step = str(context.next_step or context.last_step or "").strip()
    next_step = str(context.next_step or "").strip()
    blocker = str(context.blocker or "").strip()
    conversation_id = str(context.conversation_id or "").strip()

    if not any([topic, state, pending_step, next_step, blocker, conversation_id]):
        return None

    data: dict[str, Any] = {
        "conversation_id": conversation_id,
        "state": state,
    }
    if topic:
        data["background_loop_topic"] = topic
        data["objective_summary"] = topic
    if pending_step and context.status in {WorkContextStatus.ACTIVE, WorkContextStatus.WAITING}:
        data["background_loop_pending_step"] = pending_step
    if next_step:
        data["pending_step"] = next_step
    if blocker:
        data["last_step_result"] = {
            "blockers": [blocker],
            "status": "blocked" if state == "blocked" else "completed",
        }

    out = {
        "id": str(event_id or "").strip() or f"wc-{conversation_id or 'global'}",
        "event_type": str(event_type or "").strip() or "task_loop_context_updated",
        "created_at": str(created_at or "").strip() or datetime.utcnow().isoformat() + "Z",
        "event_data": data,
    }
    return out


__all__ = ["build_workspace_event_from_work_context"]
