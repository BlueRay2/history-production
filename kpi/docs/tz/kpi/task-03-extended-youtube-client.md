# task-03 — Extended YouTubeClient with full API surface coverage

**Status:** `pending`
**Dep:** task-01 (schema must accept all metric/dimension combos)
**Risk:** High (any single misconfigured request multiplies into thousands of failed daily calls)

## Scope

Extend the existing `kpi/ingest/youtube_client.py` (or create new `kpi/ingest/youtube_full_client.py` if cleaner) to expose typed methods for **every** API surface we will ingest. Reuse existing OAuth + creds loading.

## Required methods

### Data API v3 (`youtubeData.googleapis.com`)
- `get_channel_metadata()` — `channels.list(mine=True, part=...)` — returns dict with all stats fields + branding + topics
- `list_uploads(playlist_id, page_token=None)` — paginate uploads playlist, return all video_ids
- `get_videos_metadata(video_ids: list)` — `videos.list(id=...,part=snippet,contentDetails,statistics,topicDetails,status)` — chunks of 50 IDs

### Analytics API v2 (`youtubeAnalytics.googleapis.com`) — channel-level
- `analytics_channel_basic(start, end, dimensions=None)` — pulls all core metrics with optional dimension breakdown
  - Default dimensions=`day` for daily granularity
  - Configurable dimension lists for per-call breakdown by `country`, `deviceType`, `insightTrafficSourceType`, `insightPlaybackLocationType`, `sharingService`, `subscribedStatus`, `youtubeProduct`, `creatorContentType` (Shorts vs Long)
- `analytics_demographics(start, end)` — `dimensions=ageGroup,gender; metrics=viewerPercentage`
- `analytics_geography(start, end, breakdown='country')` — country split
- `analytics_traffic_sources(start, end, detail=False)` — type or type+detail
- `analytics_playback_locations(start, end)`
- `analytics_devices_os(start, end)`
- `analytics_sharing_services(start, end)`
- `analytics_live(start, end)` — averageConcurrentViewers, peakConcurrentViewers (returns empty if no live streams)
- `analytics_playlist(playlist_id, start, end)` — playlistViews, playlistEstimatedMinutesWatched, playlistSaves, etc.

### Analytics API v2 — per-video
- `analytics_video_basic(video_id, start, end)` — all per-video metrics
- `analytics_video_retention(video_id, start, end)` — `dimensions=elapsedVideoTimeRatio; metrics=audienceWatchRatio,relativeRetentionPerformance`
- `analytics_video_traffic_sources(video_id, start, end, detail=False)`
- `analytics_video_devices(video_id, start, end)`

### Reporting API v1 (`youtubereporting.googleapis.com`)
- `list_report_types()` — wraps `reportTypes.list(includeSystemManaged=True)`. Returns 20 active report types (per current API state; auto-discovers if YouTube adds new types later)
- `ensure_jobs(report_type_ids: list[str]) -> dict[str, str]` — returns mapping `report_type_id → job_id`. Idempotent: looks up existing jobs first, creates if missing
- `list_reports(job_id, since_iso=None, page_size=100)` — list reports for job; supports pagination
- `download_report(report_id, download_url, target_path)` — fetch CSV, persist to local path, return parsed row count
- `delete_job(job_id)` — admin op for cleanup

## Quota budgeting

- Each method MUST estimate quota cost upfront via constant table:
  ```python
  QUOTA_COST = {
    'channels.list': 1, 'videos.list': 1, 'playlistItems.list': 1,
    'youtubeAnalytics.reports.query': 1,  # but 4 if monetary scope used (we don't)
    'youtubereporting.jobs.list': 1, 'youtubereporting.jobs.create': 1,
    'youtubereporting.jobs.reports.list': 1,
    # CSV download not counted (HTTP GET to googleapis CDN)
  }
  ```
- Before each call, check daily quota in `quota_usage` table. If `units_used + cost > daily_budget`, raise `QuotaExhaustedError`. Default daily_budget = 9000 (100K hardcap minus 10% safety margin).
- After successful call, increment `quota_usage` atomically via `INSERT ... ON CONFLICT DO UPDATE`.

## Retry policy

- Transient (5xx, 408, 429 with `retry-after`): exponential backoff 1s/2s/4s/8s/16s, max 5 attempts
- Auth errors (401 after refresh, 403): fail-fast, classify in error_text as `auth_failed`
- 400 `Unknown identifier` for metrics: fail-fast, log to `schema_drift_log` as `metric_removed` (auto-detected), classify error as `schema_drift`
- Network errors: same as transient

## Schema drift detection

- After each successful Analytics call with default metric set, compare returned `columnHeaders` against expected list. If headers contain new metrics → log to `schema_drift_log` as `metric_added` (informational, not error).
- Daily Reporting `list_report_types` call → diff against `reporting_jobs.report_type_id` list. New report types → log `report_type_added` (informational).
- Deprecated report types in API response → log `report_type_deprecated`.

## Test plan

- vcrpy cassettes for each method: `tests/cassettes/youtube_client/{method_name}.yaml`
- Mock quota_usage table — verify pre-flight check works
- Schema drift unit test: feed known-old metric set, modified metric in response → assert log entry created
- Failure injection: force 429 response, verify exponential backoff respected via mock clock

## Acceptance criteria

- All listed methods callable, return parsed dicts (not raw HTTP responses)
- Quota budgeting enforced via pre-flight check
- Retry policy validated by failure injection tests
- Schema drift detection produces correct log entries
- vcrpy cassettes committed for all methods (committed sanitized — no real channel ID in cassette body, replaced with fixture)

## Review loop slots

- [ ] Codex round 1: pending
- [ ] Gemini round 1: pending
