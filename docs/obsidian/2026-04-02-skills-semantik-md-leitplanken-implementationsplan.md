# Skills-Semantik ueber MD-Leitplanken stabilisieren - Implementationsplan

Erstellt am: 2026-04-02
Zuletzt aktualisiert: 2026-04-04
Status: **In Umsetzung**
Bezieht sich auf:

- [[2026-04-04-skill-catalog-offene-punkte-masterliste]] - zentraler Sammelpunkt fuer offene Punkte im Skill-Catalog-Strang
- [[2026-04-02-thinking-strategy-authority-and-frontend-visibility-implementationsplan]] - Thinking/Control/Execution-Authority
- [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]] - Live-Drift Follow-up fuer die letzte Output-Meile
- [[2026-04-03-skill-catalog-restfehler-routing-und-output-implementationsplan]] - Restfehleranalyse fuer Routing, Output und Trace
- [[2026-04-04-skill-catalog-draft-evidence-output-repair-gap]] - Befund nach Routing-/Trace-Fix: Draft-Evidence geht im Repair verloren
- [[2026-03-31-control-layer-audit]] - Control als bindende Policy-Autoritaet
- [[2026-04-01-container-capability-followup-grounding-analyse]] - Beispiel fuer Drift durch fehlende semantische Leitplanken
- [[2026-04-01-container-capability-followup-grounding-fix]] - Addon-basierte Grounding-Verbesserung im Containerpfad

---

## Umsetzungsstand 2026-04-02

Block 1, Block 2, Block 4 und Block 5 sind jetzt als erster funktionsfaehiger Skill-Pfad umgesetzt.

Konkrete Aenderungen:

- Die neue semantische Leitplankenschicht liegt jetzt unter
  [intelligence_modules/skill_addons](<repo-root>/intelligence_modules/skill_addons)
- Die Grunddokumentation ist angelegt:
  [README.md](<repo-root>/intelligence_modules/skill_addons/README.md)
  und [ADDON_SPEC.md](<repo-root>/intelligence_modules/skill_addons/ADDON_SPEC.md)
- Die Taxonomie-MDs sind vorhanden und sauber getrennt nach Ebenen:
  [00-overview.md](<repo-root>/intelligence_modules/skill_addons/taxonomy/00-overview.md),
  [10-runtime-skills.md](<repo-root>/intelligence_modules/skill_addons/taxonomy/10-runtime-skills.md),
  [20-drafts.md](<repo-root>/intelligence_modules/skill_addons/taxonomy/20-drafts.md),
  [30-tools-vs-skills.md](<repo-root>/intelligence_modules/skill_addons/taxonomy/30-tools-vs-skills.md),
  [40-session-skills.md](<repo-root>/intelligence_modules/skill_addons/taxonomy/40-session-skills.md),
  [50-answering-rules.md](<repo-root>/intelligence_modules/skill_addons/taxonomy/50-answering-rules.md)
- Der Loader fuer gezielte semantische Skill-Kontextauswahl existiert jetzt:
  [loader.py](<repo-root>/intelligence_modules/skill_addons/loader.py)
