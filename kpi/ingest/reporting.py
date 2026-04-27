"""YouTube Reporting API client for the KPI dashboard.

Why a separate path from `ingest/youtube_client.py`:
The v2 Analytics `reports.query()` endpoint does not expose channel-level
`impressions` / `impressionsClickThroughRate` for non-content-owner channels
(Google issuetracker #254665034). The Reporting API (`youtubereporting v1`)
delivers daily CSV reports that DO include card-level impression data via
the `channel_cards_a1` system-managed report.

How it works:
1. `ensure_cards_job()` registers a daily report job (idempotent — finds
   existing job by reportTypeId before creating).
2. `fetch_new_card_reports()` lists reports created since `since_iso`,
   downloads each CSV, sums per-card numbers up to channel-day level, and
   returns a list of (date, card_impressions, card_clicks, card_click_rate)
   tuples.
3. `upsert_card_metrics()` writes those daily rows into
   `channel_metric_snapshots` with grain='daily' and metric_keys
   `cardImpressions` / `cardClickRate` so the existing weekly aggregator
   picks them up naturally.

Reports lag: a freshly-created Reporting API job produces its first CSV
~24-48h after creation; backfill (~30 days) follows over the next several
days. Until the first report lands, the dashboard falls back to the
Analytics API values that ingest/jobs.py still pulls.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from googleapiclient.discovery import build

from ingest.youtube_client import YouTubeClient

_LOG = logging.getLogger(__name__)

CARDS_REPORT_TYPE = "channel_cards_a1"
JOB_NAME = "kpi-dashboard-cards"


def _reporting_service(yt: YouTubeClient | None = None):
    yt = yt or YouTubeClient()
    return build("youtubereporting", "v1", credentials=yt._google_creds)


def ensure_cards_job(svc=None) -> str:
    """Return the job id for our cards report — create one if missing."""
    svc = svc or _reporting_service()
    existing = svc.jobs().list().execute().get("jobs", [])
    for j in existing:
        if j.get("reportTypeId") == CARDS_REPORT_TYPE:
            return j["id"]
    created = svc.jobs().create(
        body={"reportTypeId": CARDS_REPORT_TYPE, "name": JOB_NAME}
    ).execute()
    _LOG.info("reporting: created job %s", created["id"])
    return created["id"]


@dataclass(frozen=True)
class CardDailyRow:
    date_iso: str       # YYYY-MM-DD
    impressions: int
    clicks: int
    click_rate: float   # 0.0-1.0


def _parse_yyyymmdd(s: str) -> str:
    if len(s) == 8 and s.isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    return s


def _aggregate_csv(csv_text: str) -> list[CardDailyRow]:
    """Sum per-card rows up to channel-day level."""
    reader = csv.DictReader(io.StringIO(csv_text))
    by_day: dict[str, dict[str, float]] = {}
    for row in reader:
        d = _parse_yyyymmdd(row.get("date", ""))
        if not d:
            continue
        bucket = by_day.setdefault(d, {"impressions": 0, "clicks": 0})
        bucket["impressions"] += int(row.get("card_impressions") or 0)
        bucket["clicks"] += int(row.get("card_clicks") or 0)
    out: list[CardDailyRow] = []
    for d, agg in sorted(by_day.items()):
        impr = int(agg["impressions"])
        clicks = int(agg["clicks"])
        ctr = (clicks / impr) if impr else 0.0
        out.append(CardDailyRow(date_iso=d, impressions=impr, clicks=clicks, click_rate=ctr))
    return out


def fetch_new_card_reports(
    job_id: str,
    *,
    svc=None,
    since_iso: str | None = None,
) -> list[CardDailyRow]:
    """List + download all reports newer than `since_iso`, return parsed rows.

    The Reporting API REISSUES reports for the same `(startTime, endTime)`
    window — for example, when YouTube backfills retroactive corrections.
    Without deduping, a corrected reissue gets *added on top of* the original,
    inflating every metric. Codex review 2026-04-26 [HIGH]: dedupe by window,
    keep the newest `createTime` only.
    """
    svc = svc or _reporting_service()
    kwargs: dict = {"jobId": job_id, "pageSize": 100}
    if since_iso:
        kwargs["createdAfter"] = since_iso
    reports = svc.jobs().reports().list(**kwargs).execute().get("reports", [])
    if not reports:
        return []

    # Dedupe per (startTime, endTime) — keep newest createTime.
    by_window: dict[tuple[str, str], dict] = {}
    for rep in reports:
        key = (rep.get("startTime", ""), rep.get("endTime", ""))
        prev = by_window.get(key)
        if prev is None or rep.get("createTime", "") > prev.get("createTime", ""):
            by_window[key] = rep

    import requests
    from google.auth.transport.requests import Request as _AuthReq

    yt_creds = svc._http.credentials
    if not yt_creds.valid:
        yt_creds.refresh(_AuthReq())

    out: list[CardDailyRow] = []
    for rep in by_window.values():
        url = rep.get("downloadUrl")
        if not url:
            continue
        resp = requests.get(url, headers={"Authorization": f"Bearer {yt_creds.token}"}, timeout=60)
        resp.raise_for_status()
        out.extend(_aggregate_csv(resp.text))
    return out


def _iso_week_window(date_iso: str) -> tuple[str, str]:
    """Map YYYY-MM-DD → (Monday, Sunday) of its ISO week."""
    from datetime import date, timedelta

    d = date.fromisoformat(date_iso)
    monday = d - timedelta(days=d.isoweekday() - 1)
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def upsert_card_metrics(
    rows: Iterable[CardDailyRow],
    *,
    run_id: str,
    db_path: str | Path | None = None,
) -> int:
    """Write Reporting-API card metrics into channel_metric_snapshots.

    Two grains are written so the dashboard surfaces them immediately:
      - daily   : raw per-day values from the CSV.
      - weekly  : ISO-week aggregates (sum impressions, sum clicks, recompute
                  CTR = clicks/impressions). Same metric_key as the existing
                  Analytics-API path, so the latest-observed query picks the
                  Reporting value because it lands later.
    """
    import sqlite3
    from datetime import datetime, timezone

    from app.db import db_path as default_db_path

    path = str(db_path or default_db_path())
    observed = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    rows_list = list(rows)
    written = 0

    # Per-week aggregation for weekly-grain rows.
    weekly: dict[tuple[str, str], dict[str, int]] = {}
    for r in rows_list:
        wk = _iso_week_window(r.date_iso)
        bucket = weekly.setdefault(wk, {"impressions": 0, "clicks": 0})
        bucket["impressions"] += r.impressions
        bucket["clicks"] += r.clicks

    with sqlite3.connect(path, timeout=10.0) as conn:
        # Codex review r1 [LOW] + r3 follow-up: keep Python's connect-time
        # 10s lock-wait and align PRAGMA busy_timeout to the same 10000ms
        # (was 5000 in r1 patch, which actually LOWERED the effective wait;
        # Python's `timeout=` arg already feeds busy_timeout internally).
        conn.execute("PRAGMA busy_timeout=10000")

        # daily rows
        for r in rows_list:
            for key, value in (
                ("cardImpressions", float(r.impressions)),
                ("cardClickRate", float(r.click_rate)),
            ):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO channel_metric_snapshots
                        (metric_key, grain, window_start, window_end,
                         observed_on, value_num, run_id, preliminary)
                    VALUES (?, 'daily', ?, ?, ?, ?, ?, 0)
                    """,
                    (key, r.date_iso, r.date_iso, observed, value, run_id),
                )
                written += 1

        # Codex review 2026-04-26 [HIGH]: weekly aggregates must come from the
        # canonical day-level state in DB, not from the current `rows_list`
        # batch. Otherwise a single late-arriving day (typical for Reporting
        # API CSVs) would overwrite the previously-complete weekly snapshot
        # with a partial-week total. Re-aggregate per ISO week from DB.
        for (start, end) in weekly.keys():
            agg_row = conn.execute(
                """
                WITH latest AS (
                    SELECT metric_key, window_start, value_num,
                           ROW_NUMBER() OVER (
                             PARTITION BY metric_key, window_start
                             ORDER BY julianday(observed_on) DESC
                           ) AS rn
                    FROM channel_metric_snapshots
                    WHERE grain = 'daily'
                      AND metric_key IN ('cardImpressions', 'cardClickRate')
                      AND window_start >= ? AND window_end <= ?
                )
                SELECT metric_key, SUM(value_num) AS total
                FROM latest
                WHERE rn = 1
                GROUP BY metric_key
                """,
                (start, end),
            ).fetchall()
            agg_map = {row[0]: row[1] or 0.0 for row in agg_row}
            impr = float(agg_map.get("cardImpressions", 0.0))
            # cardClickRate is a daily ratio — to produce a weekly CTR we need
            # the click count, which equals (cardImpressions × cardClickRate)
            # per day summed. Recompute via a second pass to keep the SQL
            # simple and explicit.
            clicks_row = conn.execute(
                """
                WITH latest_pairs AS (
                    SELECT window_start, metric_key, value_num,
                           ROW_NUMBER() OVER (
                             PARTITION BY metric_key, window_start
                             ORDER BY julianday(observed_on) DESC
                           ) AS rn
                    FROM channel_metric_snapshots
                    WHERE grain = 'daily'
                      AND metric_key IN ('cardImpressions', 'cardClickRate')
                      AND window_start >= ? AND window_end <= ?
                )
                SELECT
                    SUM(CASE WHEN metric_key='cardImpressions' THEN value_num ELSE 0 END
                        * COALESCE((SELECT lp2.value_num FROM latest_pairs lp2
                                    WHERE lp2.metric_key='cardClickRate'
                                      AND lp2.window_start = latest_pairs.window_start
                                      AND lp2.rn = 1), 0)) AS clicks
                FROM latest_pairs
                WHERE rn = 1 AND metric_key='cardImpressions'
                """,
                (start, end),
            ).fetchone()
            clicks = float((clicks_row[0] if clicks_row else 0) or 0)
            ctr = (clicks / impr) if impr else 0.0

            for key, value in (
                ("cardImpressions", impr),
                ("cardClickRate", ctr),
            ):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO channel_metric_snapshots
                        (metric_key, grain, window_start, window_end,
                         observed_on, value_num, run_id, preliminary)
                    VALUES (?, 'weekly', ?, ?, ?, ?, ?, 0)
                    """,
                    (key, start, end, observed, value, run_id),
                )
                written += 1
    return written
