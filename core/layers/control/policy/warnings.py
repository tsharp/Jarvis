"""Warning and verification-text helpers for ControlLayer policy flows."""

from __future__ import annotations

from typing import Any


def verification_text_for_policy(verification: dict[str, Any], *, verification_text_fn) -> str:
    """Flatten verification payload into policy-readable text."""
    return str(verification_text_fn(verification))


def warning_list_for_policy(raw: Any, *, warning_list_fn) -> list[str]:
    """Normalize warning payloads into a compact string list."""
    return list(warning_list_fn(raw))


def sanitize_warning_messages_for_policy(warnings: Any, *, sanitize_warning_messages_fn) -> list[str]:
    """Drop prompt/template warning noise while keeping real runtime signals."""
    return list(sanitize_warning_messages_fn(warnings))
