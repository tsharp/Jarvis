"""Skill-intent helpers for ControlLayer strategy flows."""

from __future__ import annotations

import re
from typing import Any


def extract_requested_skill_name(user_text: str) -> str:
    """Best-effort extraction of a user-provided skill name."""
    text = (user_text or "").strip()
    if not text:
        return ""
    patterns = [
        r"(?:skill|funktion)\s+namens\s+[`\"']?([A-Za-z][A-Za-z0-9_-]{2,63})[`\"']?",
        r"(?:namens|named|called|name)\s+[`\"']?([A-Za-z][A-Za-z0-9_-]{2,63})[`\"']?",
    ]
    stopwords = {
        "skill", "funktion", "function", "neu", "neue", "new",
        "bitte", "einen", "eine", "einer", "den", "die", "das",
    }
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.UNICODE)
        if not match:
            continue
        candidate = match.group(1).strip("`\"'.,:;!?()[]{} ").lower()
        candidate = candidate.replace("-", "_")
        candidate = re.sub(r"[^a-z0-9_]", "_", candidate)
        candidate = re.sub(r"_+", "_", candidate).strip("_")
        if len(candidate) >= 3 and candidate not in stopwords:
            return candidate
    return ""


def is_skill_creation_sensitive(
    thinking_plan: dict[str, Any],
    *,
    tool_names_fn,
) -> bool:
    """Detect whether the current plan contains skill-creation sensitive tools."""
    raw = thinking_plan.get("suggested_tools", []) if isinstance(thinking_plan, dict) else []
    names = tool_names_fn(raw, limit=64)
    sensitive = {"create_skill", "autonomous_skill_task"}
    return any(name in sensitive for name in names)
