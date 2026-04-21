# System Addons — TRION Selbstwissen

Dieses Modul gibt TRION ein maschinenlesbares Selbstbild über sein eigenes System.
Es folgt dem bewährten Muster von `container_addons` und `skill_addons`:
Lazy Loading, Query-Class-gesteuert, nur relevante Abschnitte, statisches Wissen
streng getrennt von Live-Zustand.

## Motivation

TRION hat bereits:
- Live-Tool-Wissen (`list_live_tools()`, MCP-Registry)
- Hardware-/Docker-Info (`get_system_info`, `get_system_overview`)
- Skill-Inventar (`list_skills`, semantischer Kontext)
- Autonomy-Status-Endpoint (`/api/runtime/autonomy-status`)

Was fehlt ist die **verbindende Schicht**: ein konsistentes Selbstbild das erklärt
wo welche Daten liegen, welche Endpoints existieren, welche Auth-Regeln gelten
und wie TRION sich sicher selbst erweitern kann.

Ohne diese Schicht rät TRION — z. B. "ich schaue in meinem Container nach API-Keys",
obwohl Secrets nie im Dateisystem liegen, sondern verschlüsselt in der SQL-Memory-DB.

## Drei Wissensebenen

```
┌─────────────────────────────────────────────────────────────┐
│  Ebene 1 — Statisches Selbstwissen (topology/ + self_extension/)
│  Markdown-Addons, von Menschen gepflegt.                    │
│  "Secrets liegen in mcp-sql-memory."                        │
│  "Admin-API ist unter http://jarvis-admin-api:8200."        │
├─────────────────────────────────────────────────────────────┤
│  Ebene 2 — Dynamisches Selbstwissen (artifact_registry)     │
│  SQLite-Tabelle in mcp-sql-memory, von TRION geschrieben.   │
│  "Ich habe Skill ingest-pipeline erstellt (OPENAI_KEY)."    │
│  "Ich habe Cron daily-summary eingerichtet."                │
├─────────────────────────────────────────────────────────────┤
│  Ebene 3 — Live-Zustand (Tools)                             │
│  Immer aus Tools, nie aus Addons oder Registry.             │
│  get_system_info / list_skills / container_list / ...       │
└─────────────────────────────────────────────────────────────┘
```

**Trennungsprinzip (gilt für alle drei Ebenen):**
- Ebene 1+2 erklären WO etwas liegt und WAS TRION erstellt hat.
- Ebene 1+2 behaupten NIE ob ein Service gerade läuft oder erreichbar ist.
- Ebene 3 (Live-Tools) ist immer die einzige Wahrheitsquelle für aktuellen Zustand.

---

## Ebene 1 — Statische Addons

### Verzeichnisstruktur

```
system_addons/
├── README.md                     ← diese Datei
├── ADDON_SPEC.md                 ← Dateiformat, Frontmatter-Felder, Scope-Werte
├── loader.py                     ← Retrieval-Engine (analog container_addons/loader.py)
├── topology/                     ← statisches Topologie-Wissen
│   ├── 00-services.md            ← Services, URLs, Ports, Docker-Netz
│   ├── 10-data-locations.md      ← wo liegen Secrets, Skills, Blueprints, Workspace
│   ├── 20-auth-model.md          ← interner Token, Docker-Netz-only Endpoints
│   └── 30-tool-surface.md        ← welche Tools/Endpoints TRION aufrufen kann
└── self_extension/
    ├── 00-skill-lifecycle.md     ← create → validate → run, was der Runner macht
    ├── 10-safe-paths.md          ← was TRION selbst erweitern darf (und was nicht)
    └── 20-alias-model.md         ← Alias-Logik in skill_runner (TEST_KEY ↔ TEST_API_KEY)
```

### Query-Classes

Der Loader lädt nur was zur aktuellen Frage passt:

| Query-Class | Wann aktiv | Relevante Docs |
|---|---|---|
| `system_topology` | "welche services", "läuft X", "auf welchem port" | `topology/00-services.md` |
| `data_locations` | "wo liegen", "api key", "secrets", "blueprints" | `topology/10-data-locations.md` |
| `auth_model` | "auth", "token", "credentials", "zugriff" | `topology/20-auth-model.md` |
| `tool_surface` | "welche tools", "endpoints", "kann ich X aufrufen" | `topology/30-tool-surface.md` |
| `self_extension` | "skill erstellen", "reparieren", "selbst bauen", "lücke" | `self_extension/*` |

### Addon-Dateiformat

Jede Addon-Datei ist eine Markdown-Datei mit YAML-Frontmatter.
Details siehe `ADDON_SPEC.md`.

Gültige `scope`-Werte:

| Scope | Inhalt |
|---|---|
| `topology` | Service-Layout, Docker-Netz, Ports |
| `data_locations` | Wo welche Daten gespeichert sind |
| `auth_model` | Auth-Mechanismen, Token-Grenzen |
| `tool_surface` | Verfügbare Tools und Endpoints |
| `skill_lifecycle` | Skill create/validate/run Ablauf |
| `safe_paths` | Was TRION selbst erweitern darf |
| `alias_model` | Secret-Alias-Logik im Skill-Runner |

---

## Ebene 2 — Dynamisches Selbstwissen (Artifact Registry)

