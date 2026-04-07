# Output-Entry Konsolidierung — Implementationsplan

Erstellt am: 2026-03-30
Status: **Abgeschlossen** ✓
Bezieht sich auf:

- [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]]

---

## Ausgangslage

Laut Atlas (Priorität 2) gibt es drei verschiedene Output-Entry-Points, die alle separat aufgerufen werden ohne gemeinsame Vorbereitungsfunktion:

| Pfad | Entry-Point | Datei |
|---|---|---|
| Sync-Flow | `orch._execute_output_layer()` → `orch.output.generate()` | `orchestrator_sync_flow_utils.py:515` |
| Stream-Flow (Normal) | `orch.output.generate_stream()` direkt | `orchestrator_stream_flow_utils.py:1947` |
| Stream-Flow (LoopEngine) | `loop_engine.run_stream()` | `orchestrator_stream_flow_utils.py:1928` |

**Unit-Gate beim Start: 2515 passed · 3 skipped · 0 failed**

---

## Probleme im Detail

### Problem 1 — Dupliziertes Pre-Output-Setup (4 Zeilen, 2× vorhanden)

Sync (`orchestrator_sync_flow_utils.py:511-513`) und Stream (`orchestrator_stream_flow_utils.py:1854-1893`) führen beide unabhängig voneinander dieselben Schritte durch:

```python
# Schritt 1 — Memory-Guard-Flag
memory_required_but_missing = mem_res.required_missing

# Schritt 2 — Output-Model auflösen
resolved_output_model, model_resolution = orch._resolve_runtime_output_model(request.model)
verified_plan["_output_model_resolution"] = model_resolution

# Schritt 3 — Output-Time-Budget (nur Stream, fehlt in Sync)
verified_plan["_output_time_budget_s"] = get_output_timeout_deep_s() if ... else get_output_timeout_interactive_s()
```

Sync hat Schritt 3 gar nicht — diese Inkonsistenz ist selbst ein latenter Bug.

### Problem 2 — LoopEngine greift auf private Methode zu

```python
# orchestrator_stream_flow_utils.py:1915
sys_prompt = orch.output._build_system_prompt(
    verified_plan, full_context,
    memory_required_but_missing=memory_required_but_missing_stream,
)
```

`_build_system_prompt` ist eine private Methode von `OutputLayer`, die von 8 Tests direkt
aufgerufen wird. Die Stream-Flow-Utils greifen von außen auf eine Interna-Methode zu — das
bricht die Kapselung und macht Refactors fragil.

### Problem 3 — `_execute_output_layer()` ist ein dünner Wrapper

```python
# orchestrator.py:4866
async def _execute_output_layer(self, ...) -> str:
    """Execute Output Layer (Step 3)."""
    log_info(...)
    answer = await self.output.generate(...)
    log_info(...)
    return answer
```

Diese Methode delegiert nur, fügt zwei Log-Zeilen hinzu, und wird in 3 Tests als
Mock-Anker verwendet. Ihr einziger Nutzen: ein stabiler Patch-Punkt für Tests.

---

## Konsolidierungsplan

### Phase 1 — `prepare_output_invocation()` Stage

**Ziel:** Pre-Output-Setup aus beiden Flows in eine gemeinsame Funktion in
`core/orchestrator_pipeline_stages.py` extrahieren.

**Was wird extrahiert:**
- `mem_res.required_missing` → `memory_required_but_missing`
- `orch._resolve_runtime_output_model(request.model)` → `resolved_output_model`, `model_resolution`
- `verified_plan["_output_model_resolution"] = model_resolution`
- `verified_plan["_output_time_budget_s"] = ...` (wird jetzt auch in Sync aktiv)

**Signatur:**
```python
def prepare_output_invocation(
    orch: Any,
    request: Any,
    verified_plan: Dict,
    mem_res: Any,
    response_mode: str,
) -> Tuple[str, bool]:
    """
    Gemeinsames Pre-Output-Setup für Sync- und Stream-Flow.

    Returns:
        resolved_output_model        — aufgelöstes Modell-Handle
        memory_required_but_missing  — Guard-Flag aus MemoryResolution
    """
```

