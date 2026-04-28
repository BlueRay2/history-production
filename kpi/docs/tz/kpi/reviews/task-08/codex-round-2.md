# Round 2 Review — task-08-cron-systemd-tests
**Reviewer:** Codex
**Verdict:** NEEDS_CHANGES

## Findings (≤5)
- MEDIUM / `kpi/scripts/heartbeat.sh:105` / Fresh issue: sustained `degraded` or `down` status will alert every hour, not only on the first transition. The heartbeat inserts a new `monitoring_pings` row with `alert_sent=0`, then selects the newest unalerted row for the current status and marks only that row `alert_sent=1`. On the next hourly heartbeat, the still-degraded system creates a fresh unalerted row and sends the same class of alert again. This conflicts with the migration/task text that says Telegram fires on the first `degraded`/`down` transition and that alert deduplication via `alert_sent` works. Suggested fix: before alerting, compare against the previous ping status or maintain a durable last-alerted status; alert only when transitioning from `ok` to non-ok or when the severity changes, while still writing every heartbeat row.

## R1 resolution verification
- H1 resolved: `install_kpi_vault.sh` now contains all five literal unit names: `claude-kpi-monitoring.service`, `kpi-nightly-ingest.service`, `kpi-nightly-ingest.timer`, `kpi-heartbeat.service`, and `kpi-heartbeat.timer`. The focused structural test passes.
- H2 resolved: `/home/aiagent/assistant/config/scheduled-crons.tson` contains enabled durable entries for `kpi_nightly_ingest` (`30 3 * * *`) and `kpi_monitoring_heartbeat` (`0 * * *`). Both referenced prompt files exist via `/home/aiagent/assistant/config/cron-prompts/` and call the expected wrapper scripts.
- M1 resolved: installer health probing is now reachability-only: HTTP 200 plus JSON status in `ok|degraded|down`, with `status:ok` explicitly deferred until after first ingest. The installer disables both timers and `claude-kpi-monitoring.service` before aborting on `0.0.0.0:${PORT}`.
- M2 resolved: `telegram-alert.sh` returns `0` delivered, `2` skipped, and `3` failed. `run_nightly.sh` writes the first-success flag only after `send_telegram_alert` returns success.
- M3 resolved for the reported DB write/schema failure mode: `heartbeat.sh` writes an explicit temp result token, catches schema/write failures as `error:*`, sends a Telegram failure alert, logs the DB error, and exits 4.

## Verdict rationale (3-5 sentences)
All five round-1 findings are addressed in the current workspace. The focused task-08 tests pass locally: `pytest -q kpi/tests/test_install_kpi_vault_script.py kpi/tests/test_heartbeat.py` reports `21 passed`. The remaining issue is a fresh heartbeat alert-dedup regression against the monitoring schema intent: every non-ok hourly row is new and unalerted, so a persistent outage can spam Telegram hourly. I could not run `systemd-analyze verify --user` because the user systemd manager is unavailable in this environment (`Failed to initialize manager: No such device or address`).
