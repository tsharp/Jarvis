# TRION Chatflow Analyse

Erstellt am: 2026-03-24

Diese Notizserie dokumentiert den normalen TRION-Chatflow getrennt von `gaming-station`, Container Commander und Marketplace.

Ziel:

- den Chatflow als Pipeline sichtbar machen
- Layer sauber trennen
- Abhaengigkeiten und Gates explizit benennen
- Drift-/Fehlblockierungsrisiken dokumentieren

## Inhalt

- [[10-TRION-Chatflow-Dependencies]]
- [[11-TRION-Chatflow-Layer-0-Entry-Orchestrator]]
- [[12-TRION-Chatflow-Layer-1-Tool-Selector]]
- [[13-TRION-Chatflow-Layer-2-Thinking]]
- [[14-TRION-Chatflow-Layer-2.5-Policy-Shaping-and-Context]]
- [[15-TRION-Chatflow-Layer-3-Control]]
- [[16-TRION-Chatflow-Layer-4-Output-Grounding-and-Execution]]
- [[17-TRION-Chatflow-Layer-5-Memory-and-Telemetry]]

## Kerngedanke

Der wichtigste Architekturpunkt ist:

- `Thinking` plant
- `Control` entscheidet
- `Executor/Runtime` fuehrt aus
- `Output` formuliert und grounded

Fehlblockierungen entstehen in TRION meistens nicht innerhalb eines einzelnen Layers, sondern an den Uebergaengen zwischen:

- Tool-Vorschlag
- Domain-/Budget-Signalen
- Control-Entscheidung
- Grounding-/Evidence-Pflicht
