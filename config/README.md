# TRION Config — Modulare Struktur

Die ursprüngliche `config.py` (1653 Zeilen, God-File) wurde in diese Verzeichnisstruktur aufgesplittet.
Jede Kategorie hat ein eigenes Unterverzeichnis mit einem `__init__.py` als Python-Modul.

> **Status:** Das kanonische Entry-Point ist jetzt `config/__init__.py`.
> Die alte Root-Datei `config.py` wurde entfernt.

---

## Verzeichnisübersicht

```
config/
├── infra/          ← Dienste, Endpunkte, Datenbank, CORS, Logging
├── models/         ← LLM-Modelle, Provider, Embedding-Konfiguration
├── pipeline/       ← Laufzeit-Schwellenwerte, Layer-Steuerung, Query-Budget
├── output/         ← Ausgabe-Caps, Timeouts, Deep-Jobs, Stream-Verhalten
├── autonomy/       ← Autonomie-Cron-System, Hardware-Guard
├── context/        ← Chunking, Small-Model-Mode, JIT-Retrieval, Context-Budget
├── features/       ← Feature-Flags, laufende Migrationen (TypedState, Signature)
├── digest/         ← Digest-Pipeline (Phase 8: Daily/Weekly/Archive-Komprimierung)
└── skills/         ← Skill-Management, Auto-Create-Policy, Secrets, Autosave-Dedupe
```

---

## Kategorien im Detail

### `infra/` — Infrastruktur & Dienste
**Was gehört hier rein:**
Reine Verbindungsparameter ohne Logik. Alles was einen Host, Port, Pfad oder CORS-Regel beschreibt.

**Enthält:**
- `ALLOW_ORIGINS`, `ENABLE_CORS`, `ALLOWED_ORIGINS`
- `OLLAMA_BASE`, `MCP_BASE`, `VALIDATOR_URL`, `DB_PATH`
- `LOG_LEVEL`
- `WORKSPACE_BASE`
- Settings-Adapter (`_EnvOnlySettingsFallback`, `settings`-Import)

**Leitprinzip:** Keine Schwellenwerte, keine Logik — nur "Wo ist was?"

---

### `models/` — LLM-Modelle & Provider
**Was gehört hier rein:**
Welches Modell wird für welche Rolle verwendet, und auf welchem Provider läuft es.

**Enthält:**
- `get_thinking_model()`, `get_control_model()`, `get_output_model()`
- `get_thinking_provider()`, `get_control_provider()`, `get_output_provider()`
- `get_control_model_deep()`, `_normalize_provider()`
- `get_embedding_model()`, `get_embedding_runtime_policy()`, `get_embedding_execution_mode()`
- `get_embedding_fallback_policy()`, `get_embedding_gpu_endpoint()`, `get_embedding_cpu_endpoint()`
- `get_embedding_endpoint_mode()`
- `get_tool_selector_model()`, `ENABLE_TOOL_SELECTOR`
- Rückwärts-kompatible Konstanten: `THINKING_MODEL`, `CONTROL_MODEL`, `OUTPUT_MODEL`, `EMBEDDING_MODEL`

**Leitprinzip:** "Wer macht was mit welchem Modell?" — kein Runtime-Tuning hier.

---

### `pipeline/` — Pipeline-Steuerung & Laufzeit-Thresholds
**Was gehört hier rein:**
Alle Schwellenwerte und Schalter, die das Verhalten der 3-Layer-Pipeline steuern.
Das ist das größte Modul — es enthält das Domain-Wissen der Orchestrierung.

