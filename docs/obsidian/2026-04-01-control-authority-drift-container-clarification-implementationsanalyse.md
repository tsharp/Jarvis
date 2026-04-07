# Control-Authority-Drift bei Container-Requests - Clarification-/Allowlist-Implementationsanalyse

Erstellt am: 2026-04-01
Zuletzt aktualisiert: 2026-04-01
Status: **Analyse**
Bezieht sich auf:

- [[2026-04-01-control-authority-drift-approved-fallback-container-requests]] - bisherige DCS zum generischen Fallback
- [[2026-04-01-control-authority-drift-container-clarification-implementationsplan]] - geplanter generischer Fixpfad
- [[2026-03-31-control-layer-audit]] - Sollbild: Control als bindende Policy-Autoritaet
- [[2026-03-30-drift-testsuite-implementationsplan]] - Drift-Invarianten
- [[2026-04-01-trion-home-container-addons]] - Beispielkontext TRION Home
- [[2026-03-22-container-commander-trion/05-Open-Issues-Next-Steps]] - offener Home-Fast-Path

---

## Anlass

Live-Symptom weiterhin:

- User: `starte einmal bitte: TRION Home Workspace`
- Thinking: `suggested_tools=["request_container"]`
- UI: `Control Layer: Approved`
- finale Antwort:

> Ich habe aktuell keinen verifizierten Tool-Nachweis fuer eine belastbare Faktenantwort. Bitte Tool-Abfrage erneut ausfuehren.

Ziel dieser Analyse ist **kein TRION-Home-Hotfix**, sondern eine generische und stabile Korrektur fuer:

- alle aktuellen Blueprint-Requests
- zukuenftige Container-Blueprints
- Sync- und Stream-Pfad

---

## Kurzfazit

Ja: Es existieren weiterhin nachgelagerte Schichten, die den praktisch wirksamen Control-Entscheid entwerten.

Der Befund ist inzwischen **zweiteilig**:

1. `needs_clarification` ist ein legitimer interaktiver Laufzeitzustand, wird vom Output-Grounding aber weiterhin indirekt in `missing_evidence_fallback` transformiert.
2. Die von Control bereits reconcilierten Tool-Rechte und Tool-Vorschlaege werden spaeter wieder aufgeweicht:
   - `suggested_tools` werden gemerged statt autoritativ ersetzt
   - `tools_allowed` wird in Sync und Stream spaeter nochmals mit `decide_tools().keys()` ueberschrieben

Damit ist `Control` noch nicht die einzige wirksame Autoritaet.

---

## Bestaetigte Befunde

### 1. `needs_clarification` faellt im Output-Layer in den generischen Evidence-Fallback

Im Stream-Pfad wird der Suggest-/Clarification-Fall explizit als:

- `status="needs_clarification"`

geschrieben, plus einer nutzerfaehigen Rueckfrage im `tool_context`.

Das war als Soft-Guidance gedacht und **nicht** als Tech-Failure.

Der Output-Precheck behandelt aber nur diese Sonderfaelle als pass-through:

- `_blueprint_gate_blocked`
- `pending_approval`
- `routing_block`

`needs_clarification` ist dort **nicht** enthalten. Wenn gleichzeitig:

- `suggested_tools` gesetzt sind
- der Turn nicht conversational ist
- keine `ok`-Evidence vorliegt

dann geht der Pfad auf:

- `blocked_reason="missing_evidence"`
- `mode="missing_evidence_fallback"`

Das wurde lokal reproduziert mit einem Minimalfall:

- `suggested_tools=["request_container"]`
- grounding evidence: `status="needs_clarification"`

Ergebnis:

- generischer Fallback-Text

Wichtig:

- Das ist **kein TRION-Home-spezifisches Problem**
- jeder kuenftige Container-Request mit Clarification-/Suggest-Zustand ist betroffen

### 2. `apply_corrections()` behaelt alte Tool-Vorschlaege, statt den korrigierten Satz autoritativ zu machen

Der Control-Layer setzt fuer Clarification-/No-Match-Faelle bereits:

- `verification["suggested_tools"] = ["blueprint_list"]`

`apply_corrections()` merged das aber mit dem Thinking-Satz:

- alt: `["request_container"]`
- neu: `["blueprint_list"]`
- Ergebnis: `["blueprint_list", "request_container"]`

