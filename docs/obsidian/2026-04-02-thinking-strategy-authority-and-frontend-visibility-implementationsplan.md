# Thinking als Strategie-Layer und Frontend-Sichtbarkeit - Implementationsplan

Erstellt am: 2026-04-02
Zuletzt aktualisiert: 2026-04-03
Status: **In Umsetzung**
Bezieht sich auf:

- [[2026-04-04-skill-catalog-offene-punkte-masterliste]] - zentraler Sammelpunkt fuer offene Punkte im Skill-Catalog-Strang
- [[2026-04-01-container-capability-followup-grounding-analyse]] - Root-Cause des Capability-Drifts
- [[2026-04-01-container-capability-followup-grounding-fix]] - erster Fix fuer den active-container capability path
- [[2026-04-02-skills-semantik-md-leitplanken-implementationsplan]] - Folgeplan fuer Skill-Taxonomie und semantische Leitplanken
- [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]] - Live-Follow-up fuer Output-Drift trotz korrekter Strategy
- [[2026-03-31-control-layer-audit]] - Control als bindende Policy-Autoritaet
- [[2026-04-01-control-authority-drift-container-clarification-implementationsplan]] - bestehende Control-/Routing-Drift-Fixes
- [[2026-03-29-sync-stream-pipeline-preamble-konsolidierung]] - bestehende Sync-/Stream-Konsolidierung

---

## Umsetzungsstand 2026-04-02

Block 1, Block 2, Block 4 und Block 5 sind jetzt als erster Schritt teilweise umgesetzt.

Konkrete Aenderungen:

- Thinking-Plan und Schema kennen jetzt explizit `resolution_strategy` plus `strategy_hints`:
  [thinking.py](<repo-root>/core/layers/thinking.py)
  und [orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
- Fuer aktive Container-Capability-Follow-ups gibt es jetzt auch ohne perfektes Modell-JSON eine deterministische Strategie-Inferenz:
  `resolution_strategy=active_container_capability`
  in [orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
- Control validiert diese Strategie jetzt explizit und schreibt sie als Autoritaet in den Turn-State:
  `_authoritative_resolution_strategy`
  in [control.py](<repo-root>/core/layers/control.py)
- Execution liest diese autoritative Strategie vor den Legacy-Toolheuristiken und erzwingt damit fuer den Containerfall den inspect-first Pfad:
  [orchestrator.py](<repo-root>/core/orchestrator.py)
- Stream-Contract fuer `thinking_stream` ist kompatibel gemacht:
  [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)
  emittiert jetzt sowohl `chunk` als auch `thinking_chunk`, damit Frontend und aeltere Consumer nicht auseinanderlaufen.
- `thinking_done` nutzt jetzt einen kompakteren UI-Payload mit stabilen Feldern wie:
  - `intent`
  - `memory_keys`
  - `needs_chat_history`
  - `is_fact_query`
  - `suggested_tools`
  - `response_length_hint`
  - `resolution_strategy`
  - `cached`
  - `skipped`
  - `source`
- Frontend liest fuer `thinking_stream` jetzt beide Feldvarianten:
  [chat.js](<repo-root>/adapters/Jarvis/static/js/chat.js)
- Die Layer-1-Box wird im Frontend nicht mehr irrefuehrend als `Control`, sondern als `Thinking` dargestellt:
  [chat.js](<repo-root>/adapters/Jarvis/static/js/chat.js)
- Die Thinking-Metaansicht wurde erweitert und legt den kompakten Prozesspfad sichtbar offen:
  [chat-thinking.js](<repo-root>/adapters/Jarvis/static/js/chat-thinking.js)
- Der Contract ist ueber gezielte Source-Tests abgesichert:
  [test_frontend_stream_activity_contract.py](<repo-root>/tests/unit/test_frontend_stream_activity_contract.py)
- Die Strategy-Authority ist ueber gezielte Unit-Tests abgesichert:
  [test_orchestrator_plan_schema_utils.py](<repo-root>/tests/unit/test_orchestrator_plan_schema_utils.py),
  [test_control_contract_flow.py](<repo-root>/tests/unit/test_control_contract_flow.py),
  [test_orchestrator_runtime_safeguards.py](<repo-root>/tests/unit/test_orchestrator_runtime_safeguards.py)
- Der rueckverlinkte Folgeplan fuer Skill-Stabilisierung hat jetzt seinen
  funktionsfaehigen ersten End-to-End-Unterbau fuer Block 1, 2, 4 und 5:
  [2026-04-02-skills-semantik-md-leitplanken-implementationsplan](<repo-root>/docs/obsidian/2026-04-02-skills-semantik-md-leitplanken-implementationsplan.md),
  [skill_addons README](<repo-root>/intelligence_modules/skill_addons/README.md),
  [skill_addons ADDON_SPEC](<repo-root>/intelligence_modules/skill_addons/ADDON_SPEC.md),
  [skill_addons loader](<repo-root>/intelligence_modules/skill_addons/loader.py),
  [thinking.py](<repo-root>/core/layers/thinking.py),
  [orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py),
  [orchestrator.py](<repo-root>/core/orchestrator.py),
  [output.py](<repo-root>/core/layers/output.py)
- Fuer diesen Skill-Folgepfad existiert jetzt auch ein konkreter Prompt-Flow-
  Regressionstest auf dem Kernpfad:
  [test_skill_catalog_prompt_flow.py](<repo-root>/tests/unit/test_skill_catalog_prompt_flow.py)

Noch offen:

- echte Strategy-Events wie `strategy_selected` oder `strategy_validated`
- Thinking-Prompt und Laufzeitheuristik weiter auf mehrere Strategy-Typen ausbauen, nicht nur `active_container_capability`
- den neuen Skill-Folgepfad `skill_catalog_context` bei Bedarf noch sichtbarer
  im Event-/Frontend-Trace machen
- Control-Entscheidung ggf. als eigener Event im Stream sichtbar machen statt nur im verifizierten Plan
- Execution fuer weitere Strategy-Klassen deterministisch hinterlegen
- fuer `skill_catalog_context` die letzte Output-Meile haerter binden, damit
  korrekte Strategy nicht mehr in allgemeine Faehigkeits-/Persona-Antworten
  driftet:
  [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]]

Damit ist Thinking nicht nur wieder sichtbar, sondern fuer den ersten echten Resolver-Fall auch wieder semantisch bindungsfaehig.
Die vorbereitete Skill-Schicht schliesst daran direkt an:
Thinking -> Strategy Proposal -> Control Validation -> Deterministic Execution -> semantische Skill-Leitplanken -> saubere Skill-Antworten.

---

## Anlass

Der erste Fix fuer aktive Container-Capability-Follow-ups hat den inhaltlichen Drift deutlich reduziert:

- `trion-home` wird nicht mehr als generische Alpine-/Shell-Sandbox beschrieben
- `container_inspect` und `container_addons` liefern bereits bessere Fakten

Trotzdem bleibt der Ablauf architektonisch noch unsauber:

- Thinking schlaegt fuer `was kannst du in diesem container alles tun?` weiter generische Low-Level-Tools vor
- dieselben generischen Tools koennen spaeter immer noch mitlaufen
- Grounding repariert dadurch weiterhin Symptome statt einen sauberen, kontrollierten Strategieweg auszufuehren

Parallel dazu wirkt Thinking im Frontend teilweise "weg", obwohl es backendseitig weiter laeuft.

---

## Kurzdiagnose

### 1. Thinking ist nicht weg, aber funktional degradiert

Thinking laeuft weiterhin und erzeugt den JSON-Plan mit:

- `intent`
- `memory_keys`
- `hallucination_risk`
- `suggested_tools`

Im aktuellen Design ist Thinking fuer viele Faelle aber zu stark auf konkrete Low-Level-Tools reduziert.
Dadurch wird es bei semantischen Fragen wie Container-Capabilities eher zu einem schwachen Tool-Hinweisgeber als zu einem echten Strategie-Layer.

### 2. Die eigentliche Autoritaetskette ist noch nicht sauber

Das Zielbild sollte sein:

1. Thinking liefert **Strategie-/Hypothesen-Vorschlaege**
2. Control erlaubt, verwirft oder reduziert diese Strategie
3. Execution setzt nur noch den von Control freigegebenen Pfad deterministisch um
4. Output formuliert aus der ausgefuehrten und grounded Evidence

Heute liegen Thinking-Vorschlag, Post-Control-Routing und Execution-Entscheidungen noch zu nah beieinander.

### 3. Thinking-Sichtbarkeit im Frontend driftet vom Backend-Contract

Die Frontend-Hooks fuer Thinking existieren weiterhin:

- [chat-thinking.js](<repo-root>/adapters/Jarvis/static/js/chat-thinking.js)
- [chat.js](<repo-root>/adapters/Jarvis/static/js/chat.js)
- [api.js](<repo-root>/adapters/Jarvis/static/js/api.js)

Der Laufzeitvertrag ist aber inkonsistent:

- Backend sendet `thinking_stream` aktuell mit Feld `thinking_chunk`:
  [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py#L324)
- Frontend liest bei `thinking_stream` aber `chunk.chunk`:
  [chat.js](<repo-root>/adapters/Jarvis/static/js/chat.js#L366)

Damit existiert sehr wahrscheinlich ein direkter Sichtbarkeits-Bug:

- Thinking-Events kommen an
- die Thinking-Box wird erstellt
- aber der eigentliche Stream-Text wird nicht korrekt eingetragen

Das erklaert, warum Thinking im Frontend "weg" wirken kann, obwohl es backendseitig laeuft.

---

## Zielbild

Thinking soll wieder explizit zwei Rollen haben:

### A. Semantischer Strategie-Layer

Thinking beschreibt fuer den Turn:

- was fuer eine Frage das ist
- welche Autoritaetsquelle primaer ist
- welche Strategy/Resolver-Klasse genutzt werden soll
- welche Low-Level-Validierung optional sinnvoll ist

Beispiel fuer den Containerfall:

- nicht primaer `container_stats`, `exec_in_container`
- sondern `resolution_strategy=active_container_capability`

### B. Sichtbare Laufzeitspur im Frontend

Thinking soll fuer Nutzer wieder nachvollziehbar sichtbar sein:

- live waehrend Layer 1 laeuft
- abgeschlossen mit kompaktem Summary
- getrennt von Sequential Thinking, aber im selben UI-Stil nachvollziehbar

Nicht Ziel:

- rohe Chain-of-Thought offenzulegen
- unkontrolliert alle internen Zwischenschritte zu streamen

Ziel ist eine **strukturierte, kontrollierte Prozesssicht**, nicht ein ungebremster Gedankendump.

---

## Umsetzungsblaecke

## Block 1 - Thinking von Low-Level-Tools auf Strategie-Vorschlaege umbauen

### Ziel

Thinking soll fuer semantische Faelle primaer **Strategien** statt konkrete Runtime-Tools vorschlagen.

### Aenderungen

- `core/layers/thinking.py`
  - neues Plan-Feld wie:
    - `resolution_strategy`
    - oder `strategy_hints`
  - fuer Capability-/Purpose-/Identity-Fragen ueber laufende Container:
    - `resolution_strategy=active_container_capability`
  - `suggested_tools` bleibt erlaubt, aber nur noch advisory

- `core/orchestrator_plan_schema_utils.py`
  - neues Feld in die Thinking-Plan-Schema-Normalisierung aufnehmen

- `core/orchestrator.py`
  - Resolver-Helfer einfuehren, der Strategien aus dem Plan liest und nicht nur Toolnamen

### Akzeptanzkriterium

Thinking fuer:

- `was kannst du in diesem container alles tun?`

liefert semantisch sichtbar einen Capability-Resolver-Hinweis statt nur:

- `container_stats`
- `exec_in_container`

---

## Block 2 - Control validiert Strategien, nicht nur Toolmengen

### Ziel

Control soll nicht nur eine Tool-Allowlist kontrollieren, sondern auch die **finale Ausfuehrungsstrategie**.

### Aenderungen

- `core/layers/control.py`
  - Strategie-Hinweise aus Thinking lesen
  - validieren, ob eine Strategie:
    - erlaubt
    - zu reduzieren
    - oder zu verwerfen ist
  - optional neues autoritatives Feld wie:
    - `_authoritative_resolution_strategy`

- `core/control_contract.py`
  - Strategy-Override/Approval als Teil des Turn-Contracts aufnehmen, falls noetig

### Beispiele

- Thinking: `resolution_strategy=active_container_capability`
- Control:
  - `allow`
  - `warn`
  - `routing_block`
  - oder reduzierte Strategie wie:
    - nur `container_inspect`
    - ohne Runtime-Exec

### Akzeptanzkriterium

Die finale Execution-Strategie fuer einen Turn ist danach nicht mehr implizit in verstreuten Toollisten versteckt, sondern explizit nachvollziehbar.

---

## Block 3 - Deterministische Execution aus Strategie statt Tool-Restmischung

### Ziel

Execution soll fuer semantische Resolver-Faelle deterministisch aus einer validierten Strategie erzeugt werden.

### Aenderungen

- `core/orchestrator.py`
  - `_resolve_execution_suggested_tools()` so erweitern, dass Strategie-Faelle vor generischen Tool-Fallbacks aufgeloest werden

- fuer `active_container_capability`:
  - deterministische Reihenfolge:
    1. aktiven Container aufloesen
    2. `container_inspect`
    3. `container_addons`
    4. optionale Runtime-Validierung nur wenn wirklich noetig

- generische Fallbacks wie
  - `container_stats`
  - `exec_in_container` mit Dummy-Command

  duerfen in diesem Pfad nicht mehr reflexartig mitlaufen

### Akzeptanzkriterium

Ein Capability-Turn fuehrt nicht mehr parallel sowohl:

- Strategy-Resolver
- als auch generische Legacy-Fallback-Tools

aus.

---

## Block 4 - Thinking-/Control-/Execution-Trace als first-class Event-Contract

### Ziel

Der Prozess soll im Frontend wieder sichtbar werden, aehnlich nachvollziehbar wie Sequential Thinking, aber kontrolliert und kompakt.

### Aenderungen

- neues Event-Modell fuer Layer 1 / 2 / Strategy:
  - `thinking_stream`
  - `thinking_done`
  - optional:
    - `strategy_selected`
    - `strategy_validated`
    - `strategy_rejected`
    - `execution_strategy`

- `core/orchestrator_stream_flow_utils.py`
  - Thinking- und Strategy-Events mit stabilem Schema emitten

- `adapters/Jarvis/static/js/api.js`
  - Event-Felder konsistent mappen

- `adapters/Jarvis/static/js/chat.js`
  - Thinking-/Strategy-Box sichtbar halten
  - Layer 1 und Sequential klar trennen

### Wichtiger bestehender Bug

Der aktuelle Event-Contract ist fuer `thinking_stream` inkonsistent:

- Backend:
  [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py#L324)
  sendet `thinking_chunk`

- Frontend:
  [chat.js](<repo-root>/adapters/Jarvis/static/js/chat.js#L371)
  liest `chunk.chunk`

Das muss als erster UI-Trace-Fix bereinigt werden.

### Akzeptanzkriterium

Thinking ist im Frontend wieder sichtbar als:

- Live-Layer-1-Analyse
- mit kompakter Summary
- ohne dass Nutzer auf Sequential Thinking angewiesen sind, um ueberhaupt einen Planpfad zu sehen

---

## Block 5 - Frontend-Darstellung angleichen an Sequential Thinking

### Ziel

Thinking soll aehnlich transparent wirken wie Sequential Thinking, aber nicht identisch.

### Aenderungen

- `adapters/Jarvis/static/js/chat-thinking.js`
  - Thinking-Meta erweitern:
    - `intent`
    - `memory_keys`
    - `is_fact_query`
    - `resolution_strategy`
    - `suggested_tools` nur als advisory
    - `hallucination_risk`

- `adapters/Jarvis/static/js/chat.js`
  - Thinking-Box nicht als "Control" labeln, wenn es eigentlich Layer 1 ist
  - klarere Trennung:
    - `Thinking`
    - `Control`
    - `Sequential`

- optional:
  - einheitliche Timeline-/Accordion-Darstellung fuer alle drei

### Akzeptanzkriterium

Ein Nutzer kann im UI unterscheiden:

- was Thinking vorgeschlagen hat
- was Control davon erlaubt hat
- was danach wirklich ausgefuehrt wurde

---

## Block 6 - Tests fuer Event-Contract und Strategy-Authority

### Ziel

Die neue Autoritaetskette und Frontend-Sichtbarkeit muessen als Contract abgesichert werden.

### Tests

- Backend
  - neuer Test fuer Strategy-Vorschlag im Thinking-Plan
  - neuer Test: Control validiert/ueberschreibt Strategy autoritativ
  - neuer Test: Execution folgt Strategy statt Legacy-Fallback-Tools

- Frontend
  - Contract-Test fuer `thinking_stream` Event-Feldnamen
  - Test fuer Rendering von Thinking-/Control-/Sequential-Boxen
  - Test, dass `resolution_strategy` sichtbar wird

### Akzeptanzkriterium

Thinking-Transparenz und Strategy-Authority koennen nicht mehr still regressieren.

---

## Empfohlene Reihenfolge

1. Block 4 - Event-Contract fuer Thinking im Stream sauberziehen
2. Block 5 - Frontend-Sichtbarkeit reparieren und angleichen
3. Block 1 - Thinking als Strategie-Layer erweitern
4. Block 2 - Control validiert Strategien
5. Block 3 - Execution deterministisch aus Strategie ableiten
6. Block 6 - Tests vervollstaendigen

Begruendung:

- zuerst Thinking wieder sichtbar machen, damit spaetere Architekturarbeit beobachtbar ist
- dann semantische Strategy-Authority aufbauen
- erst danach Legacy-Fallbacks komplett abschalten

---

## Offene Architekturentscheidung

Noch zu entscheiden ist, wie stark Thinking strukturierte Strategien ausdruecken soll:

### Option A - Neues Feld `resolution_strategy`

Vorteile:

- explizit
- gut testbar
- leicht fuer Control validierbar

Nachteil:

- neues Plan-Schema-Feld

### Option B - Strategy nur implizit ueber `intent` und `suggested_tools`

Vorteile:

- weniger Schema-Aenderung

Nachteile:

- wieder leichter Drift
- schwerer fuer Control deterministisch zu lesen

### Empfehlung

Option A:

- `resolution_strategy`
- optional `strategy_hints`

weil das die sauberste Trennung zwischen semantischem Plan und konkreter Tool-Ausfuehrung erlaubt.

---

## Erwartete Wirkung

Nach Umsetzung sollte fuer Capability-Fragen ueber laufende Container gelten:

- Thinking ist sichtbar und nachvollziehbar
- Thinking liefert eine semantische Strategie statt Tool-Raten
- Control bestaetigt oder reduziert diese Strategie
- Execution folgt dem validierten Strategieweg deterministisch
- Output braucht keine sichtbare Tail-Reparatur mehr fuer denselben Turn

Damit wird Thinking wieder eine echte, beobachtbare Schicht im System statt ein halb-verdeckter Vorfilter.
