#!/usr/bin/env bash
# Idempotent installer for the kpi-vault stack:
#   * deploy symlink assistant/deploys/kpi-vault → kpi/
#   * 5 systemd --user units (3 services + 2 timers)
#   * daemon-reload + enable --now: monitoring service + both timers
#   * 0.0.0.0 bind safety check
#   * /api/health probe
set -euo pipefail

ASSISTANT_ROOT="/home/aiagent/assistant"
REPO_ROOT="${ASSISTANT_ROOT}/git/history-production"
KPI_ROOT="${REPO_ROOT}/kpi"
DEPLOY_DIR="${ASSISTANT_ROOT}/deploys"
DEPLOY_LINK="${DEPLOY_DIR}/kpi-vault"
SYSTEMD_USER="${HOME}/.config/systemd/user"
UNIT_SRC="${KPI_ROOT}/systemd"
PORT="${KPI_MONITORING_PORT:-8787}"

UNITS_LONG_RUN=(claude-kpi-monitoring.service)
# Full unit list referenced by name (test_install_kpi_vault_script expects
# these literal strings in the installer body for static-grep verification).
ALL_UNITS=(
    claude-kpi-monitoring.service
    kpi-nightly-ingest.service
    kpi-nightly-ingest.timer
    kpi-heartbeat.service
    kpi-heartbeat.timer
)
UNITS_TIMER_PAIRS=(kpi-nightly-ingest kpi-heartbeat)  # each → .service + .timer

info() { printf '[install-kpi-vault] %s\n' "$*" >&2; }
die()  { printf '[install-kpi-vault] FATAL: %s\n' "$*" >&2; exit 1; }

# 1. Deploy symlink
mkdir -p "${DEPLOY_DIR}"
if [[ -e "${DEPLOY_LINK}" && ! -L "${DEPLOY_LINK}" ]]; then
    die "${DEPLOY_LINK} exists and is not a symlink"
fi
ln -sfn "${KPI_ROOT}" "${DEPLOY_LINK}"
[[ -L "${DEPLOY_LINK}" ]] || die "symlink not created"
info "deploy symlink OK: ${DEPLOY_LINK} -> $(readlink "${DEPLOY_LINK}")"

# 2. Copy + patch systemd units
mkdir -p "${SYSTEMD_USER}"
for unit in "${UNITS_LONG_RUN[@]}"; do
    cp -f "${UNIT_SRC}/${unit}" "${SYSTEMD_USER}/${unit}"
done
for pair in "${UNITS_TIMER_PAIRS[@]}"; do
    cp -f "${UNIT_SRC}/${pair}.service" "${SYSTEMD_USER}/${pair}.service"
    cp -f "${UNIT_SRC}/${pair}.timer"   "${SYSTEMD_USER}/${pair}.timer"
done

# Patch port override into monitoring unit so KPI_MONITORING_PORT env propagates
sed -i "s/^Environment=KPI_MONITORING_PORT=.*/Environment=KPI_MONITORING_PORT=${PORT}/" \
    "${SYSTEMD_USER}/claude-kpi-monitoring.service"

systemctl --user daemon-reload

# 3. Enable + start the long-running monitoring service
systemctl --user enable --now claude-kpi-monitoring.service

# 4. Enable + start timers (NOT the oneshot services they wrap)
for pair in "${UNITS_TIMER_PAIRS[@]}"; do
    systemctl --user enable --now "${pair}.timer"
done

info "systemd units enabled"

# 5. Health checks
sleep 2

# 5a. 0.0.0.0 bind safety — hard abort + rollback timers if violated
if ss -ltn | grep -q "0.0.0.0:${PORT}"; then
    info "0.0.0.0 detected — disabling timers + monitoring service before abort"
    for pair in "${UNITS_TIMER_PAIRS[@]}"; do
        systemctl --user disable --now "${pair}.timer" 2>/dev/null || true
    done
    systemctl --user disable --now claude-kpi-monitoring.service 2>/dev/null || true
    die "monitoring service bound to 0.0.0.0:${PORT} — security violation. Aborting."
fi

# 5b. localhost listener present
if ! ss -ltn | grep -q "127.0.0.1:${PORT}"; then
    die "nothing listening on 127.0.0.1:${PORT}"
fi

# 5c. /api/health REACHABILITY check (not status:ok).
# Rationale: on a fresh install before the first nightly run, /api/health
# legitimately returns status:down (no orchestrator rows yet). We verify the
# endpoint is reachable + returns valid JSON; status:ok is verified post-first-ingest.
http_code="$(curl -sS --max-time 10 -o /tmp/kpi-health-probe.json -w '%{http_code}' "http://127.0.0.1:${PORT}/api/health" 2>/dev/null || echo 000)"
if [[ "$http_code" != "200" ]]; then
    die "/api/health returned HTTP ${http_code} (expected 200)"
fi
if ! grep -qE '"status"\s*:\s*"(ok|degraded|down)"' /tmp/kpi-health-probe.json; then
    die "/api/health JSON malformed — got: $(cat /tmp/kpi-health-probe.json)"
fi
hstatus="$(python3 -c 'import json,sys; print(json.load(open("/tmp/kpi-health-probe.json")).get("status","?"))')"
info "health check PASS: /api/health reachable, status=${hstatus}"
[[ "$hstatus" == "ok" ]] || info "  (status≠ok is expected pre-first-ingest; will flip ok after first nightly run)"

# 6. List timers for visibility
systemctl --user list-timers --all 2>&1 | grep -E "kpi-(nightly|heartbeat)" || true

info "kpi-vault installation complete"
