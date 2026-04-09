# Orchestrator-Architektur-Refactor-Plan

Erstellt am: 2026-04-07
Status: **In Arbeit**

Update 2026-04-09:

- ein weiterer reiner Routing-/Klassifikationsrestblock ist jetzt ebenfalls aus
  `core/orchestrator.py` herausgezogen nach:
  - `core/orchestrator_modules/policy/domain_container.py`
  - Host-Runtime-Lookup-Heuristik
  - Active-Container-/Inventory-/Blueprint-/Binding-/Request-Klassifikation
  - Skill-Catalog-Context-/Priority-Klassifikation
- `core/orchestrator.py` liegt lokal fuer diesen Stand jetzt bei `2870` statt
  `6161` Zeilen
- der Monolith behaelt fuer diesen Strang nur noch duenne Wrapper
- direkt gepinnt zusaetzlich ueber:
  - `tests/unit/test_orchestrator_domain_container_policy_utils.py` mit
    `17 passed`
  - `tests/unit/test_orchestrator_domain_routing_policy.py` mit `33 passed`
  - `tests/unit/test_orchestrator_runtime_safeguards.py` mit
    `89 passed, 14 warnings`

Update 2026-04-08:

- der Architektur-Audit liegt jetzt in
  [[2026-04-08-orchestrator-architecture-audit-first-extraction-cut]]
- der erste Extraktionsstrang ist lokal bereits in Phase `1a` bis `1c`
  umgesetzt:
  - Domain-Route-/Gate-Policy
  - Home-Info-/Home-Start-/Binding-/Capability-Tool-Shaping
  - Container-Query-Policy-Materialisierung
  - Skill-Catalog-nahe Strategy-/Trace-/Finalization-Helfer
- der naechste semantische Kontextblock ist lokal ebenfalls umgesetzt in:
  - `core/orchestrator_semantic_context_utils.py`
  - Skill-Katalog-/Addon-/Runtime-Snapshot-Kontext
  - Active-Container-Capability-Context
- der anschliessende Response-Guard-/Contract-Block ist lokal ebenfalls
  umgesetzt in:
  - `core/orchestrator_response_guard_utils.py`
  - Conversation-Consistency-Guard
  - Grounding-Auto-Recovery-Kleber
- der kleine Output-Glue-Block ist lokal ebenfalls umgesetzt in:
  - `core/orchestrator_output_glue_utils.py`
  - Tool-Result-Formatierung / Tool-Card / Evidence-Merge
  - `compute_ctx_mode` / Workspace-Observation-Extraktion
- der grosse Policy-Catalog-/Cron-/Policy-Runtime-Block ist lokal ebenfalls
  umgesetzt in:
  - `core/orchestrator_policy_catalog.py`
  - `core/orchestrator_cron_intent_utils.py`
  - `core/orchestrator_policy_runtime_utils.py`
  - Policy-Konstanten / Domain- und Tool-Marker
  - Cron-Intent-/Schedule-/Ack-Logik
  - Tone-/Query-Budget-/Domain-/Precontrol-Steuerungsblock
- der stateful Runtime-/Follow-up-Block ist lokal ebenfalls umgesetzt in:
  - `core/orchestrator_state_runtime_utils.py`
  - Container-State / Pending-Container-Resolution
  - Grounding-State / Carryover / usable-grounding
  - Follow-up-Tool-Reuse inklusive state-only Fallback
- der Context-/Workspace-/Retrieval-Block ist lokal ebenfalls umgesetzt in:
  - `core/orchestrator_context_workspace_utils.py`
  - Master-Workspace-Event-Summary / Persistenz-Kleber
  - Retrieval-Budget-Policy
  - Tool-Context-Clipping inklusive JSON-/Structured-Fail-Safes
- der Execution-Resolution-Block ist lokal ebenfalls umgesetzt in:
  - `core/orchestrator_execution_resolution_utils.py`
  - Control-Tool-Decision-Sammlung
  - finale Execution-Tool-Resolution / Follow-up-Reuse / Fallback-Kette
