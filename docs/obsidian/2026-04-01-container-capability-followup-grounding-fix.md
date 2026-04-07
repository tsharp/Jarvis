# Active-Container-Capability-Follow-up - Blueprint-/Addon-Grounding im normalen Chatpfad

Erstellt am: 2026-04-01
Zuletzt aktualisiert: 2026-04-01
Status: **Fix umgesetzt**
Bezieht sich auf:

- [[2026-04-01-container-capability-followup-grounding-analyse]] - Root-Cause-Analyse des Capability-Drifts
- [[2026-04-01-control-authority-drift-approved-fallback-container-requests]] - vorheriger Fix fuer Start-/Clarification-Drift
- [[2026-04-02-thinking-strategy-authority-and-frontend-visibility-implementationsplan]] - Folgeplan fuer Thinking als Strategie-Layer und UI-Sichtbarkeit
- [[2026-04-01-trion-home-container-addons]] - vorhandenes `trion-home`-Addon-Wissen
- [[04-Container-Addons]] - Zielbild fuer Blueprint-spezifisches Containerwissen

---

## Anlass

Nach dem Fix fuer den Startpfad blieb ein separater Fehler im normalen Chat bestehen:

- `was kannst du in diesem container alles tun?`

wurde weiterhin wie eine generische Runtime-Abfrage behandelt.
Der Pfad endete in:

- `container_stats`
- `exec_in_container` mit `echo 'Container ready'`

dadurch entstand vor dem Output-Grounding weiter eine inhaltliche Luecke.

---

## Ziel des Fixes

Deiktische Follow-ups ueber den **aktiven Container** sollen im normalen Chatpfad:

1. zuerst auf den bekannten aktiven Container aufgeloest werden,
2. dann ueber `container_inspect` die reale Container-Identitaet verifizieren,
3. anschliessend Blueprint-/Addon-Wissen ueber `container_addons` einspeisen,
4. und daraus **Grounding-Evidence plus Prompt-Kontext** erzeugen,

statt generische Linux-Annahmen spaeter per `[Grounding-Korrektur]` flicken zu muessen.

---

## Umgesetzte Aenderungen

### 1. Deiktische Capability-Queries werden jetzt explizit erkannt

