# TRION Chat + Shell Vereinigung, CIM und Control

Erstellt am: 2026-03-25

Statushinweis (2026-03-26):

- Der vorbereitende Entflechtungsschnitt in `container_commander/engine.py` und `container_commander/mcp_tools.py` ist inzwischen umgesetzt.
- Der aktuelle operative Umsetzungsstand und die naechste Reihenfolge stehen in `22-TRION-Chat-Shell-Implementationsplan.md`.

## Zweck dieser Notiz

Diese Notiz beantwortet die konkrete Architekturfrage:

- Wie vereinen wir normalen Chat und `TRION shell` so, dass es sich nicht wie zwei verschiedene Modelle anfuehlt?
- Brauchen wir dafuer ein zusaetzliches CIM/Control zwischen Chat und Shell?
- Sind die bestehenden CIM-/Control-Regeln fuer eine Live-Shell tatsaechlich zu hart?

Kurzantwort:

- Ja, du liegst im Kern richtig.
- Aber nicht im Sinn von: noch eine zweite volle Control-Autoritaet neben der bestehenden.
- Sondern im Sinn von: ein eigener **Shell-Control-/Shell-CIM-Modus** zwischen Chat-Handoff und PTY ist noetig.

Wichtig:

- Die normale Chat-Control ist fuer diskrete Turns gebaut.
- Die Shell braucht ein zustandsbasiertes Mikro-Gate pro Schritt.
- Das eigentliche Problem ist also weniger "zu wenig Safety" als "falsche Granularitaet und falsche Invarianten".

---

## 1. Aktueller Befund

## 1.1 Normale Chat-Control ist ein Plan-Gate

Die normale Pipeline arbeitet so:

1. Thinking formt einen Plan.
2. Control prueft diesen Plan als bindende Policy-Entscheidung.
3. Output erzeugt die Antwort auf Basis dieser Freigabe.

Wichtige Stellen:

- `core/layers/control.py`
- `core/control_contract.py`
- `core/orchestrator_control_skip_utils.py`
- `core/safety/light_cim.py`
- `intelligence_modules/cim_policy/cim_policy_engine.py`

Praezise Beobachtung:

- `ControlLayer` ist explizit als Layer vor der Antwort formuliert.
- Er entscheidet ueber `approved`, `decision_class`, `hard_block`, `block_reason_code`, `warnings`, `corrections`, `final_instruction`.
- Er denkt also in **turnweisen Planobjekten**, nicht in live beobachteten Shell-Zustandsuebergaengen.

Beleg:

- `core/layers/control.py:63`
- `core/layers/control.py:90`
- `core/control_contract.py`

Das ist passend fuer:

- Chat-Antworten
- Tool-Freigaben
- Plan-Korrekturen
- Routing-/Policy-Entscheidungen

Das ist schlecht passend fuer:

- "mach noch einen Check"
- "weiter"
- GUI-Dialog noch offen?
- dieselbe Aktion nochmal oder nicht?
- Shell wartet auf Prompt?

---

## 1.2 LightCIM ist schnell, aber ebenfalls chat-/planorientiert

`LightCIM` ist zwar leichtgewichtig, aber semantisch weiter auf normale Requests ausgelegt:

- Intent-Validierung
- einfache Logikkonsistenz
- Safety-Schlagworte
- Eskalationsentscheidung

Beleg:

- `core/safety/light_cim.py:1`
- `core/safety/light_cim.py:61`
- `core/safety/light_cim.py:168`

Besonders wichtig:

- Es prueft u. a. `needs_memory`, `memory_keys`, `is_new_fact`, `new_fact_key`, `new_fact_value`.
- Das sind gute Invarianten fuer Chat-/Planobjekte.
- Das sind aber keine primaeren Invarianten fuer einen PTY-Schritt.

Fuer eine Shell ist die zentrale Frage haeufig nicht:

- "ist der Plan formal vollstaendig?"

sondern:

- "hat der letzte Befehl sichtbar etwas geaendert?"
- "steht noch ein Prompt offen?"
- "waere die Wiederholung derselben Aktion eine Schleife?"
- "ist erst Verifikation noetig statt ein neuer Befehl?"

---

## 1.3 CIM-Policy ist ein Intent-Router, kein guter PTY-Step-Governor

Der vorhandene CIM-Policy-Engine-Code ist auf kontrollierte Autonomie fuer Skill-/Intent-Entscheidungen ausgelegt.

Beleg:

- `intelligence_modules/cim_policy/cim_policy_engine.py:3`
- `intelligence_modules/cim_policy/cim_policy_engine.py:11`
- `intelligence_modules/cim_policy/cim_policy_engine.py:45`

Die Engine denkt in Kategorien wie:

- `RUN_SKILL`
- `FORCE_CREATE_SKILL`
- `REQUEST_USER_CONFIRMATION`
- `FALLBACK_CHAT`

