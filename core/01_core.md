# Core Modul Dokumentation (`/core`)

Das `/core`-Modul ist der aktive Laufzeitkern des Systems. Hier laufen
Orchestrierung, Layer-Verdrahtung, Policy-Entscheidungen, Grounding,
Tool-Ausfuehrung und mehrschrittige Task-Loops zusammen.

## Wichtige Einstiegspunkte

- `bridge.py`
  Rueckwaertskompatible Fassade. `CoreBridge` stellt weiter `get_bridge()`
  bereit, delegiert die produktive Verarbeitung aber an den
  `PipelineOrchestrator`.

- `orchestrator.py`
  Produktiver Integrationspunkt fuer Request-Verarbeitung, Streaming,
  Layer-Aufrufe, MCP-Hub-Anbindung, Workspace-Events und Task-Loop-Einstieg.

- `models.py`
  Zentrale Request-/Response-Typen wie `CoreChatRequest` und
  `CoreChatResponse`.

- `layers/`
  Aktive Layer-Struktur mit `thinking.py`, `control/` und `output/`.

- `orchestrator_modules/`
  Ausgelagerte Hilfsmodule fuer Kontext, Policy, Runtime, Execution, Output
  und Workspace-Event-Pfade.

- `task_loop/`
  Eigener Bereich fuer mehrschrittige Planung, Step-Runtime und Runner.

## Laufzeitbild

Der produktive Request-Pfad ist heute:

1. `CoreBridge` oder ein direkter Call landet im `PipelineOrchestrator`.
2. Der Orchestrator sammelt Kontext, Runtime-Signale und Routing-Hinweise.
3. Thinking bereitet Intent und Arbeitsplan vor.
4. Control verifiziert Plan, Policy und erlaubte Tools.
5. Output erzeugt Antwort, fuehrt freigegebene Tools aus und haelt
   Grounding-/Contract-Regeln ein.
6. Falls noetig uebernimmt der `task_loop/`-Bereich die mehrschrittige
   Weiterfuehrung derselben Aufgabe.

## Datenmodelle

- `CoreChatRequest`
  Tragt Messages, `conversation_id`, Modellwahl und Adapter-Metadaten.

- `CoreChatResponse`
  Tragt Inhalt, `done_reason` und die Rueckgabe fuer Sync-/Stream-Caller.

- `Message`
  Standardformat fuer Chat-Nachrichten im Core-Pfad.

## Architektur-Hinweise

- `CoreBridge` bleibt wichtig als Compat-Surface, ist aber nicht mehr der
  alleinige Besitzort der Pipeline-Logik.
- Die eigentliche Implementierung ist inzwischen stark in Packages und
  `orchestrator_modules/` aufgeteilt.
- `core/layers/control` und `core/layers/output` sind aktive Packages, keine
  alten Top-Level-Dateien mehr.
- Der Task-Loop ist in die normale Orchestrierung integriert und kein
  separater Nebenpfad.

## Wichtig zu beachten

> [!IMPORTANT]
> **Async Flow**: Die Kernpfade sind asynchron und fuer Streaming ausgelegt.
> Blockierende Aufrufe im produktiven Pfad bleiben riskant.
> **Compat Surface**: `get_bridge()` existiert weiter fuer bestehende Call-Sites
> und Tests, auch wenn die eigentliche Laufzeit im `PipelineOrchestrator`
> lebt.
> **Referenzdoku**: Fuer die aktuelle Detailstruktur sind
> `core/README.md`, `core/layers/README.md` und `core/task_loop/README.md`
> die massgeblichen Uebersichten.
