"""
System-Addons — DB Bridge
══════════════════════════
Kapselt den Zugriff auf sql-memory/memory_mcp/database.py.
Löst sys.path + DB_PATH aus Env-Var — einzige Stelle wo diese Kopplung sitzt.

Exportiert: artifact_save, artifact_get, artifact_list, artifact_update
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict

# Locate sql-memory relative to this file or via env override
_SQL_MEMORY_ROOT = os.environ.get(
    "SQL_MEMORY_ROOT",
    str(Path(__file__).resolve().parents[3] / "sql-memory"),
)
if _SQL_MEMORY_ROOT not in sys.path:
    sys.path.insert(0, _SQL_MEMORY_ROOT)

# DB_PATH must be set before importing database (it reads config on import)
_DB_PATH = os.environ.get("SQL_MEMORY_DB_PATH", "/data/memory.db")
os.environ.setdefault("SQL_MEMORY_DB_PATH", _DB_PATH)

import importlib
_db = importlib.import_module("memory_mcp.database")


def artifact_save(
    type: str,
    name: str,
    purpose: Optional[str] = None,
    related_secrets: Optional[str] = None,
    depends_on: Optional[str] = None,
    meta: Optional[str] = None,
) -> str:
    return _db.artifact_save(
        type=type,
        name=name,
        purpose=purpose,
        related_secrets=related_secrets,
        depends_on=depends_on,
        meta=meta,
    )


def artifact_get(name: str) -> Optional[Dict]:
    return _db.artifact_get(name=name)


def artifact_list(
    type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict]:
    return _db.artifact_list(type=type, status=status, limit=limit)


def artifact_update(
    name: str,
    status: Optional[str] = None,
    meta: Optional[str] = None,
) -> bool:
    return _db.artifact_update(name=name, status=status, meta=meta)
