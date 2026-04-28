# DEPRECATED 2026-04-26: legacy /weekly route, replaced by app.monitoring
# (task-07 of kpi-vault TZ). Kept in-tree for rollback only; scheduled
# for removal +7 days post-task-02 merge.
"""Data assembly for /weekly route.

Pulls the latest ISO-week window from `channel_metric_snapshots`, the
retention curves published in that window, the scripts-finished count
for the week (git-derived), and the exceptions stats for the sidebar.

Each metric surfaces through `value_with_reason()` so the `_card.html`
partial can render `ok` / `below_privacy_floor` / `channel_too_new` /
`no_data_pulled` states per J-03.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.services.kpis import MetricReading, value_with_reason

# Metric keys surfaced as weekly top-row cards. Matches task-06 spec
# exactly: Impressions / CTR / AVD / AVP / Retention-avg. Scripts-finished
# is the sixth card but comes from git_events (not channel snapshots) so
# it is appended by the template, not this list.
# NOTE 2026-04-26: `impressions` / `impressionsClickThroughRate` are documented
# YouTube Analytics metrics but NOT exposed via the public reports.query() API —
# they're Studio-UI-only (see Google issuetracker #254665034). Substituted with
# `cardImpressions` / `cardClickRate` which the API accepts; semantically these
# are info-card impressions (not thumbnail impressions). Closest API analog
# until Google opens the thumbnail-impressions endpoint for non-content-owner
# channels.
WEEKLY_METRICS: tuple[tuple[str, str], ...] = (
    ("cardImpressions", "Card impressions"),
    ("cardClickRate", "Card CTR"),
    ("averageViewDuration", "AVD"),
    ("averageViewPercentage", "AVP"),
    ("retentionAverage", "Retention-avg"),
)


@dataclass(frozen=True)
class MetricCard:
    metric_key: str
    label: str
    current: MetricReading
    wow_delta: float | None  # signed delta vs prior week; None if prior window missing


def _latest_weekly_window(conn: sqlite3.Connection) -> tuple[str, str] | None:
    row = conn.execute(
        """
        SELECT window_start, window_end
        FROM channel_metric_snapshots
        WHERE grain = 'weekly'
        ORDER BY window_end DESC
        LIMIT 1
        """
    ).fetchone()
    return (row["window_start"], row["window_end"]) if row else None


def _prior_weekly_window(window_start: str) -> tuple[str, str]:
    """Return (prior_start, prior_end) one ISO-week earlier."""
    start = datetime.fromisoformat(window_start).date()
    prior_start = start - timedelta(days=7)
    prior_end = start - timedelta(days=1)
    return (prior_start.isoformat(), prior_end.isoformat())


def _metric_card(
    conn: sqlite3.Connection,
    metric_key: str,
    label: str,
    window: tuple[str, str],
    *,
    channel_subs: int | None,
    channel_published_at: str | None,
    today: date | None = None,
) -> MetricCard:
    ws, we = window
    current = value_with_reason(
        conn,
        metric_key=metric_key, grain="weekly",
        window_start=ws, window_end=we,
        channel_subs=channel_subs,
        channel_published_at=channel_published_at,
        today=today,
    )
    prior = value_with_reason(
        conn,
        metric_key=metric_key, grain="weekly",
        window_start=_prior_weekly_window(ws)[0],
        window_end=_prior_weekly_window(ws)[1],
        channel_subs=channel_subs,
        channel_published_at=channel_published_at,
        today=today,
    )
    wow = None
    if current.reason == "ok" and prior.reason == "ok" and prior.value:
        wow = (current.value - prior.value) / prior.value
    return MetricCard(metric_key, label, current, wow)


def weekly_snapshot(
    conn: sqlite3.Connection,
    *,
    channel_subs: int | None = None,
    channel_published_at: str | None = None,
    today: date | None = None,
) -> dict:
    """Return the full payload for /weekly rendering.

    Shape:
      {
        "window": (start, end) | None,
        "cards": [MetricCard, ...],
        "scripts_finished_this_week": int,
        "unmapped_videos": int,
        "retention_curves": [{video_id, title, points: [(t_pct, retention), ...]}, ...],
      }
    """
    today = today or datetime.now(timezone.utc).date()
    window = _latest_weekly_window(conn)
    cards: list[MetricCard] = []
    scripts_this_week = 0
    retention_curves: list[dict] = []

    if window:
        ws, we = window
        cards = [
            _metric_card(conn, key, label, window,
                         channel_subs=channel_subs,
                         channel_published_at=channel_published_at,
                         today=today)
            for key, label in WEEKLY_METRICS
        ]
        scripts_this_week = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM git_events
            WHERE event_type = 'script_finished'
              AND committed_at >= ? AND committed_at <= ?
            """,
            (ws, we + "T23:59:59Z"),
        ).fetchone()["n"]
        # Retention curves: surface the most recently published videos that
        # actually have retention data. Filtering by `published_at` ∈ the
        # latest weekly window is too strict because YouTube Analytics only
        # exposes retention curves once a video crosses the audience-privacy
        # threshold (~50 watch hours over 90 days). Brand-new videos have no
        # retention yet, which left the chart permanently blank for active
        # publishers. The new query joins `videos` with `video_retention_points`
        # and ranks by published_at DESC, capping at 6 curves so the legend
        # stays readable.
        _MAX_RETENTION_CURVES = 6
        retention_curves = [
            {
                "video_id": r["video_id"],
                "title": r["title"],
                # JSON-safe [elapsed, retention] pairs — `app.js` indexes by
                # p[0]/p[1] as the Chart.js dataset contract expects. Use
                # the latest observed snapshot per (video, elapsed) to dodge
                # duplicate rows from append-only daily refreshes.
                "points": [
                    [pt["elapsed_seconds"], pt["retention_pct"]]
                    for pt in conn.execute(
                        """
                        WITH ranked AS (
                            SELECT elapsed_seconds, retention_pct,
                                   ROW_NUMBER() OVER (
                                     PARTITION BY elapsed_seconds
                                     -- Codex review 2026-04-26 [MED]: use
                                     -- julianday() so mixed precision
                                     -- ('…56Z' vs '…56.123456Z') sorts
                                     -- chronologically. Plain TEXT DESC
                                     -- would put '…56Z' AFTER '…56.123456Z'
                                     -- and resolve to a stale snapshot.
                                     ORDER BY julianday(observed_on) DESC
                                   ) AS rn
                            FROM video_retention_points
                            WHERE video_id = ?
                        )
                        SELECT elapsed_seconds, retention_pct
                        FROM ranked WHERE rn = 1
                        ORDER BY elapsed_seconds
                        """,
                        (r["video_id"],),
                    )
                ],
            }
            for r in conn.execute(
                """
                SELECT v.video_id, v.title, v.published_at
                FROM videos v
                WHERE EXISTS (
                    SELECT 1 FROM video_retention_points rp
                    WHERE rp.video_id = v.video_id
                )
                ORDER BY v.published_at DESC
                LIMIT ?
                """,
                (_MAX_RETENTION_CURVES,),
            )
        ]

    unmapped = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM videos v
        WHERE NOT EXISTS (
            SELECT 1 FROM video_project_map m
            WHERE m.video_id = v.video_id AND m.active = 1
        )
        """
    ).fetchone()["n"]

    # recent_publishes is shared between /weekly and /monthly — imported
    # lazily to avoid circular import at module load.
    from app.services.monthly_view import recent_publishes
    recent = recent_publishes(conn)

    return {
        "window": window,
        "cards": cards,
        "scripts_finished_this_week": scripts_this_week,
        "unmapped_videos": unmapped,
        "retention_curves": retention_curves,
        "recent_publishes": recent,
    }


def channel_age_days(channel_published_at: str | None, today: date | None = None) -> int | None:
    """Return channel age in days for the calibration banner, or None."""
    if not channel_published_at:
        return None
    today = today or datetime.now(timezone.utc).date()
    try:
        pub = datetime.fromisoformat(channel_published_at.replace("Z", "+00:00")).date()
    except ValueError:
        return None
    return (today - pub).days
