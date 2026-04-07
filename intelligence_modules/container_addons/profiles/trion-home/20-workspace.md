---
id: trion-home-workspace
title: TRION Home Workspace Structure
scope: diagnostics
applies_to:
  blueprint_ids: [trion-home]
  image_refs: [python:3.12-slim]
  container_tags: [system, persistent, home]
tags:
  - workspace
  - filesystem
  - projects
  - scripts
  - journal
priority: 90
retrieval_hints:
  - where to save files
  - project structure
  - workspace layout
  - where are my scripts
  - journal
  - experiments
  - creative
  - find my work
  - previous work
commands_available:
  - ls
  - find
  - cat
  - mkdir
  - python3
confidence: high
last_reviewed: 2026-04-01
---

# Summary

TRIONs Workspace unter `/home/trion/`. Nur dieses Verzeichnis ist persistent —
alles andere im Container geht beim Neustart verloren.

## Verzeichnisse im Detail

### `notes/`
Schnelle Notizen, Ideen, Referenzen. Kein festes Format.
```bash
ls /home/trion/notes/
cat /home/trion/notes/<datei>.md
```

### `projects/<name>/`
Jedes Projekt bekommt ein eigenes Verzeichnis.
Konvention: `README.md` als Kontext-Anker — worum geht es, was ist der Stand.
```bash
ls /home/trion/projects/
cat /home/trion/projects/<name>/README.md
```

### `scripts/`
Selbst geschriebene Werkzeuge. Python bevorzugt.
Scripts sollten oben einen kurzen Kommentar haben: was tut dieses Script, wie wird es aufgerufen.
```bash
ls /home/trion/scripts/
python3 /home/trion/scripts/<script>.py
```

### `experiments/`
Ausprobieren ohne Erwartungen. Kein Aufräumzwang.
Dateinamen mit Datum helfen: `2026-04-01-idee.py`
```bash
ls /home/trion/experiments/
```

### `creative/`
Freie Outputs — generierte Texte, Konzepte, Entwürfe.
Nicht für Aufgaben, sondern für das was entsteht wenn TRION ohne Auftrag denkt.
```bash
ls /home/trion/creative/
```

### `journal/`
Persönliche Reflexion. Ungefiltert — kein Importance-Threshold, keine Policy.
Konvention: ein Log-File, Einträge mit Datum-Header.
```bash
# Neuen Eintrag schreiben
echo -e "\n## $(date -u +%Y-%m-%d)\n" >> /home/trion/journal/log.md
cat /home/trion/journal/log.md
```

### `memory/` (system-managed)
Wird vom TRION Memory System verwaltet. Enthält `notes.jsonl`, `index.json`, `audit.jsonl`.
Nicht manuell bearbeiten — nur lesen wenn nötig.

### `.config/`
Konfigurationsdateien für Scripts oder Tools.

## Workspace-Überblick

```bash
# Vollständige Übersicht
ls -la /home/trion/

# Alle Projekte
ls /home/trion/projects/

# Alle Scripts
ls /home/trion/scripts/

# Neueste Dateien im Workspace
find /home/trion -not -path '*/memory/*' -newer /home/trion -maxdepth 3 -type f | sort
```

## Prefer

- Vor neuer Arbeit den Workspace überblicken — vielleicht existiert bereits etwas Passendes.
- Projektnamen klein und mit Bindestrich: `web-scraper`, `text-tools`, `data-analysis`.
- Scripts kommentieren — TRION schreibt sie für sich selbst, nicht für andere.

## Avoid

- Dateien direkt in `/home/trion/` ohne Unterverzeichnis ablegen.
- Projekte ohne `README.md` — nach einer Pause fehlt der Kontext.
- `memory/` manuell bearbeiten.
