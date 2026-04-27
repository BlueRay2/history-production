"""Tests for ingest.youtube_client.

Strategy (updated r1 per Codex + Gemini HIGH findings):
  googleapiclient builds request URLs from discovery docs at runtime, which
  makes exact-URL VCR cassette matching fragile. Instead we mock the Resource
  chain with unittest.mock and assert the intended API surface: which method
  chain is invoked, which kwargs are passed, how errors are classified, and
  how retries fire. Cassettes in tests/fixtures/youtube_cassettes/ remain as
  documented response-shape references (smoke-parsed below).

No network. No real credentials.
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


def test_cassette_fixtures_parseable():
    """Smoke: cassettes are committed and parseable as documentation of response shapes."""
    import yaml

    for name in ("channel_overview.yaml", "channel_analytics_7d.yaml", "video_retention_empty.yaml"):
        path = FIXTURE_DIR / name
        assert path.exists(), f"missing fixture {path}"
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "interactions" in doc and doc["interactions"], f"{name} has no interactions"


# -------- Mock-based API surface tests (r1 HIGH fix) ------------------------


def _mock_built_client():
    """Build a Mock that mimics googleapiclient Resource chains.

    `.channels().list(...).execute()` and
    `.reports().query(...).execute()` both return configurable response dicts.
    """
    from unittest.mock import MagicMock

    data = MagicMock(name="youtube_v3")
    analytics = MagicMock(name="youtubeAnalytics_v2")
    return data, analytics


@pytest.fixture
def client_with_mocks(fake_creds, monkeypatch):
    from unittest.mock import MagicMock, patch

    env, cs = fake_creds
    # Avoid real googleapiclient.discovery.build — stub it.
    data_mock, analytics_mock = _mock_built_client()

    def fake_build(name, _version, **_kwargs):
        return data_mock if name == "youtube" else analytics_mock

    # Patch googleapiclient.discovery.build globally so the YouTubeClient
    # __init__ picks up the stub on both calls. Also stub credentials so we
    # don't need real OAuth plumbing.
    fake_creds_obj = MagicMock(name="credentials")
    with patch("googleapiclient.discovery.build", new=fake_build), \
         patch("ingest.youtube_client._build_credentials", return_value=fake_creds_obj):
        from ingest.youtube_client import YouTubeClient

        client = YouTubeClient(env_path=env, client_secret_path=cs)
        yield client, data_mock, analytics_mock


def test_get_channel_overview_calls_data_api(client_with_mocks):
    client, data_mock, _ = client_with_mocks
    data_mock.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "UCjLrTC9jdfx6iI5w7SL8LHw", "statistics": {"subscriberCount": "44"}}]
    }
    result = client.get_channel_overview("UCjLrTC9jdfx6iI5w7SL8LHw", run_id="r-test")
    data_mock.channels.return_value.list.assert_called_once_with(
        part="snippet,statistics,brandingSettings", id="UCjLrTC9jdfx6iI5w7SL8LHw"
    )
    assert result["items"][0]["id"] == "UCjLrTC9jdfx6iI5w7SL8LHw"


def test_get_channel_analytics_validates_metrics(client_with_mocks):
    client, _, _ = client_with_mocks
    # Malformed metrics string should raise before touching the API.
    with pytest.raises(ValueError, match="invalid characters"):
        client.get_channel_analytics(
            start_date="2026-04-14",
            end_date="2026-04-20",
            metrics="views; DROP TABLE--",
            run_id="r-test",
        )


def test_get_channel_analytics_passes_kwargs(client_with_mocks):
    client, _, analytics_mock = client_with_mocks
    analytics_mock.reports.return_value.query.return_value.execute.return_value = {
        "rows": [[412, 1189]],
    }
    result = client.get_channel_analytics(
        start_date="2026-04-14",
        end_date="2026-04-20",
        metrics="views,impressionsClickThroughRate",
        dimensions="day",
        run_id="r-test",
    )
    analytics_mock.reports.return_value.query.assert_called_once_with(
        ids="channel==MINE",
        startDate="2026-04-14",
        endDate="2026-04-20",
        metrics="views,impressionsClickThroughRate",
        dimensions="day",
    )
    assert result["rows"][0][0] == 412


def test_get_retention_tolerates_empty_rows(client_with_mocks):
    """Sparse-metric path (J-03): small-channel retention returns empty rows,
    and the client MUST pass that through unchanged for task-05 to classify
    the reason as below_privacy_floor."""
    client, _, analytics_mock = client_with_mocks
    analytics_mock.reports.return_value.query.return_value.execute.return_value = {
        "rows": []
    }
    result = client.get_retention(
        video_id="vAbCdEf12345",
        start_date="2026-03-10",
        end_date="2026-04-20",
        run_id="r-test",
    )
    assert result["rows"] == []


def test_http_503_retries_then_succeeds(client_with_mocks, monkeypatch):
    """Transient 503 should be retried; on 3rd attempt success returns."""
    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        pytest.skip("google-api-python-client not installed")

    monkeypatch.setattr("time.sleep", lambda _s: None)

    class FakeResp:
        def __init__(self, status):
            self.status = status
            self.reason = "unavailable"

    client, data_mock, _ = client_with_mocks
    attempts = {"n": 0}

    def flaky_execute():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise HttpError(resp=FakeResp(503), content=b"unavailable")
        return {"items": [{"id": "UC-test"}]}

    data_mock.channels.return_value.list.return_value.execute = flaky_execute
    result = client.get_channel_overview("UC-test", run_id="r-retry")
    assert attempts["n"] == 3
    assert result["items"][0]["id"] == "UC-test"


def test_http_401_does_not_retry(client_with_mocks, monkeypatch):
    """Auth error (401) must fail fast — retrying cannot fix a bad credential."""
    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        pytest.skip("google-api-python-client not installed")

    monkeypatch.setattr("time.sleep", lambda _s: None)

    class FakeResp:
        def __init__(self):
            self.status = 401
            self.reason = "unauthorized"

    client, data_mock, _ = client_with_mocks
    attempts = {"n": 0}

    def always_401():
        attempts["n"] += 1
        raise HttpError(resp=FakeResp(), content=b"auth failed")

    data_mock.channels.return_value.list.return_value.execute = always_401
    with pytest.raises(HttpError):
        client.get_channel_overview("UC-test", run_id="r-auth")
    assert attempts["n"] == 1, "401 must not be retried"
