"""Tests for app.lib.retry."""

from __future__ import annotations

import pytest

from app.lib.retry import NonRetriable, is_transient_http_status, retry


def test_transient_status_classification():
    for s in (408, 429, 500, 502, 503, 504, 599):
        assert is_transient_http_status(s), f"{s} should be transient"
    for s in (200, 301, 400, 401, 403, 404, 410):
        assert not is_transient_http_status(s), f"{s} should NOT be transient"


def test_retry_succeeds_after_transient_errors(monkeypatch):
    attempts = {"n": 0}
    monkeypatch.setattr("time.sleep", lambda _s: None)  # fast-forward

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    assert retry(flaky, max_attempts=5, base_delay=0.001) == "ok"
    assert attempts["n"] == 3


def test_retry_raises_after_exhaustion(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _s: None)

    def always_fails():
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError, match="nope"):
        retry(always_fails, max_attempts=3, base_delay=0.001)


def test_nonretriable_short_circuits(monkeypatch):
    attempts = {"n": 0}
    monkeypatch.setattr("time.sleep", lambda _s: None)

    def auth_error():
        attempts["n"] += 1
        raise NonRetriable() from RuntimeError("401 bad creds")

    with pytest.raises(RuntimeError, match="401 bad creds"):
        retry(auth_error, max_attempts=5, base_delay=0.001)
    assert attempts["n"] == 1, "NonRetriable must short-circuit on first attempt"


def test_custom_retriable_predicate(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _s: None)
    attempts = {"n": 0}

    def only_retry_value_error(_exc):
        return isinstance(_exc, ValueError)

    def mixed():
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise ValueError("transient")
        raise KeyError("non-retriable")

    with pytest.raises(KeyError, match="non-retriable"):
        retry(mixed, max_attempts=5, base_delay=0.001, retriable=only_retry_value_error)
    assert attempts["n"] == 2
