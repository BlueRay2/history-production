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
    # Empty videos table → status='partial' (r2 fix). Seed one video below
    # if you want 'ok' — but most of these tests exercise channel-level
    # behavior and don't care about per-video.
    assert result.status in ("ok", "partial")
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
    # Empty videos table → status='partial' (r2 fix). Seed one video below
    # if you want 'ok' — but most of these tests exercise channel-level
    # behavior and don't care about per-video.
    assert result.status in ("ok", "partial")
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
    assert run_row["status"] in ("ok", "partial")
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
    # Empty videos table → status='partial' (r2 fix). Seed one video below
    # if you want 'ok' — but most of these tests exercise channel-level
    # behavior and don't care about per-video.
    assert result.status in ("ok", "partial")
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
    # BACKFILL_DAYS=45, last_target = today-2 = 2026-04-20,
    # first_target = today-46 = 2026-03-07 (Codex r1 fix for off-by-one).
    # Inclusive range 2026-03-07..2026-04-20 = 45 days.
    assert count == 45
    with dbmod.connect() as conn:
        runs = conn.execute("SELECT COUNT(*) FROM ingestion_runs").fetchone()[0]
    assert runs == 45


def test_microsecond_observed_on_survives_same_second_rerun(fresh_db):
    """Codex r1 MED: second-resolution observed_on collided on PK; fix moved
    to microsecond precision so two fast-succession refreshes produce two
    distinct snapshot rows instead of one silent drop."""
    client = MagicMock(name="youtube_client")
    client.get_channel_analytics.return_value = _fake_analytics_response(views=100)
    r1 = run_daily_refresh(target_date=date(2026, 4, 10), client=client, today=date(2026, 4, 22))
    r2 = run_daily_refresh(target_date=date(2026, 4, 10), client=client, today=date(2026, 4, 22))
    # Empty videos table → status='partial' (r2 fix). Either value is a successful run.
    assert r1.status in ("ok", "partial") and r2.status in ("ok", "partial")
    # Both runs must have written their rows — 2 runs × 2 metrics = 4 rows.
    with dbmod.connect() as conn:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM channel_metric_snapshots WHERE window_start='2026-04-06'"
        ).fetchone()[0]
    assert cnt == 4, "same-second re-run must NOT silently drop rows"


def test_per_video_pull_writes_video_metric_rows(fresh_db):
    """Codex r1 HIGH: per-video path was missing. Verify video_id gets
    routed to video_metric_snapshots when present in `videos` table."""
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO videos (video_id, title) VALUES ('vXYZ', 'Test video')",
        )
    client = MagicMock(name="youtube_client")
    client.get_channel_analytics.return_value = _fake_analytics_response()
    client.get_video_analytics.return_value = _fake_analytics_response(views=42, ctr=0.0812)
    client.get_retention.return_value = {"rows": []}  # privacy-floor empty

    result = run_daily_refresh(
        target_date=date(2026, 4, 10), client=client, today=date(2026, 4, 22),
    )
    # Empty videos table → status='partial' (r2 fix). Seed one video below
    # if you want 'ok' — but most of these tests exercise channel-level
    # behavior and don't care about per-video.
    assert result.status in ("ok", "partial")
    with dbmod.connect() as conn:
        video_cnt = conn.execute("SELECT COUNT(*) FROM video_metric_snapshots").fetchone()[0]
        chan_cnt = conn.execute("SELECT COUNT(*) FROM channel_metric_snapshots").fetchone()[0]
    # Only 2 metrics per video test response.
    assert video_cnt == 2
    assert chan_cnt == 2


def test_empty_videos_table_marks_partial(fresh_db):
    """Codex+Gemini r2 [MED]: empty videos table should surface as 'partial'
    with a diagnostic error_text rather than silent 'ok'."""
    client = MagicMock(name="youtube_client")
    client.get_channel_analytics.return_value = _fake_analytics_response()
    result = run_daily_refresh(
        target_date=date(2026, 4, 10), client=client, today=date(2026, 4, 22),
    )
    assert result.status == "partial"
    assert result.error_text is not None
    assert "videos table empty" in result.error_text
    # Channel rows still landed — partial means "channel ok, per-video skipped".
    with dbmod.connect() as conn:
        chan_cnt = conn.execute("SELECT COUNT(*) FROM channel_metric_snapshots").fetchone()[0]
    assert chan_cnt == 2


