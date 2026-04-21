"""
core.layers.output.grounding.state
=====================================
Zentraler Grounding-State-Container.

Alle Grounding-Flags (fallback_used, violation_detected, repair_attempted …)
landen unter verified_plan._execution_result.grounding.
Diese zwei Funktionen sind die einzigen erlaubten Schreiber.
"""
from typing import Any, Dict, Optional


def runtime_grounding_state(
    verified_plan: Dict[str, Any],
    execution_result: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Liest oder erstellt den grounding-Dict unter execution_result.
    Synct den Pointer zurück in verified_plan._execution_result.
    """
    if not isinstance(execution_result, dict):
        existing = (verified_plan or {}).get("_execution_result")
        execution_result = existing if isinstance(existing, dict) else {}
    grounding = execution_result.get("grounding")
    if not isinstance(grounding, dict):
        grounding = {}
        execution_result["grounding"] = grounding
    if isinstance(verified_plan, dict):
        verified_plan["_execution_result"] = execution_result
    return grounding


def set_runtime_grounding_value(
    verified_plan: Dict[str, Any],
    execution_result: Optional[Dict[str, Any]],
    key: str,
    value: Any,
) -> None:
    """Schreibt einen einzelnen Wert in den Grounding-State."""
    grounding = runtime_grounding_state(verified_plan, execution_result)
    grounding[str(key)] = value