Das ist fuer Chat-Intent gut.
Fuer eine laufende Shell ist das zu grob und an der falschen Stelle im Ablauf.

Eine PTY braucht keine neue Skill-Router-Entscheidung pro Mini-Schritt.
Sie braucht eine schnelle Antwort auf:

- weiterlesen
- verifizieren
- stoppen
- bestaetigen lassen
- keine Wiederholung

---

## 1.4 Der Shellmodus hat faktisch schon heute einen eigenen Control-Lane

Der aktuelle Shellmodus ist bereits bewusst **nicht** an die volle normale Pipeline gebunden.

Beleg aus der Notiz:

- `docs/obsidian/2026-03-22-container-commander-trion/03-TRION-Shell-Mode.md`

Direkt im Code sieht man:

- eigener Session-State in RAM
- Schritt-Historie
- Verifikation des letzten Schritts
- Blocker-Erkennung
- Loop-Guard
- strukturierte Stop-Gruende

Wichtige Stellen:

- `adapters/admin-api/commander_api/containers.py:328`
- `adapters/admin-api/commander_api/containers.py:365`
- `adapters/admin-api/commander_api/containers.py:784`
- `adapters/admin-api/commander_api/containers.py:936`
- `adapters/admin-api/commander_api/containers.py:1003`

Das ist der entscheidende Befund:

- Die Shell hat bereits **eine andere Regelmechanik** als Chat.
- Also ist die Kernfrage nicht mehr, ob es eine Sonderlogik braucht.
- Die Sonderlogik existiert schon.
- Die eigentliche Architekturfrage ist: **wie machen wir daraus einen offiziellen, sauberen Shell-Control-Modus statt eine isolierte Sonderroute?**

---

## 2. Liegt die Vermutung "CIM-Regeln fuer Shell zu hart" richtig?

## 2.1 Ja, inhaltlich richtig

Ja.

Die normale CIM-/Control-Logik ist fuer Shell-Schritte zu hart bzw. praeziser:

- zu turnorientiert
- zu planfeldorientiert
- zu langsam fuer PTY-Mikrointeraktion
- zu wenig zustandsbasiert

Ein Live-Shell-Schritt ist oft absichtlich unvollstaendig.

Beispiele:

- ein rein diagnostischer `ps`, `tail`, `grep`
- ein leerer Befehl mit Stop-Grund
- ein kurzer Follow-up wie `weiter`
- eine reine Verifikationsrunde ohne neue Aktion

Im normalen Chat waeren solche Turns leicht als "unklar", "ohne genug Struktur" oder "noch nicht ausformuliert" lesbar.
In der Shell sind sie normal.

---

## 2.2 Aber: nicht Safety lockern, sondern den Regler verlagern

Der wichtige Architekturpunkt ist:

- Ihr solltet nicht einfach CIM "weicher drehen".
- Ihr solltet die **Safety-Ebenen trennen**.

Was global hart bleiben sollte:

- echte Sicherheitsverbote
- Credential-/Secret-Exfiltration
- destructive Aktionen ohne klaren Auftrag
- Host-Escape / Cross-Boundary-Aktionen
- offensichtliche malware-/abuse-Muster

Was fuer Shell anders geregelt werden muss:

- Mikroschritt-Freigabe
- Verifikationspflicht nach Aktion
- Repeat-Stop statt Hard-Block
- Prompt-/Dialog-Erkennung
- Zustandswechsel statt Planvollstaendigkeit
- kurze Follow-up-Turns wie `und`, `weiter`, `nochmal`

Das bedeutet:

- **Safety-Schwelle nicht senken**
- **Schrittlogik an Shell-Realitaet anpassen**

---

## 3. Brauchen wir einen extra CIM/Control zwischen Chat und Shell?

## 3.1 Ja, aber als Modus, nicht als zweite Hoheitsmacht

Empfehlung:

- Ja, es braucht eine zusaetzliche Schicht zwischen normalem Chat und PTY.
- Aber diese Schicht sollte **kein zweiter konkurrierender Control-Layer** sein.
- Sondern ein **Shell-Control-Adapter** mit eigenem Regelprofil.

Am saubersten ist dieses Modell:

1. Normaler Chat entscheidet ueber den Handoff in `TRION shell`.
2. Ab Shell-Aktivierung gilt ein eigener `Shell Control Profile`.
3. Beim Ruecksprung in den normalen Chat werden Shell-Ergebnisse wieder in gemeinsame Erinnerungsformen uebersetzt.

Damit bleibt die Single-Control-Idee erhalten:

- Chat-Control bleibt Autoritaet fuer Chat-/Planturns.
- Shell-Control bleibt Autoritaet fuer PTY-Mikroturns.

Wichtig:

- zwei Modi
- eine Gesamtarchitektur
- kein policy-chaos

