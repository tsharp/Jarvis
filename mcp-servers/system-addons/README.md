# System-Addons MCP Server

Dieser MCP-Server gibt TRION sein **dynamisches Selbstwissen** — er ist die
Laufzeit-Schicht zu den statischen Docs in `intelligence_modules/system_addons/`.

## Wofür ist er da?

TRION kann bereits statisches Systemwissen aus Markdown-Docs laden (Topology,
Data-Locations, Auth-Model, Tool-Surface, Self-Extension). Was bisher fehlte:
ein Gedächtnis für das, was TRION **selbst gebaut oder eingerichtet** hat.

Dieser Server stellt genau das bereit:

| Ebene | Quelle | Zuständigkeit dieses Servers |
|---|---|---|
| Statisches Wissen | `intelligence_modules/system_addons/` | ❌ (nur Loader) |
| **Dynamisches Wissen** | `mcp-sql-memory` (SQLite) | ✅ Artifact Registry |
| Live-Zustand | Tools (`get_system_info` etc.) | ❌ (native Tools) |

## Artifact Registry

Die Kernfunktion: TRION registriert hier jedes Artefakt das es selbst erstellt.

```
create_skill erfolgreich   →  artifact_save(type="skill", name, purpose, related_secrets)
cron_create erfolgreich    →  artifact_save(type="cron",  name, purpose)
Skill gelöscht             →  artifact_update(name, status="removed")
Cron-Job gelöscht          →  artifact_update(name, status="removed")
```

Beim nächsten Neustart oder in einer neuen Session weiß TRION damit:
- welche Skills es selbst gebaut hat (und welche Secrets sie brauchen)
- welche Cron-Jobs es eingerichtet hat
- was noch aktiv ist vs. was gelöscht/deprecated wurde

## MCP-Tools

| Tool | Zweck |
|---|---|
| `artifact_save` | Artefakt anlegen oder aktualisieren (Upsert) |
| `artifact_list` | Alle bekannten Artefakte auflisten (gefiltert nach type/status) |
| `artifact_get` | Details zu einem Artefakt per Name |
| `artifact_update` | Status oder Meta eines Artefakts ändern |

## Architektur

```
TRION (Orchestrator)
        │
        │  MCP-Call (artifact_save / artifact_list / ...)
        ▼
mcp-servers/system-addons/server.py
        │
        │  CRUD
        ▼
sql-memory/memory_mcp/database.py  →  mcp-sql-memory (SQLite)
        │
        └── Tabelle: trion_artifact_registry
```

Der Server ist ein dünner MCP-Wrapper über die bereits implementierten
CRUD-Funktionen in `sql-memory/memory_mcp/database.py`.

## Drift-Schutz (geplant)

Der Loader in `intelligence_modules/system_addons/loader.py` prüft bei
Query-Class `self_extension` oder `data_locations`, ob registrierte Skills
noch in `list_skills` existieren. Falls nicht → Status `unverified`.

## Dateien

```
mcp-servers/system-addons/
├── README.md
└── system_addons_mcp/
    ├── __init__.py
    ├── server.py     ← FastMCP Entry-Point, nur register_tools() + mcp.run()
    ├── tools.py      ← 4 @mcp.tool Definitionen, Input-Validierung
    ├── models.py     ← Pydantic Response-Schemas (ArtifactRecord etc.)
    └── db_bridge.py  ← Wrapper um database.py CRUD + sys.path/DB_PATH
```

### Modul-Verantwortlichkeiten

| Modul | Verantwortung |
|---|---|
| `server.py` | FastMCP-Instanz + `register_tools()` — keine Business-Logik |
| `tools.py` | Tool-Handler: Input validieren, `db_bridge` aufrufen, Response bauen |
| `models.py` | Pydantic-Typen — zentral, damit `tools.py` sauber bleibt |
| `db_bridge.py` | Isoliert die `database.py`-Kopplung — `sys.path` + `DB_PATH` nur hier |

## Abhängigkeiten

- `sql-memory/memory_mcp/database.py` — CRUD-Funktionen (bereits implementiert)
- `mcp-sql-memory` Container — SQLite-DB mit `trion_artifact_registry`-Tabelle
- Port: **8090**
