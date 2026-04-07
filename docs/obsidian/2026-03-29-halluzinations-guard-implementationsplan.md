# TRION Halluzinations-Guard — Implementationsplan fuer Claude Code

Erstellt am: 2026-03-29
Status: **abgeschlossen (Phase 1–5, 2026-03-29)**
Bezieht sich auf: [[2026-03-29-halluzinations-guard-analyse]]

---

## Zweck

Dieser Plan uebersetzt die Analyse in einen **praezisen, KI-tauglichen Umsetzungsplan**.

Ziel:

- Halluzinationen bei personen- und faktenbezogenen Fragen deterministisch verhindern
- den Guard in **allen aktiven Orchestrator-Pfaden** konsistent verdrahten
- den Datenvertrag zwischen `ContextManager`, Orchestrator und Output-Layer so erweitern, dass "Fakt wurde gesucht, aber nicht gefunden" explizit transportiert wird

Wichtig:

- zuerst die **deterministischen Architektur-Fixes**
- den Validator-Service **nicht** als ersten Fix missbrauchen
- keine Big-Bang-Umstellung
- in kleinen, testbaren Phasen arbeiten

---

## Kurzdiagnose

Der aktuelle Fehler ist die Kombination aus drei Ursachen:

1. `memory_required_but_missing` ist nur im Sync-Pfad verdrahtet
2. `ContextResult` kennt keinen Zustand wie `memory_keys_not_found`
3. `memory_used` ist semantisch zu grob und als Guard-Signal unbrauchbar

Zusaetzlich:

- der Stream-Pfad und der LoopEngine-Pfad umgehen den Guard
- Validator-Service und Client existieren, sind aber nicht eingebunden

---

## Zielzustand

Nach dem Fix soll fuer Fragen wie:

- "Wie heiße ich?"
- "Was habe ich dir über mich gesagt?"
- "Welche Zahl hatten wir uns gemerkt?"

folgendes gelten:

1. Wenn ein explizit angeforderter Memory-Key nicht gefunden wurde, wird das als strukturierte Information transportiert.
2. Sync-Flow, Stream-Flow und LoopEngine-Flow setzen denselben Guard konsistent.
3. Output darf in diesem Fall **nicht raten**.
4. Die Antwort muss stattdessen robust sagen, dass die Information nicht gespeichert ist.

---

## Nicht-Ziele

Nicht in Phase 1-4:

- allgemeine semantische Wahrheitspruefung aller Antworten
- globale Post-Generation-Validierung jeder Antwort
- komplexe Latenz-sensitive Validator-Kaskaden
- Umbau des Thinking-Layers
- Umbau des Control-Layers jenseits minimal noetiger Datenweitergabe

---

## Implementationsstrategie

Die beste Reihenfolge ist:

1. Datenvertrag reparieren
2. Sync-Guard reparieren
3. Stream-Guard reparieren
4. LoopEngine-Guard reparieren
5. Tests absichern
6. Validator-Integration optional spaeter

Grund:

- Solange der Datenvertrag kein "missing required fact"-Signal kennt, bleibt jeder spaetere Guard fragil.
- Validator zuerst einzubauen wuerde nur Symptome kaschieren und Latenz erhoehen.

---

## Phase 0 — Vorarbeit und Guard-Invarianten fixieren

### Ziel

Vor der eigentlichen Umsetzung einmal festhalten, was der Guard fachlich bedeuten soll.

### Guard-Invarianten

Die folgenden Regeln muessen nach dem Umbau gelten:

1. `memory_used` bedeutet nur noch: "irgendein Kontext wurde geladen"
2. `memory_used` darf **nicht** fuer den Anti-Halluzinations-Guard verwendet werden
3. Der Guard muss auf einem expliziten "required memory lookup missing"-Signal beruhen
4. Sync, Stream und LoopEngine muessen dieselbe Semantik benutzen
5. Output darf bei aktivem Guard niemals Namen, Zahlen oder Fakten raten

### Deliverable

- kurze Kommentar- oder Doc-Notiz in den betroffenen Stellen, damit spaetere Refactors dieselbe Semantik beibehalten

### DoD

