"""Deterministic tool-decision helpers for ControlLayer."""

from __future__ import annotations

from typing import Any


async def decide_tools(
    user_text: str,
    verified_plan: dict[str, Any],
    *,
    normalize_suggested_tools_fn,
    user_text_has_explicit_skill_intent_fn,
    is_tool_available_fn,
    cim_tool_args_fn,
    log_info_fn,
) -> list[dict[str, Any]]:
    """
    Deterministic tool decision fallback used by the orchestrator.

    Returns:
        [{"name": <tool_name>, "arguments": {...}}, ...]
    """
    _ = user_text  # reserved for future model-based argument filling

    candidates = normalize_suggested_tools_fn(verified_plan)
    if not candidates:
        return []

    decided: list[dict[str, Any]] = []
    seen = set()

    for item in candidates:
        name = item.get("name", "")
        if not name or name in seen:
            continue
        if (
            name in {"autonomous_skill_task", "create_skill", "run_skill", "list_skills", "get_skill_info"}
            and not user_text_has_explicit_skill_intent_fn(user_text)
        ):
            log_info_fn(
                "[ControlLayer] decide_tools filtered skill tool without explicit skill intent: "
                f"{name}"
            )
            continue
        if not is_tool_available_fn(name):
            log_info_fn(f"[ControlLayer] decide_tools filtered unavailable tool: {name}")
            continue
        args = item.get("arguments", {}) if isinstance(item.get("arguments"), dict) else {}
        if not args:
            args = cim_tool_args_fn(verified_plan, name, user_text=user_text)
        if name == "analyze" and not str(args.get("query", "")).strip():
            args["query"] = (user_text or "").strip()
        if name == "think" and not str(args.get("message", "")).strip():
            args["message"] = (user_text or "").strip()
        decided.append({"name": name, "arguments": args})
        seen.add(name)

    if decided:
        names = [item["name"] for item in decided]
        log_info_fn(f"[ControlLayer] decide_tools={names}")
    return decided
