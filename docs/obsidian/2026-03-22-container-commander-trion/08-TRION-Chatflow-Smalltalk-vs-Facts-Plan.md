# TRION Chatflow: Smalltalk vs Faktenfragen

Erstellt am: 2026-03-24

## Problem

Der normale TRION-Chatflow unterscheidet aktuell noch nicht robust genug zwischen:

- konversationellen Turns
- leichten Faktenfragen
- echten Tool-/Systemfragen

Das sichtbarste Symptom ist der unpassende Grounding-Fallback bei sozialem Kontext:

- User: `guten Abend Trion wie geht es dir?`
- User: `mein name ist danny`
- Antwort:
  - `Ich habe aktuell keinen verifizierten Tool-Nachweis für eine belastbare Faktenantwort. Bitte Tool-Abfrage erneut ausführen.`

Diese Antwort ist sachlich falsch geroutet:

- der Turn ist kein Tool-Case
- der Turn ist keine belastbare Faktenfrage
- der Turn ist eher `smalltalk` bzw. `social_fact`

## Root-Cause-Hypothese

Die heutige Pipeline koppelt noch zu locker und an den falschen Stellen:

- `dialogue_act`
- `needs_memory`
- `suggested_tools`
- Grounding-Evidenzpflicht

Der kritische Drift-Pfad ist sehr wahrscheinlich:

1. Fruehe Schichten lassen `suggested_tools` im Plan stehen, auch bei konversationellen Turns.
2. Die Output-Layer betrachtet bereits bloesse Tool-Vorschlaege als evidenzpflichtig.
3. Es gibt keine explizite Unterscheidung zwischen:
   - `Tool wurde wirklich benutzt`
   - `Tool wurde nur vorgeschlagen`
4. Dadurch kann ein sozialer Turn in den Fakten-/Grounding-Fallback kippen.

## Wichtige Beobachtungen im Code

### 1. Ton- und Dialogklassifikation ist vorhanden, aber noch nicht ausreichend

[tone_hybrid.py](<repo-root>/core/tone_hybrid.py)

Relevante Stelle:

- `ToneHybrid.classify(...)`
- liefert heute:
  - `dialogue_act`
  - `response_tone`
  - `response_length_hint`
  - `tone_confidence`

Wichtig:

- `smalltalk`, `ack`, `feedback` werden bereits erkannt
- daraus entsteht aber noch kein harter Routing-Modus fuer den Rest der Pipeline

### 2. Precontrol-Policy behandelt Domain-/Memory-Konflikte, aber keinen echten Konversationsmodus

[orchestrator_precontrol_policy_utils.py](<repo-root>/core/orchestrator_precontrol_policy_utils.py)

Relevante Stelle:

- `resolve_precontrol_policy_conflicts(...)`

Wichtig:

- dort werden Konflikte zwischen Domain-Lock, Query-Budget und Tool-Intent aufgeloest
- aber es gibt noch keinen expliziten `conversation_mode`
- `social_fact`-Turns wie `mein name ist danny` werden dort nicht separat modelliert

### 3. Der Sync-Flow injiziert frueh Tools fuer sehr kurze Inputs

[orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)

Relevante Stellen:

- `process_request(...)`
- `selected_tools = await orch.tool_selector.select_tools(...)`
- Short-Input-Bypass:
  - bei sehr kurzem Input werden notfalls Core-Follow-up-Tools injiziert

Wichtig:

- kurze Inputs sind oft gerade die heiklen konversationellen Turns:
  - `danke`
  - `mein name ist danny`
  - `und du?`
- genau dort darf Tool-Injektion nicht spaeter als harte Grounding-Pflicht enden

### 4. Die Grounding-Precheck-Logik behandelt schon Tool-Vorschlaege als evidenzpflichtig

[output.py](<repo-root>/core/layers/output.py)

Relevante Stellen:

- `_grounding_precheck(...)`
- `_extract_selected_tool_names(...)`

Kritischer Mechanismus:

- `has_tool_suggestions = bool(self._extract_selected_tool_names(verified_plan))`
- `require_evidence` wird bereits wahr, wenn:
  - Tools vorgeschlagen wurden
  - auch ohne echte Tool-Ausfuehrung

Das ist fuer Tool-/Faktenfaelle sinnvoll, fuer Smalltalk aber falsch.

## Zielarchitektur

TRION sollte nicht nur zwischen `dialogue_act` und `needs_memory` unterscheiden, sondern einen expliziten Konversationsmodus fuehren.

Vorgeschlagene Modi:

1. `conversational`
   - Gruss
   - Smalltalk
   - Dank
   - Selbstvorstellung
   - lockere soziale Follow-ups

