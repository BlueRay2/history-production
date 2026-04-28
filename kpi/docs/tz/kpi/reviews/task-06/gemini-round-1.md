# Round 1 Review — task-06-monitoring-schema (RETROACTIVE)
**Reviewer:** Gemini
**Date:** 2026-04-27 (retroactive)
**Commit:** 9db7883
**Verdict:** NEEDS_CHANGES

## Findings (1)

| ID | Severity | Location | Summary |
|---|---|---|---|
| GEM-06-001 | Medium | `kpi/db/migrations-kpi/002_monitoring.sql` | Inefficient correlated subqueries in `v_last_run_per_source` view. |

### GEM-06-001: Inefficient correlated subqueries in `v_last_run_per_source`

**Severity:** Medium

**Description:**
The view `v_last_run_per_source` uses two separate and nearly identical correlated subqueries to fetch the `last_status` and `last_run_id`. Each subquery independently executes a `ORDER BY julianday(...) DESC LIMIT 1` operation for every group produced by the outer query. This is inefficient as it requires multiple scans and sorts over the same data. While acceptable for a small `ingestion_runs` table, this will scale poorly and could become a performance bottleneck.

**Recommendation:**
Refactor the view to use a Common Table Expression (CTE) with a window function (`ROW_NUMBER()` or `RANK()`) to determine the latest run for each `(source, source_detail)` group. This approach would scan and sort the data only once, making the view significantly more performant.

**Example (suggested):**
```sql
CREATE VIEW v_last_run_per_source AS
WITH ranked_runs AS (
    SELECT
        ir.*,
        ROW_NUMBER() OVER(PARTITION BY ir.source, ir.source_detail ORDER BY julianday(ir.started_at) DESC) as rn
    FROM ingestion_runs ir
)
SELECT
    r.source,
    r.source_detail,
    julianday(r.started_at) AS last_started_jd,
    r.status AS last_status,
    r.run_id AS last_run_id,
    (SELECT COUNT(*) FROM ingestion_runs ir_count
     WHERE ir_count.source = r.source AND ir_count.source_detail IS r.source_detail) AS total_runs
FROM ranked_runs r
WHERE r.rn = 1;
```
*(Note: `total_runs` still requires a subquery or a separate CTE, but the primary performance issue of sorting is resolved.)*

## Verdict rationale (2-4 sentences)

The commit successfully implements the required schema changes and derived views specified in task-06. The Python tests are comprehensive, covering view logic, constraints, and migration idempotency, which is excellent. However, the verdict is `NEEDS_CHANGES` due to a notable performance issue in the `v_last_run_per_source` view, which uses expensive and redundant correlated subqueries. Fixing this will ensure the monitoring queries remain efficient as the dataset grows.
