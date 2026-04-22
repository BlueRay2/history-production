"""End-to-end smoke tests for Flask routes with a seeded DB."""

from __future__ import annotations

import pytest

from app import db as dbmod
from app.main import create_app


@pytest.fixture
def seeded_app(tmp_path, monkeypatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("DASHBOARD_KPI_DB", str(db_file))
    dbmod.migrate()
    with dbmod.connect() as conn:
        conn.execute(
            "INSERT INTO ingestion_runs (run_id, source, started_at, status) "
            "VALUES ('run-1', 'test', '2026-04-22T00:00:00Z', 'ok')"
        )
        conn.execute(
            "INSERT INTO projects (city_slug, first_commit_at, canonical_path, status) "
            "VALUES ('istanbul', '2026-03-25T00:00:00Z', 'istanbul', 'active'),"
            "       ('orphan',   '2026-04-01T00:00:00Z', 'orphan',   'active')"
        )
        conn.execute(
            "INSERT INTO videos (video_id, title, published_at) VALUES "
            "('v1', 'Istanbul Story', '2026-04-18T10:00:00Z'),"
            "('v2', 'Some Random Title', '2026-04-19T10:00:00Z')"
        )
        conn.execute(
            "INSERT INTO video_project_map "
            "(city_slug, video_id, confidence, mapping_source, active) "
            "VALUES ('istanbul', 'v1', 0.95, 'auto', 1),"
            "       ('orphan',   'v2', 0.40, 'auto', 0)"
        )
        for m, val in [("impressions", 1500), ("views", 412), ("averageViewPercentage", 38.0)]:
            conn.execute(
                "INSERT INTO channel_metric_snapshots "
                "(metric_key, grain, window_start, window_end, observed_on, "
                " value_num, run_id, preliminary) "
                "VALUES (?, 'weekly', '2026-04-14', '2026-04-20', "
                "        '2026-04-22T00:00:00.111Z', ?, 'run-1', 0)",
                (m, val),
            )
    app = create_app(channel_subs=200)  # above privacy floor
    app.config.update(TESTING=True)
    return app


def test_root_redirects_to_weekly(seeded_app):
    client = seeded_app.test_client()
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/weekly")


def test_weekly_renders_with_metric_labels(seeded_app):
    client = seeded_app.test_client()
    resp = client.get("/weekly")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Impressions" in body
    assert "CTR" in body
    assert "Scripts finished" in body
    assert "2026-04-14" in body  # window header


def test_monthly_stub_renders(seeded_app):
    client = seeded_app.test_client()
    resp = client.get("/monthly")
    assert resp.status_code == 200
    assert "task-07" in resp.data.decode()


def test_exceptions_lists_unmapped_and_pending(seeded_app):
    client = seeded_app.test_client()
    resp = client.get("/exceptions")
    assert resp.status_code == 200
    body = resp.data.decode()
    # v2 has an active=0 row → appears in pending suggestions section.
    # It does NOT appear in the unmapped-videos section because "unmapped"
    # is strictly defined as "no active=1 row"; any pending row still
    # counts as a row.
    assert "Some Random Title" in body  # pending suggestion
    assert "orphan" in body              # suggested city for v2
    # v1 is fully mapped (active=1) → absent from both lists.
    assert "Istanbul Story" not in body


def test_approve_via_htmx_returns_hx_redirect(seeded_app):
    client = seeded_app.test_client()
    resp = client.post(
        "/mapping/approve",
        data={"video_id": "v2", "city_slug": "orphan"},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect") == "/exceptions"


def test_reject_via_form_redirect(seeded_app):
    client = seeded_app.test_client()
    resp = client.post(
        "/mapping/reject",
        data={"video_id": "v2", "city_slug": "orphan"},
    )
    assert resp.status_code == 303
    assert resp.headers["Location"].endswith("/exceptions")
