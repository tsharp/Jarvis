# TRION Chat + Shell Implementationsplan

Erstellt am: 2026-03-25

## Zweck dieser Notiz

Diese Notiz uebersetzt die bisherigen Analysen in einen konkreten Umsetzungsplan.

Sie beantwortet:

- in welcher Reihenfolge der Umbau passieren sollte
- welche minimalen Implementationsschnitte sinnvoll sind
- welche Komponenten betroffen sind
- woran man erkennt, dass die jeweilige Phase fertig ist

Basis dieser Notiz:

- [[19-TRION-Planmodus-und-Sequential-Thinking-Analyse]]
- [[20-TRION-Chat-Shell-Memory-und-Kontext-Analyse]]
- [[21-TRION-Chat-Shell-CIM-und-Control-Analyse]]

Wichtig:

- Das ist ein Implementationsplan, kein Code.
- Der Plan ist absichtlich auf kleine, kontrollierbare Schnitte ausgelegt.
- Ziel ist nicht ein Big-Bang-Umbau, sondern ein stabiler Ausbau des bestehenden Shell-Pfads.

---

## 1. Zielbild

Am Ende soll sich `TRION shell` nicht mehr wie ein Fremdmodus anfuehlen, sondern wie dieselbe TRION-Instanz in einem anderen Arbeitsmodus.

Dafuer braucht der Zielstand drei Dinge gleichzeitig:

1. einen gemeinsamen Missionskontext zwischen Chat und Shell
2. einen formalen Shell-Control-Modus statt isolierter Sonderlogik
3. eine semantische Memory-Bruecke von Shell zurueck in den Chat

Nicht Ziel:

- komplettes PTY-Transkript speichern
- normale Chat-Control auf jeden Shell-Schritt zwingen
- globale CIM-Regeln einfach nur weicher machen

---

## 2. Leitprinzipien fuer die Umsetzung

## 2.1 Eine Identitaet, zwei Modi

- `Chat Mode` bleibt der normale Thinking/Control/Output-Flow.
- `Shell Mode` wird ein eigener Arbeitsmodus mit eigener Schrittlogik.
- Beide Modi muessen aber denselben Aufgabenkontext und dieselbe Erinnerungsschicht teilen.

## 2.2 Safety nicht lockern, sondern anders schneiden

Hart bleiben:

- Secrets / Credential-Exfiltration
- destructive Aktionen ohne klaren Auftrag
- Host-Escape / Boundary-Verletzungen
- malware-/abuse-artige Muster

Anders geregelt werden:

- Diagnosebefehle
- Verifikationsschritte
- Wiederholungsstopps
- Dialog-/Prompt-Erkennung
- kurze Follow-up-Turns

## 2.3 Memory nur verdichtet speichern

Speichern:

- Ziel
- gepruefte Hypothese
- ausgefuehrte Checks
- tatsaechliche Aenderungen
- Blocker
- naechster sinnvoller Schritt

Nicht speichern:

- komplettes PTY-Log
- jede Shell-Zeile
- jede Wiederholung als eigener Langzeitfakt

---

## 3. Empfohlene Umsetzungsreihenfolge

Die Reihenfolge ist bewusst so gewaehlt, dass zuerst die semantische Kopplung entsteht und erst danach tiefere Shell-Autonomie.

1. gemeinsame Memory-Bruecke herstellen
2. gemeinsamen Mission-State beim Handoff einfuehren
3. Shell-Control-Modus formalisieren
4. UI-/Chat-Rueckkopplung sichtbar machen
5. erst danach Mikro-Loops oder teilautonome Mehrschrittlogik

Grund:

- Wenn zuerst Shell-Autonomie ausgebaut wird, aber Chat und Memory weiter getrennt bleiben, fuehlt sich das System trotz besserer Shell weiter fragmentiert an.

---

## 4. Implementationsphasen

## Vor Phase 0: gezielter Entflechtungsschnitt in Container Commander

### Warum dieser Schritt jetzt sichtbar dokumentiert werden muss

Einige zentrale Commander-Module sind inzwischen so gross geworden, dass die eigentlichen TRION-Chat/Shell-Phasen dort unnoetig riskant und schwer testbar werden.