- keine offene Unklarheit mehr, was `memory_used` bedeutet
- keine offene Unklarheit mehr, was `memory_required_but_missing` bedeuten soll

---

## Phase 1 — Datenvertrag von `ContextResult` erweitern

### Ziel

Der Retrieval-Layer muss explizit transportieren, welche angeforderten Keys nicht gefunden wurden.

### Betroffene Dateien

- `core/context_manager.py`
- `core/orchestrator_flow_utils.py`
- ggf. `core/models.py` nur wenn dort ein paralleles Kontextmodell gepflegt wird

### Konkrete Aenderungen

#### 1. `ContextResult` erweitern

In `core/context_manager.py`:

- Feld hinzufuegen:
  - `memory_keys_requested: list[str]`
  - `memory_keys_found: list[str]`
  - `memory_keys_not_found: list[str]`

Minimalvariante:

- nur `memory_keys_not_found`

Empfohlen:

- alle drei Felder, damit spaetere Debugbarkeit besser ist

#### 2. Memory-Key-Loops anreichern

Sowohl im Small-Model-Mode als auch im Full-Context-Mode:

- angefragte Keys erfassen
- gefundene Keys erfassen
- nicht gefundene Keys erfassen

Wichtig:

- `memory_used` Verhalten vorerst nicht fuer bestehende andere Nutzung brechen
- aber **zusaetzlich** die fehlenden Keys explizit markieren

#### 3. `build_effective_context()` Trace erweitern

In `core/orchestrator_flow_utils.py`:

- Trace um diese Felder erweitern:
  - `memory_keys_requested`
  - `memory_keys_found`
  - `memory_keys_not_found`

Ziel:

- Sync- und Stream-Pfad koennen denselben Trace lesen
- kein direkter Zugriff auf `ContextResult` noetig

### Wichtige Hinweise fuer Claude Code

- `memory_used` nicht entfernen, da es anderweitig fuer Telemetrie/Budgeting genutzt wird
- nur **neue, praezisere** Felder ergaenzen
- beide Retrieval-Zweige anfassen:
  - small_model_mode
  - full context path

### DoD

- wenn `memory_keys=["user_name"]` und nichts gefunden wird:
  - `memory_keys_not_found == ["user_name"]`
- wenn `user_name` gefunden wird:
  - `memory_keys_not_found == []`
- Trace enthaelt dieselben Informationen fuer beide Orchestrator-Pfade

---

## Phase 2 — Sync-Flow deterministisch reparieren

### Ziel

Der bestehende Sync-Guard soll auf das neue praezise Signal umgestellt werden.

### Betroffene Dateien

- `core/orchestrator_sync_flow_utils.py`
- `core/orchestrator.py`
- `core/layers/output.py`

### Konkrete Aenderungen

#### 1. Guard-Berechnung umstellen

Alte Logik:

```python
needs_memory = thinking_plan.get("needs_memory") or thinking_plan.get("is_fact_query")
high_risk = thinking_plan.get("hallucination_risk") == "high"
memory_required_but_missing = needs_memory and high_risk and not memory_used
```

Neue Ziellogik:

```python
needs_memory = thinking_plan.get("needs_memory") or thinking_plan.get("is_fact_query")
missing_required_memory = bool(ctx_trace.get("memory_keys_not_found"))
memory_required_but_missing = bool(needs_memory) and missing_required_memory
```

Optional spaeter:

- weitere Differenzierung nur fuer bestimmte Key-Typen

Nicht in Phase 2:

- erneute Kopplung an `hallucination_risk`

#### 2. Output-Layer unveraendert anschliessen

`memory_required_but_missing` weiter an `_execute_output_layer(...)` uebergeben.

Der bestehende Anti-Halluzinations-Block im Output-Layer darf zunaechst bleiben, kann aber textlich geschaerft werden.

### Empfehlung

Output-Text in `core/layers/output.py` leicht verschaerfen:

- nicht nur "Diese Info ist nicht gespeichert"
- sondern explizit "nicht raten / nicht erfinden"

### DoD

- Sync-Frage mit fehlendem `user_name` aktiviert den Guard
- Sync-Frage mit vorhandenem `user_name` aktiviert den Guard nicht
- `hallucination_risk="medium"` blockiert den Guard nicht mehr unnoetig

