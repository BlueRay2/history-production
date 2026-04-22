"""End-to-end tests for /monthly route."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app import db as dbmod
from app.main import create_app

_FROZEN = date(2026, 4, 22)


@pytest.fixture
def seeded_monthly(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES ('run-1', 'test', '2026-04-22T00:00:00Z', 'ok')"
        )
        conn.execute(
            "INSERT INTO projects (city_slug, first_commit_at, canonical_path, status) "
            "VALUES ('istanbul', '2026-03-25T00:00:00Z', 'istanbul', 'active')"
        )
        conn.execute(
            "INSERT INTO videos (video_id, title, published_at) VALUES "
            "('v1', 'Istanbul Story', '2026-04-01T10:00:00Z')"
        )
        conn.execute(
            "INSERT INTO video_project_map "
            "(city_slug, video_id, confidence, mapping_source, active) "
            "VALUES ('istanbul', 'v1', 0.95, 'auto', 1)"
        )
        # Monthly channel snapshot for subs sparkline + cards.
        for m, val in [
            ("subscribersNet", 3),
            ("estimatedRevenue", 12.5),
            ("playbackBasedCPM", 4.8),
        ]:
            conn.execute(
                "INSERT INTO channel_metric_snapshots "
                "(metric_key, grain, window_start, window_end, observed_on, "
                " value_num, run_id, preliminary) "
                "VALUES (?, 'monthly', '2026-04-01', '2026-04-30', "
                "        '2026-04-22T00:00:00.111Z', ?, 'run-1', 0)",
                (m, val),
            )
        # Video-level monthly snapshots for top_performers.
        for m, val in [("views", 500), ("averageViewPercentage", 40.0), ("subscribersGained", 3)]:
            conn.execute(
                "INSERT INTO video_metric_snapshots "
                "(video_id, metric_key, grain, window_start, window_end, "
                " observed_on, value_num, run_id, preliminary) "
                "VALUES ('v1', ?, 'monthly', '2026-04-01', '2026-04-30', "
                "        '2026-04-22T00:00:00.222Z', ?, 'run-1', 0)",
                (m, val),
            )
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "istanbul").mkdir()
    (repo_root / "istanbul" / "COST_ESTIMATE.md").write_text(
        "**Total: $25.00**\n", encoding="utf-8",
    )
    app = create_app(channel_subs=200, today=_FROZEN, repo_root=repo_root)
    app.config.update(TESTING=True)
    return app


def test_monthly_renders_all_sections(seeded_monthly):
    client = seeded_monthly.test_client()
    resp = client.get("/monthly")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Net New Subs" in body
    assert "Top-3 performers" in body
    assert "Cost per video" in body
    assert "Script iterations" in body
    assert "Subs — 12-month rolling" in body
    assert "Recent publishes" in body
    assert "Istanbul Story" in body


def test_monthly_empty_renders_200(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    app = create_app(today=_FROZEN, repo_root=tmp_path)
    app.config.update(TESTING=True)
    resp = app.test_client().get("/monthly")
    assert resp.status_code == 200
    assert "Нет monthly-данных ещё" in resp.data.decode()
