# TRION Chatflow Layer 5: Memory + Telemetry

## Rolle

Nach der Antwort speichert TRION:

- neue Fakten
- Assistant-Outputs
- Workspace-/Runtime-Events

Dieser Layer ist nachgelagert, aber wichtig, weil er spaetere Turns stark beeinflusst.

## Hauptdateien

- [orchestrator.py](<repo-root>/core/orchestrator.py)
- [context_manager.py](<repo-root>/core/context_manager.py)

## Inputs

- `conversation_id`
- `verified_plan`
- finale Antwort

## Outputs

- neue Memory-Fakten
- autosavebare Antwortinhalte
- Workspace-Events wie `control_decision` oder `chat_done`

## Wichtige Mechanik

### 1. Fact Save

Wenn `is_new_fact` gesetzt ist und Key/Value vorhanden sind:

- Speicherung ueber `memory_fact_save`

### 2. Autosave Guard

Autosave wird unterdrueckt, wenn:

- Grounding fehlte
- Toolphase fehlschlug
- Antwort leer oder qualitativ unbrauchbar ist

### 3. Workspace Events

Der Orchestrator speichert interne Ereignisse ueber:

- `workspace_event_save`

## Typische Drift-Risiken

1. schlechte Antworten werden trotzdem gespeichert und verstaerken spaetere Fehler
2. `needs_memory` und `is_new_fact` werden zu aggressiv aus fruehen Layers uebernommen
3. soziale Fakten wie Namen und Vorlieben brauchen einen anderen Pfad als harte Faktenfragen

## Aktueller offener Architekturpunkt

`social_memory` sollte explizit als eigener Typ behandelt werden:

- speicherbar
- aber nicht toolpflichtig
- nicht automatisch `is_fact_query`

Beispiel:

- `mein name ist danny`

Das ist eher:

- `social_memory_candidate = true`

und nicht:

- Tool-/Grounding-Fall

## Invariante

- Memory soll spaetere Konversation verbessern
- Memory darf Drift nicht durch Selbstverstaerkung verschlimmern
