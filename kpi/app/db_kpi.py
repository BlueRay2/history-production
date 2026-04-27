"""SQLite connection helper + migrator for the KPI metrics vault (ADR 0002).

Separate module from `app/db.py` so the legacy `dashboard-kpi.sqlite` and the
new `kpi.sqlite` can coexist during the 3-day verification window without
cross-contamination.

Usage:
    python -m app.db_kpi migrate           # apply pending migrations
    python -m app.db_kpi status            # show current schema version
    python -m app.db_kpi connect           # echo path for ad-hoc sqlite3 CLI

Env override:
    KPI_DB=/path/to/custom/file.sqlite
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

_DEFAULT_DB = "/home/aiagent/assistant/state/kpi.sqlite"
_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations-kpi"


def db_path() -> str:
    return os.environ.get("KPI_DB", _DEFAULT_DB)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, timeout=10.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    # Microsecond precision matches snapshot tables' observed_on convention.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL,
            sha256     TEXT NOT NULL
        )
        """
    )


def _applied_versions(conn: sqlite3.Connection) -> dict[str, str]:
    _ensure_migrations_table(conn)
    return {
        row["version"]: row["sha256"]
        for row in conn.execute("SELECT version, sha256 FROM schema_migrations")
    }


def _discover_migrations(dir_: Path | None = None) -> list[tuple[str, Path, str]]:
    base = dir_ if dir_ is not None else _MIGRATIONS_DIR
    files = sorted(p for p in base.glob("*.sql"))
    out: list[tuple[str, Path, str]] = []
    for p in files:
        version = p.stem.split("_", 1)[0]
        out.append((version, p, p.read_text(encoding="utf-8")))
    return out


def _split_statements(sql: str) -> list[str]:
    """Split semicolon-delimited SQL into individual statements.

    SQL-aware state-machine: respects single-quoted strings, double-quoted
    identifiers, and `--` line comments. Comment characters are CONSUMED
    (not added to the buffer) so post-pass line stripping is unnecessary —
    Codex r2 finding (MED): the previous post-pass `splitlines()` strip
    corrupted multiline string literals containing lines starting with `--`
    (e.g. `INSERT ... VALUES ('a\\n-- literal\\nb');`).

    Limitations (acceptable for our migrations):
      - Does not handle SQLite C-style `/* ... */` block comments
      - Does not handle `BEGIN...END` trigger bodies (none in this codebase)

    For richer cases, drop in `sqlglot` or `sqlparse` later.
    """
    out: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(sql)
    in_single = False
    in_double = False
    in_line_comment = False
    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""
        if in_line_comment:
            # Consume comment chars; do not buffer them.
            if ch == "\n":
                in_line_comment = False
                buf.append(ch)  # preserve newline so line numbers stay aligned
            i += 1
            continue
        if in_single:
            buf.append(ch)
            if ch == "'" and nxt == "'":           # escaped quote — keep both
                buf.append(nxt); i += 2; continue
            if ch == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            buf.append(ch)
            if ch == '"':
                in_double = False
            i += 1
            continue
        # Outside any quoted/comment context
        if ch == "-" and nxt == "-":
            in_line_comment = True
            i += 2
            continue
        if ch == "'":
            in_single = True; buf.append(ch); i += 1; continue
        if ch == '"':
            in_double = True; buf.append(ch); i += 1; continue
        if ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch); i += 1
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def _apply_migration(
    conn: sqlite3.Connection, version: str, sql: str, expected_sha: str | None = None
) -> None:
    sha = _sha256(sql)
    if expected_sha is not None and expected_sha != sha:
        raise RuntimeError(
            f"migration {version} hash mismatch: applied={expected_sha[:12]} "
            f"current_file={sha[:12]} — file changed since last apply, refusing to drift"
        )
    statements = _split_statements(sql)
    # Atomic apply: all statements + bookkeeping in one transaction.
    conn.execute("BEGIN")
    try:
        for stmt in statements:
            conn.execute(stmt)
        conn.execute(
            "INSERT INTO schema_migrations(version, applied_at, sha256) VALUES (?, ?, ?)",
            (version, _now_iso(), sha),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def migrate(*, conn: sqlite3.Connection | None = None) -> int:
    """Apply all pending migrations. Returns count applied."""
    if conn is None:
        with connect() as c:
            return migrate(conn=c)
    applied = _applied_versions(conn)
    pending = _discover_migrations()
    count = 0
    for version, path, sql in pending:
        if version in applied:
            # Verify file unchanged since apply.
            current_sha = _sha256(sql)
            if current_sha != applied[version]:
                raise RuntimeError(
                    f"migration {version} ({path.name}) was modified since apply: "
                    f"applied_sha={applied[version][:12]}, current_sha={current_sha[:12]}. "
                    "Migrations are immutable. Add a new migration file instead."
                )
            continue
        print(f"[migrate-kpi] applying {version} ({path.name})", file=sys.stderr)
        _apply_migration(conn, version, sql)
        count += 1
    if count == 0:
        print(f"[migrate-kpi] up to date ({len(applied)} migrations applied)", file=sys.stderr)
    return count


def status(*, conn: sqlite3.Connection | None = None) -> None:
    if conn is None:
        with connect() as c:
            return status(conn=c)
    applied = _applied_versions(conn)
    print(f"db: {db_path()}")
    print(f"applied migrations: {len(applied)}")
    for v in sorted(applied):
        print(f"  {v}  sha={applied[v][:12]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.db_kpi", description="KPI vault DB")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate", help="apply pending migrations")
    sub.add_parser("status", help="show schema version")
    sub.add_parser("connect", help="echo path for ad-hoc sqlite3 CLI")
    args = parser.parse_args(argv)
    if args.cmd == "migrate":
        migrate()
    elif args.cmd == "status":
        status()
    elif args.cmd == "connect":
        print(db_path())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
