# Skill-Catalog Control-First Policy Contract - Implementationsplan

Erstellt am: 2026-04-04
Zuletzt aktualisiert: 2026-04-05
Status: **In Umsetzung**
Bezieht sich auf:

- [[2026-04-04-skill-catalog-offene-punkte-masterliste]] - zentraler Sammelpunkt fuer offene Punkte im Skill-Catalog-Strang
- [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]] - Live-Befunde und bereits verifizierte Rechecks
- [[2026-04-03-skill-catalog-restfehler-routing-und-output-implementationsplan]] - bisherige Routing-/Output-Restfehler
- [[2026-04-04-skill-catalog-draft-evidence-output-repair-gap]] - Null-Draft-Befund und aktuelle Positivfall-Luecke
- [[2026-04-02-skills-semantik-md-leitplanken-implementationsplan]] - semantische Skill-Leitplanken
- [[2026-03-31-control-layer-audit]] - Control als bindende Policy-Autoritaet

---

## Update 2026-04-05 - Hint-Kanonisierung und policy-treuer Follow-up-Output

Der Control-first-Contract-Pfad ist im aktuellen Live-Recheck weiter gehaertet:

- Thinking-/Plan-Drift bekommt fuer `skill_catalog_context` jetzt keine
  semantische Autoritaet mehr
- Roh-Hints werden nur noch als Debug-Signal mitgefuehrt; die finalen
  `strategy_hints` werden auf kanonische Skill-Catalog-Hints reduziert
- Drift-Begriffe wie `builtin_tools`, `system_layers` oder `wishlist`
  werden auf kanonische Semantik gemappt oder verworfen
- `list_draft_skills` wird fuer Runtime-plus-Wishlist-Faelle ohne explizites
  Draft-Signal aus `suggested_tools` entfernt

Der zuletzt gepruefte Live-Prompt

- `Welche Skills hast du aktuell und welche Skills wuerdest du dir als Naechstes wuenschen? ...`

lief damit jetzt sichtbar auf dem gewollten Contract:

- `strategy_hints`: nur kanonische Skill-Catalog-Hints
- `suggested_tools = ["list_skills"]`
- `final_execution_tools = ["list_skills"]`
- `skill_catalog_required_tools = ["list_skills"]`
- `skill_catalog_force_sections = ["Runtime-Skills", "Einordnung", "Wunsch-Skills"]`

Zusaetzlich ist der Output-Contract jetzt enger:

- der `Runtime-Skills`-Abschnitt darf keine Built-in Tools, allgemeinen
  Faehigkeiten, Drafts oder Wunsch-/Aktionsanteile enthalten
- wenn der Policy-Contract `Wunsch-Skills` fordert, nutzen Prompt und
  Safe-Fallback jetzt auch genau diese Ueberschrift statt generisch
  `Naechster Schritt`

Offener Rest:

- der aktuelle Live-Recheck endet noch mit
  `skill_catalog_postcheck = repaired:unverified_session_system_skills`
- damit ist der Contract-Pfad fuer diesen Fall sauber, der Rohoutput driftet
  intern aber noch kurz in unbelegte Session-/System-Skill-Erwaehnungen

Neu verifiziert:

- `pytest -q tests/unit/test_orchestrator_plan_schema_utils.py` -> `8 passed`
- `pytest -q tests/unit/test_output_tool_injection.py` -> `9 passed`
- `pytest -q tests/unit/test_output_grounding.py` -> `41 passed`
- `pytest -q tests/unit/test_skill_catalog_prompt_flow.py tests/unit/test_skill_catalog_semantic_gap_suite.py` -> `9 passed`

## Update 2026-04-04 - erster Implementationsschnitt

Der erste Codeschnitt fuer Block 1 ist jetzt umgesetzt.

Stand:

- direkt nach Control wird jetzt ein frueher `_skill_catalog_policy`-Block auf
  `verified_plan` materialisiert
- der Contract traegt aktuell mindestens:
  - `mode`
  - `required_tools`
  - `force_sections`
  - `draft_explanation_required`
  - `followup_split_required`
  - `allow_sequential`
