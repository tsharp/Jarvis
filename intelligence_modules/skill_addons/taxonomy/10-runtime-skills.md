---
id: skill-runtime-skills
title: Installed Runtime Skills
scope: runtime_skills
tags:
  - skill_taxonomy
  - runtime_skills
priority: 95
question_types:
  - welche skills hast du
  - welche skills sind installiert
  - welche runtime skills gibt es
retrieval_hints:
  - installed skills
  - active skills
  - runtime skill registry
source_of_truth:
  live_data:
    - list_skills
    - /v1/skills
    - installed.json
    - TypedState
  addon_role: semantic_guardrails
last_reviewed: 2026-04-02
---

# Summary

- Installed Runtime Skills sind die Skills, die in der Runtime-Registry aktiv
  installiert und nutzbar sind.
- `list_skills` deckt nur installierte Runtime-Skills ab.

## Included

- aktive Skill-Eintraege aus der Skill-Registry
- konkrete Skill-Metadaten aus `/v1/skills`
- kompakte Statussicht aus TypedState

## Not Included

- Draft Skills
- Built-in Tools
- Session-/System-Skills
- potenziell verfuegbare, aber nicht installierte Marketplace-Skills

## Source of Truth

- Konkrete Counts, Namen und Status muessen live aus `list_skills`, `/v1/skills`
  oder einem Runtime-Snapshot kommen.
- Diese Datei ersetzt kein Inventar und haelt keine Namensliste vor.

## Answering Notes

- Formulierungsmuster: `Im Runtime-Skill-System sind aktuell <count> aktive
  Skills installiert.`
- Danach kann klarstellend folgen, dass dies nicht identisch mit Tools oder
  Session-Skills ist.
