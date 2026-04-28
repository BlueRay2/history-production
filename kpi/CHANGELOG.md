# kpi metrics-vault changelog

## 2026-04-28 — task-08 merged: cron + systemd timers + heartbeat + install + tests

- `scripts/run_nightly.sh` (wraps `python -m ingest.nightly` with first-success and failure Telegram alerts)
- `scripts/heartbeat.sh` (hourly health check; per-incident alert dedup with 5 canonical sequences pinned)
- `scripts/install_kpi_vault.sh` (idempotent installer; mktemp + trap; reachability-only health probe pre-first-ingest; rollback timers on 0.0.0.0 detection)
- `scripts/lib/telegram-alert.sh` (rc 0/2/3 = delivered/skipped/failed)
- `systemd/kpi-{nightly-ingest,heartbeat}.{service,timer}` (oneshot + Persistent=true)
- `tests/test_heartbeat.py` (8 tests) + `tests/test_install_kpi_vault_script.py` (11 tests)
- 6 review rounds, 7 findings addressed (1H+5M+1L), final commit `13a0261`.

## 2026-04-28 — task-06-fixup-gemini-r1 merged: optimize v_last_run_per_source

- `db/migrations-kpi/003_optimize_v_last_run_per_source.sql` — replace dual correlated subqueries with single CTE+ROW_NUMBER() pass. Equivalence verified empirically. Codex r1 + Gemini r1 ACCEPTED zero findings (commit `4e30342`).

## 2026-04-28 — Retroactive audit closed (tasks 04/05/06/07)

- All previously degraded reviews re-run with full file access. Status promoted to `merged (full reviewed)` for tasks 04/05/07 and `merged (full reviewed + fixup applied)` for task 06. Details in `docs/tz/kpi/retroactive-audit-log.md`.

## 2026-04-26 — Legacy dashboard decommissioned

- Replaced by metrics vault (kpi-vault TZ tasks 01/03/04/05/06/07/08).
- Backup committed to deep-memory archive at `archive/dashboard-kpi-final-backup-YYYY-MM-DD.sqlite` with sha256 verification.
- Decommission carried out by `scripts/decommission_dashboard.sh` after the ≥3-day verification window post-task-08 (preflight gate enforces).
- Legacy SQLite moved to `state/dashboard-kpi.sqlite.retired-YYYY-MM-DD`; manual `rm` scheduled +7 days for post-stability cleanup.
- Legacy modules `kpi/app/main.py` and `kpi/app/services/weekly_view.py` carry `# DEPRECATED 2026-04-26` headers; full file removal scheduled +7 days post-task-02 merge.
