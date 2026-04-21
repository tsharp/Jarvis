---
id: system-data-locations
title: Daten-Orte im TRION-System
scope: data_locations
tags:
  - secrets
  - blueprints
  - skills
  - workspace
  - memory
  - api-keys
priority: 95
retrieval_hints:
  - api key
  - api keys
  - wo liegen
  - secrets
  - wo werden
  - vault
  - wo sind die
  - blueprints gespeichert
  - skill gespeichert
  - workspace
confidence: high
last_reviewed: 2026-04-20
---

# Daten-Orte im TRION-System

## Invarianten

- Diese Datei beschreibt wo Daten strukturell gespeichert sind.
- Diese Datei sagt nicht ob ein Service gerade erreichbar ist.
- Secret-Werte sind nie ausgabefähig — nur Namen.
- TRION-Home-Container-Dateisystem enthält keine API-Keys oder Secrets.

## Secrets / API-Keys

| feld | wert |
|---|---|
| gespeichert | `mcp-sql-memory` (SQLite, verschlüsselt) |
| nie hier | Home-Container-Dateisystem, Umgebungsvariablen im Klartext, normale Dateien |
| TRION-Zugriff auf Namen | `GET http://jarvis-admin-api:8200/api/secrets` → nur Namen, nie Werte |
| TRION-Zugriff auf Werte | nicht direkt — nur Skill-Runner kann Werte auflösen |
| Abruf in Skill-Code | `get_secret("NAME")` — injiziert vom Skill-Runner zur Laufzeit |
| Speichern | `POST /api/secrets` (admin-api → mcp-sql-memory `secret_save`) |

**Wichtig:** API-Keys liegen nie im Home-Container. Ein `exec_in_container` auf dem
Home-Container findet keine Secrets. Der einzige Pfad zu Secret-Namen ist
`GET /api/secrets` über die Admin-API.

## Blueprints

| feld | wert |
|---|---|
| gespeichert | `jarvis-admin-api` (SQLite) |
| TRION-Zugriff | `blueprint_list` MCP-Tool |
| direkt | `GET http://jarvis-admin-api:8200/api/blueprints` |
| modus | read_only für TRION |

## Skills

| feld | wert |
|---|---|
| Code gespeichert | `tool-executor` Container unter `/skills/{name}/` |
| Metadaten | `trion-skill-server` (`SkillManager`) |
| TRION-Zugriff | `list_skills`, `get_skill_info`, `create_skill`, `run_skill` |
| Drafts | `trion-skill-server` — nicht in `list_skills` sichtbar bis promoted |

## Workspace / Events

| feld | wert |
|---|---|
| gespeichert | `mcp-sql-memory` (SQLite) |
| TRION-Zugriff | `workspace_event_save`, `workspace_event_list` |
| zweck | Protokoll von Aktionen und Ergebnissen über Sessions hinweg |

## Memory-Graph

| feld | wert |
|---|---|
| gespeichert | `mcp-sql-memory` (SQLite) |
| TRION-Zugriff | `memory_graph_search` |
| zweck | semantische Fakten, persistentes Wissen über Gespräche hinweg |

## Artifact-Registry (geplant)

| feld | wert |
|---|---|
| gespeichert | `mcp-sql-memory` (neue Tabelle `trion_artifact_registry`) |
| TRION-Zugriff | `artifact_save`, `artifact_list`, `artifact_get`, `artifact_update` (noch nicht implementiert) |
| zweck | von TRION selbst erstellte Artefakte (Skills, Cron-Jobs, Wrapper) mit Kontext |

## Cron-Jobs

| feld | wert |
|---|---|
| gespeichert | `jarvis-admin-api` |
| TRION-Zugriff | `autonomy_cron_status`, `autonomy_cron_list_jobs`, `autonomy_cron_create_job` etc. |

## Home-Container-Workspace

| feld | wert |
|---|---|
| container | `trion_trion-home_*` |
| TRION-Zugriff | `home_read`, `home_write`, `home_list` |
| inhalt | Arbeitsdateien, temporäre Ergebnisse, selbst geschriebene Skripte |
| nicht hier | Secrets, API-Keys, Blueprints, Skill-Code, Memory-DB |

## Zugriff

- Für Secret-Namen: `GET /api/secrets` oder zukünftig `list_secret_names` Tool
- Für Skill-Inventar: `list_skills`
- Für Blueprint-Inventar: `blueprint_list`
- Für Workspace-History: `workspace_event_list`
- Für eigene erstellte Artefakte: `artifact_list` (geplant)

## Grenzen

- TRION kann nie Secret-Werte direkt lesen — nur der Skill-Runner kann das
- Home-Container hat kein Wissen über System-Daten anderer Services
- Diese Datei sagt nicht ob ein Service gerade erreichbar ist
