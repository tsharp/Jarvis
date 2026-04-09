# Orchestrator Architecture Audit: First Extraction Cut

Erstellt am: 2026-04-08
Status: **Audit abgeschlossen / Phase 1-2q lokal umgesetzt**

Inkrement 2026-04-09:

- ein weiterer reiner Domain-/Container-/Skill-Routing-Klassifikationsrest ist
  jetzt ebenfalls in `core/orchestrator_modules/policy/domain_container.py`
  gebuendelt
- konkret zusaetzlich ausgelagert:
  - Host-Runtime-Lookup-Heuristik
  - Active-Container-Capability-Klassifikation
  - Inventory-/Blueprint-/Binding-/Request-Klassifikation
  - Skill-Catalog-Context-/Priority-Klassifikation
- `core/orchestrator.py` liegt lokal fuer diesen Stand jetzt bei `2870` statt
  `6161` Zeilen
- verifiziert fuer diesen Nachschnitt ueber:
  - `17 passed` in `tests/unit/test_orchestrator_domain_container_policy_utils.py`
  - `33 passed` in `tests/unit/test_orchestrator_domain_routing_policy.py`
  - `89 passed, 14 warnings` in
    `tests/unit/test_orchestrator_runtime_safeguards.py`

Aktueller Umsetzungsstand 2026-04-08:

- der Audit selbst ist abgeschlossen
- der daraus abgeleitete erste Extraktionsschnitt ist lokal in Phase `1a` bis
  `1c` umgesetzt
- der naechste semantische Kontextblock ist lokal ebenfalls umgesetzt
- der anschliessende Response-Guard-/Contract-Block ist lokal ebenfalls
  umgesetzt
- der kleine Output-Glue-Block ist lokal ebenfalls umgesetzt
- der grosse Policy-Catalog-/Cron-/Policy-Runtime-Block ist lokal ebenfalls
  umgesetzt
- der stateful Runtime-/Follow-up-Block ist lokal ebenfalls umgesetzt
- der Context-/Workspace-/Retrieval-Block ist lokal ebenfalls umgesetzt
- der Execution-Resolution-Block ist lokal ebenfalls umgesetzt
- der Postprocess-/Autosave-Block ist lokal ebenfalls umgesetzt
- der Compact-Context-/Guardrail-Block ist lokal ebenfalls umgesetzt
- der Container-Candidate-Evidence-Block ist lokal ebenfalls umgesetzt
- der Interaction-/Response-Mode-Block ist lokal ebenfalls umgesetzt
- der Workspace-/Container-Event-Runtime-Block ist lokal ebenfalls umgesetzt
- der Interaction-/Routing-Restblock ist lokal ebenfalls umgesetzt
- der Pipeline-/Facade-Restblock ist lokal ebenfalls umgesetzt
- der verbleibende Class-Body-Policy-Catalog ist lokal ebenfalls verschlankt
- der API-/Lifecycle-Facade-Restblock ist lokal ebenfalls umgesetzt
- fuer die Wrapper-/Facade-Ordnung existiert jetzt zusaetzlich ein
  geordnetes Unterpaket `core/orchestrator_modules/`
- die Zielmodule sind aktuell fachlich unter `core/orchestrator_modules/`
  gruppiert:
  - `catalog.py`
  - `policy/domain_container.py`
  - `policy/cron_intent.py`
  - `policy/runtime.py`
  - `runtime/state.py`
  - `runtime/response_guard.py`
  - `context/semantic.py`
  - `context/workspace.py`
  - `context/compact.py`
  - `context/container_candidates.py`
  - `output/glue.py`
  - `execution/resolution.py`
  - `postprocess.py`
  - `api_facade.py`
  - `pipeline_facade.py`
  - `interaction_runtime.py`
  - `workspace_events.py`
- die bisherigen Top-Level-Dateien bleiben vorerst als Compatibility-Shims
  stehen, damit bestehende Imports und Testpfade stabil bleiben
