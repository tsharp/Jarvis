# Implementationsplan: Workspace-/Event-Wahrheit Konsolidierung

Erstellt am: 2026-03-31
Status: **Abgeschlossen ✓** (2026-03-31)
Branch: `feat/drift-testsuite`
Abhängig von: [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]] — Abschnitt C

---

## Problemstellung

Workspace-Events werden an **zwei fundamental verschiedenen Stellen** emittiert, über **zwei verschiedene Transporte**, mit einer **kompletten Lücke im Sync-Pfad**.

### Ist-Zustand: 3 Pfade, keine gemeinsame Basis

```
Chat/Stream-Pfad:
  Orchestrator._save_workspace_entry()
    → hub.call_tool("workspace_event_save")  ← DB-Persistenz
    → return {type:"workspace_update", ...}  ← SSE-Dict
    → Caller yield (text, done, ws_dict)     ← SSE-Stream

Chat/Sync-Pfad:
  [LÜCKE] — 0 workspace saves
  → Events gehen komplett verloren

Shell-Pfad (Container Commander):
  hub.call_tool("workspace_event_save")      ← DB-Persistenz (identisch)
  _emit_workspace_update()
    → emit_activity()
    → broadcast_event_sync()                 ← WebSocket an alle Terminals
```

### Identifizierte Probleme

| # | Problem | Auswirkung |
|---|---------|-----------|
| P1 | Sync-Pfad hat **0** Workspace-Saves | Chat ohne Stream verliert alle Observations |
| P2 | `_save_workspace_entry` + `_save_container_event` = Code-Duplikation | 2 Fast-Lane-Calls mit identischem Parse-Boilerplate |
| P3 | Shell-Pfad ruft Fast-Lane manuell auf, ohne SSE-Dict zurückzugeben | Inkonsistenz im Rückgabewert-Contract |
| P4 | 13 direkte Aufrufe in `orchestrator_stream_flow_utils.py` ohne Abstraktion | Jede Änderung am Event-Format muss 13× gepflegt werden |
| P5 | Control Layer emittiert **nichts direkt** | Korrekt — Orchestrator delegiert, DARF NICHT geändert werden |

---

## Kritische Constraint

> **"Wir dürfen keine Layer auslassen und vor allem nicht Control. Sonnst haben wir wieder mehr Pfade."**

Das bedeutet:
- Der Control Layer (`core/layers/control.py`) darf **keine** direkte Emission bekommen
- Der Orchestrator bleibt der einzige Aufrufer von `_build_control_workspace_summary()` → Workspace-Save
- Neue Abstraktion muss **alle bestehenden Aufrufer abdecken**, nicht parallel laufen

---

## Analysierter Ist-Stand: Aufrufer-Inventar

### Stream Flow Utils (`core/orchestrator_stream_flow_utils.py`)
13 Aufrufe von `orch._save_workspace_entry(...)`:

| Kontext | `entry_type` | `source_layer` |
|---------|-------------|----------------|
| Thinking Plan gespeichert | `thinking_plan` | `thinking` |
| Sequential Thinking Result | `sequential_thinking` | `thinking` |
| Control Verification | `control_verification` | `control` |
| Tool-Call-Start | `tool_call` | `tools` |
| Tool-Call-Result | `tool_result` | `tools` |
| Host Runtime Result | `host_runtime` | `tools` |
| Container Start-Event | `container_start` | `container` |
| Container Stop-Event | `container_stop` | `container` |
| Approval Request | `approval_request` | `container` |
| Approval Result | `approval_result` | `container` |
| Output generiert | `output` | `output` |
| Direct Response | `direct_response` | `output` |
| Error | `error` | `orchestrator` |

### Core Orchestrator (`core/orchestrator.py`)
- `_save_workspace_entry(conversation_id, content, entry_type, source_layer)` — allgemeiner Speicher
- `_save_container_event(conversation_id, container_evt)` — Container-spezifisch, identischer Fast-Lane-Aufruf
- `_persist_sequential_workspace_event(...)` — delegiert an `workspace_event_utils`
- `_build_control_workspace_summary(verification)` — baut den Content-String, ruft dann `_save_workspace_entry`

