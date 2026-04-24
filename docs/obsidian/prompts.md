# Zentralisierung des Prompt-Managements

## Ziel

Das eigentliche Problem ist nicht ein einzelner schlechter Prompt, sondern dass viele Prompt-Texte und harte Antwortregeln aktuell ueber den Code verstreut sind.

Heute liegen Formulierungen, Stilvorgaben, Contracts und Task-Loop-Hinweise in vielen Dateien als harte Python-Strings vor:

- `parts.append("...")`
- Inline-Listen mit Regeln
- grosse System-Prompt-Konstanten
- verstreute Recovery-/Fallback-/Status-Texte

Das fuehrt zu vier konkreten Problemen:

1. Aenderungen am Ton oder an Regeln muessen an vielen Stellen parallel gemacht werden.
2. Prompt-Verhalten driftet zwischen Layern und Sonderpfaden auseinander.
3. Es ist schwer zu sehen, welche Formulierung aktuell wirklich die Source of Truth ist.
4. Kleine Text-Fixes enden schnell in inkonsistenten Teil-Patches statt in einem klaren Prompt-System.

Das Ziel dieser Arbeit ist deshalb:

- Hardcoded Prompt-Texte zentral sammeln
- Prompt-Text von Ausfuehrungslogik trennen
- eine klare Source of Truth fuer Formulierungen schaffen
- Textanpassungen kuenftig an einer Stelle pflegbar machen

Nicht das Ziel:

- Control-, Orchestrator- oder Policy-Logik in Templates zu verschieben
- Entscheidungslogik in Markdown zu verstecken
- die komplette Architektur in einem Schritt umzubauen

## Zielbild

Alle relevanten Prompt-Texte werden an einer zentralen Stelle abgelegt und von dort geladen.

Der Code soll dann moeglichst nur noch:

- den passenden Prompt auswaehlen
- Variablen injizieren
- den gerenderten Text an den bestehenden Flow uebergeben

Die inhaltliche Entscheidung bleibt im Code.
Die Formulierung wandert in zentrale Prompt-Dateien.

## Zielarchitektur

Die Zielarchitektur trennt sauber zwischen Text, Rendering und Verhalten.

### 1. Prompt-Dateien als Source of Truth

Unter `intelligence_modules/prompts/` liegen die eigentlichen Prompt-Texte.

Dort liegen:

- Layer-Prompts
- textuelle Contracts
- Task-Loop-Formulierungen
- Persona- und Stilbausteine

Dort liegt nicht:

- Routing-Logik
- Policy-Logik
- Layer-Entscheidungslogik
- Orchestrator-Verhalten

### 2. Prompt Loader als zentrale Leseschicht

Der Loader ist die einzige technische Stelle, die Prompt-Dateien direkt liest und rendert.

Seine Verantwortung:

- Frontmatter lesen
- Prompt-Text laden
- Variablen einsetzen
- Rendering-Fehler klar melden

Der Loader soll keine Logik uebernehmen, welcher Prompt fachlich richtig ist.
Er ist nur Infrastruktur.

### 3. Code entscheidet, Prompt-Dateien formulieren

Die aufrufenden Module entscheiden weiterhin:

- welcher Prompt benoetigt wird
- welche Variablen uebergeben werden
- wann welcher Contract gilt
- welcher Layer welchen Text bekommt

Die Prompt-Datei entscheidet nur:

- wie etwas formuliert ist
- welche statischen Regeln oder Textbausteine mitgegeben werden

Faustregel:

- Auswahl und Verhalten im Code
- Wortlaut im Prompt-System

### 4. Schmale Integrationspunkte pro Layer

Jeder betroffene Layer soll moeglichst ueber wenige Integrationspunkte an das Prompt-System angebunden sein.

Beispiel Zielzustand:

- Output Layer hat wenige Builder/Resolver, die zentrale Prompt-Dateien laden
- Task-Loop hat klar benannte Text-Bausteine fuer Status, Recovery und Rueckfragen
- Thinking und Control laden spaeter ihre grossen System-Prompts ebenfalls zentral

Nicht das Ziel ist, ueberall im Code kleine Einzel-Loads zu verstreuen.
Die zentrale Bueendelung soll auch im Code sichtbar bleiben.

### 5. Deterministisches Verhalten

Der Umstieg auf zentrale Prompt-Dateien darf Formulierungen aendern, aber nicht still Verhalten verbiegen.

Deshalb gilt fuer die Zielarchitektur:

- Prompt-Dateien beeinflussen Text
- Policy-Dateien beeinflussen Verhalten
- Control entscheidet Freigaben
- Orchestrator entscheidet Ausfuehrungsfluss
- Output formuliert das Endergebnis

Wenn eine Aenderung nur durch einen Prompt-Text eine fachliche Entscheidung verschiebt, ist das ein Architekturfehler.

## Vorschlag fuer die Struktur

### [NEW] `intelligence_modules/prompts/`

- `layers/`
  Enthält die grossen Layer-Prompts wie Thinking, Control und Output.