Betroffen:

- `container_commander/engine.py` (~2450 Zeilen)
- `container_commander/mcp_tools.py` (~2385 Zeilen)
- `container_commander/blueprint_store.py` (~977 Zeilen)

Wichtig:

- Das ist **kein** separater Big-Bang-Refactor vor der eigentlichen Umsetzung.
- Es ist ein kleiner vorbereitender Entflechtungsschnitt, damit die nachfolgenden Phasen kontrolliert implementiert werden koennen.
- Ziel ist bessere Modulgrenze, nicht Verhaltensaenderung.

### Prioritaet

1. `container_commander/engine.py` zuerst
2. `container_commander/mcp_tools.py` direkt danach
3. `container_commander/blueprint_store.py` nur soweit entflechten, wie Phase 1/2 es wirklich braucht

### Begruendung der Reihenfolge

`engine.py` mischt aktuell Lifecycle, Runtime-Overrides, Approval, Trust-Gates, Secret-Injection, Health/Readiness, Quota, TTL/Recovery und Connection-Helfer in einem Modul. Das ist der groesste strukturelle Risikotreiber fuer die kommenden Shell-Memory-, Mission-State- und Control-Schnitte.

`mcp_tools.py` mischt Tool-Dispatcher, Gaming-Blueprint-Sonderlogik, Home-Container-Tools, Blueprint-Creation, Discovery und Autonomy-Cron-Verwaltung. Das erschwert jede saubere Erweiterung des Shell-Pfads ueber MCP-/Tool-Grenzen.

`blueprint_store.py` ist zwar ebenfalls gross, hat aber bereits vergleichsweise klarere interne Bloecke. Deshalb nicht zuerst gross anfassen, sondern nur gezielt in Richtung CRUD/Serialization, Migrationen und Graph-Sync trennen.

### DoD fuer diesen vorbereitenden Schnitt

- keine neue Produktfunktion
- keine aenderung am externen API-/Tool-Verhalten
- nur Verantwortlichkeiten aus grossen Dateien in kleinere interne Module verschieben
- bestehende Tests bleiben gruen oder werden nur dort angepasst, wo Importpfade intern sauber nachgezogen werden muessen

### Statusstand nach dem umgesetzten Prep-Schnitt

Stand: 2026-03-26

Erledigt:

- `container_commander/engine.py` wurde in mehreren Schritten entflechtet und von ~2450 auf ~1412 Zeilen reduziert.
- `container_commander/mcp_tools.py` wurde in mehreren Schritten entflechtet und von ~2385 auf ~1558 Zeilen reduziert.
- Die bestehenden Aussenflaechen blieben stabil: `call_tool()`, bestehende Tool-Namen und die zentralen `engine.py`-Funktionsnamen bleiben als Wrapper erhalten.
- Der vorbereitende Schnitt wurde ueber die betroffenen Contract-/Regression-Tests laufend gegengeprueft.

Neu eingefuehrte interne Module:

- `container_commander/engine_runtime_blueprint.py`
- `container_commander/engine_connection.py`
- `container_commander/engine_deploy_support.py`
- `container_commander/engine_start_support.py`
- `container_commander/engine_runtime_state.py`
- `container_commander/mcp_tools_gaming.py`
- `container_commander/mcp_tools_home.py`
- `container_commander/mcp_tools_cron.py`

Bewusst noch offen:

- `container_commander/blueprint_store.py` wurde in dieser Runde noch **nicht** strukturell zerlegt.
- Das ist aktuell akzeptabel, weil die dringenden Hotspots fuer die kommenden Chat/Shell-Phasen zuerst in `engine.py` und `mcp_tools.py` lagen.
- `blueprint_store.py` wird nur dann gezielt geteilt, wenn Phase 1/2 dort konkrete Reibung erzeugt.

### Konkrete Refactor-Checklist

1. `engine.py`: zuerst rein interne Zielstruktur festlegen
   - geplanter Schnitt mindestens in: `deploy/lifecycle`, `runtime_state/quota_ttl_recovery`, `connection_helpers`
   - noch keine Logikaenderung, nur Zielgrenzen und Verschiebereihenfolge festziehen

