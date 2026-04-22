"""Derived KPI views + value_with_reason API.

Sparse-metric semantics (J-03 per consensus):
  value_with_reason() -> (value: float|None, reason: "ok" | "below_privacy_floor"
      | "channel_too_new" | "no_data_pulled")

Privacy floors per Gemini research (small-channel YouTube Analytics):
  - below_privacy_floor: channel subs <50 OR video total views <100
  - channel_too_new: channel age <14 days

View definitions (materialised via CREATE VIEW in migration 002 — for MVP
we execute them inline; future migration 002 will persist):
  - v_weekly_scripts_finished
  - v_cycle_time_days
  - v_script_iterations_approx
  - v_cost_per_video (JOIN with cost_parse results)
  - v_weekly_channel_kpis
  - v_monthly_channel_kpis
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from ingest.cost_parse import scan_all_cities

_LOG = logging.getLogger(__name__)

Reason = Literal["ok", "below_privacy_floor", "channel_too_new", "no_data_pulled"]

# Privacy floor thresholds per Gemini research.
SUB_FLOOR = 50
VIDEO_VIEW_FLOOR = 100
CHANNEL_NEW_DAYS = 14


@dataclass(frozen=True)
class MetricReading:
    value: float | None
    reason: Reason


def value_with_reason(
    conn: sqlite3.Connection,
    *,
    metric_key: str,
    grain: str,
    window_start: str,
    window_end: str,
    video_id: str | None = None,
    channel_published_at: str | None = None,
    channel_subs: int | None = None,
    video_view_count: int | None = None,
    today: date | None = None,
) -> MetricReading:
    """Return latest snapshot value for (entity, metric, window) + sparse reason.

    Classification order:
      1. channel_too_new: if channel_published_at within CHANNEL_NEW_DAYS.
      2. below_privacy_floor: subs or view count below thresholds.
      3. no_data_pulled: table has no matching row for the window.
      4. ok: row exists, value surfaced.
    """
    today = today or datetime.now(timezone.utc).date()

    # 1. Privacy floor — applies to both channel and per-video metrics. A
    #    channel under the subs floor hides ALL metrics (not just per-video),
    #    per YouTube Analytics small-channel behavior (Gemini research).
    #    Per-video also hides if the video itself is below the view floor.
    if channel_subs is not None and channel_subs < SUB_FLOOR:
        return MetricReading(None, "below_privacy_floor")
    if video_id is not None and video_view_count is not None and video_view_count < VIDEO_VIEW_FLOOR:
        return MetricReading(None, "below_privacy_floor")

    # 2. Channel too new — classified only after privacy-floor so a tiny new
    #    channel returns the more-actionable "below_privacy_floor" reason.
    if channel_published_at:
        try:
            pub = datetime.fromisoformat(channel_published_at.replace("Z", "+00:00")).date()
            if (today - pub).days < CHANNEL_NEW_DAYS:
                return MetricReading(None, "channel_too_new")
        except ValueError:
            pass  # malformed date — continue with data-presence check

    # Query latest snapshot.
    if video_id is not None:
        row = conn.execute(
            """
            SELECT value_num FROM video_metric_snapshots
            WHERE video_id = ? AND metric_key = ? AND grain = ?
              AND window_start = ? AND window_end = ?
            ORDER BY observed_on DESC LIMIT 1
            """,
            (video_id, metric_key, grain, window_start, window_end),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT value_num FROM channel_metric_snapshots
            WHERE metric_key = ? AND grain = ?
              AND window_start = ? AND window_end = ?
            ORDER BY observed_on DESC LIMIT 1
            """,
            (metric_key, grain, window_start, window_end),
        ).fetchone()

    if row is None:
        return MetricReading(None, "no_data_pulled")
    return MetricReading(row["value_num"], "ok")


