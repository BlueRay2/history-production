"""Metrics repository — append-only snapshot reads and writes.

Append-only invariant:
  - Every snapshot row is identified by (entity, metric_key, grain, window,
    observed_on). Re-pulls emit a NEW row with fresh `observed_on`.
  - Dashboard reads select the latest row per (entity, metric_key, window)
    via MAX(observed_on).
  - Preliminary-flag handling: when YouTube's 2-day-lag window resettles
    with stable values, caller may mark prior preliminary rows as stable by
    writing a new row with preliminary=0; the legacy preliminary row stays
    for audit.

Consumed by: ingest/jobs.py (task-03 writer), dashboard views (task-06+).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SnapshotRow:
    """Single append-only metric observation.

    video_id == None marks a channel-level snapshot (stored in
    channel_metric_snapshots). Otherwise the row lives in
    video_metric_snapshots.
    """

    metric_key: str
    grain: str              # "daily" | "weekly" | "monthly"
    window_start: str       # ISO date YYYY-MM-DD
    window_end: str         # ISO date YYYY-MM-DD
    observed_on: str        # ISO timestamp YYYY-MM-DDTHH:MM:SSZ
    value_num: float | None
    run_id: str
    preliminary: bool
    video_id: str | None = None


def _table_for(video_id: str | None) -> str:
    return "video_metric_snapshots" if video_id is not None else "channel_metric_snapshots"


def write_snapshot_batch(conn: sqlite3.Connection, rows: Iterable[SnapshotRow]) -> int:
    """Insert snapshot rows in a single transaction.

    Uses `INSERT OR IGNORE` so idempotent re-runs with the same
    (entity, metric, window, observed_on) PK are no-ops rather than errors.
    A fresh `observed_on` (usually the ingest run's wall-clock) produces a
    genuinely new row even if the other 4 columns match a prior snapshot —
    this is the append-only semantics.

    Returns the count of rows actually inserted (re-runs return 0).
    """
    rows = list(rows)
    if not rows:
        return 0

    inserted = 0
    conn.execute("BEGIN IMMEDIATE")
    try:
        for r in rows:
            table = _table_for(r.video_id)
            if r.video_id is not None:
                cur = conn.execute(
                    f"""
                    INSERT OR IGNORE INTO {table}
                        (video_id, metric_key, grain, window_start, window_end,
                         observed_on, value_num, run_id, preliminary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r.video_id, r.metric_key, r.grain, r.window_start,
                        r.window_end, r.observed_on, r.value_num, r.run_id,
                        1 if r.preliminary else 0,
                    ),
                )
            else:
                cur = conn.execute(
                    f"""
                    INSERT OR IGNORE INTO {table}
                        (metric_key, grain, window_start, window_end,
                         observed_on, value_num, run_id, preliminary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r.metric_key, r.grain, r.window_start, r.window_end,
                        r.observed_on, r.value_num, r.run_id,
                        1 if r.preliminary else 0,
                    ),
                )
            inserted += cur.rowcount
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass
        raise
    return inserted


def latest_snapshot(
    conn: sqlite3.Connection,
    *,
    metric_key: str,
    grain: str,
    window_start: str,
    window_end: str,
    video_id: str | None = None,
) -> sqlite3.Row | None:
    """Return the most recently observed snapshot for this (entity, metric, window).

    Uses the `idx_channel_metric_latest` / `idx_video_metric_latest`
    indexes declared in migration 001 for O(log n) lookup.
    """
    table = _table_for(video_id)
    if video_id is not None:
        row = conn.execute(
            f"""
            SELECT * FROM {table}
            WHERE video_id = ? AND metric_key = ? AND grain = ?
              AND window_start = ? AND window_end = ?
            ORDER BY observed_on DESC
            LIMIT 1
            """,
            (video_id, metric_key, grain, window_start, window_end),
        ).fetchone()
    else:
        row = conn.execute(
            f"""
            SELECT * FROM {table}
            WHERE metric_key = ? AND grain = ?
              AND window_start = ? AND window_end = ?
            ORDER BY observed_on DESC
            LIMIT 1
            """,
            (metric_key, grain, window_start, window_end),
        ).fetchone()
    return row


def count_snapshots(
    conn: sqlite3.Connection,
    *,
    table: str,
    metric_key: str | None = None,
) -> int:
    """Utility for ops/tests — count rows, optionally filtered by metric."""
    if metric_key is None:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE metric_key = ?",
        (metric_key,),
    ).fetchone()[0]
