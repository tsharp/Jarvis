# Work Context Migration Matrix

Diese Datei dokumentiert die schrittweise Konsolidierung hin zu einem
gemeinsamen `work_context`.

Ziel ist nicht, moeglichst viel sofort umzuziehen, sondern Doppellogik
kontrolliert zu vermeiden.

## Zielbild

Es soll genau eine fachliche Wahrheit pro Conversation geben fuer:

- Thema
- letzter verifizierter Stand
- offene Blocker
- fehlende Fakten
- naechster sinnvoller Schritt
- relevante Capability-/Arbeitsparameter

Nicht alle heutigen Quellen verschwinden. Einige bleiben:

- Runtime-State
- Persistenz-/Transportkanaele
- Darstellungen fuer kompakte Modelle oder Chat-History

Die Regel ist:

**Eine Verantwortung, eine primaere Quelle.**

---

## Schrittprotokoll

### Schritt 1 — Quellen inventarisieren

**Gemacht**
- bestehende Zustandsquellen fuer Task-Loop-/Chat-Handoff geprueft
- erstes `core/work_context/`-Scaffold angelegt
- Verantwortungen fuer Runtime, Persistenz und Darstellung getrennt

**Ziel**
- vor jeder Implementierung sichtbar machen, welche Quelle spaeter
  Reader, Writer, Runtime-State oder Ersatz wird

### Schritt 2 — Migrationsmatrix festhalten

**Gemacht**
- die heutige Verteilung der Arbeitsdaten als Matrix dokumentiert
- fuer jede Quelle eine Migrationsrichtung notiert:
  `bleibt`, `reader`, `writer`, `wird ersetzt`, `darstellung`

**Ziel**
- beim naechsten Coding-Schritt keine parallelen Wahrheiten mehr erzeugen

### Schritt 3 — Ersten Contract festziehen

**Gemacht**
- `core/work_context/contracts.py` mit erstem typed Contract gefuellt
- `WorkContextStatus`, `WorkContextSource`, `WorkContextFact`,
  `WorkContext` und `WorkContextUpdate` eingefuehrt
- erste Vertragstests fuer Normalisierung und Serialisierung angelegt

**Ziel**
- ab jetzt einen stabilen Feldsatz zu haben, auf den Reader und Writer
  spaeter konkret hinarbeiten koennen

### Schritt 4 — Ersten Reader bauen

**Gemacht**
- `readers/task_loop.py` mit erstem Snapshot-Reader gefuellt
- Task-Loop-Snapshot -> `WorkContext` fuer aktive und terminale Faelle
  abgebildet
- terminale Loop-Verdichtung aus `unresolved_context.py` wiederverwendet
- Reader-Tests fuer `completed`, `waiting_for_user` und `None` angelegt

**Ziel**
- den ersten echten Uebersetzungspfad von bestehender Runtime in den
  gemeinsamen Arbeitskontext zu haben, ohne schon globale Verdrahtung
  einzubauen

### Schritt 5 — Workspace-Event-Reader bauen

**Gemacht**
- `readers/workspace_events.py` mit erstem Event-Reader gefuellt
- `task_loop_*`-Events in `WorkContext` ueberfuehrt
- die bestehende Task-Loop-Semantik aus `context_cleanup.py` fuer
  `topic`, `blocker` und `next_step` bewusst nachgezogen
- Reader-Tests fuer `task_loop_completed`, `task_loop_context_updated`,
  Event-Reihenfolge und irrelevante Events angelegt

**Ziel**
- denselben Arbeitszustand auch aus persistierten Events lesen zu koennen,
  damit `work_context` nicht nur am Runtime-Snapshot haengt

### Schritt 6 — Kleinen Load-/Merge-Service bauen

**Gemacht**
- `service.py` mit `load_work_context()` und `merge_work_context()` gefuellt
- Prioritaet festgelegt: zuerst Task-Loop-Snapshot, dann Workspace-Events
- fehlende Felder aus Events in den primaeren Snapshot-Kontext eingemischt
- erste Service-Tests fuer Merge, Snapshot+Events und Events-only angelegt

**Ziel**
- einen einzigen kleinen Einstiegspunkt zu haben, ueber den spaeter
  Orchestrator, Chat und Task-Loop denselben Arbeitskontext laden koennen

### Schritt 7 — Erste Selector-Helfer bauen

