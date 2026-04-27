"""Nightly ingest orchestrator for the KPI metrics vault (task-04).

Drives one full ingestion cycle per invocation. Default `target_date` is
`today_utc - 2` because YouTube Analytics finalizes data with a 2-day lag.

Phases (in order, atop a single ingestion_runs orchestrator row):
  1. Pre-flight: nonblocking flock + orchestrator run open + quota probe
  2. Refresh video registry via Data API v3
  3. Channel-level Analytics pulls (no-dim + 6 dimensional breakdowns + demographics + live)
  4. Per-video Analytics pulls (basic + retention + traffic) for videos
     published within the last 90 days
  5. Reporting API CSV ingest (download new reports for each registered job,
     parse rows into channel_snapshots / video_snapshots)
  6. Schema drift sync (diff API report types against registered jobs)
  7. Close orchestrator run with aggregated status

Status semantics:
  ok               — all sub-runs succeeded (channel + per-video + reporting)
  partial          — channel-level OK, at least one per-video / reporting sub-run failed
  api_failure      — channel-level pull failed (cascading early abort)
  quota_exhausted  — daily quota cap hit mid-run
  db_failure       — SQLite write failed (orchestrator-level)
  auth_failed      — OAuth refresh / 401 / 403 (non-rate-limit)

Idempotency: re-runs for the same target_date append rows with new
`observed_on` (microsecond precision); latest-wins is enforced by monitoring
queries (max(observed_on)). No deletes, ever.

CLI entry: `python -m ingest.nightly [--target-date YYYY-MM-DD] [--dry-run]`.
"""

from __future__ import annotations

import argparse
import fcntl
import logging
import os
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from googleapiclient.errors import HttpError

from ingest.youtube_full import (  # type: ignore[import-not-found]
    AnalyticsResult,
    DAILY_QUOTA_BUDGET_DEFAULT,
    QuotaExhaustedError,
    SchemaDriftError,
    YouTubeFullClient,
    _connect_kpi_db,
    _is_auth_error,
    _log_schema_drift,
    _now_iso_micro,
    _today_total_units,
    _today_utc_iso,
    get_default_client,
)

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_LOCK_PATH = Path(
    os.environ.get(
        "KPI_NIGHTLY_LOCK",
        "/home/aiagent/assistant/state/kpi-ingest.lock",
    )
)
"""Path of the nonblocking flock guarding nightly runs."""

PER_VIDEO_FRESHNESS_DAYS = 90
"""Per-video pulls only target videos published within this many days of target_date."""

ORCHESTRATOR_SOURCE = "nightly_orchestrator"

TELEGRAM_BOT_ENV = Path(
    os.environ.get(
        "KPI_TELEGRAM_ENV",
        "/home/aiagent/.claude/channels/telegram/.env",
    )
)
"""Source of BOT_TOKEN for direct Bot API alerts (no MCP — survives Claude downtime)."""

YAROSLAV_CHAT_ID = os.environ.get("KPI_TELEGRAM_CHAT_ID", "208368262")
"""Default alert recipient — configurable for tests."""

# Status → severity emoji prefix per task spec table.
STATUS_EMOJI: dict[str, str] = {
    "partial": "⚠️",
    "api_failure": "🔴",
    "db_failure": "🔴",
    "quota_exhausted": "🟠",
    "auth_failed": "🔴",
    "schema_drift": "🟡",
}

# Channel-level Analytics calls expressed as (label, dimension_or_None, metrics).
# `metrics=None` lets the YouTubeFullClient default kick in; otherwise we pin.
CHANNEL_DIM_PULLS: tuple[tuple[str, str | None, str | None], ...] = (
    ("daily_core", None, None),
    ("device", "deviceType", None),
    ("traffic_source", "insightTrafficSourceType", None),
    ("playback_location", "insightPlaybackLocationType", None),
    ("country", "country", None),
    ("sharing_service", "sharingService", "shares"),
    ("subscribed_status", "subscribedStatus", None),
)
"""Each tuple becomes one analytics_channel_basic sub-run.

Source: task-04 spec Phase 3 — seven dimensional pulls plus demographics + live.
"""

# Per-video pulls (label → method-name on YouTubeFullClient + dimension_key fallback)
PER_VIDEO_PULL_LABELS: tuple[str, ...] = ("basic", "retention", "traffic_sources")


# ---------------------------------------------------------------------------
# Telegram alert (direct Bot API curl, not MCP)
# ---------------------------------------------------------------------------


def _load_bot_token() -> str | None:
    """Parse BOT_TOKEN from the Telegram channel env file. Returns None on miss.

    Strips outer quotes + trailing inline comments + UTF-8 BOM. Same parser
    discipline as task-08's runbook to avoid silent token drift.
    """
    if not TELEGRAM_BOT_ENV.exists():
        return None
    try:
        text = TELEGRAM_BOT_ENV.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() != "BOT_TOKEN":
            continue
        value = value.partition("#")[0].strip().strip('"').strip("'")
        return value or None
    return None


