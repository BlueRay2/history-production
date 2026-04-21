# Process — Dashboard KPI (identical to gemini-delegation-hardening)

**Branch:** `kpi`
**Source of truth:** `/home/aiagent/assistant/git/consensus-dashboard-kpi/` (consensus v3 run, 2026-04-21). **Authoritative verdict:** the highest-numbered `verdict-roundN.md` file in that directory (Codex-judge under owner-override of 5-round cap per Ярослав msg 6830). Prior verdicts `verdict.md` (Round 3) and earlier `verdict-roundM.md` where M < N are preserved for audit trail only — they do NOT govern current ship authorization.
**Created:** 2026-04-21T19:25+03:00
**Owner:** Claude (coordinator). Review: Codex + Gemini per-task (see review loop below).

## Context

Consensus Mode v3 run diagnosed the 9-task bundle for a local-hosted KPI dashboard for YouTube channel "Cities Evolution" (44 subs / 24 videos / 8.5k views). Dashboard pulls daily at 03:30 GMT+3 via pure-Python YouTube API client, extracts intelligent KPIs from `history-production` git repo (cycle time idea→publish, script iterations, cost-per-video estimates), serves at `127.0.0.1:<port>` via Flask + Jinja + HTMX + Chart.js + SQLite.

**Consensus state:** initial Round 5 verdict was `no-ship` with three fixable findings (J-01 process/README alignment, J-02 task-08 deploy path, J-03 sparse-metric semantics). J-02 and J-03 confirmed resolved in Round 6. J-01 converged across Rounds 6–8. J-04 (cron path drift) raised Round 6 and resolved Round 7. Latest judge decision is always the highest-numbered `verdict-roundN.md` in the consensus directory.

Full consensus artefacts (research, debates, findings register, verdicts) are in `assistant/git/consensus-dashboard-kpi/`.

## Task index + live status

| ID | File | Scope | Status | Codex review | Gemini review |
|---|---|---|---|---|---|
| 01 | [task-01-adr-and-schema.md](task-01-adr-and-schema.md) | Stack ADR (Flask+Jinja+HTMX+Chart.js+SQLite), DB schema, raw SQL migrations, `schema_migrations` table | `in-review-gemini (r1)` | ✅ accepted r3 | pending |
| 02 | [task-02-youtube-api-client.md](task-02-youtube-api-client.md) | OAuth install-flow, refresh-token cache in `/home/aiagent/.config/youtube-api/.env` (600), typed client wrapper, vcrpy cassette fixtures | `pending` | — | — |
| 03 | [task-03-append-snapshot-ingest.md](task-03-append-snapshot-ingest.md) | Ingestion runs table, rolling 45-d backfill, append-only writes with `observed_on`, preliminary-flag overwrite logic, first-run 45-d backfill script | `pending` | — | — |
| 04 | [task-04-history-git-parser.md](task-04-history-git-parser.md) | `ingest/history_git.py`, heuristic commit scoring (phase-\d+ / script / final / lock patterns), confidence + evidence columns, golden git fixtures | `pending` | — | — |
| 05 | [task-05-mapping-and-derived-kpis.md](task-05-mapping-and-derived-kpis.md) | `video_project_map` + derived KPI views: cycle-time, scripts-per-week, script-iterations (approx), cost-per-video (fail-closed parser) | `pending` | — | — |
| 06 | [task-06-web-shell-and-weekly-tab.md](task-06-web-shell-and-weekly-tab.md) | Flask app skeleton, `/weekly` route, metric cards, retention chart, exceptions panel, calibration banner | `pending` | — | — |
| 07 | [task-07-monthly-tab-and-exceptions.md](task-07-monthly-tab-and-exceptions.md) | `/monthly` route, composite-score top-performers, cost-distribution, unmapped-cities panel | `pending` | — | — |
| 08 | [task-08-cron-systemd-runbook.md](task-08-cron-systemd-runbook.md) | `30 3 * * *` cron via CronCreate durable:true, systemd user unit, 127.0.0.1 bind check, failure→Telegram alert, runbook | `pending` | — | — |
| 09 | [task-09-baseline-calibration.md](task-09-baseline-calibration.md) | 4-week data accumulation gate, `config/kpi-thresholds.yaml` bootstrap, R/Y/G activation only after gate | `pending` | — | — |

## Per-task review loop

Each task file has a **Review loop** section with explicit sign-off slots. Workflow (identical to gemini-delegation-hardening):

