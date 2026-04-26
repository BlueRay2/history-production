# task-05 — 60-day backfill bootstrap

**Status:** `pending`
**Dep:** task-03 (extended client), task-01 (schema)
**Risk:** Medium (one-shot operation; quota-pacing critical to not exhaust daily 10K)

## Scope

One-shot script `python -m ingest.backfill --days 60` that pulls 60 days of historical data on first deployment. After successful completion, leaves a sentinel file `state/kpi-backfill-complete.flag` so subsequent invocations are no-ops unless `--force` passed.

## Why 60 days specifically (per Yaroslav D4)

Channel `Cities Evolution` was created < 2 months ago. 60-day window covers full channel history. Larger window (e.g. 365) wastes quota on empty days; smaller (e.g. 30) misses earliest videos.

## Per-day ingest plan

For each day from `today_utc - 60` to `today_utc - 2` (inclusive):
- Run the same set of Analytics calls as task-04 step 3 (channel-level dimensions) BUT with `start=end=that_day`
- Per-video calls for videos that existed on that day (`published_at <= that_day`)
- All rows tagged with `observed_on=now_utc()` (= when we backfilled, not synthetic)

## Reporting API consideration

Reporting API does NOT support arbitrary historical backfill — it only delivers reports starting from when job was created (with ~30-day lookback for channel reports created today). So:

- On first backfill run, **register all 14 active channel report types** as jobs immediately (creates job → reports begin generating ~24h later, with backfill ~30d covered automatically by YouTube)
- Backfill script does NOT block on Reporting API readiness; it returns success after Analytics API portion done
- Subsequent nightly runs (task-04) pick up Reporting CSVs as they appear

## Quota pacing

60 days × 8 channel-level calls + ~30 videos × 3 per-video calls × videos that existed each day ≈ ~3000-5000 quota units total. Daily cap 10K, so backfill fits in one day comfortably IF nightly hasn't run yet.

Pacing rule: pause 1 second between calls (~5000 calls / 1s = 1.4 hours wall-clock — acceptable for one-shot bootstrap). If quota_usage approaches 8500 mid-backfill, **pause and persist progress** to `state/kpi-backfill-cursor.json` with last-completed date, exit rc=2 with "resume tomorrow". Re-run resumes from cursor.

## Idempotency

- Sentinel flag prevents accidental re-runs
- `--force` flag bypasses sentinel for explicit re-runs (e.g., schema migration requires re-pull)
- Cursor file enables multi-day resumption if quota interrupts

## Test plan

- Mocked Analytics API with synthetic 60-day window of data, verify all rows land
- Quota interrupt at day 30 → cursor file written, exit rc=2; resume → cursor honored, continues from day 30
- Sentinel flag prevents accidental second full backfill
- vcrpy cassette for full 60-day backfill happy path

## Acceptance criteria

- 60-day backfill completes in < 2 hours wall-clock when run on quiet day (no nightly cron yet)
- All 14 Reporting API jobs registered idempotently
- Sentinel flag prevents accidental re-run
- Cursor-based resumption works on quota interrupt
- Telegram broadcast on completion: `✅ kpi backfill 60d ok — N rows, M quota units used`

## Review loop slots

- [ ] Codex round 1: pending
- [ ] Gemini round 1: pending
