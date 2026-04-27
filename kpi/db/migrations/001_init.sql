-- Migration 001: initial schema for KPI dashboard
-- Source: consensus-dashboard-kpi research/codex.md §2 + finding J-03 sparse-metric semantics
-- Ship: consensus-dashboard-kpi/verdict-round9.md
-- Applied via: python -m app.db migrate
--
-- Note: this file does NOT contain BEGIN/COMMIT. Transaction boundaries are
-- managed by app/db.py so that DDL + schema_migrations bookkeeping are atomic
-- (Codex round-1 review, finding [high] atomicity, 2026-04-21).

-- Schema versioning
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL,
    sha256     TEXT NOT NULL
);

-- YouTube video registry
CREATE TABLE videos (
    video_id      TEXT PRIMARY KEY,
    title         TEXT,
    published_at  TEXT,
    channel_id    TEXT,
    city_slug     TEXT,
    duration_s    INTEGER,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- Git-side project registry (one row per city folder in history-production)
CREATE TABLE projects (
    city_slug         TEXT PRIMARY KEY,
    first_commit_at   TEXT,
    canonical_path    TEXT,
    default_branch    TEXT,
    status            TEXT,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- City <-> video mapping with confidence + manual override
CREATE TABLE video_project_map (
    city_slug       TEXT NOT NULL,
    video_id        TEXT NOT NULL,
    confidence      REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    mapping_source  TEXT NOT NULL CHECK (mapping_source IN ('auto','manual')),
    active          INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0,1)),
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (city_slug, video_id),
    FOREIGN KEY (city_slug) REFERENCES projects(city_slug),
    FOREIGN KEY (video_id)  REFERENCES videos(video_id)
);

-- Every daily ingest run (for quota + failure audit)
CREATE TABLE ingestion_runs (
    run_id        TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    status        TEXT NOT NULL,
    quota_units   INTEGER,
    error_text    TEXT
);

-- Channel-level metric snapshots (append-only)
CREATE TABLE channel_metric_snapshots (
    metric_key    TEXT NOT NULL,
    grain         TEXT NOT NULL,
    window_start  TEXT NOT NULL,
    window_end    TEXT NOT NULL,
    observed_on   TEXT NOT NULL,
    value_num     REAL,
    run_id        TEXT NOT NULL,
    preliminary   INTEGER NOT NULL DEFAULT 0 CHECK (preliminary IN (0,1)),
    PRIMARY KEY (metric_key, grain, window_start, window_end, observed_on),
    FOREIGN KEY (run_id) REFERENCES ingestion_runs(run_id)
);

-- Per-video metric snapshots (append-only)
CREATE TABLE video_metric_snapshots (
    video_id      TEXT NOT NULL,
    metric_key    TEXT NOT NULL,
    grain         TEXT NOT NULL,
    window_start  TEXT NOT NULL,
    window_end    TEXT NOT NULL,
    observed_on   TEXT NOT NULL,
    value_num     REAL,
    run_id        TEXT NOT NULL,
    preliminary   INTEGER NOT NULL DEFAULT 0 CHECK (preliminary IN (0,1)),
    PRIMARY KEY (video_id, metric_key, grain, window_start, window_end, observed_on),
    FOREIGN KEY (video_id) REFERENCES videos(video_id),
    FOREIGN KEY (run_id)   REFERENCES ingestion_runs(run_id)
);

-- Per-video retention curve points
CREATE TABLE video_retention_points (
    video_id         TEXT NOT NULL,
    observed_on      TEXT NOT NULL,
    elapsed_seconds  REAL NOT NULL,
    retention_pct    REAL,
    run_id           TEXT NOT NULL,
    PRIMARY KEY (video_id, observed_on, elapsed_seconds),
    FOREIGN KEY (video_id) REFERENCES videos(video_id),
    FOREIGN KEY (run_id)   REFERENCES ingestion_runs(run_id)
);

-- Git events (commits interpreted as KPI milestones)
CREATE TABLE git_events (
    commit_sha    TEXT PRIMARY KEY,
    city_slug     TEXT,
    branch_name   TEXT,
    committed_at  TEXT NOT NULL,
    event_type    TEXT NOT NULL,
    event_value   TEXT,
    payload_json  TEXT,
    confidence    REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    FOREIGN KEY (city_slug) REFERENCES projects(city_slug)
);

-- Indexes for latest-snapshot reads
CREATE INDEX idx_channel_metric_latest
    ON channel_metric_snapshots(metric_key, window_end, observed_on DESC);

CREATE INDEX idx_video_metric_latest
    ON video_metric_snapshots(video_id, metric_key, window_end, observed_on DESC);

CREATE INDEX idx_git_events_city_type
    ON git_events(city_slug, event_type, committed_at);

CREATE INDEX idx_vpm_video_active
    ON video_project_map(video_id, active);

CREATE INDEX idx_vpm_city_active
    ON video_project_map(city_slug, active);
