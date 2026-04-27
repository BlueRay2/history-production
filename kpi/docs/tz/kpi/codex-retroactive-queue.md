# Retroactive review queue — kpi metrics vault

Tasks shipped with `gemini-degraded` or `codex-degraded` review status
require retroactive review when the affected agent's capacity returns.

## Open queue

| Task | Commit | Degraded reviewer(s) | Reason | Recover via |
|---|---|---|---|---|
| task-04 | 698d8c1 | ~~Codex (sandbox bug)~~ — RESOLVED 2026-04-27 via `codex exec --model gpt-5.5 -c sandbox_permissions=["disk-full-read-access"] -c model_reasoning_effort="xhigh" --skip-git-repo-check --json`. Real Codex r1 v2 produced 6 actionable findings. | n/a | n/a — recovered |
| task-04 | 698d8c1 | ~~Gemini r2 (auth_interactive)~~ — RESOLVED 2026-04-27. Real Gemini r2 ACCEPTED post-r1 fixes. | n/a | n/a — recovered |
| task-04 | 1396c58 | Gemini r3 (capacity-exhausted) | `MODEL_CAPACITY_EXHAUSTED` on gemini-3.1-pro-preview AND gemini-2.5-flash. Google-side capacity issue, not auth/quota. Codex r3 ACCEPTED this commit. | When 3.1-pro/2.5-flash capacity returns: `gemini -p "$(cat /tmp/task04-gemini-r3-prompt.txt)"`. Re-running r3 review on commit 1396c58. |
| task-05 | 612650e | Codex r2 + Gemini r1 (sandbox + auth_interactive) | Codex `bwrap: loopback: Failed RTM_NEWADDR` returned even with `disk-full-read-access`; Gemini `auth_interactive` rc=41 on long prompts (small ping still pongs). Codex r1 was substantive (7 findings actioned). | Sandbox heals: `codex exec --model gpt-5.5 -c sandbox_permissions=["disk-full-read-access"] -c model_reasoning_effort="xhigh" --skip-git-repo-check --json "$(cat /tmp/task05-r2-prompt.txt)"`. Gemini: interactive `gemini auth login`, then `gemini -p` from `cd ~`. |
| task-06 | 9db7883 | Codex r1 + Gemini r1 (sandbox + auth_interactive) | Same bwrap loopback. Migration is additive 4-views + 1 heartbeat table; 8 tests verify each view's correctness via seeded data. Coordinator self-review: spec coverage complete; SQL hazards minimal (LEFT JOIN preserves zero-snapshot videos, IS-not-= for nullable source_detail correlation). | Same recovery path as task-05. |

## Recovery protocol

1. Re-run the original prompt (saved alongside each task as `*-prompt.txt`
   in `/tmp/` or in the task review directory).
2. If retroactive review returns ACCEPTED with no new comments → upgrade
   commit metadata via a follow-up `docs/tz/kpi/retroactive-audit-log.md`
   entry. Do NOT amend or rewrite history; record the upgrade as an
   append-only ledger entry.
3. If retroactive review returns substantive comments → create a fix-up
   task `task-XX-fixup-{reviewer}-rN.md` and process through the normal
   review loop.

## History

(Empty — first entry is task-04 above, 2026-04-27.)