- der Postprocess-/Autosave-Block ist lokal ebenfalls umgesetzt in:
  - `core/orchestrator_postprocess_utils.py`
  - archive-embedding queue / fallback
  - fact-save / assistant-autosave / grounding-gates
- der Compact-Context-/Guardrail-Block ist lokal ebenfalls umgesetzt in:
  - `core/orchestrator_compact_context_utils.py`
  - `_get_compact_context` / fail-closed compact context
  - `_apply_effective_context_guardrail` / full-mode head-tail clipping
- der Container-Candidate-Evidence-Block ist lokal ebenfalls umgesetzt in:
  - `core/orchestrator_container_candidate_utils.py`
  - blueprint hint extraction aus recent history
  - `_container_resolution` / `_container_candidates` materialisierung
- der Interaction-/Response-Mode-Block ist lokal ebenfalls umgesetzt in:
  - `core/orchestrator_interaction_runtime_utils.py`
  - `home_read` directory recovery / skill-name extraction
  - think-tool filtering / response-mode policy
  - runtime output-model resolution / keyword fallback / trigger router
- der Workspace-/Container-Event-Runtime-Block ist lokal ebenfalls umgesetzt in:
  - `core/orchestrator_workspace_event_runtime_utils.py`
  - container-event-content build / emitter delegation fuer workspace saves
- der Interaction-/Routing-Restblock ist im selben Modul ebenfalls weiter
  verkleinert:
  - `core/orchestrator_interaction_runtime_utils.py`
  - explicit deep/think markers / tool-name extraction
  - home-info-vs-home-start detection / skill-router / blueprint-router glue
- der Pipeline-/Facade-Restblock ist lokal ebenfalls umgesetzt in:
  - `core/orchestrator_pipeline_facade_utils.py`
  - context-append / failure-compact / final-cap
  - tool-context success/failure helpers
  - skill-prefetch / container-verify / structure-summary / thinking execution
- der verbleibende Class-Body-Policy-Catalog ist lokal ebenfalls verschlankt:
  - Class-Attribute werden nach der Klassendefinition mechanisch gebunden
  - bestehende Class-Contracts bleiben dabei erhalten
- der API-/Lifecycle-Facade-Restblock ist lokal ebenfalls umgesetzt in:
  - `core/orchestrator_api_facade_utils.py`
  - pending confirmation / process / stream / chunked stream
  - control facade / save_memory / autonomous objective
- als geordneter Zwischenschritt liegt fuer diese Wrapper-/Facade-Module jetzt
  zusaetzlich ein echtes Unterpaket vor:
  - `core/orchestrator_modules/`
  - `api_facade.py`
  - `pipeline_facade.py`
  - `interaction_runtime.py`
  - `workspace_events.py`
  - zusaetzlich sind die groesseren Extraktionsmodule jetzt ebenfalls
    thematisch untergeordnet einsortiert:
    - `catalog.py`
    - `policy/`
    - `runtime/`
    - `context/`
    - `output/`
    - `execution/`
    - `postprocess.py`
  - die bisherigen Top-Level-Dateien bleiben vorerst als Compatibility-Shims
    stehen, weil `core/orchestrator.py` und mehrere Tests noch harte Datei-
    und Import-Contracts auf diesen Pfaden haben
- der Monolith ist in diesem Bereich jetzt deutlich stärker auf Wrapper und
  Aufrufkoordination reduziert
