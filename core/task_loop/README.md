# Task Loop Architecture

Der `task_loop`-Bereich laeuft jetzt vollstaendig ueber Package-Entry-Points. Die frueheren Backing-Dateien `runner.pyback`, `step_runtime.pyback` und `planner.pyback` sind entfernt.

## Aktiver Zustand

- `runner/`
  Aktives Package fuer `core.task_loop.runner` mit den Modulen `messages.py`, `snapshot_state.py`, `chat_sync.py`, `chat_async.py` und `chat_stream.py`.

- `step_runtime/`
  Aktives Package fuer `core.task_loop.step_runtime` mit den Modulen `prompting.py`, `plans.py`, `requests.py`, `prepare.py` und `execution.py`.

- `planner/`
  Aktives Package fuer `core.task_loop.planner` mit den Modulen `objective.py`, `specs.py`, `steps.py` und `snapshots.py`.

## Weitere aktive Module

- `capabilities/container/`
  Aktives Capability-Paket fuer container-spezifische Task-Loop-Logik:
  `extractors.py`, `context.py`, `discovery_policy.py`, `flow.py`,
  `request_policy.py`, `parameter_policy.py`, `recovery.py`, `replan_policy.py`.
  Dort liegen jetzt die echte Freitext-Extraktion, der strukturierte Container-Kontext,
  die Read-first-/Discovery-Regeln, die Container-Request-/Parameter-Policy
  und die container-spezifische Recovery-/Replan-Logik.

- `action_resolution/`
  Neues Ziel-Paket fuer die generische Uebersetzung von geplanten Loop-Schritten
  in konkrete naechste Massnahmen. Dort sollen Read-first-/Auto-Clarify-/
  Recovery-Resolution und capability-uebergreifender Domain-Dispatch fuer
  Container, Skills, MCPs, Cronjobs und generische Loop-Anfragen landen.

- `step_runtime/render_contract.py`
  Aktiver generischer Vertrag dafuer, was ein `analysis_step`,
  `tool_request_step` und `tool_execution_step` ueberhaupt behaupten duerfen.
  `prompting.py` nutzt diesen Vertrag jetzt direkt.

- `replan_engine.py`
  Aktiver generischer Ort fuer Plan-Umschreibungen aus Recovery-/Verify-Hinweisen.

- `recovery_policy.py`
  Aktiver generischer Hook zwischen capability-spezifischen Recovery-Hinweisen
  und dem generischen `replan_engine.py`.

- `evaluation_policy.py`
  Aktive Bewertung des Loop-Zustands nach einem Schritt:
  Fortschritt, Stopgruende und Continue-vs-Complete-Entscheidung.

- `completion_policy.py`
  Aktive Abschlusslogik fuer echte Loop-Vollstaendigkeit und den finalen
  Completion-Text.

- `evidence_policy.py`
  CSV-gestuetzte Erstbewertung fuer Ergebnisqualitaet und Completion-Readiness
  auf Basis von `CIM-skill_rag/output_standards.csv` und
  `CIM-skill_rag/validation_tests.csv`.

- `progress_policy.py`
  CSV-gestuetzte Erstbewertung fuer Fortschritt, Recovery-Bedarf und
  Reasoning-Gates auf Basis von `CIM-skill_rag/error_handling_patterns.csv`
  und `intelligence_modules/procedural_rag/anti_patterns.csv`.

## Ergebnis

- Kein `exec`-Shim mehr in den Package-Entrypoints
- Keine verbleibenden `*.pyback`-Dateien im aktiven Task-Loop
- Keine verbleibenden container-spezifischen Top-Level-`container_*`-Compat-Dateien mehr
- `core.task_loop.runner`, `core.task_loop.step_runtime` und `core.task_loop.planner` bleiben die stabile Import- und Patch-Surface

## Aktueller Handoff-Stand

Diese Sektion beschreibt den zuletzt verifizierten technischen Stand der
Task-Loop-Arbeit nach den Container-/Auto-Clarify-/Routing-Fixes.

### Zielbild

Der gewuenschte Loop ist:

1. Input / Ziel aufnehmen
2. Kontext sammeln
3. Planen
4. Massnahme ausfuehren
5. Ergebnis pruefen
6. bei Bedarf replannen / Rueckfrage / Abschluss