### Shell Context Bridge (`container_commander/shell_context_bridge.py`)
- `_emit_workspace_update(hub, conversation_id, event_type, event_data)` — Fast-Lane + WebSocket-Mirror
- Kein SSE-Dict-Rückgabe nötig (Shell hat keinen SSE-Stream)

### Sync Flow Utils (`core/orchestrator_sync_flow_utils.py`)
- **0 Workspace-Saves** — komplette Lücke

---

## Lösungsdesign

### Zentraler Emitter: `WorkspaceEventEmitter`

Neue Klasse `core/workspace_event_emitter.py`:

```
WorkspaceEventEmitter
  ├── persist(conversation_id, entry_type, content, source_layer)
  │     → hub.call_tool("workspace_event_save", ...)
  │     → parse entry_id (ToolResult oder dict)
  │     → return WorkspaceEventResult(entry_id, sse_dict)
  │
  ├── persist_container(conversation_id, container_evt)
  │     → delegiert an persist() mit normalisierten Feldern
  │     → return WorkspaceEventResult(entry_id, sse_dict)
  │
  └── persist_and_broadcast(hub, conversation_id, event_type, event_data)
        → persist(...)
        → emit_activity(event_type, event_data)   ← nur Shell-Pfad
        → return WorkspaceEventResult(entry_id, None)  ← kein SSE im Shell-Pfad
```

**`WorkspaceEventResult`** — simples Dataclass:
```python
@dataclass
class WorkspaceEventResult:
    entry_id: Optional[int]
    sse_dict: Optional[Dict]   # None wenn Shell-Pfad
```

### Transport-Entscheidung bleibt beim Aufrufer

Der Emitter entscheidet **nicht** welcher Transport. Der Aufrufer entscheidet:

```
Stream-Pfad:   result = emitter.persist(...)
               if result.sse_dict: yield ("", False, result.sse_dict)

Sync-Pfad:     result = emitter.persist(...)
               # kein yield — kein SSE-Stream
               # entry_id trotzdem in DB

Shell-Pfad:    result = emitter.persist_and_broadcast(hub, ...)
               # WS-Broadcast passiert intern im Emitter
```

**Warum so?** — Der Stream-Pfad muss den SSE-yield-Mechanismus behalten. Der Sync-Pfad hat keinen Generator. Der Shell-Pfad hat keinen SSE-Stream. Die Transportlogik gehört zum Aufrufer, nicht zum Emitter.

---

## Implementationsschritte

### Phase 1: Emitter extrahieren (kein Behavior-Change)

**Ziel:** Code-Duplikation entfernen, kein Behavior-Change, alle Tests grün.

1. **`core/workspace_event_emitter.py` anlegen**
   - `WorkspaceEventResult` Dataclass
   - `WorkspaceEventEmitter.persist()` — übernimmt kompletten Body von `_save_workspace_entry`
   - `WorkspaceEventEmitter.persist_container()` — übernimmt `_save_container_event`
   - Unit-Tests in `tests/unit/test_workspace_event_emitter.py`

2. **`Orchestrator._save_workspace_entry` umleiten**
   - Instanz `self._ws_emitter = WorkspaceEventEmitter(get_hub)` im `__init__`
   - `_save_workspace_entry` → delegiert an `self._ws_emitter.persist(...).sse_dict`
   - `_save_container_event` → delegiert an `self._ws_emitter.persist_container(...).sse_dict`
   - Kein Change an den 13 Aufrufern in `stream_flow_utils` — API identisch

3. **`shell_context_bridge._emit_workspace_update` umleiten**
   - `persist_and_broadcast()` Methode auf Emitter
   - Shell-Pfad: Fast-Lane-Call intern im Emitter, `emit_activity()` danach im Emitter
   - Rückgabe `WorkspaceEventResult(entry_id, None)` — Shell braucht kein SSE-Dict

4. **Tests Phase 1:**
   - Unit-Tests für `WorkspaceEventEmitter` (mock Fast-Lane)
   - Bestehende Integration-Tests müssen weiter grün sein
   - Kein neues Behavior