- Sync-/Stream-Trace tragen `policy_mode`, `required_tools` und
  `force_sections` jetzt mit
- Output liest den Contract bereits als erste Leitplanke mit, statt nur implizit
  aus spaeten Hints zu arbeiten

Verifiziert:

- `pytest -q tests/unit/test_control_contract_flow.py`
- `pytest -q tests/unit/test_skill_catalog_prompt_flow.py`
- `pytest -q tests/unit/test_output_tool_injection.py`
- `pytest -q tests/unit/test_frontend_stream_activity_contract.py`

Wichtig:

- Das ist noch **nicht** der komplette Control-first-Umbau.
- Der Skill-Semantik-Resolver sitzt weiterhin spaet.
- Live-Rechecks fuer den neuen Contract-Schnitt stehen noch aus.

## Update 2026-04-04 - zweiter Implementationsschnitt

Der Skill-Semantik-Resolver ist jetzt an den Contract gebunden.

Stand:

- `_maybe_build_skill_semantic_context(...)` liest jetzt
  `_skill_catalog_policy`
- `required_tools` treiben den semantischen Read-only-Snapshot jetzt
  deterministisch
- bei Draft-fokussierten Faellen wird damit auch `list_draft_skills`
  direkt ueber den Contract in den Resolver gezogen
- `selected_hints` fuer `skill_addons` kommen jetzt ebenfalls aus dem Contract
  statt lose nur aus dem spaeten Plan-Zustand

Verifiziert:

- `pytest -q tests/unit/test_skill_catalog_prompt_flow.py`
- `pytest -q tests/unit/test_orchestrator_runtime_safeguards.py -k "skill_semantic_context or skill_catalog_context_hook"`
- `pytest -q tests/unit/test_control_contract_flow.py tests/unit/test_output_tool_injection.py`

Wichtig:

- Der Resolver sitzt weiterhin noch im spaeteren Ablaufabschnitt.
- Inhaltlich ist er jetzt aber bereits **contract-gesteuert** statt
  primär usertext-/hint-getrieben.
- Der naechste saubere Check ist damit ein Live-Recheck des neuen Pfads.

## Update 2026-04-04 - Gap-Suite nach Live-Drifts

Nach den Rechecks mit mehrdeutigen Skill-Prompts ist die neue Lage klarer:

- der fruehe Pfad aus Thinking, Precontrol, Control und fruehem
  `_skill_catalog_policy` ist fuer die geprueften Faelle der stabilste Teil
- die aktuellen Restfehler sitzen jetzt enger in Output-Semantik,
  Postcheck-Kriterien und der Breite der Contract-Ableitung

Bereits geschlossen:

- `tools_vs_skills`-Antworten mit freier Built-in-/Core-Capability-
  Selbstbeschreibung werden jetzt im Output-Semantik-Check erkannt und im
  Postcheck auf den sicheren Runtime-/Einordnungs-Fallback gezogen
- `inventory_read_only`-Antworten mit ungefragten Skill-Erstellungs-/
  Aktionsangeboten werden jetzt im Output-Semantik-Check erkannt und im
  Postcheck auf den sicheren Inventar-Fallback gezogen
- Draft-Befunde werden jetzt nur noch mit echter
  `list_draft_skills`-Evidence als verifiziert akzeptiert; sonst zieht der
  Postcheck auf explizite Nicht-Verifikation statt Registry-Ableitungen
- fuer den geprueften Follow-up-Fall fordert der Contract nicht mehr zu breit
  `list_draft_skills`; reine Runtime-plus-Wishlist-Faelle bleiben jetzt bei
  `required_tools = [list_skills]`

Diese Luecken sind jetzt explizit als bekannte Gaps in
[tests/unit/test_skill_catalog_semantic_gap_suite.py](<repo-root>/tests/unit/test_skill_catalog_semantic_gap_suite.py)
festgehalten.

Verifiziert:

- `pytest -q tests/unit/test_skill_catalog_semantic_gap_suite.py`
- aktueller Stand: `6 passed`

Einordnung:

- der Umbau weg von spaetem Hardprompting hin zu frueher Policy-Bindung bleibt
  richtig
