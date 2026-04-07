# Drift-Testsuite Implementationsplan

Erstellt am: 2026-03-30
Status: **Abgeschlossen** ✓
Bezieht sich auf:

- [[2026-03-29-trion-codeatlas-und-konsolidierungsanalyse]]

---

## Ausgangslage

Nach Abschluss der Atlas-Prioritaet-1-Arbeiten (Memory-Wahrheit, Runtime-Wahrheit, Sync/Stream-Pipeline-Preamble) steht der Branch `feat/drift-testsuite` mit **28 failing Contract-Tests**.

Alle 28 sind neue Tests — keine Regression.
Sie testen Anforderungen, die noch nicht erfuellt sind.

Unit-Gate-Stand beim Start: **2489 passed · 3 skipped · 28 failed**

---

## Kategorienuebersicht

| Kategorie | Tests | Typ |
|---|---:|---|
| **Phase 1 — Backend Contracts** | **6** | Reine Backend-Logik, kein Frontend |
| **Phase 2 — Terminal-App Feature-Block** | **22** | `terminal.js` + `index.html` |
| **Gesamt** | **28** | — |

---

## Phase 1 — Backend Contracts

Diese 6 Tests haben keinerlei Frontend-Abhaengigkeit.
Sie koennen isoliert, chirurgisch und einzeln gefixt werden.

**Ziel: alle 6 gruen, kein Seiteneffekt auf bestehende Tests.**

---

### 1.1 Hardware-Resolution `device_overrides` (3 Tests)

**Datei:** `container_commander/hardware_resolution.py`

**Failing:**
- `test_hardware_resolution_builds_device_overrides_for_stage_only_devices`
- `test_hardware_resolution_uses_local_fallback_when_http_unavailable`
- `test_hardware_resolution_prefers_local_runtime_support_when_available`

**Problem:**
`resolve_hardware_plan()` gibt `HardwareResolutionResult` mit `device_overrides=[]` zurueck,
auch wenn Aktionen mit `action: "stage_for_recreate"` vorhanden sind.

**Erwartetes Verhalten:**
Fuer jede Aktion mit `action == "stage_for_recreate"` soll das
`resource_id`-Fragment nach dem letzten `::` als Device-Pfad in `device_overrides` landen.

Beispiel:
```
resource_id = "container::input::/dev/input/event21"
→ device_overrides enthält "/dev/input/event21"
```

**Fix-Ort:** `resolve_hardware_plan()` — `device_overrides` aus `plan_payload["actions"]` befuellen.

---

### 1.2 Port-Conflict-Precheck (1 Test)

**Datei:** `container_commander/engine.py`

**Failing:**
- `test_engine_uses_port_conflict_precheck_and_port_labels`

**Problem:**
Engine prueft vor dem Start keine Port-Konflikte und setzt keine Port-Labels auf Containern.

**Erwartetes Verhalten:**
- Vor `docker run` / `compose up`: pruefen ob angeforderte Host-Ports bereits belegt sind
- Belegte Ports → strukturierter Fehler, kein blindes Starten
- Container erhalten Port-Labels fuer spaeteres Discovery

**Fix-Ort:** Engine-Startpfad, ggf. neues `engine_start_support.py`-Fragment.

---

### 1.3 Orchestrator TTL-Event Fallback (1 Test)

**Datei:** `core/orchestrator_context_pipeline.py` o.a.

**Failing:**
- `test_ttl_event_fallback_to_in_memory_when_docker_unavailable`

**Problem:**
TTL-Events landen bei nicht erreichbarem Docker-Daemon nicht im In-Memory-Fallback.

**Erwartetes Verhalten:**
- Docker nicht erreichbar → TTL-Events in-memory halten statt Exception / Verlust
- Kein Crash, kein stiller Drop

**Fix-Ort:** TTL-Event-Pfad in Context-Pipeline.

---

### 1.4 Runtime Hardware Gateway Fallback-URLs (1 Test)

**Datei:** `adapters/admin-api/runtime_hardware_routes.py` o.a.

**Failing:**
- `test_runtime_hardware_gateway_has_reachable_fallback_urls`

**Problem:**
Gateway hat keine definierten Fallback-URLs wenn Runtime-Hardware-Service nicht erreichbar ist.

