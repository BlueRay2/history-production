"""Empty-state rendering — routes must produce no stack traces on an empty DB.

Clock-sensitive reasons (channel_too_new) use a frozen `today` (Codex r1 MED).
"""

from __future__ import annotations

from datetime import date

import pytest

from app import db as dbmod
from app.main import create_app

_FROZEN = date(2026, 4, 22)


@pytest.fixture
def empty_app(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()  # schema only, no rows
    app = create_app()
    app.config.update(TESTING=True)
    return app


def test_weekly_empty_renders_200(empty_app):
    client = empty_app.test_client()
    resp = client.get("/weekly")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Нет данных ingestion-прогона" in body


def test_exceptions_empty_renders_200(empty_app):
    client = empty_app.test_client()
    resp = client.get("/exceptions")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Нет pending-предложений" in body


def test_monthly_empty_renders_200(empty_app):
    client = empty_app.test_client()
    resp = client.get("/monthly")
    assert resp.status_code == 200


def test_sparse_metric_reasons_render_on_weekly(tmp_path, monkeypatch):
    """Each J-03 reason (below_privacy_floor / channel_too_new /
    no_data_pulled) must render without crashing. Ok state is covered by
    test_dashboard_views.py.
    """
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    # Seed one weekly snapshot row so /weekly has a window but all cards
    # will trip the privacy floor because channel_subs < 50.
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES ('run-1', 'test', '2026-04-22T00:00:00Z', 'ok')"
        )
        conn.execute(
            "INSERT INTO channel_metric_snapshots "
            "(metric_key, grain, window_start, window_end, observed_on, "
            " value_num, run_id, preliminary) "
            "VALUES ('impressions', 'weekly', '2026-04-14', '2026-04-20', "
            "        '2026-04-22T00:00:00.123Z', 100, 'run-1', 0)"
        )
    app = create_app(channel_subs=44)  # below SUB_FLOOR=50
    app.config.update(TESTING=True)
    resp = app.test_client().get("/weekly")
    assert resp.status_code == 200
    assert "N/A" in resp.data.decode()


def test_channel_too_new_reason_renders(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES ('run-1', 'test', '2026-04-22T00:00:00Z', 'ok')"
        )
        conn.execute(
            "INSERT INTO channel_metric_snapshots "
            "(metric_key, grain, window_start, window_end, observed_on, "
            " value_num, run_id, preliminary) "
            "VALUES ('impressions', 'weekly', '2026-04-14', '2026-04-20', "
            "        '2026-04-22T00:00:00.123Z', 100, 'run-1', 0)"
        )
    # Channel published 5 days before frozen today → channel_too_new.
    app = create_app(
        channel_subs=500,
        channel_published_at="2026-04-17T00:00:00Z",
        today=_FROZEN,
    )
    app.config.update(TESTING=True)
    resp = app.test_client().get("/weekly")
    assert resp.status_code == 200
    body = resp.data.decode()
    # In calibration, card value shows an em-dash.
    assert "Канал младше 14 дней" in body


def test_no_data_pulled_reason_renders_on_card(tmp_path, monkeypatch):
    """Reach the `no_data_pulled` branch in _card.html — DB has at least
    one weekly snapshot (so /weekly has a window) but the specific metric
    `averageViewDuration` has no row for the selected window."""
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES ('run-1', 'test', '2026-04-22T00:00:00Z', 'ok')"
        )
        # Seed only `impressions` in the latest weekly window — the other
        # four metrics will therefore hit no_data_pulled.
        conn.execute(
            "INSERT INTO channel_metric_snapshots "
            "(metric_key, grain, window_start, window_end, observed_on, "
            " value_num, run_id, preliminary) "
            "VALUES ('impressions', 'weekly', '2026-04-14', '2026-04-20', "
            "        '2026-04-22T00:00:00.123Z', 1500, 'run-1', 0)"
        )
    app = create_app(channel_subs=500, today=_FROZEN)
    app.config.update(TESTING=True)
    resp = app.test_client().get("/weekly")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Нет данных ingestion-прогона за этот период" in body
