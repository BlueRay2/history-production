#!/usr/bin/env bash
# Wrapper for nightly KPI ingest. Runs `python -m ingest.nightly`,
# emits a Telegram alert on first-success and on failure.
# Exit codes are propagated for systemd timer / CronCreate to react.
set -u

KPI_ROOT="/home/aiagent/assistant/git/history-production/kpi"
PYTHON="${KPI_PYTHON:-/home/aiagent/miniconda3/envs/practicum/bin/python}"
LOG_DIR="${KPI_LOG_DIR:-/home/aiagent/assistant/state/kpi-logs}"
FIRST_RUN_FLAG="/home/aiagent/assistant/state/kpi-vault-first-success.flag"
LOG_FILE="${LOG_DIR}/nightly-$(date -u +%Y-%m-%dT%H%M%SZ).log"

mkdir -p "$LOG_DIR"

# shellcheck disable=SC1091
source "$(dirname "$(readlink -f "$0")")/lib/telegram-alert.sh"

cd "$KPI_ROOT" || { send_telegram_alert "❌ kpi nightly: cwd $KPI_ROOT missing"; exit 2; }

set -o pipefail
"$PYTHON" -m ingest.nightly 2>&1 | tee "$LOG_FILE"
rc=${PIPESTATUS[0]}

if (( rc == 0 )); then
    if [[ ! -f "$FIRST_RUN_FLAG" ]]; then
        date -u +%Y-%m-%dT%H:%M:%SZ > "$FIRST_RUN_FLAG"
        send_telegram_alert "🚀 kpi vault live — first nightly success at $(cat "$FIRST_RUN_FLAG")"
    fi
else
    tail_excerpt="$(tail -n 12 "$LOG_FILE" 2>/dev/null | head -c 1500)"
    send_telegram_alert "❌ kpi nightly failed (rc=$rc) — log: ${LOG_FILE}\n${tail_excerpt}"
fi

exit "$rc"