- Thinking / Plan-Schema erkennen semantische Skill-Fragen jetzt explizit als
  `resolution_strategy=skill_catalog_context` und tragen passende
  `strategy_hints` wie `runtime_skills`, `draft_skills`, `tools_vs_skills`,
  `session_skills`, `overview`, `answering_rules`:
  [thinking.py](<repo-root>/core/layers/thinking.py),
  [orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
- Control akzeptiert und stabilisiert diese Strategie jetzt ebenfalls als
  autoritative Skill-Aufloesung:
  [control.py](<repo-root>/core/layers/control.py)
- Der Orchestrator baut fuer Skill-Fragen jetzt einen kombinierten Skill-
  Kontext aus Runtime-Snapshot plus `skill_addons`:
  [orchestrator.py](<repo-root>/core/orchestrator.py),
  [orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py),
  [orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)
- Die Output-Schicht trennt jetzt sprachlich Runtime-Skills, Skill-Registry-
  Facts und Skill-Semantik:
  [output.py](<repo-root>/core/layers/output.py)
- Die Leitentscheidung `keine zweite Truth-Source fuer konkrete Skill-Inventare`
  ist im Spec und in den Tests explizit abgesichert:
  [test_skill_addons_contract.py](<repo-root>/tests/unit/test_skill_addons_contract.py)
  und [test_skill_addons_loader_contract.py](<repo-root>/tests/unit/test_skill_addons_loader_contract.py)
- Der neue Skill-Pfad ist ueber gezielte Unit-Tests abgesichert:
  [test_orchestrator_plan_schema_utils.py](<repo-root>/tests/unit/test_orchestrator_plan_schema_utils.py),
  [test_control_contract_flow.py](<repo-root>/tests/unit/test_control_contract_flow.py),
  [test_orchestrator_runtime_safeguards.py](<repo-root>/tests/unit/test_orchestrator_runtime_safeguards.py),
  [test_output_grounding.py](<repo-root>/tests/unit/test_output_grounding.py),
  [test_output_tool_injection.py](<repo-root>/tests/unit/test_output_tool_injection.py)
- Ein erster echter Prompt-Flow-Gegencheck fuer die Skill-Semantik liegt jetzt
  ebenfalls vor und spannt den Pfad von Strategy-Inferenz ueber Control-
  Autoritaet und Skill-Kontextaufbau bis in den Output-Prompt:
  [test_skill_catalog_prompt_flow.py](<repo-root>/tests/unit/test_skill_catalog_prompt_flow.py)

Wichtig:

- Die MD-Schicht enthaelt weiterhin **keine** konkreten Runtime-Counts,
  Namenslisten oder Installationsbehauptungen.
- Live-Inventar bleibt bei `list_skills`, `/v1/skills`, Registry und TypedState.
- Die neuen Antwortregeln werden jetzt nicht nur dokumentiert, sondern auch im
  Output-Prompt und in den Grounding-Fallbacks durchgezogen.
- Offen sind jetzt vor allem groessere Live-/UI-End-to-End-Absicherungen und
  spaetere Frontend-Sichtbarkeit fuer `skill_catalog_context`.
- Der erste echte Live-E2E hat zusaetzlich gezeigt, dass der letzte Output-
  Schritt noch semantisch driftet, obwohl Routing und Runtime-Autoritaet
  stimmen:
  [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]]
- Im zugehoerigen Follow-up sind inzwischen auch die ersten Gegenmassnahmen
  umgesetzt:
  - Block 1: Live-Fall als Regression festgehalten
  - Block 2: Hint-Inferenz fuer generische Skill-Inventarfragen geschaerft
  [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]]
- Der anschliessende WebUI-Live-Test zeigt jetzt einen gemischten Stand:
  - Routing, Trace-Sichtbarkeit und semantische Trennung greifen
  - mehrere Antworten bleiben aber noch auf den Reparaturpfad angewiesen
  - zusaetzlich sind noch zwei Restfehler offen:
    - sichtbarer `[Grounding-Korrektur]`-Leak
    - `draft_skills`-Inventarfrage kippt in Skill-Erstellung
  [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]]
- Die zugehoerige Root-Cause-Analyse zeigt inzwischen klar:
  kein zweites Skill-Inventar, aber eine zweite verdeckte
  Routing-/Policy-Wahrheit fuer Skill-Fragen.
  Der Folgeplan dafuer ist separat dokumentiert:
  [[2026-04-03-skill-catalog-restfehler-routing-und-output-implementationsplan]]
- Der erste Folge-Schnitt aus dieser Root-Cause-Analyse ist inzwischen
  umgesetzt:
  - Block A: bindende Policy fuer Skill-Inventarfragen
  - Block B: Read-only-Skill-Tools und Aktions-Tools sauber getrennt
  [[2026-04-03-skill-catalog-restfehler-routing-und-output-implementationsplan]]
- Damit ist der `draft_skills`-Inventarfehler auf Code-/Test-Ebene nicht mehr
  der primaere offene Punkt.
  Offen bleiben jetzt vor allem:
  - sichtbarer `[Grounding-Korrektur]`-Leak im Stream
  - Trace-/Execution-Konsistenz
  - native Stabilisierung fuer gemischte Inventar-/Wunsch-Prompts
  [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]]
- Der nachgezogene Live-Gegencheck nach Routing-/Trace-Fix zeigt jetzt noch
  einen engeren Restfehler:
  Draft-Evidence kommt korrekt bis in die Execution, wird aber im spaeteren
  Skill-Catalog-Repair noch nicht stabil in die Endantwort uebernommen.
  Das ist separat dokumentiert:
  [[2026-04-04-skill-catalog-draft-evidence-output-repair-gap]]

Damit ist die Kette jetzt sauber vorbereitet:
Thinking/Authority -> Skill-Semantik -> Runtime-Zusammenfuehrung -> saubere Antwortformulierung.

---

## Anlass

