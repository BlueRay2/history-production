# task-07 — Monitoring web UI (Flask app `app.monitoring`)

**Status:** `pending`
**Dep:** task-06 (views), task-04 (data flowing)
**Risk:** Low (read-only Flask; cosmetic if broken)

## Scope

Replace the legacy analytical Flask app (`app.main`) with a **monitoring-focused** Flask app `app.monitoring`. New systemd unit `claude-kpi-monitoring.service`. Same port `8787` (preserve URL stability for team).

## Pages (per locked decision D6)

### 1. `/` — 24h ingest summary (default)
- Header: «Last 24h ingest summary»
- Table: per-source rows (data_api / analytics_api / reporting_api / nightly_orchestrator / backfill / monitoring)
  - last_started_at (relative time: "12 minutes ago")
  - last_status (color-coded: green ok / yellow partial / red api_failure or db_failure / orange quota_exhausted)
  - count_24h_total / count_24h_failed
  - rows_written_24h
- Top-level health badge: ✅ all green / ⚠️ degraded (any non-`ok` last status) / 🔴 down (no orchestrator run in >26h)

### 2. `/freshness` — per-metric freshness matrix
- Heatmap-style grid: rows = metric_keys (e.g. `views`, `cardImpressions`, `subscribersGained`, etc.), cols = dimension_keys ('', 'country=US', 'deviceType=MOBILE', etc.)
- Cell color encodes `days_since_last_obs`:
  - 0-1 days: green
  - 2-3 days: yellow
  - 4-7 days: orange
  - 7+ days: red
- Hover tooltip: exact `last_obs_jd` timestamp
- Filter: by metric_key prefix (search bar)

### 3. `/quota` — YouTube quota usage
- For each API (data_api_v3, analytics_api_v2, reporting_api_v1):
  - Today's units_used / 10000 with progress bar
  - Today's request_count
  - Last 7 days as a small line chart
- Threshold annotations: 50% (informational), 80% (warning), 95% (critical)

### 4. `/schema-drift` — API surface change log
- Table of `schema_drift_log` entries, newest first
- Filter: by source (analytics_api / reporting_api), drift_type
- Each row: detected_at, source, drift_type, identifier, notes
- Allow human "acknowledge" — adds `acknowledged_at` column update via `POST /schema-drift/{id}/ack`

### 5. `/videos` — per-video coverage matrix
- Table: video_id (truncated), title (truncated 40 chars), `metrics_pulled_7d`, `last_pulled_jd` (relative time)
- Sort: by `last_pulled_jd` ASC (so stalest at top)
- Color row red if `metrics_pulled_7d == 0` AND `published_at` < 90 days ago

### 6. `/errors` — last 50 failed runs
- Table: started_at, source, source_detail, status, error_text (truncated 200 chars)
- Filter: by source, by status
- Click on row → modal showing full error_text + run_id

## Visual design

- Same minimal stack as legacy: Flask + Jinja + HTMX + Chart.js + Tailwind via CDN
- Color palette: monochrome + status accents (green/yellow/orange/red)
- No analytical KPIs anywhere — explicit principle: "this is plumbing health, not channel performance"

## Routes summary

```python
# app/monitoring/__init__.py + routes.py
GET /                       → 24h summary
GET /freshness              → freshness heatmap
GET /quota                  → quota usage
GET /schema-drift           → drift log
POST /schema-drift/<id>/ack → acknowledge drift entry
GET /videos                 → video coverage
GET /errors                 → error register
GET /api/health             → JSON: {status: ok|degraded|down, checks: [...]}
```

## `/api/health` JSON shape

For external monitoring (e.g. cron-based smoke check, future Grafana/Prometheus pull):

```json
{
  "status": "ok",
  "last_orchestrator_run": "2026-04-26T03:30:00Z",
  "hours_since_last_run": 18.5,
  "failing_sources": [],
  "quota_used_today": {"data_api_v3": 47, "analytics_api_v2": 982, "reporting_api_v1": 12},
  "schema_drift_unacknowledged": 0
}
```

## Test plan

- Smoke tests: each route returns 200 with valid HTML
- `/api/health`: synthetic ingestion_runs DB → assert correct status classification
- `/schema-drift/ack`: POST → DB updated → GET shows acknowledged
- HTMX search filter on freshness: type prefix → filtered grid

## Acceptance criteria

- All 6 pages render with seed data
- `/api/health` returns deterministic JSON
- Service binds 127.0.0.1:8787 only (per legacy security)
- No leaked CSS/JS from legacy templates
- Tailwind via CDN works offline-acceptable (no inline-only restrictions)

## Review loop slots

- [ ] Codex round 1: pending
- [ ] Gemini round 1: pending
