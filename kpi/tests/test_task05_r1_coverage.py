"""Regression coverage for Codex r1 findings on task-05."""

from __future__ import annotations

import pytest

from app import db as dbmod
from app.services.kpis import (
    cycle_time_days,
    script_iterations_approx,
    top_performers,
    value_with_reason,
)
from app.services.mapping import approve_mapping, suggest_mappings


# --- script_iterations_approx: windowing + mapping gating -------------------

@pytest.fixture
def db_with_windowed_revisions(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO projects (city_slug, first_commit_at, canonical_path, status) "
            "VALUES ('istanbul', '2026-03-25T00:00:00Z', 'istanbul', 'active'),"
            "       ('orphan',   '2026-04-01T00:00:00Z', 'orphan',   'active')"
        )
        conn.execute(
            "INSERT INTO videos (video_id, title, published_at) VALUES "
            "('v1', 'Istanbul Story', '2026-04-15T10:00:00Z')"
        )
        conn.execute(
            "INSERT INTO video_project_map "
            "(city_slug, video_id, confidence, mapping_source, active) "
            "VALUES ('istanbul', 'v1', 0.95, 'auto', 1)"
        )
        # istanbul: 1 pre-start revision (should be excluded), 2 in-window,
        #           1 post-finish revision (should be excluded).
        for sha, city, ts, etype in [
            ('pre',  'istanbul', '2026-03-28T00:00:00Z', 'revision'),
            ('st',   'istanbul', '2026-04-01T00:00:00Z', 'script_started'),
            ('in1',  'istanbul', '2026-04-05T00:00:00Z', 'revision'),
            ('in2',  'istanbul', '2026-04-10T00:00:00Z', 'revision'),
            ('fin',  'istanbul', '2026-04-14T00:00:00Z', 'script_finished'),
            ('post', 'istanbul', '2026-04-16T00:00:00Z', 'revision'),
            # orphan city has revisions but NO active mapping → excluded.
            ('os',   'orphan',   '2026-04-01T00:00:00Z', 'script_started'),
            ('or',   'orphan',   '2026-04-03T00:00:00Z', 'revision'),
            ('of',   'orphan',   '2026-04-10T00:00:00Z', 'script_finished'),
        ]:
            conn.execute(
                "INSERT INTO git_events (commit_sha, city_slug, committed_at, event_type, confidence) "
                "VALUES (?, ?, ?, ?, 0.8)",
                (sha, city, ts, etype),
            )
    yield db_file


def test_iterations_windowed_to_start_finish(db_with_windowed_revisions):
    with dbmod.connect() as conn:
        rows = script_iterations_approx(conn)
    by_city = {r["city_slug"]: r for r in rows}
    # istanbul is mapped, so it surfaces with exactly 2 in-window revisions.
    assert "istanbul" in by_city
    assert by_city["istanbul"]["n_revisions"] == 2
    # orphan has no active mapping → must be excluded entirely.
    assert "orphan" not in by_city


# --- cycle_time_days uses first_scaffold_commit_at, not first_commit_at ----

def test_cycle_time_uses_scaffold_event(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO projects (city_slug, first_commit_at, canonical_path, status) "
            "VALUES ('istanbul', '2026-03-20T00:00:00Z', 'istanbul', 'active')"
            # Earliest commit (README) is Mar 20 — should NOT be used.
        )
        conn.execute(
            "INSERT INTO videos (video_id, title, published_at) VALUES "
            "('v1', 'Istanbul', '2026-04-15T00:00:00Z')"
        )
        conn.execute(
            "INSERT INTO video_project_map "
            "(city_slug, video_id, confidence, mapping_source, active) "
            "VALUES ('istanbul', 'v1', 0.95, 'auto', 1)"
        )
        # Scaffold event five days later than first_commit_at.
        conn.execute(
            "INSERT INTO git_events (commit_sha, city_slug, committed_at, event_type, confidence) "
            "VALUES ('s1', 'istanbul', '2026-03-25T00:00:00Z', 'scaffold', 0.9)"
        )
    with dbmod.connect() as conn:
        rows = cycle_time_days(conn)
    assert len(rows) == 1
    # 2026-04-15 - 2026-03-25 = 21 days (scaffold), NOT 26 days (first commit).
    assert 20 < rows[0]["cycle_days"] < 22


# --- manual approve wins: deactivates competing rows -----------------------

def test_approve_deactivates_competing_mappings(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO projects (city_slug, first_commit_at, canonical_path, status) "
            "VALUES ('istanbul', '2026-03-25T00:00:00Z', 'istanbul', 'active'),"
            "       ('izmir',    '2026-03-25T00:00:00Z', 'izmir',    'active')"
        )
        conn.execute(
            "INSERT INTO videos (video_id, title, published_at) VALUES "
            "('v1', 'Cities on the Bosphorus', '2026-04-15T00:00:00Z')"
        )
        # Two auto-active rows for the same video pointing at different cities.
        conn.execute(
            "INSERT INTO video_project_map "
            "(city_slug, video_id, confidence, mapping_source, active) "
            "VALUES ('istanbul', 'v1', 0.9, 'auto', 1),"
            "       ('izmir',    'v1', 0.9, 'auto', 1)"
        )
        assert approve_mapping(conn, "istanbul", "v1") is True
        rows = list(conn.execute(
            "SELECT city_slug, active, mapping_source FROM video_project_map WHERE video_id='v1'"
        ))
    by_city = {r["city_slug"]: r for r in rows}
    assert by_city["istanbul"]["active"] == 1
    assert by_city["istanbul"]["mapping_source"] == "manual"
    assert by_city["izmir"]["active"] == 0  # competing row deactivated