def test_bounded_error_text_truncates_long_failure_list(fresh_db):
    """Gemini r2 [MED]: aggregated error_text bounded to avoid excessive size."""
    from ingest.jobs import _bounded_error_text, _ERROR_TEXT_MAX
    # Generate 500 fake failures of ~50 chars each = ~25k chars full, exceeds 4k cap.
    failures = [f"vid_{i:04d}: HttpError(403) forbidden by policy" for i in range(500)]
    bounded = _bounded_error_text(failures)
    assert len(bounded) <= _ERROR_TEXT_MAX
    assert "and" in bounded and "more errors, truncated" in bounded


def test_45_day_backfill_exact_range(fresh_db):
    """Codex r2 [MED]: explicit regression for 45-day range boundary fix."""
    from ingest import first_run
    client = MagicMock(name="youtube_client")
    client.get_channel_analytics.return_value = _fake_analytics_response()
    count = first_run.run_first_time_backfill(client=client, today=date(2026, 4, 22))
    # 45 calendar days inclusive: today-46 (2026-03-07) through today-2 (2026-04-20).
    assert count == 45, f"expected exactly 45 daily runs, got {count}"


def test_per_video_writes_atomic_with_retention(fresh_db):
    """Codex+Gemini r2 [MED/LOW]: snapshot + retention writes in one
    transaction. We verify this by forcing a retention-write error after
    snapshot writes completed in-memory, and asserting the snapshot rows
    ALSO rollback (no orphan snapshot without matching retention)."""
    with dbmod.connect() as conn:
        conn.execute("INSERT INTO videos (video_id, title) VALUES ('vABC', 'x')")

    from ingest.jobs import _write_all_atomic
    import sqlite3 as sq
    from app.repositories.metrics import SnapshotRow

    snapshot_rows = [SnapshotRow(
        metric_key="views", grain="weekly",
        window_start="2026-04-13", window_end="2026-04-19",
        observed_on="2026-04-22T00:00:00.000000Z",
        value_num=100.0, run_id="run-test", preliminary=False, video_id="vABC",
    )]
    # Seed ingestion_runs so FK passes.
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES ('run-test', 'test', '2026-04-22T00:00:00Z', 'in_progress')"
        )
    # Retention row referencing a video_id that doesn't exist → FK violation.
    bad_retention = [("ghost_video", "2026-04-22T00:00:00Z", 100.0, 0.5, "run-test")]

    with dbmod.connect() as conn:
        with pytest.raises(sq.IntegrityError):
            _write_all_atomic(conn, snapshot_rows, bad_retention)
        # Atomic rollback: snapshot rows must NOT have landed either.
        cnt = conn.execute(
            "SELECT COUNT(*) FROM video_metric_snapshots WHERE video_id='vABC'"
        ).fetchone()[0]
    assert cnt == 0, "atomic transaction must rollback snapshot rows on retention FK failure"


def test_preliminary_from_week_end_not_target(fresh_db):
    """Codex r1 MED: preliminary must derive from (today - window_end), not
    (today - target_date). Pull a target_date whose week_end is far in the
    past — preliminary must be False even if target_date itself is recent."""
    client = MagicMock(name="youtube_client")
    client.get_channel_analytics.return_value = _fake_analytics_response()
    # target = 2026-04-01 (Wed), week_end = 2026-04-05 (Sun)
    # today = 2026-04-22, today - week_end = 17 days → NOT preliminary.
    run_daily_refresh(target_date=date(2026, 4, 1), client=client, today=date(2026, 4, 22))
    with dbmod.connect() as conn:
        row = conn.execute("SELECT preliminary FROM channel_metric_snapshots LIMIT 1").fetchone()
    assert row["preliminary"] == 0


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
