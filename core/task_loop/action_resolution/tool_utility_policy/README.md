# Tool-Utility-Policy

Entscheidet auf Basis eines Intent-Textes, **welche Capability-Family** genutzt
werden soll und **ob der Auftrag persistent oder one_shot** ausgefuehrt wird.

## Ziel

Wenn TRION einen neuen Auftrag plant, soll er nicht blind raten, welches
Werkzeug passt. Diese Policy gibt eine datenggestuetzte Empfehlung:

| Capability | Wann |
|---|---|
| `container` | System-/GPU-/OS-Operationen, isolierte Code-Umgebungen |
| `skill` | Benannte Skills, wiederverwendbare Workflows, Dokument-Verarbeitung |
| `cron` | Zeitgesteuerte, wiederkehrende Auftraege |
| `mcp` | Externe APIs, MCP-Server, Dritt-Services, Remote-Tools |
| `direct` | Einfache Chat-Antworten ohne Tool-Einsatz |

| Modus | Wann |
|---|---|
| `one_shot` | Einmaliger Auftrag, kein Scheduling |
| `persistent` | Wiederkehrend, Hintergrund, Cronjob-wuerdig |

## Architektur

```
assess_tool_utility(text, context)
         │
         ▼
feature_extraction.py       ← Pattern-Matching gegen capability_intent_map_v2.csv
         │                    + Keyword-Fallback → f ∈ [0,1]^6
         ▼
affinity_matrix.py          ← M · f → raw scores pro Capability
         │                    (Matrix aus capability_feature_weights_v2.csv)
         ▼
csv_enrichment.py           ← Score-Boost via intent_category_map.csv
         │                    + skill_templates.csv (SKILL-Sekundaersignal)
         ▼
mode_decision.py            ← one_shot vs. persistent
         │                    (execution_mode_signals_v2.csv + Feature-Vektor)
         ▼
ToolUtilityAssessment       ← Ergebnis mit scores, confidence, rationale
```

## Feature-Vektor (6 Dimensionen)

**Finale Namen — identisch in allen drei v2-CSVs:**

| Index | Name | Signal-Beispiele |
|---|---|---|
| 0 | `temporal` | täglich, stündlich, schedule, cron, weekly, recurring, ... |
| 1 | `system` | container, docker, gpu, cpu, install, bash, os-level, ... |
| 2 | `tooling` | skill, workflow, tool call, run skill, named skill, ... |
| 3 | `document` | pdf, docx, slides, spreadsheet, excel, template, ... |
| 4 | `integration` | mcp, api, webhook, extern, server, remote, rpc, ... |
| 5 | `simplicity` | erklär, answer directly, kurz, what is, ohne tools, ... |

> Hinweis: Die urspruenglichen Feature-Namen (compute, data, persistent, network)
> wurden durch die v2-CSV-Namen ersetzt. ChatGPT hat bewusst eine sinnvollere
> Aufteilung gewaehlt — `tooling` trifft Skills besser, `document` ist ein
> starker Skill-Discriminator, `integration` klarer als `network`.

## Affinity-Matrix

Wird vollstaendig aus `capability_feature_weights_v2.csv` geladen (30 Zeilen, 5x6).
Kein hartcodierter Fallback mehr noetig — die CSV ist der Single Source of Truth.

**Aus der v2-CSV (Auszug der staerksten Signale):**

```
               temporal  system  tooling  document  integration  simplicity
container:      0.48     0.97    0.61     0.28      0.72         0.18
skill:          0.42     0.33    0.96     0.67      0.58         0.22
cron:           0.98     0.41    0.36     0.24      0.63         0.12
mcp:            0.21     0.29    0.54     0.31      0.99         0.10
direct:         0.14     0.12    0.18     0.46      0.27         0.98
```

## CSV-Datenquellen

### v2 — aktiv genutzt (in `CIM-skill_rag/`)

| Datei | Inhalt | Zeilen | Status |
|---|---|---|---|
| `capability_intent_map_v2.csv` | intent_pattern → capability_family + confidence + feature_signal | 80 | fertig |
| `execution_mode_signals_v2.csv` | signal_phrase → one_shot\|persistent + confidence | 50 | fertig |
| `capability_feature_weights_v2.csv` | capability × feature → weight (Affinity-Matrix) | 30 | fertig |

**Schema `capability_intent_map_v2.csv`:**
```
intent_pattern, capability_family, confidence, example_phrase, feature_signal, semantic_description
```
- `feature_signal` ist immer exakt einer von: `temporal`, `system`, `tooling`, `document`, `integration`, `simplicity`
- `capability_family` ist immer exakt einer von: `container`, `skill`, `cron`, `mcp`, `direct`
- Patterns sind Python `re`-kompatibel mit `re.IGNORECASE`

