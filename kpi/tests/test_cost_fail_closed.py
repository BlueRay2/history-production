"""cost_per_video must surface NULL (not 0, not error) when COST_ESTIMATE.md is absent."""

from __future__ import annotations

import pytest

from app import db as dbmod
from app.services.kpis import cost_per_video


@pytest.fixture
def repo_with_partial_costs(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()

    # Build a fake repo layout: istanbul has COST_ESTIMATE.md, nagasaki does not.
    repo = tmp_path / "repo"
    (repo / "istanbul").mkdir(parents=True)
    (repo / "istanbul" / "COST_ESTIMATE.md").write_text(
        "# Cost estimate — Istanbul\n\n"
        "Partial subtotals live above.\n\n"
        "**Total: $17.42**\n",
        encoding="utf-8",
    )
    (repo / "nagasaki").mkdir(parents=True)
    # No COST_ESTIMATE.md at all → fail-closed → None.

    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO projects (city_slug, first_commit_at, canonical_path, status) "
            "VALUES ('istanbul', '2026-03-01T00:00:00Z', 'istanbul', 'active'),"
            "       ('nagasaki', '2026-04-01T00:00:00Z', 'nagasaki', 'active')"
        )
        conn.execute(
            "INSERT INTO videos (video_id, title, published_at) VALUES "
            "('v1', 'Istanbul Story', '2026-04-15T10:00:00Z'),"
            "('v2', 'Nagasaki Hope',  '2026-04-21T22:00:00Z')"
        )
        conn.execute(
            "INSERT INTO video_project_map "
            "(city_slug, video_id, confidence, mapping_source, active) "
            "VALUES ('istanbul', 'v1', 0.95, 'auto', 1),"
            "       ('nagasaki', 'v2', 0.95, 'auto', 1)"
        )
    yield db_file, repo


def test_cost_per_video_fail_closed_on_missing_file(repo_with_partial_costs):
    _db_file, repo = repo_with_partial_costs
    with dbmod.connect() as conn:
        rows = cost_per_video(conn, repo)
    by_video = {r["video_id"]: r for r in rows}
    assert by_video["v1"]["cost_value"] == 17.42
    assert by_video["v1"]["cost_unit"] == "USD"
    # Nagasaki has no COST_ESTIMATE.md → None, not 0, not raise.
    assert by_video["v2"]["cost_value"] is None
    assert by_video["v2"]["cost_unit"] is None


def test_cost_per_video_fail_closed_on_malformed_file(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()

    repo = tmp_path / "repo"
    (repo / "istanbul").mkdir(parents=True)
    # File exists but has no canonical total line.
    (repo / "istanbul" / "COST_ESTIMATE.md").write_text(
        "# Cost estimate — Istanbul\n\n"
        "We spent roughly 42 dollars maybe.\n"
        "Scene 1: $5\n",
        encoding="utf-8",
    )

    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO projects (city_slug, first_commit_at, canonical_path, status) "
            "VALUES ('istanbul', '2026-03-01T00:00:00Z', 'istanbul', 'active')"
        )
        conn.execute(
            "INSERT INTO videos (video_id, title, published_at) VALUES "
            "('v1', 'Istanbul Story', '2026-04-15T10:00:00Z')"
        )
        conn.execute(
            "INSERT INTO video_project_map "
            "(city_slug, video_id, confidence, mapping_source, active) "
            "VALUES ('istanbul', 'v1', 0.95, 'auto', 1)"
        )

    with dbmod.connect() as conn:
        rows = cost_per_video(conn, repo)

    assert len(rows) == 1
    assert rows[0]["video_id"] == "v1"
    assert rows[0]["cost_value"] is None
    assert rows[0]["cost_unit"] is None
