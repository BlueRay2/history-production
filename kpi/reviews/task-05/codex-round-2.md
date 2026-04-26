# Codex Round 2 Review — task-05-mapping-and-derived-kpis

**Reviewer:** codex
**Date:** 2026-04-22T07:40+03:00
**Commit reviewed:** 16c0d6c
**Verdict:** REQUEST_CHANGES
**Extraction:** Verbatim agent_message from codex-reader MCP session (read-only sandbox, saved by coordinator).

## Findings

- **[HIGH]** (app/services/kpis.py:325-345, confidence: high) `top_performers()` still does not implement the aligned-window rule its comment describes. The `aligned` CTE groups only by `(window_start, window_end)` and checks `COUNT(DISTINCT metric_key) = 3`, so it will treat a window as valid even when `views`, `averageViewPercentage`, and `subscribersGained` are split across different videos. `pivoted` then drops every video in that window, and the query returns no performers instead of falling back to the latest window where at least one video has the full metric triplet. Example: W2 has `views` on `v1`, `averageViewPercentage` on `v2`, `subscribersGained` on `v3`; W1 has all three on `v4`. Current SQL picks W2 and excludes W1 entirely.

## Summary

The other five r1 findings look credibly resolved on this commit, but the aligned-window fix in `top_performers()` is still incomplete, so task-05 is not ready to accept yet.

Local test rerun was not possible in this sandbox; verdict is based on code inspection of 16c0d6c.
