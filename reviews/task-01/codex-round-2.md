# Codex Round 2 Review — task-01-adr-and-schema

**Reviewer:** codex
**Date:** 2026-04-21T21:16:04+03:00
**Commits reviewed:** 709dd7e (vs a20bd18)
**Verdict:** request changes
**Extraction:** Claude coordinator extracted verbatim from Codex agent_message item in `reviews/codex-round-2-raw.log` after sandbox write to this path failed.

## Findings (if any)

- [medium] [app/db.py](/home/aiagent/assistant/git/history-production/app/db.py:110) — `BEGIN IMMEDIATE` makes each migration atomic once it starts, but the applied-version snapshot is still taken before the write lock. Two concurrent `migrate()` calls can both decide `001` is pending; the first one commits, and the second then enters its own transaction with stale state and fails on already-existing DDL instead of treating the migration as applied. If concurrent migrators are meant to be supported, re-check `schema_migrations` after acquiring the transaction or move the pending-version decision under the same lock.

## Addressed from round-1

- [high] atomicity: The original crash window between `executescript(sql)` and the `schema_migrations` insert is closed. Each migration's statements plus the bookkeeping insert now run inside one explicit `BEGIN IMMEDIATE` / `COMMIT`, with `ROLLBACK` on exceptions, and `_split_statements()` handles `001_init.sql` correctly as written because it is plain semicolon-delimited DDL with comment lines and no embedded semicolons in SQL literals.
- [medium] test coverage: `test_full_kpi_schema_shape()` now checks the promised table set, all five named secondary indexes, and the key FK edges for `video_project_map`, `video_metric_snapshots`, and `git_events`. `test_atomic_migration_rollback_on_failure()` does prove rollback: it forces a mid-migration `OperationalError`, then verifies earlier DDL did not survive and no `schema_migrations` row for version `999` was inserted.
- pycache: confirmed removed from `709dd7e`. The compare shows both tracked `.pyc` files deleted, and fetching `app/__pycache__/db.cpython-39.pyc` at that commit returns 404.

## New observations

- No connection-lifecycle regression found in the new transaction path: the exception path rolls back before re-raising, and `connect()` still closes the SQLite handle in `finally`.
- `_split_statements()` is intentionally narrow but acceptable for the current migration. It would not be robust enough for future SQL containing semicolons inside string literals or trigger bodies.
