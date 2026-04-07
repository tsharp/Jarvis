---
id: skill-overview
title: Skill Taxonomy Overview
scope: overview
tags:
  - skill_taxonomy
  - runtime_skills
  - draft_skills
  - tools_vs_skills
  - session_skills
priority: 100
question_types:
  - welche skills hast du
  - welche arten von skills gibt es
  - was ist der unterschied zwischen skills und tools
retrieval_hints:
  - skill taxonomy
  - skill categories
  - meaning of skills
source_of_truth:
  live_data:
    - list_skills
    - /v1/skills
    - TypedState
  addon_role: semantic_guardrails
last_reviewed: 2026-04-02
---

# Summary

- In TRION ist `Skills` kein einzelner Datentopf, sondern ein Sammelbegriff fuer
  mehrere Ebenen.
- Fuer saubere Antworten muessen mindestens Installed Runtime Skills, Draft
  Skills, Built-in Tools und Session-/System-Skills getrennt werden.
- `list_skills` deckt nicht die komplette Faehigkeitenwelt ab.

## Definition

- Installed Runtime Skills sind aktiv installierte Skills aus der Runtime-
  Registry.
- Draft Skills sind vorhandene, aber noch nicht aktiv installierte oder
  freigegebene Skills.
- Built-in Tools sind native oder MCP-gebundene Werkzeuge; sie sind
  Faehigkeiten, aber keine installierten Runtime-Skills.
- Session-/System-Skills sind kontextuelle `SKILL.md`- oder Laufzeit-Skills und
  nicht automatisch Teil der TRION Runtime-Registry.

## Source of Truth

- Konkrete Inventardaten kommen aus Registry, `/v1/skills`, `list_skills` und
  TypedState.
- Diese Datei liefert nur Begriffe, Grenzen und Antwortsemantik.

## Answering Notes

- Wenn eine Frage offen laesst, welche Ebene mit `Skills` gemeint ist, soll die
  Antwort die moeglichen Ebenen kurz trennen.
- Instanzbezogene Aussagen wie Counts, Namen oder Status kommen nur aus Live-
  Daten.
