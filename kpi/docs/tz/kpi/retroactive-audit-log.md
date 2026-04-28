# Retroactive audit log — kpi metrics-vault

Append-only ledger of retroactive code-review outcomes for tasks shipped
under `gemini-degraded` or `codex-degraded` status. Per
`process.md` Recovery protocol §2: ACCEPTED upgrades recorded here without
amending history; substantive findings spawn fix-up tasks.

## 2026-04-27 — Retroactive audit pass (Yaroslav directive msg 8247)

| Task | Affected commit | Original status | Retro reviewer | Verdict | Action |
|---|---|---|---|---|---|
| task-04 | `1396c58` | gemini-r3-degraded (Google capacity exhaustion) | Gemini 3.1-pro retroactive r3 (with embedded diff) | **ACCEPTED zero new findings** | Upgrade — full r3 audit complete; both reviewers ACCEPTED |
| task-05 | `612650e` | codex-r2-degraded (sandbox bwrap) + gemini-r1-degraded (auth_interactive) | Codex r2 retroactive + Gemini r1 retroactive (with embedded diff) | **ACCEPTED zero new findings (both)** | Upgrade — task-05 fully reviewed |
| task-06 | `9db7883` | codex-r1-degraded + gemini-r1-degraded | Codex r1 retroactive + Gemini r1 retroactive (with embedded diff) | Codex ACCEPTED zero findings; **Gemini ACCEPTED with one MED finding GEM-06-001** | Fix-up cycle — see `task-06-fixup-gemini-r1.md` |
| task-07 | `a7d1b4c` (r3) and `372586c` (r4) | gemini-r3-degraded + gemini-r4-degraded (auth_interactive) | Gemini r3 retroactive (file-based prompt) + Gemini r4 retroactive | **ACCEPTED zero new findings (both)** | Upgrade — task-07 fully reviewed |

### Fix-up cycle: task-06-fixup-gemini-r1

- **Finding:** GEM-06-001 (Medium): inefficient dual correlated subqueries in `v_last_run_per_source`.
- **Fix:** Migration `003_optimize_v_last_run_per_source.sql` — CTE + `ROW_NUMBER()` single-pass window function. Equivalence verified empirically on seeded data.
- **Fixup commit:** `4e30342`
- **Codex r1:** ACCEPTED zero findings.
- **Gemini r1:** ACCEPTED — confirms the original finding is properly addressed.
- **Status:** ready-to-merge → merged into `kpi` (this commit).

### Aggregate status post-audit

| Task | Pre-audit status | Post-audit status |
|---|---|---|
| 01 | merged | merged ✅ |
| 03 | merged | merged ✅ |
| 04 | merged (gemini-r3-degraded) | **merged (full reviewed)** ✅ |
| 05 | merged (codex-r2 + gemini-r1 degraded) | **merged (full reviewed)** ✅ |
| 06 | merged (codex-r1 + gemini-r1 degraded) | **merged + fixup applied + fixup reviewed** ✅ |
| 07 | merged (gemini-r3,r4 degraded) | **merged (full reviewed)** ✅ |

### Lessons learned

1. **File-based prompts** beat argv for large diffs — task-07 r3 retry-3 hit "Argument list too long" until switched to file-based read_file pattern.
2. **Embedded diffs in prompts** prevent the "META: audit blocked" bogus verdict that Gemini issued in retry-1 when it incorrectly claimed it could not access files.
3. **Conseca 429 rate-limit on `gemini-2.5-flash`** (the safety-policy generator) blocks the entire Gemini CLI even when the main `gemini-3.1-pro-preview` is healthy. Cooldown 3-5 minutes typically clears it.
4. **Two-track audit** (Codex + Gemini) caught the GEM-06-001 finding that Codex retroactive missed. Two-reviewer rule is load-bearing even when both are nominally retroactive.
