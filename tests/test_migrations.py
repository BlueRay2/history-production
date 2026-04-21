"""Tests for app.db migrator.

Covers:
  - fresh DB: migrate applies all, returns count.
  - re-run migrate: no-op on fully-applied state.
  - tampered migration (content hash mismatch): errors.
  - PRAGMA foreign_keys=ON is actually enforced by connect().
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

import pytest

from app import db as dbmod


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    yield db_file


def test_migrate_applies_all_on_fresh_db(fresh_db):
    applied = dbmod.migrate()
    assert applied >= 1, "at least migration 001 should apply"
    with dbmod.connect() as conn:
        rows = [r["version"] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
    assert "001" in rows


def test_migrate_is_idempotent(fresh_db):
    first = dbmod.migrate()
    second = dbmod.migrate()
    assert second == 0, "second migrate should be no-op"
    assert first >= 1


def test_migrate_detects_tampered_migration(fresh_db):
    dbmod.migrate()
    # Simulate tamper: overwrite the stored sha256 with a bogus value.
    with dbmod.connect() as conn:
        conn.execute("UPDATE schema_migrations SET sha256='deadbeef' WHERE version='001'")
    with pytest.raises(RuntimeError, match="different content"):
        dbmod.migrate()


def test_foreign_keys_enforced(fresh_db):
    dbmod.migrate()
    with dbmod.connect() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO video_project_map(city_slug, video_id, confidence, mapping_source, active) "
                "VALUES ('ghost', 'nothere', 0.5, 'auto', 0)"
            )


def test_wal_mode_enabled(fresh_db):
    dbmod.migrate()
    with dbmod.connect() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_schema_migrations_table_shape(fresh_db):
    dbmod.migrate()
    with dbmod.connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(schema_migrations)")}
    assert cols == {"version", "applied_at", "sha256"}
