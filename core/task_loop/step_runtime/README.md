# Step Runtime Structure

Dieser Ordner ist jetzt das aktive Package fuer `core.task_loop.step_runtime`.

Aktueller Zustand:

- `core/task_loop/step_runtime/__init__.py`
  Schlanker Package-Entry-Point mit direkten Re-Exports aus den fachlichen Step-Runtime-Modulen.

- `prompting.py`
  Bereits ausgelagert. Enthaelt den Prompt-Bau, die kleinen Meta-/Status-Helfer und
  nur noch generische artefaktbasierte Faktenbloecke.

- `render_contract.py`
  Bereits aktiv. Enthaelt den generischen Behauptungsrahmen dafuer, was ein
  `analysis_step`, `tool_request_step`, `tool_execution_step` oder `response_step`
  ueberhaupt sagen darf.

- `plans.py`
  Bereits ausgelagert. Enthält den Verified-Plan-Aufbau fuer einzelne Loop-Schritte.

- `requests.py`
  Bereits ausgelagert. Enthält die Materialisierung von `TaskLoopStepRequest`.

- `prepare.py`
  Bereits ausgelagert. Enthält den Prepare-Flow inklusive Control-Verify und `PreparedTaskLoopStepRuntime`.

- `execution.py`
  Bereits ausgelagert. Enthält Result-/Artifact-Helfer, Orchestrator-Ausführung, Output-Streaming und Fallback-Handling.

Ergebnis:

- kein `step_runtime.pyback` mehr
- kein `exec`-Shim mehr
- keine container-spezifische Policy mehr direkt im Prompt-Pfad
- stabile Surface bleibt `core.task_loop.step_runtime.*`
