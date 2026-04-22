"""Tests for app.services.kpis — derived KPI views + sparse-metric discipline."""

from __future__ import annotations

from datetime import date

import pytest

from app import db as dbmod
from app.services.kpis import (
    MetricReading,
    cycle_time_days,
    script_iterations_approx,
    value_with_reason,
    weekly_scripts_finished,
)


@pytest.fixture
def populated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES ('run-1', 'test', '2026-04-22T00:00:00Z', 'ok')"
        )
        conn.execute(
            "INSERT INTO videos (video_id, title, published_at) VALUES "
            "('v1', 'Istanbul Story', '2026-04-15T10:00:00Z')"
        )
        conn.execute(
            "INSERT INTO projects (city_slug, first_commit_at, canonical_path, status) "
            "VALUES ('istanbul', '2026-03-25T00:00:00Z', 'istanbul', 'active')"
        )
        conn.execute(
            "INSERT INTO video_project_map (city_slug, video_id, confidence, mapping_source, active) "
            "VALUES ('istanbul', 'v1', 0.95, 'auto', 1)"
        )
        # One channel metric for 2026-04-14..20 weekly
        conn.execute(
            "INSERT INTO channel_metric_snapshots "
            "(metric_key, grain, window_start, window_end, observed_on, value_num, run_id, preliminary) "
            "VALUES ('views', 'weekly', '2026-04-14', '2026-04-20', "
            "        '2026-04-22T00:00:00.123456Z', 412.0, 'run-1', 0)"
        )
        # git_events for istanbul
        events = [
            ('c1', 'istanbul', '2026-03-25T00:00:00Z', 'scaffold', 0.9),
            ('c2', 'istanbul', '2026-04-01T00:00:00Z', 'script_started', 0.85),
            ('c3', 'istanbul', '2026-04-05T00:00:00Z', 'revision', 0.7),
            ('c4', 'istanbul', '2026-04-10T00:00:00Z', 'revision', 0.7),
            ('c5', 'istanbul', '2026-04-14T00:00:00Z', 'script_finished', 0.8),
        ]
        for sha, city, ts, etype, conf in events:
            conn.execute(
                "INSERT INTO git_events "
                "(commit_sha, city_slug, committed_at, event_type, confidence) "
                "VALUES (?, ?, ?, ?, ?)",
                (sha, city, ts, etype, conf),
            )
    yield db_file


def test_value_with_reason_ok(populated_db):
    with dbmod.connect() as conn:
        r = value_with_reason(
            conn,
            metric_key="views", grain="weekly",
            window_start="2026-04-14", window_end="2026-04-20",
        )
    assert isinstance(r, MetricReading)
    assert r.reason == "ok"
    assert r.value == 412.0


def test_value_with_reason_no_data_pulled(populated_db):
    with dbmod.connect() as conn:
        r = value_with_reason(
            conn,
            metric_key="impressions", grain="weekly",
            window_start="2026-04-14", window_end="2026-04-20",
        )
    assert r.reason == "no_data_pulled"
    assert r.value is None


def test_value_with_reason_channel_too_new(populated_db):
    with dbmod.connect() as conn:
        r = value_with_reason(
            conn,
            metric_key="views", grain="weekly",
            window_start="2026-04-14", window_end="2026-04-20",
            channel_published_at="2026-04-20T00:00:00Z",
            today=date(2026, 4, 22),
        )
    assert r.reason == "channel_too_new"
    assert r.value is None


def test_value_with_reason_below_privacy_floor_subs(populated_db):
    with dbmod.connect() as conn:
        r = value_with_reason(
            conn,
            metric_key="views", grain="weekly",
            window_start="2026-04-14", window_end="2026-04-20",
            video_id="v1",
            channel_subs=44,  # < SUB_FLOOR 50
        )
    assert r.reason == "below_privacy_floor"


def test_value_with_reason_below_privacy_floor_views(populated_db):
    with dbmod.connect() as conn:
        r = value_with_reason(
            conn,
            metric_key="views", grain="weekly",
            window_start="2026-04-14", window_end="2026-04-20",
            video_id="v1",
            video_view_count=50,  # < VIDEO_VIEW_FLOOR 100
        )
    assert r.reason == "below_privacy_floor"


def test_weekly_scripts_finished(populated_db):
    with dbmod.connect() as conn:
        rows = weekly_scripts_finished(conn)
    # Exactly one script_finished event at 2026-04-14 → week count = 1
    assert len(rows) == 1
    assert rows[0]["n_finished"] == 1


def test_cycle_time_days(populated_db):
    with dbmod.connect() as conn:
        rows = cycle_time_days(conn)
    assert len(rows) == 1
    # published 2026-04-15, first_commit 2026-03-25 = 21 days
    assert 20 < rows[0]["cycle_days"] < 22


def test_script_iterations_approx(populated_db):
    with dbmod.connect() as conn:
        rows = script_iterations_approx(conn)
    istanbul = [r for r in rows if r["city_slug"] == "istanbul"][0]
    # 2 revisions between script_started and script_finished
    assert istanbul["n_revisions"] == 2
    assert istanbul["has_start"] == 1
    assert istanbul["has_finish"] == 1
