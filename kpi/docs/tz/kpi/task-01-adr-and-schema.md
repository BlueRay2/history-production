# task-01 — ADR + flexible schema for comprehensive metric storage

**Status:** `pending`
**Dep:** —
**Risk:** High (foundation for all other tasks; schema mistakes cascade)

## Scope

1. ADR `docs/adr/0002-kpi-metrics-vault.md` documenting the architectural shift from analytical KPI dashboard to comprehensive metric ingestor + monitoring UI. Reference `consensus-metrics-vault-2026-04-26/phase-1-research/` and explicitly enumerate locked decisions D1-D6 from README.md.
2. Raw SQL migration `db/migrations-kpi/001_init.sql` (note: separate migration tree from legacy `db/migrations/` to avoid conflict with retired `dashboard-kpi.sqlite`).
3. Reuse `schema_migrations(version TEXT PK, applied_at TEXT, sha256 TEXT)` table — same pattern as legacy.
4. New `app/db.py` connection helper pointing at `state/kpi.sqlite` (env override `KPI_DB`).
5. Idempotent migrator: `python -m app.db migrate`.

## Schema design — flexible wide-table key/value model

**Why key/value instead of dedicated columns per metric:**
- ~60 Analytics API metrics, but only ~50% are non-zero on small channels — adding 60 columns wastes space.
- YouTube can add/deprecate metrics without notice. Wide schema lets us record any new metric without migration.
- DS analysis later will pivot/unstack as needed; SQLite handles 5M rows of (entity, metric_key, value) just fine with proper indexes.

**Tables (migration 001):**

