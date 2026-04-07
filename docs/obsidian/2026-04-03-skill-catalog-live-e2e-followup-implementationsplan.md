# Skill-Catalog Live-E2E Drift Follow-up - Implementationsplan

Erstellt am: 2026-04-03
Zuletzt aktualisiert: 2026-04-05
Status: **In Umsetzung**
Bezieht sich auf:

- [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]] - neuer Zielplan: frueher bindender Skill-Catalog-Contract
- [[2026-04-04-skill-catalog-offene-punkte-masterliste]] - zentraler Sammelpunkt fuer offene Punkte im Skill-Catalog-Strang
- [[2026-04-02-skills-semantik-md-leitplanken-implementationsplan]] - semantische Skill-Leitplanken
- [[2026-04-02-thinking-strategy-authority-and-frontend-visibility-implementationsplan]] - Strategy-Authority und Trace
- [[2026-03-31-control-layer-audit]] - Control als bindende Policy-Autoritaet
- [[2026-04-03-skill-catalog-restfehler-routing-und-output-implementationsplan]] - Restfehleranalyse fuer Routing, Output und Trace
- [[2026-04-04-skill-catalog-draft-evidence-output-repair-gap]] - neuer Befund: Draft-Evidence geht im Repair verloren

---

## Nachtrag 2026-04-05 - Live-Recheck nach Hint-Kanonisierung und Output-Nachschaerfung

Der erneute Live-Gegencheck fuer den gemischten Inventar-/Wunsch-Prompt

- `Welche Skills hast du aktuell und welche Skills wuerdest du dir als Naechstes wuenschen? Trenne bitte sauber zwischen Runtime-Skills, Built-in Tools und anderen Ebenen und erklaere kurz, warum list_skills nicht alles zeigt.`

zeigt jetzt:

- `resolution_strategy = skill_catalog_context`
- `strategy_hints` nur noch kanonisch:
  - `skill_taxonomy`
  - `answering_rules`
  - `runtime_skills`
  - `tools_vs_skills`
  - `overview`
  - `fact_then_followup`
- `suggested_tools = ["list_skills"]`
- `final_execution_tools = ["list_skills"]`
- `skill_catalog_required_tools = ["list_skills"]`
- `skill_catalog_force_sections = ["Runtime-Skills", "Einordnung", "Wunsch-Skills"]`

Sichtbarer Endtext:

- `Runtime-Skills`
- `Einordnung`
- `Wunsch-Skills`

Der zuvor offene Follow-up-/Heading-Drift ist damit fuer diesen Prompt nicht
mehr sichtbar.

Offener Live-Rest:

- `skill_catalog_postcheck = repaired:unverified_session_system_skills`

Einordnung:

- User-facing ist die Antwort jetzt sauber
- Routing, Contract und Tool-Auswahl sind fuer diesen Prompt sauber
- der Rohoutput driftet intern aber noch kurz in unbelegte Session-/System-
  Skills, bevor der Postcheck auf die sichere Fassung zieht

Der naechste Live-/Code-Schritt ist damit nur noch:

- diesen letzten Rohoutput-Drift fuer gemischte Inventar-/Wunsch-Prompts
  nativ zu vermeiden

## Nachtrag 2026-04-04

Der aus
[[2026-04-03-skill-catalog-restfehler-routing-und-output-implementationsplan]]
abgeleitete Folge-Schnitt fuer Routing und Read-only-Tooltrennung
(Block A + B) ist jetzt umgesetzt.

Konkreter Stand:

- Der SKILL-Domain-Pfad trennt jetzt explizit zwischen Read-only-Skill-Tools
  und Skill-Aktions-Tools:
  [core/orchestrator.py](<repo-root>/core/orchestrator.py)
- Fuer `skill_catalog_context` haben Read-only-Inventarfragen jetzt
  bindende Prioritaet gegenueber spaeterem SKILL-Reseed.
- `Welche Draft-Skills gibt es gerade?` wird im Routing jetzt auf
  `list_draft_skills` gebunden statt auf `autonomous_skill_task`.
- Auch die Marker-/Keyword-Erkennung deckt jetzt den Hyphen-Fall
  `Draft-Skills` stabil ab.
- Die dazugehoerigen Regressionen sind in
  [test_orchestrator_domain_routing_policy.py](<repo-root>/tests/unit/test_orchestrator_domain_routing_policy.py)
  festgehalten.

Verifiziert:

- `pytest -q tests/unit/test_orchestrator_domain_routing_policy.py`
- `pytest -q tests/unit/test_control_contract_flow.py tests/unit/test_skill_catalog_prompt_flow.py`
- `pytest -q tests/unit/test_orchestrator_runtime_safeguards.py -k "skill_catalog_context or resolve_execution_suggested_tools"`

Einordnung:

