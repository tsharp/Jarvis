# Task-Loop Control-First Turn-Mode Implementationsplan

Erstellt am: 2026-04-12
Status: **In Umsetzung**
Bezieht sich auf:

- [[2026-04-09-trion-multistep-loop-implementationsplan]] - aktueller Task-Loop-Stand und verbleibende Produktreste
- [[2026-03-22-container-commander-trion/15-TRION-Chatflow-Layer-3-Control]] - Sollbild: Control als bindende Policy-Autoritaet
- [[2026-04-01-control-authority-drift-approved-fallback-container-requests]] - belegter Fehler: `approved=True` war nicht die letzte Wahrheit
- [[2026-04-02-thinking-strategy-authority-and-frontend-visibility-implementationsplan]] - Thinking nur als Rohsignal, Control schreibt autoritative Strategie
- [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]] - Control-first Contract statt spaeter Drift-/Repair-Logik

---

## Ist-Stand 2026-04-12

Wichtige Architekturkorrektur vom 2026-04-13:

- der sichtbare `task_loop` wird nicht mehr als eigener innerer Chat- oder
  Step-Kanal gedacht
- der Loop ist kuenftig ein sichtbarer Modus des normalen Chatturns
- per-Step-Budgets sind im Loop kein zulaessiger produktiver Stopgrund mehr
- ein Loop darf nur wegen echter Fehler, Blocker, User-Waits, Cancel oder
  klarer Kreis-/No-Progress-Erkennung stoppen
- der bisherige Step-Prompt-/Step-Runner-Pfad ist damit nur noch ein
  Uebergangsschnitt, nicht das finale Sollbild

Der Plan ist nicht mehr rein konzeptionell. Ein erster vertikaler Slice ist
bereits im Code umgesetzt.

Bereits umgesetzt:

- Thinking kennt Task-Loop-Kandidaten als Rohsignal:
  - `task_loop_candidate`
  - `task_loop_kind`
  - `task_loop_confidence`
  - `estimated_steps`
  - `needs_visible_progress`
  - `task_loop_reason`
- Control schreibt einen autoritativen Turn-Modus:
  - `_authoritative_turn_mode`
  - `_authoritative_turn_mode_reason`
  - `_authoritative_turn_mode_reasons`
  - `_authoritative_turn_mode_blockers`
- neue Task-Loop-Starts im Sync- und Stream-Pfad werden nach Thinking plus
  Control ueber den autoritativen Turn-Modus geroutet
- der sichtbare Loop kennt jetzt explizite Step-Contracts:
  - `step_type`
  - `step_status`
  - `step_execution_source`
  - `task_loop_step_request`
  - `task_loop_step_result`
- der Planner annotiert Schritte bereits strukturiert, inklusive erster
  `tool_request_step`-Klassifikation und `requested_capability`
- der Task-Loop-Planning-Pfad nutzt jetzt denselben Tool-/Capability-Exposure-
  Eingang wie der normale Orchestrator, statt Thinking isoliert mit
  `available_tools=[]` zu fahren
- der Planner erzeugt bei vorhandenem Tool-Bedarf jetzt capability-naehere
  Tool-Plaene statt nur generischer Analyse-/Validierungsplaene
- der Stream-Runner kann Tool-Schritte ueber den bestehenden Orchestrator-
  Vertrag laufen lassen, statt sie nur als Chat-only Schritt zu behandeln
- aktive Tool-Schritte in `waiting_for_approval` koennen jetzt im Sync- und
  Stream-Pfad ueber den echten Runtime-/Orchestrator-Resume fortgesetzt werden
- aktive Tool-Schritte in `waiting_for_user` koennen jetzt mit konkreten neuen
  User-Parametern ebenfalls ueber denselben Runtime-/Orchestrator-Pfad
  fortgesetzt werden
- ein blindes `weiter` schiebt runtimegebundene Tool-Schritte in
  `waiting_for_user` nicht mehr faelschlich ueber den simplen Manual-Continue-
  Pfad
- Container-Query-Tools (`blueprint_list`, `container_list`, `container_inspect`,
  `container_stats`, `container_logs`) werden im Planner jetzt korrekt als
  `capability_type="container_manager"` klassifiziert und loesen das
  container-spezifische Template aus — nicht mehr das generische Tool-Template
  (2026-04-12)
- Klare Trennung zwischen Container-Action-Tools (schreibend/mutierend →
  `NEEDS_CONFIRMATION`) und Container-Query-Tools (nur lesend → `SAFE`):
  `_CONTAINER_ACTION_TOOLS` vs `_CONTAINER_QUERY_TOOLS` in `planner.py`.
  `blueprint_list` und andere Query-Tools blockieren den Loop nicht mehr —
  nur `request_container`, `stop_container`, `exec_in_container` etc.
  erfordern noch Bestätigung (2026-04-12)
- Loop läuft SAFE-Schritte vollautomatisch durch — kein manuelles "weiter"
  mehr nötig. Collection-Schritte ("Fehlende X-Angaben sammeln") pausieren
  nicht mehr: die KI füllt fehlende Parameter mit sinnvollen Defaults und
  dokumentiert die Annahmen. `_needs_user_reply`-Logik und
  `_stream_needs_user_reply`-Block entfernt (2026-04-12)
- Continue-Pfad nutzt jetzt `run_chat_auto_loop_async` mit echten
  Control/Output-Layern statt manueller Ein-Schritt-Logik in
  `continue_chat_task_loop`. Die KI denkt in jedem Schritt wirklich nach
  statt nur ein Schritt-Template auszugeben. `maybe_handle_task_loop_sync`
  leitet alle aktiven Loop-Continues direkt an den async Runner weiter
  (2026-04-12)
- `runtime_resume_user_text` erweitert: substantieller User-Input (z.B.
  "python:3.11-slim") wird jetzt als `resume_user_text` an den Runner
  weitergegeben — nicht mehr nur bei TOOL_REQUEST-Schritten (2026-04-12)

- Task-Loop-UI: `chat-plan.js` implementiert jetzt eine Live-Step-Liste
  (keine generischen `<details>`-Blöcke mehr für `task_loop_update` Events).
  Stream-Event-to-UI-Mapping: laufende Schritte blau-pulsierend, abgeschlossene
  grün/durchgestrichen, Freigabe-Schritte gelb mit Hint, Fehlzustände rot.
  Header zeigt Plan-Länge und wechselt bei `is_final` automatisch auf
  "Task-Loop abgeschlossen" / "Freigabe erforderlich" / "gestoppt".
  `finalizePlanBox` überschreibt bei Task-Loop-Boxen Titel und Icon nicht.
  Step-Counter zeigt Plan-Länge, nicht Event-Count (2026-04-13)
- Step-Boxen als aufklappbare `<details>/<summary>` umgebaut: Status-Prefix im
  Titel ("Schritt 2 abgeschlossen: …"), laufende/wartende Schritte auto-geöffnet,
  fertige/ausstehende Schritte zugeklappt. Capability und Typ als kompakter
  Body-Content (2026-04-13)
- `_effective_max_steps` ersetzt hardcodierten `max_steps=4`: leitet Cap aus
  `min(max(plan_len * 3, 20), 50)` ab — Loop läuft bis Plan erfüllt oder
  echter Guard feuert (2026-04-12)