Dadurch bleibt genau das Tool weiter im Plan, das Control fuer diesen Turn eigentlich nicht mehr frei ausfuehren lassen wollte.

Das ist ein struktureller Contract-Bruch:

- Control korrigiert den erlaubten Interaktionsmodus
- der Plan behaelt den alten Action-Intent trotzdem bei

### 3. Reconciled `tools_allowed` wird spaeter wieder entwertet

`control_decision_from_plan()` reconciled bereits korrekt:

- bei `_blueprint_gate_blocked=True`
- und `approved=True`

wird `request_container` aus `tools_allowed` entfernt oder zu `decision_class="routing_block"` degradiert.

Das Problem:

- Sync: `control_decision = control_decision.with_tools_allowed(_ctrl_decisions_sync.keys())`
- Stream: `control_decision = control_decision.with_tools_allowed(_control_tool_decisions.keys())`

Wenn `decide_tools()` leer ist, wird aus einem zuvor korrekt reconcilierten:

- `tools_allowed=["blueprint_list"]`

wieder:

- `tools_allowed=[]`

Leere Allowlist bedeutet spaeter effektiv:

- kein wirksamer Filter mehr

Dadurch kann `request_container` aus dem gemergten `suggested_tools`-Satz wieder durchrutschen.

Das ist kein einzelner UI-Bug, sondern eine echte Aufweichung der Control-Autoritaet in beiden Laufzeitpfaden.

### 4. Der Stream-Control-Event verliert `decision_class`

Das Frontend kann `warn` / `routing_block` / `hard_block` nur rendern, wenn der Stream-Event diese Daten auch liefert.

Aktuell sendet der Stream-Control-Event nur:

- `approved`
- `skipped`

Nicht aber:

- `decision_class`
- `reason`
- `warnings`
- `tools_allowed`

Folge:

- die UI faellt auf `approved ? "allow" : "hard_block"` zurueck
- ein `warn` oder spaeterer Gate-Zustand kann visuell weiter als `Approved` erscheinen

Das ist observability drift:

- nicht die Ursache des Fallbacks
- aber ein staerkerer Verwirrungsfaktor im Live-Debugging

---

## Wahrscheinliche Fehlerkette im betroffenen Typfall

1. Thinking schlaegt `request_container` vor.
2. Pipeline/Router markiert den Container-Fall als clarification- oder no-match-nah.
3. Control korrigiert den Turn semantisch in Richtung `blueprint_list` / Rueckfrage.
4. `apply_corrections()` behaelt `request_container` trotzdem im Plan.
5. Reconciled `tools_allowed` wird spaeter nochmals ueberschrieben und verliert seine Restriktion.
6. Executor erreicht einen `needs_clarification`-Zustand oder arbeitet mit einem semantisch falschen Tool-Set weiter.
7. Output-Grounding kennt `needs_clarification` nicht als pass-through.
8. Ergebnis: generischer `missing_evidence_fallback`.
9. Das UI zeigt parallel nur `approved` und verschleiert den eigentlichen Zwischenzustand.

---

## Architekturdiagnose

Der verbleibende Drift ist **nicht** nur:

- ein falsch gemappter Status

sondern eine Kombination aus drei Vertragsluecken:

1. **Statusvertrag unvollstaendig**
   - `needs_clarification` existiert im Executor
   - wird aber nicht systemweit als nicht-technischer Endzustand getragen

2. **Toolsatz-Vertrag unvollstaendig**
   - Control darf den Toolsatz semantisch korrigieren
   - der Plan behaelt aber den alten Vorschlag zusaetzlich

3. **Allowlist-Vertrag nicht stabil**
   - reconcile ist vorhanden
   - wird spaeter aber erneut verdraengt

Das ist die eigentliche Schattenautoritaet:

- nicht eine einzelne Funktion
- sondern mehrere nachgelagerte Schichten, die den Control-Entscheid nicht als finalen Vertrag behandeln

---

## Zielbild fuer einen stabilen Fix

Der Fix sollte generisch und dauerhaft diese Invariante herstellen:

> Wenn Control einen Container-Turn in `clarification_required`, `routing_block` oder einen anderen nicht-technischen Interaktionszustand ueberfuehrt, darf keine nachgelagerte Schicht daraus wieder einen generischen Evidence-Failure machen oder das urspruengliche Start-Tool implizit reaktivieren.

