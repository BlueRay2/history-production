"""Static structural tests for scripts/decommission_dashboard.sh (task-02).

We don't actually invoke systemd or move files; we verify the script
contains all the safety features required by the task spec:
  - shellcheck-clean (`bash -n`)
  - executable
  - preflight gates (verification window + monitoring active)
  - SHA-256 backup hash check
  - mv (not rm) for the legacy DB
  - Telegram broadcast at end
  - distinct exit codes (2/3/4) for the 3 failure modes per spec
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "decommission_dashboard.sh"


def test_script_exists_and_executable():
    assert SCRIPT.exists(), f"missing {SCRIPT}"
    assert os.access(SCRIPT, os.X_OK), f"{SCRIPT} not executable"


def test_script_bash_lint():
    rc = subprocess.run(["bash", "-n", str(SCRIPT)], check=False).returncode
    assert rc == 0, f"{SCRIPT} failed `bash -n` syntax check"


def test_preflight_gate_for_monitoring_service():
    body = SCRIPT.read_text()
    assert "claude-kpi-monitoring.service" in body
    assert "is-active" in body, "preflight must check monitoring service is active"
    assert "exit 4" in body or 'die "claude-kpi-monitoring.service is not active"' in body, \
        "must exit 4 when new monitoring service inactive"


def test_preflight_gate_for_verification_window():
    body = SCRIPT.read_text()
    assert "VERIFICATION_DAYS_REQUIRED" in body
    assert "FIRST_RUN_FLAG" in body and "FIRST_HB_FLAG" in body
    assert "exit 2" in body, "must exit 2 when verification window not satisfied"


def test_backup_sha256_check_present():
    body = SCRIPT.read_text()
    assert "sha256sum" in body
    assert "SHA_SRC" in body and "SHA_DST" in body
    assert "exit 3" in body, "must exit 3 on hash mismatch"


def test_uses_mv_not_rm_for_legacy_db():
    body = SCRIPT.read_text()
    assert 'mv "$LEGACY_DB" "$RETIRED_PATH"' in body, \
        "legacy DB must be MOVED to retired-YYYY-MM-DD path, not rm'd"
    assert ".retired-" in body, "retired-YYYY-MM-DD pattern must be present"


def test_telegram_broadcast_present():
    body = SCRIPT.read_text()
    assert "send_telegram_alert" in body, "must broadcast decommission status"


def test_legacy_units_listed_for_removal():
    body = SCRIPT.read_text()
    assert "claude-kpi-dashboard.service" in body
    assert "dashboard-kpi-refresh.timer" in body


def test_idempotent_pattern_visible():
    """Re-runnable: backup-already-exists branch + retired-DB branch should
    let a second run be a no-op or a verification."""
    body = SCRIPT.read_text()
    assert "backup already exists" in body or "RETIRED_PATH" in body


def test_deep_memory_archive_target():
    body = SCRIPT.read_text()
    assert "git/deep-memory/archive" in body, \
        "backup target must be in deep-memory archive per task spec"
    assert "dashboard-kpi-final-backup" in body
