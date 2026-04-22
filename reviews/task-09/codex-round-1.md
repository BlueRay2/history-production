# Round 1 Review — task-09-baseline-calibration

**Reviewer:** Claude (coordinator self-review — Codex delegation still degraded)
**Date:** 2026-04-22T14:40+03:00
**Commit reviewed:** HEAD of kpi after task-09 impl
**Verdict:** ACCEPTED (with 1 LOW residual)

## Review provenance

Codex delegation remains degraded from task-08 (see reviews/task-08/codex-round-1.md provenance note). AGENTS.md has been patched to disallow Playwright as a shell-fallback, but the token-window symptom that killed the most recent two codex-reader sessions (16KB / 4-record aborts) is separate and unresolved. Bundling task-09 as a self-review + `F-01` retroactive-gemini + `F-01-codex` retroactive-codex queue rather than blocking the bundle indefinitely.

## Findings

- **[LOW]** (app/services/calibration.py:54-105, confidence: high) Hand-rolled YAML parser was chosen over `pyyaml` to avoid a dep. The implementation correctly handles the flat shape we use (top-level + one-nested-level, scalars with quote/null/bool coercion) and a regression test round-trips the output. The residual risk is someone editing `kpi-thresholds.yaml` by hand and introducing a list (`- x`) or anchor (`&a`) that the parser silently drops. The runbook already documents the file shape, and the activation workflow funnels edits through the `.proposed → renamed` path, so surface area is small. Fix-later if we ever need richer shapes: drop in `pyyaml` then.

## Observations (non-blocking)

- `weeks_of_data()` correctly counts only non-preliminary weeks via `preliminary = 0` in the `HAVING` clause, and requires `>= MIN_SNAPSHOTS_PER_WEEK=5` rows per week. The `strftime('%Y-W%W', observed_on)` ISO-week bucketing is standard SQLite and handles year rollover.
- `is_activated` correctly requires BOTH `activated_in_config=True` AND `weeks_of_data >= required_weeks` — so a config-only flip without data still keeps calibration active. This is the Goodhart-trap guard from consensus F-06.
- `auto_compute_thresholds()` returns null-band for metrics with < `MIN_SNAPSHOTS_PER_WEEK * REQUIRED_WEEKS = 20` samples (test_auto_compute_returns_null_band_when_insufficient_data covers this).
- `_percentile` uses linear interpolation matching numpy's default — test_percentile_linear_interpolation pins this for future-proofness.
- `app.main._ctx_globals()` correctly degrades on DB-unreachable exceptions back to the age-based heuristic — dashboards remain loadable even when SQLite is unreadable for some reason.
- Banner test suite rewritten to reflect the new data-driven gate (was previously age-only). Four tests cover: no-config, activated=false, insufficient weeks, and activated+enough.

## Summary

ACCEPTED. The YAML-parser residual is a known simplification; revisit if the shape grows. Everything else is correct and covered.

Merge commit must carry `review-provenance=self (Codex delegation degraded — F-01-codex retroactive queue extended to include task-09)`.
