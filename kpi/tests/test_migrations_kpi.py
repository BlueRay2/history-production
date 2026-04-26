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