Das Zielbild ist damit:

- kein TRION-Home-Sonderfall
- kein Blueprint-Name-Hardcoding
- keine punktuelle Ausnahme im Router
- ein gemeinsamer Contract fuer alle Container-Requests

---

## Architekturentscheidung

Fuer Container-Requests wird kuenftig das folgende Single-Authority-Prinzip als Zielarchitektur gesetzt:

### 1. Control ist Owner des finalen Tool-Satzes

Thinking bleibt advisory.
Control bestimmt fuer den aktuellen Turn autoritativ:

- welche Tools ueberhaupt noch erlaubt sind
- welcher Interaktionsmodus gilt
- ob ein Start-Request in Discovery, Clarification oder Approval ueberfuehrt wird

Konsequenz:

- `_resolve_execution_suggested_tools()` soll sich primaer an `control_decision.tools_allowed` orientieren
- Thinking-Signale duerfen diesen Satz nicht spaeter wieder erweitern

### 2. Autoritative Control-Korrekturen ersetzen, nicht mergen

Wenn Control einen Container-Turn semantisch umstellt, z.B.:

- von `request_container` auf `blueprint_list`
- von direkter Ausfuehrung auf Rueckfrage
- von Start auf Approval-/Discovery-Modus

dann ist das keine additive Empfehlung, sondern eine autoritative Korrektur des Turns.

Konsequenz:

- in diesen Faellen darf `suggested_tools` nicht mit Thinking gemerged werden
- der von Control korrigierte Toolsatz ersetzt den vorherigen Satz fuer diesen Turn

Begruendung:

- Sonderregeln sollen zentral in Control modelliert werden koennen
- nicht spaeter als Workaround in Executor, Output oder UI
- dadurch bleibt Fine-Tuning lokal und vorhersagbar

### 3. Nachgelagerte Schichten duerfen Control nicht re-expandieren

Nach Control duerfen spaetere Schichten:

- Tool-Argumente konkretisieren
- technische Runtime-Zustaende verarbeiten
- Fehler, Approval und Clarification transportieren

Sie duerfen aber nicht:

- den erlaubten Toolsatz wieder erweitern
- aus leerer Allowlist implizit "alles erlaubt" machen
- einen von Control deaktivierten Start-Request wieder in die Ausfuehrung bringen

Konsequenz:

- `decide_tools()` liefert nur noch Args / konkrete Tool-Instanzen
- nicht mehr implizit eine neue Autoritaet ueber den finalen Tool-Satz

### 4. Runtime liefert technische oder interaktive Zustandsklassen, aber keine neue Policy

Runtime bleibt verantwortlich fuer echte Laufzeitzustaende wie:

- `ok`
- `error`
- `timeout`
- `pending_approval`
- `needs_clarification`
- `routing_block`

Aber die Interpretation, welche Reaktion auf diese Zustaende erlaubt ist, bleibt an den Control-/Contract-Regeln ausgerichtet.

Konsequenz:

- Output darf aus einem legitimen interaktiven Zustand keinen generischen Policy-/Grounding-Fallback erfinden
- UI soll den finalen Contract-Zustand anzeigen, nicht ein rohes Zwischenfeld

### 5. Sonderregeln gehoeren in Control, nicht in Schattenpfade

Wenn kuenftig Speziallogik noetig ist, z.B.:

- Home-Reuse
- Discovery-first statt Start
- Hardware-/Approval-Ausnahmen
- Blueprint-spezifische Policy-Pfade

dann sollen diese Regeln primaer im Control-Layer modelliert werden.

Begruendung:

- Control bleibt die einzige Policy-Autoritaet
- Fine-Tuning wird einfacher
- Sonderfaelle muessen nicht in mehreren nachgelagerten Schichten synchronisiert werden

### Zusammenfassung in einem Satz

Control entscheidet **was** in diesem Turn noch erlaubt ist.
Nachgelagerte Schichten entscheiden nur noch **wie** dieser erlaubte Pfad technisch ausgefuehrt oder sichtbar gemacht wird.

---

## Optionale Erweiterung - `control_profiles`