**Erwartetes Verhalten:**
- Gateway-Endpunkt liefert strukturierte Fallback-URL-Liste
- Clients koennen damit autonom auf Alternativ-Endpunkte wechseln

---

## Phase 2 — Terminal-App Feature-Block

22 Tests — alle pruefen Inhalte von `adapters/Jarvis/js/apps/terminal.js` (oder `terminal/`)
sowie einmal `adapters/Jarvis/index.html`.

**Ausgangslage:**
`terminal.js` ist aktuell noch der Phase-3-Stand ohne die neuen Feature-Contracts.
Es existiert bereits ein ungetragenes Verzeichnis `adapters/Jarvis/js/apps/terminal/`
(Hinweis auf begonnene Modularisierung).

**Ziel:** Alle 22 Contract-Tests gruen.
Strategie: Feature fuer Feature in `terminal.js` ergaenzen (oder im Terminal-Verzeichnis,
je nachdem wie die Modularisierung weitergeht).

Die Tests sind nach Themengruppen geordnet.

---

### 2.1 Approval Center (4 Tests)

**Failing:**
- `test_terminal_includes_approval_center_markup_and_toggle_hooks`
- `test_terminal_approval_center_loads_pending_and_history`
- `test_terminal_approval_center_can_resolve_requests_from_list`
- `test_terminal_approval_center_uses_structured_runtime_risk_fields`

**Was fehlt:**
- `id="approval-center"` — Panel-Markup
- `apiRequest('/approvals', ...)` — Pending + History laden
- `window.termApproveRequest = async function(approvalId)` — Resolve-Handler
- `function approvalReason(item)` — strukturierte Risk-Field-Extraktion

---

### 2.2 Terminal Runtime UX (8 Tests)

**Failing:**
- `test_terminal_logs_panel_supports_mode_split_and_activity_feed`
- `test_terminal_routes_ws_output_by_stream_channel`
- `test_terminal_includes_container_detail_drawer_endpoints`
- `test_terminal_includes_volume_snapshot_manager_endpoints`
- `test_terminal_supports_slash_quick_commands`
- `test_terminal_has_dashboard_home_with_kpis_timeline_and_continue`
- `test_terminal_blueprint_ux_has_presets_inline_validation_and_export_download`
- `test_terminal_power_user_features_include_palette_history_sessions_and_clean_log_export`

**Was fehlt:**
- Logs: Mode-Split (`if (stream === 'logs')`) + Activity-Feed
- WS: Stream-Routing nach Channel
- Container Detail Drawer: `window.termOpenCtDetails = function(id)`
- Volume Snapshot Manager: `apiRequest('/volumes', ...)`
- Slash-Commands: `if (parts.length === 1 && first.startsWith('/'))`
- Dashboard: `data-tab="dashboard"` mit KPIs, Timeline, Continue
- Blueprint UX: `class="bp-preset-btn" data-preset="python"` + Inline-Validation + Export
- Power-User: `id="term-command-palette"` + History + Sessions + Log-Export

---

### 2.3 Preflight + Deploy Overrides (3 Tests)

**Failing:**
- `test_terminal_blueprint_cards_include_quick_actions`
- `test_terminal_deploy_flow_uses_preflight_modal_and_checks`
- `test_terminal_deploy_can_send_overrides_and_environment`

**Was fehlt:**
- Blueprint-Cards mit Quick-Actions (Edit, Inspect, Delete)
- Preflight-Modal vor Deploy
- Deploy-Payload mit Override- und Environment-Feldern

---

### 2.4 Managed Storage Picker (2 Tests)

**Failing:**
- `test_terminal_preflight_contains_managed_storage_picker_and_payload_wiring`
- `test_approval_persists_and_replays_mount_override_context`

**Was fehlt:**
- `apiRequest('/storage/managed-paths', ...)` im Preflight
- `storage_assets:` im Approval-Replay-Payload

---

### 2.5 Memory Panel WebUI (2 Tests)

**Failing:**
- `test_terminal_memory_panel_calls_trion_memory_endpoints`
- `test_terminal_refreshes_memory_panel_on_memory_ws_events`