Dabei soll pro Turn genau **ein** autoritativer Ausfuehrungsmodus gelten:

- `direct`
- `task_loop`
- `interactive_defer`

### Autoritaetsgrenze: Control vs Routing

Seit den Handoff-Fixes gilt fuer aktive Task-Loops eine feste Rollenverteilung:

- **Control bestimmt nur den groben Runtime-Modus.**
  Wenn bereits ein aktiver Loop-Snapshot existiert, darf Control weiter
  `execution_mode=task_loop` und `turn_mode=task_loop` setzen, damit der Turn
  nicht in einen Low-Risk-Skip oder einen falschen `direct`-Pfad kippt.
  Der dazugehoerige Reason-Code ist bewusst nur noch
  `active_task_loop_present`.

- **Routing entscheidet final ueber das Handoff.**
  Die Frage, ob ein aktiver Loop wirklich fortgesetzt wird oder nur als
  Hintergrund-Kontext erhalten bleibt, wird ausschliesslich in
  `core/task_loop/active_turn_policy.py` und
  `core/orchestrator_modules/task_loop_routing.py` entschieden.
  Control darf an dieser Stelle kein semantisches Resume mehr behaupten.

- **Resume-vs-Background ist ein Routing-Detail, kein Control-Reason.**
  Die eigentlichen Handoff-Details kommen aus den Routing-Reason-Details:
  - `explicit_continue_request`
  - `runtime_resume_candidate`
  - `meta_turn_background_preserved`
  - `independent_tool_turn_background_preserved`
  - `authoritative_task_loop_non_resume_background`
  - `background_loop_preserved`

- **Thinking-/Trace-UI zeigt beide Ebenen getrennt.**
  `authoritative_execution_mode` / `authoritative_turn_mode` zeigen nur noch,
  dass ein aktiver Loop praesent ist. Die konkrete Branch-Entscheidung wird
  zusaetzlich als `task_loop_active_reason`,
  `task_loop_active_reason_detail` und `task_loop_routing_branch`
  in Thinking- und Routing-Events ausgespielt.

### Handoff-Regeln fuer aktive Loops

Fuer einen aktiven Loop in `WAITING_FOR_USER` oder `BLOCKED` gelten jetzt diese
Produktregeln:

1. `weiter` oder ein echter Runtime-Resume-Kandidat gehen in den aktiven Loop.
2. Explizites `stoppen` beendet den aktiven Loop.
3. Ein expliziter neuer Task-Loop-Start ersetzt bzw. startet einen neuen Loop.
4. Meta-Fragen zum bisherigen Stand laufen im normalen Orchestrator, der Loop
   bleibt als `context_only` im Hintergrund erhalten.
5. Unabhaengige Tool-/Discovery-Fragen laufen ebenfalls im normalen
   Orchestrator, der Loop bleibt im Hintergrund erhalten.
6. Nur ein echter Moduswechsel ohne Background-Preserve oder ein harter Blocker
   darf den aktiven Loop clearen.

### Was aktuell bereits sauber funktioniert

- `task_loop_candidate`-Prompts mit sichtbarer Mehrschrittigkeit werden ueber
  `execution_mode` in die Loop-Strasse geroutet statt in den normalen Chat-Pfad.
- Container-spezifische Task-Loop-Logik sitzt zentral unter
  `capabilities/container/`.
- `action_resolution/` und `auto_clarify/` sind als neue Mittelschicht
  zwischen Planung und Laufzeit eingefuehrt.
- Read-first-/Discovery-Logik fuer Container greift:
  `blueprint_list` wird vor `request_container` bevorzugt.
- Die alte Blueprint-Suggest-Logik wurde vom sofortigen
  `ask_user`-Verhalten auf das neue Recheck-Schema umgestellt:
  `0.68 <= score < 0.80` bedeutet jetzt Discovery/Recheck statt direkter
  Rueckfrage.
- Im Task-Loop duerfen autoritative Discovery-Schritte wie `blueprint_list`
  nicht mehr durch die alte Container-Query-Policy zurueck auf
  `request_container` ueberschrieben werden.
- Fuer `python_container` gibt es jetzt eine erste sichere Bindungsregel:
  wenn nach `blueprint_list` genau ein Python-Kandidat erkennbar ist,
  wird dieser automatisch als `selected_blueprint` uebernommen
  (typisch: `python-sandbox`).

