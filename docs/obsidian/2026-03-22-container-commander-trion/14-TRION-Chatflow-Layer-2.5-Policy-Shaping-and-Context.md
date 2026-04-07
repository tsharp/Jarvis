# TRION Chatflow Layer 2.5: Policy Shaping + Context

## Rolle

Zwischen Thinking und Control passiert in TRION bereits viel operative Formung des Plans.

Das ist der sensibelste Drift-Bereich.

Hier werden:

- Plan-Schema normalisiert
- Tone-/Dialogsignale eingearbeitet
- Query-Budget angewendet
- Domain-Route angewendet
- Precontrol-Konflikte aufgeloest
- Kontext aus Memory/System geladen

## Hauptdateien

- [orchestrator_policy_signal_utils.py](<repo-root>/core/orchestrator_policy_signal_utils.py)
- [orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
- [orchestrator_precontrol_policy_utils.py](<repo-root>/core/orchestrator_precontrol_policy_utils.py)
- [context_manager.py](<repo-root>/core/context_manager.py)
- [orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)
- [orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)

## Inputs

- `thinking_plan`
- `tone_signal`
- `selected_tools`
- `user_text`
- Chat-History

## Outputs

- `verified_plan`-Vorstufe
- angereicherter Kontext

## Teil-Gates in diesem Layer

### 1. Dialogue Control

- `dialogue_act`
- `response_tone`
- `response_length_hint`

### 2. `conversation_mode`

Neu als Router-Feld:

- `conversational`
- `factual_light`
- `tool_grounded`
- `mixed`

### 3. Query Budget

Entscheidet:

- Thinking skippen?
- Toollast reduzieren?
- Antwortbudget begrenzen?

### 4. Domain Route

Klassifiziert z. B.:

- `CONTAINER`
- `SKILL`
- `CRONJOB`

### 5. Precontrol Policy Resolver

Loest Konflikte zwischen:

- Domain-Lock
- Query-Budget
- Tool-Intent
- Memory-Forcing

### 6. Context Retrieval

Liefert:

- Memory-Daten
- System-/Toolwissen
- Laws / Runtime-Kontext

## Typische Drift-Risiken

1. `needs_memory` wird zu schnell wie Faktenpflicht behandelt
2. Domain-Lock uebersteuert konversationelle Turns
3. `suggested_tools` bleiben nach Guards im Plan und loesen spaeter Grounding aus
4. Kontext-Retrieval holt persoenliche Memory-Signale und wird downstream faelschlich als Faktenmodus gelesen

## Der aktuell kritischste Uebergang

- `selected_tools` / `suggested_tools`
- plus kurzer Input
- plus kein echter Toollauf
- plus Grounding

Genau dort entstehen unpassende Antworten wie:

- `Ich habe aktuell keinen verifizierten Tool-Nachweis ...`

## Invariante

- Dieser Layer darf den Plan formen
- er darf ihn aber nicht in eine versteckte zweite Safety-Autoritaet verwandeln