- `core/orchestrator.py` liegt lokal jetzt bei `2906` statt `6161` Zeilen
- grob gezaehlte Codezeilen liegen bei `2611` statt `5575`
- verifiziert ueber die zuletzt gezielten Suites mit:
  - `161 passed` fuer Workspace-/Emitter-/Event-Drift-Pfade
  - `156 passed` fuer Interaction-/Routing-/Skill-Context-Pfade
  - `215 passed, 5 skipped` fuer Pipeline-/Context-/Budget-/Skill-Context-/Runtime-Safeguard-Pfade
  - `100 passed, 2 skipped` fuer Class-Attr-/Import-/Runtime-Grundpfade
  - `116 passed, 2 skipped` fuer API-/Control-/Runtime-Grundpfade
  - `167 passed` fuer Source-Layout-/Drift-/Skill-Context-/Package-Policy-Migrationspfade
  - `59 passed, 2 skipped` fuer die gezielte Modul-Regressionssuite nach
    dem physischen Umzug der grossen Extraktionsmodule unter
    `core/orchestrator_modules/`
  - `226 passed, 2 skipped, 9 warnings` fuer die grosse persistierte
    Refactor-Regression via
    `scripts/ops/run_orchestrator_refactor_suite.sh refactor-regression`

Persistente Test-Reports fuer diesen Pfad:

- Ordner: `artifacts/test-reports/orchestrator/`
- letzter Lauf:
  - `2026-04-08T23-48-09Z-refactor-regression.log`
  - `2026-04-08T23-48-09Z-refactor-regression.junit.xml`
- stabile Alias-Dateien:
  - `latest-refactor-regression.log`
  - `latest-refactor-regression.junit.xml`

Aktueller Paketstand innerhalb von `core/orchestrator_modules/`:

- `catalog.py`
- `policy/cron_intent.py`
- `policy/domain_container.py`
- `policy/runtime.py`
- `runtime/state.py`
- `runtime/response_guard.py`
- `context/semantic.py`
- `context/workspace.py`
- `context/compact.py`
- `context/container_candidates.py`
- `output/glue.py`
- `execution/resolution.py`
- `postprocess.py`
- `api_facade.py`
- `pipeline_facade.py`
- `interaction_runtime.py`
- `workspace_events.py`

## Ziel des Audits

Den ersten sicheren Extraktionsschnitt fuer `core/orchestrator.py` so konkret
festlegen, dass daraus direkt ein kleiner, regressionsarmer Codeschnitt
entstehen kann.

Der Schwerpunkt liegt bewusst **nicht** auf Runtime-/Streaming-/Execution-State,
sondern auf der heute bereits relativ gut abgrenzbaren Entscheidungslogik rund
um Domain- und Container-Policy.

## Aktueller Befund zu `core/orchestrator.py`

Stand des Audits zum Audit-Zeitpunkt:

- Datei groesse: `6161` Zeilen
- typischer Aenderungsdruck liegt gleichzeitig auf:
  - Domain-Routing
  - Container-Query-Klassen
  - Home-/Binding-/Inventory-Fast-Paths
  - Control-/Grounding-/Execution-Verknuepfung
- die Datei ist funktional nicht mehr "ein Orchestrator", sondern ein
  Sammelpunkt fuer mehrere Policy- und Runtime-Schichten

Das Problem ist weniger einzelne Komplexitaet als die **Mischung aus
Entscheidungslogik und Seiteneffekten** in derselben Datei.

## Funktionscluster im Monolithen

### 1. Pure bis fast-pure Entscheidungslogik

Relativ gute Extraktionskandidaten:

- Domain-Routing-Seed und Domain-Gate
- Container-Query-Klassifikation und Tool-Override
- TRION-Home-Start-Rewrite
- Skill-Katalog-Read-vs-Action-Entscheidung
- Query-Budget-Tool-Policy
- Host-Runtime-Fast-Path-Shaping

Merkmal:

- arbeitet vor allem auf `user_text`, `verified_plan`, `suggested_tools`
- benoetigt kaum I/O
- Seiteneffekte beschraenken sich meist auf plan-interne Metadaten

### 2. Semantische Kontextanreicherung

Mittleres Risiko:

- Skill-Katalog-Runtime-Snapshots
- Active-Container-Capability-Context
- Addon-/Grounding-Evidence-Anreicherung
- Output-Repair/Contract-Postchecks

Merkmal:

- fachlich trennbar, aber enger mit Prompt- und Grounding-Contracts gekoppelt

### 3. Stateful / runtime-nahe Pfade

Spaeter extrahieren:

- Tool-Execution sync/async
- Conversation-/Container-State
- Workspace-Event-Persistenz
- Streaming-/Chunking-/Lifecycle-Flows
- Recovery- und Verification-Pfade