2. `engine.py`: Deploy- und Startpfad auslagern
   - `start_container()` organisatorisch verkleinern
   - Runtime-Overrides, Approval, Trust-Gates, Secret-/Env-Aufbau und Docker-Run-Vorbereitung in interne Hilfsmodule verschieben

3. `engine.py`: Runtime-State auslagern
   - Quota, `_active`-Reconciliation, TTL-Timer und Recovery logisch zusammenziehen
   - Ziel: Deploy-Pfad und Runtime-State sind getrennt lesbar

4. `engine.py`: Connection-/Port-/Health-Helfer auslagern
   - Port-Binding, Access-Link-Metadaten, Connection-Info und Readiness-/Health-Helfer aus dem Hauptmodul herausziehen
   - Ziel: `engine.py` bleibt Orchestrator statt Helfer-Sammelstelle

5. `engine.py`: nach jedem Teilschnitt Contract-Tests ausfuehren
   - vorhandene Commander-Engine- und Runtime-Recovery-Tests gezielt laufen lassen
   - erst weitergehen, wenn der Schnitt verhaltensgleich stabil ist

6. `mcp_tools.py`: Dispatcher und Tool-Registry von Tool-Implementierungen trennen
   - `TOOL_DEFINITIONS`, `call_tool()` und eigentliche Tool-Handler nicht mehr in einem Block halten
   - Ziel: stabile Registrierungsoberflaeche, interne Fachmodule dahinter

7. `mcp_tools.py`: Tool-Handler nach Fachgruppen aufteilen
   - Container-Tools
   - Blueprint-/Storage-Tools
   - Home-Tools
   - Autonomy-Cron-Tools
   - Gaming-Sonderlogik nur dann mitziehen, wenn sie fuer die Trennung stoert

8. `mcp_tools.py`: Importgrenzen stabilisieren
   - Aufpassen auf zirkulaere Imports zwischen `mcp_tools`, `engine`, `blueprint_store`, `host_companions`
   - Ziel: gleiche Tool-Namen, gleiche Responses, sauberere interne Abhaengigkeiten

9. `blueprint_store.py`: nur gezielte Teilung vorbereiten
   - Migrationen/DB-Init
   - CRUD + Serialization
   - Graph-Sync
   - nur dann wirklich verschieben, wenn Phase 1/2 daran konkret ansetzt

10. Abschluss des Prep-Schnitts dokumentieren
   - kurze Notiz: welche Modulgrenzen jetzt gelten
   - kurze Notiz: welche Dateien fuer Phase 0/1/2 danach die primaeren Einstiegspunkte sind

### Umsetzungsstand der Checklist

1. `engine.py`: interne Zielstruktur festgelegt
   - erledigt

2. `engine.py`: Deploy- und Startpfad ausgelagert
   - erledigt
   - primaere interne Module: `engine_start_support.py`, `engine_runtime_blueprint.py`

3. `engine.py`: Runtime-State ausgelagert
   - erledigt
   - primaeres internes Modul: `engine_runtime_state.py`

4. `engine.py`: Connection-/Port-/Health-Helfer ausgelagert
   - erledigt
   - primaere interne Module: `engine_connection.py`, `engine_deploy_support.py`

5. `engine.py`: nach jedem Teilschnitt Contract-Tests ausgefuehrt
   - erledigt

6. `mcp_tools.py`: Dispatcher und Tool-Registry von Tool-Implementierungen getrennt
   - im pragmatischen Sinn erledigt
   - `call_tool()` und `TOOL_DEFINITIONS` bleiben in `mcp_tools.py`, die groesseren Fachbloecke wurden dahinter ausgelagert

7. `mcp_tools.py`: Tool-Handler nach Fachgruppen aufgeteilt
   - erledigt fuer die groessten Hotspots
   - `mcp_tools_gaming.py`
   - `mcp_tools_home.py`
   - `mcp_tools_cron.py`

