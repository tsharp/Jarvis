---
id: container-answering-rules
title: Container Answering Rules
scope: answering_rules
tags:
  - taxonomy
  - answering-rules
  - inventory
  - blueprint
priority: 130
retrieval_hints:
  - sauber trennen
  - nicht vermischen
  - running containers
  - blueprints
  - active container
  - capabilities
  - truth source
confidence: high
last_reviewed: 2026-04-05
---

# Summary

Containerantworten muessen die Wahrheitsquelle sichtbar sauber halten.

## Hard Rules

- `list_container_blueprints` bedeutet: was grundsaetzlich existiert oder startbar ist.
- `list_running_containers` bedeutet: was gerade lebt.
- Diese beiden Listen duerfen nie in denselben Antworttopf geworfen werden.

## Inventarfragen

Bei Fragen wie:
- `welche Container hast du`
- `welche Container laufen`
- `welche Container sind installiert`

gilt:
- keine Blueprint-Antwort als Hauptantwort
- keine Capability-Antwort als Ersatz
- keine Start-/Deploy-Empfehlung als Default

## Blueprint-Fragen

Bei Fragen wie:
- `welche Blueprints gibt es`
- `welche Container koennte ich starten`

gilt:
- keine Behauptung ueber aktuell laufende Container
- keine Session-Bindung behaupten

## Active-Container-Fragen

Bei Fragen wie:
- `welcher Container ist gerade aktiv`
- `auf welchen Container ist dieser Turn gebunden`

gilt:
- Session-/Conversation-State ist autoritativ
- statische Profile sind nur Erklaerung, nicht Bindungsbeweis

## Capability-Fragen

Bei Fragen wie:
- `was kannst du in diesem Container tun`
- `welches Tooling hat dieser Container`

gilt:
- Inventarlisten sind nicht die Hauptantwort
- Blueprint-Katalog ist nicht die Hauptantwort
- Profilwissen darf nur semantisch erklaeren, nicht Runtime-Fakten erfinden
