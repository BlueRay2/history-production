#!/usr/bin/env bash
# Hourly heartbeat: query monitoring views, write a row to monitoring_pings,
# emit Telegram alert on first transition into degraded/down.
# Exit 0 on success ("ok"/"degraded"/"down" all written cleanly).
# Exit 4 on heartbeat write failure (DB unwritable, schema missing, etc.) —
# this surfaces real monitoring-side breakage to the systemd journal /
# CronCreate consumer instead of swallowing it.
set -u

KPI_ROOT="/home/aiagent/assistant/git/history-production/kpi"
PYTHON="${KPI_PYTHON:-/home/aiagent/miniconda3/envs/practicum/bin/python}"
DB="${KPI_DB:-/home/aiagent/assistant/state/kpi.sqlite}"
FIRST_HB_FLAG="/home/aiagent/assistant/state/kpi-vault-first-heartbeat.flag"
LOG_DIR="${KPI_LOG_DIR:-/home/aiagent/assistant/state/kpi-logs}"
LOG_FILE="${LOG_DIR}/heartbeat-$(date -u +%Y-%m-%dT%H%M%SZ).log"
RESULT_FILE="$(mktemp -t kpi-heartbeat-result.XXXXXX)"
trap 'rm -f "$RESULT_FILE"' EXIT

mkdir -p "$LOG_DIR"

# shellcheck disable=SC1091
source "$(dirname "$(readlink -f "$0")")/lib/telegram-alert.sh"

cd "$KPI_ROOT" || { send_telegram_alert "❌ kpi heartbeat: cwd $KPI_ROOT missing" || true; exit 4; }

# Embedded Python emits one of: "ok|degraded|down|error:<reason>" to RESULT_FILE.
# Schema-missing OR write-failure → "error:..." → wrapper exits 4.
KPI_DB="$DB" "$PYTHON" - "$RESULT_FILE" <<'PYEOF' >>"$LOG_FILE" 2>&1
import json, os, sqlite3, sys
from datetime import datetime, timezone

result_file = sys.argv[1]
db = os.environ.get("KPI_DB", "/home/aiagent/assistant/state/kpi.sqlite")

def emit(token):
    open(result_file, "w").write(token)

try:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
except Exception as e:
    emit(f"error:db_connect:{type(e).__name__}")
    sys.exit(0)

try:
    rows = con.execute("""
        SELECT source, source_detail, last_status, last_started_jd,
               (julianday('now') - last_started_jd) * 24.0 AS hours_since
          FROM v_last_run_per_source
    """).fetchall()
except sqlite3.OperationalError as e:
    emit(f"error:schema:{e}")
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
try:
    con.execute(
        "INSERT INTO monitoring_pings (ping_at, status, details_json, alert_sent) VALUES (?, ?, ?, 0)",
        (now_iso, status, json.dumps(detail))
    )
    con.commit()
except sqlite3.OperationalError as e:
    emit(f"error:write:{e}")
    sys.exit(0)
emit(status)
PYEOF

result="$(cat "$RESULT_FILE" 2>/dev/null)"

# Heartbeat write failure → alert + exit 4
if [[ "$result" == error:* ]]; then
    send_telegram_alert "❌ kpi heartbeat write failure: ${result}" || true
    echo "[heartbeat] DB error: ${result}" >> "$LOG_FILE"
    exit 4
fi

status="$result"

# First-heartbeat-ok ping (only after successful write)
if [[ ! -f "$FIRST_HB_FLAG" && "$status" == "ok" ]]; then
    first_hb_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    if send_telegram_alert "💓 kpi vault heartbeat ok — first hourly check at ${first_hb_iso}"; then
        echo "$first_hb_iso" > "$FIRST_HB_FLAG"
    else
        echo "[heartbeat] first-hb Telegram delivery failed; will retry" >> "$LOG_FILE"
    fi
elif [[ "$status" == "degraded" || "$status" == "down" ]]; then
    # Dispatch alert for most recent unalerted matching row, then mark alert_sent=1.
    KPI_DB="$DB" "$PYTHON" - "$status" <<'PYEOF' >>"$LOG_FILE" 2>&1 || true
import os, sqlite3, subprocess, sys
status = sys.argv[1]
db = os.environ.get("KPI_DB", "/home/aiagent/assistant/state/kpi.sqlite")
con = sqlite3.connect(db)
row = con.execute(
    "SELECT ping_at, details_json FROM monitoring_pings "
    "WHERE alert_sent = 0 AND status = ? ORDER BY ping_at DESC LIMIT 1",
    (status,)
).fetchone()
if row:
    msg = f"⚠️ kpi vault status={status} at {row[0]}\nDetails: {row[1]}"
    rc = subprocess.run([
        "bash", "-c",
        'source /home/aiagent/assistant/git/history-production/kpi/scripts/lib/telegram-alert.sh && '
        'send_telegram_alert "$1"',
        "_", msg
    ], check=False).returncode
    if rc == 0:
        con.execute("UPDATE monitoring_pings SET alert_sent = 1 WHERE ping_at = ?", (row[0],))
        con.commit()
PYEOF
fi

exit 0