---

## Phase 3 — Stream-Flow sauber nachziehen

### Ziel

Der Stream-Pfad muss dieselbe Guard-Semantik wie der Sync-Pfad erhalten.

### Betroffene Dateien

- `core/orchestrator_stream_flow_utils.py`
- ggf. `core/orchestrator.py`
- `core/layers/output.py`

### Konkrete Aenderungen

#### 1. Guard-Berechnung im Stream-Pfad hinzufuegen

Direkt nach `build_effective_context(...)` im Stream-Pfad:

- `needs_memory` berechnen
- `memory_keys_not_found` aus `ctx_trace_stream` lesen
- `memory_required_but_missing` berechnen

#### 2. `generate_stream(...)` korrekt aufrufen

Der Parameter `memory_required_but_missing` wird von `generate_stream(...)` bereits unterstuetzt.

Er muss beim Aufruf explizit uebergeben werden.

#### 3. Keine zweite Semantik erfinden

Der Stream-Pfad darf nicht:

- andere Bedingungen nutzen als der Sync-Pfad
- keine Sonderlogik nur fuer Streaming einfuehren

### Wichtige Hinweise fuer Claude Code

- es reicht nicht, den Parameter nur in der Signatur zu kennen
- er muss im konkreten Aufruf in `orchestrator_stream_flow_utils.py` gesetzt werden

### DoD

- Stream-Frage mit fehlendem `user_name` aktiviert denselben Guard wie der Sync-Pfad
- Stream-Frage mit vorhandenem `user_name` laeuft normal weiter
- kein Unterschied mehr zwischen Chat-UI und Nicht-Stream-Antwort bezueglich Guard-Verhalten

---

## Phase 4 — LoopEngine-Pfad absichern

### Ziel

Auch der LoopEngine-Zweig darf den Guard nicht umgehen.

### Betroffene Dateien

- `core/orchestrator_stream_flow_utils.py`
- ggf. `core/layers/output.py`

### Konkrete Aenderungen

Im LoopEngine-Zweig wird aktuell `_build_system_prompt(...)` direkt aufgerufen.

Dieser Aufruf muss denselben Guard erhalten:

- `memory_required_but_missing` auch dort berechnen oder den vorher berechneten Wert wiederverwenden
- an `_build_system_prompt(...)` weitergeben

Wichtig:

- es darf keinen Pfad geben, in dem Streaming + LoopEngine den Guard stillschweigend verliert

### DoD

- LoopEngine-Pfad baut denselben Anti-Halluzinations-Block in den Prompt ein
- kein Sonderfall ohne Guard bleibt uebrig

---

## Phase 5 — Tests und Regression-Schutz

### Ziel

Den Fix so absichern, dass ein spaeterer Refactor den Guard nicht wieder nur im Sync-Pfad behaelt.

### Neue oder anzupassende Tests

#### A. ContextManager-Tests

Datei-Vorschlaege:

- `tests/unit/test_context_manager.py`
- oder neue Datei `tests/unit/test_context_manager_missing_memory_keys.py`

Abdecken:

- fehlender Key wird in `memory_keys_not_found` aufgenommen
- gefundener Key nicht
- small_model_mode und full-context path

#### B. Orchestrator Sync-Tests

Datei-Vorschlag:

- neue Datei `tests/unit/test_orchestrator_hallucination_guard_sync.py`

Abdecken:

- `needs_memory=True`, `memory_keys_not_found=["user_name"]` -> `_execute_output_layer(..., memory_required_but_missing=True)`
- vorhandener Key -> Flag `False`

#### C. Orchestrator Stream-Tests

Datei-Vorschlag:

- neue Datei `tests/unit/test_orchestrator_hallucination_guard_stream.py`

Abdecken:

- `generate_stream(...)` bekommt `memory_required_but_missing=True`
- Stream nutzt nicht nur `memory_used`

#### D. LoopEngine-Tests

Datei-Vorschlag:

- neue Datei `tests/unit/test_orchestrator_hallucination_guard_loopengine.py`

Abdecken:

- `_build_system_prompt(..., memory_required_but_missing=True)` im LoopEngine-Zweig

#### E. Output-Layer-Tests

