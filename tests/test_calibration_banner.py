"""Calibration banner visibility — <28d visible, >=28d hidden.

All tests inject a frozen `today` so they remain deterministic regardless
of real-clock drift (Codex r1 MED finding).
"""

from __future__ import annotations

from datetime import date

import pytest

from app import db as dbmod
from app.main import create_app

_FROZEN = date(2026, 4, 22)


@pytest.fixture(autouse=True)
def _migrated(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()


def test_banner_visible_when_channel_under_28_days():
    # Channel published 10 days before frozen today → banner visible.
    app = create_app(channel_published_at="2026-04-12T00:00:00Z", today=_FROZEN)
    app.config.update(TESTING=True)
    resp = app.test_client().get("/weekly")
    body = resp.data.decode()
    assert "Baseline calibration in progress" in body


def test_banner_hidden_when_channel_older_than_28_days():
    app = create_app(channel_published_at="2026-01-01T00:00:00Z", today=_FROZEN)
    app.config.update(TESTING=True)
    resp = app.test_client().get("/weekly")
    body = resp.data.decode()
    assert "Baseline calibration in progress" not in body


def test_banner_hidden_when_no_channel_publish_date():
    app = create_app(channel_published_at=None, today=_FROZEN)
    app.config.update(TESTING=True)
    resp = app.test_client().get("/weekly")
    body = resp.data.decode()
    assert "Baseline calibration in progress" not in body
