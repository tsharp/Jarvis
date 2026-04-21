---
id: system-skill-lifecycle
title: Skill-Lifecycle — create, validate, run
scope: skill_lifecycle
tags:
  - skill
  - create_skill
  - run_skill
  - validate
  - lifecycle
priority: 85
retrieval_hints:
  - skill erstellen
  - neuen skill
  - skill lifecycle
  - create skill
  - skill runner
  - was macht der runner
  - wie funktionieren skills
  - skill speichern
confidence: high
last_reviewed: 2026-04-20
---

# Skill-Lifecycle

## Summary
Skills sind isolierte, sandboxed Python-Module die TRION's Fähigkeiten erweitern.
Der komplette Lifecycle läuft über zwei Services: `trion-skill-server` (MCP, Port 8088)
und `tool-executor` (REST, Port 8000).

## Ablauf: create → validate → run

```
create_skill(name, code, description)
        │
        ▼
[skill-server] 1. Package-Check
        │      Fehlende Pakete gegen ALLOWED_MODULES-Allowlist prüfen
        │      Nicht-allowlisted → BLOCK, kein Executor-Call
        │
        ▼
[skill-server] 2. Secret-Scanner (C8)
        │      Prüft ob Klartext-Secrets im Code stehen
        │      Gefunden → BLOCK mit Fehlermeldung
        │
        ▼
[skill-server] 3. CIM-Validation (mini_control_layer)
        │      Policy-Entscheidung: APPROVE / WARN / BLOCK
        │      BLOCK → kein Executor-Call
        │
        ▼
[tool-executor] 4. Persistierung
        │       Skill-Code wird unter /skills/{name}/ gespeichert
        │       auto_promote=True (default) → sofort aktiv
        │       auto_promote=False → Draft-Modus, erst nach promote aktiv
        │
        ▼
        ✅ Skill verfügbar via list_skills + run_skill
```

## Ausführung: run_skill

```
run_skill(name, action, args)
        │
        ▼
[tool-executor/skill_runner.py]
        │
        ├── Sandbox-Globals aufbauen:
        │   get_secret = _get_secret (injiziert)
        │   __builtins__ = eingeschränkt (kein eval, exec, open, ...)
        │   __import__ = restricted_import (nur ALLOWED_MODULES)
        │
        ├── Code kompilieren + exec() in restricted_globals
        │
        └── action-Funktion aufrufen (default: "run")
```

## Sandbox-Grenzen

**Erlaubte Module:**
`json`, `math`, `datetime`, `re`, `asyncio`, `requests`, `httpx`, `aiohttp`,
`numpy`, `pandas`, `scipy`, `PIL`, `bs4`, `psutil`, `platform`, u. a.

**Blockierte Module:**
`os`, `sys`, `subprocess`, `shutil`, `pathlib`, `socket`, `pickle`,
`ctypes`, `multiprocessing`, `importlib`

**Blockierte Builtins:**
`eval`, `exec`, `compile`, `open`, `__import__`, `globals`, `locals`,
`vars`, `dir`, `getattr`, `setattr`, `delattr`, `input`, `breakpoint`

## Wo Skills gespeichert werden

- Skill-Code: `tool-executor` Container unter `/skills/{name}/`
- Metadaten + Drafts: `trion-skill-server` (`SkillManager`)
- Listing: `list_skills` MCP-Tool → fragt `trion-skill-server` ab

## Draft-Modus

- `auto_promote=False` → Skill wird als Draft gespeichert, nicht in `list_skills` sichtbar
- Draft fördern: `promote_skill_draft(name)`
- Draft einsehen: `list_draft_skills`, `get_skill_draft(name)`

## Zugriff für TRION

| Ziel | Tool |
|---|---|
| Neuen Skill erstellen | `create_skill(name, code, description)` |
| Skill-Code vorab prüfen | `validate_skill_code(code)` |
| Skill ausführen | `run_skill(name, action?, args?)` |
| Installierte Skills auflisten | `list_skills` |
| Details zu einem Skill | `get_skill_info(name)` |

## Grenzen

- Kein Filesystem-Zugriff im Skill-Code (kein `open`, kein `pathlib`)
- Kein Netzwerk-Socket direkt (nur HTTP via `requests`/`httpx`)
- Kein Zugriff auf Host-Prozesse (`os`, `subprocess` blockiert)
- Secret-Klartext-Werte niemals in den Skill-Code schreiben — Scanner blockiert das
