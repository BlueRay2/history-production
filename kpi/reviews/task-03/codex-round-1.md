# Codex Round 1 Review — task-03-append-snapshot-ingest

**Reviewer:** codex
**Date:** 2026-04-22T01:06:47+03:00
**Commit reviewed:** ca9b626
**Verdict:** request changes
**Extraction:** Claude coordinator extracted verbatim from Codex agent_message in `reviews/task-03-codex-r1-raw.log`. Sandbox blocked `apply_patch` + `exec_command` on target path (bwrap network-namespace issue, same as task-02 r-N reviews).

## Findings

- **[high]** (`ingest/jobs.py:144-165`, `ingest/jobs.py:172-214`) `run_daily_refresh()` only performs a single channel-level `get_channel_analytics()` call and emits `SnapshotRow(..., video_id=None)` rows. Nothing here ingests per-video metrics or retention, so `video_metric_snapshots` and `video_retention_points` remain empty and the advertised `"partial"` status is unreachable. Suggested fix: implement the per-video/retention path before closing the run.

- **[medium]** (`ingest/jobs.py:133-141`) failures during `YouTubeClient()` construction escape before `ingestion_runs` is opened. On the real cron path (`client=None`), credential/bootstrap/auth errors are neither classified nor audited. Suggested fix: open the run before client construction, or wrap construction in the same record-and-close path.

- **[medium]** (`ingest/jobs.py:64-65`, `ingest/jobs.py:195`, `app/repositories/metrics.py:50-56`) `observed_on` has only second resolution, but it is part of the PK and duplicate inserts are silently ignored. Two same-second re-pulls of the same window can produce different `run_id`s but only one snapshot row, which breaks the append-only invariant. Suggested fix: use sub-second precision or another uniqueness source and add a regression test.

- **[medium]** (`ingest/first_run.py:39-46`, `tests/test_ingest_jobs.py:164-169`) the "45-day" backfill only runs 44 target dates: `(today - 45)` through `(today - 2)` inclusive is 44 days, and the test encodes that bug. Suggested fix: start at `today - 46` or rename the constant/docs.

- **[medium]** (`ingest/jobs.py:68-79`, `ingest/jobs.py:143-156`) preliminary status is computed from `target_date`, but the spec defines it from `observed_on - window_end`. For weekly windows those diverge. Suggested fix: compute from resolved `week_end` and add a boundary test.

## Observations (non-blocking)

- (`app/repositories/metrics.py:106-143`, `db/migrations/001_init.sql:118-123`) `latest_snapshot()` is correct, but the claimed covering index is not actually covering; this is a performance note, not a correctness blocker.
- (`ingest/jobs.py:141-169`) a hard crash can leave `status='in_progress'`. I did not treat that as blocking because no reconciler was required in this task.

## Summary

Request changes. The main blocker is that task-03's per-video and retention ingest paths are still missing; the remaining issues are a same-second append collision, a one-day-short backfill, and preliminary status being derived from the wrong date.
