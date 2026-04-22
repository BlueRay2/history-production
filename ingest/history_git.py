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

# Anchored scaffold subject (Codex r1 MED): must start with a directive verb;
# rejects cases like "docs(x): scaffold note cleanup" or "fix: scaffold generator".
_SCAFFOLD_SUBJECT = re.compile(
    r"^(scaffold|Initial commit|chore(?:\([^)]+\))?:\s*scaffold)\b",
    re.IGNORECASE,
)
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
    """Yield (sha, committed_at, subject, files_by_status) tuples for every non-merge commit on all branches.

    Uses `--raw` mode so each file entry carries its status flag
    (A=added, M=modified, D=deleted, R=renamed, etc.). Format:
      :src_mode dst_mode src_sha dst_sha STATUS\\tpath
    Returns `files_by_status` as a list of (status, path) tuples. Callers
    that only care about non-deleted files can filter for status != 'D'.

    (Gemini r1 MED: previous `--name-only` did not distinguish deletions,
    so a commit that removed SCRIPT.md was misclassified as a 'revision'.
    `--raw` restores deletion-awareness without further git calls.)
    """
    raw = _run_git(
        [
            "log", "--all", "--no-merges",
            "--raw",
            "--format=%x02%H%x01%cI%x01%s",
        ],
        cwd=repo_root,
    )
    current_sha: str | None = None
    current_dt: str | None = None
    current_subject: str | None = None
    current_files: list[tuple[str, str]] = []

    for line in raw.splitlines():
        if line.startswith("\x02"):
            if current_sha is not None:
                yield current_sha, current_dt, current_subject, list(current_files)
            header = line[1:]
            parts = header.split("\x01", 2)
            if len(parts) < 3:
                current_sha = None
                continue
            current_sha, current_dt, current_subject = parts[0], parts[1], parts[2]
            current_files = []
        elif line and current_sha is not None:
            # Raw format: ':MODES SRC DST STATUS\tpath'
            if line.startswith(":"):
                try:
                    meta, path = line.split("\t", 1)
                    status = meta.split()[-1]  # last whitespace-separated token = status letter(s)
                    # Normalise R100 → R, C100 → C, M → M, D → D, A → A.
                    status = status[0] if status else "?"
                    current_files.append((status, path.strip()))
                except Exception:  # noqa: BLE001
                    continue
    if current_sha is not None:
        yield current_sha, current_dt, current_subject, list(current_files)


