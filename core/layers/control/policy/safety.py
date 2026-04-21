"""Safety helpers for ControlLayer policy flows."""

from __future__ import annotations

import re
from typing import Any


def has_hard_safety_markers_for_policy(
    verification: dict[str, Any],
    *,
    has_hard_safety_markers_fn,
) -> bool:
    """Check whether verification already carries hard safety markers."""
    return bool(has_hard_safety_markers_fn(verification))


def is_light_cim_hard_denial_for_policy(
    cim_result: dict[str, Any],
    *,
    is_light_cim_hard_denial_fn,
) -> bool:
    """Check whether LightCIM produced an explicit hard denial."""
    return bool(is_light_cim_hard_denial_fn(cim_result))


def user_text_has_hard_safety_keywords(user_text: str, *, light_cim) -> bool:
    """Detect destructive or obviously unsafe user prompts."""
    text = str(user_text or "").strip().lower()
    if not text:
        return False
    destructive_shell_patterns = (
        r"\brm\s+-rf\s+/\b",
        r"\bsudo\s+rm\s+-rf\b",
        r"\bmkfs\.[a-z0-9]+\b",
        r"\b(?:del|erase)\s+[/\-][a-z]+\b",
        r"\bformat\s+[a-z]:\b",
    )
    for pattern in destructive_shell_patterns:
        try:
            if re.search(pattern, text):
                return True
        except re.error:
            continue
    high_risk_markers = (
        "virus",
        "malware",
        "trojan",
        "ransomware",
        "keylogger",
        "botnet",
        "credential theft",
        "passwort ausliest",
        "passwörter ausliest",
        "passwoerter ausliest",
        "passwords ausliest",
        "delete all files",
        "alle dateien loesch",
        "alle dateien lösch",
    )
    if any(marker in text for marker in high_risk_markers):
        return True
    try:
        keywords = list(getattr(light_cim, "danger_keywords", []) or []) + list(
            getattr(light_cim, "sensitive_keywords", []) or []
        )
        for keyword in keywords:
            if light_cim._contains_keyword(text, str(keyword or "")):
                return True
    except Exception:
        return True
    return False


def user_text_has_malicious_intent(user_text: str) -> bool:
    """Detect plainly malicious execution intent in the user prompt."""
    text = str(user_text or "").strip().lower()
    if not text:
        return False
    direct_patterns = (
        r"rm\s+-rf\s+/",
        r"\bsudo\s+rm\s+-rf\b",
        r"\b(?:hacke|hacken|hack|exploit|crack)\b",
        r"\b(?:virus|malware|trojan|ransomware|keylogger|botnet)\b",
        r"\b(?:alle\s+dateien\s+(?:lösch\w*|loesch\w*|delete\w*)|delete\s+all\s+files)\b",
    )
    for pattern in direct_patterns:
        try:
            if re.search(pattern, text):
                return True
        except re.error:
            continue
    if re.search(r"\b(?:passw(?:ort|oerter|örter)|passwords?)\b", text) and re.search(
        r"\b(?:ausles\w*|auslies\w*|stehl\w*|exfiltrat\w*|klau\w*)\b",
        text,
    ):
        return True
    return False


def user_text_has_explicit_skill_intent_for_policy(
    user_text: str,
    *,
    user_text_has_explicit_skill_intent_fn,
) -> bool:
    """Detect explicit skill-related user intent."""
    return bool(user_text_has_explicit_skill_intent_fn(user_text))
