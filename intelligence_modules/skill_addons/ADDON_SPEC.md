# Skill Addon Spec

Dieses Format ist fuer semantische Skill-Fragen in TRION optimiert.

## Ziel

Ein Skill Addon soll **nicht** Skill-Registry oder API-Antworten ersetzen.
Es soll nur die Informationen liefern, die ein kleines Modell fuer saubere
Skill-Antworten braucht:

- welche Skill-Arten es im Gesamtsystem gibt
- wie sich Runtime-Skills, Drafts, Tools und Session-Skills unterscheiden
- welche Quelle fuer welche Aussage autoritativ ist
- wie auf mehrdeutige Skill-Fragen formuliert werden soll

Skill Addons sind **keine zweite Truth-Source fuer konkrete Skill-Inventare**.

## Dateiformat

Jede Addon-Datei ist eine Markdown-Datei mit YAML-Frontmatter.

Beispiel:

```md
---
id: skill-runtime-skills
title: Installed Runtime Skills
scope: runtime_skills
tags:
  - skill_taxonomy
  - runtime_skills
priority: 90
question_types:
  - welche skills hast du
  - welche skills sind installiert
retrieval_hints:
  - active skills
  - installed skills
  - runtime skill registry
source_of_truth:
  live_data:
    - list_skills
    - /v1/skills
    - TypedState
  addon_role: semantic_guardrails
last_reviewed: 2026-04-02
---

# Summary

- Installed Runtime Skills sind aktiv installierte Skills aus der Runtime-
  Registry.
- Konkrete Counts und Namenslisten muessen live aus Registry oder API kommen.
```

## Frontmatter-Felder

Pflicht:

- `id`
- `title`
- `scope`
- `tags`
- `priority`

Optional aber empfohlen:

- `question_types`
- `retrieval_hints`
- `source_of_truth.live_data`
- `source_of_truth.addon_role`
- `last_reviewed`

## Gueltige `scope`-Werte

- `overview`
  Oberbegriff, Taxonomie und zentrale Abgrenzung
- `runtime_skills`
  installierte Runtime-Skills und ihre Wahrheitsquellen
- `draft_skills`
  vorhandene, aber nicht aktive Skills
- `tools_vs_skills`
  Unterschied zwischen nativen Tools und installierten Skills
- `session_skills`
  Session-, Codex- oder System-Skills ausserhalb der Runtime-Registry
- `answering_rules`
  Formulierungs- und Prioritaetsregeln fuer Antworten

## Inhaltliche Regeln

Ein Skill Addon soll:
- Kategorien und Begriffe erklaeren
- explizit sagen, welche Quelle fuer welche Aussage gilt
- Beispiele als Muster oder Templates formulieren
- Mehrdeutigkeit offenlegen, wenn "Skills" mehrere Ebenen meinen kann

Ein Skill Addon darf nicht:
- konkrete Counts enthalten
- aktuelle Namenslisten pflegen
- Installationsstatus einzelner Skills behaupten
- Live-Runtime-Snapshots duplizieren

## Empfohlene Sections

Nicht jede Datei braucht alle, aber diese Struktur ist ideal:

- `# Summary`
- `## Definition`
- `## Included`
- `## Not Included`
- `## Source of Truth`
- `## Answering Notes`

## Retrieval-Ziel

Spaeter soll TRION **nicht** alle Skill Addons komplett laden, sondern nur:
- 1-3 kleine, hochrelevante Leitplankenbloecke
- passend zum Skill-Fragetyp
- immer zusammen mit Live-Daten, falls die Frage instanzbezogene Fakten braucht
