"""Recent-publishes widget: last 5 videos surfaced on both tabs."""

from __future__ import annotations

from datetime import date

import pytest

from app import db as dbmod
from app.main import create_app
from app.services.monthly_view import recent_publishes

_FROZEN = date(2026, 4, 22)


@pytest.fixture
def seeded_publishes(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES ('run-1', 'test', '2026-04-22T00:00:00Z', 'ok')"
        )
        # Seven videos — widget should return 5 most recent by published_at.
        for i, pub in enumerate([
            "2026-04-01T00:00:00Z",
            "2026-04-05T00:00:00Z",
            "2026-04-10T00:00:00Z",
            "2026-04-12T00:00:00Z",
            "2026-04-15T00:00:00Z",
            "2026-04-18T00:00:00Z",
            "2026-04-20T00:00:00Z",
        ]):
            conn.execute(
                "INSERT INTO videos (video_id, title, published_at) VALUES (?, ?, ?)",
                (f"v{i+1}", f"Vid {i+1}", pub),
            )
        # Seed a week-1 views snapshot for v7 only (most recent).
        conn.execute(
            "INSERT INTO video_metric_snapshots "
            "(video_id, metric_key, grain, window_start, window_end, "
            " observed_on, value_num, run_id, preliminary) "
            "VALUES ('v7', 'views', 'weekly', '2026-04-20', '2026-04-27', "
            "        '2026-04-28T00:00:00.111Z', 320, 'run-1', 0)"
        )
    return db_file


def test_recent_publishes_returns_5_latest(seeded_publishes):
    with dbmod.connect() as conn:
        rows = recent_publishes(conn, limit=5)
    assert len(rows) == 5
    titles = [r["title"] for r in rows]
    # Most recent first.
    assert titles[0] == "Vid 7"
    assert titles[-1] == "Vid 3"
    # v1, v2 dropped off (oldest).
    assert "Vid 1" not in titles


def test_week1_views_surfaced_when_present(seeded_publishes):
    with dbmod.connect() as conn:
        rows = recent_publishes(conn, limit=5)
    by_id = {r["video_id"]: r for r in rows}
    assert by_id["v7"]["week1_views"] == 320
    assert by_id["v6"]["week1_views"] is None


def test_widget_renders_on_monthly(seeded_publishes, monkeypatch, tmp_path):
    app = create_app(today=_FROZEN, repo_root=tmp_path)
    app.config.update(TESTING=True)
    resp = app.test_client().get("/monthly")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Recent publishes" in body
    assert "Vid 7" in body
