"""Regression coverage for Codex r1 findings on task-07."""

from __future__ import annotations

from datetime import date

import pytest

from app import db as dbmod
from app.main import create_app
from app.services.monthly_view import (
    parse_fail_cities,
    recent_publishes,
    sparse_metrics_gated,
)

_FROZEN = date(2026, 4, 22)


# --- [HIGH] sparse_metrics_gated must surface even without snapshots -------

def test_sparse_metrics_gated_when_no_snapshots_yet(tmp_path, monkeypatch):
    """Fresh channel with zero channel_metric_snapshots + below privacy
    floor MUST be surfaced on the exceptions panel."""
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        result = sparse_metrics_gated(
            conn,
            channel_subs=44,  # below SUB_FLOOR=50
            channel_published_at=None,
            today=_FROZEN,
        )
    # All WEEKLY_METRICS + MONTHLY_METRICS should surface as
    # below_privacy_floor.
    assert len(result) > 0
    reasons = {r["reason"] for r in result}
    assert "below_privacy_floor" in reasons


def test_sparse_metrics_gated_when_channel_too_new(tmp_path, monkeypatch):
    """No snapshots + channel <14 days old → surface channel_too_new for
    every metric across grains."""
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        result = sparse_metrics_gated(
            conn,
            channel_subs=500,
            channel_published_at="2026-04-17T00:00:00Z",  # 5 days before frozen
            today=_FROZEN,
        )
    reasons = {r["reason"] for r in result}
    assert "channel_too_new" in reasons


def test_exceptions_page_shows_gated_on_empty_db(tmp_path, monkeypatch):
    """End-to-end: fresh DB + below-floor channel renders the gated
    section instead of the 'Все метрики доступны' empty-state."""
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    app = create_app(channel_subs=44, today=_FROZEN, repo_root=tmp_path)
    app.config.update(TESTING=True)
    resp = app.test_client().get("/exceptions")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Sparse-metrics gated" in body
    assert "below_privacy_floor" in body
    assert "Все метрики доступны" not in body


# --- [HIGH] parse_fail_cities agrees with cost_parse fallback path ---------

def test_parse_fail_city_when_only_docs_path_valid(tmp_path, monkeypatch):
    """A city with malformed root COST_ESTIMATE.md but valid docs/ one
    should NOT be reported as parse-fail — cost_per_video accepts it."""
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()

    repo = tmp_path / "repo"
    city = repo / "istanbul"
    (city / "docs").mkdir(parents=True)
    # Root file exists but is malformed; docs file has canonical total.
    (city / "COST_ESTIMATE.md").write_text("# partial estimate\n", encoding="utf-8")
    (city / "docs" / "COST_ESTIMATE.md").write_text("**Total: $17.42**\n", encoding="utf-8")

    result = parse_fail_cities(repo)
    assert "istanbul" not in result  # fallback succeeds → not a parse-fail


def test_parse_fail_city_when_all_paths_fail(tmp_path, monkeypatch):
    """A city with no valid canonical total in either candidate file IS
    a parse-fail — both cost_per_video and the exceptions panel agree."""
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()

    repo = tmp_path / "repo"
    city = repo / "istanbul"
    (city / "docs").mkdir(parents=True)
    (city / "COST_ESTIMATE.md").write_text("# partial estimate\n", encoding="utf-8")
    (city / "docs" / "COST_ESTIMATE.md").write_text("# also partial\n", encoding="utf-8")

    result = parse_fail_cities(repo)
    assert "istanbul" in result


# --- [MED] recent_publishes strict-boundary window match -------------------

def test_recent_publishes_no_double_match_on_boundary(tmp_path, monkeypatch):
    """A video published on a week boundary date should match exactly one
    weekly window (the one containing the publish date), never both."""
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES ('run-1', 'test', '2026-04-22T00:00:00Z', 'ok')"
        )
        # Publish on 2026-04-20 — a Monday boundary between weeks.
        conn.execute(
            "INSERT INTO videos (video_id, title, published_at) VALUES "
            "('v1', 'Boundary Video', '2026-04-20T10:00:00Z')"
        )
        # Two adjacent windows touching the boundary:
        #   W_prev: 2026-04-13 → 2026-04-20   (ends ON publish date)
        #   W_curr: 2026-04-20 → 2026-04-27   (starts ON publish date)
        # Only W_curr should match (window_end > published_at requires
        # W_prev's 2026-04-20 to NOT match, since 20 > 20 is false).
        conn.execute(
            "INSERT INTO video_metric_snapshots "
            "(video_id, metric_key, grain, window_start, window_end, "
            " observed_on, value_num, run_id, preliminary) "
            "VALUES ('v1', 'views', 'weekly', '2026-04-13', '2026-04-20', "
            "        '2026-04-21T00:00:00.111Z', 999, 'run-1', 0)"
        )
        conn.execute(
            "INSERT INTO video_metric_snapshots "
            "(video_id, metric_key, grain, window_start, window_end, "
            " observed_on, value_num, run_id, preliminary) "
            "VALUES ('v1', 'views', 'weekly', '2026-04-20', '2026-04-27', "
            "        '2026-04-28T00:00:00.222Z', 500, 'run-1', 0)"
        )
    with dbmod.connect() as conn:
        rows = recent_publishes(conn, limit=5)
    assert len(rows) == 1
    # Must be W_curr's 500, NOT W_prev's 999.
    assert rows[0]["week1_views"] == 500


# --- [HIGH] cost-histogram keeps legitimate 0.0 values ---------------------

def test_cost_histogram_keeps_zero_values(tmp_path, monkeypatch):
    """A city with `**Total: $0.00**` should appear in the histogram
    (Codex r1 flagged that Jinja `select` drops 0.0 as falsy)."""
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()

    repo = tmp_path / "repo"
    (repo / "istanbul").mkdir(parents=True)
    (repo / "istanbul" / "COST_ESTIMATE.md").write_text(
        "**Total: $0.00**\n", encoding="utf-8",
    )

    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO projects (city_slug, first_commit_at, canonical_path, status) "
            "VALUES ('istanbul', '2026-03-25T00:00:00Z', 'istanbul', 'active')"
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
        # Seed a monthly channel snapshot so /monthly has a window.
        conn.execute(
            "INSERT INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES ('run-1', 'test', '2026-04-22T00:00:00Z', 'ok')"
        )
        conn.execute(
            "INSERT INTO channel_metric_snapshots "
            "(metric_key, grain, window_start, window_end, observed_on, "
            " value_num, run_id, preliminary) "
            "VALUES ('subscribersNet', 'monthly', '2026-04-01', '2026-04-30', "
            "        '2026-04-22T00:00:00.111Z', 5, 'run-1', 0)"
        )

    app = create_app(channel_subs=500, today=_FROZEN, repo_root=repo)
    app.config.update(TESTING=True)
    resp = app.test_client().get("/monthly")
    assert resp.status_code == 200
    body = resp.data.decode()
    # The rendered cost-hist data-values JSON array must contain a 0 entry.
    assert "data-values='[0.0]'" in body or "data-values='[0]'" in body