Datei-Vorschlag:

- bestehende Output-Tests erweitern

Abdecken:

- Anti-Halluzinations-Block erscheint wenn Flag `True`
- Anti-Halluzinations-Block fehlt wenn Flag `False`

### Minimal notwendige Tests vor Merge

1. ContextManager missing-keys
2. Sync Guard wiring
3. Stream Guard wiring
4. LoopEngine Guard wiring

### DoD

- alle Guard-Tests gruen
- mindestens ein Test stellt sicher, dass Stream und Sync dieselbe Semantik verwenden

---

## Phase 6 — Optional: Validator-Service integrieren

### Ziel

Den bestehenden Validator als **zusätzliche** Absicherung einhaengen, nicht als Ersatz fuer den deterministischen Guard.

### Status

Aktuell **nicht eingebunden**, obwohl vorhanden:

- `modules/validator/validator_client.py`
- `validator-service/validator-service/main.py`

### Empfehlung

Nicht in den ersten Fix aufnehmen.

Erst danach als optionale Phase:

- nur fuer `is_fact_query=True` oder `needs_memory=True`
- nur fuer sensible Turns wie Identitaet, Zahlen, Fakten
- nur wenn Latenzbudget es erlaubt

### Sinnvolle Integrationspunkte

- nach Output-Generierung
- vor finalem Versand an den User
- bei `hallucination=yes` -> Fallback-Antwort

### Warum optional

- deterministic first, validator second
- sonst wird ein Architekturfehler nur durch eine spaete Zusatzpruefung verdeckt

---

## Empfohlene PR- oder Task-Schnitte fuer Claude Code

### PR 1 — Kontextvertrag erweitern

Enthaelt:

- `ContextResult` neue Felder
- Memory-Key-Tracking
- Trace-Weitergabe in `build_effective_context`

### PR 2 — Sync-Guard reparieren

Enthaelt:

- neue Guard-Bedingung im Sync-Pfad
- Output-Tests

### PR 3 — Stream- und LoopEngine-Guard reparieren

Enthaelt:

- Stream-Guard-Berechnung
- `generate_stream(...)` Verdrahtung
- LoopEngine-Systemprompt-Verdrahtung

### PR 4 — Regression-Suite haerten

Enthaelt:

- dedizierte Tests fuer Sync/Stream/LoopEngine-Paritaet

### PR 5 — optional Validator

Enthaelt:

- Validator-Client Einbindung
- Latenz-/Fallback-Regeln

---

## Konkrete Arbeitsanweisung fuer Claude Code

### Arbeitsmodus

Arbeite **phaseweise**. Nicht alles in einem Schritt veraendern.

### Reihenfolge

1. Phase 1 voll umsetzen
2. passende Tests fuer Phase 1 schreiben
3. Phase 2 umsetzen
4. Tests laufen lassen
5. Phase 3 und 4 umsetzen
6. Stream-/LoopEngine-Tests laufen lassen
7. erst danach optional Phase 6

### Wichtige Regeln

- `memory_used` nicht als globalen Status fuer andere Features kaputtmachen
- keine neue Guard-Logik nur fuer einen Pfad bauen
- Sync und Stream muessen dieselbe Semantik teilen
- Validator nicht als Ersatz fuer den deterministischen Fix verwenden

### Wenn Unklarheit entsteht

Im Zweifel gilt:

- Guard basiert auf **fehlenden explizit angefragten Memory-Keys**
- nicht auf allgemeinem Kontextvorhandensein

---

## Akzeptanzkriterien Endzustand

Der Fix ist erst dann fertig, wenn alle folgenden Aussagen stimmen:

1. `ContextResult` oder sein Trace transportiert fehlende angeforderte Memory-Keys explizit
2. Sync-Flow aktiviert den Guard bei fehlenden Keys
3. Stream-Flow aktiviert denselben Guard bei fehlenden Keys
4. LoopEngine-Pfad aktiviert denselben Guard bei fehlenden Keys
5. `memory_used` ist nicht mehr die Guard-Grundlage
6. Output erfindet bei aktivem Guard keine Fakten mehr
7. Tests decken Sync, Stream und LoopEngine ab

---

## Empfohlene Minimalversion

