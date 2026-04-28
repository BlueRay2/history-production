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
    # Returns:
    #   0 — message confirmed delivered (Telegram returned ok:true)
    #   2 — skipped by config (no .env / no token / empty message)
    #   3 — delivery attempt failed (curl error, HTTP non-2xx, or ok:false)
    # Callers should treat any non-zero return as "alert NOT delivered" and
    # plan retry / state preservation (e.g., do not flip first-success flag).
    local message="${1:-}"
    local chat_id="${2:-$KPI_TG_DEFAULT_CHAT}"
    [[ -z "$message" ]] && { echo "[tg-alert] empty message; skip" >&2; return 2; }
    [[ -f "$KPI_TG_ENV" ]] || { echo "[tg-alert] no .env at $KPI_TG_ENV; skip" >&2; return 2; }
    local token
    token="$(grep '^BOT_TOKEN=' "$KPI_TG_ENV" 2>/dev/null | cut -d= -f2)"
    [[ -z "$token" ]] && { echo "[tg-alert] BOT_TOKEN missing; skip" >&2; return 2; }
    local response http_code
    response="$(curl -sS --max-time 15 -o /tmp/.tg-alert-resp.$$.json -w '%{http_code}' \
        "https://api.telegram.org/bot${token}/sendMessage" \
        -d chat_id="$chat_id" \
        --data-urlencode "text=${message}" 2>/dev/null || echo "000")"
    http_code="$response"
    if [[ "$http_code" =~ ^2 ]] && grep -q '"ok":true' /tmp/.tg-alert-resp.$$.json 2>/dev/null; then
        rm -f /tmp/.tg-alert-resp.$$.json
        return 0
    fi
    echo "[tg-alert] delivery FAILED http=${http_code} body=$(cat /tmp/.tg-alert-resp.$$.json 2>/dev/null | head -c 200)" >&2
    rm -f /tmp/.tg-alert-resp.$$.json
    return 3
}
