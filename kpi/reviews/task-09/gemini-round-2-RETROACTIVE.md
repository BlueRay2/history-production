# Round 2 RETROACTIVE Review — task-09-baseline-calibration (Gemini-3.1-pro)

**Reviewer:** Gemini-3.1-pro R2
**Verdict:** REQUEST_CHANGES

## Findings resolution
- R1-HIGH 1 (grain mix): resolved
- R1-HIGH 2 (weeks_of_data row vs day): resolved
- R1-MED 1 (ISO week boundary): resolved
- R1-MED 2 (start_date erasure): partially (The `auto_compute_thresholds` function now accepts an `existing_config_path` argument to preserve the date, but there is no evidence in the diff that callers were updated to actually pass it.)
- R1-LOW (REQUIRED_WEEKS divergent SOT): partially (The function accepts a `required_weeks` override, but without caller updates to pass the YAML's value, it defaults to the module constant and will still overwrite the user's YAML setting back to 4 in the proposed file.)

## New findings (regressions or newly visible, max 3)
- **[MED] Missing caller updates render fixes inert:** The fixes for configuration state preservation (start date erasure and divergent REQUIRED_WEEKS) rely entirely on new optional parameters (`existing_config_path`, `required_weeks`). Because the callers orchestrating the calibration check (e.g., the cron job/scripts) were not updated to read the current YAML state and pass these arguments, the original bugs will still silently manifest in production. The callers must be updated to utilize these parameters.

## Verdict rationale
The SQL analytical fixes for the grain mix and date bounding are excellent, mathematically sound, and elegantly resolve the core aggregation flaws. However, the configuration state preservation fixes are effectively dead code. Because the callers were not updated to pass the new parameters, `auto_compute_thresholds` will still permanently erase the dashboard's install date and override user-configured week requirements upon generation. Changes are requested to complete the fix by updating the caller(s).
