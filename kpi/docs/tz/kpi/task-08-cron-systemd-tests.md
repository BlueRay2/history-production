# task-08 — Cron + systemd + tests + first ingest verification

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
5. **DO NOT remove legacy code in task-08.** (Codex r2 finding) Legacy `app.main`, `weekly_view.py`, `monthly_view.py`, templates and `claude-kpi-dashboard.service` STAY untouched throughout task-08. Removal is the responsibility of **task-02** (now moved to final step) AFTER ≥3 days of new system stable operation. This preserves the rollback-friendly state during stabilization.
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

During task-08 (and the ≥3-day verification window before task-02 fires), legacy is **fully alive** — both `claude-kpi-dashboard.service` and `claude-kpi-monitoring.service` run side-by-side. To rollback at this stage:

1. `systemctl --user stop kpi-nightly-ingest.timer` — stop new ingest
2. `systemctl --user stop claude-kpi-monitoring.service` — stop new UI
3. `systemctl --user disable kpi-*` — disable new units
4. Legacy continues running unchanged

(Post-task-02 rollback procedure is in task-02's own rollback section.)

## Acceptance criteria

- All 3 systemd units active, all 2 cron entries registered
- First scheduled nightly run completes in <5min and writes >0 rows
- Heartbeat fires hourly, writes monitoring_pings rows
- `/api/health` returns `{status: ok}` continuously after first run
- **Legacy stays untouched** — task-08 ship commit contains zero changes to `app.main`, `weekly_view.py`, `monthly_view.py`, legacy templates, or `claude-kpi-dashboard.service`. Legacy retirement is task-02's scope, executed only after ≥3-day verification window.
- All tests pass

## Review loop slots

- [ ] Codex round 1: pending
- [ ] Gemini round 1: pending
