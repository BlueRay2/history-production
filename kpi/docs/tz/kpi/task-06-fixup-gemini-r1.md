# task-06 fixup — Gemini retroactive r1 finding GEM-06-001

**Type:** fix-up cycle (per kpi/docs/tz/kpi/process.md "Recovery protocol")
**Source finding:** `kpi/docs/tz/kpi/reviews/task-06/gemini-round-1.md` (retroactive ACCEPTED with one MED finding)
**Affected commit (now degraded by retroactive finding):** `9db7883`
**Fix migration:** `kpi/db/migrations-kpi/003_optimize_v_last_run_per_source.sql`
**Owner:** Claude (coordinator)
**Created:** 2026-04-27T23:35+03:00 (post-retroactive-audit)

## Finding (verbatim)

> **GEM-06-001: Inefficient correlated subqueries in `v_last_run_per_source`**
> Severity: Medium
> The view `v_last_run_per_source` uses two separate and nearly identical correlated subqueries to fetch the `last_status` and `last_run_id`. Each subquery independently executes a `ORDER BY julianday(...) DESC LIMIT 1` operation for every group produced by the outer query. This is inefficient as it requires multiple scans and sorts over the same data. While acceptable for a small `ingestion_runs` table, this will scale poorly and could become a performance bottleneck.
>
> **Recommendation:** Refactor the view to use a Common Table Expression (CTE) with a window function (`ROW_NUMBER()` or `RANK()`) to determine the latest run for each `(source, source_detail)` group.

## Fix design

**Migration 003** (`kpi/db/migrations-kpi/003_optimize_v_last_run_per_source.sql`) replaces the view with a CTE+`ROW_NUMBER()` implementation:

```sql
DROP VIEW IF EXISTS v_last_run_per_source;
CREATE VIEW v_last_run_per_source AS
WITH ranked AS (
    SELECT
        ir.source, ir.source_detail, ir.status, ir.run_id,
        julianday(ir.started_at) AS started_jd,
        ROW_NUMBER() OVER (
            PARTITION BY ir.source, ir.source_detail
            ORDER BY julianday(ir.started_at) DESC, ir.run_id DESC
        ) AS rn,
        COUNT(*) OVER (PARTITION BY ir.source, ir.source_detail) AS total_runs
    FROM ingestion_runs ir
)
SELECT source, source_detail,
       started_jd AS last_started_jd,
       status     AS last_status,
       run_id     AS last_run_id,
       total_runs
FROM ranked
WHERE rn = 1;
```

**Behavior preservation:** Equivalence verified empirically with seeded `ingestion_runs` data — original-vs-new view produce byte-identical rowsets (script: `python3 -c "..."` in commit message).

**SQLite version requirement:** ≥ 3.25 (Oct 2018) for window functions. Project Python stdlib bundles SQLite 3.40+ on the CI image, comfortably above the floor.

**Tie-breaking:** Original view's `MAX(julianday(started_at))` plus separate scalar subqueries had implementation-dependent tie-break for two runs at identical `started_at`. New view explicitly tie-breaks by `run_id DESC`, deterministic. No existing test exercises the tie case.

## Review loop (per process.md)

1. ~~Implement~~ — done in this commit.
2. **Dispatch parallel review (round 1):**
   - Codex via `scripts/codex-tracked-exec.sh` → `kpi/docs/tz/kpi/reviews/task-06-fixup/codex-round-1.md`.
   - Gemini via `scripts/gemini-agent.sh review` → `kpi/docs/tz/kpi/reviews/task-06-fixup/gemini-round-1.md`.
3. Merge findings into single fix commit if any.
4. Both accept → merge fast-forward into `kpi`.

## Out of scope

- Optimization of other views (`v_metric_freshness`, `v_video_coverage_7d`, `v_quota_today`) — separate task if performance becomes an issue (ingestion_runs scales fastest of the four).
- Index tuning on `ingestion_runs(source, source_detail, started_at)` — optional follow-up; depends on cardinality observed after backfill.
