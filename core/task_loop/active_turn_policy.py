from __future__ import annotations

from typing import Any, Dict, Optional

from core.task_loop.chat_runtime import (
    is_task_loop_cancel,
    is_task_loop_continue,
    should_restart_task_loop,
)
from core.task_loop.contracts import (
    TaskLoopState,
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

ACTIVE_TASK_LOOP_DETAIL_EXPLICIT_CONTINUE = "explicit_continue_request"
ACTIVE_TASK_LOOP_DETAIL_RUNTIME_RESUME = "runtime_resume_candidate"
ACTIVE_TASK_LOOP_DETAIL_EXPLICIT_RESTART = "explicit_restart_request"
ACTIVE_TASK_LOOP_DETAIL_EXPLICIT_CANCEL = "explicit_cancel_request"
ACTIVE_TASK_LOOP_DETAIL_META_TURN = "meta_turn_background_preserved"
ACTIVE_TASK_LOOP_DETAIL_INDEPENDENT_TOOL_TURN = "independent_tool_turn_background_preserved"
ACTIVE_TASK_LOOP_DETAIL_BACKGROUND_PRESERVED = "background_loop_preserved"
ACTIVE_TASK_LOOP_DETAIL_AUTHORITATIVE_NON_RESUME = "authoritative_task_loop_non_resume_background"
ACTIVE_TASK_LOOP_DETAIL_BLOCKED_BY_CONTROL = "blocked_by_authoritative_turn_mode"
ACTIVE_TASK_LOOP_DETAIL_MODE_SHIFT = "mode_shift_clear_active_loop"


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
    last_step_result = getattr(snapshot, "last_step_result", None)
    if isinstance(last_step_result, dict) and last_step_result:
        return str(snapshot.last_step_result.get("status") or "").strip().lower()
    current = getattr(snapshot, "current_step_status", None)
    return str(getattr(current, "value", current) or "").strip().lower()


def _snapshot_step_type(snapshot: Any) -> str:
    last_step_result = getattr(snapshot, "last_step_result", None)
    if isinstance(last_step_result, dict) and last_step_result:
        return str(snapshot.last_step_result.get("step_type") or "").strip().lower()
    current = getattr(snapshot, "current_step_type", None)
    return str(getattr(current, "value", current) or "").strip().lower()


def _snapshot_execution_source(snapshot: Any) -> str:
    last_step_result = getattr(snapshot, "last_step_result", None)
    if isinstance(last_step_result, dict) and last_step_result:
        return str(snapshot.last_step_result.get("step_execution_source") or "").strip().lower()
    current = getattr(snapshot, "step_execution_source", None)
    return str(getattr(current, "value", current) or "").strip().lower()


def _snapshot_state(snapshot: Any) -> str:
    current = getattr(snapshot, "state", None)
    return str(getattr(current, "value", current) or "").strip().lower()


def _active_step_meta(snapshot: Any) -> Dict[str, Any]:
    pending_step = str(getattr(snapshot, "pending_step", "") or "").strip()
    current_step_id = str(getattr(snapshot, "current_step_id", "") or "").strip()
    for step in list(getattr(snapshot, "plan_steps", []) or []):
        if not isinstance(step, dict):
            continue
        step_title = str(step.get("title") or "").strip()
        step_id = str(step.get("step_id") or "").strip()
        if pending_step and step_title == pending_step:
            return dict(step)
        if current_step_id and step_id == current_step_id:
            return dict(step)
    return {}


def _active_step_suggested_tools(snapshot: Any) -> set[str]:
    step_meta = _active_step_meta(snapshot)
    return {
        str(tool or "").strip()
        for tool in step_meta.get("suggested_tools") or []
        if str(tool or "").strip()
    }


def _active_step_capability_type(snapshot: Any) -> str:
    step_meta = _active_step_meta(snapshot)
    requested_capability = step_meta.get("requested_capability")
    if not isinstance(requested_capability, dict):
        return ""
    return str(requested_capability.get("capability_type") or "").strip().lower()


def _plan_suggested_tools(plan: Optional[Dict[str, Any]]) -> set[str]:
    if not isinstance(plan, dict):
        return set()
    return {
        str(tool or "").strip()
        for tool in plan.get("suggested_tools") or []
        if str(tool or "").strip()
    }


def _plan_capability_type(plan: Optional[Dict[str, Any]]) -> str:
    if not isinstance(plan, dict):
        return ""
    requested_capability = plan.get("requested_capability")
    if isinstance(requested_capability, dict):
        cap_type = str(requested_capability.get("capability_type") or "").strip().lower()
        if cap_type:
            return cap_type
    resolution = plan.get("_container_resolution")
    if isinstance(resolution, dict):
        cap_type = str(resolution.get("capability_type") or "").strip().lower()
        if cap_type:
            return cap_type
    return ""


def _plan_looks_like_independent_tool_turn(
    snapshot: Optional[Any],
    verified_plan: Optional[Dict[str, Any]],
) -> bool:
    if snapshot is None or not isinstance(verified_plan, dict):
        return False
    plan_tools = _plan_suggested_tools(verified_plan)
    active_tools = _active_step_suggested_tools(snapshot)
    if plan_tools and active_tools and plan_tools.isdisjoint(active_tools):
        return True
    plan_capability = _plan_capability_type(verified_plan)
    active_capability = _active_step_capability_type(snapshot)
    if plan_capability and active_capability and plan_capability != active_capability:
        return True
    return False


def is_independent_tool_turn_candidate(
    snapshot: Optional[Any],
    verified_plan: Optional[Dict[str, Any]],
) -> bool:
    return _plan_looks_like_independent_tool_turn(snapshot, verified_plan)


def can_keep_active_task_loop_in_background(snapshot: Optional[Any]) -> bool:
    if snapshot is None:
        return False
    return _snapshot_state(snapshot) in {
        TaskLoopState.WAITING_FOR_USER.value,
        TaskLoopState.BLOCKED.value,
    }


def explain_active_task_loop_routing(
    user_text: str,
    snapshot: Optional[Any],
    verified_plan: Optional[Dict[str, Any]],
    *,
    raw_request: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if snapshot is None:
        return {
            "reason": "",
            "detail": "",
            "runtime_resume_candidate": False,
            "background_preservable": False,
            "meta_turn": False,
            "independent_tool_turn": False,
        }

    runtime_resume_candidate = is_runtime_resume_candidate(
        snapshot,
        user_text,
        raw_request=raw_request,
        verified_plan=verified_plan,
    )
    background_preservable = can_keep_active_task_loop_in_background(snapshot)
    meta_turn = is_task_loop_meta_turn(user_text)
    independent_tool_turn = _plan_looks_like_independent_tool_turn(snapshot, verified_plan)

    if is_task_loop_cancel(user_text):
        return {
            "reason": ACTIVE_TASK_LOOP_REASON_CANCEL,
            "detail": ACTIVE_TASK_LOOP_DETAIL_EXPLICIT_CANCEL,
            "runtime_resume_candidate": runtime_resume_candidate,
            "background_preservable": background_preservable,
            "meta_turn": meta_turn,
            "independent_tool_turn": independent_tool_turn,
        }
    if should_restart_task_loop(user_text, raw_request):
        return {
            "reason": ACTIVE_TASK_LOOP_REASON_RESTART,
            "detail": ACTIVE_TASK_LOOP_DETAIL_EXPLICIT_RESTART,
            "runtime_resume_candidate": runtime_resume_candidate,
            "background_preservable": background_preservable,
            "meta_turn": meta_turn,
            "independent_tool_turn": independent_tool_turn,
        }
    if is_authoritative_task_loop_turn(verified_plan):
        if is_task_loop_continue(user_text):
            return {
                "reason": ACTIVE_TASK_LOOP_REASON_CONTINUE,
                "detail": ACTIVE_TASK_LOOP_DETAIL_EXPLICIT_CONTINUE,
                "runtime_resume_candidate": runtime_resume_candidate,
                "background_preservable": background_preservable,
                "meta_turn": meta_turn,
                "independent_tool_turn": independent_tool_turn,
            }
        if runtime_resume_candidate:
            return {
                "reason": ACTIVE_TASK_LOOP_REASON_CONTINUE,
                "detail": ACTIVE_TASK_LOOP_DETAIL_RUNTIME_RESUME,
                "runtime_resume_candidate": runtime_resume_candidate,
                "background_preservable": background_preservable,
                "meta_turn": meta_turn,
                "independent_tool_turn": independent_tool_turn,
            }
        return {
            "reason": ACTIVE_TASK_LOOP_REASON_CONTEXT_ONLY,
            "detail": ACTIVE_TASK_LOOP_DETAIL_AUTHORITATIVE_NON_RESUME,
            "runtime_resume_candidate": runtime_resume_candidate,
            "background_preservable": background_preservable,
            "meta_turn": meta_turn,
            "independent_tool_turn": independent_tool_turn,
        }

    if background_preservable:
        detail = ACTIVE_TASK_LOOP_DETAIL_BACKGROUND_PRESERVED
        if independent_tool_turn:
            detail = ACTIVE_TASK_LOOP_DETAIL_INDEPENDENT_TOOL_TURN
        elif meta_turn:
            detail = ACTIVE_TASK_LOOP_DETAIL_META_TURN
        return {
            "reason": ACTIVE_TASK_LOOP_REASON_CONTEXT_ONLY,
            "detail": detail,
            "runtime_resume_candidate": runtime_resume_candidate,
            "background_preservable": background_preservable,
            "meta_turn": meta_turn,
            "independent_tool_turn": independent_tool_turn,
        }

    blockers = []
    if isinstance(verified_plan, dict):
        blockers = [
            str(item or "").strip()
            for item in verified_plan.get("_authoritative_turn_mode_blockers") or []
            if str(item or "").strip()
        ]
    if blockers:
        return {
            "reason": ACTIVE_TASK_LOOP_REASON_BLOCKED,
            "detail": ACTIVE_TASK_LOOP_DETAIL_BLOCKED_BY_CONTROL,
            "runtime_resume_candidate": runtime_resume_candidate,
            "background_preservable": background_preservable,
            "meta_turn": meta_turn,
            "independent_tool_turn": independent_tool_turn,
        }
    return {
        "reason": ACTIVE_TASK_LOOP_REASON_MODE_SHIFT,
        "detail": ACTIVE_TASK_LOOP_DETAIL_MODE_SHIFT,
        "runtime_resume_candidate": runtime_resume_candidate,
        "background_preservable": background_preservable,
        "meta_turn": meta_turn,
        "independent_tool_turn": independent_tool_turn,
    }


def is_runtime_resume_candidate(
    snapshot: Optional[Any],
    user_text: str,
    *,
    raw_request: Optional[Dict[str, Any]] = None,
    verified_plan: Optional[Dict[str, Any]] = None,
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
        if _plan_looks_like_independent_tool_turn(snapshot, verified_plan):
            return False
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
    explanation = explain_active_task_loop_routing(
        user_text,
        snapshot,
        verified_plan,
        raw_request=raw_request,
    )
    return str(explanation.get("reason") or "").strip()
