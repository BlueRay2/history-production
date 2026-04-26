"""Tests for ingest.history_git — git event parser.

Strategy: build a tiny synthetic git repo in tmp_path, populate it with
commit patterns that mimic history-production conventions (phaseN(city)
subjects, city/ folder structure, SCRIPT.md files), then assert the
parser emits the expected event types and confidences.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from ingest.history_git import (
    GitEvent,
    _classify,
    _infer_city,
    parse_history_repo,
    write_events,
)
from app import db as dbmod


@pytest.fixture
def git_repo(tmp_path):
    """Build a minimal history-production-shaped repo for parsing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@t", "LC_ALL": "C"}
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=repo, check=True, env=env)

    def commit(subject: str, files: dict[str, str]):
        for path, content in files.items():
            full = repo / path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
        subprocess.run(["git", "commit", "-q", "-m", subject], cwd=repo, check=True, env=env)

    # istanbul lifecycle
    commit("scaffold(istanbul): initial directory", {"istanbul/README.md": "istanbul"})
    commit("feat(istanbul): script draft", {"istanbul/SCRIPT.md": "script v1"})
    commit("feat(istanbul): script iteration", {"istanbul/SCRIPT.md": "script v2"})
    commit("phase3(istanbul): SCRIPT.md + TELEPROMPTER.md",
           {"istanbul/SCRIPT.md": "final", "istanbul/TELEPROMPTER.md": "teleprompter"})

    # kyoto lifecycle (no script finish yet)
    commit("scaffold(kyoto): init", {"kyoto/README.md": "kyoto"})
    commit("feat(kyoto): add script", {"kyoto/SCRIPT.md": "draft"})

    # weird commit — no city folder, subject unclear
    commit("chore: typo in root readme", {"README.md": "readme"})

    yield repo


def test_infer_city_from_touched_files():
    assert _infer_city(["istanbul/SCRIPT.md"], "feat: x") == "istanbul"
    assert _infer_city(["docs/adr.md", "istanbul/SCRIPT.md", "istanbul/README.md"], "x") == "istanbul"


def test_infer_city_from_subject_when_no_city_files():
    assert _infer_city(["README.md"], "feat(nagasaki): something") == "nagasaki"


def test_infer_city_rejects_reserved_slugs():
    assert _infer_city(["docs/adr.md"], "docs: update") is None
    assert _infer_city(["scripts/x.sh"], "chore: x") is None


def test_classify_scaffold():
    etype, conf = _classify("scaffold(istanbul): init", ["istanbul/README.md"], "istanbul")
    assert etype == "scaffold"
    assert conf >= 0.9


def test_classify_script_finished_strong():
    etype, conf = _classify(
        "phase3(istanbul): final",
        ["istanbul/SCRIPT.md", "istanbul/TELEPROMPTER.md"],
        "istanbul",
    )
    assert etype == "script_finished"
    assert conf >= 0.7


def test_classify_revision():
    etype, conf = _classify(
        "feat(istanbul): iterate",
        ["istanbul/SCRIPT.md"],
        "istanbul",
    )
    assert etype == "revision"
    assert 0.5 < conf <= 0.8


def test_classify_unclassified_without_city():
    etype, conf = _classify("chore: typo", ["README.md"], None)
    assert etype == "unclassified"
    assert conf == 0.0


def test_parse_history_repo_happy_path(git_repo):
    events = parse_history_repo(git_repo)
    assert len(events) == 7  # 4 istanbul + 2 kyoto + 1 root
    # Find istanbul events
    istanbul = [e for e in events if e.city_slug == "istanbul"]
    types = [e.event_type for e in istanbul]
    # Order: scaffold → script_started (first SCRIPT.md) → revision → script_finished
    assert types == ["scaffold", "script_started", "revision", "script_finished"]
    # All confidence clamped to [0,1]
    assert all(0.0 <= e.confidence_clamped() <= 1.0 for e in events)


def test_parse_repo_upgrades_first_script_to_started(git_repo):
    events = parse_history_repo(git_repo)
    istanbul = [e for e in events if e.city_slug == "istanbul"]
    # Exactly one script_started per city, not one per SCRIPT.md touch.
    assert sum(1 for e in istanbul if e.event_type == "script_started") == 1


def test_write_events_idempotent(tmp_path, monkeypatch, git_repo):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    events = parse_history_repo(git_repo)
    with dbmod.connect() as conn:
        first = write_events(conn, events)
        second = write_events(conn, events)  # same events, should be no-op
    assert first > 0
    assert second == 0, "re-running write_events on same commits must be idempotent"


