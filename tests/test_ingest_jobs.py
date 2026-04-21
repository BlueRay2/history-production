"""Tests for ingest.jobs.run_daily_refresh + ingest.first_run."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from app import db as dbmod
from ingest import jobs
from ingest.jobs import run_daily_refresh


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    yield db_file


def _fake_analytics_response(views=412, ctr=0.0463):
    return {
        "columnHeaders": [
            {"name": "views", "columnType": "METRIC", "dataType": "INTEGER"},
            {"name": "impressionsClickThroughRate", "columnType": "METRIC", "dataType": "FLOAT"},
        ],
        "rows": [[views, ctr]],
    }


def test_daily_refresh_happy_path(fresh_db):
    client = MagicMock(name="youtube_client")
    client.get_channel_analytics.return_value = _fake_analytics_response()
    result = run_daily_refresh(
        target_date=date(2026, 4, 20),
        client=client,
        today=date(2026, 4, 22),
    )
    assert result.status == "ok"
    assert result.rows_written == 2  # 2 metrics x 1 row
    with dbmod.connect() as conn:
        rows = list(conn.execute(
            "SELECT metric_key, value_num, preliminary FROM channel_metric_snapshots"
            " ORDER BY metric_key"
        ))
    keys = [r["metric_key"] for r in rows]
    assert "views" in keys
    assert "impressionsClickThroughRate" in keys
    # 2026-04-22 minus 2-day lag = target 2026-04-20 → 2 days ago → NOT preliminary
    # (< 3 days OLD would be preliminary; 2 days back IS preliminary per < 3 rule)
    assert rows[0]["preliminary"] == 1  # preliminary flag set


def test_daily_refresh_not_preliminary_after_window(fresh_db):
    client = MagicMock(name="youtube_client")
    client.get_channel_analytics.return_value = _fake_analytics_response()
    # Pull a date well in the past (>3 days) — preliminary=False
    result = run_daily_refresh(
        target_date=date(2026, 4, 10),
        client=client,
        today=date(2026, 4, 22),
    )
    assert result.status == "ok"
    with dbmod.connect() as conn:
        row = conn.execute(
            "SELECT preliminary FROM channel_metric_snapshots LIMIT 1"
        ).fetchone()
    assert row["preliminary"] == 0


def test_daily_refresh_records_ingestion_run(fresh_db):
    client = MagicMock(name="youtube_client")
    client.get_channel_analytics.return_value = _fake_analytics_response()
    result = run_daily_refresh(
        target_date=date(2026, 4, 20),
        client=client,
        today=date(2026, 4, 22),
    )
    with dbmod.connect() as conn:
        run_row = conn.execute(
            "SELECT status, started_at, finished_at FROM ingestion_runs WHERE run_id = ?",
            (result.run_id,),
        ).fetchone()
    assert run_row["status"] == "ok"
    assert run_row["started_at"] is not None
    assert run_row["finished_at"] is not None


def test_daily_refresh_quota_exhausted(fresh_db):
    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        pytest.skip("google-api-python-client not installed")

    class FakeResp:
        status = 429
        reason = "quota"

    client = MagicMock(name="youtube_client")
    client.get_channel_analytics.side_effect = HttpError(resp=FakeResp(), content=b"quota")

    result = run_daily_refresh(
        target_date=date(2026, 4, 20),
        client=client,
        today=date(2026, 4, 22),
    )
    assert result.status == "quota_exhausted"
    assert result.rows_written == 0
    # ingestion_runs must record the failure.
    with dbmod.connect() as conn:
        status = conn.execute(
            "SELECT status FROM ingestion_runs WHERE run_id = ?",
            (result.run_id,),
        ).fetchone()[0]
    assert status == "quota_exhausted"


def test_daily_refresh_empty_response_writes_nothing(fresh_db):
    client = MagicMock(name="youtube_client")
    client.get_channel_analytics.return_value = {"columnHeaders": [], "rows": []}
    result = run_daily_refresh(
        target_date=date(2026, 4, 20),
        client=client,
        today=date(2026, 4, 22),
    )
    assert result.status == "ok"
    assert result.rows_written == 0


def test_first_run_backfill_skipped_when_populated(fresh_db, monkeypatch):
    from ingest import first_run

    # Pre-populate the table past FIRST_RUN_THRESHOLD.
    from app.repositories.metrics import SnapshotRow, write_snapshot_batch
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES ('seed', 'test', '2026-04-20T00:00:00Z', 'ok')",
        )
        rows = [
            SnapshotRow("views", "weekly", "2026-04-01", "2026-04-07",
                         f"2026-04-22T0{i}:00:00Z", 10.0, "seed", False)
            for i in range(first_run.FIRST_RUN_THRESHOLD + 1)
        ]
        write_snapshot_batch(conn, rows)

    assert first_run.needs_first_run() is False


def test_first_run_backfill_fires_on_empty_db(fresh_db, monkeypatch):
    from ingest import first_run

    assert first_run.needs_first_run() is True

    client = MagicMock(name="youtube_client")
    client.get_channel_analytics.return_value = _fake_analytics_response()

    count = first_run.run_first_time_backfill(
        client=client,
        today=date(2026, 4, 22),
    )
    # BACKFILL_DAYS=45, last_target = today-2 = 2026-04-20.
    # First target = 2026-04-22 - 45 = 2026-03-08. Range is inclusive: 44 days.
    assert count == 44
    with dbmod.connect() as conn:
        runs = conn.execute("SELECT COUNT(*) FROM ingestion_runs").fetchone()[0]
    assert runs == 44


def test_first_run_aborts_on_quota(fresh_db, monkeypatch):
    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        pytest.skip("google-api-python-client not installed")

    from ingest import first_run

    class FakeResp:
        status = 429
        reason = "quota"

    call_count = {"n": 0}

    def flaky_get(**_kwargs):
        call_count["n"] += 1
        if call_count["n"] >= 3:
            raise HttpError(resp=FakeResp(), content=b"quota")
        return _fake_analytics_response()

    client = MagicMock(name="youtube_client")
    client.get_channel_analytics.side_effect = flaky_get

    count = first_run.run_first_time_backfill(
        client=client,
        today=date(2026, 4, 22),
    )
    # 2 successful + 1 that raises = 3 runs attempted, loop breaks after the quota error.
    assert count == 3