Aktuell driftet der Begriff `Skills` in TRION ueber mehrere Ebenen:

- Runtime-Skills aus der Skill-Registry und `list_skills`
- Draft-Skills
- eingebaute/native Tools
- Codex-/Session-Skills mit `SKILL.md`
- potenziell verfuegbare, aber nicht installierte Skills

Dadurch entstehen bei Fragen wie:

- `welche skills hast du?`
- `was fehlt dir an skills?`
- `was ist der unterschied zwischen tools und skills?`

fachlich halb-richtige, aber semantisch unsaubere Antworten.

Der Kernfehler ist nicht primaer ein fehlendes Tool, sondern ein fehlender **Begriffs- und Kategorienkontext**.

---

## Kurzdiagnose

### 1. Die Runtime-Wahrheit ist vorhanden, aber zu eng fuer semantische Fragen

Heute existieren bereits mehrere echte Datenquellen:

- `list_skills` / Skill-Server fuer aktive Runtime-Skills
- Drafts ueber `/v1/skills`
- TypedState-Skill-Kontext in [core/typedstate_skills.py](<repo-root>/core/typedstate_skills.py)
- Skill-Prefetch ueber [core/context_manager.py](<repo-root>/core/context_manager.py) und [core/orchestrator.py](<repo-root>/core/orchestrator.py)

Das Problem:

- diese Quellen sagen gut, **welche Skills registriert sind**
- sie sagen aber nicht sauber genug, **welche Arten von Skills/Faehigkeiten es im Gesamtsystem gibt**

### 2. Eine zweite Truth-Source fuer konkrete Skill-Inventare waere gefaehrlich

Wenn wir in Markdown konkrete Installationsstaende oder Namenslisten pflegen, erzeugen wir sofort Drift.

Beispiele fuer Dinge, die **nicht** in MD gepflegt werden sollten:

- `aktuell 7 Skills installiert`
- `Skill X ist vorhanden`
- `Skill Y ist nicht installiert`

Solche Fakten muessen strukturiert und live aus:

- Skill-Registry
- REST-/MCP-Endpunkten
- TypedState-Pipelines

kommen.

### 3. Was fehlt, ist eine semantische Leitplankenschicht

Analog zu `container_addons` fehlt fuer Skill-Fragen ein kleiner, nachladbarer Wissensblock, der erklaert:

- was in TRION ueberhaupt als `Skill` gilt
- wie sich Skill-Arten voneinander unterscheiden
- was `list_skills` wirklich abdeckt
- was **nicht** unter Runtime-Skills faellt
- wie Antworten auf Skill-Fragen sauber formuliert werden sollen

---

## Zielbild

TRION soll bei Skill-Fragen zwei Wissensarten kombinieren:

### A. Strukturierte Live-Wahrheit

Fuer instanzbezogene Fakten:

- installierte Runtime-Skills
- Draft-Skills
- Detail-Metadaten einzelner Skills
- optional spaeter verfuegbare Marketplace-Skills

### B. Semantische MD-Leitplanken

Fuer erklaerendes und stabileres Wissen:

- Skill-Taxonomie
- Begriffsgrenzen
- Antwortregeln
- Unterschiede zwischen Skill, Tool, Draft, Session-Skill, Built-in Capability

Die MD-Leitplanken sollen **keine Inventarliste** sein, sondern eine **Begriffsschicht gegen Drift**.

---

## Was TRION ueber Skills verstehen soll

Mindestens diese Ebenen muessen sauber unterscheidbar werden:

1. **Installed Runtime Skills**
- aktiv installierte Skills aus der Skill-Registry
- Quelle: `list_skills`, `/v1/skills`, `installed.json`

2. **Draft Skills**
- vorhandene, aber noch nicht aktiv installierte / freigegebene Skills
- Quelle: `/v1/skills`, Draft-Channel

3. **Built-in Tools**
- native oder MCP-gebundene Tools
- sind keine Runtime-Skills, auch wenn sie funktional "Faehigkeiten" sind

4. **Session-/System-Skills**
- Codex-/Session-spezifische `SKILL.md`-Faehigkeiten
- sind nicht automatisch Teil der TRION Runtime-Skill-Registry

5. **Available but not installed Skills** (optional spaeter)
- Marketplace-/Katalog-Skills
- nur wenn dafuer eine belastbare Quelle existiert

---

## Leitprinzipien fuer die MD-Schicht

### 1. Keine per-Skill-Pflege

Die MDs sollen **nicht** jeden neuen Skill einzeln nachtragen muessen.

Stattdessen enthalten sie:

- Kategorien
- Definitionen
- Regeln
- typische Unterschiede
- Antwortmuster

### 2. Statisch erklaerend, nicht dynamisch inventarisierend

MD darf enthalten:

- `Runtime-Skills sind installierbare Skills in der Skill-Registry`
- `Draft-Skills sind noch nicht aktive Skills`
- `Built-in Tools sind keine installierten Skills`

MD darf nicht enthalten:

- konkrete Counts
- aktuelle Namenslisten
- Installationsstatus einzelner Skills

### 3. Nur als Zusatzkontext, nie als einzige Wahrheit

Antworten auf Skill-Fragen sollen immer:

- zunaechst strukturierte Wahrheit nutzen
- dann mit MD-Leitplanken semantisch sauber einordnen

---

## Vorschlag fuer die Struktur

Neuer Ordner:

```text
intelligence_modules/skill_addons/
  README.md
  ADDON_SPEC.md
  taxonomy/
    00-overview.md
    10-runtime-skills.md
    20-drafts.md
    30-tools-vs-skills.md
    40-session-skills.md
    50-answering-rules.md
```

### Inhalt der Dateien

`00-overview.md`
- Was ist ein Skill in TRION?
- Was sind die Hauptkategorien?

`10-runtime-skills.md`
- installierte Runtime-Skills
- Registry-/Skill-Server als Wahrheitsquelle

`20-drafts.md`
- was sind Drafts?
- warum zaehlen sie nicht als aktive Skills?

`30-tools-vs-skills.md`
- Unterschied zwischen nativen Tools/MCP-Tools und Skills
- warum `list_skills` nicht die komplette Faehigkeitenwelt abdeckt

`40-session-skills.md`
- Session-/Codex-Skills als separate Ebene
- nicht identisch mit der TRION Runtime

`50-answering-rules.md`
- Wie auf Fragen nach Skills/Faehigkeiten geantwortet werden soll
- Prioritaetsregeln fuer Formulierungen

---

## Loader-/Retrieval-Modell

Analog zu `container_addons` sollte es einen kleinen Loader geben, z. B.:

- `load_skill_addon_context(query, tags, runtime_snapshot=...)`

Der Loader waehlt **nicht pro Skill**, sondern pro **Fragetyp/Kategorie** passende MD-Abschnitte aus.

Beispielhafte Tags:

- `skill_taxonomy`
- `runtime_skills`
- `draft_skills`
- `tools_vs_skills`
- `session_skills`
- `answering_rules`

### Retrieval-Ziel

Nicht:

- moeglichst viel Text

Sondern:

- 1-3 kleine, hochrelevante Leitplankenbloecke

---

## Integrationspunkte

## Block 1 - Skill-Fragen sauber erkennen

### Ziel

Skill-Fragen sollen nicht nur `list_skills` triggern, sondern auch semantisch klassifiziert werden.

### Beispiele

- `welche skills hast du?`
- `welche arten von skills gibt es?`
- `was ist der unterschied zwischen skill und tool?`
- `was fehlt dir an skills?`

### Aenderungen

- Thinking / Query-Policy:
  - neue semantische Skill-Fragetypen ergaenzen
  - z. B. `resolution_strategy=skill_catalog_context`

### Akzeptanzkriterium

Skill-Fragen werden nicht mehr nur als nacktes `list_skills` interpretiert.

---

## Block 2 - Skill-Addons Loader einfuehren

### Ziel

Semantische MD-Leitplanken fuer Skill-Fragen gezielt laden.

### Status

Umgesetzt als vorbereitender Retrieval-Baustein.

### Aenderungen

- neuer Ordner `intelligence_modules/skill_addons/`
- `README.md` und `ADDON_SPEC.md`
- Loader-Modul analog zu `container_addons`

### Akzeptanzkriterium

Der Orchestrator kann fuer Skill-Fragen relevanten Skill-Kategorienkontext nachladen.

---

## Block 3 - Strukturierte Runtime-Sicht von semantischer Skill-Sicht trennen

### Ziel

Antworten muessen klar zwischen Inventar und Begriffsschicht unterscheiden.

### Status

Teilweise umgesetzt:
- technisch ueber getrennten Runtime-Snapshot vs. `skill_addons`
- sprachlich ueber Output-/Grounding-Regeln

### Aenderungen

- `list_skills` bleibt Wahrheitsquelle fuer installierte Runtime-Skills
- TypedState bleibt kompakte Darstellung aktiver/draft Skills
- Skill-Addon-Kontext liefert nur Interpretation und Begriffsgrenzen

