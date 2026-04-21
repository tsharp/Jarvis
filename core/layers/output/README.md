# Output Layer Structure

Dieses Verzeichnis ist das aktive Package fuer `core.layers.output`.

## Aktiver Zustand

- `__init__.py`
  Package-Entry-Point fuer die stabile Import-Surface `core.layers.output`.
  `OutputLayer` wird von hier aus re-exportiert.

- `layer.py`
  Besitzermodul fuer `OutputLayer` und verbleibende Integrationslogik.
  Es verdrahtet die ausgelagerten Prompt-, Grounding- und Generationsteile.

- `prompt/`
  Aktive Prompt-Bausteine:
  `system_prompt.py`, `budget.py`, `tool_injection.py`.

- `generation/`
  Aktive Generierungspfade:
  `async_stream.py`, `sync_stream.py`, `tool_check.py`.

- `grounding/`
  Aktive Grounding-Module:
  `evidence.py`, `state.py`, `precheck.py`, `postcheck.py`,
  `fallback.py`, `stream.py`.

- `contracts/`
  Aktive Antwortkontrakte:
  `container.py` sowie das Package `skill_catalog/`
  mit `snapshot.py`, `trace.py` und `evaluation.py`.

- `analysis/`
  Aktive Analysehilfen:
  `numeric.py`, `qualitative.py`, `evidence_summary.py`.

## Einordnung

Das Output-Package ist live und ersetzt die fruehere Top-Level-Datei
`core/layers/output.py`.

Die bereits ausgelagerten Teilbereiche liegen in den oben genannten
Subpackages. `layer.py` bleibt aktuell noch der Integrationspunkt fuer:

- `OutputLayer` selbst
- verbleibende Contract-/Prompt-Regeln, die noch als Methoden an der Klasse
  haengen
- die Zusammensetzung von Control-Entscheidung, Runtime-Grounding und
  LLM-Ausgabe

## Ergebnis

- `core.layers.output` bleibt die stabile Import-Surface
- die Paketstruktur ist aktiv, nicht mehr nur Migrationsziel
- die Doku referenziert jetzt die tatsaechlich vorhandenen Module
