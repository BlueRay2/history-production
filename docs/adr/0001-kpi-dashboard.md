# ADR-0001 — KPI Dashboard stack & architecture

**Status:** Accepted
**Date:** 2026-04-21
**Context:** consensus-dashboard-kpi run (9 rounds, 2026-04-21), ship verdict round 9.
**Owner:** Ярослав (208368262); implementation lead: Claude.

## Context

Build a local-hosted KPI dashboard for YouTube channel "Cities Evolution" (UCjLrTC9jdfx6iI5w7SL8LHw, 44 subs, 24 videos). Daily 03:30 GMT+3 refresh via pure-Python YouTube API client + history-production git introspection. Weekly / Monthly tabs. Localhost-only MVP.

## Decision

### Stack
- **Backend framework:** Flask + Jinja (minimal, Python-native).
- **Frontend interactivity:** HTMX for server-fragment swaps; no SPA. Small amount of hand-rolled vanilla JS for local widget state — **no Alpine.js** (avoids micro-framework soup per consensus round 2).
- **Charts:** Chart.js via CDN.
- **Database:** SQLite with WAL journal mode + `PRAGMA foreign_keys=ON`.
- **DB migrations:** raw SQL files in `db/migrations/NNN_*.sql` applied by `app/db.py migrate` — no Alembic overhead at this scale.
- **YouTube ingest:** `google-api-python-client` + `google-auth-oauthlib` — **not** claude-headless+MCP (consensus round 1 finding F-08).
- **Python:** 3.11+.
- **Runtime:** home-server miniconda env `practicum` + flask dev server under systemd user unit.

### Data model (see `db/migrations/001_init.sql`)
- Append-only snapshot pattern with `(entity, metric, window, observed_on)` PK — no destructive updates.
- First-class `video_project_map` table with `confidence` + manual-override support.
- `git_events` table records heuristic parse output with confidence scores.

### Deploy layout
- Code lives in this repo (`history-production`) under branch `kpi`.
- Install script creates symlink `/home/aiagent/assistant/deploys/kpi-dashboard → /home/aiagent/assistant/git/history-production`.
- Runtime state (DB, logs) under `/home/aiagent/assistant/state/` and `/home/aiagent/assistant/logs/`.

### Metric handling (sparse-data discipline)
- Unavailable metrics return NULL in SQL, never 0 (consensus finding J-03).
- Repository API `value_with_reason() -> (value, reason)` where reason ∈ {`ok`, `below_privacy_floor`, `channel_too_new`, `no_data_pulled`}.
- UI renders each reason distinctly (`N/A` with tooltip vs raw value).

## Consequences

### Positive
- Tests are easy: raw SQL + std-lib sqlite3 has zero ORM magic.
- Deploy is a single symlink + one systemd unit.
- Future LAN / auth migration to FastAPI would touch only `app/main.py` — ingest/repo/views stay portable.

### Negative / accepted trade-offs
- Flask dev server is not production-grade — acceptable for localhost single-user MVP; gunicorn/uvicorn migration deferred until LAN access is scoped.
- Raw SQL migrations lack the diff tooling of Alembic — acceptable at expected schema volume (≤20 migrations before major refactor).

## Rejected alternatives

- **Streamlit:** heavy rerun model; poor fit for 10-15 charts; weak auth story.
- **FastAPI+HTMX+Alpine+Chart.js:** over-engineered for this MVP; ~2× build time; framework soup risk.
- **Grafana + SQLite:** wrong fit for heuristic joins + mapping overrides + write-back exception workflow.
- **Evidence.dev:** static-site builder; no live mapping-approval workflow.
- **Datasette:** explorer UI, not a curated dashboard; read-only by design.

## References

- Consensus run: `/home/aiagent/assistant/git/consensus-dashboard-kpi/`
- Authoritative verdict: highest-numbered `verdict-roundN.md` in that directory (currently `verdict-round9.md`).
- Task process: [../tz/dashboard-kpi/process.md](../tz/dashboard-kpi/process.md)
