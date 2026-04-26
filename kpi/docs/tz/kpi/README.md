# Process — Comprehensive YouTube metrics vault (project codename: `kpi`)

**Branch:** `kpi`
**Source of truth:** `/home/aiagent/assistant/git/consensus-metrics-vault-2026-04-26/`
**Created:** 2026-04-26T18:15+03:00
**Owner:** Claude (coordinator). Review: Codex + Gemini per-task in parallel (identical to `dashboard-kpi`).

## Context

Replaces the current analytical KPI dashboard (`dashboard-kpi/`) with a **comprehensive nightly metrics ingestor + monitoring UI**. Goal is **data accumulation** for future DS analysis (channel age <2 months at project start; team plans to revisit accumulated data after several months for trend analysis, modeling, and growth experiments).

**Architectural shift:**
- *Before:* curated KPI surface (Impressions/CTR/AVD/AVP/Retention) + derived insights (cycle-time, scripts-per-week)
- *After:* exhaustive metric collection (ALL Analytics API metrics + ALL Reporting API non-deprecated reports) into wide flexible schema; web UI is **monitoring, not analytics** — shows ingest health, not channel performance

**Locked decisions (per Ярослав 2026-04-26 msg 7800):**

| # | Decision | Rationale |
|---|---|---|
| D1 | **Full replace** of `dashboard-kpi` | Different profile of use — no value in coexistence |
| D2 | **SQLite continues** (no Postgres) | Zero ops overhead; ~3-5M rows/year manageable with proper indexes |
| D3 | **Current OAuth scopes only** (`youtube.readonly` + `yt-analytics.readonly`) | Monetary scope blocked by Google Cloud Console verification (Brimit org constraints). No revenue/CPM/ad-impressions data collection in scope |
| D4 | **60-day backfill** on first run | Channel age <2 months — exhaustive 60d covers full history |
| D5 | **Project codename `kpi`** (sibling dir to `dashboard-kpi`) | Concise per Ярослав |
| D6 | **Monitoring UI pages confirmed** | See task-07 spec |

## Out of scope (explicit)

- Revenue/CPM/ad metrics — blocked by D3
- Migration of historical data from `dashboard-kpi.sqlite` — full replace per D1; backup-then-drop only
- Postgres/DuckDB — blocked by D2
- Predictive analytics / ML over collected data — separate downstream project for future

## Task index + live status

| ID | File | Scope | Status | Codex review | Gemini review |
|---|---|---|---|---|---|
| 01 | [task-01-adr-and-schema.md](task-01-adr-and-schema.md) | ADR locking architectural shift; new flexible wide-schema for arbitrary metrics + Reporting CSV registry | `in-review (r 1)` | — | — |
| 02 | [task-02-decommission-old-dashboard.md](task-02-decommission-old-dashboard.md) | Backup + drop `dashboard-kpi.sqlite`; disable `claude-kpi-dashboard.service`; remove old Flask routes | `pending` | — | — |
| 03 | [task-03-extended-youtube-client.md](task-03-extended-youtube-client.md) | Full-coverage YouTubeClient: all Analytics dimensions/metrics, all Reporting jobs, quota budgeting | `pending` | — | — |
| 04 | [task-04-nightly-ingest-job.md](task-04-nightly-ingest-job.md) | Comprehensive nightly job: per-day per-video × all metrics × all dimensions; resilient to partial failures | `pending` | — | — |
| 05 | [task-05-backfill-bootstrap.md](task-05-backfill-bootstrap.md) | One-shot 60-day backfill script; quota-aware pacing; idempotent | `pending` | — | — |
| 06 | [task-06-monitoring-schema.md](task-06-monitoring-schema.md) | Schema for ingest health: ingestion_runs extension, freshness derived view, quota_usage table, schema_drift detector | `pending` | — | — |
| 07 | [task-07-monitoring-ui.md](task-07-monitoring-ui.md) | Flask app with 6 pages (24h summary, freshness matrix, quota usage, schema drift, video coverage, errors register) | `pending` | — | — |
| 08 | [task-08-cron-systemd-tests.md](task-08-cron-systemd-tests.md) | Cron + systemd timer for nightly 03:30; vcrpy cassettes; smoke tests; failure→Telegram alert (direct Bot API curl, not MCP) | `pending` | — | — |

## Per-task review loop (identical to dashboard-kpi)

1. **Claim task:** transition `pending` → `in-progress` in this index. Push to origin.
2. **Implement** on `kpi` branch.
3. **Dispatch parallel review (round N):** status `in-progress` → `in-review (r N)`.
   - Codex via `scripts/codex-tracked-exec.sh` → `kpi/docs/tz/kpi/reviews/task-XX/codex-round-N.md`.
   - Gemini via `scripts/gemini-agent.sh review` (with `GEMINI_ALLOW_FLASH_FALLBACK=1` on 429) → `kpi/docs/tz/kpi/reviews/task-XX/gemini-round-N.md`.
   **Both delegated simultaneously.**
4. **Merge findings** into a single fix commit.
5. **Both accept in same round** → status `ready-to-merge`.
6. **Gemini-degraded fallback** if Gemini returns 429 after flash-fallback retries AND Codex accepted.
7. **Merge** fast-forward into `kpi` branch.
8. Push `origin/kpi` after every status transition.

**Anti-loop guard:** 5 review rounds without convergence → escalate to Ярослав.

**Status vocabulary:** `pending` → `in-progress` → `in-review (r N)` → `ready-to-merge` → `ready-to-merge (gemini-degraded)` → `merged`.

## Dependencies between tasks

**Updated post-Gemini-r1 finding F3:** task-02 moved AFTER task-08 to avoid monitoring outage during multi-day implementation of new system. New system must be operational and verified BEFORE legacy is decommissioned.

- **task-01** (ADR + schema) blocks all others.
- **task-03** (YouTube client) blocks task-04 and task-05.
- **task-04** (nightly ingest) blocks task-08 (cron schedules it).
- **task-05** (backfill) can run in parallel with task-04 implementation but DEPENDS on task-03.
- **task-06** (monitoring schema) blocks task-07 (monitoring UI).
- **task-07** can develop in parallel with task-04 (both depend on schema from task-01 + task-06).
- **task-08** (cron + tests + initial activation) blocks task-02 — legacy stays online and watched until new system runs ≥3 successful nightly cycles.
- **task-02** (decommission legacy) is the FINAL step — only after task-08 verifies new system is healthy.

Critical path: 01 → 03 → 04 → 08 → 02, with 05/06/07 parallelizable after 03/01.

Legacy `dashboard-kpi.sqlite` and its Flask service stay running (untouched, providing existing analytical view) throughout 01-08. Both systems coexist for ≥3 days post-task-08 ship; only after new monitoring system is verified does task-02 retire legacy.

## Telegram broadcast cadence

Per dashboard-kpi process. One concise DM per status transition, immediate broadcast for critical bugs.

## Git remote

Existing remote on `kpi` branch (BlueRay2/history-production). Push after every status transition.

## Future work (outside this bundle)

- Monetary scope addition once org verification permits (separate task)
- DS analysis tooling on top of accumulated data (months from now)
- Optional migration to time-series DB if SQLite struggles past year-1 (separate ADR)