- `core/orchestrator.py` liegt lokal jetzt bei `2906` statt `6161` Zeilen
- grob gezaehlte Codezeilen liegen bei `2611` statt `5575`
- zuletzt verifiziert ueber:
  - Workspace-/Emitter-/Event-Drift-Suite mit `161 passed`
  - Interaction-/Routing-/Skill-Context-Suite mit `156 passed`
  - Pipeline-/Context-/Budget-/Runtime-Safeguard-Suite mit `215 passed, 5 skipped`
  - Class-Attr-/Import-/Runtime-Grundpfade mit `100 passed, 2 skipped`
  - API-/Control-/Runtime-Grundpfade mit `116 passed, 2 skipped`
  - Source-Layout-/Drift-/Skill-Context-/Package-Policy-Migrationssuite mit
    `167 passed`
  - gezielte Modul-Regressionssuite nach physischem Umzug unter
    `core/orchestrator_modules/` mit `59 passed, 2 skipped`
  - persistierte grosse Refactor-Regression via
    `scripts/ops/run_orchestrator_refactor_suite.sh refactor-regression` mit
    `226 passed, 2 skipped, 9 warnings`
  - Report-Pfad:
    `artifacts/test-reports/orchestrator/`
  - letzte Dateien:
    - `2026-04-08T23-48-09Z-refactor-regression.log`
    - `2026-04-08T23-48-09Z-refactor-regression.junit.xml`
    - `latest-refactor-regression.log`
    - `latest-refactor-regression.junit.xml`

## Ausgangslage

`core/orchestrator.py` ist inzwischen ein echter Wartungsblocker:

- zu viele Verantwortlichkeiten in einer Datei
- hoher Review- und Testaufwand pro Aenderung
- schlechte Parallelisierbarkeit fuer mehrere Arbeitsstraenge
- hohe Seiteneffektgefahr selbst bei kleinen Anpassungen

Nach dem aktuellen Produktisierungs- und Härtungsstand ist jetzt der richtige
Zeitpunkt fuer einen Architekturpfad:

- Live-Fixes und Git-Safety sind auf `main`
- die grossen Runtime-/Container-/Contract-Pfade sind nun nicht mehr nur lokal,
  sondern im Hauptrepo angekommen
- weitere Produktarbeit sollte nicht dauerhaft in denselben Monolithen
  hineingeschichtet werden

## Zielbild

Kein grosser Rewrite, sondern kontrollierte Extraktion in fachlich trennbare
Module.

Wichtige Leitplanken:

1. keine Verhaltensaenderung als Primärziel
2. kleine, testbare Schnitte statt Big-Bang-Refactor
3. erst Entscheidungslogik, dann stateful/runtime-nahe Pfade
4. jeder Schnitt bekommt vorher oder parallel Pinning-Regressionen

## Warum kein Big-Bang-Rewrite

Ein kompletter Neubau des Orchestrators wuerde aktuell mehr Risiko als Nutzen
bringen:

- zu viele lebende Produktpfade haengen daran
- Streaming-, Sync-, Control-, Grounding- und Containerpfade greifen ineinander
- die bestehenden Regressionen sind inzwischen wertvoll genug, dass man sie
  lieber zur Extraktion als zur Neuschreibung nutzt

Deshalb gilt:

- erst entflechten
- dann weiter verkleinern
- erst spaeter groessere Signatur- oder Ownership-Aenderungen

## Kandidaten fuer die Zielstruktur

Sinnvolle Extraktionsmodule:

- `orchestrator_domain_routing.py`
- `orchestrator_container_policy.py`
- `orchestrator_grounding.py`
- `orchestrator_workspace_events.py`
- `orchestrator_skill_catalog.py`
- `orchestrator_response_repair.py`

Diese Namen sind noch Arbeitstitel. Wichtig ist die fachliche Trennung, nicht
der exakte Dateiname.

## Empfohlene Extraktionsreihenfolge

### Phase 1: Fast-pure Entscheidungslogik

Zuerst rausziehen:

- Domain-/Policy-Gates
- Tool-Auswahl-Normalisierung
- Container-Query-/Routing-/Binding-/Home-Tool-Shaping
- Grounding-/Repair-Entscheidungslogik

Warum zuerst:

- deutlich besser testbar
- weniger versteckter Runtime-Zustand
- hoher Wartungsgewinn bei vergleichsweise kontrollierbarem Risiko

### Phase 2: Semantische Kontext- und Kataloglogik

Danach:

- Skill-Katalog-Pfade
- Addon-/Query-Class-bezogene Antwortlogik
- Antwortreparatur und sichtbarer Contract-Fallback

### Phase 3: Stateful/runtime-nahe Pfade

Spaeter:

