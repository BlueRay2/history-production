# Round 1 Review — task-05-backfill-bootstrap
**Reviewer:** Codex GPT-5.5 (xhigh)  
**Verdict:** REQUEST_CHANGES

## Spec coverage
60-day default and `--days` override are present. Sentinel and `--force` are implemented. The shared lock is acquired with a 1-hour wait behavior. Reporting job registration calls `ensure_jobs`.

Coverage is incomplete for cursor resume, quota pacing, Reporting job failure handling, quota-exhausted alerts, and parity with task-04 channel-level Analytics pulls.

## Findings
- [HIGH] kpi/ingest/backfill.py:517 — Cursor resume only works when `stored_end == end_date`. A quota pause is expected to resume “tomorrow”, but tomorrow’s `end_date = today_utc - 2` has advanced, so the cursor is silently ignored and the run restarts a new window. Resume should freeze and reuse the cursor’s original `end_date`, unless `--force` is passed or the operator explicitly clears the cursor.

- [HIGH] kpi/ingest/backfill.py:632 — Reporting job registration failures are logged and ignored, then the backfill can still write the sentinel. That violates the acceptance criterion that all Reporting API jobs are registered idempotently. Treat `list_report_types` / `ensure_jobs` failure as terminal `api_failure` or avoid writing the sentinel until registration succeeds.

- [HIGH] kpi/ingest/backfill.py:642 — The `>= 8500` quota gate runs only before each day, not between Analytics calls. A large per-day loop can cross 8500 and keep consuming quota until the day finishes or the client hits its 9000 cap. Add a post-call or per-subrun threshold check inside `_ingest_one_day`, and persist cursor before further calls once the pause threshold is reached.

- [HIGH] kpi/ingest/backfill.py:684 — The `QuotaExhaustedError` mid-day path closes the orchestrator and returns without sending the required Telegram `quota_exhausted` alert. Add the same explicit backfill alert used by the pre-day threshold path.

- [MEDIUM] kpi/ingest/backfill.py:293 — Backfill does not run `analytics_live`, even though the spec says to run the same channel-level Analytics set as task-04 step 3, and nightly includes a live channel pull. Add the live sub-run after demographics to preserve task-04 parity.

- [MEDIUM] kpi/ingest/backfill.py:319 — Demographics `HttpError` and other channel-level failures are swallowed as a sub-run `api_failure`, despite `_ingest_one_day` documenting that channel-level failures abort the backfill. Mirror nightly behavior: channel-level non-schema failures should propagate to terminal `api_failure` / `auth_failed`.

- [LOW] kpi/ingest/backfill.py:526 — Resume does not seed `BackfillResult` from cursor `rows_written` / `quota_used`, and a second quota pause overwrites cursor totals with only the current process’s rows. This does not break date progress, but completion/pause reporting undercounts.

## Observations (non-blocking)
Tests cover the happy path, sentinel, dry-run, force-over-sentinel, basic cursor resume, quota threshold, and lock timeout. Missing regression tests for cursor resume across a changed UTC day, Reporting registration failure, live-pull parity, mid-day quota alert, and channel-level demographics `HttpError`.

I could not re-run tests locally because the shell sandbox failed with `bwrap: loopback: Failed RTM_NEWADDR`; this review is source-based.
