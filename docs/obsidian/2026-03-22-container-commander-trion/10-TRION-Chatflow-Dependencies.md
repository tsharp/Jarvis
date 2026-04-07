# TRION Chatflow Dependencies

## Pipeline-Uebersicht

Normaler Sync-Flow:

1. Adapter / API nimmt Chat entgegen
2. Bridge delegiert an Orchestrator
3. Tool Selector liefert Kandidaten
4. Thinking erzeugt Plan
5. Policy-Shaping / Query-Budget / Domain-Route / Kontext greifen ein
6. Control erzeugt `control_decision`
7. Output fuehrt Tool-/Antwortpfad aus
8. Memory / Workspace-Telemetrie speichern den Turn

Stream-Flow:

- nutzt denselben Kern, aber mit Event-Emission ueber `process_stream_with_events(...)`

## Hauptabhaengigkeiten

### Adapter / Entry

- [main.py](<repo-root>/adapters/admin-api/main.py)
- [bridge.py](<repo-root>/core/bridge.py)
- [orchestrator.py](<repo-root>/core/orchestrator.py)

### Tool-Kandidaten

- [tool_selector.py](<repo-root>/core/tool_selector.py)
- [hub.py](<repo-root>/mcp/hub.py)
- `memory_semantic_search`

### Thinking

- [thinking.py](<repo-root>/core/layers/thinking.py)
- [tone_hybrid.py](<repo-root>/core/tone_hybrid.py)

### Policy-Shaping / Routing / Context

- [orchestrator_policy_signal_utils.py](<repo-root>/core/orchestrator_policy_signal_utils.py)
- [orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
- [orchestrator_precontrol_policy_utils.py](<repo-root>/core/orchestrator_precontrol_policy_utils.py)
- [context_manager.py](<repo-root>/core/context_manager.py)
- [orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)
- [orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)

### Control

- [control.py](<repo-root>/core/layers/control.py)
- [control_contract.py](<repo-root>/core/control_contract.py)
- [control_decision_utils.py](<repo-root>/core/control_decision_utils.py)
- [control_policy_utils.py](<repo-root>/core/control_policy_utils.py)

### Output / Grounding / Runtime

- [output.py](<repo-root>/core/layers/output.py)
- [grounding_policy.py](<repo-root>/core/grounding_policy.py)
- [hub.py](<repo-root>/mcp/hub.py)
- [orchestrator.py](<repo-root>/core/orchestrator.py)

### Memory / Telemetrie

- [orchestrator.py](<repo-root>/core/orchestrator.py)
- `memory_fact_save`
- `workspace_event_save`

## Kritische Datenobjekte

### `thinking_plan`

Erzeugt in Thinking, mutiert in Policy-Shaping, gelesen in Control und Output.

Enthaelt u. a.:

- `intent`
- `needs_memory`
- `is_fact_query`
- `suggested_tools`
- `dialogue_act`
- `conversation_mode`

### `control_decision`

Erzeugt in Control, downstream read-only.

Wichtig:

- keine zweite Policy-Autoritaet in Runtime oder Output

### `execution_result`

Runtime-/Toolzustand.

Wichtig:

- darf Policy nicht neu entscheiden
- enthaelt Laufzeitstatus, Tool-Events und Grounding-Runtimewerte

## Kritische Uebergangspunkte

1. `selected_tools` -> `suggested_tools`
2. `dialogue_act` -> `conversation_mode`
3. `needs_memory` -> Kontext-Retrieval
4. `suggested_tools` -> Grounding-Evidence-Pflicht
5. `control_decision` -> tool_allowed / tool_blocked
6. `answer` -> Autosave / Memory

## Aktuell wichtigste Drift-Risiken

1. Bloesse Tool-Vorschlaege werden wie echte Tool-Nutzung behandelt
2. `needs_memory` wird zu schnell wie `is_fact_query` interpretiert
3. kurze soziale Turns bekommen unnoetig Tool-/Grounding-Last
4. Routing-/Gate-Status (`unavailable`, `pending_approval`) werden downstream als Technikfehler missverstanden
