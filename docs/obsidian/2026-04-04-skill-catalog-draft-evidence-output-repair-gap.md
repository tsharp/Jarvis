# Skill-Catalog Draft-Evidence und Output-Repair - Befund

Erstellt am: 2026-04-04
Zuletzt aktualisiert: 2026-04-04
Status: **Vorlaeufig behoben**
Bezieht sich auf:

- [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]] - neuer Zielplan: fruehen Skill-Catalog-Contract statt spaeter Repair-Verantwortung ausbauen
- [[2026-04-04-skill-catalog-offene-punkte-masterliste]] - zentraler Sammelpunkt fuer offene Punkte im Skill-Catalog-Strang
- [[2026-04-03-skill-catalog-restfehler-routing-und-output-implementationsplan]] - Restfehleranalyse fuer Routing, Output und Trace
- [[2026-04-03-skill-catalog-live-e2e-followup-implementationsplan]] - Live-E2E-Follow-up und UI-Gegencheck
- [[2026-04-02-skills-semantik-md-leitplanken-implementationsplan]] - semantische Skill-Leitplanken

---

## Anlass

Der Live-Gegencheck nach Umsetzung von Block A bis D zeigt:

- Routing ist fuer Draft-Inventarfragen jetzt korrekt
- `list_draft_skills` und `list_skills` laufen beide
- Trace und Execution sind konsistent sichtbar
- die finale Antwort verliert den Draft-Befund aber trotzdem

Beobachteter Prompt:

- `Welche Draft-Skills gibt es gerade? Nenne die Draft-Skills explizit. Erklaere danach kurz, warum list_skills sie nicht anzeigt.`

Beobachteter Trace:

- `resolution_strategy=skill_catalog_context`
- `Tools: list_draft_skills, list_skills`
- `Exec Tools: list_draft_skills, list_skills`
- `Postcheck: repaired:missing_runtime_section`

Beobachtete Endantwort:

- nur Runtime-Nullbefund
- keine explizite Draft-Liste
- kurze Einordnung zu Runtime-Skills vs. Built-in Tools

---

## Update 2026-04-04 spaeterer Live-Gegencheck

Nach dem gezielten Fix fuer `list_draft_skills`-Evidence und Skill-Catalog-
Repair zeigt der erneute WebUI-Test jetzt:

- `list_draft_skills` und `list_skills` laufen weiter korrekt
- die Endantwort enthaelt jetzt auch die Draft-Einordnung im Repair-Text
- im aktuellen lokalen Setup sind dabei **keine Draft-Skills verifiziert**
- die Antwort nennt jetzt explizit, dass `list_skills` nur installierte
  Runtime-Skills zeigt und Drafts deshalb nicht auffuehrt

Zusatzbefund aus dem Workspace:

- unter [shared_skills](<repo-root>/shared_skills) gibt es aktuell kein
  `_drafts`-Verzeichnis

Damit ist fuer den aktuellen Instanzzustand der konkrete Draft-Evidence-Fehler
vorlaeufig behoben.

## Update 2026-04-05 - Semantischer Contract nachgezogen

Die verbleibende semantische Luecke
`Draft-Claims ohne echte list_draft_skills-Evidence`
ist jetzt ebenfalls im Output geschlossen:

- Draft-Befunde gelten im Skill-Catalog-Postcheck nur noch dann als
  verifiziert, wenn in diesem Turn echte `list_draft_skills`-Evidence mit
  `status=ok` vorliegt
- `skill_registry_snapshot` bleibt als Hilfssignal sichtbar, reicht aber nicht
  mehr fuer verifizierte Draft-Claims im finalen Skill-Catalog-Text
- ohne `list_draft_skills`-Evidence repariert der Safe-Fallback jetzt auf eine
  explizite Nicht-Verifikation statt Draft-Zustaende aus Registry-Signalen
  abzuleiten

Verifiziert:

- [tests/unit/test_skill_catalog_semantic_gap_suite.py](<repo-root>/tests/unit/test_skill_catalog_semantic_gap_suite.py)
- `pytest -q tests/unit/test_skill_catalog_semantic_gap_suite.py` -> `5 passed, 1 xfailed`
- `pytest -q tests/unit/test_output_grounding.py` -> `40 passed`

Offen bleibt aber:

- der Pfad landet weiterhin erst ueber
  `Postcheck: repaired:missing_runtime_section` in der sauberen Endantwort
- die Thinking-/Sequential-Trace driftet fuer diesen Pfad noch in generische,
  hypothetische Erklaerungen statt sich enger an den Runtime-/Tool-Befund zu
  halten

## Update 2026-04-04 spaeterer Recheck nach Output-/Hint-/Precontrol-Nachschaerfung

Nach Backend-Restart und erneutem Live-Test mit

- `Welche Draft-Skills gibt es gerade? Nenne die Draft-Skills explizit. Erklaere danach kurz, warum list_skills sie nicht anzeigt.`

zeigt der Pfad jetzt:

- `Tools` und `Exec Tools` bleiben korrekt bei
  `list_draft_skills`, `list_skills`
- die Endantwort bleibt sichtbar im strukturierten Skill-Catalog-Format:
  - `Runtime-Skills`
  - `Einordnung`
- `Postcheck` steht im finalen Trace jetzt auf `passed`
- in der sichtbaren Endantwort tauchen keine hypothetischen Draft-Beispiele
  mehr auf

Damit ist der fruehere Kernrestfehler
`repaired:missing_runtime_section` fuer den geprueften Null-Draft-Prompt
nicht mehr der primaere Live-Befund.

