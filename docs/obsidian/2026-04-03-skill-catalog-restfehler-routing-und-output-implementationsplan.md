# Skill-Catalog Restfehler Routing und Output - Implementationsplan

Erstellt am: 2026-04-03
Zuletzt aktualisiert: 2026-04-05
Status: **In Umsetzung**
Bezieht sich auf:

- [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]] - neuer Zielplan: frueher bindender Contract fuer Skill-Catalog
- [[2026-04-04-skill-catalog-offene-punkte-masterliste]] - zentraler Sammelpunkt fuer offene Punkte im Skill-Catalog-Strang
- [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]] - Live-E2E-Befund nach Block 6
- [[2026-04-02-skills-semantik-md-leitplanken-implementationsplan]] - semantische Skill-Leitplanken
- [[2026-04-02-thinking-strategy-authority-and-frontend-visibility-implementationsplan]] - Trace- und Authority-Pfad
- [[2026-03-31-control-layer-audit]] - Control als bindende Policy-Autoritaet
- [[2026-04-04-skill-catalog-draft-evidence-output-repair-gap]] - neuer Befund nach Block A bis D

---

## Update 2026-04-05 - Routing-/Contract-Teil im Live-Recheck bestanden, letzter Output-Rest bleibt

Der zuletzt gepruefte gemischte Skill-Catalog-Prompt zeigt fuer diesen Plan
inzwischen klar:

- Routing-/Contract-Seite ist fuer den geprueften Fall sauber
  - `resolution_strategy = skill_catalog_context`
  - kanonische `strategy_hints`
  - `suggested_tools = ["list_skills"]`
  - `final_execution_tools = ["list_skills"]`
  - `skill_catalog_required_tools = ["list_skills"]`
- der frueher offene Follow-up-Drift ist fuer diesen Prompt ebenfalls enger
  gezogen:
  - der sichtbare Anschlussblock nutzt jetzt `Wunsch-Skills`
  - kein implizites `list_draft_skills` mehr im Live-Trace

Damit verschiebt sich der Restbefund jetzt nochmals enger:

- nicht mehr primaer Routing
- nicht mehr primaer Contract-Breite
- sondern letzter Rohoutput-Drift mit
  `skill_catalog_postcheck = repaired:unverified_session_system_skills`

Einordnung:

- der semantische Postcheck repariert den Fall bereits korrekt auf eine
  konservative und sichtbare saubere Antwort
- offen bleibt damit nur noch, die Rohantwort selbst so eng zu fuehren, dass
  unbelegte Session-/System-Skills fuer diesen Prompt gar nicht mehr kurz
  auftauchen

Neu verifiziert:

- `pytest -q tests/unit/test_orchestrator_plan_schema_utils.py` -> `8 passed`
- `pytest -q tests/unit/test_output_tool_injection.py` -> `9 passed`
- `pytest -q tests/unit/test_output_grounding.py` -> `41 passed`
- `pytest -q tests/unit/test_skill_catalog_prompt_flow.py tests/unit/test_skill_catalog_semantic_gap_suite.py` -> `9 passed`

## Umsetzungsstand 2026-04-04

Architektur-Update:

- Die zuletzt verifizierten Live-Faelle zeigen, dass der vorgelagerte Pfad
  `skill_catalog_context` bereits sauber erkennt und mit passenden
  Read-only-Tools stabilisiert.
- Der neue Hauptschnitt ist deshalb nicht mehr primaer weiterer Prompt- oder
  Repair-Ausbau, sondern ein frueher bindender Policy-Contract:
  [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]]

Block A und Block B sind jetzt umgesetzt.

Konkrete Aenderungen:

- Der Orchestrator trennt jetzt explizit zwischen kanonischen
  Read-only-Skill-Tools und Skill-Aktions-Tools:
  [core/orchestrator.py](<repo-root>/core/orchestrator.py)
- Der kanonische Read-only-Satz umfasst jetzt:
  - `list_skills`
  - `list_draft_skills`
  - `get_skill_info`
- Fuer `skill_catalog_context` gilt im SKILL-Domain-Pfad jetzt eine
  explizite Prioritaetsregel:
  Read-only-Inventarfragen werden nicht mehr spaeter auf
  `autonomous_skill_task` umgebogen.
