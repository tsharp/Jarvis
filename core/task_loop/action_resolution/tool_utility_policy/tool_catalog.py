"""Tool-Katalog: Capability-Type + Intent → konkrete suggested_tools.

Zwei Phasen:
  1. Intent-Analyse: Enthaelt der Text aktive Schluesselwoerter?
     (starte, create, fuehre aus, ...)
     → Aktions-Tools (schreibend/ausfuehrend)

  2. Fallback: Discovery-Tools (lesend, sicher)
     (list_skills, container_list, autonomy_cron_status, ...)

Faustregel: Lieber ein listendes Tool zu viel als ein schreibendes zu frueh.
Das read_first_policy-Prinzip gilt hier auch.

MCP und direct erhalten absichtlich keine statischen Vorschlaege —
MCP-Tools sind dynamisch registriert, direct braucht keine Tools.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Discovery-Tools — sicher, immer lesend
# ---------------------------------------------------------------------------
_DISCOVERY: dict[str, list[str]] = {
    "container_manager":  ["container_list"],
    "skill":              ["list_skills"],
    "cron":               ["autonomy_cron_status", "autonomy_cron_list_jobs"],
    "secrets":            ["list_secret_names"],
    "system_knowledge":   ["get_system_info", "get_system_overview"],
    "mcp":                [],
    "direct":             [],
}

# ---------------------------------------------------------------------------
# Aktions-Intent-Map: (keywords, tools)
# Erster Match gewinnt → spezifischste Keywords zuerst
# ---------------------------------------------------------------------------
_ACTION_INTENTS: dict[str, list[tuple[list[str], list[str]]]] = {
    "container_manager": [
        (["exec", "befehl", "command"],          ["exec_in_container"]),
        (["stop", "stoppe", "beende", "kill"],   ["stop_container"]),
        (["logs", "log", "output"],               ["container_logs"]),
        (["stats", "statistik", "ressourcen", "resources", "cpu", "ram", "speicher"],
                                                  ["container_stats"]),
        (["blueprint", "vorlage"],                ["blueprint_list"]),
        (["inspect", "details"],                  ["container_inspect"]),
        (["start", "starte", "launch", "run", "deploy",
          "erstelle", "create", "new", "neuen"],  ["request_container"]),
    ],
    "skill": [
        (["validate", "validiere", "prüfe code", "pruefe code"],
                                                  ["validate_skill_code"]),
        (["info", "details", "inspect", "zeige skill"],
                                                  ["get_skill_info"]),
        (["create", "erstelle", "new", "neu", "baue", "build", "schreibe"],
                                                  ["create_skill"]),
        (["run", "execute", "fuehre", "führe", "ausführen", "ausfuehren",
          "starte", "start"],                     ["run_skill"]),
    ],
    "cron": [
        (["queue", "warteschlange"],              ["autonomy_cron_queue"]),
        (["validate", "validiere"],               ["autonomy_cron_validate"]),
        (["run now", "jetzt", "sofort"],            ["autonomy_cron_run_now"]),
        (["resume", "fortsetze", "weiter", "reaktiviere"],
                                                  ["autonomy_cron_resume_job"]),
        (["pause", "pausiere"],                   ["autonomy_cron_pause_job"]),
        (["delete", "remove", "lösche", "loesche", "entferne"],
                                                  ["autonomy_cron_delete_job"]),
        (["update", "aktualisiere", "change", "ändern", "aendern", "modifiziere"],
                                                  ["autonomy_cron_update_job"]),
        (["create", "erstelle", "anlege", "anleg", "schedule",
          "einrichten", "new", "neu", "richte"],  ["autonomy_cron_create_job"]),
    ],
    "system_knowledge": [],  # immer Discovery, keine Aktions-Tools
    "mcp":    [],
    "direct": [],
}


DISCOVERY_TOOLS: frozenset[str] = frozenset(
    tool for tools in _DISCOVERY.values() for tool in tools
)


def is_discovery_only(tools: list[str]) -> bool:
    """True wenn alle Tools in der Liste reine Discovery-/Read-Tools sind."""
    return bool(tools) and all(t in DISCOVERY_TOOLS for t in tools)


def suggest_tools_for_step(
    capability_type: str,
    intent: str,
) -> list[str]:
    """Gibt eine priorisierte Tool-Liste fuer capability_type + intent zurueck.

    Gibt [] zurueck fuer unbekannte capability_types, mcp und direct.
    Bevorzugt Discovery-Tools ausser der Intent enthaelt eindeutige Aktions-Marker.
    """
    cap = str(capability_type or "").strip().lower()
    text = str(intent or "").lower()

    action_intents = _ACTION_INTENTS.get(cap)
    if action_intents is None:
        return []

    for keywords, tools in action_intents:
        if any(kw in text for kw in keywords):
            return list(tools)

    return list(_DISCOVERY.get(cap, []))


__all__ = ["suggest_tools_for_step", "is_discovery_only", "DISCOVERY_TOOLS"]
