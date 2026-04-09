from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional, Tuple

from core.tools.tool_result import ToolResult


_NORMALIZE_NATIVE_TOOLS = {
    "request_container",
    "home_start",
    "stop_container",
    "exec_in_container",
    "blueprint_list",
    "container_stats",
    "container_logs",
    "container_list",
    "container_inspect",
    "home_read",
    "home_write",
    "home_list",
    "autonomous_skill_task",
    "run_skill",
    "create_skill",
    "list_skills",
    "get_skill_info",
    "validate_skill_code",
    "autonomy_cron_status",
    "autonomy_cron_list_jobs",
    "autonomy_cron_validate",
    "autonomy_cron_create_job",
    "autonomy_cron_update_job",
    "autonomy_cron_pause_job",
    "autonomy_cron_resume_job",
    "autonomy_cron_run_now",
    "autonomy_cron_delete_job",
    "autonomy_cron_queue",
    "cron_reference_links_list",
    "get_system_info",
    "get_system_overview",
}
_NORMALIZE_EXECUTION_TOOLS = {
    "run_skill",
    "exec_in_container",
    "request_container",
    "home_start",
    "create_skill",
    "container_stats",
    "container_logs",
}


def contains_keyword_intent(
    text: str,
    keyword: str,
    *,
    whole_word: bool = False,
) -> bool:
    if not text or not keyword:
        return False
    if not whole_word:
        return keyword in text
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(keyword)}(?![A-Za-z0-9_])"
    return re.search(pattern, text) is not None


def extract_tool_domain_tag(
    text: str,
    *,
    tool_domain_tag_re: Any,
    tool_domain_tag_short_re: Any,
) -> str:
    raw = str(text or "")
    match = tool_domain_tag_re.search(raw)
    if not match:
        match = tool_domain_tag_short_re.search(raw)
    if not match:
        return ""
    return str(match.group(1) or "").strip().upper()


def contains_explicit_tool_intent(
    user_text: str,
    *,
    extract_tool_domain_tag_fn: Callable[[str], str],
    contains_keyword_intent_fn: Callable[..., bool],
    tool_intent_keywords: Any,
    tool_intent_word_keywords: Any,
) -> bool:
    lower = (user_text or "").lower()
    if extract_tool_domain_tag_fn(lower):
        return True
    for token in tool_intent_keywords:
        if contains_keyword_intent_fn(
            lower,
            token,
            whole_word=token in tool_intent_word_keywords,
        ):
            return True
    return False


def contains_explicit_skill_intent(
    user_text: str,
    *,
    extract_tool_domain_tag_fn: Callable[[str], str],
    contains_keyword_intent_fn: Callable[..., bool],
    skill_intent_keywords: Any,
    skill_intent_word_keywords: Any,
) -> bool:
    lower = (user_text or "").lower()
    if extract_tool_domain_tag_fn(lower) == "SKILL":
        return True
    for token in skill_intent_keywords:
        if contains_keyword_intent_fn(
            lower,
            token,
            whole_word=token in skill_intent_word_keywords,
        ):
            return True
    return False


def has_cron_schedule_signal(
    user_text: str,
    route: Optional[Dict[str, Any]] = None,
) -> bool:
    text = str(user_text or "").lower()
    route = route if isinstance(route, dict) else {}
    if str(route.get("cron_expression_hint") or "").strip():
        return True
    if str(route.get("one_shot_at_hint") or "").strip():
        return True
    if str(route.get("schedule_mode_hint") or "").strip().lower() in {"one_shot", "recurring"}:
        return True
    if re.search(
        r"(?:in|nach|um|at)\s+\d{1,4}\s*(?:sek|sekunden|s|min|minuten|minute|h|std|stunden|stunde)\b",
        text,
    ):
        return True
    return False


def is_explicit_cron_create_intent(
    user_text: str,
    route: Optional[Dict[str, Any]] = None,
    *,
    cron_meta_guard_markers: Any,
    has_cron_schedule_signal_fn: Callable[[str, Optional[Dict[str, Any]]], bool],
) -> bool:
    text = str(user_text or "").lower()
    if not text:
        return False
    if any(marker in text for marker in cron_meta_guard_markers):
        return False
    create_markers = (
        "erstelle",
        "erstell",
        "anlege",
        "anleg",
        "create",
        "setze auf",
        "schedule",
        "richte ein",
        "einrichten",
    )
    if not any(marker in text for marker in create_markers):
        return False
    return has_cron_schedule_signal_fn(text, route)


