# TRION Halluzinations-Guard — Analyse & Fix-Plan

Erstellt: 2026-03-29
Status: **Zur Review (Codx)**

---

## Symptom

```
Frage: "Hey TRION, weißt du wie ich heiße?"
Antwort: "Ja, natürlich — du bist Markus."
```

Tatsächlicher Name: Danny. In der DB steht unter `user_name` der Wert `Max` (aus einem alten E2E-Test). TRION hat weder `Max` noch `Danny` ausgegeben — er hat **halluziniert**.

Workspace-Log zeigte:
```
control_decision: approved=True | warnings=1 | corrections=needs_memory,memory_keys,...
chat_done: memory_used=True
```

---

## Wo wurde der Anti-Halluzinations-Guard aktiv verhindert

### Bruch 1 — Stream-Flow hat keinen Guard

**Datei:** `core/orchestrator_stream_flow_utils.py`

Der Chat-UI nutzt ausschließlich den Stream-Pfad. `memory_required_but_missing` existiert dort **nicht** — die Variable wird nie berechnet, nie gesetzt, nie weitergegeben.

Der Guard in `output.py` (ANTI-HALLUZINATION-Block) kann im Stream-Flow daher **niemals** feuern.

**Vermutung:** Bei einem Umbau des Orchestrators (Aufteilung in sync/stream utils) wurde dieser Guard nur im Sync-Pfad verdrahtet und im Stream-Pfad vergessen.

---

### Bruch 2 — `high_risk`-Bedingung im Sync-Flow zu eng

**Datei:** `core/orchestrator_sync_flow_utils.py`, Zeile 624

```python
needs_memory = thinking_plan.get("needs_memory") or thinking_plan.get("is_fact_query")
high_risk    = thinking_plan.get("hallucination_risk") == "high"
memory_required_but_missing = needs_memory and high_risk and not memory_used
```

Control korrigierte den Plan mit `hallucination_risk: "medium"` (nicht `"high"`).
→ `high_risk = False`
→ `memory_required_but_missing = False`
→ Guard tot.

Die Bedingung `== "high"` ist zu eng. Für Identitäts-/Fakten-Abfragen sollte jedes `hallucination_risk` außer `"low"` genügen — oder die Bedingung ganz entfallen wenn `memory_keys_not_found` gepflegt wird (siehe Bruch 4).

---

### Bruch 3 — `memory_used=True` ist keine Garantie

**Datei:** `core/context_manager.py`

`memory_used=True` wird gesetzt sobald **irgendeiner** der Memory-Pfade Daten geliefert hat — Daily Protocol, ein anderer Key, semantische Suche. Es bedeutet **nicht**: "der explizit angeforderte Key wurde gefunden und hat einen Wert."

In der Guard-Bedingung steht `and not memory_used` — das heißt: sobald irgendwas aus dem Memory kam (z.B. `user_preference_autonomy`), gilt der Guard als unnötig. Das ist falsch.

Konkretes Beispiel aus dem Fall:
- Memory-Keys angefordert: `['user_name']`
- `user_name` → nicht in der aktuellen Konversation, nicht in `global` → leer
- Aber `memory_used=True` wegen anderer Keys im gleichen Lauf
- → Guard-Bedingung `not memory_used` = `False` → kein Guard

---

### Bruch 4 — `ContextResult` trackt nicht welche Keys leer blieben

**Datei:** `core/context_manager.py`

```python
for key in memory_keys:
    content, found = key_results.get(key, ("", False))
    if found:
        result.memory_data += content
        result.memory_used = True  # ← blindes True, kein Key-Tracking
    # wenn nicht found: stillschweigend ignoriert
```

Die Information "Key X wurde explizit angefragt und war leer" geht verloren. `ContextResult` hat kein Feld wie `memory_keys_not_found`. Stromabwärts kann niemand mehr unterscheiden zwischen "kein Memory angefragt" und "Memory angefragt, aber nichts gefunden".

---

### Bruch 5 — Validator-Service ist nicht im Orchestrator eingebunden

