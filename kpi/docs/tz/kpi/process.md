# Process — `kpi` metrics vault implementation workflow

**This file:** how to execute the 8-task bundle.
**Status table + task index:** [README.md](README.md)
**Source of truth:** `/home/aiagent/assistant/git/consensus-metrics-vault-2026-04-26/`

## Execution model

Identical to `dashboard-kpi/process.md` — Claude implements each task on `kpi` branch, cycles through Codex review → Gemini review → merge.

## Review loop (per task) — PARALLEL Codex + Gemini

1. **Implement.** Claude writes code + tests + fixtures per task file. Status: `pending` → `in-progress`.
2. **Dispatch parallel review (round N).** Simultaneously delegate:
   - Codex via `scripts/codex-tracked-exec.sh`. Output → `kpi/docs/tz/kpi/reviews/task-XX/codex-round-N.md`.
   - Gemini via `scripts/gemini-agent.sh review` (with `GEMINI_ALLOW_FLASH_FALLBACK=1`). Output → `kpi/docs/tz/kpi/reviews/task-XX/gemini-round-N.md`.
   Status: `in-review (r N)`.
3. **Collect both responses.** Wait for both, normalize to `accepted` | `request changes`.
4. **Merge findings.** Deduplicate overlapping. Apply union of all unique findings in single fix commit.
5. **Iterate.** Re-dispatch round N+1 if either returned `request changes`.
6. **Both accept.** Status `ready-to-merge`.
7. **Gemini-degraded fallback.** If Gemini 429 after flash-fallback retries, may ship `ready-to-merge (gemini-degraded)` + Telegram alert + retroactive audit queue.
8. **Merge.** Fast-forward into `kpi`. Status: `merged`.
9. **Push.** `git push origin kpi`.
10. **Telegram broadcast.** One DM per status transition.

## Status vocabulary

```
pending
  → in-progress
    → in-review (round N)   ← Codex + Gemini in parallel
      → ready-to-merge                        (both accepted)
      → ready-to-merge (gemini-degraded)       (Codex accepted; Gemini 429 after flash fallback)
        → merged
```

## Anti-loop guard

5 review rounds without convergence → escalate to Ярослав in Telegram. Round count cumulative across both reviewers.

## Telegram broadcast cadence

| Trigger | Content |
|---|---|
| Task starts | "🚀 task-0X starting — {scope}" |
| First review round | "👀 task-0X → Codex+Gemini review" |
| Status settled to ready-to-merge | "✅ task-0X ready-to-merge" |
| Anti-loop or critical bug | Immediate detail |

## Common operational notes

- All DB paths use **new SQLite file** `state/kpi.sqlite` (replaces legacy `state/dashboard-kpi.sqlite`)
- All Flask routes use **new app entry** `app.monitoring:create_app` (legacy `app.main` retired)
- Cron entries renamed from `dashboard_kpi_*` to `kpi_*` for clarity
- Old `claude-kpi-dashboard.service` is **disabled and removed** during task-02
- Telegram failure alerts go via direct Bot API curl (per dashboard-kpi pattern, survives Claude session downtime)
