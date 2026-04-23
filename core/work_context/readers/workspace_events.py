"""Reader fuer verdichtete Arbeitskontext-Signale aus workspace_events."""

from __future__ import annotations

import json
from typing import Any, Iterable, Optional

from core.work_context.contracts import (
    WorkContext,
    WorkContextSource,
    WorkContextStatus,
)


_TASK_LOOP_EVENT_PREFIX = "task_loop_"


def _event_data(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("event_data", {})
    if isinstance(data, dict):
        return dict(data)
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return parsed
        except (TypeError, ValueError):
            pass
    return {}


def _topic(data: dict[str, Any]) -> str:
    return str(
        data.get("background_loop_topic")
        or data.get("objective_summary")
        or data.get("pending_step")
        or ""
    ).strip()


def _pending_step(data: dict[str, Any]) -> str:
    return str(
        data.get("background_loop_pending_step")
        or data.get("pending_step")
        or ""
    ).strip()


def _execution_result(data: dict[str, Any]) -> dict[str, Any]:
    last_step_result = data.get("last_step_result")
    if isinstance(last_step_result, dict):
        result = last_step_result.get("execution_result")
        if isinstance(result, dict):
            return result
    return {}


def _recovery_step(data: dict[str, Any]) -> str:
    for artifact in reversed(list(data.get("verified_artifacts") or [])):
        if not isinstance(artifact, dict):
            continue
        if str(artifact.get("artifact_type") or "").strip().lower() != "container_recovery_hint":
            continue
        title = str(artifact.get("replan_step_title") or "").strip()
        if title:
            return title
    return ""


def _blocker(data: dict[str, Any], event_type: str) -> str:
    blockers: list[str] = []
    last_step_result = data.get("last_step_result")
    if isinstance(last_step_result, dict):
        execution_result = _execution_result(data)
        for status_rows in (
            list(last_step_result.get("tool_statuses") or []),
            list(execution_result.get("tool_statuses") or []),
        ):
            for row in status_rows:
                if not isinstance(row, dict):
                    continue
                status = str(row.get("status") or "").strip().lower()
                if status in {"", "ok", "success", "completed"}:
                    continue
                tool_name = str(row.get("tool_name") or "tool").strip()
                reason = str(row.get("reason") or status).strip()
                blockers.append(f"{tool_name}:{reason}" if reason else tool_name)
        for item in list(last_step_result.get("blockers") or []):
            text = str(item or "").strip()
            if text:
                blockers.append(text)
        step_status = str(last_step_result.get("status") or "").strip().lower()
        if step_status in {"blocked", "failed", "waiting_for_user", "waiting_for_approval"}:
            blockers.append(step_status)

    stop_reason = str(data.get("stop_reason") or "").strip()
    if stop_reason and event_type in {"task_loop_blocked", "task_loop_waiting_for_user"}:
        blockers.append(stop_reason)

    for item in blockers:
        if item:
            return item[:120]
    return ""


def _next_step(data: dict[str, Any], blocker: str) -> str:
    pending = _pending_step(data)
    if pending:
        return pending
    recovery = _recovery_step(data)
    if recovery:
        return recovery
    current_plan = list(data.get("current_plan") or [])
    completed = {str(item or "").strip() for item in list(data.get("completed_steps") or [])}
    for item in current_plan:
        title = str(item or "").strip()
        if title and title not in completed:
            return title
    if blocker:
        return "Offenen Task-Loop-Blocker klaeren"
    return ""


def _status(event_type: str, data: dict[str, Any]) -> WorkContextStatus:
    raw = str(
        data.get("background_loop_state")
        or data.get("state")
        or event_type.removeprefix(_TASK_LOOP_EVENT_PREFIX)
        or ""
    ).strip().lower()
    if raw in {"waiting_for_user", "waiting"}:
        return WorkContextStatus.WAITING
    if raw == "blocked":
        return WorkContextStatus.BLOCKED
    if raw == "completed":
        return WorkContextStatus.COMPLETED
    if raw == "cancelled":
        return WorkContextStatus.CANCELLED
    if raw:
        return WorkContextStatus.ACTIVE
    return WorkContextStatus.UNKNOWN


def _relevant_task_loop_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for event in list(events or []):
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "").strip()
        if not event_type.startswith(_TASK_LOOP_EVENT_PREFIX):
            continue
        rows.append(event)
    rows.sort(key=lambda item: str(item.get("created_at") or ""))
    return rows


def build_work_context_from_workspace_events(
    events: Iterable[dict[str, Any]],
    *,
    conversation_id: str = "",
) -> Optional[WorkContext]:
    rows = _relevant_task_loop_events(events)
    if not rows:
        return None

    last_event = rows[-1]
    event_type = str(last_event.get("event_type") or "").strip()
    data = _event_data(last_event)

    topic = _topic(data)
    blocker = _blocker(data, event_type)
    next_step = _next_step(data, blocker)
    loop_status = _status(event_type, data)
    pending_step = _pending_step(data)
    source_conv = str(
        conversation_id
        or last_event.get("conversation_id")
        or data.get("conversation_id")
        or ""
    ).strip()

    if not any([topic, blocker, next_step, pending_step, source_conv]):
        return None

    metadata = {
        "event_type": event_type,
        "event_count": len(rows),
        "latest_event_id": str(last_event.get("id") or "").strip(),
    }
    created_at = str(last_event.get("created_at") or "").strip()

    return WorkContext(
        conversation_id=source_conv,
        topic=topic or "Offene Aufgabe",
        status=loop_status,
        source=WorkContextSource.WORKSPACE_EVENTS,
        updated_at=created_at,
        last_step=pending_step or "",
        next_step=next_step,
        blocker=blocker,
        metadata=metadata,
    )


__all__ = ["build_work_context_from_workspace_events"]
