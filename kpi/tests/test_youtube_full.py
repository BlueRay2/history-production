"""Tests for YouTubeFullClient (task-03 of kpi TZ).

Focus on quota tracking, retry classification, schema drift detection.
Real API calls are mocked via simple stub clients (no vcrpy needed for the
unit tests in this file — VCR cassettes for integration tests go in
test_youtube_full_integration.py later if added).
"""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import pytest

from app import db_kpi
from ingest import youtube_full as yf


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "kpi-test.sqlite"
    monkeypatch.setenv("KPI_DB", str(db_file))
    db_kpi.migrate()
    yield db_file


# -------------------- Quota tracking ----------------------------------------


def test_quota_check_passes_when_under_budget(temp_db):
    used = yf.quota_check("data_api_v3", 100)
    assert used == 0


def test_quota_check_raises_when_over_budget(temp_db, monkeypatch):
    monkeypatch.setattr(yf, "DAILY_QUOTA_BUDGET_DEFAULT", 1000)
    # Pre-fill 950 units used today
    with sqlite3.connect(str(temp_db)) as c:
        c.execute(
            "INSERT INTO quota_usage(api_name, date_utc, units_used, request_count, last_updated) "
            "VALUES (?, ?, ?, ?, ?)",
            ("data_api_v3", yf._today_utc_iso(), 950, 50, yf._now_iso_micro()),
        )
    with pytest.raises(yf.QuotaExhaustedError):
        yf.quota_check("data_api_v3", 100)


def test_quota_increment_creates_row(temp_db):
    yf.quota_increment("data_api_v3", 5)
    with sqlite3.connect(str(temp_db)) as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT * FROM quota_usage").fetchone()
    assert row["units_used"] == 5
    assert row["request_count"] == 1


def test_quota_increment_upserts(temp_db):
    yf.quota_increment("analytics_api_v2", 3)
    yf.quota_increment("analytics_api_v2", 7)
    with sqlite3.connect(str(temp_db)) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM quota_usage").fetchall()
    assert len(rows) == 1
    assert rows[0]["units_used"] == 10
    assert rows[0]["request_count"] == 2


# -------------------- Schema drift logging ----------------------------------


def test_log_schema_drift_inserts_row(temp_db):
    yf._log_schema_drift("analytics_api", "metric_removed", "fakeMetric", "test note")
    with sqlite3.connect(str(temp_db)) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM schema_drift_log").fetchall()
    assert len(rows) == 1
    assert rows[0]["identifier"] == "fakeMetric"
    assert rows[0]["acknowledged_at"] is None


def test_log_schema_drift_dedupe_via_unique(temp_db):
    """Same (detected_at, source, drift_type, identifier) tuple → INSERT OR IGNORE."""
    now = yf._now_iso_micro()
    # Force same detected_at by manual insert
    with sqlite3.connect(str(temp_db)) as c:
        c.execute(
            "INSERT INTO schema_drift_log(detected_at, source, drift_type, identifier, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (now, "analytics_api", "metric_removed", "x", "first"),
        )
        c.execute(
            "INSERT OR IGNORE INTO schema_drift_log(detected_at, source, drift_type, identifier, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (now, "analytics_api", "metric_removed", "x", "second"),
        )
        rows = c.execute("SELECT COUNT(*) AS n FROM schema_drift_log").fetchone()
    assert rows[0] == 1


# -------------------- Retry classification ----------------------------------


def _http_error(status):
    """Build a fake googleapiclient HttpError with given status."""
    from googleapiclient.errors import HttpError

    resp = MagicMock()
    resp.status = status
    return HttpError(resp=resp, content=b'{"error": "test"}', uri="http://test")


def test_is_transient_classification():
    assert yf._is_transient(_http_error(429)) is True
    assert yf._is_transient(_http_error(503)) is True
    assert yf._is_transient(_http_error(400)) is False
    assert yf._is_transient(_http_error(401)) is False


def test_is_auth_error_classification():
    assert yf._is_auth_error(_http_error(401)) is True
    assert yf._is_auth_error(_http_error(403)) is True
    assert yf._is_auth_error(_http_error(429)) is False


