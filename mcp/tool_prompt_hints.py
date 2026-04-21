from __future__ import annotations

from typing import Dict, List, Tuple


TOOL_KEYWORDS: Dict[str, List[str]] = {
    "get_system_info": [
        "GPU", "VRAM", "CPU", "RAM", "Arbeitsspeicher", "Disk", "Festplatte",
        "Temperatur", "Hardware", "nvidia", "Prozessor", "Auslastung",
        "Netzwerk", "Ports", "Docker-Status", "Uptime", "Kernel", "dmesg",
    ],
    "get_system_overview": [
        "System", "Übersicht", "Hardware", "Status", "GPU", "CPU", "RAM", "Disk",
        "alle Infos", "Zusammenfassung",
    ],
    "request_container": [
        "Container", "starten", "erstellen", "Python", "Code ausführen",
        "Sandbox", "deployen", "aufsetzen", "neuen Container",
    ],
    "stop_container": [
        "Container", "stoppen", "beenden", "löschen", "herunterfahren",
    ],
    "exec_in_container": [
        "Code", "ausführen", "Container", "Python", "Script", "Command",
        "Bash", "Shell", "Terminal", "run",
    ],
    "container_logs": [
        "Logs", "Container", "Ausgabe", "Output", "Fehler", "Error", "Log",
    ],
    "container_stats": [
        "Container", "Stats", "Status", "läuft", "aktiv", "Ressourcen",
    ],
    "container_list": [
        "Container", "auflisten", "alle Container", "welche Container", "laufende Container", "list containers",
    ],
    "container_inspect": [
        "Container", "inspizieren", "Details", "Konfiguration", "Container-Info", "inspect",
    ],
    "blueprint_list": [
        "Blueprint", "Container-Typen", "verfügbare Typen", "Vorlagen",
    ],
    "blueprint_get": ["Blueprint", "Details", "Konfiguration"],
    "blueprint_create": ["Blueprint", "erstellen", "neue Vorlage"],
    "snapshot_list": ["Snapshot", "Backup", "Versionen", "gespeichert"],
    "snapshot_restore": ["Snapshot", "wiederherstellen", "zurücksetzen"],
    "optimize_container": ["Container", "optimieren", "Performance", "tuning"],
    "list_skills": [
        "Skills", "auflisten", "installiert", "verfügbar", "was kann ich",
        "Fähigkeiten",
    ],
    "run_skill": [
        "Skill", "ausführen", "starten", "verwenden", "benutzen",
    ],
    "create_skill": [
        "Skill", "erstellen", "bauen", "programmieren", "neu schreiben",
        "implementieren",
    ],
    "autonomous_skill_task": [
        "Skill", "automatisch", "eigenständig", "selbst erstellen",
        "Aufgabe erledigen", "reparieren", "verbessern",
    ],
    "promote_skill_draft": [
        "Skill", "veröffentlichen", "promoten", "Draft aktivieren",
    ],
    "home_read": [
        "Datei", "lesen", "öffnen", "Inhalt anzeigen", "Notiz lesen", "was steht",
    ],
    "home_write": [
        "Datei", "schreiben", "speichern", "Notiz", "erstellen", "notieren",
        "aufschreiben", "festhalten",
    ],
    "home_list": [
        "Dateien", "auflisten", "Verzeichnis", "Ordner", "welche Dateien",
    ],
    "memory_save": [
        "merken", "speichern", "Fakt", "Notiz", "wissen", "nicht vergessen",
    ],
    "memory_search": [
        "suchen", "finden", "erinnern", "Erinnerung", "was weiß ich",
        "gespeichert", "Fakten",
    ],
    "memory_graph_search": [
        "Graph", "Wissen", "Zusammenhang", "verbunden", "Beziehung",
    ],
    "workspace_save": [
        "Workspace", "Notiz", "Task", "Aufgabe merken", "Plan speichern", "Eintrag erstellen",
    ],
    "workspace_list": [
        "Workspace", "Einträge anzeigen", "offene Aufgaben", "Was habe ich geplant",
    ],
    "workspace_event_save": [
        "Workspace-Event", "Telemetrie", "Container-Event speichern", "internes Ereignis",
    ],
    "workspace_event_list": [
        "Workspace-Events", "Container-Status", "aktive Container", "Event-Log lesen",
    ],
    "skill_metric_record": ["Skill", "Metriken", "Statistik", "aufzeichnen"],
    "skill_metrics_list": ["Skill", "Statistiken", "Übersicht", "Metriken"],
    "graph_add_node": ["Graph", "Knoten", "Wissen", "speichern", "Relation"],
}