**Gemacht**
- `selectors.py` mit kleinen lesenden Helfern gefuellt
- `has_open_work_context()` erkennt jetzt auch terminale, aber noch
  fachlich offene Arbeitszustaende
- `visible_next_step()` liefert einen sichtbaren naechsten Schritt mit
  einfachem Fallback fuer Blocker und fehlende Fakten
- `should_explain_from_work_context()` und
  `should_execute_from_work_context()` spiegeln die bestehende
  Follow-up-Semantik deterministisch auf den neuen `WorkContext`
- erste Selector-Tests angelegt

**Ziel**
- den gemeinsamen Arbeitskontext zuerst sauber konsumierbar zu machen,
  bevor produktive Routing- oder Writer-Pfade daran angeschlossen werden

### Schritt 8 — `unresolved_context` auf `work_context`-Lesepfad vorbereiten

**Gemacht**
- die Follow-up-Marker aus `core/task_loop/unresolved_context.py` in
  `core/work_context/selectors.py` gezogen, damit `selectors` die
  allgemeine Leseschicht selbst besitzen
- `unresolved_context.py` liest jetzt fuer die Antwortbildung den
  sichtbaren naechsten Schritt ueber `work_context`-Selectoren statt nur
  ueber lokale Feldlogik
- kleiner Brueckentest fuer `unresolved_context -> work_context` angelegt

**Ziel**
- den ersten produktiven Konsum des neuen `work_context` im bestehenden
  Follow-up-Pfad zu erreichen, ohne den gesamten Task-Loop-Handoff schon
  umzubauen

### Schritt 9 — unresolved Handoff in `orchestrator_modules/task_loop.py` umstellen

**Gemacht**
- `_resolve_unresolved_followup(...)` liest jetzt zuerst den gemeinsamen
  `work_context` ueber `load_work_context(...)`
- die Entscheidung `erklaeren` vs. `neuen Loop seeden` laeuft dort nicht
  mehr direkt auf lokalen Marker-Helfern, sondern ueber
  `has_open_work_context()`,
  `should_explain_from_work_context()` und
  `should_execute_from_work_context()`
- der bestehende Nutzervertrag bleibt gleich: Antworttext und
  Loop-Seeding kommen weiterhin aus `unresolved_context.py`

**Ziel**
- den eigentlichen unresolved Follow-up-Handoff auf den gemeinsamen
  Arbeitskontext zu setzen, ohne auf einen Schlag den gesamten
  Task-Loop-Orchestrator umzubauen

### Schritt 10 — `context_cleanup.py` auf `work_context` lesen lassen

**Gemacht**
- die `task_loop_*`-Bridge in `core/context_cleanup.py` liest den
  Arbeitszustand jetzt zuerst ueber
  `build_work_context_from_workspace_events([event])`
- `TypedState.task_loop_*` wird damit nicht mehr primaer aus lokaler
  Event-Semantik befuellt, sondern aus derselben `work_context`-Projektion,
  die auch andere Handoff-Pfade verwenden
- die NOW/NEXT-Renderer selbst blieben bewusst unveraendert; sie bekommen
  nur ihre Daten jetzt aus der gemeinsamen Quelle

**Ziel**
- normalen Chat-Kontext und Task-Loop-Handoff auf dieselbe fachliche
  Quelle zu setzen, ohne die kompakte Darstellung oder Priorisierung
  schon umzubauen

### Schritt 11 — `context_manager.py` mit `work_context` einspeisen

**Gemacht**
- `ContextManager.build_small_model_context()` kann jetzt den aktuellen
  `work_context` als synthetisches `task_loop_context_updated`-Event ueber
  den bestehenden `extra_events`-Pfad einspeisen
- die Einspeisung greift nur, wenn fuer die Conversation noch keine
  `task_loop_*`-Events im geladenen Eventsatz liegen; so vermeiden wir
  doppelte Kontextprojektionen
- erster kleiner Writer in
  `core/work_context/writers/workspace_events.py` angelegt, der einen
  `WorkContext` in task-loop-kompatible Event-Form projiziert

**Ziel**
- auch der Compact-Context-Aggregator soll den gemeinsamen Arbeitszustand
  sehen koennen, selbst wenn dieser gerade nur im aktuellen Task-Loop-
  Snapshot vorhanden ist und noch nicht als persistiertes Event vorliegt

### Schritt 12 — `context_cleanup.py` auf minimalen Legacy-Fallback reduzieren

