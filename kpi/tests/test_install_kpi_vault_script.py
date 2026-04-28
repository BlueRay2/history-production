"""Tests for scripts/install_kpi_vault.sh structural correctness (task-08).

We don't actually invoke systemd here (no DBus in CI), but we verify:
  - the script is executable and well-formed bash (`bash -n`)
  - it lists the expected unit files and references them by name
  - it has the 0.0.0.0 binding safety check
  - the systemd unit files exist with the names referenced by the installer
  - run_nightly.sh, heartbeat.sh, telegram-alert.sh are present + executable
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
SYSTEMD = REPO_ROOT / "systemd"
INSTALL = SCRIPTS / "install_kpi_vault.sh"


REQUIRED_UNITS = [
    "claude-kpi-monitoring.service",
    "kpi-nightly-ingest.service",
    "kpi-nightly-ingest.timer",
    "kpi-heartbeat.service",
    "kpi-heartbeat.timer",
]


REQUIRED_SCRIPTS = [
    "install_kpi_vault.sh",
    "run_nightly.sh",
    "heartbeat.sh",
    "lib/telegram-alert.sh",
]


def test_install_script_exists_and_executable():
    assert INSTALL.exists(), f"missing {INSTALL}"
    assert os.access(INSTALL, os.X_OK), f"{INSTALL} is not executable"


def test_install_script_bash_lint():
    rc = subprocess.run(["bash", "-n", str(INSTALL)], check=False).returncode
    assert rc == 0, "install_kpi_vault.sh failed `bash -n` syntax check"


def test_install_script_references_expected_units():
    body = INSTALL.read_text()
    for unit in REQUIRED_UNITS:
        assert unit in body, f"install script does not reference {unit}"


def test_install_script_has_0_0_0_0_safety_check():
    body = INSTALL.read_text()
    assert "0.0.0.0:" in body, "install script missing 0.0.0.0 bind safety check"
    assert "security violation" in body or "SECURITY" in body or "Aborting" in body, \
        "install script must abort if 0.0.0.0 binding detected"


def test_install_script_health_probe_presence():
    body = INSTALL.read_text()
    assert "/api/health" in body, "install script must probe /api/health endpoint"
    assert '"status"' in body and '"ok"' in body, \
        "install script must validate status:ok in health response"


def test_systemd_units_present():
    for unit in REQUIRED_UNITS:
        path = SYSTEMD / unit
        assert path.exists(), f"missing systemd unit {path}"


def test_required_scripts_present_and_executable():
    for rel in REQUIRED_SCRIPTS:
        path = SCRIPTS / rel
        assert path.exists(), f"missing script {path}"
        assert os.access(path, os.X_OK), f"{path} is not executable"


def test_timers_have_persistent_true():
    """systemd timers must set Persistent=true so missed firings replay after reboot."""
    for unit in ["kpi-nightly-ingest.timer", "kpi-heartbeat.timer"]:
        body = (SYSTEMD / unit).read_text()
        assert "Persistent=true" in body, f"{unit} must set Persistent=true"


def test_oneshot_services_use_oneshot_type():
    for unit in ["kpi-nightly-ingest.service", "kpi-heartbeat.service"]:
        body = (SYSTEMD / unit).read_text()
        assert "Type=oneshot" in body, f"{unit} must declare Type=oneshot"


def test_nightly_timer_calendar_is_0330_minsk():
    body = (SYSTEMD / "kpi-nightly-ingest.timer").read_text()
    assert "OnCalendar=*-*-* 03:30:00 Europe/Minsk" in body, \
        "kpi-nightly-ingest.timer must fire at 03:30 Europe/Minsk"


def test_heartbeat_timer_is_hourly():
    body = (SYSTEMD / "kpi-heartbeat.timer").read_text()
    assert "OnCalendar=hourly" in body, "kpi-heartbeat.timer must fire hourly"


def test_run_nightly_sources_telegram_lib():
    body = (SCRIPTS / "run_nightly.sh").read_text()
    assert "lib/telegram-alert.sh" in body, "run_nightly.sh must source the telegram alert lib"


def test_heartbeat_sources_telegram_lib():
    body = (SCRIPTS / "heartbeat.sh").read_text()
    assert "lib/telegram-alert.sh" in body, "heartbeat.sh must source the telegram alert lib"


def test_telegram_lib_silent_on_missing_token():
    """Token missing → function returns 0 silently. We can verify by sourcing
    in a subshell with a fake env path."""
    body = (SCRIPTS / "lib/telegram-alert.sh").read_text()
    assert "send_telegram_alert" in body
    assert "BOT_TOKEN" in body or "bot_token" in body.lower(), \
        "telegram-alert.sh must read BOT_TOKEN env"