### Zuletzt belegte Root Causes

Die folgenden Fehler wurden waehrend der aktuellen Loop-Arbeit bereits
isoliert und sind wichtig fuer jeden Folge-Chat:

- **Routing-Authority war verteilt**
  `task_loop_candidate`, `turn_mode`, `execution_mode` und aktive Snapshots
  konnten parallel auf das Routing wirken.
  Der Fix war: `execution_mode` als primaere Runtime-Authority.

- **Blueprint-Suggest blockierte zu frueh**
  Der alte Router behandelte `suggest_blueprint` praktisch als sofortige
  User-Rueckfrage. Das stand im Widerspruch zum neuen
  `auto_clarify/safety_gates`-Modell (`< 0.80` => erst Recheck).

- **Discovery-Step wurde vor Ausfuehrung wieder zu `request_container`**
  Im echten Task-Loop wurde `blueprint_list` durch die alte
  Container-Query-Policy erneut auf `request_container` zurueckgebogen.
  Das war ein separater Orchestrator-Policy-Bug, nicht ein Planner-Bug.

- **`blueprint_list`-Discovery wurde nicht bindend in den Request-Schritt
  uebernommen**
  Dadurch lief `request_container` ohne saubere Blueprint-Bindung und fiel
  immer wieder auf denselben Recovery-Pfad zurueck.

### Kritische Dateien fuer den aktuellen Stand

- Routing / Authority
  - `core/layers/control/strategy/execution_mode.py`
  - `core/task_loop/routing_policy.py`
  - `core/orchestrator_modules/task_loop_routing.py`

- Task-Loop Schritt-Laufzeit
  - `core/task_loop/step_runtime/prepare.py`
  - `core/task_loop/step_runtime/requests.py`
  - `core/task_loop/step_runtime/prompting.py`
  - `core/task_loop/step_runtime/execution.py`

- Container-Discovery / Request / Recovery
  - `core/task_loop/capabilities/container/flow.py`
  - `core/task_loop/capabilities/container/request_policy.py`
  - `core/task_loop/capabilities/container/parameter_policy.py`
  - `core/task_loop/capabilities/container/recovery.py`
  - `core/task_loop/capabilities/container/replan_policy.py`

- Action Resolution / Auto Clarify
  - `core/task_loop/action_resolution/resolver.py`
  - `core/task_loop/action_resolution/read_first_policy.py`
  - `core/task_loop/action_resolution/auto_clarify/policy.py`
  - `core/task_loop/action_resolution/auto_clarify/safety_gates.py`
  - `core/task_loop/action_resolution/auto_clarify/parameter_completion.py`
  - `core/task_loop/action_resolution/auto_clarify/capabilities/container.py`

- Orchestrator-Policy fuer Container-Schritte
  - `core/orchestrator_modules/policy/domain_container.py`
  - `core/orchestrator_pipeline_stages.py`
  - `core/blueprint_router.py`

### Aktueller Container-Loop-Stand

Der verifizierte Zielpfad fuer eine Anfrage wie
`"Bitte plane und bearbeite ... python-Container ... sichtbar in mehreren Schritten"` ist:

1. `analysis_step`
   Ziel / Success-Kriterium knapp sichtbar machen
2. `tool_execution_step`
   `blueprint_list`
3. `tool_request_step`
   Container-Anfrage/Freigabe vorbereiten
4. `tool_execution_step`
   `request_container`
5. `response_step`
   sichtbare Zusammenfassung / Rueckfrage / naechster Pfad

Wichtige Invariante:

- `blueprint_list` ist nur Discovery.
- `request_container` darf erst laufen, wenn der Blueprint sauber gebunden ist
  oder bewusst vom User geklaert wurde.

### Fixes — Session 2026-04-20

Die folgenden Probleme wurden in dieser Session isoliert, gefixt und live verifiziert:

**Fix A — Natuerlicher Chat-Flow (resume_user_text)**
Bisher brach der Task-Loop, wenn der User auf eine Rueckfrage TRION's
inhaltlich antwortete (statt "weiter" zu schreiben). Der Text wurde ignoriert.

Fix: `resume_user_text` wird durch den ganzen Loop-Stack durchgereicht.
`is_task_loop_continue(user_text)` → `resume_text = ""`, sonst `resume_text = user_text`.
Betroffen: `core/task_loop/runner/chat_sync.py`, `core/task_loop/chat_runtime.py`.

