# Control-Authority-Drift bei Container-Requests

Erstellt am: 2026-04-01
Zuletzt aktualisiert: 2026-04-01
Status: **Fix umgesetzt**
Bezieht sich auf:

- [[2026-03-31-control-layer-audit]] — bestehender Audit zu Control-Drift
- [[2026-03-30-drift-testsuite-implementationsplan]] — Drift-Invarianten
- [[2026-03-22-container-commander-trion/15-TRION-Chatflow-Layer-3-Control]] — Sollbild: Control als bindende Policy-Autoritaet
- [[2026-03-22-container-commander-trion/16-TRION-Chatflow-Layer-4-Output-Grounding-and-Execution]] — nachgelagerte Runtime-/Output-Schicht
- [[2026-04-01-trion-home-container-addons]] — aktueller TRION-Home-Kontext

---

## Anlass

Konkreter Live-Befund aus dem Chat:

- User: `kannst du einmal den TRION home container starten?`
- Thinking schlug `request_container` vor
- UI zeigte `Control Layer: Approved`
- finale Modellantwort:

> Ich habe aktuell keinen verifizierten Tool-Nachweis fuer eine belastbare Faktenantwort. Bitte Tool-Abfrage erneut ausfuehren.

Dasselbe Verhalten trat auch bei:

- `starte einmal bitte: TRION Home Workspace`

auf.

---

## Kurzdiagnose

Der `Control Layer` ist praktisch noch nicht die einzige Wahrheit.

Nach `approved=True` greifen weiterhin mindestens zwei nachgelagerte Schatten-Autoritaeten:

1. Container-Routing / Blueprint-Gate
2. Output-Grounding / Evidence-Gate

Dadurch kann der sichtbare Zustand

- `Control Layer: Approved`

im selben Turn spaeter in

- `request_container` ist effektiv nicht ausfuehrbar
- keine erfolgreiche Tool-Evidence vorhanden
- generischer Grounding-Fallback

kippen.

---

## Beobachtete Ursache-Kette

### 1. Frontend zeigt nur das rohe `approved`

Das Chat-UI rendert aktuell nur:

- `approved ? "Approved" : "Rejected"`

Es zeigt **nicht**:

- `decision_class`
- `tools_allowed`
- `routing_block`
- `_blueprint_gate_blocked`

Folge:

- Das UI kann `Approved` anzeigen, obwohl der Request spaeter effektiv nicht mehr ausfuehrbar ist.

### 2. Reconcile kann `request_container` nachtraeglich entwerten

Im `control_contract` existiert bereits ein Reconcile fuer:

- `_blueprint_gate_blocked=True`
- gleichzeitig `approved=True`

Dann wird:

- `request_container` aus `tools_allowed` entfernt

oder, falls kein anderes sinnvolles Tool bleibt:

- zu `decision_class="routing_block"` degradiert.

Das ist richtig als Schutz, zeigt aber auch:

- `approved=True` aus dem UI ist nicht die letzte Wahrheit.

### 3. Der Sync-Executor codiert Routing-Block als technisches `unavailable`

Im `request_container`-Pfad wird bei:

- Blueprint-Gate preplanned
- JIT no match
- JIT suggest requires selection
- Router-Fehler

haeufig ein technischer Tool-Status geschrieben:

- `status="unavailable"`

Semantisch ist das problematisch:

- `unavailable` sieht aus wie Tech-Failure
- tatsaechlich ist es oft ein Routing-/Policy-/Selection-Zustand

### 4. Output-Grounding behandelt `unavailable` als fehlende oder fehlgeschlagene Tool-Evidence

Wenn:

- Tools vorgeschlagen oder benutzt wurden
- aber keine erfolgreiche extrahierbare Evidence vorliegt

dann greift der Grounding-Fallback.

Bei Statuswerten wie:

- `error`
- `skip`
- `partial`
- `unavailable`

kippt der Pfad in:

- `tool_execution_failed_fallback`

oder

- `missing_evidence_fallback`

Das erklaert exakt den sichtbaren Endtext.

---

## Warum `TRION Home` hier besonders auffaellt

Fuer `TRION Home` existiert bereits dokumentierter Reuse-/Fast-Path-Kontext:

- persistenter Home-Container
- Home-Container-Addons
- Host-/Runtime-Lookup

Aber der vorhandene Home-spezifische Harden-Pfad greift aktuell nur fuer:

- `is_fact_query=True`
- Home-Info-Fragen

Nicht aber robust fuer:

- `starte TRION Home`
- `starte TRION Home Workspace`

Dadurch landet der Intent weiter im generischen:

- `request_container`

statt in einem harten:

- Home-Start/Reuse-Fast-Path

Das ist konsistent mit der frueheren Session-Reuse-Doku:

- ein echter Orchestrator-Override fuer bestehende passende Container war dort noch als offener Phase-2-Punkt markiert.

---

## Architekturbruch in einem Satz

Der sichtbare Fehler ist nicht primär ein einzelner Tool-Bug, sondern ein Vertragsbruch:

- `Control approved`

ist im Live-System noch **kein stabiler Endzustand**, weil spaetere Schichten die praktische Ausfuehrbarkeit erneut umdeuten koennen.

---

## Bereits dokumentierte Drift-Indizien

Die bestehende Drift-Testsuite beschreibt den Fall bereits nahezu direkt:

- `approved=true + gate_blocked` ist illegal
- `status=unavailable` darf nicht automatisch den generischen Fallback ausloesen
- Routing-Block und Tech-Unavailable sind semantisch verschieden

Damit ist der Live-Befund keine neue Theorie, sondern eine bestaetigte Drift zwischen:

- Architekturvertrag
- Executor-Statusmodell
- UI-Anzeige
- Output-Grounding

---

## Wahrscheinlicher Ablauf im konkreten Chat

1. Thinking markiert den Request als Container-Start und schlaegt `request_container` vor.
2. Control gibt roh `approved=True`.
3. Nachgelagertes Blueprint-/Routing-Gate verhindert die echte Ausfuehrung oder entfernt `request_container` faktisch.
4. Das Frontend zeigt weiter nur `Approved`.
5. Es entsteht keine erfolgreiche Tool-Evidence.
6. Output-Grounding faellt auf den generischen Tool-Nachweis-/Evidence-Fallback zurueck.

---

## Umgesetzter Fix — 2026-04-01

### Geänderte Dateien

| Datei | Änderung |
|---|---|
| `core/control_contract.py` | `DoneReason.ROUTING_BLOCK` ergänzt; `finalize_done_reason()` priorisiert `routing_block` vor `unavailable` |
| `core/orchestrator_tool_execution_sync_utils.py` | 6 Policy/Routing-Block-Pfade von `status="unavailable"` auf `status="routing_block"` umgestellt (control_tool_not_allowed, skill_gate_blocked, blueprint_gate, JIT blocked, JIT suggest, JIT no match); tech-Fehler bleiben `unavailable`/`error` |
| `core/layers/output.py` | Neuer Guard: wenn alle fehlgeschlagenen Evidence-Items `routing_block` sind → `mode="pass"`, kein Fallback; `routing_block` aus `_build_tool_failure_fallback`-Set entfernt |
| `adapters/Jarvis/static/js/chat-thinking.js` | `finalizeControl()` nutzt `decision_class` statt rohes `approved`; zeigt `allow`, `warn`, `routing_block` (orange), `hard_block` mit eigenen Icons und Farben |
| `tests/unit/test_drift_contracts.py` | 5 neue Invarianten INV-15–17 (`TestRoutingBlockContract`); bestehenden `test_valid_done_reasons_are_technical` auf neuen Enum-Wert aktualisiert |

### Testergebnis

```
80 passed in 0.52s
```

