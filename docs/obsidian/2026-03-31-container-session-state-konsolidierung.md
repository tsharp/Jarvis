# Implementationsplan: Container-/Session-State-Wahrheit Konsolidierung

Erstellt am: 2026-03-31
Status: **Abgeschlossen ✓**
Branch: `feat/drift-testsuite`
Abhängig von: [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]] — Abschnitt D

---

## Problemstellung

Der Codeatlas identifiziert vier State-Typen fuer dieselbe Kernfrage:

> Welcher Container ist zuletzt relevant — und welche Container gelten fuer diese Conversation als bekannt?

Diese vier State-Typen existieren heute:

| State-Typ | Wo | Problem? |
|-----------|-----|----------|
| Docker-Runtime-Wahrheit | `engine.py` → `_active: Dict[str, ContainerInstance]` | Nein — ground truth vom Docker-Daemon, sinnvoll getrennt |
| Commander-Runtime-Wahrheit | `engine_runtime_state.py` → `RuntimeStateRefs` | Nein — Quota/TTL-Infrastruktur, sinnvoll getrennt |
| Orchestrator-Conversation-Wahrheit | `orchestrator.py` → `_conversation_container_state` | **Ja** — raw dict, kein typisiertes Objekt, Verwaltungslogik im 5008-Zeilen-Orchestrator |
| Shell/API-Brücke | `containers.py` → `_remember_container_state()` | Teilweise — ruft direkt `bridge.orchestrator._remember_container_state()` auf (SLF001) |

**Nicht alles zusammenwerfen.** Nur die Orchestrator-Conversation-Wahrheit (Typ 3) wird konsolidiert.
Docker- und Commander-Runtime bleiben wo sie sind.

---

## Ist-Zustand im Detail

### `core/orchestrator.py` — Conversation-State-Verwaltung

```
_conversation_container_state: Dict[str, dict]   ← raw dict, kein Typ
_conversation_container_lock: threading.Lock

_get_recent_container_state(conv_id, history_len)
  → liest aus dict, prüft TTL + history delta

_remember_container_state(conv_id, *, last_active, home, known, history_len)
  → merged + schreibt in dict

_update_container_state_from_tool_result(conv_id, tool_name, tool_args, result, ...)
  → holt state, ruft merge_container_state_from_tool_result() auf, ruft _remember_container_state()

_normalize_container_entries(rows)      ← static, delegiert an container_state_utils
_select_preferred_container_id(rows, …) ← static, delegiert an container_state_utils
```

Initialisierung in `core/orchestrator_flow_utils.py` (Zeile 60–61):
```python
orch._conversation_container_state = {}
orch._conversation_container_lock = lock_factory()
```

Nutzung in orchestrator.py:
- Zeile 820, 854: `_update_container_state_from_tool_result()`
- Zeile 3433, 3446: als Funktions-Referenzen weitergegeben

### `core/container_state_utils.py` — Merge- und Select-Logik

Bereits ausgelagert — gut. Enthält:
- `normalize_container_entries(rows)` — normalisiert Container-Listen
- `merge_container_state_from_tool_result(state, ...)` — Merge-Logik für alle Tool-Ergebnisse
- `tool_requires_container_id(tool_name, required_tools)` — Tool-Filter
- `select_preferred_container_id(rows, ...)` — Auswahl-Logik

**Problem:** Die Felder des State-Dicts sind nirgends als Typ definiert. `last_active_container_id`, `home_container_id`, `known_containers`, `updated_at`, `history_len` existieren nur als implizite Dict-Keys.

### `adapters/admin-api/commander_api/containers.py` — API-Brücke

```python
def _remember_container_state(conversation_id, container_id, blueprint_id, status, name):
    bridge.orchestrator._remember_container_state(...)  # noqa: SLF001
```

3 Call-Sites (Zeilen 764, 846, 960): ruft direkt eine private Methode über bridge auf.
Funktioniert, aber erzeugt enge Kopplung und SLF001-Suppression.