- Der historische Live-Befund vom 2026-04-03 unten bleibt als Befund stehen.
- Der darin dokumentierte `draft_skills`-Fehler ist inzwischen auf
  Code-/Test-Ebene adressiert.
- Als naechster offener Schritt bleibt jetzt primaer der sichtbare
  Output-Leak `[Grounding-Korrektur]`, danach Trace-/Execution-Konsistenz.

## Nachtrag 2026-04-04 - zweiter Live-Befund nach Block C und D

Der erneute WebUI-Gegencheck zeigt:

- sichtbarer `[Grounding-Korrektur]`-Leak ist weg
- `Tools` und `Exec Tools` sind konsistent sichtbar
- Draft-Inventarfragen kippen nicht mehr in Skill-Erstellung

Aber:

- die finale Antwort verliert den Draft-Befund weiterhin, sobald der
  Skill-Catalog-Postcheck reparierend eingreift
- `Postcheck: repaired:missing_runtime_section` bleibt sichtbar
- die Ersatzantwort schrumpft auf Runtime-Nullbefund plus generische Einordnung

Damit ist der naechste harte Restfehler jetzt:

- nicht mehr primär Routing
- sondern Draft-Evidence-Luecke zwischen `list_draft_skills`-Execution und
  Skill-Catalog-Repair

Separat dokumentiert:

- [[2026-04-04-skill-catalog-draft-evidence-output-repair-gap]]

## Nachtrag 2026-04-04 - dritter Live-Befund nach Draft-Evidence-Fix

Der erneute WebUI-Gegencheck mit

- `Welche Draft-Skills gibt es gerade? Nenne die Draft-Skills explizit. Erklaere danach kurz, warum list_skills sie nicht anzeigt.`

zeigt jetzt:

- Routing bleibt korrekt auf `skill_catalog_context`
- `Tools` und `Exec Tools` bleiben konsistent bei
  `list_draft_skills`, `list_skills`
- die Endantwort enthaelt jetzt den korrekten Null-Draft-Befund:
  - keine installierten Runtime-Skills
  - aktuell keine Draft-Skills verifiziert
  - `list_skills` zeigt nur installierte Runtime-Skills

Wichtig:

- Im aktuellen lokalen Setup gibt es unter
  [shared_skills](<repo-root>/shared_skills)
  kein `_drafts`-Verzeichnis.
  Der Null-Draft-Befund ist damit fuer diese Instanz plausibel.
- Der zuvor dokumentierte Draft-Evidence-Fehler ist damit fuer den
  aktuellen Null-Draft-Fall vorlaeufig behoben:
  [[2026-04-04-skill-catalog-draft-evidence-output-repair-gap]]
- Offen bleibt aber weiterhin:
  - `Postcheck: repaired:missing_runtime_section`
  - Thinking-/Sequential-Trace driftet noch in hypothetische Erklaerungen
    statt eng am Runtime-Befund zu bleiben

Folgerung:

- Der naechste Arbeitsschritt ist jetzt nicht mehr primaer Draft-Evidence,
  sondern native Stabilisierung des Skill-Catalog-Rohoutputs plus spaeterer
  Positivfall-Test mit echten Drafts.

## Nachtrag 2026-04-04 - vierter Live-Befund nach Prompt-/Hint-/Precontrol-Nachschaerfung

Nach Restart des gemounteten Backend-Containers `jarvis-admin-api` und erneutem
Live-Gegencheck zeigt der Pfad jetzt zwei deutliche Verbesserungen:

### A. Inventar plus Wunsch-Follow-up

Prompt:

- `Welche Skills hast du aktuell und welche Skills wuerdest du dir als Naechstes wuenschen?`

Befund:

- `Hints` enthalten jetzt sichtbar auch `fact_then_followup`
- `needs_sequential_thinking=false`
- `Exec Tools: list_skills`
- `Postcheck: passed`
- die Endantwort bleibt sauber getrennt in:
  - `Runtime-Skills`
  - `Einordnung`
  - `Wunsch-Skills`

### B. Draft-Inventar

Prompt:

- `Welche Draft-Skills gibt es gerade? Nenne die Draft-Skills explizit. Erklaere danach kurz, warum list_skills sie nicht anzeigt.`

Befund:

- `Exec Tools` bleiben korrekt bei `list_draft_skills`, `list_skills`
- `Postcheck: passed`
- die Endantwort bleibt im strukturierten Skill-Catalog-Format und enthaelt
  keine hypothetischen Draft-Beispiele mehr

Wichtig:

- Nach Frontend-Hard-Reload zeigt die sichtbare `Live Trace`-Box fuer den
  Draft-Pfad jetzt ebenfalls den finalen `trace_final`-Snapshot konsistent mit
  `needs_sequential_thinking=false`.
