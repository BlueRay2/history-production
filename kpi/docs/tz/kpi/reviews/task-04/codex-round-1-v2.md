# Round 1 Review — task-04-nightly-ingest-job
**Reviewer:** Codex GPT-5.5 (xhigh)
**Verdict:** REQUEST_CHANGES

## Spec coverage
The implementation covers the requested 7-phase shape: flocked pre-flight, video registry refresh, channel Analytics pulls, per-video Analytics pulls, Reporting CSV ingest, schema drift sync, and orchestrator close. Idempotent append-only snapshot writes are present, and Gemini r1 fixes for malformed `observed_on` suffixes, preflight quota skip, Telegram alerts on normal non-`ok` closes, and most bulk-write batching are directionally sound.

Remaining spec gaps are around correctness of Reporting API CSV dimensional data, channel-level failure classification, crash recovery for downloaded-but-unparsed reports, incomplete schema-drift job creation error handling, db-failure alerting, and the retention window not using the requested last full week start.

## Findings
- [HIGH] kpi/ingest/nightly.py:820 — `_parse_and_upsert_reporting_csv` appears to treat every non-`date` / non-`video_id` CSV column as a metric. YouTube Reporting API reports commonly include dimension columns such as country, device, playback location, traffic source, subscribed status, and similar string fields. Those will be inserted as metric keys with `value_num=NULL`, while the actual dimension context is lost, corrupting a core data source. Suggested fix: classify CSV columns into dimensions vs metrics, encode dimension columns into `dimension_key`, and only emit snapshot rows for numeric metric columns.

- [MEDIUM] kpi/ingest/nightly.py:1215 — Channel-level `SchemaDriftError` and generic exceptions inside `_channel_pulls` are downgraded into `result.failures`, allowing the orchestrator to finish as `partial`. The spec defines `partial` for per-video failures with channel-level success, while channel-level failure should produce `api_failure` or another explicit non-green terminal status. Suggested fix: make all Phase 3 channel call failures abort the orchestrator, except truly intentional empty-row responses.

- [MEDIUM] kpi/ingest/nightly.py:682 — Reporting high-water mark includes `download_status='downloaded'` when calculating `MAX(create_time)`. If the process crashes after marking a report downloaded but before parsing it, the next run can skip that report forever because it is counted as already processed. Suggested fix: retry existing `downloaded` rows before listing new reports, or compute the list high-water mark from `parsed` only.

- [MEDIUM] kpi/ingest/nightly.py:932 — Gemini’s schema-drift auto-create fix is incomplete because `client.ensure_jobs(added, conn=conn)` swallows non-quota exceptions and returns success from `_sync_schema_drift`. A failed job creation can therefore leave the orchestrator `ok` with only a warning log. Suggested fix: propagate the failure or return it so Phase 7 marks the run non-`ok` and alerts.

- [MEDIUM] kpi/ingest/nightly.py:1132 — The outer `db_failure` path updates the orchestrator row and re-raises, but does not call `_send_telegram_alert`. The status table requires a red alert for `db_failure`. Suggested fix: best-effort send an alert in the outer exception handler after or around the `_close_run(..., status="db_failure")` attempt.

- [LOW] kpi/ingest/nightly.py:1345 — Per-video retention uses `target_date - timedelta(days=7)` as the start date, but the spec asks for `last_full_week_start`. This is a rolling 7-day window, not a full-week boundary. Suggested fix: compute and document the project’s week convention, then use that boundary for retention pulls.

## Observations (non-blocking)
- The flock implementation satisfies the silent concurrent-exit requirement.
- The PK suffix fix keeps the timestamp parseable by `julianday()`, and the new regression test pins that behavior.
- The injected fake client keeps nightly tests fast, but it currently under-represents Reporting API dimension-heavy CSVs and channel-level API failure semantics.
