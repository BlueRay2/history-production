# Gemini Round 2 Review — task-03-append-snapshot-ingest

**Reviewer:** gemini
**Date:** 2026-04-22T19:00:00+03:00 (reported by Gemini; wall-clock 2026-04-22T01:23+03:00)
**Commit reviewed:** 0faaa8d
**Verdict:** request changes
**Extraction:** Gemini delivered content both via write_file (succeeded this round — explicit write-first instruction bypassed the r1 tool-routing failure) and in its `response` field. Claude coordinator extracted from the `response` field.

## Findings (3)

### 1. (MEDIUM) Potential for unbounded error string to exceed database column limits

- **Location:** `ingest/jobs.py` (`run_daily_refresh`)
- **Issue:** The per-video error aggregation logic concatenates all failure messages with a separator ('; '). In a scenario with a large number of videos and a systemic failure (e.g., invalid API credentials), the resulting `error_text` string could become excessively large and potentially exceed the size limit of the `ingestion_runs.error_text` database column, causing the final status update to fail.
- **Recommendation:** Truncate the aggregated error message at a reasonable length (e.g., 4096 or 8192 characters) and append a summary message like `"... (and N more errors)"` to ensure the final run status is always recordable.

### 2. (LOW) Inconsistent data state possible if crash occurs between metric and retention writes

- **Location:** `ingest/jobs.py` (`run_daily_refresh`)
- **Issue:** The main loop calls `_write_snapshot_batch` and `_write_retention_points` sequentially. If the system were to crash after the first write succeeds but before the second one completes, the database would be left in an inconsistent state for that run, with video metrics recorded but retention data missing.
- **Recommendation:** For each video, wrap both the snapshot and retention database writes within a single, encompassing database transaction. This ensures that either all data for a video is committed successfully or none of it is, maintaining data integrity.

### 3. (LOW) Silent success on empty `videos` table can mask configuration issues

- **Location:** `ingest/jobs.py` (`_discover_mapped_video_ids`)
- **Issue:** The function correctly returns an empty list if the `videos` table is empty or no videos are found. This causes the parent `run_daily_refresh` job to complete successfully but process no data. This "silent success" can mask upstream data population failures or misconfigurations where videos were expected to be present.
- **Recommendation:** The `run_daily_refresh` job should log a prominent `WARNING` if no videos are discovered. For production environments, consider adding a configuration flag to make this a hard failure, ensuring that an empty run is a noteworthy event.

## Addressed from round-1

The changes in commit `0faaa8d` correctly address all findings from the first review round.
- Per-video processing, PK uniqueness, 45-day off-by-one, client instantiation — all confirmed resolved.

## New observations

- Retention PK scaling (`elapsed * 1000`) is a good robust pattern.
- Snapshot PK could include `run_id` for future hardening but microsecond precision is sufficient for now.

## Summary

The core logic is sound and R1 issues are fixed, but three minor-to-medium risks related to data integrity and operational visibility were identified. The most important are ensuring error messages are bounded and wrapping per-video writes in a single transaction.
