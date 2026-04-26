# Round 1 RETROACTIVE Review — task-08-cron-systemd-runbook (Gemini-3.1-pro)

**Reviewer:** Gemini-3.1-pro (retroactive, after Codex+capacity returned)
**Verdict:** REQUEST_CHANGES

## Findings

- **[HIGH]** (`scripts/run_refresh.py:53`, `systemd/dashboard-kpi-refresh.service:11-12`, confidence: high) **Log Rotation Missing & Systemd Duplication.** The task spec explicitly requires the cron log to be "rotated daily, keep 30 files". `run_refresh.py` uses a static `logging.FileHandler` which never rotates. Furthermore, the systemd unit is configured to append stdout/stderr to the exact same file. Because Python sets up both a `FileHandler` and a `StreamHandler(sys.stderr)`, every log line will be written twice when triggered by systemd. 
  *Fix:* In `run_refresh.py`, replace `logging.FileHandler` with `logging.handlers.TimedRotatingFileHandler(when="midnight", backupCount=30, encoding="utf-8")`. In `dashboard-kpi-refresh.service`, remove the `StandardOutput=` and `StandardError=` lines so Python exclusively manages the log file and its lifecycle.

- **[MEDIUM]** (`scripts/install_kpi_dashboard.sh:13`, `systemd/claude-kpi-dashboard.service:10`, confidence: high) **Installer Port Variable Mismatch.** `install_kpi_dashboard.sh` accepts `DASHBOARD_KPI_PORT` from the environment to verify the `ss` bind check. However, `claude-kpi-dashboard.service` has `Environment=DASHBOARD_KPI_PORT=8787` statically hardcoded. If an operator sets a custom port during installation, the service will still bind to 8787, but the installer will test the custom port and fail the health check.
  *Fix:* Either remove the environment variable fallback in the installer (hardcode `PORT="8787"` to match the unit), or update the installer to explicitly `sed -i` the port into the copied unit file.

- **[LOW]** (`scripts/run_refresh.py:68-76`, confidence: high) **Unstripped BOM and Comments in Bot Token Parser.** (Carried over from self-review). `Path.read_text(encoding="utf-8")` does not strip a Byte Order Mark (`\ufeff`), which will cause the first line to be silently skipped if a BOM is present. It also fails to strip inline comments (e.g., `BOT_TOKEN=abc # prod`).
  *Fix:* Use `encoding="utf-8-sig"` to safely consume any BOM, and strip comments via `value.partition("#")[0].strip().strip('"').strip("'")`.

- **[LOW]** (`tests/test_run_refresh.py:40`, confidence: high) **Test Hygiene: `basicConfig` Leak.** Because `logging.basicConfig()` does nothing if handlers are already configured on the root logger, and pytest runs tests in the same process, only the first test actually configures the logger. Subsequent tests silently write their logs to the first test's `tmp_path`.
  *Fix:* Pass `force=True` to `logging.basicConfig(...)` in `_setup_logging()` to ensure handlers are re-bound when the module is reloaded during tests.

## Observations (non-blocking)

- The workaround for systemd's lack of support for Bash default variables (`${VAR:-default}`)—by declaring `Environment=DASHBOARD_KPI_PORT=8787` explicitly in the unit file—is a correct and robust adaptation of the task spec.
- The direct `curl` approach for Telegram alerts effectively bypasses the MCP layer as requested, ensuring alerts fire even if the Claude/Gemini session is completely down.
- File-based locking using `fcntl.flock` on `state/run_refresh.lock` correctly supports the dual-scheduling "bypass-the-weakness" mandate without race conditions.

## Disagreements with self-review

1. **Agreed with MED finding 1 (Lock OSError):** Handled correctly in the implementation diff. The `try/except OSError` successfully prevents silent filesystem failures.
2. **Agreed with MED finding 2 (SQLite Heuristic):** Handled correctly in the implementation diff. `_classify()` now relies on specific SQLite markers rather than the generic word "database", eliminating the false positive for YouTube API errors.
3. **Disagreed with LOW finding 2 (Test Import Path):** The self-review complained that `scripts/run_refresh` is only importable in tests because of `pytest.ini`'s `pythonpath = ["."]`, and suggested adding it to `setuptools`. I disagree. Relying on `pythonpath` for testing non-package executable scripts is standard practice and avoids polluting the production package distribution with top-level tool scripts. No change is required here.
