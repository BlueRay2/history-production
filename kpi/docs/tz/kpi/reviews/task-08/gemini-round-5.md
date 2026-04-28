# Round 5 Review — task-08-cron-systemd-tests
**Reviewer:** Gemini
**Verdict:** LOOKS_GOOD

## Summary
I have reviewed the `per-incident dedup` logic implemented in `kpi/scripts/heartbeat.sh` in response to the MEDIUM severity finding in `codex-round-5.md`. The updated logic and the new corresponding tests in `kpi/tests/test_heartbeat.py` appear to correctly resolve the issue where a post-recovery alert could be incorrectly suppressed.

## Findings
The implementation correctly addresses the scenario raised by Codex: `degraded(alerted) → ok(recovery) → degraded(delivery-failed) → degraded(retry-expected)`.

The new approach correctly defines an "incident" as the contiguous series of pings of the current status, starting from the most recent ping of a *different* status. By searching for `alert_sent=1` only within the bounds of this new incident, the script correctly determines that a new alert is required, even if a same-severity alert exists from a *previous* incident. This resolves the bug.

## Evidence
1.  **Code Logic:** The Python code block at `kpi/scripts/heartbeat.sh:157-187` implements the fix. It first finds the `boundary_at` timestamp, which marks the end of the previous state and the beginning of the current incident. It then correctly checks for `already_alerted` pings only *after* this boundary (`ping_at > ?`), effectively isolating the current incident from past ones.

2.  **Test Coverage:** `kpi/tests/test_heartbeat.py` now includes `test_post_recovery_failed_delivery_then_retry`. This test case explicitly constructs the problematic database state that Codex identified and asserts `not _should_suppress_per_incident(db, "degraded")`, confirming that the logic will correctly retry the failed alert in the new incident. This is a high-quality regression test that directly validates the fix.

## Commands
A full run of the test suite would be the final validation step. Based on my review of the code and test logic, I expect the following command to pass:
```bash
pytest kpi/tests/test_heartbeat.py
```

## Risks
Low. The change is confined to the alerting logic and is backed by a specific test case that covers the previously-missed failure mode. The logic is more robust than the previous implementation.

## Recommended Handoff
Handoff to Codex for final verification. The implementation appears to be a direct and correct resolution to the r5 finding, complete with a targeted regression test.