def _http_error_with_message(status: int, message: str):
    """Build an HttpError where str(err) embeds the given message."""
    from googleapiclient.errors import HttpError
    import json

    resp = MagicMock(status=status, reason=message)
    content = json.dumps({"error": {"code": status, "message": message}}).encode()
    return HttpError(resp=resp, content=content, uri="http://test")


def test_is_unknown_identifier_extracts_metric_name():
    err = _http_error_with_message(
        400, "Unknown identifier (impressions) given in field parameters.metrics."
    )
    assert yf._is_unknown_identifier(err) == "impressions"


def test_is_unknown_identifier_returns_none_for_other_errors():
    err = _http_error_with_message(503, "internal server error")
    assert yf._is_unknown_identifier(err) is None


# -------------------- _retry_call orchestration -----------------------------


def test_retry_call_succeeds_first_attempt(temp_db):
    callable_ = MagicMock()
    callable_.execute.return_value = {"ok": 1}
    result = yf._retry_call(callable_, "data_api_v3", 1)
    assert result == {"ok": 1}
    # Quota incremented once
    with sqlite3.connect(str(temp_db)) as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT units_used FROM quota_usage").fetchone()
    assert row["units_used"] == 1


def test_retry_call_backs_off_on_transient_then_succeeds(temp_db, monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(yf.time, "sleep", lambda s: sleeps.append(s))
    callable_ = MagicMock()
    callable_.execute.side_effect = [
        _http_error(503),
        _http_error(503),
        {"ok": 2},
    ]
    result = yf._retry_call(callable_, "data_api_v3", 1, max_attempts=5)
    assert result == {"ok": 2}
    assert sleeps == [1, 2]


def test_retry_call_raises_after_max_attempts(temp_db, monkeypatch):
    monkeypatch.setattr(yf.time, "sleep", lambda s: None)
    callable_ = MagicMock()
    callable_.execute.side_effect = [_http_error(503)] * 5
    from googleapiclient.errors import HttpError

    with pytest.raises(HttpError):
        yf._retry_call(callable_, "data_api_v3", 1, max_attempts=5)


def test_retry_call_fail_fast_on_auth_error(temp_db, monkeypatch):
    monkeypatch.setattr(yf.time, "sleep", lambda s: None)
    callable_ = MagicMock()
    callable_.execute.side_effect = _http_error(401)
    from googleapiclient.errors import HttpError

    with pytest.raises(HttpError):
        yf._retry_call(callable_, "data_api_v3", 1)


def test_retry_call_logs_drift_on_unknown_identifier(temp_db, monkeypatch):
    """A 400 'Unknown identifier' must log to schema_drift_log AND raise SchemaDriftError."""
    monkeypatch.setattr(yf.time, "sleep", lambda s: None)
    err = _http_error_with_message(
        400, "Unknown identifier (impressions) given in field parameters.metrics."
    )
    callable_ = MagicMock()
    callable_.execute.side_effect = err
    with pytest.raises(yf.SchemaDriftError):
        yf._retry_call(callable_, "youtubeAnalytics.reports.query", 1)

    with sqlite3.connect(str(temp_db)) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM schema_drift_log").fetchall()
    assert len(rows) == 1
    assert rows[0]["drift_type"] == "metric_removed"
    assert rows[0]["identifier"] == "impressions"


def test_retry_call_drift_still_charges_quota(temp_db, monkeypatch):
    """Codex r1 MED reversed: failed Data API requests STILL consume quota
    per Google's docs, so our local counter stays aligned with billing."""
    monkeypatch.setattr(yf.time, "sleep", lambda s: None)
    err = _http_error_with_message(400, "Unknown identifier (foo)")
    callable_ = MagicMock()
    callable_.execute.side_effect = err
    with pytest.raises(yf.SchemaDriftError):
        yf._retry_call(callable_, "youtubeAnalytics.reports.query", 1)

    with sqlite3.connect(str(temp_db)) as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT units_used FROM quota_usage").fetchone()
    # Reservation happened at start of _retry_call before API hit.
    assert row is not None
    assert row["units_used"] == 1


# -------------------- Quota cost table ---------------------------------------


def test_jobs_create_cost_is_50():
    """Codex r1 finding F1 in TZ review."""
    assert yf.QUOTA_COST["youtubereporting.jobs.create"] == 50


def test_quota_cost_table_completeness():
    expected = {
        "channels.list", "videos.list", "playlistItems.list", "playlists.list",
        "youtubeAnalytics.reports.query",
        "youtubereporting.jobs.list", "youtubereporting.jobs.create",
        "youtubereporting.jobs.delete", "youtubereporting.jobs.reports.list",
    }
    assert expected.issubset(set(yf.QUOTA_COST))


# -------------------- AnalyticsResult parsing ------------------------------


def test_analytics_result_metric_dimension_split():
    raw = {
        "columnHeaders": [
            {"name": "country", "columnType": "DIMENSION"},
            {"name": "views", "columnType": "METRIC"},
            {"name": "estimatedMinutesWatched", "columnType": "METRIC"},
        ],
        "rows": [["US", 100, 500], ["GB", 50, 250]],
    }
    res = yf.AnalyticsResult(
        column_headers=raw["columnHeaders"], rows=raw["rows"], raw=raw
    )
    assert res.metric_names == ["views", "estimatedMinutesWatched"]
    assert res.dimension_names == ["country"]
    assert len(res.rows) == 2


# -------- Codex r1 / Gemini r1 HIGH: budget aggregated across api_names ------


def test_quota_check_aggregates_across_api_names(temp_db, monkeypatch):
    """Budget cap applies to TOTAL units, not per-method."""
    monkeypatch.setattr(yf, "DAILY_QUOTA_BUDGET_DEFAULT", 100)
    today = yf._today_utc_iso()
    with sqlite3.connect(str(temp_db)) as c:
        c.execute(
            "INSERT INTO quota_usage VALUES (?, ?, ?, ?, ?)",
            ("data_api_v3", today, 60, 1, yf._now_iso_micro()),
        )
        c.execute(
            "INSERT INTO quota_usage VALUES (?, ?, ?, ?, ?)",
            ("analytics_api_v2", today, 30, 1, yf._now_iso_micro()),
        )
    # Total = 90; cap = 100; +5 OK
    assert yf.quota_check("any", 5) == 90
    # +20 NOT OK (90+20=110 > 100)
    with pytest.raises(yf.QuotaExhaustedError):
        yf.quota_check("any", 20)


def test_quota_check_and_reserve_atomic(temp_db, monkeypatch):
    """Reservation is atomic (BEGIN IMMEDIATE)."""
    monkeypatch.setattr(yf, "DAILY_QUOTA_BUDGET_DEFAULT", 50)
    total = yf.quota_check_and_reserve("youtubeAnalytics.reports.query", 30)
    assert total == 30
    total2 = yf.quota_check_and_reserve("channels.list", 10)
    assert total2 == 40
    # +15 over cap
    with pytest.raises(yf.QuotaExhaustedError):
        yf.quota_check_and_reserve("videos.list", 15)
    # Failed reservation MUST NOT have committed
    with sqlite3.connect(str(temp_db)) as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT api_name, units_used FROM quota_usage ORDER BY api_name"
        ).fetchall()
    assert len(rows) == 2
    by_api = {r["api_name"]: r["units_used"] for r in rows}
    assert by_api == {"youtubeAnalytics.reports.query": 30, "channels.list": 10}


