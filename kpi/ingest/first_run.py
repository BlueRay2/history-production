"""First-run backfill — one-shot 45-day historical pull.

Runs exactly once on a fresh deployment. Detects emptiness of
channel_metric_snapshots; if fewer than FIRST_RUN_THRESHOLD rows, pulls the
last 45 days of weekly data via repeated calls to run_daily_refresh.

Entry point for task-08 install script: `python -m ingest.first_run`.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from app.db import connect as db_connect
from app.repositories.metrics import count_snapshots
from ingest.jobs import run_daily_refresh

_LOG = logging.getLogger(__name__)

BACKFILL_DAYS = 45
FIRST_RUN_THRESHOLD = 7  # <this many rows means we haven't backfilled

# Backfill window: target dates from (today - BACKFILL_DAYS - 1) through
# (today - PRELIMINARY_LAG_DAYS) inclusive = BACKFILL_DAYS+2-2 = 45 days
# iterated (Codex r1 MED fix — previously 44 due to off-by-one).


def needs_first_run() -> bool:
    """True iff channel_metric_snapshots is near-empty."""
    with db_connect() as conn:
        count = count_snapshots(conn, table="channel_metric_snapshots")
    return count < FIRST_RUN_THRESHOLD


def run_first_time_backfill(*, client=None, today: date | None = None) -> int:
    """Pull BACKFILL_DAYS of daily data. Returns count of ingest runs completed.

    Iterates target_date from (today - BACKFILL_DAYS) up to (today - 2),
    calling run_daily_refresh() once per target date. Aborts on quota
    exhaustion (leaves remaining days for the next invocation).
    """
    today = today or datetime.now(timezone.utc).date()
    # first_target starts one day earlier than BACKFILL_DAYS so the inclusive
    # range spans exactly BACKFILL_DAYS calendar days (Codex r1 MED).
    first_target = today - timedelta(days=BACKFILL_DAYS + 1)
    last_target = today - timedelta(days=2)

    runs_completed = 0
    current = first_target
    while current <= last_target:
        result = run_daily_refresh(current, client=client, today=today)
        runs_completed += 1
        _LOG.info(
            "first_run backfill day=%s run_id=%s status=%s rows=%d",
            current.isoformat(),
            result.run_id,
            result.status,
            result.rows_written,
        )
        if result.status == "quota_exhausted":
            _LOG.warning("first_run aborted at %s (quota exhausted)", current.isoformat())
            break
        current += timedelta(days=1)
    return runs_completed


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[first_run] %(message)s")
    if not needs_first_run():
        print("[first_run] channel_metric_snapshots already populated; no-op.")
        return 0
    completed = run_first_time_backfill()
    print(f"[first_run] backfill completed: {completed} daily runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