### Phase 2: Sync-Pfad-Lücke schließen

**Ziel:** Sync-Antworten hinterlassen Workspace-Trace.

5. **`orchestrator_sync_flow_utils.py` ergänzen**
   - Nach Thinking-Plan: `orch._save_workspace_entry(cid, thinking_summary, "thinking_plan", "thinking")`
   - Nach Control-Verify (falls nicht geskippt): `orch._save_workspace_entry(cid, control_summary, "control_verification", "control")`
   - Nach Output-Generate: `orch._save_workspace_entry(cid, response_summary, "output", "output")`
   - Kein SSE-yield nötig — Entry landet in DB, Frontend fragt beim nächsten Chat-Open ab

   **Wichtig:** Control Layer wird auch im Sync-Pfad vom Orchestrator aufgerufen — der `_build_control_workspace_summary(verification)` Aufruf wird dort ebenfalls ergänzt. Control Layer selbst bleibt unberührt.

6. **Tests Phase 2:**
   - Unit-Test: Sync-Flow speichert mindestens 1 Workspace-Entry
   - Mock Fast-Lane in Sync-Flow-Test

### Phase 3: Drift-Guard (optional, Phase 4 des Atlas)

7. **Drift-Test in `tests/drift/test_workspace_event_paths.py`**
   - Pflichtfelder: `entry_type`, `source_layer`, `conversation_id`
   - Kein direkter `hub.call_tool("workspace_event_save")` außerhalb von `WorkspaceEventEmitter`
   - Prüft: `orchestrator_sync_flow_utils.py` hat mindestens 3 Emitter-Aufrufe
   - Prüft: `shell_context_bridge.py` hat 0 direkte `hub.call_tool("workspace_event_save")` Aufrufe

---

## Layer-Zuordnung (vollständig)

| Layer | Emittiert? | Wie? | Nach Refactor |
|-------|-----------|------|---------------|
| ThinkingLayer | Nein (direkt) | Orchestrator ruft nach `thinking.analyze()` | unverändert |
| ControlLayer | Nein (direkt) | Orchestrator ruft `_build_control_workspace_summary()` | unverändert |
| OutputLayer | Nein (direkt) | Orchestrator nach `output.generate()` | unverändert |
| Orchestrator (Stream) | Ja | 13x `_save_workspace_entry` → yield | via Emitter |
| Orchestrator (Sync) | **Nein → Ja** | **NEU: 3x nach Phase 2** | via Emitter |
| Shell Context Bridge | Ja | Fast-Lane + `emit_activity` | via `persist_and_broadcast` |
| Container Commander | Nein (direkt) | über Shell Bridge | unverändert |

---

## Was explizit NICHT geändert wird

- **Control Layer** (`core/layers/control.py`): bekommt keine Emission, nie
- **ThinkingLayer** (`core/layers/thinking.py`): keine Änderung
- **OutputLayer** (`core/layers/output.py`): keine Änderung
- **SSE-yield-Mechanismus**: bleibt beim Aufrufer in `stream_flow_utils`
- **WebSocket-Transport**: bleibt in Shell Bridge (`emit_activity`)
- **Fast-Lane-Tool `workspace_event_save`**: kein Change am MCP-Tool selbst
- **13 bestehende Aufrufstellen in stream_flow_utils**: Phase 1 ändert nur Innenleben von `_save_workspace_entry`, Aufrufer unberührt

---

## Testplan

### Neue Tests

| Datei | Was wird getestet |
|-------|-------------------|
| `tests/unit/test_workspace_event_emitter.py` | `persist()`, `persist_container()`, `persist_and_broadcast()` mit gemocktem Fast-Lane |
| `tests/unit/test_workspace_event_emitter.py` | `entry_id=None` wenn Fast-Lane fehlt → graceful None |
| `tests/drift/test_workspace_event_paths.py` | Kein direkter `hub.call_tool("workspace_event_save")` außerhalb Emitter |
| `tests/drift/test_workspace_event_paths.py` | Sync-Flow hat ≥3 `_save_workspace_entry` Aufrufe |

