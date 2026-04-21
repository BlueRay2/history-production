# task-08 — Cron + systemd + runbook

**Status:** `pending`
**Dep:** 03, 07
**Risk:** Medium

## Scope

1. `scripts/run_refresh.py`:
   - Entry point for daily cron.
   - Calls `ingest.jobs.run_daily_refresh(target_date=date.today() - timedelta(days=2))` (preliminary data handling).
   - Exit codes: 0 ok, 1 api failure, 2 db failure, 3 partial, 40 quota exhausted.
   - Logs to `logs/dashboard-kpi.log` (rotated daily, keep 30 files).
   - On non-zero: Telegram alert to Ярослав (208368262) via `scripts/queue-eta-notify.sh` pattern.
2. Cron registration: `CronCreate` durable:true, id `dashboard_kpi_refresh`, schedule `30 3 * * *` (GMT+3 local), prompt:
   ```
   # cron-id: dashboard_kpi_refresh
   Execute /home/aiagent/assistant/scripts/run_refresh.py and verify rc=0.
   ```
   Fallback: systemd user timer `~/.config/systemd/user/dashboard-kpi-refresh.{service,timer}` with `OnCalendar=*-*-* 03:30:00 Europe/Minsk`. Both layers per CLAUDE.md bypass-the-weakness rule.
3. **Deploy path (J-02 resolution from consensus Round 5):** dashboard code lives in `history-production` repo `kpi` branch. Install script creates symlink:
   `/home/aiagent/assistant/deploys/kpi-dashboard → /home/aiagent/assistant/git/history-production` (worktree on `kpi` branch while WIP; switched to `main` once task bundle merges).
   Acceptance criterion: `readlink /home/aiagent/assistant/deploys/kpi-dashboard` must exit 0 post-install.

4. Systemd user service `claude-kpi-dashboard.service`:
   - `ExecStart=/home/aiagent/miniconda3/envs/practicum/bin/flask --app app.main run --host 127.0.0.1 --port ${DASHBOARD_KPI_PORT:-8787}`
   - `Restart=always`
   - `WorkingDirectory=/home/aiagent/assistant/deploys/kpi-dashboard` (symlink established in step 3).
   - `Environment=PYTHONUNBUFFERED=1 DASHBOARD_KPI_DB=/home/aiagent/assistant/state/dashboard-kpi.sqlite`.

5. Install script `scripts/install_kpi_dashboard.sh`:
   - `mkdir -p /home/aiagent/assistant/deploys/` and creates the symlink per step 3.
   - Copies systemd unit; `systemctl --user daemon-reload && systemctl --user enable --now claude-kpi-dashboard.service`.
   - Verifies `curl -sf http://127.0.0.1:8787/weekly` returns 200.
   - Writes port binding check: `ss -ltn | grep 127.0.0.1:8787` must show, NOT `0.0.0.0:8787`.
   - Acceptance: `[[ -L /home/aiagent/assistant/deploys/kpi-dashboard ]]` AND systemctl active.
5. Runbook `docs/runbook.md`:
   - Start/stop/restart.
   - Debug cron (pull last run log; inspect `ingestion_runs` table).
   - Token rotation via `bootstrap_youtube_oauth.py --rotate`.
   - DB backup path (weekly cron → `deep-memory/backups/`).
   - Failure playbook per exit code.

## Test plan

- `tests/test_run_refresh.py`: mock ingest success → rc=0; mock api fail → rc=1 + alert called.
- `tests/test_install.py` (integration, opt-in): run install script → check unit active + port bound to 127.0.0.1.
- `tests/test_localhost_bind.py`: parsing `ss -ltn` output verifies NOT listening on 0.0.0.0.

## Files touched

- `scripts/run_refresh.py`, `scripts/install_kpi_dashboard.sh` (new)
- `systemd/claude-kpi-dashboard.service`, `systemd/dashboard-kpi-refresh.service`, `systemd/dashboard-kpi-refresh.timer` (new)
- `docs/runbook.md` (new)
- `tests/test_run_refresh.py`, `tests/test_install.py`, `tests/test_localhost_bind.py` (new)

## Review loop

- [ ] Codex round-1 → `reviews/task-08/codex-round-1.md`
- [ ] Gemini round-1 → `reviews/task-08/gemini-round-1.md`
- [ ] `ready-to-merge` | `ready-to-merge (gemini-degraded)`
- [ ] `merged`

## Bypass-the-weakness notes

- Dual scheduling (CronCreate + systemd timer) per CLAUDE.md § Bypass the Weakness.
- Flock in `run_refresh.py` prevents concurrent invocations if both layers fire.
- Failure alert to Telegram is direct Bot API curl (not MCP) to survive Claude session downtime.
