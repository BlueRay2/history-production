"""Daily ingest job entry point — pulls YouTube metrics into the append-only
snapshot tables.

Invoked by:
  - scripts/run_refresh.py (task-08 cron) — daily 03:30 GMT+3 production run
  - ingest/first_run.py (task-03) — initial 45-day backfill

Semantics:
  - Target date = `today - 2` by default (YouTube Analytics 2-day freshness lag).
  - Preliminary flag = true for rows observed <3 days after window_end.
  - Append-only: every invocation writes NEW rows with fresh `observed_on`.
  - Idempotent on (video_id, metric, window, observed_on) PK — re-runs inside
    the same second are no-ops via `INSERT OR IGNORE`.

Exit-code semantics (returned as int to callers):
  0  — success, all intended rows written
  1  — YouTube API transient failure after retries exhausted
  2  — sqlite / repository failure
  3  — partial success (channel rows landed, per-video had issues)
  40 — quota exhausted (HTTP 429), next-day reschedule recommended
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.db import connect as db_connect
from app.repositories.metrics import SnapshotRow, write_snapshot_batch

_LOG = logging.getLogger(__name__)

# YouTube Analytics has a 2-day freshness lag; pulls for today generally
# return incomplete data. Default pull targets `today - PRELIMINARY_LAG_DAYS`
# and marks observations as preliminary for < PRELIMINARY_WINDOW_DAYS old.
PRELIMINARY_LAG_DAYS = 2
PRELIMINARY_WINDOW_DAYS = 3

# Channel-level weekly metrics we always pull in the daily refresh.
CHANNEL_WEEKLY_METRICS = (
    "views",
    "estimatedMinutesWatched",
    "averageViewDuration",
    "averageViewPercentage",
    "impressions",
    "impressionsClickThroughRate",
    "subscribersGained",
    "subscribersLost",
)


@dataclass
class RunResult:
    run_id: str
    status: str          # "ok" | "partial" | "api_failure" | "db_failure" | "quota_exhausted"
    rows_written: int
    error_text: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _week_window(target_date: date) -> tuple[str, str]:
    """ISO-week window ending on target_date's week. Returns (start, end) YYYY-MM-DD."""
    # ISO week starts Monday; compute the Monday of target_date's ISO week
    # and the Sunday that closes it.
    weekday = target_date.isoweekday()  # 1=Mon..7=Sun
    monday = target_date - timedelta(days=weekday - 1)
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def _is_preliminary(target_date: date, today: date) -> bool:
    return (today - target_date).days < PRELIMINARY_WINDOW_DAYS


def _open_ingestion_run(conn: sqlite3.Connection, source: str) -> str:
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO ingestion_runs (run_id, source, started_at, status)
        VALUES (?, ?, ?, 'in_progress')
        """,
        (run_id, source, _now_iso()),
    )
    return run_id


def _close_ingestion_run(
    conn: sqlite3.Connection,
    run_id: str,
    status: str,
    *,
    quota_units: int | None = None,
    error_text: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE ingestion_runs
        SET finished_at = ?, status = ?, quota_units = ?, error_text = ?
        WHERE run_id = ?
        """,
        (_now_iso(), status, quota_units, error_text, run_id),
    )


def run_daily_refresh(
    target_date: date | None = None,
    *,
    client=None,
    today: date | None = None,
) -> RunResult:
    """Pull one day's worth of YouTube metrics into snapshot tables.

    Args:
        target_date: the day whose data we're pulling. Default: today-2.
        client: optional YouTubeClient; if None, a fresh one is instantiated.
            Accepting a client parameter makes tests trivial — fixtures pass
            a mock that answers .get_channel_analytics / .get_retention.
        today: injected "today" (defaults to UTC date). Tests pin it.

    Returns a RunResult with status + rows_written + optional error_text.
    """
    today = today or datetime.now(timezone.utc).date()
    target_date = target_date or (today - timedelta(days=PRELIMINARY_LAG_DAYS))
    preliminary = _is_preliminary(target_date, today)

    # Lazy client construction so unit tests that pass their own `client`
    # never need google-auth installed on the path.
    if client is None:
        from ingest.youtube_client import YouTubeClient  # noqa: WPS433

        client = YouTubeClient()

    with db_connect() as conn:
        run_id = _open_ingestion_run(conn, source="daily_refresh")
        try:
            week_start, week_end = _week_window(target_date)
            analytics = client.get_channel_analytics(
                start_date=week_start,
                end_date=week_end,
                metrics=",".join(CHANNEL_WEEKLY_METRICS),
                run_id=run_id,
            )
            rows = list(_analytics_to_snapshot_rows(
                analytics,
                grain="weekly",
                window_start=week_start,
                window_end=week_end,
                run_id=run_id,
                preliminary=preliminary,
            ))
            try:
                written = write_snapshot_batch(conn, rows)
            except sqlite3.Error as db_exc:
                _close_ingestion_run(conn, run_id, "db_failure", error_text=str(db_exc))
                return RunResult(run_id, "db_failure", 0, str(db_exc))

            _close_ingestion_run(conn, run_id, "ok")
            return RunResult(run_id, "ok", written)
        except Exception as api_exc:  # noqa: BLE001 — catch-all to record in run log
            status = _classify_api_exception(api_exc)
            _close_ingestion_run(conn, run_id, status, error_text=str(api_exc))
            return RunResult(run_id, status, 0, str(api_exc))


def _analytics_to_snapshot_rows(
    analytics: dict,
    *,
    grain: str,
    window_start: str,
    window_end: str,
    run_id: str,
    preliminary: bool,
):
    """Translate a YouTube Analytics reports.query() response into SnapshotRows.

    YouTube Analytics response shape:
      {
        "columnHeaders": [{"name": "views", ...}, ...],
        "rows": [[412, 1189, 173, 24.8, ...]]  # single row for channel-total
      }
    """
    headers = analytics.get("columnHeaders", [])
    rows = analytics.get("rows") or []
    if not rows:
        return
    metric_names = [h["name"] for h in headers if h.get("columnType") != "DIMENSION"]
    # Channel-total query returns exactly one row; per-video would have many.
    observed_on = _now_iso()
    for data_row in rows:
        # Skip any dimension columns — we only wrote metric-only queries here.
        for idx, metric_name in enumerate(metric_names):
            value = data_row[idx]
            try:
                value_num = float(value) if value is not None else None
            except (TypeError, ValueError):
                value_num = None
            yield SnapshotRow(
                metric_key=metric_name,
                grain=grain,
                window_start=window_start,
                window_end=window_end,
                observed_on=observed_on,
                value_num=value_num,
                run_id=run_id,
                preliminary=preliminary,
                video_id=None,  # channel-level
            )


def _classify_api_exception(exc: BaseException) -> str:
    """Map raised exceptions from YouTubeClient to run status strings."""
    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        return "api_failure"
    if isinstance(exc, HttpError):
        status = int(getattr(exc, "status_code", 0) or getattr(exc.resp, "status", 0) or 0)
        if status == 429:
            return "quota_exhausted"
    return "api_failure"