**Datei:** `validator-service/validator-service/main.py`

Der Validator-Service hat einen `LLM_VALIDATOR_SYSTEM_PROMPT` der explizit auf `hallucination: "no|maybe|yes"` prüft und bei `"yes"` auf `final_result: "fail"` setzt.

Dieser Service wird von keiner Stelle in den Orchestrator-Pfaden aufgerufen:
- Nicht in `orchestrator_sync_flow_utils.py`
- Nicht in `orchestrator_stream_flow_utils.py`
- Nicht in `orchestrator.py`

Er ist eine Standalone-App ohne Integration — ein fertiges Werkzeug das niemand benutzt.

---

## Vollständige Kette des Versagens

```
User: "Wie heiße ich?"
  ↓
Thinking-Layer: needs_memory=false, hallucination_risk=medium
  ↓
Control: korrigiert → needs_memory=true, memory_keys=['user_name'], hallucination_risk=medium
  ↓
apply_corrections(): merged korrekt ins verified_plan
  ↓
ContextManager: sucht user_name
  → nicht in aktueller conversation_id
  → nicht in global
  → key_results['user_name'] = ("", False)
  → memory_keys_not_found = ['user_name']  ← wird NICHT getrackt
  → memory_used = True  ← wegen anderem Key (user_preference_autonomy o.ä.)
  ↓
orchestrator_stream_flow_utils.py:
  → memory_required_but_missing existiert NICHT im Stream-Pfad
  ↓
output.py: kein ANTI-HALLUZINATION-Block im Prompt
  ↓
Modell: hat keinen Wert, erfindet "Markus"
  ↓
Validator-Service: existiert, wäre relevant, wird nicht aufgerufen
  ↓
Antwort landet ungeprüft beim User
```

---

## Fix-Plan

### Fix A — `ContextResult` um `memory_keys_not_found` erweitern

**Datei:** `core/context_manager.py`

```python
@dataclass
class ContextResult:
    memory_data: str = ""
    memory_used: bool = False
    sources: list = field(default_factory=list)
    memory_keys_not_found: list[str] = field(default_factory=list)  # NEU
```

In der Key-Loop:
```python
for key in memory_keys:
    content, found = key_results.get(key, ("", False))
    if found:
        result.memory_data += content
        result.memory_used = True
    else:
        result.memory_keys_not_found.append(key)  # NEU
```

---

### Fix B — Guard-Bedingung in beiden Flow-Paths reparieren

**Datei:** `core/orchestrator_sync_flow_utils.py`
```python
# Alt (kaputt):
memory_required_but_missing = needs_memory and high_risk and not memory_used

# Neu:
memory_required_but_missing = needs_memory and bool(ctx_result.memory_keys_not_found)
```

**Datei:** `core/orchestrator_stream_flow_utils.py`
```python
# Neu hinzufügen (fehlt komplett):
memory_required_but_missing = needs_memory and bool(ctx_result.memory_keys_not_found)
```

Voraussetzung: `ctx_result` muss im Stream-Flow zugänglich sein (prüfen ob bereits vorhanden oder übergeben werden muss).

---

### Fix C — Anti-Halluzinations-Text im Output-Prompt schärfen

**Datei:** `core/layers/output.py`

```python
if memory_required_but_missing:
    prompt_parts.append("\n### ANTI-HALLUZINATION:")
    prompt_parts.append(
        "Die folgenden Informationen wurden explizit im Gedächtnis gesucht "
        "und wurden NICHT gefunden."
    )
    prompt_parts.append(
        "Du kennst die Antwort NICHT. "
        "Antworte mit: 'Das habe ich nicht gespeichert' oder 'Das weiß ich leider nicht.' "
        "NIEMALS raten. NIEMALS Namen, Zahlen oder Fakten erfinden. "
        "Auch nicht als Beispiel, Platzhalter oder Schätzung."
    )
```

---

### Fix D — Validator-Service in Output-Pfad einhängen (optional, post-generation)

