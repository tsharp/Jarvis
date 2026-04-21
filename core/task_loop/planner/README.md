# Planner Structure

Dieser Ordner ist jetzt das aktive Package fuer `core.task_loop.planner`.

Aktueller Zustand:

- `core/task_loop/planner/__init__.py`
  Schlanker Package-Entry-Point mit direkten Re-Exports aus den fachlichen Planner-Modulen.

- `objective.py`
  Bereits ausgelagert. Enthält Objective-Cleaning, Intent-/Keyword-Helfer und Fallback-Erkennung.

- `specs.py`
  Bereits ausgelagert. Enthält die Step-Spezifikationen fuer Tool-, Container-, MCP- und Skill-/Cron-Pfade.

- `steps.py`
  Bereits ausgelagert. Enthält `TaskLoopStep`, die konkrete Step-Erzeugung und `build_task_loop_steps(...)`.

- `snapshots.py`
  Bereits ausgelagert. Enthält `create_task_loop_snapshot_from_plan(...)`.

Ergebnis:

- kein `planner.pyback` mehr
- kein `exec`-Shim mehr
- stabile Surface bleibt `core.task_loop.planner.*`
