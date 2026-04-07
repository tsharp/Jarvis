---
id: skill-answering-rules
title: Skill Answering Rules
scope: answering_rules
tags:
  - skill_taxonomy
  - answering_rules
priority: 100
question_types:
  - welche skills hast du
  - was fehlt dir an skills
  - was ist der unterschied zwischen skills und tools
retrieval_hints:
  - answering rules
  - phrasing guardrails
  - skill ambiguity
source_of_truth:
  live_data:
    - list_skills
    - /v1/skills
    - TypedState
    - session context
  addon_role: semantic_guardrails
last_reviewed: 2026-04-02
---

# Summary

- Skill-Antworten muessen erst Fakt-Ebene und dann Begriffs-Ebene sauber
  trennen.
- `list_skills` beschreibt nur installierte Runtime-Skills.

## Answering Rules

- Zuerst die autoritative Live-Quelle fuer instanzbezogene Fakten nutzen.
- Danach die richtige Kategorie benennen: Runtime-Skills, Draft Skills,
  Built-in Tools oder Session-/System-Skills.
- Wenn `Skills` mehrdeutig ist, die Mehrdeutigkeit explizit aufloesen statt
  still eine Ebene zu raten.
- Built-in Tools nicht als installierte Skills darstellen.
- Draft Skills nicht als aktive Skills formulieren.
- Session-/System-Skills nur nennen, wenn die Quelle dafuer im aktuellen
  Kontext explizit vorhanden ist.

## Formulierungsmuster

- `Im Runtime-Skill-System sind aktuell <count> aktive Skills installiert.`
- `Das deckt nur installierte Runtime-Skills ab, nicht Built-in Tools oder
  Session-Skills.`
- `Wenn du mit Skills die gesamte Faehigkeitenwelt meinst, muss man Runtime-
  Skills, Tools und Session-Skills getrennt betrachten.`

## Avoid

- `Ich habe <count> Skills`, wenn der Count in Wahrheit nur `list_skills`
  meint, aber die Antwort als Gesamtfaehigkeit formuliert ist.
- `Tool X ist als Skill installiert`, wenn nur Tool-Verfuegbarkeit belegt ist.
- `Mir fehlen Skill Y und Z`, wenn dafuer keine belastbare Draft- oder
  Katalogquelle vorliegt.
