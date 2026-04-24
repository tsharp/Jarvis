# MCP Tool Authority Cleanup Implementationsplan

Erstellt am: 2026-04-12
Status: **Abgeschlossen**
Bezieht sich auf:

- [[2026-04-12-task-loop-control-first-turn-mode-implementationsplan]] - aktueller Task-Loop-Umbau und Tool-/Capability-Drift im sichtbaren Loop
- [[2026-03-22-container-commander-trion/15-TRION-Chatflow-Layer-3-Control]] - Single Control Authority als Kerninvariante
- [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]] - keine zweite Tool-/Policy-Wahrheit neben Control
- [[../TRION aufbau/Core/Core Grund system]] - Zielbild: Orchestrator als Fließband, nicht als Domänenhirn
- [[../TRION aufbau/Refactor/MCP Pipeline]] - Doppelte Buchführung in `mcp_registry.py` und `TOOL_KEYWORDS`
- [[../TRION aufbau/Core/Output]] - Native Tool Loop im Output als Architekturbruch
- [[../TRION aufbau/Core/Thinking]] - hartkodiertes Toolwissen und Seiteneingriffe in den MCP Hub

---

## Ist-Stand 2026-04-12

Der erste Refactor-Slice ist umgesetzt.
Der zweite Slice ist ebenfalls umgesetzt und testgruen.
Der dritte Slice ist ebenfalls umgesetzt und testgruen.
Der vierte Slice (Block E) ist jetzt ebenfalls umgesetzt und testgruen.

Bereits umgesetzt:

- `core/tool_exposure.py` existiert jetzt als gemeinsamer Read-Adapter fuer
  live entdeckte Tools aus `MCPHub.list_tools()`
- `core/layers/output.py` liest seine Toolliste fuer Prompt-Injection nicht
  mehr aus `mcp_registry.py:get_enabled_tools()`, sondern aus dem neuen
  Exposure-Adapter
- `mcp_registry.py:get_enabled_tools()` ist auf einen deprecated
  Kompatibilitaets-Shim reduziert und fuehrt keine statische Toolbeschreibung
  mehr
- `TOOL_KEYWORDS` und die statischen Basis-Detection-Strings liegen nicht mehr
  im Herzen von `mcp/hub.py`, sondern in `mcp/tool_prompt_hints.py`

Alle Bloecke vollstaendig umgesetzt.

Bewusst beibehaltene Reste:

- Hub generiert Detection Rules weiterhin fuer `_auto_register_tools` (graph-seitiger
  Speicherpfad); das ist kein Architekturbruch, da Thinking den Pfad nicht mehr nutzt

Neu umgesetzt in Slice 2:

- `core/orchestrator_sync_flow_utils.py` und
  `core/orchestrator_stream_flow_utils.py` bauen vor Thinking jetzt einen
  strukturierten Tool-Exposure-Snapshot statt rohe Toolnamen durchzureichen
- `core/task_loop/pipeline_adapter.py` nutzt fuer seinen Thinking-Call
  denselben Snapshot und haengt damit am gleichen Tool-Kontextvertrag wie der
  normale Flow
- `core/orchestrator_flow_utils.py` haengt den live initialisierten Hub als
  `orch.mcp_hub` an den Orchestrator, damit echte Runtime-Pfade den
  Exposure-Snapshot gegen `hub.list_tools()` aufloesen koennen
- `core/tool_exposure.py` faellt in Test-/Dummy-Pfaden ohne gesetzten Hub
  deterministisch auf strukturierte Platzhalter zurueck, statt still den
  globalen Hub zu initialisieren
- fokussierte Regression fuer Exposure + Thinking + Task-Loop ist gruen
  (`43 passed`)

---

## Anlass

TRION führt aktuell mehrere parallele Wahrheiten darüber, welche Tools es
gibt, wie sie beschrieben sind und wie Layer 0-3 sie kennen sollen.

Die sichtbarsten Symptome:

- `mcp_registry.py:get_enabled_tools()` beschreibt Tools erneut hartkodiert,
  obwohl der `MCPHub` sie live via `list_tools()` entdeckt
- `mcp/hub.py:TOOL_KEYWORDS` erzeugt statische Trigger-/Detection-Regeln in
  API-naher Kernlogik
- `Thinking` trägt eigenes hartkodiertes Toolwissen und zieht sich zusätzlich
  dynamische Regeln seitlich aus dem Hub
- `Output` importiert erneut eine Toolliste und betreibt zusätzlich einen
  eigenen Tool-Loop
