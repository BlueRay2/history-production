# Codex Round 1 Review — task-07-monthly-tab-and-exceptions

**Reviewer:** codex
**Date:** 2026-04-22T10:15+03:00
**Commit reviewed:** 4a9ec24
**Verdict:** REQUEST_CHANGES

## Findings

- **[HIGH]** (app/services/monthly_view.py:148-159, confidence: high) `sparse_metrics_gated()` skips an entire grain when `channel_metric_snapshots` has no row for it. On a fresh/small channel that is still below the privacy floor or `<14` days old, `value_with_reason()` would classify every metric as gated, but this code returns nothing and `templates/exceptions.html` falls through to "Все метрики доступны". That is a user-facing false negative for the exact state this panel is meant to explain.

- **[HIGH]** (app/services/monthly_view.py:229-234, confidence: high) `parse_fail_cities()` bypasses `ingest.cost_parse.parse_city_cost()` and breaks on the first existing candidate file. If `{city}/COST_ESTIMATE.md` exists but is malformed while `{city}/docs/COST_ESTIMATE.md` is valid, `/exceptions/cost_templates` will report the city as a parse-fail even though `cost_per_video()` / `scan_all_cities()` accept it via the fallback path in `ingest/cost_parse.py:76-84`. That makes the exceptions page disagree with the KPI source of truth.

- **[HIGH]** (templates/monthly.html:52-54, confidence: high) Uses Jinja `select` with no test, which filters by truthiness rather than "not None". That does remove `None`, but it also drops legitimate `0` / `0.0` costs from the histogram payload. If zero-cost templates are valid, the chart silently undercounts them.

- **[MEDIUM]** (app/services/monthly_view.py:111-116, confidence: medium) Can double-match boundary-touching weekly windows because both predicates are inclusive around `published_at + 7 days`. If week-1 and week-2 windows share that boundary date, the join returns both rows and `ROW_NUMBER() ... ORDER BY vms.observed_on DESC` picks whichever was observed later, not necessarily the actual week-1 snapshot. The current tests only cover a single matching window, so this path is untested.

## Observations

- No blocking issue found in top-performer ordering; the SQL `ORDER BY composite_score DESC` survives because the template iterates the surrounding list, not dict key order.
- No circular-import break found in the weekly → monthly lazy import; the cycle is deferred to function scope and is safe as written.