### Warum nicht Markdown oder CSV?

| | Markdown | CSV | SQLite |
|---|---|---|---|
| TRION kann schreiben | ✅ `home_write` | ⚠️ nur append | ✅ via MCP-Tool |
| Querybar | ❌ | ⚠️ simpel | ✅ |
| Relationen ("Skills die OPENAI_KEY nutzen") | ❌ | ❌ | ✅ |
| Schema-Enforcement | ❌ | ❌ | ✅ |
| Drift-Erkennung via `status`-Feld | ❌ | ❌ | ✅ |
| Schon im System | — | — | ✅ mcp-sql-memory |

**Entscheidung: SQLite via `mcp-sql-memory`** — die Infrastruktur ist bereits vorhanden.

### Tabelle: `trion_artifact_registry`

```sql
CREATE TABLE trion_artifact_registry (
    id          TEXT PRIMARY KEY,         -- z. B. "skill-ingest-pipeline"
    type        TEXT NOT NULL,            -- "skill" | "cron" | "mcp_wrapper" | "config"
    name        TEXT NOT NULL,
    purpose     TEXT,                     -- warum wurde es erstellt
    related_secrets TEXT,                 -- komma-separierte Secret-Namen (nur Namen!)
    depends_on  TEXT,                     -- andere Artefakt-IDs
    created_at  TEXT NOT NULL,            -- ISO 8601
    updated_at  TEXT,
    status      TEXT DEFAULT 'active',    -- "active" | "deprecated" | "removed"
    meta        TEXT                      -- JSON für alles weitere
);
```

### Neue MCP-Tools (in mcp-sql-memory)

| Tool | Zweck | Wer ruft es auf |
|---|---|---|
| `artifact_save(type, name, purpose, meta)` | Artefakt registrieren oder aktualisieren | TRION nach create_skill / cron_create / etc. |
| `artifact_list(type?, status?)` | Alle bekannten Artefakte auflisten | Loader, TRION bei Selbst-Inventur |
| `artifact_get(name)` | Details zu einem Artefakt | TRION bei Detailfragen |
| `artifact_update(name, status, meta)` | Status setzen (z. B. "removed") | TRION nach Löschen |

### Wann TRION schreibt

| Aktion | TRION ruft auf |
|---|---|
| `create_skill` erfolgreich | `artifact_save(type="skill", ...)` |
| `autonomy_cron_create_job` erfolgreich | `artifact_save(type="cron", ...)` |
| Skill löschen | `artifact_update(name, status="removed")` |
| Cron-Job löschen | `artifact_update(name, status="removed")` |

### Loader-Integration

Der `loader.py` fragt bei Query-Class `self_extension` oder `data_locations`
zusätzlich `artifact_list()` ab und mischt relevante Registry-Einträge
als strukturierten Block in den Kontext ein.

Einträge mit `status="removed"` werden nicht eingespeist.
Einträge mit `status="deprecated"` werden mit Hinweis eingespeist.

### Drift-Schutz

Beim Laden prüft der Loader: existiert ein Artefakt mit `type="skill"` noch
wirklich in `list_skills`? Falls nicht → Status automatisch auf `unverified`
setzen und in der Einspeisung markieren. TRION sieht dann:
`[unverified] skill ingest-pipeline — nicht mehr in list_skills gefunden`.

---

## Integration (geplant)

Analog zu `container_addons`:

1. **Loader** (`loader.py`) — Query-Class + Intent-Text → statische Docs + Registry-Einträge
2. **Orchestrator-Hook** — wird nur aufgerufen wenn Query-Class erkannt wird
3. **Kontext-Einspeisung** — wie `_container_addon_context` im Orchestrator-Kontext
4. **Schreib-Convention** — TRION ruft `artifact_save` nach jedem erfolgreichen Create auf

---

## Implementierungsplan

### Phase 1 — Statisches Wissen (aktuell)
- [x] Verzeichnisstruktur anlegen
- [x] ADDON_SPEC.md schreiben
- [x] Platzhalter-Docs anlegen
- [x] Topology-Docs füllen (00–30) — via ChatGPT-Prompt + manuell
- [x] Self-Extension-Docs füllen (00–20)
- [ ] loader.py implementieren (analog container_addons/loader.py)
- [ ] Query-Class-Erkennung im Orchestrator-Kontext verdrahten
- [ ] Tests für Loader schreiben

### Phase 2 — Dynamisches Wissen (Artifact Registry)
- [ ] Tabelle `trion_artifact_registry` in mcp-sql-memory anlegen
- [ ] MCP-Tools implementieren: `artifact_save`, `artifact_list`, `artifact_get`, `artifact_update`
- [ ] Loader um Registry-Abfrage erweitern
- [ ] Drift-Guard implementieren (unverified-Markierung)
- [ ] TRION-Convention verankern: nach create_skill/cron_create → artifact_save
- [ ] Tests für Registry-Tools schreiben

### Phase 3 — Orchestrator-Integration
- [ ] Simple-Task-Loop-Trigger für Selbstwissen-Fragen
- [ ] `list_secret_names` Tool registrieren (Vault-Namen, nie Werte)
- [ ] System-Addon-Kontext in Orchestrator-Pipeline einspeisen
