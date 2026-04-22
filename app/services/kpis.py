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

    # Classify channel age if publish date known.
    if channel_published_at:
        try:
            pub = datetime.fromisoformat(channel_published_at.replace("Z", "+00:00")).date()
            if (today - pub).days < CHANNEL_NEW_DAYS:
                return MetricReading(None, "channel_too_new")
        except ValueError:
            pass  # malformed date — continue with other checks

    # Privacy floor for per-video metrics.
    if video_id is not None:
        if video_view_count is not None and video_view_count < VIDEO_VIEW_FLOOR:
            return MetricReading(None, "below_privacy_floor")
        if channel_subs is not None and channel_subs < SUB_FLOOR:
            return MetricReading(None, "below_privacy_floor")

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
    """For each mapped video, compute (published_at - first_commit_at) days.

    Uses active mappings only (video_project_map.active = 1). Videos with
    no project match or project with no git history return NULL cycle time
    (surfaced as 'unmapped' in exceptions panel by task-07).
    """
    return list(conn.execute(
        """
        SELECT
            v.video_id,
            v.title,
            v.published_at,
            p.first_commit_at,
            julianday(v.published_at) - julianday(p.first_commit_at) AS cycle_days
        FROM videos v
        JOIN video_project_map m ON m.video_id = v.video_id AND m.active = 1
        JOIN projects p ON p.city_slug = m.city_slug
        WHERE v.published_at IS NOT NULL AND p.first_commit_at IS NOT NULL
        ORDER BY v.published_at DESC
        """
    ))


def script_iterations_approx(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Count of revision events per city between script_started and script_finished.

    Approximate — rebase/squash collapses commits, so this is labelled
    '(approx)' in UI per J-03.
    """
    return list(conn.execute(
        """
        SELECT
            city_slug,
            COUNT(CASE WHEN event_type = 'revision' THEN 1 END) AS n_revisions,
            COUNT(CASE WHEN event_type = 'script_started' THEN 1 END) AS has_start,
            COUNT(CASE WHEN event_type = 'script_finished' THEN 1 END) AS has_finish
        FROM git_events
        WHERE city_slug IS NOT NULL
        GROUP BY city_slug
        HAVING has_start >= 1 OR has_finish >= 1
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


def top_performers(conn: sqlite3.Connection, *, limit: int = 3) -> list[sqlite3.Row]:
    """Composite-score ranking of videos for Top-Performers panel.

    Score = equal-weight z-score across (views_30d, retention_avg,
    subs_gained_per_video). Videos missing any input are EXCLUDED (not
    ranked as 0) — per task-05 spec.

    SQL-only implementation: computes each metric's mean + stddev via
    window functions, then sums z-scores.
    """
    rows = list(conn.execute(
        """
        WITH latest AS (
            SELECT
                video_id,
                metric_key,
                value_num,
                ROW_NUMBER() OVER (PARTITION BY video_id, metric_key ORDER BY observed_on DESC) AS rn
            FROM video_metric_snapshots
            WHERE grain = 'weekly'
        ),
        pivoted AS (
            SELECT
                video_id,
                MAX(CASE WHEN metric_key = 'views' AND rn = 1 THEN value_num END) AS views,
                MAX(CASE WHEN metric_key = 'averageViewPercentage' AND rn = 1 THEN value_num END) AS retention,
                MAX(CASE WHEN metric_key = 'subscribersGained' AND rn = 1 THEN value_num END) AS subs_gained
            FROM latest
            GROUP BY video_id
            HAVING views IS NOT NULL AND retention IS NOT NULL AND subs_gained IS NOT NULL
        ),
        stats AS (
            SELECT
                AVG(views) AS mv, AVG(retention) AS mr, AVG(subs_gained) AS ms,
                -- SQLite has no STDDEV; approximate via sqrt(avg(x²) - avg(x)²).
                -- Use NULLIF to avoid division by zero in degenerate cases.
                NULLIF(
                    (SELECT SQRT(AVG(views*views) - AVG(views)*AVG(views)) FROM pivoted),
                    0) AS sv,
                NULLIF(
                    (SELECT SQRT(AVG(retention*retention) - AVG(retention)*AVG(retention)) FROM pivoted),
                    0) AS sr,
                NULLIF(
                    (SELECT SQRT(AVG(subs_gained*subs_gained) - AVG(subs_gained)*AVG(subs_gained)) FROM pivoted),
                    0) AS ss
            FROM pivoted
        )
        SELECT
            p.video_id, v.title, p.views, p.retention, p.subs_gained,
            ((p.views - s.mv) / COALESCE(s.sv, 1) +
             (p.retention - s.mr) / COALESCE(s.sr, 1) +
             (p.subs_gained - s.ms) / COALESCE(s.ss, 1)) AS composite_score
        FROM pivoted p
        CROSS JOIN stats s
        JOIN videos v ON v.video_id = p.video_id
        ORDER BY composite_score DESC
        LIMIT ?
        """,
        (limit,),
    ))
    return rows