8. `mcp_tools.py`: Importgrenzen stabilisiert
   - erledigt fuer diese Runde
   - die Aussen-API blieb stabil, source-/contract-basierte Tests wurden gruen gehalten

9. `blueprint_store.py`: nur gezielte Teilung vorbereiten
   - bewusst verschoben
   - nur bei konkretem Bedarf in Phase 1/2 anfassen

10. Abschluss des Prep-Schnitts dokumentieren
   - erledigt
   - primaere Einstiegspunkte fuer die naechsten Phasen:
   - `container_commander/engine.py` als schlankerer Lifecycle-/Orchestrierungs-Einstieg
   - `container_commander/mcp_tools.py` als stabile MCP-Registry-/Dispatch-Oberflaeche
   - `container_commander/engine_start_support.py` fuer Deploy-/Startfluss
   - `container_commander/engine_runtime_state.py` fuer Runtime-State, Quota, TTL und Recovery
   - `container_commander/mcp_tools_home.py` und `container_commander/mcp_tools_cron.py` fuer die Shell-nahen Tool-Grenzen

### Konsequenz fuer den weiteren Plan

Der vorbereitende Entflechtungsschnitt ist damit fuer diese Runde ausreichend abgeschlossen.

Das bedeutet:

- kein weiterer Strukturumbau als Vorbedingung fuer Phase 0
- Rueckkehr in den eigentlichen TRION Chat/Shell-Plan
- `blueprint_store.py` vorerst nur beobachten, nicht prophylaktisch zerlegen

## Phase 0: Begriffe und Event-Schema festziehen

### Ziel

Vor dem eigentlichen Umbau wird einmal klar definiert, welche Objekte zwischen Chat und Shell fliessen.

### Zu definieren

1. `shell mission state`
2. `shell control profile`
3. `shell memory event types`
4. `chat return summary`

### Konkrete Deliverables

- ein kleines internes Schema fuer den Handoff-Block
- ein kleines internes Schema fuer Shell-Checkpoint-Events
- klare Liste erlaubter Shell-Control-Entscheidungen

### Empfohlenes minimales Schema

`shell_mission_state`

- `conversation_id`
- `container_id`
- `blueprint_id`
- `goal`
- `active_hypothesis`
- `recent_findings`
- `open_blockers`
- `next_step_hint`
- `source_mode`

`shell_checkpoint`

- `container_id`
- `goal`
- `finding`
- `action_taken`
- `change_applied`
- `blocker`
- `next_step`
- `confidence`

### DoD

- alle benoetigten Begriffe sind einmal schriftlich fixiert
- keine offene Grundsatzfrage mehr zu Event-Namen und Objektgrenzen

---

## Phase 1: Shell-Memory in den normalen Kontext rueckfuehren

### Ziel

Die Shell darf nicht mehr nur ein isoliertes `trion_shell_summary` schreiben, das spaeter kaum wiederverwendet wird.

### Kernidee

Die bestehende `workspace_events`- und Compact-Context-Pipeline soll Shell-Erkenntnisse als bekannte, semantisch verarbeitbare Informationen lesen koennen.

### Betroffene Bereiche

- `adapters/admin-api/commander_api/containers.py`
- `core/context_cleanup.py`
- `core/context_manager.py`
- ggf. `core/workspace_event_utils.py`

### Implementationsschritte

1. entscheiden, ob `trion_shell_summary` erweitert oder in neue Event-Typen aufgeteilt wird
2. `context_cleanup.py` fuer Shell-relevante Event-Typen verdrahten
3. Shell-Zusammenfassungen in NOW/RULES/NEXT-lesbare Fakten uebersetzen
4. sicherstellen, dass der normale Chat diese Infos im Compact Context wieder sieht

### Empfohlene Event-Typen

- `shell_session_started`
- `shell_checkpoint`
- `shell_blocker_detected`
- `shell_change_applied`
- `shell_session_summary`

Wenn minimal begonnen werden soll:

- zuerst nur `shell_session_summary`
- spaeter `shell_checkpoint` und `shell_blocker_detected`

### DoD