**Fix B — requires_user-Propagation**
`step_requires_user` wurde im `execution.py`-SUCCESS-Pfad hart auf `False`
gesetzt, obwohl der Planschritt `requires_user=True` hatte.
Fix: `waiting_for_user=step_requires_user` im SUCCESS-Pfad.
Betroffen: `core/task_loop/step_runtime/execution.py`.

**Fix C — False COMPLETED bei response_step**
Die `evidence_policy` triggerte keine Verifikation fuer `response_step`,
wodurch der Loop als COMPLETED abschloss, obwohl noch User-Rueckfragen offen waren.
Fix: `response_step` zur requires_verification-Bedingung hinzugefuegt.
Betroffen: `core/task_loop/evidence_policy.py`.

**Fix D — blueprint_list Infinite Loop (2 Guards)**
Root Cause: `maybe_apply_recovery_replan` prueft nicht, ob der gerade
abgeschlossene Schritt selbst ein Recovery-Step war. Die `verified_artifacts`
enthielten noch den alten `container_recovery_hint` → denselben Discovery-Step
wurde endlos neu eingeplant.

Guard 1 (`_is_recovery_step`): Wenn `current_step_title` selbst ein
kanonischer Discovery-Titel (oder dessen `(Recovery)`-Variante) ist →
kein weiterer Replan.

Guard 2 (completed_steps): Wenn eine `(Recovery)`-Variante des
`replan_step_title` bereits in `completed_steps` liegt → kein weiterer Replan.
Nur die `(Recovery)`-Variante wird geprueft, nicht der exakte Originaltitel,
weil ein initialer Planschritt mit demselben Titel noch einen Recovery-Versuch
erlauben soll.

Ergebnis live verifiziert: `blueprint_list` laeuft jetzt maximal 2x
(1x geplant + 1x als `(Recovery)`-Schritt), danach stoppt der Loop sauber
und fragt den User.

Betroffen: `core/task_loop/recovery_policy.py`.

### Bekannte Restpunkte / offene Unsicherheiten

- Der User-visible Text in `analysis_step` / `response_step` kann noch zu frei
  sein und unverifizierte Details nennen, obwohl die Tool-Lage konservativer ist.

- Es gibt noch keinen robusten User-Stop-/Cancel-Pfad fuer laufende
  Task-Loops in der WebUI. Wenn die Eingabe waehrend Streaming gesperrt ist,
  kann der User den Loop nicht sauber abbrechen.

- Das Modell antwortet manchmal "Ich habe aktuell keinen verifizierten
  Tool-Nachweis..." obwohl das Tool ✅ ok zurueckgegeben hat. Das ist ein
  Modell-Verhalten (deepseek-v3.1), kein Code-Bug — aber es verursacht
  unnoetige Recovery-Runden. Mittel- bis langfristig sollte der Prompt
  fuer Discovery-Schritte das Modell staerker zu einer konkreten Antwort
  zwingen.

### Empfehlung fuer den naechsten Chat

Wenn ein neuer Chat diesen Bereich uebernimmt, zuerst:

1. `core/task_loop/README.md` lesen
2. den letzten Container-Live-Fall gegen die Logs pruefen
3. nur dann erneut an Routing/Blueprint-Gates schrauben, wenn der aktuelle
   Fehler dort wirklich noch liegt

Die wahrscheinlichsten naechsten Arbeiten sind:

- Abschlusslogik sauber auf `WAITING_FOR_USER` statt `COMPLETED` ziehen,
  wenn noch echte Parameter-/Freigabe-Rueckfragen offen sind
- User-visible Schritttexte strenger an verifizierte Discovery-/Request-Daten
  koppeln
- echten Stop-/Cancel-Pfad fuer laufende Task-Loops in der WebUI bauen
- Modell-Prompt fuer Discovery-Schritte haerten, damit "kein verifizierter
  Nachweis"-Antworten nicht unnoetige Recovery-Runden ausloesen

---

## Tool-Utility-Policy Integration — Session 2026-04-20

Dieser Abschnitt dokumentiert die neue Policy-Schicht und die
offenen Schwachstellen, die beim Code-Review gefunden wurden.

### Was implementiert wurde

