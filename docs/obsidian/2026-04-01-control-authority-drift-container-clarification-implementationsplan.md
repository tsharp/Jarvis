# Control-Authority-Drift bei Container-Requests - Clarification-/Allowlist-Implementationsplan

Erstellt am: 2026-04-01
Zuletzt aktualisiert: 2026-04-01
Status: **Plan**
Bezieht sich auf:

- [[2026-04-01-control-authority-drift-container-clarification-implementationsanalyse]] - Architekturentscheidung und Root-Cause-Analyse
- [[2026-04-01-control-authority-drift-approved-fallback-container-requests]] - bisherige DCS und frueherer Fixstand
- [[2026-03-30-drift-testsuite-implementationsplan]] - bestehende Drift-Invarianten
- [[2026-03-31-control-layer-audit]] - Sollbild: Control als bindende Policy-Autoritaet

---

## Ziel

Der Fix soll generisch fuer alle aktuellen und zukuenftigen Container-Requests sicherstellen:

- Control bleibt die einzige Policy-Autoritaet
- Clarification-/Discovery-/Approval-Zustaende fuehren nicht mehr in den generischen Evidence-Fallback
- der von Control korrigierte Toolsatz kann spaeter nicht mehr implizit reaktiviert werden
- Sync und Stream verhalten sich identisch

Kein Ziel dieses Plans:

- TRION-Home-Hardcode
- punktueller Hotfix nur fuer `TRION Home Workspace`

---

## Zielarchitektur in Kurzform

1. Control bestimmt den finalen erlaubten Tool-Satz.
2. Autoritative Control-Korrekturen ersetzen den Thinking-Toolsatz fuer den Turn.
3. Nachgelagerte Schichten duerfen Control nicht wieder erweitern.
4. `needs_clarification` ist ein legitimer interaktiver Laufzeitzustand und kein generischer Grounding-Failure.
5. UI und Observability zeigen denselben Contract-Zustand, den Backend und Runtime wirklich verwenden.

---

## Umsetzungsblaecke

## Block 1 - Runtime-/Grounding-Contract fuer Clarification festziehen

### Ziel

`needs_clarification` muss systemweit als nicht-technischer Interaktionszustand behandelt werden.

### Aenderungen

- `core/control_contract.py`
  - pruefen, ob `DoneReason.NEEDS_CLARIFICATION` eingefuehrt wird
  - `finalize_done_reason()` erweitern
  - alternativ oder zusaetzlich einen zentralen Helper fuer nicht-technische Interaktionszustaende schaffen

- `core/layers/output.py`
  - `_grounding_precheck()` um `needs_clarification`-Pass-Through erweitern
  - Clarification darf weder `missing_evidence_fallback` noch `tool_execution_failed_fallback` triggern
  - die Logik fuer nicht-technische Interaktionszustaende zentralisieren, statt Status einzeln verstreut zu behandeln

### Tests

- `tests/unit/test_output_grounding.py`
  - neuer Runtime-Test: `needs_clarification` fuehrt zu `mode="pass"`

- `tests/unit/test_drift_contracts.py`
  - neue Invariante: Clarification ist kein generischer Grounding-Fallback
  - neue Invariante: Clarification ist kein Tech-Failure

### Akzeptanzkriterium

Ein Turn mit:

- `suggested_tools=["request_container"]`
- grounding evidence `status="needs_clarification"`

endet nicht mehr im generischen Tool-Nachweis-Fallback.

---

## Block 2 - Autoritative Tool-Korrektur durch Control

### Ziel

Wenn Control einen Container-Turn von Start auf Discovery/Clarification/Approval umstellt, darf der alte Action-Toolsatz nicht parallel weiterleben.

### Aenderungen

- `core/layers/control.py`
  - `apply_corrections()` von blindem Merge auf autoritative Korrektur umstellen
  - empfohlen:
    - explizites Flag wie `suggested_tools_replace=True`
    - oder separates Feld wie `_authoritative_suggested_tools`

- Clarification-/No-Match-/vergleichbare Policy-Korrekturen muessen den Thinking-Satz ersetzen, nicht erweitern

### Tests

- neuer Test in `tests/unit/test_drift_contracts.py`
  - wenn Control `blueprint_list` fuer den Turn setzt, bleibt `request_container` nicht parallel im finalen Toolsatz

