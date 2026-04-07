# TRION MemoryResolution — Implementationsplan

Erstellt am: 2026-03-29
Status: **abgeschlossen (2026-03-29)**
Bezieht sich auf:

- [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]]
- [[2026-03-29-halluzinations-guard-implementationsplan]]

---

## Ziel

Den ersten zentralen Wahrheitsknoten aus dem Atlas schliessen:

> *"aus needs_memory, memory_keys, memory_used, memory_required_but_missing einen klaren kleinen Vertrag machen"*

Heute gibt es **5 Stellvertreter fuer eine einzige Wahrheit**:

| Stellvertreter | Wo | Problem |
|---|---|---|
| `needs_memory` / `is_fact_query` | Thinking-Plan | semantische Absicht, kein Resultat |
| `memory_keys` | Thinking → Control → Flow | reine Key-Liste, kein Status |
| `memory_used` | `ContextResult` | zu grob — feuert auch fuer Laws, Tools, Container |
| `memory_keys_requested/found/not_found` | `ContextResult` (neu) | richtig, aber drei lose Felder |
| `memory_required_but_missing` | Sync + Stream separat berechnet | Endergebnis, 2x unabhaengig gerechnet |

Jeder neue Ausfuehrungspfad muss alle fuenf kennen und korrekt kombinieren.
Genau das hat zum urspruenglichen Halluzinations-Bug gefuehrt.

---

## Zielzustand

Ein einziges Objekt `MemoryResolution` wird **einmal** in `build_effective_context()` gebaut
und von dort unveraendert an alle Verbraucher weitergereicht.

```python
@dataclass
class MemoryResolution:
    requested_keys: List[str]   # welche Keys wurden angefragt
    found_keys: List[str]       # welche wurden gefunden
    missing_keys: List[str]     # welche wurden nicht gefunden
    required_missing: bool      # = needs_memory AND missing_keys vorhanden
```

Verbraucher bekommen nur noch `resolution.required_missing` — kein eigenes Nachrechnen mehr.

---

## Nicht-Ziele

- `memory_used` nicht entfernen — wird noch fuer Telemetrie / Budget genutzt
- kein Umbau von Thinking oder Control
- kein Umbau der MCP-Retrieval-Logik
- kein Zusammenlegen von Sync- und Stream-Flow

---

## Betroffene Stellen heute

### Berechnung (2x, unabhaengig)

| Datei | Zeile | Was |
|---|---|---|
| `core/orchestrator_sync_flow_utils.py` | ~622–626 | `needs_memory + missing_required_memory → memory_required_but_missing` |
| `core/orchestrator_stream_flow_utils.py` | ~1996–1998 | identische Berechnung, andere Variablennamen |

### Datenquelle

| Datei | Was |
|---|---|
| `core/context_manager.py` — `ContextResult` | `memory_keys_requested/found/not_found` (3 lose Felder) |
| `core/orchestrator_flow_utils.py` — `build_effective_context()` | traegt alle 3 in den Trace |

### Verbraucher

| Datei | Signatur |
|---|---|
| `core/layers/output.py` | `_build_system_prompt(..., memory_required_but_missing: bool)` — 5 Stellen |
| `core/layers/output.py` | `generate_stream(..., memory_required_but_missing: bool)` |
| `core/layers/output.py` | `_execute_output_layer(..., memory_required_but_missing: bool)` |
| `core/orchestrator_stream_flow_utils.py` | `orch.output._build_system_prompt(...)` + `generate_stream(...)` |
| `core/orchestrator_sync_flow_utils.py` | `_execute_output_layer(...)` |

---

## Implementationsstrategie

Drei Phasen, jede fuer sich deploybar.

---

## Phase 1 — `MemoryResolution` Dataclass definieren

### Wo

Neue Datei: `core/memory_resolution.py`

Oder alternativ direkt in `core/context_manager.py` (schlanker, kein neues Modul).

Empfehlung: **eigene Datei**, da mehrere Module importieren werden.

### Inhalt

```python
# core/memory_resolution.py
from dataclasses import dataclass, field
from typing import List


@dataclass
class MemoryResolution:
    """
    Einzige Wahrheitsquelle fuer Memory-Retrieval-Ergebnis.

    Ersetzt die verteilten Stellvertreter:
      needs_memory, memory_keys, memory_used,
      memory_keys_requested/found/not_found, memory_required_but_missing

    Wird einmal in build_effective_context() gebaut und unveraendert weitergereicht.
    Kein Pfad berechnet required_missing selbst.
    """
    requested_keys: List[str] = field(default_factory=list)
    found_keys: List[str] = field(default_factory=list)
    missing_keys: List[str] = field(default_factory=list)
    required_missing: bool = False

    @classmethod
    def from_context_result(cls, ctx, thinking_plan: dict) -> "MemoryResolution":
        """Baut MemoryResolution aus ContextResult + Thinking-Plan."""
        requested = list(getattr(ctx, "memory_keys_requested", []))
        found = list(getattr(ctx, "memory_keys_found", []))
        missing = list(getattr(ctx, "memory_keys_not_found", []))
        needs = bool(
            thinking_plan.get("needs_memory") or thinking_plan.get("is_fact_query")
        )
        return cls(
            requested_keys=requested,
            found_keys=found,
            missing_keys=missing,
            required_missing=needs and bool(missing),
        )

    def to_trace(self) -> dict:
        """Fuer Rueckwaertskompatibilitaet im ctx_trace."""
        return {
            "memory_keys_requested": self.requested_keys,
            "memory_keys_found": self.found_keys,
            "memory_keys_not_found": self.missing_keys,
            "memory_required_but_missing": self.required_missing,
        }
```

