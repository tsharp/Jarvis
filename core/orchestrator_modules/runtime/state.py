from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.container_state_utils import (
    normalize_container_entries as _normalize_container_entries,
    select_preferred_container_id as _select_preferred_container_id,
    tool_requires_container_id as _tool_requires_container_id,
)
from core.grounding_state_utils import (
    build_grounding_state_payload,
    extract_recent_grounding_state,
    grounding_evidence_has_content,
    has_usable_grounding_evidence,
    inject_carryover_grounding_evidence,
)
from core.orchestrator_runtime_utils import (
    build_followup_tool_reuse_specs,
    parse_container_list_result_for_selection,
    should_attempt_followup_tool_reuse,
    stringify_reuse_tool_names,
)


def get_recent_container_state(
    *,
    container_state_store: Any,
    conversation_id: str,
    history_len: int = 0,
) -> Optional[Dict[str, Any]]:
    return container_state_store.get_recent(conversation_id, history_len)


def normalize_container_entries(rows: Any, *, limit: int = 64) -> List[Dict[str, str]]:
    return _normalize_container_entries(rows, limit=limit)


def remember_container_state(
    *,
    container_state_store: Any,
    conversation_id: str,
    last_active_container_id: str = "",
    home_container_id: str = "",
    known_containers: Optional[List[Dict[str, str]]] = None,
    history_len: int = 0,
) -> None:
    container_state_store.remember(
        conversation_id,
        last_active_container_id=last_active_container_id,
        home_container_id=home_container_id,
        known_containers=known_containers,
        history_len=history_len,
    )


def update_container_state_from_tool_result(
    *,
    container_state_store: Any,
    conversation_id: str,
    tool_name: str,
    tool_args: Dict[str, Any],
    result: Any,
    history_len: int = 0,
) -> None:
    container_state_store.update_from_tool_result(
        conversation_id,
        tool_name,
        tool_args,
        result,
        history_len=history_len,
    )


def tool_requires_container_id(
    tool_name: str,
    *,
    container_id_required_tools: List[str],
) -> bool:
    return _tool_requires_container_id(tool_name, container_id_required_tools)


def select_preferred_container_id(
    rows: Any,
    *,
    expected_home_blueprint_id: str,
    preferred_ids: Optional[List[str]] = None,
) -> str:
    return _select_preferred_container_id(
        rows,
        expected_home_blueprint_id=expected_home_blueprint_id,
        preferred_ids=preferred_ids,
    )


def resolve_pending_container_id_sync(
    *,
    tool_hub: Any,
    conversation_id: str,
    preferred_ids: Optional[List[str]],
    history_len: int,
    safe_str_fn: Callable[[Any, int], str],
    update_container_state_from_tool_result_fn: Callable[..., None],
    expected_home_blueprint_id: str,
) -> Tuple[str, str]:
    try:
        list_result = tool_hub.call_tool("container_list", {})
    except Exception as exc:
        return "", f"container_list_failed:{safe_str_fn(exc, 160)}"

    update_container_state_from_tool_result_fn(
        conversation_id,
        "container_list",
        {},
        list_result,
        history_len=history_len,
    )
    selected, parse_err = parse_container_list_result_for_selection(
        list_result,
        expected_home_blueprint_id=expected_home_blueprint_id,
        preferred_ids=preferred_ids,
    )
    if parse_err:
        return "", f"container_list_error:{safe_str_fn(parse_err, 160)}"
    if selected:
        return selected, ""
    return "", "no_active_container_found"


async def resolve_pending_container_id_async(
    *,
    tool_hub: Any,
    conversation_id: str,
    preferred_ids: Optional[List[str]],
    history_len: int,
    safe_str_fn: Callable[[Any, int], str],
    update_container_state_from_tool_result_fn: Callable[..., None],
    expected_home_blueprint_id: str,
) -> Tuple[str, str]:
    try:
        if hasattr(tool_hub, "call_tool_async"):
            list_result = await tool_hub.call_tool_async("container_list", {})
        else:
            list_result = await asyncio.to_thread(tool_hub.call_tool, "container_list", {})
    except Exception as exc:
        return "", f"container_list_failed:{safe_str_fn(exc, 160)}"

    update_container_state_from_tool_result_fn(
        conversation_id,
        "container_list",
        {},
        list_result,
        history_len=history_len,
    )
    selected, parse_err = parse_container_list_result_for_selection(
        list_result,
        expected_home_blueprint_id=expected_home_blueprint_id,
        preferred_ids=preferred_ids,
    )
    if parse_err:
        return "", f"container_list_error:{safe_str_fn(parse_err, 160)}"
    if selected:
        return selected, ""
    return "", "no_active_container_found"


def get_recent_grounding_state(
    *,
    conversation_grounding_state: Dict[str, Dict[str, Any]],
    conversation_grounding_lock: Any,
    conversation_id: str,
    history_len: int = 0,
    ttl_s: int,
    ttl_turns: int,
) -> Optional[Dict[str, Any]]:
    conv_id = str(conversation_id or "").strip()
    if not conv_id:
        return None
    with conversation_grounding_lock:
        state = conversation_grounding_state.get(conv_id)
        snapshot, should_drop = extract_recent_grounding_state(
            state,
            now_ts=time.time(),
            ttl_s=ttl_s,
            ttl_turns=ttl_turns,
            history_len=history_len,
        )
        if should_drop:
            conversation_grounding_state.pop(conv_id, None)
        return snapshot


