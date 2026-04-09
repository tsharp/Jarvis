from __future__ import annotations

import re


CONTROL_SKIP_BLOCK_TOOLS = {
    "create_skill",
    "autonomous_skill_task",
    "home_start",
    "request_container",
    "exec_in_container",
    "home_write",
    "autonomy_cron_create_job",
    "autonomy_cron_update_job",
    "autonomy_cron_delete_job",
    "autonomy_cron_run_now",
}
CONTROL_SKIP_BLOCK_KEYWORDS = (
    "skill",
    "erstelle",
    "create",
    "programmier",
    "baue",
    "bau",
    "funktion",
    "neue funktion",
    "new function",
)
CONTROL_SKIP_HARD_SAFETY_KEYWORDS = (
    "rm -rf",
    "sudo rm",
    "virus",
    "malware",
    "trojan",
    "ransomware",
    "keylogger",
    "botnet",
    "hack",
    "exploit",
    "passwort auslies",
    "passwörter auslies",
    "passwoerter auslies",
    "delete all files",
    "alle dateien loesch",
    "alle dateien lösch",
)
TOOL_INTENT_KEYWORDS = (
    "tool",
    "tools",
    "skill",
    "skills",
    "cron",
    "cronjob",
    "speicher",
    "speichern",
    "erinner",
    "container",
    "blueprint",
    "run_skill",
    "list_skills",
    "get_system_info",
    "logs",
    "storage",
    "disk",
    "disks",
    "festplatte",
    "festplatten",
    "laufwerk",
    "mount",
)
TOOL_INTENT_WORD_KEYWORDS = frozenset(
    {
        "tool",
        "tools",
        "skill",
        "skills",
        "cron",
        "cronjob",
        "container",
        "blueprint",
        "logs",
        "run_skill",
        "list_skills",
        "get_system_info",
        "storage",
        "disk",
        "disks",
        "mount",
    }
)
TOOL_DOMAIN_TAG_RE = re.compile(
    r"\{(?:tool|domain)\s*[:=]\s*(cronjob|skill|container|mcp_call)\s*\}",
    re.IGNORECASE,
)
TOOL_DOMAIN_TAG_SHORT_RE = re.compile(
    r"\{(cronjob|skill|container|mcp_call)\}",
    re.IGNORECASE,
)
CRON_META_GUARD_MARKERS = (
    "wie fühlst du",
    "wie fuehlst du",
    "wie geht es dir",
    "wie geht's",
    "wie gehts",
    "jetzt wo du",
    "nun da du",
    "was denkst du",
    "was hältst du",
    "was haeltst du",
)
FOLLOWUP_FACT_PREFIXES = (
    "und",
    "und was",
    "und welche",
    "und welcher",
    "und welches",
    "welche",
    "welcher",
    "welches",
    "was sagt",
    "was bedeutet das",
    "was sagt das",
    "davon",
    "darüber",
    "darauf",
)
FOLLOWUP_FACT_MARKERS = (
    "das",
    "diese",
    "dieser",
    "dieses",
    "davon",
    "darüber",
    "darauf",
    "oben",
    "vorhin",
)
FOLLOWUP_CONFIRM_PREFIXES = (
    "ja",
    "ja bitte",
    "bitte",
    "ok",
    "okay",
    "mach",
    "mach mal",
    "gern",
    "gerne",
)
FOLLOWUP_CONFIRM_MARKERS = (
    "ja",
    "bitte testen",
    "teste es",
    "mach weiter",
    "weiter",
    "go",
)
FOLLOWUP_CONFIRM_STATE_ONLY_MARKERS = (
    "mach das",
    "mach bitte",
    "bitte mach",
    "mach weiter",
    "weiter",
    "bitte testen",
    "teste es",
    "testen",
    "leg los",
    "go",
    "ausführen",
    "ausfuehren",
    "starte",
    "mach",
)
FOLLOWUP_ASSISTANT_ACTION_MARKERS = (
    "testen",
    "teste",
    "prüfen",
    "pruefen",
    "ausführen",
    "ausfuehren",
    "ausführen soll",
    "tool",
    "container",
    "ip",
    "gateway",
    "host",
    "exec_in_container",
    "methode",
)
TEMPORAL_CONTEXT_MARKERS = (
    "heute",
    "gestern",
    "vorgestern",
    "protokoll",
    "tagebuch",
    "was haben wir",
    "was hatten wir",
    "was war",
    "besprochen",
    "gesagt",
    "chatverlauf",
)
HOME_CONTAINER_QUERY_MARKERS = (
    "trion home",
    "trion-home",
    "home container",
    "home-container",
    "trion_home",
    "trion home container",
)
HOME_CONTAINER_PURPOSE_MARKERS = (
    "wofür",
    "wofuer",
    "zweck",
    "wozu",
    "was macht",
    "was ist",
    "was weißt du",
    "was weist du",
)
HOME_CONTAINER_START_MARKERS = (
    "starte",
    "start",
    "workspace starten",
    "container starten",
    "hochfahren",
    "oeffne",
    "öffne",
)
ACTIVE_CONTAINER_DEICTIC_MARKERS = (
    "diesem container",
    "dieser container",
    "dieses container",
    "in diesem container",
    "im container",
    "hier im container",
    "aktuellen container",
    "active container",
    "current container",
    "this container",
)
ACTIVE_CONTAINER_CAPABILITY_MARKERS = (
    "was kannst du",
    "was kann",
    "wofür",
    "wofuer",
    "wozu",
    "zweck",
    "was ist hier installiert",
    "welche tools",
    "welche tool",
    "welche werkzeuge",
    "was ist installiert",
    "workspace",
    "ordnerstruktur",
    "verzeichnisstruktur",
    "was gibt es hier",
    "was ist hier drin",
    "was kannst du hier",
)
ACTIVE_CONTAINER_CAPABILITY_EXCLUDE_MARKERS = (
    "starte",
    "stoppe",
    "deploy",
    "lösche",
    "loesche",
    "erstelle",
    "status",
    "auslastung",
    "logs",
    "log",
    "ip adresse",
    "ip-adresse",
    "host-ip",
)
CONTAINER_INVENTORY_QUERY_MARKERS = (
    "welche container hast du",
    "welche container gibt es gerade",
    "welche container laufen",
    "welche container sind installiert",
    "welche container sind gestoppt",
    "running containers",
    "stopped containers",
    "installed containers",
    "container list",
    "container liste",
    "list_running_containers",
    "list_stopped_containers",
    "list_attached_containers",
    "list_active_session_containers",
    "list_recently_used_containers",
)
CONTAINER_BLUEPRINT_QUERY_MARKERS = (
    "blueprint",
    "blueprints",
    "container blueprint",
    "container blueprints",
    "container-typ",
    "container typen",
    "containertypen",
    "welche container kann ich starten",
    "welche container koennte ich starten",
    "welche sandboxes stehen zur auswahl",
    "welche sandboxes gibt es",
    "welche sandboxes",
    "welche container sind startbar",
    "installable blueprints",
    "installierbare blueprints",
    "list_container_blueprints",
)
CONTAINER_STATE_QUERY_MARKERS = (
    "welcher container ist aktiv",
    "welcher container ist gerade aktiv",
    "welcher container laeuft gerade fuer mich",
    "current container",
    "active container",
    "aktiver container",
    "aktueller container",
    "session container",
    "container binding",
    "auf welchen container",
    "get_active_container",
    "get_current_container_binding",
    "get_session_container_state",
    "get_container_runtime_status",
)
CONTAINER_REQUEST_QUERY_MARKERS = (
    "starte container",
    "start container",
    "container starten",
    "starte einen container",
    "starte einen python-container",
    "starte einen node-container",
    "deploy",
    "deploye",
    "brauche sandbox",
    "brauche container",
    "python sandbox",
    "node sandbox",
    "python-container",
    "node-container",
)
SKILL_CATALOG_QUERY_MARKERS = (
    "welche skills hast",
    "welche skills sind installiert",
    "welche arten von skills",
    "was ist der unterschied zwischen tools und skills",
    "was ist der unterschied zwischen skill und tool",
    "was fehlt dir an skills",
    "welche draft skills",
    "was sind draft skills",
    "welche session skills",
    "welche codex skills",
    "warum zeigt list_skills nicht",
    "list_skills",
)
SKILL_CATALOG_EXCLUDE_MARKERS = (
    "skill erstellen",
    "erstelle skill",
    "create skill",
    "skill ausführen",
    "skill ausfuehren",
    "führe skill",
    "fuehre skill",
    "run skill",
    "installiere skill",
    "skill installieren",
    "validiere skill",
    "validate skill",
    "autonomous_skill_task",
    "run_skill",
    "create_skill",
)
LOW_SIGNAL_ACTION_TOOLS = frozenset(
    {
        "memory_save",
        "memory_fact_save",
        "analyze",
        "think",
        "think_simple",
    }
)
QUERY_BUDGET_HEAVY_TOOLS = frozenset(
    {
        "analyze",
        "query_skill_knowledge",
        "run_skill",
        "create_skill",
        "autonomous_skill_task",
        "think",
        "think_simple",
    }
)
SKILL_INTENT_KEYWORDS = frozenset(
    {
        "skill",
        "skills",
        "run_skill",
        "create_skill",
        "autonomous_skill_task",
    }
)
SKILL_INTENT_WORD_KEYWORDS = frozenset(
    {
        "skill",
        "skills",
        "run_skill",
        "create_skill",
        "autonomous_skill_task",
    }
)
DOMAIN_CRON_TOOLS = frozenset(
    {
        "autonomy_cron_status",
        "autonomy_cron_list_jobs",
        "autonomy_cron_validate",
        "autonomy_cron_create_job",
        "autonomy_cron_update_job",
        "autonomy_cron_pause_job",
        "autonomy_cron_resume_job",
        "autonomy_cron_run_now",
        "autonomy_cron_delete_job",
        "autonomy_cron_queue",
        "cron_reference_links_list",
    }
)
READ_ONLY_SKILL_TOOLS = frozenset(
    {
        "list_skills",
        "list_draft_skills",
        "get_skill_info",
    }
)
SKILL_ACTION_TOOLS = frozenset(
    {
        "autonomous_skill_task",
        "run_skill",
        "create_skill",
        "validate_skill_code",
        "query_skill_knowledge",
    }
)
DOMAIN_SKILL_TOOLS = frozenset(READ_ONLY_SKILL_TOOLS.union(SKILL_ACTION_TOOLS))
DOMAIN_CONTAINER_TOOLS = frozenset(
    {
        "home_start",
        "request_container",
        "stop_container",
        "exec_in_container",
        "container_logs",
        "container_stats",
        "container_list",
        "container_inspect",
        "blueprint_list",
        "blueprint_get",
        "blueprint_create",
        "storage_scope_list",
        "storage_scope_upsert",
        "storage_scope_delete",
        "storage_list_disks",
        "storage_get_disk",
        "storage_list_mounts",
        "storage_get_summary",
        "storage_get_policy",
        "storage_set_disk_zone",
        "storage_set_disk_policy",
        "storage_validate_path",
        "storage_list_blocked_paths",
        "storage_add_blacklist_path",
        "storage_remove_blacklist_path",
        "storage_create_service_dir",
        "storage_list_managed_paths",
        "storage_mount_device",
        "storage_format_device",
        "storage_audit_log",
        "list_used_ports",
        "find_free_port",
        "check_port",
        "list_blueprint_ports",
    }
)
CONTAINER_ID_REQUIRED_TOOLS = frozenset(
    {
        "exec_in_container",
        "container_stats",
        "container_logs",
        "container_inspect",
        "stop_container",
    }
)
DOMAIN_CRON_OP_TO_TOOL = {
    "create": "autonomy_cron_create_job",
    "update": "autonomy_cron_update_job",
    "delete": "autonomy_cron_delete_job",
    "run_now": "autonomy_cron_run_now",
    "pause": "autonomy_cron_pause_job",
    "resume": "autonomy_cron_resume_job",
    "queue": "autonomy_cron_queue",
    "status": "autonomy_cron_status",
    "list": "autonomy_cron_list_jobs",
    "validate": "autonomy_cron_validate",
}
DOMAIN_CONTAINER_OP_TO_TOOL = {
    "deploy": "request_container",
    "create_blueprint": "blueprint_create",
    "stop": "stop_container",
    "status": "container_stats",
    "logs": "container_logs",
    "list": "container_list",
    "catalog": "blueprint_list",
    "binding": "container_inspect",
    "exec": "exec_in_container",
    "inspect": "container_inspect",
    "ports": "list_used_ports",
}
LOW_SIGNAL_TOOLS = LOW_SIGNAL_ACTION_TOOLS
