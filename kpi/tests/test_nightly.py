"""Tests for `ingest.nightly` (task-04).

Strategy: rather than vcrpy for the orchestrator (the underlying API client
is already cassette-covered by task-03 tests), we inject a `FakeFullClient`
that mirrors `YouTubeFullClient`'s public surface. This isolates orchestrator
logic from API-shape concerns and runs deterministically in milliseconds.

Coverage:
  - dry-run smoke (no API calls, orchestrator opens + closes cleanly)
  - flock concurrency (second nightly run exits silently while first holds)
  - quota pre-exhaustion (orchestrator aborts as `quota_exhausted`)
  - happy path (orchestrator status=ok, rows landed in expected tables)
  - per-video failure injection (orchestrator status=partial, channel data persists)
  - reporting CSV parsing (channel-keyed + video-keyed routing)
  - schema drift sync (added/deprecated detection + soft-disable side-effect)
  - dimension-key encoding (skips `day`, joins multi-dim with pipe)
  - duration parser
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import pytest

# Set KPI_DB to in-memory before importing ingest.nightly so module-level
# defaults pick up the correct path.
os.environ.setdefault("KPI_NIGHTLY_LOCK", "/tmp/kpi-nightly-test.lock")


# ---------------------------------------------------------------------------
# Fake client + fixtures
# ---------------------------------------------------------------------------


@dataclass
class _FakeAnalyticsResult:
    column_headers: list[dict[str, Any]]
    rows: list[list[Any]]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeFullClient:
    """Stand-in for YouTubeFullClient with controllable per-call behavior."""

    channel_metadata: dict[str, Any] = field(default_factory=lambda: {
        "id": "UC_test",
        "contentDetails": {"relatedPlaylists": {"uploads": "UU_test"}},
    })
    upload_video_ids: list[str] = field(default_factory=list)
    video_metadata: list[dict[str, Any]] = field(default_factory=list)
    channel_basic_rows: list[list[Any]] = field(default_factory=list)
    channel_basic_headers: list[dict[str, Any]] = field(default_factory=list)
    demographics_rows: list[list[Any]] = field(default_factory=list)
    live_rows: list[list[Any]] = field(default_factory=list)
    per_video_basic: dict[str, list[list[Any]]] = field(default_factory=dict)
    per_video_retention: dict[str, list[list[Any]]] = field(default_factory=dict)
    per_video_traffic: dict[str, list[list[Any]]] = field(default_factory=dict)
    raise_for_video: set[str] = field(default_factory=set)
    report_types_ids: list[str] = field(default_factory=list)
    existing_jobs: dict[str, str] = field(default_factory=dict)
    list_reports_calls: int = 0
    list_reports_returns: list[list[dict[str, Any]]] = field(default_factory=list)
    download_returns: dict[str, Path] = field(default_factory=dict)
    enforce_quota: bool = False

    def get_channel_metadata(self, *, conn=None):
        if self.enforce_quota:
            from ingest.youtube_full import quota_check_and_reserve
            quota_check_and_reserve("channels.list", 1)
        return self.channel_metadata

    def list_uploads(self, playlist_id, *, conn=None):
        return list(self.upload_video_ids)

    def get_videos_metadata(self, ids, *, conn=None):
        return [v for v in self.video_metadata if v.get("id") in set(ids)]

    def analytics_channel_basic(self, start_date, end_date, *,
                                metrics=None, dimensions=None, conn=None):
        if self.enforce_quota:
            from ingest.youtube_full import quota_check_and_reserve
            quota_check_and_reserve("youtubeAnalytics.reports.query", 1)
        if dimensions:
            # Realistic: small channels have no per-dimension rows for a single day.
            # Return zero rows (valid analytics response, exercises empty-rows codepath).
            headers = [{"name": d, "columnType": "DIMENSION"} for d in dimensions.split(",")]
            headers += list(self.channel_basic_headers)
            return _FakeAnalyticsResult(column_headers=headers, rows=[])
        return _FakeAnalyticsResult(
            column_headers=list(self.channel_basic_headers),
            rows=list(self.channel_basic_rows),
        )

    def analytics_demographics(self, start_date, end_date, *, conn=None):
        return _FakeAnalyticsResult(
            column_headers=[
                {"name": "ageGroup", "columnType": "DIMENSION"},
                {"name": "gender", "columnType": "DIMENSION"},
                {"name": "viewerPercentage", "columnType": "METRIC"},
            ],
            rows=list(self.demographics_rows),
        )

    def analytics_live(self, start_date, end_date, *, conn=None):
        return _FakeAnalyticsResult(
            column_headers=[
                {"name": "averageConcurrentViewers", "columnType": "METRIC"},
                {"name": "peakConcurrentViewers", "columnType": "METRIC"},
            ],
            rows=list(self.live_rows),
        )

    def analytics_video_basic(self, video_id, start_date, end_date, *,
                              metrics=None, conn=None):
        if video_id in self.raise_for_video:
            raise RuntimeError(f"injected per-video failure for {video_id}")
        return _FakeAnalyticsResult(
            column_headers=[
                {"name": "views", "columnType": "METRIC"},
                {"name": "likes", "columnType": "METRIC"},
            ],
            rows=list(self.per_video_basic.get(video_id, [])),
        )

    def analytics_video_retention(self, video_id, start_date, end_date, *, conn=None):
        return _FakeAnalyticsResult(
            column_headers=[
                {"name": "elapsedVideoTimeRatio", "columnType": "DIMENSION"},
                {"name": "audienceWatchRatio", "columnType": "METRIC"},
                {"name": "relativeRetentionPerformance", "columnType": "METRIC"},
            ],
            rows=list(self.per_video_retention.get(video_id, [])),
        )

    def analytics_video_traffic_sources(self, video_id, start_date, end_date,
                                        *, detail=False, conn=None):
        return _FakeAnalyticsResult(
            column_headers=[
                {"name": "insightTrafficSourceType", "columnType": "DIMENSION"},
                {"name": "views", "columnType": "METRIC"},
            ],
            rows=list(self.per_video_traffic.get(video_id, [])),
        )

    def list_report_types(self, *, conn=None):
        return [{"id": rt} for rt in self.report_types_ids]

    def list_jobs(self, *, conn=None):
        return [{"reportTypeId": rt, "id": jid} for rt, jid in self.existing_jobs.items()]

    def list_reports(self, job_id, *, since_iso=None, page_size=100, conn=None):
        if not self.list_reports_returns:
            return []
        idx = min(self.list_reports_calls, len(self.list_reports_returns) - 1)
        self.list_reports_calls += 1
        return self.list_reports_returns[idx]

    def download_report(self, report, *, target_dir=None, report_type_id=None, max_attempts=3):
        rid = report.get("id", "")
        return self.download_returns.get(rid, Path("/nonexistent.csv"))


@pytest.fixture
def kpi_db(tmp_path, monkeypatch):
    """Provide a fresh KPI SQLite DB pre-populated via the migration script."""
    db_path = tmp_path / "kpi.sqlite"
    monkeypatch.setenv("KPI_DB", str(db_path))
    # Apply migration 001 directly
    sql_path = (
        Path(__file__).resolve().parent.parent
        / "db"
        / "migrations-kpi"
        / "001_init.sql"
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
def lock_path(tmp_path, monkeypatch):
    p = tmp_path / "nightly.lock"
    monkeypatch.setenv("KPI_NIGHTLY_LOCK", str(p))
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dry_run_opens_and_closes_orchestrator(kpi_db, lock_path):
    from ingest import nightly

    result = nightly.run_nightly(
        target_date=None,
        dry_run=True,
        client=FakeFullClient(),
        conn=kpi_db,
        lock_path=lock_path,
    )
    assert result is not None
    assert result.status == "ok"
    assert result.error_text == "dry-run"
    row = kpi_db.execute(
        "SELECT status FROM ingestion_runs WHERE source='nightly_orchestrator'"
    ).fetchone()
    assert row["status"] == "ok"


def test_flock_concurrency_second_run_exits_silently(kpi_db, lock_path):
    """A second concurrent nightly run must return None without side effects."""
    from ingest import nightly

    holder_done = threading.Event()
    holder_started = threading.Event()

    def _holder() -> None:
        # Hold the flock for ~0.5s while the second call attempts to acquire
        with nightly._nightly_flock(lock_path) as acquired:
            assert acquired
            holder_started.set()
            time.sleep(0.5)
            holder_done.set()

    t = threading.Thread(target=_holder, daemon=True)
    t.start()
    holder_started.wait(timeout=2)

    # Second run during holder window should return None
    result = nightly.run_nightly(
        target_date=None,
        dry_run=True,
        client=FakeFullClient(),
        conn=kpi_db,
        lock_path=lock_path,
    )
    assert result is None
    holder_done.wait(timeout=2)
    t.join(timeout=2)


def test_quota_pre_exhausted_aborts_orchestrator(kpi_db, lock_path, monkeypatch):
    from ingest import nightly
    from ingest import youtube_full

    monkeypatch.setattr(youtube_full, "DAILY_QUOTA_BUDGET_DEFAULT", 100)
    # Pre-load quota_usage so the very first reservation overflows the cap
    today = youtube_full._today_utc_iso()
    kpi_db.execute(
        "INSERT INTO quota_usage(api_name, date_utc, units_used, request_count, last_updated) "
        "VALUES ('data_api_v3', ?, 100, 1, ?)",
        (today, youtube_full._now_iso_micro()),
    )

    fake = FakeFullClient(upload_video_ids=["v1"], enforce_quota=True)
    result = nightly.run_nightly(
        target_date=None,
        dry_run=False,
        client=fake,
        conn=kpi_db,
        lock_path=lock_path,
    )
    assert result is not None
    assert result.status == "quota_exhausted"


def test_happy_path_writes_channel_and_video_rows(kpi_db, lock_path):
    from ingest import nightly

    fake = FakeFullClient(
        upload_video_ids=["vid_alpha"],
        video_metadata=[{
            "id": "vid_alpha",
            "snippet": {
                "title": "Alpha",
                "publishedAt": "2026-04-20T12:00:00Z",
                "channelId": "UC_test",
                "categoryId": "27",
            },
            "contentDetails": {"duration": "PT5M30S"},
            "status": {"privacyStatus": "public", "uploadStatus": "processed"},
        }],
        channel_basic_headers=[
            {"name": "views", "columnType": "METRIC"},
            {"name": "estimatedMinutesWatched", "columnType": "METRIC"},
        ],
        channel_basic_rows=[[100, 200]],
        demographics_rows=[["age25-34", "MALE", 30.0]],
        live_rows=[],
        per_video_basic={"vid_alpha": [[42, 7]]},
        per_video_retention={"vid_alpha": [[0.0, 1.0, 1.05], [0.5, 0.6, 0.95]]},
        per_video_traffic={"vid_alpha": [["YT_SEARCH", 30]]},
        report_types_ids=[],
    )
    result = nightly.run_nightly(
        target_date=None, dry_run=False,
        client=fake, conn=kpi_db, lock_path=lock_path,
    )
    assert result is not None
    assert result.status == "ok", result.failures
    # Channel snapshots: 7 channel-basic dim pulls × 2 metrics each (rows mocked)
    # plus demographics (1 metric). Should be > 0.
    chan_rows = kpi_db.execute("SELECT COUNT(*) AS n FROM channel_snapshots").fetchone()["n"]
    assert chan_rows > 0
    vid_rows = kpi_db.execute("SELECT COUNT(*) AS n FROM video_snapshots").fetchone()["n"]
    assert vid_rows > 0
    ret_rows = kpi_db.execute("SELECT COUNT(*) AS n FROM video_retention_points").fetchone()["n"]
    assert ret_rows == 2


def test_per_video_failure_degrades_to_partial(kpi_db, lock_path):
    from ingest import nightly

    fake = FakeFullClient(
        upload_video_ids=["vid_beta"],
        video_metadata=[{
            "id": "vid_beta",
            "snippet": {
                "title": "Beta",
                "publishedAt": "2026-04-20T12:00:00Z",
                "channelId": "UC_test",
            },
            "contentDetails": {"duration": "PT3M"},
            "status": {"privacyStatus": "public", "uploadStatus": "processed"},
        }],
        channel_basic_headers=[
            {"name": "views", "columnType": "METRIC"},
        ],
        channel_basic_rows=[[10]],
        per_video_basic={"vid_beta": [[1]]},
        raise_for_video={"vid_beta"},  # video_basic call will raise
    )
    result = nightly.run_nightly(
        target_date=None, dry_run=False,
        client=fake, conn=kpi_db, lock_path=lock_path,
    )
    assert result is not None
    assert result.status == "partial"
    assert any("vid_beta" in f for f in result.failures)
    # Channel rows should still be persisted
    assert kpi_db.execute("SELECT COUNT(*) AS n FROM channel_snapshots").fetchone()["n"] > 0


def test_reporting_csv_parsing_routes_channel_and_video(kpi_db, lock_path, tmp_path):
    from ingest import nightly

    # Channel-level CSV (no video_id col)
    chan_csv = tmp_path / "chan.csv"
    chan_csv.write_text(
        "date,views,estimatedMinutesWatched\n"
        "20260420,100,500\n"
        "20260421,120,600\n",
        encoding="utf-8",
    )
    # Video-level CSV
    vid_csv = tmp_path / "vid.csv"
    vid_csv.write_text(
        "date,video_id,views,likes\n"
        "20260420,vid_alpha,42,7\n"
        "20260421,vid_alpha,55,9\n",
        encoding="utf-8",
    )
    # Pre-register a video so video_snapshots FK doesn't fail
    kpi_db.execute(
        "INSERT INTO videos(video_id) VALUES ('vid_alpha')"
    )
    # Pre-register two reporting jobs
    kpi_db.execute(
        "INSERT INTO reporting_jobs(job_id, report_type_id, created_at) "
        "VALUES ('job_chan', 'channel_basic_a3', '2026-04-01T00:00:00Z')"
    )
    kpi_db.execute(
        "INSERT INTO reporting_jobs(job_id, report_type_id, created_at) "
        "VALUES ('job_vid', 'video_basic_a3', '2026-04-01T00:00:00Z')"
    )

    fake = FakeFullClient(
        list_reports_returns=[
            [{"id": "r_chan", "createTime": "2026-04-22T00:00:00Z",
              "startTime": "2026-04-20T00:00:00Z", "endTime": "2026-04-21T00:00:00Z",
              "downloadUrl": "https://example.com/r_chan"}],
            [{"id": "r_vid", "createTime": "2026-04-22T00:00:00Z",
              "startTime": "2026-04-20T00:00:00Z", "endTime": "2026-04-21T00:00:00Z",
              "downloadUrl": "https://example.com/r_vid"}],
        ],
        download_returns={"r_chan": chan_csv, "r_vid": vid_csv},
    )
    # Open an orchestrator-style run row so FK on snapshots resolves
    orch_id = "orch-test"
    kpi_db.execute(
        "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
        "VALUES (?, 'nightly_orchestrator', ?, 'running')",
        (orch_id, "2026-04-22T00:00:00Z"),
    )

    rows, failures = nightly._ingest_reporting_csv(
        kpi_db, fake, orchestrator_run_id=orch_id
    )
    assert failures == []
    # 2 days × 2 metrics = 4 channel rows, 2 days × 2 metrics = 4 video rows
    assert kpi_db.execute("SELECT COUNT(*) AS n FROM channel_snapshots WHERE source='reporting_api'").fetchone()["n"] == 4
    assert kpi_db.execute("SELECT COUNT(*) AS n FROM video_snapshots WHERE source='reporting_api'").fetchone()["n"] == 4
    assert rows == 8


def test_schema_drift_sync_detects_added_and_deprecated(kpi_db, lock_path):
    from ingest import nightly

    # Pre-register one job; new API surface drops it and adds a new one
    kpi_db.execute(
        "INSERT INTO reporting_jobs(job_id, report_type_id, created_at, status) "
        "VALUES ('job_old', 'old_report', '2026-04-01T00:00:00Z', 'active')"
    )
    fake = FakeFullClient(report_types_ids=["new_report"])

    added, deprecated = nightly._sync_schema_drift(kpi_db, fake)
    assert added == ["new_report"]
    assert deprecated == ["old_report"]
    # Drift log entries
    drift_n = kpi_db.execute("SELECT COUNT(*) AS n FROM schema_drift_log").fetchone()["n"]
    assert drift_n == 2
    # Old job soft-disabled
    status = kpi_db.execute(
        "SELECT status FROM reporting_jobs WHERE report_type_id='old_report'"
    ).fetchone()["status"]
    assert status == "disabled"


def test_dimension_key_encoding_skips_day_and_joins_multidim():
    from ingest.nightly import _encode_dimension_key

    headers = [
        {"name": "day", "columnType": "DIMENSION"},
        {"name": "country", "columnType": "DIMENSION"},
        {"name": "deviceType", "columnType": "DIMENSION"},
        {"name": "views", "columnType": "METRIC"},
    ]
    row = ["2026-04-25", "RU", "MOBILE", 100]
    assert _encode_dimension_key(headers, row) == "country=RU|deviceType=MOBILE"


def test_iso8601_duration_parser():
    from ingest.nightly import _iso8601_duration_seconds

    assert _iso8601_duration_seconds("PT0S") == 0
    assert _iso8601_duration_seconds("PT45S") == 45
    assert _iso8601_duration_seconds("PT1H") == 3600
    assert _iso8601_duration_seconds("PT1H30M5S") == 5405
    assert _iso8601_duration_seconds("garbage") is None
    assert _iso8601_duration_seconds("") is None


def test_preflight_quota_skips_orchestrator_open(kpi_db, lock_path, monkeypatch):
    """When daily budget is already met, no orchestrator row is opened."""
    from ingest import nightly
    from ingest import youtube_full

    monkeypatch.setattr(youtube_full, "DAILY_QUOTA_BUDGET_DEFAULT", 50)
    monkeypatch.setattr(nightly, "DAILY_QUOTA_BUDGET_DEFAULT", 50)
    today = youtube_full._today_utc_iso()
    kpi_db.execute(
        "INSERT INTO quota_usage(api_name, date_utc, units_used, request_count, last_updated) "
        "VALUES ('data_api_v3', ?, 50, 1, ?)",
        (today, youtube_full._now_iso_micro()),
    )

    sent: list[str] = []
    monkeypatch.setattr(nightly, "_send_telegram_alert", lambda msg, **kw: sent.append(msg) or True)

    result = nightly.run_nightly(
        target_date=None, dry_run=False,
        client=FakeFullClient(enforce_quota=True),
        conn=kpi_db, lock_path=lock_path,
    )
    assert result is not None
    assert result.status == "quota_exhausted"
    assert result.orchestrator_run_id == "preflight"
    # No orchestrator row created
    n = kpi_db.execute(
        "SELECT COUNT(*) AS n FROM ingestion_runs WHERE source='nightly_orchestrator'"
    ).fetchone()["n"]
    assert n == 0
    # Alert fired
    assert any("quota cap already reached" in s for s in sent)


def test_telegram_alert_invoked_on_partial_status(kpi_db, lock_path, monkeypatch):
    """Per-video failure should produce a 'partial' alert via Telegram."""
    from ingest import nightly

    sent: list[str] = []
    monkeypatch.setattr(nightly, "_send_telegram_alert", lambda msg, **kw: sent.append(msg) or True)

    fake = FakeFullClient(
        upload_video_ids=["vid_gamma"],
        video_metadata=[{
            "id": "vid_gamma",
            "snippet": {"title": "G", "publishedAt": "2026-04-20T12:00:00Z", "channelId": "UC"},
            "contentDetails": {"duration": "PT1M"},
            "status": {"privacyStatus": "public", "uploadStatus": "processed"},
        }],
        channel_basic_headers=[{"name": "views", "columnType": "METRIC"}],
        channel_basic_rows=[[5]],
        per_video_basic={"vid_gamma": [[1]]},
        raise_for_video={"vid_gamma"},
    )
    result = nightly.run_nightly(
        target_date=None, dry_run=False,
        client=fake, conn=kpi_db, lock_path=lock_path,
    )
    assert result is not None and result.status == "partial"
    assert any("status=partial" in s for s in sent)


def test_schema_drift_auto_creates_jobs_for_added_types(kpi_db, lock_path):
    """Phase 6 must call ensure_jobs for newly-detected report types."""
    from ingest import nightly

    calls: list[list[str]] = []

    class _Recorder(FakeFullClient):
        def ensure_jobs(self, report_type_ids, *, name_prefix="kpi-vault", conn=None):
            ids = list(report_type_ids)
            calls.append(ids)
            for rt in ids:
                conn.execute(
                    "INSERT OR IGNORE INTO reporting_jobs(job_id, report_type_id, created_at) "
                    "VALUES (?, ?, ?)",
                    (f"job-{rt}", rt, "2026-04-27T00:00:00Z"),
                )
            return {rt: f"job-{rt}" for rt in ids}

    fake = _Recorder(report_types_ids=["new_a", "new_b"])
    added, deprecated = nightly._sync_schema_drift(kpi_db, fake)
    assert added == ["new_a", "new_b"]
    assert deprecated == []
    assert calls == [["new_a", "new_b"]]


def test_pk_collision_suffix_is_iso8601_valid(kpi_db, lock_path):
    """The microsecond suffix appended on PK collision must keep observed_on
    parseable by SQLite's julianday() — Gemini r1 HIGH finding."""
    from ingest import nightly

    # Trigger a collision: same metric + same dim + same window + same observed_on
    sub_id = "sub-test"
    kpi_db.execute(
        "INSERT INTO ingestion_runs(run_id, source, started_at, status) "
        "VALUES (?, 'analytics_api', '2026-04-27T00:00:00Z', 'running')",
        (sub_id,),
    )
    fixed_ts = "2026-04-27T07:30:00.123456Z"
    kpi_db.execute(
        "INSERT INTO channel_snapshots("
        "metric_key, dimension_key, grain, window_start, window_end, "
        "observed_on, value_num, run_id, source) "
        "VALUES ('views', '', 'day', '2026-04-25', '2026-04-25', ?, 100.0, ?, 'analytics_api')",
        (fixed_ts, sub_id),
    )

    res = nightly._FakeAnalyticsResult_proxy = type(
        "Res", (), {"column_headers": [{"name": "views", "columnType": "METRIC"}],
                    "rows": [[200]],
                    "raw": {}}
    )()
    # Force collision by patching _now_iso_micro to return the same fixed_ts
    import ingest.nightly as nm
    orig = nm._now_iso_micro
    nm._now_iso_micro = lambda: fixed_ts
    try:
        with nightly._batched_writes(kpi_db):
            written = nightly._persist_analytics_result(
                kpi_db, res,
                run_id=sub_id, source="analytics_api",
                grain="day", window_start="2026-04-25", window_end="2026-04-25",
            )
    finally:
        nm._now_iso_micro = orig

    assert written == 1
    # Verify both rows are queryable via julianday() — would fail if observed_on
    # ended in 'Z<int>' (broken format) instead of '<int>Z' (valid).
    n = kpi_db.execute(
        "SELECT COUNT(*) AS n FROM channel_snapshots "
        "WHERE julianday(observed_on) IS NOT NULL"
    ).fetchone()["n"]
    assert n == 2  # the seeded row + the collision-resolved insertion


def test_coerce_numeric_handles_edge_cases():
    from ingest.nightly import _coerce_numeric

    assert _coerce_numeric(None) is None
    assert _coerce_numeric(3.14) == 3.14
    assert _coerce_numeric(0) == 0.0
    assert _coerce_numeric(False) == 0.0
    assert _coerce_numeric(True) == 1.0
    assert _coerce_numeric("4.5") == 4.5
    assert _coerce_numeric("not a number") is None
