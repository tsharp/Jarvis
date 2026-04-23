# Control Task-Loop Detection Benchmark

Dieser Benchmark misst, wie gut der `ControlLayer` erkennt, ob ein Turn als
`task_loop`, `single_turn` oder `interactive_defer` geroutet werden sollte.

Wichtig: Das ist **kein End-to-End-Benchmark**. Gemessen wird bewusst nur der
Control-Vertrag, damit Routing-Qualitaet isoliert sichtbar bleibt.

## Ziel

Der Benchmark beantwortet zwei Fragen:

1. Haelt sich der `ControlLayer` korrekt an seinen eigenen Routing-Vertrag?
2. Wie nah liegt dieses Routing an einer menschlichen Bewertung,
   ob ein Task-Loop eigentlich noetig waere?

Damit laesst sich sauber unterscheiden zwischen:

- **Control ist falsch**
- **Thinking/Signal-Qualitaet ist zu schwach**

## Messpunkt

Der Benchmark ruft ausschliesslich diesen Pfad auf:

- `ControlLayer.apply_corrections(...)`

Dadurch werden keine Tools ausgefuehrt und keine Output-/Task-Loop-Runtime
gestartet. Der Test misst nur die autoritativen Control-Felder:

- `_authoritative_execution_mode`
- `_authoritative_turn_mode`

## Datei

- Benchmark-Test: [test_control_task_loop_detection_benchmark.py](/home/danny/Jarvis/tests/unit/test_control_task_loop_detection_benchmark.py)

## Kategorien

Der Benchmark enthaelt aktuell **100 Testfaelle**:

- `explicit_task_loop_request`
- `visible_progress_multistep`
- `implicit_high_complexity`
- `active_task_loop_presence`
- `human_multistep_but_under_signaled`
- `clear_single_turn`
- `interactive_defer_confirmation`

Die Faelle decken bewusst sowohl klare als auch grenzwertige Situationen ab:

- explizite Task-Loop-Bitten
- ungenaue, aber faktisch mehrstufige Container-Anfragen
- normale Einmalfragen
- bestaetigungspflichtige Interaktionen
- Follow-up- und Re-Entry-Szenarien

## Ausfuehrung

```bash
pytest -q -s tests/unit/test_control_task_loop_detection_benchmark.py
```

Optional zusammen mit den direkten Turn-Mode-Vertragstests:

```bash
pytest -q -s \
  tests/unit/test_task_loop_turn_mode.py \
  tests/unit/test_control_task_loop_detection_benchmark.py
```

## Aktueller Stand

Stand dieser Doku: **2026-04-22**

Ergebnis nach der Signal-Haertung fuer Control:

```text
cases=100
contract_accuracy=100/100 (100.0%)
human_task_loop_recall=75/75 (100.0%)
human_task_loop_precision=75/75 (100.0%)
human_task_loop_accuracy=100/100 (100.0%)
```

Kategorie-Output:

```text
- active_task_loop_presence: total=10 contract=100.0% human_loop_rate=100.0% predicted_loop_rate=100.0%
- clear_single_turn: total=15 contract=100.0% human_loop_rate=0.0% predicted_loop_rate=0.0%
- explicit_task_loop_request: total=20 contract=100.0% human_loop_rate=100.0% predicted_loop_rate=100.0%
- human_multistep_but_under_signaled: total=15 contract=100.0% human_loop_rate=100.0% predicted_loop_rate=100.0%
- implicit_high_complexity: total=15 contract=100.0% human_loop_rate=100.0% predicted_loop_rate=100.0%
- interactive_defer_confirmation: total=10 contract=100.0% human_loop_rate=0.0% predicted_loop_rate=0.0%
- visible_progress_multistep: total=15 contract=100.0% human_loop_rate=100.0% predicted_loop_rate=100.0%
```

## Interpretation

`contract_accuracy`:
- Misst, ob Control genau das liefert, was laut aktuellem Control-Vertrag erwartet wird.

`human_task_loop_recall`:
- Misst, wie viele menschlich als mehrstufig bewertete Faelle auch wirklich als
  `task_loop` erkannt wurden.

`human_task_loop_precision`:
- Misst, ob Control zu aggressiv faelschlich in `task_loop` springt.

## Warum das nuetzlich ist

Dieser Benchmark ist interessant fuer GitHub, weil er die zentrale Architekturfrage
messbar macht:

- **Control darf dumm bleiben**
- **aber es muss robuste Signale korrekt erkennen**

Der Benchmark zeigt damit sehr klar, ob Verbesserungen wirklich aus

- besserem Signaling
- oder aus unsauberer Verlagerung von Thinking-Logik in Control

kommen.

## Grenzen

Der Benchmark misst nicht:

- echte Thinking-Qualitaet
- echte Tool-Ausfuehrung
- Output-Formulierung
- End-to-End-Task-Loop-Verhalten

Wenn dieser Benchmark gruen ist, heisst das nur:

**Wenn die Signale vorliegen, routed Control korrekt.**