Merkmal:

- viele Abhaengigkeiten auf Hub, Runtime, Persistenz und globale Stores

## Festgelegter erster Extraktionsschnitt

Der erste sichere Schnitt ist:

- **Domain- und Container-Policy-Shaping**

Konkret umfasst das:

- Domain-Route -> Seed-Tool
- Domain-Lock -> erlaubte Toolmenge
- Container-Query-Strategy -> erforderliche Toolmenge
- `request_container` -> `home_start` Rewrite fuer TRION Home
- Host-Runtime-Lookup -> `exec_in_container` Fast-Path
- Materialisierung von `_container_query_policy`

Warum genau dieser Block:

- hohe Wartungsdichte
- bereits stark regressionsgetrieben
- weitgehend datengetrieben statt runtime-getrieben
- wenige Abhaengigkeiten auf Tool-Hub oder Persistenz
- klare Inputs/Outputs:
  - Input: `user_text`, `verified_plan`, `suggested_tools`, optional Conversation-State
  - Output: angepasste `suggested_tools` plus Plan-Metadaten

## Warum dieser Schnitt sicherer ist als groessere Alternativen

Nicht zuerst extrahieren:

- `process_request(...)`
- Streaming-Verzweigungen
- Tool-Execution
- Workspace-Event-Emission
- Grounding-Reparatur

Grund:

- diese Bereiche koppeln bereits Routing, I/O, Persistenz und Antwortvertrag
  zugleich
- dort waere ein Fehler schwerer lokal zu isolieren
- dort hilft ein "mechanischer Move" deutlich weniger als bei Policy-Logik

## Resultierende Zielstruktur fuer Phase 1

Praktisch sinnvoll als erster Modulblock:

- `core/orchestrator_domain_container_policy_utils.py`

Fachlicher Inhalt dieses Moduls:

- Domain-Routing-Seed
- Domain-Gate-Filter
- Home-Container-Info-Override
- TRION-Home-Start-Rewrite
- Active-Container-Capability-Override
- Container-Query-Policy-Materialisierung
- Container-Query-Policy-Override
- effektive Resolution-Strategy-Aufloesung
- Read-only-Skill-Tool-Selektion
- Tool-Trace-/Finalization-Kleber fuer Skill-Catalog-Routing

Der Orchestrator selbst bleibt dabei zunaechst API-stabil:

- bestehende Methoden bleiben als duenne Wrapper erhalten
- Call-Sites muessen fuer Phase 1 nicht umgebaut werden

## Pure vs. stateful Grenzlinie

Fast-pure innerhalb des ersten Schnitts:

- Allowed-Tool-Berechnung
- Seed-Tool-Auswahl
- Tool-Rewrite fuer Home/Host-Runtime
- Query-Class -> Truth-Mode Mapping

Leicht stateful, aber noch beherrschbar:

- Entscheidung `container_list` vs. `container_inspect` fuer
  `container_state_binding`
- benoetigt nur einen kleinen Snapshot des Conversation-Container-State

Explizit ausserhalb des ersten Schnitts:

- State-Mutation nach Tool-Execution
- Container-Event-Persistenz
- Runtime-Verifikation
- direkte Tool-Calls

## Bereits vorhandene Pinning-Regressionen

Direkt relevant und schon im Repo vorhanden:

- `tests/unit/test_orchestrator_domain_routing_policy.py`
- `tests/unit/test_orchestrator_runtime_safeguards.py`
- `tests/unit/test_control_contract_flow.py`
- `tests/unit/test_output_grounding.py`
- `tests/drift/test_container_state_paths.py`
- `tests/drift/test_workspace_event_paths.py`

Besonders wichtige Verhaltensanker:

- Domain-Lock filtert unpassende Tools weg
- Host-Runtime-Requests kippen auf `exec_in_container`
- `TRION Home`-Start laeuft ueber `home_start`
- `container_inventory` bleibt auf `container_list`
- `container_state_binding` nutzt `container_inspect` nur bei aktivem Ziel
- `_container_query_policy` bleibt fuer den Output-/Grounding-Layer erhalten

## Fuer den ersten Schnitt neu gepinnt

Ergaenzt fuer die Extraktionsgrenze selbst:

- `tests/unit/test_orchestrator_domain_container_policy_utils.py`

