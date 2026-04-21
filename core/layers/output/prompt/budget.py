"""
core.layers.output.prompt.budget
==================================
Output-Budget-Berechnung.

Berechnet hard_cap und soft_target aus response_mode, length_hint und query_type.
Reine Funktionen — kein State, keine Klassen-Abhängigkeit.
"""
from typing import Any, Dict

from config.output.char_limits import (
    get_output_char_cap_deep,
    get_output_char_cap_interactive,
    get_output_char_cap_interactive_analytical,
    get_output_char_cap_interactive_long,
    get_output_char_target_deep,
    get_output_char_target_interactive,
    get_output_char_target_interactive_analytical,
)


def normalize_length_hint(value: Any) -> str:
    """Validiert den length_hint. Gültige Werte: short / medium / long. Default: medium."""
    raw = str(value or "").strip().lower()
    return raw if raw in {"short", "medium", "long"} else "medium"


def resolve_output_budgets(verified_plan: Dict[str, Any]) -> Dict[str, int]:
    """
    Berechnet hard_cap und soft_target für diesen Request.

    Faktoren:
      - response_mode (interactive / deep)
      - length_hint   (short / medium / long)
      - query_type    (analytical → engeres Cap)

    Returns:
      {"hard_cap": int, "soft_target": int}
    """
    response_mode = str((verified_plan or {}).get("_response_mode", "interactive")).lower()
    length_hint = normalize_length_hint((verified_plan or {}).get("response_length_hint"))
    query_signal = (verified_plan or {}).get("_query_budget") or {}
    query_type = str((query_signal or {}).get("query_type") or "").strip().lower()

    hard_cap = get_output_char_cap_deep() if response_mode == "deep" else get_output_char_cap_interactive()
    soft_target = (
        get_output_char_target_deep() if response_mode == "deep" else get_output_char_target_interactive()
    )

    if response_mode != "deep" and hard_cap > 0:
        if length_hint == "long":
            hard_cap = max(hard_cap, get_output_char_cap_interactive_long())
            soft_target = max(soft_target, int(hard_cap * 0.72))

    if length_hint == "short":
        soft_target = int(soft_target * 0.62)
    elif length_hint == "long":
        soft_target = int(soft_target * 1.30)

    # Analytical queries get a tighter cap to avoid long generation tails.
    if response_mode != "deep" and query_type == "analytical":
        hard_cap = min(hard_cap, get_output_char_cap_interactive_analytical())
        soft_target = min(soft_target, get_output_char_target_interactive_analytical())

    if hard_cap > 0:
        soft_target = min(soft_target, max(160, hard_cap - 80))
    soft_target = max(160, soft_target)

    return {"hard_cap": hard_cap, "soft_target": soft_target}
