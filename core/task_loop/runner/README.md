# Runner Structure

Dieser Ordner ist jetzt das aktive Package fuer `core.task_loop.runner`.

Aktueller Zustand:

- `core/task_loop/runner/__init__.py`
  Schlanker Package-Entry-Point mit direkten Re-Exports aus den fachlichen Runner-Modulen.

- `messages.py`
  Bereits ausgelagert. Enthält die User-sichtbaren Stop-, Waiting- und Risk-Gate-Texte.

- `snapshot_state.py`
  Bereits ausgelagert. Enthält Snapshot-/Step-State-Helfer.

- `chat_sync.py`
  Bereits ausgelagert. Enthält den reinen Sync-Chat-Loop inklusive Step-Run und Max-Step-Heuristik.

- `chat_async.py`
  Bereits ausgelagert. Enthält den produktiven Async-Batch-Pfad inklusive Control-/Output-/Orchestrator-Step-Run.

- `chat_stream.py`
  Bereits ausgelagert. Enthält den Stream-Pfad inklusive Stream-Chunk-Typ und Step-Streaming-Flow.

Ergebnis:

- kein `runner.pyback` mehr
- kein `exec`-Shim mehr
- stabile Surface bleibt `core.task_loop.runner.*`
