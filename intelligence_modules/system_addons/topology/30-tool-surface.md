---
id: system-tool-surface
title: Tool-Surface im TRION-System
scope: tool_surface
tags:
  - tools
  - endpoints
  - mcp
  - native
  - skills
  - container
priority: 85
retrieval_hints:
  - welche tools
  - tool surface
  - welche endpoints
  - kann ich aufrufen
  - native tools
  - mcp tools
  - verfügbare tools
  - tool liste
confidence: high
last_reviewed: 2026-04-21
---

## Invarianten

- Native Tools sind immer verfügbar.
- MCP-Tools sind dynamisch und dürfen nicht als garantiert angenommen werden.
- Tool-Existenz != Tool-Gesundheit.
- Read-only bevorzugen, bevor write/execute genutzt wird.
- Secrets sind eine sensible Domäne; Secret-Werte sind nicht ausgabefähig.

## Native Tools

### System

| tool | domäne | modus |
|---|---|---|
| `get_system_info` | system | read_only |
| `get_system_overview` | system | read_only |

### Skills

| tool | domäne | modus |
|---|---|---|
| `list_skills` | skills | read_only |
| `get_skill_info` | skills | read_only |
| `create_skill` | skills | write |
| `run_skill` | skills | execute |
| `validate_skill_code` | skills | read_only |

### Container / Blueprints

| tool | domäne | modus |
|---|---|---|
| `container_list` | container | read_only |
| `blueprint_list` | blueprints | read_only |
| `request_container` | container | write |
| `exec_in_container` | container | execute |
| `stop_container` | container | write |
| `container_logs` | container | read_only |
| `container_stats` | container | read_only |
| `container_inspect` | container | read_only |

### Home / Workspace-Dateien

| tool | domäne | modus |
|---|---|---|
| `home_read` | home | read_only |
| `home_write` | home | write |
| `home_list` | home | read_only |

## MCP- / Dynamic Surface

### Memory / Workspace

| tool | domäne | modus |
|---|---|---|
| `workspace_event_list` | memory | read_only |
| `workspace_event_save` | memory | write |
| `memory_graph_search` | memory | read_only |

### Secrets

| tool_or_endpoint | domäne | modus |
|---|---|---|
| `GET /api/secrets` | secrets | read_only_names |
| `GET /api/secrets/resolve/{NAME}` | secrets | sensitive_read |
| `secret_save` | secrets | write |

### Skills via MCP / Bridge

| tool | domäne | modus |
|---|---|---|
| `list_skills` | skills | read_only |
| `create_skill` | skills | write |
| `run_skill` | skills | execute |

### Weitere dynamische Flächen

| tool_family | quelle | regel |
|---|---|---|
| sequential thinking tools | `sequential-thinking` | dynamisch |
| storage tools | `storage-broker` | dynamisch |
| skill server tools | `trion-skill-server` | dynamisch |
| sql-memory tools | `mcp-sql-memory` | dynamisch |

## Operative Reihenfolge

1. Read-only Tool verwenden, wenn ausreichend.
2. Native Tool vor MCP-Tool bevorzugen, wenn Capability gleichwertig ist.
3. MCP-Verfügbarkeit nicht annehmen; discovery/live inventory prüfen.
4. Write-/Execute-Tools nur bei echter Änderungsabsicht.
5. Secret-bezogene Pfade nie für normale Antwortgenerierung verwenden.

## Domänenregeln

### System
- `get_system_info`, `get_system_overview` liefern Realitätssignale.
- System-Tools ersetzen keine Datenpersistenz.

### Skills
- `list_skills` für Inventar.
- `get_skill_info` für Detailprüfung.
- `create_skill` verändert Systemoberfläche.
- `run_skill` führt Operation aus, nicht nur Analyse.

### Container
- Container-Tools greifen in Laufzeitumgebung ein oder lesen sie aus.
- `request_container`, `stop_container`, `exec_in_container` sind verändernd/operativ.

### Secrets
- `GET /api/secrets` gibt nur Namen zurück.
- `GET /api/secrets/resolve/{NAME}` ist sensitiv.
- Secret-Werte dürfen nicht im Tool-Output erscheinen.

## Zugriff

- Für Bestandsaufnahme: read-only Tools zuerst.
- Für Erweiterung: `create_skill` + `validate_skill_code`.
- Für operative Ausführung: `run_skill` oder passende Container-Tools.
- Für Secrets: nur Inventar listen oder intern gekapselt verwenden.

## Grenzen

- Diese Datei sagt nicht, welche MCP-Tools aktuell registriert sind.
- Diese Datei sagt nicht, ob ein Tool aktuell gesund ist.
- Diese Datei sagt nicht, welche Ergebnisse ein Tool aktuell liefern wird.
- Diese Datei ersetzt keine Live-Discovery.