- nach einer Shell-Sitzung tauchen die wichtigsten Shell-Erkenntnisse im normalen Chat-Kontext wieder auf
- ein anschliessender Chat-Turn kann auf Shell-Ergebnisse Bezug nehmen, ohne dass der User alles neu erklaeren muss

### Risiko

- zu grobe oder zu haeufige Event-Speicherung verwuestet den Compact Context

### Gegenmassnahme

- nur wenige verdichtete Events
- harte Begrenzung der Checkpoint-Haeufigkeit

---

## Phase 2: Gemeinsamen Mission-State beim Handoff bauen

### Ziel

Beim Wechsel von Chat nach Shell soll TRION nicht wie neu gestartet wirken.

### Kernidee

Statt nur `conversation_id` und Containerdaten an den Shellmodus zu geben, wird ein kleiner gemeinsamer Missionskontext uebergeben.

### Betroffene Bereiche

- Chat-Einstieg / Handoff-Stelle zum Shellmodus
- `adapters/admin-api/commander_api/containers.py`
- moeglichweise Frontend-Glue im Commander / Chat-UI
- Orchestrator-Seite fuer Kontextverdichtung

### Implementationsschritte

1. aus dem aktuellen Chatturn einen kompakten Mission-State ableiten
2. diesen beim Start von `trion-shell/start` speichern
3. diesen State in jedem `trion-shell/step` als priorisierten Kontext einspeisen
4. bei Shell-Stop den finalen Missionsstand wieder fuer den Chat rueckschreiben

### Inhalt des Mission-State

- was ist das Ziel
- was ist gerade die Arbeitshypothese
- was wurde bereits im Chat ausgeschlossen
- welcher Container ist gemeint
- welcher naechste Schritt war zuletzt beabsichtigt

### DoD

- Shell-Antworten greifen den laufenden Auftrag auf, ohne wie ein generischer Neustart zu wirken
- kurze Folgeeingaben wie `weiter` oder `pruef das jetzt` funktionieren stabiler

### Risiko

- zu viel Kontext im Shellprompt fuehrt wieder zu Latenz und Drift

### Gegenmassnahme

- Mission-State streng klein halten
- keine rohe Chat-History in die Shell spiegeln

---

## Phase 3: Shell-Control formalisieren

### Ziel

Die bestehende Shell-Sonderlogik wird in einen expliziten Shell-Control-Modus ueberfuehrt.

### Kernidee

Nicht mehr nur implizite Heuristiken im Step-Endpoint, sondern ein klares Regelprofil fuer PTY-Schritte.

### Betroffene Bereiche

- `adapters/admin-api/commander_api/containers.py`
- neue Hilfsdatei `container_commander/engine_shell_control.py` (folgt dem etablierten `engine_*.py`-Namensmuster aus dem Prep-Schnitt)
- eventuell Policy-Konfigurationsdatei fuer Shell-Regeln

Hinweis: Gaming-spezifische Shell-Interaktionen gehen ueber `container_commander/mcp_tools_gaming.py`, nicht ueber `mcp_tools.py` direkt. Der Shell-Control-Modus muss bei Tool-Dispatching ueber die stabile `call_tool()`-Oberflaeche in `mcp_tools.py` bleiben — nicht direkt in die Fachmodule eingreifen.

### Implementationsschritte

1. die existierenden Mechaniken als Shell-Control-Regeln extrahieren
2. klare Entscheidungsarten definieren
3. Shell-Step-Endpoint gegen diese Entscheidungsarten laufen lassen
4. Logging und Telemetrie auf diese Entscheidungen ausrichten

### Empfohlene Entscheidungsarten

- `allow_command`
- `allow_analysis_only`
- `require_verification`
- `require_user_confirmation`
- `stop_repeat_loop`
- `stop_on_blocker`
- `deny_action`

### Bestehende Logik, die in diesen Modus ueberfuehrt werden sollte

- action classification
- post-action verification
- blocker detection
- semantic repeat guard
- localized stop reasons

### DoD

- Shell-Control ist als eigener Modus erkennbar und nicht mehr nur verstreute Sonderlogik
- Shell-Entscheidungen sind in Logs/Events sauber benennbar
- riskantere Shell-Aktionen koennen gezielt anders behandelt werden als Diagnosechecks

