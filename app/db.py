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


def _discover_migrations(dir_: Path = _MIGRATIONS_DIR) -> list[tuple[str, Path, str]]:
    files = sorted(p for p in dir_.glob("*.sql"))
    out: list[tuple[str, Path, str]] = []
    for p in files:
        version = p.stem.split("_", 1)[0]
        out.append((version, p, p.read_text(encoding="utf-8")))
    return out


def migrate() -> int:
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
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at, sha256) VALUES (?,?,?)",
                (version, _now_iso(), current_sha),
            )
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
