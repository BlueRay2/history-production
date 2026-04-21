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


def test_full_kpi_schema_shape(fresh_db):
    """Asserts all 8 KPI tables + 5 indexes + key FKs land from migration 001.

    Addresses Codex round-1 finding [medium]: previous tests would pass even if
    a required table/FK/index were missing. This test catches regressions in
    the schema promised by task-01.
    """
    dbmod.migrate()
    expected_tables = {
        "schema_migrations",
        "videos",
        "projects",
        "video_project_map",
        "ingestion_runs",
        "channel_metric_snapshots",
        "video_metric_snapshots",
        "video_retention_points",
        "git_events",
    }
    expected_indexes = {
        "idx_channel_metric_latest",
        "idx_video_metric_latest",
        "idx_git_events_city_type",
        "idx_vpm_video_active",
        "idx_vpm_city_active",
    }
    with dbmod.connect() as conn:
        tables = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        indexes = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            )
        }
        # Key FK edges we promised
        vpm_fks = list(conn.execute("PRAGMA foreign_key_list(video_project_map)"))
        vms_fks = list(conn.execute("PRAGMA foreign_key_list(video_metric_snapshots)"))
        ge_fks = list(conn.execute("PRAGMA foreign_key_list(git_events)"))
    assert expected_tables.issubset(tables), f"missing tables: {expected_tables - tables}"
    assert expected_indexes.issubset(indexes), f"missing indexes: {expected_indexes - indexes}"
    # video_project_map: both FKs must exist
    fk_targets_vpm = {(fk["table"], fk["from"], fk["to"]) for fk in vpm_fks}
    assert ("projects", "city_slug", "city_slug") in fk_targets_vpm
    assert ("videos", "video_id", "video_id") in fk_targets_vpm
    # video_metric_snapshots: FK to videos + ingestion_runs
    fk_targets_vms = {(fk["table"], fk["from"], fk["to"]) for fk in vms_fks}
    assert ("videos", "video_id", "video_id") in fk_targets_vms
    assert ("ingestion_runs", "run_id", "run_id") in fk_targets_vms
    # git_events: FK to projects
    fk_targets_ge = {(fk["table"], fk["from"], fk["to"]) for fk in ge_fks}
    assert ("projects", "city_slug", "city_slug") in fk_targets_ge


def test_atomic_migration_rollback_on_failure(fresh_db, tmp_path, monkeypatch):
    """If a migration SQL errors mid-way, the transaction rolls back AND
    the schema_migrations row is NOT inserted (so re-running migrate works).

    Covers Codex round-1 finding [high]: atomicity between DDL + bookkeeping.
    """
    # Point migrator at a custom migrations dir containing a broken migration.
    custom_dir = tmp_path / "migrations"
    custom_dir.mkdir()
    (custom_dir / "999_broken.sql").write_text(
        "CREATE TABLE good_table (id INTEGER PRIMARY KEY);\n"
        "CREATE TABLE bad_table (id INTEGER PRIMARY KEY REFERENCES nonexistent_table(id));\n"
        "SYNTAX ERROR HERE;\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dbmod, "_MIGRATIONS_DIR", custom_dir)
    with pytest.raises(sqlite3.OperationalError):
        dbmod.migrate()
    # After failure: neither tables nor the schema_migrations row should exist
    # for version 999. good_table was created before the syntax error but the
    # explicit ROLLBACK undoes it.
    with dbmod.connect() as conn:
        tables = {
            r["name"]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        applied = list(
            conn.execute("SELECT version FROM schema_migrations WHERE version='999'")
        )
    assert "good_table" not in tables, "ROLLBACK should have undone the CREATE"
    assert applied == [], "schema_migrations must not record a failed migration"
