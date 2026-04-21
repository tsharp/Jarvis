# Core Layers

Die aktive Layer-Struktur lebt nicht mehr in einzelnen Top-Level-Dateien,
sondern ueberwiegend in Packages unter `core/layers/`.

## Aktiver Zustand

- `thinking.py`
  Einzelmodul fuer die Thinking-Schicht.

- `control/`
  Aktives Package fuer `core.layers.control`.
  Die fachlichen Bereiche liegen in:
  `runtime/`, `prompting/`, `policy/`, `tools/`, `strategy/`,
  `verification/`, `sequential/` und `cim/`.

- `output/`
  Aktives Package fuer `core.layers.output`.
  Die fachlichen Bereiche liegen in:
  `prompt/`, `generation/`, `grounding/`, `contracts/` und `analysis/`.

## Stable Import Surface

- `core.layers.thinking`
- `core.layers.control`
- `core.layers.output`

Die beiden Packages `control/` und `output/` halten diese Import-Surface
stabil, waehrend die Implementierung auf mehrere Module verteilt ist.

## Einordnung

- Thinking bleibt der Plan-/Intent-Pfad.
- Control bleibt der Verifikations-/Policy-Pfad.
- Output bleibt der Antwort-, Grounding- und Tool-Ausfuehrungspfad.

Die Detailverantwortungen der Packages sind in
`core/layers/control/README.md` und `core/layers/output/README.md`
dokumentiert.
