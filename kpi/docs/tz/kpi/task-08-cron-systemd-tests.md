# task-08 — Cron + systemd + tests + retire legacy code

**Status:** `pending`
**Dep:** task-04 (nightly job exists), task-05 (backfill exists), task-07 (monitoring UI exists)
**Risk:** Medium (last integration step; failure here means no automation)

## Scope

1. Register cron entry `kpi_nightly_ingest` in `config/scheduled-crons.tson` and via `CronCreate`:
   - Cron: `30 3 * * *` (Europe/Minsk)
   - Recurring: true, durable: true
   - Prompt loads `scripts/run_nightly.sh` (which calls `python -m ingest.nightly`)
2. Register cron entry `kpi_monitoring_heartbeat`:
   - Cron: `0 * * * *` (every hour)
   - Calls `scripts/heartbeat.sh` which checks freshness + writes `monitoring_pings` row
3. Install systemd user units:
   - `claude-kpi-monitoring.service` — Flask monitoring app on 127.0.0.1:8787
   - `kpi-nightly-ingest.service` (oneshot) + `kpi-nightly-ingest.timer` (`OnCalendar=*-*-* 03:30:00 Europe/Minsk; Persistent=true`) — fallback safety-net per dashboard-kpi pattern (dual-trigger)
   - `kpi-heartbeat.service` (oneshot) + `kpi-heartbeat.timer` (`OnCalendar=hourly`)

   **Re: dual-trigger redundancy (Gemini r1 finding F6 — LOW):** the CronCreate entry + systemd timer for nightly ingest IS intentionally redundant per the «bypass-the-weakness» principle from CLAUDE.md and inherited from `dashboard-kpi`. The `state/kpi-ingest.lock` flock (task-04) prevents double-execution if both fire. Risk of double work: zero. Risk if only one path used and that path fails: ingest stops silently for days. Trade-off accepted.
4. Install script `scripts/install_kpi_vault.sh` (idempotent) that:
   - Creates deploy symlink `assistant/deploys/kpi-vault → kpi/`
   - Copies systemd units to `~/.config/systemd/user/`
   - daemon-reload + enable --now all 3 services
   - Health check: `curl -sf http://127.0.0.1:8787/api/health` returns `{status: ok}` after start
   - Aborts if 0.0.0.0 binding detected (security check from legacy)
5. Final cleanup commit: remove legacy `app.main`, `app.services.weekly_view.py`, `app.services.monthly_view.py`, `templates/weekly.html`, `templates/monthly.html`. Keep tests for these temporarily for git-blame friendliness, removed in commit AFTER 7-day rollback window expires.
6. Telegram alert on first successful nightly run AND first heartbeat: «🚀 kpi vault live — first nightly success + heartbeat ok».

## Tests

- `tests/test_nightly_smoke.py` — vcrpy cassette for full mocked nightly run, asserts non-empty rows in `channel_snapshots` and `video_snapshots`
- `tests/test_backfill_smoke.py` — mocked 60-day backfill, sentinel file written at end
- `tests/test_monitoring_routes.py` — all 6 routes return 200 + valid HTML structure
- `tests/test_quota_pacing.py` — synthetic quota nearing cap mid-run → orchestrator returns `quota_exhausted`, run row finalized correctly
- `tests/test_heartbeat.py` — synthetic stale orchestrator (last run >26h) → heartbeat writes `down` row + alert dispatched

Run `pytest -q kpi/tests/` in CI step (manual run on every PR until CI exists).

## Telegram alert helpers

Direct Bot API curl pattern (per dashboard-kpi convention; survives Claude session downtime):

```bash
TOKEN=$(grep '^BOT_TOKEN=' /home/aiagent/.claude/channels/telegram/.env | cut -d= -f2)
curl -sS --max-time 15 \
  "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -d chat_id=208368262 \
  --data-urlencode "text=${MESSAGE}"
```

Helper in `scripts/lib/telegram-alert.sh` shared by `run_nightly.sh`, `heartbeat.sh`, `install_kpi_vault.sh`.

## Rollback

For 7 days post-merge, legacy systemd units (`claude-kpi-dashboard.service` etc.) are removed but unit files preserved in git history. To rollback:
1. `git checkout HEAD~M -- kpi/systemd/` (where M = commits since task-02)
2. Re-run legacy `install_kpi_dashboard.sh`
3. Restore `state/dashboard-kpi.sqlite` from `state/dashboard-kpi.sqlite.retired-2026-04-26`

After 7 days, retired sqlite is `rm`'d by scheduled cron, rollback then requires deep-memory backup restore.

## Acceptance criteria

- All 3 systemd units active, all 2 cron entries registered
- First scheduled nightly run completes in <5min and writes >0 rows
- Heartbeat fires hourly, writes monitoring_pings rows
- `/api/health` returns `{status: ok}` continuously after first run
- Legacy code removed in same commit as final ship; rollback path documented
- All tests pass

## Review loop slots

- [ ] Codex round 1: pending
- [ ] Gemini round 1: pending
