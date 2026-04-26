# Codex Round 2 Review — task-03-append-snapshot-ingest

**Reviewer:** codex
**Date:** 2026-04-22T01:22:07+03:00
**Commit reviewed:** 0faaa8d
**Verdict:** request changes
**Extraction:** Claude coordinator extracted verbatim from Codex agent_message in `reviews/task-03-codex-r2-raw.log` (inline review due to sandbox apply_patch/exec failure).

## Findings

1. **Medium** — `ingest/jobs.py`: `_discover_mapped_video_ids()` treating an empty `videos` table as a normal empty worklist still lets the refresh complete without surfacing that all per-video analytics and retention pulls were skipped. In production that is indistinguishable from success even though the pipeline now depends on those mappings being present. This should at least mark the run `partial` with a clear diagnostic, and it needs a regression test for the empty-table case.

2. **Medium** — `ingest/jobs.py`: `write_snapshot_batch()` and `_write_retention_points()` are still separate transactions. If the process dies after the snapshot batch commits but before retention commits, the retry gets a new microsecond `observed_on`, so the latest snapshot row and latest retention rows no longer describe the same logical observation. If downstream code treats those tables as one sample, this is a consistency bug. Use a shared transaction or a run-scoped key if the two writes are meant to be atomic together.

3. **Medium** — `ingest/first_run.py`: the 45-day boundary fix is still not paired with an explicit regression test in the changed test set. That was one of the round-1 findings, so it should be locked down directly; otherwise a later refactor can reintroduce the off-by-one without touching any of the new round-2 tests.

## Addressed from round-1

- The high-severity round-1 gap is addressed: daily refresh now performs per-video analytics and retention pulls and degrades individual video failures to `partial`.
- The microsecond `observed_on` change addresses same-second primary-key collisions, and the new uniqueness test covers that path.
- The preliminary-window fix now keys off `window_end`, and the new boundary test covers that behavior.
- Moving client construction inside the run-level `try/except` is the right shape for recording credential failures in `ingestion_runs`.

## New observations

- I do not see a reason to expand the primary key with `run_id` if `observed_on` already persists microseconds; that would add schema churn without addressing the atomicity gap above.
- Joining per-video errors with `"; "` is acceptable as long as `ingestion_runs.error_text` is an unconstrained `TEXT` column. I would not block on that by itself.

## Summary

Most round-1 defects were fixed, but the new per-video path still has one silent-misconfiguration path and one consistency gap, and the `first_run` off-by-one fix still needs explicit regression coverage.
