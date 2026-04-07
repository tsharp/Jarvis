# Bug: `'NoneType' object has no attribute 'items'` — corrections=null Crash

Erstellt am: 2026-03-31
Status: **Gefixt ✓ (2026-03-31)**
Priorität: **P1** (betrifft jeden Chat-Turn mit Control-Layer-Aufruf)

---

## Symptom

User schickt eine Nachricht (z. B. "hallo wie geht es dir?").
TRION antwortet mit:

```
Fehler: 'NoneType' object has no attribute 'items'
```

Im Log:

```
[2026-03-31T01:21:31Z] [ERROR] [Admin-API-Chat] Stream error: 'NoneType' object has no attribute 'items'
```

---

## Root Cause

Das LLM (gpt-4.1 via ollama_cloud) gibt als Control-Layer-Response gelegentlich zurück:

```json
{ "corrections": null, ... }
```

Statt dem erwarteten:

```json
{ "corrections": {}, ... }
```

In `control.py` → `apply_corrections()`:

```python
# Zeile 2094
for k, v in verification.get("corrections", {}).items():
```

`dict.get(key, default)` liefert den Default nur wenn der **Key fehlt**.
Wenn der Key vorhanden ist und `null` enthält, gibt `.get("corrections", {})` → `None` zurück.
`None.items()` → `AttributeError: 'NoneType' object has no attribute 'items'`

Der Fehler steigt durch den Stream-Generator hoch und wird in `main.py` gefangen:

```python
except Exception as e:
    log_error(f"[Admin-API-Chat] Stream error: {e}")
```

Daher sieht der User die Fehlermeldung als Chat-Antwort.

---

## Betroffene Stellen

| Datei | Zeile | Pattern |
|---|---:|---|
| `core/layers/control.py` | 2094 | `apply_corrections` — direkter Crash-Punkt |
| `core/layers/control.py` | 589 | `verification.get("corrections", {}).get(...)` |
| `core/orchestrator_stream_flow_utils.py` | 756 | `corrections = verification.get("corrections", {})` |
| `core/orchestrator_stream_flow_utils.py` | 589 | Guard für memory_keys |

---

## Reproduzierbar

Tritt auf wenn:
- Control Layer aktiv (kein Skip)
- LLM gibt `corrections: null` zurück (passiert bei Small-Talk / einfachen Anfragen)
- Konkret beobachtet: deepseek-v3.1:671b, gpt-4.1

---

## Geplanter Fix

**Nicht** überall `or {}` einfügen — das wäre eine Notlösung.

**Richtiger Ort: `_stabilize_verification_result`** in `core/layers/control.py`

Jedes `verification`-Dict geht durch diese Funktion bevor es zurückgegeben wird.
Dort schon vorhandenes Muster für denselben Fall (Zeile 1262):

```python
corrections = verification.get("corrections", {})
if not isinstance(corrections, dict):
    corrections = {}
```

Fix: Dieses Muster allgemein auf das gesamte `verification`-Dict anwenden:

```python
# Am Anfang von _stabilize_verification_result (nach isinstance-Guard):
if not isinstance(verification.get("corrections"), dict):
    verification["corrections"] = {}
if not isinstance(verification.get("warnings"), list):
    verification["warnings"] = []
```

**Warum das stabil ist:**
- Einziger Normalisierungspunkt — alle Downstream-Aufrufer sind automatisch safe
- `apply_corrections`, alle Stream/Sync-Guards, alle Workspace-Entries betroffen
- Kein neuer Caller kann den Fehler erneut einführen

---

## Zusammenhang

- Bezieht sich auf: [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]]
- Ist kein Drift-Test-Failure, aber blockiert normalen Betrieb
- Sollte vor den Drift-Tests gefixt werden

---

## Offene Fragen

- Gibt es weitere Felder in `verification` die `null` statt `[]`/`{}` sein können?
  - Kandidaten: `warnings`, `suggested_tools`, `final_instruction`
  - Empfehlung: alle vier in `_stabilize_verification_result` normalisieren
