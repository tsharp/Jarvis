"""Tool normalization helpers for ControlLayer."""

from __future__ import annotations

import re
from typing import Any


def normalize_tool_arguments(raw_args: Any, *, safe_parse_json_fn) -> dict[str, Any]:
    """Normalize tool args to a dict and accept JSON-string payloads."""
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str) and raw_args.strip():
        parsed = safe_parse_json_fn(
            raw_args,
            default={},
            context="ControlLayer.suggested_tool_args",
        )
        if isinstance(parsed, dict):
            return parsed
    return {}


def sanitize_tool_name(raw_name: Any) -> str:
    """
    Extract a clean tool identifier from noisy LLM text.
    Accept plain tokens, quoted names, key/value fragments, and call syntax.
    """
    text = str(raw_name or "").strip()
    if not text:
        return ""

    def _clean(candidate: str) -> str:
        candidate = str(candidate or "").strip().strip("`\"'.,:;!?()[]{}")
        if not candidate:
            return ""
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{1,63}", candidate):
            return candidate.lower()
        return ""

    direct = _clean(text)
    if direct:
        return direct

    kv_patterns = (
        r'(?i)"tool"\s*:\s*"([A-Za-z][A-Za-z0-9_]{1,63})"',
        r"(?i)'tool'\s*:\s*'([A-Za-z][A-Za-z0-9_]{1,63})'",
        r'(?i)"name"\s*:\s*"([A-Za-z][A-Za-z0-9_]{1,63})"',
        r"(?i)'name'\s*:\s*'([A-Za-z][A-Za-z0-9_]{1,63})'",
        r'(?i)\btool\s*[:=]\s*"?([A-Za-z][A-Za-z0-9_]{1,63})"?',
        r'(?i)\bname\s*[:=]\s*"?([A-Za-z][A-Za-z0-9_]{1,63})"?',
    )
    for pattern in kv_patterns:
        match = re.search(pattern, text)
        if match:
            cleaned = _clean(match.group(1))
            if cleaned:
                return cleaned

    quoted = re.findall(r'["\'`]\s*([A-Za-z][A-Za-z0-9_]{1,63})\s*["\'`]', text)
    for candidate in quoted:
        cleaned = _clean(candidate)
        if cleaned:
            return cleaned

    call_match = re.search(r"\b([A-Za-z][A-Za-z0-9_]{1,63})\s*\(", text)
    if call_match:
        cleaned = _clean(call_match.group(1))
        if cleaned:
            return cleaned

    token_candidates = re.findall(r"\b([A-Za-z][A-Za-z0-9_]{2,63})\b", text)
    snake_case = [token for token in token_candidates if "_" in token]
    for candidate in snake_case:
        cleaned = _clean(candidate)
        if cleaned:
            return cleaned

    if " " in text:
        return ""

    stripped = re.sub(r"^[-*#/\s]+", "", text)
    return _clean(stripped)


def normalize_suggested_tools(
    verified_plan: dict[str, Any],
    *,
    sanitize_tool_name_fn,
    normalize_tool_arguments_fn,
) -> list[dict[str, Any]]:
    """Normalize suggested tools to ``[{name, arguments}]``."""
    raw = verified_plan.get("suggested_tools", []) if isinstance(verified_plan, dict) else []
    normalized: list[dict[str, Any]] = []

    for item in raw:
        if isinstance(item, dict):
            name = sanitize_tool_name_fn(item.get("tool") or item.get("name"))
            args = normalize_tool_arguments_fn(item.get("args"))
            if not args:
                args = normalize_tool_arguments_fn(item.get("arguments"))
            if not name and len(item) == 1:
                key, value = next(iter(item.items()))
                name = sanitize_tool_name_fn(key)
                if not args:
                    args = normalize_tool_arguments_fn(value)
            if name:
                normalized.append({"name": name, "arguments": args})
        else:
            name = sanitize_tool_name_fn(item)
            if name:
                normalized.append({"name": name, "arguments": {}})

    return normalized


def cim_tool_args(
    verified_plan: dict[str, Any],
    tool_name: str,
    *,
    user_text: str = "",
) -> dict[str, Any]:
    """Fill obvious args from CIM decision metadata when available."""
    cim = verified_plan.get("_cim_decision", {}) if isinstance(verified_plan, dict) else {}
    if tool_name == "request_container":
        blueprint_id = str((verified_plan or {}).get("_selected_blueprint_id") or "").strip()
        if blueprint_id:
            return {"blueprint_id": blueprint_id}
    skill_name = str(cim.get("skill_name") or "").strip()
    if not skill_name:
        return {}
    if tool_name == "get_skill_info":
        return {"skill_name": skill_name}
    if tool_name == "run_skill":
        return {"name": skill_name, "action": "run", "args": {}}
    if tool_name == "create_skill":
        desc = f"Auto-generated skill scaffold from user request: {user_text.strip()[:240]}"
        code = (
            "def main(args=None):\n"
            "    \"\"\"Auto-generated scaffold. Replace with real implementation.\"\"\"\n"
            "    args = args or {}\n"
            "    return {\n"
            f"        \"skill\": \"{skill_name}\",\n"
            "        \"status\": \"todo\",\n"
            "        \"message\": \"Scaffold created. Implement business logic.\",\n"
            "        \"args\": args,\n"
            "    }\n"
        )
        return {
            "name": skill_name,
            "description": desc,
            "code": code,
        }
    return {}
