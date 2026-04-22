"""Parse history-production git log into git_events rows.

Extracts KPI milestones from commit messages + touched-file patterns:
  - scaffold: first commit mentioning a city (scaffold|Initial commit)
  - script_started: first commit touching {city}/SCRIPT.md
  - script_finished: phase[2-5] + touches TELEPROMPTER.md / SEO_PACKAGE.md
  - revision: subsequent commits touching {city}/SCRIPT.md
  - publish_metadata: commit touches {city}/docs/publish.json (future convention)
  - unclassified: fallback for commits touching a city folder without match

Each row carries a `confidence: REAL` (0..1) and `payload_json` with evidence
(regex matches, touched files, commit SHA) for the UI's uncertain-mapping
panel.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path

_LOG = logging.getLogger(__name__)

_CITY_ROOT_PATTERN = re.compile(r"^([a-z0-9][a-z0-9_-]+)/")

_SCAFFOLD_SUBJECT = re.compile(r"\b(scaffold|Initial commit|chore.*scaffold)\b", re.IGNORECASE)
_SCRIPT_FINAL_SUBJECT = re.compile(r"\b(phase[\-]?[2-5]|final|lock|ready)\b", re.IGNORECASE)


@dataclass(frozen=True)
class GitEvent:
    commit_sha: str
    city_slug: str | None
    branch_name: str | None
    committed_at: str
    event_type: str
    event_value: str | None
    payload: dict
    confidence: float

    def confidence_clamped(self) -> float:
        return max(0.0, min(1.0, self.confidence))


def _run_git(args: list[str], cwd: Path) -> str:
    """Invoke git with a fixed env and return stdout. Raises on non-zero."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "LC_ALL": "C"},  # deterministic locale
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (rc={result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


def _iter_commits(repo_root: Path):
    """Yield (sha, committed_at, subject, files) tuples for every non-merge commit on all branches.

    Uses `--format="%x02%H%x01%cI%x01%s"` so each commit block BEGINS with
    \\x02 — the touched-files list produced by `--name-only` always belongs
    to the commit whose header appeared most recently. Parsing is line-based.
    """
    raw = _run_git(
        [
            "log", "--all", "--no-merges",
            "--name-only", "--format=%x02%H%x01%cI%x01%s",
        ],
        cwd=repo_root,
    )
    current_sha: str | None = None
    current_dt: str | None = None
    current_subject: str | None = None
    current_files: list[str] = []

    def flush():
        if current_sha is not None:
            yield current_sha, current_dt, current_subject, list(current_files)

    for line in raw.splitlines():
        if line.startswith("\x02"):
            # New commit header. Flush the previous one.
            if current_sha is not None:
                yield current_sha, current_dt, current_subject, list(current_files)
            header = line[1:]  # strip \x02
            parts = header.split("\x01", 2)
            if len(parts) < 3:
                current_sha = None
                continue
            current_sha, current_dt, current_subject = parts[0], parts[1], parts[2]
            current_files = []
        elif line and current_sha is not None:
            current_files.append(line.strip())
    if current_sha is not None:
        yield current_sha, current_dt, current_subject, list(current_files)


def _infer_city(files: list[str], subject: str) -> str | None:
    """Infer the city slug associated with a commit from its touched files.

    If multiple city folders are touched, returns the most-frequent one.
    Falls back to parsing the commit subject for conventional `phaseN(city)`
    or `feat(city)` prefixes.
    """
    candidates: dict[str, int] = {}
    for f in files:
        m = _CITY_ROOT_PATTERN.match(f)
        if m:
            candidates[m.group(1)] = candidates.get(m.group(1), 0) + 1
    if candidates:
        # Take the slug with the most touched files. Reserved slugs like
        # `docs`, `scripts`, `tests`, `.claude` etc. filter below.
        for slug, _count in sorted(candidates.items(), key=lambda kv: -kv[1]):
            if slug not in _RESERVED_ROOT_SLUGS:
                return slug
    # Fallback: conventional commit subject "phaseN(city): ..."
    m = re.match(r"[a-z]+\d*\(([a-z][a-z0-9_-]*)\)", subject, re.IGNORECASE)
    if m and m.group(1).lower() not in _RESERVED_ROOT_SLUGS:
        return m.group(1).lower()
    return None


_RESERVED_ROOT_SLUGS = {
    "docs", "scripts", "tests", "app", "ingest", "db", "reviews",
    ".claude", ".github", ".entire", "previews", "shorts", "tiktok",
}


def _classify(subject: str, files: list[str], city_slug: str | None) -> tuple[str, float]:
    """Return (event_type, confidence) for a given commit.

    Never raises. Falls back to ('unclassified', 0.0) when the combination
    of subject + files doesn't match any known pattern.
    """
    if city_slug is None:
        return "unclassified", 0.0

    touches_script = any(f == f"{city_slug}/SCRIPT.md" for f in files)
    touches_teleprompter = any(f == f"{city_slug}/TELEPROMPTER.md" for f in files)
    touches_seo = any(f == f"{city_slug}/SEO_PACKAGE.md" for f in files)
    touches_publish_meta = any(f == f"{city_slug}/docs/publish.json" for f in files)

    if touches_publish_meta:
        return "publish_metadata", 1.0

    subject_scaffold = _SCAFFOLD_SUBJECT.search(subject) is not None
    if subject_scaffold:
        return "scaffold", 0.9 if (touches_script or any(f.startswith(f"{city_slug}/") for f in files)) else 0.6

    subject_final = _SCRIPT_FINAL_SUBJECT.search(subject) is not None
    if subject_final and (touches_teleprompter or touches_seo):
        return "script_finished", 0.8
    if subject_final:
        return "script_finished", 0.5  # subject-only, weaker evidence

    if touches_script:
        # Can't tell if this is the FIRST SCRIPT touch without cross-commit
        # state. Caller sequences commits chronologically and upgrades the
        # first occurrence to "script_started". Middle touches = revision.
        return "revision", 0.7

    return "unclassified", 0.2 if city_slug else 0.0


def parse_history_repo(repo_root: Path) -> list[GitEvent]:
    """Walk a history-production-style git repo and return GitEvents.

    After initial classification, post-process to upgrade the earliest
    `revision` per city to `script_started` (first SCRIPT.md touch).
    """
    events: list[GitEvent] = []
    first_script_seen: set[str] = set()
    # Git log --all returns newest first; reverse so we see earliest per-city
    # SCRIPT.md touch and can upgrade it to script_started.
    commits = list(_iter_commits(repo_root))
    commits.reverse()
    for sha, committed_at, subject, files in commits:
        city = _infer_city(files, subject)
        event_type, confidence = _classify(subject, files, city)
        if event_type == "revision" and city is not None and city not in first_script_seen:
            event_type = "script_started"
            confidence = 0.85
            first_script_seen.add(city)
        payload = {
            "subject": subject[:200],
            "touched_files": files[:20],
            "file_count": len(files),
        }
        events.append(GitEvent(
            commit_sha=sha,
            city_slug=city,
            branch_name=None,  # multi-branch reachability left for task-05
            committed_at=committed_at,
            event_type=event_type,
            event_value=None,
            payload=payload,
            confidence=confidence,
        ))
    return events


def write_events(conn: sqlite3.Connection, events: list[GitEvent]) -> int:
    """Upsert events into git_events. Returns number of rows inserted.

    INSERT OR IGNORE on commit_sha PK so re-runs are idempotent.
    """
    if not events:
        return 0
    inserted = 0
    conn.execute("BEGIN IMMEDIATE")
    try:
        for e in events:
            # projects row must exist for FK. Auto-create on first sighting.
            if e.city_slug is not None:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO projects (city_slug, first_commit_at, canonical_path, status)
                    VALUES (?, ?, ?, 'active')
                    """,
                    (e.city_slug, e.committed_at, e.city_slug),
                )
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO git_events
                    (commit_sha, city_slug, branch_name, committed_at, event_type,
                     event_value, payload_json, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    e.commit_sha, e.city_slug, e.branch_name, e.committed_at,
                    e.event_type, e.event_value, json.dumps(e.payload),
                    e.confidence_clamped(),
                ),
            )
            inserted += cur.rowcount
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass
        raise
    return inserted