- Die Domain-Route seedet fuer Skill-Katalogfragen jetzt gezielt ein
  Read-only-Tool statt pauschal `autonomous_skill_task`:
  - Draft-Inventar -> `list_draft_skills`
  - sonstiges Runtime-Inventar -> `list_skills`
- Auch der spaetere Domain-Tool-Filter behandelt
  `skill_catalog_context` jetzt als Read-only-Pfad und filtert
  Aktions-Tools in diesem Fall heraus:
  [core/orchestrator.py](<repo-root>/core/orchestrator.py)
- Die Keyword-/Marker-Erkennung fuer Draft-Inventar wurde nachgeschaerft,
  damit auch `Draft-Skills` mit Bindestrich robust als Inventarfrage
  erkannt wird:
  [core/orchestrator.py](<repo-root>/core/orchestrator.py)
- Die Regressionen fuer den neuen Routing-/Policy-Pfad sind in den
  Domain-Routing-Tests festgehalten:
  [test_orchestrator_domain_routing_policy.py](<repo-root>/tests/unit/test_orchestrator_domain_routing_policy.py)

Verifiziert:

- `pytest -q tests/unit/test_orchestrator_domain_routing_policy.py`
- `pytest -q tests/unit/test_control_contract_flow.py tests/unit/test_skill_catalog_prompt_flow.py`
- `pytest -q tests/unit/test_orchestrator_runtime_safeguards.py -k "skill_catalog_context or resolve_execution_suggested_tools"`

Wichtig:

- Der konkrete Live-Fail
  `Welche Draft-Skills gibt es gerade?` -> Skill-Erstellungsflow
  ist damit auf Code-/Test-Ebene adressiert.
- Der anschliessende Live-Gegencheck zeigt aber einen neuen engeren Restfehler:
  `list_draft_skills` wird zwar korrekt ausgefuehrt, der Draft-Befund geht aber
  im spaeteren Output-Repair wieder verloren.
  Das ist separat dokumentiert:
  [[2026-04-04-skill-catalog-draft-evidence-output-repair-gap]]
- Der nachgezogene Fix dafuer ist fuer den aktuellen Null-Draft-Fall jetzt
  vorlaeufig erfolgreich:
  die Endantwort behaelt den Draft-Befund und erklaert korrekt, warum
  `list_skills` ihn nicht anzeigt.
  Nach dem folgenden Prompt-/Hint-/Precontrol-Schnitt lief der zuletzt
  gepruefte Draft-Prompt zudem mit `Postcheck: passed`.
- Die Restfehlerlage verschiebt sich damit von
  Routing/Read-only-Trennung auf:
  - fruehes Einfrieren des bereits guten Skill-Catalog-Befunds als Contract
  - Positivfall mit echten Draft-Skills
  - breite Gegenpruefung weiterer Follow-up-Varianten
- Der naechste offene Arbeitsschritt liegt damit bei
  [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]]
  und danach bei
  [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]]
  auf Positivfall mit echten Drafts plus breiterer Follow-up-Gegenpruefung.

Neuer Befund nach dem spaeteren Control-first-Contract-Schnitt:

- der fruehe Pfad fuer `skill_catalog_context` ist jetzt sichtbar deutlich
  sauberer:
  - Policy-Contract im Trace
  - `Sequential=false`
  - `Postcheck: passed` in den geprueften Kernfaellen
- die aktuelle Restfehlerlage liegt damit enger nicht mehr im Routing,
  sondern in spaeterer Output-Semantik und zu permissiven
  Postcheck-Kriterien

Seit dem gezielten Output-Fix geschlossen:

- `tools_vs_skills`-Antworten mit capability-styligen Built-in-/
  Kernfaehigkeiten-Beschreibungen werden jetzt semantisch abgefangen und im
  Postcheck repariert
- `inventory_read_only`-Antworten mit ungefragten Skill-Erstellungsangeboten
  werden jetzt semantisch abgefangen und im Postcheck repariert
- Draft-Aussagen ohne echte `list_draft_skills`-Evidence werden jetzt
  semantisch abgefangen; der Safe-Fallback markiert den Draft-Status dann
  explizit als nicht verifiziert statt ihn aus Registry-Signalen abzuleiten
- die Follow-up-Policy fordert im Runtime-plus-Wishlist-Fall nicht mehr zu
  breit `list_draft_skills`

Referenz:

- [tests/unit/test_skill_catalog_semantic_gap_suite.py](<repo-root>/tests/unit/test_skill_catalog_semantic_gap_suite.py)
- `pytest -q tests/unit/test_skill_catalog_semantic_gap_suite.py` -> `6 passed`

---

## Anlass

Der Live-E2E-Gegencheck nach Block 6 zeigt, dass der Skill-Catalog-Pfad zwar
inhaltlich deutlich stabiler geworden ist, aber noch zwei harte Restfehler
enthaelt:

- reine Skill-Inventarfragen koennen weiter in sichtbare Reparaturantworten
  kippen
- mindestens ein Inventarfall (`Welche Draft-Skills gibt es gerade?`) kippt
  sogar in einen Skill-Erstellungsflow

Der Kern ist dabei **keine zweite Inventar-Truth-Source**, sondern eine
versteckte zweite **Routing-/Policy-Wahrheit** fuer die Bedeutung von `skill`:

- die semantische Schiene behandelt den Prompt als Katalog-/Inventarfrage
- die Domain-/Tool-Schiene behandelt denselben Prompt teils als Skill-Aktion

Damit ueberstimmt spaeterer Tool-/Domain-Code die korrekte fruehe Deutung.

---

## Kurzbefund

### 1. Kein zweites Inventar, aber zwei konkurrierende Deutungen

Die Runtime-Wahrheit fuer Skill-Inventare bleibt korrekt bei:

- [core/orchestrator.py](<repo-root>/core/orchestrator.py)
- [core/layers/output.py](<repo-root>/core/layers/output.py)
- [intelligence_modules/skill_addons](<repo-root>/intelligence_modules/skill_addons)

Der Konflikt liegt stattdessen hier:

