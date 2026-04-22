"""Tests for scripts/run_refresh.py entry point.

Asserts exit-code classification and that non-zero triggers a Telegram
alert call. Telegram curl is replaced with a spy so tests don't hit the
network.
"""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# Import via importlib so we get a fresh module each test.
_RUN_REFRESH_PATH = "scripts.run_refresh"


def _reload():
    if _RUN_REFRESH_PATH in sys.modules:
        return importlib.reload(sys.modules[_RUN_REFRESH_PATH])
    import scripts.run_refresh  # noqa: F401
    return sys.modules[_RUN_REFRESH_PATH]


def _make_result(status: str = "ok", error_text: str = "") -> SimpleNamespace:
    return SimpleNamespace(status=status, rows_written=10, error_text=error_text)


def test_rc0_on_success(tmp_path, monkeypatch):
    mod = _reload()
    monkeypatch.setattr(mod, "_LOCK_FILE", tmp_path / "lock")
    monkeypatch.setattr(mod, "_LOG_FILE", tmp_path / "log")
    monkeypatch.setattr(mod, "_LOG_DIR", tmp_path)
    alert = MagicMock()
    monkeypatch.setattr(mod, "_alert_telegram", alert)
    with patch(f"{_RUN_REFRESH_PATH}.run_daily_refresh", return_value=_make_result("ok")):
        rc = mod.run()
    assert rc == 0
    alert.assert_not_called()


def test_rc1_on_api_fail(tmp_path, monkeypatch):
    mod = _reload()
    monkeypatch.setattr(mod, "_LOCK_FILE", tmp_path / "lock")
    monkeypatch.setattr(mod, "_LOG_FILE", tmp_path / "log")
    monkeypatch.setattr(mod, "_LOG_DIR", tmp_path)
    alert = MagicMock()
    monkeypatch.setattr(mod, "_alert_telegram", alert)
    result = _make_result("failed", error_text="HTTP 500 from YouTube API")
    with patch(f"{_RUN_REFRESH_PATH}.run_daily_refresh", return_value=result):
        rc = mod.run()
    assert rc == 1
    alert.assert_called_once()
    assert "rc=1" in alert.call_args.args[0]


def test_rc2_on_db_error(tmp_path, monkeypatch):
    mod = _reload()
    monkeypatch.setattr(mod, "_LOCK_FILE", tmp_path / "lock")
    monkeypatch.setattr(mod, "_LOG_FILE", tmp_path / "log")
    monkeypatch.setattr(mod, "_LOG_DIR", tmp_path)
    alert = MagicMock()
    monkeypatch.setattr(mod, "_alert_telegram", alert)
    result = _make_result("failed", error_text="sqlite3 database is locked")
    with patch(f"{_RUN_REFRESH_PATH}.run_daily_refresh", return_value=result):
        rc = mod.run()
    assert rc == 2
    alert.assert_called_once()


def test_rc3_on_partial(tmp_path, monkeypatch):
    mod = _reload()
    monkeypatch.setattr(mod, "_LOCK_FILE", tmp_path / "lock")
    monkeypatch.setattr(mod, "_LOG_FILE", tmp_path / "log")
    monkeypatch.setattr(mod, "_LOG_DIR", tmp_path)
    alert = MagicMock()
    monkeypatch.setattr(mod, "_alert_telegram", alert)
    with patch(f"{_RUN_REFRESH_PATH}.run_daily_refresh", return_value=_make_result("partial")):
        rc = mod.run()
    assert rc == 3
    alert.assert_called_once()


def test_rc40_on_quota(tmp_path, monkeypatch):
    mod = _reload()
    monkeypatch.setattr(mod, "_LOCK_FILE", tmp_path / "lock")
    monkeypatch.setattr(mod, "_LOG_FILE", tmp_path / "log")
    monkeypatch.setattr(mod, "_LOG_DIR", tmp_path)
    alert = MagicMock()
    monkeypatch.setattr(mod, "_alert_telegram", alert)
    result = _make_result("failed", error_text="quotaExceeded: daily limit")
    with patch(f"{_RUN_REFRESH_PATH}.run_daily_refresh", return_value=result):
        rc = mod.run()
    assert rc == 40
    alert.assert_called_once()