def _send_telegram_alert(message: str, *, chat_id: str = YAROSLAV_CHAT_ID) -> bool:
    """Best-effort Bot API alert. Returns True on HTTP 200, False otherwise.

    Failures are NEVER raised — alerts must not crash the orchestrator. Any
    network/auth error is logged and swallowed; the orchestrator status row
    in `ingestion_runs` remains the durable failure record.
    """
    token = _load_bot_token()
    if not token:
        _LOG.warning("telegram alert skipped: no BOT_TOKEN at %s", TELEGRAM_BOT_ENV)
        return False
    try:
        import requests

        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message[:4000]},
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        _LOG.warning(
            "telegram alert non-200: status=%d body=%s",
            resp.status_code, resp.text[:200],
        )
        return False
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("telegram alert failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Sub-run / orchestrator helpers
# ---------------------------------------------------------------------------


@dataclass
class SubRun:
    run_id: str
    source: str  # 'data_api' | 'analytics_api' | 'reporting_api'
    source_detail: str | None
    started_at: str
    rows_written: int = 0
    quota_units: int = 0
    status: str = "running"
    error_text: str | None = None


def _new_run_id() -> str:
    return uuid.uuid4().hex


def _open_run(
    conn: sqlite3.Connection,
    *,
    source: str,
    source_detail: str | None,
    scheduled_for: str | None = None,
) -> SubRun:
    run = SubRun(
        run_id=_new_run_id(),
        source=source,
        source_detail=source_detail,
        started_at=_now_iso_micro(),
    )
    conn.execute(
        """
        INSERT INTO ingestion_runs(
            run_id, source, source_detail, started_at, status,
            rows_written, quota_units, scheduled_for
        )
        VALUES (?, ?, ?, ?, 'running', 0, 0, ?)
        """,
        (run.run_id, run.source, run.source_detail, run.started_at, scheduled_for),
    )
    return run


def _close_run(
    conn: sqlite3.Connection,
    run: SubRun,
    *,
    status: str,
    error_text: str | None = None,
) -> None:
    run.status = status
    run.error_text = error_text or run.error_text
    conn.execute(
        """
        UPDATE ingestion_runs
           SET finished_at=?, status=?, rows_written=?, quota_units=?, error_text=?
         WHERE run_id=?
        """,
        (
            _now_iso_micro(),
            status,
            run.rows_written,
            run.quota_units,
            run.error_text,
            run.run_id,
        ),
    )


# ---------------------------------------------------------------------------
# Flock guard
# ---------------------------------------------------------------------------


@contextmanager
def _batched_writes(conn: sqlite3.Connection) -> Iterator[None]:
    """Wrap a series of inserts in BEGIN IMMEDIATE / COMMIT.

    Gemini r1 MED: with isolation_level=None (autocommit) on the kpi
    connection, naked INSERTs each spawn their own transaction — for a full
    nightly cycle (channel × dims × per-video × metrics) that's thousands of
    fsyncs and easily breaks the 5-minute SLA. Wrapping each persist call
    in BEGIN IMMEDIATE / COMMIT collapses them into one transaction.

    On exception, ROLLBACK is attempted; the exception propagates so the
    caller can map it to sub-run status.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass
        raise


@contextmanager
def _nightly_flock(lock_path: Path) -> Iterator[bool]:
    """Acquire nonblocking exclusive flock; yield True if acquired, False if held.

    The caller is expected to bail rc=0 silently when False — concurrent
    runs are an explicit no-op per the task spec.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "a+")
    try:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    finally:
        fh.close()


# ---------------------------------------------------------------------------
# Analytics → snapshot row mapping
# ---------------------------------------------------------------------------


def _encode_dimension_key(
    headers: list[dict[str, Any]], row: list[Any]
) -> str:
    """Encode dimension columns of a row into the canonical `dim=val|dim2=val2` form.

    Skips dimensions named `day` (those are folded into window_start/end at the
    sub-run level — they are not value-bearing breakdowns). Returns `''` for
    rows with no remaining dimensions.
    """
    parts: list[str] = []
    for header, cell in zip(headers, row):
        if header.get("columnType") != "DIMENSION":
            continue
        name = header.get("name", "")
        if name == "day":
            continue  # day is implicit in window_start/end
        parts.append(f"{name}={cell}")
    return "|".join(parts)


