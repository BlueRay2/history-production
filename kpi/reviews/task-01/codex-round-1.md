# Codex Round 1 Review — task-01-adr-and-schema

**Reviewer:** codex
**Date:** 2026-04-21T21:06:30+03:00
**Commits reviewed:** e901155, a20bd18
**Verdict:** request changes
**Extraction:** Claude coordinator extracted this review verbatim from Codex agent_message item in `reviews/codex-round-1-raw.log` after sandbox write to this path failed. Review text unchanged.

## Findings

- [high] (app/db.py:91) Migration application and migration bookkeeping are not atomic. `001_init.sql` opens and commits its own transaction, then `migrate()` writes the `schema_migrations` row afterwards in a separate autocommitted statement. If the process dies, or a second `migrate()` runs, between those two steps, the schema can be fully applied but still look unapplied, and the next run will fail on `table/index already exists`. Suggested fix: run each migration body and the `schema_migrations` insert inside one explicit `BEGIN IMMEDIATE` transaction, which also serializes concurrent migrators. That means removing `BEGIN/COMMIT` from the SQL file or otherwise ensuring the Python layer owns the transaction boundary.
- [medium] (tests/test_migrations.py:70) The test suite does not verify the schema promised by task-01. It only checks `schema_migrations` column names, so a missing KPI table, foreign key, or one of the five required indexes in `001_init.sql` would still pass. Suggested fix: add one schema-shape test that asserts the expected table set, required foreign-key edges, and index names from the task spec.

## Additional observations

- ADR scope looks aligned with the task: Flask + Jinja + HTMX + Chart.js + SQLite, raw SQL migrations, WAL, FK enforcement, and J-03 sparse-metric null semantics are all captured.
- `db/migrations/001_init.sql` matches the task schema shape itself: 8 domain tables plus `schema_migrations`, with the expected foreign keys and 5 indexes.
- Type hints are consistent with the requested style, and `from __future__ import annotations` is present where it matters.
- `.gitignore` now covers future Python bytecode, sqlite files, and Entire logs, but the reviewed head still contains tracked `app/__pycache__/*.pyc` artifacts from the earlier commit. Those files should be removed from git; ignore rules do not retroactively untrack them.
- `pyproject.toml` is appropriately minimal for task-01.
- I did not run `pytest` locally in this review because the shell sandbox was unavailable; findings are from static diff inspection.
