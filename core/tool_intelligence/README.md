# Tool Intelligence Module

Dieses Paket ist der Zielort fuer tool-nahe Fehlererkennung, Loesungssuche
und gezielte Retry-/Reflection-Helfer.

## Aktiver Zustand

- `manager.py`
  Zentrale Fassade `ToolIntelligenceManager`.
  Sie kombiniert Fehlererkennung, Suche nach frueheren Loesungen und
  optionalen Auto-Retry.

- `error_detector.py`
  Aktive Fehlererkennung und Fehlerklassifikation.
  Erkennt nicht nur Top-Level-`error`-Felder, sondern auch semantische
  verschachtelte Fehler in Tool-Resultaten.

- `auto_search.py`
  Aktive Suche nach frueheren Loesungen.
  Nutzt zwei Quellen:
  den `archive_manager` und Workspace-Eintraege aus der SQLite-DB
  unter `/app/memory_data/memory.db`.

- `auto_retry.py`
  Verfuegbarer Retry-Helfer fuer retrybare Fehler.
  Wird vom Manager lazy aktiviert, wenn:
  ein Fehler als retrybar klassifiziert ist,
  ein `tool_hub` vorhanden ist
  und Original-Args vorliegen.

- `reflection_loop.py`
  Verfuegbarer Regel-Helfer fuer eine alternative zweite Tool-Runde.
  Das Modul ist im Paket exportiert, aber nicht der zentrale Standardpfad des
  `ToolIntelligenceManager`.

## Paketrolle

Dieses Paket sitzt logisch zwischen Tool-Ergebnisbewertung und moeglicher
Recovery:

1. Tool-Resultat wird auf echte Fehler geprueft.
2. Fehler werden in retrybar vs. nicht retrybar klassifiziert.
3. Fruehere aehnliche Loesungen koennen aus Workspace/Archiv geholt werden.
4. Bei passenden Fehlern kann ein gezielter Retry mit korrigierten Args
   erfolgen.

## Integrationslage

Die produktive Integration laeuft ueber `core/orchestrator.py`.

Dabei gilt:

- `ToolIntelligenceManager` ist der sichtbare Entry-Point des Pakets.
- `detect_tool_error(...)` wird auch direkt vom Orchestrator importiert.
- `AutoRetry` ist kein reiner "Phase-3-Platzhalter" mehr, sondern ein
  vorhandener Hilfsbaustein.
- `ReflectionLoop` ist verfuegbar, aber nicht als Standardpfad dieser README
  zu behandeln wie der Manager-Pfad.

## Stable Surface

Das Paket exportiert ueber `core.tool_intelligence`:

- `ToolIntelligenceManager`
- `detect_tool_error`
- `classify_error`
- `AutoSearch`
- `AutoRetry`
- `ReflectionLoop`