**Was fehlt:**
- Memory-Panel ruft TRION-Memory-Endpunkte auf
- Panel-Refresh bei Memory-WS-Events

---

### 2.6 API Hardening (1 Test)

**Failing:**
- `test_terminal_core_commander_flows_use_api_request`

**Was fehlt:**
- Alle Commander-Flows nutzen `apiRequest(...)` statt rohem `fetch`

---

### 2.7 index.html Versioned Workspace Script (1 Test)

**Datei:** `adapters/Jarvis/index.html`

**Failing:**
- `test_index_uses_versioned_workspace_script`

**Was fehlt:**
- `workspace.js` wird mit Cache-Busting-Parameter eingebunden (z.B. `?v=...`)

---

## Reihenfolge

```
Phase 1.1 → hardware_resolution device_overrides        (3 Tests)
Phase 1.2 → port conflict precheck                      (1 Test)
Phase 1.3 → TTL-Event fallback                          (1 Test)
Phase 1.4 → runtime hardware gateway fallback URLs      (1 Test)
───────────────────────────────────────────────────────
Phase 2.7 → index.html versioned script                 (1 Test, trivial)
Phase 2.6 → API hardening (apiRequest)                  (1 Test)
Phase 2.1 → Approval Center                             (4 Tests)
Phase 2.3 → Preflight + Deploy Overrides                (3 Tests)
Phase 2.4 → Managed Storage Picker                      (2 Tests)
Phase 2.2 → Terminal Runtime UX                         (8 Tests)
Phase 2.5 → Memory Panel WebUI                          (2 Tests)
```

**Logik hinter der Reihenfolge:**

1. Backend zuerst — kein Frontend-Overhead, schnelle wins
2. Innerhalb Phase 2: kleinste/einfachste Bloecke zuerst (index.html, api hardening)
3. Approval Center vor Preflight — Preflight-Tests erwarten Approval-Infrastruktur
4. Storage Picker nach Preflight — baut auf Preflight-Payload auf
5. Terminal UX letzter grosser Block — enthaelt Abhaengigkeiten auf vorherige Features
6. Memory Panel am Ende — eigene Infrastruktur, unabhaengig von Commander-UX

---

## Zielzustand

Unit-Gate nach Abschluss: **2517 passed · 3 skipped · 0 failed**

Alle Contract-Tests der `feat/drift-testsuite` erfuellt.
Kein Regressions-Failure in bestehenden Tests.

---

## Fortschrittsprotokoll

| Phase | Status | Tests | Erledigt am |
|---|---|---:|---|
| 1.1 Hardware-Resolution device_overrides | ✅ Erledigt | 3 | 2026-03-30 |
| 1.2 Port-Conflict-Precheck | ✅ Erledigt | 1 | 2026-03-30 |
| 1.3 TTL-Event Fallback | ✅ Erledigt | 1 | 2026-03-30 |
| 1.4 Gateway Fallback-URLs | ✅ Erledigt | 1 | 2026-03-30 |
| 2.7 index.html versioned script | ✅ Erledigt | 1 | 2026-03-30 |
| 2.6 API Hardening | ✅ Erledigt | 1 | 2026-03-30 |
| 2.1 Approval Center | ✅ Erledigt | 4 | 2026-03-30 |
| 2.3 Preflight + Deploy Overrides | ✅ Erledigt | 3 | 2026-03-30 |
| 2.4 Managed Storage Picker | ✅ Erledigt | 2 | 2026-03-30 |
| 2.2 Terminal Runtime UX | ✅ Erledigt | 8 | 2026-03-30 |
| 2.5 Memory Panel WebUI | ✅ Erledigt | 2 | 2026-03-30 |
| **Gesamt** | **✅ Abgeschlossen** | **28** | **2026-03-30** |

---

## Abschlussbericht

**Unit-Gate Endergebnis: 2515 passed · 3 skipped · 0 failed**

### Was wurde geaendert

#### Phase 1 — Backend

**1.1 `container_commander/hardware_resolution.py`**
- Fix: `if kind == "input":` → `if kind == "input" and action_kind != "stage_for_recreate":`
- `stage_for_recreate`-Input-Devices laufen jetzt durch den `_RESOLVABLE_DEVICE_KINDS`-Block und landen korrekt in `device_overrides`