def maybe_downgrade_cron_create_signal(
    user_text: str,
    signal: Dict[str, Any],
    *,
    is_explicit_cron_create_intent_fn: Callable[[str, Optional[Dict[str, Any]]], bool],
) -> Dict[str, Any]:
    if not isinstance(signal, dict):
        return signal
    tag = str(signal.get("domain_tag") or "").strip().upper()
    op = str(signal.get("operation") or "").strip().lower()
    if tag != "CRONJOB" or op != "create":
        return signal
    if is_explicit_cron_create_intent_fn(user_text, signal):
        return signal
    patched = dict(signal)
    patched["operation"] = "status"
    patched["cron_create_downgraded"] = True
    patched["reason"] = (
        f"{str(signal.get('reason') or '').strip()}, cron:create->status_guard"
    ).strip(", ")
    return patched


def normalize_tools(
    suggested_tools: list,
    *,
    get_hub_fn: Callable[[], Any],
    log_info_fn: Callable[[str], None],
) -> list:
    """
    Normalize suggested_tools:
    - filter invalid tool names
    - convert installed skill names into run_skill specs
    """
    if not suggested_tools:
        return []

    tool_hub = get_hub_fn()
    tool_hub.initialize()

    installed_skills = set()
    try:
        skills_result = tool_hub.call_tool("list_skills", {"include_available": False})
        skills_data = skills_result or {}
        if "structuredContent" in skills_data:
            skills_data = skills_data["structuredContent"]
        for skill in skills_data.get("installed", []):
            installed_skills.add(skill.get("name", ""))
    except Exception:
        pass

    normalized = []
    for tool in suggested_tools:
        if isinstance(tool, dict):
            normalized.append(tool)
        elif (
            tool_hub.get_mcp_for_tool(tool)
            or tool in _NORMALIZE_NATIVE_TOOLS
            or tool_hub._tool_definitions.get(tool, {}).get("execution") == "direct"
        ):
            normalized.append(tool)
        elif tool in installed_skills:
            log_info_fn(f"[Orchestrator] Skill-Normalization: '{tool}' -> run_skill(name='{tool}')")
            normalized.append({"tool": "run_skill", "args": {"name": tool, "action": "run", "args": {}}})
        else:
            log_info_fn(f"[Orchestrator] Filtered invalid tool: '{tool}'")

    has_execution = any(
        (isinstance(tool, dict) and tool.get("tool") in _NORMALIZE_EXECUTION_TOOLS)
        or (isinstance(tool, str) and tool in _NORMALIZE_EXECUTION_TOOLS)
        for tool in normalized
    )
    if has_execution:
        before = len(normalized)
        normalized = [tool for tool in normalized if not (isinstance(tool, str) and tool == "home_write")]
        if len(normalized) < before:
            log_info_fn("[Orchestrator] home_write gefiltert (Execution-Tool vorhanden)")
    return normalized


def extract_cron_job_id_from_text(user_text: str, verified_plan: Optional[Dict[str, Any]]) -> str:
    route = (verified_plan or {}).get("_domain_route", {}) if isinstance(verified_plan, dict) else {}
    hinted = str((route or {}).get("cron_job_id_hint") or "").strip().lower()
    if re.fullmatch(r"[a-f0-9]{12}", hinted):
        return hinted
    match = re.search(r"\b([a-f0-9]{12})\b", str(user_text or "").lower())
    return str(match.group(1)).lower() if match else ""


