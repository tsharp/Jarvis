---
id: skill-tools-vs-skills
title: Tools Versus Skills
scope: tools_vs_skills
tags:
  - skill_taxonomy
  - tools_vs_skills
priority: 90
question_types:
  - was ist der unterschied zwischen tools und skills
  - welche faehigkeiten hast du
  - warum zeigt list_skills nicht alles
retrieval_hints:
  - tools vs skills
  - built-in tools
  - mcp tools
source_of_truth:
  live_data:
    - list_skills
    - tool registry
  addon_role: semantic_guardrails
last_reviewed: 2026-04-02
---

# Summary

- Built-in Tools sind native oder MCP-gebundene Werkzeuge.
- Tools koennen Faehigkeiten abbilden, sind aber nicht automatisch installierte
  Runtime-Skills.
- `list_skills` deckt nicht die komplette Faehigkeitenwelt ab.

## Included

- native Tools im Laufzeitsystem
- MCP-gebundene Tools
- funktionale Faehigkeiten, die ohne Skill-Installation verfuegbar sind

## Not Included

- installierte Runtime-Skills als Tool-Ersatz
- die Behauptung, dass jedes Tool ein Skill sei

## Source of Truth

- Tool-Verfuegbarkeit kommt aus Tool-Registry oder Laufzeitkontext.
- Skill-Verfuegbarkeit kommt aus Skill-Registry oder `/v1/skills`.
- Diese Datei liefert nur die begriffliche Trennlinie.

## Answering Notes

- Wenn Nutzer nach `Faehigkeiten` fragen, kann eine Antwort sowohl Tools als
  auch Skills erwaehnen, muss die Ebenen aber trennen.
- Built-in Tools duerfen nicht als installierte Skills dargestellt werden.
