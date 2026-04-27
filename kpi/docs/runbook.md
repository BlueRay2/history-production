# KPI Dashboard Runbook

Local-hosted dashboard for YouTube channel Cities Evolution. Binds to
`127.0.0.1:8787` only; MVP has no auth.

## Architecture

- **Web service:** `claude-kpi-dashboard.service` (systemd user unit) →
  Flask app at `app.main:create_app()`.
- **Daily refresh:** two independent triggers for reliability
  (bypass-the-weakness):
  1. In-session `CronCreate` (id `dashboard_kpi_refresh`) at
     `30 3 * * *` Europe/Minsk.
  2. Systemd user timer `dashboard-kpi-refresh.timer`
     (`OnCalendar=*-*-* 03:30:00 Europe/Minsk`, `Persistent=true`).
- Both layers call `scripts/run_refresh.py`; a flock on
  `state/run_refresh.lock` prevents concurrent runs.
- Failure alerts go directly to Ярослав via Bot API curl (not MCP) so
  they survive a dead Claude session.

## Start / stop / restart

```bash
systemctl --user status claude-kpi-dashboard.service
systemctl --user restart claude-kpi-dashboard.service
systemctl --user stop claude-kpi-dashboard.service
systemctl --user start claude-kpi-dashboard.service
```

Refresh timer:

```bash
systemctl --user list-timers dashboard-kpi-refresh.timer
systemctl --user start dashboard-kpi-refresh.service   # one-off manual run
```

## Install / re-install

```bash
/home/aiagent/assistant/deploys/kpi-dashboard/scripts/install_kpi_dashboard.sh
```

Idempotent: safe to re-run. Creates the deploy symlink, installs the
three systemd units, enables the service + timer, and verifies 200 on
`GET http://127.0.0.1:8787/weekly` plus `127.0.0.1:8787` bind (and NOT
`0.0.0.0:8787`).

## Debug the daily refresh

1. Inspect the last run log:
   ```bash
   tail -200 /home/aiagent/assistant/logs/dashboard-kpi.log
   ```
2. Inspect the `ingestion_runs` table:
   ```bash
   sqlite3 /home/aiagent/assistant/state/dashboard-kpi.sqlite \
     "SELECT run_id, source, started_at, finished_at, status, error_text
      FROM ingestion_runs ORDER BY started_at DESC LIMIT 5;"
   ```
3. Manual dry run:
   ```bash
   /home/aiagent/miniconda3/envs/practicum/bin/python \
     /home/aiagent/assistant/deploys/kpi-dashboard/scripts/run_refresh.py
   echo "rc=$?"
   ```

## OAuth token rotation

If the YouTube Analytics refresh token expires or is revoked:

```bash
cd /home/aiagent/assistant/git/history-production/kpi
/home/aiagent/miniconda3/envs/practicum/bin/python scripts/bootstrap_youtube_oauth.py --rotate
```

This re-runs the installed-app OAuth flow. The new refresh token writes
to `/home/aiagent/.config/youtube-api/.env` (0600).

## DB backup

Weekly backup → deep-memory repo:

```bash
cp /home/aiagent/assistant/state/dashboard-kpi.sqlite \
   /home/aiagent/assistant/git/deep-memory/backups/dashboard-kpi-$(date +%F).sqlite
cd /home/aiagent/assistant/git/deep-memory
git add backups/ && git commit -m "kpi backup $(date +%F)" && git push
```

Automate via a weekly cron if desired (not in MVP scope).

## Failure playbook by exit code

| rc | Meaning | Action |
|----|---------|--------|
| 0  | ok | none |
| 1  | YouTube API failure | check quota, token validity, network |
| 2  | DB failure | check SQLite file permissions and disk space |
| 3  | partial | one or more videos failed — inspect `ingestion_runs.error_text`; usually transient |
| 40 | quota exhausted | wait for quota reset; consider narrower `video_ids` scope |

Any non-zero rc also posts a 🔴 alert to Ярослав's Telegram.

## Port + bind guarantee

`install_kpi_dashboard.sh` explicitly verifies after start:

- `ss -ltn | grep 127.0.0.1:8787` MUST show
- `ss -ltn | grep 0.0.0.0:8787` MUST NOT show

If either check fails, the installer aborts non-zero without leaving the
service in a partial state.
