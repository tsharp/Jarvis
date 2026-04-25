"""
Shared helpers for control decision normalization and workspace summaries.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.layers.control.policy.decision import (
    DEFAULT_HARD_BLOCK_REASON_CODES,
    is_allowed_hard_block_reason_code,
    is_control_hard_block_decision,
    make_hard_block_verification,
    normalize_block_reason_code,
    normalize_control_verification,
)


def soften_control_deny(
    verification: Dict[str, Any],
    *,
    warning_message: str = (
        "Soft control deny downgraded to warning "
        "(single hard-block authority = Control hard_block only)."
    ),
    fallback_reason: str = "soft_control_warning_auto_corrected",
) -> Dict[str, Any]:
    _ = warning_message, fallback_reason
    return normalize_control_verification(verification)


def build_control_workspace_summary(
    verification: Dict[str, Any],
    *,
    skipped: bool,
    skip_reason: str = "",
) -> str:
    ver = verification if isinstance(verification, dict) else {}
    approved = ver.get("approved", True)
    warnings = ver.get("warnings", []) if isinstance(ver.get("warnings", []), list) else []
    corrections = ver.get("corrections", {}) if isinstance(ver.get("corrections", {}), dict) else {}
    reason = str(ver.get("reason", "") or "").strip()
    correction_keys = sorted([str(k) for k in corrections.keys()])[:6]
    parts = [
        f"approved={bool(approved)}",
        f"skipped={bool(skipped)}",
    ]
    if skip_reason:
        parts.append(f"skip_reason={skip_reason}")
    if reason:
        parts.append(f"reason={reason[:120]}")
    if warnings:
        parts.append(f"warnings={len(warnings)}")
    if correction_keys:
        parts.append(f"corrections={','.join(correction_keys)}")
    return " | ".join(parts)


def build_done_workspace_summary(
    done_reason: str,
    *,
    response_mode: str = "",
    model: str = "",
    memory_used: Optional[bool] = None,
) -> str:
    parts = [f"done_reason={str(done_reason or 'stop').strip()}"]
    if response_mode:
        parts.append(f"response_mode={response_mode}")
    if model:
        parts.append(f"model={model}")
    if memory_used is not None:
        parts.append(f"memory_used={bool(memory_used)}")
    return " | ".join(parts)
