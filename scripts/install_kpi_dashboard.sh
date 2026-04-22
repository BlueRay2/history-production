#!/usr/bin/env bash
# Install the KPI dashboard: deploy symlink, systemd units, port check.
#
# Safe to re-run — idempotent symlink + systemctl enable --now.
set -euo pipefail

ASSISTANT_ROOT="/home/aiagent/assistant"
REPO_ROOT="${ASSISTANT_ROOT}/git/history-production"
DEPLOY_DIR="${ASSISTANT_ROOT}/deploys"
DEPLOY_LINK="${DEPLOY_DIR}/kpi-dashboard"
SYSTEMD_USER="${HOME}/.config/systemd/user"
UNIT_SRC="${REPO_ROOT}/systemd"
PORT="${DASHBOARD_KPI_PORT:-8787}"

info() { printf '[install] %s\n' "$*" >&2; }
die() { printf '[install] FATAL: %s\n' "$*" >&2; exit 1; }

# 1. Create deploy symlink.
mkdir -p "${DEPLOY_DIR}"
if [[ -e "${DEPLOY_LINK}" && ! -L "${DEPLOY_LINK}" ]]; then
  die "${DEPLOY_LINK} exists and is not a symlink"
fi
ln -sfn "${REPO_ROOT}" "${DEPLOY_LINK}"
[[ -L "${DEPLOY_LINK}" ]] || die "symlink not created"
readlink "${DEPLOY_LINK}" >/dev/null || die "readlink failed"
info "deploy symlink OK: ${DEPLOY_LINK} -> $(readlink "${DEPLOY_LINK}")"

# 2. Install systemd user units.
# Patch DASHBOARD_KPI_PORT in claude-kpi-dashboard.service so an operator
# override via env var (DASHBOARD_KPI_PORT=...) propagates to the unit
# (Gemini-3.1-pro F-01 R1 MEDIUM: previously installer tested $PORT but
# unit hardcoded 8787 → custom-port deploy would fail health check).
mkdir -p "${SYSTEMD_USER}"
for unit in claude-kpi-dashboard.service dashboard-kpi-refresh.service dashboard-kpi-refresh.timer; do
  cp -f "${UNIT_SRC}/${unit}" "${SYSTEMD_USER}/${unit}"
done
sed -i "s/^Environment=DASHBOARD_KPI_PORT=.*/Environment=DASHBOARD_KPI_PORT=${PORT}/" \
  "${SYSTEMD_USER}/claude-kpi-dashboard.service"
systemctl --user daemon-reload
systemctl --user enable --now claude-kpi-dashboard.service
systemctl --user enable --now dashboard-kpi-refresh.timer
info "systemd units enabled"

# 3. Health check: 127.0.0.1 bind + HTTP 200 on /weekly.
sleep 2
if ! ss -ltn | grep -q "127.0.0.1:${PORT}"; then
  die "nothing listening on 127.0.0.1:${PORT}"
fi
if ss -ltn | grep -q "0.0.0.0:${PORT}"; then
  die "refusing to ship: also listening on 0.0.0.0:${PORT}"
fi
if ! curl -sf "http://127.0.0.1:${PORT}/weekly" >/dev/null; then
  die "GET /weekly did not return 2xx"
fi
info "install OK — dashboard live on 127.0.0.1:${PORT}"