- Conversation-/Binding-State
- Lifecycle-Hooks
- Streaming-/Sync-Verzweigung
- Tool-Ausfuehrungskoordination
- Workspace-Event-Persistenz

Diese Teile sind riskanter und sollten erst nach den reinen
Entscheidungsmodulen folgen.

## Bester erster Schnitt

Der erste Refactor-Schnitt sollte **nicht** bei `process_request(...)` beginnen.

Besserer Startpunkt:

- Container-/Domain-Policy im Orchestrator

Konkret:

- `_resolve_execution_suggested_tools`
- Container query policy override
- Domain route enforcement
- Home / request / binding tool shaping

Warum genau dieser Block:

- fachlich inzwischen deutlich klarer als noch frueher
- bereits gut mit Regressionen abgesichert
- relativ sauber gegen die restliche Antwortgenerierung abgrenzbar

## Pinning-Regressionen vor jedem Schnitt

Vor jedem Extraktionsschritt muessen die relevanten Verhaltenspfade mit
Pinning-Tests abgesichert bleiben.

Pflichtblöcke:

- `container_request`
- `TRION Home`
- `container_state_binding`
- `container_inventory`
- skill catalog
- workspace events
- output repair
- control authority

## Explizite Nicht-Ziele fuer den ersten Schritt

Nicht gleichzeitig mit dem Refactor mischen:

- neue Produktfeatures
- UI-Umbauten ohne Architekturbezug
- neue Toolfamilien
- neue Persistenzmodelle ausserhalb klar betroffener Extraktionspfade
- grossflaechige API-Signaturwechsel

## Praktischer naechster Schritt

Der frueher naechste Schritt ist inzwischen erledigt:

1. aktuelle Funktionscluster in `core/orchestrator.py` benannt
2. pure vs. stateful Bereiche markiert
3. erster sicherer Extraktionsschnitt festgelegt
4. benoetigte Pinning-Tests benannt

Stand jetzt:

1. Audit ist abgeschlossen
2. Phase `1a` bis `1c` fuer den ersten Policy-Strang sind lokal umgesetzt
3. der initiale Phase-2-Semantikblock ist lokal ebenfalls umgesetzt
4. der grosse Policy-Catalog-/Cron-/Policy-Runtime-Block ist lokal ebenfalls umgesetzt
5. der stateful Runtime-/Follow-up-Block ist lokal ebenfalls umgesetzt
6. der Context-/Workspace-/Retrieval-Block ist lokal ebenfalls umgesetzt
7. der Execution-Resolution-Block ist lokal ebenfalls umgesetzt
8. der Postprocess-/Autosave-Block ist lokal ebenfalls umgesetzt
9. der Compact-Context-/Guardrail-Block ist lokal ebenfalls umgesetzt
10. der Container-Candidate-Evidence-Block ist lokal ebenfalls umgesetzt
11. der Interaction-/Response-Mode-Block ist lokal ebenfalls umgesetzt
12. der Workspace-/Container-Event- und API-/Lifecycle-Facade-Schnitt ist lokal
    ebenfalls umgesetzt
13. zusaetzlich ist der verbleibende Domain-/Container-Policy-Block unter
    `core/orchestrator_modules/policy/domain_container.py` konsolidiert
14. `core/orchestrator.py` liegt lokal jetzt bei `2870` Zeilen
15. der lokale Clean-Install-/Release-Gate ist nach stack-seitigen Volume-
    Permission-Fixes fuer `jarvis-admin-api`, `storage-broker` und
    `trion_home_data` wieder gruen
16. der aktuelle persistierte Refactor-Regression-Stand ist:
   - `230 passed, 2 skipped, 9 warnings`
   - `artifacts/test-reports/orchestrator/2026-04-09T20-26-50Z-refactor-regression.log`
   - `artifacts/test-reports/orchestrator/2026-04-09T20-26-50Z-refactor-regression.junit.xml`
17. der naechste fachlich saubere Schritt ist jetzt:
   - Workspace-/Container-Event-Koordination
   - groessere Sync-/Stream-/Lifecycle-Koordination
