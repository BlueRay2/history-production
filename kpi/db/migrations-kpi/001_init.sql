-- Migration 001 — KPI metrics vault initial schema
-- Source: ADR 0002 + consensus-metrics-vault-2026-04-26
-- Applied via: python -m app.db_kpi migrate
--
-- This migration is INTENTIONALLY in a separate folder (`migrations-kpi/`)
-- from the legacy `migrations/` to avoid accidental cross-contamination
-- with `dashboard-kpi.sqlite`. New DB lives at `state/kpi.sqlite`.
--
-- Note: no BEGIN/COMMIT — transaction managed by app/db_kpi.py atomic with
-- schema_migrations bookkeeping (Codex r1 atomicity finding from ADR 0001
-- carried forward).
--
-- Temporal naming convention (Codex r1 LOW noted naming drift):
--   - `*_at`          — internal Python-generated UTC ISO timestamps (microsecond precision)
--                       Examples: `created_at`, `started_at`, `finished_at`, `observed_on`
--                       (`observed_on` carries legacy ADR 0001 name; semantically equivalent to *_at)
--   - `*_time`        — verbatim YouTube API field names mirrored 1:1 (intentional)
--                       Examples: `start_time`, `end_time`, `create_time` from Reporting API
--   - `*_utc`         — date-only fields (no time component) explicitly tied to UTC date
--                       Examples: `date_utc`
--   - `scheduled_for` — domain semantic (the planned time, not actual)
-- This naming preserves close-mapping to YouTube API source and is intentional, not drift.

-- Schema versioning (same pattern as ADR 0001 to preserve operator muscle memory)
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    sha256     TEXT NOT NULL
);