- Task-Loop, normaler Orchestrator und Output benutzen dadurch nicht dieselbe
  Tool-Autorität

Das ist kein kleines Prompt-Problem, sondern ein Architekturbruch:

- doppelte Buchführung
- mehrfache Tool-Autoritäten
- Drift zwischen Discovery, Prompting, Planning und Ausführung

---

## Ziel

TRION bekommt **eine einzige Tool-Autorität**.

Konkret:

1. `mcp_registry.py` beschreibt nur noch MCP-Endpunkte, Transport und
   Enablement
2. Der `MCPHub` ist die einzige Live-Quelle für entdeckte Tools
3. Eine zentrale Tool-Exposure-Schicht bereitet diese Live-Tools für
   `Tool Selector`, `Thinking`, `Control`, `Task-Loop` und `Output` auf
4. Layer konsumieren Tool-Kontext nur noch über diese Exposure-Schicht
5. `Output` führt keine eigenständige zweite Tool-Welt mehr

Kurzform:

- Registry = MCP-Konfiguration
- Hub = Tool-Discovery
- Exposure = Tool-Kontext für Layer
- Control = Autorisierung
- Runner/Executor = Ausführung

---

## Nicht-Ziel

Dieser Plan baut bewusst **keine neue Tool-Logik neben dem Hub**.

Insbesondere nicht:

- eine neue statische Tool-Registry im Core
- eine zusätzliche Task-Loop-eigene Toolliste
- ein Thinking-eigenes Toolwissen aus hartkodierten Promptblöcken
- ein Output-eigenes Toolwissen aus `get_enabled_tools()`
- ein Regex-/Keyword-System im Hub als zweite Intent- oder Tool-Erkennung

---

## Architekturprinzipien

### 1. Single Tool Authority

Es darf nur eine Quelle dafür geben, welche Tools real im System verfügbar
sind:

- `MCPHub.list_tools()`

Alle anderen Toollisten sind abgeleitete Projektionen, keine Wahrheiten.

### 2. Registry ist Konfiguration, nicht Discovery

`mcp_registry.py` darf sagen:

- welcher MCP existiert
- wie er erreichbar ist
- ob er enabled ist

`mcp_registry.py` darf nicht sagen:

- welche konkreten Tools das System aktuell hat
- wie diese Tools fachlich beschrieben werden
- welche Triggerwörter das LLM dafür kennen soll

### 3. Prompting ist nicht Discovery

Toolbeschreibungen im Prompt sind nur eine Sicht auf bereits entdeckte Tools.
Sie dürfen keine zweite Autorität bilden.

### 4. Output ist kein Agent

Der Output-Layer darf Toolwissen konsumieren, aber keine eigene
Tool-Wahrheit und keine eigenständige Ausführungsschleife aufbauen.

### 5. Thinking bekommt Kontext injiziert

Thinking soll Toolkontext als Argument bekommen:

- live entdeckt
- optional angereichert
- aber nicht aus hartkodierten Domain-Blöcken oder Seiteneingriffen in den Hub

---

## Sollbild

### Heutiger problematischer Zustand

`Registry config -> Hub discovery -> mehrere statische/hartkodierte Layer-Toolwelten`

Beispiele:

- Registry beschreibt MCPs
- Hub entdeckt live Tools
- Registry beschreibt Tools nochmal
- Hub baut Keyword-Regeln
- Thinking hat hartkodiertes Toolwissen
- Output lädt erneut Toolwissen

### Zielzustand

`Registry config -> Hub discovery -> Tool exposure adapter -> Layer consumption`

Also:

1. Registry liefert nur MCP-Konfiguration
2. Hub entdeckt Tools live
3. Exposure-Adapter normalisiert Tool-Metadaten für Layer
4. Tool Selector / Thinking / Task-Loop / Output lesen dieselbe Sicht
5. Control autorisiert Nutzung
6. Executor/Orchestrator führen aus

---

## Neuer Contract

### Block A - MCP Registry auf reine Config reduzieren

Status: **umgesetzt**

`mcp_registry.py` behält:

- `MCPS`
- `get_enabled_mcps()`
- `get_mcps()`
- `get_mcp_config()`

`mcp_registry.py` verliert:

- `get_enabled_tools()`
- statische Toolbeschreibungen als Promptquelle

Akzeptanzkriterium:

- niemand im Runtime-Pfad liest Tooldefinitionen mehr aus `mcp_registry.py`

Ist-Stand:

- `mcp_registry.py:get_enabled_tools()` ist jetzt nur noch ein deprecated
  Kompatibilitaets-Shim auf `core.tool_exposure.list_live_tools()`
- die statische Parallelbeschreibung der Tools wurde aus der Runtime-Nutzung
  entfernt
- `get_enabled_tools()` vollstaendig geloescht; `warnings`-Import entfernt

### Block B - Tool Exposure Adapter einführen

Status: **teilweise umgesetzt**

Neues Zielobjekt, z. B.:

- `core/tool_exposure.py`

Verantwortung:

- `hub.list_tools()` konsumieren
- Fast-Lane-Tools sauber mergen
- einheitliche Normalform liefern:
  - `name`
  - `description`
  - `server`
  - `transport`
  - `tags`
  - `input_schema`
  - `visibility`
  - `execution_class`

Wichtig:

- das ist keine zweite Discovery
- nur ein normalisierter Read-Adapter auf Basis der echten Live-Tools

Akzeptanzkriterium:

- alle Layer koennen denselben Exposure-Snapshot konsumieren

Ist-Stand:

- `core/tool_exposure.py` liefert jetzt eine normalisierte Live-Sicht auf
  `hub.list_tools()`
- Output nutzt diesen Adapter bereits
- Thinking, normaler Orchestrator und Task-Loop konsumieren jetzt ebenfalls
  denselben formalisierten Exposure-Snapshot
- in Teilkontexten ohne echten Hub wird ein strukturierter Platzhalter-Snapshot
  genutzt, damit Tests und leichte Dummy-Orchestratoren nicht ungewollt den
  globalen Hub initialisieren
- noch offen sind weitere Layer sowie eine spaetere Vereinheitlichung der
  Hint-/Detection-Zufuhr

### Block C - TOOL_KEYWORDS aus Hub-Kernlogik herausziehen

Status: **teilweise umgesetzt**

`mcp/hub.py:TOOL_KEYWORDS` wird nicht mehr als API-nahe Kernlogik benutzt.

Zielbild:

- entweder komplett entfernen
- oder in eine reine Daten-/Prompt-Schicht auslagern
  - z. B. `core/tool_prompt_hints.py`
  - oder spaeter in `intelligence_modules`

Wichtig:

- keine Triggererkennung im Hub
- keine semantische LLM-Anleitung im Discovery-Layer

Akzeptanzkriterium:

- der Hub entdeckt Tools, aber interpretiert keine Nutzerintentionen mehr über
  Keyword-Mapping

Ist-Stand:

- `TOOL_KEYWORDS` und statische Basis-Detection-Rules liegen jetzt in
  `mcp/tool_prompt_hints.py`
- `mcp/hub.py` importiert diese Hint-Daten nur noch
- noch offen ist die eigentliche Entkopplung der Detection-Rule-Erzeugung aus
  dem Hub-Lifecycle

### Block D - Thinking auf Exposure statt Hardcode ausrichten

Status: **umgesetzt**

Thinking soll Tool-Kontext nur noch so bekommen:

- `available_tools`
- optionale, externe Tool-Hints
- optionale Addon-/RAG-Kontexte

Thinking soll nicht mehr:

- statische Tooltexte aus Registry importieren
- direkt Detection Rules aus dem Hub ziehen
- hartkodiertes Domänenwissen als primäre Toolwahrheit tragen

Akzeptanzkriterium:

- Thinking bleibt Plan-Layer, nicht Tool-Wissensautorität

Ist-Stand:

- Thinking bekommt in Sync-, Stream- und Task-Loop-Planning-Pfaden jetzt einen
  gemeinsamen strukturierten `available_tools`-Snapshot aus
  `core/tool_exposure.py`
- `ThinkingLayer.analyze_stream()` und `analyze()` haben jetzt einen
  optionalen `tool_hints`-Parameter und rufen den Hub nicht mehr selbst auf
- der `from mcp.hub import get_hub`-Import ist aus `thinking.py` entfernt
- `core/tool_exposure.py` stellt `build_detection_hints(hub=None)` bereit;
  alle drei Caller-Pfade (sync, stream, task-loop) bauen die Hints dort und
  reichen sie injiziert durch
- `mcp/hub.py` hat `get_detection_rules()` als public method, die
  `_generate_detection_rules()` delegiert (kein DB-Roundtrip)

### Block E - Output von zweiter Tool-Wahrheit entkoppeln

Status: **umgesetzt**

Output darf nicht mehr:

- `get_enabled_tools()` als Parallelquelle nutzen
- eine eigene Toolwelt im Prompt behaupten