### Bestehende Tests die nach Refactor grün bleiben müssen

| Datei | Kritischer Aspekt |
|-------|------------------|
| `tests/integration/test_thinking_flow.py` | Bridge-Patches dürfen nicht durch Emitter-Einführung brechen |
| `tests/e2e/test_ja_bitte_container_flow.py` | Stream-Flow SSE-yield Mechanismus intakt |
| `tests/e2e/test_todays_fixes_e2e.py` | MountUtils, Grounding Evidence |

---

## Risiken

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| Sync-Flow-Tests durch workspace-calls verlangsamt | Niedrig | Mock Fast-Lane in Tests |
| `persist_and_broadcast` bricht Shell-Pfad | Mittel | Isolierter Test für `_emit_workspace_update` vor Migration |
| Import-Zyklus `workspace_event_emitter` ↔ `orchestrator` | Niedrig | Emitter hat kein Import von `orchestrator` — only `get_hub` |
| Flaky Fast-Lane in Sync-Tests | Mittel | `HOST_HELPER_URL=''` Pattern aus Fix 8 adaptieren |

---

## Verweise

- [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]] — Abschnitt C (Ausgangslage)
- [[2026-03-31-bugfix-session]] — Bugfix-Kontext dieser Session
- [[2026-03-30-drift-testsuite-implementationsplan]] — Drift-Tests die Phase 3 begleiten

---

## Abschlussvermerk (2026-03-31)

Alle drei Phasen implementiert und getestet. Unit-Gate: **2553 passed · 3 skipped · 0 Failures**.

### Geänderte Dateien

| Datei | Art | Beschreibung |
|-------|-----|--------------|
| `core/workspace_event_emitter.py` | **neu** | Zentraler Emitter: `WorkspaceEventResult`, `persist()`, `persist_container()`, `persist_and_broadcast()`, Singleton `get_workspace_emitter()` |
| `core/orchestrator.py` | geändert | `_save_workspace_entry` + `_save_container_event` delegieren an Emitter — API identisch, alle 13 Aufrufer in stream_flow_utils unberührt |
| `container_commander/shell_context_bridge.py` | geändert | `save_shell_session_summary` + `save_shell_checkpoint` nutzen `persist_and_broadcast` — kein direktes `hub.call_tool` mehr |
| `core/orchestrator_sync_flow_utils.py` | geändert | 3 neue `_save_workspace_entry`-Aufrufe: observation/thinking + control_decision/control + chat_done/orchestrator |
| `tests/unit/test_workspace_event_emitter.py` | **neu** | 24 Unit-Tests: `_parse_entry_id`, `persist()`, `persist_container()`, `persist_and_broadcast()`, Singleton |
| `tests/unit/test_workspace_event_sync_path.py` | **neu** | 5 Unit-Tests: Sync-Pfad schreibt ≥3 Workspace-Entries |
| `tests/unit/test_shell_context_bridge_contract.py` | geändert | 2 Tests auf neue Delegation (persist_and_broadcast) umgestellt |
| `tests/drift/test_workspace_event_paths.py` | **neu** | 21 Drift-Guard-Tests in 4 Invarianten-Klassen |

### Eingetretene Wirkung

- `hub.call_tool("workspace_event_save")` wird ausschliesslich durch `WorkspaceEventEmitter` aufgerufen
- Sync-Pfad (`process_request`) hinterlässt vollständigen Workspace-Trace (war vorher 0 Entries)
- Shell-Bridge hat keinen direkten Fast-Lane-Call mehr
- Drift-Guard verhindert zukünftige direkte Aufrufe in neuen Modulen

### Offene Legacy-Aufrufer (noch nicht migriert)

Zwei Dateien im Adapter-Layer rufen `workspace_event_save` noch direkt auf — explizit als `known_legacy` im Drift-Guard dokumentiert:

- `adapters/admin-api/main.py`
- `adapters/admin-api/commander_api/containers.py`

Diese sind nicht Teil von Phase 1–3 (scope: core/ + container_commander/).
Migration wäre nächster logischer Schritt wenn der Adapter-Layer konsolidiert wird.
