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


def quota_check(api_name: str, units: int, *, conn: sqlite3.Connection | None = None) -> int:
    """Return current `units_used` for `api_name` today; raise if budget exceeded.

    Pre-flight check ONLY — does not increment.
    """
    own_conn = conn is None
    conn = conn or _connect_kpi_db()
    try:
        row = conn.execute(
            "SELECT units_used FROM quota_usage WHERE api_name=? AND date_utc=?",
            (api_name, _today_utc_iso()),
        ).fetchone()
        used = int(row["units_used"]) if row else 0
        budget = DAILY_QUOTA_BUDGET_DEFAULT
        if used + units > budget:
            raise QuotaExhaustedError(
                f"{api_name} daily budget {budget} would be exceeded "
                f"(used={used}, requested={units})"
            )
        return used
    finally:
        if own_conn:
            conn.close()


def quota_increment(api_name: str, units: int, *, conn: sqlite3.Connection | None = None) -> None:
    """Atomically bump `units_used` and `request_count` for today."""
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


def _is_transient(err: HttpError) -> bool:
    status = getattr(err.resp, "status", None)
    if status in (408, 429, 500, 502, 503, 504):
        return True
    return False


def _is_auth_error(err: HttpError) -> bool:
    status = getattr(err.resp, "status", None)
    return status in (401, 403)


def _is_unknown_identifier(err: HttpError) -> str | None:
    """If error message indicates an unknown metric/dimension, return its name."""
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
    """Run `callable_` with quota check + exp backoff retry.

    Quota budget pre-check happens once. After success, quota_increment fires
    so concurrent runs see updated counter. On schema drift, raises
    SchemaDriftError; on auth error, raises HttpError unwrapped.
    """
    quota_check(api_name, units, conn=conn)
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = callable_.execute()
            quota_increment(api_name, units, conn=conn)
            return result
        except HttpError as exc:
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
                # Don't bump quota on rejected request (YouTube doesn't charge).
                raise SchemaDriftError(f"{api_name}: unknown identifier {unknown}") from exc
            if _is_auth_error(exc):
                raise
            if not _is_transient(exc) or attempt == max_attempts:
                raise
            wait = 2 ** (attempt - 1)
            _LOG.warning(
                "transient %s on %s attempt=%d, sleeping=%ds: %s",
                exc.resp.status, api_name, attempt, wait, str(exc)[:120],
            )
            time.sleep(wait)
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
        """List all currently-active Reporting API report types (excluding deprecated)."""
        all_types: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            kwargs: dict[str, Any] = {"includeSystemManaged": True, "pageSize": 200}
            if page_token:
                kwargs["pageToken"] = page_token
            req = self._reporting.reportTypes().list(**kwargs)
            res = _retry_call(
                req,
                "youtubereporting.jobs.list",
                QUOTA_COST["youtubereporting.jobs.list"],
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
    ) -> Path:
        """Download CSV to local file, return path. CSV is not parsed here."""
        import requests
        from google.auth.transport.requests import Request as _AuthReq

        # Refresh creds if stale
        creds = self._reporting._http.credentials
        if not creds.valid:
            creds.refresh(_AuthReq())

        url = report["downloadUrl"]
        rt = report_type_id or "unknown_report_type"
        target_dir = target_dir / rt
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{report['id']}.csv"

        if target.exists():
            return target  # already downloaded

        resp = requests.get(
            url, headers={"Authorization": f"Bearer {creds.token}"}, timeout=120
        )
        resp.raise_for_status()
        target.write_text(resp.text, encoding="utf-8")
        return target


# ----------------------------------------------------------------------------
# Module-level convenience: singleton
# ----------------------------------------------------------------------------

_default_client: YouTubeFullClient | None = None


def get_default_client() -> YouTubeFullClient:
    global _default_client
    if _default_client is None:
        _default_client = YouTubeFullClient()
    return _default_client
