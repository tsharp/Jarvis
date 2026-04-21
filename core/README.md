# Core Architecture

Dieses Verzeichnis ist der aktive Kern der TRION-Laufzeit.

Die fruehere Beschreibung als starre "4-Layer-Architektur" mit festen
Modellannahmen ist nicht mehr aktuell. Der heutige Stand ist:

- ein produktiver `PipelineOrchestrator`
- drei aktive Haupt-Layer unter `core/layers/`
- ein ausgelagerter Satz von `orchestrator_modules/` fuer Routing-, Policy-,
  Kontext-, Output- und Runtime-Helfer
- ein eigener `task_loop/`-Bereich fuer mehrschrittige Ausfuehrung
- typed Contracts fuer die Trennung von Policy-Entscheidung und Runtime-Result

## Aktive Hauptbausteine

- `bridge.py`
  Rueckwaertskompatible Fassade. `CoreBridge` delegiert an den
  `PipelineOrchestrator`, haelt aber die bestehende Singleton-/Patch-Surface.

- `orchestrator.py`
  Produktiver Integrationspunkt fuer Request-Verarbeitung, Streaming,
  Layer-Verdrahtung, MCP-Hub-Anbindung, Grounding, Tool-Ausfuehrung,
  Workspace-Events und Task-Loop-Einstieg.

- `layers/`
  Aktive Layer-Struktur:
  `thinking.py`, `control/`, `output/`.
  Details dazu stehen in `core/layers/README.md`.

- `orchestrator_modules/`
  Aus dem Monolithen herausgezogene Hilfsmodule fuer:
  `context/`, `policy/`, `runtime/`, `execution/`, `output/`,
  `workspace_events.py`, `postprocess.py`, `interaction_runtime.py`
  und `task_loop.py`.

- `task_loop/`
  Mehrschrittige Chat-/Tool-Ausfuehrung mit eigener Planner-, Step-Runtime-
  und Runner-Struktur sowie container-spezifischen Capability-Paketen.
  Details dazu stehen in `core/task_loop/README.md`.

- `control_contract.py`
  Typed Contracts fuer den Single-Authority-Pfad:
  `ControlDecision` ist die Policy-Autoritaet,
  `ExecutionResult` beschreibt nur Runtime-Ergebnisse.

## Layer-Einordnung

- Thinking
  Intent-, Plan- und Kontextvorbereitung.

- Control
  Verifikation, Policy, Tool-Entscheidung, Turn-Mode-/Strategie-Autoritaet
  und Safety-Normalisierung.

- Output
  Prompt-Zusammensetzung, Grounding, Contract-Pruefung, Antwortgenerierung
  und Tool-nahe Ausgabepfade.

Es gibt weiterhin einen `tool_selector.py`, aber dieser ist heute ein
Hilfsbaustein des Orchestrators und keine separat dokumentierte "Layer 0"
im Sinne einer eigenen stabilen Architekturgrenze.

## Task-Loop-Einordnung

Der Task-Loop ist kein externer Sonderpfad mehr, sondern in den Orchestrator
integriert. Die relevanten Eintrittspunkte liegen in:

- `core/orchestrator_modules/task_loop.py`
- `core/task_loop/chat_runtime.py`
- `core/task_loop/runner/`
- `core/task_loop/step_runtime/`
- `core/task_loop/planner/`

Der Loop nutzt die echten `ControlLayer`- und `OutputLayer`-Instanzen fuer
aktive Schritte weiter und haelt den Zustandsverlauf ueber den Task-Loop-Store
und Workspace-Events sichtbar.

## Typischer Laufzeitfluss

1. Request kommt ueber `CoreBridge` oder direkt in den `PipelineOrchestrator`.
2. Der Orchestrator sammelt Kontext, Runtime-Signale und Policy-Hinweise.
3. Thinking erzeugt oder ergaenzt den Arbeitsplan.
4. Control verifiziert den Plan und bleibt die Autoritaet fuer Policy,
   Korrekturen, Warning-/Block-Signale und erlaubte Tools.
5. Output erzeugt die Antwort bzw. fuehrt freigegebene Tools aus und haelt
   Grounding-/Contract-Regeln ein.
6. Bei mehrschrittigen Aufgaben uebernimmt der Task-Loop die Schrittfuehrung
   und bindet denselben Control-/Output-Pfad erneut pro Schritt ein.

## Stable Surface

Die relevanten stabilen Import-/Patch-Surfaces sind:

- `core.bridge`
- `core.orchestrator`
- `core.layers.thinking`
- `core.layers.control`
- `core.layers.output`
- `core.task_loop.*`

Die interne Implementierung ist inzwischen deutlich staerker in Packages und
Hilfsmodule aufgeteilt, aber diese sichtbaren Entry-Points bleiben die
entscheidenden Andockstellen.
