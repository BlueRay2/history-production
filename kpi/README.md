# KPI Dashboard

Self-contained subproject. Local-hosted Flask dashboard for the YouTube channel
"Cities Evolution" with daily YouTube Analytics ingestion and weekly/monthly
views.

All dashboard artifacts live under this directory — the parent repository
(`history-production`) keeps script/episode directories (`istanbul/`, `kyoto/`,
`quanzhou/`, …) clean of dashboard code.

## Layout

| Path | Purpose |
|---|---|
| `app/` | Flask application (routes, services, repositories, db wiring) |
| `ingest/` | YouTube API client, env loader, ingestion jobs, git-log parser |
| `db/migrations/` | SQLite schema (append-only snapshot model) |
| `templates/`, `static/` | Jinja templates and JS/CSS for the web UI |
| `scripts/` | `install_kpi_dashboard.sh`, `run_refresh.py`, `bootstrap_youtube_oauth.py` |
| `systemd/` | Three user units: web service + refresh service + refresh timer |
| `config/kpi-thresholds.yaml.sample` | Threshold defaults (copy → `kpi-thresholds.yaml` to override) |
| `tests/` | pytest suite (~25 files, includes VCR cassettes) |
| `pyproject.toml` | Package metadata + dev deps (pytest, vcrpy) |
| `docs/runbook.md` | Operational runbook |
| `docs/adr/0001-kpi-dashboard.md` | Architecture decision record |
| `docs/tz/dashboard-kpi/` | Task specs (task-01 … task-09) |
| `reviews/` | Codex/Gemini multi-agent review logs (task-01 … task-09) |

## Quick start

```bash
# 1. Install the dashboard (creates deploy symlink + systemd units, health-checks).
/home/aiagent/assistant/git/history-production/kpi/scripts/install_kpi_dashboard.sh

# 2. After install — http://127.0.0.1:8787/weekly
```

See `docs/runbook.md` for ops, debug, OAuth rotation, backup, and the
exit-code playbook.
