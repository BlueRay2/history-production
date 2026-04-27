"""Tests for app.repositories.metrics — append-only snapshot semantics.

Covers:
  - Single-row insert round-trip.
  - Re-run with same PK = no-op (INSERT OR IGNORE).
  - Re-run with fresh observed_on = new row appended.
  - latest_snapshot returns the most recent row.
  - Channel vs per-video row routing.
  - FK enforcement: writing a video_metric row without a matching videos entry fails.
"""

from __future__ import annotations

import pytest

from app import db as dbmod
from app.repositories.metrics import SnapshotRow, latest_snapshot, write_snapshot_batch


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    # Open a single connection reused across assertions in the test for
    # simplicity (each test gets its own tmp DB via fresh_db fixture).
    conn = None
    try:
        ctx = dbmod.connect()
        conn = ctx.__enter__()
        # Seed an ingestion_runs row so our writes satisfy the FK.
        conn.execute(
            "INSERT INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES (?, 'test', '2026-04-21T00:00:00Z', 'ok')",
            ("run-test",),
        )
        yield conn
    finally:
        if conn is not None:
            try:
                ctx.__exit__(None, None, None)  # type: ignore[name-defined]
            except Exception:
                pass


def _row(observed_on: str, metric: str = "views", value: float = 100.0) -> SnapshotRow:
    return SnapshotRow(
        metric_key=metric,
        grain="weekly",
        window_start="2026-04-14",
        window_end="2026-04-20",
        observed_on=observed_on,
        value_num=value,
        run_id="run-test",
        preliminary=True,
        video_id=None,
    )


def test_channel_snapshot_round_trip(fresh_db):
    inserted = write_snapshot_batch(fresh_db, [_row("2026-04-22T00:00:00Z", value=412)])
    assert inserted == 1
    found = latest_snapshot(
        fresh_db,
        metric_key="views", grain="weekly",
        window_start="2026-04-14", window_end="2026-04-20",
    )
    assert found is not None
    assert found["value_num"] == 412.0


def test_same_observed_on_is_noop(fresh_db):
    assert write_snapshot_batch(fresh_db, [_row("2026-04-22T00:00:00Z", value=412)]) == 1
    # Same PK columns — INSERT OR IGNORE should drop it.
    assert write_snapshot_batch(fresh_db, [_row("2026-04-22T00:00:00Z", value=999)]) == 0
    row = latest_snapshot(
        fresh_db,
        metric_key="views", grain="weekly",
        window_start="2026-04-14", window_end="2026-04-20",
    )
    # First value wins.
    assert row["value_num"] == 412.0


def test_fresh_observed_on_appends_new_row(fresh_db):
    assert write_snapshot_batch(fresh_db, [_row("2026-04-22T00:00:00Z", value=412)]) == 1
    assert write_snapshot_batch(fresh_db, [_row("2026-04-22T12:00:00Z", value=500)]) == 1
    latest = latest_snapshot(
        fresh_db,
        metric_key="views", grain="weekly",
        window_start="2026-04-14", window_end="2026-04-20",
    )
    assert latest["observed_on"] == "2026-04-22T12:00:00Z"
    assert latest["value_num"] == 500.0
    # Both rows persist in history.
    cnt = fresh_db.execute("SELECT COUNT(*) FROM channel_metric_snapshots").fetchone()[0]
    assert cnt == 2


def test_video_row_routes_to_video_table(fresh_db):
    # Seed a videos row so FK succeeds.
    fresh_db.execute(
        "INSERT INTO videos (video_id, title) VALUES ('vXYZ', 'Test')",
    )
    video_row = SnapshotRow(
        metric_key="views",
        grain="daily",
        window_start="2026-04-20",
        window_end="2026-04-20",
        observed_on="2026-04-22T00:00:00Z",
        value_num=55,
        run_id="run-test",
        preliminary=False,
        video_id="vXYZ",
    )
    assert write_snapshot_batch(fresh_db, [video_row]) == 1
    # Channel table should be empty; video table has the row.
    assert fresh_db.execute("SELECT COUNT(*) FROM channel_metric_snapshots").fetchone()[0] == 0
    assert fresh_db.execute("SELECT COUNT(*) FROM video_metric_snapshots").fetchone()[0] == 1


def test_video_row_without_videos_entry_fk_fails(fresh_db):
    bad = SnapshotRow(
        metric_key="views",
        grain="daily",
        window_start="2026-04-20",
        window_end="2026-04-20",
        observed_on="2026-04-22T00:00:00Z",
        value_num=55,
        run_id="run-test",
        preliminary=False,
        video_id="nonexistent",
    )
    with pytest.raises(Exception):  # sqlite3.IntegrityError wrapped at executemany
        write_snapshot_batch(fresh_db, [bad])
    # Transaction rolled back.
    assert fresh_db.execute("SELECT COUNT(*) FROM video_metric_snapshots").fetchone()[0] == 0


def test_empty_batch_returns_zero(fresh_db):
    assert write_snapshot_batch(fresh_db, []) == 0
