"""SQLite connection helper + raw-SQL migrator for KPI dashboard.

Usage:
    python -m app.db migrate           # apply pending migrations
    python -m app.db status            # show current schema version
    python -m app.db connect           # return connection string for ad-hoc sqlite3 CLI
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

_DEFAULT_DB = "/home/aiagent/assistant/state/dashboard-kpi.sqlite"
_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations"


def db_path() -> str:
    return os.environ.get("DASHBOARD_KPI_DB", _DEFAULT_DB)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    return {r["version"]: r["sha256"] for r in conn.execute("SELECT version, sha256 FROM schema_migrations")}


def _discover_migrations(dir_: Path | None = None) -> list[tuple[str, Path, str]]:
    # Resolve at call time so tests can monkey-patch _MIGRATIONS_DIR.
    base = dir_ if dir_ is not None else _MIGRATIONS_DIR
    files = sorted(p for p in base.glob("*.sql"))
    out: list[tuple[str, Path, str]] = []
    for p in files:
        version = p.stem.split("_", 1)[0]
        out.append((version, p, p.read_text(encoding="utf-8")))
    return out


def _split_statements(sql: str) -> list[str]:
    """Split semicolon-delimited SQL into individual statements.

    Good enough for DDL-only migrations (no string literals containing ';').
    Drops empty statements and standalone BEGIN/COMMIT — transaction boundaries
    are owned by the migrator, not the SQL file (Codex round-1 finding [high]).
    """
    out: list[str] = []
    for raw in sql.split(";"):
        stmt = raw.strip()
        if not stmt:
            continue
        if stmt.upper() in ("BEGIN", "COMMIT"):
            continue
        # Drop SQL line comments that stand alone; keep multi-line bodies intact
        lines = [ln for ln in stmt.splitlines() if not ln.strip().startswith("--")]
        body = "\n".join(lines).strip()
        if body:
            out.append(body)
    return out


def migrate() -> int:
    """Apply pending migrations atomically per version.

    Each migration's DDL + schema_migrations insert run inside one
    BEGIN IMMEDIATE transaction so a crash between steps cannot leave the DB
    with schema applied but unrecorded (Codex round-1 finding [high]).
    BEGIN IMMEDIATE also serializes concurrent migrators against each other.
    """
    with connect() as conn:
        applied = _applied_versions(conn)
        migrations = _discover_migrations()
        pending = 0
        for version, path, sql in migrations:
            current_sha = _sha256(sql)
            if version in applied:
                if applied[version] != current_sha:
                    raise RuntimeError(
                        f"migration {version} ({path.name}) already applied with different content "
                        f"(stored sha {applied[version]} vs current {current_sha}) — refusing to overwrite"
                    )
                continue
            conn.execute("BEGIN IMMEDIATE")
            try:
                # Concurrent-migrator race guard (Codex round-2 finding [medium]):
                # another migrator may have applied this version in the window
                # between our _applied_versions() snapshot and acquiring the
                # BEGIN IMMEDIATE write lock. Re-check inside the transaction.
                row = conn.execute(
                    "SELECT sha256 FROM schema_migrations WHERE version = ?",
                    (version,),
                ).fetchone()
                if row is not None:
                    if row[0] != current_sha:
                        # Another migrator applied a DIFFERENT content for this
                        # version — real tamper or divergent deploys. Refuse.
                        conn.execute("ROLLBACK")
                        raise RuntimeError(
                            f"migration {version} ({path.name}) was applied by another migrator "
                            f"with different content (stored sha {row[0]} vs current {current_sha})"
                        )
                    # Same content already applied by a racing migrator — no-op.
                    conn.execute("ROLLBACK")
                    print(
                        f"[migrate] {version} already applied by another migrator (race)",
                        file=sys.stderr,
                    )
                    continue
                for stmt in _split_statements(sql):
                    conn.execute(stmt)
                conn.execute(
                    "INSERT INTO schema_migrations(version, applied_at, sha256) VALUES (?,?,?)",
                    (version, _now_iso(), current_sha),
                )
                conn.execute("COMMIT")
            except Exception:
                # ROLLBACK is idempotent on sqlite3; safe even if already rolled back.
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.OperationalError:
                    pass
                raise
            pending += 1
            print(f"[migrate] applied {version} ({path.name})", file=sys.stderr)
        if pending == 0:
            print("[migrate] nothing to apply", file=sys.stderr)
        return pending


def status() -> None:
    with connect() as conn:
        applied = _applied_versions(conn)
        print(f"db: {db_path()}")
        print(f"applied migrations: {len(applied)}")
        for v in sorted(applied):
            print(f"  {v}  sha={applied[v][:12]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KPI dashboard DB helper")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate")
    sub.add_parser("status")
    sub.add_parser("connect").add_argument(
        "--print-path", action="store_true", help="print db file path and exit"
    )
    args = parser.parse_args(argv)
    if args.cmd == "migrate":
        migrate()
        return 0
    if args.cmd == "status":
        status()
        return 0
    if args.cmd == "connect":
        print(db_path())
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
