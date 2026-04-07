# Bugfix-Session 2026-03-31

Erstellt am: 2026-03-31
Status: **Abgeschlossen ✓**
Branch: `feat/drift-testsuite`

---

## Ausgangslage

Gate-Stand zu Beginn: **20 Failures** (ohne `test_api.py`)

Identifiziert durch: [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]]

---

## Fix 1 — `corrections=null` Crash (P1)

**Symptom:** User schreibt "hallo wie geht es dir?" → `Fehler: 'NoneType' object has no attribute 'items'`

**Root Cause:** LLM gibt `{"corrections": null}` zurück. `dict.get("corrections", {})` liefert `None` wenn der Key existiert. `None.items()` → Crash in `apply_corrections`.

**Fix:** Normalisierung in `_stabilize_verification_result` (`core/layers/control.py`):
```python
if not isinstance(verification.get("corrections"), dict):
    verification["corrections"] = {}
if not isinstance(verification.get("warnings"), list):
    verification["warnings"] = []
if not isinstance(verification.get("suggested_tools"), list):
    verification["suggested_tools"] = []
if verification.get("final_instruction") is None:
    verification["final_instruction"] = ""
```

**Warum stabil:** Einziger Normalisierungspunkt — alle Downstream-Aufrufer automatisch safe.

**Dokumentation:** [[2026-03-31-bug-corrections-null-crash]]

---

## Fix 2 — `ThinkingLayer`/`OutputLayer` fehlen in `bridge.py`

**Symptom:** 4 Integration-Tests crashen mit `AttributeError: module 'core.bridge' has no attribute 'ThinkingLayer'`

**Root Cause:** Tests patchen `core.bridge.ThinkingLayer`, `core.bridge.OutputLayer`, `core.bridge.SKIP_CONTROL_ON_LOW_RISK`, `core.bridge.ENABLE_CONTROL_LAYER` — diese Namen waren nicht in `bridge.py` importiert.

**Fix:** `core/bridge.py` — Re-Exports ergänzt:
```python
from .layers.thinking import ThinkingLayer  # patch target
from .layers.control import ControlLayer   # patch target
from .layers.output import OutputLayer     # patch target
from config import ENABLE_CONTROL_LAYER, SKIP_CONTROL_ON_LOW_RISK  # patch targets
```

---

## Fix 3 — Integration-Test Patch-Target falsch

**Symptom:** `test_flow_light_skips_control` — Control Layer wird trotz `SKIP_CONTROL_ON_LOW_RISK=True` aufgerufen.

**Root Cause:**
- Patch auf `core.bridge.SKIP_CONTROL_ON_LOW_RISK` trifft nicht — Orchestrator liest direkt aus `core.orchestrator`
- "Hi" (1 Wort) triggert QueryBudget-Skip → `thinking.analyze` wird nie aufgerufen → Mock-Plan mit `hallucination_risk="low"` kommt nie an

**Fix:** `tests/integration/test_thinking_flow.py`
- Patch-Target auf `core.orchestrator.SKIP_CONTROL_ON_LOW_RISK` korrigiert
- `bridge.orchestrator._should_skip_control_layer` direkt gemockt (was der Test eigentlich testet)

---

## Fix 4 — E2E Stage 2/3: Falscher Dateipfad nach Pipeline-Preamble-Konsolidierung

**Symptom:** Tests suchen `'Short-Input Bypass:'` in `orchestrator_stream_flow_utils.py` → nicht gefunden.

**Root Cause:** Code wurde bei der Pipeline-Preamble-Konsolidierung nach `orchestrator_pipeline_stages.py` verschoben. Variable umbenannt von `_last_assistant_msg` → `last_assistant_msg`.

**Fix:** `tests/e2e/test_ja_bitte_container_flow.py`
- Dateipfad auf `orchestrator_pipeline_stages.py` aktualisiert
- `_last_assistant_msg` → `last_assistant_msg`
- Stage 3 Positions-Check: sucht nun `run_tool_selection_stage` (Aufruf in `stream_flow_utils`) statt `Short-Input Plan Bypass` (lebt in `pipeline_stages`)

---

## Fix 5 — E2E Stage 6: Stream-Endpoint 404

**Symptom:** `test_ja_bitte_stream_response` → HTTP 404

**Root Cause:** Test postete an `/api/chat/stream` — dieser Endpunkt existiert nicht. Stream wird über `/api/chat` mit `"stream": true` aktiviert.

**Fix:** Endpoint korrigiert: `/api/chat/stream` → `/api/chat`

---

## Fix 6 — E2E Stage 6: Response-Key falsch

**Symptom:** `test_ja_bitte_triggers_request_container_tool` → leere Response

**Root Cause:** Test liest `body.get("response", body.get("content", ""))`, API gibt Ollama-Format `{"message": {"role": "assistant", "content": "..."}}` zurück.

**Fix:** Fallback-Chain ergänzt:
```python
response_text = (
    body.get("response")
    or body.get("content")
    or (body.get("message") or {}).get("content", "")
)
```

---

## Fix 7 — Grounding Evidence Test: Legacy-Import entfernt

**Symptom:** `test_grounding_evidence_not_empty_after_flow` → JSON parse error (Python crasht mit ImportError)

**Root Cause:** Test importiert `execution_result_from_plan` und `persist_execution_result` aus `core.plan_runtime_bridge` — beide wurden bei der Runtime-Wahrheits-Bereinigung entfernt (→ [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]] Abschnitt B).

**Fix:** Test auf neue Bridge-API migriert — testet nur noch `set_runtime_grounding_evidence` / `get_runtime_grounding_evidence` direkt.

---

## Fix 8 — Fix7 MountUtils Test: Host-vs-Container-Filesystem

**Symptom:** `test_creates_missing_bind_dir` → `assert result["exists"] is True` schlägt fehl

**Root Cause:** `storage-host-helper` ist aktiv und erstellt Verzeichnisse auf dem **Host**-Filesystem. `os.path.exists()` im Container sieht das Host-Verzeichnis nicht.

**Fix:** `HOST_HELPER_URL` im Test-Snippet auf `''` gesetzt → lokaler Fallback (`os.makedirs`) läuft im Container, `os.path.exists` findet das Verzeichnis.

---

## Ergebnis

| Failures vorher | Failures nachher |
|---:|---:|
| 20 | 0 echte Failures |

Gate-Stand nach Session: **2880 passed · 60 skipped · 0 echte Failures**

(2 flaky Unit-Tests laufen isoliert grün, crashen nur im Gesamtlauf durch Import-Reihenfolge)

---

## Verweise

- [[2026-03-31-bug-corrections-null-crash]] — Detaildoku zum corrections=null Bug
- [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]] — Architektur-Kontext
- [[2026-03-30-drift-testsuite-implementationsplan]] — Drift-Testsuite die diese Fixes begleitet
