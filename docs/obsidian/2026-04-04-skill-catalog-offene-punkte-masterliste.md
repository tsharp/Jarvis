# Skill-Catalog Offene Punkte - Masterliste

Erstellt am: 2026-04-04
Zuletzt aktualisiert: 2026-04-05
Status: **Aktiv**
Bezieht sich auf:

- [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]] - neuer Zielplan: frueher bindender Contract statt spaeter Prompt-/Repair-Fokus
- [[2026-04-04-skill-catalog-draft-evidence-output-repair-gap]] - aktueller Null-Draft-Befund nach Draft-Evidence-Fix
- [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]] - Live-E2E-Follow-up und UI-Gegencheck
- [[2026-04-03-skill-catalog-restfehler-routing-und-output-implementationsplan]] - Root-Cause und Restfehlerbloecke
- [[2026-04-02-skills-semantik-md-leitplanken-implementationsplan]] - semantische Skill-Leitplanken
- [[2026-04-02-thinking-strategy-authority-and-frontend-visibility-implementationsplan]] - Thinking-/Strategy-/Trace-Folgepunkte
- [[2026-03-31-control-layer-audit]] - uebergeordnete offene Control-Punkte

---

## Zweck

Diese Notiz ist der zentrale Sammelpunkt fuer offene Punkte im aktuellen
Skill-Catalog-Strang.

Sie soll:

- offene Punkte an einer Stelle sammeln
- historische, bereits ueberholte Restfehler von echten offenen Themen trennen
- die naechste sinnvolle Reihenfolge festhalten
- Suchaufwand ueber mehrere Tagesnotizen reduzieren

---

## Stand 2026-04-04

Neuer Architekturentscheid:

- Der vorgelagerte Pfad erkennt `skill_catalog_context` inzwischen bereits
  nahe am Zielbild.
- Der naechste Hauptschnitt ist deshalb kein weiteres Hardprompting, sondern
  ein **frueher bindender Skill-Catalog-Policy-Contract**.
- Referenz dafuer ist ab jetzt:
  [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]]

Bereits nicht mehr primaer offen:

- Routing fuer Draft-Inventarfragen auf Skill-Erstellung
- sichtbarer `[Grounding-Korrektur]`-Leak im aktuellen Skill-Catalog-Pfad
- Trace-vs-Execution-Unsichtbarkeit fuer den geprueften Null-Draft-Fall
- Draft-Evidence-Verlust im aktuellen **Null-Draft-Fall**
- native Antworttrennung fuer den geprueften Wunsch-/Follow-up-Fall
  (`Runtime-Skills` -> `Einordnung` -> `Wunsch-Skills`)

Wichtig:

- Der aktuelle lokale Workspace hat unter
  [shared_skills](<repo-root>/shared_skills) kein `_drafts`-Verzeichnis.
- Damit ist der Null-Draft-Befund plausibel, aber **kein Positivfall** mit
  echten Draft-Skills verifiziert.

Quellen:

- [[2026-04-04-skill-catalog-draft-evidence-output-repair-gap]]
- [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]]

Neuer Live-Stand nach Backend-Restart und Recheck:

- der Wunsch-/Follow-up-Prompt
  `Welche Skills hast du aktuell und welche Skills wuerdest du dir als Naechstes wuenschen?`
  lief mit:
  - `fact_then_followup` in den Hints
  - `needs_sequential_thinking=false`
  - `Postcheck: passed`
- der Draft-Prompt
  `Welche Draft-Skills gibt es gerade? ... warum list_skills sie nicht anzeigt`
  lief mit:
  - `Tools` und `Exec Tools`: `list_draft_skills`, `list_skills`
  - `Postcheck: passed`
  - sichtbarer Endantwort ohne hypothetische Draft-Beispiele
