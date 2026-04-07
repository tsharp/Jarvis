---
id: skill-draft-skills
title: Draft Skills
scope: draft_skills
tags:
  - skill_taxonomy
  - draft_skills
priority: 85
question_types:
  - welche draft skills gibt es
  - welche skills sind noch nicht aktiv
  - was fehlt dir an skills
retrieval_hints:
  - draft skills
  - inactive skills
  - skill pipeline
source_of_truth:
  live_data:
    - /v1/skills
    - TypedState
  addon_role: semantic_guardrails
last_reviewed: 2026-04-02
---

# Summary

- Draft Skills sind vorhandene Skills, die noch nicht aktiv installiert oder
  freigegeben sind.
- Sie zaehlen nicht als aktive Runtime-Skills.

## Included

- Skill-Entwuerfe mit Draft-Status
- Skills, die in der Skill-Pipeline sichtbar sind, aber noch nicht im aktiven
  Runtime-Inventar auftauchen

## Not Included

- bereits aktiv installierte Runtime-Skills
- Built-in Tools
- Session-/System-Skills

## Source of Truth

- Draft-Informationen kommen aus `/v1/skills` und einer passenden TypedState-
  Sicht.
- Diese Datei erklaert nur, warum Drafts semantisch getrennt von aktiven Skills
  beantwortet werden muessen.

## Answering Notes

- Wenn nach `welche skills hast du` gefragt wird, sollen Drafts nicht still als
  aktive Skills mitgezaehlt werden.
- Wenn die Frage eher nach Luecken oder in Vorbereitung befindlichen Skills
  fragt, koennen Drafts als eigene Ebene erwaehnt werden.
