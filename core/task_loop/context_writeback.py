from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List, Optional, Tuple

from core.task_loop.contracts import TaskLoopSnapshot
from core.task_loop.events import (
    TaskLoopEventType,
    make_task_loop_event,
    persist_task_loop_workspace_event,
)


def _clip(text: Any, limit: int = 400) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 3)].rstrip() + "..."


def build_background_loop_state(snapshot: TaskLoopSnapshot) -> Dict[str, Any]:
    topic = str(snapshot.objective_summary or "").strip()
    pending_step = str(snapshot.pending_step or "").strip()
    if not topic:
        topic = pending_step
    return {
        "background_loop_preserved": True,
        "background_loop_state": snapshot.state.value,
        "background_loop_topic": topic,
        "background_loop_pending_step": pending_step,
        "background_loop_step_index": int(snapshot.step_index or 0),
    }


def build_context_only_artifact(
    assistant_text: str,
    *,
    done_reason: str = "",
) -> Dict[str, Any]:
    return {
        "artifact_type": "context_only_turn",
        "done_reason": str(done_reason or "").strip(),
        "assistant_summary": _clip(assistant_text, 500),
    }


def apply_context_only_turn_to_snapshot(
    snapshot: TaskLoopSnapshot,
    assistant_text: str,
    *,
    done_reason: str = "",
) -> TaskLoopSnapshot:
    artifacts = list(snapshot.verified_artifacts)
    artifacts.append(build_context_only_artifact(assistant_text, done_reason=done_reason))
    last_step_result = dict(snapshot.last_step_result or {})
    last_step_result["trace_reason"] = "task_loop_context_only_turn"
    if done_reason:
        last_step_result["context_only_done_reason"] = str(done_reason)
    return replace(
        snapshot,
        last_user_visible_answer=str(assistant_text or ""),
        verified_artifacts=artifacts,
        last_step_result=last_step_result,
    )


def persist_context_only_turn(
    snapshot: TaskLoopSnapshot,
    assistant_text: str,
    *,
    done_reason: str = "",
    save_workspace_entry_fn: Any = None,
) -> Tuple[TaskLoopSnapshot, Dict[str, Any], List[Dict[str, Any]], List[str]]:
    updated = apply_context_only_turn_to_snapshot(
        snapshot,
        assistant_text,
        done_reason=done_reason,
    )
    event = make_task_loop_event(
        TaskLoopEventType.CONTEXT_UPDATED,
        updated,
        event_data={
            "context_only": True,
            "context_only_done_reason": str(done_reason or "").strip(),
            **build_background_loop_state(updated),
        },
    )
    workspace_updates: List[Dict[str, Any]] = []
    event_ids: List[str] = []
    if save_workspace_entry_fn is not None:
        saved = persist_task_loop_workspace_event(
            save_workspace_entry_fn,
            updated.conversation_id,
            event,
        )
        if isinstance(saved, dict):
            workspace_updates.append(saved)
            event_id = saved.get("entry_id") or saved.get("id")
            if event_id:
                event_ids.append(str(event_id))
    if event_ids:
        updated = replace(updated, workspace_event_ids=list(updated.workspace_event_ids) + event_ids)
    return updated, event, workspace_updates, event_ids
