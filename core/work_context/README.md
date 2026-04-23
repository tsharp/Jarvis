# Work Context Architecture

Dieses Package ist das geplante Geruest fuer einen gemeinsamen
Arbeitskontext zwischen:

- normalem Chat-Flow
- Task-Loop
- spaeteren Re-Entry-/Follow-up-Pfaden

## Ziel

Der Arbeitskontext soll die **fachliche Wahrheit pro Conversation** tragen,
nicht die reine Runtime eines einzelnen Task-Loops.

Gemeint ist ein kompakter, strukturierter Zustand wie:

- `topic`
- `status`
- `verified_facts`
- `open_blockers`
- `missing_facts`
- `next_step`
- `capability_context`
- `last_step`

Damit gilt spaeter:

- `Control` entscheidet nur den Modus
- `Task-Loop` fuehrt aus
- `Chat` kann denselben Zustand erklaeren oder wieder aufnehmen

## Noch nicht aktiv

Dieses Package ist aktuell **nur ein Scaffold**.

Es ist noch nicht in den produktiven Orchestrator verdrahtet und ersetzt
noch keine bestehende Runtime-Quelle wie:

- `TaskLoopStore`
- `workspace_events`
- `compact context`
- `rolling summary`

## Aktueller Stand

Stand dieser Doku: **2026-04-22**

Bereits umgesetzt:

- `contracts.py`
  Erster typed Contract fuer den gemeinsamen Arbeitskontext:
  `WorkContext`, `WorkContextFact`, `WorkContextStatus`,
  `WorkContextSource`, `WorkContextUpdate`

- `readers/task_loop.py`
  Erster Reader von `TaskLoopSnapshot` nach `WorkContext`

- `readers/workspace_events.py`
  Zweiter Reader von `task_loop_*`-Events nach `WorkContext`

- `service.py`
  Kleiner Load-/Merge-Einstiegspunkt:
  `load_work_context(...)` priorisiert aktuell
  `TaskLoopSnapshot -> workspace_events`

- `selectors.py`
  Kleine lesende Helfer fuer offene Arbeitskontexte und fuer die
  Unterscheidung `erklaeren` vs. `ausfuehren` auf Basis des
  gemeinsamen Zustands

- erste produktive Nutzung im bestehenden Follow-up-Pfad
  `core/task_loop/unresolved_context.py` nutzt jetzt `work_context`
  bereits lesend fuer sichtbaren naechsten Schritt und Follow-up-Marker

- unresolved Follow-up-Handoff in
  `core/orchestrator_modules/task_loop.py`
  liest jetzt den gemeinsamen `work_context`, bevor er zwischen
  `erklaeren` und `Loop-Reentry` entscheidet

- `core/context_cleanup.py`
  liest `task_loop_*`-Events jetzt zuerst als `work_context` ein und
  speist daraus den kompakten `TASK_CONTEXT`/`NEXT`-Pfad fuer den
  normalen Chat

- `core/context_manager.py`
  kann den aktuellen `work_context` jetzt als synthetisches
  `task_loop_context_updated`-Event in den bestehenden Compact-Context-
  Pfad einspeisen, wenn noch keine `task_loop_*`-Events geladen wurden

- `core/context_cleanup.py`
  traegt fuer Task-Loop-Kontext jetzt nur noch einen kleinen Legacy-Fallback;
  die primaere fachliche Interpretation laeuft dort ueber `work_context`

- `core/work_context/normalization.py`
  enthaelt jetzt die gemeinsame terminale Normalisierung fuer Task-Loop-
  Zustaende, die sowohl vom `task_loop`-Reader als auch vom
  unresolved-Follow-up-Pfad genutzt wird

- `core/work_context/readers/task_loop.py`
  haengt fuer terminale Snapshots nicht mehr an
  `core/task_loop/unresolved_context.py`, sondern direkt an der gemeinsamen
  Normalisierung

- nach der Konsolidierung wurden auch triviale Snapshot-Wrapper entfernt;
  Reader nutzen die gemeinsame terminale Normalisierung jetzt direkt

- auch der Unresolved-Follow-up-Pfad ruft die gemeinsame terminale
  Normalisierung jetzt direkt auf; ein weiterer Convenience-Wrapper wurde
  entfernt

Aktuell bewusst **noch nicht** umgesetzt:

- globale Orchestrator-Verdrahtung
- Writers zurueck nach `workspace_events` / Chat-Memory
- Ersatz bestehender Pfade wie `unresolved_context` oder `context_cleanup`

Das heisst:

- die neue Struktur ist vorbereitet
- Contracts und erste Reader existieren
- aber der produktive Chat-/Task-Loop-Fluss nutzt `work_context` noch nicht als
  erste Autoritaet

## Geplante Rollen

- `contracts.py`
  Typen und shape des gemeinsamen Arbeitskontexts.

- `normalization.py`
  Verdichtung und Normalisierung von Rohsignalen in einen stabilen
  Arbeitszustand.

- `selectors.py`
  Kleine Leser fuer haeufige Fragen wie:
  `gibt es offenen Kontext?`, `ist Re-Entry moeglich?`,
  `welcher naechste Schritt ist sichtbar?`

- `service.py`
  Spaeterer zentrale Merge-/Load-/Update-Punkt fuer den Work Context.

- `readers/`
  Adapter, die bestehenden Zustand aus Task-Loop, Workspace und anderen
  Quellen einlesen.

- `writers/`
  Adapter, die den verdichteten Zustand wieder in sichtbare Kanaele
  schreiben.

## Beabsichtigte Architekturregel

Nicht mehrere konkurrierende Wahrheiten:

- Task-Loop-intern
- Chat-intern
- Summary-intern

Sondern:

**ein gemeinsamer fachlicher Arbeitskontext, mehrere Leser und mehrere
Darstellungen.**

## Naechster Schritt

Wenn das Geruest passt, koennen wir als Naechstes entscheiden:

1. exakte Contract-Felder in `contracts.py`
2. erste Reader-Reihenfolge
3. erste Writer-Ziele
4. welche bestehende Quelle vorerst autoritativ sein soll

## Naechster sinnvoller Schritt

Der naechste logische Block ist jetzt:

- den produktiven Konsum ausweiten

Konkret:

- weitere bestehende Follow-up-/Routing-Pfade schrittweise auf
  `work_context + selectors` lesen lassen
- danach entweder den naechsten kleinen Aggregationspfad
  (`context_manager.py` / compact context) anschliessen oder erste
  Writer vorbereiten
- erst danach Writer und produktive Rueckprojektionen bauen

Der naechste logische Block danach waere:

- diese Projektion gezielt fuer weitere Rueckkanäle zu verwenden
  oder die ersten echten Writer-Pfade kontrolliert produktiv zu machen

Warum diese Reihenfolge:

- erst den gemeinsamen Zustand **lesen**
- dann in Chat-/Task-Loop-Routing **verwenden**
- erst danach Writer und produktive Verdrahtung bauen

So vermeiden wir, dass neue Zustandsprojektionen entstehen, bevor klar ist,
wie der Zustand spaeter konsumiert wird.

## Migrationsnotiz

Die aktuelle Quellen-/Verantwortungsmatrix steht in:

- [MIGRATION.md](/home/danny/Jarvis/core/work_context/MIGRATION.md)

Dort wird nach jedem Architektur-Schritt festgehalten:

- was gemacht wurde
- welches Ziel der Schritt hatte
- welche bestehende Quelle spaeter bleibt, Reader, Writer oder Ersatz wird