# -------- Codex r1 HIGH: 403 quotaExceeded != auth -------------------------


def test_403_quotaExceeded_is_transient_not_auth():
    err = _http_error_with_message(
        403, '{"error":{"errors":[{"reason":"quotaExceeded"}]}}'
    )
    assert yf._is_transient(err) is True
    assert yf._is_auth_error(err) is False
    assert yf._is_rate_limit_403(err) is True


def test_403_genuine_auth_remains_auth_error():
    err = _http_error_with_message(403, "forbidden — wrong scope")
    assert yf._is_auth_error(err) is True
    assert yf._is_transient(err) is False


def test_401_remains_auth_error():
    err = _http_error_with_message(401, "Invalid Credentials")
    assert yf._is_auth_error(err) is True
    assert yf._is_transient(err) is False


# -------- Codex r1 HIGH: network errors are transient ----------------------


def test_connection_error_is_transient():
    assert yf._is_transient(ConnectionError("ECONNRESET")) is True


def test_timeout_error_is_transient():
    assert yf._is_transient(TimeoutError("DNS lookup")) is True


def test_oserror_is_transient():
    assert yf._is_transient(OSError("network")) is True


def test_value_error_is_not_transient():
    assert yf._is_transient(ValueError("nope")) is False


def test_retry_call_retries_connection_error(temp_db, monkeypatch):
    monkeypatch.setattr(yf.time, "sleep", lambda s: None)
    callable_ = MagicMock()
    callable_.execute.side_effect = [
        ConnectionError("ECONNRESET"),
        ConnectionError("ECONNRESET"),
        {"ok": 1},
    ]
    result = yf._retry_call(callable_, "data_api_v3", 1, max_attempts=5)
    assert result == {"ok": 1}


