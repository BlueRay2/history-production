"""Tests for KPI vault migrator (task-01 of kpi TZ).

Covers:
  - Fresh DB → migrate applies 001
  - Re-running migrate is no-op
  - Modifying a SQL file after apply → RuntimeError (immutability guard)
  - Schema invariants: PK constraints, FK constraints, CHECK on `source`
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from app import db_kpi


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "kpi-test.sqlite"
    monkeypatch.setenv("KPI_DB", str(db_file))
    yield db_file


def test_fresh_db_migrate_applies_001(temp_db):
    count = db_kpi.migrate()
    assert count == 1
    with db_kpi.connect() as conn:
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        assert [r["version"] for r in rows] == ["001"]


def test_migrate_is_idempotent(temp_db):
    db_kpi.migrate()
    second = db_kpi.migrate()
    assert second == 0


def test_modified_migration_file_raises(temp_db, monkeypatch, tmp_path):
    # Apply once
    db_kpi.migrate()
    # Tamper with a copy of the migrations dir
    fake_dir = tmp_path / "fake-migrations"
    fake_dir.mkdir()
    src = db_kpi._MIGRATIONS_DIR / "001_init.sql"
    (fake_dir / "001_init.sql").write_text(src.read_text() + "\n-- mutation\n")
    monkeypatch.setattr(db_kpi, "_MIGRATIONS_DIR", fake_dir)
    with pytest.raises(RuntimeError, match="was modified since apply"):
        db_kpi.migrate()


def test_schema_has_required_tables(temp_db):
    db_kpi.migrate()
    with db_kpi.connect() as conn:
        names = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        }
    expected = {
        "schema_migrations",
        "videos",
        "ingestion_runs",
        "channel_snapshots",
        "video_snapshots",
        "video_retention_points",
        "reporting_jobs",
        "reporting_reports",
        "quota_usage",
        "schema_drift_log",
    }
    missing = expected - names
    assert not missing, f"missing tables: {missing}"


def test_check_constraint_source(temp_db):
    db_kpi.migrate()
    with db_kpi.connect() as conn:
        # Open a synthetic ingestion_run for FK
        conn.execute(
            "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
            "VALUES (?, ?, ?, ?)",
            ("r1", "data_api", "2026-04-26T00:00:00Z", "ok"),
        )
        # Valid source — passes
        conn.execute(
            "INSERT INTO channel_snapshots"
            "(metric_key, dimension_key, grain, window_start, window_end, "
            " observed_on, value_num, run_id, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("views", "", "day", "2026-04-26", "2026-04-26",
             "2026-04-26T00:00:00.000001Z", 1.0, "r1", "data_api"),
        )
        # Invalid source — fails
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO channel_snapshots"
                "(metric_key, dimension_key, grain, window_start, window_end, "
                " observed_on, value_num, run_id, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("views", "", "day", "2026-04-26", "2026-04-26",
                 "2026-04-26T00:00:00.000002Z", 1.0, "r1", "garbage"),
            )


def test_foreign_keys_enforced(temp_db):
    db_kpi.migrate()
    with db_kpi.connect() as conn:
        # Try to insert channel_snapshot with non-existent run_id → FK error
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO channel_snapshots"
                "(metric_key, dimension_key, grain, window_start, window_end, "
                " observed_on, value_num, run_id, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("views", "", "day", "2026-04-26", "2026-04-26",
                 "2026-04-26T00:00:00.000001Z", 1.0, "nonexistent_run", "data_api"),
            )


def test_pk_collision_via_microsecond_observed_on(temp_db):
    """Microsecond precision dodges PK collision on rapid re-pulls."""
    db_kpi.migrate()
    with db_kpi.connect() as conn:
        conn.execute(
            "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
            "VALUES (?, ?, ?, ?)",
            ("r1", "analytics_api", "2026-04-26T00:00:00Z", "ok"),
        )
        # Two near-identical rows with different microseconds
        for usec in ("000001", "000002"):
            conn.execute(
                "INSERT INTO channel_snapshots"
                "(metric_key, dimension_key, grain, window_start, window_end, "
                " observed_on, value_num, run_id, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("views", "", "day", "2026-04-26", "2026-04-26",
                 f"2026-04-26T00:00:00.{usec}Z", 1.0, "r1", "analytics_api"),
            )
        n = conn.execute("SELECT COUNT(*) AS c FROM channel_snapshots").fetchone()["c"]
        assert n == 2


def test_schema_drift_log_pk_and_unique(temp_db):
    db_kpi.migrate()
    with db_kpi.connect() as conn:
        # First insert
        conn.execute(
            "INSERT INTO schema_drift_log"
            "(detected_at, source, drift_type, identifier, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            ("2026-04-26T00:00:00Z", "analytics_api", "metric_added", "newMetric", "test"),
        )
        # Same natural key — UNIQUE constraint blocks
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO schema_drift_log"
                "(detected_at, source, drift_type, identifier, notes) "
                "VALUES (?, ?, ?, ?, ?)",
                ("2026-04-26T00:00:00Z", "analytics_api", "metric_added", "newMetric", "dup"),
            )
        # Different identifier — passes
        conn.execute(
            "INSERT INTO schema_drift_log"
            "(detected_at, source, drift_type, identifier, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            ("2026-04-26T00:00:00Z", "analytics_api", "metric_added", "anotherMetric", "ok"),
        )
        # Verify surrogate id PK exists
        ids = [r["id"] for r in conn.execute("SELECT id FROM schema_drift_log ORDER BY id")]
        assert ids == [1, 2]


def test_quota_usage_pk(temp_db):
    db_kpi.migrate()
    with db_kpi.connect() as conn:
        conn.execute(
            "INSERT INTO quota_usage(api_name, date_utc, units_used, request_count, last_updated) "
            "VALUES (?, ?, ?, ?, ?)",
            ("data_api_v3", "2026-04-26", 100, 50, "2026-04-26T00:00:00Z"),
        )
        # Same (api_name, date_utc) PK — collision
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO quota_usage(api_name, date_utc, units_used, request_count, last_updated) "
                "VALUES (?, ?, ?, ?, ?)",
                ("data_api_v3", "2026-04-26", 200, 100, "2026-04-26T01:00:00Z"),
            )


# Codex r1 LOW: index assertions
def test_critical_indexes_present(temp_db):
    db_kpi.migrate()
    with db_kpi.connect() as conn:
        idx_names = {
            r["name"]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        }
    expected = {
        "idx_ingestion_runs_recent",
        "idx_ingestion_runs_source_status",
        "idx_channel_snapshots_lookup",
        "idx_channel_snapshots_dim",
        "idx_video_snapshots_lookup",
        "idx_video_snapshots_metric",  # Codex r1 HIGH fix
        "idx_reporting_reports_lookup",
        "idx_schema_drift_unack",
    }
    missing = expected - idx_names
    assert not missing, f"missing indexes: {missing}"


# Codex r1 LOW: atomicity rollback test
def test_migration_rollback_on_failure(temp_db, monkeypatch, tmp_path):
    """If any statement in a migration fails, all prior statements roll back
    AND schema_migrations row is NOT inserted (so re-running can retry)."""
    fake_dir = tmp_path / "broken-migrations"
    fake_dir.mkdir()
    (fake_dir / "001_init.sql").write_text(
        "CREATE TABLE good_table (id INTEGER PRIMARY KEY);\n"
        "CREATE TABLE bad_table (id INVALID_TYPE_FOR_TESTING);\n"
        "-- the second statement uses bogus type that SQLite still accepts ?"
    )
    # Actually SQLite is lenient with types. Use invalid SQL.
    (fake_dir / "001_init.sql").write_text(
        "CREATE TABLE good_table (id INTEGER PRIMARY KEY);\n"
        "INVALID SQL STATEMENT;"
    )
    monkeypatch.setattr(db_kpi, "_MIGRATIONS_DIR", fake_dir)
    with pytest.raises(sqlite3.OperationalError):
        db_kpi.migrate()
    # Verify rollback: good_table should NOT exist, schema_migrations empty
    with db_kpi.connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE name IN ('good_table', 'schema_migrations')"
        ).fetchall()
        names = {r["name"] for r in rows}
        # schema_migrations may exist (created by _ensure_migrations_table) but empty
        assert "good_table" not in names
        if "schema_migrations" in names:
            applied = conn.execute("SELECT COUNT(*) AS n FROM schema_migrations").fetchone()
            assert applied["n"] == 0


# Codex r1 MED: SQL-safe statement splitter
def test_split_statements_respects_string_literals():
    """Semicolons inside quoted strings must NOT split statements."""
    sql = """
    INSERT INTO t (val) VALUES ('hello;world');
    INSERT INTO t (val) VALUES ('quote''with semicolon; inside');
    INSERT INTO t (msg) VALUES ('-- this is data, not a comment');
    CREATE TABLE u (x TEXT);
    """
    parts = db_kpi._split_statements(sql)
    assert len(parts) == 4
    assert "hello;world" in parts[0]
    assert "quote''with semicolon; inside" in parts[1]
    assert "this is data, not a comment" in parts[2]
    assert parts[3].startswith("CREATE TABLE u")


def test_split_statements_respects_double_quoted_identifiers():
    sql = 'CREATE TABLE "weird;name" (id INT);\nSELECT 1;'
    parts = db_kpi._split_statements(sql)
    assert len(parts) == 2
    assert '"weird;name"' in parts[0]


def test_split_statements_strips_line_comments():
    sql = """
    -- top comment
    CREATE TABLE x (id INT); -- inline trailing
    -- between
    SELECT 1; -- final
    """
    parts = db_kpi._split_statements(sql)
    assert len(parts) == 2
    assert parts[0].startswith("CREATE TABLE x")
    assert parts[1].startswith("SELECT 1")


# Codex r1 MED: enum CHECK constraints work on multiple columns
def test_enum_checks_enforce(temp_db):
    db_kpi.migrate()
    with db_kpi.connect() as conn:
        # ingestion_runs.status CHECK
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
                "VALUES (?, ?, ?, ?)",
                ("r_bad", "data_api", "2026-04-26T00:00:00Z", "BOGUS_STATUS"),
            )
        # ingestion_runs.source CHECK
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
                "VALUES (?, ?, ?, ?)",
                ("r_bad2", "BOGUS_SOURCE", "2026-04-26T00:00:00Z", "ok"),
            )
        # videos.privacy_status CHECK
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO videos(video_id, privacy_status) VALUES (?, ?)",
                ("v_bad", "secret"),
            )
        # videos.is_short out of range
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO videos(video_id, is_short) VALUES (?, ?)",
                ("v_bad2", 2),
            )
        # video_retention_points.elapsed_ratio range
        conn.execute(
            "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
            "VALUES (?, ?, ?, ?)",
            ("r_ok", "analytics_api", "2026-04-26T00:00:00Z", "ok"),
        )
        conn.execute(
            "INSERT INTO videos(video_id) VALUES (?)", ("vid_ok",),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO video_retention_points"
                "(video_id, observed_on, window_start, window_end, elapsed_ratio, run_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("vid_ok", "2026-04-26T00:00:00Z", "2026-04-26", "2026-04-26", 1.5, "r_ok"),
            )
