"""Tests for ingest.youtube_client.

Cassette-based tests use vcrpy to replay pre-recorded HTTP interactions.
Cassettes live in tests/fixtures/youtube_cassettes/.

No network. No real credentials. Fixtures stub out OAuth credential building
so googleapiclient's discovery cache lookup still works.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("googleapiclient", reason="google-api-python-client not installed; task-02 deps required")
pytest.importorskip("google.oauth2", reason="google-auth not installed; task-02 deps required")

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "youtube_cassettes"


@pytest.fixture
def fake_creds(tmp_path, monkeypatch):
    """Build a minimal .env + client_secret.json pair pointing the module at them."""
    client_secret = tmp_path / "client_secret.json"
    client_secret.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "fake-client-id.apps.googleusercontent.com",
                    "client_secret": "fake-client-secret",
                    "project_id": "cities-evolution-kpi-test",
                }
            }
        ),
        encoding="utf-8",
    )
    env = tmp_path / ".env"
    env.write_text(
        "YOUTUBE_REFRESH_TOKEN=1//fake-refresh-token\n"
        "GCP_PROJECT=cities-evolution-kpi-test\n"
        "YOUTUBE_SCOPES=https://www.googleapis.com/auth/youtube.readonly,"
        "https://www.googleapis.com/auth/yt-analytics.readonly\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("YOUTUBE_CREDS_ENV", str(env))
    return env, client_secret


def test_creds_loader_parses_env(fake_creds):
    from ingest.youtube_client import _load_creds

    env, cs = fake_creds
    creds = _load_creds(env, cs)
    assert creds.refresh_token == "1//fake-refresh-token"
    assert creds.gcp_project == "cities-evolution-kpi-test"
    assert "https://www.googleapis.com/auth/youtube.readonly" in creds.scopes


def test_creds_loader_raises_on_missing_key(tmp_path, fake_creds):
    from ingest.youtube_client import _load_creds

    env, cs = fake_creds
    # Nuke a required key.
    env.write_text("GCP_PROJECT=only-this\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="YOUTUBE_REFRESH_TOKEN"):
        _load_creds(env, cs)


def test_retriable_classification_on_googleapi_error():
    from ingest.youtube_client import _is_retriable_googleapi_error

    class FakeResp:
        def __init__(self, status: int):
            self.status = status
            self.reason = f"HTTP {status}"

    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        pytest.skip("google-api-python-client not installed")

    assert _is_retriable_googleapi_error(
        HttpError(resp=FakeResp(503), content=b"transient")
    )
    assert _is_retriable_googleapi_error(
        HttpError(resp=FakeResp(429), content=b"quota")
    )
    assert not _is_retriable_googleapi_error(
        HttpError(resp=FakeResp(401), content=b"auth")
    )
    assert not _is_retriable_googleapi_error(
        HttpError(resp=FakeResp(403), content=b"forbidden")
    )
    assert not _is_retriable_googleapi_error(RuntimeError("unrelated"))


def test_cassette_fixtures_exist():
    """Smoke: cassettes are committed and parseable."""
    import yaml  # pyyaml usually pre-installed via pytest env

    for name in ("channel_overview.yaml", "channel_analytics_7d.yaml", "video_retention_empty.yaml"):
        path = FIXTURE_DIR / name
        assert path.exists(), f"missing fixture {path}"
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "interactions" in doc and doc["interactions"], f"{name} has no interactions"