- der naechste technische Fokus liegt jetzt aber nicht mehr auf noch haerteren
  Prompt-Regeln, sondern auf:
  - engerer Contract-Ableitung
  - staerkerem semantischen Output-Validator
  - saubererem `inventory_read_only`-Verhalten im Output

## Anlass

Die zuletzt geprueften Live-Faelle fuer `skill_catalog_context` laufen bereits
nahe am Zielbild:

- Strategy: `skill_catalog_context`
- Hints: passend zur Skill-Frage
- finale Tools: `list_draft_skills`, `list_skills`
- Sequential: aus
- Postcheck: `passed`

Der zentrale Architekturrestfehler ist damit nicht mehr primaer ein
Prompt-/Repair-Problem, sondern:

- das frueh korrekte Ergebnis wird noch nicht als **bindender Contract**
  durch die Pipeline getragen
- der eigentliche kombinierte Skill-Kontext aus Live-Fakten und
  `skill_addons` entsteht erst **nach** Control
- Output enthaelt daher noch mehr Verantwortung fuer Struktur,
  Guardrails und Korrektur, als eigentlich noetig sein sollte

Kurz:

- der vorgelagerte Pfad erkennt den Fall bereits gut
- der Zustand wird aber noch nicht frueh genug eingefroren

---

## Architektur-Befund

Aktueller Ist-Zustand:

1. Thinking klassifiziert die Anfrage als `skill_catalog_context`
2. Precontrol/Control haerten bereits Teile davon
3. der echte kombinierte Skill-Catalog-Kontext wird erst spaeter ueber
   `_maybe_build_skill_semantic_context(...)` aufgebaut
4. Output bekommt dadurch spaet sowohl Live-Fakten als auch semantische
   Leitplanken und muss daraus noch Struktur und Guardrails retten

Wichtige Folge:

- Control sieht aktuell vor allem **Plan-Signale**
- Output sieht spaeter die **kombinierte Skill-Semantik**

Das ist fuer den verifizierten Null-Draft-Fall bereits stabiler geworden,
bleibt aber architektonisch rueckwaertig:

- Prompt-/Postcheck-Haertung sitzt zu spaet
- Policy sitzt noch nicht hart genug vor dem semantischen Kontextaufbau

---

## Zielbild

Der Skill-Catalog-Pfad soll zu einem frueh gebundenen Policy-Fall werden.

Reihenfolge:

1. Thinking klassifiziert nur:
   - `resolution_strategy=skill_catalog_context`
   - passende `strategy_hints`
   - read-only Skill-Tools
2. Control friert das Ergebnis als **Skill-Catalog-Policy-Contract** ein
3. Ein deterministischer Resolver laedt anhand dieses Contracts:
   - Live-Fakten
   - semantische Guardrails aus `skill_addons`
4. Output rendert nur noch innerhalb dieses Contracts

Nicht Ziel:

- `skill_addons` als zweite Truth-Source fuer Inventar zu behandeln
- einen zweiten Thinking-Durchlauf nach Control einzufuehren
- alles ueber noch haerteres Prompting zu loesen

---

## Kernregel

Fuer `skill_catalog_context` gilt kuenftig:

- Live-Runtime/Registry/Tool-Evidence ist die Inventar-Wahrheit
- `skill_addons` liefern nur Begriffs- und Antwortregeln
- Control setzt frueh die harten Leitplanken
- Output ist Renderer und nicht primaere Rettungsschicht

---

## Implementationsbloecke

### Block 1 - Skill-Catalog-Policy-Contract nach Control materialisieren

Status:

- erster Schnitt umgesetzt am 2026-04-04

Ziel:

- das bereits erkannte `skill_catalog_context`-Ergebnis als bindenden
  Downstream-Contract auf `verified_plan` festschreiben

Vorschlag fuer einen neuen Block auf `verified_plan`:

```json
{
  "_skill_catalog_policy": {
    "mode": "inventory_read_only",
    "required_tools": ["list_draft_skills", "list_skills"],
    "force_sections": ["Runtime-Skills", "Einordnung"],
    "draft_explanation_required": true,
    "allow_sequential": false,
    "semantic_guardrails_only": true
  }
}
```