### Akzeptanzkriterium

Antworten wie:

- `Im Runtime-Skill-System sind aktuell 0 aktive Skills installiert.`
- `Das ist aber nicht identisch mit Built-in Tools oder Session-Skills.`

werden moeglich und natuerlich.

---

## Block 4 - Orchestrator-Injektion fuer Skill-Semantik

### Ziel

Skill-Addon-Kontext soll im normalen Chatpfad verfuegbar werden.

### Status

Umgesetzt.

### Aenderungen

- neuer Helper im Orchestrator, z. B.:
  - `_maybe_build_skill_semantic_context()`
- kombiniert:
  - Runtime-Snapshot (`list_skills` / `/v1/skills`)
  - Skill-Addon-Kontext

### Platz im Ablauf

Analog zur Container-Capability-Context-Injektion:

- vor Output
- mit Grounding-Evidence
- optional auch schon fuer Thinking/Control bei klaren Skill-Fragen

### Akzeptanzkriterium

Skill-Fragen koennen mit kleinem, semantisch sauberem Zusatzkontext beantwortet werden.

---

## Block 5 - Antwortregeln gegen semantischen Drift

### Ziel

Das Modell soll bei Skill-Fragen sauber formulieren.

### Status

Umgesetzt als erster Output-/Grounding-Schritt.

### MD-Leitregeln

- `list_skills` beschreibt nur installierte Runtime-Skills
- Built-in Tools nicht als installierte Skills darstellen
- Session-/Codex-Skills nur nennen, wenn die Quelle dafuer explizit vorhanden ist
- wenn mehrere Ebenen gemeint sein koennen, diese explizit unterscheiden

### Akzeptanzkriterium

Antworten auf `welche skills hast du?` oder `was fehlt dir an skills?` werden nicht mehr unsauber verallgemeinert.

---

## Block 6 - Tests

### Backend

- Test fuer Skill-Frage -> Strategy/Resolver statt nur `list_skills`
- Test fuer Loader-Auswahl der richtigen Skill-Addon-Dokumente
- Test, dass Runtime-Counts nicht aus MD stammen
- Test, dass Tools und Skills in Antworten nicht vermischt werden

### Output/Grounding

- Test fuer natuerliche Zusammenfassung von `list_skills` plus semantischer Einordnung
- Test fuer saubere Mehr-Ebenen-Antwort:
  - Runtime-Skills
  - Drafts
  - Built-in Tools

### Frontend

- optional spaeter:
  - `resolution_strategy=skill_catalog_context`
  - Strategy-/Summary-Sichtbarkeit

---

## Empfohlene Reihenfolge

1. `skill_addons` README + Spec + Taxonomie-MDs anlegen
   Status: erledigt
2. Loader fuer Skill-Addon-Kontext bauen
   Status: erledigt
3. Skill-Fragen semantisch klassifizieren
   Status: erledigt
4. Orchestrator-Injektion fuer Skill-Semantik einbauen
   Status: erledigt
5. Antwort-/Grounding-Regeln absichern
   Status: erledigt
6. danach erst tiefere Loop-/Refinement-Logik fuer Skill-Unsicherheiten
   Status: offen

---

## Wichtige Architekturentscheidung

### Option A - Skill-Addons als semantische Zusatzschicht

Vorteile:

- kein Drift bei Inventardaten
- analog zu `container_addons`
- gute Leitplanke fuer kleine Modelle

Nachteil:

- braucht weiterhin strukturierte Runtime-Quellen daneben

### Option B - Alles nur ueber strukturierte APIs loesen

Vorteile:

- eine Wahrheitsschicht fuer Live-Daten

Nachteile:

- semantische Begriffsgrenzen bleiben schwerer transportierbar
- Modell driftet eher bei offenen Fragen

### Empfehlung

Option A.

Nicht als Ersatz fuer Runtime-Wahrheit, sondern als **semantische Erklaerschicht ueber der Runtime-Wahrheit**.

---

## Erwarteter Nutzen

Wenn das sauber umgesetzt ist, kann TRION bei Skill-Fragen stabiler sagen:

- was im Runtime-Skill-System installiert ist
- was nur Draft ist
- was ein Tool statt eines Skills ist
- was Session-spezifisch ist
- und was ihm fuer einen bestimmten Use-Case eigentlich fehlen wuerde

Damit reduzieren wir nicht nur Skill-Drift, sondern bauen zugleich die Grundlage fuer spaetere Refinement-Loops auf einer sauberen Begriffsordnung.