def extract_cron_expression_from_text(user_text: str, verified_plan: Optional[Dict[str, Any]]) -> str:
    route = (verified_plan or {}).get("_domain_route", {}) if isinstance(verified_plan, dict) else {}
    hinted = str((route or {}).get("cron_expression_hint") or "").strip()
    if hinted:
        return hinted

    lower = str(user_text or "").lower()
    match = re.search(r"(?<!\S)([\d*/,\-]+\s+[\d*/,\-]+\s+[\d*/,\-]+\s+[\d*/,\-]+\s+[\d*/,\-]+)(?!\S)", lower)
    if match:
        return str(match.group(1) or "").strip()
    match = re.search(r"(?:jede|alle)\s+(\d{1,3})\s*(?:min|minuten|minute)\b", lower)
    if match:
        value = max(1, min(59, int(match.group(1))))
        return f"*/{value} * * * *"
    match = re.search(r"(?:in|nach)\s+(\d{1,3})\s*(?:min|minuten|minute)\b", lower)
    if match:
        value = max(1, min(59, int(match.group(1))))
        return f"*/{value} * * * *"
    match = re.search(r"(?:einmal|once)\s+in\s+(\d{1,3})\s*(?:min|minuten|minute)\b", lower)
    if match:
        value = max(1, min(59, int(match.group(1))))
        return f"*/{value} * * * *"
    if "jede minute" in lower or "every minute" in lower:
        return "*/1 * * * *"
    if "jede stunde" in lower or "every hour" in lower:
        return "0 * * * *"
    return "*/15 * * * *"


def extract_one_shot_run_at_from_text(
    user_text: str,
    verified_plan: Optional[Dict[str, Any]],
    *,
    datetime_cls: Any = datetime,
    timedelta_cls: Any = timedelta,
    timezone_utc: Any = timezone.utc,
) -> str:
    route = (verified_plan or {}).get("_domain_route", {}) if isinstance(verified_plan, dict) else {}
    hinted = str((route or {}).get("one_shot_at_hint") or "").strip()
    if hinted:
        return hinted

    lower = str(user_text or "").lower()
    now = datetime_cls.utcnow()
    match = re.search(
        r"(?:in|nach)\s+(\d{1,4}|einer|einem|ein|one)\s*"
        r"(sek|sekunde|sekunden|seconds?|s|min|minute|minuten|minutes?|h|std|stunde|stunden|hours?|tage?|days?)\b",
        lower,
    )
    if match:
        raw_amount = str(match.group(1) or "").strip()
        amount = 1 if raw_amount in {"einer", "einem", "ein", "one"} else max(1, int(raw_amount))
        unit = str(match.group(2) or "").strip().lower()
        if unit.startswith(("sek", "s")):
            run_at = now + timedelta_cls(seconds=amount)
        elif unit.startswith(("h", "std", "stun")):
            run_at = now + timedelta_cls(hours=amount)
        elif unit.startswith(("tag", "day")):
            run_at = now + timedelta_cls(days=amount)
        else:
            run_at = now + timedelta_cls(minutes=amount)
        run_at = (run_at + timedelta_cls(minutes=1)).replace(second=0, microsecond=0)
        return run_at.replace(tzinfo=timezone_utc).isoformat().replace("+00:00", "Z")

    match = re.search(r"(?:heute|today)\s*(?:um|at)?\s*(\d{1,2})[:.](\d{2})\b", lower)
    if match:
        hour = max(0, min(23, int(match.group(1))))
        minute = max(0, min(59, int(match.group(2))))
        run_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if run_at <= now:
            run_at = run_at + timedelta_cls(days=1)
        return run_at.replace(tzinfo=timezone_utc).isoformat().replace("+00:00", "Z")

    return ""


