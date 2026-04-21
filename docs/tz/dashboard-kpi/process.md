# Process — Dashboard KPI implementation workflow

**This file:** describes how to execute the 9-task bundle.
**Status table + task index:** [README.md](README.md)
**Source of truth:** `/home/aiagent/assistant/git/consensus-dashboard-kpi/` (consensus v3 run, 2026-04-21). Authoritative verdict: `verdict-round6.md` or later (Codex-judge under owner-override of 5-round cap per Ярослав msg 6830). Prior verdicts (Round 3/4/5) preserved for audit only.

## Execution model

**Identical to `gemini-delegation-hardening`** (`/home/aiagent/assistant/git/home_server/docs/tz/gemini-delegation-hardening/README.md`).

The Lead (Claude) implements each task on this branch (`kpi`), then cycles it through Codex review → Gemini review → merge. Each cycle is tracked via per-task status in README.md and per-round review files in `reviews/task-XX/`.

## Review loop (per task)

1. **Implement.** Claude writes code + tests + fixtures per task file. Status: `pending` → `in-progress`.
2. **Codex review (round N).** Claude delegates via `scripts/codex-tracked-exec.sh` with prompt pointing at the task file + diff. Codex writes `reviews/task-XX/codex-round-N.md`. Status: `in-review-codex`.
3. **Iterate on Codex feedback.** If Codex has comments → apply fixes → repeat Codex round N+1. Status stays `in-review-codex`.
4. **Codex accepts.** Codex returns "accepted, no comments" → Status: `in-review-gemini`.
5. **Gemini review (round M).** Claude delegates via `scripts/gemini-agent.sh review` with same prompt shape. Gemini writes `reviews/task-XX/gemini-round-M.md`.
6. **Iterate on Gemini feedback.** If Gemini has comments → apply fixes → if the fix touched code Codex already signed off on, regress to `in-review-codex` for one more Codex round, then return to `in-review-gemini`.
7. **Gemini accepts.** Status: `ready-to-merge`.
8. **Merge.** Fast-forward commits on `kpi` branch. No PR to `main` until all 9 tasks are merged. Status: `merged`.
9. **Push.** `git push origin kpi` after every status transition.
10. **Telegram broadcast.** One concise DM to Ярослав (208368262) per status transition — not per round. Exceptions: critical bug or scope question → immediate broadcast.

## Status vocabulary (authoritative)

```
pending
  → in-progress
    → in-review-codex (round N)
      → in-review-gemini (round N)
        → ready-to-merge
        → ready-to-merge (gemini-degraded)
          → merged
```

- **Regression allowed:** `in-review-gemini` → `in-review-codex` when Gemini findings require Codex re-check.
- **Gemini-degraded path:** if Gemini 2.5-pro is unavailable (429 capacity) at review time, task may ship as `ready-to-merge (gemini-degraded)` + merge-commit body MUST include `Review: Codex-accepted r{N}; Gemini: unavailable 429 at review time`. Retroactive Gemini audit mandatory when capacity returns.

## Anti-loop guard

If a task hits **5 review rounds** without convergence → **pause and escalate to Ярослав** in Telegram for guidance. Do not silently ship a contested change.

Round count is cumulative across Codex + Gemini (e.g., Codex-r1, Codex-r2, Gemini-r1, Codex-r3, Gemini-r2 = 5 rounds → escalate).

## Telegram broadcast cadence

| Trigger | Content |
|---|---|
| Task starts (pending → in-progress) | "🚀 task-0X starting — {brief scope}" |
| Codex review entered (first time) | "👀 task-0X → Codex review" |
| Status settled to ready-to-merge | "✅ task-0X ready-to-merge, Codex+Gemini accepted" |
| Status settled to ready-to-merge (gemini-degraded) | "⚠️ task-0X shipping gemini-degraded (429) — retroactive audit queued" |
| Task merged | "🎉 task-0X merged; moving to task-0Y" |
| Anti-loop guard triggered | "🚧 task-0X hit 5-round anti-loop — need your call on {summary}" |
| Critical finding | immediate DM with context + stop-ship request if needed |
| Bundle complete | "🏁 dashboard-kpi bundle: 9/9 merged on `kpi` branch. PR to `main`?" |

## Autonomous execution scope

Proceed through tasks in dependency order **without mid-bundle pauses** UNLESS:
1. Anti-loop guard triggered (5 rounds).
2. Critical finding emerges (security issue, data loss risk, fundamental architecture flaw).
3. Ярослав intervenes.
4. Gemini retroactive review surfaces a fundamental disagreement requiring task rework.

## Git workflow

- Branch: `kpi` (pre-created from `main` on 2026-04-21).
- Commits: per-task milestones (e.g., `task-01(kpi): ADR + schema + migration-001`).
- Push cadence: after every status transition.
- Merge strategy to `main`: deferred until all 9 tasks merged on `kpi`. Single rebase-ready merge request at end.

## Ship authorization (as of 2026-04-21, Round 5 closed)

Consensus run closed at Round 5 (5-round hard cap). Judge verdict is documented in `consensus-dashboard-kpi/verdict-round5.md`:

- **F-02, F-05, F-08** (the three high-severity findings from Round 3) — **resolved** in the task bundle.
- **F-01** downgraded to low (Gemini research now available inline).
- **F-03, F-04, F-06, F-07** — resolved or accepted as residual risk.
- Three new judge findings (J-01, J-02, J-03) raised in Round 5 — all addressed in this revision of the bundle before any task starts.

Task implementations proceed autonomously from `task-01-adr-and-schema` onwards per the dep graph. Owner (Ярослав) sign-off on the amended bundle is prerequisite; once signed, Claude (coordinator) transitions tasks `pending` → `in-progress` without further pause except for the conditions listed in "Autonomous execution scope" above.

## Gemini retroactive review policy

All tasks that ship with `ready-to-merge (gemini-degraded)` enter a **retroactive-audit queue**. When Gemini capacity returns:
1. Claude delegates each queued task to Gemini via `scripts/gemini-agent.sh review` with same prompt shape as a normal review.
2. If Gemini returns "accepted, no comments" → upgrade status `ready-to-merge (gemini-degraded)` → `merged (gemini-audited)`. Commit amend in the branch history is NOT performed; instead, a `docs/tz/dashboard-kpi/retroactive-audit-log.md` records the upgrade.
3. If Gemini has substantive comments → create a fix-up task `task-0X-fixup-gemini-r1.md`; process it through the normal review loop.

## References

- Process template: `/home/aiagent/assistant/git/home_server/docs/tz/gemini-delegation-hardening/README.md`
- Consensus charter: `/home/aiagent/assistant/config/consensus-mode.md`
- CLAUDE.md § Bypass the Weakness: reminder that failures are fixed with layered defenses, not manual workarounds.
- CLAUDE.md § Разграничение прав: all settings/hook changes require Ярослав approval before execution.
