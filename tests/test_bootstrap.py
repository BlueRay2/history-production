"""Tests for scripts/bootstrap_youtube_oauth.py.

Covers: client_secret parsing, .env write, refuse-overwrite default, --rotate
path backs up previous .env, chmod 600 enforced.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

# Load the script as a module for unit-level tests.
BOOTSTRAP = Path(__file__).parent.parent / "scripts" / "bootstrap_youtube_oauth.py"


@pytest.fixture
def bootstrap(monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location("bootstrap_module", BOOTSTRAP)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mk_client_secret(path: Path, project_id: str = "proj-xyz") -> None:
    path.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "x.apps.googleusercontent.com",
                    "client_secret": "secret",
                    "project_id": project_id,
                }
            }
        ),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def test_load_gcp_project(tmp_path, bootstrap):
    cs = tmp_path / "client_secret.json"
    _mk_client_secret(cs, project_id="my-project-42")
    assert bootstrap._load_gcp_project(cs) == "my-project-42"


def test_write_env_creates_600_file(tmp_path, bootstrap):
    env = tmp_path / ".env"
    bootstrap._write_env(env, "1//fake-token", "my-project-42")
    assert env.exists()
    mode = env.stat().st_mode & 0o777
    assert mode == 0o600, f"expected 0o600 perms, got {oct(mode)}"
    content = env.read_text(encoding="utf-8")
    assert "YOUTUBE_REFRESH_TOKEN=1//fake-token" in content
    assert "GCP_PROJECT=my-project-42" in content
    assert "YOUTUBE_SCOPES=" in content


def test_main_refuses_overwrite(tmp_path, bootstrap, monkeypatch, capsys):
    cs = tmp_path / "client_secret.json"
    _mk_client_secret(cs)
    env = tmp_path / ".env"
    env.write_text("existing=1\n", encoding="utf-8")
    os.chmod(env, 0o600)
    rc = bootstrap.main(["--client-secret", str(cs), "--env", str(env)])
    assert rc == 3
    err = capsys.readouterr().err
    assert "already exists" in err
    assert "--rotate" in err


def test_main_rotate_backs_up(tmp_path, bootstrap, monkeypatch):
    cs = tmp_path / "client_secret.json"
    _mk_client_secret(cs)
    env = tmp_path / ".env"
    env.write_text("YOUTUBE_REFRESH_TOKEN=old\nGCP_PROJECT=old\n", encoding="utf-8")
    os.chmod(env, 0o600)

    monkeypatch.setattr(bootstrap, "_run_oauth_flow", lambda _p: "1//NEW-TOKEN")
    rc = bootstrap.main(["--client-secret", str(cs), "--env", str(env), "--rotate"])
    assert rc == 0
    backups = list(tmp_path.glob(".env.bak.*"))
    assert len(backups) == 1, "exactly one backup expected"
    backup_content = backups[0].read_text(encoding="utf-8")
    assert "old" in backup_content
    # Backup also 0o600
    assert backups[0].stat().st_mode & 0o777 == 0o600
    # New env has the new token
    assert "1//NEW-TOKEN" in env.read_text(encoding="utf-8")


def test_main_errors_on_missing_client_secret(tmp_path, bootstrap, capsys):
    cs = tmp_path / "does-not-exist.json"
    env = tmp_path / ".env"
    rc = bootstrap.main(["--client-secret", str(cs), "--env", str(env)])
    assert rc == 2
    assert "not found" in capsys.readouterr().err
