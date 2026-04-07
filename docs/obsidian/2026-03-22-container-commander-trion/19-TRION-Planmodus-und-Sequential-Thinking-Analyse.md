# TRION Planmodus und Sequential Thinking

Erstellt am: 2026-03-25

## Zweck dieser Notiz

Diese Notiz dokumentiert zwei Dinge praezise anhand des aktuellen Repo-Stands:

1. wie der umgangssprachlich gemeinte `Whiteboard`- bzw. `Planmodus` fuer TRION technisch aufgebaut ist
2. wie `Sequential Thinking` aktuell funktioniert

Wichtig:

- Im aktuellen Code gibt es keinen echten technischen Begriff `whiteboard`.
- Was damit praktisch gemeint ist, sind heute die UI-Flaechen `Planmodus`, `Planning` und die zugehoerigen `planning_*`-Events.
- Fuer `Container Commander TRION shell` ist relevant, dass Shell-Control, Planmodus und Sequential Thinking drei verschiedene Dinge sind.

---

## 1. Wie funktioniert unser `Whiteboard` bzw. Planmodus fuer TRION?

## Kurzfassung

Der Planmodus ist kein einzelnes Modul, sondern ein Event-getriebenes Zusammenspiel aus:

- Live-Stream-Events aus dem Orchestrator
- Persistenz in `workspace_events`
- Replay dieser `workspace_events`
- Frontend-Renderer fuer Chat und TRION-Plugin

Technisch ist der Planmodus heute also eher ein `planning event ledger + UI renderer` als ein eigener agentischer Whiteboard-Speicher.

## Der Begriff `Whiteboard`

Im Repo existiert kein produktiver Identifier wie:

- `whiteboard`
- `withboard`
- `plan_mode`

Stattdessen wird das Konzept ueber diese Begriffe abgebildet:

- `planning_start`
- `planning_step`
- `planning_done`
- `planning_error`
- `Sequential Thinking`
- `Planning`-Tab
- `Planmodus (live)`

Die sauberste technische Formulierung ist deshalb:

- `Whiteboard` = die sichtbare Plan-/Checklist-Darstellung von `planning_*`- und teils `sequential_*`-Events

## Hauptbausteine

### A. Chat-Planbox im WebUI

Die normale Chat-Oberflaeche besitzt eine eigene Live-Planbox:

- `adapters/Jarvis/static/js/chat.js`
- `adapters/Jarvis/static/js/chat-plan.js`

Was dort passiert:

- `chat.js` behandelt `planning_*` und `sequential_*` als eigene Plan-Events.
- `chat-plan.js` baut daraus eine UI-Box `Planmodus (live)`.
- Diese Box zeigt Ereignisse einzeln an, z. B.:
  - `planning_start`
  - `planning_step`
  - `planning_done`
  - `planning_error`
  - `sequential_start`
  - `sequential_step`
  - `sequential_done`
  - `sequential_error`

Wichtig:

- Die Chat-Planbox ist ein Live-Renderer fuer den Stream.
- Sie ist nicht selbst die Datenquelle.

### B. Planning-Tab im TRION-Plugin

Das TRION-Runtime-Plugin `sequential-thinking` erzeugt drei Tabs:

- `Thinking`
- `Build`
- `Planning`

Datei:

- `trion/plugins/sequential-thinking/plugin.ts`

Das Plugin:

- hoert auf `sequential_start`, `seq_thinking_stream`, `sequential_step`, `sequential_done`, `sequential_error`
- pflegt daraus eine Checkliste im `Planning`-Tab
- pflegt daneben `Thinking` und `Build Activity`

Die Planning-Darstellung ist hier checklistenartig:

- abgeschlossene Schritte werden als `- [x]`
- der naechste Schritt als `- [ ]`

Wichtig:

- dieser Planning-Tab ist eine Visualisierung des Sequential-Laufs
- kein eigener Planner mit Schreibrechten

### C. Workspace-Events als Persistenzschicht

Der eigentliche haltbare Unterbau des Planmodus sind `workspace_events`.

Relevante Teile:

- `core/workspace_event_utils.py`
- `core/orchestrator.py`
- `adapters/admin-api/main.py`
- `adapters/Jarvis/static/js/workspace.js`

Der Flow:

1. Orchestrator oder Master erzeugen `planning_*`-Ereignisse.
2. Diese werden via `workspace_event_save` als interne Telemetrie gespeichert.
3. `workspace.js` laedt die Events spaeter ueber `/api/workspace-events`.
4. `workspace.js` re-spielt passende `planning_*`-Events wieder als synthetische `workspace_update`-SSEs mit `replay: true`.

Damit kann der Planstatus nach Reloads oder spaeterem UI-Oeffnen wieder aufgebaut werden.

