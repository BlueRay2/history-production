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
    """Microsecond-precision ISO timestamp for `observed_on` (Codex r1 MED).

    Second resolution caused same-second re-pulls to collide on PK and be
    silently dropped by INSERT OR IGNORE, violating the append-only invariant.
    Microsecond precision means two re-pulls inside the same second still get
    distinct observed_on rows.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _week_window(target_date: date) -> tuple[str, str]:
    """ISO-week window ending on target_date's week. Returns (start, end) YYYY-MM-DD."""
    # ISO week starts Monday; compute the Monday of target_date's ISO week
    # and the Sunday that closes it.
    weekday = target_date.isoweekday()  # 1=Mon..7=Sun
    monday = target_date - timedelta(days=weekday - 1)
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def _is_preliminary(window_end: date, today: date) -> bool:
    """Preliminary iff the window just closed (<3 days ago) (Codex r1 MED).

    Derived from `observed_on - window_end`, not `target_date`. For weekly
    windows these diverge: target_date may fall mid-week but the actual
    stability of the aggregated week is measured from the week's end.
    """
    return (today - window_end).days < PRELIMINARY_WINDOW_DAYS


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
    video_ids: list[str] | None = None,
) -> RunResult:
    """Pull one day's worth of YouTube metrics into snapshot tables.

    Args:
        target_date: the day whose data we're pulling. Default: today-2.
        client: optional YouTubeClient. If None, a fresh one is constructed
            INSIDE the run_id-bracketed try/except so credential/bootstrap
            errors are audited in ingestion_runs (Codex r1 MED).
        today: injected "today" (defaults to UTC date). Tests pin it.
        video_ids: optional list of video_ids to pull per-video analytics +
            retention for. If None, task-04 populates `videos` table and
            this can fall back to querying published videos from the DB
            (deferred — see follow-up).

    Returns a RunResult with status + rows_written + optional error_text.
    """
    today = today or datetime.now(timezone.utc).date()
    target_date = target_date or (today - timedelta(days=PRELIMINARY_LAG_DAYS))
    week_start_s, week_end_s = _week_window(target_date)
    week_end_d = date.fromisoformat(week_end_s)
    preliminary = _is_preliminary(week_end_d, today)

    with db_connect() as conn:
        run_id = _open_ingestion_run(conn, source="daily_refresh")
        try:
            # Construct the client INSIDE the run's try/except so credential
            # errors are classified and audited, not silently crashed.
            if client is None:
                from ingest.youtube_client import YouTubeClient  # noqa: WPS433
                client = YouTubeClient()

            # --- channel-level pull ---
            analytics = client.get_channel_analytics(
                start_date=week_start_s,
                end_date=week_end_s,
                metrics=",".join(CHANNEL_WEEKLY_METRICS),
                run_id=run_id,
            )
            channel_rows = list(_analytics_to_snapshot_rows(
                analytics,
                grain="weekly",
                window_start=week_start_s,
                window_end=week_end_s,
                run_id=run_id,
                preliminary=preliminary,
                video_id=None,
            ))

            # --- per-video + retention pull (Codex r1 HIGH fix) ---
            video_rows: list[SnapshotRow] = []
            retention_points: list[tuple] = []
            per_video_failures: list[str] = []
            vids_to_pull = video_ids or _discover_mapped_video_ids(conn)
            for vid in vids_to_pull:
                try:
                    per_video = client.get_video_analytics(
                        video_id=vid,
                        start_date=week_start_s,
                        end_date=week_end_s,
                        metrics=",".join(CHANNEL_WEEKLY_METRICS[:5]),
                        run_id=run_id,
                    )
                    video_rows.extend(_analytics_to_snapshot_rows(
                        per_video,
                        grain="weekly",
                        window_start=week_start_s,
                        window_end=week_end_s,
                        run_id=run_id,
                        preliminary=preliminary,
                        video_id=vid,
                    ))
                    retention = client.get_retention(
                        video_id=vid,
                        start_date=week_start_s,
                        end_date=week_end_s,
                        run_id=run_id,
                    )
                    retention_points.extend(_retention_to_rows(retention, vid, run_id))
                except Exception as per_vid_exc:  # noqa: BLE001 — per-video tolerance
                    # Sparse-metric semantics (J-03): empty rows and privacy
                    # floors aren't errors, but real HTTP failures for one
                    # video shouldn't kill the whole run.
                    per_video_failures.append(f"{vid}: {per_vid_exc}")

            # --- single-txn write (channel + video + retention) ---
            try:
                written = write_snapshot_batch(conn, channel_rows + video_rows)
                if retention_points:
                    _write_retention_points(conn, retention_points)
            except sqlite3.Error as db_exc:
                _close_ingestion_run(conn, run_id, "db_failure", error_text=str(db_exc))
                return RunResult(run_id, "db_failure", 0, str(db_exc))

            # Partial status if any per-video call failed but channel + some
            # videos succeeded.
            status = "partial" if per_video_failures else "ok"
            err = "; ".join(per_video_failures) if per_video_failures else None
            _close_ingestion_run(conn, run_id, status, error_text=err)
            return RunResult(run_id, status, written, err)

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
    video_id: str | None = None,
):
    """Translate a YouTube Analytics reports.query() response into SnapshotRows.

    Channel-level queries (video_id=None) land in channel_metric_snapshots;
    video-level queries land in video_metric_snapshots.
    """
    headers = analytics.get("columnHeaders", [])
    rows = analytics.get("rows") or []
    if not rows:
        return
    metric_names = [h["name"] for h in headers if h.get("columnType") != "DIMENSION"]
    observed_on = _now_iso()
    for data_row in rows:
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
                video_id=video_id,
            )


def _retention_to_rows(retention: dict, video_id: str, run_id: str):
    """Translate a retention curve response into (video_id, observed_on,
    elapsed_seconds, retention_pct, run_id) tuples for video_retention_points.

    Sparse-metric discipline (J-03): empty rows return empty list — caller
    must tolerate that per Gemini research on privacy floors.
    """
    rows = retention.get("rows") or []
    if not rows:
        return
    observed_on = _now_iso()
    for data_row in rows:
        # Expected order: elapsedVideoTimeRatio, audienceWatchRatio, relativeRetentionPerformance
        elapsed = float(data_row[0]) if data_row[0] is not None else 0.0
        retention_pct = float(data_row[1]) if len(data_row) > 1 and data_row[1] is not None else None
        # Convert ratio (0..1) to pseudo-seconds via 100× scaling (data model
        # stores elapsed_seconds; actual ratio stored as seconds×100 for
        # integer-ish readability while keeping real REAL precision).
        yield (
            video_id,
            observed_on,
            elapsed * 1000,  # scale to preserve ordering/PK uniqueness
            retention_pct,
            run_id,
        )


def _write_retention_points(conn: sqlite3.Connection, rows: list[tuple]) -> None:
    if not rows:
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.executemany(
            """
            INSERT OR IGNORE INTO video_retention_points
                (video_id, observed_on, elapsed_seconds, retention_pct, run_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass
        raise


def _discover_mapped_video_ids(conn: sqlite3.Connection) -> list[str]:
    """Return video_ids from `videos` table. Empty until task-04 populates it.

    Falls back to empty list so the daily refresh still completes the
    channel-level pull even before the videos registry exists.
    """
    return [r["video_id"] for r in conn.execute("SELECT video_id FROM videos")]


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
