# Gemini r1 Review — task-06-fixup-gemini-r1
**Reviewer:** Gemini
**Verdict:** ACCEPTED

## Summary

This review verifies the fix for finding `GEM-06-001`, which identified a performance issue in the `v_last_run_per_source` view. The original implementation used two inefficient correlated subqueries to retrieve the status and `run_id` of the last ingestion run. The fix, applied in migration `003_optimize_v_last_run_per_source.sql`, refactors the view to use a window function (`ROW_NUMBER()`) for improved performance and determinism.

## Findings

**Status:** ACCEPTED

The finding `GEM-06-001` is properly addressed. The new implementation of the `v_last_run_per_source` view is functionally equivalent, more performant, and more robust.

**Finding `GEM-06-001`:** Inefficient correlated subqueries in `v_last_run_per_source`.

**Resolution:**
- The two correlated subqueries were replaced with a single Common Table Expression (CTE) using the `ROW_NUMBER()` window function.
- This change is a standard and effective optimization for this class of query.
- The new implementation also introduces a deterministic tie-breaker (`run_id DESC`) when multiple runs have the exact same timestamp, which is an improvement over the original's implementation-dependent behavior.
- The migration is safely implemented using `DROP VIEW IF EXISTS`, making it idempotent.

## Evidence

**Original View Definition (from `002_monitoring.sql`):**
```sql
CREATE VIEW v_last_run_per_source AS
SELECT
    ir.source,
    ir.source_detail,
    MAX(julianday(ir.started_at))                                  AS last_started_jd,
    (SELECT r2.status
       FROM ingestion_runs r2
      WHERE r2.source = ir.source
        AND r2.source_detail IS ir.source_detail
      ORDER BY julianday(r2.started_at) DESC
      LIMIT 1)                                                     AS last_status,
    (SELECT r2.run_id
       FROM ingestion_runs r2
      WHERE r2.source = ir.source
        AND r2.source_detail IS ir.source_detail
      ORDER BY julianday(r2.started_at) DESC
      LIMIT 1)                                                     AS last_run_id,
    COUNT(*)                                                       AS total_runs
FROM ingestion_runs ir
GROUP BY ir.source, ir.source_detail;
```

**New View Definition (from `003_optimize_v_last_run_per_source.sql`):**
```sql
CREATE VIEW v_last_run_per_source AS
WITH ranked AS (
    SELECT
        ir.source,
        ir.source_detail,
        ir.status,
        ir.run_id,
        julianday(ir.started_at) AS started_jd,
        ROW_NUMBER() OVER (
            PARTITION BY ir.source, ir.source_detail
            ORDER BY julianday(ir.started_at) DESC, ir.run_id DESC
        ) AS rn,
        COUNT(*) OVER (
            PARTITION BY ir.source, ir.source_detail
        ) AS total_runs
    FROM ingestion_runs ir
)
SELECT
    source,
    source_detail,
    started_jd  AS last_started_jd,
    status      AS last_status,
    run_id      AS last_run_id,
    total_runs
FROM ranked
WHERE rn = 1;
```

## Commands
```sh
# Locate the codex review to get context on the fix
read_file kpi/docs/tz/kpi/reviews/task-06-fixup/codex-round-1.md

# Find the relevant migration directory
read_file kpi/app/db_kpi.py

# List the migration files
list_directory kpi/db/migrations-kpi/

# Read the new migration file
read_file kpi/db/migrations-kpi/003_optimize_v_last_run_per_source.sql

# Read the previous migration file to see the original view
read_file kpi/db/migrations-kpi/002_monitoring.sql
```

## Risks

None. The change is a standard SQL optimization and is well-contained within a database migration. The use of `DROP VIEW IF EXISTS` ensures the migration is safe to re-run. The SQLite version compatibility was noted and addressed in the migration's comments.

## Recommended Handoff

Handoff to Claude for final integration. The fix is accepted.
