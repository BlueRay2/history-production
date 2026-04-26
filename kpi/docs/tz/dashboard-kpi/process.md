# Process — Dashboard KPI implementation workflow

**This file:** describes how to execute the 9-task bundle.
**Status table + task index:** [README.md](README.md)
**Source of truth:** `/home/aiagent/assistant/git/consensus-dashboard-kpi/` (consensus v3 run, 2026-04-21). **Authoritative verdict:** the highest-numbered `verdict-roundN.md` file in that directory (Codex-judge under owner-override of 5-round cap per Ярослав msg 6830). Prior verdicts preserved for audit only.

## Execution model

**Identical to `gemini-delegation-hardening`** (`/home/aiagent/assistant/git/home_server/docs/tz/gemini-delegation-hardening/README.md`).

The Lead (Claude) implements each task on this branch (`kpi`), then cycles it through Codex review → Gemini review → merge. Each cycle is tracked via per-task status in README.md and per-round review files in `reviews/task-XX/`.

## Review loop (per task) — PARALLEL Codex + Gemini (updated 2026-04-21 per Ярослав msg 6879)

Earlier workflow had sequential Codex → Gemini review. Ярослав directive 2026-04-21T23:06 (msg 6879): "Ревью делай и в Codex и в Gemini и исправляй правки от их обоих, а так же добавь code review от обоих одновременно для всех остальных задач." → **both reviewers run concurrently on each round**, Claude merges the union of findings into one fix pass.

1. **Implement.** Claude writes code + tests + fixtures per task file. Status: `pending` → `in-progress`.
2. **Dispatch parallel review (round N).** Claude simultaneously delegates:
   - Codex via `scripts/codex-tracked-exec.sh` with prompt pointing at the task file + diff. Output → `reviews/task-XX/codex-round-N.md`.
   - Gemini via `scripts/gemini-agent.sh review` with the same prompt shape. Output → `reviews/task-XX/gemini-round-N.md`.
   Status: `in-review (r N)`.
3. **Collect both responses.** Wait for both reviewers. Normalize each to a verdict (`accepted` | `request changes`) and a list of findings.
4. **Merge findings.** Deduplicate overlapping findings (same file:line, same category). Apply **union** of all unique findings in a single fix commit — don't split Codex fixes from Gemini fixes.
5. **Iterate.** If either reviewer returned `request changes`, commit the merged fix and re-dispatch parallel round N+1. Status stays `in-review (r N+1)`.
6. **Both accept.** Only when **both** reviewers return `accepted, no comments` in the same round → status `ready-to-merge`.
7. **Gemini-degraded fallback.** If Gemini returns 429 capacity after flash-fallback retries, record `reviews/task-XX/gemini-round-N-UNAVAILABLE.md` with classifier signature. Status may advance to `ready-to-merge (gemini-degraded)` if Codex accepted AND Ярослав is notified AND the retroactive-audit queue entry is written. See "Gemini retroactive review policy" below.
8. **Merge.** Fast-forward commits on `kpi` branch. No PR to `main` until all 9 tasks are merged. Status: `merged`.
9. **Push.** `git push origin kpi` after every status transition.
10. **Telegram broadcast.** One concise DM to Ярослав (208368262) per status transition — not per round. Exceptions: critical bug or scope question → immediate broadcast.

**Why parallel:** halves wall-clock time per task, surfaces reviewer disagreement earlier (when both see the same diff without prior signoff bias), and Ярослав's explicit directive. Risk: review workload on agents doubles per round — mitigated by the fact that Gemini and Codex sandboxes are independent.

## Status vocabulary (authoritative — parallel review model)

```
pending
  → in-progress
    → in-review (round N)   ← Codex + Gemini in parallel
      → ready-to-merge                        (both accepted)
      → ready-to-merge (gemini-degraded)       (Codex accepted; Gemini 429 after flash fallback)
        → merged
```

- **No `in-review-codex` / `in-review-gemini` separation.** One `in-review (r N)` badge represents both reviewers.
- **Regression:** if round N+1 fixes touch code both reviewers had signed off on in round N (rare — only when a fix from one reviewer surfaces a new issue), Claude dispatches round N+1 to both reviewers again.
- **Gemini-degraded path:** if Gemini 2.5-pro is unavailable (429 capacity) **after flash-fallback retry**, task may ship as `ready-to-merge (gemini-degraded)` + merge-commit body MUST include `Review: Codex-accepted r{N}; Gemini: unavailable 429 at review time`. Retroactive Gemini audit mandatory when capacity returns.

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

## Ship authorization

Consensus run extended beyond the 5-round cap by explicit owner-override (Ярослав msg 6830: "Продолжайте дебаты пока судья не даст формальное разрешение на продолжение"). **The authoritative judge verdict is the highest-numbered `verdict-roundN.md` in `consensus-dashboard-kpi/`.** Do not consult earlier verdicts to determine current ship state.

Finding state across all rounds:
- **F-02, F-05, F-08** (the three high-severity findings from Round 3) — **resolved** in the task bundle (confirmed by Codex Round 6).
- **F-01** downgraded to low (Gemini research now available inline, 3/3 quorum).
- **F-03, F-04, F-06, F-07** — resolved or accepted as residual risk.
- **J-01** (process/README alignment) + **J-02** (task-08 deploy path) + **J-03** (sparse-metric null semantics) — raised in Round 5, progressively resolved across Rounds 6 and 7.
- **J-04** (cron path drift) — raised in Round 6, resolved in Round 7.

Task implementations proceed autonomously from `task-01-adr-and-schema` onwards per the dep graph only after a `ship` verdict is recorded. Owner (Ярослав) sign-off after ship is noted; Claude (coordinator) transitions tasks `pending` → `in-progress` without further pause except for the conditions listed in "Autonomous execution scope" above.

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
