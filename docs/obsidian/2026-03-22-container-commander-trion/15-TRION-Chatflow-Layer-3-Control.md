# TRION Chatflow Layer 3: Control

## Rolle

Control ist die Policy-Autoritaet.

Es ist der Layer, der aus dem Plan eine bindende Freigabe- oder Warnentscheidung macht.

## Hauptdateien

- [control.py](<repo-root>/core/layers/control.py)
- [control_contract.py](<repo-root>/core/control_contract.py)
- [control_decision_utils.py](<repo-root>/core/control_decision_utils.py)
- [control_policy_utils.py](<repo-root>/core/control_policy_utils.py)

## Inputs

- User-Text
- geformter Plan
- kompakter Memory-/Kontextauszug

## Outputs

- `control_decision`
- Warnungen
- `final_instruction`

## Wichtige Prinzipien

1. Single Control Authority
2. `control_decision` ist downstream read-only
3. Runtime-/Tool-Fehler sind nicht automatisch Policy-Fehler

## Gate-Charakter

Das ist das haerteste eigentliche Entscheidungs-Gate im Chatflow.

Es entscheidet u. a.:

- approved / denied
- warn / hard_block
- Korrekturen fuer Planfelder

## Typische Drift-Risiken

1. routing-bedingte `unavailable`-Faelle werden downstream als harte Fehler gelesen
2. `pending_approval` wird spaeter wie Technikfehler behandelt
3. Output oder Runtime interpretiert Control-Zustaende neu

## Invariante

- nur Control trifft Policy-Entscheidungen
- Output und Executor lesen diese Entscheidungen nur
