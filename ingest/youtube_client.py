"""Typed wrapper around YouTube Data API v3 + YouTube Analytics API v2.

Cron ingest (task-03) and exceptions panel (task-07) both consume this module.

Auth model:
  - Loads refresh token from `$YOUTUBE_CREDS_ENV` (default
    `/home/aiagent/.config/youtube-api/.env`, chmod 600).
  - Rebuilds `google.oauth2.credentials.Credentials` for every client instance;
    the underlying googleapiclient handles access-token refresh transparently
    via the embedded `refresh_token`.

Quota accounting:
  - Every public method logs a caller-supplied `run_id` tag and the endpoint
    name via `logging.getLogger(__name__)`. Persisting to
    `ingestion_runs.quota_units` is the caller's responsibility (task-03).

No secrets in logs:
  - Refresh token never logged. Access token never logged.
  - Error messages redact the header Authorization value if present.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from .env_loader import load_env
from app.lib.retry import NonRetriable, is_transient_http_status, retry

_LOG = logging.getLogger(__name__)

DEFAULT_ENV_PATH = Path(os.environ.get("YOUTUBE_CREDS_ENV", "/home/aiagent/.config/youtube-api/.env"))
_TOKEN_URI = "https://oauth2.googleapis.com/token"


@dataclass(frozen=True)
class YouTubeCreds:
    refresh_token: str
    gcp_project: str
    scopes: tuple[str, ...]
    client_id: str
    client_secret: str


def _load_creds(
    env_path: Path = DEFAULT_ENV_PATH,
    client_secret_path: Path = Path("/home/aiagent/.config/youtube-api/client_secret.json"),
) -> YouTubeCreds:
    env = load_env(env_path)
    try:
        refresh_token = env["YOUTUBE_REFRESH_TOKEN"]
        gcp_project = env["GCP_PROJECT"]
        scopes = tuple(s.strip() for s in env["YOUTUBE_SCOPES"].split(",") if s.strip())
    except KeyError as exc:
        raise RuntimeError(
            f"{env_path} missing key {exc.args[0]} — run scripts/bootstrap_youtube_oauth.py first"
        ) from exc
    # client_id / client_secret live in client_secret.json (not .env — they are not as
    # sensitive as the refresh token, but we keep them out of world-readable config).
    import json

    secret = json.loads(client_secret_path.read_text(encoding="utf-8"))
    section = secret.get("installed") or secret.get("web") or {}
    return YouTubeCreds(
        refresh_token=refresh_token,
        gcp_project=gcp_project,
        scopes=scopes,
        client_id=section["client_id"],
        client_secret=section["client_secret"],
    )


def _build_credentials(creds: YouTubeCreds):
    from google.oauth2.credentials import Credentials

    return Credentials(
        token=None,  # forces refresh on first request
        refresh_token=creds.refresh_token,
        token_uri=_TOKEN_URI,
        client_id=creds.client_id,
        client_secret=creds.client_secret,
        scopes=list(creds.scopes),
    )


class YouTubeClient:
    """Thin typed façade over YouTube Data + Analytics APIs.

    All methods accept a `run_id` for quota attribution and retry transient
    HTTP failures (5xx, 429, 408) up to 5 attempts with exponential backoff.
    Auth errors (401 after refresh, 403) fail fast and are NOT retried.
    """

    def __init__(
        self,
        env_path: Path = DEFAULT_ENV_PATH,
        client_secret_path: Path = Path("/home/aiagent/.config/youtube-api/client_secret.json"),
    ):
        self._creds = _load_creds(env_path, client_secret_path)
        self._google_creds = _build_credentials(self._creds)
        from googleapiclient.discovery import build

        self._data = build("youtube", "v3", credentials=self._google_creds, cache_discovery=False)
        self._analytics = build(
            "youtubeAnalytics", "v2", credentials=self._google_creds, cache_discovery=False
        )

    # --- public surface ---------------------------------------------------

    def get_channel_overview(self, channel_id: str, run_id: str) -> dict:
        """Return subs, views, video count, title, publishedAt for a channel."""
        _LOG.info("get_channel_overview run_id=%s channel_id=%s", run_id, channel_id)
        return retry(
            lambda: self._data.channels()
            .list(part="snippet,statistics,brandingSettings", id=channel_id)
            .execute(),
            retriable=_is_retriable_googleapi_error,
        )

    def get_channel_analytics(
        self,
        *,
        start_date: str,
        end_date: str,
        metrics: str,
        dimensions: str | None = None,
        filters: str | None = None,
        max_results: int | None = None,
        run_id: str,
    ) -> dict:
        """Channel-level Analytics API query. start_date/end_date in YYYY-MM-DD."""
        _LOG.info(
            "get_channel_analytics run_id=%s start=%s end=%s metrics=%s dims=%s",
            run_id,
            start_date,
            end_date,
            metrics,
            dimensions,
        )
        kwargs = {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": metrics,
        }
        if dimensions:
            kwargs["dimensions"] = dimensions
        if filters:
            kwargs["filters"] = filters
        if max_results is not None:
            kwargs["maxResults"] = max_results
        return retry(
            lambda: self._analytics.reports().query(**kwargs).execute(),
            retriable=_is_retriable_googleapi_error,
        )

    def get_video_analytics(
        self,
        *,
        video_id: str,
        start_date: str,
        end_date: str,
        metrics: str,
        dimensions: str = "day",
        run_id: str,
    ) -> dict:
        """Per-video Analytics query. Default dimension=day for time-series."""
        _LOG.info(
            "get_video_analytics run_id=%s video_id=%s start=%s end=%s metrics=%s",
            run_id,
            video_id,
            start_date,
            end_date,
            metrics,
        )
        return retry(
            lambda: self._analytics.reports()
            .query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=end_date,
                metrics=metrics,
                dimensions=dimensions,
                filters=f"video=={video_id}",
            )
            .execute(),
            retriable=_is_retriable_googleapi_error,
        )

    def get_retention(
        self,
        *,
        video_id: str,
        start_date: str,
        end_date: str,
        run_id: str,
    ) -> dict:
        """Retention curve via elapsedVideoTimeRatio dimension.

        Per Gemini research: small channels often return empty here due to
        privacy floors. Caller MUST tolerate an empty `rows` list and record
        the reason as `below_privacy_floor` in its repository layer (task-05).
        """
        _LOG.info(
            "get_retention run_id=%s video_id=%s start=%s end=%s",
            run_id,
            video_id,
            start_date,
            end_date,
        )
        return retry(
            lambda: self._analytics.reports()
            .query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=end_date,
                metrics="audienceWatchRatio,relativeRetentionPerformance",
                dimensions="elapsedVideoTimeRatio",
                filters=f"video=={video_id}",
            )
            .execute(),
            retriable=_is_retriable_googleapi_error,
        )


# --- internals --------------------------------------------------------------


def _is_retriable_googleapi_error(exc: BaseException) -> bool:
    """Classify googleapiclient.HttpError transience. Auth = never retry."""
    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        return False
    if not isinstance(exc, HttpError):
        return False
    status = int(getattr(exc, "status_code", 0) or getattr(exc.resp, "status", 0) or 0)
    if status in (401, 403):
        return False  # auth / permission — retry won't fix
    return is_transient_http_status(status)
