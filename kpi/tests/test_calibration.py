"""Baseline calibration gate (task-09)."""

from __future__ import annotations

from datetime import date, timedelta
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
    """Seed `n_weeks` worth of channel_metric_snapshots spread across
    distinct calendar days within each week so `weeks_of_data()` (which
    counts DISTINCT days, not raw rows) correctly clears the threshold.
    """
    conn.execute(
        "INSERT OR IGNORE INTO ingestion_runs (run_id, source, started_at, status) "
        "VALUES ('run-1', 'test', '2026-01-01T00:00:00Z', 'ok')"
    )
    # Start at 2026-01-05 (Monday of ISO week 2) so each n_weeks block
    # lands cleanly on its own ISO week without year-boundary edge cases.
    base_monday = date(2026, 1, 5)
    for week_ix in range(n_weeks):
        week_start = base_monday + timedelta(days=week_ix * 7)
        week_end = week_start + timedelta(days=6)
        for snap_ix in range(snapshots_per_week):
            day = week_start + timedelta(days=snap_ix)  # consecutive days
            observed_on = f"{day.isoformat()}T12:00:00Z"
            conn.execute(
                "INSERT OR IGNORE INTO channel_metric_snapshots "
                "(metric_key, grain, window_start, window_end, observed_on, "
                " value_num, run_id, preliminary) "
                "VALUES ('impressions', 'weekly', ?, ?, ?, ?, 'run-1', 0)",
                (
                    week_start.isoformat(),
                    week_end.isoformat(),
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


def test_auto_compute_preserves_existing_start_date(fresh_db, tmp_path):
    """Verify F-01 R1 MED2 fix: when an existing config with calibration.start_date
    exists, recompute MUST preserve that date instead of stamping today."""
    existing = tmp_path / "kpi-thresholds.yaml"
    existing.write_text(
        "calibration:\n  start_date: \"2025-12-01\"\n"
        "  required_weeks: 4\n  activated: false\n",
        encoding="utf-8",
    )
    with dbmod.connect() as conn:
        _seed_weeks(conn, n_weeks=4)
        out = tmp_path / "kpi-thresholds.yaml.proposed"
        auto_compute_thresholds(
            conn,
            output_path=out,
            metric_keys=("impressions",),
            existing_config_path=existing,
        )
    parsed = _load_yaml(out)
    assert parsed["calibration"]["start_date"] == "2025-12-01"


def test_auto_compute_required_weeks_param_propagated(fresh_db, tmp_path):
    """Verify F-01 R1 LOW fix: required_weeks param controls both gating and
    YAML output, so callers reading custom value from YAML stay consistent."""
    with dbmod.connect() as conn:
        _seed_weeks(conn, n_weeks=4)  # 4 weeks * 5 = 20 samples
        out = tmp_path / "kpi-thresholds.yaml.proposed"
        # required_weeks=6 means need 6*5=30 samples → 20 insufficient → null band
        result = auto_compute_thresholds(
            conn,
            output_path=out,
            metric_keys=("impressions",),
            required_weeks=6,
        )
    assert result["impressions"].green_above is None  # gated out
    parsed = _load_yaml(out)
    # And the YAML records the override, not the module default
    assert parsed["calibration"]["required_weeks"] == 6


def test_auto_compute_grain_filter(fresh_db, tmp_path):
    """Verify F-01 R1 HIGH1 fix: grain filter prevents daily/weekly mix in
    percentile computation. Seed daily-grain rows alongside weekly; weekly
    bands must be computed from weekly rows only."""
    with dbmod.connect() as conn:
        # Seed weekly rows with values in low range [100..119]
        _seed_weeks(conn, n_weeks=4)
        # Now inject daily-grain rows at very different values (10000+) — if
        # they leaked into the percentile pool, bands would be polluted.
        conn.execute(
            "INSERT OR IGNORE INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES ('run-2', 'test', '2026-02-01T00:00:00Z', 'ok')"
        )
        for i in range(20):
            conn.execute(
                "INSERT OR IGNORE INTO channel_metric_snapshots "
                "(metric_key, grain, window_start, window_end, observed_on, "
                " value_num, run_id, preliminary) "
                "VALUES ('impressions', 'daily', ?, ?, ?, ?, 'run-2', 0)",
                ("2026-02-01", "2026-02-01", f"2026-02-{(i % 28) + 1:02d}T12:00:00Z", 10000 + i),
            )
        out = tmp_path / "kpi-thresholds.yaml.proposed"
        result = auto_compute_thresholds(
            conn,
            output_path=out,
            metric_keys=("impressions",),
            grain="weekly",
        )
    band = result["impressions"]
    # Weekly values are 100..119; pollution would push bands to 5000+
    assert band.green_above is not None and band.green_above < 200
    assert band.red_below is not None and band.red_below < 200
