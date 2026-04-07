# TRION Control Layer Audit — Memory Write, Control Skip, Warning-Handling

Erstellt am: 2026-03-31
Status: **Analyse abgeschlossen — kein Fix yet**
Bezieht sich auf:

- [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]] — Systemüberblick
- [[2026-03-29-halluzinations-guard-analyse]] — ursprünglicher Halluzinations-Bug
- [[2026-03-29-memory-resolution-contract-plan]] — Memory Read/Guard (abgeschlossen)

---

## Hintergrund

Code-Audit auf Basis einer externen Analyse (ChatGPT, auf Chat-Log-Beispielen).
Drei potenzielle Schwachstellen wurden identifiziert und gegen den echten Code gegengeprüft.

**Ergebnis: Alle drei Punkte bestätigt.**

---

## Befund 1 — Memory Write ist nicht deterministisch

### Kernproblem

Die Atlas-Konsolidierung (A) hat den **Read/Guard-Pfad** deterministisch gemacht
(`MemoryResolution`, guard durch alle Pfade). Aber der **Write-Pfad** ist eine andere
Baustelle — und die war nicht Teil der Konsolidierung.

### Was passiert heute

`orchestrator.py` entscheidet ob gespeichert wird über `skip_autosave`.
Diese Variable wird von **6+ unabhängigen Bedingungen** gesetzt, die
nicht über Control kontrollierbar sind:

| Bedingung | Datei:Zeile | Skip-Grund |
|---|---|---|
| `_pending_intent` gesetzt | `orchestrator.py:4804` | `pending_intent_confirmation` |
| Tool-Fehler + leere Antwort | `orchestrator.py:4807` | `tool_failure_with_empty_answer` |
| `missing_evidence` in Runtime | `orchestrator.py:4813` | `grounding_evidence_missing` |
| `violation_detected` in Runtime | `orchestrator.py:4820` | `grounding_violation` |
| Zu wenig `successful_evidence` | `orchestrator.py:4825` | `insufficient_evidence` |
| Dedupe-Guard feuert | `orchestrator.py:4839` | (silent return) |

### Das eigentliche Problem

Control kann `needs_memory` korrigieren (`control.py:2102` — `apply_corrections`).
Aber Control-Korrekturen und Write-Entscheidung laufen **entkoppelt**:

```
Thinking: needs_memory=False
Control: corrections → needs_memory=True  ✓ (Korrektur greift)
Orchestrator: skip_autosave=True wegen pending_intent  → KEIN WRITE
```

Der Write kann fehlen, **ohne dass es irgendwo als Fehler sichtbar wird**.

### Abgrenzung zu Atlas-Arbeit A

- Atlas A (done): `memory_required_but_missing` wird deterministisch berechnet → Halluzinations-Guard greift
- **Offen:** Ob tatsächlich geschrieben wird, wenn es sollte → eigene Lücke

### Schwere

**Mittel.** Silent loss — kein Crash, kein Log-Alarm, nur fehlende Memory-Einträge.

---

## Befund 2 — Control Skip bei low_risk umgeht Control vollständig

### Kernproblem

`orchestrator_control_skip_utils.py:4–49` — wenn `hallucination_risk == "low"`:
Control wird **nicht aufgerufen**. Kein `control.verify()`, keine Policy-Prüfung,
keine Warning-Klassifikation.

### Was passiert stattdessen

```python
# orchestrator_stream_flow_utils.py:512
if skip_control:
    verified_plan["_skipped"] = True
    control_decision = ControlDecision(
        approved=True,
        hard_block=False,
        decision_class="allow",
        reason="control_skipped",
    )
```

Analog im Sync-Pfad: `orchestrator_sync_flow_utils.py:293`.

### Skip-Bedingungen

Skip wird ausgelöst wenn **alle** zutreffen:
1. `hallucination_risk == "low"` (kommt aus dem Thinking-Layer — Modell schätzt sich selbst ein)
2. Kein Tool aus `control_skip_block_tools` vorgeschlagen
3. Kein Keyword aus `control_skip_block_keywords` in user_text
4. Kein Hard-Safety-Keyword in user_text

### Das eigentliche Problem