def weekly_scripts_finished(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Count of script_finished events per ISO week.

    event_value == 'also:script_started' commits (batch-phase3) still count
    as a script_finished for this view — primary event_type matters.
    """
    return list(conn.execute(
        """
        SELECT
            strftime('%Y-W%W', committed_at) AS iso_week,
            COUNT(*) AS n_finished
        FROM git_events
        WHERE event_type = 'script_finished'
        GROUP BY iso_week
        ORDER BY iso_week DESC
        """
    ))


def cycle_time_days(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """For each mapped video, compute (published_at - first_scaffold_commit_at) days.

    Cycle time per task-05 spec is `published_at - first_scaffold_commit_at`,
    where the scaffold milestone is the earliest `event_type='scaffold'` row
    in `git_events` for the city. We fall back to `projects.first_commit_at`
    only when no scaffold event exists (older pre-parser projects), so the
    KPI still surfaces a value rather than dropping the row.

    Uses active mappings only (video_project_map.active = 1). Videos without
    an active mapping are excluded entirely — task-07 surfaces them in the
    exceptions panel.
    """
    return list(conn.execute(
        """
        WITH first_scaffold AS (
            SELECT city_slug, MIN(committed_at) AS first_scaffold_at
            FROM git_events
            WHERE event_type = 'scaffold' AND city_slug IS NOT NULL
            GROUP BY city_slug
        )
        SELECT
            v.video_id,
            v.title,
            v.published_at,
            COALESCE(fs.first_scaffold_at, p.first_commit_at) AS start_at,
            julianday(v.published_at)
              - julianday(COALESCE(fs.first_scaffold_at, p.first_commit_at)) AS cycle_days
        FROM videos v
        JOIN video_project_map m ON m.video_id = v.video_id AND m.active = 1
        JOIN projects p ON p.city_slug = m.city_slug
        LEFT JOIN first_scaffold fs ON fs.city_slug = p.city_slug
        WHERE v.published_at IS NOT NULL
          AND COALESCE(fs.first_scaffold_at, p.first_commit_at) IS NOT NULL
        ORDER BY v.published_at DESC
        """
    ))


def script_iterations_approx(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Count of `revision` events per *mapped* city strictly between
    `script_started` and `script_finished` milestones.

    Approximate — rebase/squash collapses commits, and cities with batch
    phase-3 commits have overlapping start/finish so the window degenerates
    to zero revisions for that city (correctly). Labelled '(approx)' in UI.

    Joins `video_project_map.active=1` so unmapped cities are excluded from
    the per-video KPI surface (per task-07 exceptions contract).
    """
    return list(conn.execute(
        """
        WITH starts AS (
            SELECT city_slug, MIN(committed_at) AS started_at
            FROM git_events
            WHERE event_type = 'script_started' AND city_slug IS NOT NULL
            GROUP BY city_slug
        ),
        finishes AS (
            SELECT city_slug, MAX(committed_at) AS finished_at
            FROM git_events
            WHERE event_type = 'script_finished' AND city_slug IS NOT NULL
            GROUP BY city_slug
        )
        SELECT
            s.city_slug,
            SUM(CASE
                WHEN ge.event_type = 'revision'
                 AND ge.committed_at >= s.started_at
                 AND ge.committed_at <= f.finished_at
                THEN 1 ELSE 0 END) AS n_revisions,
            1 AS has_start,
            1 AS has_finish
        FROM starts s
        JOIN finishes f ON f.city_slug = s.city_slug
        JOIN video_project_map m ON m.city_slug = s.city_slug AND m.active = 1
        LEFT JOIN git_events ge ON ge.city_slug = s.city_slug
        GROUP BY s.city_slug
        ORDER BY n_revisions DESC
        """
    ))


def cost_per_video(
    conn: sqlite3.Connection,
    repo_root: Path,
) -> list[dict]:
    """Join COST_ESTIMATE.md totals with active video mappings.

    Fail-closed: videos mapped to a city whose COST_ESTIMATE.md is missing or
    malformed surface as `cost_value=None`, `cost_unit=None` (not 0, not
    error). Videos without an active mapping are excluded (caller surfaces
    them via the unmapped-cities panel in task-07).
    """
    cost_by_city = {e.city_slug: e for e in scan_all_cities(repo_root)}
    mapped = list(conn.execute(
        """
        SELECT v.video_id, v.title, m.city_slug
        FROM videos v
        JOIN video_project_map m
          ON m.video_id = v.video_id AND m.active = 1
        ORDER BY v.published_at DESC
        """
    ))
    out: list[dict] = []
    for row in mapped:
        est = cost_by_city.get(row["city_slug"])
        out.append({
            "video_id": row["video_id"],
            "title": row["title"],
            "city_slug": row["city_slug"],
            "cost_value": est.total_value if est else None,
            "cost_unit": est.unit if est else None,
        })
    return out


def _latest_window_rows(
    conn: sqlite3.Connection,
    *,
    grain: str,
    scope: Literal["channel", "video"],
) -> list[sqlite3.Row]:
    """Return latest (metric_key, window) snapshots for the requested grain.

    Uses `ROW_NUMBER() OVER (...)` to dedupe across multiple `observed_on`
    snapshots per (entity, metric, window) — daily append-only writes mean
    the same (video, metric, week) can have N rows; the dashboard only
    wants the latest-observed value.
    """
    table = "channel_metric_snapshots" if scope == "channel" else "video_metric_snapshots"
    partition = "metric_key, window_start, window_end" if scope == "channel" \
        else "video_id, metric_key, window_start, window_end"
    return list(conn.execute(
        f"""
        WITH ranked AS (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY {partition}
                ORDER BY observed_on DESC
            ) AS rn
            FROM {table}
            WHERE grain = ?
        )
        SELECT * FROM ranked WHERE rn = 1
        ORDER BY window_end DESC, metric_key
        """,
        (grain,),
    ))


def weekly_channel_kpis(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Latest weekly channel snapshots: impressions, CTR, AVD, AVP, etc."""
    return _latest_window_rows(conn, grain="weekly", scope="channel")


def monthly_channel_kpis(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Latest monthly channel snapshots: subs, RPM, revenue."""
    return _latest_window_rows(conn, grain="monthly", scope="channel")


def top_performers(
    conn: sqlite3.Connection,
    *,
    limit: int = 3,
    grain: str = "monthly",
) -> list[sqlite3.Row]:
    """Composite-score ranking of videos for Top-Performers panel.

    Score = equal-weight z-score across (views, averageViewPercentage,
    subscribersGained) within a single aligned window: the most recent
    (window_start, window_end) pair that has all three metrics present for
    at least one video. This avoids mixing metrics across windows (Codex
    r1 finding). Videos missing any of the three inputs inside that window
    are EXCLUDED, not scored as 0.

    SQLite has no STDDEV; we approximate via sqrt(E[x²] - E[x]²) and guard
    divide-by-zero with NULLIF → COALESCE(..., 1).
    """
    rows = list(conn.execute(
        """
        WITH ranked AS (
            SELECT video_id, metric_key, window_start, window_end, value_num,
                   ROW_NUMBER() OVER (
                       PARTITION BY video_id, metric_key, window_start, window_end
                       ORDER BY observed_on DESC
                   ) AS rn
            FROM video_metric_snapshots
            WHERE grain = ?
              AND metric_key IN ('views', 'averageViewPercentage', 'subscribersGained')
              AND value_num IS NOT NULL
        ),
        latest AS (
            SELECT * FROM ranked WHERE rn = 1
        ),
        -- Per-video coverage inside each window: how many of the three
        -- metrics the video has with a non-null value.
        video_window_coverage AS (
            SELECT video_id, window_start, window_end,
                   COUNT(DISTINCT metric_key) AS n_metrics
            FROM latest
            GROUP BY video_id, window_start, window_end
        ),
        -- Aligned window = the latest window_end for which AT LEAST ONE
        -- video has all three metrics (covering the r2 finding: a window
        -- where metrics are split across different videos must NOT be
        -- selected).
        aligned AS (
            SELECT window_start, window_end
            FROM video_window_coverage
            WHERE n_metrics = 3
            GROUP BY window_start, window_end
            ORDER BY window_end DESC
            LIMIT 1
        ),
        pivoted AS (
            SELECT
                l.video_id,
                MAX(CASE WHEN metric_key = 'views' THEN value_num END) AS views,
                MAX(CASE WHEN metric_key = 'averageViewPercentage' THEN value_num END) AS retention,
                MAX(CASE WHEN metric_key = 'subscribersGained' THEN value_num END) AS subs_gained
            FROM latest l
            JOIN aligned a
              ON l.window_start = a.window_start AND l.window_end = a.window_end
            GROUP BY l.video_id
            HAVING views IS NOT NULL AND retention IS NOT NULL AND subs_gained IS NOT NULL
        ),
        stats AS (
            SELECT
                AVG(views)       AS mv, AVG(retention)   AS mr, AVG(subs_gained) AS ms,
                NULLIF(SQRT(MAX(0, AVG(views*views)       - AVG(views)*AVG(views))),       0) AS sv,
                NULLIF(SQRT(MAX(0, AVG(retention*retention)   - AVG(retention)*AVG(retention))),   0) AS sr,
                NULLIF(SQRT(MAX(0, AVG(subs_gained*subs_gained) - AVG(subs_gained)*AVG(subs_gained))), 0) AS ss
            FROM pivoted
        )
        SELECT
            p.video_id, v.title, p.views, p.retention, p.subs_gained,
            ((p.views       - s.mv) / COALESCE(s.sv, 1) +
             (p.retention   - s.mr) / COALESCE(s.sr, 1) +
             (p.subs_gained - s.ms) / COALESCE(s.ss, 1)) AS composite_score
        FROM pivoted p
        CROSS JOIN stats s
        JOIN videos v ON v.video_id = p.video_id
        ORDER BY composite_score DESC
        LIMIT ?
        """,
        (grain, limit),
    ))
    return rows
