"""Calibration banner visibility — data-driven gate (task-09).

Banner visible ⇔ calibration.activated=false in config OR weeks_of_data<4.
Banner hidden ⇔ activated=true AND weeks_of_data>=4.

All tests inject a frozen `today` so they remain deterministic regardless
of real-clock drift (task-06 r1 MED finding).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app import db as dbmod
from app.main import create_app
from tests.test_calibration import _seed_weeks

_FROZEN = date(2026, 4, 22)


@pytest.fixture
def fresh_db_and_config(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    return tmp_path


def test_banner_visible_when_no_config_exists(fresh_db_and_config):
    # No kpi-thresholds.yaml → activated=false → banner visible.
    app = create_app(today=_FROZEN, repo_root=fresh_db_and_config)
    app.config.update(TESTING=True)
    resp = app.test_client().get("/weekly")
    body = resp.data.decode()
    assert "Baseline calibration in progress" in body


def test_banner_visible_when_activated_false_in_config(fresh_db_and_config):
    cfg = fresh_db_and_config / "config" / "kpi-thresholds.yaml"
    cfg.write_text(
        "calibration:\n  start_date: \"2026-01-01\"\n"
        "  required_weeks: 4\n  activated: false\n",
        encoding="utf-8",
    )
    # Seed 5 weeks of data — still visible because config flag says false.
    with dbmod.connect() as conn:
        _seed_weeks(conn, n_weeks=5)
    app = create_app(today=_FROZEN, repo_root=fresh_db_and_config)
    app.config.update(TESTING=True)
    resp = app.test_client().get("/weekly")
    body = resp.data.decode()
    assert "Baseline calibration in progress" in body


def test_banner_visible_when_not_enough_weeks(fresh_db_and_config):
    cfg = fresh_db_and_config / "config" / "kpi-thresholds.yaml"
    cfg.write_text(
        "calibration:\n  start_date: \"2026-01-01\"\n"
        "  required_weeks: 4\n  activated: true\n",
        encoding="utf-8",
    )
    # Only 2 weeks of data.
    with dbmod.connect() as conn:
        _seed_weeks(conn, n_weeks=2)
    app = create_app(today=_FROZEN, repo_root=fresh_db_and_config)
    app.config.update(TESTING=True)
    resp = app.test_client().get("/weekly")
    body = resp.data.decode()
    assert "Baseline calibration in progress" in body


def test_banner_hidden_when_activated_and_enough_weeks(fresh_db_and_config):
    cfg = fresh_db_and_config / "config" / "kpi-thresholds.yaml"
    cfg.write_text(
        "calibration:\n  start_date: \"2026-01-01\"\n"
        "  required_weeks: 4\n  activated: true\n",
        encoding="utf-8",
    )
    with dbmod.connect() as conn:
        _seed_weeks(conn, n_weeks=5)
    app = create_app(today=_FROZEN, repo_root=fresh_db_and_config)
    app.config.update(TESTING=True)
    resp = app.test_client().get("/weekly")
    body = resp.data.decode()
    assert "Baseline calibration in progress" not in body