1. **Claim task:** transition status `pending` → `in-progress` in this index. Push to origin.
2. **Implement** on this branch (code + tests + golden fixtures where the task file requires them).
3. **Hand off to Codex review:** status `in-progress` → `in-review-codex (round 1)`.
4. **Delegate to Codex** via `scripts/codex-tracked-exec.sh` with a prompt pointing at this task file + the diff. Codex writes review comments into `reviews/task-XX/codex-round-N.md` (create dir if needed).
5. If Codex has comments → apply fixes → bump round counter → re-delegate until Codex returns "accepted, no comments".
6. **Hand off to Gemini review:** status `in-review-codex` → `in-review-gemini (round 1)`.
7. **Delegate to Gemini** via `scripts/gemini-agent.sh review`. Gemini writes to `reviews/task-XX/gemini-round-N.md`.
8. If Gemini has comments that require code changes Codex already cleared → regress to `in-review-codex` round N+1, then return to `in-review-gemini`. Otherwise iterate Gemini round N+1.
9. When Gemini also returns "accepted, no comments" → status `ready-to-merge`.
10. Merge fast-forward into `kpi` branch (no PR to `main` until whole bundle is ready). Mark task `merged`.
11. Push `origin/kpi` after every status transition.

**Anti-loop guard:** if a task hits 5 review rounds without convergence, pause and escalate to Ярослав in Telegram for guidance. Do NOT silently ship a contested change.

**Gemini-degraded override (2026-04-21):** at consensus kickoff, Gemini 2.5-pro returned 429 capacity exhaustion. If Gemini remains unavailable when a task is Codex-approved, the task may ship with status `ready-to-merge (gemini-degraded)` + explicit Telegram alert to Ярослав. The merge commit body MUST include `Review: Codex-accepted r{N}; Gemini: unavailable 429 at review time`. Once Gemini capacity returns, all `gemini-degraded` merges MUST undergo retroactive Gemini review; any fundamental disagreement triggers a fix-up task.

**Status vocabulary (authoritative):** `pending` → `in-progress` → `in-review-codex` (round N) → `in-review-gemini` (round N) → `ready-to-merge` → `ready-to-merge (gemini-degraded)` → `merged`. May regress (e.g. back from gemini to codex) if a gemini finding requires code changes that codex should re-check.

**Progress broadcast cadence:** per-task status transitions trigger one concise Telegram update to Ярослав (208368262) — not each round, only phase changes. Exception: if a review round reveals a critical bug or a scope question, send immediately.

**Git remote update cadence:** push `origin/kpi` after every status transition. `git push -u origin kpi` on first transition; subsequent pushes are `git push`.

**Autonomous execution:** proceed through tasks in dependency order without mid-bundle pauses UNLESS (a) task hits anti-loop guard, (b) critical finding emerges, (c) Ярослав intervenes, (d) consensus Gemini-retroactive review surfaces a fundamental disagreement. Report ship completion with summary: files touched, lines added/removed, tests passing, outstanding Gemini-degraded reviews.

## Dependencies between tasks

- **task-01** (ADR+schema) blocks all others.
- **task-02** (YouTube client) + **task-04** (git parser) can run in parallel after 01 lands.
- **task-03** (ingest) depends on task-02.
- **task-05** (KPIs) depends on task-03 + task-04.
- **task-06** (FE shell + weekly) depends on task-05.
- **task-07** (monthly) depends on task-06.
- **task-08** (cron/systemd) depends on task-03 + task-07 (needs end-to-end green path).
- **task-09** (baseline calibration) depends on task-08 (and 4 weeks of data, so final ship-completion happens only after calendar-bound calibration). task-09 ships code in "calibration mode"; activation is a config flip after 4 weeks.

**Critical path:** 01 → 04 → 05 → 06 → 07 → 08 → 09 (git-metric-first priority).
**Parallel window:** 02, 03 alongside 04, 05.

## Out-of-scope for this bundle (parked findings from consensus)

- **F-01 Gemini retroactive review** — after capacity returns, revisit task-02 and task-03 with Gemini for API/backfill validation.
- **F-02 COST_ESTIMATE.md template standardization** — Ярослав task, opportunistic. Fail-closed parser in task-05 handles absence gracefully.
- **F-04 Cron timing 03:30 vs 06:30** — accepted as residual risk; no functional advantage to changing.
- **LAN access + auth** — out of scope for MVP. Future migration path: Flask → FastAPI only if LAN/auth actually lands.
- **Cost tracker with real API parsing** (Seedance/Kling/Flow/ElevenLabs) — deferred; current scope uses commit-tracked estimates only.

## Links

- Consensus run: `/home/aiagent/assistant/git/consensus-dashboard-kpi/`
- Topic: `consensus-dashboard-kpi/topic.md`
- Roles: `consensus-dashboard-kpi/roles.tson`
- Research: `consensus-dashboard-kpi/research/{claude,codex,gemini,gemini-status}.md`
- Debates: `consensus-dashboard-kpi/debate/round-{1,2,3}.md`
- Findings register: `consensus-dashboard-kpi/findings.tson`
- **Authoritative judge verdict:** the highest-numbered `consensus-dashboard-kpi/verdict-roundN.md` file (Codex judge under owner-override per Ярослав msg 6830). Prior rounds (`verdict.md` Round 3 through earlier `verdict-roundM.md` files) preserved for audit trail only — do NOT use them to determine current ship state.
- Debate quality: `consensus-dashboard-kpi/debate-quality.md`
- Process reference (template): `/home/aiagent/assistant/git/home_server/docs/tz/gemini-delegation-hardening/README.md`