**Datei:** `core/orchestrator_sync_flow_utils.py` und/oder `core/orchestrator_stream_flow_utils.py`

Nach der Output-Generierung: für `is_fact_query=True` oder `needs_memory=True` Antworten den Validator-Service aufrufen. Bei `hallucination: "yes"` → Antwort durch Fallback ersetzen.

Achtung: erhöht Latenz. Nur für hoch-risiko Turns sinnvoll (identity, facts, numbers).

---

## Offene Fragen für Codx-Review

1. Wurde `memory_required_but_missing` bewusst aus dem Stream-Flow herausgelassen (Latenz?) oder ist das ein Versehen beim Umbau?
2. Wo wird `ctx_result` im Stream-Flow übergeben — ist `memory_keys_not_found` dort zugänglich?
3. Gibt es noch weitere Stellen wo `memory_used` als Guard-Bedingung falsch genutzt wird?
4. Validator-Service: war die Intention eine async post-generation Prüfung, oder war er für einen anderen Zweck gedacht?
5. War `high_risk`-Bedingung eine bewusste Performance-Entscheidung ("nur bei explizit hohem Risiko prüfen") — oder ein Versehen?

---

## Codex Gegencheck (aktueller Code-Stand 2026-03-29)

Umsetzungsplan fuer Claude Code:

- [[2026-03-29-halluzinations-guard-implementationsplan]]

### Gesamturteil

Die Analyse trifft den Kern.

Der Fehler ist **nicht** primaer, dass ein altes Modul aktiv durch ein neues ersetzt wurde, sondern dass beim Umbau des Orchestrators in getrennte Sync-/Stream-Pfade wichtige Guard-Verdrahtung **nur im Sync-Pfad** erhalten blieb.

Zusaetzlich gibt es ein strukturelles Modellierungsproblem:

- der Context-Layer transportiert nur `memory_used`
- aber nicht den entscheidenden Zustand
- "explizit angeforderter Memory-Key wurde nicht gefunden"

Und es gibt ein drittes Problem:

- der Validator-Service plus Client existieren
- sind aber in keinen aktiven Runtime-Pfad eingebunden

---

## Bestaetigte Befunde

### Befund 1 — Stream-Flow hat den Guard wirklich nicht verdrahtet

Das ist im aktuellen Code bestaetigt.

Im Sync-Pfad wird `memory_required_but_missing` berechnet und an den Output-Layer weitergegeben:

- `core/orchestrator_sync_flow_utils.py:622-636`

```python
needs_memory = thinking_plan.get("needs_memory") or thinking_plan.get("is_fact_query")
high_risk = thinking_plan.get("hallucination_risk") == "high"
memory_required_but_missing = needs_memory and high_risk and not memory_used
```

Im Stream-Pfad wird zwar Kontext gebaut und `memory_used` gelesen:

- `core/orchestrator_stream_flow_utils.py:441-455`

aber beim eigentlichen Output-Aufruf wird der Guard **nicht** uebergeben:

- `core/orchestrator_stream_flow_utils.py:2051-2055`

```python
async for chunk in orch.output.generate_stream(
    user_text=user_text,
    verified_plan=verified_plan,
    memory_data=full_context,
    model=resolved_output_model_stream,
```

Das ist besonders eindeutig, weil `generate_stream(...)` den Parameter technisch bereits unterstuetzt:

- `core/layers/output.py:1316-1324`

```python
async def generate_stream(
    ...
    memory_required_but_missing: bool = False,
```

Das spricht klar fuer:

- **kein bewusst anderes Stream-Design**
- sondern **vergessene Verdrahtung beim Split**

### Befund 2 — Auch der LoopEngine-Pfad umgeht den Guard

Im Stream-Flow gibt es zusaetzlich einen zweiten Bypass:

- `core/orchestrator_stream_flow_utils.py:2023`

```python
sys_prompt = orch.output._build_system_prompt(verified_plan, full_context)
```

Auch hier wird der Guard nicht gesetzt.

Das bedeutet:

- selbst wenn der normale Stream-Pfad spaeter gefixt wird
- bleibt der LoopEngine-Zweig ohne denselben Schutz

Das macht den Befund staerker:

- nicht nur ein einzelner Aufruf fehlt
- sondern der ganze Stream-Zweig hat den Guard beim Umbau nicht sauber mitgenommen

### Befund 3 — `memory_used` ist als Guard-Signal strukturell ungeeignet

Die Analyse ist korrekt, aber der reale Zustand ist sogar noch problematischer.

`memory_used=True` bedeutet nicht nur:

- "irgendein Memory-Key wurde gefunden"

sondern auch:

- TRION laws wurden geladen
- Active Container Context wurde geladen
- System-Tool-Kontext wurde geladen
- Skill-/Blueprint-Kontext wurde geladen

Das ist im `ContextManager` bestaetigt:

- `core/context_manager.py:302-346`
- `core/context_manager.py:376-438`

Beispiele:

```python
result.memory_used = True  # trion_laws
result.memory_used = True  # active_containers
result.memory_used = True  # system_tools
result.memory_used = True  # memory:key
```

Damit ist `not memory_used` als Anti-Halluzinations-Gate fachlich falsch.

Es sagt nur:

- "es wurde irgendein Kontext geladen"

nicht:

- "der vom Plan explizit geforderte Fakt wurde gefunden"

### Befund 4 — `ContextResult` trackt fehlende Keys wirklich nicht

Auch das ist bestaetigt.

Die Klasse `ContextResult` hat aktuell nur:

- `memory_data`
- `memory_used`
- `system_tools`
- `sources`

Siehe:

- `core/context_manager.py:41-63`

In der Memory-Key-Loop werden nicht gefundene Keys einfach verworfen:

- `core/context_manager.py:476-481`

```python
for key in memory_keys:
    content, found = key_results.get(key, ("", False))
    if found:
        result.memory_data += content
        result.memory_used = True
        result.sources.append(f"memory:{key}")
```

Es gibt aktuell **kein** Feld wie:

- `memory_keys_not_found`
- `requested_memory_keys`
- `missing_required_facts`

### Befund 5 — Diese Information geht auch im gemeinsamen Context-Trace verloren

Der Orchestrator uebernimmt aus `ContextResult` aktuell nur das grobe Signal:

- `memory_used`

Siehe:

- `core/orchestrator_flow_utils.py:104-111`
- `core/orchestrator_flow_utils.py:176-178`

Damit ist die Analyse sogar noch staerker:

- das Problem sitzt nicht nur in Sync vs. Stream
- sondern auch im Datenvertrag zwischen `ContextManager` und Orchestrator

### Befund 6 — Validator-Service und Client existieren, werden aber nirgends benutzt

Das ist klar bestaetigt.

Vorhanden:

- Service: `validator-service/validator-service/main.py`
- Client: `modules/validator/validator_client.py`

Der Client ruft sauber `/validate_llm` auf:

- `modules/validator/validator_client.py:26-65`

Der Service implementiert den Halluzinations-Check:

- `validator-service/validator-service/main.py:166-219`

Repo-weites Gegenchecken zeigt aber:

- keine Nutzung in `core/`
- keine Nutzung in `adapters/`
- keine Nutzung in aktiven Runtime-Pfaden

Das bedeutet:

- nicht ersetzt
- nicht versehentlich teilweise migriert
- sondern **gebaut, aber nie angeschlossen**

---

## Praezisierung der Root Cause

Die eigentliche Root Cause ist wahrscheinlich **dreistufig**:

### 1. Architektur-Split ohne vollstaendige Guard-Portierung

Beim Umbau des Orchestrators in:

- gemeinsame Hilfsfunktionen
- Sync-Flow
- Stream-Flow

blieb die Guard-Berechnung im Sync-Pfad erhalten, wurde aber im Stream-Pfad nicht mitgezogen.

Das wirkt wie ein klassischer Refactor-Verlust:

- Funktionalitaet existiert noch
- aber nur in einem Ausfuehrungspfad

### 2. Zu schwaches Kontextmodell

Selbst im Sync-Pfad basiert der Guard auf einem Signal, das semantisch zu grob ist:

- `memory_used`

Statt:

- "der angeforderte Key wurde gefunden"

Der Guard war also schon vor dem Stream-Bruch architektonisch fragil.

### 3. Validator blieb als Insel stehen

Der Validator-Service sieht aus wie ein spaeterer oder paralleler Qualitaetsschutz, der nie in die Hauptpipeline integriert wurde.

Das Muster passt zu:

- Modul entwickelt
- Docker/Config vorbereitet
- Client geschrieben
- Integration in Orchestrator aber nie vollendet

---

## Antwort auf die Frage "Haben wir Module ersetzt, vergessen anzubinden oder uebersehen?"

### Was nach aktuellem Gegencheck **vergessen anzubinden** wurde

- der Halluzinations-Guard im Stream-Pfad
- der Halluzinations-Guard im LoopEngine-Zweig
- der Validator-Client/Validator-Service in der Runtime-Pipeline

### Was **nicht ersetzt**, sondern **nur unvollstaendig portiert** wurde

- die Guard-Logik zwischen Sync- und Stream-Flow

Das sieht nicht nach bewusstem Ersetzen aus, sondern nach:

- Sync-Pfad weiterentwickelt
- Stream-Pfad bei einem Refactor nicht vollstaendig nachgezogen

### Was **nie sauber modelliert** wurde

- fehlende explizite Repräsentation von "angeforderter Memory-Key nicht gefunden"

Das ist kein Verdrahtungsfehler allein, sondern ein Datenmodell-Problem.

---

## Korrigierte oder geschaerfte Punkte gegenueber der Ursprungsanalyse

### Korrektur 1 — `memory_used=True` ist noch breiter als angenommen

In der Ursprungsanalyse klingt es so, als koenne `memory_used=True` durch andere Memory-Keys, Daily Protocol oder semantische Suche gesetzt werden.

Real ist es noch breiter:

- auch TRION laws
- active container context
- system_tools
- skill_graph
- blueprint_graph

koennen `memory_used=True` setzen.

Das macht den bestehenden Guard noch unzuverlaessiger als zuerst angenommen.

### Korrektur 2 — der Stream-Path ist nicht nur "ohne Berechnung", sondern auch ohne Uebergabe

Die Analyse sagt: der Stream-Flow berechnet `memory_required_but_missing` nicht.

Das stimmt.

Aber zusaetzlich gilt:

- selbst wenn man ihn separat berechnen wuerde
- der aktuelle `generate_stream(...)`-Aufruf uebergibt das Flag derzeit nicht

Und:

- der LoopEngine-Zweig baut den System-Prompt sogar direkt

Das heisst:

- der Fix muss an **mehr als einer** Stelle passieren

### Korrektur 3 — der Validator ist nicht "theoretisch da", sondern konkret als orphaned Integration

Es gibt nicht nur den Service.

Es gibt auch bereits:

- `VALIDATOR_URL` in Config/Docker
- einen Runtime-Client

Das staerkt die Vermutung:

- die Integration war offenbar vorgesehen
- wurde aber nie bis in den Orchestrator gezogen

---

## Schlussfolgerung fuer die Doku

Der aktuelle Stand spricht am klarsten fuer diese Lesart:

- **kein einzelnes Modul wurde absichtlich ersetzt**
- **mehrere Schutzbausteine wurden beim Architektur-Split nicht ueber alle Ausfuehrungspfade mitgenommen**
- **der Validator wurde vorbereitet, aber nie eingebunden**
- **das Context-Modell war fuer diesen Guard von Anfang an zu grob**

In einem Satz:

- **Der Halluzinationsschutz ist nicht an einer Stelle "kaputt", sondern durch einen unvollstaendigen Sync/Stream-Umbau plus zu grobes Memory-Signaling strukturell unterlaufen worden.**