def _persist_analytics_result(
    conn: sqlite3.Connection,
    result: AnalyticsResult,
    *,
    run_id: str,
    source: str,
    grain: str,
    window_start: str,
    window_end: str,
    video_id: str | None = None,
) -> int:
    """Write each (metric, dimension_key) cell as its own snapshot row.

    Returns the number of rows inserted. Per-row `observed_on` is generated
    fresh microsecond-precision so re-runs against the same target_date append
    cleanly without PK collision.
    """
    if not result.rows:
        return 0

    headers = result.column_headers
    metric_indices = [
        (i, h.get("name", ""))
        for i, h in enumerate(headers)
        if h.get("columnType") != "DIMENSION"
    ]
    if not metric_indices:
        return 0

    inserted = 0
    table = "video_snapshots" if video_id else "channel_snapshots"
    for row in result.rows:
        dim_key = _encode_dimension_key(headers, row)
        for col_idx, metric_key in metric_indices:
            value = row[col_idx]
            value_num = _coerce_numeric(value)
            observed_on = _now_iso_micro()
            try:
                if video_id:
                    conn.execute(
                        f"""
                        INSERT INTO {table}(
                            video_id, metric_key, dimension_key, grain,
                            window_start, window_end, observed_on,
                            value_num, run_id, source
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            video_id,
                            metric_key,
                            dim_key,
                            grain,
                            window_start,
                            window_end,
                            observed_on,
                            value_num,
                            run_id,
                            source,
                        ),
                    )
                else:
                    conn.execute(
                        f"""
                        INSERT INTO {table}(
                            metric_key, dimension_key, grain,
                            window_start, window_end, observed_on,
                            value_num, run_id, source
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            metric_key,
                            dim_key,
                            grain,
                            window_start,
                            window_end,
                            observed_on,
                            value_num,
                            run_id,
                            source,
                        ),
                    )
                inserted += 1
            except sqlite3.IntegrityError as exc:
                # PK collision can happen if two rows of one batch happen to
                # land at the exact same microsecond. Retry once with a
                # tiny perturbation (extra microsecond) — guaranteed unique.
                conn.execute(
                    f"""
                    INSERT INTO {table}(
                        {'video_id, ' if video_id else ''}metric_key, dimension_key, grain,
                        window_start, window_end, observed_on,
                        value_num, run_id, source
                    )
                    VALUES ({'?, ' if video_id else ''}?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        *((video_id,) if video_id else ()),
                        metric_key,
                        dim_key,
                        grain,
                        window_start,
                        window_end,
                        _now_iso_micro()[:-1] + f"{col_idx:03d}Z",  # forced uniqueness suffix
                        value_num,
                        run_id,
                        source,
                    ),
                )
                inserted += 1
    return inserted


def _coerce_numeric(value: Any) -> float | None:
    """Map Analytics API cell to value_num. None for non-numerics (preserve sparsity)."""
    if value is None:
        return None
    if isinstance(value, bool):
        # SQL NUMERIC affinity treats bool as 0/1 — Analytics API never returns
        # bools today, but be explicit.
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    # Strings (e.g. country codes are dimensions, not metrics — already filtered).
    # If a metric ever comes through as a string, surface it as NULL rather than
    # blowing up the whole run.
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _persist_retention_points(
    conn: sqlite3.Connection,
    result: AnalyticsResult,
    *,
    run_id: str,
    video_id: str,
    window_start: str,
    window_end: str,
) -> int:
    """video_retention_points has its own column shape, not a generic snapshot."""
    if not result.rows:
        return 0
    headers = result.column_headers
    name_to_idx = {h.get("name", ""): i for i, h in enumerate(headers)}
    elapsed_idx = name_to_idx.get("elapsedVideoTimeRatio")
    if elapsed_idx is None:
        return 0
    awr_idx = name_to_idx.get("audienceWatchRatio")
    rrp_idx = name_to_idx.get("relativeRetentionPerformance")

    inserted = 0
    observed_on = _now_iso_micro()
    for row in result.rows:
        elapsed = _coerce_numeric(row[elapsed_idx])
        if elapsed is None:
            continue
        awr = _coerce_numeric(row[awr_idx]) if awr_idx is not None else None
        rrp = _coerce_numeric(row[rrp_idx]) if rrp_idx is not None else None
        try:
            conn.execute(
                """
                INSERT INTO video_retention_points(
                    video_id, observed_on, window_start, window_end,
                    elapsed_ratio, audience_watch_ratio,
                    relative_retention_performance, run_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    video_id,
                    observed_on,
                    window_start,
                    window_end,
                    elapsed,
                    awr,
                    rrp,
                    run_id,
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            # Re-run on same target_date — retention points are de-duped by PK.
            # Skipping is correct here (retention curves are stable per window).
            continue
    return inserted


# ---------------------------------------------------------------------------
# Phase 2: video registry refresh
# ---------------------------------------------------------------------------


def _upsert_videos(
    conn: sqlite3.Connection, video_metas: list[dict[str, Any]]
) -> int:
    inserted = 0
    for v in video_metas:
        video_id = v.get("id")
        if not video_id:
            continue
        snippet = v.get("snippet", {}) or {}
        content = v.get("contentDetails", {}) or {}
        status = v.get("status", {}) or {}
        duration_iso = content.get("duration")
        duration_s = _iso8601_duration_seconds(duration_iso) if duration_iso else None
        is_short = 1 if (duration_s is not None and duration_s <= 60) else 0
        tags_json = (
            __import__("json").dumps(snippet.get("tags", []))
            if snippet.get("tags")
            else None
        )
        try:
            conn.execute(
                """
                INSERT INTO videos(
                    video_id, title, published_at, channel_id, duration_s,
                    privacy_status, upload_status, category_id, tags_json,
                    default_lang, default_audio_lang, is_short, made_for_kids,
                    live_broadcast_content
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    title=excluded.title,
                    published_at=excluded.published_at,
                    channel_id=excluded.channel_id,
                    duration_s=excluded.duration_s,
                    privacy_status=excluded.privacy_status,
                    upload_status=excluded.upload_status,
                    category_id=excluded.category_id,
                    tags_json=excluded.tags_json,
                    default_lang=excluded.default_lang,
                    default_audio_lang=excluded.default_audio_lang,
                    is_short=excluded.is_short,
                    made_for_kids=excluded.made_for_kids,
                    live_broadcast_content=excluded.live_broadcast_content,
                    updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
                """,
                (
                    video_id,
                    snippet.get("title"),
                    snippet.get("publishedAt"),
                    snippet.get("channelId"),
                    duration_s,
                    status.get("privacyStatus"),
                    status.get("uploadStatus"),
                    snippet.get("categoryId"),
                    tags_json,
                    snippet.get("defaultLanguage"),
                    snippet.get("defaultAudioLanguage"),
                    is_short,
                    1 if status.get("madeForKids") else 0 if status.get("madeForKids") is False else None,
                    snippet.get("liveBroadcastContent"),
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError as exc:
            _LOG.warning("upsert_videos: skip %s due to %s", video_id, exc)
            continue
    return inserted


def _iso8601_duration_seconds(iso: str) -> int | None:
    """Parse PT#H#M#S duration to integer seconds. Returns None on parse failure."""
    import re

    m = re.match(
        r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?$",
        iso or "",
    )
    if not m:
        return None
    h, mins, secs = m.group(1), m.group(2), m.group(3)
    total = 0
    if h:
        total += int(h) * 3600
    if mins:
        total += int(mins) * 60
    if secs:
        total += int(float(secs))
    return total


# ---------------------------------------------------------------------------
# Phase 5: Reporting API CSV ingest
# ---------------------------------------------------------------------------


def _ingest_reporting_csv(
    conn: sqlite3.Connection,
    client: YouTubeFullClient,
    *,
    orchestrator_run_id: str,
) -> tuple[int, list[str]]:
    """Download new reports for each registered job, parse and upsert rows.

    Returns (rows_written_total, list_of_failed_report_ids).
    """
    import csv as _csv

    rows_total = 0
    failed_reports: list[str] = []

    jobs = conn.execute(
        "SELECT job_id, report_type_id FROM reporting_jobs WHERE status='active'"
    ).fetchall()
    for job in jobs:
        job_id = job["job_id"]
        rt = job["report_type_id"]
        # Codex r1 v2 MED: high-water mark must use 'parsed' only, otherwise a
        # crash between download and parse permanently skips that report.
        last_processed = conn.execute(
            """
            SELECT MAX(create_time) AS last
              FROM reporting_reports
             WHERE job_id=? AND download_status='parsed'
            """,
            (job_id,),
        ).fetchone()
        since_iso = last_processed["last"] if last_processed and last_processed["last"] else None

        # Re-list any reports stuck in 'downloaded' or 'pending' so a previous
        # crash doesn't lose them on retry. We treat them as new_reports for
        # this iteration: parsing path is idempotent (snapshot rows append-only
        # with fresh observed_on; reporting_reports row state moves forward).
        stuck = conn.execute(
            """
            SELECT report_id, job_id, start_time, end_time, create_time, download_url, csv_local_path
              FROM reporting_reports
             WHERE job_id=? AND download_status IN ('pending', 'downloaded', 'failed')
            """,
            (job_id,),
        ).fetchall()
        stuck_reports = [
            {
                "id": r["report_id"],
                "createTime": r["create_time"],
                "startTime": r["start_time"],
                "endTime": r["end_time"],
                "downloadUrl": r["download_url"],
                "_local_path": r["csv_local_path"],
            }
            for r in stuck
        ]

        try:
            new_reports = client.list_reports(job_id, since_iso=since_iso, conn=conn)
            # Merge stuck (deduplicated by id) so retries happen first.
            new_ids = {r.get("id") for r in new_reports}
            new_reports = [r for r in stuck_reports if r["id"] not in new_ids] + new_reports
        except QuotaExhaustedError:
            raise
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("list_reports failed for job %s: %s", job_id, exc)
            failed_reports.append(f"job:{job_id}")
            continue

        for report in new_reports:
            report_id = report.get("id")
            if not report_id:
                continue
            # Insert/Upsert report row in 'pending' state first
            conn.execute(
                """
                INSERT OR IGNORE INTO reporting_reports(
                    report_id, job_id, start_time, end_time, create_time,
                    download_url, download_status
                )
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    report_id,
                    job_id,
                    report.get("startTime", ""),
                    report.get("endTime", ""),
                    report.get("createTime", ""),
                    report.get("downloadUrl"),
                ),
            )

            # Download
            try:
                local_path = client.download_report(report, report_type_id=rt)
            except Exception as exc:  # noqa: BLE001
                _LOG.warning("download failed for report %s: %s", report_id, exc)
                conn.execute(
                    """
                    UPDATE reporting_reports
                       SET download_status='failed', error_text=?
                     WHERE report_id=?
                    """,
                    (str(exc)[:500], report_id),
                )
                failed_reports.append(report_id)
                continue
            conn.execute(
                """
                UPDATE reporting_reports
                   SET download_status='downloaded',
                       downloaded_at=?, csv_local_path=?
                 WHERE report_id=?
                """,
                (_now_iso_micro(), str(local_path), report_id),
            )

            # Parse + write rows
            try:
                with _batched_writes(conn):
                    row_count = _parse_and_upsert_reporting_csv(
                        conn,
                        local_path,
                        report_type_id=rt,
                        orchestrator_run_id=orchestrator_run_id,
                    )
            except Exception as exc:  # noqa: BLE001
                _LOG.warning("parse failed for report %s: %s", report_id, exc)
                conn.execute(
                    """
                    UPDATE reporting_reports
                       SET download_status='failed', error_text=?
                     WHERE report_id=?
                    """,
                    (str(exc)[:500], report_id),
                )
                failed_reports.append(report_id)
                continue

            conn.execute(
                """
                UPDATE reporting_reports
                   SET download_status='parsed', parsed_at=?, rows_parsed=?
                 WHERE report_id=?
                """,
                (_now_iso_micro(), row_count, report_id),
            )
            rows_total += row_count

    return rows_total, failed_reports


def _parse_and_upsert_reporting_csv(
    conn: sqlite3.Connection,
    csv_path: Path,
    *,
    report_type_id: str,
    orchestrator_run_id: str,
) -> int:
    """Parse Reporting CSV and route each metric column to channel/video snapshots.

    Reporting CSVs always include a `date` column (YYYYMMDD) plus optional
    `video_id` (channel-level reports omit it). Every other column becomes a
    metric. Channel-keyed rows write to channel_snapshots; video-keyed rows
    write to video_snapshots.
    """
    import csv as _csv

    text = csv_path.read_text(encoding="utf-8") if csv_path.exists() else ""
    if not text.strip():
        return 0
    reader = _csv.reader(text.splitlines())
    try:
        header = next(reader)
    except StopIteration:
        return 0
    if "date" not in header:
        return 0

    date_idx = header.index("date")
    video_idx = header.index("video_id") if "video_id" in header else None
    candidate_cols = [
        (i, name)
        for i, name in enumerate(header)
        if i != date_idx and i != video_idx
    ]
    if not candidate_cols:
        return 0

    # Codex r1 v2 HIGH: Reporting CSVs mix dimension columns (country, device,
    # traffic_source, playback_location, subscribed_status, …) with metric
    # columns. Treating every non-date/video_id column as a metric blew up
    # value_num for non-numeric cells AND lost the dimension context entirely.
    # Classify using all rows — a column is a metric iff every non-empty cell
    # in the entire CSV coerces to numeric. Anything that ever fails coercion
    # is a dimension. This is a single full-pass scan; cost is acceptable for
    # the small CSVs we ingest.
    rows = list(reader)
    metric_indices: set[int] = set()
    dimension_indices: list[int] = []
    for col_idx, _ in candidate_cols:
        all_numeric = True
        seen_nonempty = False
        for r in rows:
            if not r or len(r) <= col_idx:
                continue
            cell = r[col_idx]
            if cell == "":
                continue
            seen_nonempty = True
            if _coerce_numeric(cell) is None:
                all_numeric = False
                break
        if all_numeric and seen_nonempty:
            metric_indices.add(col_idx)
        else:
            dimension_indices.append(col_idx)
    metric_cols = [(i, n) for i, n in candidate_cols if i in metric_indices]
    if not metric_cols:
        return 0

    inserted = 0
    for row in rows:
        if not row or len(row) < len(header):
            continue
        d_raw = row[date_idx]
        if not d_raw:
            continue
        # Reporting CSVs use YYYYMMDD without separators
        if len(d_raw) == 8 and d_raw.isdigit():
            d_iso = f"{d_raw[:4]}-{d_raw[4:6]}-{d_raw[6:8]}"
        else:
            d_iso = d_raw  # fall through; some report types already use ISO
        v_id = row[video_idx] if video_idx is not None else None

        # Codex r1 v2 HIGH: encode dimension columns into the canonical
        # `dim=val|dim2=val2` key so the metric snapshot retains its breakdown.
        dim_parts: list[str] = []
        for col_idx in dimension_indices:
            dim_name = header[col_idx]
            dim_value = row[col_idx]
            if dim_value == "":
                continue
            dim_parts.append(f"{dim_name}={dim_value}")
        dim_key = "|".join(dim_parts)

        for col_idx, metric_key in metric_cols:
            value_num = _coerce_numeric(row[col_idx])
            observed_on = _now_iso_micro()
            try:
                if v_id:
                    conn.execute(
                        """
                        INSERT INTO video_snapshots(
                            video_id, metric_key, dimension_key, grain,
                            window_start, window_end, observed_on,
                            value_num, run_id, source
                        )
                        VALUES (?, ?, ?, 'day', ?, ?, ?, ?, ?, 'reporting_api')
                        """,
                        (
                            v_id,
                            metric_key,
                            dim_key,
                            d_iso,
                            d_iso,
                            observed_on,
                            value_num,
                            orchestrator_run_id,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO channel_snapshots(
                            metric_key, dimension_key, grain,
                            window_start, window_end, observed_on,
                            value_num, run_id, source
                        )
                        VALUES (?, ?, 'day', ?, ?, ?, ?, ?, 'reporting_api')
                        """,
                        (
                            metric_key,
                            dim_key,
                            d_iso,
                            d_iso,
                            observed_on,
                            value_num,
                            orchestrator_run_id,
                        ),
                    )
                inserted += 1
            except sqlite3.IntegrityError:
                # Same-microsecond collision in a tight loop; suffix-perturb retry.
                if v_id:
                    conn.execute(
                        """
                        INSERT INTO video_snapshots(
                            video_id, metric_key, dimension_key, grain,
                            window_start, window_end, observed_on,
                            value_num, run_id, source
                        )
                        VALUES (?, ?, ?, 'day', ?, ?, ?, ?, ?, 'reporting_api')
                        """,
                        (
                            v_id, metric_key, dim_key, d_iso, d_iso,
                            _now_iso_micro()[:-1] + f"{col_idx:03d}Z",
                            value_num, orchestrator_run_id,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO channel_snapshots(
                            metric_key, dimension_key, grain,
                            window_start, window_end, observed_on,
                            value_num, run_id, source
                        )
                        VALUES (?, ?, 'day', ?, ?, ?, ?, ?, 'reporting_api')
                        """,
                        (
                            metric_key, dim_key, d_iso, d_iso,
                            _now_iso_micro()[:-1] + f"{col_idx:03d}Z",
                            value_num, orchestrator_run_id,
                        ),
                    )
                inserted += 1
    return inserted


# ---------------------------------------------------------------------------
# Phase 6: schema drift sync
# ---------------------------------------------------------------------------


def _sync_schema_drift(
    conn: sqlite3.Connection, client: YouTubeFullClient
) -> tuple[list[str], list[str]]:
    """Diff API report types against registered jobs and log drift.

    Returns (added_types, deprecated_types). Deprecated types are also
    soft-disabled in `reporting_jobs` (status='disabled'), so the next nightly
    run skips them naturally.
    """
    api_types = client.list_report_types(conn=conn)
    api_ids = {t["id"] for t in api_types}

    registered = {
        row["report_type_id"]
        for row in conn.execute("SELECT report_type_id FROM reporting_jobs").fetchall()
    }
    active = {
        row["report_type_id"]
        for row in conn.execute(
            "SELECT report_type_id FROM reporting_jobs WHERE status='active'"
        ).fetchall()
    }

    added = sorted(api_ids - registered)
    for rt in added:
        _log_schema_drift(
            "reporting_api",
            "report_type_added",
            rt,
            notes="visible in list_report_types but no job registered",
            conn=conn,
        )
    # Gemini r1 HIGH: spec Phase 6 mandates auto-creation of jobs for added types.
    # ensure_jobs is idempotent + persists into reporting_jobs (50 quota units each).
    ensure_jobs_failed: Exception | None = None
    if added:
        try:
            client.ensure_jobs(added, conn=conn)
        except QuotaExhaustedError:
            # Quota gate is the gating boundary, propagate to orchestrator.
            raise
        except Exception as exc:  # noqa: BLE001
            # Codex r1 v2 MED: silent swallow let orchestrator close 'ok' even
            # when job creation failed. Capture and re-raise so Phase 6 caller
            # can degrade orchestrator status to 'partial' + alert.
            _LOG.warning(
                "ensure_jobs for newly-added report types failed: %s "
                "(types remain registered in schema_drift_log for next-run retry)",
                exc,
            )
            ensure_jobs_failed = exc

    deprecated = sorted(active - api_ids)
    for rt in deprecated:
        conn.execute(
            "UPDATE reporting_jobs SET status='disabled' WHERE report_type_id=?",
            (rt,),
        )
        _log_schema_drift(
            "reporting_api",
            "report_type_deprecated",
            rt,
            notes="job soft-disabled; was active but no longer in list_report_types",
            conn=conn,
        )

    if ensure_jobs_failed is not None:
        raise ensure_jobs_failed
    return added, deprecated


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


@dataclass
class NightlyResult:
    orchestrator_run_id: str
    target_date: str
    status: str
    rows_written: int = 0
    quota_units: int = 0
    sub_runs: list[SubRun] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    error_text: str | None = None

    def as_summary(self) -> str:
        return (
            f"orchestrator={self.orchestrator_run_id[:8]} "
            f"date={self.target_date} status={self.status} "
            f"rows={self.rows_written} quota={self.quota_units} "
            f"sub_runs={len(self.sub_runs)} failures={len(self.failures)}"
        )


def run_nightly(
    *,
    target_date: date | None = None,
    dry_run: bool = False,
    client: YouTubeFullClient | None = None,
    conn: sqlite3.Connection | None = None,
    lock_path: Path = DEFAULT_LOCK_PATH,
) -> NightlyResult | None:
    """Execute one nightly cycle. Returns None if another run held the flock."""
    target_date = target_date or (datetime.now(timezone.utc).date() - timedelta(days=2))
    target_str = target_date.isoformat()

    with _nightly_flock(lock_path) as acquired:
        if not acquired:
            _LOG.info("nightly: another run holds %s, exiting silently", lock_path)
            return None

        own_conn = conn is None
        conn = conn or _connect_kpi_db()
        orchestrator: SubRun | None = None
        try:
            # Gemini r1 MED: Phase-1 pre-flight quota check. If today's API budget
            # is already at the cap before the orchestrator opens its run row,
            # bail with a quota_exhausted result + Telegram alert without
            # creating an in-flight ingestion_runs entry that we'd just close
            # immediately. Read-only check (does NOT reserve units).
            today = _today_utc_iso()
            already_used = _today_total_units(conn, today)
            if already_used >= DAILY_QUOTA_BUDGET_DEFAULT:
                preflight_result = NightlyResult(
                    orchestrator_run_id="preflight",
                    target_date=target_str,
                    status="quota_exhausted",
                    error_text=(
                        f"daily quota cap {DAILY_QUOTA_BUDGET_DEFAULT} already "
                        f"reached before orchestrator open (used={already_used})"
                    ),
                )
                _send_telegram_alert(
                    f"{STATUS_EMOJI['quota_exhausted']} KPI nightly preflight: "
                    f"quota cap already reached today ({already_used}/"
                    f"{DAILY_QUOTA_BUDGET_DEFAULT}); skipping run for "
                    f"target_date={target_str}"
                )
                return preflight_result

            orchestrator = _open_run(
                conn,
                source=ORCHESTRATOR_SOURCE,
                source_detail=f"target_date={target_str}",
                scheduled_for=target_str,
            )
            client = client or get_default_client()

            result = NightlyResult(
                orchestrator_run_id=orchestrator.run_id,
                target_date=target_str,
                status="ok",
            )

            if dry_run:
                _close_run(conn, orchestrator, status="ok", error_text="dry-run")
                result.status = "ok"
                result.error_text = "dry-run"
                return result

            # ------------------------------------------------------------ Phase 2
            try:
                video_ids = _refresh_videos(conn, client, result)
            except QuotaExhaustedError as exc:
                _abort(conn, orchestrator, result, status="quota_exhausted", error=exc)
                return result
            except HttpError as exc:
                if _is_auth_error(exc):
                    _abort(conn, orchestrator, result, status="auth_failed", error=exc)
                    return result
                _abort(conn, orchestrator, result, status="api_failure", error=exc)
                return result

            # ------------------------------------------------------------ Phase 3
            try:
                _channel_pulls(conn, client, result, target_date)
            except QuotaExhaustedError as exc:
                _abort(conn, orchestrator, result, status="quota_exhausted", error=exc)
                return result
            except HttpError as exc:
                if _is_auth_error(exc):
                    _abort(conn, orchestrator, result, status="auth_failed", error=exc)
                    return result
                _abort(conn, orchestrator, result, status="api_failure", error=exc)
                return result
            except Exception as exc:  # noqa: BLE001
                # Codex r1 v2 MED: channel-level non-HTTP failure (e.g.
                # transient network mis-classified, fake-client bug surfaced
                # in tests, etc.) maps to api_failure terminal — not db_failure,
                # because the orchestrator state is consistent.
                _abort(conn, orchestrator, result, status="api_failure", error=exc)
                return result

            # ------------------------------------------------------------ Phase 4
            try:
                _per_video_pulls(conn, client, result, target_date, video_ids)
            except QuotaExhaustedError as exc:
                _abort(conn, orchestrator, result, status="quota_exhausted", error=exc)
                return result

            # ------------------------------------------------------------ Phase 5
            try:
                rep_rows, rep_failures = _ingest_reporting_csv(
                    conn, client, orchestrator_run_id=orchestrator.run_id
                )
                result.rows_written += rep_rows
                if rep_failures:
                    result.failures.extend(f"reporting:{r}" for r in rep_failures)
            except QuotaExhaustedError as exc:
                _abort(conn, orchestrator, result, status="quota_exhausted", error=exc)
                return result
            except Exception as exc:  # noqa: BLE001
                _LOG.warning("reporting ingest aborted: %s", exc)
                result.failures.append(f"reporting_phase:{type(exc).__name__}")

            # ------------------------------------------------------------ Phase 6
            try:
                added, deprecated = _sync_schema_drift(conn, client)
                if added or deprecated:
                    _LOG.info(
                        "schema_drift: added=%d deprecated=%d", len(added), len(deprecated)
                    )
            except Exception as exc:  # noqa: BLE001
                _LOG.warning("schema drift sync failed: %s", exc)
                result.failures.append(f"schema_drift:{type(exc).__name__}")

            # ------------------------------------------------------------ Phase 7
            final_status = "ok" if not result.failures else "partial"
            result.status = final_status
            _close_run(
                conn,
                orchestrator,
                status=final_status,
                error_text="; ".join(result.failures)[:500] or None,
            )
            # Gemini r1 MED: Telegram alert on non-ok orchestrator status.
            if final_status != "ok":
                _send_telegram_alert(
                    f"{STATUS_EMOJI.get(final_status, '⚠️')} KPI nightly "
                    f"target_date={target_str} status={final_status} "
                    f"failures={len(result.failures)} "
                    f"rows={result.rows_written} "
                    f"first={result.failures[0] if result.failures else 'n/a'}"
                )
            return result

        except Exception as exc:  # noqa: BLE001
            _LOG.exception("nightly orchestrator crashed: %s", exc)
            if orchestrator is not None:
                try:
                    _close_run(
                        conn,
                        orchestrator,
                        status="db_failure",
                        error_text=str(exc)[:500],
                    )
                except Exception:  # noqa: BLE001
                    pass
            # Codex r1 v2 MED: spec status table mandates red 🔴 alert on
            # db_failure. Best-effort, never raises.
            _send_telegram_alert(
                f"{STATUS_EMOJI['db_failure']} KPI nightly crashed: "
                f"target_date={target_str} "
                f"exc={type(exc).__name__}: {str(exc)[:200]}"
            )
            raise
        finally:
            if own_conn:
                conn.close()


def _refresh_videos(
    conn: sqlite3.Connection,
    client: YouTubeFullClient,
    result: NightlyResult,
) -> list[str]:
    sub = _open_run(conn, source="data_api", source_detail="refresh_videos")
    try:
        ch = client.get_channel_metadata(conn=conn)
        uploads_pl = (
            ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        )
        if not uploads_pl:
            sub.error_text = "channel has no uploads playlist"
            _close_run(conn, sub, status="ok")
            result.sub_runs.append(sub)
            return []
        ids = client.list_uploads(uploads_pl, conn=conn)
        if not ids:
            _close_run(conn, sub, status="ok")
            result.sub_runs.append(sub)
            return []
        metas = client.get_videos_metadata(ids, conn=conn)
        with _batched_writes(conn):
            sub.rows_written = _upsert_videos(conn, metas)
        _close_run(conn, sub, status="ok")
        result.sub_runs.append(sub)
        result.rows_written += sub.rows_written
        return ids
    except Exception as exc:  # noqa: BLE001
        _close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
        result.sub_runs.append(sub)
        raise


def _channel_pulls(
    conn: sqlite3.Connection,
    client: YouTubeFullClient,
    result: NightlyResult,
    target_date: date,
) -> None:
    target_str = target_date.isoformat()
    for label, dim, metrics in CHANNEL_DIM_PULLS:
        sub = _open_run(
            conn, source="analytics_api", source_detail=f"channel:{label}"
        )
        try:
            kwargs: dict[str, Any] = dict(start_date=target_str, end_date=target_str)
            if dim is not None:
                kwargs["dimensions"] = dim
            if metrics is not None:
                kwargs["metrics"] = metrics
            res = client.analytics_channel_basic(**kwargs, conn=conn)
            with _batched_writes(conn):
                written = _persist_analytics_result(
                    conn, res,
                    run_id=sub.run_id,
                    source="analytics_api",
                    grain="day",
                    window_start=target_str,
                    window_end=target_str,
                )
            sub.rows_written = written
            _close_run(conn, sub, status="ok")
            result.rows_written += written
        except SchemaDriftError as exc:
            _close_run(conn, sub, status="schema_drift", error_text=str(exc)[:500])
            result.failures.append(f"channel:{label}:schema_drift")
        except QuotaExhaustedError:
            _close_run(conn, sub, status="quota_exhausted")
            result.sub_runs.append(sub)
            raise
        except HttpError as exc:
            _close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
            if _is_auth_error(exc):
                result.sub_runs.append(sub)
                raise
            # Channel-level non-auth API failure aborts the orchestrator
            result.sub_runs.append(sub)
            raise
        except Exception as exc:  # noqa: BLE001
            # Codex r1 v2 MED: channel-level non-Schema/non-Quota failures must
            # produce api_failure (terminal), not partial — spec restricts
            # 'partial' to per-video failures with channel-level success.
            _close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
            result.sub_runs.append(sub)
            raise
        result.sub_runs.append(sub)

    # Demographics
    sub = _open_run(conn, source="analytics_api", source_detail="channel:demographics")
    try:
        res = client.analytics_demographics(target_str, target_str, conn=conn)
        written = _persist_analytics_result(
            conn, res,
            run_id=sub.run_id,
            source="analytics_api",
            grain="day",
            window_start=target_str,
            window_end=target_str,
        )
        sub.rows_written = written
        _close_run(conn, sub, status="ok")
        result.rows_written += written
    except QuotaExhaustedError:
        _close_run(conn, sub, status="quota_exhausted")
        result.sub_runs.append(sub)
        raise
    except SchemaDriftError as exc:
        _close_run(conn, sub, status="schema_drift", error_text=str(exc)[:500])
        result.failures.append("channel:demographics:schema_drift")
    except Exception as exc:  # noqa: BLE001
        # Codex r1 v2 MED: channel-level non-Schema failure → api_failure terminal.
        _close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
        result.sub_runs.append(sub)
        raise
    result.sub_runs.append(sub)

    # Live (best-effort; empty rows ≠ failure)
    sub = _open_run(conn, source="analytics_api", source_detail="channel:live")
    try:
        res = client.analytics_live(target_str, target_str, conn=conn)
        written = _persist_analytics_result(
            conn, res,
            run_id=sub.run_id,
            source="analytics_api",
            grain="day",
            window_start=target_str,
            window_end=target_str,
        )
        sub.rows_written = written
        _close_run(conn, sub, status="ok")
        result.rows_written += written
    except QuotaExhaustedError:
        _close_run(conn, sub, status="quota_exhausted")
        result.sub_runs.append(sub)
        raise
    except Exception as exc:  # noqa: BLE001
        _close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
        result.failures.append(f"channel:live:{type(exc).__name__}")
    result.sub_runs.append(sub)


def _per_video_pulls(
    conn: sqlite3.Connection,
    client: YouTubeFullClient,
    result: NightlyResult,
    target_date: date,
    candidate_video_ids: list[str],
) -> None:
    """Pull basic + retention + traffic for each video published in last 90d.

    Per-video failures are non-fatal — they degrade the orchestrator to
    `partial` but do not raise.
    """
    target_str = target_date.isoformat()
    cutoff = target_date - timedelta(days=PER_VIDEO_FRESHNESS_DAYS)
    cutoff_iso = cutoff.isoformat()

    placeholders = ",".join("?" * len(candidate_video_ids)) if candidate_video_ids else "''"
    rows = conn.execute(
        f"""
        SELECT video_id, published_at FROM videos
         WHERE video_id IN ({placeholders})
           AND substr(published_at, 1, 10) >= ?
        """,
        (*candidate_video_ids, cutoff_iso),
    ).fetchall() if candidate_video_ids else []

    fresh_ids = [r["video_id"] for r in rows]
    if not fresh_ids:
        _LOG.info("per_video: no fresh videos to pull (cutoff=%s)", cutoff_iso)
        return

    for video_id in fresh_ids:
        # 1. basic
        sub = _open_run(
            conn, source="analytics_api", source_detail=f"video:{video_id}:basic"
        )
        try:
            res = client.analytics_video_basic(video_id, target_str, target_str, conn=conn)
            with _batched_writes(conn):
                sub.rows_written = _persist_analytics_result(
                    conn, res,
                    run_id=sub.run_id,
                    source="analytics_api",
                    grain="day",
                    window_start=target_str,
                    window_end=target_str,
                    video_id=video_id,
                )
            _close_run(conn, sub, status="ok")
            result.rows_written += sub.rows_written
        except QuotaExhaustedError:
            _close_run(conn, sub, status="quota_exhausted")
            result.sub_runs.append(sub)
            raise
        except Exception as exc:  # noqa: BLE001
            _close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
            result.failures.append(f"video:{video_id}:basic:{type(exc).__name__}")
        result.sub_runs.append(sub)

        # 2. retention
        sub = _open_run(
            conn, source="analytics_api", source_detail=f"video:{video_id}:retention"
        )
        try:
            # Codex r1 v2 LOW: spec asks for "last full week start", not a rolling
            # 7-day window. Use ISO Monday-anchored week boundary.
            # Monday-of-the-week-containing(target_date - 7d) collapses to
            # "the Monday of the previous full ISO week".
            iso_year, iso_week, _ = (target_date - timedelta(days=7)).isocalendar()
            # Use date.fromisocalendar with day=1 (Monday). Available since 3.8.
            week_start = date.fromisocalendar(iso_year, iso_week, 1).isoformat()
            res = client.analytics_video_retention(
                video_id, week_start, target_str, conn=conn
            )
            with _batched_writes(conn):
                sub.rows_written = _persist_retention_points(
                    conn, res,
                    run_id=sub.run_id,
                    video_id=video_id,
                    window_start=week_start,
                    window_end=target_str,
                )
            _close_run(conn, sub, status="ok")
            result.rows_written += sub.rows_written
        except QuotaExhaustedError:
            _close_run(conn, sub, status="quota_exhausted")
            result.sub_runs.append(sub)
            raise
        except Exception as exc:  # noqa: BLE001
            _close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
            result.failures.append(f"video:{video_id}:retention:{type(exc).__name__}")
        result.sub_runs.append(sub)

        # 3. traffic
        sub = _open_run(
            conn, source="analytics_api", source_detail=f"video:{video_id}:traffic"
        )
        try:
            res = client.analytics_video_traffic_sources(
                video_id, target_str, target_str, conn=conn
            )
            with _batched_writes(conn):
                sub.rows_written = _persist_analytics_result(
                    conn, res,
                    run_id=sub.run_id,
                    source="analytics_api",
                    grain="day",
                    window_start=target_str,
                    window_end=target_str,
                    video_id=video_id,
                )
            _close_run(conn, sub, status="ok")
            result.rows_written += sub.rows_written
        except QuotaExhaustedError:
            _close_run(conn, sub, status="quota_exhausted")
            result.sub_runs.append(sub)
            raise
        except Exception as exc:  # noqa: BLE001
            _close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
            result.failures.append(f"video:{video_id}:traffic:{type(exc).__name__}")
        result.sub_runs.append(sub)


def _abort(
    conn: sqlite3.Connection,
    orchestrator: SubRun,
    result: NightlyResult,
    *,
    status: str,
    error: Exception,
) -> None:
    result.status = status
    result.error_text = str(error)[:500]
    _close_run(conn, orchestrator, status=status, error_text=result.error_text)
    # Gemini r1 MED: Telegram alert on every abort path (quota/auth/api/db).
    _send_telegram_alert(
        f"{STATUS_EMOJI.get(status, '🔴')} KPI nightly aborted: "
        f"target_date={result.target_date} status={status} "
        f"error={result.error_text[:200]}"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ingest.nightly", description=__doc__)
    p.add_argument(
        "--target-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=None,
        help="UTC date to ingest. Defaults to today_utc - 2 (Analytics finalization lag).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Open + close orchestrator run without API calls (smoke test).",
    )
    p.add_argument(
        "-v", "--verbose", action="store_true", help="Enable INFO-level logging."
    )
    return p


def main(argv: Iterable[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )

    try:
        result = run_nightly(target_date=args.target_date, dry_run=args.dry_run)
    except QuotaExhaustedError as exc:
        _LOG.error("nightly aborted (quota): %s", exc)
        return 3
    except HttpError as exc:
        if _is_auth_error(exc):
            _LOG.error("nightly aborted (auth): %s", exc)
            return 4
        _LOG.error("nightly aborted (api): %s", exc)
        return 2
    except Exception as exc:  # noqa: BLE001
        _LOG.exception("nightly crashed: %s", exc)
        return 5

    if result is None:
        # Another run held the flock — silent exit per spec.
        return 0
    print(result.as_summary())
    if result.status == "ok":
        return 0
    if result.status == "partial":
        return 1
    if result.status in ("quota_exhausted",):
        return 3
    if result.status == "auth_failed":
        return 4
    return 2


if __name__ == "__main__":
    sys.exit(main())
