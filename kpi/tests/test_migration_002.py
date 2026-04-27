"""Tests for migration 002 — monitoring views + monitoring_pings (task-06).

Verifies:
- Migration applies idempotently
- Each of the 4 views returns correct values for synthetic seed data
- monitoring_pings table accepts inserts with valid status / rejects invalid
- Partial index on alert_sent works for "what needs to be alerted" queries
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


@pytest.fixture
def kpi_db(tmp_path, monkeypatch):
    """Apply both migrations 001 and 002 to an in-memory KPI DB."""
    db_path = tmp_path / "kpi.sqlite"
    monkeypatch.setenv("KPI_DB", str(db_path))
    # Apply migration 001
    sql_001 = (Path(__file__).resolve().parent.parent
               / "db" / "migrations-kpi" / "001_init.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(sql_001)
    # Apply migration 002
    sql_002 = (Path(__file__).resolve().parent.parent
               / "db" / "migrations-kpi" / "002_monitoring.sql").read_text(encoding="utf-8")
    conn.executescript(sql_002)
    conn.commit()
    conn.close()
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _iso_at(delta_days: float):
    return (datetime.now(timezone.utc) - timedelta(days=delta_days)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def test_views_exist_after_migration(kpi_db):
    """All 4 views should be queryable after migration 002."""
    for view in ("v_last_run_per_source", "v_metric_freshness",
                 "v_video_coverage_7d", "v_quota_today"):
        result = kpi_db.execute(f"SELECT * FROM {view} LIMIT 1").fetchall()
        assert isinstance(result, list)  # No exception means view is valid SQL


def test_v_last_run_per_source_returns_latest_per_tuple(kpi_db):
    """View should pick the run with greatest started_at per (source, source_detail)."""
    # Seed three runs for same source/source_detail with increasing time
    for delta, status in [(2, "api_failure"), (1, "partial"), (0, "ok")]:
        kpi_db.execute(
            "INSERT INTO ingestion_runs(run_id, source, source_detail, started_at, "
            "status) VALUES (?, ?, ?, ?, ?)",
            (f"run-{delta}", "analytics_api", "channel:daily_core",
             _iso_at(delta), status),
        )
    # Different tuple — should be separate row
    kpi_db.execute(
        "INSERT INTO ingestion_runs(run_id, source, source_detail, started_at, status) "
        "VALUES ('run-other', 'data_api', 'refresh_videos', ?, 'ok')",
        (_iso_at(0.5),),
    )

    rows = kpi_db.execute(
        "SELECT * FROM v_last_run_per_source ORDER BY source, source_detail"
    ).fetchall()
    assert len(rows) == 2

    analytics = next(r for r in rows if r["source"] == "analytics_api")
    assert analytics["last_status"] == "ok"  # most recent of the 3
    assert analytics["last_run_id"] == "run-0"
    assert analytics["total_runs"] == 3

    data_api = next(r for r in rows if r["source"] == "data_api")
    assert data_api["last_status"] == "ok"
    assert data_api["total_runs"] == 1


def test_v_metric_freshness_days_since(kpi_db):
    """View should compute days_since_last_obs for each (metric, dim) tuple."""
    # Need a real ingestion_runs row (FK constraint)
    kpi_db.execute(
        "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
        "VALUES ('r1', 'analytics_api', ?, 'ok')", (_iso_at(0.1),)
    )
    # Seed snapshots for two metrics
    snapshots = [
        ("views",                    "",            _iso_at(0.5)),
        ("views",                    "",            _iso_at(2.0)),  # older
        ("estimatedMinutesWatched",  "",            _iso_at(5.0)),
        ("views",                    "country=RU",  _iso_at(1.0)),
    ]
    for mk, dk, obs in snapshots:
        kpi_db.execute(
            "INSERT INTO channel_snapshots(metric_key, dimension_key, grain, "
            "window_start, window_end, observed_on, value_num, run_id, source) "
            "VALUES (?, ?, 'day', '2026-04-25', '2026-04-25', ?, 100.0, 'r1', 'analytics_api')",
            (mk, dk, obs),
        )

    rows = {(r["metric_key"], r["dimension_key"]): r
            for r in kpi_db.execute("SELECT * FROM v_metric_freshness").fetchall()}
    # views without dim — most recent of two = ~0.5 days ago
    assert rows[("views", "")]["days_since_last_obs"] < 1.5
    assert rows[("views", "")]["observation_count"] == 2
    # estimatedMinutesWatched ~5 days ago
    assert 4.5 < rows[("estimatedMinutesWatched", "")]["days_since_last_obs"] < 5.5


def test_v_video_coverage_7d_excludes_old_snapshots(kpi_db):
    """Snapshots older than 7 days should not contribute to coverage count."""
    kpi_db.execute(
        "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
        "VALUES ('r1', 'analytics_api', ?, 'ok')", (_iso_at(0.1),)
    )
    kpi_db.execute(
        "INSERT INTO videos(video_id, title) VALUES ('vid_a', 'Alpha')"
    )
    kpi_db.execute(
        "INSERT INTO videos(video_id, title) VALUES ('vid_b', 'Beta')"
    )
    # vid_a: 2 metrics within 7d, 1 metric older
    inserts = [
        ("vid_a", "views",          _iso_at(2)),
        ("vid_a", "likes",          _iso_at(3)),
        ("vid_a", "shares",         _iso_at(10)),  # too old, excluded
        ("vid_b", "views",          _iso_at(50)),  # too old
    ]
    for v, mk, obs in inserts:
        kpi_db.execute(
            "INSERT INTO video_snapshots(video_id, metric_key, dimension_key, grain, "
            "window_start, window_end, observed_on, value_num, run_id, source) "
            "VALUES (?, ?, '', 'day', '2026-04-25', '2026-04-25', ?, 1.0, 'r1', 'analytics_api')",
            (v, mk, obs),
        )
    rows = {r["video_id"]: r for r in kpi_db.execute(
        "SELECT * FROM v_video_coverage_7d").fetchall()}
    assert rows["vid_a"]["metrics_pulled_7d"] == 2
    assert rows["vid_b"]["metrics_pulled_7d"] == 0


def test_v_quota_today_only_returns_today_row(kpi_db):
    """Yesterday's quota_usage rows should be filtered out by the view."""
    today = datetime.now(timezone.utc).date().isoformat()
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    kpi_db.execute(
        "INSERT INTO quota_usage(api_name, date_utc, units_used, request_count, last_updated) "
        "VALUES ('data_api_v3', ?, 100, 5, ?)", (today, _now_iso())
    )
    kpi_db.execute(
        "INSERT INTO quota_usage(api_name, date_utc, units_used, request_count, last_updated) "
        "VALUES ('analytics_api_v2', ?, 200, 7, ?)", (today, _now_iso())
    )
    kpi_db.execute(
        "INSERT INTO quota_usage(api_name, date_utc, units_used, request_count, last_updated) "
        "VALUES ('data_api_v3', ?, 999, 99, ?)", (yesterday, _now_iso())
    )
    rows = kpi_db.execute("SELECT * FROM v_quota_today ORDER BY api_name").fetchall()
    assert len(rows) == 2
    assert {r["api_name"] for r in rows} == {"data_api_v3", "analytics_api_v2"}
    # Yesterday's 999 should NOT appear
    assert all(r["units_used"] != 999 for r in rows)


