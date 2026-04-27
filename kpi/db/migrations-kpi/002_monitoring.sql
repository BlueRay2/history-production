-- Migration 002 — Monitoring schema (task-06)
-- Additive views + monitoring_pings heartbeat table.
-- No breaking changes to migration 001 schema.
-- Applied via: python -m app.db_kpi migrate
--
-- All views use julianday() for time arithmetic since observed_on / started_at
-- are ISO-8601 strings with microsecond precision (consistent with task-04 fix
-- for PK collision suffix preserving valid ISO format).

-- ===========================================================================
-- VIEW v_last_run_per_source
-- Latest started_at + status per (source, source_detail). Drives the
-- "ingest health" page in task-07 — shows whether each sub-run is fresh.
-- Gemini r1 finding F2 (CT-D Vision review, applied here): use NOT
-- DISTINCT (IS) for nullable source_detail correlation rather than equality.
-- ===========================================================================
CREATE VIEW v_last_run_per_source AS
SELECT
    ir.source,
    ir.source_detail,
    MAX(julianday(ir.started_at))                                  AS last_started_jd,
    (SELECT r2.status
       FROM ingestion_runs r2
      WHERE r2.source = ir.source
        AND r2.source_detail IS ir.source_detail
      ORDER BY julianday(r2.started_at) DESC
      LIMIT 1)                                                     AS last_status,
    (SELECT r2.run_id
       FROM ingestion_runs r2
      WHERE r2.source = ir.source
        AND r2.source_detail IS ir.source_detail
      ORDER BY julianday(r2.started_at) DESC
      LIMIT 1)                                                     AS last_run_id,
    COUNT(*)                                                       AS total_runs
FROM ingestion_runs ir
GROUP BY ir.source, ir.source_detail;

-- ===========================================================================
-- VIEW v_metric_freshness
-- Days since each (metric_key, dimension_key) was last observed at the
-- channel level. Driver for the "freshness matrix" page.
-- ===========================================================================
CREATE VIEW v_metric_freshness AS
WITH last_obs AS (
    SELECT metric_key, dimension_key,
           MAX(julianday(observed_on)) AS last_obs_jd,
           COUNT(*)                    AS observation_count
    FROM channel_snapshots
    GROUP BY metric_key, dimension_key
)
SELECT metric_key,
       dimension_key,
       last_obs_jd,
       observation_count,
       (julianday('now') - last_obs_jd) AS days_since_last_obs
FROM last_obs;

-- ===========================================================================
-- VIEW v_video_coverage_7d
-- Per-video metric coverage over the last 7 days. Driver for the
-- "video coverage matrix" page. Uses LEFT JOIN so videos with zero
-- snapshots still appear (with metrics_pulled_7d = 0).
-- ===========================================================================
CREATE VIEW v_video_coverage_7d AS
SELECT
    v.video_id,
    v.title,
    v.published_at,
    COUNT(DISTINCT vs.metric_key)        AS metrics_pulled_7d,
    MAX(julianday(vs.observed_on))       AS last_pulled_jd,
    (julianday('now') - MAX(julianday(vs.observed_on))) AS days_since_last_pull
FROM videos v
LEFT JOIN video_snapshots vs
       ON v.video_id = vs.video_id
      AND julianday(vs.observed_on) >= julianday('now', '-7 days')
GROUP BY v.video_id, v.title, v.published_at;

-- ===========================================================================
-- VIEW v_quota_today
-- Today's UTC quota usage rolled up by api_name. Drives the
-- "quota usage" page.
-- ===========================================================================
CREATE VIEW v_quota_today AS
SELECT api_name,
       units_used,
       request_count,
       last_updated
FROM quota_usage
WHERE date_utc = strftime('%Y-%m-%d', 'now');

-- ===========================================================================
-- TABLE monitoring_pings
-- Cron-driven heartbeat: every hour a separate cron checks ingest health
-- (last nightly within 26h, no source failing 3+ consecutive runs, etc.)
-- and writes one row here. Telegram alert fires on first 'degraded' /
-- 'down' transition (alert_sent flag for dedup).
-- ===========================================================================
CREATE TABLE monitoring_pings (
    ping_at        TEXT NOT NULL,
    status         TEXT NOT NULL CHECK (status IN ('ok', 'degraded', 'down')),
    details_json   TEXT,
    alert_sent     INTEGER NOT NULL DEFAULT 0 CHECK (alert_sent IN (0, 1)),
    PRIMARY KEY (ping_at)
);

CREATE INDEX idx_monitoring_pings_recent
    ON monitoring_pings(ping_at DESC);

CREATE INDEX idx_monitoring_pings_alert_pending
    ON monitoring_pings(alert_sent, status)
    WHERE alert_sent = 0 AND status IN ('degraded', 'down');