### Risiko

- zu fruehe Generalisierung zerlegt den heute funktionierenden Pfad

### Gegenmassnahme

- zuerst Verhalten 1:1 erhalten
- dann erst intern sauber kapseln

---

## Phase 4: Safety-Schnitt fuer Shell sauber trennen

### Ziel

Globale Safety bleibt aktiv, aber Shell bekommt einen eigenen operativen Regelschnitt.

### Kernidee

Es gibt zwei Ebenen:

1. globale Verbote
2. Shell-spezifische Schrittregeln

### Betroffene Bereiche

- `core/safety/light_cim.py`
- `core/layers/control.py`
- Shell-Control-Modul aus Phase 3
- ggf. neue Shell-Policy-Konfig

### Implementationsschritte

1. globale Non-Negotiables identifizieren, die auch in Shell immer gelten
2. Shell-spezifische Erlaubnisse definieren, z. B. fuer Diagnose- und Verifikationsschritte
3. Confirmation-Gates fuer echte Write-/Install-/Process-Control-Aktionen sauber markieren
4. vermeiden, dass Chat-Planinvarianten auf Shell-Mikroschritte durchschlagen

### Praktische Regeltrennung

Immer hart:

- Secrets auslesen
- hostnahe destructive Aktionen
- bösartige Nutzung

Shell-spezifisch:

- `ps`, `grep`, `cat`, `tail`, `find` sehr leicht erlauben
- `sed -i`, `rm`, `mv`, `chmod`, Paketinstallationen oder Prozesskills strenger behandeln
- GUI-Bestaetigungsloops frueh stoppen

### DoD

- Shell-Diagnose fuehlt sich frei und fluessig an
- riskante Schritte bleiben kontrolliert
- keine doppelte Blockade durch Chat-Control plus Shell-Control fuer denselben Mikroschritt

---

## Phase 5: Rueckkopplung in UI und Chat sichtbar machen

### Ziel

Der User soll den Moduswechsel als Kontinuitaet erleben, nicht als Kontextverlust.

### Kernidee

Die Shell muss im Chat und im Commander klar lesbar als Teil derselben Aufgabe erscheinen.

### Betroffene Bereiche

- Commander-Frontend
- Chat-Frontend
- Shell-Stop / Rueckgabe-Response
- Workspace-/Plan-UI bei Bedarf

### Implementationsschritte

1. beim Shell-Start einen klaren Handoff-Text mit Ziel anzeigen
2. waehrend Shelllauf den aktuellen Missionsstand sichtbar halten
3. beim Shell-Ende nicht nur "Shell beendet", sondern "was wurde geprueft / geaendert / bleibt offen"
4. optional Shell-Checkpoint-Infos in das Whiteboard / den Planmodus spiegeln

### DoD

- der User erkennt jederzeit, woran TRION gerade arbeitet
- nach Shell-Ende ist klar, wie es im Chat weitergeht

### Risiko

- UI ueberlaedt mit internen Details

### Gegenmassnahme

- nur die semantischen Ergebnisse zeigen, nicht die komplette interne Telemetrie

---

## Phase 6: Mikro-Loops und spaetere Teilautonomie

### Ziel

Erst wenn Memory-Bruecke, Mission-State und Shell-Control stabil sind, kann ueber Mehrschritt-Shellautonomie nachgedacht werden.

### Kernidee

Autonomie darf erst auf einem stabilen Schrittregler aufsetzen.

### Implementationsschritte

1. einfache verifikationsgetriebene Zweischritt-Loops erlauben
2. nur fuer klar eingegrenzte Diagnoseszenarien aktivieren
3. harte Stopbedingungen definieren
4. Session in jedem Fall in checkpointfaehigem Zustand halten

### Moegliche Stopbedingungen

- kein sichtbarer Zustandswechsel
- interaktiver Prompt offen
- GUI-Dialog unveraendert
- wiederholter Befehl
- riskante Aktion ohne klare Freigabe
- Modell kann keinen sicheren naechsten Schritt begruenden

