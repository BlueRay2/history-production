# task-04 — history-production git parser

**Status:** `pending`
**Dep:** 01
**Risk:** High

## Scope

1. `ingest/history_git.py`:
   - Walks `git log --all --no-merges` on `history-production` (configurable path via env `HISTORY_PRODUCTION_PATH`).
   - Emits `git_events` rows with `event_type` ∈ {`scaffold`, `script_started`, `script_finished`, `revision`, `publish_metadata`, `unclassified`}.
   - Each row carries `confidence: REAL` (0..1) + `payload_json` with evidence (regex matches, touched files).
2. Heuristic scoring (per `consensus-dashboard-kpi/research/codex.md#4`):
   - `scaffold`: commit subject matches `^scaffold|^Initial commit|^chore.*scaffold` AND touches `{city}/README.md` or is first commit mentioning `{city}/`. Confidence 0.9 if all; 0.6 if subject-only.
   - `script_started`: touches `{city}/SCRIPT.md` for first time.
   - `script_finished`: subject matches `phase[2-5]|final|lock|ready` AND touches `{city}/TELEPROMPTER.md` or `{city}/SEO_PACKAGE.md`. Confidence 0.8 if both; 0.5 if subject-only.
   - `revision`: subsequent commits touching `{city}/SCRIPT.md` after `script_started`.
   - `publish_metadata`: commit touches `{city}/docs/publish.json` (future convention). Confidence 1.0 when present.
   - `unclassified`: fallback for commits that touch a city folder but don't match above.
3. `ingest/history_git.py` also maintains `projects` table: discovers new city slugs, seeds `first_commit_at`.
4. **Cost parse:** `ingest/cost_parse.py`:
   - Globs `{city}/COST_ESTIMATE.md` AND `{city}/docs/COST_ESTIMATE.md` (either location supported per F-07).
   - Fail-closed: returns `None` if no canonical `Total:` line found. Logs warning; writes backlog row.
   - Canonical line variants accepted: `**Total: $X.XX**`, `**Итого: N credits**`, `**Grand total: $X.XX**`. Regex library documented.

## Golden fixtures

Per `debate/round-2.md`:
- `tests/fixtures/git_history/snapshot_1_pre_nagasaki/` — bundled git repo at post-istanbul state.
- `tests/fixtures/git_history/snapshot_2_post_istanbul/` — adds istanbul phase commits.
- `tests/fixtures/git_history/snapshot_3_post_nagasaki_v2/` — adds nagasaki-v2 with `phase3-5` batch style.
- Expected outputs committed: `tests/fixtures/expected_git_events/snapshot_N.json`.

## Test plan

- `tests/test_history_git.py`: run parser against each snapshot, diff against expected JSON.
- `tests/test_cost_parse.py`: matrix of COST_ESTIMATE.md format variants (istanbul-style, nagasaki-v2-style, broken, missing total).
- `tests/test_convention_drift.py`: synthetic commit with odd subject → classifier falls back to `unclassified` with confidence 0.

## Files touched

- `ingest/history_git.py`, `ingest/cost_parse.py` (new)
- `tests/fixtures/git_history/*` (new, committed as bundled `.tar.gz` or submodule pins)
- `tests/fixtures/expected_git_events/*.json` (new)
- `tests/test_history_git.py`, `tests/test_cost_parse.py`, `tests/test_convention_drift.py` (new)

## Review loop

- [ ] Codex round-1 → `reviews/task-04/codex-round-1.md`
- [ ] Gemini round-1 → `reviews/task-04/gemini-round-1.md`
- [ ] `ready-to-merge` | `ready-to-merge (gemini-degraded)`
- [ ] `merged`

## Risk notes

- F-03: revision count approximate under rebase; UI label "approx.".
- F-07: dual path support for COST_ESTIMATE.md location.
- Convention drift: new cities adopting different commit style will land as `unclassified` until regex updated.
