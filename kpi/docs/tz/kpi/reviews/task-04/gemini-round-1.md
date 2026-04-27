# Round 1 Review — task-04-nightly-ingest-job
**Reviewer:** Gemini 3.1-pro
**Verdict:** REQUEST_CHANGES

## Spec coverage
The implementation correctly orchestrates the 7 phases defined in the spec, handling idempotency and partial-failure semantics robustly. Sub-runs track API quotas perfectly. However, the schema drift phase lacks job auto-creation, and the Telegram alert is currently unhandled.

## Findings
- [HIGH] `kpi/ingest/nightly.py` (`_persist_analytics_result`, `_parse_and_upsert_reporting_csv`) — **Invalid ISO 8601 timestamps on PK collisions.** When handling same-microsecond collisions, the uniqueness suffix is appended to the end of the Z (`_now_iso_micro() + str(col_idx)`). This results in malformed timestamps like `...Z1` which break SQLite strict date comparisons (e.g. `julianday()`). Fix by inserting the suffix before the timezone indicator: `_now_iso_micro()[:-1] + str(col_idx) + "Z"`.
- [HIGH] `kpi/ingest/nightly.py` (`_sync_schema_drift`) — **Schema drift sync does not auto-create jobs.** The phase detects and logs new report types, but fails to actually create jobs for them. Satisfy the Phase 6 spec by calling `client.ensure_jobs(added, conn=conn)` for the detected additions.
- [MEDIUM] `kpi/ingest/nightly.py` (`run_nightly`) — **Missing Telegram alert.** The spec and Acceptance Criteria mandate a Telegram alert on non-`ok` orchestrator status (Phase 7). The code computes the failures and updates the DB but never triggers an external notification.
- [MEDIUM] `kpi/ingest/nightly.py` (Insert Loops) — **Unbatched SQLite inserts cause heavy disk I/O.** Because the connection runs in `isolation_level=None` (autocommit), loops inside `_persist_analytics_result`, `_upsert_videos`, and `_parse_and_upsert_reporting_csv` execute each `INSERT` as a separate transaction. This risks violating the "< 5 minutes" SLA on large channel pulls. Wrap bulk inserts in explicit `BEGIN IMMEDIATE` / `COMMIT` blocks.
- [MEDIUM] `kpi/ingest/nightly.py` (`run_nightly`) — **Missing explicit pre-flight quota check.** Phase 1 requires verifying quota usage before starting. The orchestrator opens the run row without checking, meaning if quota is already capped, it opens a dangling run just to fail it. Call `from ingest.youtube_full import quota_check; quota_check("nightly_orchestrator", 0, conn=conn)` before `_open_run()`.

## Observations (non-blocking)
- In `_upsert_videos`, the ternary `1 if status.get("madeForKids") else 0 if status.get("madeForKids") is False else None` correctly differentiates explicit boolean values from missing keys.
- Using `fcntl.flock` directly inside a context manager elegantly satisfies the silent-exit concurrency requirement.
- The `FakeFullClient` test design cleanly isolates orchestrator business logic without relying on bulky HTTP cassettes.
