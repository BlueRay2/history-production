# Codex Round 1 Review — task-04-history-git-parser

**Reviewer:** codex
**Date:** 2026-04-22T04:23:32+03:00
**Commit reviewed:** e277fa7
**Verdict:** request changes
**Extraction:** Claude coordinator extracted verbatim from Codex agent_message in `reviews/task-04-codex-r1-raw.log` (apply_patch + shell sandbox blocked).

## Findings

- **[medium]** (ingest/history_git.py:156, ingest/history_git.py:181) The scaffold heuristic from the task spec is only subject-driven here. The spec also treats the first commit mentioning `{city}/` as `scaffold`, but the chronological pass only upgrades first `SCRIPT.md` touches. A city whose first commit is `feat(kyoto): add README` or similar never gets a scaffold event, which undercounts project-creation milestones. Suggested fix: track `first_city_seen` during the chronological pass and upgrade the earliest city-touch commit when no stronger classification should win.
- **[medium]** (ingest/history_git.py:31, ingest/history_git.py:156) `_SCAFFOLD_SUBJECT` is broader than the spec and the confidence gate is too permissive. The regex matches `scaffold` anywhere in the subject, and any city-file touch returns `0.9`. That means later commits like `docs(istanbul): scaffold note cleanup` or `fix: scaffold generator` can be mislabeled as high-confidence `scaffold`. Suggested fix: anchor the subject pattern to the start conditions in the spec and reserve `0.9` for README/first-city evidence, not any city file.
- **[medium]** (ingest/history_git.py:160, ingest/history_git.py:190) `script_started` is only produced when the initial classification is `revision`. If the first `SCRIPT.md` touch is also a `phase3/final` commit that adds `TELEPROMPTER.md` or `SEO_PACKAGE.md`, the commit is locked in as `script_finished` and the city never gets a `script_started` event. That conflicts with the "first SCRIPT.md touch" rule and is exactly the kind of batch-style commit the task spec calls out. Suggested fix: detect first `SCRIPT.md` touches from the file list before or alongside classification, then apply an explicit precedence rule for overlapping start/finish evidence.

## Observations (non-blocking)

- The `\x01`/`\x02` delimiters in `_iter_commits` are acceptable for this repo's conventional commit traffic, but they are not binary-safe if someone ever injects control characters into a commit subject. I would treat that as an acceptable repo-specific constraint rather than a blocker.
- `tests/test_history_git.py` covers the happy path well, but it does not exercise the missing first-city scaffold path or the "first SCRIPT touch is already a phase/final commit" case. The task spec also called out `tests/test_convention_drift.py`, which is absent in this commit.

## Summary

Needs one more pass on classification precedence. The cost parser and SQLite idempotency pieces look sound; the remaining problems are in how `scaffold` and `script_started` are inferred from commit history.
