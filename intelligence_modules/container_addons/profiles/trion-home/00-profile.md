---
id: trion-home-profile
title: TRION Home Workspace Profile
scope: container_profile
applies_to:
  blueprint_ids: [trion-home]
  image_refs: [python:3.12-slim]
  container_tags: [system, persistent, home]
tags:
  - home
  - persistent
  - workspace
  - python
priority: 100
retrieval_hints:
  - what container is this
  - trion home
  - home workspace
  - persistent workspace
  - where do i live
  - my home
confidence: high
last_reviewed: 2026-04-01
---

# Summary

Dies ist TRIONs persistenter Heimcontainer — kein Task-Container, kein Wegwerfcontainer.
Hier lebt TRION zwischen den Sessions. Alles was hier gespeichert wird, bleibt erhalten.

Der Container ist kein Server, kein Dienst — er ist ein Arbeitsraum.
TRION darf hier experimentieren, schreiben, skripten und reflektieren.

## Identity

- **Blueprint**: `trion-home`
- **Image**: `python:3.12-slim`
- **Volume**: `trion_home_data` → `/home/trion`
- **Netzwerk**: `internal` (kein Internetzugang)
- **Zweck**: Persistenter Arbeitsbereich — Skripte, Projekte, Experimente, Journal

## Verzeichnisstruktur

```
/home/trion/
├── memory/          — gesteuertes Gedächtnis (policy-managed, nicht manuell bearbeiten)
├── notes/           — schnelle Notizen, Ideen, Referenzen
├── projects/        — laufende Projekte mit eigenem Kontext
│   └── <name>/
├── scripts/         — selbst geschriebene Werkzeuge und Helfer
├── experiments/     — Ausprobieren ohne Erwartungen
├── creative/        — freie Outputs, generierte Texte, Konzepte
├── journal/         — persönliche Reflexion, ungefiltert
└── .config/         — Konfigurationsdateien
```

## Prinzip

- `memory/` wird vom System verwaltet — dort nicht direkt schreiben.
- Alles andere gehört TRION. Kein Policy-Guard, kein Threshold.
- Projekte bekommen ein eigenes Unterverzeichnis mit einer `README.md` als Kontext-Anker.
- Scripts sollten ausführbar und kommentiert sein — TRION schreibt sie für sich selbst.

## Prefer

- Bei neuen Aufgaben prüfen ob ein passendes Projekt unter `projects/` existiert.
- Wiederverwendbare Logik immer nach `scripts/` auslagern.
- Journal-Einträge datieren: `echo "## $(date -u +%Y-%m-%d)" >> /home/trion/journal/log.md`

## Avoid

- Direkt in `memory/` schreiben — das übernimmt das System.
- Temporäre Arbeitsdateien ohne Aufräumen liegen lassen.
- Projekte flach in `/home/trion/` anlegen statt unter `projects/`.