Offen bleibt jetzt enger:

- vor dem Frontend-Hard-Reload zeigte die sichtbare `Live Trace`-Box fuer
  diesen Draft-Pfad noch einen aelteren Thinking-Stand
- nach Hard-Reload zeigt die `Live Trace`-Box jetzt konsistent den finalen
  `trace_final`-Snapshot mit:
  - `needs_sequential_thinking=false`
  - `final_execution_tools`: `list_draft_skills`, `list_skills`
  - `skill_catalog_postcheck: passed`
- es fehlt weiterhin der Positivfall mit **echten** Draft-Skills

---

## Kurzbefund

### 1. Der Fehler sitzt nicht mehr im Routing

Der vorherige Live-Fail
`Welche Draft-Skills gibt es gerade?` -> Skill-Erstellungsflow
ist nicht mehr reproduziert.

Der Pfad bleibt jetzt korrekt bei:

- `skill_catalog_context`
- Read-only-Skill-Tools
- keiner Skill-Erstellung

### 2. Der Fehler sitzt im Output-Postcheck-/Repair-Pfad

Die Rohantwort verfehlt weiterhin das geforderte Antwortschema und wird deshalb
im Output-Postcheck repariert:

- Verletzungsgrund: `missing_runtime_section`
- anschliessend Safe-Repair auf Basis des Skill-Catalog-Fallbacks

Das ist **kein frueher Precheck-Fallback**, sondern ein **spaeter
Postcheck-Repair**.

### 3. Die Repair-Datenbasis fuer Drafts ist unvollstaendig

Der aktuelle Skill-Catalog-Safe-Repair liest Draft-Daten robust aus:

- `skill_registry_snapshot`

aber noch nicht gleichwertig aus:

- `list_draft_skills`

Dadurch entsteht aktuell diese Kette:

1. `list_draft_skills` wird korrekt ausgefuehrt
2. Trace zeigt die korrekte Execution
3. die Rohantwort driftet
4. der Postcheck ersetzt die Rohantwort
5. die Ersatzantwort kennt den Draft-Befund nicht vollstaendig
6. dadurch bleibt nur der Runtime-Nullbefund plus generische Einordnung sichtbar

---

## Technischer Befund

Relevant:

- Skill-Catalog-Postcheck und Repair in
  [core/layers/output.py](<repo-root>/core/layers/output.py)
- Skill-Catalog-Snapshot-Extraktion in
  [core/layers/output.py](<repo-root>/core/layers/output.py)
- Skill-Routing / final execution trace in
  [core/orchestrator.py](<repo-root>/core/orchestrator.py)

Konkret:

- `missing_runtime_section` triggert den Skill-Catalog-Repair
- der Repair baut die Antwort aus `_build_skill_catalog_safe_fallback(...)`
- die Snapshot-Extraktion fuellt `draft_count` / `draft_names` derzeit vor allem
  aus `skill_registry_snapshot`
- `list_draft_skills` ist als Execution-Signal vorhanden, aber noch nicht
  gleichwertig in die Repair-Snapshot-Logik eingespeist

---

## Einordnung

Der urspruengliche konkrete Blocker
`Draft-Evidence geht im Repair verloren`
ist fuer das aktuelle Null-Draft-Setup nicht mehr der primaere Restfehler.

Nicht mehr primaer offen:

- Routing fuer Draft-Inventar
- sichtbarer `[Grounding-Korrektur]`-Leak
- Trace-vs-Execution-Unsichtbarkeit
- Draft-Evidence aus `list_draft_skills` im Skill-Catalog-Repair

Jetzt primaer offen:

- es fehlt noch ein Gegencheck mit **tatsaechlich vorhandenen** Draft-Skills,
  um den Positivfall live zu bestaetigen

---

## Konsequenz fuer den Implementationsplan

Der gezielte Bugfix fuer den geprueften Null-Draft-Fall ist jetzt erfolgt.

Der naechste Schritt ist deshalb nicht mehr dieselbe Repair-Luecke, sondern:

- fruehen Skill-Catalog-Contract in Control/Orchestrator materialisieren:
  [[2026-04-04-skill-catalog-control-first-policy-contract-implementationsplan]]
- danach Positivfall mit echten Drafts explizit live oder fixture-basiert testen

Empfohlene Reihenfolge:

1. den neuen Control-first-Contract umsetzen
2. einen Positivfall mit verifizierten Draft-Skills herstellen
   (Fixture, temporaerer Draft oder dedizierter Testbestand)
3. danach kurzer erneuter Live-/UI-Gegencheck fuer:
   - Null-Draft-Fall
   - Positivfall mit echten Drafts
   - Erklaerung zu `list_skills`

---

## Erwartetes Zielbild

Fuer Draft-Inventarfragen muss die finale Antwort auch nach Repair sichtbar
enthalten:

- ob Draft-Skills verifiziert vorhanden sind
- wenn verfuegbar: welche Draft-Skills verifiziert sind
- warum `list_skills` sie nicht anzeigt

Nicht mehr zulaessig:

- `list_draft_skills` wird ausgefuehrt, aber in der finalen Antwort verschwindet
  der Draft-Befund
- Repair reduziert die Antwort auf Runtime-Nullbefund, obwohl Draft-Evidence
  verifiziert vorliegt
- die Rohantwort/Thinking-Trace erfindet hypothetische Draft-Skills oder
  generische Beispiele, obwohl der Runtime-Befund bereits eindeutig ist
