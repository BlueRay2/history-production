# Retroactive review queue — kpi metrics vault

Tasks shipped with `gemini-degraded` or `codex-degraded` review status
require retroactive review when the affected agent's capacity returns.

## Open queue

| Task | Commit | Degraded reviewer(s) | Reason | Recover via |
|---|---|---|---|---|
| task-04 | 698d8c1 | Codex (sandbox bug, all rounds) | `bwrap: loopback: Failed RTM_NEWADDR` blocks file reads in `codex exec`; Codex self-reports it cannot read repo files. | Owner override (`--dangerously-bypass-approvals-and-sandbox`) once authorized OR sandbox repaired. Then `codex exec ...` with the round-1/2 prompts. |
| task-04 | 698d8c1 | Gemini r2 (auth_interactive, transient) | `rc=41 FatalAuthenticationError` on large prompts (small ping still works → flash fallback path). | After `gemini auth login` in interactive terminal: `gemini -p "$(cat r2-prompt.txt)"`. |

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
