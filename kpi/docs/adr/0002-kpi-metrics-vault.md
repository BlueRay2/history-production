# ADR 0002 — KPI metrics vault (architectural shift from analytical dashboard)

**Status:** Accepted
**Date:** 2026-04-26
**Decided by:** Ярослав (channel owner) + Claude/Codex/Gemini consensus run
**Source consensus:** `/home/aiagent/assistant/git/consensus-metrics-vault-2026-04-26/`
**Supersedes (partially):** ADR 0001 — its dashboard surface is being retired in favour of monitoring UI; the underlying SQLite + Flask + HTMX stack from 0001 is preserved.

## Context

The original `dashboard-kpi` (ADR 0001) surfaced a curated set of KPIs (Impressions, CTR, AVD, AVP, Retention) plus derived insights (cycle-time, scripts-per-week, cost-per-video) for the «Cities Evolution» YouTube channel. That product solved the question *«how is the channel doing this week?»*

Channel age is now <2 months. The team needs a different artefact: **bulk historical raw data accumulated daily**, so DS analysis (statistical modelling, growth experiments, retention cohort analysis) becomes possible after several months. Curated KPIs hide raw signals; we want raw signals stored verbatim.

## Decision

**Replace** the analytical KPI dashboard with a **comprehensive nightly metrics vault** + **monitoring UI**.

The vault writes ALL available metrics from three YouTube APIs every night into a flexible wide-schema SQLite database. The web UI shifts from analytics-of-channel to analytics-of-the-pipeline-itself: ingest health, freshness, quota usage, schema drift, error register.

### Locked decisions (D1–D6 from Ярослав 2026-04-26 msg 7800)

| ID | Decision | Rationale |
|---|---|---|
| **D1** | Full replace, not coexist | Different profile of use; no value in maintaining analytical KPI surface in parallel |
| **D2** | SQLite continues; no Postgres | Zero ops overhead; ~3-5M rows/year manageable with proper indexes; Yaroslav prefers single binary |
| **D3** | Current OAuth scopes only (`youtube.readonly` + `yt-analytics.readonly`); **no monetary scope** | Brimit org constraints prevent Google Cloud Console verification for `yt-analytics-monetary.readonly` |
| **D4** | 60-day backfill on first run | Channel <2 months old; 60d covers full history without quota waste |
| **D5** | Project codename `kpi`; sibling directory to `dashboard-kpi` | Concise per Yaroslav |
| **D6** | 6 monitoring pages: 24h summary, freshness matrix, quota usage, schema drift, video coverage, errors | Confirmed by Yaroslav |

### Schema strategy

**Wide flexible key/value model** instead of one column per metric:

- `channel_snapshots(metric_key, dimension_key, grain, window_start, window_end, observed_on, value_num, run_id, source)`
- `video_snapshots(video_id, metric_key, dimension_key, grain, window_start, window_end, observed_on, value_num, run_id, source)`

This handles:
- ~60+ Analytics API metrics (only ~50% non-zero on small channels — sparse-friendly)
- Auto-discovered dimensions (country, device, traffic source, sharing service, demographics, ...) via `dimension_key='key=value'` encoding
- Future YouTube API additions/removals without migration
- Reporting API CSV rows ingested via same schema (just `source='reporting_api'`)

Dedicated tables for non-uniform data:
- `videos` — registry with rich Data API metadata
- `video_retention_points` — retention curves keyed by `elapsed_ratio` (0.0–1.0)
- `reporting_jobs` + `reporting_reports` — track Reporting API job lifecycle and CSV downloads

### Monitoring infrastructure

- `ingestion_runs` extended with `source`, `source_detail`, `quota_units`
- `quota_usage(api_name, date_utc, units_used, request_count)` — per-API daily quota tracking
- `schema_drift_log(id PK, detected_at, source, drift_type, identifier, acknowledged_at)` — detect API surface changes
- `monitoring_pings(ping_at PK, status, details_json, alert_sent)` — heartbeat for monitoring-of-monitoring

### Stack continuity

Stack from ADR 0001 carried over:
- **SQLite** (WAL, foreign_keys ON, microsecond ISO timestamps)
- **Flask** + **Jinja** for monitoring UI
- **HTMX** for inline drill-downs (replacing analytical Chart.js)
- **systemd user units** + **CronCreate** dual-trigger pattern (bypass-the-weakness)
- **Python ≥3.9** (matches `practicum` conda env on home server)

## Alternatives considered

1. **PostgreSQL backend** — rejected per D2. Could revisit if year-1 SQLite struggles.
2. **DuckDB layer for analytics queries** — rejected as premature optimization. Add later if SQLite slow.
3. **TimescaleDB** — rejected as overkill for 3-5M rows/year scale.
4. **Coexistence with dashboard-kpi instead of replace** — rejected per D1; team would maintain two parallel views.
5. **One-table-per-metric schema** — rejected: schema would grow with each new YouTube API metric. Wide key/value avoids migration treadmill.
6. **Append-only event log instead of snapshots** — rejected: pivoting raw events into time-series queries adds complexity. Snapshot model with `observed_on` already gives us audit trail at acceptable cost.

## Consequences

### Positive
- Raw data preserved verbatim → DS analysis 6-12 months from now is unblocked
- Schema absorbs YouTube API changes without migrations
- Monitoring UI surfaces ingest pipeline health, not just channel performance — operationally more useful
- Side-by-side coexistence during 3-day verification window (legacy stays alive) → safe rollout

### Negative
- Loss of curated KPI surface for casual «how's the channel» glance — team must use Studio UI directly during transition
- Wide schema requires more verbose SQL in future analysis queries (pivot-style)
- ~5M rows/year on SQLite may become slow past year 2-3 — separate ADR for migration if/when needed
- Schema drift detector adds maintenance load (someone must acknowledge new metrics)

### Neutral
- Quota usage roughly the same as `dashboard-kpi` (most quota was on Analytics API queries; we now make a few more per night for additional dimensions, but bulk of cost was already there)
- Cron + systemd dual-trigger preserved — same redundancy benefit, same operational footprint

## Implementation phases

Per `docs/tz/kpi/README.md` task index:
- task-01 (this) — ADR + schema + migrator
- task-03 — extended YouTubeClient
- task-04 — nightly orchestrator
- task-05 — 60-day backfill
- task-06 — monitoring schema
- task-07 — monitoring UI
- task-08 — cron + systemd + tests + first ingest verification
- task-02 — legacy decommission (FINAL, after 3-day verification window)

Critical path: 01 → 03 → 04 → 08 → 02

## References

- `kpi/docs/tz/kpi/README.md` — task index + status table
- `kpi/docs/tz/kpi/process.md` — review workflow
- `assistant/git/consensus-metrics-vault-2026-04-26/phase-3-findings/findings.tson` — full review trail
- `assistant/git/consensus-metrics-vault-2026-04-26/phase-4-judge/verdict.md` — SHIP decision rationale
