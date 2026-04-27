# Round 2 Review

## Verdict

request changes

## Findings

- **MED** `kpi/app/monitoring/templates/_freshness_drilldown.html:8` — The drilldown filter form uses `hx-target="closest div"`. From inside the form, the closest `div` is the header wrapper, not the outer drilldown fragment, so filtering replaces only the header with a full drilldown fragment and leaves the old table behind. Recommendation: target a stable outer wrapper, e.g. add `freshness-drilldown` to the outer div and use `hx-target="closest .freshness-drilldown"`.

- **LOW** `kpi/app/monitoring/routes.py:211` — `stale=` is not limited to the documented dropdown values. Any parseable float is accepted, so direct requests like `stale=2`, `stale=-1`, or `stale=inf` bypass the intended `1/3/7` choices. SQL binding is safe and non-floats fall back to `None`. Recommendation: whitelist `{"1", "3", "7"}` before casting, or validate parsed values against `{1.0, 3.0, 7.0}`.

- **LOW** `kpi/systemd/claude-kpi-monitoring.service:10` — The `--user` / commented `User=aiagent` guidance is correct, but the comment says running as root would break a “read-only KPI_DB sqlite handle owner check”; no such owner check exists in the code. Recommendation: remove that clause or replace it with the concrete least-privilege/root execution risk.

## Notes

Verified: `_is_failing()` is used by both `/` and `/api/health`; parseable failing runs older than 24h do not degrade `/api/health`; ack repeat preserves the first `acknowledged_by`; read routes use `_db()` while only ack opens writable SQLite; `series` is passed as a dict to `tojson`; the errors `<pre>` uses normal Jinja escaping.

The five new tests cover their named paths, but they do not pin `/` stuck-running behavior, stale 7d non-degrade, stale whitelist handling, or the drilldown `dim/all` HTMX interaction.

I could not run the local tests because the shell sandbox fails before command execution with `bwrap: loopback: Failed RTM_NEWADDR`; this is a static review against commit `2f2de05`.
