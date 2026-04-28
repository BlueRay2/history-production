# Round 5 Review — task-08-cron-systemd-tests
**Reviewer:** Codex
**Verdict:** NEEDS_CHANGES

## Findings (≤5)
- MEDIUM / `kpi/scripts/heartbeat.sh:153` / Retry after a failed post-recovery same-severity alert is still suppressed: the new gate only checks status values, so `last_alerted_status` can refer to an older incident before an `ok` recovery. Example sequence: `degraded` sends successfully and marks `alert_sent=1`; one or more `ok` heartbeats are written with `alert_sent=0`; a later `ok→degraded` regression attempts Telegram delivery and fails, leaving that new degraded row `alert_sent=0`; the next sustained degraded heartbeat sees `prev_status == degraded` and `last_alerted_status == degraded` from the old incident, then exits before retrying the undelivered current-episode alert. This is the same delivery-retry class as r4, but hidden by a prior same-severity alert. Suggested fix: suppress only after proving there is no pending unalerted row for the current non-ok episode, or compare timestamps so the successful alert must be newer than the latest recovery/status-change boundary.

## R4 resolution verification
- Codex r4 MED resolved only for the first-ever or no-prior-same-status-alert case: if the initial `ok→degraded` delivery fails and no previous degraded/down alert exists, `last_alerted_status` remains `NULL` or non-current, so the next degraded heartbeat retries.
- The new tests pin three useful sequences: retry after a failed first degraded delivery, post-recovery `ok→degraded` re-alert, and sustained degraded suppression after a successful alert.
- The tests do not pin the combined canonical sequence `degraded(alerted) → ok → degraded(delivery failed) → degraded(retry expected)`, where the implementation still suppresses because the old `degraded` alert remains the latest `alert_sent=1` row.

## Verdict rationale (3-5 sentences)
The replacement condition is an improvement over r4 for fresh incidents without an older same-status alert. However, because `ok` recovery rows do not update `alert_sent` and there is no separate incident boundary, status-only comparison against the latest alerted row still conflates a new post-recovery incident with the old one. `bash -n kpi/scripts/heartbeat.sh` passes, and the focused heartbeat suite passes locally: `pytest -q kpi/tests/test_heartbeat.py` reports `10 passed`. I did not run the full `kpi/tests/` suite or `systemd-analyze verify --user` in this round.
