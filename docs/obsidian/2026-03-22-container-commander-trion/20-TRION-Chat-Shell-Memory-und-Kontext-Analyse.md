# TRION Chat, Shell, Memory und Kontext

Erstellt am: 2026-03-25

Statushinweis (2026-03-26):

- Der vorbereitende Entflechtungsschnitt in `container_commander/engine.py` und `container_commander/mcp_tools.py` ist inzwischen umgesetzt.
- Der aktuelle operative Umsetzungsstand und die naechste Reihenfolge stehen in `22-TRION-Chat-Shell-Implementationsplan.md`.

## Zweck dieser Notiz

Diese Notiz beantwortet die Architekturfrage:

- Wie entstehen heute TRION-Erinnerungen?
- Wie werden sie abgerufen?
- Wo wird Chat-Kontext wirklich gehalten?
- Warum fuehlt sich `TRION shell` aktuell wie ein getrennter Modus an?
- Wie kann man Chat + Shell koppeln, ohne den Code mit Volltranskripten und Spezialfaellen zuzumüllen?

Wichtig:

- Diese Notiz beschreibt den aktuellen Stand.
- Sie ist absichtlich analytisch und trennt sauber zwischen:
  - Chat-History
  - SQL-Memory
  - Workspace-Telemetrie
  - Home-Memory
  - Shell-Session-State

---

## 1. Kurzfassung

Das wichtigste Architekturdetail ist:

- TRION hat **nicht einen einzigen Memory-Kanal**, sondern mehrere getrennte Kanaele.

Aktuell relevante Kanaele:

1. Frontend-Chat-History
2. SQL-Memory (`memory_save`, `memory_fact_save`, Graph/Semantic Search)
3. Workspace-Events (`workspace_event_save`, `workspace_event_list`)
4. taegliches Protokoll (`/api/protocol/append`, `memory/YYYY-MM-DD.md`)
5. Home-Memory (`container_commander/home_memory.py`)
6. flüchtiger Conversation-Runtime-State im Orchestrator
7. flüchtiger Shell-Session-State im Commander

Der Grund fuer das Fremdmodell-Gefuehl in der Shell ist aktuell:

- Die Shell nutzt fast nur **6 + 7**
- Der normale Chat nutzt stark **1 + 2 + 3 + 4 + 6**
- Die Shell schreibt am Ende nur ein `trion_shell_summary`-Event
- dieses Event fliesst heute **nicht sinnvoll in den normalen Chat-Kontext zurueck**

---

## 2. Woher kommt heute der normale Chat-Kontext?

## 2.1 Frontend-History ist der primaere Turn-Kontext

Im WebUI wird die Chat-History lokal im Browser gehalten:

- `adapters/Jarvis/static/js/chat-state.js`
- `adapters/Jarvis/static/js/chat.js`
- `adapters/Jarvis/static/js/api.js`

Wichtige Details:

- `chat-state.js` speichert `messages` in `localStorage`
- dazu auch die `conversation_id`
- `getMessagesForBackend()` schickt nur die letzten N Nachrichten zum Backend
- `api.js` sendet diese Nachrichten explizit in jedem `/api/chat`-Request

Das bedeutet:

- Der Server ist **nicht** die kanonische Vollquelle der Chat-History.
- Der direkte Dialogkontext kommt bei normalen Turns primaer aus:
  - `request.messages`
  - `conversation_id`

Praezise:

- Die Roh-History ist heute vor allem ein **client-seitig gehaltenes Request-Payload**
- nicht ein vollstaendig serverseitig rekonstruiertes Konversationsgedaechtnis

## 2.2 Das Backend verarbeitet diese History turnweise

Im Backend ist `CoreChatRequest` das zentrale Modell:

- `core/models.py`

Es enthaelt:

- `messages`
- `conversation_id`

Die Pipeline arbeitet dann jeweils auf diesem turnweisen Request.

Folge:

- Wenn ein Modus wie `TRION shell` nicht dieselbe History aktiv in `messages` oder aequivalenten Kontext einspeist, fuehlt er sich automatisch entkoppelt an.

---

## 3. Welche Memory-Arten speichert TRION im normalen Chat?

## 3.1 Freitext-Autosave der Assistant-Antwort

