from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional
import re


DEFAULT_HARD_BLOCK_REASON_CODES = {
    "malicious_intent",
    "pii",
    "critical_cim",
    "hardware_self_protection",
}


def normalize_block_reason_code(value: Any) -> str:
    code = str(value or "").strip().lower()
    if not code:
        return ""
    code = re.sub(r"[^a-z0-9_]+", "_", code)
    code = re.sub(r"_+", "_", code).strip("_")
    return code


def is_allowed_hard_block_reason_code(
    code: str,
    *,
    allowed_codes: Optional[Iterable[str]] = None,
) -> bool:
    normalized = normalize_block_reason_code(code)
    scope = {
        normalize_block_reason_code(item)
        for item in (allowed_codes or DEFAULT_HARD_BLOCK_REASON_CODES)
        if normalize_block_reason_code(item)
    }
    return normalized in scope


def _warning_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if value:
        return [str(value)]
    return []


def make_hard_block_verification(
    *,
    reason_code: str,
    warnings: Any = None,
    final_instruction: str = "Request blocked",
    reason: str = "",
) -> Dict[str, Any]:
    normalized_code = normalize_block_reason_code(reason_code) or "critical_cim"
    return {
        "approved": False,
        "hard_block": True,
        "decision_class": "hard_block",
        "block_reason_code": normalized_code,
        "reason": reason or normalized_code,
        "corrections": {},
        "warnings": _warning_list(warnings),
        "final_instruction": final_instruction,
    }


def is_control_hard_block_decision(
    verification: Dict[str, Any],
    *,
    allowed_reason_codes: Optional[Iterable[str]] = None,
) -> bool:
    if not isinstance(verification, dict):
        return False
    if verification.get("approved") is not False:
        return False

    if bool(verification.get("hard_block")):
        return True

    decision_class = str(verification.get("decision_class") or "").strip().lower()
    if decision_class == "hard_block":
        return True

    reason_code = str(verification.get("block_reason_code") or "").strip().lower()
    if is_allowed_hard_block_reason_code(
        reason_code,
        allowed_codes=allowed_reason_codes,
    ):
        return True

    reason_text = " ".join(
        str(part or "")
        for part in (
            verification.get("reason"),
            verification.get("final_instruction"),
            " ".join(str(w) for w in (verification.get("warnings") or [])),
        )
    ).lower()
    hard_markers = (
        "dangerous keyword detected",
        "sensitive content detected",
        "email address detected",
        "phone number detected",
        "pii",
        "malicious",
        "policy guard",
    )
    return any(marker in reason_text for marker in hard_markers)


def normalize_control_verification(verification: Dict[str, Any]) -> Dict[str, Any]:
    """Return a consistent Control verification without downgrading denies.

    Control may return legacy shapes such as approved=False + decision_class=warn.
    Those are normalized to a deny shape unless Control explicitly approved the
    request. Warning-only decisions must therefore be emitted by Control as
    approved=True + decision_class=warn before the Orchestrator sees them.
    """
    if not isinstance(verification, dict):
        return {
            "approved": False,
            "hard_block": False,
            "decision_class": "deny",
            "block_reason_code": "invalid_control_verification",
            "reason": "Invalid Control verification result",
            "corrections": {},
            "warnings": [],
            "final_instruction": "",
        }

    out = dict(verification)
    out["warnings"] = _warning_list(out.get("warnings"))
    corrections = out.get("corrections")
    if not isinstance(corrections, dict):
        out["corrections"] = {}

    approved = out.get("approved") is True
    out["approved"] = approved

    if approved:
        decision_class = str(out.get("decision_class") or "allow").strip().lower()
        if decision_class in {"deny", "hard_block", "routing_block"}:
            decision_class = "warn" if out["warnings"] else "allow"
        out["decision_class"] = decision_class
        out["hard_block"] = False
        out["block_reason_code"] = ""
        return out

    if is_control_hard_block_decision(out):
        reason_code = normalize_block_reason_code(out.get("block_reason_code")) or "critical_cim"
        out["hard_block"] = True
        out["decision_class"] = "hard_block"
        out["block_reason_code"] = reason_code
        out["reason"] = str(out.get("reason") or reason_code)
        return out

    decision_class = str(out.get("decision_class") or "").strip().lower()
    if decision_class in {"allow", "warn", "hard_block"}:
        decision_class = "deny"
    out["decision_class"] = decision_class or "deny"
    out["hard_block"] = False
    out["block_reason_code"] = normalize_block_reason_code(out.get("block_reason_code"))
    out["reason"] = str(out.get("reason") or "control_denied")
    return out


__all__ = [
    "DEFAULT_HARD_BLOCK_REASON_CODES",
    "is_allowed_hard_block_reason_code",
    "is_control_hard_block_decision",
    "make_hard_block_verification",
    "normalize_block_reason_code",
    "normalize_control_verification",
]
