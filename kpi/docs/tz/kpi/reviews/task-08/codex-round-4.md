# Round 4 Review — task-08-cron-systemd-tests
**Reviewer:** Codex
**Verdict:** NEEDS_CHANGES

## Findings (≤5)
- MEDIUM / `kpi/scripts/heartbeat.sh:138` / Fresh alert-delivery retry gap: comparing current status to the immediately previous heartbeat row fixes the recovered `ok→degraded` re-regression case, but it also suppresses retry after a failed Telegram send for the initial transition. Example sequence: previous row is `ok`, current row is `degraded`, Telegram delivery returns non-zero, so the row remains `alert_sent=0`; the next hourly heartbeat is still `degraded`, `prev_status == status`, and the script exits before looking for the undelivered unalerted row. That means a transient Telegram/API failure can turn a real outage transition into no delivered alert until the status changes again. Suggested fix: when `prev_status == status`, first check for an existing `alert_sent=0` row for the current non-ok status and retry delivery; only suppress if there is no pending undelivered alert.

## R3 resolution verification
- Codex r3 MED resolved for normal successful-alert transition semantics: comparing against `ORDER BY ping_at DESC LIMIT 1 OFFSET 1` uses the immediately previous observed heartbeat status, not the last alerted status.
- Case (a) `ok→degraded`: resolved. The current inserted `degraded` row sees previous row `ok`, treats it as a transition, sends, and marks the current row `alert_sent=1` on success.
- Case (b) `degraded→degraded`: resolved. The current inserted `degraded` row sees previous row `degraded` and exits without alert spam.
- Case (c) `degraded→ok`: unchanged and acceptable for the current task scope. The shell takes the OK branch, so no degraded/down Telegram alert is attempted; only the first-heartbeat OK alert path remains.
- Case (d) `ok→degraded` post-recovery: resolved. The previous row after recovery is `ok`, so a later `degraded` heartbeat is treated as a fresh transition and re-alerts.

## Verdict rationale (3-5 sentences)
The r3 finding about same-severity re-regression after recovery is fixed in the successful-delivery path. `bash -n kpi/scripts/heartbeat.sh` passes, and the focused heartbeat tests pass locally: `pytest -q kpi/tests/test_heartbeat.py` reports `7 passed`. However, the new suppression gate now runs before any pending unalerted-row lookup, so a failed transition alert is not retried on sustained non-ok status. I did not run the full `kpi/tests/` suite or `systemd-analyze verify --user` in this round.