Als mittelfristige Architektur-Erweiterung ist ein eigenes profilbasiertes System fuer den Control-Layer sinnvoll.

Ziel waere **nicht**, unstrukturierte Prompt-Dokumente fuer Control einzufuehren, sondern:

- strukturierte, testbare Policy-Overlays
- zentral gepflegte Sonderregeln
- weniger Hardcodes direkt in `control.py`

### Warum das sinnvoll sein kann

Wenn Control kuenftig Owner des finalen Tool-Satzes ist, dann sollten auch Spezialfaelle moeglichst dort modelliert werden, z.B.:

- Discovery-first statt Start
- Approval-first
- Reuse-Praferenz vor Neu-Start
- Home-/persistent-/system-Container-Sonderverhalten
- Blueprint-Klassen mit speziellen Guardrails

Ohne ein solches System droht langfristig:

- wachsende Sonderlogik in `core/layers/control.py`
- schlecht sichtbare Hardcodes
- schwierigeres Fine-Tuning bei neuen Containerfamilien

### Was **nicht** empfehlenswert ist

Nicht empfehlenswert waere ein reines Markdown-System analog zu `container_addons`, bei dem Control freien Fliesstext "interpretiert".

Gruende:

- Policy wird dann implizit statt explizit
- Regeln werden schwer testbar
- Prioritaeten und Konflikte werden unscharf
- neue Schattenautoritaeten drohen auf Prompt-Ebene

### Empfehltes Modell

Stattdessen:

- **typed manifests** fuer die eigentliche Policy
- optionale `.md`-Dateien nur als menschliche Dokumentation

Skizze:

- `intelligence_modules/control_profiles/<profile>/manifest.yaml`
- optional:
  - `README.md`
  - `notes.md`

### Mögliche Felder in `manifest.yaml`

- `id`
- `title`
- `priority`
- `enabled`
- `domain`
- `applies_to`
  - `blueprint_ids`
  - `container_tags`
  - `intent_patterns`
  - `tool_names`
- `policy`
  - `authoritative_tools`
  - `replace_suggested_tools`
  - `disallowed_tools`
  - `prefer_existing_container`
  - `interaction_mode`
  - `clarification_policy`
  - `approval_policy`
  - `status_pass_through`
- `ui_hints`
  - `decision_class_override`
  - `status_label`
- `tests`
  - optionale Referenz auf erwartete Invarianten oder Contract-IDs

### Trennung der Verantwortlichkeiten

Das Ziel waere eine saubere Zweiteilung:

1. **Live-Capabilities**
   - Tool-Registry
   - Blueprint-Registry
   - Runtime-/Router-/Approval-Faehigkeiten

2. **Static Policy Overlays**
   - `control_profiles`
   - also die Frage, wie Control vorhandene Faehigkeiten policy-seitig behandeln soll

So bleibt klar getrennt:

- **was existiert gerade?** → dynamische Laufzeitquellen
- **wie soll Control damit umgehen?** → strukturierte Profile

### Beispielhafte Anwendungsfaelle

- Profil fuer persistente Home-/System-Container:
  - bevorzuge Reuse
  - Discovery statt blindem Neu-Start

- Profil fuer approval-pflichtige Containerklassen:
  - Approval ist normaler Interaktionszustand
  - kein generischer Fallback

- Profil fuer unscharfe Blueprint-Familien:
  - Clarification ersetzt Start
  - `replace_suggested_tools=true`

### Vorteile

- Sonderregeln bleiben im Control-Layer
- Fine-Tuning wird lokaler und sicherer
- neue Containerfamilien koennen ueber Konfiguration statt Code-Hardcodes modelliert werden
- Policies werden testbarer und besser dokumentiert

### Risiken

- zusaetzliche Komplexitaet im Regelwerk
- Profil-Konflikte brauchen Prioritaets- und Merge-Regeln
- schlechtes Design koennte neue indirekte Schattenautoritaeten erzeugen

### Einschätzung

Ein `control_profiles`-System ist **sinnvoll**, aber nur unter zwei Bedingungen:

1. Der aktuelle Contract-Fix wird zuerst sauber hergestellt.
2. Die Profile bleiben strukturiert und regelbasiert, nicht prompt-/textbasiert.

Damit ist `control_profiles` eine gute **mittelfristige Architektur-Erweiterung**, aber kein Ersatz fuer den jetzt noetigen Contract-Fix.