- nach Frontend-Hard-Reload zeigt auch die sichtbare `Live Trace`-Box jetzt den
  finalen `trace_final`-Snapshot konsistent mit:
  - `needs_sequential_thinking=false`
  - `final_execution_tools`: `list_draft_skills`, `list_skills`
  - `skill_catalog_postcheck: passed`

Neuer Stand nach Gap-Suite auf die zuletzt beobachteten Live-Drifts:

- der fruehe Control-/Policy-Pfad bleibt fuer die geprueften Faelle der
  stabilste Teil:
  - `skill_catalog_context`
  - passende Hints
  - Read-only-Tools
  - `Sequential=false`
  - sichtbarer Policy-Contract im Trace
- die bisherige semantische Gap-Suite ist jetzt voll geschlossen:
  - der Follow-up-Contract erzwingt im Runtime-plus-Wishlist-Fall kein
    implizites `list_draft_skills` mehr, wenn keine explizite Draft-Frage
    vorliegt
- der erste Gap ist geschlossen:
  - `tools_vs_skills`-Antworten mit capability-styliger Built-in-/
    Kernfaehigkeiten-Selbstbeschreibung werden jetzt im semantischen
    Leakage-Check und im Postcheck repariert
- der zweite Gap ist geschlossen:
  - `inventory_read_only`-Antworten mit ungefragten Skill-Erstellungs- oder
    Aktionsangeboten werden jetzt im semantischen Leakage-Check erkannt und im
    Postcheck auf den sicheren Inventar-Fallback gezogen
- der dritte Gap ist geschlossen:
  - Draft-Befunde gelten im Skill-Catalog-Output jetzt nur noch mit echter
    `list_draft_skills`-Evidence als verifiziert; ohne diese Evidence wird auf
    explizite Nicht-Verifikation repariert

Verifiziert ueber Gap-Suite:

- [tests/unit/test_skill_catalog_semantic_gap_suite.py](<repo-root>/tests/unit/test_skill_catalog_semantic_gap_suite.py)
- `pytest -q tests/unit/test_skill_catalog_semantic_gap_suite.py`
- aktueller Stand: `6 passed`

## Update 2026-04-05 - Stand nach Hint-Kanonisierung und Output-Nachschaerfung

Der gemischte Inventar-/Wunsch-Prompt

- `Welche Skills hast du aktuell und welche Skills wuerdest du dir als Naechstes wuenschen? Trenne bitte sauber zwischen Runtime-Skills, Built-in Tools und anderen Ebenen und erklaere kurz, warum list_skills nicht alles zeigt.`

lief im aktuellen Live-Recheck jetzt mit sauberem Upstream-Contract:

- `resolution_strategy = skill_catalog_context`
- kanonische `strategy_hints`:
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

Zusatzstand:

- der Follow-up-Anschlussblock bleibt jetzt auch im sichtbaren Endtext
  policy-konsistent bei `Wunsch-Skills`
- die zuvor offene zu breite `list_draft_skills`-Ableitung fuer diesen
  Prompt ist damit im Live-Trace nicht mehr sichtbar
- die sichtbare Endantwort ist fuer den geprueften Fall jetzt korrekt getrennt
  und konservativ formuliert

Offen bleibt nur noch ein letzter Live-Restbefund:

- `skill_catalog_postcheck = repaired:unverified_session_system_skills`

Das bedeutet:

- Routing, Contract und sichtbare Antwort sind inzwischen sauber
- der Rohoutput driftet intern fuer diesen Prompt aber noch kurz in
  unbelegte Session-/System-Skill-Erwaehnungen
- der Postcheck zieht das bereits korrekt auf die sichere Fassung zurueck

Neu verifiziert:

- `pytest -q tests/unit/test_orchestrator_plan_schema_utils.py` -> `8 passed`
- `pytest -q tests/unit/test_output_tool_injection.py` -> `9 passed`
- `pytest -q tests/unit/test_output_grounding.py` -> `41 passed`
- `pytest -q tests/unit/test_skill_catalog_prompt_flow.py tests/unit/test_skill_catalog_semantic_gap_suite.py` -> `9 passed`

