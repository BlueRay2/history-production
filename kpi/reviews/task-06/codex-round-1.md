# Codex Round 1 Review — task-06-web-shell-and-weekly-tab

**Reviewer:** codex
**Date:** 2026-04-22T07:53+03:00
**Commit reviewed:** 1027991
**Verdict:** REQUEST_CHANGES
**Extraction:** Verbatim agent_message from codex-reader MCP session (read-only sandbox).

## Findings

- **[HIGH]** (app/services/weekly_view.py:136-148, templates/weekly.html:25-27, static/app.js:8-10) `retention_curves[*]["points"]` is built as `list(conn.execute(...))`, i.e. `sqlite3.Row` objects. Once any `video_retention_points` exist, `snap.retention_curves|tojson` will not serialize that shape, so `/weekly` will 500 before Chart.js runs. Even aside from serialization, the JS expects positional arrays (`p[0]`, `p[1]`), not row objects. Convert points to plain tuples/lists or dicts in Python and keep the JS/data contract consistent.

- **[MEDIUM]** (app/services/weekly_view.py:21-26) The weekly KPI set is wrong for the task spec. The spec calls for `Impressions / CTR / AVD / AVP / Retention-avg / Scripts-finished`, but this commit renders `Views` in the fifth slot instead of `Retention-avg`. The page has six cards total only because `Scripts finished` is added separately in the template.

- **[MEDIUM]** (tests/test_calibration_banner.py:18-23, tests/test_empty_state.py:69-89) These tests depend on the real clock. `test_banner_visible_when_channel_under_28_days` stops being true on 2026-05-10, and `test_channel_too_new_reason_renders` stops being true on 2026-05-01. They need a frozen/injected `today`, otherwise the suite will fail just by time passing.

## Observations (non-blocking)

- `app/main.py:141-144` does bind explicitly to `127.0.0.1`; I do not see any `0.0.0.0` path in this commit.
- WoW math in `app/services/weekly_view.py:51-90` looks correct: prior bounds are the immediately preceding 7-day window, and zero/missing baselines suppress the delta instead of dividing by zero.
- The approve/reject routes in `app/main.py:104-118` delegate to task-05's `approve_mapping()` / `reject_mapping()`, so the manual-override discipline (deactivating competing rows on approve) is preserved. For a 127.0.0.1-only MVP, the lack of CSRF protection is acceptable.
- `_card.html` does implement all four J-03 branches, but the tests only exercise `ok`, `below_privacy_floor`, and `channel_too_new`; I do not see a test that reaches `no_data_pulled` through the card partial.
- Jinja escaping is otherwise fine: no `|safe`, normal autoescape is intact, and `tojson` is the right approach once the retention payload is converted to primitives.
- I did not rerun the suite locally.
