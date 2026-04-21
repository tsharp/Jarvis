"""Default verification helpers for ControlLayer."""

from __future__ import annotations

from typing import Any


def default_verification(thinking_plan: dict[str, Any]) -> dict[str, Any]:
    """Return the fail-closed fallback verification result."""
    _ = thinking_plan
    return {
        "approved": False,
        "hard_block": True,
        "decision_class": "hard_block",
        "block_reason_code": "control_decision_missing",
        "reason": "control_layer_fallback_fail_closed",
        "corrections": {
            "needs_memory": None,
            "memory_keys": None,
            "hallucination_risk": None,
            "resolution_strategy": None,
            "new_fact_key": None,
            "new_fact_value": None,
            "suggested_response_style": None,
            "dialogue_act": None,
            "response_tone": None,
            "response_length_hint": None,
            "tone_confidence": None,
        },
        "warnings": ["Control-Layer Fallback (fail-closed)"],
        "final_instruction": "Request blocked: control decision unavailable.",
    }