Nach einer normalen Antwort speichert der Orchestrator Assistant-Output ueber:

- `core/orchestrator.py`
- `mcp/client.py`

Pfad:

- `orchestrator._save_memory(...)`
- `autosave_assistant(...)`
- `memory_save(...)`

Was gespeichert wird:

- freier Assistant-Text
- `conversation_id`
- `role="assistant"`
- Layer, typischerweise `stm`

Wichtige Bedingung:

- Autosave ist gegatet
- schlechte oder ungroundete Antworten werden bewusst **nicht** gespeichert

Skip-Gruende sind unter anderem:

- fehlende Evidenz
- Grounding-Violation
- Tool-Failure mit leerer Antwort
- Pending Intent Confirmation
- Duplicate-Window

Das ist wichtig:

- TRION speichert nicht blind jeden Output
- sondern versucht Selbstverstaerkung schlechter Antworten zu vermeiden

## 3.2 Strukturierte Fakten

Wenn der verifizierte Plan eine neue Tatsache enthaelt:

- `is_new_fact = true`
- `new_fact_key`
- `new_fact_value`

dann speichert der Orchestrator:

- `memory_fact_save`

Dateien:

- `core/orchestrator.py`
- `sql-memory/memory_mcp/tools.py`

Dabei werden:

- strukturierte Fakten in SQL gespeichert
- Embeddings erzeugt
- Graph-Nodes gebaut

Das ist also der sauberste Pfad fuer dauerhafte, explizite Fakten.

## 3.3 Daily Protocol

Das WebUI appended nach Chat-Antworten auch in das taegliche Protokoll:

- `adapters/Jarvis/static/js/chat.js`
- `adapters/admin-api/protocol_routes.py`

Gespeichert wird:

- `user_message`
- `ai_response`
- `conversation_id`

Kontextseitig wird das spaeter vor allem fuer Zeitbezug genutzt:

- `ContextManager._load_daily_protocol(...)`

Das Protokoll ist also:

- eher ein chronologisches Journal
- nicht der primaere semantische Memory-Store

## 3.4 Workspace-Events

Der Orchestrator speichert daneben interne Telemetrie:

- `observation`
- `control_decision`
- `chat_done`
- `planning_*`
- Tool-/Container-Ereignisse

Pfad:

- `core/orchestrator.py`
- `core/orchestrator_stream_flow_utils.py`

Diese Workspace-Events dienen:

- UI-Observability
- kompakter Kontextbildung
- nicht primär als voller Dialogspeicher

---

## 4. Wie wird Memory im normalen Chat wieder abgerufen?

## 4.1 ContextManager ist der zentrale Retrieval-Baustein

Datei:

- `core/context_manager.py`

Der ContextManager baut Kontext aus mehreren Quellen:

- TRION-Gesetze
- aktive Container
- System-Tools
- Skills
- Blueprints
- Daily Protocol
- User-/System-Memory

Wichtig:

- Retrieval ist budgetiert
- multi-context
- fallbacks werden kontrolliert angewendet

## 4.2 Memory-Abruf ist `needs_memory`- und `memory_keys`-gesteuert

Thinking liefert:

- `needs_memory`
- `memory_keys`
- `is_fact_query`
- `needs_chat_history`

Dann entscheidet `ContextManager.get_context(...)`:

- ob ueberhaupt Memory gesucht wird
- welche Keys gesucht werden
- in welchem Umfang gesucht wird

Wesentlich:

- `memory_keys` sind ein Routing-Mechanismus
- keine freie Volltext-Konversationsrekonstruktion

## 4.3 Retrieval passiert nicht nur in einem einzigen Speicher

Je nach Fall kommen zusammen:

- strukturierte Facts
- Graph Search
- Semantic Search
- Fallback-Suche
- System-Context

Der ContextManager durchsucht:

- die aktuelle `conversation_id`
- optional auch `system`

Das erzeugt den Eindruck von „TRION erinnert sich“, ist aber technisch:

- ein gezieltes Retrieval
- kein einfaches Wiedereinlesen kompletter Chatprotokolle

## 4.4 Workspace-Events fuer Small/Compact Context

Fuer kleine Modelle oder kompakte Kontexte baut TRION aus `workspace_events` einen NOW/RULES/NEXT-Block:

- `ContextManager.build_small_model_context(...)`
- `core/context_cleanup.py`

Wichtig:

- `workspace_event_list` wird geladen
- daraus wird `TypedState` gebaut
- daraus entsteht kompakter Laufzeitkontext

Das ist ein extrem wichtiger Pfad fuer „Gefuehl von Kontinuitaet“, aber:

- er verarbeitet nur erkannte Event-Typen
- nicht automatisch beliebige neue Event-Arten

---

## 5. Welche conversation-spezifischen Zustände haelt TRION zusaetzlich im RAM?

Neben gespeichertem Memory existiert flüchtiger Runtime-State im Orchestrator.

## 5.1 Container-State pro Conversation

Datei:

- `core/orchestrator.py`

Relevant:

- `_conversation_container_state`
- `_remember_container_state(...)`
- `_get_recent_container_state(...)`

Das speichert pro `conversation_id` z. B.:

- letzter aktiver Container
- bekannter Home-Container
- bekannte Containerliste

Das ist wichtig:

- Es ist kein dauerhaftes Memory
- aber es erzeugt starke Kontinuitaet ueber Folgefragen

Genau dieser State wird bereits von `TRION shell` teilweise befuellt:

- `adapters/admin-api/commander_api/containers.py`
- `_remember_container_state(...)`

Das ist heute der wichtigste bestehende Beruehrungspunkt zwischen Shell und normalem Chat.

## 5.2 Grounding-Carryover pro Conversation

Ebenfalls im Orchestrator:

- `_conversation_grounding_state`

Das speichert:

- juengste Tool-Runs
- juengste Evidenz

Zweck:

- Carry-over von Grounding/Evidence in Folge-Turns

## 5.3 Conversation Consistency State

Dateien:

- `core/orchestrator.py`
- `core/conversation_consistency.py`

Hier werden stance-/themenbezogene Aussagen kurzfristig pro Conversation gehalten, z. B.:

- ob etwas erlaubt oder nicht erlaubt gesagt wurde
- um spaetere Widersprueche zu erkennen

Auch das ist:

- flüchtiger Konsistenzstate
- kein vollwertiger Memory-Store

---

## 6. Was macht `TRION shell` heute mit Erinnerung und Kontext?

## 6.1 Shell hat einen eigenen Session-State

Datei:

- `adapters/admin-api/commander_api/containers.py`

Pro Session wird im RAM gehalten:

- `conversation_id`
- `container_id`
- `container_name`
- `blueprint_id`
- `language`
- `commands`
- `user_requests`
- `last_reply`
- `last_command`
- `last_shell_tail`
- `last_verification`
- `last_stop_reason`
- `step_history`

Das ist lokal fuer die Shell-Session sehr nuetzlich.

Aber:

- dieser State ist nicht Teil des normalen Chat-History- oder Memory-Retrieval-Pfads

## 6.2 Shell speichert am Ende nur ein Summary-Event

Beim Stop:

- wird aus der Session eine strukturierte Zusammenfassung gebaut
- diese wird als `trion_shell_summary` in `workspace_events` gespeichert

Wichtig:

- Das ist **kein** `memory_save`
- **kein** `memory_fact_save`
- **kein** editierbarer Workspace-Eintrag
- **kein** standardisierter Event-Typ, den `context_cleanup.py` semantisch auswertet

## 6.3 Shell-Events gelangen heute kaum in den normalen Chat-Kontext

Das ist der Kern des Problems.

`trion_shell_summary` wird zwar gespeichert, aber:

- `context_cleanup.py` kennt diesen Event-Typ nicht
- `build_small_model_context(...)` gewinnt daraus aktuell keinen semantischen Kontext
- der normale Chat nutzt ihn daher nicht sinnvoll fuer Folgeantworten

Praezise:

- Shell speichert heute Erinnerungen hauptsaechlich als **isolierte Telemetrie**
- nicht als **normal nutzbaren Konversationskontext**

## 6.4 Was Shell heute schon mit Chat teilt

Es gibt trotzdem drei geteilte Bruecken:

1. gleiche `conversation_id`
2. Container-State-Seed via `_remember_container_state(...)`
3. dieselben Runtime-Fakten ueber Container/Addons im Shell-Step-Prompt

