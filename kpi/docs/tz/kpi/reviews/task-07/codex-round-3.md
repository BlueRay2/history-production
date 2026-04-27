# Round 3 Review

## Verdict

request changes

## Findings

- **LOW** `kpi/tests/test_monitoring.py:355` — `test_freshness_stale_filter_whitelist` does not actually pin the whitelist behavior. It only asserts `200` for `stale=-1`, `stale=inf`, and `stale=banana`; the previous buggy implementation would also pass those assertions while still sending `-1.0` / `inf` into the SQL parameter list. Recommendation: seed freshness rows and assert invalid values, especially `stale=inf` or `stale=2`, behave the same as no filter, while `stale=3` still filters.

## Notes

Verified the three implementation fixes at `7a0f18f`: `_freshness_drilldown.html` now has a single outer `.freshness-drilldown` wrapper and targets `closest .freshness-drilldown`; `/freshness` only casts `{"1","3","7"}` before appending the SQL stale parameter; the systemd comment now describes least-privilege/blast-radius and no longer mentions a fictitious SQLite owner check.

Verified tracked tree state through GitHub: `7a0f18f` is one commit after `74d52eb` and removes only `kpi/ingest/reporting.py` and `kpi/scripts/pull_card_reports.py`; both paths 404 at `kpi`/`7a0f18f`.

I could not run `git status` or the 19 monitoring tests locally because the shell sandbox fails before command execution with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. GitHub shows no CI statuses or workflow runs for `7a0f18f`.
