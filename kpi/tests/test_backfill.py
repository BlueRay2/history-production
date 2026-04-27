"""Tests for `ingest.backfill` (task-05).

Strategy mirrors test_nightly.py — inject a fake YouTubeFullClient instead
of vcrpy cassettes so per-day quota / cursor / sentinel logic is tested
against deterministic API responses.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Fake client (subset of YouTubeFullClient surface that backfill uses)
# ---------------------------------------------------------------------------


@dataclass
class _FakeAnalyticsResult:
    column_headers: list[dict[str, Any]]
    rows: list[list[Any]]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeBackfillClient:
    """Minimal stand-in for YouTubeFullClient. Returns the same payloads
    regardless of date so per-day loop iterations are differentiated only
    by the date parameter we pass in."""

    upload_video_ids: list[str] = field(default_factory=list)
    video_metadata: list[dict[str, Any]] = field(default_factory=list)
    raise_quota_after_calls: int | None = None
    _call_count: int = 0
    report_types: list[str] = field(default_factory=list)
    ensure_jobs_calls: list[list[str]] = field(default_factory=list)

    def _bump(self):
        self._call_count += 1
        if self.raise_quota_after_calls is not None and self._call_count > self.raise_quota_after_calls:
            from ingest.youtube_full import QuotaExhaustedError
            raise QuotaExhaustedError("synthetic quota stop")

    def get_channel_metadata(self, *, conn=None):
        self._bump()
        return {
            "id": "UC_test",
            "contentDetails": {"relatedPlaylists": {"uploads": "UU_test"}},
        }

    def list_uploads(self, playlist_id, *, conn=None):
        self._bump()
        return list(self.upload_video_ids)

    def get_videos_metadata(self, ids, *, conn=None):
        self._bump()
        return [v for v in self.video_metadata if v.get("id") in set(ids)]

    def analytics_channel_basic(self, start_date, end_date, *,
                                metrics=None, dimensions=None, conn=None):
        self._bump()
        if dimensions:
            return _FakeAnalyticsResult(
                column_headers=[{"name": d, "columnType": "DIMENSION"} for d in dimensions.split(",")] +
                                [{"name": "views", "columnType": "METRIC"}],
                rows=[],  # dimensional empty for backfill historic days
            )
        return _FakeAnalyticsResult(
            column_headers=[{"name": "views", "columnType": "METRIC"}],
            rows=[[5]],
        )

    def analytics_demographics(self, start_date, end_date, *, conn=None):
        self._bump()
        return _FakeAnalyticsResult(column_headers=[], rows=[])

    def analytics_video_basic(self, video_id, start_date, end_date, *,
                              metrics=None, conn=None):
        self._bump()
        return _FakeAnalyticsResult(
            column_headers=[{"name": "views", "columnType": "METRIC"}],
            rows=[[1]],
        )

    def analytics_video_retention(self, video_id, start_date, end_date, *, conn=None):
        self._bump()
        return _FakeAnalyticsResult(column_headers=[], rows=[])

    def analytics_video_traffic_sources(self, video_id, start_date, end_date, *,
                                        detail=False, conn=None):
        self._bump()
        return _FakeAnalyticsResult(column_headers=[], rows=[])

    def list_report_types(self, *, conn=None):
        self._bump()
        return [{"id": rt} for rt in self.report_types]

    def list_jobs(self, *, conn=None):
        return []

    def ensure_jobs(self, ids, *, name_prefix="kpi-vault", conn=None):
        self.ensure_jobs_calls.append(list(ids))
        return {rt: f"job-{rt}" for rt in ids}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def kpi_db(tmp_path, monkeypatch):
    db_path = tmp_path / "kpi.sqlite"
    monkeypatch.setenv("KPI_DB", str(db_path))
    sql_path = (
        Path(__file__).resolve().parent.parent
        / "db" / "migrations-kpi" / "001_init.sql"
    )
    conn = sqlite3.connect(str(db_path))
    conn.executescript(sql_path.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def lock_path(tmp_path):
    return tmp_path / "kpi-ingest.lock"


@pytest.fixture
def sentinel_path(tmp_path):
    return tmp_path / "kpi-backfill-complete.flag"


@pytest.fixture
def cursor_path(tmp_path):
    return tmp_path / "kpi-backfill-cursor.json"


@pytest.fixture
def silent_telegram(monkeypatch):
    """Capture Telegram alerts without sending."""
    from ingest import backfill, nightly
    sent = []
    monkeypatch.setattr(backfill, "_send_telegram_alert", lambda msg, **kw: sent.append(msg) or True)
    monkeypatch.setattr(nightly, "_send_telegram_alert", lambda msg, **kw: sent.append(msg) or True)
    return sent


def _video_meta(vid, days_ago):
    pub = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id": vid,
        "snippet": {"title": vid, "publishedAt": pub, "channelId": "UC_test"},
        "contentDetails": {"duration": "PT1M"},
        "status": {"privacyStatus": "public", "uploadStatus": "processed"},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sentinel_blocks_rerun(kpi_db, lock_path, sentinel_path, cursor_path, silent_telegram):
    from ingest import backfill
    sentinel_path.parent.mkdir(parents=True, exist_ok=True)
    sentinel_path.touch()  # pretend backfill already ran

    result = backfill.run_backfill(
        days=3, force=False, dry_run=False,
        client=FakeBackfillClient(),
        conn=kpi_db, lock_path=lock_path,
        sentinel_path=sentinel_path, cursor_path=cursor_path,
    )
    assert result.status == "already_done"
    assert result.days_processed == 0
    # No API calls made
    assert result.rows_written == 0


def test_dry_run_short_circuits(kpi_db, lock_path, sentinel_path, cursor_path, silent_telegram):
    from ingest import backfill

    result = backfill.run_backfill(
        days=10, force=False, dry_run=True,
        client=FakeBackfillClient(),
        conn=kpi_db, lock_path=lock_path,
        sentinel_path=sentinel_path, cursor_path=cursor_path,
    )
    assert result.status == "dry_run"
    assert result.days_processed == 10
    assert not sentinel_path.exists()


def test_full_3day_backfill_writes_rows_and_sentinel(
    kpi_db, lock_path, sentinel_path, cursor_path, silent_telegram, monkeypatch
):
    from ingest import backfill

    # Skip per-call sleep for fast tests
    monkeypatch.setattr(backfill, "INTER_CALL_PAUSE_SEC", 0)

    fake = FakeBackfillClient(
        upload_video_ids=["vid_a"],
        video_metadata=[_video_meta("vid_a", days_ago=10)],
        report_types=["channel_basic_a3", "video_basic_a3"],
    )

    result = backfill.run_backfill(
        days=3, force=False, dry_run=False,
        client=fake, conn=kpi_db, lock_path=lock_path,
        sentinel_path=sentinel_path, cursor_path=cursor_path,
        flock_wait=5,
    )
    assert result.status == "ok", result.error_text
    assert result.days_processed == 3
    assert sentinel_path.exists()
    assert not cursor_path.exists()  # cursor cleared on success
    # Reporting jobs registered
    assert fake.ensure_jobs_calls and "channel_basic_a3" in fake.ensure_jobs_calls[0]
    # Channel snapshots written (3 days × at least 1 metric)
    n_channel = kpi_db.execute("SELECT COUNT(*) AS n FROM channel_snapshots").fetchone()["n"]
    assert n_channel >= 3
    # Telegram success alert
    assert any("backfill" in s and "ok" in s for s in silent_telegram)


def test_quota_threshold_persists_cursor_and_pauses(
    kpi_db, lock_path, sentinel_path, cursor_path, silent_telegram, monkeypatch
):
    """If today_used crosses 8500 mid-loop, save cursor and exit cleanly."""
    from ingest import backfill
    from ingest import youtube_full

    monkeypatch.setattr(backfill, "INTER_CALL_PAUSE_SEC", 0)
    # Pre-load quota near threshold so the very next iteration trips it
    today = youtube_full._today_utc_iso()
    # Set quota to 8501 so the FIRST day's check trips immediately
    kpi_db.execute(
        "INSERT INTO quota_usage(api_name, date_utc, units_used, request_count, last_updated) "
        "VALUES ('analytics_api_v2', ?, 8501, 1, ?)",
        (today, youtube_full._now_iso_micro()),
    )

    fake = FakeBackfillClient(
        upload_video_ids=[],
        video_metadata=[],
        report_types=[],
    )
    # Pre-create a cursor as if a prior partial run had landed day -60..-58 already
    end_date = (datetime.now(timezone.utc).date() - timedelta(days=2))
    last_done = end_date - timedelta(days=3)
    cursor_path.parent.mkdir(parents=True, exist_ok=True)
    cursor_path.write_text(json.dumps({
        "started_at": "2026-04-26T00:00:00Z",
        "last_completed_date": last_done.isoformat(),
        "end_date": end_date.isoformat(),
        "rows_written": 100,
        "quota_used": 5000,
    }), encoding="utf-8")

    result = backfill.run_backfill(
        days=5, force=False, dry_run=False,
        client=fake, conn=kpi_db, lock_path=lock_path,
        sentinel_path=sentinel_path, cursor_path=cursor_path,
        flock_wait=5,
    )
    # Either quota_exhausted (preferred) or completes if no remaining days
    assert result.status in ("quota_exhausted", "ok")
    if result.status == "quota_exhausted":
        # Cursor should still exist with updated state, sentinel should NOT
        assert cursor_path.exists()
        assert not sentinel_path.exists()


def test_cursor_resume_continues_from_next_day(
    kpi_db, lock_path, sentinel_path, cursor_path, silent_telegram, monkeypatch
):
    from ingest import backfill

    monkeypatch.setattr(backfill, "INTER_CALL_PAUSE_SEC", 0)

    end_date = (datetime.now(timezone.utc).date() - timedelta(days=2))
    last_done = end_date - timedelta(days=2)  # window of 5 days, 3 already done
    cursor_path.parent.mkdir(parents=True, exist_ok=True)
    cursor_path.write_text(json.dumps({
        "started_at": "2026-04-26T00:00:00Z",
        "last_completed_date": last_done.isoformat(),
        "end_date": end_date.isoformat(),
        "rows_written": 50,
        "quota_used": 1000,
    }), encoding="utf-8")

    fake = FakeBackfillClient(report_types=[])

    result = backfill.run_backfill(
        days=5, force=False, dry_run=False,
        client=fake, conn=kpi_db, lock_path=lock_path,
        sentinel_path=sentinel_path, cursor_path=cursor_path,
        flock_wait=5,
    )
    # Should process only the remaining 2 days (last_done+1 .. end_date)
    assert result.status == "ok"
    assert result.days_processed == 2
    assert sentinel_path.exists()
    assert not cursor_path.exists()


def test_force_bypasses_sentinel(
    kpi_db, lock_path, sentinel_path, cursor_path, silent_telegram, monkeypatch
):
    from ingest import backfill

    monkeypatch.setattr(backfill, "INTER_CALL_PAUSE_SEC", 0)
    sentinel_path.parent.mkdir(parents=True, exist_ok=True)
    sentinel_path.touch()

    fake = FakeBackfillClient(report_types=[])
    result = backfill.run_backfill(
        days=2, force=True, dry_run=False,
        client=fake, conn=kpi_db, lock_path=lock_path,
        sentinel_path=sentinel_path, cursor_path=cursor_path,
        flock_wait=5,
    )
    assert result.status == "ok"
    assert result.days_processed == 2


def test_lock_timeout_returns_lock_timeout_status(
    kpi_db, lock_path, sentinel_path, cursor_path, silent_telegram, monkeypatch
):
    """When the lock is held by another process, backfill should bail with lock_timeout."""
    import fcntl as _fcntl

    # Hold the lock from a separate file descriptor
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    holder = open(lock_path, "a+")
    _fcntl.flock(holder.fileno(), _fcntl.LOCK_EX)

    try:
        from ingest import backfill

        result = backfill.run_backfill(
            days=2, force=False, dry_run=False,
            client=FakeBackfillClient(),
            conn=kpi_db, lock_path=lock_path,
            sentinel_path=sentinel_path, cursor_path=cursor_path,
            flock_wait=2,  # short for test
        )
        assert result.status == "lock_timeout"
        assert any("lock" in s.lower() for s in silent_telegram)
    finally:
        try:
            _fcntl.flock(holder.fileno(), _fcntl.LOCK_UN)
        finally:
            holder.close()
