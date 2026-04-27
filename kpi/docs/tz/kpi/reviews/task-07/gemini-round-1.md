# Round 1 Review

## Verdict
request changes

## Findings

- **HIGH** | `kpi/app/monitoring/routes.py:126` (and `freshness.html`, `_freshness_drilldown.html`): **Missing filters on `/freshness`.** The spec dictates a filter bar to search "by metric_key prefix (search), by status (only show stale >Nd), by dimension prefix (when drill-down expanded)". The implementation only supports `q` (metric prefix). The status dropdown and the drill-down dimension search are completely missing from both the frontend templates and the backend SQL queries.
  - *Recommendation:* Add the missing HTML inputs for `status` and dimension prefix. Update `freshness()` and `freshness_drilldown()` to parse these parameters and append the appropriate `WHERE` conditions.
- **MED** | `kpi/tests/test_monitoring.py:72`: **Missing `ro-mode` test.** The 13 tests cover the paths, health logic, schema drift, and string filtering, but there is no explicit test enforcing database safety against writes. The read-only connection logic (`_db()`) could regress without triggering a test failure.
  - *Recommendation:* Add an edge-case test (`test_ro_mode_write_attempt`) that fetches `_db()` and attempts to execute a destructive query (`INSERT`/`UPDATE`), asserting that it correctly raises a `sqlite3.OperationalError` for read-only databases.
- **MED** | `kpi/systemd/claude-kpi-monitoring.service:5`: **Missing `User=` directive.** This unit lacks a `User=` parameter. Unless deployed as a user-level service (`~/.config/systemd/user/`), it will run as `root` which accesses the `aiagent` user's home directory. This is a security risk and violates the principle of least privilege.
  - *Recommendation:* Explicitly set `User=aiagent` (or another appropriate user) in the `[Service]` section.
- **LOW** | `kpi/app/monitoring/routes.py:84` vs `routes.py:307`: **Discrepancy in `degraded` health logic.** In the UI (`/`), the `degraded` state relies on checking if the latest non-ok run was within the last 24 hours (`<= 24`). In `/api/health`, it marks as `degraded` if the latest run is *ever* non-ok, regardless of age. 
  - *Recommendation:* Unify the logic between the visual badge and the JSON API payload to prevent inconsistent health reports across different monitoring endpoints.

## Notes
- **Spec Coverage:** Besides the freshness filters, the remaining features—24h summary, quota usage visualization, schema drift logs, error tables, and video coverage matrices—are cleanly and correctly implemented to spec. The "stale red" highlighting logic for videos accurately respects the `< 90 days` and zero metrics condition.
- **DB Safety:** `_db()` correctly sets `?mode=ro` locally, safeguarding the metrics database against rogue writes. The standalone writable connection in `/schema-drift/<id>/ack` safely binds the user ID parameter, ensuring zero SQL injection.
- **Frontend Security:** Jinja autoescaping handles typical XSS injection paths. Null-safety mappings like `r.notes or '—'` and `r.source_detail or '—'` successfully intercept potential `NoneType` rendering errors in UI templates.
inconsistency in the interpretation of "degraded" status.
*   **Recommendation**: Align the definition of "degraded" status between the `/` summary page and the `/api/health` endpoint. Either remove the `_hours_since(...) <= 24` condition from the `index` route's `any_recent_non_ok` check, or update the spec to reflect that `degraded` status on the `/` page specifically refers to *recent* non-`ok` runs.

## Notes
*   **DB Safety**: The use of `f"file:{path}?mode=ro"` for read-only connections and explicit writable connections for `/schema-drift/<id>/ack` is well-implemented and secure against accidental writes. Parameterized queries are correctly used for all database interactions, preventing SQL injection. The `id` validation for `/schema-drift/<id>/ack` is also well handled.
*   **Templates**: Jinja2's default autoescaping is correctly leveraged for XSS protection. Null-safety for data fields (`r.notes`, `r.error_text`, `r.source_detail`) is handled appropriately in both `routes.py` and the templates. The conditional red highlighting in `videos.html` aligns with the specification.
*   **systemd unit**: The `systemd` unit file is correctly configured with `WorkingDirectory`, `ExecStart`, `Restart=on-failure`, and appropriate log paths. The absence of a `User=` directive is intentional and consistent with running as the session-scope user (`aiagent`).
*   **Spec Coverage (Positive)**: All specified pages and the `/api/health` endpoint are implemented as routes. The content and logic for each page (except the `/freshness` filter) largely align with the specification, including health badge rules and video highlighting logic.
