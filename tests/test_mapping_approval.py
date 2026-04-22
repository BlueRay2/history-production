"""Approving a pending mapping removes it from exceptions."""

from __future__ import annotations

from datetime import date

import pytest

from app import db as dbmod
from app.main import create_app

_FROZEN = date(2026, 4, 22)


@pytest.fixture
def seeded_exceptions(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO projects (city_slug, first_commit_at, canonical_path, status) "
            "VALUES ('kyoto', '2026-04-01T00:00:00Z', 'kyoto', 'active')"
        )
        conn.execute(
            "INSERT INTO videos (video_id, title, published_at) VALUES "
            "('v1', 'Ancient Capital', '2026-04-15T00:00:00Z')"
        )
        conn.execute(
            "INSERT INTO video_project_map "
            "(city_slug, video_id, confidence, mapping_source, active) "
            "VALUES ('kyoto', 'v1', 0.6, 'auto', 0)"
        )
    app = create_app(channel_subs=200, today=_FROZEN, repo_root=tmp_path)
    app.config.update(TESTING=True)
    return app


def test_approve_removes_from_exceptions(seeded_exceptions):
    client = seeded_exceptions.test_client()

    # Before approve: v1 appears in both unmapped and pending sections.
    resp = client.get("/exceptions")
    assert "Ancient Capital" in resp.data.decode()

    # Approve via HTMX.
    resp = client.post(
        "/mapping/approve",
        data={"video_id": "v1", "city_slug": "kyoto"},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200

    # After approve: v1 is mapped (active=1), so it drops out of both lists.
    resp = client.get("/exceptions")
    body = resp.data.decode()
    assert "Ancient Capital" not in body
    assert "Все видео сопоставлены с городом." in body


def test_reject_removes_pending_row(seeded_exceptions):
    client = seeded_exceptions.test_client()
    resp = client.post(
        "/mapping/reject",
        data={"video_id": "v1", "city_slug": "kyoto"},
    )
    assert resp.status_code == 303

    resp = client.get("/exceptions")
    body = resp.data.decode()
    # Row removed from pending. v1 still appears as unmapped (no active=1 row now).
    assert "Нет pending-предложений." in body
    assert "Ancient Capital" in body  # still shows up as unmapped video