- semantische Inferenz fuer `skill_catalog_context` in
  [core/orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
- Domain-Routing und Tool-Gating in
  [core/domain_router_hybrid.py](<repo-root>/core/domain_router_hybrid.py)
  und [core/orchestrator.py](<repo-root>/core/orchestrator.py)

Das ist faktisch eine zweite Policy-Autoritaet fuer dieselbe User-Frage.

### 2. Read-only-Inventory und Skill-Aktion sind nicht sauber getrennt

Control kennt `list_draft_skills` bereits als sichere Read-only-Aktion:

- [core/layers/control.py](<repo-root>/core/layers/control.py)

Die SKILL-Domain im Orchestrator behandelt aber `SKILL` aktuell primär als
Aktionsdomain und erlaubt dort nur einen engeren Tool-Satz:

- [core/orchestrator.py](<repo-root>/core/orchestrator.py)

Wenn nach dem Domain-Filter kein erlaubtes Tool uebrig bleibt, wird fuer
`SKILL` erneut `autonomous_skill_task` gesaet.

### 3. Der Output-Contract wird live noch nicht nativ stabil eingehalten

Die Antwortregeln fuer `skill_catalog_context` sind vorhanden:

- [core/layers/output.py](<repo-root>/core/layers/output.py)

Live sieht man aber mehrfach `Postcheck: repaired:missing_runtime_section`.
Damit ist klar:

- die Regeln greifen als Sicherheitsnetz
- das Modell haelt sie im Stream-Pfad noch nicht robust ohne Reparatur ein

### 4. Der sichtbare Reparaturblock ist aktuelles Stream-Verhalten

Der sichtbare Block `[Grounding-Korrektur]` ist keine zufaellige Leckage,
sondern direkte Folge des aktuellen Streaming-Modus:

- Default `tail_repair` in [config.py](<repo-root>/config.py)
- Anhaengen der Korrektur im Stream in
  [core/layers/output.py](<repo-root>/core/layers/output.py)

Damit ist das System derzeit zugleich:

- fuer Debug gut beobachtbar
- fuer echten User-Betrieb noch zu roh

### 5. Trace und echte Execution koennen auseinanderlaufen

Die Thinking-Box zeigt vor allem den Plan-/Thinking-Zustand:

- [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)

Die finale Tool-Auswahl wird aber spaeter noch einmal in
`_resolve_execution_suggested_tools(...)` entschieden:

- [core/orchestrator.py](<repo-root>/core/orchestrator.py)

Dadurch kann live `Tools: list_draft_skills` sichtbar sein, waehrend die
tatsaechliche Execution in `autonomous_skill_task` kippt.

---

## Zielbild

Bei Skill-Inventarfragen soll es nur noch **eine** bindende Deutung geben:

1. `skill_catalog_context` ist fuer Inventar-/Taxonomiefragen die autoritative
   Query-Klasse
2. Read-only-Skill-Tools duerfen durch Domain-Gates nicht in Skill-Erstellung
   umgebogen werden
3. sichtbare Antworten duerfen keinen Reparatur-Anhang leaken
4. Trace und reale Tool-Auswahl muessen fuer Debug und UI konsistent sein

Nicht mehr zulaessig:

- `Welche Draft-Skills gibt es gerade?` -> Skill-Erstellung
- sichtbarer `[Grounding-Korrektur]`-Block bei normalen Skill-Antworten
- Thinking zeigt Read-only-Tool, Execution laeuft aber auf Aktions-Tool

---

## Implementationsbloecke

### Block A - Eine bindende Policy fuer Skill-Inventarfragen

Status:

- umgesetzt am 2026-04-04

Ziel:

- `skill_catalog_context` muss fuer Inventarfragen spaeter nicht mehr von einer
  zweiten SKILL-Domain-Policy ueberschrieben werden.

Arbeitspunkte:

- explizit definieren, welche Klasse von Prompts als
  `skill_catalog_context`-Inventarfragen gilt
- klare Prioritaetsregel zwischen
  `resolution_strategy=skill_catalog_context` und `domain_tag=SKILL`
  einfuehren
- verhindern, dass eine spaetere Domain-Reseed-Logik
  `autonomous_skill_task` injiziert, wenn bereits eine Read-only-Skill-Frage
  erkannt wurde

Relevante Stellen:

- [core/orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
- [core/domain_router_hybrid.py](<repo-root>/core/domain_router_hybrid.py)
- [core/orchestrator.py](<repo-root>/core/orchestrator.py)
- [core/orchestrator_pipeline_stages.py](<repo-root>/core/orchestrator_pipeline_stages.py)

### Block B - Read-only-Skill-Tools und Aktions-Tools sauber trennen

Status:

- umgesetzt am 2026-04-04

Ziel:

- Read-only-Skill-Inventarfragen duerfen nur auf Read-only-Werkzeuge laufen.

Arbeitspunkte:

- gemeinsamen kanonischen Satz an Read-only-Skill-Tools definieren:
  - `list_skills`
  - `list_draft_skills`
  - `get_skill_info`
- diesen Satz zwischen Control und Orchestrator angleichen
- Domain-Gates duerfen Read-only-Skill-Tools nicht mehr wegfiltern
- Reseed fuer `SKILL` nur dann, wenn wirklich ein Aktionsintent vorliegt

Relevante Stellen:

- [core/layers/control.py](<repo-root>/core/layers/control.py)
- [core/orchestrator.py](<repo-root>/core/orchestrator.py)

### Block C - Sichtbaren Reparatur-Leak aus dem User-Output entfernen

Ziel:

- Reparatur darf intern/tracebar bleiben, aber nicht als
  `[Grounding-Korrektur]` in normalen Skill-Antworten erscheinen.

Arbeitspunkte:

- entscheiden, ob `skill_catalog_context` im Stream auf
  `buffered` oder auf unsichtbare Tail-Replacement-Semantik umgestellt wird
- Postcheck-/Repair-Status weiter im Trace halten
- sichtbaren Korrektur-Anhang im User-Text fuer diesen Pfad abschalten

Relevante Stellen:

- [config.py](<repo-root>/config.py)
- [core/layers/output.py](<repo-root>/core/layers/output.py)
- [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)

### Block D - Trace und tatsaechliche Tool-Execution zusammenfuehren

Ziel:

- Thinking-Box und Live-Trace sollen nicht nur Plan-Tools, sondern auch die
  finale Execution-Realitaet transparent zeigen.

Arbeitspunkte:

- klar unterscheiden zwischen:
  - `thinking_suggested_tools`
  - `final_execution_tools`
- finalen Toolsatz nach `_resolve_execution_suggested_tools(...)` ebenfalls in
  die Trace-Daten aufnehmen
- fuer `skill_catalog_context` sichtbar machen, wenn ein Tool-Reroute oder
  Reseed passiert ist

Relevante Stellen:

- [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)
- [core/orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)
- [core/orchestrator.py](<repo-root>/core/orchestrator.py)
- [adapters/Jarvis/static/js/chat-thinking.js](<repo-root>/adapters/Jarvis/static/js/chat-thinking.js)

### Block E - Follow-up-Split fuer Wunsch-Skills zu Ende haerten

Ziel:

- gemischte Prompts aus Inventar und Wunsch-Skills sollen nicht nur
  reparierbar, sondern nativ stabil beantwortbar werden.

Arbeitspunkte:

- Output-Contract fuer `fact_then_followup` weiter auf Rohantwort-Ebene
  haerten
- Postcheck so belassen, dass er als Sicherheitsnetz dient, aber nicht die
  primaere Normalform bleibt
- Live-Faelle explizit auf faktischen Block plus markierten Anschlussblock
  testen

Relevante Stellen:

- [core/orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
- [core/layers/output.py](<repo-root>/core/layers/output.py)

---

## Testplan

### Unit / Contract

- Query-Inferenz:
  reine Inventarfrage, Draft-Frage, gemischte Inventar-/Wunsch-Frage,
  explizite Skill-Erstellung
- Domain-/Tool-Policy:
  `skill_catalog_context` darf bei Read-only-Prompts nicht auf
  `autonomous_skill_task` reseeden
- Stream-/Output-Pfad:
  Reparaturstatus im Trace sichtbar, aber kein sichtbarer
  `[Grounding-Korrektur]`-Block in der User-Antwort
- Trace:
  Thinking-Tools und finale Execution-Tools sind getrennt sichtbar

Naheliegende Testdateien:

- [test_orchestrator_plan_schema_utils.py](<repo-root>/tests/unit/test_orchestrator_plan_schema_utils.py)
- [test_control_contract_flow.py](<repo-root>/tests/unit/test_control_contract_flow.py)
- [test_skill_catalog_prompt_flow.py](<repo-root>/tests/unit/test_skill_catalog_prompt_flow.py)
- [test_output_grounding.py](<repo-root>/tests/unit/test_output_grounding.py)
- [test_frontend_stream_activity_contract.py](<repo-root>/tests/unit/test_frontend_stream_activity_contract.py)

### Live / UI

Pflichtprompts:

- `Welche Skills hast du?`
- `Welche Skills stehen dir aktuell zur Verfuegung?`
- `Welche Draft-Skills gibt es gerade?`
- `Was ist der Unterschied zwischen Tools und Skills?`
- `Welche Skills hast du und welche wuerdest du dir als Naechstes wuenschen?`

Erwartung:

- keine Skill-Erstellung bei Read-only-Inventarfragen
- keine sichtbare `[Grounding-Korrektur]`
- `Runtime-Skills` bleibt Antwortanfang
- gemischte Fragen bleiben sauber in Faktblock und Anschlussblock getrennt
- Trace zeigt finale Tool-Execution nachvollziehbar

---

## Priorisierung

1. Block A und Block B zuerst
   sonst bleibt die Gefahr bestehen, dass Inventarfragen in Skill-Erstellung
   kippen
2. Danach Block C
   damit der Pfad im echten UI-Test user-tauglich wird
3. Danach Block D
   damit verbleibende Abweichungen sauber debugbar sind
4. Block E als letzte Nachhaertung
   sobald Routing und sichtbarer Output stabil sind

---

## Abnahmekriterien

- `Welche Draft-Skills gibt es gerade?` fuehrt deterministisch zu einer
  Read-only-Antwort und nie zu `pending_skill_creation`
- `skill_catalog_context` wird bei Inventarfragen spaeter nicht mehr von einer
  zweiten Domain-/Tool-Policy ueberschrieben
- der Postcheck kann weiter `repaired:*` im Trace markieren, ohne dass ein
  sichtbarer Korrekturblock an den User geleakt wird
- Thinking-/Trace-Ansicht und finale Tool-Execution widersprechen sich nicht
  mehr still

---

## Einordnung

Der jetzt gefundene Restfehler ist wichtig, weil er die frueher abgesicherte
Leitentscheidung **nicht** bricht:

- es gibt weiterhin keine zweite Daten-Truth-Source fuer Skill-Inventare

Aber:

- es gibt aktuell eine zweite verdeckte **Policy-/Routing-Wahrheit** fuer
  Skill-Fragen

Genau diese muss vereinheitlicht werden, bevor der Skill-Catalog-Pfad als
live-signoff-faehig gelten kann.