### D. Der Sequential-Planning-Persistenzpfad

Fuer Sequential Thinking existiert ein kompakter Persistenzpfad:

- `core/workspace_event_utils.py`
- `core/orchestrator_stream_flow_utils.py`

`build_sequential_workspace_summary(...)` mappt:

- `sequential_start` -> `planning_start`
- `sequential_step` -> `planning_step`
- `sequential_done` -> `planning_done`
- `sequential_error` -> `planning_error`

Dabei wird absichtlich nur eine kompakte Pipe-Zeile gespeichert, z. B.:

- `task_id=... | step=2 | title=Collect Evidence | thought_len=742`

Das heisst:

- die Persistenz speichert keine vollstaendigen Gedankenbloeke
- sondern kompakte Telemetrie fuer UI-Rekonstruktion

### E. Der Master-Autonomy-Planpfad

Neben Sequential Thinking gibt es einen zweiten Planpfad:

- `core/master/orchestrator.py`
- `core/orchestrator_flow_utils.py`
- `core/orchestrator.py`

Der Master-Orchestrator emittiert ebenfalls:

- `planning_start`
- `planning_step`
- `planning_done`
- `planning_error`

Wichtige Details:

- Beim Initialisieren wird `orch.master.set_event_sink(orch._persist_master_workspace_event)` gesetzt.
- Dadurch werden Master-Planereignisse ebenfalls in `workspace_events` geschrieben.
- Die Inhalte sind hier keine Sequential-Step-Zusammenfassungen, sondern Phasen wie:
  - `phase=planning`
  - `decision=continue`
  - `next_action=...`
  - `phase=reflecting`

Das ist also ein zweiter Produzent von `planning_*`.

## Wichtige Praezisierung: Sequential-Planning und Master-Planning sind nicht dasselbe

Beide benutzen dieselben `planning_*`-Eventnamen, aber nicht dieselbe Semantik.

Sequential-Planning:

- kommt aus dem Sequential-Lauf
- `source_layer="sequential"`
- beschreibt Reasoning-Schritte

Master-Planning:

- kommt aus dem Master-Orchestrator
- `source_layer="master"`
- beschreibt Autonomie-/Loop-Phasen

Diese Unterscheidung ist wichtig, weil nicht jede UI beide Quellen gleich behandelt.

## Replay- und Hydrationsverhalten

### Chat/UI-Seite

`workspace.js` re-spielt allgemein alle `planning_(start|step|done|error)`-Events wieder in die UI.

Das ist relativ breit und source-layer-unabhaengig.

### TRION-Plugin-Seite

Das Plugin `trion/plugins/sequential-thinking/plugin.ts` hydriert Planning nur dann, wenn:

- `entry_type` mit `planning_` beginnt
- `source_layer === "sequential"`
- `replay === true`

Das bedeutet praktisch:

- Sequential-Planning wird nachgeladen und rekonstruiert
- Master-Planning wird dort aktuell nicht als Planning-Checklist hydriert

## Readiness / Voraussetzungen

Die Runtime-Readiness prueft fuer den Planmodus explizit:

- `sequential_thinking` bzw. Alias `think` / `think_simple`
- `workspace_event_save`
- `workspace_event_list`

Siehe:

- `adapters/admin-api/runtime_routes.py`

Implikation:

- ohne Sequential-Tool und ohne Workspace-Event-Tools ist der Planmodus funktional unvollstaendig

## Was hat das mit `Container Commander TRION shell` zu tun?

Hier liegt die wichtigste Abgrenzung:

- Der aktuelle `TRION shell`-Pfad ist **nicht** derselbe Mechanismus wie der Planmodus.

Die Shell-Routen liegen in:

- `adapters/admin-api/commander_api/containers.py`

Dort gibt es:

- `trion-shell/start`
- `trion-shell/step`
- `trion-shell/stop`

Was diese Routen tun:

- Shell-Session im Speicher fuehren
- letzte Shell-Aktion verifizieren
- naechsten Shell-Befehl per LLM ableiten
- Loop-Guards anwenden
- Session am Ende als `trion_shell_summary` in `workspace_events` speichern

Was sie **nicht** tun:

- keine `planning_start`
- keine `planning_step`
- keine `planning_done`
- kein automatisches Befuellen des Planning-Tabs

Kurz:

- der heutige TRION-Shellmodus hat eine eigene Session- und Summary-Logik
- aber keinen echten Anschluss an den Planning-/Whiteboard-Pfad

Das ist fuer spaetere Arbeiten wichtig, weil man sonst faelschlich annimmt, `TRION shell` benutze bereits denselben Plan-Backbone.

---

## 2. Wie funktioniert Sequential Thinking?

