"""Data assembly for /monthly route.

Pulls latest monthly channel snapshots, top-3 performers (from task-05
`top_performers()`), cost distribution (from `cost_per_video`), and
script-iterations histogram (from `script_iterations_approx`).

Each metric passes through `value_with_reason()` so `_card.html` can
render the four J-03 states.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from app.services.kpis import (
    MetricReading,
    cost_per_video,
    script_iterations_approx,
    top_performers,
    value_with_reason,
)
from app.services.weekly_view import MetricCard

# Metric keys surfaced as monthly top-row cards. Matches task-07 spec.
MONTHLY_METRICS: tuple[tuple[str, str], ...] = (
    ("subscribersNet", "Net New Subs"),
    ("subscriberConversionRate", "Sub Conv Rate"),
    ("playbackBasedCPM", "RPM"),
    ("estimatedRevenue", "Revenue 30d"),
    ("topPerformerScore", "Top Score"),
    ("costPerVideoAvg", "Cost/Video"),
)


def _latest_monthly_window(conn: sqlite3.Connection) -> tuple[str, str] | None:
    row = conn.execute(
        """
        SELECT window_start, window_end
        FROM channel_metric_snapshots
        WHERE grain = 'monthly'
        ORDER BY window_end DESC
        LIMIT 1
        """
    ).fetchone()
    return (row["window_start"], row["window_end"]) if row else None


def _subs_sparkline(conn: sqlite3.Connection) -> list[tuple[str, float]]:
    """12-month rolling net-subs series, (window_end, value) pairs."""
    rows = list(conn.execute(
        """
        WITH ranked AS (
            SELECT window_end, value_num,
                   ROW_NUMBER() OVER (
                       PARTITION BY window_start, window_end
                       ORDER BY observed_on DESC
                   ) AS rn
            FROM channel_metric_snapshots
            WHERE grain = 'monthly' AND metric_key = 'subscribersNet'
        )
        SELECT window_end, value_num FROM ranked
        WHERE rn = 1
        ORDER BY window_end DESC
        LIMIT 12
        """
    ))
    return [(r["window_end"], r["value_num"]) for r in reversed(rows)]


def _metric_card(
    conn: sqlite3.Connection,
    metric_key: str,
    label: str,
    window: tuple[str, str],
    *,
    channel_subs: int | None,
    channel_published_at: str | None,
    today: date | None,
) -> MetricCard:
    ws, we = window
    current = value_with_reason(
        conn,
        metric_key=metric_key, grain="monthly",
        window_start=ws, window_end=we,
        channel_subs=channel_subs,
        channel_published_at=channel_published_at,
        today=today,
    )
    # MoM delta would need the prior month's window_start/end — skipped in
    # MVP and rendered as None (card partial already hides WoW when None).
    return MetricCard(metric_key, label, current, None)


def recent_publishes(conn: sqlite3.Connection, *, limit: int = 5) -> list[dict]:
    """Last `limit` videos by published_at, with week-1 views if captured.

    If `video_metric_snapshots` has a `views` row for the first 7-day
    window post-publish, we surface it; otherwise `week1_views=None`.
    """
    rows = list(conn.execute(
        """
        WITH ranked AS (
            SELECT v.video_id, v.title, v.published_at, vms.value_num,
                   ROW_NUMBER() OVER (
                       PARTITION BY v.video_id
                       ORDER BY vms.observed_on DESC
                   ) AS rn
            FROM videos v
            LEFT JOIN video_metric_snapshots vms
              ON vms.video_id = v.video_id
             AND vms.metric_key = 'views'
             AND vms.grain = 'weekly'
             AND date(vms.window_start) <= date(v.published_at, '+7 days')
             AND date(vms.window_end)   >= date(v.published_at, '+7 days')
            WHERE v.published_at IS NOT NULL
        )
        SELECT video_id, title, published_at, value_num AS week1_views
        FROM ranked
        WHERE rn = 1
        ORDER BY published_at DESC
        LIMIT ?
        """,
        (limit,),
    ))
    return [dict(r) for r in rows]


def sparse_metrics_gated(
    conn: sqlite3.Connection,
    *,
    channel_subs: int | None,
    channel_published_at: str | None,
    today: date | None,
) -> list[dict]:
    """Surface metric keys that are below-privacy-floor or channel-too-new.

    Used by the exceptions panel to show which metrics are currently
    gated. We enumerate the weekly+monthly top-row metrics for the latest
    window of each grain and record anything whose reason != 'ok'.
    """
    from app.services.weekly_view import WEEKLY_METRICS

    gated: list[dict] = []

    for grain, metrics in (("weekly", WEEKLY_METRICS), ("monthly", MONTHLY_METRICS)):
        row = conn.execute(
            """
            SELECT window_start, window_end
            FROM channel_metric_snapshots
            WHERE grain = ?
            ORDER BY window_end DESC
            LIMIT 1
            """,
            (grain,),
        ).fetchone()
        if not row:
            continue
        for key, label in metrics:
            r = value_with_reason(
                conn,
                metric_key=key, grain=grain,
                window_start=row["window_start"], window_end=row["window_end"],
                channel_subs=channel_subs,
                channel_published_at=channel_published_at,
                today=today,
            )
            if r.reason != "ok":
                gated.append({
                    "grain": grain,
                    "metric_key": key,
                    "label": label,
                    "reason": r.reason,
                })
    return gated


def monthly_snapshot(
    conn: sqlite3.Connection,
    *,
    repo_root: Path,
    channel_subs: int | None = None,
    channel_published_at: str | None = None,
    today: date | None = None,
) -> dict:
    window = _latest_monthly_window(conn)
    today = today or datetime.now(timezone.utc).date()
    cards: list[MetricCard] = []
    if window:
        cards = [
            _metric_card(
                conn, key, label, window,
                channel_subs=channel_subs,
                channel_published_at=channel_published_at,
                today=today,
            )
            for key, label in MONTHLY_METRICS
        ]

    performers = top_performers(conn, limit=3, grain="monthly")
    cost_rows = cost_per_video(conn, repo_root)
    iteration_rows = script_iterations_approx(conn)
    return {
        "window": window,
        "cards": cards,
        "performers": [dict(r) for r in performers],
        "cost_distribution": cost_rows,
        "iteration_histogram": [dict(r) for r in iteration_rows],
        "subs_sparkline": _subs_sparkline(conn),
        "recent_publishes": recent_publishes(conn),
    }


def parse_fail_cities(repo_root: Path) -> list[str]:
    """List city slugs with a COST_ESTIMATE.md file present but no canonical
    total line — surfaced on /exceptions/cost_templates (F-02 backlog)."""
    cities: list[str] = []
    reserved = {
        "docs", "scripts", "tests", "app", "ingest", "db", "reviews",
        ".claude", ".github", ".entire", "previews", "shorts", "tiktok", "assets",
        "static", "templates", "state",
    }
    if not repo_root.exists():
        return []
    for entry in sorted(repo_root.iterdir()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in reserved:
            continue
        for candidate in (entry / "COST_ESTIMATE.md", entry / "docs" / "COST_ESTIMATE.md"):
            if candidate.exists():
                from ingest.cost_parse import _parse_file  # type: ignore
                if _parse_file(candidate, entry.name) is None:
                    cities.append(entry.name)
                break
    return cities
