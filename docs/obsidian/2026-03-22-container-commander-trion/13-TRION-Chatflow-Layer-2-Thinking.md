# TRION Chatflow Layer 2: Thinking

## Rolle

Thinking analysiert die User-Anfrage und erzeugt den ersten strukturierten Plan.

## Hauptdateien

- [thinking.py](<repo-root>/core/layers/thinking.py)
- [tone_hybrid.py](<repo-root>/core/tone_hybrid.py)

## Inputs

- User-Text
- optional Memory-Kontext
- vorausgewaehlte Tools
- Tone-Signal

## Outputs

- `thinking_plan`

Typische Felder:

- `intent`
- `needs_memory`
- `memory_keys`
- `is_fact_query`
- `suggested_tools`
- `dialogue_act`
- `response_tone`
- `response_length_hint`
- `needs_sequential_thinking`

## Abhaengigkeiten

- Tool Selector
- Tone-Hybrid-Klassifikation
- ggf. Skills-/Memory-Kontext

## Gate-Charakter

Thinking ist kein Safety-Gate, aber ein semantisches Vor-Gate:

- es bestimmt die erste Form des Turns
- es kann bereits Drift erzeugen, wenn es zu viel Tool-/Memory-Last annimmt

## Typische Drift-Risiken

1. `needs_memory` wird zu oft gesetzt
2. `suggested_tools` bleiben fuer soziale Turns zu breit
3. `dialogue_act` ist richtig, aber downstream nicht stark genug
4. Follow-up-Kurzformen wie `ja bitte`, `und du?`, `mein name ist ...` sind besonders fehleranfaellig

## Aktuell wichtiger Architekturpunkt

`dialogue_act` allein reicht nicht.

Darum wurde jetzt zusaetzlich ein konzeptioneller `conversation_mode` eingefuehrt, der spaeter im Flow staerker fuer Routing und Grounding genutzt werden soll.

## Invariante

- Thinking plant
- Thinking fuehrt nicht aus
- Thinking blockiert nicht hart