**Gemacht**
- die alte lokale Task-Loop-Semantik in `core/context_cleanup.py` wurde von
  mehreren spezialisierten `_task_loop_*`-Hilfsfunktionen auf einen kleinen
  `legacy_task_loop_projection`-Fallback reduziert
- der produktive Pfad bleibt unveraendert `work_context`-first ueber
  `build_work_context_from_workspace_events(...)`
- lokale Task-Loop-Interpretation in `context_cleanup.py` ist damit nicht
  mehr zweite Primaerlogik, sondern nur noch defensive Rueckfallebene

**Ziel**
- Doppellogik abbauen, ohne den sichtbaren `TASK_CONTEXT`/`NEXT`-Vertrag im
  normalen Chat zu veraendern

### Schritt 13 — terminale Task-Loop-Verdichtung zentralisieren

**Gemacht**
- die gemeinsame terminale Normalisierung liegt jetzt in
  `core/work_context/normalization.py`
- `core/work_context/readers/task_loop.py` und
  `core/task_loop/unresolved_context.py` nutzen fuer
  `verified_facts`, `missing_facts`, Status und den terminalen
  `WorkContext` jetzt dieselbe Normalisierung
- die fruehere doppelte `WorkContext`-Ableitung in
  `unresolved_context.py` wurde entfernt

**Ziel**
- genau eine gemeinsame terminale Verdichtung fuer den Task-Loop-Zustand zu
  haben, statt parallele Umsetzungen in Reader und unresolved-Follow-up-Pfad

### Schritt 14 — Reader von `unresolved_context` entkoppeln

**Gemacht**
- die Snapshot-zu-terminaler-Projektion liegt jetzt ebenfalls in
  `core/work_context/normalization.py`
- `core/work_context/readers/task_loop.py` liest terminale Snapshots nicht
  mehr ueber `core/task_loop/unresolved_context.py`, sondern direkt ueber die
  gemeinsame Normalisierung
- in `core/task_loop/unresolved_context.py` wurden mehrere technische
  Hilfsfunktionen entfernt; die Kompatibilitaetsschicht delegiert jetzt fuer
  terminale Projektion an die gemeinsame Normalisierung

**Ziel**
- einen weiteren Altpfad zu entfernen und die Abhaengigkeit
  `work_context -> task_loop.unresolved_context` fuer terminale Reader-Logik
  aufzulösen

### Schritt 15 — triviale Wrapper nach der Konsolidierung entfernen

**Gemacht**
- den reinen Durchreicher `_terminal_projection(...)` aus
  `core/work_context/readers/task_loop.py` entfernt
- den nur noch einmal genutzten Wrapper
  `build_terminal_task_loop_work_context_from_snapshot(...)` aus
  `core/work_context/normalization.py` entfernt
- der Reader nutzt jetzt direkt
  `build_terminal_task_loop_projection(...)` plus
  `build_terminal_task_loop_work_context(...)`

**Ziel**
- nach der groesseren Konsolidierung noch die letzten rein technischen
  Wrapper entfernen, ohne Fachverhalten zu aendern

### Schritt 16 — letzten Unresolved-Convenience-Wrapper entfernen

**Gemacht**
- `build_terminal_task_loop_work_context_from_unresolved(...)` aus
  `core/work_context/normalization.py` entfernt
- `core/task_loop/unresolved_context.py` ruft die gemeinsame terminale
  Normalisierung jetzt direkt mit den Feldern des `UnresolvedTaskContext`
  auf

**Ziel**
- den letzten reinen Convenience-Wrapper im terminalen Task-Loop-Pfad
  entfernen und die gemeinsame Normalisierung noch direkter nutzen

---

## Matrix

