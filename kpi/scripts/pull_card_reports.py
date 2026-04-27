#!/usr/bin/env python3
"""One-shot puller for the YouTube Reporting API cards report.

Usage:
  pull_card_reports.py [--since 2026-04-01T00:00:00Z]

Idempotent: ensures the `channel_cards_a1` job exists, lists reports newer
than --since (defaults to 60 days back), downloads + parses each CSV, and
upserts daily channel-level card impressions / CTR rows into
`channel_metric_snapshots`. Uses a synthetic run_id so rows trace back to
this puller in `ingestion_runs`.

Exit codes:
  0  success (any number of rows written, including 0 if no reports yet)
  1  API or auth failure
  2  DB failure
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Make the repo importable when run via deploy symlink.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.db import db_path  # noqa: E402
from ingest.reporting import (  # noqa: E402
    ensure_cards_job,
    fetch_new_card_reports,
    upsert_card_metrics,
)

_LOG = logging.getLogger(__name__)


def _open_run(run_id: str) -> None:
    with sqlite3.connect(db_path(), timeout=10.0) as conn:
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute(
            """
            INSERT INTO ingestion_runs (run_id, source, started_at, status)
            VALUES (?, 'reporting_cards', ?, 'running')
            """,
            (run_id, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
        )


def _close_run(run_id: str, status: str, rows: int, err: str | None = None) -> None:
    with sqlite3.connect(db_path(), timeout=10.0) as conn:
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute(
            """
            UPDATE ingestion_runs
               SET status = ?, finished_at = ?, error_text = ?
             WHERE run_id = ?
            """,
            (
                status,
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                f"{err} (rows={rows})" if err else f"rows={rows}",
                run_id,
            ),
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--since",
        default=(datetime.now(timezone.utc) - timedelta(days=60))
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        help="Only fetch reports created after this RFC3339 timestamp",
    )
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    run_id = f"cards-{uuid.uuid4().hex[:12]}"
    try:
        _open_run(run_id)
    except sqlite3.Error as exc:
        print(f"db open failed: {exc}", file=sys.stderr)
        return 2

    try:
        job_id = ensure_cards_job()
        rows = fetch_new_card_reports(job_id, since_iso=args.since)
    except Exception as exc:  # noqa: BLE001 — boundary
        _close_run(run_id, "api_failure", 0, err=str(exc)[:300])
        print(f"reporting api failure: {exc}", file=sys.stderr)
        return 1

    # Codex review 2026-04-26 [LOW]: catch broader Exception around upsert.
    # CSV parsing, type coercion, or upstream module bugs would otherwise
    # exit via uncaught traceback and leave `ingestion_runs.status='running'`,
    # breaking the documented 0/1/2 exit-code contract.
    try:
        written = upsert_card_metrics(rows, run_id=run_id)
    except sqlite3.Error as exc:
        _close_run(run_id, "db_failure", 0, err=str(exc)[:300])
        print(f"db write failure: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 — boundary, must close run row
        _close_run(run_id, "api_failure", 0, err=f"{type(exc).__name__}: {exc}"[:300])
        print(f"upsert failure: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    _close_run(run_id, "ok", written)
    print(f"job={job_id} reports_aggregated={len(rows)} rows_written={written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