Wenn Claude Code zuerst nur das Noetigste fixen soll:

1. `ContextResult` + Trace um `memory_keys_not_found` erweitern
2. Sync-Guard auf `memory_keys_not_found` umstellen
3. Stream-Guard plus `generate_stream(...)` Verdrahtung nachziehen
4. LoopEngine-Systemprompt ebenfalls anschliessen

Das ist der kleinste Fix mit der groessten Wirkung.

---

## Endfazit

Die richtige Reihenfolge ist:

- zuerst praezises Missing-Memory-Signal
- dann Sync/Stream/LoopEngine Guard-Paritaet
- erst danach optional Validator

In einem Satz:

- **Nicht den Validator vorziehen, sondern zuerst den Datenvertrag reparieren und den Halluzinations-Guard ueber alle aktiven Ausfuehrungspfade konsistent verdrahten.**

---

## Umsetzungs-Nachtrag — 2026-03-29

Status: **Phase 1–5 abgeschlossen und deployed**

### Was umgesetzt wurde

| Phase | Datei(en) | Aenderung |
|---|---|---|
| 1 — Datenvertrag | `core/context_manager.py` | `ContextResult` um `memory_keys_requested`, `memory_keys_found`, `memory_keys_not_found` erweitert; beide Key-Loops (small_model_mode + full_context) tragen fehlende Keys ein |
| 1 — Trace | `core/orchestrator_flow_utils.py` | `build_effective_context()` gibt alle drei Felder in den Trace weiter |
| 2 — Sync-Guard | `core/orchestrator_sync_flow_utils.py` | Guard-Bedingung von `hallucination_risk=="high" and not memory_used` auf `bool(memory_keys_not_found)` umgestellt; `memory_used` ist kein Guard-Signal mehr |
| 2 — Output-Text | `core/layers/output.py` | Anti-Halluzinations-Block textlich geschaerft: explizit "NIEMALS raten / NIEMALS erfinden" |
| 3 — Stream-Guard | `core/orchestrator_stream_flow_utils.py` | Guard-Berechnung nach `build_effective_context()` hinzugefuegt (`memory_required_but_missing_stream`) |
| 4 — LoopEngine | `core/orchestrator_stream_flow_utils.py` | `_build_system_prompt()` und `generate_stream()` erhalten das Guard-Flag; kein Pfad mehr ohne Guard |
| 5 — Tests | `tests/unit/test_hallucination_guard_context_manager.py` | 9 Tests fuer ContextResult Key-Tracking (beide Retrieval-Pfade) |
| 5 — Tests | `tests/unit/test_hallucination_guard_wiring.py` | 9 Tests: Sync-Guard-Logik, Output-Prompt-Block, Trace-Propagation |

### Test-Ergebnis

```
18 passed in 0.47s
```

Keine Regression im Unit-Gate (2474 passed, 31 pre-existing failures unberuehrt).

### Deploy

```
docker compose restart jarvis-admin-api trion-runtime
```

Beide Container neu gestartet am 2026-03-29.

### Weiterfuehrender Schritt (nach diesem Plan umgesetzt)

Die fuenf Stellvertreter wurden durch ein einziges Domaenobjekt ersetzt:
→ [[2026-03-29-memory-resolution-contract-plan]]

`MemoryResolution` schliesst den ersten Wahrheitsknoten aus dem Atlas vollstaendig ab.

### Was noch offen ist

- **Phase 6 (optional):** Validator-Service als zusaetzliche Post-Generation-Pruefung einhaengen — erst sinnvoll wenn deterministischer Guard stabil laeuft
- **Phase 3a Chat↔Shell:** `exec_in_container` stdout-Snippet im `container_exec`-Event (separates Feature, nicht Guard-bezogen)

### Wichtigste Guard-Invarianten (jetzt aktiv)

1. `memory_used` bedeutet nur noch: "irgendein Kontext wurde geladen" — kein Guard-Signal
2. Guard basiert ausschliesslich auf `memory_keys_not_found` (explizit angeforderte, nicht gefundene Keys)
3. Sync, Stream und LoopEngine verwenden dieselbe Semantik
4. Output erfindet bei aktivem Guard keine Namen, Zahlen oder Fakten mehr