## Kurzfassung

Es gibt aktuell zwei relevante Sequential-Implementierungen:

1. den **live genutzten Sequential-Pfad im Control-Layer**
2. den **separaten MCP-Server `mcp-servers/sequential-thinking`**

Fuer den normalen TRION-Orchestrator und die sichtbaren Live-Sequential-Events ist heute der **Control-Layer-Streaming-Pfad** der wichtigere aktive Pfad.

Der MCP-Server existiert zusaetzlich als Tool-/Service-Pfad und als eigenstaendige Reasoning-Engine.

## 2.1 Trigger: Wann wird Sequential Thinking ueberhaupt angefordert?

Die Entscheidung beginnt im Thinking-Layer:

- `core/layers/thinking.py`

Der Thinking-Prompt erzeugt unter anderem:

- `needs_sequential_thinking`
- `sequential_complexity`
- `suggested_cim_modes`
- `reasoning_type`

Gedacht ist:

- einfache Fakten -> kein Sequential
- mehrschrittige, vergleichende, hypothetische oder komplexe Aufgaben -> Sequential

Der Thinking-Layer liefert also **nur das Signal**, nicht die eigentliche Ausfuehrung.

## 2.2 Policy-Gates vor dem Sequential-Lauf

Bevor Sequential wirklich laeuft, greifen mehrere Regeln.

### A. Container-Runtime-Fast-Path

In:

- `core/orchestrator_precontrol_policy_utils.py`

wird fuer bestimmte Container-Runtime-Requests Sequential explizit abgeschaltet:

- `needs_sequential_thinking = False`
- `_sequential_deferred = True`
- `_sequential_deferred_reason = "container_runtime_fast_path"`

Sinn:

- Container-/Host-Runtime-Anfragen sollen nicht unnoetig in langen Sequential-Laeufen haengen bleiben

### B. Interactive-Mode-Deferral

In:

- `core/orchestrator.py`

wird Sequential im `interactive`-Modus ab einer Konfigurationsschwelle deaktiviert und als aufgeschoben markiert:

- `_sequential_deferred = True`
- `_sequential_deferred_reason = interactive_mode_complexity_*`

Sinn:

- interaktive Antworten sollen nicht durch tiefe Sequential-Laeufe zu traege werden

Wichtig:

- Sequential kann also vom Thinking-Layer angefordert sein
- aber zur Laufzeit trotzdem bewusst unterdrueckt oder verschoben werden

## 2.3 Der aktive Live-Pfad: Control-Layer Streaming

Der fuer die sichtbare Sequential-UI entscheidende Pfad sitzt in:

- `core/orchestrator_stream_flow_utils.py`
- `core/layers/control.py`

### Ablauf

1. `orchestrator_stream_flow_utils.py` prueft:
   - `needs_sequential_thinking`
   - `sequential_thinking_required`
2. Falls aktiv:
   - Aufruf von `orch.control._check_sequential_thinking_stream(...)`
3. Die erzeugten Events werden:
   - live an die UI gereicht
   - zusaetzlich als Workspace-Telemetrie persistiert

### Was `_check_sequential_thinking_stream(...)` konkret macht

Datei:

- `core/layers/control.py`

Schritte:

1. erzeugt `task_id`, `complexity`, `reasoning_type`
2. emitttet `sequential_start`
3. versucht optional CIM-Kontext ueber `analyze`
4. baut daraus einen strikten System-Prompt
5. streamt Modellantwort live
6. unterscheidet zwischen:
   - `thinking`-Strom
   - finalem `content`
7. parsed das fertige `content` in einzelne `## Step N:`-Bloeke
8. emitttet pro Schritt `sequential_step`
9. emitttet zum Schluss `sequential_done`
10. bei Fehlern `sequential_error`

### Besonderheit des Live-Pfads

Der Live-Pfad ist kein Aufruf an den separaten MCP-Server `think`.

Stattdessen:

- ruft der Control-Layer das Modell direkt an
- benutzt optional CIM-Kontext
- streamt dabei echte Zwischeninhalte in die UI

Das ist fuer die Produktlogik wichtig:

- sichtbare Live-Sequential-Events in Chat/Plugin kommen aus diesem Streaming-Pfad
- nicht primaer aus `mcp-servers/sequential-thinking/sequential_thinking.py`

## 2.4 Event-Struktur des Live-Sequential-Pfads

Die wichtigsten Events sind:

- `sequential_start`
- `seq_thinking_stream`
- `seq_thinking_done`
- `sequential_step`
- `sequential_done`
- `sequential_error`

Semantik:

- `seq_thinking_stream` = laufender Gedankenstrom / Zwischenreasoning
- `sequential_step` = fertig geparster Schrittblock
- `sequential_done` = Lauf beendet, Zusammenfassung verfuegbar