Das reicht fuer operative Shell-Kontrolle, aber nicht fuer das Gefuehl:

- „ich rede mit demselben TRION wie im Chat“

---

## 7. Rolle von Home-Memory

Es gibt noch einen weiteren Speicher:

- `container_commander/home_memory.py`
- API unter `adapters/admin-api/trion_memory_routes.py`

Das ist ein file-backed Notizspeicher mit:

- Importance-Threshold
- Forced Keywords
- Policy / Redaction
- `remember_note`
- `recent_notes`
- `recall_notes`

Wichtig:

- Das ist **nicht** derselbe Kanal wie normales SQL-Memory.
- Der normale Chat-ContextManager zieht Home-Memory aktuell nicht automatisch.
- Home-Memory ist eher ein separater TRION-Home-/Notizspeicher.

Folgerung:

- Home-Memory ist fuer Shell-Integration allein keine gute Standardloesung
- sonst baut man einen weiteren Sonderpfad statt einer echten Vereinheitlichung

---

## 8. Warum fuehlt sich Shell aktuell wie ein Fremdmodell an?

Technisch kommen mehrere Ursachen zusammen.

## 8.1 Shell bekommt nicht dieselbe Chat-History

Normale Chat-Turns:

- erhalten `request.messages`
- also explizite Verlaufshistory aus dem Frontend

Shell-Turns:

- nutzen stattdessen nur `instruction`
- Shell-Tail
- Session-State
- Runtime-Fakten
- Addon-Kontext

Es fehlt also die normale dialogische Rueckbindung.

## 8.2 Shell schreibt nicht in denselben semantischen Memory-Kanal

Normale Chat-Antworten:

- koennen in `memory_save`
- Fakten in `memory_fact_save`

Shell:

- schreibt am Ende nur `trion_shell_summary`

Dadurch entstehen keine semantisch leicht wiederauffindbaren Shell-Erinnerungen im normalen Retrieval-Kanal.

## 8.3 Shell-Summary wird vom Kompaktkontext nicht verstanden

Weil `context_cleanup.py` `trion_shell_summary` nicht als bekannten Event-Typ verarbeitet, wird daraus kein NOW/RULES/NEXT-Wissen.

## 8.4 Shell ist aktuell ein separater Prompt-Loop

Der Shell-Step-Prompt ist gezielt gebaut fuer:

- naechsten Shell-Befehl
- Verifikation der letzten Aktion
- Loop-Guards

Das ist sinnvoll, aber es ist eben ein eigener Denkkanal.

---

## 9. Was ist der sauberste Integrationsansatz ohne Code-Muell?

## Grundprinzip

Nicht versuchen:

- kompletten Shell-Transcript in normalen Chat-Memory zu kippen
- jede Shell-Zeile als Event zu speichern
- zwei vollstaendige Konversationssysteme zu verheiraten

Sondern:

- nur **verdichtete Shell-Erkenntnisse**
- in **denselben semantischen Kanaelen**
- mit **klaren Event-/Memory-Typen**

## 9.1 Was man nicht tun sollte

### A. Volltranskript speichern

Schlecht, weil:

- zu laut
- zu viel Rauschen
- hohe Drift-Gefahr
- Retrieval wird unpraezise

### B. Home-Memory als Primärbrücke missbrauchen

Schlecht, weil:

- weiterer Sonderpfad
- nicht im normalen ContextManager-Flow
- erhoeht Systemkomplexitaet statt sie zu senken

### C. Shell einfach an `request.messages` ankleben

Allein unzureichend, weil:

- Shell hat eigene Runtime-Semantik
- das eigentliche Problem ist nicht nur History, sondern gemeinsame Retrieval-Faehigkeit

## 9.2 Sauberer Minimalansatz

Architektonisch am saubersten wirkt:

1. Shell-Session behält ihren lokalen RAM-State
2. Shell schreibt nur verdichtete checkpoints / summaries
3. diese checkpoints werden in einen bereits verstandenen Kanal überführt
4. normaler Chat kann diese checkpoints dann abrufen

Die zwei besten Kandidaten dafuer sind:

### Option A: Workspace-kompatible, typisierte Shell-Events

