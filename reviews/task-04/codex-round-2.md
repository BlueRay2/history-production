# Codex Round 2 Review — task-04-history-git-parser

**Reviewer:** codex
**Date:** 2026-04-22T04:33+03:00
**Commit reviewed:** 00dff11
**Verdict:** request changes
**Extraction:** Claude coordinator extracted verbatim from Codex agent_message (sandbox write blocked). Note: Codex's output title accidentally said "(Gemini)" — this is Codex's review per the delegation script.

## Findings

1. **MED** — `_iter_commits` / `_active_files`: raw-status handling still is not proven correct beyond the `D` case. `git log --raw` emits rename/copy statuses as `R100`, `R087`, `C075`, etc., not bare `R` / `C`, and this classifier is reconstructing file activity from history rather than just reading HEAD state. That means `A`, `R*`, and `C*` need explicit backward-walk handling as well as status normalization. The new regression only covers deleted files, so a rename/copy/new-file path can still be miscounted as a revision or dropped from the active set. I would not accept this without tests covering at least `A`, `R100`, and `C075`.

## Open Questions / Assumptions

- `event_value='also:script_started'` is only sufficient if downstream consumers are documented to treat `event_value` as a secondary-milestone channel. If analytics filter on `event_type='script_started'`, the original undercount still exists. If one row per commit is not a hard invariant, this should be a second `GitEvent` row; otherwise the secondary-event model needs to be made explicit.
- The scaffold regex looks properly subject-anchored from the pattern you provided.
- The 0.9 / 0.7 / 0.5 scaffold confidence ladder looks reasonable.
- Limiting the first-city second pass to `unclassified` / `revision` seems correct; I would keep `script_started` excluded.
- `_LOG.warning` is the right severity for canonical-path drift, assuming task-08 keeps standard warning-level logging in cron.

## Change Summary

- Remaining blocker is raw `--raw` status handling outside the deletion case.
- I could not run tests or inspect exact file/line locations because the shell wrapper and file-write path both failed in this session.