# -------- Codex r1 MED: failed requests still count for billing -----------


def test_retry_call_charges_quota_even_on_failure(temp_db, monkeypatch):
    """When transient retries are exhausted, quota was already reserved upfront —
    matches Google's behavior: rejected requests still consume quota."""
    monkeypatch.setattr(yf.time, "sleep", lambda s: None)
    callable_ = MagicMock()
    callable_.execute.side_effect = [_http_error(503)] * 5
    from googleapiclient.errors import HttpError

    with pytest.raises(HttpError):
        yf._retry_call(callable_, "data_api_v3", 1, max_attempts=5)
    with sqlite3.connect(str(temp_db)) as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT units_used FROM quota_usage WHERE api_name='data_api_v3'").fetchone()
    # Reservation happened up-front, before the retries.
    assert row is not None
    assert row["units_used"] == 1


def test_quota_exhausted_error_does_not_charge(temp_db, monkeypatch):
    """If reservation fails (over budget), quota_usage should NOT have new row."""
    monkeypatch.setattr(yf, "DAILY_QUOTA_BUDGET_DEFAULT", 5)
    callable_ = MagicMock()
    with pytest.raises(yf.QuotaExhaustedError):
        yf._retry_call(callable_, "data_api_v3", 100)
    with sqlite3.connect(str(temp_db)) as c:
        rows = c.execute("SELECT * FROM quota_usage").fetchall()
    assert rows == []


# -------- Codex r1 MED: reportTypes.list uses correct api_name -------------


def test_reporttypes_list_billed_separately():
    """Codex r1 MED: previously reportTypes.list was billed under jobs.list."""
    assert "youtubereporting.reportTypes.list" in yf.QUOTA_COST


# -------- Gemini r1 HIGH: client method coverage --------------------------


def _make_client_with_mocks():
    """Build a YouTubeFullClient with all 3 service handles replaced by MagicMocks."""
    c = yf.YouTubeFullClient.__new__(yf.YouTubeFullClient)
    c._data = MagicMock()
    c._analytics = MagicMock()
    c._reporting = MagicMock()
    return c


def test_get_channel_metadata_extracts_first_item(temp_db):
    c = _make_client_with_mocks()
    c._data.channels().list().execute.return_value = {
        "items": [{"snippet": {"title": "Cities Evolution"}, "statistics": {"subscriberCount": "57"}}]
    }
    meta = c.get_channel_metadata()
    assert meta["snippet"]["title"] == "Cities Evolution"


def test_get_channel_metadata_raises_on_empty_items(temp_db):
    c = _make_client_with_mocks()
    c._data.channels().list().execute.return_value = {"items": []}
    with pytest.raises(RuntimeError, match="0 items"):
        c.get_channel_metadata()


def test_list_uploads_paginates(temp_db):
    c = _make_client_with_mocks()
    list_call = c._data.playlistItems().list
    list_call().execute.side_effect = [
        {"items": [{"contentDetails": {"videoId": f"v{i}"}} for i in range(50)],
         "nextPageToken": "p2"},
        {"items": [{"contentDetails": {"videoId": f"v{i}"}} for i in range(50, 60)]},
    ]
    ids = c.list_uploads("uploads-pl")
    assert len(ids) == 60
    assert ids[0] == "v0" and ids[-1] == "v59"