Das "ueberplanen, unterfuehren"-Problem war die Root Cause des Fehlers,
bei dem TRION einen korrekten Mehrstufen-Plan aufstellte, dann aber statt
Tool-Calls nur eine narrative Antwort lieferte.

**Vollstaendige Pipeline:**

```
User Intent
  → assess_tool_utility()               (tool_utility_policy/policy.py)
  → CapabilityFamily + ExecutionMode
  → capability_hint.py                  (step_runtime/)
       fills requested_capability in step_meta
  → plans.py Phase 1+2                  (step_runtime/)
       Phase 1: capability_hint → requested_capability
       Phase 2: tool_catalog → suggested_tools
  → requests.py fallback                (step_runtime/)
       reads step_plan["suggested_tools"] when step_meta has none
       + ANALYSIS → TOOL_EXECUTION upgrade
  → execution.py gate                   (step_runtime/)
       should_execute_tool_via_orchestrator(TOOL_EXECUTION) = True
       AND suggested_tools non-empty
  → echter Tool-Call
```

**Neue Module:**

| Datei | Zweck |
|---|---|
| `action_resolution/tool_utility_policy/contracts.py` | CapabilityFamily, ExecutionMode, ToolUtilityAssessment |
| `action_resolution/tool_utility_policy/feature_extraction.py` | 6D-Featurevektor aus Pattern-Matching (capability_intent_map_v2.csv) |
| `action_resolution/tool_utility_policy/affinity_matrix.py` | M·f Dot-Product → normierte Scores (capability_feature_weights_v2.csv) |
| `action_resolution/tool_utility_policy/mode_decision.py` | one_shot vs. persistent (execution_mode_signals_v2.csv + Feature-Fallback) |
| `action_resolution/tool_utility_policy/csv_enrichment.py` | Score-Boost via intent_category_map.csv + skill_templates.csv |
| `action_resolution/tool_utility_policy/policy.py` | Pipeline-Entry + force_capability/force_mode Overrides |
| `action_resolution/tool_utility_policy/tool_catalog.py` | Statisches Capability→Tools-Mapping, Read-first-Prinzip |
| `action_resolution/domain_dispatch.py` | Intent → assess_tool_utility → ActionResolutionDecision |
| `step_runtime/capability_hint.py` | requested_capability aus Policy ableiten wenn nicht explizit gesetzt |
| `orchestrator_modules/policy/cron_mode_guard.py` | CronModeConfirmation + Prefix one_shot_intent:: in _build_cron_objective |

**Verifizierter Live-Test:**
`list_skills` Tool-Card erschien mit echten Daten (0 installiert) statt
Memory-Halluzination ueber "node-sandbox".

---

### Bekannte Schwachstellen (Code-Review 2026-04-20)

#### 1. `requires_approval` zu agressiv — requests.py:97

```python
requires_approval=bool(step_meta.get("requires_user")) or bool(suggested_tools)
```

Jeder Schritt mit `suggested_tools` triggert den Approval-Gate — auch
reine Discovery-Calls wie `list_skills` oder `container_list`.
Das bedeutet: jede automatische Tool-Suggestion blockiert den Loop auf
User-Freigabe, auch wenn das Tool read-only und ungefaehrlich ist.

**Fix-Richtung:** Discovery-Tools (`_DISCOVERY`-Menge aus tool_catalog.py)
vom `requires_approval`-Gate ausschliessen.
Read-only-Discovery sollte keine User-Freigabe brauchen.

---

#### 2. Inline-Import in requests.py — geringes Code-Smell

```python
# Zeile 39-40 in step_runtime/requests.py
from core.task_loop.contracts import TaskLoopStepType
if suggested_tools and step_type is TaskLoopStepType.ANALYSIS:
```

Import liegt innerhalb der Funktion statt am Modul-Top.
Kein Laufzeit-Fehler, aber verletzt die Python-Konvention und
verhindert dass statische Analysetools den Importgraph sehen.

**Fix:** Import an den Anfang der Datei verschieben.

---

#### 3. `detect_loop` erkennt keine Oszillationen — guards.py:24

```python
def detect_loop(actions, *, repeated_threshold=2):
    tail = fingerprints[-repeated_threshold:]
    return len(set(tail)) == 1
```

Nur identische Wiederholungen am Ende werden erkannt (A-A oder A-A-A).
Das Pattern A-B-A-B (zwei abwechselnde fehlschlagende Actions) wird
**nicht** erkannt, auch wenn es beliebig lang laeuft.