-- ===========================================================================
-- VIDEOS — registry with rich Data API metadata
-- ===========================================================================
CREATE TABLE videos (
    video_id              TEXT PRIMARY KEY,
    title                 TEXT,
    published_at          TEXT,
    channel_id            TEXT,
    duration_s            INTEGER,
    privacy_status        TEXT CHECK (privacy_status IS NULL OR
        privacy_status IN ('public', 'unlisted', 'private')),
    upload_status         TEXT CHECK (upload_status IS NULL OR
        upload_status IN ('processed', 'uploaded', 'rejected', 'failed', 'deleted')),
    category_id           TEXT,
    tags_json             TEXT,                    -- JSON array of tags as TEXT
    default_lang          TEXT,
    default_audio_lang    TEXT,
    is_short              INTEGER NOT NULL DEFAULT 0 CHECK (is_short IN (0, 1)),
    made_for_kids         INTEGER CHECK (made_for_kids IS NULL OR made_for_kids IN (0, 1)),
    live_broadcast_content TEXT CHECK (live_broadcast_content IS NULL OR
        live_broadcast_content IN ('none', 'live', 'upcoming')),
    created_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- ===========================================================================
-- INGESTION RUNS — audit trail for every ingest call
-- ===========================================================================
CREATE TABLE ingestion_runs (
    run_id        TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
        -- 'data_api' | 'analytics_api' | 'reporting_api'
        -- | 'nightly_orchestrator' | 'backfill' | 'monitoring' | 'reporting_cards' (legacy)
    source_detail TEXT,
        -- e.g. 'analytics_api:per_video', 'reporting_api:channel_cards_a1'
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    status        TEXT NOT NULL CHECK (status IN (
        'running', 'ok', 'partial',
        'api_failure', 'db_failure', 'quota_exhausted',
        'auth_failed', 'schema_drift'
    )),
    rows_written  INTEGER NOT NULL DEFAULT 0,
    quota_units   INTEGER NOT NULL DEFAULT 0,
    error_text    TEXT,
    scheduled_for TEXT,
    CHECK (source IN (
        'data_api', 'analytics_api', 'reporting_api',
        'nightly_orchestrator', 'backfill', 'monitoring',
        'reporting_cards'  -- legacy compatibility during 3-day verification window
    ))
);

CREATE INDEX idx_ingestion_runs_recent ON ingestion_runs(started_at DESC);
CREATE INDEX idx_ingestion_runs_source_status ON ingestion_runs(source, status, started_at DESC);

-- ===========================================================================
-- CHANNEL SNAPSHOTS — flexible wide-schema (key/value with dimensions)
-- ===========================================================================
CREATE TABLE channel_snapshots (
    metric_key    TEXT NOT NULL,
        -- e.g. 'views', 'estimatedMinutesWatched', 'subscribersGained', 'cardImpressions'
    dimension_key TEXT NOT NULL DEFAULT '',
        -- '' (no breakdown) | 'country=RU' | 'deviceType=MOBILE' | 'trafficSource=BROWSE' | 'subscribedStatus=SUBSCRIBED' | etc.
        -- multi-dimension encoded as 'dim1=val1|dim2=val2'
    grain         TEXT NOT NULL,
        -- 'day' | 'week' | 'month' | 'lifetime'
    window_start  TEXT NOT NULL,           -- YYYY-MM-DD
    window_end    TEXT NOT NULL,           -- YYYY-MM-DD
    observed_on   TEXT NOT NULL,           -- ISO 8601 microsecond UTC
    value_num     REAL,                    -- nullable when API returned no data
    run_id        TEXT NOT NULL,
    source        TEXT NOT NULL CHECK (source IN ('data_api', 'analytics_api', 'reporting_api')),
    PRIMARY KEY (metric_key, dimension_key, grain, window_start, window_end, observed_on),
    FOREIGN KEY (run_id) REFERENCES ingestion_runs(run_id)
);

CREATE INDEX idx_channel_snapshots_lookup
    ON channel_snapshots(metric_key, grain, window_end DESC, observed_on DESC);

CREATE INDEX idx_channel_snapshots_dim
    ON channel_snapshots(dimension_key, metric_key, window_end DESC);

-- ===========================================================================
-- VIDEO SNAPSHOTS — same shape as channel, keyed additionally by video_id
-- ===========================================================================
CREATE TABLE video_snapshots (
    video_id      TEXT NOT NULL,
    metric_key    TEXT NOT NULL,
    dimension_key TEXT NOT NULL DEFAULT '',
    grain         TEXT NOT NULL,
    window_start  TEXT NOT NULL,
    window_end    TEXT NOT NULL,
    observed_on   TEXT NOT NULL,
    value_num     REAL,
    run_id        TEXT NOT NULL,
    source        TEXT NOT NULL CHECK (source IN ('data_api', 'analytics_api', 'reporting_api')),
    PRIMARY KEY (video_id, metric_key, dimension_key, grain, window_start, window_end, observed_on),
    FOREIGN KEY (run_id) REFERENCES ingestion_runs(run_id),
    FOREIGN KEY (video_id) REFERENCES videos(video_id)
);

CREATE INDEX idx_video_snapshots_lookup
    ON video_snapshots(video_id, metric_key, grain, window_end DESC, observed_on DESC);

-- Codex r1 finding HIGH: cross-video queries (e.g. coverage/freshness) need
-- a leading-non-video-id index. Without this, "all videos with metric_key=views
-- in last 7 days" full-scans the table.
CREATE INDEX idx_video_snapshots_metric
    ON video_snapshots(metric_key, grain, window_end DESC, observed_on DESC, video_id);

-- ===========================================================================
-- VIDEO RETENTION POINTS — per-video retention curves (elapsedVideoTimeRatio)
-- ===========================================================================
CREATE TABLE video_retention_points (
    video_id                       TEXT NOT NULL,
    observed_on                    TEXT NOT NULL,
    window_start                   TEXT NOT NULL,
    window_end                     TEXT NOT NULL,
    elapsed_ratio                  REAL NOT NULL CHECK (elapsed_ratio >= 0.0 AND elapsed_ratio <= 1.0),
    audience_watch_ratio           REAL,
    relative_retention_performance REAL,
    run_id                         TEXT NOT NULL,
    PRIMARY KEY (video_id, observed_on, window_start, window_end, elapsed_ratio),
    FOREIGN KEY (video_id) REFERENCES videos(video_id),
    FOREIGN KEY (run_id) REFERENCES ingestion_runs(run_id)
);

-- ===========================================================================
-- REPORTING JOBS — Reporting API job registry
-- ===========================================================================
CREATE TABLE reporting_jobs (
    job_id          TEXT PRIMARY KEY,
    report_type_id  TEXT NOT NULL,                   -- e.g. 'channel_basic_a3'
    job_name        TEXT,
    created_at      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled'))
);

CREATE TABLE reporting_reports (
    report_id       TEXT PRIMARY KEY,                 -- YouTube-assigned
    job_id          TEXT NOT NULL,
    start_time      TEXT NOT NULL,
    end_time        TEXT NOT NULL,
    create_time     TEXT NOT NULL,                    -- when YouTube generated the report
    download_url    TEXT,
    download_status TEXT NOT NULL DEFAULT 'pending' CHECK (download_status IN
        ('pending', 'downloaded', 'parsed', 'failed')),
    downloaded_at   TEXT,
    parsed_at       TEXT,
    csv_local_path  TEXT,
    rows_parsed     INTEGER,
    error_text      TEXT,
    FOREIGN KEY (job_id) REFERENCES reporting_jobs(job_id)
);

CREATE INDEX idx_reporting_reports_lookup
    ON reporting_reports(job_id, end_time DESC, download_status);

-- ===========================================================================
-- QUOTA USAGE — per-API daily quota tracking
-- ===========================================================================
CREATE TABLE quota_usage (
    api_name      TEXT NOT NULL,                    -- 'data_api_v3' | 'analytics_api_v2' | 'reporting_api_v1'
    date_utc      TEXT NOT NULL,                    -- YYYY-MM-DD
    units_used    INTEGER NOT NULL DEFAULT 0,
    request_count INTEGER NOT NULL DEFAULT 0,
    last_updated  TEXT NOT NULL,
    PRIMARY KEY (api_name, date_utc)
);

-- ===========================================================================
-- SCHEMA DRIFT LOG — detect YouTube API surface changes
-- (Gemini r1 finding F4: surrogate id PK + acknowledged_at columns)
-- ===========================================================================
CREATE TABLE schema_drift_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at     TEXT NOT NULL,
    source          TEXT NOT NULL,                   -- 'analytics_api' | 'reporting_api'
    drift_type      TEXT NOT NULL,
        -- 'metric_added' | 'metric_removed' | 'dimension_added'
        -- | 'report_type_added' | 'report_type_deprecated'
    identifier      TEXT NOT NULL,                   -- metric_key / report_type_id
    notes           TEXT,
    acknowledged_at TEXT,                            -- NULL = unacknowledged; set via /schema-drift/{id}/ack
    acknowledged_by TEXT,
    UNIQUE (detected_at, source, drift_type, identifier)
);

-- Partial index — only un-acknowledged rows for fast "what needs attention" query
CREATE INDEX idx_schema_drift_unack
    ON schema_drift_log(acknowledged_at)
    WHERE acknowledged_at IS NULL;