Also nicht nur:

- `trion_shell_summary`

sondern semantisch verwertbare Events wie:

- `observation`
- `note`
- oder ein neuer Event-Typ, den `context_cleanup.py` explizit versteht

Nutzen:

- gleiche Telemetrie-/Compact-Context-Pipeline
- wenig neue Infrastruktur

### Option B: gezieltes `memory_save` fuer Shell-Summary-Kernaussagen

Nicht das Vollprotokoll, sondern nur z. B.:

- Ziel der Session
- wichtigste Findings
- welche Aenderungen wirklich gemacht wurden
- offener Blocker

Nutzen:

- gleicher semantischer Retrieval-Kanal wie normaler Chat
- spaetere Follow-up-Fragen koennen shellbezogene Erinnerung ueber denselben Memory-Mechanismus finden

## 9.3 Empfohlene Trennung der Datenebenen

Die sauberste Zielarchitektur waere:

### Ebene 1: Shell-Operativzustand

- bleibt lokal in der Shell-Session
- kurzlebig
- detailreich

### Ebene 2: Shell-Checkpoint / Summary

- pro sinnvoller Sessionphase oder beim Stop
- kompakt
- menschenlesbar
- fuer Chat anschlussfaehig

### Ebene 3: Semantischer Langzeitwert

Nur wenn wirklich relevant:

- veraenderte Konfiguration
- festgestellte Ursache
- wiederkehrender Workaround
- userrelevante Entscheidung

Diese Ebene sollte in:

- `memory_save`
- und eventuell strukturiert in Faktenform

nicht in Volltranskriptform

---

## 10. Konkrete Design-Folgerung fuer Chat + Shell

Wenn das Ziel ist:

- Shell soll sich wie dieselbe Person / dasselbe TRION anfuehlen

dann braucht man **keinen** riesigen Unified-Transcript.

Man braucht stattdessen drei Dinge:

1. gleiche `conversation_id`
2. einen gemeinsamen verdichteten Erinnerungskanal
3. optional gezielte Rueckinjektion der letzten Shell-Zusammenfassung in Folge-Turns

Das heisst praktisch:

- der Chat muss nicht jede Shellzeile kennen
- aber er muss die letzten relevanten Shell-Erkenntnisse kennen

Und umgekehrt:

- die Shell muss nicht die gesamte Chat-History kennen
- aber sie sollte die letzten relevanten Chat-Ziele, Constraints und offenen Punkte kennen

---

## 11. Praezises Architektururteil

### Was heute gut ist

- Chat-Memory ist bereits mehrstufig und relativ robust
- Autosave ist gegatet
- Container-State wird conversation-spezifisch getragen
- Workspace-Events bilden eine gute Observability-Schicht
- Shell hat bereits vernuenftigen lokalen Session-State

### Was heute die Luecke ist

- Shell erzeugt keinen normal gut retrievbaren semantischen Follow-up-Kontext
- `trion_shell_summary` bleibt weitgehend isoliert
- Chat-History und Shell-History laufen parallel statt ueber eine gemeinsame Summary-Schicht verbunden zu sein

### Was man deshalb vermeiden sollte

- mehr Sonderspeicher
- mehr Volltranskripte
- mehr ad-hoc Prompt-Kleberei

### Was wahrscheinlich richtig ist

- Shell-Summary in einen vom normalen Chat verstandenen kompakten Memory-/Workspace-Pfad ueberfuehren
- nicht die rohe Shell-Sitzung, sondern nur ihre verdichteten Erkenntnisse

---

## Relevante Dateien

- `adapters/Jarvis/static/js/chat-state.js`
- `adapters/Jarvis/static/js/chat.js`
- `adapters/Jarvis/static/js/api.js`
- `core/models.py`
- `core/context_manager.py`
- `core/context_cleanup.py`
- `core/orchestrator.py`
- `core/orchestrator_stream_flow_utils.py`
- `core/conversation_consistency.py`
- `mcp/client.py`
- `sql-memory/memory_mcp/tools.py`
- `adapters/admin-api/protocol_routes.py`
- `adapters/admin-api/commander_api/containers.py`
- `container_commander/home_memory.py`
- `adapters/admin-api/trion_memory_routes.py`