Damit ist die Kernlogik des ersten Moduls nicht nur indirekt ueber den
Monolithen, sondern auch **isoliert** testbar.

Stand nach Phase 1b:

- angrenzende Home-/Capability-Overrides liegen jetzt ebenfalls in demselben
  Modulblock
- damit ist die komplette fachliche Kette
  `home info -> home start -> active container capability -> container query class`
  innerhalb eines gemeinsamen Policy-Strangs gebuendelt

Stand nach Phase 1c:

- auch der kleine Strategy-/Shaping-Kleber fuer
  - Resolution-Strategy
  - Read-only-Skill-Selektion
  - Tool-Name-Normalform
  - Execution-Trace/Finalization
  liegt jetzt ausserhalb des Monolithen
- dadurch ist der verbleibende Orchestrator-Anteil in diesem Bereich vor allem
  noch Wrapper- und Aufrufkoordination statt Policy-Implementation

## Erweiterung nach dem Audit: initialer Semantik-Block

Stand nach dem naechsten lokalen Extraktionsschnitt:

- die Skill-Katalog-/Addon-/Runtime-Snapshot-Kontextlogik liegt jetzt in
  `core/orchestrator_semantic_context_utils.py`
- darin gebuendelt:
  - Runtime-Snapshot-Parsing fuer `list_skills`
  - Registry-/Draft-Snapshot-Parsing fuer `list_draft_skills`
  - Skill-Runtime-/Registry-Zusammenfassungen fuer Prompt-Context
  - Addon-Tag-Ableitung aus `container_inspect`
  - Active-Container-Capability-Context
  - Skill-Semantic-Context inklusive Grounding-Evidence-Kleber
- der Orchestrator behaelt in diesem Bereich nur noch Wrapper und
  Aufrufkoordination
- zusaetzlich isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_semantic_context_utils.py`

## Erweiterung nach dem Audit: Context- und Container-Restbloeke

Stand nach dem naechsten lokalen Extraktionsschnitt:

- der Compact-Context-/Guardrail-Pfad liegt jetzt in
  `core/orchestrator_compact_context_utils.py`
- darin gebuendelt:
  - `_get_compact_context`
  - `_apply_effective_context_guardrail`
  - fail-closed Compact-Context-Rueckgabe bei Retrieval-/Build-Fehlern
  - Guardrail-Head/Tail-Clipping fuer ueberlange Full-Mode-Prompts
- der advisory Container-Candidate-Evidence-Pfad liegt jetzt in
  `core/orchestrator_container_candidate_utils.py`
- darin gebuendelt:
  - Blueprint-Hint-Extraktion aus recent chat history
  - Materialisierung von `_container_resolution`
  - Materialisierung von `_container_candidates`
  - fail-closed `resolver_error`-Abbildung fuer Blueprint-Router-Ausfaelle
- der Orchestrator behaelt in beiden Bereichen nur noch Wrapper und
  Aufrufkoordination
- zusaetzlich isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_compact_context_utils.py`
  - `tests/unit/test_orchestrator_container_candidate_utils.py`

## Erweiterung nach dem Audit: Interaction- und Response-Mode-Block

Stand nach dem naechsten lokalen Extraktionsschnitt:

- der Interaction-/Response-Mode-Pfad liegt jetzt in
  `core/orchestrator_interaction_runtime_utils.py`
- darin gebuendelt:
  - `home_read`-Directory-Recovery via Fast-Lane
  - Skill-Name-Sanitizing und Requested-Skill-Extraktion
  - Think-Tool-Filter und Tool-Selector-Filter
  - Requested-Response-Mode und Runtime-Output-Model-Resolution
  - Interactive-vs-Deep-Response-Mode-Policy
  - Keyword-Tool-Fallback fuer Storage/Skill/Container-Pfade
  - Skill-Trigger-Router
- `core/orchestrator.py` behaelt fuer diesen Strang nur noch Wrapper
- isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_interaction_runtime_utils.py`

## Erweiterung nach dem Audit: Workspace-/Container-Event-Runtime-Block

Stand nach dem naechsten lokalen Extraktionsschnitt:

- der Workspace-/Container-Event-Pfad liegt jetzt in
  `core/orchestrator_workspace_event_runtime_utils.py`
- darin gebuendelt:
  - Build-Pfad fuer `container_started`-/`container_exec`-Workspace-Events
  - `workspace_event_emitter`-Delegation fuer `_save_workspace_entry`
  - `workspace_event_emitter`-Delegation fuer `_save_container_event`
- `core/orchestrator.py` behaelt fuer diesen Strang nur noch Wrapper mit
  bewusst stehen gelassenen Emitter-Contract-Markern fuer Drift-Tests
- isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_workspace_event_runtime_utils.py`

