# task-02 — Decommission legacy dashboard

**Status:** `pending`
**Dep:** task-01 (new schema must exist before tearing down old)
**Risk:** Medium (irreversible legacy removal; backup MUST succeed before drop)

## Scope

1. **Backup legacy DB** to `assistant/git/deep-memory/archive/dashboard-kpi-final-backup-2026-04-26.sqlite` (off-repo, in deep-memory archive). Verify backup file size matches source.
2. **Stop and disable systemd services:**
   - `systemctl --user stop claude-kpi-dashboard.service`
   - `systemctl --user stop dashboard-kpi-refresh.timer`
   - `systemctl --user disable claude-kpi-dashboard.service dashboard-kpi-refresh.timer`
   - Remove unit files: `~/.config/systemd/user/claude-kpi-dashboard.service`, `dashboard-kpi-refresh.{service,timer}`
3. **Remove deploy symlink:** `rm /home/aiagent/assistant/deploys/kpi-dashboard`.
4. **Drop the legacy CronCreate entry** for `dashboard_kpi_refresh` via `CronDelete`. Update `config/scheduled-crons.tson` to remove the entry. Run `scripts/cron-state.sh` reconcile.
5. **Mark legacy code as deprecated** in `kpi/app/main.py` and `kpi/app/services/weekly_view.py` — add header comment `# DEPRECATED 2026-04-26: replaced by app.monitoring (task-07 of kpi-vault TZ)`. Files removed in task-07 final cleanup commit, not here, to allow gradual migration if rollback needed.
6. **Drop legacy SQLite file** `state/dashboard-kpi.sqlite` ONLY after backup verified. Use `mv` rather than `rm` initially: `mv state/dashboard-kpi.sqlite state/dashboard-kpi.sqlite.retired-2026-04-26` — keep on disk for 7 days, scheduled `rm` via cron 7 days later.
7. **Document in CHANGELOG** at `kpi/CHANGELOG.md` a top entry: `## 2026-04-26 — Legacy dashboard decommissioned. Replaced by metrics vault. Backup at deep-memory archive.`
8. **Telegram alert** to Ярослав with backup path + verification status.

## Backup verification

Compute SHA-256 of source and backup, assert equal:

```bash
SHA_SRC=$(sha256sum state/dashboard-kpi.sqlite | cut -d' ' -f1)
SHA_DST=$(sha256sum git/deep-memory/archive/dashboard-kpi-final-backup-2026-04-26.sqlite | cut -d' ' -f1)
[[ "$SHA_SRC" == "$SHA_DST" ]] || die "backup hash mismatch"
```

Commit deep-memory archive entry with message: `kpi: backup of legacy dashboard-kpi.sqlite before decommission (sha256: $SHA_SRC)`.

## Test plan

- Manual: after task-02 merge, `systemctl --user status claude-kpi-dashboard.service` returns `Loaded: not-found`.
- Manual: `curl http://127.0.0.1:8787/weekly` returns `connection refused` (service no longer running).
- Manual: `ls /home/aiagent/assistant/state/dashboard-kpi.sqlite.retired-*` exists, original gone.
- Hash equality assertion above runs as part of decommission script.

## Acceptance criteria

- Legacy systemd units removed cleanly
- Backup verified at deep-memory with sha256 match
- CronDelete entry executed and scheduled-crons.tson updated
- Telegram broadcast sent to Ярослав
- No lingering Flask process on 127.0.0.1:8787
- CHANGELOG entry committed

## Rollback plan

If next-step tasks fail and need rollback within 7 days:

1. Stop new monitoring service (when it exists)
2. Restore from `state/dashboard-kpi.sqlite.retired-*` → `state/dashboard-kpi.sqlite`
3. Recreate systemd units (unit files preserved in git history via `git show HEAD~N:kpi/systemd/`)
4. Re-enable + start

After 7 days, retired file is removed permanently — rollback then requires deep-memory backup.

## Review loop slots

- [ ] Codex round 1: pending
- [ ] Gemini round 1: pending
