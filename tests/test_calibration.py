"""Baseline calibration gate (task-09)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import db as dbmod
from app.services.calibration import (
    MIN_SNAPSHOTS_PER_WEEK,
    REQUIRED_WEEKS,
    _load_yaml,
    auto_compute_thresholds,
    load_status,
    weeks_of_data,
)


def _seed_weeks(conn, n_weeks: int, *, snapshots_per_week: int = MIN_SNAPSHOTS_PER_WEEK):
    """Seed `n_weeks` worth of channel_metric_snapshots, each with
    `snapshots_per_week` non-preliminary rows so `weeks_of_data` counts them.
    """
    conn.execute(
        "INSERT OR IGNORE INTO ingestion_runs (run_id, source, started_at, status) "
        "VALUES ('run-1', 'test', '2026-01-01T00:00:00Z', 'ok')"
    )
    for week_ix in range(n_weeks):
        # spread observed_on dates across distinct ISO weeks
        base = f"2026-01-{(week_ix * 7) + 1:02d}T00:00:00"
        for snap_ix in range(snapshots_per_week):
            observed_on = f"{base}.{snap_ix:03d}Z"
            conn.execute(
                "INSERT OR IGNORE INTO channel_metric_snapshots "
                "(metric_key, grain, window_start, window_end, observed_on, "
                " value_num, run_id, preliminary) "
                "VALUES ('impressions', 'weekly', ?, ?, ?, ?, 'run-1', 0)",
                (
                    base[:10], base[:10],
                    observed_on,
                    100.0 + week_ix * 20 + snap_ix,
                ),
            )


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    return db_file


def test_weeks_of_data_below_threshold(fresh_db):
    with dbmod.connect() as conn:
        _seed_weeks(conn, n_weeks=3)
        assert weeks_of_data(conn) == 3


def test_weeks_of_data_at_threshold(fresh_db):
    with dbmod.connect() as conn:
        _seed_weeks(conn, n_weeks=4)
        assert weeks_of_data(conn) == 4


def test_weeks_of_data_skips_preliminary_only_weeks(fresh_db):
    """A week with ONLY preliminary snapshots should not count."""
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES ('run-1', 'test', '2026-01-01T00:00:00Z', 'ok')"
        )
        for snap_ix in range(6):
            conn.execute(
                "INSERT INTO channel_metric_snapshots "
                "(metric_key, grain, window_start, window_end, observed_on, "
                " value_num, run_id, preliminary) "
                "VALUES ('impressions', 'weekly', '2026-01-01', '2026-01-07', "
                f"        '2026-01-05T00:00:00.{snap_ix:03d}Z', 100, 'run-1', 1)"
            )
        assert weeks_of_data(conn) == 0


def test_is_activated_requires_both_config_and_data(fresh_db, tmp_path):
    cfg = tmp_path / "kpi-thresholds.yaml"
    # Config says activated=false, plenty of data → still not activated.
    cfg.write_text(
        "calibration:\n  start_date: \"2026-01-01\"\n"
        "  required_weeks: 4\n  activated: false\n",
        encoding="utf-8",
    )
    with dbmod.connect() as conn:
        _seed_weeks(conn, n_weeks=5)
        status = load_status(conn, config_path=cfg)
    assert status.weeks_of_data == 5
    assert status.is_activated is False  # config flag false

    # Config says activated=true but only 2 weeks → still not activated.
    cfg.write_text(
        "calibration:\n  start_date: \"2026-01-01\"\n"
        "  required_weeks: 4\n  activated: true\n",
        encoding="utf-8",
    )
    # Fresh DB for 2-week scenario.
    import os
    os.remove(fresh_db)
    dbmod.migrate()
    with dbmod.connect() as conn:
        _seed_weeks(conn, n_weeks=2)
        status = load_status(conn, config_path=cfg)
    assert status.is_activated is False

    # Both conditions met → activated.
    with dbmod.connect() as conn:
        _seed_weeks(conn, n_weeks=5)
        # 2 + 5 = 7 weeks seeded total (different week indices, so 7 distinct weeks)
        status = load_status(conn, config_path=cfg)
    assert status.weeks_of_data >= 4
    assert status.activated_in_config is True
    assert status.is_activated is True


def test_auto_compute_writes_proposed_yaml(fresh_db, tmp_path):
    with dbmod.connect() as conn:
        _seed_weeks(conn, n_weeks=4, snapshots_per_week=MIN_SNAPSHOTS_PER_WEEK)
        out = tmp_path / "kpi-thresholds.yaml.proposed"
        result = auto_compute_thresholds(
            conn,
            output_path=out,
            metric_keys=("impressions",),
        )
    band = result["impressions"]
    assert band.green_above is not None
    assert band.yellow_above is not None
    assert band.red_below is not None
    # Green > yellow > red.
    assert band.green_above > band.yellow_above > band.red_below
    # File written and parseable back.
    parsed = _load_yaml(out)
    assert parsed["impressions"]["green_above"] == band.green_above
    assert parsed["calibration"]["activated"] is False


def test_auto_compute_returns_null_band_when_insufficient_data(fresh_db, tmp_path):
    with dbmod.connect() as conn:
        _seed_weeks(conn, n_weeks=2)  # 2 * 5 = 10 samples, need 20
        out = tmp_path / "kpi-thresholds.yaml.proposed"
        result = auto_compute_thresholds(conn, output_path=out, metric_keys=("impressions",))
    assert result["impressions"].green_above is None


def test_percentile_linear_interpolation():
    from app.services.calibration import _percentile
    # [1, 2, 3, 4, 5] — p25 should be 2.0, p50 = 3.0, p75 = 4.0
    assert _percentile([1, 2, 3, 4, 5], 25) == 2.0
    assert _percentile([1, 2, 3, 4, 5], 50) == 3.0
    assert _percentile([1, 2, 3, 4, 5], 75) == 4.0