---

## Prioritaet 1 - Aktuelle Kernpunkte

### 1. Skill-Catalog-Policy frueh binden statt spaet reparieren

Status:

- weitgehend umgesetzt, letzter Rohoutput-Rest offen

Kern:

- Thinking, Precontrol und Control erkennen die geprueften Skill-Catalog-Faelle
  bereits sauber:
  - `skill_catalog_context`
  - passende Hints
  - Read-only-Tools
  - `Sequential=false`
  - `Postcheck=passed`
- dieser Zustand wird aber noch nicht als bindender Downstream-Contract durch
  die Pipeline getragen
- der eigentliche kombinierte Skill-Kontext aus Live-Fakten und `skill_addons`
  entsteht noch zu spaet

Warum offen:

- die korrekte fruehe Deutung soll von einem guten Befund zu einer
  verbindlichen Policy werden
- dafuer muessen Control/Orchestrator frueher festziehen, welche Tools,
  Abschnitte und Guardrails gelten

Update:

- `_skill_catalog_policy` wird frueh materialisiert und von Output/Trace und
  Skill-Semantik-Resolver gelesen
- die Hint-Kanonisierung begrenzt den Live-Pfad jetzt auf kanonische
  Skill-Catalog-Hints
- der gepruefte Runtime-plus-Wishlist-Fall bleibt im Live-Trace jetzt bei
  `required_tools = ["list_skills"]`
- offen bleibt aktuell nur noch:
  - letzter Rohoutput-Drift in unbelegte Session-/System-Skills
  - finaler Live-Recheck nach dieser letzten Nachschaerfung

Primaere Quelle:

- [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]]

Sekundaere Quellen:

- [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]]
- [[2026-04-03-skill-catalog-restfehler-routing-und-output-implementationsplan]]
- [[2026-04-04-skill-catalog-draft-evidence-output-repair-gap]]

### 2. Positivfall mit echten Draft-Skills verifizieren

Status:

- offen

Kern:

- bisher ist nur der Null-Draft-Fall plausibilisiert
- es fehlt ein echter Positivfall mit verifizierten Draft-Skills

Primaere Quelle:

- [[2026-04-04-skill-catalog-draft-evidence-output-repair-gap]]

Moegliche Formen:

- Fixture
- temporaerer Draft unter `shared_skills/_drafts`
- dedizierter Testbestand

### 3. Native Stabilitaet fuer gemischte Inventar-/Wunsch-Prompts

Status:

- weitgehend behoben, letzter Rohoutput-Rest offen

Kern:

- der gepruefte Wunsch-/Follow-up-Prompt laeuft jetzt live mit:
  - `fact_then_followup`
  - `needs_sequential_thinking=false`
  - `Required Tools`: `list_skills`
  - `Exec Tools`: `list_skills`
  - sichtbar getrennten Abschnitten bis `Wunsch-Skills`
- fuer diesen Block offen bleibt damit nur noch:
  - letzter Rohoutput-Drift hinter `repaired:unverified_session_system_skills`
  - breitere Gegenpruefung weiterer Prompt-Varianten

Primaere Quelle:

- [[2026-04-03-skill-catalog-restfehler-routing-und-output-implementationsplan]]

Sekundaere Quelle:

- [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]]

---

## Prioritaet 2 - Angrenzende Folgepunkte

### 4. Skill-Catalog-Live-/UI-Gegencheck nach Contract-Refactor erneut fahren

Status:

- offen nach den Kernfixes

Kern:

- nach Rohoutput-Haertung und Positivfall-Test soll der komplette Pfad erneut
  live geprueft werden

Soll erneut abdecken:

- Null-Draft-Fall
- Positivfall mit echten Drafts
- Erklaerung, warum `list_skills` Drafts nicht zeigt
- gemischte Inventar-/Wunsch-Fragen
- mehrdeutige `tools_vs_skills`-/`capabilities`-Prompts

