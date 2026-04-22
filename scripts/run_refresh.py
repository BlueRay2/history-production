#!/usr/bin/env python3
"""Daily KPI-dashboard refresh entry-point.

Invoked by the cron/systemd layer:
  /home/aiagent/assistant/deploys/kpi-dashboard/scripts/run_refresh.py

Exit codes (per task-08 spec):
  0  ok
  1  api failure
  2  db failure
  3  partial (some data pulled, some failed)
  40 quota exhausted

On any non-zero rc, sends a Telegram alert to Yaroslav directly via Bot
API (curl) — NOT through MCP — so the alert survives a dead Claude session.

A flock on `state/run_refresh.lock` prevents concurrent invocations when
both cron and systemd timer fire on the same tick (bypass-the-weakness
dual-scheduling guarantee).
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

# Make the repo importable when run via deploy symlink.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ingest.jobs import RunResult, run_daily_refresh  # noqa: E402

_LOG_DIR = Path("/home/aiagent/assistant/logs")
_LOG_FILE = _LOG_DIR / "dashboard-kpi.log"
_LOCK_FILE = Path("/home/aiagent/assistant/state/run_refresh.lock")
_YAROSLAV_CHAT_ID = "208368262"
_BOT_ENV_FILE = Path("/home/aiagent/.claude/channels/telegram/.env")


_EXIT_OK = 0
_EXIT_API_FAIL = 1
_EXIT_DB_FAIL = 2
_EXIT_PARTIAL = 3
_EXIT_QUOTA = 40


def _setup_logging() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(_LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def _bot_token() -> str | None:
    """Parse BOT_TOKEN from the telegram channel .env (plain KEY=VALUE)."""
    if not _BOT_ENV_FILE.is_file():
        return None
    for line in _BOT_ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "BOT_TOKEN":
            return value.strip().strip('"').strip("'")
    return None


def _alert_telegram(text: str) -> None:
    """Direct Bot API curl — survives Claude session downtime."""
    token = _bot_token()
    if not token:
        logging.warning("cannot alert — BOT_TOKEN not available")
        return
    try:
        subprocess.run(
            [
                "curl", "-sS", "--max-time", "15",
                f"https://api.telegram.org/bot{token}/sendMessage",
                "-d", f"chat_id={_YAROSLAV_CHAT_ID}",
                "--data-urlencode", f"text={text}",
            ],
            check=False,
            capture_output=True,
        )
    except Exception:  # pragma: no cover — best-effort alerting
        logging.exception("telegram alert curl failed")


def _classify(result: RunResult) -> int:
    """Map a RunResult into a task-08 exit code."""
    status = getattr(result, "status", None)
    error_text = getattr(result, "error_text", "") or ""
    if status == "ok":
        return _EXIT_OK
    if status == "partial":
        return _EXIT_PARTIAL
    low = error_text.lower()
    if "quota" in low or "ratelimit" in low or "rate limit" in low:
        return _EXIT_QUOTA
    if "sqlite" in low or "database" in low or "db" in low.split():
        return _EXIT_DB_FAIL
    return _EXIT_API_FAIL


def run(target_date: date | None = None) -> int:
    _setup_logging()
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

    # File-based flock: `fcntl.flock` is POSIX-only but this script is
    # linux-only too. Using `open + flock` non-blocking: if another process
    # holds the lock we exit 0 silently (that run is authoritative).
    import fcntl
    try:
        lock_fp = open(_LOCK_FILE, "w")
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logging.info("another run_refresh is active — exiting 0")
        return _EXIT_OK

    try:
        target_date = target_date or (date.today() - timedelta(days=2))
        logging.info("daily refresh start target=%s", target_date)
        result = run_daily_refresh(target_date=target_date)
        rc = _classify(result)
        status = getattr(result, "status", "unknown")
        rows = getattr(result, "rows_written", None)
        error = getattr(result, "error_text", "") or ""
        logging.info("daily refresh finished rc=%d status=%s rows=%s", rc, status, rows)

        if rc != _EXIT_OK:
            _alert_telegram(
                f"🔴 KPI dashboard refresh failed\n"
                f"rc={rc} status={status} target={target_date}\n"
                f"error: {error[:400]}"
            )
        return rc
    except Exception as exc:  # noqa: BLE001
        logging.exception("run_refresh crashed")
        _alert_telegram(f"🔴 KPI refresh CRASHED: {type(exc).__name__}: {exc}")
        return _EXIT_API_FAIL
    finally:
        try:
            fcntl.flock(lock_fp.fileno(), fcntl.LOCK_UN)
            lock_fp.close()
        except Exception:
            pass


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())