def test_get_videos_metadata_chunks_by_50(temp_db):
    c = _make_client_with_mocks()
    list_call = c._data.videos().list
    # 130 ids → 3 chunks (50/50/30)
    list_call().execute.side_effect = [
        {"items": [{"id": f"v{i}"} for i in range(50)]},
        {"items": [{"id": f"v{i}"} for i in range(50, 100)]},
        {"items": [{"id": f"v{i}"} for i in range(100, 130)]},
    ]
    ids = [f"v{i}" for i in range(130)]
    out = c.get_videos_metadata(ids)
    assert len(out) == 130


def test_ensure_jobs_idempotent_skip_existing(temp_db, monkeypatch):
    c = _make_client_with_mocks()
    c._reporting.jobs().list().execute.return_value = {
        "jobs": [
            {"id": "j1", "reportTypeId": "channel_basic_a3"},
            {"id": "j2", "reportTypeId": "channel_cards_a1"},
        ]
    }
    # Should not call .create() at all
    out = c.ensure_jobs(["channel_basic_a3", "channel_cards_a1"])
    assert out == {"channel_basic_a3": "j1", "channel_cards_a1": "j2"}
    c._reporting.jobs().create.assert_not_called()


def test_ensure_jobs_creates_missing(temp_db, monkeypatch):
    c = _make_client_with_mocks()
    c._reporting.jobs().list().execute.return_value = {"jobs": []}
    c._reporting.jobs().create().execute.return_value = {"id": "j-new"}
    out = c.ensure_jobs(["channel_basic_a3"])
    assert out == {"channel_basic_a3": "j-new"}
    # 50 units charged for jobs.create
    with sqlite3.connect(str(temp_db)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT api_name, units_used FROM quota_usage").fetchall()
    by_api = {r["api_name"]: r["units_used"] for r in rows}
    assert by_api.get("youtubereporting.jobs.create") == 50


def test_list_report_types_filters_deprecated(temp_db):
    c = _make_client_with_mocks()
    c._reporting.reportTypes().list().execute.return_value = {
        "reportTypes": [
            {"id": "active_a1"},
            {"id": "deprecated_a1", "deprecateTime": "2025-01-01T00:00:00Z"},
            {"id": "active_b1"},
        ]
    }
    out = c.list_report_types()
    ids = [t["id"] for t in out]
    assert "active_a1" in ids and "active_b1" in ids
    assert "deprecated_a1" not in ids


# -------- download_report atomicity (Codex r1 MED) -------------------------


def test_download_report_atomic_rename(tmp_path, monkeypatch):
    """Successful download writes to .partial then renames to final name."""
    c = _make_client_with_mocks()

    class FakeCreds:
        valid = True
        token = "t"

    c._reporting._http = MagicMock(credentials=FakeCreds())

    class FakeResponse:
        text = "csv,data\n1,2\n"

        def raise_for_status(self):
            return None

    monkeypatch.setattr(yf.requests if hasattr(yf, "requests") else __import__("requests"),
                        "get", lambda *a, **kw: FakeResponse())
    target_dir = tmp_path / "csvs"
    out = c.download_report(
        {"id": "r1", "downloadUrl": "https://example/csv"},
        target_dir=target_dir,
        report_type_id="channel_basic_a3",
    )
    assert out.exists()
    assert out.read_text() == "csv,data\n1,2\n"
    # No leftover .partial
    assert not (target_dir / "channel_basic_a3" / "r1.csv.partial").exists()


def test_download_report_skips_existing_nonempty(tmp_path):
    c = _make_client_with_mocks()
    target_dir = tmp_path / "csvs" / "channel_basic_a3"
    target_dir.mkdir(parents=True)
    existing = target_dir / "r1.csv"
    existing.write_text("already here")
    # Should NOT call requests.get (would fail because no requests stub)
    out = c.download_report(
        {"id": "r1", "downloadUrl": "https://example/csv"},
        target_dir=tmp_path / "csvs",
        report_type_id="channel_basic_a3",
    )
    assert out == existing
    assert out.read_text() == "already here"
