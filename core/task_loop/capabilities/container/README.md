# Container Capability

Dieses Paket kapselt alle container-spezifischen Regeln fuer den Task-Loop.

## Aktiver Zustand

- `extractors.py`
  Aktive Freitext-Extraktion fuer Container-/Python-Felder und Container-Identitaet.
- `context.py`
  Aktiver strukturierter Capability-Kontext und Merge aus Snapshot/Artifacts/User-Reply.
- `discovery_policy.py`
  Aktive Read-first-Regeln wie `blueprint_list`, `container_list`, `container_inspect`.
- `flow.py`
  Aktive Planungsvorlagen fuer gemischte Discovery-/Request-Container-Flows.
- `request_policy.py`
  Aktive Blueprint-Auswahl, Discovery-Auswertung und sichtbare Choice-Gates
  fuer `request_container`.
- `parameter_policy.py`
  Aktive Pflichtfeldpruefung und gezielte Rueckfrage-Entscheidung.
- `recovery.py`
  Aktive Outcome-Klassifikation und naechster sicherer Tool-Pfad.
- `replan_policy.py`
  Aktive sichtbare Recovery-Zusammenfassung und Replan-Step-Bau fuer
  container-spezifische Recovery-Hinweise.

## Aktuelle Verantwortungen

In dieses Paket gehoert:
- container-spezifische Text-/Signal-Extraktion
- strukturierter `capability_context`
- Discovery-/Read-first-Regeln
- container-spezifische Flow-Blueprints fuer den Planner
- Blueprint-Auswahl und Choice-Gates fuer Container-Anfragen
- Pflichtfeldpruefung fuer Container-/Python-Container-Anfragen
- container-spezifische Recovery-Entscheidungen
- container-spezifische Replan-Narration und Recovery-Step-Bau

Nicht in dieses Paket gehoert:
- Prompt-Rendering
- generische Plan-Umschreibung
- User-sichtbare Narration ausserhalb capability-spezifischer Fakten

## Compat-Lage

Es gibt keine verbleibenden Top-Level-`container_*`-Compat-Dateien mehr.

Die eigentliche Runtime-Logik fuer Context, Discovery, Flow, Request, Parameter
und Recovery lebt bereits hier
im Paket `capabilities/container/`.