```sql
-- Channel-level snapshots (one channel — current account)
CREATE TABLE channel_snapshots (
  metric_key   TEXT NOT NULL,                    -- e.g. 'views', 'estimatedMinutesWatched', 'subscribersGained'
  dimension_key TEXT NOT NULL DEFAULT '',         -- e.g. '', 'country=RU', 'device=MOBILE', 'trafficSource=BROWSE'
  grain        TEXT NOT NULL,                    -- 'day' | 'week' | 'month' | 'lifetime'
  window_start TEXT NOT NULL,                    -- YYYY-MM-DD
  window_end   TEXT NOT NULL,                    -- YYYY-MM-DD
  observed_on  TEXT NOT NULL,                    -- ISO 8601 microsecond UTC ('2026-04-26T18:30:01.123456Z')
  value_num    REAL,                             -- numeric metric value (NULL if missing)
  run_id       TEXT NOT NULL,                    -- FK ingestion_runs
  source       TEXT NOT NULL CHECK (source IN ('data_api', 'analytics_api', 'reporting_api')),
  PRIMARY KEY (metric_key, dimension_key, grain, window_start, window_end, observed_on),
  FOREIGN KEY (run_id) REFERENCES ingestion_runs(run_id)
);

CREATE INDEX idx_channel_snapshots_lookup
  ON channel_snapshots(metric_key, grain, window_end DESC, observed_on DESC);

CREATE INDEX idx_channel_snapshots_dim
  ON channel_snapshots(dimension_key, metric_key, window_end DESC);

-- Per-video snapshots
CREATE TABLE video_snapshots (
  video_id     TEXT NOT NULL,
  metric_key   TEXT NOT NULL,
  dimension_key TEXT NOT NULL DEFAULT '',
  grain        TEXT NOT NULL,
  window_start TEXT NOT NULL,
  window_end   TEXT NOT NULL,
  observed_on  TEXT NOT NULL,
  value_num    REAL,
  run_id       TEXT NOT NULL,
  source       TEXT NOT NULL CHECK (source IN ('data_api', 'analytics_api', 'reporting_api')),
  PRIMARY KEY (video_id, metric_key, dimension_key, grain, window_start, window_end, observed_on),
  FOREIGN KEY (run_id) REFERENCES ingestion_runs(run_id),
  FOREIGN KEY (video_id) REFERENCES videos(video_id)
);

CREATE INDEX idx_video_snapshots_lookup
  ON video_snapshots(video_id, metric_key, grain, window_end DESC, observed_on DESC);

-- Video registry (similar to legacy)
CREATE TABLE videos (
  video_id      TEXT PRIMARY KEY,
  title         TEXT,
  published_at  TEXT,
  channel_id    TEXT,
  duration_s    INTEGER,
  privacy_status TEXT,                           -- 'public' | 'unlisted' | 'private'
  upload_status TEXT,                            -- 'processed' | 'uploaded' | 'rejected'
  category_id   TEXT,
  tags_json     TEXT,                            -- JSON array of tags
  default_lang  TEXT,
  default_audio_lang TEXT,
  is_short      INTEGER NOT NULL DEFAULT 0,      -- 1 if duration ≤ 60s
  made_for_kids INTEGER,
  live_broadcast_content TEXT,                    -- 'none' | 'live' | 'upcoming'
  created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- Retention curves (per-video, per-elapsed-position)
CREATE TABLE video_retention_points (
  video_id        TEXT NOT NULL,
  observed_on     TEXT NOT NULL,
  window_start    TEXT NOT NULL,
  window_end      TEXT NOT NULL,
  elapsed_ratio   REAL NOT NULL,                  -- 0.0 to 1.0 (Analytics API uses elapsedVideoTimeRatio dimension)
  audience_watch_ratio REAL,
  relative_retention_performance REAL,
  run_id          TEXT NOT NULL,
  PRIMARY KEY (video_id, observed_on, window_start, window_end, elapsed_ratio),
  FOREIGN KEY (video_id) REFERENCES videos(video_id),
  FOREIGN KEY (run_id) REFERENCES ingestion_runs(run_id)
);

-- Reporting API CSV registry — track which jobs we have, which reports downloaded
CREATE TABLE reporting_jobs (
  job_id          TEXT PRIMARY KEY,
  report_type_id  TEXT NOT NULL,                  -- e.g. 'channel_basic_a3'
  job_name        TEXT,
  created_at      TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'active'  -- 'active' | 'disabled'
);

CREATE TABLE reporting_reports (
  report_id       TEXT PRIMARY KEY,                -- YouTube-assigned report ID
  job_id          TEXT NOT NULL,
  start_time      TEXT NOT NULL,                   -- window covered
  end_time        TEXT NOT NULL,
  create_time     TEXT NOT NULL,                   -- when YouTube generated
  download_url    TEXT,
  download_status TEXT NOT NULL DEFAULT 'pending', -- 'pending' | 'downloaded' | 'parsed' | 'failed'
  downloaded_at   TEXT,
  parsed_at       TEXT,
  csv_local_path  TEXT,                             -- /home/aiagent/assistant/state/kpi-reporting-csv/{job}/{report_id}.csv
  rows_parsed     INTEGER,
  error_text      TEXT,
  FOREIGN KEY (job_id) REFERENCES reporting_jobs(job_id)
);

CREATE INDEX idx_reporting_reports_lookup
  ON reporting_reports(job_id, end_time DESC, download_status);

-- Ingestion run audit (extended from legacy)
CREATE TABLE ingestion_runs (
  run_id        TEXT PRIMARY KEY,
  source        TEXT NOT NULL,                     -- 'data_api' | 'analytics_api' | 'reporting_api' | 'backfill' | 'monitoring'
  source_detail TEXT,                              -- e.g. 'analytics_api:per_video', 'reporting_api:channel_cards_a1'
  started_at    TEXT NOT NULL,
  finished_at   TEXT,
  status        TEXT NOT NULL,                     -- 'running' | 'ok' | 'partial' | 'api_failure' | 'db_failure' | 'quota_exhausted'
  rows_written  INTEGER NOT NULL DEFAULT 0,
  quota_units   INTEGER NOT NULL DEFAULT 0,
  error_text    TEXT,
  scheduled_for TEXT                               -- if scheduled by cron, the planned run timestamp
);

CREATE INDEX idx_ingestion_runs_recent
  ON ingestion_runs(started_at DESC);

CREATE INDEX idx_ingestion_runs_source_status
  ON ingestion_runs(source, status, started_at DESC);

-- Quota usage tracking (YouTube API daily 10K units default)
CREATE TABLE quota_usage (
  api_name     TEXT NOT NULL,                       -- 'data_api_v3' | 'analytics_api_v2' | 'reporting_api_v1'
  date_utc     TEXT NOT NULL,                       -- YYYY-MM-DD
  units_used   INTEGER NOT NULL DEFAULT 0,
  request_count INTEGER NOT NULL DEFAULT 0,
  last_updated TEXT NOT NULL,
  PRIMARY KEY (api_name, date_utc)
);

-- Schema drift detector — capture API surface changes
CREATE TABLE schema_drift_log (
  detected_at    TEXT NOT NULL,
  source         TEXT NOT NULL,                     -- which API
  drift_type     TEXT NOT NULL,                     -- 'metric_added' | 'metric_removed' | 'dimension_added' | 'report_type_added' | 'report_type_deprecated'
  identifier     TEXT NOT NULL,                     -- metric_key / report_type_id
  notes          TEXT,
  PRIMARY KEY (detected_at, source, drift_type, identifier)
);
```

## Observed_on convention

**Microsecond UTC ISO 8601** (`%Y-%m-%dT%H:%M:%fZ`) — same as legacy after the F-04 / B-12 fix in `dashboard-kpi`. Required for `julianday()` ordering and to dodge same-second PK collisions.

## Indexes — query patterns to support

- "Latest value for a metric in a window" — `idx_channel_snapshots_lookup` covers
- "All metrics for a video over time range" — `idx_video_snapshots_lookup` covers
- "Failed runs in last 24h by source" — `idx_ingestion_runs_source_status` covers
- "Recent runs in monitoring UI" — `idx_ingestion_runs_recent` covers
- "Reports pending download" — `idx_reporting_reports_lookup` covers

## Test plan

- `tests/test_migrations_kpi.py`: fresh DB → `migrate` → re-run is no-op; hash mismatch errors.
- `tests/test_schema_kpi.py`: PK constraints, FK constraints (PRAGMA foreign_keys=ON), CHECK constraint on `source`.
- Constraint tests: dimension_key DEFAULT '' works; `is_short` boolean range; `published_at` ISO format check via Python preprocessing.

## Acceptance criteria

- ADR file committed; references locked decisions D1-D6 verbatim
- Migration applies cleanly to fresh DB
- All indexes present after migration
- All FKs validated by integration test
- Reporting jobs registry pre-populated with all 14 active channel report types from listing API on first migration

## Review loop slots

- [ ] Codex round 1: pending
- [ ] Gemini round 1: pending
