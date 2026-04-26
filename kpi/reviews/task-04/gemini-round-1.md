# Gemini Round 1 Review — task-04-history-git-parser

**Reviewer:** gemini
**Date:** 2026-04-22T04:25+03:00 (Gemini reported 19:30 UTC; corrected to wall-clock)
**Commit reviewed:** e277fa7
**Verdict:** request changes
**Extraction:** Claude coordinator extracted verbatim from Gemini `response` field in `reviews/task-04-gemini-r1-raw.log` (direct write_file was blocked by tool policy; Gemini inlined content).

## Findings

- **[MEDIUM]** (`ingest/history_git.py`, `_classify` function): The event classifier incorrectly identifies file deletions as revisions. The `_classify` function checks for the presence of a file path (e.g., `{city_slug}/SCRIPT.md`) in the commit's file list. However, `git log --name-only` does not distinguish between modified and deleted files. Consequently, a commit that *deletes* `SCRIPT.md` will be misclassified as a `'revision'` with 0.7 confidence.
  **Suggestion:** Modify the `_iter_commits` function to use `git log --numstat` instead of `--name-only`. This will provide file status (Added/Modified/Deleted), allowing the `_classify` function to ignore deleted files when identifying revisions or other events.

- **[MEDIUM]** (`ingest/history_git.py`, `write_events` function): The project auto-creation logic can lead to silent data conflicts. The `INSERT OR IGNORE INTO projects` statement correctly prevents duplicates based on `city_slug`. However, if a project already exists with a different `canonical_path`, this discrepancy is silently ignored. This could lead to a stale `canonical_path` in the database if conventions change.
  **Suggestion:** After the `INSERT OR IGNORE`, execute a `SELECT` to retrieve the existing `canonical_path` for the given `city_slug`. Compare it with the path that would have been inserted and log a warning if they do not match.

## Observations (non-blocking)

- (`ingest/history_git.py`, `_iter_commits` function): The use of `\x02` (prefix) and `\x01` (separator) to parse `git log` output is a robust method for handling potentially complex commit messages. While unconventional, it is not an issue.
- The test suite for both new modules is comprehensive, utilizing a synthetic git repository and covering major success paths, failure modes, and edge cases like idempotency. The quality of the tests is high.

## Summary

The review identified two medium-severity issues. The most significant is the misclassification of file deletions as `'revision'` events, which could corrupt KPI data. The second issue is a silent failure to update project metadata (`canonical_path`) if it conflicts with existing records. Both issues should be addressed. The overall code quality, test coverage, and adherence to fail-closed principles are otherwise strong.