### DoD

- Shell kann kurze kontrollierte Mikrosequenzen selbst durchlaufen
- Stopverhalten bleibt nachvollziehbar
- kein "blindes Weiterrennen"

---

## 5. Empfohlene PR- oder Task-Schnitte

Wenn das als reale Arbeitsserie umgesetzt wird, sind diese Schnitte sinnvoll:

1. `PR 1: Shell events in Compact Context`
2. `PR 2: Mission State Handoff Chat -> Shell`
3. `PR 3: Shell Control abstraction`
4. `PR 4: Shell safety profile + confirmation gates`
5. `PR 5: UI continuity Chat <-> Shell`
6. `PR 6: optional micro-loops`

Warum diese Reihenfolge gut ist:

- jeder Schritt ist testbar
- jeder Schritt verbessert bereits spuerbar das Nutzergefuehl
- keine Phase zwingt sofort zu tiefer Autonomie

---

## 6. Priorisierte Minimalversion

Wenn nur das Nötigste zuerst gebaut werden soll, dann diese drei Punkte:

1. `trion_shell_summary` oder neue Shell-Events in `context_cleanup.py` integrieren
2. beim Shell-Start einen kleinen Mission-State uebergeben und im Session-State halten
3. die bestehende Shell-Sonderlogik als offiziellen `Shell Control Profile` benennen und kapseln

Das waere bereits der Punkt, an dem:

- Chat und Shell sich deutlich weniger getrennt anfuehlen
- Shellwissen im normalen Chat wieder auftaucht
- die Architektur nicht mehr wie ein Sonderpfad wirkt

### Status zur priorisierten Minimalversion (Stand: 2026-03-29 spaet)

Von diesen drei Minimalpunkten sind aktuell zwei in der Praxis umgesetzt und ein dritter teilweise vorbereitet:

1. Shell-Events in `context_cleanup.py` integrieren
   - erledigt
   - `shell_session_summary`, `trion_shell_summary`-Alias und `shell_checkpoint` sind verdrahtet

2. kleinen Mission-State beim Shell-Start uebergeben und in Session halten
   - erledigt
   - `build_mission_state()` wird beim Start geladen und im Shell-Session-State gehalten

3. bestehende Shell-Sonderlogik als offiziellen `Shell Control Profile` benennen und kapseln
   - noch offen
   - die Logik lebt weiter in `containers.py`, ist aber fachlich bereits klarer isolierbar

Zusatzstand:

- Die fruehere operative Luecke "Shell-Unterhaltung erscheint nicht live im Agent Workspace" ist behoben.
- Shell-Events werden nicht mehr nur gespeichert, sondern nach Persistierung zusaetzlich live als `workspace_update` gespiegelt.
- Die Sprachwahl im `trion-shell`-Flow wurde stabilisiert, damit deutschsprachige Shell-Sessions bei kurzen Follow-ups nicht unnötig auf Englisch kippen.

---

## 7. Reihenfolge fuer die echte Umsetzung

Die pragmatisch beste Reihenfolge ist:

1. Event-/Schema-Entscheidung
2. Shell-Memory-Bruecke
3. Mission-State-Handoff
4. Shell-Control-Kapselung
5. Safety-Schnitt
6. UI-Rueckkopplung
7. Mikro-Loops spaeter

Nicht empfohlen:

- zuerst Mikro-Loops bauen
- zuerst Volltranskript-Speicherung bauen
- zuerst globales CIM fuer Shell "lockern"

---

## 8. Endfazit

Die gesammelten Analysen sprechen klar fuer einen evolutionaeren Umbau.

Der richtige Weg ist:

- nicht Chat und Shell gewaltsam in denselben Einzelschritt-Flow pressen
- sondern die bestehende Shell-Mechanik zu einem offiziellen Modus ausbauen
- und ueber Mission-State plus semantische Event-Bruecke an den normalen Chat koppeln

In einem Satz:

- **Zuerst gemeinsame Erinnerung und gemeinsamer Missionszustand, dann formaler Shell-Control-Modus, erst ganz zum Schluss mehr Shell-Autonomie.**
