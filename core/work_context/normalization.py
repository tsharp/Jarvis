"""Normalisierung fuer Work-Context-Signale."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from core.task_loop.capabilities.container.context import extract_container_context
from core.task_loop.capabilities.container.request_policy import (
    extract_discovered_blueprints,
    extract_selected_blueprint,
)
from core.task_loop.contracts import TaskLoopSnapshot, TaskLoopState

from core.work_context.contracts import (
    WorkContext,
    WorkContextFact,
    WorkContextSource,
    WorkContextStatus,
)


@dataclass(frozen=True)
class TerminalTaskLoopProjection:
    conversation_id: str
    source_state: str
    topic: str
    next_step: str
    blocker: str
    capability_context: dict[str, Any]
    selected_blueprint: dict[str, Any]
    discovered_blueprints: list[dict[str, Any]]
    next_tools: list[str]


def _tool_blocker_from_status_rows(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "").strip().lower()
        if status in {"", "ok", "success", "completed"}:
            continue
        tool_name = str(row.get("tool_name") or "tool").strip()
        reason = str(row.get("reason") or status).strip()
        return f"{tool_name}:{reason}" if reason else tool_name
    return ""


def _recovery_hint(snapshot: TaskLoopSnapshot) -> dict[str, Any]:
    for artifact in reversed(list(snapshot.verified_artifacts or [])):
        if not isinstance(artifact, dict):
            continue
        if str(artifact.get("artifact_type") or "").strip().lower() != "container_recovery_hint":
            continue
        return dict(artifact)
    return {}


def _terminal_blocker(snapshot: TaskLoopSnapshot) -> str:
    last_step_result = snapshot.last_step_result if isinstance(snapshot.last_step_result, dict) else {}
    blocker = _tool_blocker_from_status_rows(list(last_step_result.get("tool_statuses") or []))
    if blocker:
        return blocker
    execution_result = last_step_result.get("execution_result")
    if isinstance(execution_result, dict):
        blocker = _tool_blocker_from_status_rows(list(execution_result.get("tool_statuses") or []))
        if blocker:
            return blocker
    for item in list(last_step_result.get("blockers") or []):
        text = str(item or "").strip()
        if text:
            return text
    if snapshot.stop_reason is not None:
        return str(snapshot.stop_reason.value or "").strip()
    return ""


def _terminal_next_step(snapshot: TaskLoopSnapshot, blocker: str) -> str:
    if str(snapshot.pending_step or "").strip():
        return str(snapshot.pending_step).strip()
    hint = _recovery_hint(snapshot)
    title = str(hint.get("replan_step_title") or "").strip()
    if title:
        return title
    completed = {str(item or "").strip() for item in list(snapshot.completed_steps or [])}
    for item in list(snapshot.current_plan or []):
        step_title = str(item or "").strip()
        if step_title and step_title not in completed:
            return step_title
    if blocker:
        return "Offenen technischen Blocker pruefen"
    return ""


def _terminal_next_tools(snapshot: TaskLoopSnapshot) -> list[str]:
    hint = _recovery_hint(snapshot)
    return [str(item or "").strip() for item in list(hint.get("next_tools") or []) if str(item or "").strip()]


def build_terminal_task_loop_projection(
    snapshot: TaskLoopSnapshot | None,
) -> TerminalTaskLoopProjection | None:
    if snapshot is None:
        return None
    if snapshot.state not in {TaskLoopState.COMPLETED, TaskLoopState.BLOCKED, TaskLoopState.CANCELLED}:
        return None

    capability_context = extract_container_context(snapshot)
    blocker = _terminal_blocker(snapshot)
    next_step = _terminal_next_step(snapshot, blocker)
    selected_blueprint = extract_selected_blueprint(snapshot)
    discovered_blueprints = extract_discovered_blueprints(snapshot)
    topic = str(snapshot.objective_summary or "").strip() or str(snapshot.pending_step or "").strip()

    if not any(
        [
            blocker,
            next_step,
            capability_context,
            selected_blueprint,
            discovered_blueprints,
            topic,
        ]
    ):
        return None

    return TerminalTaskLoopProjection(
        conversation_id=str(snapshot.conversation_id or "").strip(),
        source_state=str(snapshot.state.value or "").strip(),
        topic=topic,
        next_step=next_step,
        blocker=blocker,
        capability_context=dict(capability_context or {}),
        selected_blueprint=dict(selected_blueprint or {}),
        discovered_blueprints=[row for row in discovered_blueprints if isinstance(row, dict)],
        next_tools=_terminal_next_tools(snapshot),
    )


def build_terminal_task_loop_verified_facts(
    *,
    selected_blueprint: dict[str, Any] | None,
    discovered_blueprints: Iterable[dict[str, Any]] | None,
) -> tuple[WorkContextFact, ...]:
    facts: list[WorkContextFact] = []

    selected = str(
        (selected_blueprint or {}).get("label")
        or (selected_blueprint or {}).get("blueprint_id")
        or ""
    ).strip()
    if selected:
        facts.append(
            WorkContextFact(
                key="selected_blueprint",
                value=selected,
                source=WorkContextSource.TASK_LOOP,
                confidence=1.0,
            )
        )

    labels: list[str] = []
    for row in list(discovered_blueprints or [])[:6]:
        if not isinstance(row, dict):
            continue
        label = str(row.get("name") or row.get("blueprint_id") or row.get("id") or "").strip()
        if label:
            labels.append(label)
    if labels:
        facts.append(
            WorkContextFact(
                key="discovered_blueprints",
                value=", ".join(labels),
                source=WorkContextSource.TASK_LOOP,
                confidence=1.0,
            )
        )

    return tuple(facts)


def build_terminal_task_loop_missing_facts(
    *,
    capability_context: dict[str, Any] | None,
    selected_blueprint: dict[str, Any] | None,
    discovered_blueprints: Iterable[dict[str, Any]] | None,
    blocker: str,
) -> tuple[str, ...]:
    missing: list[str] = []
    request_family = str((capability_context or {}).get("request_family") or "").strip().lower()
    rows = [row for row in list(discovered_blueprints or []) if isinstance(row, dict)]

    if request_family == "python_container":
        python_rows = [
            row for row in rows
            if "python" in " ".join(
                str(row.get(key) or "") for key in ("id", "blueprint_id", "name", "description")
            ).lower()
        ]
        if not python_rows:
            missing.append("python_blueprint")
        elif not selected_blueprint:
            missing.append("selected_blueprint")
    elif rows and not selected_blueprint:
        missing.append("selected_blueprint")

    if str(blocker or "").strip():
        missing.append("block_reason")

    return tuple(missing)


def build_terminal_task_loop_status(source_state: str, *, has_blocker: bool) -> WorkContextStatus:
    value = str(source_state or "").strip().lower()
    if value == "blocked":
        return WorkContextStatus.BLOCKED
    if value == "cancelled":
        return WorkContextStatus.CANCELLED
    if value == "waiting_for_user":
        return WorkContextStatus.WAITING
    if has_blocker:
        return WorkContextStatus.BLOCKED
    return WorkContextStatus.COMPLETED


def build_terminal_task_loop_work_context(
    *,
    conversation_id: str,
    topic: str,
    source_state: str,
    next_step: str,
    blocker: str,
    capability_context: dict[str, Any] | None,
    selected_blueprint: dict[str, Any] | None,
    discovered_blueprints: Iterable[dict[str, Any]] | None,
    next_tools: Iterable[str] | None = None,
) -> WorkContext:
    return WorkContext(
        conversation_id=str(conversation_id or "").strip(),
        topic=str(topic or "").strip(),
        status=build_terminal_task_loop_status(source_state, has_blocker=bool(blocker)),
        source=WorkContextSource.TASK_LOOP,
        next_step=str(next_step or "").strip(),
        blocker=str(blocker or "").strip(),
        verified_facts=build_terminal_task_loop_verified_facts(
            selected_blueprint=selected_blueprint,
            discovered_blueprints=discovered_blueprints,
        ),
        missing_facts=build_terminal_task_loop_missing_facts(
            capability_context=capability_context,
            selected_blueprint=selected_blueprint,
            discovered_blueprints=discovered_blueprints,
            blocker=blocker,
        ),
        capability_context=dict(capability_context or {}),
        metadata={
            "source_state": str(source_state or "").strip(),
            "next_tools": [str(item or "").strip() for item in list(next_tools or []) if str(item or "").strip()],
        },
    )

__all__ = [
    "TerminalTaskLoopProjection",
    "build_terminal_task_loop_projection",
    "build_terminal_task_loop_missing_facts",
    "build_terminal_task_loop_status",
    "build_terminal_task_loop_verified_facts",
    "build_terminal_task_loop_work_context",
]
