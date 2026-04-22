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
