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


def test_retry_call_does_not_increment_quota_on_drift(temp_db, monkeypatch):
    """If API rejects with 'Unknown identifier', YouTube doesn't bill us — we shouldn't count it."""
    monkeypatch.setattr(yf.time, "sleep", lambda s: None)
    err = _http_error_with_message(400, "Unknown identifier (foo)")
    callable_ = MagicMock()
    callable_.execute.side_effect = err
    with pytest.raises(yf.SchemaDriftError):
        yf._retry_call(callable_, "youtubeAnalytics.reports.query", 1)

    with sqlite3.connect(str(temp_db)) as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT * FROM quota_usage").fetchone()
    assert row is None


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