- Fuer den Wunsch-/Follow-up-Fall ist die fruehere Rohoutput-/Repair-
  Dominanz im geprueften Live-Prompt damit vorlaeufig nicht mehr reproduziert.

Verifiziert seit dem letzten Doku-Stand zusaetzlich:

- `pytest -q tests/unit/test_output_tool_injection.py`
- `pytest -q tests/unit/test_skill_catalog_prompt_flow.py`
- `pytest -q tests/unit/test_output_grounding.py -k "skill_catalog"`
- `pytest -q tests/unit/test_orchestrator_plan_schema_utils.py`
- `pytest -q tests/unit/test_orchestrator_query_budget_policy.py -k "skill_catalog_inventory_fast_path or keeps_sequential_for_recall_signal or container_runtime_fast_path"`

Folgerung:

- Native Rohoutput-Stabilitaet ist fuer die zuletzt geprueften zwei Live-Faelle
  deutlich verbessert.
- Der eigentliche naechste Architekturpunkt liegt jetzt aber frueher:
  der bereits gute Skill-Catalog-Befund muss als bindender Contract durch die
  Pipeline getragen werden.
- Referenz dafuer ist ab jetzt:
  [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]]
- Danach bleibt der Positivfall mit echten Drafts der naechste Live-Haertetest.

## Nachtrag 2026-04-04 - Architekturentscheid nach verifizierten Rechecks

Die zuletzt geprueften Live-Traces zeigen fuer den Skill-Catalog-Pfad bereits:

- `Intent`: passend zur Skill-Frage
- `Strategy`: `skill_catalog_context`
- `Hints`: `draft_skills`, `tools_vs_skills`, `runtime_skills`,
  `skill_taxonomy`, `answering_rules`
- `Suggested / final tools`: `list_draft_skills`, `list_skills`
- `Sequential`: aus
- `Postcheck`: `passed`

Einordnung:

- Thinking, Precontrol und Control erkennen den geprueften Fall damit bereits
  fast so, wie man ihn haben will.
- Der Hauptrestfehler ist daher nicht mehr primaer spaete Prompt-Haertung,
  sondern fehlende fruehe Bindung dieses Ergebnisses als Downstream-Contract.
- Das ist jetzt im neuen Zielplan zusammengezogen:
  [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]]

Konsequenz fuer die naechste Umsetzung:

- kein zweiter Thinking-Durchlauf
- keine neue semantische Truth-Source
- stattdessen:
  - Control/Orchestrator materialisieren einen verbindlichen
    Skill-Catalog-Policy-Block
  - ein deterministischer Resolver laedt danach die passenden `skill_addons`
  - Output rendert innerhalb dieses Contracts

## Nachtrag 2026-04-04 - mehrdeutige Skill-Prompts nach Contract-Schnitt

Weitere Live-Prompts zeigen jetzt ein scharfes Restbild:

Prompt A:

- `Welche Skills kannst du benutzen? Ich meine auch sowas wie Tools oder eingebaute Sachen.`

Prompt B:

- `Kannst du mal mit Skills arbeiten und schauen, was da geht?`

Befund:

- der fruehe Pfad bleibt jeweils sauber bei:
  - `skill_catalog_context`
  - passenden `tools_vs_skills`-/`overview`-/`capabilities`-Hints
  - `list_skills`
  - `Sequential=false`
  - sichtbarem Policy-Contract
- die Endantwort driftet aber spaeter wieder in freie
  Built-in-/Core-Capabilities und teils sogar in ungefragte
  Skill-Erstellungsangebote
- `Postcheck` steht dabei aktuell trotzdem noch auf `passed`

Update 2026-04-05:

- der Built-in-/Core-Capability-Drift fuer den `tools_vs_skills`-Teil ist
  inzwischen im Output-Leakage-Check + Postcheck geschlossen
- die ungefragten Skill-Erstellungs-/Aktionsangebote im
  `inventory_read_only`-Pfad sind inzwischen ebenfalls geschlossen
- die Draft-Evidence-Luecke ist inzwischen ebenfalls geschlossen:
  Draft-Befunde gelten nur noch mit echter `list_draft_skills`-Evidence als
  verifiziert
- der zu breite Follow-up-Contract ist inzwischen ebenfalls geschlossen:
  Runtime-plus-Wishlist-Faelle bleiben ohne explizite Draft-Frage bei
  `list_skills`

Einordnung:

- der fruehe Policy-/Control-Pfad ist fuer diese Faelle inzwischen der
  stabilste Teil
- die verbleibende Luecke sitzt enger in Output-Semantik und
  Postcheck-Kriterien, nicht mehr primaer im Routing

Verifiziert ueber die nachgezogene Gap-Suite:

- [tests/unit/test_skill_catalog_semantic_gap_suite.py](<repo-root>/tests/unit/test_skill_catalog_semantic_gap_suite.py)
- `pytest -q tests/unit/test_skill_catalog_semantic_gap_suite.py`
- aktueller Stand: `6 passed`

---

## Umsetzungsstand 2026-04-03

Block 1, Block 2, Block 3, Block 4, Block 5 und Block 6 sind jetzt umgesetzt.

Konkrete Aenderungen:

- Der beobachtete Live-Fall ist jetzt als Regression im Testpfad festgehalten:
  [test_skill_catalog_prompt_flow.py](<repo-root>/tests/unit/test_skill_catalog_prompt_flow.py)
- Der Prompt-Flow-Test deckt jetzt auch den generischen Inventarfall
  `Dir stehen SKILLS zu verfuegung ... Was fuer skills haettest du gerne?`
  als `skill_catalog_context`-Pfad ab.
- Die Hint-Inferenz fuer generische Skill-Inventarfragen wurde in
  [core/orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
  geschaerft.
- Zusaetzlich abgesichert ist das ueber
  [test_orchestrator_plan_schema_utils.py](<repo-root>/tests/unit/test_orchestrator_plan_schema_utils.py)
- Generische Skill-Inventarfragen ziehen jetzt robuster semantische Hints wie:
  - `runtime_skills`
  - `tools_vs_skills`
  - `overview`
  - `answering_rules`
- Die Output-Schicht erzwingt fuer `skill_catalog_context` jetzt einen
  deutlich haerteren Antwortmodus mit markierten Abschnitten:
  - `Runtime-Skills`
  - `Einordnung`
  - optional `Naechster Schritt`
- Der erste Satz muss den Runtime-Befund jetzt explizit als autoritative
  Runtime-Aussage formulieren.
- Fuer Null-Inventarfaelle ist die explizite Formulierung
  `Im Runtime-Skill-System sind aktuell keine installierten Skills vorhanden.`
  jetzt direkt im Prompt-Contract hinterlegt.
- Unmarkierte Faehigkeitslisten, Persona-/Selbstbeschreibungen und
  anthropomorphe Metaphern sind fuer diesen Pfad jetzt zusaetzlich explizit
  untersagt:
  [core/layers/output.py](<repo-root>/core/layers/output.py)
- Abgesichert ist das ueber erweiterte Prompt-/Flow-Tests:
  [test_output_tool_injection.py](<repo-root>/tests/unit/test_output_tool_injection.py)
  und
  [test_skill_catalog_prompt_flow.py](<repo-root>/tests/unit/test_skill_catalog_prompt_flow.py)
- Zusaetzlich hat die Output-Schicht jetzt einen gezielten semantischen
  Postcheck fuer `skill_catalog_context`:
  - erkennt freie Persona-/Faehigkeitslisten nach Runtime-Inventarfragen
  - erkennt Vermischung von Runtime-Skills und Tools ausserhalb von
    `Einordnung`
  - erkennt unbelegte Session-/System-Skill-Claims
- Wenn dieser Postcheck feuert, wird die Antwort jetzt auf eine kurze,
  sachliche Reparaturfassung aus Runtime-Snapshot plus Kategorienregel
  zusammengezogen:
  [core/layers/output.py](<repo-root>/core/layers/output.py)
- Der neue Reparaturpfad ist ueber gezielte Grounding-Tests abgesichert:
  [test_output_grounding.py](<repo-root>/tests/unit/test_output_grounding.py)
- Fuer gemischte Prompts aus Faktinventar plus Wunsch-/Brainstorming-Teil
  gibt es jetzt zusaetzlich ein explizites Hint-/Output-Signal
  `fact_then_followup`:
  - der faktische Inventarteil hat Vorrang
  - Brainstorming darf erst danach in einem markierten Anschlussblock
    `Wunsch-Skills` oder `Naechster Schritt` folgen
- Der `skill_catalog_context`-Postcheck repariert jetzt auch unsauber
  vermischte Inventar-/Wunsch-Antworten auf eine sauber getrennte Fassung:
  [core/orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
  und
  [core/layers/output.py](<repo-root>/core/layers/output.py)
- Der Stream-/Debug-Trace fuer `skill_catalog_context` enthaelt jetzt zusaetzlich:
  - gewaehlte Hints
  - ausgewaehlte Addon-Docs
  - aktivierten Strict-Mode
  - finalen Postcheck-Status (`pending`, `passed`, `repaired:...`)
- Im Streaming-Pfad wird das ueber ein leichtes `thinking_trace`-Event auch in
  die Thinking-Box gespiegelt:
  [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py),
  [adapters/Jarvis/static/js/chat.js](<repo-root>/adapters/Jarvis/static/js/chat.js),
  [adapters/Jarvis/static/js/chat-thinking.js](<repo-root>/adapters/Jarvis/static/js/chat-thinking.js)
- Auch der Sync-/Debug-Pfad traegt diese Skill-Katalog-Trace-Daten jetzt in
  `verified_plan["_ctx_trace"]` ein:
  [core/orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)

Verifiziert:

- `pytest -q tests/unit/test_orchestrator_plan_schema_utils.py tests/unit/test_skill_catalog_prompt_flow.py`
- `pytest -q tests/unit/test_skill_addons_loader_contract.py tests/unit/test_orchestrator_runtime_safeguards.py tests/unit/test_output_tool_injection.py -q`
- `pytest -q tests/unit/test_output_tool_injection.py tests/unit/test_skill_catalog_prompt_flow.py`
- `pytest -q tests/unit/test_output_grounding.py tests/unit/test_output_tool_injection.py tests/unit/test_skill_catalog_prompt_flow.py`
- `pytest -q tests/unit/test_orchestrator_plan_schema_utils.py tests/unit/test_output_tool_injection.py tests/unit/test_skill_catalog_prompt_flow.py tests/unit/test_output_grounding.py`
- `pytest -q tests/unit/test_orchestrator_runtime_safeguards.py tests/unit/test_output_grounding.py tests/unit/test_frontend_stream_activity_contract.py tests/unit/test_orchestrator_plan_schema_utils.py tests/unit/test_output_tool_injection.py tests/unit/test_skill_catalog_prompt_flow.py`

Wichtig:

- Der Live-Drift ist damit jetzt reproduzierbar und im Plan/Testbestand sichtbar.
- Routing, Strategy und Addon-Auswahl sind fuer den beobachteten Fall stabiler.
- Auch wenn das Modell trotz Prompt weiter driftet, bleibt der
  `skill_catalog_context`-Pfad jetzt ueber einen spezialisierten
  Postcheck/Reparaturmodus semantisch sauber.
- Gemischte Skill-Inventarfragen mit anschliessendem Wunsch-/Brainstorming-Teil
  verwischen den faktischen Runtime-Befund jetzt nicht mehr, sondern werden
  auf einen Faktblock plus optionalen Anschlussblock getrennt.
- Der naechste Live-Test ist jetzt deutlich besser erklaerbar, weil Hints,
  Addon-Docs, Strict-Mode und Postcheck-Status entlang des Pfads sichtbar sind.
- Der nachgezogene Live-/UI-Gegencheck zeigt aber auch, dass der Pfad trotz
  umgesetzter Bloecke 1 bis 6 noch nicht komplett signoff-faehig ist:
  - mehrere Skill-Inventarantworten landen inhaltlich korrekt erst ueber den
    Reparaturpfad
  - der Reparaturblock `[Grounding-Korrektur]` ist derzeit noch user-sichtbar
  - der `draft_skills`-Pfad kann fuer reine Inventarfragen noch in einen
    Skill-Erstellungsflow kippen

Offen als naechster Schritt:

- `missing_runtime_section` im Skill-Catalog-Pfad weiter zurueckdruecken,
  damit die finale Antwort nicht primaer ueber Repair entsteht
- Sequential-/Thinking-Drift fuer draft-fokussierte Inventarfragen eindämmen
- danach Positivfall mit echten Draft-Skills explizit gegenpruefen
- danach kurzer erneuter Live-/UI-Gegencheck des kompletten
  Skill-Catalog-Pfads

---

## Live-E2E-Auswertung 2026-04-03 nach Block 6

Nach Umsetzung von Block 6 wurde der Pfad in der WebUI live geprueft.

Getestete Prompts:

- `Welche Skills hast du?`
- `Welche Skills stehen dir aktuell zur Verfuegung?`
- `Was ist der Unterschied zwischen Tools und Skills?`
- `Dir stehen SKILLS zu Verfuegung. Kannst du mal schauen, was du darueber in
  Erfahrung bringen kannst? Was fuer Skills haettest du gerne?`
- `Welche Draft-Skills gibt es gerade?`
- `Warum zeigt list_skills nicht alle Faehigkeiten von dir?`

Positiv:

- Die Trace-Sichtbarkeit aus Block 6 funktioniert live:
  - `Catalog Hints`
  - `Addon Docs`
  - `Inventory Mode`
  - `Postcheck`
- Fuer allgemeine Skill-Inventarfragen wird weiter sauber
  `resolution_strategy=skill_catalog_context` gesetzt.
- Die Hints sind im Live-Trace jetzt deutlich besser:
  - `runtime_skills`
  - `overview`
  - `tools_vs_skills`
  - `answering_rules`
  - im gemischten Fall auch `fact_then_followup`
- Der semantische Kern der Antworten ist bei mehreren Prompts jetzt korrekt:
  - keine installierten Runtime-Skills
  - klare Trennung zwischen Runtime-Skills und Built-in Tools/Faehigkeiten

Negativ / offen:

- Bei den Prompts
  - `Welche Skills hast du?`
  - `Welche Skills stehen dir aktuell zur Verfuegung?`
  - `Was ist der Unterschied zwischen Tools und Skills?`
  - `Dir stehen SKILLS ... Was fuer Skills haettest du gerne?`
  - `Warum zeigt list_skills nicht alle Faehigkeiten von dir?`
  endet der Trace jeweils bei
  `Postcheck: repaired:missing_runtime_section`.
- Das ist fachlich besser als freier Drift, zeigt aber auch:
  der Basisausgabe-Contract wird live noch nicht stabil nativ eingehalten,
  sondern erst im Reparaturpfad erzwungen:
  [core/layers/output.py](<repo-root>/core/layers/output.py)
- Der Reparaturpfad leakt aktuell sichtbar in die User-Antwort hinein als
  `[Grounding-Korrektur]`.
  Das ist fuer Debug hilfreich, aber fuer echten E2E-Betrieb falsch.
- Der gemischte Prompt mit Wunsch-Skills ist nur ein Teiltreffer:
  `fact_then_followup` wird zwar erkannt, die Rohantwort driftet aber vor der
  Reparatur noch in generische Faehigkeiten.
- `Welche Draft-Skills gibt es gerade?` ist aktuell ein echter Live-Fail:
  statt einer reinen Inventarantwort oeffnet der Pfad einen
  Skill-Erstellungsdialog (`pending_skill_creation`) und endet danach in einem
  JSON-Fehler.

Bewertung pro Prompt:

- `Welche Skills hast du?` -> inhaltlich ok, technisch nur ueber Reparaturpfad
- `Welche Skills stehen dir aktuell zur Verfuegung?` -> inhaltlich ok,
  technisch nur ueber Reparaturpfad
- `Was ist der Unterschied zwischen Tools und Skills?` -> inhaltlich ok,
  technisch nur ueber Reparaturpfad
- gemischter Inventar-/Wunsch-Prompt -> teilweise ok, aber noch nicht sauber
  genug
- `Welche Draft-Skills gibt es gerade?` -> fehlgeschlagen
- `Warum zeigt list_skills nicht alle Faehigkeiten von dir?` -> inhaltlich ok,
  technisch nur ueber Reparaturpfad

Fazit:

- Bloecke 1 bis 6 haben den Pfad klar stabilisiert und debugbar gemacht.
- Fuer einen sauberen Live-Signoff fehlen aber noch zwei Nachschaerfungen:
  1. Reparaturblock darf nicht user-sichtbar werden.
  2. `draft_skills` darf bei Inventarfragen keinen Erstellungsflow starten.
- Die tiefergehende Ursachenanalyse und der Folgeplan fuer diese Restfehler
  sind jetzt separat dokumentiert:
  [[2026-04-03-skill-catalog-restfehler-routing-und-output-implementationsplan]]

## Anlass

Der neue Skill-Pfad wurde live gegen einen echten Prompt getestet.

Beobachteter Turn:

- User fragt sinngemaess nach verfuegbaren Skills und nach Wunsch-Skills
- Thinking erkennt korrekt:
  - `resolution_strategy=skill_catalog_context`
  - `suggested_tools=["list_skills"]`
  - `is_fact_query=true`
- Control gibt frei
- Output antwortet:
  - korrekt: aktuell keine installierten Runtime-Skills
  - danach aber semantisch driftend:
    - `Ich habe trotzdem grundlegende Faehigkeiten`
    - `Memory`
    - `Eigenes Denken`
    - `Tools`
    - `Skill-Erstellung`
    - anthropomorphe Nebenformulierung mit `mein Koerper`

Damit ist der Pfad **architektonisch korrekt geroutet**, aber **in der finalen Formulierung noch nicht hart genug gebunden**.

---

## Kurzdiagnose

### 1. Routing- und Resolver-Pfad funktionieren bereits

Der Live-Trace zeigt:

- semantische Erkennung funktioniert
- `skill_catalog_context` wird gesetzt
- `list_skills` wird als faktische Quelle genutzt

Der Fehler sitzt damit **nicht primaer** in Thinking oder beim Tool-Routing.

### 2. Der Output-Prompt ist fuer Skill-Kategorien noch zu weich

Aktuell gibt es in [output.py](<repo-root>/core/layers/output.py):

- `list_skills` beschreibt nur installierte Runtime-Skills
- Ebenen trennen
- Built-in Tools nicht als installierte Skills formulieren
- Session-/System-Skills nur nennen, wenn explizit belegt

Das reicht fuer den Live-Fall noch nicht aus.
Das Modell bleibt frei genug, nach der korrekten Runtime-Aussage in eine weichere `Faehigkeitenwelt` zu springen.

### 3. Es fehlt ein harter Antwortmodus fuer mehrdeutige Skill-Inventarfragen

Die Frage `welche skills hast du?` ist nicht nur semantisch mehrdeutig, sondern im Modell auch sozial anschlussfaehig.
Ohne engeres Antwortschema driftet die Antwort leicht in:

- allgemeine Tools
- Systemfaehigkeiten
- Persona-/Selbstbeschreibung
- Wunsch-/Brainstorming-Teil

### 4. Es fehlt noch eine semantische Post-Generation-Kontrolle

Der aktuelle Pfad validiert:

- Tool-Evidence
- Zahlen-/Qualitativ-Grounding

Er validiert aber noch nicht stark genug:

- Kategorie-Leakage zwischen Runtime-Skills und Built-in Tools
- unbelegte Session-/System-Skill-Behauptungen
- anthropomorphe oder locker-personalisierende Zusatzaussagen in faktischen Skill-Antworten

### 5. `strategy_hints` sind im Live-Fall noch nicht maximal hilfreich

Im beobachteten Trace waren die Hints:

- `runtime_skills`
- `draft_skills`
- `overview`

Fuer den eigentlichen Antwortstil waere in solchen Faellen zusaetzlich besonders hilfreich:

- `answering_rules`
- `tools_vs_skills`

Damit waere die Output-Schicht frueher und robuster auf Kategorie-Trennung ausgerichtet.

---

## Zielbild

Bei Fragen wie:

- `welche skills hast du?`
- `welche skills stehen dir zur verfuegung?`
- `was ist der unterschied zwischen tools und skills?`

soll TRION in stabiler Reihenfolge antworten:

1. erst die autoritative Runtime-Aussage
2. dann eine explizite Kategorienklaerung
3. dann nur bei Bedarf ein sauber markierter Zusatzblock zu Built-in Tools oder Drafts
4. erst danach optional rueckfragen oder Wunsch-Skill-Diskussion

Nicht mehr zulaessig als unmarkierter Fliesstext:

- Runtime-Skills und Tools vermischen
- unbelegte Session-/System-Skills nennen
- allgemeine Agentenfaehigkeiten als installierte Skill-Landschaft darstellen

---

## Erwartetes Zielverhalten

Beispiel fuer denselben Live-Fall:

`Im Runtime-Skill-System sind aktuell keine installierten Skills vorhanden.`

`Das bezieht sich nur auf installierte Runtime-Skills. Built-in Tools und allgemeine Systemfaehigkeiten sind davon getrennt und werden nicht als installierte Skills gezaehlt.`

`Wenn du willst, kann ich dir im naechsten Schritt getrennt zeigen: Runtime-Skills, Draft-Skills und Built-in Tools/Faehigkeiten.`

Optional erst danach:

`Wenn du neue Skills priorisieren willst, waeren konkrete Use-Cases hilfreich.`

---

## Umsetzungsbloecke

## Block 1 - Live-Fall sauber als Regression festhalten

### Ziel

Der beobachtete Drift muss als reproduzierbarer Contract vorliegen, nicht nur als Chat-Beispiel.

### Aenderungen

- neuen Testfall fuer den beobachteten Live-Prompt anlegen
- nicht nur auf `skill_catalog_context` pruefen, sondern auf verbotene Drift-Muster
- Negativ-Assertions fuer:
  - unmarkiertes `Ich habe trotzdem grundlegende Faehigkeiten`
  - Built-in Tools als Skill-Ersatz ohne Trennsatz
  - unbelegte Session-/System-Skill-Behauptungen
  - anthropomorphe Runtime-Hinweise wie `mein Koerper`

### Akzeptanzkriterium

Der konkrete Fehlmodus ist als Testfall sichtbar und kann nicht still wieder auftreten.

---

## Block 2 - Strategy-Hints fuer Skill-Inventarfragen schaerfen

### Ziel

Schon vor dem Output soll klarer werden, dass es sich um einen streng kategorisierten Skill-Inventarfall handelt.

### Aenderungen

- [core/orchestrator_plan_schema_utils.py](<repo-root>/core/orchestrator_plan_schema_utils.py)
  - fuer `skill_catalog_context` staerker defaults setzen:
    - `answering_rules`
    - `tools_vs_skills`, wenn nach `verfuegbar`, `zur verfuegung`, `Faehigkeiten` oder `hast du` gefragt wird
- optional:
  - dedizierten Hint wie `inventory_question` oder `strict_skill_inventory` einfuehren

### Akzeptanzkriterium

Skill-Inventarfragen tragen konsistent genug Hints, damit spaetere Layer nicht mehr raten muessen.

---

## Block 3 - Output fuer `skill_catalog_context` von Regeln auf Antwortschema anheben

### Ziel

Die aktuelle Regelmenge soll in einen staerkeren, fast schablonenartigen Antwortmodus ueberfuehrt werden.

### Aenderungen

- [core/layers/output.py](<repo-root>/core/layers/output.py)
  - fuer `skill_catalog_context` zusaetzliche harte Prompt-Regeln:
    - erster Satz muss die Runtime-Autoritaet benennen
    - wenn keine Runtime-Skills vorhanden: das explizit als Runtime-Befund formulieren
    - Built-in Tools nur in einem explizit markierten zweiten Abschnitt
    - allgemeine Agentenfaehigkeiten nicht als Skill-Liste formulieren
    - anthropomorphe Metaphern in faktischen Skill-Antworten vermeiden
  - bevorzugtes Format fuer diesen Strategy-Typ:
    - `Runtime-Skills`
    - `Einordnung`
    - optional `Naechster Schritt`

### Akzeptanzkriterium

Das Modell antwortet bei Skill-Inventarfragen nicht mehr frei aus der Persona heraus, sondern entlang des vorgesehenen Kategorienschemas.

---

## Block 4 - Semantischen Postcheck fuer Skill-Kategorie-Leakage einfuehren

### Ziel

Wenn das Modell trotz Prompt weiter driftet, muss der Pfad reparieren oder fail-closed zusammenfassen koennen.

### Aenderungen

- [core/layers/output.py](<repo-root>/core/layers/output.py)
  - leichter Postcheck fuer `skill_catalog_context`:
    - erkennt Vermischung von Runtime-Skills und Tools
    - erkennt unbelegte Session-/System-Skill-Claims
    - erkennt zu freie Selbstbeschreibung nach Runtime-Inventarfragen
  - Fallback:
    - kurze, sachliche Reparaturantwort aus Runtime-Snapshot plus Skill-Addon-Regeln

### Akzeptanzkriterium

Auch bei Modell-Drift bleibt die ausgegebene Antwort semantisch sauber oder wird auf eine sichere Kurzfassung repariert.

---

## Block 5 - Optionaler Split zwischen Faktantwort und Follow-up-Frage

### Ziel

Gemischte User-Prompts wie `was kannst du / was haettest du gern` sollen nicht die Faktantwort verwischen.

### Aenderungen

- entweder im Output:
  - zuerst faktischer Hauptblock
  - erst danach ein markierter Follow-up-Block
- oder bereits im Plan:
  - Hinweis, dass faktischer Inventarteil Vorrang vor Brainstorming hat

### Akzeptanzkriterium

Die Frage nach Wunsch-Skills darf den faktischen Skill-Inventarteil nicht mehr semantisch verwaschen.

---

## Block 6 - Sichtbarkeit im Trace und spaeter im Frontend verbessern

### Ziel

Wenn der Pfad wieder driftet, soll sofort sichtbar sein, ob das Problem aus:

- Hints
- Addon-Auswahl
- Runtime-Snapshot
- Output-Regeln

kommt.

### Aenderungen

- Stream-/Debug-Trace fuer `skill_catalog_context` erweitern um:
  - gewaehlte Hints
  - ausgewaehlte Addon-Docs
  - aktivierten strict-mode fuer Skill-Inventar
  - ggf. semantischen Postcheck/Fallback

### Akzeptanzkriterium

Der naechste Live-Test ist besser erklaerbar und nicht nur am Endtext beurteilbar.

---

## Empfohlene Reihenfolge

1. Block 1 - Live-Fall als Regression festhalten
2. Block 2 - Strategy-Hints schaerfen
3. Block 3 - Output auf Antwortschema umstellen
4. Block 4 - semantischen Postcheck einfuehren
5. Block 5 - Faktteil und Follow-up sauber trennen
6. Block 6 - Trace/Frontend sichtbarer machen

Begruendung:

- zuerst den Fehler sauber einfrieren
- dann die wahrscheinlich wirksamste Stelle fixen: Output-Schema
- erst danach mit Postcheck/Fallback absichern

---

## Nicht-Ziele

- kein blindes Umschreiben der Skill-Addon-MDs ohne klaren Trace-Befund
- keine zweite Truth-Source fuer Inventardaten
- kein hektischer Persona-Fix quer durch andere Antworttypen
- kein Frontend-Umbau, bevor der Backend-Vertrag fuer diese Antworten sauber ist

---

## Erwarteter Nutzen

Mit diesem Follow-up wird der Skill-Pfad nicht nur korrekt geroutet, sondern auch in der letzten Meile robuster:

- sauberere Trennung zwischen Runtime-Skills und Built-in Tools
- weniger Persona-/Faehigkeitsdrift
- stabilere Antworten auf offene Skill-Fragen
- bessere Erklaerbarkeit bei Live-E2E-Tests