def test_write_events_auto_creates_projects(tmp_path, monkeypatch, git_repo):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    events = parse_history_repo(git_repo)
    with dbmod.connect() as conn:
        write_events(conn, events)
        projects = [r["city_slug"] for r in conn.execute("SELECT city_slug FROM projects")]
    assert "istanbul" in projects
    assert "kyoto" in projects


def test_deleted_file_does_not_count_as_revision(tmp_path):
    """Gemini r1 MED: deleting SCRIPT.md must NOT register as a 'revision'."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@t", "LC_ALL": "C"}
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=repo, check=True, env=env)
    # Commit 1: add istanbul/SCRIPT.md (should be script_started)
    (repo / "istanbul").mkdir()
    (repo / "istanbul" / "SCRIPT.md").write_text("v1")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "feat(istanbul): add script"], cwd=repo, check=True, env=env)
    # Commit 2: DELETE istanbul/SCRIPT.md — must NOT be classified as revision.
    (repo / "istanbul" / "SCRIPT.md").unlink()
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "chore: remove istanbul script"], cwd=repo, check=True, env=env)

    events = parse_history_repo(repo)
    # First commit: script_started. Second commit: must NOT be 'revision'.
    event_types = [e.event_type for e in events if e.city_slug == "istanbul"]
    # At least one script_started; the deletion commit should be unclassified
    # (inherited scaffold from the 2nd-pass upgrade may also apply).
    assert "script_started" in event_types
    # Count revisions — should be zero because the only other istanbul commit DELETED the file.
    revisions = [e for e in events if e.event_type == "revision" and e.city_slug == "istanbul"]
    assert len(revisions) == 0


def test_batch_phase3_commit_flags_also_script_started(tmp_path):
    """Codex r1 MED: when first SCRIPT.md touch is a phase3/final commit,
    event_type stays script_finished but event_value carries 'also:script_started'."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@t", "LC_ALL": "C"}
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=repo, check=True, env=env)
    (repo / "nagasaki").mkdir()
    (repo / "nagasaki" / "SCRIPT.md").write_text("final script")
    (repo / "nagasaki" / "TELEPROMPTER.md").write_text("teleprompter")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "commit", "-q", "-m", "phase3(nagasaki): SCRIPT + TELEPROMPTER"],
        cwd=repo, check=True, env=env,
    )
    events = parse_history_repo(repo)
    nag = [e for e in events if e.city_slug == "nagasaki"]
    assert len(nag) == 1
    assert nag[0].event_type == "script_finished"
    assert nag[0].event_value == "also:script_started"


def test_no_scaffold_inferred_from_first_city_touch(tmp_path):
    """Codex r1 MED: city with no explicit scaffold subject gets the earliest
    commit upgraded to scaffold confidence 0.6 in the 2nd pass."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@t", "LC_ALL": "C"}
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=repo, check=True, env=env)
    (repo / "kyoto").mkdir()
    (repo / "kyoto" / "README.md").write_text("kyoto intro")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "feat(kyoto): add README"], cwd=repo, check=True, env=env)

    events = parse_history_repo(repo)
    kyoto = [e for e in events if e.city_slug == "kyoto"]
    assert len(kyoto) == 1
    assert kyoto[0].event_type == "scaffold"
    assert kyoto[0].confidence == 0.6
    assert kyoto[0].event_value == "inferred-first-city"


def test_scaffold_regex_rejects_false_positive():
    """Codex r1 MED: anchored regex rejects 'docs(x): scaffold note cleanup'."""
    from ingest.history_git import _SCAFFOLD_SUBJECT
    assert _SCAFFOLD_SUBJECT.search("docs(istanbul): scaffold note cleanup") is None
    assert _SCAFFOLD_SUBJECT.search("fix: scaffold generator bug") is None
    # True positives
    assert _SCAFFOLD_SUBJECT.search("scaffold(istanbul): initial") is not None
    assert _SCAFFOLD_SUBJECT.search("Initial commit") is not None
    assert _SCAFFOLD_SUBJECT.search("chore: scaffold kyoto directory") is not None


def test_added_file_included_in_active_set(tmp_path):
    """Codex r2 MED: status=A (newly added) must be included in active_files
    so SCRIPT.md additions trigger script_started."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@t", "LC_ALL": "C"}
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=repo, check=True, env=env)
    # Newly added file (status=A in --raw output)
    (repo / "prague").mkdir()
    (repo / "prague" / "SCRIPT.md").write_text("fresh script")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "feat(prague): add script"], cwd=repo, check=True, env=env)
    events = parse_history_repo(repo)
    prague = [e for e in events if e.city_slug == "prague"]
    assert any(e.event_type == "script_started" for e in prague), \
        "newly added SCRIPT.md (status=A) must trigger script_started"


