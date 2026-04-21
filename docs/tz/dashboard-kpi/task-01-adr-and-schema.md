# task-01 — ADR + DB schema

**Status:** `pending`
**Dep:** —
**Risk:** Medium

## Scope

1. ADR `docs/adr/0001-kpi-dashboard.md` locking stack choice (Flask + Jinja + HTMX + Chart.js + SQLite) with rationale referencing `consensus-dashboard-kpi/debate/round-2.md`.
2. Raw SQL migrations under `db/migrations/001_init.sql` (and numbered subsequent).
3. `schema_migrations(version TEXT PK, applied_at TEXT)` table.
4. `app/db.py` thin connection helper (`sqlite3` std-lib, WAL journal_mode, `PRAGMA foreign_keys=ON`).
5. DB file: `assistant/state/dashboard-kpi.sqlite` (outside this repo; path configured via env `DASHBOARD_KPI_DB`).
6. Idempotent migrator CLI: `python -m app.db migrate` — applies pending migrations, skips already-applied, errors on hash mismatch.

## Schema (migration 001)

Per consensus `research/codex.md#2`:
- `videos(video_id PK, title, published_at, channel_id, city_slug NULL, duration_s, created_at, updated_at)`
- `projects(city_slug PK, first_commit_at, canonical_path, default_branch, status, created_at)`
- `video_project_map(city_slug FK, video_id FK, confidence REAL, mapping_source TEXT, active BOOL, notes, created_at, PK(city_slug, video_id))`
- `ingestion_runs(run_id PK, source, started_at, finished_at, status, quota_units, error_text)`
- `channel_metric_snapshots(metric_key, grain, window_start, window_end, observed_on, value_num, run_id FK, preliminary BOOL DEFAULT 0, PK(metric_key, grain, window_start, window_end, observed_on))`
- `video_metric_snapshots(video_id FK, metric_key, grain, window_start, window_end, observed_on, value_num, run_id FK, preliminary BOOL DEFAULT 0, PK(video_id, metric_key, grain, window_start, window_end, observed_on))`
- `video_retention_points(video_id FK, observed_on, elapsed_seconds, retention_pct, run_id FK, PK(video_id, observed_on, elapsed_seconds))`
- `git_events(commit_sha PK, city_slug FK, branch_name, committed_at, event_type, event_value NULL, payload_json, confidence REAL)`

## Indexes

- `channel_metric_snapshots(metric_key, window_end, observed_on DESC)`
- `video_metric_snapshots(video_id, metric_key, window_end, observed_on DESC)`
- `git_events(city_slug, event_type, committed_at)`
- `video_project_map(video_id, active)`
- `video_project_map(city_slug, active)`

## Test plan

- `tests/test_migrations.py`: fresh DB → `migrate` → re-run `migrate` is no-op; hash mismatch errors.
- `pytest` covers all PK/FK constraints.

## Files touched

- `docs/adr/0001-kpi-dashboard.md` (new)
- `db/migrations/001_init.sql` (new)
- `app/db.py` (new)
- `tests/test_migrations.py` (new)
- `pyproject.toml` (add `pytest`, minimum Python 3.11)

## Review loop

- [ ] Codex round-1 → `reviews/task-01/codex-round-1.md`
- [ ] Codex round-N (if needed)
- [ ] Gemini round-1 → `reviews/task-01/gemini-round-1.md` (may be `gemini-degraded` if 429 continues)
- [ ] `ready-to-merge` | `ready-to-merge (gemini-degraded)`
- [ ] `merged`
