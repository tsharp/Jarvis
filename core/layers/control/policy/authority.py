"""Authority helpers for ControlLayer policy flows."""

from __future__ import annotations

import re
from typing import Any


def infer_block_reason_code(
    verification: dict[str, Any],
    *,
    user_text: str = "",
    thinking_plan: dict[str, Any],
    verification_text_fn,
) -> str:
    """Infer a canonical hard-block reason code from verification signals."""
    text = verification_text_fn(verification)
    if re.search(r"(dangerous keyword|malicious|policy guard|virus|malware|trojan|ransomware|keylogger|botnet)", text):
        return "malicious_intent"
    if re.search(r"(sensitive content|email address detected|phone number detected|pii|password|api key|token|credentials)", text):
        return "pii"
    if re.search(r"(critical|deny_autonomy|policy_check)", text):
        return "critical_cim"
    if bool((thinking_plan or {}).get("_hardware_gate_triggered")):
        return "hardware_self_protection"
    _ = user_text
    return ""


def enforce_block_authority(
    verification: dict[str, Any],
    thinking_plan: dict[str, Any],
    *,
    user_text: str = "",
    warning_list_fn,
    normalize_block_reason_code_fn,
    infer_block_reason_code_fn,
    is_allowed_hard_block_reason_code_fn,
    default_hard_block_reason_codes,
    has_hard_safety_markers_fn,
    user_text_has_hard_safety_keywords_fn,
    user_text_has_malicious_intent_fn,
) -> dict[str, Any]:
    """Apply Control-layer authority rules to final block vs warn decisions."""
    if not isinstance(verification, dict):
        return verification

    warnings = warning_list_fn(verification.get("warnings", []))
    approved = verification.get("approved") is not False
    code = normalize_block_reason_code_fn(verification.get("block_reason_code"))

    if approved:
        verification["approved"] = True
        verification["hard_block"] = False
        verification["block_reason_code"] = ""
        if str(verification.get("decision_class") or "").strip().lower() in {"", "hard_block"}:
            verification["decision_class"] = "warn" if warnings else "allow"
        return verification

    if not code:
        code = infer_block_reason_code_fn(
            verification,
            user_text=user_text,
            thinking_plan=thinking_plan,
        )

    hard_block_allowed = (
        is_allowed_hard_block_reason_code_fn(
            code,
            allowed_codes=default_hard_block_reason_codes,
        )
        or has_hard_safety_markers_fn(verification)
        or user_text_has_hard_safety_keywords_fn(user_text)
        or user_text_has_malicious_intent_fn(user_text)
    )

    if not hard_block_allowed:
        warnings.append(
            "Deterministic override: non-authoritative soft block converted to warning (Control-only hard-block policy)."
        )
        verification["approved"] = True
        verification["hard_block"] = False
        verification["decision_class"] = "warn"
        verification["block_reason_code"] = ""
        verification["reason"] = "soft_block_auto_corrected"
        verification["warnings"] = warnings
        return verification

    verification["approved"] = False
    verification["hard_block"] = True
    verification["decision_class"] = "hard_block"
    verification["block_reason_code"] = code or "critical_cim"
    if not str(verification.get("reason") or "").strip():
        verification["reason"] = verification["block_reason_code"]
    verification["warnings"] = warnings
    return verification