def extract_cron_schedule_from_text(
    user_text: str,
    verified_plan: Optional[Dict[str, Any]],
    *,
    extract_cron_expression_from_text_fn: Callable[[str, Optional[Dict[str, Any]]], str],
    extract_one_shot_run_at_from_text_fn: Callable[[str, Optional[Dict[str, Any]]], str],
    datetime_cls: Any = datetime,
    timedelta_cls: Any = timedelta,
    timezone_utc: Any = timezone.utc,
) -> Dict[str, str]:
    route = (verified_plan or {}).get("_domain_route", {}) if isinstance(verified_plan, dict) else {}
    mode_hint = str((route or {}).get("schedule_mode_hint") or "").strip().lower()
    lower = str(user_text or "").lower()

    schedule_mode = "unknown"
    if mode_hint in {"one_shot", "recurring"}:
        schedule_mode = mode_hint
    else:
        one_shot_markers = ("einmalig", "nur einmal", "einmal", "one-time", "once")
        recurring_markers = ("jede ", "alle ", "täglich", "taeglich", "wöchentlich", "woechentlich", "every ")
        has_one_shot = any(marker in lower for marker in one_shot_markers)
        has_recurring = any(marker in lower for marker in recurring_markers)
        if has_one_shot and not has_recurring:
            schedule_mode = "one_shot"
        elif has_recurring and not has_one_shot:
            schedule_mode = "recurring"

    cron_expr = extract_cron_expression_from_text_fn(user_text, verified_plan)
    run_at = extract_one_shot_run_at_from_text_fn(user_text, verified_plan)

    if schedule_mode == "one_shot" and not run_at:
        fallback = datetime_cls.utcnow().replace(second=0, microsecond=0) + timedelta_cls(minutes=1)
        run_at = fallback.replace(tzinfo=timezone_utc).isoformat().replace("+00:00", "Z")

    if schedule_mode == "unknown":
        schedule_mode = "one_shot" if run_at else "recurring"

    if schedule_mode == "one_shot":
        cron_expr = cron_expr or "*/15 * * * *"
    else:
        cron_expr = cron_expr or "*/15 * * * *"
        run_at = ""

    return {
        "schedule_mode": schedule_mode,
        "cron": cron_expr,
        "run_at": run_at,
    }


def build_cron_name(user_text: str) -> str:
    lower = str(user_text or "").strip().lower()
    if not lower:
        return "trion-cron-job"
    cleaned = re.sub(r"[^a-z0-9]+", "-", lower).strip("-")
    if not cleaned:
        cleaned = "trion-cron-job"
    return f"cron-{cleaned[:40]}"


def looks_like_self_state_request(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    low = raw.lower()
    if "wie dein tag war" in low or "wie dein tag ist" in low:
        return True
    if "wie es dir geht" in low:
        return True
    if "wie du dich" in low and ("fühl" in low or "fuehl" in low or "feel" in low):
        return True
    return False


def build_cron_objective(
    user_text: str,
    *,
    looks_like_self_state_request_fn: Callable[[str], bool],
) -> str:
    text = str(user_text or "").strip()
    lower = text.lower()
    if looks_like_self_state_request_fn(text):
        return f"self_state_report::{text[:220]}"
    if any(token in lower for token in ("erinner", "remind", "erinnerung")):
        reminder_text = ""
        match = re.search(r"mir\s+zu\s+sagen[:,]?\s*(.+)$", text, flags=re.IGNORECASE)
        if match:
            reminder_text = str(match.group(1) or "").strip()
        if not reminder_text:
            match = re.search(
                r"(?:erinnere?\s+(?:mich|mir)|remind\s+me)\s*(?:daran)?[:,]?\s*(.+)$",
                text,
                flags=re.IGNORECASE,
            )
            if match:
                reminder_text = str(match.group(1) or "").strip()
        reminder_text = reminder_text.strip(" .,!:;")
        if not reminder_text:
            reminder_text = "Cronjob funktioniert?"
        return f"user_reminder::{reminder_text[:220]}"
    if any(token in lower for token in ("cleanup", "bereinigen", "aufräumen", "aufraeumen")):
        return "cleanup status summary"
    if any(token in lower for token in ("backup", "sichern", "archiv")):
        return "backup status summary"
    if text:
        return f"user_request::{text[:220]}"
    return ""


def extract_direct_cron_reminder_text(objective: str) -> str:
    text = str(objective or "").strip()
    lower = text.lower()
    if lower.startswith("user_reminder::"):
        reminder = text.split("::", 1)[1].strip()
        return reminder[:180] if reminder else "Cronjob funktioniert?"
    return ""


def extract_cron_ack_message_from_objective(
    objective: str,
    *,
    looks_like_self_state_request_fn: Callable[[str], bool],
) -> str:
    text = str(objective or "").strip()
    lower = text.lower()
    if lower.startswith("user_reminder::"):
        reminder = text.split("::", 1)[1].strip()
        return reminder[:180] if reminder else "Cronjob funktioniert?"
    if lower.startswith("self_state_report::"):
        return "Selbststatus beim Trigger ausgeben."
    if lower.startswith("user_request::"):
        request = text.split("::", 1)[1].strip()
        if looks_like_self_state_request_fn(request):
            return "Selbststatus beim Trigger ausgeben."
        return request[:180] if request else "Autonomes Ziel ausführen."
    return "Autonomes Ziel ausführen."


def format_utc_compact(
    raw_iso: str,
    *,
    datetime_cls: Any = datetime,
    timezone_utc: Any = timezone.utc,
) -> str:
    raw = str(raw_iso or "").strip()
    if not raw:
        return ""
    try:
        dt = datetime_cls.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone_utc)
        dt_utc = dt.astimezone(timezone_utc)
        return dt_utc.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return raw


