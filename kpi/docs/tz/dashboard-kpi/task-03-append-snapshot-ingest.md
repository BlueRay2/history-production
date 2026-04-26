# task-03 — Append-snapshot ingest

**Status:** `pending`
**Dep:** 01, 02
**Risk:** High

## Scope

1. `ingest/jobs.py`:
   - `run_daily_refresh(target_date: date)` — main entry point called by task-08 cron.
   - Opens `ingestion_runs` row → pulls channel + video metrics for `[target_date - 45d, target_date]` → writes to `channel_metric_snapshots` / `video_metric_snapshots` / `video_retention_points` → closes run row.
2. **Append semantics:** PK is `(entity, metric, window, observed_on)`. Re-pulls for same window emit new `observed_on` rows, never mutate. Dashboard reads latest `observed_on` per entity/metric/window.
3. **Preliminary-flag overwrite:** rows where `observed_on - window_end < 3` get `preliminary=1`. Next run's pull for same window downgrades prior preliminary rows (sets `preliminary=0`) if numeric value stable OR adds new authoritative row if changed.
4. **First-run 45-day backfill:** `ingest/first_run.py` — one-shot script; checks if `channel_metric_snapshots` has <7 rows → pulls 45 days; otherwise no-op.
5. `app/repositories/metrics.py`:
   - `latest_snapshot(entity_id, metric, window_start, window_end) -> SnapshotRow` (returns row with max `observed_on`).
   - `write_snapshot_batch(rows: list[SnapshotRow])` — single-txn batch insert with `INSERT OR IGNORE`.

## Failure handling

- YouTube API 429 quota → `ingestion_runs.status='quota_exhausted'` + Telegram alert (Ярослав DM) + cron rescheduled next day.
- Network timeout → retry 3× exponential via `app/lib/retry.py`; then fail run.
- Partial success: row-level commits inside a single metric group (channel-level metrics commit independently of per-video).

## Test plan

- `tests/test_snapshot_append.py`:
  - Re-run same window twice → no destructive overwrite; 2 distinct `observed_on` rows exist.
  - `latest_snapshot` returns the newer row.
  - Preliminary flag downgrade when stable value.
- `tests/test_first_run_backfill.py`: on empty DB, first-run script pulls 45 days (mocked via cassettes).
- `tests/test_quota_exhaustion.py`: simulated 429 → run row marked `quota_exhausted`.

## Files touched

- `ingest/jobs.py`, `ingest/first_run.py` (new)
- `app/repositories/__init__.py`, `app/repositories/metrics.py` (new)
- `tests/test_snapshot_append.py`, `tests/test_first_run_backfill.py`, `tests/test_quota_exhaustion.py` (new)

## Review loop

- [ ] Codex round-1 → `reviews/task-03/codex-round-1.md`
- [ ] Gemini round-1 → `reviews/task-03/gemini-round-1.md` (F-01, F-05 focus)
- [ ] `ready-to-merge` | `ready-to-merge (gemini-degraded)`
- [ ] `merged`
