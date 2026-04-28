#!/usr/bin/env bash
# Shared Telegram alert helper for kpi-vault scripts.
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/lib/telegram-alert.sh"
#   send_telegram_alert "🚀 kpi vault live"
#   send_telegram_alert "⚠️ ingest failure: ..." 208368262   # optional chat_id
#
# Reads BOT_TOKEN from /home/aiagent/.claude/channels/telegram/.env.
# Silent no-op if token missing or curl fails (alerts must never block ingest).

set -u

KPI_TG_ENV="${KPI_TG_ENV:-/home/aiagent/.claude/channels/telegram/.env}"
KPI_TG_DEFAULT_CHAT="${KPI_TG_DEFAULT_CHAT:-208368262}"

send_telegram_alert() {
    local message="${1:-}"
    local chat_id="${2:-$KPI_TG_DEFAULT_CHAT}"
    [[ -z "$message" ]] && return 0
    [[ -f "$KPI_TG_ENV" ]] || { echo "[tg-alert] no .env at $KPI_TG_ENV; skip" >&2; return 0; }
    local token
    token="$(grep '^BOT_TOKEN=' "$KPI_TG_ENV" 2>/dev/null | cut -d= -f2)"
    [[ -z "$token" ]] && { echo "[tg-alert] BOT_TOKEN missing; skip" >&2; return 0; }
    curl -sS --max-time 15 \
        "https://api.telegram.org/bot${token}/sendMessage" \
        -d chat_id="$chat_id" \
        --data-urlencode "text=${message}" \
        >/dev/null 2>&1 || echo "[tg-alert] curl failed; skip" >&2
    return 0
}