Output soll:

- denselben Exposure-Snapshot lesen
- mittelfristig den Native Tool Loop verlieren oder strikt hinter denselben
  Kontrollvertrag gezogen werden

Akzeptanzkriterium:

- keine eigene Toolquelle mehr im Output-Layer

Ist-Stand:

- Output liest seine Prompt-Toolliste ueber `core/tool_exposure.py`
- `_get_ollama_tools()`, `MAX_TOOL_ITERATIONS` und `from mcp.hub import get_hub`
  wurden als totes Holz entfernt — der Native Tool Loop existierte nur noch als
  Kommentar; der Orchestrator hatte die Ausfuehrung laengst uebernommen
- Modul-Docstring korrigiert: kein "Native Tool Calling" mehr

---

## Betroffene Dateien

Direkt:

- `mcp_registry.py`
- `mcp/hub.py`
- `core/layers/thinking.py`
- `core/layers/output.py`
- `core/orchestrator.py`
- `core/orchestrator_pipeline_stages.py`
- `core/task_loop/pipeline_adapter.py`

Voraussichtlich neu:

- `core/tool_exposure.py`
- optional `core/tool_prompt_hints.py`

Indirekt:

- `tests/unit/test_frontend_stream_activity_contract.py`
- Task-Loop-/Thinking-/Output-/Hub-Tests

---

## Reihenfolge

### Block 1 - Exposure-Adapter bauen

Zuerst den gemeinsamen Read-Adapter auf Basis von `hub.list_tools()`.

Warum zuerst:

- ohne diesen Adapter fehlt der sichere Ersatz für `get_enabled_tools()`

### Block 2 - `get_enabled_tools()` entkoppeln und entfernen

Alle Leser auf den Exposure-Adapter umstellen.

### Block 3 - `TOOL_KEYWORDS` aus dem Hub herausziehen

Nicht im gleichen Schritt wie Discovery neu erfinden, sondern erst nach
stabilem Exposure-Pfad bereinigen.

### Block 4 - Thinking-Detection-Seiteneingriffe entfernen

Seiteneingriffe und harte Tool-Dopplung weiter abbauen, nachdem der gemeinsame
Exposure-Snapshot jetzt in Thinking und Task-Loop anliegt.

### Block 5 - Output-Ausfuehrungslogik bereinigen

Die Toolquelle ist bereits vereinheitlicht. Als naechstes muss die
Ausfuehrungsseite folgen: Native Tool Loop abbauen oder unter denselben
Kontrollvertrag ziehen.

---

## Offene Designfragen

1. Wie werden Fast-Lane-Tools im Exposure-Adapter formal markiert, ohne wieder
   eine Sonderwelt zu erzeugen?
2. Soll `TOOL_KEYWORDS` komplett verschwinden oder als reine Prompt-Hint-Daten
   kurzfristig erhalten bleiben?
3. Wie stark darf Thinking noch tool-spezifische Leitplanken enthalten, wenn
   `intelligence_modules` und Addon-Loader ausgebaut werden?
4. Wie wird Output mittelfristig vom Native Tool Loop getrennt, ohne aktuelle
   Features hart zu brechen?

---

## Akzeptanzkriterien Gesamt

- `mcp_registry.py` enthält keine statische Toolliste mehr
- `MCPHub.list_tools()` ist die einzige Tool-Discovery-Wahrheit
- Thinking, Task-Loop und Output lesen dieselbe Tool-Exposure
- es gibt keine zweite Toolbeschreibung im Registry-/Prompt-Pfad
- Hub enthält keine API-nahe Keyword-/Trigger-Logik mehr
- Task-Loop-/Thinking-/Output-Drift bei Toolwissen wird messbar kleiner
- Test-/Dummy-Pfade initialisieren nicht still den globalen Hub, nur um
  `available_tools` fuer Thinking zu materialisieren

---

## Erste Umsetzungssequenz

Wenn dieser Plan freigegeben wird, sollte der erste echte Code-Schnitt sein:

1. `core/tool_exposure.py` einführen
2. `mcp_registry.py:get_enabled_tools()` auf deprecated ziehen
3. erste Leser auf den Exposure-Adapter umstellen:
   - `Output`
   - Task-Loop-Planning
   - Thinking-Toolkontext
4. danach `TOOL_KEYWORDS` aus dem Hub herausziehen

Das ist der kleinste sinnvolle Einstieg, der sofort Architekturgewinn bringt,
ohne den gesamten Orchestrator in einem Zug umzubauen.