### Bekannter Nebenläufiger Drift (NICHT Teil dieses Plans)

`engine_runtime_state.py` (Zeilen 237–251, 330–347) ruft direkt `_mcp_call("workspace_event_save", ...)` auf — das ist ein weiterer Drift aus [[2026-03-31-workspace-event-emitter-implementationsplan]]. Für diesen Plan ignorieren, separat adressieren.

---

## Lösungsdesign

### Ziel: `ConversationContainerState` + `ConversationContainerStateStore`

```
core/conversation_container_state.py  (neu)
  ├── ConversationContainerState (dataclass)
  │     ├── last_active_container_id: str
  │     ├── home_container_id: str
  │     ├── known_containers: List[Dict[str, str]]
  │     ├── updated_at: float
  │     └── history_len: int
  │
  └── ConversationContainerStateStore
        ├── __init__(lock_factory, ttl_s_fn, ttl_turns_fn, home_blueprint_fn)
        ├── remember(conv_id, *, last_active, home, known, history_len) → None
        ├── get_recent(conv_id, history_len) → Optional[ConversationContainerState]
        └── update_from_tool_result(conv_id, tool_name, tool_args, result, history_len) → None
```

**Was sich nicht ändert:**
- `container_state_utils.py` Merge/Select-Logik bleibt unberührt (Store delegiert intern dorthin)
- Öffentliche Methoden auf dem Orchestrator bleiben als dünne Wrapper — API-Kompatibilität
- Docker-Runtime-State (`engine.py._active`) — nicht angefasst
- Commander-Runtime-State (`engine_runtime_state.py`) — nicht angefasst

### Transport bleibt beim Aufrufer

Wie beim WorkspaceEventEmitter: Der Store verwaltet State, aber der Aufrufer entscheidet wann er schreibt/liest. Kein Behavior-Change.

---

## Implementationsschritte

### Phase 1: Typ einführen — kein Behavior-Change

**1. `core/conversation_container_state.py` anlegen**

- `ConversationContainerState` Dataclass mit allen 5 Feldern
- Hilfsmethode `from_dict(d: dict) → ConversationContainerState`
- Hilfsmethode `to_dict() → dict`
- Unit-Tests: `tests/unit/test_conversation_container_state.py`

### Phase 2: Store extrahieren — kein Behavior-Change

**2. `ConversationContainerStateStore` in derselben Datei**

- Übernimmt `_conversation_container_state` dict + `_conversation_container_lock`
- `remember(...)` — übernimmt Body von `_remember_container_state`
- `get_recent(...)` — übernimmt Body von `_get_recent_container_state`
- `update_from_tool_result(...)` — übernimmt Body von `_update_container_state_from_tool_result`
- Alle drei delegieren intern an `container_state_utils`
- Unit-Tests: erweitern `test_conversation_container_state.py`

**3. `core/orchestrator_flow_utils.py` anpassen**

```python
# Vorher:
orch._conversation_container_state = {}
orch._conversation_container_lock = lock_factory()

# Nachher:
from core.conversation_container_state import ConversationContainerStateStore
orch._container_state_store = ConversationContainerStateStore(
    lock_factory=lock_factory,
    ttl_s_fn=get_followup_tool_reuse_ttl_s,
    ttl_turns_fn=get_followup_tool_reuse_ttl_turns,
    home_blueprint_fn=orch._expected_home_blueprint_id,
)
```

**4. `core/orchestrator.py` umleiten**

Die drei Methoden werden zu dünnen Wrappern:
```python
def _get_recent_container_state(self, conv_id, history_len=0):
    return self._container_state_store.get_recent(conv_id, history_len)

def _remember_container_state(self, conv_id, *, ...):
    self._container_state_store.remember(conv_id, ...)

def _update_container_state_from_tool_result(self, conv_id, ...):
    self._container_state_store.update_from_tool_result(conv_id, ...)
```

