"""System-Knowledge-Kontext für Task-Loop-Steps.

Erkennt die Query-Class aus dem Intent-Text und lädt passende
system_addon-Docs. Rein statisches Wissen — kein Live-Tool-Call.
Live-Daten kommen aus get_system_info / get_system_overview (Step-Tools).
"""
from __future__ import annotations

from typing import Any


_QUERY_CLASS_SIGNALS: list[tuple[str, list[str]]] = [
    ("self_extension", [
        "skill erstellen", "neuen skill", "create skill", "skill bauen",
        "lücke schließen", "self extension", "selbst erweitern",
        "safe path", "sichere pfade", "alias model", "get_secret",
        "skill lifecycle", "skill reparieren",
    ]),
    ("data_locations", [
        "wo liegen", "wo sind", "api key", "api keys", "secrets",
        "vault", "wo werden gespeichert", "blueprints gespeichert",
        "skill gespeichert", "wo ist die", "daten liegen",
        "wo speichert", "memory gespeichert",
    ]),
    ("auth_model", [
        "auth", "token", "credentials", "bearer", "zugriff",
        "zugriffsmodell", "wie authentifiziere", "interner token",
        "secret resolve", "wie zugriff",
    ]),
    ("tool_surface", [
        "welche tools", "tool surface", "endpoints", "kann ich aufrufen",
        "native tools", "mcp tools", "verfügbare tools", "tool liste",
        "welche endpoints", "tool übersicht",
    ]),
    ("system_topology", [
        "welche services", "service map", "auf welchem port",
        "interne url", "docker netz", "läuft auf port",
        "container name", "service topologie", "welcher port",
        "wo läuft", "service übersicht",
    ]),
]

_GENERIC_SIGNALS: list[str] = [
    "system info", "system overview", "system topologie", "selbstwissen",
    "system selbst", "get_system_info", "get_system_overview",
    "system übersicht", "systemzustand", "eigenes system",
]


def _detect_query_class(intent: str) -> str:
    text = str(intent or "").lower()
    for query_class, signals in _QUERY_CLASS_SIGNALS:
        if any(s in text for s in signals):
            return query_class
    return ""


def is_system_knowledge_intent(intent: str) -> bool:
    text = str(intent or "").lower()
    if any(s in text for s in _GENERIC_SIGNALS):
        return True
    return bool(_detect_query_class(intent))


async def load_system_knowledge_context(
    intent: str,
    *,
    use_embeddings: bool = True,
) -> dict[str, Any]:
    """Lädt system_addon-Kontext für den gegebenen Intent.

    Gibt leeres Dict zurück wenn kein relevanter Kontext gefunden wurde.
    Fängt alle Exceptions damit der Task-Loop nie daran scheitert.
    """
    try:
        if not is_system_knowledge_intent(intent):
            return {}

        from intelligence_modules.system_addons.loader import load_system_addon_context

        query_class = _detect_query_class(intent)
        result = await load_system_addon_context(
            intent=intent,
            query_class=query_class,
            max_docs=3,
            max_chars=3000,
            use_embeddings=use_embeddings,
        )
        context_text = str(result.get("context_text") or "").strip()
        if not context_text:
            return {}
        return {
            "system_addon_context": context_text,
            "system_addon_query_class": query_class or str(result.get("query_class") or ""),
            "system_addon_docs": [
                str(d.get("id") or d.get("title") or "").strip()
                for d in (result.get("selected_docs") or [])
                if isinstance(d, dict) and str(d.get("id") or d.get("title") or "").strip()
            ],
        }
    except Exception:
        return {}


__all__ = ["is_system_knowledge_intent", "load_system_knowledge_context"]
