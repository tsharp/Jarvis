from __future__ import annotations

import unicodedata
from typing import Any, Dict, Optional

from core.task_loop.contracts import RiskLevel
from core.task_loop.capability_policy import WRITE_LIKE_TOOLS


TASK_LOOP_START_MARKERS = (
    "task-loop",
    "task loop",
    "taskloop",
    "im task-loop modus",
    "im task loop modus",
    "im multistep modus",
    "multistep modus",
    "multistep",
    "multi-step",
    "mehrschritt",
    "schrittweise",
    "schritt fuer schritt",
    "schritt fur schritt",
    "step by step",
    "planungsmodus",
    "plan und dann",
    "plane und fuehre",
)


def clean_task_loop_objective(user_text: str) -> str:
    objective = " ".join(str(user_text or "").strip().split())
    objective = objective.removeprefix("Bitte ").strip()
    for marker in TASK_LOOP_START_MARKERS:
        lower = objective.lower()
        if lower.startswith(marker + ":"):
            objective = objective[len(marker) + 1:].strip()
            break
        if lower.startswith(marker + " "):
            objective = objective[len(marker):].strip(" :")
            break
    objective = objective.removeprefix("Bitte ").strip()
    lower = objective.lower()
    for prefix in ("einen plan machen:", "einen plan erstellen:", "arbeiten:"):
        if lower.startswith(prefix):
            objective = objective[len(prefix):].strip()
            break
    return objective or "Aufgabe"


def _clip(value: Any, limit: int = 120) -> str:
    text = " ".join(str(value or "").strip().split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _keyword_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.lower().split())


def _has_any_keyword(value: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in value for keyword in keywords)


def _is_fallback_text(value: Any) -> bool:
    text = _keyword_text(value)
    if not text:
        return False
    return _has_any_keyword(
        text,
        (
            "fallback",
            "analyse fehlgeschlagen",
            "analysis failed",
            "unknown",
            "nicht analysiert",
        ),
    )


def _clean_reasoning(value: Any) -> str:
    reasoning = _clip(value, 160)
    if _is_fallback_text(reasoning):
        return ""
    return reasoning


def _is_fallback_thinking_plan(thinking_plan: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(thinking_plan, dict) or not thinking_plan:
        return True
    raw_intent = str(thinking_plan.get("intent") or "").strip()
    reasoning = str(thinking_plan.get("reasoning") or "").strip()
    intent_lower = raw_intent.lower()
    if (
        raw_intent
        and intent_lower not in {"unknown", "fallback"}
        and not _is_fallback_text(raw_intent)
    ):
        return False
    return not reasoning or _is_fallback_text(reasoning)


def _risk_from_thinking_plan(thinking_plan: Optional[Dict[str, Any]]) -> RiskLevel:
    plan = thinking_plan if isinstance(thinking_plan, dict) else {}
    risk = str(plan.get("hallucination_risk") or "").strip().lower()
    suggested_tools = [
        str(item or "").strip() for item in plan.get("suggested_tools") or []
    ]
    if WRITE_LIKE_TOOLS.intersection(set(suggested_tools)):
        return RiskLevel.NEEDS_CONFIRMATION
    if risk == "high":
        return RiskLevel.NEEDS_CONFIRMATION
    return RiskLevel.SAFE


def _task_kind(objective: str, intent: str) -> str:
    text = _keyword_text(f"{objective} {intent}")
    if _has_any_keyword(
        text,
        (
            "pruef",
            "pruf",
            "check",
            "validier",
            "test",
            "verifizier",
            "review",
            "bewert",
        ),
    ):
        return "validation"
    if _has_any_keyword(
        text,
        (
            "implement",
            "umsetz",
            "bau",
            "fix",
            "verbesser",
            "erweiter",
            "aender",
            "ander",
            "update",
            "erstelle",
        ),
    ):
        return "implementation"
    if _has_any_keyword(
        text,
        (
            "analys",
            "untersuch",
            "erklaer",
            "warum",
            "einschaetz",
            "vergleich",
            "finde heraus",
        ),
    ):
        return "analysis"
    return "default"


__all__ = [
    "TASK_LOOP_START_MARKERS",
    "_clean_reasoning",
    "_clip",
    "_has_any_keyword",
    "_is_fallback_text",
    "_is_fallback_thinking_plan",
    "_keyword_text",
    "_risk_from_thinking_plan",
    "_task_kind",
    "clean_task_loop_objective",
]