Kein Change an den Aufrufstellen (820, 854, 3433, 3446) — API identisch.

### Phase 3: containers.py Kopplung dokumentieren (kein Rewrite)

**5. Kopplung einfrieren, nicht sofort reparieren**

`containers.py._remember_container_state()` ruft `bridge.orchestrator._remember_container_state()` auf. Nach Phase 2 ist das weiterhin gültig — der Orchestrator hat den Wrapper noch.

**Warum noch kein Rewrite?** Die containers.py-Funktion hat nur 3 Call-Sites und funktioniert. Ein Rewrite auf `bridge.orchestrator._container_state_store.remember()` würde die Kopplung nur marginal verbessern — es bleibt eine bridge-Abhängigkeit. Besser: das zusammen mit der containers.py-Konsolidierung (größeres Thema) angehen.

Stattdessen: den Drift-Guard so schreiben dass er die SLF001-Suppression in containers.py auf maximal diese 3 bekannten Stellen einschränkt.

### Phase 4: Drift-Guard

**6. `tests/drift/test_container_state_paths.py`**

Invarianten:
- `_conversation_container_state` darf ausschließlich in `ConversationContainerStateStore` existieren (nicht mehr als Attribut auf dem Orchestrator)
- `_conversation_container_lock` darf ausschließlich im Store existieren
- `orchestrator.py` darf keine `_conversation_container_state`-Direktzugriffe mehr haben
- `ConversationContainerState` Dataclass existiert mit allen Pflichtfeldern
- Alle drei Store-Methoden (`remember`, `get_recent`, `update_from_tool_result`) existieren

---

## Layer-Zuordnung

| Komponente | Zustand vorher | Zustand nachher |
|-----------|----------------|-----------------|
| `orchestrator.py` `_conversation_container_state` | raw `Dict[str, dict]` im Orchestrator | **entfernt**, lebt im Store |
| `orchestrator.py` `_remember/get_recent/update` | vollständige Implementierung | dünne Wrapper auf Store |
| `container_state_utils.py` | Merge/Select-Logik | unverändert |
| `conversation_container_state.py` | **nicht existent** | **neu**: Typ + Store |
| `containers.py` Kopplung | `bridge.orchestrator._remember_container_state()` | unverändert (Wrapper bleibt) |
| Docker-Runtime `engine.py._active` | sinnvoll getrennt | unverändert |
| Commander-Runtime `engine_runtime_state.py` | sinnvoll getrennt | unverändert |

---

## Was explizit NICHT geändert wird

- **Docker-Runtime** (`engine.py._active`): kein Handlungsbedarf
- **Commander-Runtime** (`engine_runtime_state.py`): kein Handlungsbedarf
- **`container_state_utils.py`** Merge/Select-Logik: bleibt, nur Typ-Import hinzufügen
- **Öffentliche Methoden-API** auf Orchestrator: bleiben als Wrapper — kein Breaking Change
- **`containers.py`** SLF001-Aufruf: eingefroren, nicht rewritten (separates Thema)
- **`engine_runtime_state.py`** `_mcp_call("workspace_event_save")` Drift: separates Thema

---

## Testplan

### Neue Tests

| Datei | Was wird getestet |
|-------|-------------------|
| `tests/unit/test_conversation_container_state.py` | `ConversationContainerState.from_dict()`, `to_dict()` |
| `tests/unit/test_conversation_container_state.py` | `Store.remember()` — merge mit prev state |
| `tests/unit/test_conversation_container_state.py` | `Store.get_recent()` — TTL-Ablauf, history-delta |
| `tests/unit/test_conversation_container_state.py` | `Store.update_from_tool_result()` — alle Tool-Types |
| `tests/drift/test_container_state_paths.py` | `_conversation_container_state` nicht mehr im Orchestrator |
| `tests/drift/test_container_state_paths.py` | Store hat alle Pflicht-Methoden |