### DoD

- Klasse existiert und ist importierbar
- `from_context_result()` baut korrekt aus ContextResult + Thinking-Plan
- `to_trace()` liefert rueckwaertskompatiblen Dict fuer bestehende Trace-Consumer

---

## Phase 2 — `build_effective_context()` baut und gibt `MemoryResolution` zurueck

### Datei

`core/orchestrator_flow_utils.py`

### Aenderung

`build_effective_context()` gibt heute `(text: str, trace: dict)` zurueck.

Neues Return-Tupel: `(text: str, trace: dict, resolution: MemoryResolution)`

```python
# Nach ctx = orch.context.get_context(...)
resolution = MemoryResolution.from_context_result(ctx, cleanup_payload or {})
trace.update(resolution.to_trace())  # Rueckwaertskompatibilitaet im Trace bleibt

# Return
return context_text, trace, resolution
```

### Rueckwaertskompatibilitaet

Alle bestehenden Aufrufer von `build_effective_context()` lesen heute `(text, trace)`.
Da Python-Tupel-Unpacking mit 3 Elementen fehlschlaegt wenn man nur 2 erwartet, gibt es zwei saubere Optionen:

**Option A — schrittweise Migration (empfohlen):**

```python
# Aufrufer migrieren von:
ctx_text, ctx_trace = build_effective_context(...)
# auf:
ctx_text, ctx_trace, mem_res = build_effective_context(...)
```

Da es exakt 4 Aufrufstellen gibt, ist das ein kleiner Eingriff.

**Option B — Wrapper:**

Einen thin Wrapper `build_effective_context_compat()` behalten bis alle migriert sind.

Empfehlung: **Option A direkt**, alle 4 Stellen sind in `orchestrator_sync_flow_utils.py` und `orchestrator_stream_flow_utils.py`.

### Aufrufstellen (alle 4)

```
core/orchestrator_sync_flow_utils.py   — 1x
core/orchestrator_stream_flow_utils.py — 3x (Main-Stream, LoopEngine, Short-Input-Bypass)
```

### DoD

- `build_effective_context()` gibt Tupel der Laenge 3 zurueck
- alle 4 Aufrufer entpacken korrekt
- `resolution.required_missing` entspricht dem bisherigen `memory_required_but_missing`

---

## Phase 3 — Berechnungs-Duplikat aus Sync und Stream entfernen

### Dateien

- `core/orchestrator_sync_flow_utils.py` ~Zeile 622–626
- `core/orchestrator_stream_flow_utils.py` ~Zeile 1996–1998

### Aenderung

**Vorher (Sync):**

```python
needs_memory = thinking_plan.get("needs_memory") or thinking_plan.get("is_fact_query")
missing_required_memory = bool(ctx_trace.get("memory_keys_not_found"))
memory_required_but_missing = bool(needs_memory) and missing_required_memory
```

**Nachher (Sync):**

```python
memory_required_but_missing = mem_res.required_missing
```

**Vorher (Stream):**

```python
_needs_memory_stream = thinking_plan.get("needs_memory") or thinking_plan.get("is_fact_query")
_missing_required_memory_stream = bool(ctx_trace_stream.get("memory_keys_not_found"))
memory_required_but_missing_stream = bool(_needs_memory_stream) and _missing_required_memory_stream
```

**Nachher (Stream):**

```python
memory_required_but_missing_stream = mem_res.required_missing
```

Alle nachgelagerten Aufrufe (`_execute_output_layer`, `generate_stream`, `_build_system_prompt`) bleiben unveraendert — nur der Eingabewert kommt jetzt aus dem Objekt.

### DoD

- keine eigene Guard-Berechnung mehr in Sync oder Stream
- `required_missing` kommt ausschliesslich aus `MemoryResolution`
- ein neuer Pfad der `build_effective_context()` aufruft bekommt automatisch das richtige Signal

---

## Phase 4 — Output-Layer: Signatur-Upgrade (optional, spaeter)

Die Output-Funktionen nehmen heute `memory_required_but_missing: bool`.

Das kann so bleiben — der bool-Wert kommt jetzt nur aus `mem_res.required_missing`.

**Optional spaeter:** das ganze `MemoryResolution`-Objekt uebergeben statt nur dem Bool,
damit Output z. B. auch die fehlenden Key-Namen in die Fehlermeldung einbauen kann:

```
"Ich habe nach 'user_name' gesucht — diese Information ist nicht gespeichert."
```

