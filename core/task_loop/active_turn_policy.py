from __future__ import annotations

from typing import Any, Dict, Optional

from core.task_loop.chat_runtime import (
    is_task_loop_cancel,
    is_task_loop_continue,
    should_restart_task_loop,
)
from core.task_loop.contracts import (
    TaskLoopStepExecutionSource,
    TaskLoopStepStatus,
    TaskLoopStepType,
)
from core.task_loop.routing_policy import is_authoritative_task_loop_execution


ACTIVE_TASK_LOOP_REASON_CONTINUE = "continue_active_task_loop"
ACTIVE_TASK_LOOP_REASON_RESTART = "restart_active_task_loop"
ACTIVE_TASK_LOOP_REASON_CANCEL = "terminate_active_task_loop_cancelled"
ACTIVE_TASK_LOOP_REASON_MODE_SHIFT = "terminate_active_task_loop_mode_shift"
ACTIVE_TASK_LOOP_REASON_BLOCKED = "terminate_active_task_loop_blocked"
ACTIVE_TASK_LOOP_REASON_CONTEXT_ONLY = "active_task_loop_context_only"


_META_PREFIXES = (
    "was ",
    "warum",
    "wieso",
    "wie ",
    "wer ",
    "wo ",
    "wann ",
    "welcher ",
    "welche ",
    "welches ",
    "status",
    "erklaer",
    "erklär",
    "erkläre",
    "erklaere",
    "was ist passiert",
    "was war das",
    "was laeuft",
    "was läuft",
)


def normalize_loop_user_text(user_text: str) -> str:
    return " ".join(str(user_text or "").strip().lower().split())


def is_authoritative_task_loop_turn(plan: Optional[Dict[str, Any]]) -> bool:
    return is_authoritative_task_loop_execution(plan)


def is_task_loop_meta_turn(user_text: str) -> bool:
    normalized = normalize_loop_user_text(user_text)
    if not normalized:
        return False
    if normalized.endswith("?"):
        return True
    return any(normalized.startswith(prefix) for prefix in _META_PREFIXES)


def _snapshot_step_status(snapshot: Any) -> str:
    if isinstance(getattr(snapshot, "last_step_result", None), dict):
        return str(snapshot.last_step_result.get("status") or "").strip().lower()
    current = getattr(snapshot, "current_step_status", None)
    return str(getattr(current, "value", current) or "").strip().lower()


def _snapshot_step_type(snapshot: Any) -> str:
    if isinstance(getattr(snapshot, "last_step_result", None), dict):
        return str(snapshot.last_step_result.get("step_type") or "").strip().lower()
    current = getattr(snapshot, "current_step_type", None)
    return str(getattr(current, "value", current) or "").strip().lower()


def _snapshot_execution_source(snapshot: Any) -> str:
    if isinstance(getattr(snapshot, "last_step_result", None), dict):
        return str(snapshot.last_step_result.get("step_execution_source") or "").strip().lower()
    current = getattr(snapshot, "step_execution_source", None)
    return str(getattr(current, "value", current) or "").strip().lower()


def is_runtime_resume_candidate(
    snapshot: Optional[Any],
    user_text: str,
    *,
    raw_request: Optional[Dict[str, Any]] = None,
) -> bool:
    if snapshot is None:
        return False
    if is_task_loop_cancel(user_text) or should_restart_task_loop(user_text, raw_request):
        return False
    normalized_user_text = normalize_loop_user_text(user_text)
    if not normalized_user_text:
        return False

    status = _snapshot_step_status(snapshot)
    step_type = _snapshot_step_type(snapshot)
    source = _snapshot_execution_source(snapshot)
    runtime_bound = (
        step_type in {TaskLoopStepType.TOOL_REQUEST.value, TaskLoopStepType.TOOL_EXECUTION.value}
        or source in {
            TaskLoopStepExecutionSource.ORCHESTRATOR.value,
            TaskLoopStepExecutionSource.APPROVAL.value,
        }
    )
    if not runtime_bound:
        return False

    if status == TaskLoopStepStatus.WAITING_FOR_APPROVAL.value:
        return is_task_loop_continue(user_text)
    if status == TaskLoopStepStatus.WAITING_FOR_USER.value:
        return (not is_task_loop_continue(user_text)) and (not is_task_loop_meta_turn(user_text))
    return False


def runtime_resume_user_text(snapshot: Optional[Any], user_text: str) -> str:
    if snapshot is None:
        return ""
    clean = str(user_text or "").strip()
    if not clean:
        return ""
    if is_task_loop_continue(user_text) and not is_task_loop_cancel(user_text):
        return ""
    return clean


def classify_active_task_loop_routing(
    user_text: str,
    snapshot: Optional[Any],
    verified_plan: Optional[Dict[str, Any]],
    *,
    raw_request: Optional[Dict[str, Any]] = None,
) -> str:
    if snapshot is None:
        return ""
    if is_task_loop_cancel(user_text):
        return ACTIVE_TASK_LOOP_REASON_CANCEL
    if should_restart_task_loop(user_text, raw_request):
        return ACTIVE_TASK_LOOP_REASON_RESTART
    if is_authoritative_task_loop_turn(verified_plan):
        if is_task_loop_continue(user_text) or is_runtime_resume_candidate(
            snapshot,
            user_text,
            raw_request=raw_request,
        ):
            return ACTIVE_TASK_LOOP_REASON_CONTINUE
        return ACTIVE_TASK_LOOP_REASON_CONTEXT_ONLY

    blockers = []
    if isinstance(verified_plan, dict):
        blockers = [
            str(item or "").strip()
            for item in verified_plan.get("_authoritative_turn_mode_blockers") or []
            if str(item or "").strip()
        ]
    if blockers:
        return ACTIVE_TASK_LOOP_REASON_BLOCKED
    return ACTIVE_TASK_LOOP_REASON_MODE_SHIFT