### Warum generisch und nicht nur für TRION Home

Der Fix greift auf Contract-Ebene — nicht per Blueprint-Name oder Tool-Name.
Jeder zukünftige Blueprint profitiert automatisch, weil:
- `routing_block` ein eigener Statuswert im Enum ist
- Output-Grounding auf den Status reagiert, nicht auf den Kontext
- UI rendert `decision_class` vom Control Layer — unabhängig vom Request

### Nachträglich gefundener Root Cause — Stream-Pfad (2026-04-01)

Nach dem ersten Restart trat der Fehler weiterhin auf. Analyse der Logs zeigte:

```
[WARNING] [Orchestrator-Autosave] Skipped assistant autosave (grounding_missing_evidence)
```

**Ursache:** Zwei unabhängige Lücken im Stream-Pfad:

#### Lücke 1 — Stream-Pfad hatte dieselben `unavailable`-Stellen wie Sync-Pfad

`orchestrator_stream_flow_utils.py` ist der aktive Pfad für Streaming-Modelle (z.B. deepseek-v3.1:671b). Er hatte dieselben sechs `status="unavailable"` an den Routing-Block-Stellen — wurde beim ersten Fix übersehen.

→ Fix: alle sechs Stellen in `orchestrator_stream_flow_utils.py` ebenfalls auf `routing_block` umgestellt.

#### Lücke 2 — `_collect_grounding_evidence` las `tool_statuses` nie

`_collect_grounding_evidence` in `output.py` liest Evidence aus zwei Quellen:
- `grounding_evidence` aus `_execution_result.metadata` (explizit geschrieben)
- `carryover_grounding_evidence`

Im Stream-Pfad schreiben die Routing-Block-Paths jedoch **nur** in `execution_result_stream.tool_statuses` — nicht in `grounding_evidence_stream`. Damit war `routing_block` für den Grounding-Precheck unsichtbar, und der Fallback feuerte weiterhin.

→ Fix: `_collect_grounding_evidence` liest jetzt zusätzlich `_execution_result.tool_statuses` als Fallback — gilt für alle Pfade (Sync, Stream, LoopEngine).

### Gesamte geänderte Dateien (final)

| Datei | Änderung |
|---|---|
| `core/control_contract.py` | `DoneReason.ROUTING_BLOCK` + `finalize_done_reason()` |
| `core/orchestrator_tool_execution_sync_utils.py` | 6 Routing-Block-Pfade → `routing_block` |
| `core/orchestrator_stream_flow_utils.py` | 6 Routing-Block-Pfade → `routing_block` (nachträglich) |
| `core/layers/output.py` | `routing_block` Guard + `_collect_grounding_evidence` liest `tool_statuses` |
| `adapters/Jarvis/static/js/chat-thinking.js` | `decision_class` statt rohes `approved` |
| `tests/unit/test_drift_contracts.py` | INV-15–17 + bestehenden Test aktualisiert |

### Testergebnis (final)

```
80 passed in 0.49s
```

### Noch offen

- Fix 4 (TRION Home Fast-Path): `starte TRION Home` soll direkt in Home-Start/Reuse-Pfad landen statt generischem `request_container` → separater Task, braucht Blick in JIT-Router

---

## Relevante Codebereiche

- `adapters/Jarvis/static/js/chat-thinking.js`
- `core/control_contract.py`
- `core/orchestrator_tool_execution_sync_utils.py`
- `core/orchestrator_stream_flow_utils.py`
- `core/layers/output.py`
- `core/orchestrator.py`
- `core/orchestrator_precontrol_policy_utils.py`

---

## Prioritaet

**Hoch fuer UX und Architekturklarheit.**

Kein klassischer Crash, aber ein besonders schaedlicher Zustand:

- UI sagt `Approved`
- Runtime fuehrt nicht aus
- Output erklaert den echten Grund nicht

Das untergraebt Debugbarkeit und Vertrauen in die Policy-Kette.
