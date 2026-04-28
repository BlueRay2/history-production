#!/usr/bin/env bash
# Hourly heartbeat: query monitoring views, write a row to monitoring_pings,
# emit Telegram alert on first transition into degraded/down.
# Exit code 0 always (heartbeat must never block timer); errors logged.
set -u

KPI_ROOT="/home/aiagent/assistant/git/history-production/kpi"
PYTHON="${KPI_PYTHON:-/home/aiagent/miniconda3/envs/practicum/bin/python}"
DB="${KPI_DB:-/home/aiagent/assistant/state/kpi.sqlite}"
FIRST_HB_FLAG="/home/aiagent/assistant/state/kpi-vault-first-heartbeat.flag"
LOG_DIR="${KPI_LOG_DIR:-/home/aiagent/assistant/state/kpi-logs}"
LOG_FILE="${LOG_DIR}/heartbeat-$(date -u +%Y-%m-%dT%H%M%SZ).log"

mkdir -p "$LOG_DIR"

# shellcheck disable=SC1091
source "$(dirname "$(readlink -f "$0")")/lib/telegram-alert.sh"

cd "$KPI_ROOT" || exit 0

# heartbeat.py is a small embedded Python helper that:
#   1. opens DB read-write
#   2. checks v_last_run_per_source for max age (>26h → degraded; >50h → down)
#   3. INSERT into monitoring_pings (ping_at, status, details_json, alert_sent=0)
#   4. emits status to stdout
status="$("$PYTHON" - <<'PYEOF' 2>&1 | tee -a "$LOG_FILE"
import json, os, sqlite3, sys
from datetime import datetime, timezone

db = os.environ.get("KPI_DB", "/home/aiagent/assistant/state/kpi.sqlite")
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row
try:
    rows = con.execute("""
        SELECT source, source_detail, last_status, last_started_jd,
               (julianday('now') - last_started_jd) * 24.0 AS hours_since
          FROM v_last_run_per_source
    """).fetchall()
except sqlite3.OperationalError as e:
    # Schema not migrated yet — treat as degraded.
    print("schema_missing")
    sys.exit(0)

if not rows:
    status = "degraded"
    detail = {"reason": "no ingestion_runs rows"}
else:
    max_hours = max(r["hours_since"] for r in rows)
    failing = [r for r in rows if r["last_status"] not in ("ok", "running")]
    if max_hours > 50 or len(failing) >= 3:
        status = "down"
    elif max_hours > 26 or failing:
        status = "degraded"
    else:
        status = "ok"
    detail = {
        "max_hours_since_last_run": round(max_hours, 2),
        "failing_count": len(failing),
        "sources": [(r["source"], r["source_detail"], r["last_status"]) for r in rows],
    }

now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
con.execute(
    "INSERT INTO monitoring_pings (ping_at, status, details_json, alert_sent) VALUES (?, ?, ?, 0)",
    (now_iso, status, json.dumps(detail))
)
con.commit()
print(status)
PYEOF
)"

# Telegram alert: first heartbeat ever AND on degraded/down transitions.
if [[ ! -f "$FIRST_HB_FLAG" && "$status" == "ok" ]]; then
    date -u +%Y-%m-%dT%H:%M:%SZ > "$FIRST_HB_FLAG"
    send_telegram_alert "💓 kpi vault heartbeat ok — first hourly check at $(cat "$FIRST_HB_FLAG")"
elif [[ "$status" == "degraded" || "$status" == "down" ]]; then
    # Look up most recent unalerted row and dispatch (single notification per state row).
    "$PYTHON" - "$status" <<'PYEOF' 2>&1 | tee -a "$LOG_FILE" || true
import os, sqlite3, sys, subprocess
status = sys.argv[1]
db = os.environ.get("KPI_DB", "/home/aiagent/assistant/state/kpi.sqlite")
con = sqlite3.connect(db)
row = con.execute(
    "SELECT ping_at, details_json FROM monitoring_pings "
    "WHERE alert_sent = 0 AND status = ? ORDER BY ping_at DESC LIMIT 1",
    (status,)
).fetchone()
if row:
    msg = f"⚠️ kpi vault status={status} at {row[0]}\\nDetails: {row[1]}"
    subprocess.run(["bash", "-c", f'source /home/aiagent/assistant/git/history-production/kpi/scripts/lib/telegram-alert.sh && send_telegram_alert "$0"', msg], check=False)
    con.execute("UPDATE monitoring_pings SET alert_sent = 1 WHERE ping_at = ?", (row[0],))
    con.commit()
PYEOF
fi

exit 0
