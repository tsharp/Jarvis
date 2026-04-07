# Sync/Stream Pipeline-Preamble Konsolidierung

Erstellt am: 2026-03-29
Status: **abgeschlossen (2026-03-30)**
Bezieht sich auf:

- [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]]
- [[2026-03-29-memory-resolution-contract-plan]]

---

## Ausgangslage

`orchestrator_sync_flow_utils.py` (673 Zeilen) und `orchestrator_stream_flow_utils.py` (2137 Zeilen) teilen drei grosse Bloecke identischer reiner Berechnungslogik — ohne jegliche `yield`-Aufrufe.

Jede Aenderung an diesen Blaecken muss heute **zweimal** gemacht werden.
Das ist die Haupt-Drift-Quelle zwischen Sync- und Stream-Pfad.

---

## Was genau doppelt ist

### Stage 1 — Tool-Selection Preamble (~20 Zeilen je)

Identisch in beiden Flows direkt vor dem ThinkingLayer-Aufruf:

```python
# _last_assistant_msg extrahieren
_last_assistant_msg = ""
for _msg in reversed(list(getattr(request, "messages", None) or [])):
    if isinstance(_msg, dict) and _msg.get("role") == "assistant":
        _last_assistant_msg = str(_msg.get("content", ""))
        break

selected_tools = await orch.tool_selector.select_tools(user_text, context_summary=_last_assistant_msg)
selected_tools = orch._filter_tool_selector_candidates(selected_tools, user_text, forced_mode=forced_response_mode)

# Short-Input Bypass
if not selected_tools and len(user_text.split()) < 5:
    if _last_assistant_msg:
        selected_tools = ["request_container", "run_skill"]
    else:
        selected_tools = ["request_container", "run_skill", "home_write"]

query_budget_signal = await orch._classify_query_budget_signal(user_text, selected_tools=selected_tools, tone_signal=tone_signal)
domain_route_signal = await orch._classify_domain_signal(user_text, selected_tools=selected_tools)
```

**Unterschied:** Stream yielded danach `{"type": "tool_selection", "tools": selected_tools}` — das bleibt im Stream-Flow.

### Stage 2 — Post-Thinking Plan Finalization (~25 Zeilen je)

Identisch nach dem ThinkingLayer (egal ob Cache-Hit, Skip oder Fresh):

```python
thinking_plan = orch._coerce_thinking_plan_schema(thinking_plan, user_text=user_text)
thinking_plan = orch._apply_query_budget_to_plan(thinking_plan, query_budget_signal, user_text=user_text)
thinking_plan = orch._apply_domain_route_to_plan(thinking_plan, domain_route_signal, user_text=user_text)
thinking_plan = orch._resolve_precontrol_policy_conflicts(user_text, thinking_plan, conversation_id=conversation_id)

# Short-Input Plan Bypass
if not thinking_plan.get("suggested_tools") and selected_tools and len(user_text.split()) < 5:
    thinking_plan["suggested_tools"] = list(selected_tools)

response_mode = orch._apply_response_mode_policy(user_text, thinking_plan, forced_mode=forced_response_mode)
orch._apply_temporal_context_fallback(user_text, thinking_plan, chat_history=request.messages)
```

**Unterschied:** Stream yielded danach `{"type": "response_mode", "mode": response_mode}` — bleibt im Stream-Flow.

### Stage 3 — Pre-Control Gates (~25 Zeilen je)

Identisch nach dem Context-Retrieval:

```python
# Skill Dedup Gate
if "autonomous_skill_task" in thinking_plan.get("suggested_tools", []):
    ...  # Block oder Route skill

# Container Candidate Evidence
if "request_container" in thinking_plan.get("suggested_tools", []):
    orch._prepare_container_candidate_evidence(user_text, thinking_plan, chat_history=...)

# Hardware Gate Early
_early_gate_msg = orch._check_hardware_gate_early(user_text, thinking_plan)
if _early_gate_msg:
    thinking_plan["_hardware_gate_triggered"] = True
    thinking_plan["_hardware_gate_warning"] = str(_early_gate_msg)[:1200]
```

**Kein Unterschied** zwischen Sync und Stream — diese Stage ist 1:1 identisch.

---

## Was NICHT extrahiert wird

| Block | Grund |
|---|---|
| ThinkingLayer-Aufruf selbst | Sync: `analyze()`, Stream: `analyze_stream()` mit Chunk-Yields |
| Intent Confirmation | Sync: return, Stream: yield + return |
| Context Compression | Stream hat zusaetzliche yield-Events |
| `build_effective_context()` | Bereits geteilt |
| Memory Save | Sync und Stream haben unterschiedliche Persistenz-Pfade |