| Quelle | Enthält heute | Rolle heute | Zielrolle im `work_context` | Bemerkung |
|---|---|---|---|---|
| `core/task_loop/store.py` | `TaskLoopSnapshot` pro Conversation, inkl. laufender Runtime-State | In-Memory Runtime-State | **bleibt Runtime-State**, spaeter Reader | Nicht als langfristige fachliche Wahrheit benutzen |
| `core/task_loop/unresolved_context.py` | verdichteter terminaler Loop-Stand: `task_topic`, `blocker`, `next_step`, `capability_context`, `discovered_blueprints` | fachliche Verdichtung fuer Follow-up | **Reader / spaeter teilweise migrieren** | Sehr nah am Zielobjekt; Kandidat fuer spaetere Uebernahme nach `work_context/contracts.py` |
| `workspace_events` | sichtbare Loop-/Runtime-/Systemereignisse | Persistenz- und Transportkanal | **Writer + Reader** | Bleibt wichtig, soll aber nicht die Fachlogik selbst tragen |
| `core/context_cleanup.py` | mappt `task_loop_*` auf `TASK_CONTEXT`, `NEXT`, `open_issues`, `last_error` | kompakte Darstellung / Semantik-Mapping | **Darstellung + spaeter Reader aus `work_context`** | Sollte spaeter weniger eigene Task-Loop-Semantik halten |
| `core/context_manager.py` | laedt `workspace_event_list`, Protokolle, Rolling Summary und baut Small-Model-Context | Kontextaggregation | **bleibt Aggregator**, liest spaeter `work_context`-Projektionen | Nicht selbst primaere Arbeitswahrheit |
| `core/context_compressor.py` / Rolling Summary | freie Textzusammenfassung alter Sessions | Langzeitkompression / Darstellung | **Darstellung / Hilfsquelle**, kein primaerer Work-Context | Zu unstrukturiert als fachliche Autoritaet |
| `_container_capability_context` im Plan | `request_family`, `known_fields`, Python-/Container-Kontext | Task-/Control-Signal | **Input-Signal / Teil von `capability_context`** | Wertvoll, aber kein kompletter Arbeitskontext |
| `_unresolved_task_context` im Plan | verdichteter offener Kontext fuer Re-Entry | temporärer Follow-up-Hook | **Input-Signal / spaeter aus `work_context` ableiten** | Sollte nicht als alleinige Parallelwelt wachsen |
| `TypedState.task_loop_*` in `context_cleanup.py` | `task_loop_topic`, `state`, `next_step`, `blocker` | kompakte Zwischenrepräsentation | **Darstellung / Reader-Ziel** | Gute Projektion, aber nicht primaere Domain-Quelle |
| `compact context` (`NOW/RULES/NEXT`) | verdichtete Anzeige fuer kleine Modelle | Darstellung | **Darstellung** | Soll spaeter aus `work_context` gespeist werden |
| Chat-History / Protokoll | freie Nutzer- und Assistentenformulierung | Verlauf / Referenz | **Darstellung / Kontext**, kein primaerer State | Nützlich fuer Rekonstruktion, aber nicht autoritativ |

---

## Vorlaeufige Verantwortungsgrenzen

### Bleibt vorerst wie es ist

- `TaskLoopStore` fuer aktive Runtime-Snapshots
- `workspace_events` als sichtbarer Persistenzkanal
- `context_cleanup` / `compact context` als Darstellung fuer kleine Modelle
- Rolling Summary als Langzeitkompression

### Soll spaeter Reader fuer `work_context` werden

- terminale Loop-Verdichtung aus `unresolved_context.py`
- `workspace_events`-basierte Task-Loop-Hinweise
- kompakte Task-/Blocker-Projektion aus `context_cleanup`

### Soll spaeter Writer fuer `work_context` werden

- Projektion zurueck in `workspace_events`
- menschenlesbare Kurzzeile fuer Chat-/Memory-Pfade
- optional Rueckprojektion in Task-Loop-Schritte / Snapshots

### Soll nicht als primaere Wahrheit wachsen

- Rolling Summary
- freie Chat-History
- isolierte Plan-Felder wie `_unresolved_task_context`

---

## Erste Migrationsregel

Ab jetzt gilt fuer neue Logik:

1. kein neuer fachlicher Zustand nur in freiem Chat-Text
2. kein neuer dauerhafter Zustand nur im `TaskLoopStore`
3. kein Ausbau von `context_cleanup` zur zweiten Domain-Engine
4. neue Handoff-Logik moeglichst in `core/work_context/` vorbereiten

---

## Empfohlene naechste Schritte

1. `contracts.py`
   Exakte Felder fuer `WorkContext` und evtl. `WorkContextUpdate`.

2. `readers/task_loop.py`
   Terminale Loop-Zustaende in einen ersten `WorkContext` mappen.

3. `readers/workspace_events.py`
   Gespiegelte/verdichtete Event-Hinweise einlesen.

4. `writers/workspace_events.py`
   Eine klare sichtbare Projektion definieren, statt mehrere implizite.
