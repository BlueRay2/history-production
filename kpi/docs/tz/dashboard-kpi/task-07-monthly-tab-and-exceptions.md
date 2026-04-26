# task-07 — Monthly tab + exceptions panel

**Status:** `pending`
**Dep:** 06
**Risk:** Medium

## Scope

1. `templates/monthly.html`:
   - Top row: 6 metric cards (Net New Subs, Sub Conversion Rate, RPM, Revenue 30d, Top-Performer-score, Cost-per-video-avg).
   - Subs growth sparkline (12-month rolling).
   - Top-3 performers table (from `v_monthly_channel_kpis`): thumbnail, title, composite score, views/retention/subs.
   - Cost-per-video distribution histogram with "(estimated)" label.
   - Script-iterations-approx histogram.
2. `app/services/monthly_view.py` — data assembly.
3. `templates/exceptions.html` enhancements (from task-06 stub):
   - Separate sections: Unmapped videos / Low-confidence mappings / Missing COST_ESTIMATE.md totals / Unclassified git events.
   - `/mapping/approve` and `/mapping/reject` HTMX endpoints in `app/main.py`.
   - `/exceptions/cost_templates` — list of cities with parse-fail cost estimates (F-02 backlog surface).
4. RECENT_PUBLISHES widget (bumped from task-06): last 5 videos, publish date, week-1 performance — surfaced on both tabs.

5. **Sparse-metric rendering (J-03 resolution, same standard as task-06):** all Monthly metric cards use `repositories.metrics.value_with_reason()`. Same four states: `ok / below_privacy_floor / channel_too_new / no_data_pulled`. Top-performers table excludes videos with any NULL composite-score input (not ranks them as 0).

6. **Exceptions panel — expanded (J-03):** adds a `Sparse-metrics gated` section listing all (metric × video|channel) pairs currently below privacy floors with explicit reason. Helps Ярослав/Насте видеть что именно «пока скрыто» и знать чего ждать при росте канала.

## Test plan

- `tests/test_monthly_view.py`: seeded DB → `/monthly` renders all sections.
- `tests/test_mapping_approval.py`: POST `/mapping/approve` → row becomes `active=1`, dashboard excludes from exceptions.
- `tests/test_recent_publishes.py`: widget shows correct 5 videos.

## Files touched

- `app/services/monthly_view.py` (new)
- `templates/monthly.html` (new)
- `templates/exceptions.html` (update)
- `templates/_recent_publishes.html` (new partial)
- `app/main.py` (add mapping endpoints)
- `tests/test_monthly_view.py`, `tests/test_mapping_approval.py`, `tests/test_recent_publishes.py` (new)

## Review loop

- [ ] Codex round-1 → `reviews/task-07/codex-round-1.md`
- [ ] Gemini round-1 → `reviews/task-07/gemini-round-1.md`
- [ ] `ready-to-merge` | `ready-to-merge (gemini-degraded)`
- [ ] `merged`
