#!/usr/bin/env bash
# Decommission the legacy KPI dashboard (task-02).
#
# DESTRUCTIVE: stops + disables systemd services, moves the legacy SQLite to
# a retired-YYYY-MM-DD path, removes the deploy symlink. ALWAYS run AFTER
# the new metrics-vault stack (task-07/task-08) has been verified live for
# ≥3 days; this is encoded as a hard preflight gate in step 0.
#
# Idempotent: re-running the script after partial completion only acts on
# the steps that haven't yet finished.
#
# Exit codes:
#   0 — clean decommission (or already decommissioned)
#   2 — preflight gate failed (verification window not satisfied)
#   3 — backup hash mismatch (refused to drop legacy DB)
#   4 — new monitoring service not active (would create dashboard outage)
set -euo pipefail

ASSISTANT_ROOT="/home/aiagent/assistant"
KPI_ROOT="${ASSISTANT_ROOT}/git/history-production/kpi"
SYSTEMD_USER="${HOME}/.config/systemd/user"
DEPLOY_DIR="${ASSISTANT_ROOT}/deploys"
LEGACY_LINK="${DEPLOY_DIR}/kpi-dashboard"
LEGACY_DB="${ASSISTANT_ROOT}/state/dashboard-kpi.sqlite"
DEEP_MEMORY="${ASSISTANT_ROOT}/git/deep-memory"
ARCHIVE_DIR="${DEEP_MEMORY}/archive"
TODAY="$(date +%F)"
BACKUP_PATH="${ARCHIVE_DIR}/dashboard-kpi-final-backup-${TODAY}.sqlite"
RETIRED_PATH="${LEGACY_DB}.retired-${TODAY}"
FIRST_RUN_FLAG="${ASSISTANT_ROOT}/state/kpi-vault-first-success.flag"
FIRST_HB_FLAG="${ASSISTANT_ROOT}/state/kpi-vault-first-heartbeat.flag"
VERIFICATION_DAYS_REQUIRED="${KPI_DECOMM_DAYS:-3}"

# shellcheck disable=SC1091
source "${KPI_ROOT}/scripts/lib/telegram-alert.sh"

info() { printf '[decomm] %s\n' "$*" >&2; }
die()  { printf '[decomm] FATAL: %s\n' "$*" >&2; exit "${2:-1}"; }

# ---------------------------------------------------------------------------
# 0. Preflight gates
# ---------------------------------------------------------------------------

# 0a. New monitoring service is healthy (will not introduce dashboard outage).
if ! systemctl --user is-active --quiet claude-kpi-monitoring.service 2>/dev/null; then
    die "claude-kpi-monitoring.service is not active — refusing to decommission legacy" 4
fi

# 0b. New stack has lived through verification window (≥${VERIFICATION_DAYS_REQUIRED} days
#     since first nightly success + first heartbeat).
gate_failed=()
for flag in "$FIRST_RUN_FLAG" "$FIRST_HB_FLAG"; do
    if [[ ! -f "$flag" ]]; then
        gate_failed+=("$flag missing")
        continue
    fi
    flag_epoch="$(stat -c %Y "$flag" 2>/dev/null || echo 0)"
    now_epoch="$(date +%s)"
    age_days=$(( (now_epoch - flag_epoch) / 86400 ))
    if (( age_days < VERIFICATION_DAYS_REQUIRED )); then
        gate_failed+=("$flag age=${age_days}d (<${VERIFICATION_DAYS_REQUIRED}d)")
    fi