Das Modell klassifiziert sich selbst als `low_risk`. Die Block-Listen
(`control_skip_block_tools`, `control_skip_block_keywords`) sind der einzige Schutz.
Wenn ein Tool dort fehlt oder ein Keyword nicht erfasst ist,
läuft der Request komplett ohne Control durch.

Beispiel: `container_stats` wurde als harmlos eingestuft — okay.
Wenn morgen ein anderes Tool fälschlich als `low_risk` durchgeht, ist Control weg.

### Schwere

**Hoch.** Control ist der zentrale Policy-Enforcer. Skip = keine Policy.

---

## Befund 3 — Warnings sind immer advisory, niemals blockierend

### Kernproblem

Es gibt drei `decision_class`-Werte: `allow / warn / hard_block`.
Aber Warnings **können niemals alleine blockieren**.

### Was passiert heute

`control.py:722`:
```python
if approved:
    if str(verification.get("decision_class") or "").strip().lower() in {"", "hard_block"}:
        verification["decision_class"] = "warn" if warnings else "allow"
    return verification  # approved=True trotz Warnings
```

`control_contract.py:114`:
```python
if approved:
    if not decision_class or decision_class == "hard_block":
        decision_class = "warn" if warnings else "allow"
    hard_block = False  # Immer False wenn approved
```

Soft Blocks werden **automatisch zu Warnings konvertiert** wenn `hard_block_allowed=False`
(`control.py:747`):
```python
warnings.append("Deterministic override: non-authoritative soft block converted to warning...")
verification["approved"] = True  # ← trotzdem approved
```

### Was fehlt

Keine INFO/CRITICAL-Hierarchie. Alle Warnings landen im selben Kanal.
Eine Warning über `needs_memory=false` (Halluzinationsrisiko) hat
dasselbe Gewicht wie eine Warning über einen Style-Hinweis.

Das Original-Log aus dem Halluzinations-Bug (`halluzinations-guard-analyse.md`):
```
control_decision: approved=True | warnings=1 | corrections=needs_memory,...
```
Das war das Muster. Es existiert strukturell noch.

### Schwere

**Mittel.** Warnings als Signal sind entwertbar. Wächst mit der Zeit.

---

## Zusammenfassung

| Befund | Kernproblem | Schwere | Fix-Status |
|---|---|---|---|
| Memory Write nicht deterministisch | Write-Pfad entkoppelt von Control-Korrekturen; 6+ silent skip conditions | Mittel | Offen |
| Control Skip bei low_risk | Modell klassifiziert sich selbst; `control.verify()` wird nie aufgerufen | Hoch | Offen |
| Warnings nicht blockierend | `warn` ≠ blockiert; keine Severity-Hierarchie | Mittel | Offen |

---

## Mögliche nächste Schritte (noch nicht entschieden)

**Für Befund 2 (Control Skip) — höchste Priorität:**
- Option A: `hallucination_risk` darf Control nie alleine skippen — nur als Zusatzbedingung
- Option B: Skip-Entscheidung aus dem Modell herausnehmen, deterministisch machen

**Für Befund 3 (Warnings):**
- Warning-Severity einführen: mindestens `advisory` vs. `blocking`
- `CRITICAL`-Warnings → dürfen nicht `approved=True` erzeugen

**Für Befund 1 (Memory Write):**
- Skip-Conditions explizit loggen (derzeit teilweise silent)
- Prüfen ob Write-Entscheidung an MemoryResolution-Objekt gekoppelt werden kann

---

## Verweise

- `core/orchestrator.py:4804` — skip_autosave logic
- `core/orchestrator_control_skip_utils.py:4` — should_skip_control_layer
- `core/orchestrator_stream_flow_utils.py:512` — skip in stream path
- `core/orchestrator_sync_flow_utils.py:293` — skip in sync path
- `core/layers/control.py:722` — approved + warnings
- `core/layers/control.py:747` — soft block → warning conversion
- `core/control_contract.py:114` — ControlDecision warning handling
- [[2026-03-29-halluzinations-guard-analyse]] — ursprüngliches Symptom (approved=True + warnings)
- [[2026-03-29-memory-resolution-contract-plan]] — Read-Seite konsolidiert (Write-Seite offen)