def remember_conversation_grounding_state(
    *,
    conversation_grounding_state: Dict[str, Dict[str, Any]],
    conversation_grounding_lock: Any,
    conversation_id: str,
    verified_plan: Dict[str, Any],
    history_len: int = 0,
    sanitize_tool_args_fn: Callable[[Any], Dict[str, Any]],
    evidence_has_content_fn: Callable[[Dict[str, Any]], bool],
) -> None:
    conv_id = str(conversation_id or "").strip()
    if not conv_id or not isinstance(verified_plan, dict):
        return
    payload = build_grounding_state_payload(
        verified_plan,
        sanitize_tool_args=sanitize_tool_args_fn,
        evidence_has_content=evidence_has_content_fn,
        max_evidence=8,
        max_tool_runs=6,
        max_fallback_tool_runs=4,
    )
    if not payload:
        return

    with conversation_grounding_lock:
        conversation_grounding_state[conv_id] = {
            "updated_at": time.time(),
            "history_len": int(history_len or 0),
            "tool_runs": payload.get("tool_runs", []),
            "evidence": payload.get("evidence", []),
        }


def inject_carryover_grounding_evidence_runtime(
    *,
    conversation_id: str,
    verified_plan: Dict[str, Any],
    history_len: int = 0,
    get_recent_grounding_state_fn: Callable[[str, int], Optional[Dict[str, Any]]],
    evidence_has_content_fn: Callable[[Dict[str, Any]], bool],
    log_info_fn: Callable[[str], None],
) -> None:
    if not isinstance(verified_plan, dict):
        return
    state = get_recent_grounding_state_fn(conversation_id, history_len)
    injected = inject_carryover_grounding_evidence(
        verified_plan,
        state,
        evidence_has_content=evidence_has_content_fn,
        max_carry_evidence=8,
        max_selected_tools=4,
    )
    if injected:
        log_info_fn("[Orchestrator] Carry-over grounding evidence injected from recent turn")


def grounding_evidence_has_content_runtime(item: Dict[str, Any]) -> bool:
    return grounding_evidence_has_content(item)


def has_usable_grounding_evidence_runtime(
    verified_plan: Dict[str, Any],
    *,
    evidence_has_content_fn: Callable[[Dict[str, Any]], bool],
) -> bool:
    return has_usable_grounding_evidence(
        verified_plan,
        evidence_has_content=evidence_has_content_fn,
    )


def resolve_followup_tool_reuse_runtime(
    *,
    user_text: str,
    verified_plan: Dict[str, Any],
    conversation_id: str = "",
    chat_history: Optional[list] = None,
    followup_enabled: bool,
    contains_explicit_tool_intent_fn: Callable[[str], bool],
    looks_like_short_fact_followup_fn: Callable[[str, Optional[list]], bool],
    looks_like_short_confirmation_followup_fn: Callable[[str, Optional[list]], bool],
    looks_like_short_confirmation_followup_state_only_fn: Callable[[str], bool],
    get_recent_grounding_state_fn: Callable[[str, int], Optional[Dict[str, Any]]],
    sanitize_tool_args_fn: Callable[[Any], Dict[str, Any]],
    log_info_fn: Callable[[str], None],
) -> List[Any]:
    explicit_tool_intent = contains_explicit_tool_intent_fn(user_text)
    short_fact_followup = looks_like_short_fact_followup_fn(user_text, chat_history)
    short_confirmation_followup = looks_like_short_confirmation_followup_fn(user_text, chat_history)
    should_attempt = should_attempt_followup_tool_reuse(
        followup_enabled=followup_enabled,
        verified_plan=verified_plan,
        explicit_tool_intent=explicit_tool_intent,
        short_fact_followup=short_fact_followup,
        short_confirmation_followup=short_confirmation_followup,
    )
    history_len = len(chat_history) if isinstance(chat_history, list) else 0
    state = None
    if not should_attempt and not explicit_tool_intent:
        if looks_like_short_confirmation_followup_state_only_fn(user_text):
            state = get_recent_grounding_state_fn(conversation_id, history_len)
            if isinstance(state, dict) and list(state.get("tool_runs") or []):
                should_attempt = True
                verified_plan["_followup_tool_reuse_state_fallback"] = True
                log_info_fn(
                    "[Orchestrator] Follow-up tool reuse fallback active "
                    "(state-only confirmation)"
                )
    if not should_attempt:
        return []

    if state is None:
        state = get_recent_grounding_state_fn(conversation_id, history_len)
    if not state:
        return []

    out = build_followup_tool_reuse_specs(
        state,
        sanitize_tool_args=sanitize_tool_args_fn,
        max_tools=2,
    )
    if out:
        verified_plan["needs_chat_history"] = True
        verified_plan["_followup_tool_reuse_active"] = True
        log_info_fn(
            "[Orchestrator] Follow-up tool reuse active: "
            f"{stringify_reuse_tool_names(out)}"
        )
    return out
