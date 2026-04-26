"""Extended YouTube API client for the kpi metrics vault (task-03 of TZ).

Covers three APIs in one typed facade:
  - YouTube Data API v3       (channel/video/playlist metadata)
  - YouTube Analytics API v2  (per-day metrics + dimension breakdowns)
  - YouTube Reporting API v1  (CSV bulk reports via async job model)

Quota budgeting:
  Each public method estimates quota cost via QUOTA_COST table BEFORE the call,
  checks the daily budget against `quota_usage` table (task-01 schema), and
  refuses to call if the call would push us over the daily cap. After successful
  call, increments `quota_usage` atomically.

Retry policy:
  Transient (5xx, 408, 429): exponential backoff 1/2/4/8/16 s, max 5 attempts.
  Auth errors (401 after refresh, 403): fail-fast, classified as `auth_failed`.
  400 'Unknown identifier' for metrics: fail-fast, logged to `schema_drift_log`
  as `metric_removed` (auto-detected drift).
  Network errors (DNS, TLS, ECONNRESET): treated as transient.

Scopes — current OAuth permits only:
  - https://www.googleapis.com/auth/youtube.readonly
  - https://www.googleapis.com/auth/yt-analytics.readonly
Monetary scope (`yt-analytics-monetary.readonly`) is NOT available per TZ
locked decision D3 (Brimit org constraints on Google Cloud Console
verification). Methods touching revenue / CPM / ad-impressions are
intentionally absent.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ingest.youtube_client import (  # type: ignore[import-not-found]
    DEFAULT_ENV_PATH,
    YouTubeClient,  # reuse cred loader
    _build_credentials,
    _load_creds,
)

_LOG = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Quota costs per endpoint (units).
# Sources cross-checked: https://developers.google.com/youtube/v3/getting-started#quota
# and https://developers.google.com/youtube/reporting/v1
# ----------------------------------------------------------------------------
QUOTA_COST: dict[str, int] = {
    # Data API v3
    "channels.list": 1,
    "videos.list": 1,
    "playlistItems.list": 1,
    "playlists.list": 1,
    # Analytics API v2 — 1 unit per query under non-monetary scope
    "youtubeAnalytics.reports.query": 1,
    # Reporting API v1
    "youtubereporting.jobs.list": 1,
    "youtubereporting.reportTypes.list": 1,    # Codex r1 MED: separate from jobs.list
    # Codex r1 finding F1 in TZ review: jobs.create costs 50 units, NOT 1.
    "youtubereporting.jobs.create": 50,
    "youtubereporting.jobs.delete": 50,
    "youtubereporting.jobs.reports.list": 1,
    # CSV download is HTTP GET to googleapis CDN — not counted.
}

DAILY_QUOTA_BUDGET_DEFAULT = int(os.environ.get("KPI_DAILY_QUOTA_BUDGET", "9000"))
"""Default safety cap = 90% of YouTube's 10,000 unit daily quota."""

DEFAULT_REPORTING_CSV_DIR = Path(
    os.environ.get("KPI_REPORTING_CSV_DIR", "/home/aiagent/assistant/state/kpi-reporting-csv")
)


class QuotaExhaustedError(RuntimeError):
    """Raised pre-flight when call would exceed daily quota budget."""


class SchemaDriftError(RuntimeError):
    """Raised when API rejects a metric/dimension that we expected to work."""


@dataclass(frozen=True)
class AnalyticsResult:
    """Normalized response from `youtubeAnalytics.reports.query`."""

    column_headers: list[dict[str, Any]]
    rows: list[list[Any]]
    raw: dict[str, Any]

    @property
    def metric_names(self) -> list[str]:
        return [
            h["name"]
            for h in self.column_headers
            if h.get("columnType") != "DIMENSION"
        ]

    @property
    def dimension_names(self) -> list[str]:
        return [h["name"] for h in self.column_headers if h.get("columnType") == "DIMENSION"]


# ----------------------------------------------------------------------------
# Quota tracking — minimal shim to read/write quota_usage in kpi.sqlite
# ----------------------------------------------------------------------------


def _kpi_db_path() -> str:
    return os.environ.get("KPI_DB", "/home/aiagent/assistant/state/kpi.sqlite")