Quelle:

- [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]]

### 5. Frontend-/Trace-Sichtbarkeit fuer `skill_catalog_context` weiter ausbauen

Status:

- spaeter / optional

Kern:

- der Pfad ist sichtbar, aber nicht zwingend schon das Endbild
- moeglich sind klarere Strategy-/Summary-Signale im Frontend

### 6. Output-Semantik und Postcheck fuer mehrdeutige Skill-Fragen nachziehen

Status:

- offen

Kern:

- der fruehe Contract ist fuer die geprueften Faelle sichtbar stabil
- die Restfehler sitzen jetzt enger in:
  - semantischer Output-Drift bei `tools_vs_skills` und `capabilities`
  - zu permissivem `Postcheck: passed`
  - ungefragten Aktions-/Erstellungsangeboten im
    `inventory_read_only`-Modus

Referenz:

- [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]]
- [tests/unit/test_skill_catalog_semantic_gap_suite.py](<repo-root>/tests/unit/test_skill_catalog_semantic_gap_suite.py)

Quellen:

- [[2026-04-02-skills-semantik-md-leitplanken-implementationsplan]]
- [[2026-04-02-thinking-strategy-authority-and-frontend-visibility-implementationsplan]]
- [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]]

### 6. Tiefere Loop-/Refinement-Logik fuer Skill-Unsicherheiten

Status:

- offen

Kern:

- im Skill-Semantik-Plan explizit als spaetere Folgearbeit markiert
- betrifft eher Ausbau als aktuellen Kernbug

Quelle:

- [[2026-04-02-skills-semantik-md-leitplanken-implementationsplan]]

---

## Prioritaet 3 - Uebergeordnete Plattformpunkte

Diese Punkte sind nicht der naechste Skill-Catalog-Blocker, bleiben aber im
rueckverlinkten Systemkontext offen.

### 8. Strategy-/Control-Eventmodell weiter vervollstaendigen

Offen:

- echte Strategy-Events wie `strategy_selected` oder `strategy_validated`
- Control-Entscheidung ggf. als eigener Stream-Event
- deterministische Execution fuer weitere Strategy-Klassen

Quelle:

- [[2026-04-02-thinking-strategy-authority-and-frontend-visibility-implementationsplan]]

### 9. Uebergeordnete Control-Schulden

Offen:

- Control Skip bei `low_risk`
- Warning-Severity / blocking vs. advisory
- Memory-Write nicht deterministisch

Quelle:

- [[2026-03-31-control-layer-audit]]

---

## Empfohlene Reihenfolge

1. Positivfall mit echten Draft-Skills herstellen und pruefen
2. danach kurzer kompletter Live-/UI-Gegencheck
3. gemischte Inventar-/Wunsch-Prompts nur noch breit gegen weitere Varianten
   gegenpruefen

---

## Nicht mehr als aktueller Hauptblocker fuehren

Diese Punkte sollen in Folgegespraechen nicht mehr als primaerer Restfehler
auftauchen, solange kein neuer Gegenbefund auftaucht:

- Draft-Inventarfrage kippt in Skill-Erstellung
- sichtbarer `[Grounding-Korrektur]`-Leak im geprueften Skill-Catalog-Pfad
- reiner Draft-Evidence-Verlust im aktuellen Null-Draft-Fall

Quellen:

- [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]]
- [[2026-04-04-skill-catalog-draft-evidence-output-repair-gap]]

---

## Pflegehinweis

Wenn ein Punkt erledigt ist:

- hier Status umstellen
- von `Prioritaet 1` nach `nicht mehr Hauptblocker` oder in eine spaetere
  Kategorie verschieben
- die urspruengliche Detailnotiz nur als Befundhistorie behalten

Damit bleibt diese Note der Einstiegspunkt und die Tagesnotizen bleiben die
Detailbelege.
