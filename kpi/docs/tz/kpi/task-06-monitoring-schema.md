# task-06 — Monitoring schema + derived views

**Status:** `pending`
**Dep:** task-01 (base schema), task-04 (so we have populating data to measure)
**Risk:** Low (read-only views; schema refactor low-impact)

## Scope

Extend schema with **derived views** + **freshness materialization** that the monitoring UI (task-07) will read. Goal: UI queries are O(N) on small materialized tables, not O(M) over multi-million-row snapshots.

## New artefacts

### 1. View `v_last_run_per_source`
```sql
CREATE VIEW v_last_run_per_source AS
SELECT source, source_detail,
       MAX(julianday(started_at)) AS last_started_jd,
       (SELECT status FROM ingestion_runs r2
         WHERE r2.source = ir.source AND r2.source_detail IS ir.source_detail
         ORDER BY julianday(r2.started_at) DESC LIMIT 1) AS last_status
FROM ingestion_runs ir
GROUP BY source, source_detail;
```
Shows the most recent run per (source, source_detail) tuple.

### 2. View `v_metric_freshness`
```sql
CREATE VIEW v_metric_freshness AS
WITH last_obs AS (
  SELECT metric_key, dimension_key, MAX(julianday(observed_on)) AS last_obs_jd
  FROM channel_snapshots GROUP BY metric_key, dimension_key
)
SELECT metric_key, dimension_key, last_obs_jd,
       (julianday('now') - last_obs_jd) AS days_since_last_obs
FROM last_obs;
```
For each (metric_key, dimension_key), how many days since we last saw a value. Drives the "freshness matrix" page.

### 3. View `v_video_coverage_7d`
```sql
CREATE VIEW v_video_coverage_7d AS
SELECT v.video_id, v.title,
       COUNT(DISTINCT vs.metric_key) AS metrics_pulled_7d,
       MAX(julianday(vs.observed_on)) AS last_pulled_jd
FROM videos v
LEFT JOIN video_snapshots vs ON v.video_id = vs.video_id
       AND julianday(vs.observed_on) >= julianday('now', '-7 days')
GROUP BY v.video_id, v.title;
```
Per-video metric coverage over last 7 days. Drives "video coverage matrix" page.

### 4. View `v_quota_today`
```sql
CREATE VIEW v_quota_today AS
SELECT api_name, units_used, request_count, last_updated
FROM quota_usage
WHERE date_utc = strftime('%Y-%m-%d', 'now');
```

### 5. Table `monitoring_pings` (heartbeat)
```sql
CREATE TABLE monitoring_pings (
  ping_at        TEXT PRIMARY KEY,
  status         TEXT NOT NULL CHECK (status IN ('ok', 'degraded', 'down')),
  details_json   TEXT,
  alert_sent     INTEGER NOT NULL DEFAULT 0
);
```
Cron-driven heartbeat that monitors itself: every hour, a separate cron job runs a check (last nightly was within 26h, no source has been failing >3 consecutive runs). Status written here. If `degraded` or `down` and `alert_sent=0`, fire Telegram alert and flip flag.

## Migration

`db/migrations-kpi/002_monitoring.sql` — additive, no breaking changes to task-01 schema.

## Test plan

- Unit tests for each view: seed snapshots, query view, assert correct freshness/coverage values
- monitoring_pings: insert degraded → assert alert_sent stays 0 until alert dispatched, then 1
- Migration idempotency

## Acceptance criteria

- All views return correct values for synthetic seed data
- `v_quota_today` correctly reads only today's row
- Hourly heartbeat cron creates monitoring_pings entries (registered in task-08)
- Alert deduplication via alert_sent flag works

## Review loop slots

- [ ] Codex round 1: pending
- [ ] Gemini round 1: pending