In [core/orchestrator.py](<repo-root>/core/orchestrator.py#L488) wurden Marker fuer:

- deiktische Referenzen wie `diesem container`, `in diesem container`, `this container`
- Capability-Intents wie `was kannst du`, `welche tools`, `was ist hier installiert`
- sowie Ausschlussmarker fuer Start/Stop/Status/Logs

erganzt.

Die neue Erkennung laeuft ueber:

- [_is_active_container_capability_query()](<repo-root>/core/orchestrator.py#L2876)

und prueft zusaetzlich, ob im Conversation-Container-State ueberhaupt ein aktiver Zielcontainer vorhanden ist.

### 2. Tool-Routing geht fuer diesen Fragetyp nicht mehr in `exec_in_container`/`container_stats`

In [core/orchestrator.py](<repo-root>/core/orchestrator.py#L2659) wird nach dem bestehenden Home-Override jetzt ein zweiter Override ausgefuehrt:

- [_prioritize_active_container_capability_tools()](<repo-root>/core/orchestrator.py#L2888)

Dieser ersetzt fuer aktive Capability-Follow-ups den schwachen generischen Pfad durch:

- `container_inspect`

und entfernt dabei gezielt:

- `exec_in_container`
- `container_stats`
- `container_list`
- `query_skill_knowledge`

wenn diese nur als generische Fallback-Tools aufgetaucht waeren.

Wirkung:

- der Resolver fragt nicht mehr blind generische Runtime-Probes ab,
- sondern startet mit der Identitaet des laufenden Containers.

### 3. Der normale Chatpfad baut jetzt explizit Addon-Kontext fuer aktive Container

Der neue Resolver sitzt in:

- [_maybe_build_active_container_capability_context()](<repo-root>/core/orchestrator.py#L3014)

Er macht fuer den aktuellen Turn:

1. Container-ID aus dem Conversation-State aufloesen
2. `container_inspect` gegen den aktiven Container ausfuehren
3. `blueprint_id`, `image` und abgeleitete Tags aus dem Inspect-Ergebnis extrahieren
4. `load_container_addon_context()` mit der aktuellen Userfrage aufrufen
5. daraus strukturierten Zusatzkontext und Grounding-Evidence erzeugen

Die fuer Addons abgeleiteten Tags kommen aus:

- [_derive_container_addon_tags_from_inspect()](<repo-root>/core/orchestrator.py#L2954)

Die komprimierte Runtime-/Identity-Zusammenfassung kommt aus:

- [_summarize_container_inspect_for_capability_context()](<repo-root>/core/orchestrator.py#L2969)

### 4. Sync- und Stream-Pfad bekommen denselben Zusatzkontext

Der gebaute Capability-Kontext wird jetzt vor dem Output in beide Pfade injiziert:

- Sync: [core/orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py#L463)
- Stream: [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py#L1827)

Dabei passieren zwei Dinge parallel:

- `context_text` wird als `active_container_ctx` in den Output-Kontext aufgenommen
- `tool_results_text` wird in die Runtime-Tool-Results gehaengt

Dadurch landet der neue Wissensblock:

- im Prompt des Output-Layers
- und zugleich in der Grounding-/Observability-Schiene

### 5. Der Output-Guard bekommt echte Evidence statt nur spaeter Reparaturbedarf

Der Resolver schreibt zusaetzlich `grounding_evidence` fuer:

- `container_inspect`
- `container_addons`

ueber:

- [set_runtime_grounding_evidence()](<repo-root>/core/orchestrator.py#L3153)

Damit hat der Output-Precheck fuer diesen Turn jetzt belastbare, extrahierbare Fakten ueber:

- Container-Identitaet
- Blueprint
- Image
- relevante Addon-Dokumente
- Blueprint-spezifische Capability-Hinweise

Der Guard muss also nicht mehr erst nach frei formulierten generischen Aussagen sichtbar reparieren.

---

## Verhalten nach dem Fix

Die Frage:

- `was kannst du in diesem container alles tun?`

wird jetzt als **active-container capability resolution path** behandelt:

1. aktiven Container aus Conversation-State bestimmen
2. `container_inspect` ausfuehren
3. `container_addons` fuer Blueprint/Image/Frage laden
4. diesen Block als Prompt-Kontext und Grounding-Evidence verwenden
5. erst danach natuerliche Antwort formulieren

Fuer `trion-home` bedeutet das insbesondere:

- kein freies Alpine-/Shell-Sandbox-Raten mehr
- sondern Priorisierung von `python:3.12-slim`, persistentem Workspace und den dokumentierten Tool-/Runtime-Grenzen aus dem Profil

---

## Geaenderte Dateien

- [core/orchestrator.py](<repo-root>/core/orchestrator.py)
- [core/orchestrator_sync_flow_utils.py](<repo-root>/core/orchestrator_sync_flow_utils.py)
- [core/orchestrator_stream_flow_utils.py](<repo-root>/core/orchestrator_stream_flow_utils.py)
- [tests/unit/test_orchestrator_runtime_safeguards.py](<repo-root>/tests/unit/test_orchestrator_runtime_safeguards.py)

---

## Tests

Neu abgesichert wurden insbesondere:

- aktives Capability-Follow-up routed auf `container_inspect` statt `container_stats`/`exec_in_container`:
  [tests/unit/test_orchestrator_runtime_safeguards.py#L188](<repo-root>/tests/unit/test_orchestrator_runtime_safeguards.py#L188)
- Addon-Kontext erzeugt zusaetzliche Grounding-Evidence fuer `container_inspect` und `container_addons`:
  [tests/unit/test_orchestrator_runtime_safeguards.py#L319](<repo-root>/tests/unit/test_orchestrator_runtime_safeguards.py#L319)

Lokal verifiziert mit:

- `python -m py_compile core/orchestrator.py core/orchestrator_sync_flow_utils.py core/orchestrator_stream_flow_utils.py tests/unit/test_orchestrator_runtime_safeguards.py`
- `pytest -q tests/unit/test_orchestrator_domain_routing_policy.py -q`
- `pytest -q tests/unit/test_orchestrator_runtime_safeguards.py -k 'active_container_capability or prioritizes_active_container_capability_strategy or prioritizes_home_container_strategy'`

Hinweis:

- kein Vollsuite-Lauf in dieser Doku-Iteration

---

## Architekturwirkung

Der Fix schliesst keinen weiteren Control-Drift, sondern einen separaten Contract-Gap:

- normale Chat-Antworten ueber **laufende** Container sind jetzt blueprint-aware,
- `container_addons` sind nicht mehr nur Commander-/Shell-Wissen,
- sondern Teil des normalen Capability-Reply-Pfads,
- und Sync/Stream verhalten sich dabei identisch.
