# Round 1 Review

## Verdict

request changes

## Findings

- **HIGH** `kpi/app/monitoring/routes.py:442` — `/api/health` treats `running` as healthy via `status NOT IN ('ok','running')`. The spec says degraded if any latest per-source run is non-`ok`, so a stuck latest `running` source can report `ok`. Recommendation: only exclude `ok`, and add a regression test for latest `running`.

- **MED** `kpi/app/monitoring/templates/base.html:10` — Badge CSS uses Tailwind `@apply` inside a normal `<style>` tag. With Tailwind CDN this should be `type="text/tailwindcss"` or replaced with direct utility classes; otherwise required green/yellow/orange/red status badges may render unstyled.

- **MED** `kpi/app/monitoring/routes.py:188` / `kpi/app/monitoring/templates/freshness.html:6` — `/freshness` is missing required spec controls/fields: no `last_obs_jd` timestamp column, no status/stale filter, no dimension-prefix filter in drilldown, and no “show all” path beyond top-30 dimensions. Recommendation: add the missing filters and timestamp display.

- **MED** `kpi/app/monitoring/routes.py:394` / `kpi/app/monitoring/templates/errors.html:27` — `/errors` does not implement the required click-row modal showing full `error_text` plus `run_id`; the route truncates `error_text` to 200 chars before rendering and the template never displays `run_id`. Recommendation: keep full error text in row data and add the modal behavior.

- **LOW** `kpi/app/monitoring/routes.py:333` — `/schema-drift/<id>/ack` is SQL-injection safe and id-validated by `<int>` plus bound parameters, but already-acknowledged rows are not idempotent in the audit sense: repeat POST overwrites `acknowledged_at`/`acknowledged_by`. Recommendation: update only where `acknowledged_at IS NULL`, still returning `204` for existing acknowledged rows.

- **LOW** `kpi/app/monitoring/routes.py:29` — `_db()` falls back to a plain writable SQLite connection when `KPI_DB` does not already exist. No read route writes through it, but the app does not strictly “open KPI_DB in mode=ro”. Recommendation: always use `file:...?mode=ro` and fail fast if the DB is missing.

- **LOW** `kpi/app/monitoring/templates/quota.html:34` — `series_json|safe` bypasses Jinja’s autoescape inside a script. The data is likely internal, but `tojson` is the safer Jinja-native pattern for script literals.

- **LOW** `kpi/tests/test_monitoring.py:99` — The 13 tests cover smoke, degraded, no-orchestrator down, ack 204/404, and `q` freshness filtering, but miss key edge cases: latest `running` health classification, last orchestrator `>26h`, read-only connection/write attempt, ack repeat idempotency, missing freshness filters, and the errors modal.

## Notes

DB writes are scoped to the ack route; schema-drift list filters and ack SQL use bound parameters. Jinja autoescape is on for `.html` templates, and null handling for `notes`, `error_text`, and `source_detail` is mostly safe.

`videos.html` row-level red tint follows the “published in last 90 days and zero metrics in 7d” interpretation. The systemd unit has the expected working directory, port/host env, `Restart=on-failure`, and append log paths; no `User=` is acceptable if installed as a user/session unit for `aiagent`.

I could not run the local tests because the shell sandbox failed before command execution, so this is a static review against commit `2a0505f`.
