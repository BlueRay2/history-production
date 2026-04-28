# Round 3 Review — task-08-cron-systemd-tests
**Reviewer:** Codex
**Verdict:** NEEDS_CHANGES

## Findings (≤5)
- MEDIUM / `kpi/scripts/heartbeat.sh:130` / Fresh transition-detection gap: recovery to `ok` does not update any durable alert state, so a later same-severity outage after recovery is suppressed as if it were still the old outage. Example sequence: `degraded` sends and marks an alert, hourly `degraded` is correctly suppressed, `ok` writes heartbeat rows with `alert_sent=0` and no recovery marker, then a later `degraded` row compares against the last alerted status (`degraded`) and exits without alerting. That is a genuine `ok→degraded` transition and should page again. Suggested fix: compare the current status to the previous heartbeat status, or maintain a separate durable last-notified/last-state record that is updated on `ok` recovery even if no Telegram recovery alert is sent.

## R2 resolution verification
- Codex r2 MED partially resolved: sustained non-ok hourly recurrence no longer double-alerts, because the latest alerted status is checked before sending. Severity changes such as `degraded→down` and `down→degraded` also alert because the current non-ok status differs from the last alerted non-ok status.
- Codex r2 MED not fully resolved for alert semantics: the implementation keys only off the last alerted status, not the last observed heartbeat status, so it misses same-severity re-regressions after an `ok` interval.
- Gemini r2 LOW resolved: `install_kpi_vault.sh` now uses `mktemp -t kpi-health-probe.XXXXXX.json` plus `trap 'rm -f "$probe_file"' EXIT`; no fixed `/tmp/kpi-health-probe.json` write remains in the scripts.

## Verdict rationale (3-5 sentences)
The `/tmp` health-probe hardening is clean, and shell syntax checks pass for both changed scripts. The focused task-08 tests still pass locally: `pytest -q kpi/tests/test_install_kpi_vault_script.py kpi/tests/test_heartbeat.py` reports `21 passed`. The heartbeat alert-spam fix handles sustained `degraded`/`down` and severity changes, but it still does not model recovery as state, causing missed alerts for a later `ok→degraded` or `ok→down` transition at the same severity as the previous alert. I did not run `systemd-analyze verify --user`; the prior environment limitation around the user systemd manager still applies here.
