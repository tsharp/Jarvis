"""
core.layers.output.prompt.tool_injection
==========================================
Tool-Injection in den Output-System-Prompt.

Entscheidet welche Tools dem LLM im System-Prompt gezeigt werden:
  none     → keine Tools
  all      → alle live Tools bis zum Limit
  selected → nur die für diesen Request gewählten Tools
"""
from typing import Any, Dict, List

from config.pipeline.domain_router import (
    get_output_tool_injection_mode,
    get_output_tool_prompt_limit,
)
from core.tool_exposure import list_live_tools


def extract_selected_tool_names(verified_plan: Dict[str, Any]) -> List[str]:
    """
    Liest die für diesen Request gewählten Tool-Namen aus dem Plan.
    Quellen: _selected_tools_for_prompt → suggested_tools (Fallback).
    Dedupliziert und erhält Reihenfolge.
    """
    raw = []
    if isinstance(verified_plan, dict):
        raw = (
            verified_plan.get("_selected_tools_for_prompt")
            or verified_plan.get("suggested_tools")
            or []
        )

    names: List[str] = []
    seen = set()
    for item in raw:
        if isinstance(item, dict):
            name = str(item.get("tool") or item.get("name") or "").strip()
        else:
            name = str(item).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def resolve_tools_for_prompt(verified_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Löst die Tool-Liste auf die in den System-Prompt injiziert wird.

    Modus 'selected' (Default): nur Request-spezifische Tools.
    Modus 'all': alle live Tools bis Limit.
    Modus 'none': leere Liste.
    """
    mode = get_output_tool_injection_mode()
    limit = get_output_tool_prompt_limit()
    all_tools = list_live_tools()

    if mode == "none":
        return []
    if mode == "all":
        return all_tools[:limit]

    selected_names = extract_selected_tool_names(verified_plan)
    if not selected_names:
        return []

    selected = []
    by_name = {t.get("name"): t for t in all_tools if t.get("name")}
    for name in selected_names:
        item = by_name.get(name)
        if item:
            selected.append(item)
        else:
            selected.append({
                "name": name,
                "mcp": "unknown",
                "description": "Selected for current request",
            })
        if len(selected) >= limit:
            break
    return selected