CORE_MEMORY_DETECTION_RULES = """
TOOL: memory_save (MCP: sql-memory)
Priority: high
Keywords: remember, save, store, note, keep in mind, merken, speichern, notieren
Triggers: remember that, save this, note that, please remember, bitte merken
Examples: User: Remember my favorite color is blue -> memory_save

TOOL: memory_graph_search (MCP: sql-memory)
Priority: high
Keywords: recall, remember, what do you know, search memory, erinnern, was weisst du
Triggers: do you remember, what did I say, what do you know about, was habe ich gesagt
Examples: User: What is my favorite color? -> memory_graph_search

TOOL: memory_all_recent (MCP: sql-memory)
Priority: medium
Keywords: recent memories, last conversations, previous chats, letzte gespraeche
Triggers: what did we talk about, show recent memories
Examples: User: What did we discuss yesterday? -> memory_all_recent
"""


CORE_COMMANDER_DETECTION_RULES = """
TOOL: blueprint_list (MCP: container-commander)
Priority: high
Keywords: blueprint, blueprints, container-typ, sandbox, container typen, welche container, verfügbare container
Triggers: zeig blueprints, welche blueprints, list blueprints, was für container gibt es, verfügbare sandboxes
Examples: User: Welche Blueprints hast du? -> blueprint_list; User: Was für Container gibt es? -> blueprint_list

TOOL: request_container (MCP: container-commander)
Priority: high
Keywords: starte container, deploy, container starten, brauche sandbox, code ausführen, python starten, node starten
Triggers: starte einen container, deploy blueprint, ich brauche einen container, führe code aus
Examples: User: Starte einen Python Container -> request_container; User: Ich brauche eine Sandbox -> request_container

TOOL: home_start (MCP: container-commander)
Priority: high
Keywords: trion home starten, home workspace starten, trion-home, home container starten
Triggers: starte TRION Home, starte TRION Home Workspace, starte den Home Container
Examples: User: Starte TRION Home Workspace -> home_start

TOOL: stop_container (MCP: container-commander)
Priority: high
Keywords: stoppe container, stop container, beende container, container beenden, container stoppen
Triggers: stoppe den container, beende den container, container runterfahren
Examples: User: Stoppe den Container -> stop_container

TOOL: exec_in_container (MCP: container-commander)
Priority: high
Keywords: ausführen, execute, run code, berechne, programmiere, führe aus, code ausführen
Triggers: führe diesen code aus, berechne fibonacci, execute in container
Examples: User: Berechne die Fibonacci-Folge -> request_container + exec_in_container

TOOL: container_stats (MCP: container-commander)
Priority: medium
Keywords: container stats, container status, auslastung, efficiency, resource usage
Triggers: wie läuft der container, container auslastung, zeig container stats
Examples: User: Wie ist die Container-Auslastung? -> container_stats

TOOL: container_list (MCP: container-commander)
Priority: medium
Keywords: alle container, laufende container, welche container laufen, container auflisten, list containers
Triggers: zeig alle container, welche container sind aktiv, liste container auf
Examples: User: Welche Container laufen gerade? -> container_list; User: Liste alle aktiven Container -> container_list

TOOL: container_inspect (MCP: container-commander)
Priority: medium
Keywords: container details, container info, container konfiguration, inspiziere container, inspect container
Triggers: zeig container details, was ist die konfiguration des containers, inspect container
Examples: User: Zeig mir die Details von Container abc123 -> container_inspect

TOOL: container_logs (MCP: container-commander)
Priority: medium
Keywords: container logs, container ausgabe, log output
Triggers: zeig container logs, was hat der container ausgegeben
Examples: User: Zeig mir die Container Logs -> container_logs
"""


def iter_base_detection_rules() -> Tuple[Tuple[int, str], ...]:
    return (
        (0, CORE_MEMORY_DETECTION_RULES),
        (0, CORE_COMMANDER_DETECTION_RULES),
    )