---

## Empfohlene Implementationsrichtung

### A. `needs_clarification` als First-Class-Contract behandeln

Empfehlung:

- `needs_clarification` als eigenen **nicht-technischen interaktiven Status** systemweit definieren
- denselben Status in:
  - Executor
  - `ExecutionResult.done_reason`
  - Output-Grounding
  - Tests
  - optional UI / Workspace-Observability

Minimal robust waere:

- neuer `DoneReason.NEEDS_CLARIFICATION`

oder allgemeiner:

- gemeinsames Set nicht-fehlerhafter Interaktionszustaende, z.B.
  - `routing_block`
  - `needs_clarification`
  - `pending_approval`

Output-Regel:

- wenn alle nicht-erfolgreichen Evidence-Items nur aus diesen Interaktionszustaenden bestehen
- dann `mode="pass"`
- **kein** `missing_evidence_fallback`
- **kein** `tool_execution_failed_fallback`

Wichtig:

- nicht nur aus der Failure-Menge entfernen
- sondern im Precheck explizit als pass-through behandeln

Sonst bleibt derselbe Drift erhalten.

### B. Control muss den Toolsatz fuer den Turn autoritativ uebergeben koennen

Empfehlung:

- `apply_corrections()` darf fuer solche Faelle nicht blind `suggested_tools` unionen

Stabile Varianten:

1. `verification["suggested_tools_replace"]=True`
   - dann ersetzt Control den Thinking-Satz autoritativ

2. separates Feld wie `_authoritative_suggested_tools`
   - Execution-Resolver nutzt dieses Feld mit Prioritaet vor Thinking

3. generischer Modus:
   - fuer policy-/routing-getriebene Korrekturen wird der Toolsatz ersetzt, nicht erweitert

Wichtig ist die Invariante:

- wenn Control `request_container` fuer diesen Turn nicht mehr will
- darf es nicht parallel im finalen `suggested_tools` weiterleben

### C. Reconciled Allowlist darf spaeter nicht mehr aufgeweicht werden

Empfehlung fuer Sync und Stream:

- `with_tools_allowed(decide_tools.keys())` nicht mehr blind anwenden

Stabile Regel:

- wenn `decide_tools()` leer ist:
  - bestehende `tools_allowed` unveraendert lassen
- wenn `decide_tools()` nicht leer ist:
  - nur die **Schnittmenge** mit bereits erlaubten Tools bilden
  - niemals eine leere Allowlist als implizites "alles erlaubt" interpretieren

Ziel:

- `decide_tools()` liefert Argumente
- aber keine neue Autoritaet ueber den erlaubten Toolsatz

### D. Execution sollte auf Control-Authority aufbauen, nicht auf Thinking-Resten

Zusatzempfehlung:

- `_resolve_execution_suggested_tools()` sollte bei vorhandenem autoritativem Control-Toolsatz nicht wieder auf gemergte Thinking-Reste zurueckfallen

Moegliche robuste Regel:

- falls `control_decision.tools_allowed` nicht leer:
  - Execution-Satz primar daraus ableiten
  - nur mit expliziten Control/verification-Korrekturen kombinieren

Damit wuerde der gesamte Pfad konsistenter:

- Control bestimmt **was**
- `decide_tools()` liefert **wie**
- Thinking bleibt advisory

### E. Stream-Control-Event auf Contract-Paritaet bringen

Der UI-Fix ist sekundar, aber wichtig fuer Debugbarkeit:

- Stream-Control-Event sollte mindestens liefern:
  - `approved`
  - `decision_class`
  - `reason`
  - `warnings`
  - `tools_allowed`

Damit rendert das Frontend denselben Zustand, den das Backend wirklich verwendet.

---

## Was **nicht** der richtige Fix waere

### Kein TRION-Home-Hardcode

Nicht empfehlen:

- `if "TRION Home" in user_text: ...`
- `if blueprint_id == "trion-home": skip grounding`
- Sonderbehandlung nur fuer `TRION Home Workspace`

Das wuerde den aktuellen Fall kaschieren, aber nicht:

- andere Blueprint-Suggest-Faelle
- kuenftige Container
- Sync/Stream-Paritaet

### Nicht einfach Evidence-Pflicht global abschalten

