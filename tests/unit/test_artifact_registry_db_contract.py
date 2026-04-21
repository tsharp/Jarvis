"""Contract-Tests für trion_artifact_registry in database.py."""
import importlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SQL_MEMORY_ROOT = str(_ROOT / "sql-memory")


def _load_db_module(db_path: str):
    if _SQL_MEMORY_ROOT not in sys.path:
        sys.path.insert(0, _SQL_MEMORY_ROOT)
    os.environ["DB_PATH"] = db_path
    cfg = importlib.import_module("memory_mcp.config")
    db = importlib.import_module("memory_mcp.database")
    importlib.reload(cfg)
    importlib.reload(db)
    return db


@pytest.fixture()
def fresh_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    db = _load_db_module(db_path)
    db.init_db()
    return db


# ── Tabellen-Struktur ───────────────────────────────────────────────────────

def test_table_created_by_init_db(fresh_db, tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    conn.close()
    assert "trion_artifact_registry" in tables


def test_indexes_created(fresh_db, tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    indexes = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_artifact%'"
    ).fetchall()]
    conn.close()
    assert "idx_artifact_type" in indexes
    assert "idx_artifact_name" in indexes
    assert "idx_artifact_status" in indexes


def test_schema_has_required_columns(fresh_db, tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    cols = {r[1] for r in conn.execute(
        "PRAGMA table_info(trion_artifact_registry)"
    ).fetchall()}
    conn.close()
    required = {"id", "type", "name", "purpose", "related_secrets",
                "depends_on", "created_at", "updated_at", "status", "meta"}
    assert required.issubset(cols)


# ── artifact_save ───────────────────────────────────────────────────────────

def test_artifact_save_returns_generated_id(fresh_db):
    aid = fresh_db.artifact_save("skill", "my-skill")
    assert aid == "skill-my-skill"


def test_artifact_save_status_is_active_by_default(fresh_db):
    fresh_db.artifact_save("skill", "my-skill")
    row = fresh_db.artifact_get("my-skill")
    assert row["status"] == "active"


def test_artifact_save_stores_purpose_and_secrets(fresh_db):
    fresh_db.artifact_save("skill", "ingest", purpose="PDF ingestion", related_secrets="OPENAI_KEY")
    row = fresh_db.artifact_get("ingest")
    assert row["purpose"] == "PDF ingestion"
    assert row["related_secrets"] == "OPENAI_KEY"


def test_artifact_save_upserts_on_second_call(fresh_db):
    fresh_db.artifact_save("skill", "my-skill", purpose="v1")
    fresh_db.artifact_save("skill", "my-skill", purpose="v2")
    rows = fresh_db.artifact_list(type="skill")
    assert len(rows) == 1
    assert rows[0]["purpose"] == "v2"


def test_artifact_save_accepts_custom_id(fresh_db):
    aid = fresh_db.artifact_save("skill", "my-skill", artifact_id="custom-id-123")
    assert aid == "custom-id-123"
    row = fresh_db.artifact_get("my-skill")
    assert row["id"] == "custom-id-123"


# ── artifact_get ────────────────────────────────────────────────────────────

def test_artifact_get_returns_none_for_unknown(fresh_db):
    assert fresh_db.artifact_get("does-not-exist") is None


def test_artifact_get_returns_correct_row(fresh_db):
    fresh_db.artifact_save("skill", "pipeline", purpose="v1")
    row = fresh_db.artifact_get("pipeline")
    assert row is not None
    assert row["name"] == "pipeline"
    assert row["type"] == "skill"


# ── artifact_list ───────────────────────────────────────────────────────────

def test_artifact_list_excludes_removed_by_default(fresh_db):
    fresh_db.artifact_save("skill", "active-skill")
    fresh_db.artifact_save("cron", "dead-job")
    fresh_db.artifact_update("dead-job", status="removed")
    rows = fresh_db.artifact_list()
    names = [r["name"] for r in rows]
    assert "active-skill" in names
    assert "dead-job" not in names


def test_artifact_list_includes_deprecated_by_default(fresh_db):
    fresh_db.artifact_save("skill", "old-skill")
    fresh_db.artifact_update("old-skill", status="deprecated")
    rows = fresh_db.artifact_list()
    assert any(r["name"] == "old-skill" for r in rows)


def test_artifact_list_filter_by_type(fresh_db):
    fresh_db.artifact_save("skill", "s1")
    fresh_db.artifact_save("cron", "c1")
    skill_rows = fresh_db.artifact_list(type="skill")
    assert all(r["type"] == "skill" for r in skill_rows)
    assert len(skill_rows) == 1


def test_artifact_list_filter_by_status(fresh_db):
    fresh_db.artifact_save("skill", "s1")
    fresh_db.artifact_save("skill", "s2")
    fresh_db.artifact_update("s2", status="removed")
    removed = fresh_db.artifact_list(status="removed")
    assert len(removed) == 1
    assert removed[0]["name"] == "s2"


# ── artifact_update ─────────────────────────────────────────────────────────

def test_artifact_update_status(fresh_db):
    fresh_db.artifact_save("skill", "my-skill")
    result = fresh_db.artifact_update("my-skill", status="removed")
    assert result is True
    row = fresh_db.artifact_get("my-skill")
    assert row["status"] == "removed"


def test_artifact_update_returns_false_for_unknown(fresh_db):
    result = fresh_db.artifact_update("does-not-exist", status="removed")
    assert result is False


def test_artifact_update_meta(fresh_db):
    fresh_db.artifact_save("skill", "my-skill")
    fresh_db.artifact_update("my-skill", meta='{"version": "2"}')
    row = fresh_db.artifact_get("my-skill")
    assert row["meta"] == '{"version": "2"}'


# ── migrate_db ──────────────────────────────────────────────────────────────

def test_migrate_db_creates_table_on_old_db(tmp_path):
    db_path = str(tmp_path / "old.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE memory (id INTEGER PRIMARY KEY, content TEXT)")
    conn.execute("CREATE TABLE facts (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    db = _load_db_module(db_path)
    db.migrate_db()

    conn = sqlite3.connect(db_path)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    conn.close()
    assert "trion_artifact_registry" in tables
