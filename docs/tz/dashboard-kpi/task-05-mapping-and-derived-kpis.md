# task-05 — Mapping + derived KPIs

**Status:** `pending`
**Dep:** 03, 04
**Risk:** High

## Scope

1. `app/services/mapping.py`:
   - `suggest_mappings()` — joins unmapped `videos` rows with unmapped `projects` via:
     - Normalized slug match (`slugify(video.title) in city_slug` or reverse).
     - Publish-date proximity (within 7d of first `script_finished` event).
   - Emits `video_project_map` rows with `confidence`, `mapping_source='auto'`.
   - CLI: `python -m app.services.mapping review` — shows pending auto-suggestions for manual approval (writes rows with `active=0` until approved via `--approve <video_id> <city_slug>`).
   - Manual-override path: `active=1` always wins over auto-suggestions.
2. `app/services/kpis.py` + `app/sql/views/`:
   - `v_weekly_scripts_finished` — count of `script_finished` events per ISO week.
   - `v_cycle_time_days` — `published_at - first_scaffold_commit_at` per mapped video.
   - `v_script_iterations_approx` — count of `revision` events between `script_started` and `script_finished` per city.
   - `v_cost_per_video` — LEFT JOIN `cost_parse` output; NULL when fail-closed.
   - `v_weekly_channel_kpis` — impressions, CTR, AVD, AVP, retention-summary from `channel_metric_snapshots` latest-per-week.
   - `v_monthly_channel_kpis` — subs-gained/lost, RPM, revenue, top-performers by composite score.
3. Composite score formula (for "Top performers"): normalized z-score across (views_30d, retention_avg, subs_gained_per_video) equal-weighted.

## Test plan

- `tests/test_kpis.py`: fixture DB with 3 mapped videos + 2 unmapped → all views return expected shapes.
- `tests/test_mapping.py`: auto-suggestion from fixture videos; manual override precedence.
- `tests/test_missing_map_exclusion.py`: unmapped videos excluded from per-video KPI views.
- `tests/test_cost_fail_closed.py`: video with no COST_ESTIMATE.md → cost KPI returns NULL (not 0, not error).

## Files touched

- `app/services/__init__.py`, `app/services/mapping.py`, `app/services/kpis.py` (new)
- `app/sql/views/v_*.sql` (new)
- `tests/test_kpis.py`, `tests/test_mapping.py`, `tests/test_missing_map_exclusion.py`, `tests/test_cost_fail_closed.py` (new)

## Review loop

- [ ] Codex round-1 → `reviews/task-05/codex-round-1.md`
- [ ] Gemini round-1 → `reviews/task-05/gemini-round-1.md`
- [ ] `ready-to-merge` | `ready-to-merge (gemini-degraded)`
- [ ] `merged`
