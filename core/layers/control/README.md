# Control Layer Structure

Dieses Verzeichnis ist das aktive Package fuer `core.layers.control`.

## Aktiver Zustand

- `__init__.py`
  Package-Fassade fuer die stabile Import-Surface `core.layers.control`.
  Aktuell wird `layer.py` noch in den Package-Namespace geladen.

- `layer.py`
  Besitzermodul fuer `ControlLayer` und verbleibende Integrationslogik.
  Von hier aus werden die fachlichen Teilmodule zusammengesetzt.

- `runtime/`
  Model-, Timeout- und Endpoint-Aufloesung.

- `prompting/`
  Prompt-Konstanten und Payload-Aufbau fuer die Verifikation.

- `policy/`
  Deterministische Safety-, Warning-, False-Block- und Authority-Regeln.

- `tools/`
  Tool-/Skill-Normalisierung, Verfuegbarkeit und Tool-Entscheidung.

- `strategy/`
  Aufloesungsstrategie, Turn-Mode, Skill-Intent und Container-Selektion.

- `verification/`
  Default-Verifikation, Korrekturen, Stabilisierung und `verify_flow`.

- `sequential/`
  Sequential-Thinking-Prompts, Parsing, Sync- und Stream-Ausfuehrung.

- `cim/`
  CIM-Kontext und Policy-Engine-Integration.

## Einordnung

Der Control-Layer ist kein Refactor-Plan mehr, sondern ein live genutztes
Package. Die Subpackages oben sind bereits aktive Importziele von `layer.py`.

Die verbleibende Compat-Lage ist:

- `core.layers.control` bleibt der stabile Entry-Point
- `layer.py` bleibt vorerst die sichtbare Klassenoberflaeche
- `__init__.py` ist noch ein Compat-/Patch-Fassade, kein reiner Re-Export

## Ergebnis

- die fruehere Top-Level-Datei `core/layers/control.py` ist ersetzt
- die fachliche Logik liegt bereits in dem Package `core/layers/control/`
- die stabile Surface fuer Call-Sites bleibt `core.layers.control.*`