- ggf. gezielter Test in `tests/unit/test_control_contract_flow.py`
  - autoritative Tool-Korrektur ersetzt statt merged

### Akzeptanzkriterium

Nach Control-Korrektur fuer Discovery/Clarification enthaelt der finale Turn-Toolsatz nicht mehr gleichzeitig:

- `blueprint_list`
- `request_container`

es sei denn, Control erlaubt das explizit selbst.

---

## Block 3 - Re-Expansion der Allowlist in Sync und Stream entfernen

### Ziel

Reconciled `tools_allowed` aus Control darf spaeter nicht mehr durch `decide_tools()` aufgeweicht werden.

### Aenderungen

- `core/orchestrator_stream_flow_utils.py`
  - `control_decision = control_decision.with_tools_allowed(_control_tool_decisions.keys())` ersetzen

- `core/orchestrator_sync_flow_utils.py`
  - denselben Override entfernen bzw. auf eine sichere Schnittmengenlogik umstellen

- Regel:
  - `decide_tools()` liefert nur noch konkrete Tool-Args
  - niemals eine implizite neue Autoritaet ueber den finalen Tool-Satz
  - eine leere `decide_tools()`-Antwort darf die bestehende Allowlist nicht loeschen

### Tests

- neuer Test in `tests/unit/test_drift_contracts.py`
  - leeres `decide_tools()` loescht keine reconciled Allowlist

- ggf. gezielte Unit-Tests fuer Sync-/Stream-Paritaet

### Akzeptanzkriterium

Wenn Control nach Reconcile nur noch `blueprint_list` erlaubt, dann darf spaeter:

- ein leerer oder anderer `decide_tools()`-Output

`request_container` nicht wieder erlauben.

---

## Block 4 - Execution-Resolver auf Control ausrichten

### Ziel

`_resolve_execution_suggested_tools()` soll primaer dem finalen Control-Satz folgen und Thinking nur noch advisory behandeln.

### Aenderungen

- `core/orchestrator.py`
  - `_resolve_execution_suggested_tools()` so anpassen, dass es primaer auf `control_decision.tools_allowed` und/oder autoritative Control-Toolfelder reagiert
  - Thinking-Fallback nur dort nutzen, wo kein autoritativer Control-Satz vorliegt

- falls notwendig:
  - ein zentrales Feld fuer den finalen autoritativen Turn-Toolsatz einfuehren

### Tests

- neuer Test fuer Resolver-Verhalten:
  - wenn Control nur `blueprint_list` erlaubt, wird `request_container` nicht mehr aus Thinking nachgezogen

### Akzeptanzkriterium

Execution folgt fuer den Turn dem von Control autorisierten Satz und nicht einem aelteren Thinking-Restzustand.

---

## Block 5 - UI-/Observability-Paritaet

### Ziel

Frontend und Logs sollen denselben Contract-Zustand anzeigen wie das Backend wirklich verwendet.

### Aenderungen

- `core/orchestrator_stream_flow_utils.py`
  - Stream-Control-Event um mindestens erweitern:
    - `decision_class`
    - `reason`
    - `warnings`
    - `tools_allowed`

- `adapters/Jarvis/static/js/chat-thinking.js`
  - bestehende `decision_class`-Logik weiter nutzen
  - sicherstellen, dass Stream-Daten vollstaendig verarbeitet werden

### Tests

- neue Frontend-/Contract-Tests falls passend
  - Control-Event transportiert `decision_class`

### Akzeptanzkriterium

Ein Turn mit Clarification-/Warn-/Routing-Zustand wird im UI nicht mehr irrefuehrend als schlicht `Approved` dargestellt.

---

## Empfohlene Reihenfolge der Implementierung

1. Block 1 - Clarification als Runtime-/Grounding-Contract
2. Block 2 - autoritative Tool-Korrektur in Control
3. Block 3 - Allowlist-Re-Expansion entfernen
4. Block 4 - Resolver an Control binden
5. Block 5 - UI-/Observability-Paritaet

Begruendung:

- Block 1 beseitigt den sichtbaren Endfehler
- Block 2 und 3 beseitigen die strukturellen Schattenautoritaeten
- Block 4 macht die Architektur konsistent
- Block 5 verbessert Debugbarkeit und UX-Paritaet

---

## Regression- und Validationsmatrix

Nach Umsetzung muessen mindestens diese Faelle getestet werden:

1. Container-Suggest / Clarification
   - Rueckfrage statt generischem Evidence-Fallback

2. Container-No-Match
   - Discovery-/`blueprint_list`-Pfad ohne `request_container`-Leak

3. Container-Pending-Approval
   - kein generischer Fallback
   - deterministische Approval-Antwort bleibt intakt

4. Erfolgreicher Container-Start
   - bisherige Success-Pfade bleiben unveraendert

5. Echter technischer Fehler
   - weiterhin Tech-Failure, kein versehentlicher Pass-Through

6. Sync-/Stream-Paritaet
   - identisches Verhalten fuer denselben Input

7. UI-Paritaet
   - Stream-Control-Status entspricht Backend-Contract

---

## Offene Implementationsentscheidungen

Diese Punkte sollten beim Coding explizit entschieden und dann konsequent durchgezogen werden:

1. `DoneReason.NEEDS_CLARIFICATION` ja/nein
   - Tendenz: ja, wenn der Zustand systemweit sauber sichtbar sein soll

2. Mechanismus fuer autoritativen Tool-Satz
   - `suggested_tools_replace=True`
   - oder `_authoritative_suggested_tools`

3. Form der Allowlist-Stabilisierung
   - Override komplett entfernen
   - oder strikt als Schnittmenge definieren

Empfehlte Tendenz:

- eigener Clarification-DoneReason
- separates autoritatives Tool-Feld oder explizites Replace-Signal
- keine spaetere Allowlist-Re-Expansion mehr

---

## Nicht Teil dieses Plans

- TRION-Home-Fast-Path als eigener UX-/Optimization-Task
- semantische Router-Qualitaetsverbesserung fuer einzelne Blueprint-Namen
- neue Blueprint-Hardcodes

Diese Themen koennen spaeter folgen, sollten aber nicht mit dem Contract-Fix vermischt werden.

---

## Optionale Folgearbeit - `control_profiles`

Nach dem Contract-Fix kann eine eigene strukturierte Profil-Schicht fuer den Control-Layer sinnvoll sein.

### Ziel

Sonderregeln und Policy-Overlays fuer Containerklassen sollen kuenftig zentral im Control-Layer modellierbar sein, ohne die Logik dauerhaft als Hardcodes in `core/layers/control.py` wachsen zu lassen.

### Nicht-Ziel

- kein reines Markdown-/Prompt-System fuer Policy
- kein Ersatz fuer den aktuellen Contract-Fix

### Vorschlag

Neue Struktur, z.B.:

- `intelligence_modules/control_profiles/<profile>/manifest.yaml`
- optional:
  - `README.md`
  - `notes.md`

### Mögliche Inhalte

- `applies_to`
  - `blueprint_ids`
  - `container_tags`
  - `intent_patterns`
  - `tool_names`

- `policy`
  - `authoritative_tools`
  - `replace_suggested_tools`
  - `disallowed_tools`
  - `prefer_existing_container`
  - `interaction_mode`
  - `clarification_policy`
  - `approval_policy`
  - `status_pass_through`

- `priority`
- `enabled`
- `ui_hints`

### Integrationsidee

1. Loader fuer `control_profiles`
2. Matching gegen:
   - Container-/Blueprint-Metadaten
   - Intent-/Domain-Signale
   - Tool-Signale
3. Anwendung der passenden Policy-Overlays im Control-Layer
4. klares Prioritaets- und Konfliktmodell

### Empfohlene Reihenfolge dieser Folgearbeit

1. Contract-Fix aus diesem Plan abschliessen
2. Profil-Schema definieren
3. Loader + Matcher bauen
4. 1-2 echte Profile als Referenz einfuehren
5. Control-Hardcodes schrittweise in Profile migrieren

### Warum erst danach

Wenn `control_profiles` vor dem Contract-Fix kommt, baut es auf einen noch instabilen Autoritaetsvertrag auf.
Sinnvoll wird das System erst dann, wenn klar ist:

- Control bestimmt den finalen Tool-Satz
- Runtime und Output respektieren diesen Satz stabil

### Potenzieller Nutzen

- bessere Wartbarkeit
- saubere Stelle fuer Sonderregeln
- einfacheres Fine-Tuning neuer Containerklassen
- weniger Schattenlogik in Orchestrator-/Output-Pfaden
