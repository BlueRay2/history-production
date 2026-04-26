# Codex Round 1 Review — task-05-mapping-and-derived-kpis

**Reviewer:** codex
**Date:** 2026-04-22T08:03+03:00
**Commit reviewed:** 899c478
**Verdict:** REQUEST_CHANGES
**Extraction:** Claude coordinator extracted verbatim from Codex agent_message (sandbox=read-only, apply_patch blocked).

## Findings

- **[HIGH]** (app/services/kpis.py:63-85) `value_with_reason()` is not implementing the J-03 sparse-metric classifier correctly. It checks `channel_too_new` before privacy-floor and only evaluates `below_privacy_floor` when `video_id` is set. For channel-level metrics that disappear under the privacy floor, this falls through to `no_data_pulled` instead of `below_privacy_floor`; on a new small channel it also returns the wrong reason first. That breaks the consensus/UI contract for sparse metrics.
- **[HIGH]** (app/services/kpis.py:133-151) `cycle_time_days()` uses `projects.first_commit_at`, but the task spec defines cycle time as `published_at - first_scaffold_commit_at`. Any project with prep commits before the scaffold milestone will show inflated cycle times, so this KPI is measuring repo age rather than idea→publish time.
- **[HIGH]** (app/services/kpis.py:157-175) `script_iterations_approx()` does not implement the required window. It counts every `revision` event for a city and only checks that the city has some `script_started`/`script_finished` event somewhere; it never constrains revisions to the interval between those milestones and never joins active mappings. That overcounts iterations and leaks unmapped cities into the per-video KPI surface.
- **[HIGH]** (app/services/mapping.py:47-60, app/services/mapping.py:128-136) The manual-override contract is not enforced. `suggest_mappings()` treats any `active=0` row as "still unmapped" even if the same video/project already has an `active=1` row, and `approve_mapping()` only flips the requested row instead of deactivating competing mappings. A manual approval therefore does not actually "win"; stale suggestions can be regenerated and downstream KPI joins can duplicate one video across multiple cities.
- **[MEDIUM]** (app/services/mapping.py:39-44, app/services/mapping.py:64-84) The implemented matcher omits required task-05 heuristics. There is no 7-day publish/script-finished proximity fallback, and the slug check is only `city_slug in title_slug`, not the spec's bidirectional normalized-slug match. Valid city/video pairs that rely on timing or reverse containment will never be suggested, leaving derived KPIs blank for those videos.
- **[HIGH]** (app/services/kpis.py:256-285) `top_performers()` is not ranking on the spec's aligned `views_30d / retention_avg / subs_gained_per_video` window. It pulls the latest *weekly* snapshot independently per metric, so a video can be ranked with views from one week and retention/subscribers from another. That produces composite scores from mixed windows and diverges from the monthly "top performers" definition.

## Observations

- `cost_per_video()` looks fail-closed in the two paths called out by the task: missing `COST_ESTIMATE.md` and malformed `COST_ESTIMATE.md` both surface `None`/`NULL`, not `0` and not an exception.
- CLI positional order matches the spec wording (`video_id city_slug`), and `write_suggestions()` does use `BEGIN IMMEDIATE` with a rollback path. The blockers here are semantic correctness issues, not the transaction scaffold.
- The current tests miss the main regressions above, especially `script_iterations_approx()` windowing/mapping gating and multi-active mapping conflicts.

## Summary

Request changes. The fail-closed cost path and transaction skeleton look fine, but the current mapping/KPI implementation still diverges from task-05 in ways that will surface wrong KPI values or wrong sparse-data reasons in the dashboard.
