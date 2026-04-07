"""
Autonomy cron helpers for Container Commander MCP tools.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Dict, List


def run_async_sync(coro):
    """
    Run async scheduler methods safely from this synchronous tool layer.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result_holder = {"value": None, "error": None}

    def _runner():
        try:
            result_holder["value"] = asyncio.run(coro)
        except Exception as exc:  # pragma: no cover - defensive
            result_holder["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if result_holder["error"] is not None:
        raise result_holder["error"]
    return result_holder["value"]


def get_autonomy_cron_scheduler():
    try:
        from core.autonomy.cron_runtime import get_scheduler

        return get_scheduler()
    except Exception:
        return None


def tool_autonomy_cron_status(args: dict) -> dict:
    scheduler = get_autonomy_cron_scheduler()
    if not scheduler:
        return {"error": "autonomy_cron_unavailable"}
    return run_async_sync(scheduler.get_status())


def tool_autonomy_cron_list_jobs(args: dict) -> dict:
    scheduler = get_autonomy_cron_scheduler()
    if not scheduler:
        return {"error": "autonomy_cron_unavailable"}
    jobs = run_async_sync(scheduler.list_jobs())
    return {"jobs": jobs, "count": len(jobs)}


def tool_autonomy_cron_validate(args: dict) -> dict:
    cron_expr = str(args.get("cron", "")).strip()
    if not cron_expr:
        return {"valid": False, "error": "missing cron"}
    try:
        from core.autonomy.cron_scheduler import validate_cron_expression

        validated = validate_cron_expression(cron_expr)
        return {"valid": True, **validated}
    except Exception as exc:
        return {"valid": False, "error": str(exc)}


def reference_links_rows_for_category(
    category: str,
    *,
    include_disabled: bool = False,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    from utils.settings import settings as runtime_settings

    categories = {"cronjobs", "skills", "blueprints"}
    requested = str(category or "").strip().lower()
    if requested not in categories:
        return []

    raw = runtime_settings.get("TRION_REFERENCE_LINK_COLLECTIONS", {})
    source = raw if isinstance(raw, dict) else {}
    rows = source.get(requested, [])
    if not isinstance(rows, list):
        return []

    out: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()
    for entry in rows:
        item = entry if isinstance(entry, dict) else {}
        name = str(item.get("name", "")).strip()
        url = str(item.get("url", "")).strip()
        if not name or not url:
            continue
        enabled = bool(item.get("enabled", True))
        if not include_disabled and not enabled:
            continue
        key = url.lower()
        if key in seen_urls:
            continue
        seen_urls.add(key)
        out.append(
            {
                "name": name[:120],
                "url": url[:500],
                "description": str(item.get("description", "")).strip()[:300],
                "enabled": enabled,
                "read_only": True,
            }
        )
        if len(out) >= max(1, int(limit)):
            break
    return out


def tool_autonomy_cron_create_job(args: dict) -> dict:
    scheduler = get_autonomy_cron_scheduler()
    if not scheduler:
        return {"error": "autonomy_cron_unavailable"}
    payload = {
        "name": args.get("name"),
        "objective": args.get("objective"),
        "conversation_id": args.get("conversation_id") or args.get("session_id") or "",
        "cron": args.get("cron"),
        "schedule_mode": args.get("schedule_mode", "recurring"),
        "run_at": args.get("run_at", ""),
        "timezone": args.get("timezone", "UTC"),
        "max_loops": args.get("max_loops", 10),
        "created_by": args.get("created_by", "user"),
        "user_approved": bool(args.get("user_approved", False)),
        "enabled": bool(args.get("enabled", True)),
    }
    auto_refs: List[Dict[str, Any]] = []
    created_by = str(payload.get("created_by", "user")).strip().lower()
    if created_by == "trion":
        auto_refs = reference_links_rows_for_category("cronjobs", include_disabled=False, limit=8)
        if auto_refs:
            payload["reference_links"] = auto_refs
            payload["reference_source"] = "settings:cronjobs:auto"
    try:
        created = run_async_sync(scheduler.create_job(payload))
        if isinstance(created, dict):
            created["reference_links_used"] = {
                "category": "cronjobs",
                "count": len(auto_refs),
                "source": "settings:cronjobs:auto" if auto_refs else "",
            }
        return created
    except Exception as exc:
        error_code = getattr(exc, "error_code", "")
        details = getattr(exc, "details", None)
        if error_code:
            return {"error": str(exc), "error_code": error_code, "details": details or {}}
        return {"error": str(exc)}


def tool_autonomy_cron_update_job(args: dict) -> dict:
    scheduler = get_autonomy_cron_scheduler()
    if not scheduler:
        return {"error": "autonomy_cron_unavailable"}
    cron_job_id = str(args.get("cron_job_id", "")).strip()
    if not cron_job_id:
        return {"error": "missing cron_job_id"}
    payload = {
        key: args[key]
        for key in [
            "name",
            "objective",
            "conversation_id",
            "cron",
            "schedule_mode",
            "run_at",
            "timezone",
            "max_loops",
            "created_by",
            "user_approved",
            "enabled",
        ]
        if key in args
    }
    try:
        updated = run_async_sync(scheduler.update_job(cron_job_id, payload))
    except Exception as exc:
        error_code = getattr(exc, "error_code", "")
        details = getattr(exc, "details", None)
        if error_code:
            return {"error": str(exc), "error_code": error_code, "details": details or {}}
        return {"error": str(exc)}
    if not updated:
        return {"error": "cron_job_not_found", "cron_job_id": cron_job_id}
    return updated


def tool_autonomy_cron_pause_job(args: dict) -> dict:
    scheduler = get_autonomy_cron_scheduler()
    if not scheduler:
        return {"error": "autonomy_cron_unavailable"}
    cron_job_id = str(args.get("cron_job_id", "")).strip()
    if not cron_job_id:
        return {"error": "missing cron_job_id"}
    paused = run_async_sync(scheduler.pause_job(cron_job_id))
    if not paused:
        return {"error": "cron_job_not_found", "cron_job_id": cron_job_id}
    return paused


def tool_autonomy_cron_resume_job(args: dict) -> dict:
    scheduler = get_autonomy_cron_scheduler()
    if not scheduler:
        return {"error": "autonomy_cron_unavailable"}
    cron_job_id = str(args.get("cron_job_id", "")).strip()
    if not cron_job_id:
        return {"error": "missing cron_job_id"}
    resumed = run_async_sync(scheduler.resume_job(cron_job_id))
    if not resumed:
        return {"error": "cron_job_not_found", "cron_job_id": cron_job_id}
    return resumed


def tool_autonomy_cron_run_now(args: dict) -> dict:
    scheduler = get_autonomy_cron_scheduler()
    if not scheduler:
        return {"error": "autonomy_cron_unavailable"}
    cron_job_id = str(args.get("cron_job_id", "")).strip()
    if not cron_job_id:
        return {"error": "missing cron_job_id"}
    try:
        scheduled = run_async_sync(scheduler.run_now(cron_job_id, reason="tool"))
    except Exception as exc:
        error_code = getattr(exc, "error_code", "")
        details = getattr(exc, "details", None)
        if error_code:
            return {"error": str(exc), "error_code": error_code, "details": details or {}}
        return {"error": str(exc)}
    if not scheduled:
        return {"error": "cron_job_not_found", "cron_job_id": cron_job_id}
    return scheduled


def tool_autonomy_cron_delete_job(args: dict) -> dict:
    scheduler = get_autonomy_cron_scheduler()
    if not scheduler:
        return {"error": "autonomy_cron_unavailable"}
    cron_job_id = str(args.get("cron_job_id", "")).strip()
    if not cron_job_id:
        return {"error": "missing cron_job_id"}
    deleted = run_async_sync(scheduler.delete_job(cron_job_id))
    return {"deleted": bool(deleted), "cron_job_id": cron_job_id}


def tool_autonomy_cron_queue(args: dict) -> dict:
    scheduler = get_autonomy_cron_scheduler()
    if not scheduler:
        return {"error": "autonomy_cron_unavailable"}
    return run_async_sync(scheduler.get_queue_snapshot())


def tool_cron_reference_links_list(args: dict) -> dict:
    categories = ("cronjobs", "skills", "blueprints")
    requested_category = str(args.get("category", "")).strip().lower()
    include_disabled = bool(args.get("include_disabled", False))
    limit = int(args.get("limit", 50) or 50)
    limit = max(1, min(100, limit))

    if requested_category and requested_category not in categories:
        return {"error": "invalid_category", "allowed_categories": list(categories)}

    if requested_category:
        links = reference_links_rows_for_category(
            requested_category,
            include_disabled=include_disabled,
            limit=limit,
        )
        return {
            "category": requested_category,
            "count": len(links),
            "links": links,
            "mode": "read_only_for_trion",
            "include_disabled": include_disabled,
        }

    collections: Dict[str, List[Dict[str, Any]]] = {}
    for category in categories:
        collections[category] = reference_links_rows_for_category(
            category,
            include_disabled=include_disabled,
            limit=limit,
        )

    return {
        "categories": list(categories),
        "collections": collections,
        "mode": "read_only_for_trion",
        "include_disabled": include_disabled,
    }