# --- proximity fallback: publish ≤7d of script_finished --------------------

def test_proximity_fallback_within_7_days(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO projects (city_slug, first_commit_at, canonical_path, status) "
            "VALUES ('kyoto', '2026-04-01T00:00:00Z', 'kyoto', 'active')"
        )
        conn.execute(
            "INSERT INTO videos (video_id, title, published_at) VALUES "
            "('v1', 'Ancient Capital Story', '2026-04-20T00:00:00Z')"
        )
        conn.execute(
            "INSERT INTO git_events (commit_sha, city_slug, committed_at, event_type, confidence) "
            "VALUES ('f1', 'kyoto', '2026-04-16T00:00:00Z', 'script_finished', 0.8)"
        )
    with dbmod.connect() as conn:
        suggestions = suggest_mappings(conn)
    kyoto = [s for s in suggestions if s.city_slug == "kyoto" and s.video_id == "v1"]
    assert len(kyoto) == 1
    # Publish Apr 20, finish Apr 16 → 4 days → proximity at 0.6.
    assert kyoto[0].confidence == 0.6


# --- value_with_reason: channel-level metric with low subs --------------------

def test_privacy_floor_applies_to_channel_metrics(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        r = value_with_reason(
            conn,
            metric_key="impressions", grain="weekly",
            window_start="2026-04-14", window_end="2026-04-20",
            channel_subs=44,  # below SUB_FLOOR 50, no video_id
        )
    assert r.reason == "below_privacy_floor"
    assert r.value is None


# --- top_performers excludes cross-window metric mixes -----------------------

def test_top_performers_aligned_window_only(tmp_path, monkeypatch):
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
            "('v1', 'A', '2026-04-15T00:00:00Z'),"
            "('v2', 'B', '2026-04-16T00:00:00Z')"
        )
        # v1: all three in week W1. v2: only views in W1, retention+subs in W2.
        # Aligned window = W1 (since it has all three). v2 lacks retention+subs
        # in W1 → excluded.
        def ins(video, metric, ws, we, val):
            conn.execute(
                "INSERT INTO video_metric_snapshots "
                "(video_id, metric_key, grain, window_start, window_end, "
                " observed_on, value_num, run_id, preliminary) "
                "VALUES (?, ?, 'monthly', ?, ?, ?, ?, 'run-1', 0)",
                (video, metric, ws, we, "2026-04-22T00:00:00." + video + "Z", val),
            )
        # W1: 2026-04-01..30
        ins("v1", "views", "2026-04-01", "2026-04-30", 500)
        ins("v1", "averageViewPercentage", "2026-04-01", "2026-04-30", 42)
        ins("v1", "subscribersGained", "2026-04-01", "2026-04-30", 3)
        ins("v2", "views", "2026-04-01", "2026-04-30", 800)
        # v2 retention+subs live in a different (older) window — must be ignored.
        ins("v2", "averageViewPercentage", "2026-03-01", "2026-03-31", 55)
        ins("v2", "subscribersGained", "2026-03-01", "2026-03-31", 5)

    with dbmod.connect() as conn:
        rows = top_performers(conn, limit=10, grain="monthly")
    vids = {r["video_id"] for r in rows}
    assert vids == {"v1"}  # v2 excluded because it lacks retention/subs in aligned window


def test_top_performers_r2_split_metrics_window_rejected(tmp_path, monkeypatch):
    """Codex r2 regression: a window where the three metrics are split
    across different videos must NOT be selected as aligned. The query must
    fall back to the latest window where ANY single video has all three.
    """
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
            "('v1', 'A', '2026-03-15T00:00:00Z'),"
            "('v2', 'B', '2026-04-02T00:00:00Z'),"
            "('v3', 'C', '2026-04-03T00:00:00Z'),"
            "('v4', 'D', '2026-04-04T00:00:00Z')"
        )

        def ins(video, metric, ws, we, val, obs_tag):
            conn.execute(
                "INSERT INTO video_metric_snapshots "
                "(video_id, metric_key, grain, window_start, window_end, "
                " observed_on, value_num, run_id, preliminary) "
                "VALUES (?, ?, 'monthly', ?, ?, ?, ?, 'run-1', 0)",
                (video, metric, ws, we, f"2026-04-30T00:00:00.{obs_tag}Z", val),
            )

        # W2 (April) — three metrics split across three different videos.
        ins("v2", "views", "2026-04-01", "2026-04-30", 500, "aaa")
        ins("v3", "averageViewPercentage", "2026-04-01", "2026-04-30", 40, "bbb")
        ins("v4", "subscribersGained", "2026-04-01", "2026-04-30", 5, "ccc")
        # W1 (March) — v1 has all three.
        ins("v1", "views", "2026-03-01", "2026-03-31", 800, "ddd")
        ins("v1", "averageViewPercentage", "2026-03-01", "2026-03-31", 55, "eee")
        ins("v1", "subscribersGained", "2026-03-01", "2026-03-31", 7, "fff")

    with dbmod.connect() as conn:
        rows = top_performers(conn, limit=10, grain="monthly")
    vids = {r["video_id"] for r in rows}
    # Must fall back to March (W1) and rank v1, NOT pick April and return empty.
    assert vids == {"v1"}