**Schema `execution_mode_signals_v2.csv`:**
```
signal_phrase, language, mode, confidence, category, example_context
```
- `mode` ist exakt `one_shot` oder `persistent`
- `language` ist `de` oder `en`
- `category` bleibt innerhalb der 6 Feature-Namen

**Schema `capability_feature_weights_v2.csv`:**
```
capability_family, feature_name, weight, rationale
```
- Exakt 30 Zeilen (5 Capabilities × 6 Features)
- `feature_name` identisch mit den 6 Feature-Vektor-Namen

### Sekundaer — Skill-Boost-Signal (bestehend)

| Datei | Signal |
|---|---|
| `intent_category_map.csv` | Skill-Kategorie-Boost (math/text/ml/...) via Pattern-Match |
| `skill_templates.csv` | Sekundaeres Keyword-Signal fuer SKILL |

> Diese beiden Dateien bleiben als ergaenzender Boost erhalten — sie werden
> in `csv_enrichment.py` geladen und erhoehen den SKILL-Score wenn der Intent
> zu einer bekannten Skill-Kategorie passt.

## Module

| Datei | Aufgabe | Abhaengige CSVs |
|---|---|---|
| `contracts.py` | `CapabilityFamily`, `ExecutionMode`, `ToolUtilityAssessment` | — |
| `feature_extraction.py` | Pattern-Match → `f ∈ [0,1]^6` | `capability_intent_map_v2.csv` |
| `affinity_matrix.py` | Matrix laden + `M · f` → raw scores | `capability_feature_weights_v2.csv` |
| `csv_enrichment.py` | Score-Boost + alle CSV-Ladeoperationen (lru_cache) | alle CSVs |
| `mode_decision.py` | `one_shot` vs. `persistent` | `execution_mode_signals_v2.csv` |
| `policy.py` | Pipeline-Einstiegspunkt `assess_tool_utility()` | — (orchestriert) |

## Implementierungsplan (naechste Session)

### Reihenfolge

1. `contracts.py` — Enums + Dataclass
2. `affinity_matrix.py` — CSV laden, Dot-Product
3. `feature_extraction.py` — Pattern-Match gegen `capability_intent_map_v2.csv`
4. `mode_decision.py` — `execution_mode_signals_v2.csv` + Feature-Schwellwerte
5. `csv_enrichment.py` — Skill-Boost via bestehende CSVs
6. `policy.py` — Pipeline zusammenbauen
7. `__init__.py` — Exports eintragen
8. `tests/unit/test_tool_utility_policy.py` — Tests

### Offene Implementierungsdetails

- **Feature-Extraktion**: `capability_intent_map_v2.csv` als Primaerquelle.
  Pro Zeile: wenn `pattern.search(text)` → `features[feature_signal_index] += confidence * 0.4`.
  Saettigung bei 1.0. Fallback-Keywords nur wenn CSV keinen Match liefert.

- **Affinity-Matrix**: direkt aus CSV als `dict[CapabilityFamily, dict[str, float]]` laden.
  Dot-Product: `score(cap) = sum(matrix[cap][f] * features[f] for f in features)`.

- **Mode-Decision**: `execution_mode_signals_v2.csv` zuerst (phrasenbasiert).
  Wenn kein Match: `features[temporal] >= 0.3 OR features[system] >= 0.3 (mit persistent-Kontext)`
  → `persistent`, sonst `one_shot`.

- **Normalisierung**: raw scores durch Gesamtsumme teilen → `[0,1]`.

- **Confidence**: Gap zwischen Top-1 und Top-2 Score × 2.0, geklemmt auf `[0,1]`.

- **Context-Override**: `context={"force_capability": "cron"}` setzt Score auf 1.0.

## Integrationsplan

1. **Domain-Dispatch** (`action_resolution/domain_dispatch.py`)
   Erster Check wenn kein `requested_capability` im Step vorhanden ist.

2. **Planner** (`step_runtime/plans.py`)
   Beim Erstellen neuer Schritte pruefen welche Capability passt.

3. **Cronjob-Intent** (`orchestrator_modules/policy/cron_intent.py`)
   `build_cron_objective` nutzt Policy um Execution-Mode zu bestaetigen
   und einen sauberen Self-Prompt zu generieren.

## Tests

`tests/unit/test_tool_utility_policy.py` (naechste Session)

| Test | Erwartung |
|---|---|
| `"Starte jede Stunde einen Sync"` | CRON + persistent |
| `"Starte einen Python-Container"` | CONTAINER + one_shot |
| `"Fuehre den ingest skill aus"` | SKILL + one_shot |
| `"Nutze das MCP-Tool zum Speichern"` | MCP + one_shot |
| `"Erklaer mir kurz den Unterschied"` | DIRECT + one_shot |
| CSV-Match boosted SKILL | score(skill) > score(container) |
| `force_capability=cron` | CRON unabhaengig vom Text |
| Ambiguoser Text | confidence < 0.4 |
| DE + EN gleichwertig erkannt | beide liefern gleiche Capability |
