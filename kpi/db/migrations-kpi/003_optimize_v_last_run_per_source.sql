-- Migration 003 — Optimize v_last_run_per_source (task-06 fixup-gemini-r1)
-- Addresses GEM-06-001: replace dual correlated subqueries with a single
-- ROW_NUMBER() window-function pass. SQLite ≥ 3.25 (Oct 2018) supports
-- window functions; project pins SQLite via Python stdlib (3.40+ on the
-- CI image, far above 3.25).
--
-- Behavior preserved exactly:
--   - last_started_jd: max julianday of started_at per (source, source_detail)
--   - last_status: status of the row producing that max
--   - last_run_id: run_id of the row producing that max
--   - total_runs: count of rows in (source, source_detail)
--
-- Tie-breaking (multiple runs at the exact same started_at instant): the
-- ORDER BY adds run_id DESC as a deterministic secondary key. Original view
-- did not specify one; behavior was implementation-dependent. Tests
-- (test_migration_002.py) only exercise distinct timestamps, so no
-- regression in test surface.

DROP VIEW IF EXISTS v_last_run_per_source;

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
