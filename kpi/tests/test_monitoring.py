"""Smoke + behavioural tests for monitoring UI (task-07)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


@pytest.fixture
def kpi_db_path(tmp_path):
    """Apply migrations 001 + 002 to a fresh KPI DB and seed minimal data."""
    db = tmp_path / "kpi.sqlite"
    sql_001 = (Path(__file__).resolve().parent.parent / "db"
               / "migrations-kpi" / "001_init.sql").read_text(encoding="utf-8")
    sql_002 = (Path(__file__).resolve().parent.parent / "db"
               / "migrations-kpi" / "002_monitoring.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db))
    conn.executescript(sql_001)
    conn.executescript(sql_002)
    # Seed: one ok run + one failed run
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    earlier = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )
    conn.execute(
        "INSERT INTO ingestion_runs(run_id, source, started_at, status, rows_written) "
        "VALUES ('orch-1', 'nightly_orchestrator', ?, 'ok', 100)",
        (earlier,),
    )
    conn.execute(
        "INSERT INTO ingestion_runs(run_id, source, source_detail, started_at, status, "
        "rows_written, error_text) "
        "VALUES ('vid-1', 'analytics_api', 'video:abc:basic', ?, 'api_failure', 0, "
        "'simulated error')",
        (earlier,),
    )
    # Seed: one drift entry
    conn.execute(
        "INSERT INTO schema_drift_log(detected_at, source, drift_type, identifier, notes) "
        "VALUES (?, 'reporting_api', 'report_type_added', 'new_a3', 'auto-discovered')",
        (now,),
    )
    # Seed: one video
    conn.execute(
        "INSERT INTO videos(video_id, title, published_at) VALUES "
        "('vid_a', 'Alpha Title', ?)",
        ((datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),),
    )
    # Seed: quota_usage today
    today = datetime.now(timezone.utc).date().isoformat()
    conn.execute(
        "INSERT INTO quota_usage(api_name, date_utc, units_used, request_count, last_updated) "
        "VALUES ('data_api_v3', ?, 47, 5, ?)",
        (today, now),
    )
    conn.commit()
    conn.close()
    return str(db)


@pytest.fixture
def client(kpi_db_path, monkeypatch):
    monkeypatch.setenv("KPI_DB", kpi_db_path)
    from app.monitoring import create_app
    app = create_app()
    app.config["KPI_DB"] = kpi_db_path
    app.config["TESTING"] = True
    return app.test_client()


# ---------------------------------------------------------------------------
# Smoke tests — every page returns 200
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/", "/freshness", "/quota", "/schema-drift", "/videos", "/errors"],
)
def test_pages_render_200(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    assert b"<html" in resp.data.lower() or b"<!doctype html" in resp.data.lower()


# ---------------------------------------------------------------------------
# /api/health JSON
# ---------------------------------------------------------------------------


def test_api_health_returns_classified_status(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded", "down")
    # We seeded one nightly_orchestrator run + one failing analytics_api → degraded
    assert data["status"] == "degraded"
    assert "analytics_api" in data["failing_sources"]
    assert data["hours_since_last_run"] is not None
    assert "data_api_v3" in data["quota_used_today"]
    assert data["quota_used_today"]["data_api_v3"] == 47


def test_api_health_down_when_no_orchestrator(client, kpi_db_path):
    """If we wipe orchestrator runs, status flips to down."""
    conn = sqlite3.connect(kpi_db_path, isolation_level=None)
    conn.execute("DELETE FROM ingestion_runs WHERE source='nightly_orchestrator'")
    conn.close()
    resp = client.get("/api/health")
    data = resp.get_json()
    assert data["status"] == "down"
    assert data["hours_since_last_run"] is None


# ---------------------------------------------------------------------------
# /schema-drift/<id>/ack POST
# ---------------------------------------------------------------------------


def test_schema_drift_ack_marks_acknowledged(client, kpi_db_path):
    # Seed-data has one unacknowledged drift entry; find its id
    conn = sqlite3.connect(kpi_db_path)
    conn.row_factory = sqlite3.Row
    drift_id = conn.execute(
        "SELECT id FROM schema_drift_log WHERE acknowledged_at IS NULL"
    ).fetchone()["id"]
    conn.close()

    resp = client.post(f"/schema-drift/{drift_id}/ack", data={"by": "test"})
    assert resp.status_code == 204

    conn = sqlite3.connect(kpi_db_path)
    conn.row_factory = sqlite3.Row
    after = conn.execute(
        "SELECT acknowledged_at, acknowledged_by FROM schema_drift_log WHERE id=?",
        (drift_id,),
    ).fetchone()
    conn.close()
    assert after["acknowledged_at"] is not None
    assert after["acknowledged_by"] == "test"


def test_schema_drift_ack_404_for_unknown_id(client):
    resp = client.post("/schema-drift/99999/ack", data={"by": "test"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Filter behaviour
# ---------------------------------------------------------------------------


def test_freshness_query_filter(client, kpi_db_path):
    """The query parameter `q` should filter metrics by prefix."""
    # Seed an extra channel_snapshot to make freshness view have data
    conn = sqlite3.connect(kpi_db_path, isolation_level=None)
    conn.execute(
        "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
        "VALUES ('r-fresh', 'analytics_api', ?, 'ok')",
        (datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),)
    )
    conn.execute(
        "INSERT INTO channel_snapshots(metric_key, dimension_key, grain, "
        "window_start, window_end, observed_on, value_num, run_id, source) "
        "VALUES ('views', '', 'day', '2026-04-25', '2026-04-25', ?, 100.0, "
        "'r-fresh', 'analytics_api')",
        (datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),)
    )
    conn.execute(
        "INSERT INTO channel_snapshots(metric_key, dimension_key, grain, "
        "window_start, window_end, observed_on, value_num, run_id, source) "
        "VALUES ('estimatedMinutesWatched', '', 'day', '2026-04-25', '2026-04-25', ?, "
        "1000.0, 'r-fresh', 'analytics_api')",
        (datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),)
    )
    conn.close()

    # No filter — both metrics show
    resp = client.get("/freshness")
    assert b"views" in resp.data
    assert b"estimatedMinutesWatched" in resp.data
    # Filter "view" — only views appears (estimatedMinutesWatched filtered out)
    resp = client.get("/freshness?q=view")
    assert b"views" in resp.data
    assert b"estimatedMinutesWatched" not in resp.data


def test_errors_page_lists_failed_run(client):
    resp = client.get("/errors")
    assert b"api_failure" in resp.data
    assert b"video:abc:basic" in resp.data


def test_videos_page_renders_seeded_video(client):
    resp = client.get("/videos")
    assert b"vid_a" in resp.data
    assert b"Alpha Title" in resp.data


# ---------------------------------------------------------------------------
# Health classification — stuck `running` (>2h)
# ---------------------------------------------------------------------------


def test_api_health_treats_stuck_running_as_failing(client, kpi_db_path):
    """A 'running' run that started >2h ago should flip status to degraded."""
    conn = sqlite3.connect(kpi_db_path, isolation_level=None)
    # Wipe all and insert fresh: orchestrator ok recent + analytics_api stuck running 4h ago
    conn.execute("DELETE FROM ingestion_runs")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    four_h_ago = (datetime.now(timezone.utc) - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    conn.execute(
        "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
        "VALUES ('orch-2', 'nightly_orchestrator', ?, 'ok')",
        (now,),
    )
    conn.execute(
        "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
        "VALUES ('stuck-1', 'analytics_api', ?, 'running')",
        (four_h_ago,),
    )
    conn.close()
    resp = client.get("/api/health")
    data = resp.get_json()
    assert data["status"] == "degraded"
    assert "analytics_api" in data["failing_sources"]


def test_api_health_fresh_running_not_treated_as_failing(client, kpi_db_path):
    """A 'running' run that started seconds ago should NOT flip status."""
    conn = sqlite3.connect(kpi_db_path, isolation_level=None)
    conn.execute("DELETE FROM ingestion_runs")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    conn.execute(
        "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
        "VALUES ('orch-3', 'nightly_orchestrator', ?, 'ok')",
        (now,),
    )
    conn.execute(
        "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
        "VALUES ('inflight-1', 'analytics_api', ?, 'running')",
        (now,),
    )
    conn.close()
    resp = client.get("/api/health")
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["failing_sources"] == []


# ---------------------------------------------------------------------------
# /schema-drift/<id>/ack — repeat POST is idempotent
# ---------------------------------------------------------------------------


def test_schema_drift_ack_repeat_is_idempotent(client, kpi_db_path):
    """Second POST against an already-acknowledged row must not overwrite by/at."""
    conn = sqlite3.connect(kpi_db_path)
    conn.row_factory = sqlite3.Row
    drift_id = conn.execute(
        "SELECT id FROM schema_drift_log WHERE acknowledged_at IS NULL"
    ).fetchone()["id"]
    conn.close()

    r1 = client.post(f"/schema-drift/{drift_id}/ack", data={"by": "first"})
    assert r1.status_code == 204
    conn = sqlite3.connect(kpi_db_path)
    conn.row_factory = sqlite3.Row
    after_first = dict(conn.execute(
        "SELECT acknowledged_at, acknowledged_by FROM schema_drift_log WHERE id=?",
        (drift_id,)
    ).fetchone())
    conn.close()

    r2 = client.post(f"/schema-drift/{drift_id}/ack", data={"by": "second"})
    assert r2.status_code == 204  # still 204, not 409
    conn = sqlite3.connect(kpi_db_path)
    conn.row_factory = sqlite3.Row
    after_second = dict(conn.execute(
        "SELECT acknowledged_at, acknowledged_by FROM schema_drift_log WHERE id=?",
        (drift_id,)
    ).fetchone())
    conn.close()

    # 'first' must be preserved — not overwritten by 'second'
    assert after_second["acknowledged_by"] == "first"
    assert after_second["acknowledged_at"] == after_first["acknowledged_at"]


# ---------------------------------------------------------------------------
# Read-only DB enforcement
# ---------------------------------------------------------------------------


def test_db_helper_opens_read_only_handle(client, kpi_db_path):
    """The Flask test_client uses the same DB; verify a request-scoped _db()
    handle rejects writes."""
    from app.monitoring.routes import _db
    from app.monitoring import create_app
    app = create_app()
    app.config["KPI_DB"] = kpi_db_path
    with app.app_context():
        conn = _db()
        with pytest.raises(sqlite3.OperationalError):
            conn.execute(
                "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
                "VALUES ('rogue', 'attacker', ?, 'ok')",
                (datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),),
            )
        conn.close()


# ---------------------------------------------------------------------------
# /freshness — status (stale-threshold) filter + last_obs column
# ---------------------------------------------------------------------------


def test_freshness_stale_filter(client, kpi_db_path):
    """`stale=3` should hide metrics whose days_since_last_obs < 3."""
    conn = sqlite3.connect(kpi_db_path, isolation_level=None)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    conn.execute(
        "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
        "VALUES ('r-stale', 'analytics_api', ?, 'ok')",
        (now_iso,),
    )
    # Fresh metric (observed today) + stale metric (observed 10d ago)
    today = datetime.now(timezone.utc).date().isoformat()
    ten_days_ago_dt = datetime.now(timezone.utc) - timedelta(days=10)
    ten_days_ago_iso = ten_days_ago_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    ten_days_ago_d = ten_days_ago_dt.date().isoformat()
    conn.execute(
        "INSERT INTO channel_snapshots(metric_key, dimension_key, grain, "
        "window_start, window_end, observed_on, value_num, run_id, source) "
        "VALUES ('fresh_metric', '', 'day', ?, ?, ?, 1.0, 'r-stale', 'analytics_api')",
        (today, today, now_iso),
    )
    conn.execute(
        "INSERT INTO channel_snapshots(metric_key, dimension_key, grain, "
        "window_start, window_end, observed_on, value_num, run_id, source) "
        "VALUES ('ancient_metric', '', 'day', ?, ?, ?, 1.0, 'r-stale', 'analytics_api')",
        (ten_days_ago_d, ten_days_ago_d, ten_days_ago_iso),
    )
    conn.close()
    resp = client.get("/freshness?stale=3")
    assert b"ancient_metric" in resp.data
    assert b"fresh_metric" not in resp.data


def test_freshness_stale_filter_whitelist(client):
    """Only the documented values 1/3/7 trigger the stale filter; anything
    else (negative, inf, garbage) silently falls back to no filter."""
    # `stale=-1` should NOT enable a filter and should NOT 500
    resp = client.get("/freshness?stale=-1")
    assert resp.status_code == 200
    resp = client.get("/freshness?stale=inf")
    assert resp.status_code == 200
    resp = client.get("/freshness?stale=banana")
    assert resp.status_code == 200