**Beide Flows danach:**
```python
resolved_output_model, memory_required_but_missing = prepare_output_invocation(
    orch, request, verified_plan, mem_res, response_mode
)
```

**Risiko:** Niedrig — reine Extraktion, kein Verhaltensänderung.

---

### Phase 2 — LoopEngine `_build_system_prompt`-Leak abdichten

**Ziel:** Stream-Flow-Utils ruft keine private Methode von OutputLayer mehr auf.

**Lösung:** `_build_system_prompt` → öffentliche Methode `build_system_prompt` umbenennen.

**Änderungen:**
1. `core/layers/output.py`: `_build_system_prompt` → `build_system_prompt` (Methode umbenennen)
2. Alle internen Aufrufe in `output.py` entsprechend anpassen (ca. 2–3 Stellen)
3. `orchestrator_stream_flow_utils.py:1915`: `orch.output._build_system_prompt(...)` → `orch.output.build_system_prompt(...)`
4. Tests aktualisieren — alle 8 Stellen die `._build_system_prompt(` aufrufen:
   - `tests/unit/test_single_truth_channel.py`
   - `tests/unit/test_hallucination_guard_wiring.py`
   - `tests/unit/test_output_tool_injection.py`
   - `tests/test_persona_v2.py`

**Risiko:** Mittel — Tests müssen angepasst werden, aber mechanisch eindeutig.

---

### Phase 3 — `_execute_output_layer()` Wrapper entfernen

**Ziel:** Thin Wrapper in `orchestrator.py` entfernen, Sync-Flow ruft `orch.output.generate()` direkt.

**Änderungen:**
1. `orchestrator_sync_flow_utils.py`: `orch._execute_output_layer(...)` → `await orch.output.generate(...)`
   - Logging-Zeilen direkt in den Flow-Code übernehmen (2 Zeilen)
2. `orchestrator.py`: `_execute_output_layer()` Methode entfernen
3. Tests aktualisieren — 3 Stellen die `_execute_output_layer` mocken:
   - `tests/unit/test_orchestrator_runtime_safeguards.py:1112` → mock `orch.output.generate`
   - `tests/unit/test_orchestrator_runtime_safeguards.py:1168` → mock `orch.output.generate`
   - `tests/unit/test_orchestrator_sync_compression.py:54` → mock `orch.output.generate`
   - `tests/unit/test_orchestrator.py:180` → Test löschen oder auf `output.generate` umschreiben

**Risiko:** Mittel — mechanische Test-Anpassungen, kein Verhaltensänderung.

---

## Reihenfolge

```
Phase 1 — prepare_output_invocation()       (sauberste Extraktion, kein Test-Impact)
Phase 2 — build_system_prompt umbenennen    (LoopEngine-Leak schließen, Tests anpassen)
Phase 3 — _execute_output_layer entfernen   (Wrapper weg, Tests anpassen)
```

**Logik:** Phase 1 hat kein Test-Impact und ist das Herzstück der Atlas-Anforderung.
Phase 2 + 3 sind Cleanup, der die Architektur sauber hält.

---

## Zielzustand

- `orchestrator_pipeline_stages.py` hat 4 Stages:
  - `run_pre_control_gates()`       ✓ (bereits vorhanden)
  - `run_plan_finalization()`       ✓ (bereits vorhanden)
  - `run_tool_selection_stage()`    ✓ (bereits vorhanden)
  - `prepare_output_invocation()`   ← neu
- `_execute_output_layer()` aus `orchestrator.py` entfernt
- `_build_system_prompt` → `build_system_prompt` (public)
- Kein Drift zwischen Sync und Stream bei Model-Auflösung und Time-Budget

Unit-Gate nach Abschluss: **≥ 2515 passed · 3 skipped · 0 failed**

---

## Fortschrittsprotokoll

| Phase | Status | Impact |
|---|---|---|
| 1. `prepare_output_invocation()` | ✅ Erledigt | kein Test-Impact |
| 2. `build_system_prompt` umbenennen | ✅ Erledigt | 12 Test-Anpassungen |
| 3. `_execute_output_layer` entfernen | ✅ Erledigt | 4 Test-Anpassungen |

**Unit-Gate Endergebnis: 2515 passed · 3 skipped · 0 failed**
