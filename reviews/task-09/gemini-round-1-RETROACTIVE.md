# Round 1 RETROACTIVE Review — task-09-baseline-calibration (Gemini-3.1-pro)

**Reviewer:** Gemini-3.1-pro (retroactive, after Codex+capacity returned)
**Verdict:** REQUEST_CHANGES

## Findings

- **[HIGH]** `auto_compute_thresholds()` mixes metrics across different time grains (app/services/calibration.py:197-201, confidence: high). The SQL query filters by `metric_key` but omits `grain`. This dumps `daily`, `weekly`, and `monthly` values for the same metric into a single array before computing percentiles, resulting in mathematically nonsensical threshold bands.
  *Fix:* Add `AND grain = 'weekly'` (or parameterize by grain) to the `WHERE` clause.

- **[HIGH]** `weeks_of_data()` overcounts by collapsing all metrics and grains (app/services/calibration.py:155-156, confidence: high). `COUNT(*) AS n_snapshots` groups only by week. A single ingestion run inserts multiple metrics (CTR, AVD, etc.), meaning 1 day of data easily produces 5+ rows. This satisfies `HAVING n_snapshots >= 5` in just one day, falsely clearing the calibration gate.
  *Fix:* Count distinct days instead of raw rows (`COUNT(DISTINCT substr(observed_on, 1, 10)) >= ?`), or restrict the CTE to a single representative metric and grain.

- **[MED]** SQLite `%W` splits contiguous ISO weeks at year boundaries (app/services/calibration.py:154, confidence: high). `strftime('%Y-W%W', observed_on)` uses `%W` (00-53) with `%Y`. Days in the same ISO week spanning Dec 31 / Jan 1 are bucketed into different weeks (e.g., `2024-W53` and `2025-W00`), causing that week to fall below the snapshot threshold.
  *Fix:* Normalize dates to the week's Monday before formatting, e.g., `strftime('%Y-%m-%d', observed_on, 'weekday 1', '-7 days')`.

- **[MED]** `auto_compute_thresholds()` overwrites `calibration.start_date` (app/services/calibration.py:234, confidence: high). The generated YAML unconditionally sets `start_date` to `datetime.now().date()`. When `.proposed` is adopted, the original installation date set by `install_kpi_dashboard.sh` is permanently erased.
  *Fix:* Read the existing config or pass the original `start_date` into the function so it can be preserved in the new YAML.

- **[LOW]** Divergent source of truth for `REQUIRED_WEEKS` (app/services/calibration.py:206, confidence: high). `load_status()` reads `required_weeks` from the YAML, but `auto_compute_thresholds()` hardcodes the `REQUIRED_WEEKS` constant. If the YAML is updated to require 6 weeks, auto-compute still validates against 4.
  *Fix:* Pass the required weeks value into `auto_compute_thresholds()`.

## Observations (non-blocking)

- The custom YAML parser (`_load_yaml`) gracefully ignores improperly indented lines and safely falls back if list syntax is encountered. The prior self-review correctly identified this as a known, acceptable residual risk.
- The dual-gate activation (`is_activated` requires both data and config boolean) successfully implements the Goodhart-trap defense specified in F-06.
- The `app/main.py` exception fallback is robust: if `kpi-thresholds.yaml` is missing entirely, `load_status()` safely returns a default deactivated state, keeping the UI banner active.

## Disagreements with self-review

- **Data accumulation gate correctness:** The self-review stated `weeks_of_data()` "correctly counts only non-preliminary weeks". This is false; because of the `COUNT(*)` without a grain/metric filter, it will advance a "week" after a single day's ingestion.
- **Threshold mathematical safety:** The self-review praised the `_percentile` function but missed that the input array mixes incompatible timeline grains (`daily` vs `weekly`), rendering the output bands completely invalid. 
- **Configuration state transitions:** The self-review missed the state loss bug where computing new thresholds overwrites the initial dashboard start date.