def build_direct_cron_create_response(
    result: Any,
    tool_args: Dict[str, Any],
    conversation_id: str,
    *,
    detect_tool_error_fn: Callable[[Any], Tuple[bool, str]],
    format_utc_compact_fn: Callable[[str], str],
    extract_cron_ack_message_from_objective_fn: Callable[[str], str],
) -> str:
    payload = result.content if isinstance(result, ToolResult) else result
    if not isinstance(payload, dict):
        return ""
    is_error, _error_msg = detect_tool_error_fn(payload)
    if is_error:
        return ""

    job_id = str(payload.get("id") or payload.get("cron_job_id") or "").strip()
    name = str(payload.get("name") or tool_args.get("name") or "cron-job").strip() or "cron-job"
    mode = str(payload.get("schedule_mode") or tool_args.get("schedule_mode") or "recurring").strip().lower()
    run_at = str(payload.get("run_at") or tool_args.get("run_at") or "").strip()
    cron_expr = str(payload.get("cron") or tool_args.get("cron") or "").strip()
    objective = str(payload.get("objective") or tool_args.get("objective") or "").strip()
    effective_conv = str(payload.get("conversation_id") or tool_args.get("conversation_id") or conversation_id or "").strip()

    id_part = f" `{job_id}`" if job_id else ""
    if mode == "one_shot":
        run_at_label = format_utc_compact_fn(run_at) or "bald (UTC)"
        reminder = extract_cron_ack_message_from_objective_fn(objective)
        return (
            f"Cronjob erstellt{id_part}: `{name}`. "
            f"Einmalige Ausführung um {run_at_label}. "
            f"Rückmeldung: \"{reminder}\"."
        )

    cron_label = cron_expr or "*/15 * * * *"
    if effective_conv:
        return (
            f"Cronjob erstellt{id_part}: `{name}`. "
            f"Wiederholend mit `{cron_label}` für Chat `{effective_conv}`."
        )
    return f"Cronjob erstellt{id_part}: `{name}`. Wiederholend mit `{cron_label}`."


def bind_cron_conversation_id(
    tool_name: str,
    tool_args: Dict[str, Any],
    conversation_id: str,
    *,
    log_info_fn: Callable[[str], None],
) -> None:
    if str(tool_name or "").strip() != "autonomy_cron_create_job":
        return
    if not isinstance(tool_args, dict):
        return
    conv_id = str(conversation_id or "").strip()
    if not conv_id:
        return
    previous = str(tool_args.get("conversation_id") or "").strip()
    if previous != conv_id:
        tool_args["conversation_id"] = conv_id
        if previous:
            log_info_fn(
                "[Orchestrator] cron conversation_id override: "
                f"{previous} -> {conv_id}"
            )


