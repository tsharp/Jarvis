---
Tags: [TRION, Refactoring, Config, Technical-Debt]
aliases: [Config, config.py]
---

> [!success] Phase 1 abgeschlossen (2026-04-13)
> Die `config.py` (1654 Zeilen) wurde in **9 Packages / 33 Module** aufgesplittet.
> Alle bestehenden `import config` Aufrufe funktionieren weiterhin über den Compat-Shim (`config/__init__.py`).
> Struktur: `config/infra` · `config/models` · `config/pipeline` · `config/output` · `config/autonomy` · `config/context` · `config/features` · `config/digest` · `config/skills`

> [!warning] Phase 2 offen — Magic Numbers
> Die Schwellenwerte liegen jetzt in sauberen Modulen, gehören aber langfristig direkt in die Core-Module die sie verwenden — nicht in die Config:
> - `TOOL_SELECTOR_MIN_SIMILARITY` (0.45) → `core/tool_selector.py`
> - `QUERY_BUDGET_SKIP_THINKING_MIN_CONFIDENCE` (0.90) → `core/layers/thinking.py`
> - `TONE_SIGNAL_OVERRIDE_CONFIDENCE` (0.82) → `core/layers/thinking.py`
> - `LOOP_ENGINE_TRIGGER_COMPLEXITY` (8) → `core/task_loop/`

# ⚙️ Das `config.py` Monstrum (1654 Zeilen)

Die Datei `config.py` in TRION ist ein klassisches Beispiel für ein "God-Object" auf Konfigurations-Ebene. Anstatt nur Umgebungsvariablen wie Ports oder Datenbankpfade zu speichern, übernimmt die Datei die Rolle eines **Feature-Flag-Systems**, einer **Hyperparameter-Registry** und eines **Policy-Managers**.

## 🔍 1. Was steckt wirklich in der Config?

Die Datei ist nicht einfach nur ein Dictionary, sondern besteht aus hunderten von `get_...()` Funktionen, die Fallbacks, Limits und sogar Logikschalter (`Rollout Percentages`) berechnen.

### 🌐 A. Infrastruktur & Modelle (Das Erwartbare)
- **Modelle:** `ministral-3:8b` (Thinking & Control), `qwen2.5:1.5b` (Tool Selector).
- **Embedding:** `hellord/mxbai-embed-large-v1:f16`
- **Endpunkte:** OLLAMA_BASE, MCP_BASE, DB_PATH.

### 🧠 B. Machine Learning Hyper-Parameter
Die Config mischt sich in die Agenten-Logik ein, indem sie magische Schwellenwerte für das LLM hartkodiert:
- `TOOL_SELECTOR_MIN_SIMILARITY` (0.45)
- `QUERY_BUDGET_SKIP_THINKING_MIN_CONFIDENCE` (0.90)
- `TONE_SIGNAL_OVERRIDE_CONFIDENCE` (0.82)
- `LOOP_ENGINE_TRIGGER_COMPLEXITY` (8)

> [!warning] Architecture Smell: Magic Numbers
> Diese Werte steuern, wann das System Entscheidungen abkürzt oder Schleifen dreht. Aktuell sind diese Werte global in der Config zementiert, statt in den jeweiligen Modulen (`tool_selector.py` oder `control.py`), zu denen sie eigentlich gehören.

### 🎛️ C. Feature Flags & Migrationen
Die Config ist voller Schalter für parallele Entwicklungs-Phasen:
- `TYPEDSTATE_MODE` ("off", "shadow", "active") -> *Zeigt eine unfertige Migration.*
- `SMALL_MODEL_MODE` -> *Ein extrem komplexer Schalter, der den Kontext hart auf 2000 Zeichen stutzt und Regeln für kleine Modelle neu definiert.*
- `DIGEST PIPELINE` (Phase 8) -> *Ein ganzes Ökosystem für CRON-Digests (Daily, Weekly, Archive), das über zig Flags in der Config gesteuert wird.*

### 🛡️ D. Domain-Regeln (Hardware & Security)
Anstatt die Hardware-Überwachung im Orchestrator oder Executor zu belassen, regelt die global Config:
- `AUTONOMY_CRON_HARDWARE_CPU_MAX_PERCENT` (90)
- `SKILL_AUTO_CREATE_ON_LOW_RISK`

---

## 🛠️ 2. Das Refactoring-Potenzial (Wie man es aufräumt)

Die größte Gefahr dieser Datei ist: **Jedes Modul im System importiert die `config.py`.** Das führt zu extremer Kopplung. Wenn sich eine Policy ändert, hängt das halbe System am Tropf der Config.

> [!info] Lösungsansatz: Namespacing & Aufsplittung
> Die Datei sollte in modulare Configs zerlegt werden (z. B. via Pydantic `BaseSettings`):

1. `config/env.py`: Purer Infrastruktur-Code (Ports, DB-Pfade, OLLAMA_BASE).
2. `config/models.py`: Nur die LLM- und Embedding-Zuweisungen.
3. `config/policies.py` (oder `hyperparams.py`): Die Schwellenwerte (`MIN_CONFIDENCE`, `CHAR_CAPS`).
4. `config/features.py`: Die hartkodierten Feature-Flags für laufende Migrationen (`TYPEDSTATE`, `DIGEST`).
