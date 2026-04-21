"""Skill discovery helpers for ControlLayer."""

from __future__ import annotations

import asyncio
from typing import Any


def extract_skill_names(result: Any) -> list[str]:
    """Extract installed/active skill names from MCP payload variants."""
    payload = result
    if isinstance(payload, dict) and isinstance(payload.get("structuredContent"), dict):
        payload = payload.get("structuredContent", {})

    names: list[str] = []
    if isinstance(payload, dict):
        skill_rows: list[Any] = []
        for key in ("skills", "installed", "active"):
            value = payload.get(key, [])
            if isinstance(value, list):
                skill_rows.extend(value)
        for item in skill_rows:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
            else:
                name = str(item or "").strip()
            if name:
                names.append(name)
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
            else:
                name = str(item or "").strip()
            if name:
                names.append(name)

    seen = set()
    deduped: list[str] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return deduped


def get_available_skills(mcp_hub, *, extract_skill_names_fn, log_debug_fn) -> list[str]:
    """Fetch the installed skill list through the synchronous hub path."""
    if not mcp_hub:
        return []
    try:
        result = mcp_hub.call_tool("list_skills", {})
        return extract_skill_names_fn(result)
    except Exception as exc:
        log_debug_fn(f"[ControlLayer] Could not fetch skills: {exc}")
        return []


async def get_available_skills_async(mcp_hub, *, extract_skill_names_fn, log_debug_fn) -> list[str]:
    """Fetch the installed skill list through the async-safe hub path."""
    if not mcp_hub:
        return []
    try:
        call_tool_async = getattr(mcp_hub, "call_tool_async", None)
        if asyncio.iscoroutinefunction(call_tool_async):
            result = await call_tool_async("list_skills", {})
        else:
            result = await asyncio.to_thread(mcp_hub.call_tool, "list_skills", {})
        return extract_skill_names_fn(result)
    except Exception as exc:
        log_debug_fn(f"[ControlLayer] Could not fetch skills (async): {exc}")
        return []
