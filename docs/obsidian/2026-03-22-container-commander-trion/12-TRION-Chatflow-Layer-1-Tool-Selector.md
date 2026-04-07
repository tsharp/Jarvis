# TRION Chatflow Layer 1: Tool Selector

## Rolle

Der Tool Selector reduziert die Werkzeugmenge vor dem eigentlichen Reasoning.

Aktueller Stand:

- nur noch Semantic Search
- kein eigener LLM-Entscheider mehr

## Hauptdateien

- [tool_selector.py](<repo-root>/core/tool_selector.py)
- [hub.py](<repo-root>/mcp/hub.py)

## Inputs

- `user_text`
- optional `context_summary` aus letzter Assistant-Nachricht

## Outputs

- Liste von Tool-Kandidaten
- oder `None`, wenn kein sinnvoller Kandidat gefunden wurde

## Abhaengigkeiten

- MCP Hub
- `memory_semantic_search`
- Tool-Registrierung im Graph / Knowledge Layer

## Wichtige Mechanik

1. kurze Inputs koennen mit `context_summary` angereichert werden
2. Semantic Search liefert Kandidaten
3. Namen werden spaeter an Thinking / Orchestrator weitergegeben

## Gate-Charakter

Das ist ein weiches Vorauswahl-Gate:

- es sollte Tools vorschlagen
- aber keine harte Toolpflicht erzeugen

## Typische Drift-Risiken

1. kurze Inputs wie `ja`, `danke`, `mein name ist danny` koennen semantisch unpassend angereichert werden
2. Tool-Kandidaten werden downstream wie echte Tool-Nutzung behandelt
3. fehlende Semantic Search fuehrt zu inkonsistenten Toolpfaden zwischen Sessions

## Invariante

- Tool Selector darf nur Kandidaten liefern
- er darf keine Evidenzpflicht und keine Policy-Entscheidung erzeugen
