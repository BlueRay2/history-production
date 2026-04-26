# Round 1 Review — task-08-cron-systemd-runbook

**Reviewer:** Claude (coordinator self-review)
**Date:** 2026-04-22T14:25+03:00
**Commit reviewed:** 0eadd70
**Verdict:** REQUEST_CHANGES

## Review provenance

Codex delegation (both via codex-reader MCP and the Bash `codex-tracked-exec.sh` + direct `codex exec` fallbacks) failed to produce a review within multiple 3-minute windows today — rollouts `019db4bf` and `019db4db` aborted after emitting only `session_meta + task_started + turn_aborted` (4 records, 16 KB each). Earlier attempts (`019db39b`, `019db43a`) hung for 2+ hours after Codex fell back to `browser_run_code` via Playwright as a file-read workaround (see alert sent to Ярослав msg 6978; fix applied in `~/.codex/AGENTS.md` prohibiting Playwright as a shell-fallback).

Per Ярослав's instruction «3 с fallback на 4» (msg 6979), AGENTS.md was updated (option 3), Bash wrapper was tried (option 4) — it also hung. To unblock the bundle, this review is a coordinator self-review with the same discipline (HIGH/MED/LOW, ≤5 findings, ship-blockers only). It is documented as `review-provenance=self` in the merge commit; F-01 retroactive review queue extended to include task-08 once Codex/Gemini delegation is healthy again.

## Findings

- **[MEDIUM]** (scripts/run_refresh.py:126-130, confidence: high) `open(_LOCK_FILE, "w")` raising a non-`BlockingIOError` (e.g. `PermissionError` when `state/` is read-only or `OSError` when disk is full) propagates out of the function with NO Telegram alert. Only `BlockingIOError` is caught. A filesystem issue silently breaks cron without surfacing to Ярослав. Fix: wrap the lock acquisition in a broad `try/except OSError` and alert before re-raising or returning a distinct rc.

- **[MEDIUM]** (scripts/run_refresh.py:112, confidence: med) `_classify`'s `"sqlite" in low or "database" in low or "db" in low.split()` substring match mis-classifies a YouTube API error whose message incidentally mentions "database" (e.g. "Analytics database unavailable"). This sends the operator down the wrong runbook path (DB playbook instead of API playbook). Fix: gate by exception *type* from the RunResult if available, or check for SQLite-specific markers (`sqlite3.`, `OperationalError`, `disk I/O error`). Fall back to API-fail rather than DB-fail when ambiguous (SQLite errors are rarer than API hiccups for this workload).

- **[LOW]** (scripts/run_refresh.py:73-85, confidence: high) The `_bot_token()` parser strips only outermost single-layer quotes (`"value"` / `'value'`), doesn't handle a trailing comment on the same line (`BOT_TOKEN=xxx # prod`), doesn't strip UTF-8 BOM at file start, and will silently skip a BOM-prefixed first line. Not ship-blocking for the one `.env` file we actually read, but worth a regex-based parse or `python-dotenv` import if we start trusting it more broadly.

- **[LOW]** (tests/test_run_refresh.py:1-110, confidence: high) Tests import the module under test as `scripts.run_refresh`, but `pyproject.toml:[tool.setuptools].packages` only lists `["app", "app.lib", "ingest"]`. The test currently works because `pythonpath = ["."]` in `[tool.pytest.ini_options]` makes top-level `scripts/` importable, but this is implicit. Future packaging changes could break the test discovery. Add `scripts` to the setuptools package list (after renaming `scripts/` → `scripts/__init__.py` + entry point) OR document the pytest-only import path explicitly in the spec.

## Observations (non-blocking)

- Timer unit `dashboard-kpi-refresh.timer` uses `OnCalendar=*-*-* 03:30:00 Europe/Minsk` with `Persistent=true` — correct syntax. `AccuracySec=30s` prevents timer drift from spreading across minutes. `Persistent=true` correctly catches up missed ticks after downtime.
- `install_kpi_dashboard.sh` is idempotent: `ln -sfn` force-refreshes the symlink without error on re-run; `systemctl --user enable --now` is idempotent by design; `ss -ltn | grep 127.0.0.1:${PORT}` checks for both the expected bind AND (separately) the absence of `0.0.0.0:${PORT}`, aborting non-zero if the latter ever matches.
- `claude-kpi-dashboard.service` explicitly passes `--host 127.0.0.1` to Flask — grep confirmed no `0.0.0.0` path anywhere in the systemd dir.
- Dual scheduling (in-session `CronCreate` + systemd `.timer`) is correctly gated by the `fcntl.LOCK_EX | LOCK_NB` flock on `state/run_refresh.lock` — concurrent invocations exit 0 silently rather than double-running.
- Direct Bot API curl alert (not MCP) correctly survives Claude-session downtime per task spec + CLAUDE.md "bypass the weakness" discipline.

## Summary

REQUEST_CHANGES on two real bugs (filesystem-error silent propagation; `_classify` heuristic collision) + two polish items. None are deployment-blocking in practice but all are easy to fix in a single r1 commit. The architecture (dual scheduling, direct curl alert, symlinked deploy path, strict 127-only bind) is sound. Merge commit must carry `review-provenance=self (Codex delegation degraded, AGENTS.md playwright-ban applied)` for the F-01 retroactive queue.