def _active_files(files_by_status: list[tuple[str, str]]) -> list[str]:
    """Filter to paths that still exist after the commit (not deleted)."""
    return [path for status, path in files_by_status if status != "D"]


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

    Takes already-filtered `files` (call _active_files on the raw list to
    drop deletions — Gemini r1 MED). Never raises. Returns
    ('unclassified', 0.0) when no pattern matches.
    """
    if city_slug is None:
        return "unclassified", 0.0

    touches_script = any(f == f"{city_slug}/SCRIPT.md" for f in files)
    touches_readme = any(f == f"{city_slug}/README.md" for f in files)
    touches_teleprompter = any(f == f"{city_slug}/TELEPROMPTER.md" for f in files)
    touches_seo = any(f == f"{city_slug}/SEO_PACKAGE.md" for f in files)
    touches_publish_meta = any(f == f"{city_slug}/docs/publish.json" for f in files)

    if touches_publish_meta:
        return "publish_metadata", 1.0

    # Codex r1 MED: anchored regex + reserve 0.9 ONLY when README.md (strong
    # scaffold evidence) is touched; city-file-touch alone drops to 0.7.
    subject_scaffold = _SCAFFOLD_SUBJECT.search(subject) is not None
    if subject_scaffold:
        if touches_readme:
            return "scaffold", 0.9
        if any(f.startswith(f"{city_slug}/") for f in files):
            return "scaffold", 0.7
        return "scaffold", 0.5

    subject_final = _SCRIPT_FINAL_SUBJECT.search(subject) is not None
    if subject_final and (touches_teleprompter or touches_seo):
        return "script_finished", 0.8
    if subject_final:
        return "script_finished", 0.5

    if touches_script:
        return "revision", 0.7

    return "unclassified", 0.2 if city_slug else 0.0


def parse_history_repo(repo_root: Path) -> list[GitEvent]:
    """Walk a history-production-style git repo and return GitEvents.

    Chronological post-pass rules (Codex r1 MED):
      1. Track first SCRIPT.md touch per city using the ACTIVE file list
         (deletions filtered out). If that first touch happens to also look
         like a script_finished (batch-style phase3 commit), emit BOTH a
         script_started and keep the script_finished on the same commit via
         precedence: script_finished wins if files include
         TELEPROMPTER/SEO, but the commit is still tagged with a secondary
         event_value='also:script_started' for downstream KPI consumers.
      2. Track first city sighting: if no commit for a city received a
         scaffold classification, upgrade the earliest city-touching commit
         to scaffold with confidence 0.6 (weaker — inferred, not declared).
    """
    events: list[GitEvent] = []
    first_script_seen: set[str] = set()
    first_city_seen: set[str] = set()
    scaffolded: set[str] = set()

    commits = list(_iter_commits(repo_root))
    commits.reverse()  # chronological oldest-first

    for sha, committed_at, subject, files_by_status in commits:
        active_files = _active_files(files_by_status)
        city = _infer_city(active_files, subject)
        event_type, confidence = _classify(subject, active_files, city)

        event_value: str | None = None

        if city is not None:
            # First SCRIPT.md touch → script_started (unless also finished).
            touches_script = any(f == f"{city}/SCRIPT.md" for f in active_files)
            if touches_script and city not in first_script_seen:
                first_script_seen.add(city)
                if event_type == "script_finished":
                    # Batch commit — keep script_finished as primary, mark
                    # that script_started also occurred on this SHA.
                    event_value = "also:script_started"
                else:
                    event_type = "script_started"
                    confidence = 0.85

            if event_type == "scaffold":
                scaffolded.add(city)

            # First city sighting placeholder: we'll upgrade in second pass.
            if city not in first_city_seen:
                first_city_seen.add(city)

        payload = {
            "subject": subject[:200],
            "touched_files": active_files[:20],
            "file_count": len(active_files),
            "file_status_summary": "".join(sorted({st for st, _ in files_by_status})) or "",
        }
        events.append(GitEvent(
            commit_sha=sha,
            city_slug=city,
            branch_name=None,
            committed_at=committed_at,
            event_type=event_type,
            event_value=event_value,
            payload=payload,
            confidence=confidence,
        ))

    # Second pass: upgrade earliest city-touching commit to scaffold for
    # cities that never received an explicit scaffold subject.
    for i, e in enumerate(events):
        if e.city_slug and e.city_slug not in scaffolded:
            # Find the earliest event for that city and promote it.
            if events[i].event_type in ("unclassified", "revision"):
                events[i] = GitEvent(
                    commit_sha=e.commit_sha,
                    city_slug=e.city_slug,
                    branch_name=e.branch_name,
                    committed_at=e.committed_at,
                    event_type="scaffold",
                    event_value=(e.event_value or "inferred-first-city"),
                    payload=e.payload,
                    confidence=0.6,
                )
                scaffolded.add(e.city_slug)

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
                # Gemini r1 MED: if a project already exists with a different
                # canonical_path, log a warning so the divergence isn't silent.
                existing = conn.execute(
                    "SELECT canonical_path FROM projects WHERE city_slug = ?",
                    (e.city_slug,),
                ).fetchone()
                if existing and existing["canonical_path"] != e.city_slug:
                    _LOG.warning(
                        "project %s canonical_path drift: stored=%r, expected=%r",
                        e.city_slug, existing["canonical_path"], e.city_slug,
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
