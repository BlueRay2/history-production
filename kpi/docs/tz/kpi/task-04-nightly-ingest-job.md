# task-04 — Comprehensive nightly ingest job

**Status:** `pending`
**Dep:** task-01 (schema), task-02 (legacy gone), task-03 (extended client)
**Risk:** High (the workhorse — drives daily data accumulation; partial failures must be classified, not propagate)

## Scope

Implement `kpi/ingest/nightly.py` orchestrating one full nightly pull cycle. Entry point `python -m ingest.nightly [--target-date YYYY-MM-DD] [--dry-run]`. Default target_date = `today_utc - 2` (Analytics API has 2-day lag for finalized data).

## Per-cycle execution plan

For each nightly run, in order:

### 1. Pre-flight
- Acquire flock on `state/kpi-ingest.lock` (NB nonblocking — bail with rc=0 if another run active)
- Open new ingestion_run row with `source='nightly_orchestrator'`
- Verify quota_usage for today not already exhausted; raise QuotaExhaustedError if so

### 2. Refresh video registry (Data API v3)
- `list_uploads(uploads_playlist_id)` → all video_ids
- `get_videos_metadata(video_ids)` in batches of 50
- UPSERT into `videos` table (update title/published_at/privacy_status/category/tags/duration; preserve created_at)
- Detect new videos since last run; log to ingestion_runs as a sub-run with source `data_api`

### 3. Channel-level Analytics pull
For each call below, open sub-run with source `analytics_api`, source_detail describing the call:
- `analytics_channel_basic(target_date, target_date)` — daily core metrics, dimensions=`day`
- `analytics_channel_basic(target_date, target_date, dimensions='deviceType')` — device split
- `analytics_channel_basic(target_date, target_date, dimensions='insightTrafficSourceType')` — traffic
- `analytics_channel_basic(target_date, target_date, dimensions='insightPlaybackLocationType')` — playback location
- `analytics_channel_basic(target_date, target_date, dimensions='country')` — geography
- `analytics_channel_basic(target_date, target_date, dimensions='sharingService')` — sharing
- `analytics_channel_basic(target_date, target_date, dimensions='subscribedStatus')` — subscriber vs not
- `analytics_demographics(target_date, target_date)` — age × gender (auto-grouped by Analytics API)
- `analytics_live(target_date, target_date)` — concurrent viewers (skip insert if rows empty)

Each call's response: rows × column_headers. Map to `channel_snapshots` rows with `dimension_key` encoding the dimension+value (e.g. `country=RU`, `deviceType=MOBILE`, default `''` for no dimension).

### 4. Per-video Analytics pull
For each video in registry where `published_at >= target_date - 90` (data freshness window):
- `analytics_video_basic(video_id, target_date, target_date)` — all per-video metrics
- `analytics_video_retention(video_id, last_full_week_start, target_date)` — retention curve over recent week
- `analytics_video_traffic_sources(video_id, target_date, target_date)` — per-video traffic split

Per-video failures (sparse data, privacy threshold, single 4xx) MUST NOT abort the whole run. Each per-video sub-run records its own status; nightly orchestrator returns `partial` if any per-video failed but channel-level succeeded.

### 5. Reporting API CSV ingest
- For each registered job in `reporting_jobs`:
  - `list_reports(job_id, since_iso=last_processed)` — get new reports since last successful download
  - For each new report: download CSV to `state/kpi-reporting-csv/{report_type_id}/{report_id}.csv`, parse, INSERT into `channel_snapshots` (or `video_snapshots` if report has video_id column) with `source='reporting_api'`
  - UPDATE `reporting_reports` row to `download_status='parsed'`
- Reports with `download_status='downloaded'` but failed parse → status `failed`, error_text recorded

### 6. Schema drift sync
- Call `list_report_types()` → diff against `reporting_jobs.report_type_id`. Auto-create job for new types (log to `schema_drift_log`); soft-disable jobs for deprecated types (status='disabled', do not fetch reports anymore).

### 7. Close orchestrator run
- Aggregate sub-run results → orchestrator status (`ok` if all green, `partial` if any non-fatal, `quota_exhausted` if hit cap, `api_failure` if channel-level failed)
- UPDATE ingestion_run row, release flock
- Telegram alert if status != `ok`

## Status semantics

| Orchestrator status | Meaning | Telegram alert |
|---|---|---|
| `ok` | all sub-runs successful | none |
| `partial` | some per-video sub-run failed, channel-level OK | yellow ⚠️ |
| `api_failure` | channel-level call failed entirely | red 🔴 |
| `quota_exhausted` | hit daily quota cap mid-run | orange 🟠 |
| `db_failure` | SQLite write failed | red 🔴 |

## Idempotency

- Same target_date re-run produces append-only rows with new `observed_on` (microsecond-precision dodges PK collision)
- Latest-wins resolution via `julianday(observed_on)` in monitoring queries
- No data loss if run twice on same day; only DB grows

## Test plan

- vcrpy cassettes for full mocked nightly run with predictable channel state
- Failure injection: per-video 403 → orchestrator returns `partial`, channel data persists
- Quota injection: pre-set quota_usage to 9000, run → orchestrator returns `quota_exhausted` after first call
- Concurrency: launch two nightly runs simultaneously → second exits 0 silently (flock test)

## Acceptance criteria

- One full nightly run on real channel completes < 5 minutes
- All channel-level dimensions ingested as separate rows with correct `dimension_key`
- Per-video metrics ingested for all videos with `published_at >= target_date - 90`
- Schema drift events appear in `schema_drift_log` when API surface changes
- Telegram alert fires on non-`ok` orchestrator status

## Review loop slots

- [ ] Codex round 1: pending
- [ ] Gemini round 1: pending