- Alle technischen Canned-Messages im Task-Loop durch natürlichsprachliches
  Deutsch ersetzt (2026-04-13):
  - Pause wegen Risk-Gate: `_msg_risk_gate(step_name)` → "Für den nächsten
    Schritt … brauche ich deine Freigabe — dieser Schritt würde etwas wirklich
    verändern…"
  - Control-Soft-Block: `_msg_control_soft_block(detail)` → "Ich brauche deine
    Bestätigung bevor ich weitermache…"
  - Hard-Block: `_msg_hard_block(detail)` → "Dieser Schritt wurde blockiert…"
  - Warte-Zustand: `_msg_waiting(detail)` → "Ich brauche mehr Informationen…"
  - Alle Fortschritts-Zwischenstände ("Zwischenstand:", "Schritt N
    abgeschlossen:") und Start-Header ("Task-Loop gestartet. Plan: …") entfernt
    — Info liegt vollständig in der Step-UI
- Unification des Active-Loop-Continue-Pfads: alle eingehenden Nachrichten
  in einem aktiven Loop (außer explizitem Cancel) laufen jetzt einheitlich über
  `stream_chat_auto_loop` statt über den alten `maybe_handle_chat_task_loop_turn`
  / `manual_mode`-Pfad. `manual_mode`-Zweig nur noch aktiv bei explizitem
  `task_loop_mode=manual/step/wait` im Request (2026-04-13)
- `_CONTINUE_MARKERS` erweitert: "freigeben", "freigabe", "genehmigen",
  "approve", "ok", "okay" gelten jetzt als Continue-Signal. Warte-Message
  bei unbekanntem Signal natürlichsprachlich angepasst (2026-04-13)
- Infinite-Freigaben-Loop gefixt: `_already_gate_approved`-Bypass in allen
  drei Runner-Pfaden (sync, async, stream) — wenn der Snapshot bereits
  `WAITING_FOR_APPROVAL + RISK_GATE_REQUIRED` ist, feuert das Risk-Gate
  beim Resume nicht erneut (2026-04-13)
- Root-Cause "needs_confirmation" im Chat-Output gefixt: nach einem
  abgeschlossenen Schritt schreibt der Runner den `risk_level` des nächsten
  Schritts bereits auf den Snapshot. `reflect_after_chat_step` sah diesen
  Wert und gab `ReflectionAction.WAITING_FOR_USER` mit `detail =
  "needs_confirmation"` zurück — das landete 1:1 als Rohtext im Chat.
  Fix: in allen drei Reflection-WAITING_FOR_USER-Handlern (`_run_chat_step`,
  `_run_chat_auto_loop_step_async`, `_stream_chat_auto_loop_step_async`)
  wird bei `stop_reason == RISK_GATE_REQUIRED` jetzt `_msg_risk_gate(
  reflecting.pending_step)` aufgerufen statt `_msg_waiting(decision.detail)`
  (2026-04-13)
- Active-Loop-Turn-Policy in neue kleine Module ausgelagert:
  - `core/task_loop/active_turn_policy.py`
  - `core/task_loop/runtime_policy.py`
  Damit liegt Resume-/Meta-Turn-/Reason-Code-Logik nicht mehr komplett in
  `core/orchestrator_modules/task_loop.py` und Budget-Policy nicht mehr nur
  implizit in `step_runtime.py` bzw. `output.py` (2026-04-13)
- Context-only-Writeback fuer normale Meta-Turns aus aktivem Loop ebenfalls
  in eigenes Modul ausgelagert:
  - `core/task_loop/context_writeback.py`
  Der normale Chatturn kann damit eine aktive Loop-Konversation jetzt nach dem
  Antwortturn strukturiert zurueck in den Loop-State schreiben, statt den
  Loop fuer solche Turns entweder blind zu resumieren oder komplett zu
  ignorieren (2026-04-13)
- Meta-Fragen an einen aktiven autoritativen Loop werden nicht mehr blind als
  Runtime-Resume interpretiert. Neuer Reason-Code:
  `active_task_loop_context_only`.
  Solche Turns bleiben im normalen Chatflow und halten den aktiven Loop nur
  als sichtbaren Kontext offen, statt direkt wieder den separaten Loop-Runner
  zu starten (2026-04-13)
- Stream- und Sync-Pfad schreiben einen normalen `context_only`-Turn jetzt in
  den aktiven Snapshot zurueck:
  - `last_user_visible_answer` wird aktualisiert
  - ein `context_only_turn`-Artefakt wird vererbt
  - ein `task_loop_context_updated`-Event kann persistiert werden
  - der aktive Loop bleibt offen statt verloren zu gehen (2026-04-13)
- Tool-Step-Typisierung in eigenes Modul ausgelagert:
  - `core/task_loop/tool_step_policy.py`
  Dort liegt jetzt zentral:
  - welche Plan-Step-Position die eigentliche Tool-Stelle traegt
  - wann ein geplanter Tool-Schritt `tool_request_step` bleibt
  - wann ein sicherer Tool-Schritt als `tool_execution_step` geplant werden
    darf
  - und dass Runtime-Ergebnisse den geplanten Tool-Step-Typ nicht rueckwaerts
    mutieren duerfen (2026-04-13)
- Sichere Query-Tools koennen jetzt im Plan erstmals als echte
  `tool_execution_step` materialisiert werden, statt wegen `SAFE` wieder in
  einen Analyse-Schritt zu kippen. Beispiel: `blueprint_list` bleibt auf dem
  Tool-Schritt sichtbar und verliert seine Tool-Metadaten nicht mehr
  (2026-04-13)
- Runtime-Ergebnisse aus dem Orchestrator schreiben fuer Tool-Schritte jetzt
  den geplanten Step-Typ zurueck, statt hart auf `tool_execution_step` zu
  wechseln. Damit verschwindet die bisherige Rueckwaertsmutation
  `tool_execution_step -> tool_request_step` beim spaeteren Resume
  (2026-04-13)
- Risikobehaftete Tool-Flows werden jetzt sichtbar in zwei getrennte Schritte
  materialisiert statt als ein semantisch ueberladener Tool-Step:
  - `tool_request_step` fuer Vorbereitung / Rueckfrage / Freigabe
  - `tool_execution_step` fuer die eigentliche Ausfuehrung ueber den
    Orchestrator
  Sichere Query-Tools koennen weiter direkt als `tool_execution_step`
  laufen. Riskante Container-/MCP-/Skill-/Generik-Tool-Flows bekommen
  dagegen jetzt einen 5-Schritt-Plan mit expliziter Request-vor-Execution-
  Trennung (2026-04-13)
- `tool_request_step` fuehrt Tools nicht mehr direkt aus. Nur
  `tool_execution_step` geht ueber die Orchestrator-Bruecke. Bestaetigte
  User-Angaben werden dabei als `verified_artifacts` (`artifact_type =
  user_reply`) in den Folge-Schritt getragen und im Ausfuehrungsprompt wieder
  sichtbar injiziert (2026-04-13)
- Capability-Ableitung und Tool-Scoping fuer sichtbare Tool-Schritte in neues
  Modul ausgelagert:
  - `core/task_loop/capability_policy.py`
  Dort liegt jetzt zentral:
  - kanonische Tool-Familien (`container_manager`, `skill_cron`, `mcp`, `tool`)
  - action-first Capability-Ableitung aus dem gesamten Tool-Set statt nur vom
    ersten Tool
  - per-Step-Scoping fuer gemischte Container-Toolfolgen
    (`blueprint_list -> request_container`)
  Folge: im `tool_request_step` wird bei gemischten Container-Flows jetzt nur
  noch der eigentliche Action-Tool-Pfad sichtbar gemacht, waehrend der
  `tool_execution_step` den ausfuehrbaren Gesamtpfad traegt (2026-04-13)
- Gemischte Container-Toolfolgen bekommen jetzt einen eigenen sichtbaren
  Planner-Slice in neuem Modul:
  - `core/task_loop/container_flow_policy.py`
  Fuer `blueprint_list -> request_container` wird nicht mehr nur ein
  action-first Toolhaufen geplant, sondern eine sichtbare Kette:
  - Ziel klaeren
  - Discovery/Blueprint-Basis pruefen (`tool_execution_step` mit Query-Tool)
  - Container-Anfrage zur Freigabe vorbereiten (`tool_request_step`)
  - Container-Anfrage ausfuehren (`tool_execution_step`)
  - Zwischenstand zusammenfassen
  Damit ist die im Plan geforderte Discovery-vor-Request-vor-Execution-Kette
  fuer den ersten Container-Mischfall jetzt konkret materialisiert
  (2026-04-13)
- Container-Request-Auswahlpolicy in neues Modul ausgelagert:
  - `core/task_loop/container_request_policy.py`
  Der `tool_request_step` fuer `request_container` liest jetzt verifizierte
  Discovery-Artefakte aus vorherigem `blueprint_list`-Evidence, erkennt
  gewaehlte Blueprint-IDs und stoppt bei mehreren verifizierten Optionen
  gezielt in `waiting_for_user`, statt in generische Zusammenfassung oder
  vorschnelle Freigabe zu kippen. Die gewaehlte Blueprint-Auswahl wird als
  `blueprint_selection`-Artefakt in den Folge-Schritt getragen und im
  Execution-Prompt wieder sichtbar gemacht (2026-04-13)
- Container-Request-Parameterlogik in neues Modul ausgelagert:
  - `core/task_loop/container_parameter_policy.py`
  Der `tool_request_step` fuer `request_container` erkennt jetzt erste
  Basisparameter aus User-Reply und Snapshot-Artefakten:
  - Blueprint-Auswahl
  - CPU
  - RAM
  - GPU/Runtime
  - Ports
  - Dauer/Laufzeit
  Fehlende Basisangaben fuehren jetzt gezielt zu `waiting_for_user` statt in
  generische Freigabe oder Abschluss zu kippen. Erkannte Angaben werden als
  `container_request_params`-Artefakt in den Folge-Schritt getragen und im
  Execution-Prompt wieder sichtbar gemacht (2026-04-13)
- Failure-/Retry-Semantik fuer technische Tool-Fehler in neues Modul
  ausgelagert:
  - `core/task_loop/failure_policy.py`
  Ein `tool_execution_step` mit technischem Fehlschlag landet jetzt nicht mehr
  sofort als harter Sackgassen-Block, sondern geht als
  `waiting_for_user` in einen sichtbaren Retry-/Replan-Pfad ueber.
  Der fehlgeschlagene Ausfuehrungsstatus bleibt dabei in
  `last_step_result.status=failed` erhalten (2026-04-13)
- Budget-Stop im Loop als erster Slice entwaffnet:
  `build_task_loop_step_plan` setzt keinen harten
  `_output_time_budget_s=8.0`-Abbruch mehr, sondern markiert den Schritt mit
  `_task_loop_disable_output_budget=true`.
  Der Output-Layer behandelt Loop-Step-Runtime jetzt mit langem technischem
  Timeout statt produktivem Budget-Stop (2026-04-13)

Noch nicht vollstaendig umgesetzt:

- der Loop laeuft intern noch zu stark als eigener Step-/Prompt-Kanal; genau
  das fuehrt aktuell zu Drift zwischen normalem Chatturn und Loop-Resume
- per-Step-Zeitbudget wirkt im Loop noch als technischer Abbruchpfad; das ist
  nach der Entscheidung vom 2026-04-13 nicht mehr gewollt
- Timeout-/Fallback-Faelle landen noch nicht sauber als strukturierte
  Loop-Zustaende, sondern teils nur als gestreamter Text
- Meta-Fragen an einen aktiven Loop werden noch nicht sauber als normale
  User-Turns behandelt; ein erster Slice inklusive Rueckschreibung in den
  aktiven Snapshot ist umgesetzt, aber die spaetere fachliche Einordnung des
  Turn-Ergebnisses in `next_action` / Step-Fortsetzung fehlt noch
- `tool_request_step` und `tool_execution_step` sind im aktuellen
  Uebergangspfad jetzt fuer riskante Tool-Flows sichtbar getrennt; die harte
  Rueckwaertsmutation ist gefixt, aber die vollstaendig fachliche Ausformung
  der Request-vs-Execution-Kette ist noch nicht fuer alle Capability-Pfade
  und Retry-/Failure-Faelle ausmodelliert
- Approval-/Resume-Semantik fuer Tool-Schritte ist als erster Slice
  umgesetzt, aber noch nicht fuer alle Status- und Retry-Faelle
  vollstaendig ausmodelliert
- konkrete Capability-Pfade fuer MCP, Container und Cron/Skills sind erst als
  gemeinsamer Bridge-Vertrag und erster Container-Request-Slice vorbereitet,
  aber noch nicht produktvollstaendig ausgebaut
- progressive Render-Überprüfung steht noch aus: WebUI buffert möglicherweise
  Stream-Events bis Ende statt sie schrittweise anzuzeigen — erst nach
  echtem End-to-End-Test verifizierbar

---

## Anlass

Der aktuelle Task-Loop ist produktiv nutzbar, aber der Turn-Einstieg ist noch
als frueher Shortcut gebaut:

- explizite Marker wie `Task-Loop:` oder `Planungsmodus` triggern den
  sichtbaren Loop bereits vor dem normalen Thinking -> Sequential -> Control-
  Pfad
- innerhalb des Task-Loops ist `Control` inzwischen pro Schritt wieder aktiv
- damit existieren auf Turn-Ebene und Step-Ebene zwei unterschiedlich starke
  Entscheidungszonen

Das war fuer einen ersten engen Produktpfad vertretbar, passt aber nicht mehr
zur jetzt festgezogenen Zielrichtung:

- der sichtbare `task_loop` soll kuenftig der Obermodus fuer komplexe Faelle
  sein
- auch dann, wenn innerhalb des Loops Tool-, MCP-, Container- oder Cronjob-
  Schritte vorkommen

Der bereits dokumentierte Altfehler in anderen Straengen war:

- `Control` zeigte sichtbar `approved=True`
- spaeter entschieden weitere Schatten-Autoritaeten faktisch noch einmal neu
- daraus entstanden Drift, semantische Aufweichung und Halluzinationspfade

Genau dieses Muster darf fuer den sichtbaren Loop nicht erneut entstehen.

---

## Ziel

Der sichtbare `task_loop` soll kein frueher Shortcut mehr sein, sondern ein
autoritativer Turn-Modus fuer komplexe Arbeit.

Dabei gilt:

1. Thinking darf den Loop als Rohsignal oder Kandidat bekannt machen
2. Control darf als einzige Policy-Autoritaet entscheiden, ob dieser Turn im
   `task_loop` laufen soll
3. Der Orchestrator darf downstream nur noch die autoritative
   Turn-Entscheidung lesen
4. Triggerwoerter und Request-Flags bleiben Eingangssignale, nicht mehr die
   finale Routing-Wahrheit
5. Tool-, MCP-, Container- und Cronjob-Schritte bleiben im sichtbaren Loop
   moeglich, laufen aber ueber Orchestrator plus Control
6. Der Loop ist kein separater innerer Kanal, sondern sichtbarer Zustand des
   normalen Chatturns
7. Budget ist im Loop kein Stop-Gate; der Loop stoppt nur bei echten Guards,
   Fehlern, Blockern, User-Waits oder explizitem Abbruch

Kurzform:

- Thinking liefert Kandidaten
- Control schreibt den Turn-Modus
- der Loop ist der sichtbare Arbeitsrahmen des normalen Chatturns
- Orchestrator ist die Ausfuehrungsbruecke

---

## Nicht-Ziel

Dieser Plan fuehrt bewusst **keine** zweite Routing- oder
Ausfuehrungsautoritaet neben Control ein.

Insbesondere soll **nicht** gebaut werden:

- ein frueher `Mode Router` mit eigener finaler Autoritaet neben Control
- ein simples `if needs_sequential_thinking and complexity > X then task_loop`
- ein isolierter Chat-Loop, der bei Toolbedarf in einen separaten Obermodus
  kippt
- ein separater Step-Prompt-Kanal, der normale Chatsemantik und Meta-Fragen
  vom restlichen System abschottet
- ein Budget-Stop im Loop, der aktive Arbeit nur wegen Zeitbudget abbricht
- ein sichtbarer Loop, der direkt MCP/Container/Cron ausfuehrt und dabei
  Control oder Orchestrator umgeht

Vor Control sind Rohsignale erlaubt.
Bindende Modusentscheidungen ausserhalb von Control sind nicht erlaubt.

---

## Architekturprinzipien

### 1. Single Control Authority auch fuer Turn-Modi

Die bestehende Doku definiert bereits:

- `Control ist die Policy-Autoritaet`
- `control_decision ist downstream read-only`
- `nur Control trifft Policy-Entscheidungen`

Dieser Grundsatz wird auf den Turn-Modus erweitert:

- `single_turn`
- `task_loop`
- `interactive_defer`

sind kuenftig keine impliziten Heuristik-Endzustaende mehr, sondern
autoritative Modusentscheidungen.

### 2. Thinking kennt den Loop nur als Kandidat

Thinking darf kuenftig ausdruecklich semantisch markieren:

- mehrstufig
- sichtbare Zwischenphasen sinnvoll
- erwartete Schrittzahl / Komplexitaet
- moeglicher Tool-/MCP-/Container-/Cron-Bedarf innerhalb eines sichtbaren
  Arbeitsfadens

Aber Thinking darf damit noch **nicht** final entscheiden:

- dass der Turn im sichtbaren `task_loop` landet
- dass `Sequential` automatisch gleich `task_loop` bedeutet
- dass Tool- oder Runtime-Bedarf den sichtbaren Loop ausschliesst

### 3. Explizite Trigger bleiben Input-Signale

Marker wie:

- `Task-Loop:`
- `im Task-Loop Modus`
- Request-Flag `task_loop=true`

bleiben wertvoll, aber nur als Input an Thinking und spaeter an Control.

Sie duerfen den Turn nicht mehr vor Control final in den Task-Loop
kurzschliessen.

### 4. Der sichtbare Loop ist Obermodus, nicht Nebenpfad

Wenn `task_loop` autoritativ gewaehlt wurde, bleibt der sichtbare Loop der
Rahmen fuer komplexe Arbeit:

- Analyse-Schritte
- Tool-Anfrage-Schritte
- Tool-Ausfuehrungsschritte
- Wartezustaende fuer User oder Approval
- Blockierungs- oder Stopzustaende

Der Loop bleibt sichtbar, auch wenn darunter Orchestrator-Schritte mit Tools,
MCP, Container-Manager oder Cronjob-Logik laufen.

### 4b. Der sichtbare Loop ist Zustand, kein separater Kanal

Der Loop darf den normalen Chatturn nicht durch einen zweiten internen Kanal
ersetzen.

Das bedeutet:

- jede User-Nachricht bleibt ein normaler Turn im normalen Orchestrator
- der aktive Loop wird als Kontext injiziert:
  - aktueller Schritt
  - offene Frage
  - verifizierte Artefakte
  - erwartete naechste Aktion
- Meta-Fragen wie `was ist passiert?` bleiben normale Fragen an denselben
  Assistenten und duerfen nicht blind als Step-Parameter-Resume behandelt
  werden
- der Loop persistiert sichtbaren Arbeitszustand, besitzt aber keine zweite
  eigene Turn-Interpretation

### 5. Orchestrator ist die Step-Ausfuehrungsbruecke

Der sichtbare Loop wird nicht selbst zur Tool- oder Runtime-Autoritaet.

Stattdessen gilt:

- der Loop plant und zeigt den Arbeitsfaden
- der Orchestrator fuehrt Step-Anfragen aus
- Control prueft pro riskantem oder ausfuehrendem Schritt

Der Leitsatz ist:

- der Loop ist der sichtbare Arbeitsmodus
- der Orchestrator ist die Ausfuehrungsbruecke
- Control bleibt die Freigabeautoritaet

### 5b. Budget ist kein produktiver Loop-Guard

Im sichtbaren Loop darf ein per-Step- oder per-Output-Budget nicht als
primaerer Stopgrund wirken.

Zulaessige Stopgruende sind:

- `waiting_for_user`
- `waiting_for_approval`
- `blocked`
- `failed`
- `loop_detected`
- `no_progress`
- `user_cancelled`

Nicht zulaessig als normaler Produktabbruch:

- Stop nur wegen `_output_time_budget_s`
- Abbruch nur weil ein Schritt laenger denkt oder laenger streamt

Wenn technische Timeouts auftreten, muessen sie als strukturierter
Runtime-Fehler oder Retry-Fall im Loop landen, nicht als stiller
Budget-Abschluss.

### 6. Step-Level-Control bleibt erhalten

Wenn der Turn bereits autoritativ als `task_loop` gewaehlt wurde, bleibt der
bestehende per-Step-Control-Pfad sinnvoll:

- `Control.verify(...)` pro Schritt
- Guard-/Repair-Pfade pro Schritt
- Reflection-/Stop-Entscheidungen pro Schritt

Turn-Level-Moduswahl und Step-Level-Freigabe bleiben damit getrennte
Verantwortungen.

---

## Sollbild

### Heutiger problematischer Grobpfad

Historisch:

`Intent confirmation -> frueher Task-Loop-Shortcut -> eigener Task-Loop-Pfad`

Aktueller Zwischenstand:

- neue Task-Loop-Starts laufen bereits ueber
  `Thinking -> Control -> _authoritative_turn_mode`
- nur aktive Loop-Fortsetzung haengt noch teilweise an frueher Sonderlogik
- innerhalb des aktiven Loops existiert aktuell noch zu viel eigener
  Step-/Prompt-/Resume-Sonderpfad; genau dieser Teil wird ab 2026-04-13 als
  Rueckbauziel behandelt

waehrend im Normalpfad weiterhin gilt:

`Thinking -> Sequential -> Control -> Output`

### Zielpfad

`Intent confirmation -> Thinking -> optional Sequential -> Control -> autoritativer turn_mode -> Routing`

Erst **nach** der Control-Entscheidung wird verzweigt:

- `turn_mode=single_turn` -> normaler Antwortpfad
- `turn_mode=task_loop` -> sichtbarer Obermodus fuer komplexe Arbeit im
  normalen Chatflow
- `turn_mode=interactive_defer` -> konservativer interaktiver Antwortpfad

Innerhalb von `task_loop` gibt es dann unterschiedliche Step-Typen:

- `analysis_step`
- `response_step`
- `tool_request_step`
- `tool_execution_step`
- `waiting_for_approval`
- `waiting_for_user`
- `blocked`
- `completed`

Tool-Ausfuehrung bleibt damit kein konkurrierender Hauptmodus mehr, sondern
eine Schrittart innerhalb des sichtbaren Loops.

Wichtige Praezisierung ab 2026-04-13:

- der `task_loop` ist kein separater Step-Chatpfad neben normalem Output und
  Orchestrator
- der normale Turn laeuft weiter durch denselben Stack
- der Loop liefert nur sichtbare Struktur, Zustand und Persistenz
- das Ergebnis eines normalen Turns wird danach in den aktiven Loop
  zurueckgeschrieben

---

## Neuer Contract

### Block A - Thinking kennt den Loop als Rohsignal

Thinking erhaelt zusaetzlich bekannte, aber nicht-autoritative Felder fuer den
sichtbaren Loop als Turn-Modus.

Empfohlene neue Thinking-Felder:

- `task_loop_candidate: true/false`
- `task_loop_kind: "visible_multistep" | "none"`
- `task_loop_confidence: 0.0-1.0`
- `task_loop_reason: string`
- `estimated_steps: int`
- `needs_visible_progress: true/false`
- `loop_tool_tendency: "none" | "possible" | "likely"`

Bestehende Felder bleiben weiter relevant:

- `needs_sequential_thinking`
- `sequential_complexity`
- `suggested_tools`
- `needs_memory`
- `resolution_strategy`
- `strategy_hints`

Wichtig:

- `needs_sequential_thinking=true` darf niemals alleine `task_loop_candidate`
  erzwingen
- explizite Task-Loop-Marker duerfen `task_loop_candidate` hochsetzen, aber
  nicht selbst final routen
- Tool- oder Runtime-Bedarf darf den Thinking-Kandidaten nicht automatisch
  aufheben

### Block B - Control kennt Turn-Modus als autoritative Option

Control erweitert seinen bindenden Contract um eine autoritative
Turn-Modusentscheidung.

Empfohlene neue autoritative Felder:

- `_authoritative_turn_mode`
- `_authoritative_turn_mode_reason`
- `_authoritative_turn_mode_reasons`
- `_authoritative_turn_mode_blockers`

Empfohlene Werte fuer `_authoritative_turn_mode`:

- `single_turn`
- `task_loop`
- `interactive_defer`

Beispiele:

- komplexe mehrstufige Aufgabe mit sichtbarem Fortschrittsnutzen
  -> `task_loop`
- normale Frage oder geringe Komplexitaet
  -> `single_turn`
- interaktiv konservativ / User will eher kurze Antwort
  -> `interactive_defer`

### Block C - Task-Loop kennt Step-Typen und Step-Zustaende

Der sichtbare Loop braucht einen expliziten Contract fuer innere
Schrittausfuehrung.

Wichtige Praezisierung:

Die Step-Typen sind ein sichtbarer Arbeitsvertrag, aber kein eigener zweiter
Prompt-Kanal. Sie beschreiben den Zustand des normalen Turns im Loop, nicht
eine davon getrennte Mini-Welt.

Empfohlene neue Step-Felder:

- `step_type`
- `step_requires_control`
- `step_requires_approval`
- `step_execution_source`
- `step_result_artifacts`
- `next_action`

Empfohlene Werte:

- `step_type=analysis_step`
- `step_type=response_step`
- `step_type=tool_request_step`
- `step_type=tool_execution_step`

`step_execution_source` soll sichtbar machen, ob der Schritt:

- rein im Loop beantwortet wurde
- ueber Orchestrator ausgefuehrt wurde
- in Approval wartet
- blockiert wurde

### Block E - Universeller Step-Bridge-Contract

Bevor einzelne MCP-, Container-, Cronjob- oder Skill-Sonderfaelle modelliert
werden, braucht der sichtbare Loop genau **einen** universellen
Bridge-Contract zum Orchestrator.

Ziel:

- keine capability-spezifischen Sonderpfade als neue Wahrheiten
- keine direkte Tool-Logik im sichtbaren Loop
- ein einheitlicher Request-/Result-Vertrag fuer alle Schrittarten

#### 1. `task_loop_step_request`

Der Loop uebergibt an den Orchestrator einen strukturierten Schrittauftrag.

Empfohlene Pflichtfelder:

- `turn_id`
- `loop_id`
- `step_id`
- `step_index`
- `step_type`
- `objective`
- `step_goal`
- `step_title`
- `artifacts_so_far`
- `requested_capability`
- `suggested_tools`
- `requires_control`
- `requires_approval`

Empfohlene optionale Felder:

- `risk_context`
- `reasoning_context`
- `user_visible_context`
- `allowed_tool_scope`
- `timeout_hint_s`
- `origin="task_loop"`

Praezisierung ab 2026-04-13:

- `timeout_hint_s` ist nur noch ein technischer Hinweis fuer Beobachtung,
  Telemetrie oder spaetere Retry-Strategien
- `timeout_hint_s` darf keinen produktiven Loop-Stop mehr erzwingen

Semantik:

- der Request beschreibt **was** der Schritt erreichen soll
- nicht bereits autoritativ **wie** der Schritt policy-seitig erlaubt ist
- der Loop darf also einen Schritt anfragen, aber nicht selbst freigeben

#### 2. `task_loop_step_result`

Der Orchestrator gibt einen strukturierten Schrittbefund an den Loop zurueck.

Empfohlene Pflichtfelder:

- `turn_id`
- `loop_id`
- `step_id`
- `step_type`
- `status`
- `control_decision`
- `execution_result`
- `verified_artifacts`
- `user_visible_summary`
- `next_action`

Empfohlene optionale Felder:

- `warnings`
- `blockers`
- `approval_request`
- `trace_reason`
- `step_execution_source`

Semantik:

- `verified_artifacts` sind die einzige vererbbare Wahrheit fuer den
  naechsten Schritt
- freie Prosa oder rohe Tool-Logs werden nicht selbst zur Wahrheitsquelle
- `user_visible_summary` ist fuer Chat/Planbox gedacht, nicht fuer
  interne Weitervererbung

#### 3. Status-Semantik

Empfohlene Werte fuer `status`:

- `completed`
- `waiting_for_approval`
- `waiting_for_user`
- `blocked`
- `failed`

Bedeutung:

- `completed`
  - Schritt ist abgeschlossen
  - `verified_artifacts` koennen in den naechsten Schritt uebernommen werden
- `waiting_for_approval`
  - der Schritt ist fachlich vorbereitet, darf aber ohne Freigabe nicht weiter
  - ein Approval-/Control-Gate ist offen
- `waiting_for_user`
  - es fehlt primaer Input, Auswahl oder Antwort des Users
  - kein harter Policy-Block, sondern Interaktionspause
- `blocked`
  - der Schritt ist durch Policy, Risk oder fehlende zulaessige
    Ausfuehrungsmoeglichkeit blockiert
  - ohne Moduswechsel oder neue Bedingung nicht fortsetzbar
- `failed`
  - technischer oder ausfuehrungsbezogener Fehlschlag
  - nicht automatisch ein Policy-Block

#### 4. Abgrenzung der Wartezustaende

Die drei Zustaende muessen hart getrennt bleiben:

- `waiting_for_approval`
  - Control-/Policy-nahe Freigabe steht aus
  - Beispiel: riskanter Tool-Schritt ist erkannt, aber noch nicht bestaetigt
- `waiting_for_user`
  - der User muss inhaltlich antworten, entscheiden oder praezisieren
  - Beispiel: Blueprint-Auswahl oder inhaltliche Rueckfrage
- `blocked`
  - auch mit sofortiger User-Antwort waere der Schritt aktuell nicht zulaessig
    oder nicht sinnvoll ausfuehrbar

Ohne diese Trennung vermischt sich wieder:

- Interaktion
- Policy
- technische Ausfuehrung

und genau daraus entsteht spaeter Drift.

#### 4b. Zustandsmaschine fuer Step-Typen

Neben der Status-Semantik braucht der sichtbare Loop klare erlaubte
Uebergaenge zwischen Step-Typen und Step-Zustaenden.

Ziel:

- keine versteckten Seitenspruenge
- kein impliziter Wechsel von Analyse zu Tool-Ausfuehrung ohne sichtbaren
  Schritt
- keine Vermischung von Approval, User-Wait und Blockierung

##### A. Empfohlener Startpunkt

Ein neuer geplanter Schritt startet typischerweise als:

- `analysis_step`
  oder
- `tool_request_step`

Nicht als direkter `tool_execution_step`, ausser der Plan ist bereits
hinreichend konkret und der Schritt ist explizit als Ausfuehrung modelliert.

##### B. Erlaubte Kernuebergaenge

Erlaubte Uebergaenge fuer Step-Typen:

- `analysis_step -> response_step`
- `analysis_step -> tool_request_step`
- `analysis_step -> waiting_for_user`
- `analysis_step -> blocked`

- `response_step -> completed`
- `response_step -> analysis_step`
- `response_step -> tool_request_step`
- `response_step -> waiting_for_user`

- `tool_request_step -> tool_execution_step`
- `tool_request_step -> waiting_for_approval`
- `tool_request_step -> waiting_for_user`
- `tool_request_step -> blocked`

- `tool_execution_step -> completed`
- `tool_execution_step -> analysis_step`
- `tool_execution_step -> response_step`
- `tool_execution_step -> waiting_for_approval`
- `tool_execution_step -> waiting_for_user`
- `tool_execution_step -> blocked`
- `tool_execution_step -> failed`

Erlaubte Uebergaenge fuer Status:

- `pending -> running`
- `running -> completed`
- `running -> waiting_for_approval`
- `running -> waiting_for_user`
- `running -> blocked`
- `running -> failed`

- `waiting_for_approval -> running`
- `waiting_for_approval -> blocked`
- `waiting_for_approval -> completed`

- `waiting_for_user -> running`
- `waiting_for_user -> blocked`
- `waiting_for_user -> completed`

- `failed -> analysis_step`
- `failed -> blocked`

##### C. Bedeutungsregeln der Uebergaenge

- `analysis_step -> tool_request_step`
  - aus Analyse entsteht ein konkreter Ausfuehrungsbedarf
  - Beispiel: "um weiter zu verifizieren, brauche ich Container-Status"

- `tool_request_step -> tool_execution_step`
  - Capability und Ziel sind ausreichend konkret
  - Control hat keinen offenen Vorbehalt oder der Schritt ist read-only sicher

- `tool_request_step -> waiting_for_approval`
  - Capability ist erkannt, aber eine Freigabe ist vor Ausfuehrung noetig

- `tool_request_step -> waiting_for_user`
  - Capability ist erkannt, aber Ziel, Auswahl oder Parameter sind noch offen

- `tool_execution_step -> analysis_step`
  - das Tool-Ergebnis muss erst wieder ausgewertet werden, bevor ein naechster
    sichtbarer Antwort- oder Ausfuehrungsschritt sinnvoll ist

- `tool_execution_step -> response_step`
  - die verifizierten Artefakte reichen direkt fuer einen sichtbaren
    Zwischenstand oder Abschluss

- `tool_execution_step -> blocked`
  - Policy, Risk oder harte Laufzeitbedingungen verhindern die Fortsetzung

- `tool_execution_step -> failed`
  - technische Ausfuehrung ist fehlgeschlagen, ohne dass schon klar ist, ob
    ein Policy-Block vorliegt

##### D. Nicht erlaubte Kurzschluesse

Nicht erlaubt sein sollen insbesondere:

- `analysis_step -> tool_execution_step`
  ohne expliziten `tool_request_step`, wenn noch keine konkrete Capability-
  Entscheidung sichtbar gemacht wurde
- `waiting_for_user -> tool_execution_step`
  ohne Rueckkehr in einen laufenden validierten Schritt
- `waiting_for_approval -> completed`
  ohne dokumentierte Freigabe oder expliziten Abbruchpfad
- `failed -> completed`
  ohne neue Analyse, Retry-Entscheidung oder verifizierten Ersatzpfad

Damit bleibt die Schrittmaschine fuer UI, Persistenz und Tests nachvollziehbar.

##### E. `next_action` als Uebergangsanker

`next_action` soll den naechsten erlaubten Schritt explizit machen.

Empfohlene Werte:

- `continue_analysis`
- `render_response`
- `prepare_tool_request`
- `execute_tool_step`
- `await_user_input`
- `await_approval`
- `stop_blocked`
- `retry_or_replan`

`next_action` ist kein zweiter Policy-Entscheider, sondern nur der
explizite Uebergangsanker zwischen:

- Step-Type
- Status
- user-sichtbarer Fortsetzung

##### F. Neue harte Invariante ab 2026-04-13

Ein fachlicher Schritt darf nicht zwischen Plan und Runtime rueckwaerts
seinen Typ wechseln.

Insbesondere unzulaessig:

- derselbe Schritt wird im Plan als `tool_request_step` gefuehrt
- zur Laufzeit als `tool_execution_step` fortgeschrieben
- und beim Resume wieder als `tool_request_step` geladen

Das ist kein erlaubter Fachuebergang, sondern Vertragsdrift zwischen
Plan-Semantik und Runtime-Semantik.

Der Plan muss deshalb kuenftig sauber zwischen unterscheiden:

- sichtbarer Anfrageschritt
- sichtbarer Ausfuehrungsschritt
- oder ein einziger runtimegebundener Tool-Schritt mit internem Statuswechsel

aber nicht beides vermischen.

#### 5. Vererbbare Artefakte

`verified_artifacts` sollen bewusst klein und strukturiert bleiben.

Empfohlene Inhalte:

- `findings`
- `selected_option`
- `tool_result_refs`
- `runtime_evidence_refs`
- `open_questions`
- `approved_next_capabilities`
- `next_step_hint`

Nicht vererbbar als Wahrheit:

- rohe Modellprosa
- ungepruefte Tool-Logs
- freie implizite Schlussfolgerungen aus einem vorherigen Schritt

#### 6. Warum dieser Contract zuerst kommt

Wenn dieser universelle Contract unscharf bleibt, entstehen spaeter fast
sicher wieder capability-spezifische Schattenpfade:

- MCP macht es anders
- Container-Manager macht es anders
- Cronjob-/Skill-Pfade machen es anders

Dann gaebe es erneut mehrere Wahrheiten statt einer konsistenten
Step-Ausfuehrungslogik.

#### 7. Erste konkrete Capability-Mappings

Damit der universelle Contract nicht abstrakt bleibt, werden die drei ersten
Zielpfade bewusst auf denselben Vertrag gemappt:

- MCP
- Container-Manager
- Cronjobs / Skills

Wichtig:

- diese Pfade bekommen **keine** eigenen konkurrierenden Request-/Result-
  Strukturen
- sie fuellen denselben `task_loop_step_request` /
  `task_loop_step_result` nur capability-spezifisch aus

##### A. MCP-Schritte

Typische Faelle:

- Daten abrufen
- Analyse ueber MCP-Tool
- strukturierte externe Runtime- oder Service-Information lesen

Empfohlenes `requested_capability`:

- `capability_type="mcp_call"`
- `capability_target="<server_or_tool_family>"`
- `capability_action="<tool_name_or_operation>"`

Typische `suggested_tools`:

- konkrete MCP-Tools oder ein kanonischer Tool-Name, den Control bereits kennt

Typische `execution_result`:

- `tool_statuses`
- `raw_result_ref`
- `structured_result`
- `runtime_evidence`

Typische `verified_artifacts`:

- `findings`
- `runtime_evidence_refs`
- `tool_result_refs`
- `open_questions`

Semantik:

- der Loop sieht nicht den vollen rohen MCP-Payload als Wahrheit
- er erbt nur die verifizierten Findings und Referenzen

##### B. Container-Manager-Schritte

Typische Faelle:

- Container-Status lesen
- Container starten / stoppen
- Blueprint oder Binding pruefen
- Inventory / Capability / Runtime-Befunde holen

Empfohlenes `requested_capability`:

- `capability_type="container_operation"`
- `capability_target="<container_or_blueprint_context>"`
- `capability_action="<inspect|list|start|stop|exec|bind|inventory>"`

Typische `suggested_tools`:

- kanonische Container-Tools wie `list_containers`, `request_container`,
  `container_stats`, `exec_in_container`

Typische `execution_result`:

- `tool_statuses`
- `container_state`
- `binding_state`
- `runtime_evidence`
- `selection_required`

Typische `verified_artifacts`:

- `selected_option`
- `runtime_evidence_refs`
- `tool_result_refs`
- `approved_next_capabilities`
- `open_questions`

Wichtig fuer die Status-Semantik:

- fehlende Blueprint- oder Container-Auswahl ist primaer `waiting_for_user`
- riskanter Start-/Exec-Schritt kann `waiting_for_approval` sein
- policy-seitig verbotene oder nicht zulaessige Container-Aktion ist `blocked`

##### C. Cronjob- und Skill-Schritte

Typische Faelle:

- bestehenden Skill ausfuehren
- Cronjob-Status lesen
- Cronjob anlegen, aendern, aktivieren oder deaktivieren
- skill-nahe Hintergrundaufgabe starten

Empfohlenes `requested_capability`:

- `capability_type="skill_or_job_operation"`
- `capability_target="<skill_name_or_job_id>"`
- `capability_action="<run|inspect|create|update|enable|disable|schedule>"`

Typische `suggested_tools`:

- kanonische Skill-/Job-Tools oder die bereits bestehende Orchestrator-
  Runtime-Funktion dafuer

Typische `execution_result`:

- `tool_statuses`
- `job_state`
- `schedule_state`
- `run_result_ref`
- `runtime_evidence`

Typische `verified_artifacts`:

- `selected_option`
- `tool_result_refs`
- `runtime_evidence_refs`
- `approved_next_capabilities`
- `next_step_hint`

Wichtig fuer die Status-Semantik:

- fehlende Parameter oder unklare Zielauswahl ist `waiting_for_user`
- aktivierende / schreibende Job-Aenderung kann `waiting_for_approval` sein
- policy-seitig unzulaessige Job- oder Skill-Aktion ist `blocked`

#### 8. Gemeinsame Contract-Regeln fuer alle drei Pfade

Unabhaengig von MCP, Container oder Cronjob/Skill gilt:

- `requested_capability` beschreibt immer nur Ziel und Aktionsart, nicht schon
  die erlaubte Policy-Wahrheit
- `control_decision` bleibt die bindende Freigabe- oder Block-Instanz
- `execution_result` darf reichhaltig sein, aber nur `verified_artifacts`
  werden in den naechsten Loop-Schritt vererbt
- `user_visible_summary` darf erklaeren, aber keine neue Wahrheit setzen

#### 9. Minimaler gemeinsamer Capability-Kern

Um spaeter keine capability-spezifischen Sonderformen zu zementieren, sollte
`requested_capability` mindestens diesen gemeinsamen Kern tragen:

- `capability_type`
- `capability_target`
- `capability_action`

Optional erweiterbar:

- `capability_params`
- `capability_scope`
- `capability_constraints`

Damit bleibt der Vertrag klein genug fuer einen universellen Dispatcher und
gross genug fuer konkrete Adapter.

### Block D - Orchestrator liest nur noch die autoritative Modusentscheidung

Der Orchestrator darf downstream nicht mehr selbst final raten:

- kein frueher Task-Loop-Short-Circuit ueber Keywords
- kein spaetes stilles Re-Routing ueber Heuristiken
- kein paralleler zweiter Modus-Resolver

Downstream gilt:

- lese `_authoritative_turn_mode`
- route exakt danach
- innerhalb von `task_loop` fuehre Step-Typen ueber den Orchestrator aus
- alles andere ist nur Trace/Debug-Kontext

---

## Entscheidungsregeln fuer Control

Control soll `task_loop` dann setzen, wenn der Turn zugleich:

- mehrstufig genug ist
- sichtbare Zwischenphasen produktseitig sinnvoll sind
- nicht als einfacher `single_turn` besser beantwortbar ist
- einen verfolgbaren Arbeitsfaden braucht
- auch bei moeglichem Toolbedarf sinnvoll im sichtbaren Rahmen bleiben soll
- nicht bewusst in `interactive_defer` gezogen werden sollte

Typische positive Signale:

- `task_loop_candidate=true`
- `needs_visible_progress=true`
- `estimated_steps >= 2`
- `needs_sequential_thinking=true`
- komplexe Analyse-, Pruef-, Umsetzungs- oder Diagnoseaufgabe
- moeglicher Tool-/MCP-/Container-/Cron-Bedarf innerhalb eines sichtbaren
  Arbeitsfadens

Typische Blocker fuer `task_loop`:

- expliziter User-Wunsch nach kurzer Sofortantwort
- stark interaktiver Kleinfall ohne Mehrwert durch sichtbare Zwischenphasen
- aktive Policy-/Risk-Blocker fuer den Gesamtturn

Wichtig:

- Tool-, Runtime-, Container- oder Cron-Bedarf blockiert `task_loop` nicht
  automatisch
- er verschiebt nur die Art der Schritte innerhalb des Loops

---

## Aktiver Loop-Zustand

Ein bereits aktiver Task-Loop bleibt ein starkes Signal, aber nicht mehr die
einzige Wahrheit.

Statt:

- `aktiver Loop => bleib blind im Loop`

soll kuenftig gelten:

- aktiver Loop geht als Signal in Thinking und Control ein
- Control kann autoritativ entscheiden:
  - `continue_active_task_loop`
  - `terminate_active_task_loop_completed`
  - `terminate_active_task_loop_blocked`
  - `terminate_active_task_loop_mode_shift`

Damit wird ein aktiver Loop kein stiller Zwangszustand.

---

## Invarianten

1. `needs_sequential_thinking=true` darf niemals alleine `task_loop`
   erzeugen
2. `task_loop_candidate=true` aus Thinking ist nicht autoritativ
3. nur Control darf den finalen Turn-Modus setzen
4. downstream darf den Turn-Modus nicht still neu interpretieren
5. Tool-, MCP-, Container- oder Cron-Bedarf darf `task_loop` nicht
   automatisch ausschliessen
6. kein Tool-, MCP-, Container- oder Cron-Schritt im sichtbaren Loop ohne
   erneute Control-Pruefung, wenn Risiko oder Freigabe relevant sind
7. der sichtbare Loop darf Orchestrator-Funktionalitaet nutzen, aber keine
   zweite Tool- oder Policy-Autoritaet bilden
8. ein aktiver Loop darf Fortsetzung beguenstigen, aber nicht blind erzwingen
9. Step-Level-Control darf Turn-Level-Moduswahl nicht ersetzen

---

## Umsetzungsblaecke

## Block 1 - Thinking-Schema fuer Loop-Kandidaten erweitern

Status: **umgesetzt**

### Ziel

Thinking kennt den sichtbaren Loop semantisch als moeglichen Bearbeitungsmodus,
aber nur als Rohsignal.

### Aenderungen

- `core/layers/thinking.py`
  - Schema und Prompt um Loop-Kandidaten erweitern
- `core/orchestrator_plan_schema_utils.py`
  - neue Felder validieren und auf sichere Defaults setzen
- `core/loop_trace.py`
  - Thinking-/Normalizer-Trace um Loop-Kandidaten erweitern

### Akzeptanzkriterium

Thinking kann fuer geeignete Prompts sichtbar markieren:

- `task_loop_candidate=true`
- `estimated_steps>=2`
- `needs_visible_progress=true`

ohne damit schon einen Task-Loop zu starten.

Ist-Stand:

- umgesetzt in `core/layers/thinking.py`
- normalisiert in `core/orchestrator_plan_schema_utils.py`
- durch Tests abgesichert

## Block 2 - Control-Contract um autoritativen Turn-Modus erweitern

Status: **umgesetzt**

### Ziel

Control kennt `task_loop` als bindende Turn-Option und schreibt diese
autoritative Entscheidung in den Turn-State.

### Aenderungen

- `core/layers/control.py`
  - Turn-Modus aus Thinking-Signalen und Policy-Blockern ableiten
- `core/control_contract.py`
  - autoritative Turn-Modus-Felder als Contract festhalten
- bestehende Contract-Helfer
  - Reason-Codes / Blocker strukturiert speichern

### Akzeptanzkriterium

Nach `Control.verify(...)` existiert fuer jeden Turn ein eindeutiger,
autoritativer Modus oder ein deterministischer Default.

Ist-Stand:

- umgesetzt in `core/layers/control.py` und `core/control_contract.py`
- `_authoritative_turn_mode=task_loop` wird bereits aus Thinking-Signalen plus
  Blockern abgeleitet
- Control-Skip wurde fuer Task-Loop-Kandidaten bewusst geschlossen

## Block 3 - Fruehen Task-Loop-Shortcut aus Sync und Stream zurueckbauen

Status: **teilweise umgesetzt**

### Ziel

Der Turn wird nicht mehr vor Control final in den Task-Loop kurzgeschlossen.

### Aenderungen

- `core/orchestrator_sync_flow_utils.py`
- `core/orchestrator_stream_flow_utils.py`
- `core/orchestrator_modules/task_loop.py`

Explizite Marker und Request-Flags werden:

- nicht entfernt
- aber in Thinking-/Control-Eingangssignale umgewandelt

### Akzeptanzkriterium

Ein neuer Turn wird erst **nach** Thinking und Control in `task_loop`
geroutet.

Ist-Stand:

- umgesetzt fuer neue Task-Loop-Starts in Sync und Stream
- der vorgelagerte Task-Loop-Planning-Pfad nutzt jetzt ebenfalls denselben
  Tool-Selection-/Capability-Exposure-Eingang wie der normale Orchestrator
- noch offen fuer die komplette Vereinheitlichung aktiver Loop-Fortsetzung

## Block 4 - Step-Contract fuer sichtbaren Loop erweitern

Status: **teilweise umgesetzt**

### Ziel

Der sichtbare Loop kann verschiedene Schrittarten sauber modellieren, ohne
selbst zur zweiten Ausfuehrungsautoritaet zu werden.

### Aenderungen

- `core/task_loop/contracts.py`
- `core/task_loop/planner.py`
- `core/task_loop/reflection.py`
- `core/task_loop/runner.py`

### Akzeptanzkriterium

Der Loop kann strukturiert unterscheiden zwischen:

- Analyse
- sichtbarer Antwort
- Tool-Anfrage
- Tool-Ausfuehrung
- Approval-Wait
- User-Wait
- Blockierung

Ist-Stand:

- `core/task_loop/contracts.py` traegt jetzt explizite Step-Typen,
  Step-Status und `step_execution_source`
- `TaskLoopSnapshot` speichert `current_step_id`, `current_step_type`,
  `current_step_status`, `verified_artifacts` und `last_step_result`
- der Runner fuehrt diese Felder bereits im Stream-Pfad mit
- der Planner baut bei sichtbarem Tool-Bedarf jetzt capability-naehere Plaene
  statt nur generische Analyse-/Validierungsschablonen
- Sync-/Manual-Pfade sind semantisch angeglichen, aber noch nicht vollstaendig
  auf dieselbe Bridge gehoben
- noch offen ist die saubere Materialisierung fuer gemischte Container-
  Toolfolgen wie `blueprint_list -> request_container`; der erste sichtbare
  Discovery-vor-Request-vor-Execution-Pfad ist jetzt fuer Container
  umgesetzt, aber noch nicht fuer andere Capability-Familien und noch nicht
  mit voller Artefakt-/Resume-Auswertung ueber alle Discovery-Faelle
- noch offen ist die saubere Trennung zwischen:
  - Discovery-/Vorbereitungsschritt
  - `waiting_for_user` bei fehlenden Parametern oder unklarer Auswahl
  - eigentlicher `request_container`-Schritt
  Erste Slices fuer unklare Blueprint-Auswahl und fehlende Basisparameter sind
  jetzt umgesetzt; offen bleibt noch die tiefere Parameter-/Intent-Auswertung
  jenseits der Basissignale:
  - Hardware-Intents
  - Mount-/Storage-Wuensche
  - Netz-/Port-Mapping mit Validierung
  - Laufzeit-/Runtime-Policies gegen konkrete Blueprint-Metadaten

## Block 5 - Step-Orchestrator-Bridge einfuehren

Status: **teilweise umgesetzt**

### Ziel

Tool-, MCP-, Container- und Cronjob-Schritte im sichtbaren Loop laufen ueber
den Orchestrator statt als Sonderlogik direkt aus dem Loop.

### Aenderungen

- `core/task_loop/step_runtime.py`
- neue duenne Bridge in `core/task_loop/`
- Orchestrator-Glue fuer step-basierte Ausfuehrung

Wichtig:

- der Loop ruft nicht direkt Tool-Hubs oder Runtime-Services als eigene
  Autoritaet
- er erstellt einen Schrittauftrag
- Orchestrator und Control fuehren ihn autoritativ aus

### Akzeptanzkriterium

Ein Loop-Schritt kann kontrolliert:

- MCP abrufen
- Container-Manager nutzen
- Skill-/Cronjob-nahe Ausfuehrung anstossen

ohne dass der sichtbare Loop selbst die Policy-Autoritaet spielt.

Ist-Stand:

- `core/task_loop/step_runtime.py` baut jetzt einen universellen
  `task_loop_step_request`
- Tool-Schritte koennen ueber den bestehenden Orchestrator-Vertrag laufen:
  - `_collect_control_tool_decisions(...)`
  - `_resolve_execution_suggested_tools(...)`
  - `_execute_tools_sync(...)`
- der erste funktionale Slice ist damit vorhanden, aktuell vor allem fuer den
  Streaming-Auto-Loop
- aktive Tool-Schritte in `waiting_for_approval` koennen bereits ueber
  denselben Bridge-Vertrag wieder aufgenommen werden
- aktive Tool-Schritte in `waiting_for_user` koennen jetzt mit konkreter
  User-Antwort ueber denselben Bridge-Vertrag wieder aufgenommen werden
- noch offen ist die volle End-to-End-Abdeckung fuer MCP-, Cronjob-/Skill- und
  nicht-triviale User-Resume-Pfade
- WebUI-Smoketests zeigen: die Bridge ist technisch erreichbar, wird fuer
  Container-Faelle aber noch nicht in jedem Loop-Lauf als echter Tool-Step
  materialisiert

## Block 6 - Aktiven Task-Loop auf autoritative Moduslogik umstellen

Status: **teilweise umgesetzt**

### Ziel

Fortsetzung, Abbruch oder Moduswechsel eines aktiven Loops laufen ebenfalls
ueber autoritative Reason-Codes statt ueber implizite Sonderfaelle.

### Aenderungen

- `core/task_loop/store.py`
- `core/task_loop/chat_runtime.py`
- `core/orchestrator_modules/task_loop.py`

### Akzeptanzkriterium

Ein aktiver Loop kann sauber:

- fortgesetzt
- abgeschlossen
- gestoppt
- blockiert
- in einen anderen Turn-Zustand ueberfuehrt

werden, ohne dass der Orchestrator still zwei Wahrheiten fuehrt.

Ist-Stand:

- aktive Loops werden im Sync- und Stream-Pfad nicht mehr blind vor Thinking
  plus Control kurzgeschlossen
- ein aktiver Loop wird jetzt als Signal in den Plan injiziert:
  - `_task_loop_active`
  - `_task_loop_active_state`
  - `_task_loop_continue_requested`
  - `_task_loop_cancel_requested`
  - `_task_loop_restart_requested`
- nach Control wird der aktive Loop ueber Reason-Codes geroutet:
  - `continue_active_task_loop`
  - `restart_active_task_loop`
  - `terminate_active_task_loop_cancelled`
  - `terminate_active_task_loop_mode_shift`
  - `terminate_active_task_loop_blocked`
- bei `mode_shift` oder `blocked` wird der aktive Loop aus dem Store geloest,
  statt weiter still als Zwangszustand mitzuschwingen

Noch offen:

- Persistenz-/Workspace-Ereignisse fuer `mode_shift` und `blocked` sind noch
  duenn
- der Resume-/Approval-Pfad fuer Tool-Schritte ist fuer
  `waiting_for_approval -> weiter` jetzt an denselben Runtime-Pfad gekoppelt
- `waiting_for_user -> neue konkrete User-Antwort` laeuft jetzt ebenfalls ueber
  denselben Runtime-Pfad
- ein schlichtes `weiter` haelt runtimegebundene Tool-Schritte in
  `waiting_for_user` jetzt bewusst im Wartezustand
- noch offen sind komplexere Resume-Faelle wie:
  - mehrstufige `failed -> retry_or_replan -> execution`-Ketten
  - mehrstufige Approval-Ketten

## Block 7 - UI/Trace auf autoritativen Turn-Modus und Step-Typen umstellen

Status: **teilweise umgesetzt**

### Ziel

Frontend und Trace zeigen nicht mehr indirekte Triggerheuristiken, sondern den
autoritativen Turn-Modus, die Step-Typen und ihre Gruende.

### Aenderungen

- Thinking-UI: Kandidat sichtbar, aber nicht als finale Autoritaet labeln
- Control-UI: finalen Turn-Modus und Reason-Codes zeigen
- Task-Loop-Planbox: Startgrund, Step-Typ, Approval-Waits und Blocker zeigen

### Akzeptanzkriterium

Die UI kann erklaeren:

- warum ein Turn im sichtbaren Task-Loop ist
- welcher Schritt gerade laeuft
- ob ein Tool-/MCP-/Container-/Cron-Schritt ansteht oder blockiert ist
- welche Blocker oder Gruende Control dafuer gesetzt hat

Ist-Stand:

- Thinking-UI/Stream-Payload traegt bereits Task-Loop-Kandidatensignale und
  `authoritative_turn_mode`
- Task-Loop-Stream-Updates tragen bereits `step_runtime`-Metadaten
- erster WebUI-Smoke ist erfolgreich fuer:
  - automatischen Task-Loop-Start ohne explizites `Task-Loop:`
  - sichtbares Step-Streaming
  - Thinking-/Control-/Task-Loop-Trace
- noch offen ist die vollstaendige Frontend-Auswertung fuer Step-Typ,
  Approval-Wait, Blocker und Reason-Codes
- noch offen ist das fachlich saubere UI-Verhalten fuer Container-Faelle:
  - container-spezifische Step-Titel statt generischem `Tool-*`
  - frueher `waiting_for_user`-Stop bei offenen Parametern
  - kein faelschliches `Task-Loop abgeschlossen` bei noch offener Rueckfrage
  Erste Slices fuer `waiting_for_user` bei mehrfacher Blueprint-Auswahl und
  fehlenden Basisparametern sind jetzt im Runtime-Pfad vorhanden; die
  UI-Auswertung dafuer ist aber noch nicht vollstaendig auf container-
  spezifische Auswahl- und Parametertexte gehoben
  Ein erster Slice fuer `waiting_for_user` bei mehrfacher Blueprint-Auswahl ist
  jetzt im Runtime-Pfad vorhanden; die UI-Auswertung dafuer ist aber noch nicht
  vollstaendig auf Container-spezifische Auswahltexte gehoben

---

## Tests

### Neue Contract-Tests

- Thinking-Plan kennt Loop-Kandidaten, aber keine autoritative Moduswahl
- Control setzt `_authoritative_turn_mode` deterministisch
- `needs_sequential_thinking=true` reicht allein nicht fuer `task_loop`
- explizites `Task-Loop:` wird ohne Control nicht direkt geroutet
- Tool-/MCP-/Container-/Cron-Bedarf blockiert `task_loop` nicht automatisch
- riskante Step-Typen erzwingen weiterhin Control/Approval
- aktiver Loop kann nicht blind jede Folgeeingabe absorbieren
- Step-Transition-Contract verbietet versteckte Spruenge
- Planner klassifiziert erste `tool_request_step`-Faelle strukturiert
- der Task-Loop-Planning-Adapter reicht denselben Tool-/Capability-Kontext wie
  der normale Orchestrator an Thinking weiter
- Planner-Rewrites verlieren `step_type`, `suggested_tools` und
  `requested_capability` nicht mehr
- der Stream-Runner kann einen Tool-Schritt ueber eine Orchestrator-Bridge
  ausfuehren

### Regressionsziele

- kein Wiederauftreten des alten Musters:
  - `Control` sagt A
  - spaeter entscheidet eine zweite Schattenlogik B
- kein Drift zwischen Sync- und Stream-Pfad
- keine neue implizite Autoritaet in Output, Runtime oder Step-Bridge

---

## Reihenfolge

1. Thinking-Contract fuer Loop-Kandidaten definieren
2. Control-Contract fuer autoritativen Turn-Modus definieren
3. Sync-/Stream-Routing auf `_authoritative_turn_mode` umstellen
4. Step-Contract fuer sichtbaren Loop definieren
5. Step-Orchestrator-Bridge fuer Tool-/MCP-/Container-/Cron-Schritte bauen
6. aktiven Loop-State an Reason-Codes koppeln
7. den Loop vom separaten Step-/Prompt-Kanal zum sichtbaren Turn-Zustand
   des normalen Chatflows zurueckbauen
8. Budget-Stop im Loop entwaffnen und Timeouts nur noch als strukturierte
   Fehler-/Retry-Zustaende behandeln
9. Resume-Semantik fuer Meta-Fragen, User-Input und Approval sauber auf normale
   Turns ausrichten
10. `tool_request_step` vs. `tool_execution_step` fachlich sauber trennen
11. UI/Trace auf den neuen Contract ziehen
12. erst danach Prompt-/Produktpolish fuer Step-Antworten weiter haerten

Aktueller Fortschritt:

1. abgeschlossen
2. abgeschlossen
3. fuer neue Turns abgeschlossen, fuer aktive Loops noch nicht vollstaendig
4. als erster Contract-Slice abgeschlossen
5. als erster Bridge-Slice im Stream-Pfad umgesetzt
6. als erster Routing-Slice in Sync und Stream umgesetzt
7. als erster Slice begonnen: Meta-Turns koennen den aktiven Loop jetzt als
   Kontext offenhalten, ohne sofort wieder den separaten Loop-Runner zu
   triggern; normale Kontextturns werden zudem in den aktiven Snapshot
   zurueckgeschrieben
8. als erster Slice umgesetzt: produktiver 8s-Step-Budget-Stop im Loop
   entfernt, technischer Langtimeout statt hartem Budgetabbruch
9. nur teilweise umgesetzt und aktuell noch fehleranfaellig
10. als erster Slice umgesetzt: keine Rueckwaertsmutation des Tool-Step-Typs
    mehr; weitere fachliche Trennung je Capability noch offen
11. teilweise umgesetzt
12. noch nicht der Fokus

---

## Offene Designfragen

1. Soll `turn_mode` ein neues oberes Contract-Feld werden oder unter
   `_control_decision` / autoritativen Zusatzfeldern leben?
2. Soll `interactive_defer` wirklich eigener Turn-Modus sein oder nur ein
   Control-Reason innerhalb von `single_turn`?
3. Sollen MCP-/Container-/Cronjob-Schritte als eigene `step_type`-Werte
   modelliert werden oder als Unterfall von `tool_execution_step`?
4. Wie viel des bestehenden `core/autonomous/loop_engine.py` soll spaeter als
   interne Step-Ausfuehrung unter `task_loop` wiederverwendet werden?
5. Wie stark sollen explizite User-Marker `Task-Loop:` den Thinking-Kandidaten
   boosten, ohne wieder eine zweite implizite Routing-Wahrheit zu schaffen?
6. Soll ein Tool-Pfad sichtbar als zwei Schritte (`tool_request_step` ->
   `tool_execution_step`) modelliert werden oder als ein runtimegebundener
   Tool-Schritt mit internem Statuswechsel?
7. Wie soll der normale Turn Meta-Fragen wie `was ist passiert?` in einem
   aktiven Loop behandeln, ohne sie vorschnell als Step-Resume zu deuten?

---

## Kurzfazit

Ja, es ist sinnvoll:

1. den Loop in Thinking als bekannten Kandidaten einzufuehren
2. `task_loop` in Control als bekannte autoritative Turn-Option einzufuehren
3. den sichtbaren Loop als Obermodus fuer komplexe Arbeit zu definieren
4. Tool-, MCP-, Container- und Cronjob-Schritte als Schrittarten innerhalb
   dieses sichtbaren Loops zu fuehren
5. den Loop als sichtbaren Zustand des normalen Chatturns zu behandeln statt
   als separaten inneren Kanal
6. Budget im Loop nicht als produktiven Stop-Gate zu verwenden

Nicht sinnvoll waere:

- den Loop wieder ausserhalb von Control final zu triggern
- rohe Komplexitaet oder `Sequential` direkt zur letzten Wahrheit zu machen
- bei Toolbedarf wieder in einen separaten konkurrierenden Obermodus zu
  zerfallen
- den Loop als eigene Mini-Chatwelt mit eigener Resume-Semantik zu bauen
- aktive Arbeit im Loop nur wegen Zeitbudget abzubrechen

Der saubere Zielzustand ist:

- Thinking kennt den Loop
- Control entscheidet den Loop
- der normale Turn arbeitet im Modus `task_loop`
- der Loop bleibt sichtbar
- Orchestrator fuehrt Schritte aus
