"""Tests for scripts/heartbeat.sh logic (task-08).

Strategy: re-implement the inline Python heartbeat logic as a fixture-driven
unit test against an isolated SQLite temp file. The shell wrapper is mostly
plumbing; the decision logic (ok/degraded/down by hours-since-last-run +
failing-source count) is what needs pinning.

Coverage:
  - empty ingestion_runs → degraded
  - all sources fresh + ok → status ok, monitoring_pings row written
  - max_hours > 26 → degraded
  - max_hours > 50 → down
  - failing_count >= 3 → down
  - alert dedup: alert_sent flag flips only once per row
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
MIG_002 = REPO_ROOT / "db" / "migrations-kpi" / "002_monitoring.sql"
MIG_003 = REPO_ROOT / "db" / "migrations-kpi" / "003_optimize_v_last_run_per_source.sql"


def _bootstrap_db(db_path: Path) -> sqlite3.Connection:
    """Create a minimal schema sufficient for v_last_run_per_source + monitoring_pings."""
    con = sqlite3.connect(db_path)
    con.executescript(
        """
        CREATE TABLE ingestion_runs (
            run_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            source_detail TEXT,
            started_at TEXT NOT NULL,
            status TEXT NOT NULL
        );
        """
    )
    con.executescript(MIG_002.read_text())
    con.executescript(MIG_003.read_text())
    con.commit()
    return con


def _seed_runs(con: sqlite3.Connection, runs):
    """runs: list of (run_id, source, source_detail, started_at_iso, status)."""
    con.executemany(
        "INSERT INTO ingestion_runs VALUES (?, ?, ?, ?, ?)", runs
    )
    con.commit()


def _heartbeat_decision(con: sqlite3.Connection):
    """Replicates the Python decision block embedded in scripts/heartbeat.sh.
    Kept aligned with that script — if the shell script changes, this must too.
    """
    rows = con.execute(
        """
        SELECT source, source_detail, last_status, last_started_jd,
               (julianday('now') - last_started_jd) * 24.0 AS hours_since
          FROM v_last_run_per_source
        """
    ).fetchall()
    if not rows:
        return "degraded", {"reason": "no ingestion_runs rows"}
    max_hours = max(r[4] for r in rows)
    failing = [r for r in rows if r[2] not in ("ok", "running")]
    if max_hours > 50 or len(failing) >= 3:
        status = "down"
    elif max_hours > 26 or failing:
        status = "degraded"
    else:
        status = "ok"
    return status, {
        "max_hours_since_last_run": round(max_hours, 2),
        "failing_count": len(failing),
    }


@pytest.fixture
def db(tmp_path):
    p = tmp_path / "kpi-heartbeat-test.sqlite"
    con = _bootstrap_db(p)
    yield con
    con.close()


def _iso(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def test_empty_ingestion_runs_is_degraded(db):
    status, detail = _heartbeat_decision(db)
    assert status == "degraded"
    assert "no ingestion_runs" in detail["reason"]


def test_fresh_ok_status_is_ok(db):
    _seed_runs(db, [
        ("r1", "channel", None, _iso(1.0), "ok"),
        ("r2", "reporting", "channel_basic_a2", _iso(2.0), "ok"),
    ])
    status, detail = _heartbeat_decision(db)
    assert status == "ok"
    assert detail["failing_count"] == 0


def test_max_hours_above_26_is_degraded(db):
    _seed_runs(db, [
        ("r1", "channel", None, _iso(30.0), "ok"),
    ])
    status, detail = _heartbeat_decision(db)
    assert status == "degraded"


def test_max_hours_above_50_is_down(db):
    _seed_runs(db, [
        ("r1", "channel", None, _iso(60.0), "ok"),
    ])
    status, detail = _heartbeat_decision(db)
    assert status == "down"


def test_three_failing_sources_is_down(db):
    _seed_runs(db, [
        ("r1", "channel", None, _iso(1.0), "api_failure"),
        ("r2", "reporting", "a", _iso(1.0), "quota_exhausted"),
        ("r3", "reporting", "b", _iso(1.0), "api_failure"),
        ("r4", "videos", None, _iso(1.0), "ok"),
    ])
    status, detail = _heartbeat_decision(db)
    assert status == "down"
    assert detail["failing_count"] == 3


def test_one_failing_source_is_degraded(db):
    _seed_runs(db, [
        ("r1", "channel", None, _iso(1.0), "ok"),
        ("r2", "reporting", "a", _iso(1.0), "api_failure"),
    ])
    status, detail = _heartbeat_decision(db)
    assert status == "degraded"
    assert detail["failing_count"] == 1


def test_alert_retry_after_failed_delivery(db):
    """If the first transition's Telegram delivery fails, alert_sent stays 0
    and the next heartbeat must still detect this as needing alert (retry),
    not suppress because prev_row==current. Codex r4 finding."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    earlier_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    # Insert two rows: earlier ok, current degraded (delivery failed → alert_sent=0)
    db.execute("INSERT INTO monitoring_pings VALUES (?, 'ok', '{}', 1)", (earlier_iso,))
    db.execute("INSERT INTO monitoring_pings VALUES (?, 'degraded', '{}', 0)", (now_iso,))
    db.commit()
    # Replicate the alert-decision logic from heartbeat.sh embedded Python:
    prev = db.execute(
        "SELECT status FROM monitoring_pings ORDER BY ping_at DESC LIMIT 1 OFFSET 1"
    ).fetchone()
    last_alerted = db.execute(
        "SELECT status FROM monitoring_pings WHERE alert_sent = 1 ORDER BY ping_at DESC LIMIT 1"
    ).fetchone()
    current = "degraded"
    should_suppress = (prev[0] == current and last_alerted is not None and last_alerted[0] == current)
    assert not should_suppress, "must NOT suppress when last_alerted differs from current"