**Fix-Richtung:** Sliding-Window auf der vollen `fingerprints`-Liste
pruefen, ob ein Muster der Laenge ≤ `repeated_threshold` sich wiederholt.
Alternativ: Schrittzahl-basiertes Hard-Limit als zweite Sicherung
(bereits via `max_steps` vorhanden — bleibt als ausreichender Schutz).

---

#### 4. `pipeline_adapter.py` 5-Wort-Heuristik — Zeile 90-94

```python
if (
    isinstance(plan, dict)
    and not plan.get("suggested_tools")
    and selected_tools
    and len(user_text.split()) < 5
):
    plan["suggested_tools"] = list(selected_tools)
```

Kurze Fortsetzungs-Nachrichten ("ja mach das", "weiter so", "ok")
erben die Tools des vorherigen Schritts.
Das kann zu falschen Tool-Injektionen fuehren wenn der User auf eine
Rueckfrage aus einem Container-Schritt anwortet, obwohl der naechste
Schritt ein Skill-Call sein sollte.

**Fix-Richtung:** Statt der Wort-Zahl pruefen ob `user_text` ein
explizites `is_task_loop_continue()`-Signal ist — dann ist die
Tool-Vererbung semantisch sinnvoll. Bei echter Antwort lieber leer lassen
und die Policy-Pipeline entscheiden lassen.

---

#### 5. Planner hat keine Policy-Awareness — planner/steps.py

`build_task_loop_steps()` baut Schritte aus dem Thinking-Plan ohne
`capability_hint` oder `tool_catalog` zu kennen.
`suggested_tools` kommt direkt aus `plan.get("suggested_tools")`.

Wenn das Modell im Thinking-Plan keine Tools angibt, gehen alle Steps
leer in `step_meta.suggested_tools` ein. Die Policy greift erst in
`plans.py` (step_plan) und `requests.py` (fallback) — zwei Ebenen tiefer.

Das funktioniert, aber es bedeutet: wenn `plans.py` oder die Fallback-Logik
in `requests.py` nicht aufgerufen wird (z.B. bei direktem Step-Resume),
bleibt `suggested_tools` leer und der Orchestrator-Gate oeffnet nicht.

**Aktueller Status:** Ausreichend abgesichert durch die bestehenden
downstream-Fixes. Kein akuter Handlungsbedarf. Langfristig waere es
sauberer wenn der Planner selbst `capability_hint` nutzt.

---

### Fixes — Session 2026-04-20 (Teil 2)

Diese drei Schwachstellen wurden direkt im selben Chat gefixt:

**Fix E — `requires_approval` Discovery-Gate**
Discovery-Tools (`list_skills`, `container_list`, `autonomy_cron_status`,
`autonomy_cron_list_jobs`) blockieren den Loop nicht mehr auf User-Freigabe.
`tool_catalog.py` exportiert jetzt `DISCOVERY_TOOLS` (frozenset) + `is_discovery_only()`.
`requests.py` nutzt `is_discovery_only(suggested_tools)` in der `requires_approval`-Logik.
Betroffen: `core/task_loop/action_resolution/tool_utility_policy/tool_catalog.py`,
`core/task_loop/step_runtime/requests.py`.

**Fix F — Inline-Import aufgeraeumt**
`from core.task_loop.contracts import TaskLoopStepType` war innerhalb der Funktion
`build_task_loop_step_request()`. Jetzt am Modul-Top zusammen mit den anderen Imports.
Betroffen: `core/task_loop/step_runtime/requests.py`.

**Fix G — `pipeline_adapter.py` Tool-Injection**
Die `len(user_text.split()) < 5`-Heuristik wurde durch `is_task_loop_continue(user_text)`
ersetzt. Tools werden nur noch vererbt wenn der User explizit einen Continue-Marker
schickt ("weiter", "ok" etc.), nicht bei echten Antworten wie "nimm gaming-station".
Betroffen: `core/task_loop/pipeline_adapter.py`.

### Offene Restpunkte

Prioritaet niedrig:
- **`detect_loop` fuer A-B-A-B-Muster erweitern** (`guards.py:24`)
  Aktueller `max_steps`-Schutz ist ausreichend; kein akuter Handlungsbedarf.
