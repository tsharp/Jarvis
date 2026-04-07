---
id: container-static-container-reference
title: Important Static Containers
scope: overview
tags:
  - taxonomy
  - static-containers
  - container-manager
priority: 118
retrieval_hints:
  - wichtige container
  - statische container
  - welche container gibt es grundsaetzlich
  - trion runtime
  - trion home
  - runtime hardware
  - filestash
question_types:
  - welche container
  - was ist trion-home
  - was ist runtime-hardware
confidence: high
last_reviewed: 2026-04-05
---

# Summary

Diese Liste beschreibt wichtige statische Containerrollen im System.
Sie beschreibt Zweck und Einordnung, nicht den aktuellen Laufstatus.

## Core Containers

- `trion-runtime`
  Kernlaufzeit fuer Orchestrator, Layer und Chat-Ausfuehrung.
- `trion-home`
  Persistenter Arbeits- und Heimcontainer fuer TRION.
- `runtime-hardware`
  Separater Dienst fuer Hardware-, Capability- und Attachment-Planung.
- `filestash`
  Dateibrowser-/Storage-nahe UI fuer verwaltete Dateizugaenge.

## Weitere bekannte Containerklassen

- `gaming-station`
  Interaktive Gaming-/Desktop-Sandbox als optionaler Containerpfad.
- `jarvis-admin-api`
  Control- und Container-Management-API fuer Deploy-, Runtime- und Statuspfade.

## Antwortregel

Wenn nach "welche Container gibt es" gefragt wird, darf diese statische Liste
nur als Einordnung dienen. Ob ein Container gerade laeuft, gestoppt ist oder
ueberhaupt lokal vorhanden ist, muss separat ueber Laufzeittools verifiziert
werden.