done
if (( ${#gate_failed[@]} > 0 )); then
    info "preflight verification window NOT satisfied:"
    for f in "${gate_failed[@]}"; do info "  - $f"; done
    info "set KPI_DECOMM_DAYS=0 to override (NOT recommended)"
    exit 2
fi

info "preflight OK: new stack live, verification window passed"

# ---------------------------------------------------------------------------
# 1. Backup legacy DB to deep-memory archive (idempotent — reuse existing)
# ---------------------------------------------------------------------------
mkdir -p "$ARCHIVE_DIR"
if [[ -f "$LEGACY_DB" ]]; then
    if [[ -f "$BACKUP_PATH" ]]; then
        info "backup already exists at $BACKUP_PATH; verifying hash"
    else
        cp -p "$LEGACY_DB" "$BACKUP_PATH"
        info "backup written to $BACKUP_PATH"
    fi
    SHA_SRC="$(sha256sum "$LEGACY_DB" | cut -d' ' -f1)"
    SHA_DST="$(sha256sum "$BACKUP_PATH" | cut -d' ' -f1)"
    if [[ "$SHA_SRC" != "$SHA_DST" ]]; then
        die "backup hash mismatch: src=$SHA_SRC dst=$SHA_DST" 3
    fi
    info "backup hash verified: $SHA_SRC"

    # Commit the archive into deep-memory (private repo).
    if git -C "$DEEP_MEMORY" status --porcelain "$BACKUP_PATH" 2>/dev/null | grep -q .; then
        git -C "$DEEP_MEMORY" add "archive/$(basename "$BACKUP_PATH")"
        git -C "$DEEP_MEMORY" commit -m "kpi: backup of legacy dashboard-kpi.sqlite before decommission (sha256: ${SHA_SRC})"
        git -C "$DEEP_MEMORY" push origin main 2>/dev/null || info "deep-memory push deferred (offline?)"
    fi
elif [[ -f "$RETIRED_PATH" ]]; then
    info "legacy DB already retired at $RETIRED_PATH; skipping backup step"
else
    info "no legacy DB found — backup step is no-op"
fi

# ---------------------------------------------------------------------------
# 2. Stop + disable legacy systemd services
# ---------------------------------------------------------------------------
for unit in claude-kpi-dashboard.service dashboard-kpi-refresh.timer dashboard-kpi-refresh.service; do
    if systemctl --user list-units --all 2>/dev/null | grep -q "$unit"; then
        systemctl --user stop "$unit" 2>/dev/null || true
        systemctl --user disable "$unit" 2>/dev/null || true
        info "stopped + disabled $unit"
    fi
    if [[ -f "${SYSTEMD_USER}/${unit}" ]]; then
        rm -f "${SYSTEMD_USER}/${unit}"
        info "removed unit file ${SYSTEMD_USER}/${unit}"
    fi
done
systemctl --user daemon-reload 2>/dev/null || true

# ---------------------------------------------------------------------------
# 3. Remove deploy symlink
# ---------------------------------------------------------------------------
if [[ -L "$LEGACY_LINK" ]]; then
    rm -f "$LEGACY_LINK"
    info "removed legacy deploy symlink $LEGACY_LINK"
fi

# ---------------------------------------------------------------------------
# 4. Remove legacy CronCreate entry from scheduled-crons.tson if present
# ---------------------------------------------------------------------------
if [[ -x "${ASSISTANT_ROOT}/scripts/cron-manage.sh" ]]; then
    if grep -q '"id":"dashboard_kpi_refresh"' "${ASSISTANT_ROOT}/config/scheduled-crons.tson" 2>/dev/null; then
        "${ASSISTANT_ROOT}/scripts/cron-manage.sh" remove --id dashboard_kpi_refresh 2>/dev/null && \
            info "removed dashboard_kpi_refresh cron entry" || \
            info "cron-manage.sh remove returned non-zero (entry may not exist)"
    fi
fi

# ---------------------------------------------------------------------------
# 5. Move (NOT delete) the legacy DB to retired-YYYY-MM-DD
# ---------------------------------------------------------------------------
if [[ -f "$LEGACY_DB" ]]; then
    mv "$LEGACY_DB" "$RETIRED_PATH"
    info "moved legacy DB to $RETIRED_PATH (kept on disk; manual rm scheduled +7 days)"
fi

# ---------------------------------------------------------------------------
# 6. Telegram broadcast
# ---------------------------------------------------------------------------
msg="📦 kpi legacy dashboard decommissioned ${TODAY}\n"
msg+="Backup: ${BACKUP_PATH}\n"
msg+="Retired DB: ${RETIRED_PATH} (rm scheduled +7 days)\n"
msg+="Archive sha256: ${SHA_SRC:-N/A}"
send_telegram_alert "$msg" || info "Telegram broadcast failed; details in script log"

info "decommission complete"
