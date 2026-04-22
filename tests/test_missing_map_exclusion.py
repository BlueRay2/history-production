"""Videos without an active mapping must be excluded from per-video KPI views."""

from __future__ import annotations

import pytest

from app import db as dbmod
from app.services.kpis import cycle_time_days, top_performers


@pytest.fixture
def mixed_mapping_db(tmp_path, monkeypatch):
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
            "VALUES ('istanbul', '2026-03-25T00:00:00Z', 'istanbul', 'active'),"
            "       ('orphan',   '2026-04-01T00:00:00Z', 'orphan',   'active')"
        )
        conn.execute(
            "INSERT INTO videos (video_id, title, published_at) VALUES "
            "('v_map',   'Istanbul Story',    '2026-04-15T10:00:00Z'),"
            "('v_unmap', 'Other Random Stuff','2026-04-16T10:00:00Z')"
        )
        # Only v_map is active; v_unmap has no row at all
        conn.execute(
            "INSERT INTO video_project_map "
            "(city_slug, video_id, confidence, mapping_source, active) "
            "VALUES ('istanbul', 'v_map', 0.95, 'auto', 1)"
        )
        # Also insert a pending (active=0) row to confirm filter works
        conn.execute(
            "INSERT INTO video_project_map "
            "(city_slug, video_id, confidence, mapping_source, active) "
            "VALUES ('orphan', 'v_unmap', 0.4, 'auto', 0)"
        )
        # Minimum metric snapshots so top_performers has inputs
        for m, val in [("views", 500), ("averageViewPercentage", 40.0), ("subscribersGained", 2)]:
            conn.execute(
                "INSERT INTO video_metric_snapshots "
                "(video_id, metric_key, grain, window_start, window_end, "
                " observed_on, value_num, run_id, preliminary) "
                "VALUES ('v_map', ?, 'weekly', '2026-04-14', '2026-04-20', "
                "        '2026-04-22T00:00:00.111Z', ?, 'run-1', 0)",
                (m, val),
            )
            conn.execute(
                "INSERT INTO video_metric_snapshots "
                "(video_id, metric_key, grain, window_start, window_end, "
                " observed_on, value_num, run_id, preliminary) "
                "VALUES ('v_unmap', ?, 'weekly', '2026-04-14', '2026-04-20', "
                "        '2026-04-22T00:00:00.222Z', ?, 'run-1', 0)",
                (m, val),
            )
    yield db_file


def test_cycle_time_excludes_inactive_mapping(mixed_mapping_db):
    with dbmod.connect() as conn:
        rows = cycle_time_days(conn)
    video_ids = [r["video_id"] for r in rows]
    assert "v_map" in video_ids
    assert "v_unmap" not in video_ids


def test_top_performers_includes_only_present_metrics(mixed_mapping_db):
    """Top-performers uses snapshots directly (not mapping-gated) — confirm
    videos missing any of the three inputs are excluded, while mapped
    videos with full inputs are ranked. Here both videos have all three
    metrics, so both should appear."""
    with dbmod.connect() as conn:
        rows = top_performers(conn, limit=10)
    vids = {r["video_id"] for r in rows}
    assert vids == {"v_map", "v_unmap"}