---

## 3.2 Warum die bestehende Shell-Route bereits die richtige Richtung zeigt

Der aktuelle Step-Endpoint macht bereits genau die Dinge, die ein Shell-Control-Modus braucht:

- klassifiziert Befehle (`_classify_shell_action`)
- verifiziert den letzten Schritt (`_verify_previous_shell_action`)
- erkennt Blocker (`_detect_shell_blocker`)
- stoppt bei Wiederholung (`loop_guard_repeat`)
- erzeugt stop-orientierte Nutzertexte statt allgemeiner Chat-Abwehr

Beleg:

- `adapters/admin-api/commander_api/containers.py:209`
- `adapters/admin-api/commander_api/containers.py:328`
- `adapters/admin-api/commander_api/containers.py:875`
- `adapters/admin-api/commander_api/containers.py:1003`

Das heisst:

- Ihr braucht nicht erst theoretisch einen Shell-Control erfinden.
- Ihr habt schon den Kern davon.
- Was fehlt, ist seine **saubere Anbindung an gemeinsame Memory-/Kontextkanaele und an eine formale Betriebsart**.

---

## 4. Wie vereinen wir Chat und Shell "vom Gefuehl"?

Das Fremdmodell-Gefuehl entsteht nicht primaer, weil andere Prompts verwendet werden.
Es entsteht, weil Chat und Shell heute auf unterschiedlichen Erinnerungspfaden leben.

Der Chat fuehlt sich konsistent an, weil er mehrere Kanaele kombiniert:

- Frontend-History
- SQL-Memory
- Workspace-Events
- Daily Protocol
- flüchtigen Conversation-State

Die Shell fuehlt sich getrennt an, weil sie praktisch nur nutzt:

- `conversation_id`
- Container-Runtime-Fakten
- flüchtigen Shell-Session-State
- spaeter eine isolierte `trion_shell_summary`

Siehe auch:

- [[20-TRION-Chat-Shell-Memory-und-Kontext-Analyse]]

---

## 4.1 Das eigentliche Ziel ist nicht Volltranskript, sondern Identitaetskontinuitaet

Damit Chat und Shell sich wie dasselbe TRION anfuehlen, braucht ihr drei gemeinsame Schienen:

1. denselben Identitaetskontext
2. denselben semantischen Erinnerungskanal
3. denselben Handoff-/Rueckgabe-Mechanismus

Nicht noetig:

- komplettes PTY-Log im Chat-Memory
- jede Shell-Zeile in SQL
- voller Shell-Verlauf im Prompt

Noetig:

- verdichtete Shell-Zustaende
- gemeinsame Container-/Task-Referenz
- dieselbe laufende Aufgabe ueber Modusgrenzen hinweg

---

## 4.2 Was beim Shell-Start in die Session hinein muss

Beim Handoff in `TRION shell` sollte nicht nur `conversation_id` uebergeben werden, sondern ein kompakter gemeinsamer Startkontext:

- aktives Ziel der Unterhaltung
- relevante letzte User-Absicht
- letzte beschlossene Arbeitshypothese
- bekannte Container-/Blueprint-Fakten
- offene Blocker oder offene Naechstschritte aus Chat

Wichtig:

- kein Vollchat
- keine letzten 30 Messages roh
- sondern ein kleiner gemeinsamer "Mission State"

Dann startet die Shell nicht wie ein neues Modell, sondern wie dieselbe Instanz in einem anderen Arbeitsmodus.

---

## 4.3 Was waehrend der Shell gespeichert werden sollte

Nicht alles speichern.
Nur das, was spaeter fuer Chat und erneuten Shell-Einstieg semantisch wertvoll ist.

Sinnvolle Speicherobjekte:

1. `shell_session_started`
2. `shell_checkpoint`
3. `shell_blocker_detected`
4. `shell_change_applied`
5. `shell_session_summary`

Nicht als Volltranskript, sondern als kompakte Faktenobjekte wie:

- Ziel
- aktuelle Hypothese
- was wurde geprueft
- was wurde veraendert
- welcher Blocker blieb offen
- was ist der naechste sinnvolle Schritt

Das passt viel besser zur bestehenden `workspace_events`- und Compact-Context-Logik als rohe PTY-Ausgabe.

---

## 4.4 Warum das heutige `trion_shell_summary` noch nicht reicht

Aktuell wird am Ende zwar eine strukturierte Shell-Zusammenfassung gespeichert:

- `adapters/admin-api/commander_api/containers.py:168`
- `adapters/admin-api/commander_api/containers.py:1096`

Aber `context_cleanup.py` kennt `trion_shell_summary` nicht als aktiv verdrahteten Event-Typ.

Beleg:

- `core/context_cleanup.py:512`
- `core/context_cleanup.py:538`
- `core/context_cleanup.py:676`