**Enthält:**
- Tool-Selector: `get_tool_selector_candidate_limit()`, `get_tool_selector_min_similarity()`
- Tool-Injection: `get_output_tool_injection_mode()`, `get_output_tool_prompt_limit()`
- Response-Mode: `get_default_response_mode()`, `get_response_mode_sequential_threshold()`
- Query-Budget: `get_query_budget_enable()`, `get_query_budget_skip_thinking_min_confidence()`, etc.
- Domain-Router: `get_domain_router_enable()`, `get_domain_router_lock_min_confidence()`, etc.
- Policy-Conflict-Resolver: `get_policy_conflict_resolver_enable()`, Rollout-PCT
- Grounding: `get_grounding_auto_recovery_enable()`, Timeout, Whitelist
- Memory-Retrieval: `get_memory_lookup_timeout_s()`, `get_memory_keys_max_per_request()`
- Context-Limits: `get_effective_context_guardrail_chars()`, `get_context_retrieval_budget_s()`
- Follow-up-Reuse: TTL-Turns, TTL-Sekunden
- Loop-Engine: `get_loop_engine_trigger_complexity()`, min_tools, char_cap, max_predict
- Layer-Toggles: `ENABLE_CONTROL_LAYER`, `SKIP_CONTROL_ON_LOW_RISK`
- Control-Prompt-Sizing: user_chars, plan_chars, memory_chars
- Control-Endpoint: `get_control_endpoint_override()`
- Validation: `ENABLE_VALIDATION`, `VALIDATION_THRESHOLD`, `VALIDATION_HARD_FAIL`

**Leitprinzip:** "Wie entscheidet das System?" — Confidence-Werte, TTLs, Caps für die Pipeline-Logik.

---

### `output/` — Ausgabe-Verhalten & Job-Limits
**Was gehört hier rein:**
Alles was die finale Antwort an den User formt: Längen, Timeouts, Stream-Verhalten, Job-Kapazitäten.

**Enthält:**
- Char-Caps (hard): `get_output_char_cap_interactive()`, `_analytical()`, `_long()`, `get_output_char_cap_deep()`
- Char-Targets (soft): `get_output_char_target_interactive()`, `_analytical()`, `get_output_char_target_deep()`
- Timeouts: `get_output_timeout_interactive_s()`, `get_output_timeout_deep_s()`
- Sequential: `get_sequential_timeout_s()`
- Stream: `get_output_stream_postcheck_mode()`
- Tone: `get_tone_signal_override_confidence()`
- Deep-Jobs: `get_deep_job_timeout_s()`, `get_deep_job_max_concurrency()`
- Autonomy-Jobs: `get_autonomy_job_timeout_s()`, `get_autonomy_job_max_concurrency()`

**Leitprinzip:** "Wie lang, wie schnell, wie?" — Output-Form, nicht Pipeline-Logik.

---

### `autonomy/` — Autonomie-Cron & Hardware-Guard
**Was gehört hier rein:**
Das gesamte Cron-Scheduler-System für autonome, zeitgesteuerte Aufgaben, inklusive Hardware-Absicherung.

**Enthält:**
- State-Pfad, Tick-Interval: `get_autonomy_cron_state_path()`, `get_autonomy_cron_tick_s()`
- Kapazitäten: max_concurrency, max_jobs, max_jobs_per_conversation, max_pending_runs (gesamt + per_job)
- Limiter: min_interval_s, manual_run_cooldown_s
- TRION-Safe-Mode: safe_mode toggle, trion_min_interval_s, trion_max_loops
- Approval-Policy: `get_autonomy_cron_trion_require_approval_for_risky()`
- Hardware-Guard: `get_autonomy_cron_hardware_guard_enabled()`, cpu_max_percent, mem_max_percent

**Leitprinzip:** "Wann, wie oft, unter welchen Bedingungen läuft ein autonomer Job?"

---

### `context/` — Kontext-Aufbau & Small-Model-Mode
**Was gehört hier rein:**
Alles was bestimmt, wie viel Kontext gebaut wird und wie dieser für kleine Modelle komprimiert wird.

**Enthält:**
- Chunking: `CHUNKING_THRESHOLD`, `CHUNK_MAX_TOKENS`, `CHUNK_OVERLAP_TOKENS`, `ENABLE_CHUNKING`
- Small-Model-Mode: `get_small_model_mode()`, now/rules/next_max, char_cap
- Small-Model-Policies: skill_prefetch_policy, skill_prefetch_thin_cap, detection_rules_policy
- Small-Model-Limits: detection_rules_thin_lines/chars, final_cap, tool_ctx_cap
- JIT-Retrieval: `get_jit_retrieval_max()`, `get_jit_retrieval_max_on_failure()`
- Context-Trace: `get_context_trace_dryrun()`
- Memory-Fallback: `get_context_memory_fallback_recall_only_enable()`, rollout_pct
- Daily-Context: `get_daily_context_followup_enable()`