## Erweiterung nach dem Audit: Interaction-/Routing-Restblock

Stand nach dem naechsten lokalen Extraktionsschnitt:

- `core/orchestrator_interaction_runtime_utils.py` umfasst jetzt zusaetzlich:
  - explizite Deep-/Think-Request-Erkennung
  - Tool-Namen-Extraktion
  - TRION-Home-Info-vs-Home-Start-Klassifikation
  - Skill-Router-Fail-Closed-Glue
  - Blueprint-Router-Fail-Closed-Glue
- damit liegt der user-text-nahe Intent-/Routing-Kleber fuer diesen Strang
  nicht mehr im Monolithen, sondern im bereits bestehenden Interaction-Modul
- `core/orchestrator.py` behaelt nur noch duenne Wrapper
- isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_interaction_runtime_utils.py`

## Erweiterung nach dem Audit: Pipeline-/Facade-Restblock

Stand nach dem naechsten lokalen Extraktionsschnitt:

- der Pipeline-/Facade-Helferblock liegt jetzt in
  `core/orchestrator_pipeline_facade_utils.py`
- darin gebuendelt:
  - zentrale Context-Mutation via `_append_context_block`
  - Failure-Compact-Build inklusive Single-Truth-Guard
  - finaler Small-Model-Cap
  - Tool-Context-Success-/Failure-Helfer
  - Skill-Prefetch-Facade
  - Container-Running-Verify
  - MCP-Structure-Summary-Build
  - Thinking-Layer-Execution-Logging
- `core/orchestrator.py` behaelt fuer diesen Strang nur noch Wrapper; bei
  `_maybe_prefetch_skills` bleiben die C6-/`self.context._get_skill_context`-
  Vertragsmarker bewusst im Wrapper stehen
- isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_pipeline_facade_utils.py`

## Erweiterung nach dem Audit: Class-Body-Policy-Catalog-Verschlankung

Stand nach dem naechsten lokalen Extraktionsschnitt:

- der grosse Klassen-Attributblock fuer Policy-/Marker-/Tool-Catalog-Konstanten
  liegt nicht mehr inline im Class-Body
- die Attribute werden jetzt nach der Klassendefinition mechanisch an
  `PipelineOrchestrator` gebunden
- dadurch bleiben bestehende Class-Attribute-Contracts erhalten, waehrend der
  sichtbare Monolith-Body weiter zusammenschrumpft
- verifiziert insbesondere ueber:
  - `tests/unit/test_orchestrator_tool_suppress_split.py`

## Erweiterung nach dem Audit: API-/Lifecycle-Facade-Restblock

Stand nach dem naechsten lokalen Extraktionsschnitt:

- der letzte API-/Lifecycle-Wrapping-Block liegt jetzt in
  `core/orchestrator_api_facade_utils.py`
- darin gebuendelt:
  - `_check_pending_confirmation`
  - `execute_autonomous_objective`
  - `process`
  - `process_stream_with_events`
  - `_process_chunked_stream`
  - `_execute_control_layer`
  - `_save_memory`
- `core/orchestrator.py` behaelt fuer diesen Strang nur noch die duennen
  Methodenkoepfe und die public API-Oberflaeche
- zusaetzlich wurde der mechanische Class-Catalog-Binder ebenfalls in dieses
  Modul gezogen
- fuer die eigentliche Ablage liegt derselbe Wrapper-Strang jetzt parallel
  geordnet unter `core/orchestrator_modules/`; die alten Top-Level-Dateien
  bleiben vorerst nur noch als Compatibility-Shims bestehen
- isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_api_facade_utils.py`

## Aktueller Resthebel

Nach Phase `2q` bleibt der naechste groessere Hebel jetzt eher bei den
verbliebenen Fassade-/Lifecycle-Restpfaden:

- die restliche Sync-/Stream-/Lifecycle-Aufrufkoordination
- gegebenenfalls die verbleibenden Public-Facade-Wrapper selbst, falls wir
  spaeter noch Richtung `pipeline_orchestrator.py` gehen wollen

Aktueller Monolith-Delta gegen `HEAD` vor dem Refactor-Strang:

- `core/orchestrator.py`: von `6161` auf `2906` Zeilen
- netto `-3255` Zeilen im Monolithen
- auf reiner Codezeilenbasis etwa von `5575` auf `2611`
  - netto also etwa `-2964` Codezeilen

## Erweiterung nach dem Semantik-Block: Response-Guard-/Contract-Kleber

Stand nach dem naechsten lokalen Extraktionsschnitt:

- die Conversation-Consistency- und Grounding-Auto-Recovery-Logik liegt jetzt
  in `core/orchestrator_response_guard_utils.py`
- darin gebuendelt:
  - Consistency-State-Read/Write mit TTL-/Pruning-Policy
  - Conversation-Consistency-Guard inklusive Grounding-Fallback
  - usable-grounding-nahe Auto-Recovery-Entscheidung ueber whitelisted
    Tool-Reuse
- der Orchestrator behaelt in diesem Bereich nur noch Wrapper und
  Callback-Wiring
- zusaetzlich isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_response_guard_utils.py`

Aktueller Monolith-Delta gegen `HEAD` vor dem Refactor-Strang:

- `core/orchestrator.py`: von `6161` auf `5180` Zeilen
- netto `-981` Zeilen im Monolithen
- auf reiner Codezeilenbasis etwa von `5575` auf `4677`
  - netto also etwa `-898` Codezeilen

## Erweiterung nach dem Response-Guard-Block: Output-Glue-Helfer

Stand nach dem naechsten lokalen Extraktionsschnitt:

- der kleine Output-Glue-Strang liegt jetzt in
  `core/orchestrator_output_glue_utils.py`
- darin gebuendelt:
  - Grounding-Evidence-Merge
  - Tool-Result-Formatierung fuer Fast-Lane- und MCP-Pfade
  - Tool-Result-Card-Bau inklusive Workspace-Event-Audit-Payload
  - `compute_ctx_mode`
  - Workspace-Observation-Extraktion
- der Orchestrator behaelt in diesem Bereich nur noch Wrapper
- zusaetzlich isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_output_glue_utils.py`

Aktueller Monolith-Delta gegen `HEAD` vor dem Refactor-Strang:

- `core/orchestrator.py`: von `6161` auf `5037` Zeilen
- netto `-1124` Zeilen im Monolithen
- auf reiner Codezeilenbasis etwa von `5575` auf `4558`
  - netto also etwa `-1017` Codezeilen

## Erweiterung nach dem Output-Glue-Block: Policy-Catalog / Cron-Intent / Policy-Runtime

Stand nach dem naechsten lokalen Extraktionsschnitt:

- der grosse Konstanten-/Marker-/Tool-Mapping-Block liegt jetzt in
  `core/orchestrator_policy_catalog.py`
- die cron-/intent-/tool-normalisierende Entscheidungslogik liegt jetzt in
  `core/orchestrator_cron_intent_utils.py`
- der Query-Budget-/Tone-/Domain-/Precontrol-Steuerungsblock liegt jetzt in
  `core/orchestrator_policy_runtime_utils.py`
- darin gebuendelt:
  - Tool-/Skill-Intent-Erkennung
  - Cron-Schedule-/Reminder-/Ack-Helfer
  - Tool-Normalisierung fuer Skill-/Home-/Cron-Pfade
  - Tone-/Query-Budget-/Domain-Klassifizierungswrapper
  - Query-Budget-Planmutation
  - Precontrol-Policy-Conflict-Resolution
  - Query-Budget-Tool-Policy und Dialogue-Control-Runtime-Kleber
- der Orchestrator behaelt in diesen Bereichen jetzt nur noch Wrapper und
  Aufrufkoordination
- zusaetzlich isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_cron_intent_utils.py`
  - `tests/unit/test_orchestrator_policy_runtime_utils.py`

Aktueller Monolith-Delta gegen `HEAD` vor dem Refactor-Strang:

- `core/orchestrator.py`: von `6161` auf `4263` Zeilen
- netto `-1898` Zeilen im Monolithen
- auf reiner Codezeilenbasis etwa von `5575` auf `3831`
  - netto also etwa `-1744` Codezeilen