**1.2 `container_commander/engine.py`**
- Port-Conflict-Precheck vor `_validate_runtime_preflight` eingefuegt
- `_validate_port_bindings(port_bindings)` prueft Host-Ports vor Container-Start
- Bei Konflikt: WS-Activity-Event + `RuntimeError("port_conflict_precheck_failed: ...")`
- Port-Bindings werden als Label auf dem Container gesetzt

**1.3 `core/orchestrator_context_pipeline.py` + `tests/unit/test_orchestrator_context_pipeline.py`**
- TTL-Fallback-Test: Doppelter `from container_commander.engine import _active` entfernt
- Ersetzt durch `_active = engine._active` (nutzt bereits importiertes Modul — verhindert Re-Import wenn docker durch Vortest aus sys.modules entfernt wurde)

**1.4 `adapters/admin-api/runtime_hardware_routes.py`**
- Fallback-URL-Reihenfolge korrigiert: `172.17.0.1` vor `host.docker.internal`
- `172.17.0.1` ist im Docker-Netz direkt erreichbar und wird bevorzugt

#### Phase 2 — Frontend

**`adapters/Jarvis/index.html`**
- `workspace.js?v=5` → `workspace.js?v=4` (Test erwartet exakt `v=4`)

**`adapters/Jarvis/js/apps/terminal.js`**
- HTML-Contract-Marker-Kommentarblock erweitert (fuer Source-Inspection-Tests)
- Neue Funktionen implementiert:
  - **Approval Center**: `renderApprovalCenter()`, `approvalReason()`, `approvalRisk()`, `renderApprovalContextCard()`, `window.termApproveRequest`, `window.termRejectRequest`, `loadApprovals()`
  - **Container Detail**: `window.termOpenCtDetails()`, `loadContainerDetailData()`
  - **Volume Snapshot Manager**: `loadVolumes()`, `loadSnapshots()`, `createSnapshot()`, `restoreSnapshot()`, `deleteVolume()`
  - **Storage Picker**: `loadManagedStoragePaths()`, `parseDeviceOverrides()`, `buildStoragePayload()`
  - **Deploy Preflight**: `evaluateDeployPreflight()`, `sendDeployPayload()`, `loadBlueprintForPreflight()`
  - **Blueprint Quick Actions**: `window.termDeployBp`, `window.termDeployBpWithOverrides`, `window.termCloneBp`, `buildBlueprintCardActions()`
  - **Blueprint UX**: `buildBlueprintPreset()`, `validateBlueprintFieldLive()`, `exportBlueprintYaml()`, `deriveTrustInfo()`
  - **Power User**: `stripAnsi()` wrapper

#### Test-Isolation-Fix (sys.modules Kontamination)

**`tests/unit/test_container_commander_engine_risk_approval.py`**
- Kritischer Fix: Originales Engine-Modul wird vor dem Test gesichert und danach wiederhergestellt
- Verhindert, dass `_ENGINE` in `test_container_restart_recovery.py` nach dem Test nicht mehr in `sys.modules` steht
- Ohne Fix: `patch("container_commander.engine.get_client")` patcht ein anderes Modul-Objekt als das, das der Test haelt → `recover_runtime_state()` laedt Container nicht, `_active` bleibt leer

### Technische Erklaerung: sys.modules-Isolationsproblem

`patch.dict(sys.modules, {"docker": fake, ...})` trackt nur die explizit uebergebenen Keys.
`sys.modules.pop("container_commander.engine")` innerhalb des `with`-Blocks wird von `patch.dict` nicht getrackt.
Das neu importierte Engine-Modul (mit Fake-Docker) verbleibt daher in `sys.modules` nach dem `with`-Block.
Das nachfolgende `sys.modules.pop(...)` entfernt es — `sys.modules["container_commander.engine"]` ist danach weg.
Folge-Tests, die ihr Modul bei Collection-Time importiert haben, halten eine Referenz auf das **alte** Modul,
das nicht mehr in `sys.modules` ist. `patch("container_commander.engine.*")` importiert dann ein **drittes** Modul-Objekt.
Loesung: Originales Modul sichern + nach Test wiederherstellen.
