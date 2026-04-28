# Gemini r4 Review — task-08-cron-systemd-tests
**Reviewer:** Gemini
**Verdict:** LOOKS_GOOD

## Summary
The Codex r3 review correctly identified a medium-severity re-regression bug where a same-severity outage following a temporary recovery would be missed. The alert logic was only considering the last status that *caused an alert*, not the immediately preceding heartbeat status. The latest commit (011a3d4) modifies `kpi/scripts/heartbeat.sh` to compare the current status against the previous heartbeat row's status, which appears to correctly fix the re-regression flaw.

## Findings
- **LOW / VERIFICATION_GAP / `kpi/tests/test_heartbeat.py`**: While the fix in `heartbeat.sh` is logically sound and directly addresses the scenario described by Codex r3, I was unable to read the contents of `test_heartbeat.py`. Therefore, I cannot confirm that a test case exists for the specific sequence (`ok` → `degraded` → `ok` → `degraded`) that would validate the fix and prevent future regressions. The fix appears correct, but test coverage for it is unverified.

## Evidence
The logic in `heartbeat.sh` was updated to query the immediately preceding heartbeat status, not the last alerted one.

**Previous logic (inferred from Codex r3):**
Compare current status to the status of the last row where `alert_sent = 1`.

**Current logic (from `heartbeat.sh`):**
```python
# Compare against the IMMEDIATELY-PREVIOUS heartbeat row's status (the row
# right before the one we just inserted).
# ...
# Codex r3 caught this: keying off last-alerted status alone missed
# same-severity re-regression after an `ok` interval.

prev = con.execute(
    "SELECT status FROM monitoring_pings ORDER BY ping_at DESC LIMIT 1 OFFSET 1"
).fetchone()
prev_status = prev[0] if prev else None

if prev_status == status:
    # Sustained condition (previous heartbeat saw the same status).
    sys.exit(0)
# ... alert logic follows
```
This SQL query explicitly fetches the status of the row immediately prior to the one just inserted (`OFFSET 1`), which correctly models the previous state and allows for detecting a fresh transition from `ok`.

## Commands
No commands were executed. Manual verification is recommended.

## Risks
- **Low:** There is a low risk that the specific re-regression scenario is not covered by an automated test. If this is the case, a future modification to the heartbeat script could inadvertently re-introduce the bug. The fix itself is simple and appears correct, minimizing the immediate risk.

## Recommended Handoff
For Codex:

```markdown
**Task:** Final verification of test coverage for heartbeat re-regression.

1.  **Manually inspect `kpi/tests/test_heartbeat.py`.**
2.  **Confirm the presence of a test case that simulates the following sequence of heartbeats:**
    *   `ok`
    *   `degraded` (assert alert sent)
    *   `degraded` (assert alert NOT sent)
    *   `ok` (assert alert NOT sent)
    *   `degraded` (assert alert sent)
3.  If this test case is missing, please add it before marking the task complete. The core logic change looks good.
```
