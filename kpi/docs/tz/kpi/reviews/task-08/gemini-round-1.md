## Summary

This review covers the implementation of a new KPI heartbeat monitoring system (task-08). The system introduces a `heartbeat.sh` script that uses embedded Python to check the status of data ingestion sources and records a heartbeat ping. This script is intended to be run as a `systemd` oneshot service (`kpi-heartbeat.service`) triggered by a timer. Unit tests (`test_heartbeat.py`) have been added to validate the core decision-making logic.

## Findings

My review is based on the files I was able to access: `kpi/scripts/heartbeat.sh`, `kpi/tests/test_heartbeat.py`, and `kpi/systemd/kpi-heartbeat.service`. I was **unable** to access `kpi/systemd/kpi-heartbeat.timer` and `kpi/scripts/install_kpi_dashboard.sh` due to persistent tool errors.

*   **[+] SUCCESS:** The primary request to cross-validate the heartbeat logic was successful. The Python decision logic embedded in `scripts/heartbeat.sh` **exactly matches** the re-implemented logic in `tests/test_heartbeat.py`. The tests correctly pin the critical business logic (status is ok/degraded/down based on age of last run and count of failing sources).

*   **[+] GOOD:** The `kpi-heartbeat.service` unit is well-defined. It correctly specifies the service as `oneshot`, sets the appropriate `WorkingDirectory` and `Environment` variables, and executes the `heartbeat.sh` script. Logging is properly redirected.

*   **[-] GAP:** The contents of `kpi/systemd/kpi-heartbeat.timer` could not be verified. I cannot confirm it is correctly configured to trigger the heartbeat service at the intended hourly interval.

*   **[-] GAP:** The installation script `kpi/scripts/install_kpi_dashboard.sh` could not be reviewed. I cannot confirm that the new `kpi-heartbeat.service` and `kpi-heartbeat.timer` units are correctly copied to the systemd directory, enabled, and started during installation.

## Evidence

### Heartbeat Logic Cross-Validation

The core decision logic is identical between the production script and the test.

**`scripts/heartbeat.sh` (embedded Python):**
```python
    max_hours = max(r["hours_since"] for r in rows)
    failing = [r for r in rows if r["last_status"] not in ("ok", "running")]
    if max_hours > 50 or len(failing) >= 3:
        status = "down"
    elif max_hours > 26 or failing:
        status = "degraded"
    else:
        status = "ok"
```

**`tests/test_heartbeat.py` (`_heartbeat_decision` function):**
```python
    max_hours = max(r[4] for r in rows)
    failing = [r for r in rows if r[2] not in ("ok", "running")]
    if max_hours > 50 or len(failing) >= 3:
        status = "down"
    elif max_hours > 26 or failing:
        status = "degraded"
    else:
        status = "ok"
```

### Systemd Service Configuration

The service file appears correct.
**`kpi/systemd/kpi-heartbeat.service`:**
```ini
[Service]
Type=oneshot
WorkingDirectory=/home/aiagent/assistant/git/history-production/kpi
Environment=KPI_DB=/home/aiagent/assistant/state/kpi.sqlite
Environment=KPI_LOG_DIR=/home/aiagent/assistant/state/kpi-logs
ExecStart=/home/aiagent/assistant/git/history-production/kpi/scripts/heartbeat.sh
```

## Commands

I recommend the executor agent run the following commands to close the verification gaps:

1.  **Verify Timer Schedule:**
    ```bash
    cat /home/aiagent/assistant/git/history-production/kpi/systemd/kpi-heartbeat.timer
    ```

2.  **Verify Installation Logic:**
    ```bash.
    grep -C 3 -E 'kpi-heartbeat.service|kpi-heartbeat.timer' /home/aiagent/assistant/git/history-production/kpi/scripts/install_kpi_dashboard.sh
    ```

## Risks

*   **Low:** The core heartbeat logic is sound and well-tested. A bug in the status determination is unlikely.
*   **Medium:** There is a risk that the heartbeat feature fails silently if the `install_kpi_dashboard.sh` script does not correctly enable and start the `kpi-heartbeat.timer`. Because I could not review these files, this risk is elevated. An improperly configured timer or a missing installation step would render the entire feature non-functional.

## Recommended Handoff

Handoff to Codex CLI for execution.

**Task:** Verify the timer configuration and installation logic for the KPI heartbeat feature.

1.  Read the file `kpi/systemd/kpi-heartbeat.timer` and confirm it is configured for `OnCalendar=hourly`.
2.  Read the file `kpi/scripts/install_kpi_dashboard.sh` and confirm it contains commands to:
    *   Copy `kpi-heartbeat.service` and `kpi-heartbeat.timer` to the appropriate systemd directory (e.g., `/etc/systemd/user/` or `/usr/lib/systemd/user`).
    *   Execute `systemctl --user daemon-reload`.
    *   Execute `systemctl --user enable --now kpi-heartbeat.timer`.

If these checks pass, the implementation can be considered complete. If not, correct the installation script.