def suggest_cron_expression_for_min_interval(min_interval_s: int) -> str:
    min_seconds = max(60, int(min_interval_s or 60))
    if min_seconds <= 59 * 60:
        minutes = max(1, (min_seconds + 59) // 60)
        return f"*/{minutes} * * * *"
    if min_seconds <= 23 * 3600:
        hours = max(1, (min_seconds + 3599) // 3600)
        return f"0 */{hours} * * *"
    days = max(1, (min_seconds + 86399) // 86400)
    return f"0 0 */{days} * *"


def extract_interval_hint_from_cron(expr: str) -> Dict[str, int]:
    raw = str(expr or "").strip()
    if not raw:
        return {"minutes": 0}
    match = re.match(r"^\*/(\d{1,3})\s+\*\s+\*\s+\*\s+\*$", raw)
    if match:
        return {"minutes": max(1, int(match.group(1)))}
    match = re.match(r"^0\s+\*/(\d{1,2})\s+\*\s+\*\s+\*$", raw)
    if match:
        return {"minutes": max(1, int(match.group(1))) * 60}
    match = re.match(r"^0\s+0\s+\*/(\d{1,2})\s+\*\s+\*$", raw)
    if match:
        return {"minutes": max(1, int(match.group(1))) * 24 * 60}
    return {"minutes": 0}


def prevalidate_cron_policy_args(
    tool_name: str,
    args: Dict[str, Any],
    *,
    datetime_cls: Any = datetime,
    timedelta_cls: Any = timedelta,
    timezone_utc: Any = timezone.utc,
    suggest_cron_expression_for_min_interval_fn: Callable[[int], str],
    extract_interval_hint_from_cron_fn: Callable[[str], Dict[str, int]],
) -> Tuple[bool, str]:
    if tool_name not in {"autonomy_cron_create_job", "autonomy_cron_update_job"}:
        return True, ""

    schedule_mode = str((args or {}).get("schedule_mode") or "recurring").strip().lower()
    if schedule_mode == "one_shot":
        run_at_raw = str((args or {}).get("run_at") or "").strip()
        if not run_at_raw:
            return False, "one_shot_run_at_missing_precheck"
        try:
            run_at = datetime_cls.fromisoformat(run_at_raw.replace("Z", "+00:00"))
            if run_at.tzinfo is None:
                run_at = run_at.replace(tzinfo=timezone_utc)
            now_utc = datetime_cls.utcnow().replace(tzinfo=timezone_utc)
            if run_at <= now_utc:
                drift_s = max(0.0, (now_utc - run_at).total_seconds())
                if drift_s <= 120.0:
                    suggested = (now_utc + timedelta_cls(minutes=1)).replace(second=0, microsecond=0)
                    args["run_at"] = suggested.isoformat().replace("+00:00", "Z")
                    return True, ""
                suggested = (now_utc + timedelta_cls(minutes=1)).replace(second=0, microsecond=0)
                return (
                    False,
                    "one_shot_run_at_in_past_precheck: "
                    f"run_at={run_at.isoformat()} suggested_run_at={suggested.isoformat().replace('+00:00','Z')}",
                )
        except Exception as exc:
            return False, f"invalid_one_shot_run_at_precheck: {exc}"
        return True, ""

    cron_expr = str((args or {}).get("cron") or "").strip()
    if not cron_expr:
        return True, ""

    try:
        from core.autonomy.cron_scheduler import (
            estimate_min_interval_seconds,
            parse_cron_expression,
        )

        parsed = parse_cron_expression(cron_expr)
        interval_s = int(estimate_min_interval_seconds(parsed))
    except Exception as exc:
        return False, f"invalid_cron_expression_precheck: {exc}"

    try:
        from config import (
            get_autonomy_cron_min_interval_s,
            get_autonomy_cron_trion_min_interval_s,
        )

        min_interval_s = int(get_autonomy_cron_min_interval_s())
        created_by = str((args or {}).get("created_by") or "").strip().lower()
        if created_by == "trion":
            min_interval_s = max(min_interval_s, int(get_autonomy_cron_trion_min_interval_s()))
    except Exception:
        min_interval_s = 300

    if interval_s < min_interval_s:
        suggested = suggest_cron_expression_for_min_interval_fn(min_interval_s)
        suggested_minutes = extract_interval_hint_from_cron_fn(suggested).get("minutes", 0)
        return (
            False,
            "cron_min_interval_violation_precheck: "
            f"requested={interval_s}s minimum={min_interval_s}s "
            f"suggested_every_minutes={suggested_minutes or max(1, (min_interval_s + 59)//60)} "
            f"suggested_cron={suggested} confirm_required=true",
        )

    return True, ""