def _connect_kpi_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_kpi_db_path(), timeout=10.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    return conn


def _today_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_iso_micro() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _today_total_units(conn: sqlite3.Connection, today: str) -> int:
    """Sum of units_used across ALL api_name rows for the given UTC date."""
    row = conn.execute(
        "SELECT COALESCE(SUM(units_used), 0) AS total FROM quota_usage WHERE date_utc=?",
        (today,),
    ).fetchone()
    return int(row["total"]) if row else 0


def quota_check_and_reserve(
    api_name: str, units: int, *, conn: sqlite3.Connection | None = None
) -> int:
    """ATOMICALLY check + reserve quota in a single SQLite transaction.

    Codex r1 / Gemini r1 finding (HIGH): the previous separate
    `quota_check` + `quota_increment` was a TOCTOU race — concurrent runs
    could each pass the check before either incremented. This function
    wraps both in `BEGIN IMMEDIATE` so SQLite serializes the read+write.

    Also (Codex r1 HIGH): budget is now applied to the SUM across ALL
    api_name rows for the day, not per-api-method. The 9000-unit cap is
    YouTube's daily project quota — split across endpoints, not per-method.

    UTC midnight rollover: today is captured ONCE at the top of the txn so
    a check that crosses 00:00:00Z will not commit to the wrong date.

    Returns the total used-today value AFTER reservation.
    """
    own_conn = conn is None
    conn = conn or _connect_kpi_db()
    today = _today_utc_iso()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            total_used = _today_total_units(conn, today)
            budget = DAILY_QUOTA_BUDGET_DEFAULT
            if total_used + units > budget:
                conn.execute("ROLLBACK")
                raise QuotaExhaustedError(
                    f"daily quota cap {budget} would be exceeded "
                    f"(today_total_used={total_used}, requested={units}, api={api_name})"
                )
            conn.execute(
                """
                INSERT INTO quota_usage(api_name, date_utc, units_used, request_count, last_updated)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(api_name, date_utc) DO UPDATE SET
                    units_used = units_used + excluded.units_used,
                    request_count = request_count + 1,
                    last_updated = excluded.last_updated
                """,
                (api_name, today, units, _now_iso_micro()),
            )
            conn.execute("COMMIT")
            return total_used + units
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass  # not in a transaction
            raise
    finally:
        if own_conn:
            conn.close()


# Backward-compat thin wrappers (used by older callers + tests). Prefer
# quota_check_and_reserve in new code.
def quota_check(api_name: str, units: int, *, conn: sqlite3.Connection | None = None) -> int:
    """Read-only check across all api_names for today. Raises if over budget."""
    own_conn = conn is None
    conn = conn or _connect_kpi_db()
    try:
        used = _today_total_units(conn, _today_utc_iso())
        budget = DAILY_QUOTA_BUDGET_DEFAULT
        if used + units > budget:
            raise QuotaExhaustedError(
                f"daily quota cap {budget} would be exceeded "
                f"(today_total_used={used}, requested={units}, api={api_name})"
            )
        return used
    finally:
        if own_conn:
            conn.close()


def quota_increment(api_name: str, units: int, *, conn: sqlite3.Connection | None = None) -> None:
    """Atomic bump (no budget check). Used for refunds/manual adjustments."""
    own_conn = conn is None
    conn = conn or _connect_kpi_db()
    try:
        conn.execute(
            """
            INSERT INTO quota_usage(api_name, date_utc, units_used, request_count, last_updated)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(api_name, date_utc) DO UPDATE SET
                units_used = units_used + excluded.units_used,
                request_count = request_count + 1,
                last_updated = excluded.last_updated
            """,
            (api_name, _today_utc_iso(), units, _now_iso_micro()),
        )
    finally:
        if own_conn:
            conn.close()


# ----------------------------------------------------------------------------
# Schema drift logging
# ----------------------------------------------------------------------------


