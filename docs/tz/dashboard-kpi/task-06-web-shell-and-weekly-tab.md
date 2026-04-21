# task-06 — Web shell + Weekly tab

**Status:** `pending`
**Dep:** 05
**Risk:** Medium

## Scope

1. `app/main.py` — Flask app factory:
   - Binds to `127.0.0.1:<port>` (env `DASHBOARD_KPI_PORT`, default 8787).
   - No auth (MVP localhost-only).
   - Routes: `/` (redirects to `/weekly`), `/weekly`, `/monthly` (stub in this task), `/exceptions`.
2. `templates/base.html`:
   - Tabs: Weekly / Monthly.
   - Nav shows calibration banner if `v_channel_age_days < 28`: "Baseline calibration in progress (N/4 weeks) — thresholds inactive".
   - HTMX for tab switching (no full page reload).
3. `templates/weekly.html`:
   - Top row: 6 metric cards (Impressions, CTR, AVD, AVP, Retention-avg, Scripts-finished).
   - Each card: current value + WoW delta (hidden if no baseline).
   - Retention curves chart (Chart.js small multiples, one line per video published in window).
   - Exceptions panel: unmapped videos count + link to `/exceptions`.
4. `app/services/weekly_view.py` — data assembly from task-05 views.
5. `templates/exceptions.html` — list of unmapped videos + low-confidence `video_project_map` rows + "Approve" / "Reject" buttons (HTMX POST to `/mapping/approve`).

## Test plan

- `tests/test_dashboard_views.py`: seeded DB → each route renders 200 + contains expected metric labels.
- `tests/test_empty_state.py`: empty DB → routes render empty-state messages, no stack traces.
- `tests/test_calibration_banner.py`: channel_age < 28d → banner visible; ≥28d → hidden.

## Files touched

- `app/main.py`, `app/services/weekly_view.py` (new)
- `templates/base.html`, `templates/weekly.html`, `templates/exceptions.html`, `templates/_card.html` (new partial)
- `static/style.css`, `static/app.js` (new; vanilla JS only for local widget state per consensus)
- `tests/test_dashboard_views.py`, `tests/test_empty_state.py`, `tests/test_calibration_banner.py` (new)
- `pyproject.toml` (add `flask`, `jinja2`)

## Review loop

- [ ] Codex round-1 → `reviews/task-06/codex-round-1.md`
- [ ] Gemini round-1 → `reviews/task-06/gemini-round-1.md`
- [ ] `ready-to-merge` | `ready-to-merge (gemini-degraded)`
- [ ] `merged`

## UX notes (per consensus DX simulation)

- "What's missing that Настя needs" — `RECENT_PUBLISHES` widget with last 5 videos + publish date + week-1 performance snapshot (from `research/claude.md#8`). Deferred to task-07 if time-boxed.
