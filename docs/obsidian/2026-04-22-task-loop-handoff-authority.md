# Task-Loop Handoff Authority

## Problem

Bei aktiven Task-Loops drifteten zuvor zwei Ebenen auseinander:

- Der `ControlLayer` markierte aktive Loops semantisch oft schon als
  `continue_active_task_loop`.
- Das eigentliche Routing konnte danach aber korrekt entscheiden, den Loop nur
  als `context_only` im Hintergrund zu behalten.

Dadurch entstanden drei Probleme:

1. Thinking- und Routing-Trace erzaehlten nicht dieselbe Geschichte.
2. UI/Debugging konnten nicht sauber unterscheiden zwischen
   "aktiver Loop vorhanden" und "dieser Turn resuemt den Loop wirklich".
3. Die semantische Autoritaet fuer Resume-vs-Background war ueber mehrere
   Schichten verteilt.

## Architekturentscheidung

### 1. Control bleibt Runtime-Schutz, nicht Resume-Autoritaet

Wenn `_task_loop_active=True` im Plan steht, darf Control weiterhin
`execution_mode=task_loop` und `turn_mode=task_loop` materialisieren.

Wichtig:

- Der Control-Reason-Code lautet hier nur noch `active_task_loop_present`.
- Dieser Code bedeutet ausschliesslich:
  "Es gibt einen aktiven Loop, also darf der Turn nicht in einen
  ungesicherten Direct-/Skip-Pfad kippen."
- Er bedeutet **nicht**:
  "Dieser Turn setzt den Loop sicher fort."

### 2. Routing ist die einzige Resume-vs-Background-Autoritaet

Die finale Entscheidung faellt in:

- `core/task_loop/active_turn_policy.py`
- `core/orchestrator_modules/task_loop_routing.py`

Dort wird aus User-Text, Snapshot und verifiziertem Plan entschieden:

- `continue_active_task_loop`
- `restart_active_task_loop`
- `terminate_active_task_loop_cancelled`
- `terminate_active_task_loop_mode_shift`
- `terminate_active_task_loop_blocked`
- `active_task_loop_context_only`

Die eigentliche Erklaerung wird ueber Routing-Detailcodes geliefert:

- `explicit_continue_request`
- `runtime_resume_candidate`
- `explicit_restart_request`
- `explicit_cancel_request`
- `meta_turn_background_preserved`
- `independent_tool_turn_background_preserved`
- `authoritative_task_loop_non_resume_background`
- `background_loop_preserved`
- `blocked_by_authoritative_turn_mode`
- `mode_shift_clear_active_loop`

## Produktregeln

Fuer aktive Loops in `WAITING_FOR_USER` oder `BLOCKED` gilt:

1. `weiter` resuemt den aktiven Loop.
2. Ein echter Runtime-Resume-Kandidat resuemt den aktiven Loop.
3. Meta-Fragen laufen im normalen Orchestrator, der Loop bleibt als
   Hintergrund-Kontext erhalten.
4. Unabhaengige Tool-/Discovery-Fragen laufen im normalen Orchestrator, der
   Loop bleibt ebenfalls erhalten.
5. Explizites `stoppen` beendet den aktiven Loop.
6. Ein expliziter neuer Task-Loop-Start startet einen neuen Loop.

## Trace-Vertrag

Die UI muss beide Ebenen getrennt sehen:

- **Control-/Thinking-Ebene**
  - `authoritative_execution_mode`
  - `authoritative_turn_mode`
  - optional `active_task_loop_present`

- **Routing-/Handoff-Ebene**
  - `task_loop_active_reason`
  - `task_loop_active_reason_detail`
  - `task_loop_routing_branch`
  - `runtime_resume_candidate`
  - `background_preservable`
  - `meta_turn`
  - `independent_tool_turn`

Damit gilt:

- `task_loop` im Control-Mode bedeutet nur "Loop praesent".
- Erst `task_loop_active_reason` + `task_loop_active_reason_detail` sagen,
  ob der Turn wirklich ein Resume ist oder nur den Loop im Hintergrund laesst.

## Betroffene Dateien

- `core/layers/control/strategy/execution_mode.py`
- `core/layers/control/strategy/turn_mode.py`
- `core/orchestrator_control_skip_utils.py`
- `core/task_loop/active_turn_policy.py`
- `core/orchestrator_modules/task_loop_routing.py`
- `core/orchestrator_stream_flow_utils.py`
- `adapters/Jarvis/static/js/chat-thinking.js`
- `adapters/Jarvis/static/js/chat-plan.js`

## Kurzform

Control sagt: `active_task_loop_present`

Routing sagt:

- `continue_active_task_loop` + `runtime_resume_candidate`
oder
- `active_task_loop_context_only` + `meta_turn_background_preserved`
oder
- `active_task_loop_context_only` + `independent_tool_turn_background_preserved`

Genau diese Trennung ist jetzt der Architekturvertrag.