Folge:

- Die Shell speichert etwas.
- Der normale Chat liest es nicht als erstes Klassenelement wieder ein.
- Dadurch fehlt die semantische Rueckkopplung.

Das ist einer der Hauptgruende fuer das "Fremdmodell"-Gefuehl.

---

## 5. Welche Art von Shell-Control wird wirklich gebraucht?

## 5.1 Chat-Control fragt: "Darf dieser Plan passieren?"

Normale Control-Fragen:

- Ist der Plan sicher?
- Ist er policy-konform?
- Sind Korrekturen noetig?
- Soll gewarnt oder hart blockiert werden?

## 5.2 Shell-Control fragt: "Ist der naechste PTY-Schritt aus diesem Zustand legitim?"

Shell-Control-Fragen:

- Hat der letzte Schritt den Zustand veraendert?
- Ist stattdessen erst Verifikation noetig?
- Liegt noch ein Prompt/Dialog offen?
- Waere eine Wiederholung nur eine Schleife?
- Ist Diagnose vor Aenderung noetig?
- Braucht diese konkrete Aktion explizite Nutzerbestaetigung?

Das ist ein anderer Problemtyp.

Darum ist die praezise Antwort:

- Ja, ein eigener Control dazwischen ist richtig.
- Aber er muss **zustandsorientiert** sein, nicht planorientiert.

---

## 5.3 Welche Regeln im Shell-Control lockerer sein muessen

Lockerer im Sinn von "arbeitsfaehiger", nicht im Sinn von "unsicherer":

- Diagnosebefehle duerfen sehr niedrigschwellig sein.
- Ein Turn darf auch nur Verifikation liefern, ohne neuen Befehl.
- Kurze Follow-ups duerfen auf Session-State aufsetzen.
- Nicht jeder Turn braucht neue Memory-/Fact-Struktur.
- "unknown" oder "unchanged" fuehrt eher zu Stop/Check als zu Policy-Alarm.
- Ein leerer Befehl mit sauberem Stop-Grund ist gueltiges Verhalten.

## 5.4 Welche Regeln im Shell-Control haerter sein sollten als im Chat

Paradoxer, aber wichtig:

- Wiederholte destructive Kommandos muessen frueher gestoppt werden.
- Interaktive Prompts muessen frueher erkannt werden.
- GUI-Bestaetigungsloops muessen frueher gebrochen werden.
- Write-Changes brauchen sichtbare Verifikation.

Das heisst:

- weniger formale Planhaerte
- mehr operative Zustandsdisziplin

---

## 6. Empfohlene Zielarchitektur

## 6.1 Gemeinsames Modellbild

Nicht:

- Chat-Modell hier
- Shell-Modell dort
- zwei getrennte Erinnerungen

Sondern:

- eine TRION-Identitaet
- zwei Arbeitsmodi
- gemeinsame semantische Memory-Bruecke

## 6.2 Praktisches Architekturmodell

1. **Chat Mode**
   - normaler Thinking/Control/Output-Flow
   - entscheidet ueber Handoff in Shell

2. **Shell Handoff Layer**
   - bildet aus Chatkontext einen kompakten Mission State
   - uebergibt Ziel, Hypothese, Containerkontext, offene Aufgaben

3. **Shell Control Mode**
   - action classification
   - verification-first
   - repeat guard
   - blocker detection
   - approval points fuer riskantere Schritte

4. **Shell Memory Bridge**
   - schreibt verdichtete Shell-Fakten in bekannte Eventformen
   - nicht als Volltranskript

5. **Chat Return Layer**
   - liest die Shell-Ergebnisse wieder als normalen Kontext ein
   - sagt nicht nur "Shell beendet", sondern "wir haben X geprueft, Y geaendert, Z ist offen"

---

## 7. Endfazit

Die Vermutung ist richtig:

- Der bestehende CIM-/Control-Stil ist fuer eine Live-Shell zu hart bzw. am falschen Ort.

Die praezise Architekturantwort ist aber:

- nicht einfach die globale Control schwammiger machen
- nicht denselben Chat-Control pro Shell-Schritt erzwingen
- sondern einen **eigenen Shell-Control-/Shell-CIM-Modus** formalisieren

Der Shellmodus braucht:

- andere Taktung
- andere Invarianten
- andere Stoplogik
- dieselben uebergeordneten Safety-Grenzen

Und fuer das gemeinsame Gefuehl braucht ihr:

- denselben Missionskontext beim Handoff
- denselben semantischen Erinnerungskanal beim Rueckweg
- keine Volltranskript-Speicherung

In einem Satz:

- **Ja, ein zusaetzlicher Control zwischen Chat und Shell ist richtig, aber als spezialisierter Shell-Control-Modus mit gemeinsamer Memory-Bruecke, nicht als zweite volle Chat-CIM-Instanz.**