Das ist **kein Blocker** fuer Phase 1–3 und wird separat geplant wenn sinnvoll.

---

## Teststrategie

### Neue Tests

Datei: `tests/unit/test_memory_resolution_contract.py`

Abdecken:

1. `MemoryResolution.from_context_result()` mit missing key → `required_missing=True`
2. `MemoryResolution.from_context_result()` mit gefundenem key → `required_missing=False`
3. `MemoryResolution.from_context_result()` ohne `needs_memory` → `required_missing=False`
4. `to_trace()` enthaelt alle erwarteten Keys
5. `build_effective_context()` gibt 3-Tupel zurueck
6. `build_effective_context()` Tupel[2].required_missing stimmt mit bisherigem Guard-Ergebnis ueberein

### Bestehende Tests

- `test_hallucination_guard_wiring.py` — muss weiterhin gruen sein
- `test_hallucination_guard_context_manager.py` — muss weiterhin gruen sein

---

## Risiken und Hinweise

### Tupel-Laenge

Das groesste Risiko ist, dass ein Aufrufer von `build_effective_context()` uebersehen wird und mit 2-Tupel-Unpacking bricht. Grep vor der Umsetzung:

```
grep -rn "build_effective_context" core/
```

### `memory_used` nicht anfassen

`memory_used` bleibt auf `ContextResult` und im Trace — es wird fuer Telemetrie und Budget-Signale verwendet. Nicht entfernen.

### Kein Big Bang

Phase 1 und 2 koennen unabhaengig deployed werden.
Phase 3 setzt Phase 2 voraus.
Phase 4 ist vollstaendig optional.

---

## Empfohlene Reihenfolge

1. Phase 1 — Dataclass schreiben (30 min)
2. Tests fuer Phase 1 schreiben und gruenbekommen
3. Phase 2 — `build_effective_context()` umstellen + alle 4 Aufrufer migrieren
4. Phase 3 — Duplikat-Berechnungen entfernen
5. Regression-Gate laufen lassen

---

## Akzeptanzkriterien

Der Plan ist abgeschlossen wenn:

1. `MemoryResolution` existiert und ist importierbar
2. `build_effective_context()` baut das Objekt und gibt es zurueck
3. Sync- und Stream-Flow rechnen `required_missing` nicht mehr selbst
4. alle bestehenden Guard-Tests gruен
5. neue `MemoryResolution`-Tests gruen
6. kein Pfad kann den Guard mehr still verlieren ohne `build_effective_context()` zu umgehen

---

## Umsetzungs-Nachtrag — 2026-03-29

Status: **Alle Phasen abgeschlossen und deployed**

### Umgesetzte Aenderungen

| Phase | Datei | Was |
|---|---|---|
| 1 — Dataclass | `core/memory_resolution.py` (neu) | `MemoryResolution` mit `from_context_result()` + `to_trace()` |
| 2 — 3-Tupel | `core/orchestrator_flow_utils.py` | beide `return`-Pfade (normal + dryrun) geben `(text, trace, resolution)` zurueck |
| 2 — Aufrufer | `core/orchestrator_sync_flow_utils.py` | 2 Aufrufstellen auf 3-Tupel migriert |
| 2 — Aufrufer | `core/orchestrator_stream_flow_utils.py` | 2 Aufrufstellen auf 3-Tupel migriert |
| 3 — Duplikat entfernt | `core/orchestrator_sync_flow_utils.py` ~622 | `needs_memory + missing_required_memory` Berechnung entfernt → `mem_res.required_missing` |
| 3 — Duplikat entfernt | `core/orchestrator_stream_flow_utils.py` ~1996 | identisch, Stream-Pfad |
| Tests | `tests/unit/test_memory_resolution_contract.py` (neu) | 12 Tests fuer Dataclass, `from_context_result()`, `to_trace()`, 3-Tupel |
| Test-Migration | 6 bestehende Testdateien | 2-Tupel-Unpackings auf 3-Tupel migriert, Mock-Returns um `MemoryResolution()` erweitert |

### Test-Ergebnis

```
80 passed, 0 failed
```

Kein neuer Failure im Unit-Gate (2486 passed, 31 pre-existing).

### Deploy

```
docker compose restart jarvis-admin-api trion-runtime
```

Deployed am 2026-03-29.

### Invarianten (jetzt aktiv)

1. `required_missing` wird **einmal** in `MemoryResolution.from_context_result()` berechnet
2. Kein Pfad rechnet die Guard-Bedingung selbst nach
3. Ein neuer Pfad der `build_effective_context()` aufruft bekommt `MemoryResolution` automatisch
4. `memory_used` bleibt unveraendert fuer Telemetrie/Budget — kein Guard-Signal

### Was noch offen ist

- Phase 4 (optional): Output-Layer bekommt das ganze `MemoryResolution`-Objekt statt nur den Bool → ermoeglicht Key-Namen in Fehlermeldung
- Atlas-Prioritaet B: Runtime-Contract-Migration (`ExecutionResult` als einzige Wahrheit)
