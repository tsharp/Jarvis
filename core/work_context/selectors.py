"""Selectors fuer haeufige Work-Context-Abfragen.

Diese Helfer bleiben bewusst klein und deterministisch:

- offener Arbeitskontext vorhanden?
- welcher naechste Schritt ist sichtbar?
- soll ein Follow-up eher erklaert oder ausgefuehrt werden?
"""

from __future__ import annotations

from typing import Optional

from core.work_context.contracts import WorkContext


_EXPLAIN_MARKERS = (
    "was fehlt",
    "what is missing",
    "what's missing",
    "woran",
    "warum",
    "why",
    "welcher blocker",
    "welcher block",
    "was blockiert",
    "welche infos",
    "welche informationen",
    "welche parameter",
    "status",
)

_ACTION_MARKERS = (
    "weiter",
    "fortsetzen",
    "continue",
    "mach",
    "pruef",
    "prüf",
    "pruefe",
    "prüfe",
    "check",
    "starte",
    "start",
    "fuehre",
    "führe",
    "run",
    "nimm",
    "verwende",
    "waehle",
    "wähle",
)


def _normalized(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def has_open_work_context(context: Optional[WorkContext]) -> bool:
    """Return True, wenn fachlich noch ein offener Arbeitsfaden existiert.

    Das schliesst nicht nur aktive/wartende Runtime-Zustaende ein, sondern
    auch terminale Snapshots mit offenem Blocker, fehlenden Fakten oder
    sichtbarem naechsten Schritt.
    """

    if context is None:
        return False
    if context.is_open:
        return True
    return bool(context.blocker or context.next_step or context.missing_facts)


def visible_next_step(context: Optional[WorkContext]) -> str:
    """Liefert den naechsten fuer den User sichtbaren Handlungshinweis."""

    if context is None:
        return ""
    if context.next_step:
        return context.next_step
    if context.blocker:
        return "Offenen technischen Blocker pruefen"
    if context.missing_facts:
        return "Fehlende Fakten klaeren"
    if context.last_step and has_open_work_context(context):
        return context.last_step
    return ""


def should_explain_from_work_context(user_text: str, context: Optional[WorkContext]) -> bool:
    """Return True fuer erklaerende Follow-ups auf offenen Arbeitskontext."""

    if not has_open_work_context(context):
        return False
    if not str(user_text or "").strip():
        return False
    if should_execute_from_work_context(user_text, context):
        return False
    return is_explanatory_unresolved_followup(user_text)


def should_execute_from_work_context(user_text: str, context: Optional[WorkContext]) -> bool:
    """Return True fuer handlungsorientierte Follow-ups auf offenen Kontext."""

    if not has_open_work_context(context):
        return False
    if not str(user_text or "").strip():
        return False
    return is_actionable_unresolved_followup(user_text)


def is_explanatory_unresolved_followup(user_text: str) -> bool:
    text = _normalized(user_text)
    if not text:
        return False
    return any(marker in text for marker in _EXPLAIN_MARKERS)


def is_actionable_unresolved_followup(user_text: str) -> bool:
    text = _normalized(user_text)
    if not text:
        return False
    return any(marker in text for marker in _ACTION_MARKERS)


__all__ = [
    "has_open_work_context",
    "is_actionable_unresolved_followup",
    "is_explanatory_unresolved_followup",
    "should_execute_from_work_context",
    "should_explain_from_work_context",
    "visible_next_step",
]