def test_lock_oserror_alerts_and_returns_rc2(tmp_path, monkeypatch):
    """r1 MED: PermissionError / OSError on lock acquisition must alert,
    not silently propagate."""
    mod = _reload()
    bad_path = tmp_path / "nonexistent-readonly-dir" / "lock"
    monkeypatch.setattr(mod, "_LOCK_FILE", bad_path)
    monkeypatch.setattr(mod, "_LOG_FILE", tmp_path / "log")
    monkeypatch.setattr(mod, "_LOG_DIR", tmp_path)

    alert = MagicMock()
    monkeypatch.setattr(mod, "_alert_telegram", alert)

    # Prevent mkdir — simulate unwritable state/ dir by making the parent
    # a read-only file (so `mkdir(parents=True, exist_ok=True)` fails).
    readonly_parent = tmp_path / "blocker"
    readonly_parent.touch()
    monkeypatch.setattr(mod, "_LOCK_FILE", readonly_parent / "child" / "lock")

    rc = mod.run()
    assert rc == mod._EXIT_DB_FAIL
    alert.assert_called_once()
    assert "cannot acquire lock" in alert.call_args.args[0]


def test_classify_does_not_misroute_api_errors_mentioning_database(tmp_path, monkeypatch):
    """r1 MED: generic 'database' in API error text must NOT route to rc=2."""
    mod = _reload()
    monkeypatch.setattr(mod, "_LOCK_FILE", tmp_path / "lock")
    monkeypatch.setattr(mod, "_LOG_FILE", tmp_path / "log")
    monkeypatch.setattr(mod, "_LOG_DIR", tmp_path)
    monkeypatch.setattr(mod, "_alert_telegram", MagicMock())
    result = _make_result("failed",
                         error_text="YouTube Analytics database unavailable (503)")
    with patch(f"{_RUN_REFRESH_PATH}.run_daily_refresh", return_value=result):
        rc = mod.run()
    assert rc == 1  # API fail, NOT db fail


def test_classify_sqlite_specific_markers_route_to_rc2(tmp_path, monkeypatch):
    """r1 MED: actual sqlite3 errors still route to rc=2."""
    mod = _reload()
    monkeypatch.setattr(mod, "_LOCK_FILE", tmp_path / "lock")
    monkeypatch.setattr(mod, "_LOG_FILE", tmp_path / "log")
    monkeypatch.setattr(mod, "_LOG_DIR", tmp_path)
    monkeypatch.setattr(mod, "_alert_telegram", MagicMock())
    for marker in ("sqlite3.OperationalError: database is locked",
                   "disk I/O error during commit"):
        result = _make_result("failed", error_text=marker)
        with patch(f"{_RUN_REFRESH_PATH}.run_daily_refresh", return_value=result):
            rc = mod.run()
        assert rc == 2, f"marker {marker!r} should route to rc=2"


def test_crash_exception_alerts_and_returns_rc1(tmp_path, monkeypatch):
    mod = _reload()
    monkeypatch.setattr(mod, "_LOCK_FILE", tmp_path / "lock")
    monkeypatch.setattr(mod, "_LOG_FILE", tmp_path / "log")
    monkeypatch.setattr(mod, "_LOG_DIR", tmp_path)
    alert = MagicMock()
    monkeypatch.setattr(mod, "_alert_telegram", alert)
    with patch(f"{_RUN_REFRESH_PATH}.run_daily_refresh", side_effect=RuntimeError("boom")):
        rc = mod.run()
    assert rc == 1
    alert.assert_called_once()
    assert "CRASHED" in alert.call_args.args[0]
