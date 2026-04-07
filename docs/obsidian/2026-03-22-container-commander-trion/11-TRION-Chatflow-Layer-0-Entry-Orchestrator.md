# TRION Chatflow Layer 0: Entry + Orchestrator

## Rolle

Dieser Layer nimmt Requests entgegen und fuehrt den Gesamtfluss zusammen.

Er ist kein einzelner Modell-Layer, sondern der operative Rahmen fuer:

- Sync-Chat
- Stream-Chat
- Event-Emission
- Layer-Reihenfolge

## Hauptdateien

- [main.py](<repo-root>/adapters/admin-api/main.py)
- [bridge.py](<repo-root>/core/bridge.py)
- [orchestrator.py](<repo-root>/core/orchestrator.py)
- [orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)
- [orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)

## Inputs

- WebUI-/API-Request
- Chat-History
- Request-Metadaten
- evtl. forcierter Response-Mode (`interactive`, `deep`)

## Outputs

- finale Chat-Antwort
- Streaming-Events
- Workspace-/Telemetry-Events

## Wichtige Aufgaben

1. Request entgegennehmen
2. Tone-Signal klassifizieren
3. Tool Selector aufrufen
4. Thinking starten oder skippen
5. Plan formen und verifizieren
6. Output ausfuehren
7. Memory und Events speichern

## Abhaengigkeiten

- Layer 1 Tool Selector
- Layer 2 Thinking
- Layer 2.5 Policy-Shaping / Context
- Layer 3 Control
- Layer 4 Output / Grounding / Execution
- Layer 5 Memory / Telemetrie

## Gates in diesem Layer

### 1. Short-Input-Bypass

Im Sync-/Stream-Flow werden bei sehr kurzen Inputs teils Core-Tools injiziert.

Risiko:

- kurze soziale Turns koennen unnoetig in Toolpfade kippen

### 2. Thinking-Skip durch Query-Budget

Wenn Query-Budget einen Fast-Path erkennt, wird Thinking reduziert oder uebersprungen.

Risiko:

- falscher Skip bei semantisch kurzen, aber kontextabhaengigen Turns

## Typische Drift-Risiken

1. Der Orchestrator fuehrt zu frueh Toolkontext ein.
2. Der Orchestrator normalisiert zu spaet den echten Konversationsmodus.
3. Stream- und Sync-Pfad koennen leicht auseinanderdriften, wenn neue Guards nur in einem Pfad landen.

## Invariante

- Der Orchestrator darf Reihenfolge und Datenfluss steuern.
- Er darf aber nicht heimlich eine zweite Policy-Autoritaet neben Control werden.