Nicht empfehlen:

- `enforce_evidence_when_tools_suggested=False` als pauschaler Fix

Das wuerde andere Schutzmechanismen aufweichen und den Contract verwischen.

### Nicht nur das UI aendern

Ein UI-Fix allein ist rein kosmetisch.
Das Kernproblem bleibt im Runtime-/Grounding-Vertrag bestehen.

---

## Betroffene Codebereiche fuer einen stabilen Fix

- `core/layers/output.py`
  - pass-through fuer `needs_clarification`
  - ggf. gemeinsames Set interaktiver Nicht-Fehler-Zustaende

- `core/control_contract.py`
  - ggf. neuer `DoneReason.NEEDS_CLARIFICATION`
  - helper fuer nicht-technische Interaktionszustande

- `core/layers/control.py`
  - `apply_corrections()` darf bei autoritativen Tool-Korrekturen nicht unionen

- `core/orchestrator_stream_flow_utils.py`
  - kein Ueberschreiben von reconciled `tools_allowed`
  - Control-Event muss `decision_class` transportieren

- `core/orchestrator_sync_flow_utils.py`
  - gleiche Allowlist-Korrektur wie Stream

- `core/orchestrator.py`
  - `_resolve_execution_suggested_tools()` sollte den autoritativen Toolsatz sauber bevorzugen

- `tests/unit/test_output_grounding.py`
  - neuer Precheck-Test fuer `needs_clarification`

- `tests/unit/test_drift_contracts.py`
  - neue Invarianten fuer:
    - clarification ist kein generic fallback
    - leeres `decide_tools()` darf Control-Allowlist nicht loeschen
    - autoritative Tool-Korrektur ersetzt alte Action-Tools

- `tests/unit/test_fix11_blueprint_suggest_soft_guidance.py`
  - erweitern von Source-Inspection auf Runtime-Contract-Tests

---

## Empfohlene Implementationsreihenfolge

### Phase 1 - Contract festziehen

- `needs_clarification` als pass-through und nicht-technischen Zustand definieren
- Tests zuerst fuer Output-Precheck und `DoneReason`

### Phase 2 - Control-Autoritaet ueber Toolsatz stabilisieren

- autoritative Tool-Korrektur statt Merge
- Allowlist-Override in Sync/Stream entfernen oder auf Schnittmenge umstellen

### Phase 3 - Execution-Resolver sauber an Control anbinden

- bevorzugte Ableitung aus autoritativem Toolsatz
- Thinking nur noch advisory

### Phase 4 - Observability/UI-Paritaet

- Stream-Control-Event vervollstaendigen
- Frontend zeigt denselben Zustand wie Backend

---

## Validation-Matrix fuer den spaeteren Fix

Nach Implementierung sollten mindestens diese Faelle stabil laufen:

1. Suggest-/Clarification-Fall
   - User bekommt Rueckfrage
   - kein generischer Evidence-Fallback

2. No-Match-Fall
   - `blueprint_list` oder Discovery
   - kein `request_container`-Leak

3. Pending-Approval-Fall
   - deterministische Approval-Antwort
   - kein generic fallback

4. Erfolgreicher Container-Start
   - normale Ausfuehrung unveraendert

5. Echter technischer Fehler
   - weiterhin `tool_execution_failed_fallback`
   - keine versehentliche Pass-Through-Verharmlosung

6. Sync- und Stream-Paritaet
   - identisches Verhalten fuer denselben Turn

---

## Abgrenzung zu TRION Home Fast-Path

Der offene Fast-Path fuer `TRION Home` bleibt sinnvoll, ist aber **nicht** der Kernfix fuer diesen Drift.

Der Fast-Path kann spaeter UX verbessern:

- direkter Reuse
- weniger Router-Abhaengigkeit
- weniger Rueckfragen

Aber selbst mit Fast-Path sollte der generische Contract-Fix zuerst sauber sein, sonst bleibt das System fuer andere Container-Typen instabil.

---

## Entscheidungsreife

Die Analyse ist aus meiner Sicht ausreichend, um mit einer stabilen Implementierung zu beginnen.

Empfehlung:

- zuerst Contract-/Runtime-Fix generisch
- danach optional TRION-Home-Fast-Path als separater UX-/Optimization-Task