## Naechster sinnvoller Schritt

Nach dem abgeschlossenen Policy-/Semantik-/Response-/Catalog-Strang sollte der
naechste Schritt **nicht** zurueck in gemischte Monolith-Glue-Logik kippen.

Sinnvolle Folgearbeit:

1. groessere stateful/runtime-nahe Pfade
2. Streaming-/Sync-/Lifecycle-/Execution-State weiterhin bewusst spaeter
3. Workspace-Event-/Persistenz- und Conversation-State-Schnitte weiterhin nur
   separat und regressionsgetrieben
4. weitere Glue-Moves nur noch dann, wenn sie eine klar erkennbare
   Modulgrenze statt kleinteiliger Zerfaserung bringen

## Konkretes Ergebnis des Audits

Der erste sichere Extraktionsschnitt ist fachlich und technisch bestaetigt und
bereits ueber seinen Folgeblock hinaus fortgefuehrt:

1. Domain-/Container-Policy ist klein genug fuer einen kontrollierten Move.
2. Der Schnitt kann ohne Signaturbruch im Orchestrator vorbereitet werden.
3. Die wichtigsten Produktpfade sind bereits durch Regressionen abgedeckt.
4. Die anschliessende semantische Kontextschicht liess sich auf derselben
   mechanischen Wrapper-Grenze ebenfalls auslagern.
5. Der anschliessende Response-Guard-/Contract-Kleber liess sich ebenfalls
   ohne Signaturbruch auf derselben Modulgrenze auslagern.
6. Auch die verbleibenden kleinen Output-Glue-Helfer liessen sich noch
   regressionsarm auslagern, ohne Source-Contracts zu verlieren.
7. Der naechste sinnvolle Schritt ist damit kein weiterer Plan, sondern die
   weitere Verkleinerung des Orchestrators entlang klarer Modulgrenzen.
8. Die groesste verbleibende strukturelle Entlastung liegt jetzt bei
   stateful Laufzeitpfaden wie Conversation-/Container-/Grounding-State und
   Follow-up-Tool-Reuse statt bei weiteren kleinen Glue-Helfern.

## Erweiterung nach dem Policy-Runtime-Block: Stateful Runtime / Follow-up

Stand nach dem naechsten lokalen Extraktionsschnitt:

- der stateful Runtime-/Follow-up-Block liegt jetzt in
  `core/orchestrator_state_runtime_utils.py`
- darin gebuendelt:
  - Container-State-Read/Write-Kleber
  - Pending-Container-ID-Resolution sync/async
  - Grounding-State-TTL-/Snapshot-Read
  - Grounding-State-Remember + Carryover-Injection
  - usable-grounding-Pruefung
  - Follow-up-Tool-Reuse inklusive state-only Fallback
- der Orchestrator behaelt in diesen Bereichen jetzt nur noch Wrapper und
  Runtime-Wiring
- zusaetzlich isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_state_runtime_utils.py`

Aktueller Monolith-Delta gegen `HEAD` vor dem Refactor-Strang:

- `core/orchestrator.py`: von `6161` auf `4194` Zeilen
- netto `-1967` Zeilen im Monolithen
- auf reiner Codezeilenbasis etwa von `5575` auf `3768`
  - netto also etwa `-1807` Codezeilen

Die groessten verbleibenden Entlastungshebel liegen jetzt eher bei:

- weiterer Lifecycle-/Execution-Koordination
- groesseren Sync-/Stream-Bridge-Pfaden
- Resten der Kontextmontage ausserhalb des jetzt ausgelagerten Clip-/Budget-Blocks

## Erweiterung nach dem Stateful-Block: Context / Workspace / Retrieval

Stand nach dem naechsten lokalen Extraktionsschnitt:

- der Context-/Workspace-/Retrieval-Block liegt jetzt in
  `core/orchestrator_context_workspace_utils.py`
- darin gebuendelt:
  - Master-Workspace-Event-Summary und Persistenz-Kleber
  - Retrieval-Budget-Policy
  - JSON-/Structured-Tool-Context-Clipping inklusive Failure-Marker-Erhalt
- der Orchestrator behaelt in diesen Bereichen jetzt nur noch duenne
  Entry-Points
- zusaetzlich isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_context_workspace_utils.py`

