# Codex Round 2 Review — task-07-monthly-tab-and-exceptions

**Reviewer:** codex
**Date:** 2026-04-22T10:20+03:00
**Commit reviewed:** 85c9b16
**Verdict:** ACCEPTED

No findings.

## Notes

- `app/services/monthly_view.py:175-181` only synthesises placeholder windows in the `else` branch when the latest snapshot row is absent. If a snapshot exists and the channel is below floor, each metric is still evaluated exactly once for that grain, so no double-fire path. Confidence: high.
- `templates/monthly.html:53-56` `rejectattr("cost_value", "none")|map(attribute="cost_value")` is correct for `list[dict]` in Jinja; the lookup used by these filters resolves mapping keys here, so `0.0` is preserved while `None` rows are removed. Confidence: high.
- `app/services/monthly_view.py:117-120` now defines a half-open date window `[window_start, window_end)`, so a publish timestamp with hour/minute precision still lands in exactly one weekly bucket. The added regression test uses `2026-04-20T10:00:00Z`, which covers the non-midnight case. Confidence: medium.

Review based on commit 85c9b16 diff and the added coverage; I did not rerun the suite locally.