2. `factual_light`
   - einfache Frage
   - geringe Halluzinationsfolgen
   - evtl. Memory sinnvoll
   - Toolpflicht nicht automatisch

3. `tool_grounded`
   - Container
   - Dateien
   - Logs
   - Hardware
   - Web-/Systemabfragen
   - alles, was belastbare Evidenz braucht

4. `mixed`
   - sozialer Einstieg plus echte Aufgabe
   - z. B.:
     - `hey, kannst du mal meine Container pruefen?`

## Designprinzipien

### 1. `suggested_tools` duerfen nicht automatisch Evidenzpflicht bedeuten

Nur diese Dinge sollten starke Grounding-Pflicht ausloesen:

- echte Tool-Ausfuehrung
- explizite Tool-Intention
- `conversation_mode = tool_grounded`
- echte Faktenfrage mit hoeherem Risiko

Nicht ausreichend:

- bloss vorgeschlagene Tools
- kurzer Input
- `needs_memory = true`

### 2. Memory und Grounding muessen entkoppelt werden

`needs_memory` darf nicht automatisch heissen:

- Faktenmodus
- Toolmodus
- Evidenzpflicht

Es gibt mindestens einen eigenen Typ:

- `social_memory`
  - Name
  - Vorlieben
  - Beziehungskontext

Beispiel:

- `mein name ist danny`
  - speicherbar
  - aber nicht toolpflichtig
  - nicht evidenzpflichtig

### 3. `dialogue_act` allein reicht nicht

`smalltalk` ist hilfreich fuer Ton und Laenge, aber nicht ausreichend fuer Routing.

Zusatzsignale werden gebraucht:

- explizite Tool-Intention
- System-/Container-/Dateibezug
- soziale Signale
- Recall-/Memory-Signal
- Halluzinationsrisiko
- Turn-Kontinuitaet

## Implementierungsplan

### Phase 1: `conversation_mode` einfuehren

Ziel:

- neben `dialogue_act` einen expliziten Routingmodus im Plan fuehren

Neue Plan-Felder:

- `conversation_mode`
  - `conversational`
  - `factual_light`
  - `tool_grounded`
  - `mixed`
- optional:
  - `social_memory_candidate: bool`
  - `grounding_relaxed_for_conversation: bool`

Betroffene Stellen:

1. [orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
   - Schema-Normalisierung um `conversation_mode` erweitern
   - erlaubte Enum-Werte zentral validieren

2. [tone_hybrid.py](<repo-root>/core/tone_hybrid.py)
   - **nicht** als einzige Autoritaet nutzen
   - aber `dialogue_act` bleibt wichtiges Eingangssignal

3. [orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)
   - nach Thinking-/Tone-Signal einen kleinen Mode-Resolver aufrufen
   - Ergebnis in `thinking_plan` / `verified_plan` persistieren

Empfohlene neue Helper-Datei:

- neu: `core/orchestrator_conversation_mode_utils.py`

Vorgeschlagene Funktion:

- `resolve_conversation_mode(user_text, thinking_plan, selected_tools, tone_signal, chat_history) -> Dict[str, Any]`

Warum eigene Datei:

- Logik bleibt getrennt von:
  - Tone-Klassifikation
  - Precontrol-Policy
  - Output-Grounding

### Phase 2: klare Heuristiken fuer `conversational` und `social_memory`

Ziel:

- soziale Turns sauber abfangen, bevor sie in Tool-/Grounding-Pfade kippen

Heuristiken fuer `conversational`:

- `dialogue_act in {"smalltalk", "ack", "feedback"}`
- keine explizite Tool-Intention
- kein Container-/Host-/Datei-/Log-/Hardware-Signal
- kein klarer Systembezug
- kein Hochrisiko-Faktenmodus

Heuristiken fuer `social_memory_candidate`:

- Muster wie:
  - `mein name ist ...`
  - `ich heiße ...`
  - `du kannst mich ... nennen`
  - `merk dir, dass ...`

Betroffene Stellen:

1. neu: [orchestrator_conversation_mode_utils.py](<repo-root>/core/orchestrator_conversation_mode_utils.py)
   - Regex-/Heuristik-Layer

2. [orchestrator_precontrol_policy_utils.py](<repo-root>/core/orchestrator_precontrol_policy_utils.py)
   - Domain-/Query-Budget-Konflikte nicht gegen `conversational` eskalieren lassen
   - kurze soziale Turns vor unnoetigen Tool-/Memory-Konflikten schuetzen

3. optional spaeter:
   - Social-Memory-Speicherung an die bestehende Memory-Schicht anbinden

### Phase 3: Grounding an `conversation_mode` koppeln

Ziel:

- konversationelle Turns duerfen nicht an fehlender Tool-Evidenz scheitern

Hauptstelle:

[output.py](<repo-root>/core/layers/output.py)

Zu aendern in:

- `_grounding_precheck(...)`

Neue Regel:

- wenn `conversation_mode == "conversational"`:
  - `suggested_tools` allein loesen **keine** Evidenzpflicht aus
- wenn `conversation_mode == "factual_light"`:
  - Evidenz nur bei echter Tool-Ausfuehrung oder klarer Faktenpflicht
- wenn `conversation_mode == "tool_grounded"`:
  - heutige strenge Evidenzlogik bleibt weitgehend erhalten

Wichtige technische Trennung:

- `has_tool_usage`
  - starkes Signal
- `has_tool_suggestions`
  - nur schwaches Signal

Der heutige Fehler entsteht genau dort, wo diese beiden zu aehnlich behandelt werden.

### Phase 4: Tool-Selection bei kurzen Inputs entschärfen

Ziel:

- Short-Input-Bypass darf soziale Turns nicht in Tool-/Grounding-Ketten schieben

Hauptstelle:

[orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)

Relevanter Abschnitt:

- Short-Input-Bypass mit:
  - `request_container`
  - `run_skill`
  - `home_write`

Plan:

- vor Tool-Injektion `conversation_mode` bzw. eine Vorstufe davon beruecksichtigen
- fuer offensichtliche soziale Inputs keinen Core-Follow-up-Toolsatz injizieren

Praxisregel:

- `danke`, `guten abend`, `mein name ist ...`, `und dir?`
  - keine Tool-Injektion
- `check mal den container`
  - Tool-Injektion weiterhin okay

### Phase 5: Prompt- und Memory-Verhalten sauber angleichen

Ziel:

- Smalltalk kurz und natuerlich
- Social-Memory speicherbar
- keine ueberharten Fakten-Fallbacks

Relevante Stellen:

1. [tone_hybrid.py](<repo-root>/core/tone_hybrid.py)
   - bleibt fuer Ton/Laenge wichtig

2. [output.py](<repo-root>/core/layers/output.py)
   - Prompt kann bei `conversation_mode=conversational` zusaetzlich klar machen:
     - keine Toolrechtfertigung
     - kurz, natuerlich, sozial passend

3. bestehende Memory-Pfade
   - spaeter optional:
     - `social_memory_candidate` explizit als speicherbar markieren

## Testplan vor dem eigentlichen Fix

Vor Code-Aenderungen sollten Regressionstests fuer genau diese Faelle definiert werden:

### A. Reiner Smalltalk

- `guten Abend Trion wie geht es dir?`
- erwartet:
  - kurzer sozialer Reply
  - kein Tool-Fallback
  - kein Evidenzfehler

### B. Social Fact

- `mein name ist danny`
- erwartet:
  - freundliche Bestaetigung
  - kein Tool-Fallback
  - optional spaeter speicherbar

### C. Smalltalk mit Memory-Signal

- `merk dir, dass ich Danny heiße`
- erwartet:
  - kein Grounding-Fallback
  - Social-Memory-Pfad erlaubt

### D. Leichte Faktenfrage ohne Toolpflicht

- `wie heißt mein Container?`
- erwartet:
  - sauber geroutet
  - falls Daten fehlen, sinnvoller Rueckfall
  - aber kein Smalltalk-Pfad

### E. Echte Toolfrage

- `prüf bitte die GPU`
- erwartet:
  - `tool_grounded`
  - Grounding bleibt aktiv

### F. Mixed Turn

- `hey, kannst du mal meine Container checken?`
- erwartet:
  - freundlich
  - aber klar im Toolmodus

## Konkrete Reihenfolge fuer die Umsetzung

1. Tests schreiben fuer:
   - Smalltalk
   - Social-Fact
   - Toolfrage
2. `conversation_mode` im Plan-Schema und Resolver einfuehren
3. Grounding-Precheck an `conversation_mode` koppeln
4. Short-Input-Bypass anpassen
5. optional danach Social-Memory speichern

## Empfehlung

Nicht einfach den Fallback “wegpatchen”.

Sauberer ist:

- expliziten `conversation_mode` einfuehren
- Tool-Suggestions von echter Tool-Evidenz trennen
- Social-Memory als eigenen Fall behandeln

Dann wird nicht nur der konkrete Fehler mit `mein name ist danny` behoben, sondern der normale TRION-Chatflow insgesamt robuster.