**Leitprinzip:** "Wie groß ist der Kontext, und wie wird er für kleine Modelle zurechtgeschnitten?"

---

### `features/` — Feature-Flags & Migrationen
**Was gehört hier rein:**
Temporäre Schalter für laufende Migrations-Phasen. Einträge hier sind **vergänglich** —
sie wandern nach Abschluss der Migration in ihr jeweiliges Heimat-Modul oder werden gelöscht.

**Enthält:**
- TypedState V1: `get_typedstate_mode()`, `get_typedstate_enable_small_only()`
- TypedState CSV: `get_typedstate_csv_path()`, `get_typedstate_csv_enable()`, `get_typedstate_csv_jit_only()`
- TypedState Skills: `get_typedstate_skills_mode()`
- Signature-Verify: `get_signature_verify_mode()`, `SIGNATURE_VERIFY_MODE`

**Leitprinzip:** "Ist dieses Feature fertig migriert? Dann gehört der Schalter NICHT mehr hier her."

---

### `digest/` — Digest-Pipeline (Phase 8)
**Was gehört hier rein:**
Das komplette Daily/Weekly/Archive-Komprimierungs-System für Langzeit-Memory.

**Enthält:**
- Master-Toggle + Sub-Toggles: `get_digest_enable()`, `_daily_enable()`, `_weekly_enable()`, `_archive_enable()`
- Zeitzone & Pfade: `get_digest_tz()`, `get_digest_store_path()`, `get_digest_state_path()`, `get_digest_lock_path()`
- Lock-Management: `get_digest_lock_timeout_s()`
- Betriebsmodus: `get_digest_run_mode()`, `get_digest_catchup_max_days()`
- Qualitätsschwellen: `get_digest_min_events_daily()`, `get_digest_min_daily_per_week()`
- UI & API: `get_digest_ui_enable()`, `get_digest_runtime_api_v2()`
- Filter & Dedupe: `get_digest_filters_enable()`, `get_digest_dedupe_include_conv()`
- JIT-Fenster: `get_jit_window_time_reference_h()`, `_fact_recall_h()`, `_remember_h()`
- Hardening: `get_digest_jit_warn_on_disabled()`, `get_digest_key_version()`

**Leitprinzip:** "Alles was Phase 8 braucht — isoliert, damit die Komplexität nicht ausblutet."

---

### `skills/` — Skill-Management, Secrets & Autosave
**Was gehört hier rein:**
Policies für das Skill-System: Wie werden Skills ausgewählt, erstellt, gesichert und dedupliziert.

**Enthält:**
- Graph & Keys: `get_skill_graph_reconcile()`, `get_skill_key_mode()`, `get_skill_control_authority()`
- Rendering: `get_skill_context_renderer()`, `get_typedstate_skills_mode()`
- Selektion: `get_skill_selection_mode()`, `get_skill_selection_top_k()`, `get_skill_selection_char_cap()`
- Pakete & Discovery: `get_skill_package_install_mode()`, `get_skill_discovery_enable()`
- Auto-Create-Policy: `get_skill_auto_create_on_low_risk()`
- Secrets (C8): `get_skill_secret_enforcement()`, `get_secret_resolve_token()`, `get_secret_rate_limit()`
- Secret-Cache: `get_secret_resolve_miss_ttl_s()`, `get_secret_resolve_not_found_ttl_s()`
- Autosave-Dedupe: `get_autosave_dedupe_enable()`, `_window_s()`, `_max_entries()`

**Leitprinzip:** "Wie verhält sich das Skill-System und wie schützt es sich selbst?"

---

## Migrations-Strategie

Die Migration passierte **schrittweise**, nicht als Big-Bang-Rewrite:

1. Modul schreiben (z.B. `config/models/__init__.py`) — Inhalt aus dem Monolithen kopieren
2. Vorübergehend einen Compat-Shim für bestehende `import config`-Aufrufe bereitstellen
   ```python
   # temporärer Compat-Shim
   from config.models import get_thinking_model, get_output_model  # noqa: F401
   ```
3. Tests grün halten — bestehende `import config` Aufrufe funktionieren weiterhin
4. Schrittweise alle direkten Imports im System auf `config.models` umstellen
5. Wenn alle Imports migriert: Root-Shim löschen und `config/__init__.py` als einzige Wahrheit behalten
