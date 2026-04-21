# System Addon Spec

Dieses Format ist für TRION's Selbstwissen optimiert.

## Ziel

Ein Addon soll TRION präzise, maschinenlesbare Fakten über sein eigenes System
liefern — nicht Prosa, nicht generische Doku:

- wo welche Daten liegen
- welche Services existieren und was sie tun
- welche Endpoints erreichbar sind und welche Auth sie brauchen
- wie TRION sich sicher selbst erweitern kann
- welche Operationen destructive sind und Bestätigung brauchen

Wichtig:

- Statisches Wissen und Live-Zustand bleiben streng getrennt.
- Ein Addon darf erklären **wo** etwas liegt und **wie** es erreichbar ist.
- Ein Addon darf **nicht** behaupten ob ein Service gerade gesund oder erreichbar ist.
- Live-Zustand kommt immer aus Tools.

## Dateiformat

Jede Addon-Datei ist eine Markdown-Datei mit YAML-Frontmatter.

Beispiel:

```md
---
id: system-data-locations
title: Daten-Orte im TRION-System
scope: data_locations
tags:
  - secrets
  - blueprints
  - skills
  - workspace
priority: 90
retrieval_hints:
  - api key
  - wo liegen
  - secrets
  - wo werden
  - vault
confidence: high
last_reviewed: 2026-04-20
---

# Daten-Orte

## Secrets
- Gespeichert: verschlüsselt in SQL-Memory-DB (mcp-sql-memory Container)
- Nie im Dateisystem oder in Umgebungsvariablen im Klartext
- Abruf in Skills: `get_secret("NAME")` — injiziert vom Skill-Runner
- Abruf für TRION: list_secret_names Tool (nur Namen, nie Werte)
```

## Frontmatter-Felder

Pflicht:

- `id` — eindeutiger Bezeichner (kebab-case)
- `title` — lesbarer Titel
- `scope` — einer der gültigen Scope-Werte (siehe unten)
- `tags` — Liste von Stichwörtern
- `priority` — 0–100, höher = bevorzugt

Optional aber empfohlen:

- `retrieval_hints` — Phrasen die dieses Addon besonders relevant machen
- `confidence` — `high` / `medium` / `low`
- `last_reviewed` — Datum der letzten Überprüfung (YYYY-MM-DD)

## Gültige `scope`-Werte

- `topology`
  Service-Layout, Docker-Netz, Ports, was wo läuft

- `data_locations`
  Wo welche Daten gespeichert sind (Secrets, Blueprints, Skills, Workspace, Memory)

- `auth_model`
  Auth-Mechanismen: interner Token, Docker-Netz-only Endpoints, Bearer-Auth

- `tool_surface`
  Welche Tools und Endpoints TRION aufrufen kann, was sie brauchen, was sie zurückgeben

- `skill_lifecycle`
  Skill create → validate → run Ablauf, was der Skill-Runner macht (Injektion, Alias)

- `safe_paths`
  Was TRION autonom erweitern darf, was User-Bestätigung braucht, was verboten ist

- `alias_model`
  Secret-Alias-Logik im Skill-Runner (TEST_KEY ↔ TEST_API_KEY)

## Inhaltliche Regeln

Ein Addon soll:
- kurze, klare Aussagen verwenden
- konkrete Pfade, URLs, Tool-Namen nennen
- Read-only von schreibenden Operationen trennen
- Bestätigungspflichten explizit markieren

Ein Addon soll nicht:
- Live-Zustand als Tatsache verkaufen ("der Service läuft")
- generische Systemdoku wiederholen
- unsichere Operationen ohne Warnung aufführen
- Endpoints nennen die nicht vom Docker-Netz aus erreichbar sind

## Empfohlene Sections

- `# Summary` — ein Satz was dieses Addon erklärt
- `## [Thema]` — die eigentlichen Fakten, strukturiert
- `## Zugriff` — wie TRION dieses Wissen operativ nutzen kann
- `## Grenzen` — was TRION hier nicht kann oder nicht darf
