---
id: skill-session-skills
title: Session And System Skills
scope: session_skills
tags:
  - skill_taxonomy
  - session_skills
priority: 80
question_types:
  - welche session skills hast du
  - welche codex skills hast du
  - welche system skills sind aktiv
retrieval_hints:
  - SKILL.md
  - codex skills
  - session skills
source_of_truth:
  live_data:
    - session context
    - SKILL.md
    - runtime prompt context
  addon_role: semantic_guardrails
last_reviewed: 2026-04-02
---

# Summary

- Session-/System-Skills sind kontextuelle Faehigkeiten aus `SKILL.md`,
  Session-Konfiguration oder Laufzeitinstruktionen.
- Sie sind nicht automatisch Teil der TRION Runtime-Skill-Registry.

## Included

- explizit in der aktuellen Session geladene `SKILL.md`-Faehigkeiten
- systemseitige Skill-Instruktionen mit klarer Quelle im aktuellen Laufkontext

## Not Included

- aktive Runtime-Skills aus der Skill-Registry
- Draft Skills
- allgemeine Modellfaehigkeiten ohne explizite Skill-Quelle

## Source of Truth

- Aussagen ueber Session-Skills brauchen eine explizite Quelle im aktuellen
  Kontext.
- Ohne solche Quelle soll nicht behauptet werden, dass bestimmte Session-Skills
  aktiv sind.

## Answering Notes

- Session-/System-Skills sollen nur genannt werden, wenn die aktuelle Session
  diese Ebene wirklich sichtbar macht.
- Sie muessen sprachlich von Runtime-Skills getrennt werden.