Arbeitspunkte:

- Policy nur fuer `skill_catalog_context` erzeugen
- read-only Inventarfall explizit markieren
- Pflicht-Tools und Pflicht-Abschnitte aus Strategy/Hints ableiten
- spaetere Output-/Trace-Pfade auf diesen Contract umstellen

Erreicht im ersten Schnitt:

- `_skill_catalog_policy` wird zentral nach Control materialisiert
- Output-/Trace-Pfade koennen den Contract jetzt lesen

Offen fuer Block 1:

- Contract noch staerker als harte Tool-/Resolver-Vorbedingung nutzen
- Live-Recheck des Contract-Pfads
- Contract-Ableitung fuer Follow-up-Faelle enger machen, damit
  `required_tools` nicht breiter sind als die spaetere Execution

Primaer relevante Stellen:

- [core/layers/control.py](<repo-root>/core/layers/control.py)
- [core/orchestrator.py](<repo-root>/core/orchestrator.py)
- [core/orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)
- [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)

### Block 2 - Skill-Semantik-Resolver von spaet nach frueh ziehen

Status:

- teilweise umgesetzt am 2026-04-04

Ziel:

- kombinierter Skill-Kontext soll nicht erst kurz vor Output entstehen

Arbeitspunkte:

- `_maybe_build_skill_semantic_context(...)` in einen frueheren,
  policy-getriebenen Resolver ueberfuehren
- Live-Snapshot und `skill_addons` weiterhin getrennt halten
- Resolver an den neuen `_skill_catalog_policy`-Block binden
- Ergebnis sowohl fuer Control-nahe Entscheidungen als auch spaeter fuer
  Output/Trace verfuegbar machen

Erreicht im aktuellen Schnitt:

- Resolver ist jetzt an `_skill_catalog_policy` gebunden
- `required_tools` und `selected_hints` kommen aus dem Contract
- `list_draft_skills` wird fuer Draft-Faelle deterministisch im Resolver
  ausgefuehrt

Offen fuer Block 2:

- Resolver im Ablauf weiter nach vorne ziehen
- Live-Recheck des contract-gesteuerten Resolver-Pfads
- fuer Output/Validator klarer markieren, welche Aussagen ohne explizite
  Tool-Evidence unzulaessig bleiben

Wichtig:

- `skill_addons` bleiben semantische Guardrails
- Live-Fakten bleiben bei `list_skills`, `list_draft_skills`, Registry

Primaer relevante Stellen:

- [core/orchestrator.py](<repo-root>/core/orchestrator.py)
- [intelligence_modules/skill_addons/loader.py](<repo-root>/intelligence_modules/skill_addons/loader.py)
- [core/orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)
- [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)

### Block 3 - Tool-/Section-Pflichten aus Policy statt aus spaetem Prompting ableiten

Ziel:

- Output soll nicht mehr primaer ueber Hardprompting wissen, was Pflicht ist

Arbeitspunkte:

- `required_tools` und `force_sections` aus `_skill_catalog_policy`
  auslesen
- `draft_explanation_required` aus Hints/Toollage ableiten und nicht nur
  im Prompt erraten
- `fact_then_followup` als strukturelle Policy in den Contract uebernehmen
- Prompt-Regeln nur noch als Guardrail behalten

Primaer relevante Stellen:

- [core/layers/output.py](<repo-root>/core/layers/output.py)
- [core/orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)

### Block 4 - Trace auf Contract, Resolver und finale Ausfuehrung ausrichten

Ziel:

- sichtbar machen, dass der Fall frueh gebunden wurde

Arbeitspunkte:

- Trace um `skill_catalog_policy_mode`, `required_tools`,
  `guardrail_docs` und `resolver_stage` erweitern
- sichtbar trennen zwischen:
  - Thinking-Klassifikation
  - Control-Policy
  - finaler Tool-Ausfuehrung
- `trace_final` auf Contract-Sicht erweitern

Primaer relevante Stellen:

- [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)
- [core/orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)
- [adapters/Jarvis/static/js/chat-thinking.js](<repo-root>/adapters/Jarvis/static/js/chat-thinking.js)

### Block 5 - Danach erst Positivfall und gezielter Prompt-Abbau

Ziel:

- erst den frueh gebundenen Pfad stabilisieren, dann Hardprompting selektiv
  reduzieren

Reihenfolge:

1. Positivfall mit echten Draft-Skills herstellen
2. denselben Contract-Pfad live pruefen
3. danach Prompt-Haertung nur dort zuruecknehmen, wo Contract + Resolver
   stabil genug sind

---

## Betroffene Dateien

Wahrscheinlich direkt:

- [core/layers/control.py](<repo-root>/core/layers/control.py)
- [core/orchestrator.py](<repo-root>/core/orchestrator.py)
- [core/orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)
- [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)
- [core/layers/output.py](<repo-root>/core/layers/output.py)

Wahrscheinlich mitziehend:

- [core/orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
- [intelligence_modules/skill_addons/loader.py](<repo-root>/intelligence_modules/skill_addons/loader.py)
- [adapters/Jarvis/static/js/chat-thinking.js](<repo-root>/adapters/Jarvis/static/js/chat-thinking.js)

Tests:

- [tests/unit/test_skill_catalog_prompt_flow.py](<repo-root>/tests/unit/test_skill_catalog_prompt_flow.py)
- [tests/unit/test_output_grounding.py](<repo-root>/tests/unit/test_output_grounding.py)
- [tests/unit/test_orchestrator_plan_schema_utils.py](<repo-root>/tests/unit/test_orchestrator_plan_schema_utils.py)
- [tests/unit/test_orchestrator_query_budget_policy.py](<repo-root>/tests/unit/test_orchestrator_query_budget_policy.py)
- [tests/unit/test_frontend_stream_activity_contract.py](<repo-root>/tests/unit/test_frontend_stream_activity_contract.py)

---

## Aufwandseinschaetzung

Einschaetzung:

- kein Komplettneubau
- grob ein **mittlerer Refactor**

Warum nicht klein:

- Sync und Stream muessen beide angepasst werden
- Policy, Resolver, Trace und Output muessen auf denselben Contract umgestellt
  werden

Warum nicht riesig:

- Read-only-Policy, Strategy-Authority und Tool-Trace existieren bereits
- der Skill-Semantik-Builder existiert bereits
- es geht mehr um frueheres Einfrieren und saubere Verkabelung als um neue
  Fachlogik von null

---

## Testplan

### Contract / Unit

- `skill_catalog_context` erzeugt `_skill_catalog_policy`
- `draft_skills`-Frage setzt `required_tools` korrekt auf
  `list_draft_skills`, `list_skills`
- `fact_then_followup` landet als strukturelle Policy im Contract
- Resolver laedt passende `skill_addons`, ohne Live-Wahrheit zu ersetzen
- Output liest Pflicht-Abschnitte aus Policy statt nur aus spaetem Prompt

### Live / UI

Pflichtprompts:

- `Welche Draft-Skills gibt es gerade? ... warum list_skills sie nicht anzeigt`
- `Welche Skills hast du aktuell und welche Skills wuerdest du dir als Naechstes wuenschen?`
- spaeter derselbe Draft-Prompt mit echten Draft-Skills

Erwartung:

- Strategy, Hints und finale Tools bleiben wie bisher korrekt
- Trace zeigt zusaetzlich den fruehen Contract
- Output bleibt bei `Postcheck: passed`
- Positivfall mit echten Drafts bleibt innerhalb desselben Contracts stabil

---

## Naechster konkreter Schritt

Zuerst nicht am Prompt weiterdrehen.

Sinnvollster erster Implementationsschnitt:

1. `_skill_catalog_policy` in Control/Orchestrator materialisieren
2. `_maybe_build_skill_semantic_context(...)` an diesen Contract binden
3. Output auf Contract-Felder statt auf implizite Spaet-Hinweise umstellen

Damit wird aus dem aktuell schon guten fruehen Befund ein bindender
Pipeline-Zustand.
