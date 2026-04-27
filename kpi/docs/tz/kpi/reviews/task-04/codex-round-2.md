# Round 2 Review — task-04-nightly-ingest-job
**Reviewer:** Codex GPT-5.5 (xhigh)
**Verdict:** REQUEST_CHANGES

## R1 finding resolution
- HIGH (CSV dim): resolved. `_parse_and_upsert_reporting_csv` now performs a full CSV pass, classifies metric columns by all non-empty cells coercing numeric, treats non-numeric columns as dimensions, and writes `dimension_key` as `dim=val|...` for both channel and video snapshots.
- MED (channel api_failure): partial. Generic exceptions in the main channel-basic loop and demographics now propagate to `run_nightly`, which maps them to `api_failure`. However, the `channel:live` block still catches generic exceptions, appends `channel:live:<type>` to `result.failures`, and lets the orchestrator close `partial`. Also, `SchemaDriftError` in channel-basic/demographics is still downgraded to `partial`, matching the narrowed “non-Schema” fix but not the broader R1 concern that channel-level failures should not produce `partial`.
- MED (high-water mark): resolved. Reporting high-water mark now uses only `download_status='parsed'`, and existing `pending|downloaded|failed` reports are re-merged into the retry set with id deduplication.
- MED (ensure_jobs propagation): resolved. `_sync_schema_drift` captures non-quota `ensure_jobs` failures, continues through deprecated drift recording, then re-raises so Phase 6 marks the nightly non-`ok`.
- MED (db_failure alert): resolved. The outer crash path now sends a best-effort red `db_failure` Telegram alert before re-raising.
- LOW (retention week): resolved. Retention now anchors to the previous ISO week Monday via `date.fromisocalendar(iso_year, iso_week, 1)`.

## New findings (max 3)
None beyond the partial R1 channel-failure resolution above.

## Verdict rationale
Most fixes landed cleanly, but the channel-level failure classification is still incomplete: a generic `analytics_live` failure remains a `partial` result even though live is part of Phase 3 channel-level ingestion. I did not re-run tests locally because shell execution in this session failed at sandbox startup; this review is source/diff based.