---

## Zielzustand

Neue Datei: `core/orchestrator_pipeline_stages.py`

Drei pure async-Funktionen:

```python
async def run_tool_selection_stage(orch, user_text, request, forced_response_mode, tone_signal, log_info_fn) -> ToolSelectionResult

async def run_plan_finalization_stage(orch, user_text, request, thinking_plan, selected_tools, query_budget_signal, domain_route_signal, forced_response_mode, conversation_id) -> PlanFinalizationResult

def run_pre_control_gates(orch, user_text, thinking_plan, request, log_info_fn, log_warn_fn) -> dict  # mutiert thinking_plan, gibt es zurueck
```

Beide Flow-Dateien rufen nur noch diese Funktionen auf.

---

## Implementationsstrategie

### Wichtigste Regel

**Keine Logik aendern — nur verschieben.**

Jede Funktion macht exakt dasselbe wie der Code heute, nur zentralisiert.

### Reihenfolge

1. Stage 3 zuerst — einfachste, keine Rueckgabewerte ausser mutiertem `thinking_plan`
2. Stage 1 — async, gibt `(selected_tools, query_budget_signal, domain_route_signal, _last_assistant_msg)` zurueck
3. Stage 2 — async, gibt `(thinking_plan, response_mode)` zurueck
4. Tests schreiben
5. Gate laufen lassen

### Warum Stage 3 zuerst

- Kein Unterschied zwischen Sync und Stream → kein Risiko
- Kein Async → einfachste Extraktion
- Sofort sichtbare Reduktion

---

## Phases

### Phase 1 — `run_pre_control_gates()`

Extrahiert: Skill-Dedup-Gate + Container-Candidate-Evidence + Hardware-Gate-Early

Dateien: `orchestrator_pipeline_stages.py` (neu), `orchestrator_sync_flow_utils.py`, `orchestrator_stream_flow_utils.py`

DoD:
- Stage-Funktion existiert
- beide Flows rufen sie auf
- kein doppelter Gate-Code mehr

### Phase 2 — `run_tool_selection_stage()`

Extrahiert: `_last_assistant_msg`, `select_tools`, `_filter_tool_selector_candidates`, Short-Input-Bypass, `_classify_query_budget_signal`, `_classify_domain_signal`

DoD:
- async Stage-Funktion existiert
- beide Flows rufen sie auf
- Stream yieldet danach weiterhin `tool_selection`-Event (das bleibt im Stream-Flow)

### Phase 3 — `run_plan_finalization_stage()`

Extrahiert: `_coerce_thinking_plan_schema`, `_apply_query_budget_to_plan`, `_apply_domain_route_to_plan`, `_resolve_precontrol_policy_conflicts`, Short-Input-Plan-Bypass, `_apply_response_mode_policy`, `_apply_temporal_context_fallback`

DoD:
- async Stage-Funktion existiert
- beide Flows rufen sie auf
- Stream yieldet danach weiterhin `response_mode`- und `thinking_done`-Events

---

## Erwartete Wirkung

| Metrik | Heute | Nach Konsolidierung |
|---|---|---|
| Zeilen Sync-Flow | 673 | ~620 |
| Zeilen Stream-Flow | 2137 | ~2060 |
| Zeilen neues Stages-Modul | 0 | ~130 |
| Doppelter Gate-Code | 3x | 0x |
| Zukuenftige Gate-Aenderung | 2 Dateien | 1 Datei |

---

## Risiken

- **ThinkingLayer-Bypasse**: Sync und Stream haben unterschiedliche Skip-Paths mit unterschiedlichen Yields. Diese werden NICHT extrahiert — nur die reinen Berechnungs-Stages.
- **Log-Prefix-Unterschiede**: Sync loggt `[Orchestrator-Sync]`, Stream loggt ohne Prefix oder `[stream]`. Diese werden beim Verschieben beibehalten oder auf neutrales `[Pipeline]` vereinheitlicht.
- **Tuple-Rueckgabe**: Stage-Funktionen geben Tuples zurueck — klar benennen, keine MagicMock-Falle wie beim 3-Tupel-Upgrade.

---

## Akzeptanzkriterien

1. `orchestrator_pipeline_stages.py` existiert mit drei Funktionen
2. Sync- und Stream-Flow enthalten keinen der drei Gate/Selection/Finalization-Bloecke mehr
3. Alle bestehenden Gate-Tests gruen
4. Unit-Gate ohne neue Failures