### Bestehende Tests die grün bleiben müssen

| Datei | Kritischer Aspekt |
|-------|------------------|
| `tests/unit/test_mini_control_core_sync.py` | Container-State-Lookup im Sync-Pfad |
| `tests/e2e/test_ja_bitte_container_flow.py` | Container-State nach request_container |
| Alle Tests die `_remember_container_state` oder `_get_recent_container_state` mocken | API-Kompatibilität der Wrapper |

---

## Risiken

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| Bestehende Tests mocken `_conversation_container_state` direkt | Mittel | grep vor Phase 2, Mocks auf Store-Methoden umstellen |
| `orchestrator_flow_utils.py` Initialisierungsreihenfolge bricht | Niedrig | Store-Init benötigt nur `lock_factory` + Funktions-Referenzen — keine Abhängigkeit auf andere orch-Attribute |
| Import-Zyklus `conversation_container_state` ↔ `orchestrator` | Niedrig | Store importiert nicht aus `orchestrator`, nur `container_state_utils` |
| TTL/history-Logik weicht im Store leicht ab | Mittel | Store-Implementierung exakt aus Orchestrator kopieren, dann Unit-Tests |

---

## Verweise

- [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]] — Abschnitt D (Ausgangslage + Abschlussvermerk)
- [[2026-03-31-workspace-event-emitter-implementationsplan]] — Abgeschlossener Vorgänger-Plan (gleiche Methodik)
- `core/container_state_utils.py` — Merge/Select-Logik (bleibt unverändert)
- `core/orchestrator_flow_utils.py` — Initialisierungsort des neuen Stores

---

## Abschlussvermerk (2026-03-31)

Alle vier Phasen implementiert und getestet.

### Geänderte / neue Dateien

| Datei | Art | Beschreibung |
|-------|-----|--------------|
| `core/conversation_container_state.py` | **neu** | `ConversationContainerState` (Dataclass, 5 Felder, `from_dict`/`to_dict`) + `ConversationContainerStateStore` (`remember`, `get_recent`, `update_from_tool_result`) |
| `core/orchestrator_flow_utils.py` | geändert | Initialisiert `orch._container_state_store = ConversationContainerStateStore(...)` statt Raw-Dict + Lock |
| `core/orchestrator.py` | geändert | `_conversation_container_state` Raw-Dict + `_conversation_container_lock` entfernt; drei Methoden sind jetzt dünne Wrapper auf `_container_state_store` |
| `tests/unit/test_conversation_container_state.py` | **neu** | Unit-Tests: Dataclass round-trip, Store.remember (merge, cap, edge-cases), Store.get_recent (TTL, history-delta, eviction), Store.update_from_tool_result (delegation, TTL-eviction) |
| `tests/drift/test_container_state_paths.py` | **neu** | 18 Drift-Guard-Tests in 5 Invarianten-Klassen |

### Eingetretene Wirkung

- `ConversationContainerState` ist das einzige typisierte Objekt für Conversation-Container-State
- `_conversation_container_state` Raw-Dict und `_conversation_container_lock` existieren nicht mehr auf dem Orchestrator
- Orchestrator-API (`_get_recent_container_state`, `_remember_container_state`, `_update_container_state_from_tool_result`) bleibt identisch — alle Aufrufer unberührt
- `containers.py`-Kopplung (`bridge.orchestrator._remember_container_state`) bleibt gültig — Wrapper ist noch da
- Drift-Guard verhindert zukünftige Raw-Dict-Einführung in core/ und adapters/

### Was explizit NICHT geändert wurde

- `container_state_utils.py` Merge/Select-Logik — unberührt, Store delegiert dorthin
- Docker-Runtime (`engine.py._active`) — sinnvoll getrennt, unberührt
- Commander-Runtime (`engine_runtime_state.py`) — sinnvoll getrennt, unberührt
- `containers.py` SLF001-Aufruf — eingefroren, separates Thema