def _log_schema_drift(
    source: str,
    drift_type: str,
    identifier: str,
    notes: str | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> None:
    own_conn = conn is None
    conn = conn or _connect_kpi_db()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_drift_log
                (detected_at, source, drift_type, identifier, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (_now_iso_micro(), source, drift_type, identifier, notes),
        )
    finally:
        if own_conn:
            conn.close()


# ----------------------------------------------------------------------------
# Retry helper
# ----------------------------------------------------------------------------


def _is_transient(err: Exception) -> bool:
    """Codex r1 HIGH: also accept non-HttpError transport failures.

    Includes:
      - HttpError with 408/429/500/502/503/504
      - HttpError with 403 reason in {quotaExceeded, rateLimitExceeded, userRateLimitExceeded}
      - Network exceptions: ConnectionError, OSError, TimeoutError, requests RequestException
    """
    if isinstance(err, HttpError):
        status = getattr(err.resp, "status", None)
        if status in (408, 429, 500, 502, 503, 504):
            return True
        if status == 403 and _is_rate_limit_403(err):
            return True
        return False
    # Transport-level: socket / TLS / DNS / connection reset
    if isinstance(err, (ConnectionError, TimeoutError)):
        return True
    try:
        from requests.exceptions import RequestException

        if isinstance(err, RequestException):
            return True
    except ImportError:
        pass
    if isinstance(err, OSError):
        # broad net for socket/EAGAIN/ECONNRESET; OK because we only retry transient
        return True
    return False


def _is_rate_limit_403(err: HttpError) -> bool:
    """Distinguish quotaExceeded / rateLimitExceeded 403s from auth 403s.

    Codex r1 HIGH: 403 is NOT always auth — Google returns 403 for quota too,
    and those should be retried (or surface as QuotaExhaustedError) rather than
    treated as a permanent auth failure.
    """
    text = str(err).lower()
    rate_indicators = (
        "quotaexceeded", "ratelimitexceeded", "userratelimitexceeded",
        "quota exceeded", "rate limit exceeded",
    )
    return any(ind in text for ind in rate_indicators)


def _is_auth_error(err: Exception) -> bool:
    """True only for genuine auth failures (not quota 403s)."""
    if not isinstance(err, HttpError):
        return False
    status = getattr(err.resp, "status", None)
    if status == 401:
        return True
    if status == 403 and not _is_rate_limit_403(err):
        return True
    return False


def _is_unknown_identifier(err: Exception) -> str | None:
    """If error message indicates an unknown metric/dimension, return its name."""
    if not isinstance(err, HttpError):
        return None
    text = str(err)
    if "Unknown identifier" not in text:
        return None
    # parse like: 'Unknown identifier (impressions) given in field parameters.metrics.'
    import re

    m = re.search(r"Unknown identifier \(([^)]+)\)", text)
    return m.group(1) if m else "unknown"


def _retry_call(
    callable_,
    api_name: str,
    units: int,
    *,
    conn: sqlite3.Connection | None = None,
    max_attempts: int = 5,
):
    """Run `callable_` with atomic quota reservation + exp backoff retry.

    Codex r1 / Gemini r1 HIGH: budget reservation is now atomic via
    quota_check_and_reserve (BEGIN IMMEDIATE). On API rejection, we DO NOT
    refund — YouTube's documentation states that rejected requests still
    consume quota (Codex r1 MED finding), so our local counter must stay
    aligned with Google's billing. The only refund case is QuotaExhaustedError
    (which never reaches the API).

    On schema drift, raises SchemaDriftError; on auth error, raises HttpError
    unwrapped; on transient (5xx, 429, quota-403, network) retries with
    exp backoff (1/2/4/8/16 s).
    """
    # Codex r2 HIGH: each retry attempt is a separate API request that YouTube
    # bills. Reserve up-front for attempt 1, and re-reserve on every subsequent
    # retry — this also gives natural backpressure: if a hot retry loop crosses
    # the daily cap, QuotaExhaustedError aborts the loop instead of hammering.
    quota_check_and_reserve(api_name, units, conn=conn)
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return callable_.execute()
        except Exception as exc:
            last_exc = exc
            unknown = _is_unknown_identifier(exc)
            if unknown is not None:
                _log_schema_drift(
                    source="analytics_api" if "Analytics" in api_name else "data_api",
                    drift_type="metric_removed",
                    identifier=unknown,
                    notes=f"API rejected as unknown identifier on {api_name}",
                    conn=conn,
                )
                raise SchemaDriftError(f"{api_name}: unknown identifier {unknown}") from exc
            if _is_auth_error(exc):
                raise
            if not _is_transient(exc) or attempt == max_attempts:
                raise
            wait = 2 ** (attempt - 1)
            status = getattr(getattr(exc, "resp", None), "status", "—")
            _LOG.warning(
                "transient %s on %s attempt=%d, sleeping=%ds: %s",
                status, api_name, attempt, wait, str(exc)[:120],
            )
            time.sleep(wait)
            # Per-retry reservation. If we cross the budget mid-loop the
            # QuotaExhaustedError will abort the retry naturally.
            quota_check_and_reserve(api_name, units, conn=conn)
    assert last_exc is not None
    raise last_exc


# ----------------------------------------------------------------------------
# YouTubeFullClient — full coverage facade
# ----------------------------------------------------------------------------


@dataclass
class YouTubeFullClient:
    """Typed wrapper for Data API v3 + Analytics v2 + Reporting v1.

    Construction loads OAuth credentials via the existing `YouTubeClient`
    lower-layer auth (re-uses refresh token + client_secret.json from
    ~/.config/youtube-api/).

    All public methods accept `conn` keyword for sharing a single SQLite
    connection across a batch — saves connection overhead for nightly runs
    that touch quota_usage many times.
    """

    env_path: Path = DEFAULT_ENV_PATH
    client_secret_path: Path = Path("/home/aiagent/.config/youtube-api/client_secret.json")
    _data: Any = field(init=False, default=None)
    _analytics: Any = field(init=False, default=None)
    _reporting: Any = field(init=False, default=None)

    def __post_init__(self) -> None:
        creds = _load_creds(self.env_path, self.client_secret_path)
        google_creds = _build_credentials(creds)
        self._data = build("youtube", "v3", credentials=google_creds, cache_discovery=False)
        self._analytics = build(
            "youtubeAnalytics", "v2", credentials=google_creds, cache_discovery=False
        )
        self._reporting = build(
            "youtubereporting", "v1", credentials=google_creds, cache_discovery=False
        )

    # ------------------------------------------------------------------ DATA
    def get_channel_metadata(
        self, *, conn: sqlite3.Connection | None = None
    ) -> dict[str, Any]:
        req = self._data.channels().list(
            mine=True,
            part="snippet,statistics,brandingSettings,contentDetails,topicDetails,status",
        )
        res = _retry_call(req, "channels.list", QUOTA_COST["channels.list"], conn=conn)
        items = res.get("items", [])
        if not items:
            raise RuntimeError("channels.list returned 0 items — token mis-scoped?")
        return items[0]

    def list_uploads(
        self, playlist_id: str, *, conn: sqlite3.Connection | None = None
    ) -> list[str]:
        """Return all video_ids from the uploads playlist (pagination handled)."""
        ids: list[str] = []
        page_token: str | None = None
        while True:
            kwargs = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": 50}
            if page_token:
                kwargs["pageToken"] = page_token
            req = self._data.playlistItems().list(**kwargs)
            res = _retry_call(req, "playlistItems.list", QUOTA_COST["playlistItems.list"], conn=conn)
            ids.extend(it["contentDetails"]["videoId"] for it in res.get("items", []))
            page_token = res.get("nextPageToken")
            if not page_token:
                break
        return ids

    def get_videos_metadata(
        self, video_ids: list[str], *, conn: sqlite3.Connection | None = None
    ) -> list[dict[str, Any]]:
        """Batch fetch metadata for up to N video_ids (chunks of 50)."""
        out: list[dict[str, Any]] = []
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i : i + 50]
            req = self._data.videos().list(
                part="snippet,contentDetails,statistics,topicDetails,status",
                id=",".join(batch),
            )
            res = _retry_call(req, "videos.list", QUOTA_COST["videos.list"], conn=conn)
            out.extend(res.get("items", []))
        return out

    # ------------------------------------------------------------- ANALYTICS
    def _analytics_query(
        self,
        *,
        ids: str = "channel==MINE",
        start_date: str,
        end_date: str,
        metrics: str,
        dimensions: str | None = None,
        filters: str | None = None,
        max_results: int = 200,
        sort: str | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> AnalyticsResult:
        kwargs: dict[str, Any] = dict(
            ids=ids,
            startDate=start_date,
            endDate=end_date,
            metrics=metrics,
            maxResults=max_results,
        )
        if dimensions:
            kwargs["dimensions"] = dimensions
        if filters:
            kwargs["filters"] = filters
        if sort:
            kwargs["sort"] = sort
        req = self._analytics.reports().query(**kwargs)
        res = _retry_call(
            req,
            "youtubeAnalytics.reports.query",
            QUOTA_COST["youtubeAnalytics.reports.query"],
            conn=conn,
        )
        return AnalyticsResult(
            column_headers=res.get("columnHeaders", []),
            rows=res.get("rows", []) or [],
            raw=res,
        )

    # Channel-level convenience methods
    def analytics_channel_basic(
        self,
        start_date: str,
        end_date: str,
        *,
        metrics: str = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost,likes,comments,shares,videosAddedToPlaylists,videosRemovedFromPlaylists",
        dimensions: str | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> AnalyticsResult:
        return self._analytics_query(
            start_date=start_date,
            end_date=end_date,
            metrics=metrics,
            dimensions=dimensions,
            conn=conn,
        )

    def analytics_channel_cards(
        self,
        start_date: str,
        end_date: str,
        *,
        conn: sqlite3.Connection | None = None,
    ) -> AnalyticsResult:
        return self._analytics_query(
            start_date=start_date,
            end_date=end_date,
            metrics="cardImpressions,cardClicks,cardClickRate,cardTeaserImpressions,cardTeaserClicks,cardTeaserClickRate",
            conn=conn,
        )

    def analytics_demographics(
        self, start_date: str, end_date: str, *, conn: sqlite3.Connection | None = None
    ) -> AnalyticsResult:
        return self._analytics_query(
            start_date=start_date,
            end_date=end_date,
            metrics="viewerPercentage",
            dimensions="ageGroup,gender",
            conn=conn,
        )

    def analytics_geography(
        self,
        start_date: str,
        end_date: str,
        *,
        breakdown: str = "country",
        conn: sqlite3.Connection | None = None,
    ) -> AnalyticsResult:
        return self._analytics_query(
            start_date=start_date,
            end_date=end_date,
            metrics="views,estimatedMinutesWatched",
            dimensions=breakdown,
            sort="-views",
            conn=conn,
        )

    def analytics_traffic_sources(
        self,
        start_date: str,
        end_date: str,
        *,
        detail: bool = False,
        conn: sqlite3.Connection | None = None,
    ) -> AnalyticsResult:
        dim = "insightTrafficSourceType"
        if detail:
            dim = "insightTrafficSourceType,insightTrafficSourceDetail"
        return self._analytics_query(
            start_date=start_date,
            end_date=end_date,
            metrics="views,estimatedMinutesWatched",
            dimensions=dim,
            conn=conn,
        )

    def analytics_playback_locations(
        self, start_date: str, end_date: str, *, conn: sqlite3.Connection | None = None
    ) -> AnalyticsResult:
        return self._analytics_query(
            start_date=start_date,
            end_date=end_date,
            metrics="views,estimatedMinutesWatched",
            dimensions="insightPlaybackLocationType",
            conn=conn,
        )

    def analytics_devices_os(
        self, start_date: str, end_date: str, *, conn: sqlite3.Connection | None = None
    ) -> AnalyticsResult:
        return self._analytics_query(
            start_date=start_date,
            end_date=end_date,
            metrics="views,estimatedMinutesWatched",
            dimensions="deviceType,operatingSystem",
            conn=conn,
        )

    def analytics_sharing_services(
        self, start_date: str, end_date: str, *, conn: sqlite3.Connection | None = None
    ) -> AnalyticsResult:
        return self._analytics_query(
            start_date=start_date,
            end_date=end_date,
            metrics="shares",
            dimensions="sharingService",
            conn=conn,
        )

    def analytics_live(
        self, start_date: str, end_date: str, *, conn: sqlite3.Connection | None = None
    ) -> AnalyticsResult:
        """Live concurrent viewers — empty rows if no streams in window."""
        try:
            return self._analytics_query(
                start_date=start_date,
                end_date=end_date,
                metrics="averageConcurrentViewers,peakConcurrentViewers",
                filters="liveOrOnDemand==LIVE",
                conn=conn,
            )
        except SchemaDriftError:
            return AnalyticsResult(column_headers=[], rows=[], raw={})

    # Per-video methods
    def analytics_video_basic(
        self,
        video_id: str,
        start_date: str,
        end_date: str,
        *,
        metrics: str = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,likes,comments,shares",
        conn: sqlite3.Connection | None = None,
    ) -> AnalyticsResult:
        return self._analytics_query(
            start_date=start_date,
            end_date=end_date,
            metrics=metrics,
            filters=f"video=={video_id}",
            conn=conn,
        )

    def analytics_video_retention(
        self,
        video_id: str,
        start_date: str,
        end_date: str,
        *,
        conn: sqlite3.Connection | None = None,
    ) -> AnalyticsResult:
        return self._analytics_query(
            start_date=start_date,
            end_date=end_date,
            metrics="audienceWatchRatio,relativeRetentionPerformance",
            dimensions="elapsedVideoTimeRatio",
            filters=f"video=={video_id}",
            conn=conn,
        )

    def analytics_video_traffic_sources(
        self,
        video_id: str,
        start_date: str,
        end_date: str,
        *,
        detail: bool = False,
        conn: sqlite3.Connection | None = None,
    ) -> AnalyticsResult:
        dim = "insightTrafficSourceType"
        if detail:
            dim = "insightTrafficSourceType,insightTrafficSourceDetail"
        return self._analytics_query(
            start_date=start_date,
            end_date=end_date,
            metrics="views,estimatedMinutesWatched",
            dimensions=dim,
            filters=f"video=={video_id}",
            conn=conn,
        )

    def analytics_video_devices(
        self,
        video_id: str,
        start_date: str,
        end_date: str,
        *,
        conn: sqlite3.Connection | None = None,
    ) -> AnalyticsResult:
        return self._analytics_query(
            start_date=start_date,
            end_date=end_date,
            metrics="views,estimatedMinutesWatched",
            dimensions="deviceType",
            filters=f"video=={video_id}",
            conn=conn,
        )

    # -------------------------------------------------------------- REPORTING
    def list_report_types(
        self, *, conn: sqlite3.Connection | None = None
    ) -> list[dict[str, Any]]:
        """List all currently-active Reporting API report types (excluding deprecated).

        Codex r1 MED: previously billed as `youtubereporting.jobs.list` —
        wrong endpoint name. Now uses `youtubereporting.reportTypes.list`.
        """
        all_types: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            kwargs: dict[str, Any] = {"includeSystemManaged": True, "pageSize": 200}
            if page_token:
                kwargs["pageToken"] = page_token
            req = self._reporting.reportTypes().list(**kwargs)
            res = _retry_call(
                req,
                "youtubereporting.reportTypes.list",
                QUOTA_COST["youtubereporting.reportTypes.list"],
                conn=conn,
            )
            all_types.extend(res.get("reportTypes", []))
            page_token = res.get("nextPageToken")
            if not page_token:
                break
        return [t for t in all_types if not t.get("deprecateTime")]

    def list_jobs(self, *, conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
        req = self._reporting.jobs().list()
        res = _retry_call(
            req,
            "youtubereporting.jobs.list",
            QUOTA_COST["youtubereporting.jobs.list"],
            conn=conn,
        )
        return res.get("jobs", [])

    def ensure_jobs(
        self,
        report_type_ids: Iterable[str],
        *,
        name_prefix: str = "kpi-vault",
        conn: sqlite3.Connection | None = None,
    ) -> dict[str, str]:
        """Idempotent: returns mapping report_type_id → job_id, creating missing.

        Persists into reporting_jobs table. Costs 50 units per CREATED job
        (Codex r1 finding F1: jobs.create is 50, not 1).
        """
        existing = self.list_jobs(conn=conn)
        existing_map = {j["reportTypeId"]: j["id"] for j in existing}
        out: dict[str, str] = {}
        for rt in report_type_ids:
            if rt in existing_map:
                out[rt] = existing_map[rt]
                continue
            req = self._reporting.jobs().create(
                body={"reportTypeId": rt, "name": f"{name_prefix}-{rt}"}
            )
            res = _retry_call(
                req,
                "youtubereporting.jobs.create",
                QUOTA_COST["youtubereporting.jobs.create"],
                conn=conn,
            )
            out[rt] = res["id"]
            _LOG.info("reporting: created job %s for %s", res["id"], rt)
        # Persist to reporting_jobs table.
        own_conn = conn is None
        c = conn or _connect_kpi_db()
        try:
            for rt, job_id in out.items():
                c.execute(
                    """
                    INSERT OR IGNORE INTO reporting_jobs(job_id, report_type_id, job_name, created_at, status)
                    VALUES (?, ?, ?, ?, 'active')
                    """,
                    (job_id, rt, f"{name_prefix}-{rt}", _now_iso_micro()),
                )
        finally:
            if own_conn:
                c.close()
        return out

    def list_reports(
        self,
        job_id: str,
        *,
        since_iso: str | None = None,
        page_size: int = 100,
        conn: sqlite3.Connection | None = None,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            kwargs: dict[str, Any] = {"jobId": job_id, "pageSize": page_size}
            if since_iso:
                kwargs["createdAfter"] = since_iso
            if page_token:
                kwargs["pageToken"] = page_token
            req = self._reporting.jobs().reports().list(**kwargs)
            res = _retry_call(
                req,
                "youtubereporting.jobs.reports.list",
                QUOTA_COST["youtubereporting.jobs.reports.list"],
                conn=conn,
            )
            out.extend(res.get("reports", []))
            page_token = res.get("nextPageToken")
            if not page_token:
                break
        return out

    def download_report(
        self,
        report: dict[str, Any],
        *,
        target_dir: Path = DEFAULT_REPORTING_CSV_DIR,
        report_type_id: str | None = None,
        max_attempts: int = 3,
    ) -> Path:
        """Download CSV to local file, return path. CSV is not parsed here.

        Codex r1 MED: retry on 401/403 mid-download by refreshing creds;
        atomic write (download to .tmp, rename on completion) so partial
        downloads don't poison existing files; verify file size > 0 before
        considering existing file complete.
        """
        import requests
        from google.auth.transport.requests import Request as _AuthReq

        url = report["downloadUrl"]
        rt = report_type_id or "unknown_report_type"
        target_dir = target_dir / rt
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{report['id']}.csv"
        tmp = target.with_suffix(".csv.partial")

        # Existing file verified non-empty? Skip.
        if target.exists() and target.stat().st_size > 0:
            return target

        last_exc: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            creds = self._reporting._http.credentials
            try:
                if not creds.valid:
                    creds.refresh(_AuthReq())
                resp = requests.get(
                    url,
                    headers={"Authorization": f"Bearer {creds.token}"},
                    timeout=120,
                )
                resp.raise_for_status()
                # Codex r2 MED: verify non-empty body before declaring success.
                # YouTube can return 200 with empty content if a report is
                # processed but contained zero rows; we should still write
                # an empty placeholder, but log a warning AND require the
                # download URL was honored (i.e. content-length present).
                content_text = resp.text
                if not content_text:
                    _LOG.warning(
                        "download_report: empty body for report %s url=%s",
                        report.get("id"), url[:80],
                    )
                tmp.write_text(content_text, encoding="utf-8")
                tmp.replace(target)  # atomic rename
                return target
            except requests.exceptions.HTTPError as exc:
                last_exc = exc
                status = getattr(exc.response, "status_code", None)
                if status in (401, 403) and attempt < max_attempts:
                    # Force creds refresh on next loop
                    try:
                        creds.refresh(_AuthReq())
                    except Exception as refresh_exc:  # noqa: BLE001
                        _LOG.warning("creds refresh failed: %s", refresh_exc)
                    time.sleep(2 ** (attempt - 1))
                    continue
                # Cleanup partial
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
                raise
            except (requests.exceptions.RequestException, OSError) as exc:
                last_exc = exc
                if attempt < max_attempts:
                    _LOG.warning(
                        "transient download error attempt=%d: %s", attempt, exc
                    )
                    time.sleep(2 ** (attempt - 1))
                    continue
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
                raise
        assert last_exc is not None
        raise last_exc


# ----------------------------------------------------------------------------
# Module-level convenience: singleton
# ----------------------------------------------------------------------------

_default_client: YouTubeFullClient | None = None


def get_default_client() -> YouTubeFullClient:
    global _default_client
    if _default_client is None:
        _default_client = YouTubeFullClient()
    return _default_client