Aktueller Monolith-Delta gegen `HEAD` vor dem Refactor-Strang:

- `core/orchestrator.py`: von `6161` auf `3816` Zeilen
- netto `-2345` Zeilen im Monolithen
- auf reiner Codezeilenbasis etwa von `5575` auf `3421`
  - netto also etwa `-2154` Codezeilen

## Erweiterung nach dem Context-Block: Execution Resolution

Stand nach dem naechsten lokalen Extraktionsschnitt:

- der Tool-Resolution-Block liegt jetzt in
  `core/orchestrator_execution_resolution_utils.py`
- darin gebuendelt:
  - Control-Tool-Decision-Sammlung inklusive Gate-Override-Paritaet
  - finale Execution-Tool-Resolution mit:
    - authoritative Control-Fallbacks
    - Follow-up-Reuse
    - Query-Budget-/Domain-/Container-Policy-Kette
    - conversational tool suppression
    - keyword / skill-trigger fallback
    - host-runtime deterministic chain
- der Orchestrator behaelt in diesen Bereichen jetzt nur noch Wrapper und
  Callback-Wiring
- zusaetzlich isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_execution_resolution_utils.py`

Aktueller Monolith-Delta gegen `HEAD` vor dem Refactor-Strang:

- `core/orchestrator.py`: von `6161` auf `3634` Zeilen
- netto `-2527` Zeilen im Monolithen
- auf reiner Codezeilenbasis etwa von `5575` auf `3254`
  - netto also etwa `-2321` Codezeilen

## Erweiterung nach dem Execution-Resolution-Block: Postprocess / Autosave

Stand nach dem naechsten lokalen Extraktionsschnitt:

- der Postprocess-/Autosave-Block liegt jetzt in
  `core/orchestrator_postprocess_utils.py`
- darin gebuendelt:
  - durable archive-embedding queue / inline fallback
  - fact-save-Kleber
  - grounded assistant-autosave inklusive:
    - pending-intent gate
    - tool-failure / empty-answer gate
    - grounding-evidence gate
    - duplicate-window gate
- der Orchestrator behaelt auch hier nur noch Wrapper und Runtime-Wiring
- zusaetzlich isoliert gepinnt ueber:
  - `tests/unit/test_orchestrator_postprocess_utils.py`

Aktueller Monolith-Delta gegen `HEAD` vor dem Refactor-Strang:

- `core/orchestrator.py`: von `6161` auf `3546` Zeilen
- netto `-2615` Zeilen im Monolithen
- auf reiner Codezeilenbasis etwa von `5575` auf `3174`
  - netto also etwa `-2401` Codezeilen

## Update 2026-04-09: Clean-Install-Gate und weiterer Monolith-Schnitt

Stand nach dem naechsten lokalen Extraktions- und Ops-Haertungsschnitt:

- `core/orchestrator.py` liegt lokal jetzt bei `2870` Zeilen
- der verbleibende Domain-/Container-Policy-Block ist unter
  `core/orchestrator_modules/policy/domain_container.py` konsolidiert
- Admin-API und Storage-Broker starten stack-seitig kurz mit Root-Rechten,
  bereiten ihre Runtime-Volumes vor und droppen danach auf UID/GID `1000`
- die Ops-Skripte fuehren Admin-API-`docker exec`-Schreibpfade explizit als
  `1000:1000` aus, damit Restore-/Reset-Laeufe keine root-owned Runtime-Dateien
  erzeugen
- `scripts/ops/trion_release_clean.sh` wartet nach dem Service-Restart auf
  `/health` und `/api/runtime/digest-state`, bevor die Abschlussdiagnose startet

Verifikation:

- `bash scripts/ops/trion_release_clean.sh --yes --non-interactive`
  - Live Restore: `status=success`
  - Abschlussdiagnose: `Status: HEALTHY`, `PASS=30`
  - Report: `logs/live_restore_report_20260409-202618.json`
- `bash scripts/ops/run_orchestrator_refactor_suite.sh refactor-regression`
  - `230 passed, 2 skipped, 9 warnings`
  - Log: `artifacts/test-reports/orchestrator/2026-04-09T20-26-50Z-refactor-regression.log`
  - JUnit: `artifacts/test-reports/orchestrator/2026-04-09T20-26-50Z-refactor-regression.junit.xml`