- `contracts/`
  Enthält textuelle Contracts fuer Output-/Antwortregeln.
- `task_loop/`
  Enthält Task-Loop-spezifische Hinweistexte, Recovery-Texte und Schrittformulierungen.
- `personas/`
  Enthält Stil- und Rollenbausteine.

Beispiel:

```md
---
scope: container_contract
target: output_layer
variables: ["required_tools", "truth_mode"]
---

Containerantworten muessen Runtime-Inventar, Blueprint-Katalog und Session-Binding sichtbar getrennt halten.

Verbindlicher Container-Contract fuer diesen Turn: Aussagen nur auf {required_tools} stuetzen.
truth_mode fuer diesen Turn: {truth_mode}.
```

## Prompt Loader

### [NEW] `intelligence_modules/prompt_manager/loader.py`

Der Loader soll bewusst klein und deterministisch bleiben.

Er soll:

- Frontmatter parsen
- Prompt-Body laden
- Variablen injizieren
- bei fehlenden Variablen oder kaputtem Frontmatter klar fehlschlagen

Ziel-API:

```python
load_prompt(category: str, template_name: str, **kwargs) -> str
```

Wichtige Randbedingungen fuer Phase 1:

- kein `jinja2`
- kein Template-Branching
- keine versteckte Logik im Prompt
- nur einfache Platzhalter wie `{required_tools}`

Fuer den Anfang reicht bewusst simples Python-Formatting.
Wenn spaeter echte Template-Komplexitaet noetig ist, kann das separat entschieden werden.

## Umsetzungsstrategie

### Phase 1: Output Layer als Proof of Concept

Wir starten dort, wo der Nutzen hoch und das Risiko kontrollierbar ist:

- `core/layers/output/layer.py`
- `core/layers/output/contracts/container.py`
- optional danach `core/layers/output/prompt/system_prompt.py`

In dieser Phase geht es nicht darum, das ganze System sofort umzubauen.
Es geht darum zu beweisen, dass zentrale Prompt-Dateien sauber funktionieren und der Code dadurch einfacher wird.

### Phase 2: Task-Loop-Texte nachziehen

Wenn der Output-Layer sauber funktioniert, ziehen wir die verteilten Task-Loop-Texte nach:

- `core/task_loop/step_runtime/prompting.py`
- `core/task_loop/step_answers.py`
- `core/task_loop/runner/messages.py`
- `core/task_loop/capabilities/container/parameter_policy.py`

### Phase 3: Grosse Layer-Prompts

Erst danach folgen die grossen System-Prompts:

- `core/layers/thinking.py`
- `core/layers/control/prompting/constants.py`
- `core/persona.py`

Diese Phase spaeter anzugehen ist wichtig, weil dort der Umbau tiefer in bestehende Flows eingreift.

## Was explizit im Code bleiben muss

Diese Dinge sollen nicht in Prompt-Dateien verschoben werden:

- Tool- oder Layer-Entscheidungen
- Recovery-/Routing-Logik
- Policy-Gates
- Control-Entscheidungen
- Orchestrator-Rewrites
- echte Conditionals mit Verhaltenswirkung

Faustregel:

- Text und Formulierung nach `prompts/`
- Verhalten und Entscheidung im Python-Code

## Erste Zielliste

Die folgenden Dateien enthalten aktuell harte Prompt-Texte oder stark verteilte Formulierungen und sind mittelfristig Kandidaten fuer die Zentralisierung:

### Output

- `core/layers/output/layer.py`
- `core/layers/output/prompt/system_prompt.py`
- `core/layers/output/contracts/container.py`
- `core/layers/output/contracts/skill_catalog/evaluation.py`

### Task Loop

- `core/task_loop/step_runtime/prompting.py`
- `core/task_loop/step_answers.py`
- `core/task_loop/runner/messages.py`
- `core/task_loop/capabilities/container/parameter_policy.py`

### Spaeter

- `core/layers/thinking.py`
- `core/layers/control/prompting/constants.py`
- `core/persona.py`
- `core/context_compressor.py`

## Verification

### Automated

- Loader-Unit-Tests fuer Frontmatter, Platzhalter und Fehlerfaelle
- Snapshot-Tests fuer gerenderte Prompt-Texte
- bestehende Layer-/Output-Tests weiterlaufen lassen

### Manual

- gezielte Testanfragen an Output- und Task-Loop-Pfade
- pruefen, ob die Formulierung weiterhin korrekt ist
- pruefen, ob sich nur Text aendert und nicht unbeabsichtigt Verhalten

## Ergebnis, das wir erreichen wollen

Am Ende soll nicht mehr unklar sein, welcher Prompt an welcher Stelle gilt.

Statt vieler verstreuter Hardcoded-Strings soll es ein zentrales Prompt-System geben, das:

- einfacher wartbar ist
- Ton und Regeln konsistent haelt
- neue Textanpassungen billiger macht
- Architektur-Drift durch verstreute Formulierungen reduziert
