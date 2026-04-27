"""60-day backfill bootstrap for KPI metrics vault (task-05).

One-shot ingestion of historical Analytics API data covering the last 60
days. Designed to be run **once** at deployment time before the nightly
orchestrator (task-04) takes over for incremental updates.

Behaviour:
  - Sentinel flag at `state/kpi-backfill-complete.flag` blocks accidental
    re-runs. `--force` overrides.
  - Cursor file at `state/kpi-backfill-cursor.json` persists progress so
    a quota-induced abort (rc=2) can be resumed on the next day.
  - Acquires the *same* flock as nightly (`state/kpi-ingest.lock`) but
    with a *blocking* wait (timeout 1h) — backfill should yield to a
    running nightly, never skip silently.
  - Reporting API jobs (all active types from `client.list_report_types()`)
    are registered immediately. They begin generating reports ~24h later
    with YouTube's natural ~30d lookback. Backfill does NOT block on them.

CLI:
  python -m ingest.backfill [--days 60] [--force] [--dry-run]
"""

from __future__ import annotations

import argparse
import fcntl
import json
import logging
import os
import sqlite3
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from googleapiclient.errors import HttpError

from ingest.nightly import (  # type: ignore[import-not-found]
    CHANNEL_DIM_PULLS,
    DEFAULT_LOCK_PATH,
    PER_VIDEO_FRESHNESS_DAYS,
    STATUS_EMOJI,
    SubRun,
    _abort,
    _batched_writes,
    _close_run,
    _open_run,
    _persist_analytics_result,
    _persist_retention_points,
    _send_telegram_alert,
    _upsert_videos,
)
from ingest.youtube_full import (  # type: ignore[import-not-found]
    DAILY_QUOTA_BUDGET_DEFAULT,
    QuotaExhaustedError,
    SchemaDriftError,
    YouTubeFullClient,
    _connect_kpi_db,
    _is_auth_error,
    _now_iso_micro,
    _today_total_units,
    _today_utc_iso,
    get_default_client,
)

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_BACKFILL_DAYS = 60
"""Per Yaroslav D4: channel age <2 months → 60-day window covers everything."""

QUOTA_PAUSE_THRESHOLD = 8500
"""Per task-05 spec: if today's quota crosses this mid-backfill, pause and
persist cursor. Leaves 1500 unit headroom for nightly to fire later same day."""

INTER_CALL_PAUSE_SEC = 1.0
"""Pause between Analytics calls. ~5000 calls × 1s ≈ 1.4 hours wall-clock —
within the spec's `< 2 hours` acceptance criterion."""

DEFAULT_FLOCK_WAIT_SEC = 3600
"""Maximum wait for nightly's flock — 1 hour per spec."""

DEFAULT_SENTINEL_PATH = Path(
    os.environ.get(
        "KPI_BACKFILL_SENTINEL",
        "/home/aiagent/assistant/state/kpi-backfill-complete.flag",
    )
)

DEFAULT_CURSOR_PATH = Path(
    os.environ.get(
        "KPI_BACKFILL_CURSOR",
        "/home/aiagent/assistant/state/kpi-backfill-cursor.json",
    )
)

BACKFILL_SOURCE = "backfill"


# ---------------------------------------------------------------------------
# Cursor (resume state)
# ---------------------------------------------------------------------------


@dataclass
class Cursor:
    """Persisted progress so quota-aborted backfill can resume next day."""

    started_at: str
    last_completed_date: str  # YYYY-MM-DD; the day fully ingested. Resume picks the day AFTER.
    end_date: str             # YYYY-MM-DD; final date in the original window.
    rows_written: int = 0
    quota_used: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "last_completed_date": self.last_completed_date,
            "end_date": self.end_date,
            "rows_written": self.rows_written,
            "quota_used": self.quota_used,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Cursor":
        return cls(
            started_at=d["started_at"],
            last_completed_date=d["last_completed_date"],
            end_date=d["end_date"],
            rows_written=int(d.get("rows_written", 0)),
            quota_used=int(d.get("quota_used", 0)),
        )


