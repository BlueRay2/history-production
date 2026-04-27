"""Tests for app.services.mapping — city↔video mapping suggestions."""

from __future__ import annotations

import pytest

from app import db as dbmod
from app.services.mapping import (
    AUTO_ACTIVATE_THRESHOLD,
    Suggestion,
    approve_mapping,
    reject_mapping,
    suggest_mappings,
    write_suggestions,
)


@pytest.fixture
def fresh_db_with_seed(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO projects (city_slug, first_commit_at, canonical_path, status) "
            "VALUES ('istanbul', '2026-03-25T00:00:00Z', 'istanbul', 'active'), "
            "       ('nagasaki', '2026-04-01T00:00:00Z', 'nagasaki', 'active'), "
            "       ('unknown-city', '2026-04-10T00:00:00Z', 'unknown-city', 'active')"
        )
        conn.execute(
            "INSERT INTO videos (video_id, title, published_at) VALUES "
            "('v_istanbul_1', 'The Istanbul Story — Port Between Two Worlds', '2026-04-15T10:00:00Z'), "
            "('v_nagasaki_1', 'Nagasaki: Hope in the Ashes', '2026-04-21T22:00:00Z'), "
            "('v_random_1', 'Random video about something else', '2026-04-20T00:00:00Z')"
        )
    yield db_file


def test_suggest_exact_slug_in_title(fresh_db_with_seed):
    with dbmod.connect() as conn:
        suggestions = suggest_mappings(conn)
    # Should suggest istanbul → v_istanbul_1 at 0.9 confidence.
    istanbul_match = [s for s in suggestions if s.city_slug == "istanbul" and s.video_id == "v_istanbul_1"]
    assert len(istanbul_match) == 1
    assert istanbul_match[0].confidence == 0.9


def test_suggest_nagasaki(fresh_db_with_seed):
    with dbmod.connect() as conn:
        suggestions = suggest_mappings(conn)
    nag = [s for s in suggestions if s.city_slug == "nagasaki" and s.video_id == "v_nagasaki_1"]
    assert len(nag) == 1
    assert nag[0].confidence == 0.9


def test_no_false_match_for_random_title(fresh_db_with_seed):
    with dbmod.connect() as conn:
        suggestions = suggest_mappings(conn)
    assert not any(s.video_id == "v_random_1" for s in suggestions)


def test_write_suggestions_auto_activates_high_confidence(fresh_db_with_seed):
    with dbmod.connect() as conn:
        suggestions = suggest_mappings(conn)
        inserted = write_suggestions(conn, suggestions)
        assert inserted >= 2  # istanbul + nagasaki at least
        active = list(conn.execute(
            "SELECT city_slug, video_id, active FROM video_project_map WHERE confidence >= ?",
            (AUTO_ACTIVATE_THRESHOLD,),
        ))
        assert all(r["active"] == 1 for r in active)


def test_approve_and_reject(fresh_db_with_seed):
    with dbmod.connect() as conn:
        # Manually insert a low-confidence row
        conn.execute(
            "INSERT INTO video_project_map (city_slug, video_id, confidence, mapping_source, active) "
            "VALUES ('istanbul', 'v_random_1', 0.4, 'auto', 0)"
        )
        assert approve_mapping(conn, "istanbul", "v_random_1") is True
        row = conn.execute(
            "SELECT active, confidence, mapping_source FROM video_project_map "
            "WHERE city_slug='istanbul' AND video_id='v_random_1'"
        ).fetchone()
        assert row["active"] == 1
        assert row["confidence"] == 1.0
        assert row["mapping_source"] == "manual"
        # Reject removes the row entirely.
        assert reject_mapping(conn, "istanbul", "v_random_1") is True
        assert conn.execute(
            "SELECT COUNT(*) FROM video_project_map "
            "WHERE city_slug='istanbul' AND video_id='v_random_1'"
        ).fetchone()[0] == 0
