# TRION Chatflow Layer 4: Output + Grounding + Execution

## Rolle

Dieser Layer formuliert die Antwort, fuehrt Tools aus und prueft Grounding-/Evidence-Regeln.

Hier treffen sich:

- Persona
- Tool-Execution
- Grounding
- finale Antwortformulierung

## Hauptdateien

- [output.py](<repo-root>/core/layers/output.py)
- [grounding_policy.py](<repo-root>/core/grounding_policy.py)
- [orchestrator.py](<repo-root>/core/orchestrator.py)
- [hub.py](<repo-root>/mcp/hub.py)

## Inputs

- `verified_plan`
- `control_decision`
- Kontext
- Runtime-/Toolzustand

## Outputs

- finale Antwort
- Tool-Resultate
- Grounding-Statuswerte

## Teil-Gates in diesem Layer

### 1. Tool Execution Gate

Nur Tools, die durch Control erlaubt sind, duerfen wirklich laufen.

### 2. Grounding Precheck

Prueft:

- Faktenfrage?
- Tool-Evidenz vorhanden?
- fehlen verifizierbare Belege?

### 3. Grounding Postcheck

Prueft:

- neue unbelegte numerische Aussagen
- unbelegte qualitative Behauptungen

## Typische Drift-Risiken

1. bloesse Tool-Vorschlaege werden wie echte Tool-Ausfuehrung behandelt
2. konversationelle Turns fallen in Fakten-Fallbacks
3. Tool-Failures und Routing-Zustaende werden vermischt
4. Persona/Ton passt, aber Grounding blockiert unpassend

## Aktueller Kernbefund

Der kritischste Fehlerpfad im normalen Chatflow lag hier:

- `suggested_tools` vorhanden
- keine echte Tool-Evidenz
- sozialer Turn
- trotzdem Grounding-Fallback

Darum ist `conversation_mode` hier jetzt die zentrale Entkopplung:

- `conversational` darf nicht wegen bloesser Tool-Vorschlaege evidenzpflichtig werden

## Invariante

- Output darf keine neue Policy-Autoritaet werden
- Grounding muss streng fuer `tool_grounded` sein
- Grounding muss weich genug fuer `conversational` bleiben
