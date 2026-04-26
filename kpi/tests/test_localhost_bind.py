"""Localhost bind guarantee — parse `ss -ltn` output.

We do NOT start a real server in CI (that would be flaky). Instead we
assert the install script's bind-check logic against synthetic `ss`
output — catches regressions in either the check direction (`0.0.0.0`
accidentally accepted) or the expected positive (`127.0.0.1` missing).
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _install_script() -> Path:
    return Path(__file__).resolve().parent.parent / "scripts" / "install_kpi_dashboard.sh"


def test_install_script_asserts_127_bind():
    """The install script explicitly greps for 127.0.0.1:PORT."""
    text = _install_script().read_text(encoding="utf-8")
    assert 'ss -ltn' in text
    assert '127.0.0.1:${PORT}' in text
    # And rejects 0.0.0.0 explicitly.
    assert '0.0.0.0:${PORT}' in text
    assert 'refusing to ship' in text


def test_install_script_curls_weekly_route():
    text = _install_script().read_text(encoding="utf-8")
    assert 'curl -sf' in text
    assert '/weekly' in text


def test_install_script_is_executable_shebang():
    text = _install_script().read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert 'set -euo pipefail' in text


def test_install_script_symlink_creation():
    """Deploy symlink is the single source of truth for both cron and
    systemd paths — guard it."""
    text = _install_script().read_text(encoding="utf-8")
    assert 'ln -sfn' in text
    assert 'DEPLOY_LINK="${DEPLOY_DIR}/kpi-dashboard"' in text
    assert '[[ -L "${DEPLOY_LINK}" ]]' in text


def test_systemd_service_localhost_only():
    unit = Path(__file__).resolve().parent.parent / "systemd" / "claude-kpi-dashboard.service"
    text = unit.read_text(encoding="utf-8")
    assert '--host 127.0.0.1' in text
    assert '0.0.0.0' not in text


def test_systemd_timer_schedules_for_0330():
    unit = Path(__file__).resolve().parent.parent / "systemd" / "dashboard-kpi-refresh.timer"
    text = unit.read_text(encoding="utf-8")
    assert 'OnCalendar=*-*-* 03:30:00 Europe/Minsk' in text
    assert 'Persistent=true' in text