def _load_cursor(path: Path) -> Cursor | None:
    if not path.exists():
        return None
    try:
        return Cursor.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        _LOG.warning("cursor at %s unreadable (%s) — ignoring", path, exc)
        return None


def _save_cursor(path: Path, cursor: Cursor) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cursor.to_dict(), indent=2), encoding="utf-8")
    tmp.replace(path)


def _clear_cursor(path: Path) -> None:
    if path.exists():
        path.unlink()


# ---------------------------------------------------------------------------
# Blocking flock (counterpart to nightly's nonblocking)
# ---------------------------------------------------------------------------


@contextmanager
def _backfill_flock(lock_path: Path, wait_seconds: int = DEFAULT_FLOCK_WAIT_SEC) -> Iterator[bool]:
    """Acquire the *same* flock as nightly, but BLOCKING with timeout.

    Backfill should yield to a running nightly, not silently skip itself.
    Polls every 5 seconds until lock is acquired or `wait_seconds` elapses.
    Yields True on success, False on timeout.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "a+")
    deadline = time.monotonic() + wait_seconds
    acquired = False
    try:
        while True:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    yield False
                    return
                time.sleep(5)
        try:
            yield True
        finally:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    finally:
        fh.close()
        if not acquired:
            return


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class BackfillResult:
    status: str
    days_processed: int
    rows_written: int
    quota_used: int
    cursor_left: bool
    error_text: str | None = None
    sub_runs: list[SubRun] = field(default_factory=list)

    def as_summary(self) -> str:
        cursor_note = " (cursor saved — re-run to resume)" if self.cursor_left else ""
        return (
            f"backfill status={self.status} days={self.days_processed} "
            f"rows={self.rows_written} quota={self.quota_used}{cursor_note}"
        )


# ---------------------------------------------------------------------------
# Per-day ingest (mirrors nightly Phase 3-4 with date-pinned window)
# ---------------------------------------------------------------------------


def _ingest_one_day(
    conn: sqlite3.Connection,
    client: YouTubeFullClient,
    target_date: date,
    candidate_video_ids: list[str],
    *,
    pause_sec: float = INTER_CALL_PAUSE_SEC,
) -> tuple[int, list[SubRun]]:
    """Pull all channel-level + per-video Analytics for one historical day.

    Returns (rows_written, sub_runs). Per-video failures degrade the day's
    result but don't abort backfill; channel-level failures DO abort
    (raised to caller).
    """
    target_str = target_date.isoformat()
    rows_written = 0
    sub_runs: list[SubRun] = []

    # Channel-level pulls (mirrors task-04 _channel_pulls but per fixed day)
    for label, dim, metrics in CHANNEL_DIM_PULLS:
        sub = _open_run(
            conn, source="analytics_api",
            source_detail=f"backfill:channel:{label}:{target_str}",
            scheduled_for=target_str,
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
            rows_written += written
            _close_run(conn, sub, status="ok")
        except SchemaDriftError as exc:
            _close_run(conn, sub, status="schema_drift", error_text=str(exc)[:500])
        except QuotaExhaustedError:
            _close_run(conn, sub, status="quota_exhausted")
            sub_runs.append(sub)
            raise
        except HttpError as exc:
            _close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
            sub_runs.append(sub)
            raise
        sub_runs.append(sub)
        time.sleep(pause_sec)

    # Demographics
    sub = _open_run(
        conn, source="analytics_api",
        source_detail=f"backfill:channel:demographics:{target_str}",
        scheduled_for=target_str,
    )
    try:
        res = client.analytics_demographics(target_str, target_str, conn=conn)
        with _batched_writes(conn):
            written = _persist_analytics_result(
                conn, res,
                run_id=sub.run_id, source="analytics_api",
                grain="day", window_start=target_str, window_end=target_str,
            )
        sub.rows_written = written
        rows_written += written
        _close_run(conn, sub, status="ok")
    except QuotaExhaustedError:
        _close_run(conn, sub, status="quota_exhausted")
        sub_runs.append(sub)
        raise
    except SchemaDriftError as exc:
        _close_run(conn, sub, status="schema_drift", error_text=str(exc)[:500])
    except Exception as exc:  # noqa: BLE001
        _close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
    sub_runs.append(sub)
    time.sleep(pause_sec)

    # Per-video pulls — only for videos that existed on this historical date
    cutoff = target_date - timedelta(days=PER_VIDEO_FRESHNESS_DAYS)
    if candidate_video_ids:
        placeholders = ",".join("?" * len(candidate_video_ids))
        rows = conn.execute(
            f"""
            SELECT video_id FROM videos
             WHERE video_id IN ({placeholders})
               AND substr(published_at, 1, 10) <= ?
               AND substr(published_at, 1, 10) >= ?
            """,
            (*candidate_video_ids, target_str, cutoff.isoformat()),
        ).fetchall()
        fresh_ids = [r["video_id"] for r in rows]
    else:
        fresh_ids = []

    for video_id in fresh_ids:
        # basic
        sub = _open_run(
            conn, source="analytics_api",
            source_detail=f"backfill:video:{video_id}:basic:{target_str}",
            scheduled_for=target_str,
        )
        try:
            res = client.analytics_video_basic(video_id, target_str, target_str, conn=conn)
            with _batched_writes(conn):
                sub.rows_written = _persist_analytics_result(
                    conn, res,
                    run_id=sub.run_id, source="analytics_api",
                    grain="day", window_start=target_str, window_end=target_str,
                    video_id=video_id,
                )
            rows_written += sub.rows_written
            _close_run(conn, sub, status="ok")
        except QuotaExhaustedError:
            _close_run(conn, sub, status="quota_exhausted")
            sub_runs.append(sub)
            raise
        except Exception as exc:  # noqa: BLE001
            _close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
        sub_runs.append(sub)
        time.sleep(pause_sec)

        # retention — uses ISO Monday week start (same as nightly)
        sub = _open_run(
            conn, source="analytics_api",
            source_detail=f"backfill:video:{video_id}:retention:{target_str}",
            scheduled_for=target_str,
        )
        try:
            iso_year, iso_week, _ = (target_date - timedelta(days=7)).isocalendar()
            week_start = date.fromisocalendar(iso_year, iso_week, 1).isoformat()
            res = client.analytics_video_retention(
                video_id, week_start, target_str, conn=conn
            )
            with _batched_writes(conn):
                sub.rows_written = _persist_retention_points(
                    conn, res,
                    run_id=sub.run_id, video_id=video_id,
                    window_start=week_start, window_end=target_str,
                )
            rows_written += sub.rows_written
            _close_run(conn, sub, status="ok")
        except QuotaExhaustedError:
            _close_run(conn, sub, status="quota_exhausted")
            sub_runs.append(sub)
            raise
        except Exception as exc:  # noqa: BLE001
            _close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
        sub_runs.append(sub)
        time.sleep(pause_sec)

        # traffic
        sub = _open_run(
            conn, source="analytics_api",
            source_detail=f"backfill:video:{video_id}:traffic:{target_str}",
            scheduled_for=target_str,
        )
        try:
            res = client.analytics_video_traffic_sources(
                video_id, target_str, target_str, conn=conn
            )
            with _batched_writes(conn):
                sub.rows_written = _persist_analytics_result(
                    conn, res,
                    run_id=sub.run_id, source="analytics_api",
                    grain="day", window_start=target_str, window_end=target_str,
                    video_id=video_id,
                )
            rows_written += sub.rows_written
            _close_run(conn, sub, status="ok")
        except QuotaExhaustedError:
            _close_run(conn, sub, status="quota_exhausted")
            sub_runs.append(sub)
            raise
        except Exception as exc:  # noqa: BLE001
            _close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
        sub_runs.append(sub)
        time.sleep(pause_sec)

    return rows_written, sub_runs


# ---------------------------------------------------------------------------
# Reporting jobs registration (one-shot, idempotent)
# ---------------------------------------------------------------------------


def _register_all_reporting_jobs(
    conn: sqlite3.Connection, client: YouTubeFullClient
) -> int:
    """Register all active YouTube Reporting API report types as jobs.

    Idempotent: ensure_jobs skips already-registered ones. Returns the count
    of jobs that exist (created + previously existing) for active types.
    """
    types = client.list_report_types(conn=conn)
    active_ids = [t["id"] for t in types]
    if not active_ids:
        return 0
    mapping = client.ensure_jobs(active_ids, conn=conn)
    return len(mapping)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def run_backfill(
    *,
    days: int = DEFAULT_BACKFILL_DAYS,
    force: bool = False,
    dry_run: bool = False,
    client: YouTubeFullClient | None = None,
    conn: sqlite3.Connection | None = None,
    lock_path: Path = DEFAULT_LOCK_PATH,
    sentinel_path: Path = DEFAULT_SENTINEL_PATH,
    cursor_path: Path = DEFAULT_CURSOR_PATH,
    flock_wait: int = DEFAULT_FLOCK_WAIT_SEC,
) -> BackfillResult:
    """Execute the backfill bootstrap. See module docstring for behaviour."""

    # Sentinel guard
    if sentinel_path.exists() and not force:
        return BackfillResult(
            status="already_done",
            days_processed=0, rows_written=0, quota_used=0, cursor_left=False,
            error_text=f"sentinel {sentinel_path} exists; pass --force to re-run",
        )

    if dry_run:
        return BackfillResult(
            status="dry_run",
            days_processed=days, rows_written=0, quota_used=0, cursor_left=False,
            error_text="dry-run",
        )

    today = datetime.now(timezone.utc).date()
    end_date = today - timedelta(days=2)  # Same lag as nightly
    start_date = end_date - timedelta(days=days - 1)

    # Resume from cursor if present
    resume_cursor = _load_cursor(cursor_path)
    if resume_cursor and not force:
        try:
            last_done = date.fromisoformat(resume_cursor.last_completed_date)
            stored_end = date.fromisoformat(resume_cursor.end_date)
        except ValueError:
            last_done = None
            stored_end = None
        if last_done and stored_end and stored_end == end_date:
            # Resume: continue from day AFTER last_done
            start_date = last_done + timedelta(days=1)
            if start_date > end_date:
                # Already finished previously — write sentinel and exit
                sentinel_path.parent.mkdir(parents=True, exist_ok=True)
                sentinel_path.touch()
                _clear_cursor(cursor_path)
                return BackfillResult(
                    status="already_done",
                    days_processed=0, rows_written=0, quota_used=0,
                    cursor_left=False,
                    error_text="cursor showed completion; sentinel re-touched",
                )
            _LOG.info("resuming backfill from cursor: start=%s", start_date)

    with _backfill_flock(lock_path, wait_seconds=flock_wait) as acquired:
        if not acquired:
            _send_telegram_alert(
                f"{STATUS_EMOJI.get('api_failure', '🔴')} kpi backfill cannot get lock — "
                f"concurrent run detected, retry later"
            )
            return BackfillResult(
                status="lock_timeout",
                days_processed=0, rows_written=0, quota_used=0, cursor_left=False,
                error_text=f"could not acquire {lock_path} within {flock_wait}s",
            )

        own_conn = conn is None
        conn = conn or _connect_kpi_db()
        client = client or get_default_client()
        orchestrator: SubRun | None = None
        result = BackfillResult(
            status="running",
            days_processed=0, rows_written=0, quota_used=0, cursor_left=False,
        )

        try:
            orchestrator = _open_run(
                conn,
                source=BACKFILL_SOURCE,
                source_detail=f"days={days} window={start_date}..{end_date}",
                scheduled_for=end_date.isoformat(),
            )

            # Step 1: refresh video registry once (pre-loop, so per-day filter
            # has accurate published_at data).
            try:
                ch = client.get_channel_metadata(conn=conn)
                uploads_pl = (
                    ch.get("contentDetails", {})
                      .get("relatedPlaylists", {})
                      .get("uploads")
                )
                if uploads_pl:
                    ids = client.list_uploads(uploads_pl, conn=conn)
                    if ids:
                        metas = client.get_videos_metadata(ids, conn=conn)
                        with _batched_writes(conn):
                            registry_rows = _upsert_videos(conn, metas)
                        result.rows_written += registry_rows
                else:
                    ids = []
            except QuotaExhaustedError:
                _abort(conn, orchestrator, _RAdapter(result, end_date),
                       status="quota_exhausted", error=QuotaExhaustedError("registry refresh"))
                return result
            except Exception as exc:  # noqa: BLE001
                _abort(conn, orchestrator, _RAdapter(result, end_date),
                       status="api_failure", error=exc)
                return result

            # Step 2: register all Reporting API jobs (idempotent, non-blocking)
            try:
                jobs_count = _register_all_reporting_jobs(conn, client)
                _LOG.info("registered/verified %d reporting jobs", jobs_count)
            except QuotaExhaustedError:
                _abort(conn, orchestrator, _RAdapter(result, end_date),
                       status="quota_exhausted",
                       error=QuotaExhaustedError("reporting jobs registration"))
                return result
            except Exception as exc:  # noqa: BLE001
                # Reporting failures are non-fatal — log and continue
                _LOG.warning("reporting job registration failed: %s", exc)

            # Step 3: Per-day backfill loop
            current = start_date
            days_done = 0
            while current <= end_date:
                # Quota check BEFORE pulling this day. If we'd cross the
                # threshold, save cursor and exit cleanly (rc=2 in CLI).
                today_used = _today_total_units(conn, _today_utc_iso())
                if today_used >= QUOTA_PAUSE_THRESHOLD:
                    last_done = (current - timedelta(days=1)).isoformat() if days_done > 0 else None
                    if last_done:
                        cursor = Cursor(
                            started_at=orchestrator.started_at,
                            last_completed_date=last_done,
                            end_date=end_date.isoformat(),
                            rows_written=result.rows_written,
                            quota_used=today_used,
                        )
                        _save_cursor(cursor_path, cursor)
                        result.cursor_left = True
                    result.status = "quota_exhausted"
                    result.error_text = (
                        f"quota threshold {QUOTA_PAUSE_THRESHOLD} reached at {today_used}"
                    )
                    _close_run(
                        conn, orchestrator, status="quota_exhausted",
                        error_text=result.error_text,
                    )
                    _send_telegram_alert(
                        f"{STATUS_EMOJI['quota_exhausted']} kpi backfill paused at "
                        f"day={current} (quota={today_used}); cursor saved, resume tomorrow"
                    )
                    return result

                try:
                    rows_today, subs_today = _ingest_one_day(
                        conn, client, current, ids
                    )
                    result.rows_written += rows_today
                    result.sub_runs.extend(subs_today)
                    days_done += 1
                    result.days_processed = days_done
                except QuotaExhaustedError:
                    last_done = (current - timedelta(days=1)).isoformat() if days_done > 0 else None
                    if last_done:
                        cursor = Cursor(
                            started_at=orchestrator.started_at,
                            last_completed_date=last_done,
                            end_date=end_date.isoformat(),
                            rows_written=result.rows_written,
                            quota_used=_today_total_units(conn, _today_utc_iso()),
                        )
                        _save_cursor(cursor_path, cursor)
                        result.cursor_left = True
                    result.status = "quota_exhausted"
                    _close_run(
                        conn, orchestrator, status="quota_exhausted",
                        error_text="quota exhausted mid-day",
                    )
                    return result
                except HttpError as exc:
                    if _is_auth_error(exc):
                        _abort(conn, orchestrator, _RAdapter(result, end_date),
                               status="auth_failed", error=exc)
                        return result
                    _abort(conn, orchestrator, _RAdapter(result, end_date),
                           status="api_failure", error=exc)
                    return result

                current += timedelta(days=1)

            # All days completed — write sentinel, clear cursor
            sentinel_path.parent.mkdir(parents=True, exist_ok=True)
            sentinel_path.touch()
            _clear_cursor(cursor_path)
            result.status = "ok"
            result.quota_used = _today_total_units(conn, _today_utc_iso())
            _close_run(conn, orchestrator, status="ok")

            _send_telegram_alert(
                f"✅ kpi backfill {days}d ok — {result.rows_written} rows, "
                f"{result.quota_used} quota units used"
            )
            return result

        except Exception as exc:  # noqa: BLE001
            _LOG.exception("backfill crashed: %s", exc)
            if orchestrator is not None:
                try:
                    _close_run(
                        conn, orchestrator, status="db_failure",
                        error_text=str(exc)[:500],
                    )
                except Exception:  # noqa: BLE001
                    pass
            _send_telegram_alert(
                f"{STATUS_EMOJI['db_failure']} kpi backfill crashed: "
                f"{type(exc).__name__}: {str(exc)[:200]}"
            )
            raise
        finally:
            if own_conn:
                conn.close()


@dataclass
class _RAdapter:
    """Tiny shim so we can reuse nightly._abort which expects a result with
    `target_date`, `status`, `error_text`, `failures`, `sub_runs` attrs."""
    inner: BackfillResult
    end_date: date

    @property
    def target_date(self) -> str:
        return self.end_date.isoformat()

    @property
    def status(self) -> str:
        return self.inner.status

    @status.setter
    def status(self, v: str) -> None:
        self.inner.status = v

    @property
    def error_text(self) -> str | None:
        return self.inner.error_text

    @error_text.setter
    def error_text(self, v: str | None) -> None:
        self.inner.error_text = v

    @property
    def failures(self) -> list[str]:
        return []

    @property
    def sub_runs(self) -> list[SubRun]:
        return self.inner.sub_runs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ingest.backfill", description=__doc__)
    p.add_argument(
        "--days", type=int, default=DEFAULT_BACKFILL_DAYS,
        help=f"Number of days to backfill (default: {DEFAULT_BACKFILL_DAYS}).",
    )
    p.add_argument(
        "--force", action="store_true",
        help="Bypass sentinel + cursor for explicit re-run.",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Print plan without making API calls.",
    )
    p.add_argument(
        "-v", "--verbose", action="store_true", help="INFO-level logging.",
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
        result = run_backfill(days=args.days, force=args.force, dry_run=args.dry_run)
    except QuotaExhaustedError as exc:
        _LOG.error("backfill aborted (quota): %s", exc)
        return 3
    except HttpError as exc:
        if _is_auth_error(exc):
            _LOG.error("backfill aborted (auth): %s", exc)
            return 4
        _LOG.error("backfill aborted (api): %s", exc)
        return 2
    except Exception as exc:  # noqa: BLE001
        _LOG.exception("backfill crashed: %s", exc)
        return 5

    print(result.as_summary())
    if result.status in ("ok", "already_done", "dry_run"):
        return 0
    if result.status in ("quota_exhausted", "lock_timeout"):
        return 2
    if result.status == "auth_failed":
        return 4
    return 1


if __name__ == "__main__":
    sys.exit(main())