def test_rename_preserves_active_file(tmp_path):
    """Codex r2 MED: git rename detection produces status like R100 which
    must normalise to R (kept in active set) — renamed SCRIPT.md still counts."""
    from ingest.history_git import _active_files
    # Directly unit-test the normaliser: if _iter_commits emits ('R', path),
    # _active_files should keep it.
    assert _active_files([("R", "istanbul/SCRIPT.md")]) == ["istanbul/SCRIPT.md"]
    assert _active_files([("A", "new.md"), ("D", "gone.md"), ("M", "mod.md")]) == ["new.md", "mod.md"]
    # Copy status (C100 → C) also kept.
    assert _active_files([("C", "copied.md")]) == ["copied.md"]


def test_rename_normalisation_via_real_git(tmp_path):
    """End-to-end: git mv of DRAFT.md → SCRIPT.md. _classify does EXACT
    equality match `f == f'{city}/SCRIPT.md'`, so the parser MUST surface
    the destination path (not 'old\\tnew' as a single string). The rename
    commit is the first SCRIPT.md touch for the city, so it MUST trigger
    script_started (Codex r3 exact-match lock-down)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@t", "LC_ALL": "C"}
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=repo, check=True, env=env)
    (repo / "warsaw").mkdir()
    (repo / "warsaw" / "DRAFT.md").write_text("initial content\n" * 50)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "feat(warsaw): draft"], cwd=repo, check=True, env=env)
    # Rename DRAFT.md → SCRIPT.md — git detects as R100.
    subprocess.run(["git", "mv", "warsaw/DRAFT.md", "warsaw/SCRIPT.md"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "feat(warsaw): rename to SCRIPT"], cwd=repo, check=True, env=env)
    events = parse_history_repo(repo)
    warsaw = [e for e in events if e.city_slug == "warsaw"]
    rename_event = warsaw[-1]  # chronologically last
    # Exact equality: the dest path MUST be in active_files as literal
    # "warsaw/SCRIPT.md", not "warsaw/DRAFT.md\twarsaw/SCRIPT.md".
    assert "warsaw/SCRIPT.md" in rename_event.payload["touched_files"], \
        f"rename must surface destination path exactly: {rename_event.payload['touched_files']}"
    # And the event type MUST be script_started (first SCRIPT.md in city).
    assert rename_event.event_type == "script_started", \
        f"rename-to-SCRIPT.md first touch must trigger script_started: {rename_event.event_type}"


def test_copy_status_surfaces_destination_path(tmp_path):
    """Codex r3: C (copy) status must emit destination path, not 'src\\tdst'.

    We can't easily trigger C via stock git commands without -C flag on log,
    but we can unit-test the parser's path handling by simulating a raw
    line shape. The real parser is exercised via _iter_commits + gets R100
    through git mv above; C075 shape is the same structure.
    """
    from ingest.history_git import _iter_commits
    # Direct subprocess test of a synthetic repo where we force --find-copies
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        env = {**os.environ, "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@t", "LC_ALL": "C"}
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
        subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=repo, check=True, env=env)
        (repo / "krakow").mkdir()
        content = "unique line " * 100
        (repo / "krakow" / "ORIGINAL.md").write_text(content)
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
        subprocess.run(["git", "commit", "-q", "-m", "feat(krakow): original"], cwd=repo, check=True, env=env)
        # Copy via cp + git add — git log --find-copies would detect.
        (repo / "krakow" / "COPY.md").write_text(content)
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
        subprocess.run(["git", "commit", "-q", "-m", "feat(krakow): copy"], cwd=repo, check=True, env=env)

        # Verify the parser yields destination paths cleanly for this repo.
        commits = list(_iter_commits(repo))
        latest_files = commits[0][3]  # newest commit files
        # Regardless of whether git detected copy (depends on --find-copies flag),
        # the new COPY.md file MUST appear as its own path, not as src\tdst blob.
        paths = [path for status, path in latest_files]
        assert any("krakow/COPY.md" == p for p in paths), \
            f"COPY.md destination path missing or malformed: {paths}"


def test_unclassified_events_still_written(git_repo, tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    events = parse_history_repo(git_repo)
    with dbmod.connect() as conn:
        write_events(conn, events)
        unclassified = conn.execute(
            "SELECT COUNT(*) FROM git_events WHERE event_type='unclassified'"
        ).fetchone()[0]
    assert unclassified >= 1  # the root README typo commit