def test_monitoring_pings_check_constraint(kpi_db):
    """status must be one of 'ok' | 'degraded' | 'down'."""
    kpi_db.execute(
        "INSERT INTO monitoring_pings(ping_at, status) VALUES (?, 'ok')",
        (_now_iso(),)
    )
    with pytest.raises(sqlite3.IntegrityError):
        kpi_db.execute(
            "INSERT INTO monitoring_pings(ping_at, status) VALUES (?, 'broken')",
            (_now_iso(),)
        )


def test_monitoring_pings_alert_dedup_index(kpi_db):
    """Partial index should make 'pending alerts' query trivial."""
    kpi_db.execute(
        "INSERT INTO monitoring_pings(ping_at, status, alert_sent) VALUES (?, 'ok', 0)",
        (_iso_at(0.3),)
    )
    kpi_db.execute(
        "INSERT INTO monitoring_pings(ping_at, status, alert_sent) VALUES (?, 'degraded', 0)",
        (_iso_at(0.2),)
    )
    kpi_db.execute(
        "INSERT INTO monitoring_pings(ping_at, status, alert_sent) VALUES (?, 'down', 1)",
        (_iso_at(0.1),)
    )
    pending = kpi_db.execute(
        "SELECT * FROM monitoring_pings "
        "WHERE alert_sent=0 AND status IN ('degraded', 'down')"
    ).fetchall()
    assert len(pending) == 1
    assert pending[0]["status"] == "degraded"


def test_migration_002_applies_via_db_kpi_migrator(tmp_path, monkeypatch):
    """The same migration applied through app.db_kpi.migrate() yields identical schema."""
    monkeypatch.setenv("KPI_DB", str(tmp_path / "via-migrator.sqlite"))
    from app.db_kpi import migrate, status as _status

    applied = migrate()
    assert applied >= 2  # both 001 and 002

    # Re-run should be idempotent
    re_applied = migrate()
    assert re_applied == 0

    # Verify all 4 views queryable
    import sqlite3 as _sql
    conn = _sql.connect(str(tmp_path / "via-migrator.sqlite"))
    for view in ("v_last_run_per_source", "v_metric_freshness",
                 "v_video_coverage_7d", "v_quota_today"):
        conn.execute(f"SELECT * FROM {view} LIMIT 1").fetchall()
    conn.close()