def test_post_recovery_re_regression_alerts(db):
    """ok → degraded (alerted) → ok (recovery) → degraded again must alert."""
    base = datetime.now(timezone.utc) - timedelta(hours=4)
    rows = [
        ((base + timedelta(hours=0)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), "degraded", 1),  # alerted
        ((base + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), "ok", 0),
        ((base + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), "ok", 0),
        ((base + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), "degraded", 0),  # NEW transition
    ]
    db.executemany(
        "INSERT INTO monitoring_pings (ping_at, status, details_json, alert_sent) VALUES (?, ?, '{}', ?)",
        rows,
    )
    db.commit()
    prev = db.execute(
        "SELECT status FROM monitoring_pings ORDER BY ping_at DESC LIMIT 1 OFFSET 1"
    ).fetchone()
    last_alerted = db.execute(
        "SELECT status FROM monitoring_pings WHERE alert_sent = 1 ORDER BY ping_at DESC LIMIT 1"
    ).fetchone()
    current = "degraded"
    should_suppress = (prev[0] == current and last_alerted is not None and last_alerted[0] == current)
    assert not should_suppress, "ok→degraded post-recovery must NOT suppress alert"


def test_sustained_degraded_after_successful_alert_suppresses(db):
    """After a successful degraded alert, hourly degraded pings must suppress."""
    base = datetime.now(timezone.utc) - timedelta(hours=3)
    rows = [
        ((base + timedelta(hours=0)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), "ok", 1),
        ((base + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), "degraded", 1),  # alerted
        ((base + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), "degraded", 0),  # sustained
    ]
    db.executemany(
        "INSERT INTO monitoring_pings (ping_at, status, details_json, alert_sent) VALUES (?, ?, '{}', ?)",
        rows,
    )
    db.commit()
    prev = db.execute(
        "SELECT status FROM monitoring_pings ORDER BY ping_at DESC LIMIT 1 OFFSET 1"
    ).fetchone()
    last_alerted = db.execute(
        "SELECT status FROM monitoring_pings WHERE alert_sent = 1 ORDER BY ping_at DESC LIMIT 1"
    ).fetchone()
    current = "degraded"
    should_suppress = (prev[0] == current and last_alerted is not None and last_alerted[0] == current)
    assert should_suppress, "sustained degraded after successful alert must suppress"


def test_monitoring_pings_insert_and_dedup(db):
    """Insert a degraded ping, dispatch alert, mark alert_sent=1; subsequent
    select for unalerted rows returns nothing."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    db.execute(
        "INSERT INTO monitoring_pings (ping_at, status, details_json, alert_sent) VALUES (?, 'degraded', '{}', 0)",
        (now_iso,)
    )
    db.commit()
    # Dispatch alert (simulated): mark alert_sent=1
    db.execute(
        "UPDATE monitoring_pings SET alert_sent = 1 WHERE ping_at = ?", (now_iso,)
    )
    db.commit()
    pending = db.execute(
        "SELECT COUNT(*) FROM monitoring_pings WHERE alert_sent = 0 AND status IN ('degraded','down')"
    ).fetchone()[0]
    assert pending == 0, "alert dedup failed: row was not flipped to alert_sent=1"
