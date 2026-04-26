# task-09 — Baseline calibration gate

**Status:** `pending`
**Dep:** 08
**Risk:** Small (code ships; activation is time-bound 4 weeks after install)

## Scope

1. `config/kpi-thresholds.yaml.sample`:
   ```yaml
   # Populated after 4 weeks of calibration data.
   channel_ctr:
     green_above: null   # e.g. 0.055
     yellow_above: null  # e.g. 0.045
     red_below: null     # e.g. 0.035
   channel_avp:
     green_above: null
     yellow_above: null
     red_below: null
   # ... for each metric
   calibration:
     start_date: "YYYY-MM-DD"
     required_weeks: 4
     activated: false
   ```
2. `app/services/calibration.py`:
   - `weeks_of_data() -> int` — count of full ISO weeks where `channel_metric_snapshots` has ≥5 preliminary-cleared rows.
   - `is_activated() -> bool` — reads `config/kpi-thresholds.yaml`, returns `calibration.activated` AND `weeks_of_data() >= 4`.
   - `auto_compute_thresholds()` — when weeks_of_data hits 4, computes `green/yellow/red` as percentile bands (25/50/75) of observed values; writes proposed values to `config/kpi-thresholds.yaml.proposed` for Ярослав manual approval.
3. UI impact:
   - `templates/base.html` banner: shows "Baseline calibration in progress (N/4 weeks)" while `is_activated() == False`.
   - Metric cards: R/Y/G background suppressed; shows raw value only.
   - Once activated: cards get R/Y/G backgrounds per thresholds.
4. Activation workflow (documented in runbook):
   - Week 4 cron detects `weeks_of_data() == 4` → writes `config/kpi-thresholds.yaml.proposed` → sends Ярослав Telegram DM with diff.
   - Ярослав reviews, edits if needed, renames to `config/kpi-thresholds.yaml`, sets `calibration.activated: true`.
   - Dashboard auto-picks up on next request.

## Test plan

- `tests/test_calibration.py`: seeded DB with 3 weeks → `is_activated() == False`; 4 weeks → proposed thresholds written.
- `tests/test_banner.py`: activation flag flips → banner hidden, card colors appear.
- `tests/test_auto_compute.py`: fixture metric values → expected percentile bands.

## Files touched

- `config/kpi-thresholds.yaml.sample` (new)
- `app/services/calibration.py` (new)
- `templates/base.html` (update — banner)
- `templates/_card.html` (update — threshold coloring)
- `tests/test_calibration.py`, `tests/test_banner.py`, `tests/test_auto_compute.py` (new)

## Review loop

- [ ] Codex round-1 → `reviews/task-09/codex-round-1.md`
- [ ] Gemini round-1 → `reviews/task-09/gemini-round-1.md`
- [ ] `ready-to-merge` | `ready-to-merge (gemini-degraded)`
- [ ] `merged`

## Why this is last

F-06 from consensus findings: shipping R/Y/G on a 4-week-old channel = Goodhart trap. The gate code must exist from day 1 (not retrofitted) so the dashboard never shows fake confidence during calibration.