Die UI kann dadurch sowohl:

- live mitlaufen
- als auch am Ende eine saubere Schrittliste anzeigen

## 2.5 Persistenz des Live-Sequential-Pfads

Nur ein Teil der Sequential-Events wird in Workspace-Telemetrie uebersetzt:

- `sequential_start`
- `sequential_step`
- `sequential_done`
- `sequential_error`

`seq_thinking_stream` wird **nicht** als voller Denktext in Workspace gespeichert.

Stattdessen wird nur kompakte Plan-Telemetrie gespeichert.

Das ist absichtlich so:

- weniger Speicherlast
- UI kann reloadbar bleiben
- keine riesigen Denkprotokolle im Workspace

## 2.6 Der separate MCP-Server `mcp-servers/sequential-thinking`

Parallel dazu existiert ein eigenstaendiger Sequential-Thinking-Server:

- `mcp-servers/sequential-thinking/sequential_thinking.py`

Diese Implementierung arbeitet anders:

1. optional `Memory.search()`
2. optional `CIM.analyze()`
3. genau **ein** Ollama-Call
4. Parsing der Antwort in Schritte
5. optional Step-Validation

Wichtige Merkmale:

- Single-shot statt Live-Step-Streaming
- eigener MCP-Service
- Tools:
  - `think`
  - `think_simple`
  - `health`

Die Architektur dort ist:

- `Memory Context`
- `CIM Roadmap`
- `Single Ollama Call`
- `Step Parsing`

Das ist also eher eine eigenstaendige Reasoning-Engine als die konkrete Live-UI-Implementierung des Chat-Sequential-Pfads.

## 2.7 Was ist aktuell die `Single Source of Truth`?

Das muss sauber getrennt beantwortet werden.

### Fuer sichtbares Live-Sequential im TRION-Chat / Planning-UI

Die operative Truth liegt heute bei:

- `core/layers/control.py`
- `core/orchestrator_stream_flow_utils.py`
- `core/workspace_event_utils.py`

### Fuer den separaten Sequential-MCP-Service

Die operative Truth liegt bei:

- `mcp-servers/sequential-thinking/sequential_thinking.py`

### Wichtig fuer spaetere Shell-Arbeiten

Der `Container Commander TRION shell`-Pfad benutzt aktuell **keinen** dieser beiden Sequential-Mechanismen direkt.

Er benutzt stattdessen:

- eine lokale Shell-Session
- eine Schritt-fuer-Schritt-LLM-Entscheidung pro User-Turn
- Verifikation der vorigen Aktion
- Loop-Guards
- Summary-Bridge bei `/stop`

Das ist funktional verwandt, aber architektonisch getrennt von Sequential Thinking.

---

## 3. Praktische Schlussfolgerung fuer die naechsten Arbeiten

Wenn wir etwas im `Container Commander TRION shell` bauen wollen, muessen wir drei Ebenen auseinanderhalten:

1. `TRION shell`
   - interaktive Shell-Control-Session pro Container
   - heute ohne echten Planning-Backbone

2. `Planmodus / Whiteboard`
   - UI fuer `planning_*`-Events
   - basiert auf Stream + Workspace-Persistenz + Replay

3. `Sequential Thinking`
   - eigener Reasoning-Mechanismus
   - im Live-Chat vor allem ueber den Control-Layer-Streaming-Pfad

Das bedeutet konkret:

- Wenn Shell einen sichtbaren Whiteboard-/Planmodus bekommen soll, muss Shell selbst `planning_*`- oder kompatible Events erzeugen oder adaptieren.
- Wenn Shell echtes Sequential Thinking nutzen soll, reicht es nicht, nur die vorhandene Shell-Step-Logik zu haben; man muesste bewusst den Control-/Sequential-Pfad integrieren oder einen Shell-spezifischen Planning-Emitter bauen.

---

## Relevante Dateien

- `core/layers/thinking.py`
- `core/layers/control.py`
- `core/orchestrator_stream_flow_utils.py`
- `core/workspace_event_utils.py`
- `core/master/orchestrator.py`
- `core/orchestrator.py`
- `core/orchestrator_flow_utils.py`
- `mcp-servers/sequential-thinking/sequential_thinking.py`
- `trion/plugins/sequential-thinking/plugin.ts`
- `adapters/Jarvis/static/js/chat-plan.js`
- `adapters/Jarvis/static/js/chat-sequential.js`
- `adapters/Jarvis/static/js/workspace.js`
- `adapters/admin-api/main.py`
- `adapters/admin-api/runtime_routes.py`
- `adapters/admin-api/commander_api/containers.py`
