"""Flask app factory for the KPI dashboard.

Binds to 127.0.0.1:$DASHBOARD_KPI_PORT (default 8787). MVP localhost-only,
no auth. Routes:
  GET  /              -> 302 to /weekly
  GET  /weekly        -> weekly dashboard
  GET  /monthly       -> stub (task-07 populates)
  GET  /exceptions    -> unmapped videos + low-confidence mappings
  POST /mapping/approve, /mapping/reject -> HTMX handlers
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

from app import db as dbmod
from app.services.mapping import approve_mapping, reject_mapping
from app.services.weekly_view import channel_age_days, weekly_snapshot

_CALIBRATION_MIN_DAYS = 28  # matches task-09 gate


def create_app(
    *,
    channel_subs: int | None = None,
    channel_published_at: str | None = None,
) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent.parent / "templates"),
        static_folder=str(Path(__file__).parent.parent / "static"),
    )

    # App-level "runtime channel profile" — injected at create-time for tests,
    # loaded from env in production startup. Dashboard is single-channel.
    app.config["CHANNEL_SUBS"] = channel_subs if channel_subs is not None \
        else _env_int("DASHBOARD_CHANNEL_SUBS")
    app.config["CHANNEL_PUBLISHED_AT"] = channel_published_at \
        or os.environ.get("DASHBOARD_CHANNEL_PUBLISHED_AT")

    def _ctx_globals() -> dict:
        age = channel_age_days(app.config["CHANNEL_PUBLISHED_AT"])
        weeks = age // 7 if age is not None else None
        return {
            "calibration_active": age is not None and age < _CALIBRATION_MIN_DAYS,
            "calibration_weeks": weeks,
            "calibration_target_weeks": _CALIBRATION_MIN_DAYS // 7,
        }

    @app.context_processor
    def _inject_globals() -> dict:
        return _ctx_globals()

    @app.route("/")
    def root():
        return redirect(url_for("weekly"))

    @app.route("/weekly")
    def weekly():
        with dbmod.connect() as conn:
            snap = weekly_snapshot(
                conn,
                channel_subs=app.config["CHANNEL_SUBS"],
                channel_published_at=app.config["CHANNEL_PUBLISHED_AT"],
            )
        return render_template("weekly.html", snap=snap)

    @app.route("/monthly")
    def monthly():
        # task-07 populates full page; this stub is kept so /monthly is a
        # valid navigation target from the tab bar on day one.
        return render_template("monthly.html", snap=None)

    @app.route("/exceptions")
    def exceptions():
        with dbmod.connect() as conn:
            unmapped = list(conn.execute(
                """
                SELECT v.video_id, v.title, v.published_at
                FROM videos v
                WHERE NOT EXISTS (
                    SELECT 1 FROM video_project_map m
                    WHERE m.video_id = v.video_id AND m.active = 1
                )
                ORDER BY v.published_at DESC
                """
            ))
            pending = list(conn.execute(
                """
                SELECT m.city_slug, m.video_id, m.confidence, m.notes, v.title
                FROM video_project_map m
                JOIN videos v ON v.video_id = m.video_id
                WHERE m.active = 0
                ORDER BY m.confidence DESC
                """
            ))
        return render_template(
            "exceptions.html",
            unmapped=unmapped,
            pending=pending,
        )

    @app.post("/mapping/approve")
    def mapping_approve():
        video_id = request.form["video_id"]
        city_slug = request.form["city_slug"]
        with dbmod.connect() as conn:
            approve_mapping(conn, city_slug, video_id)
        return _htmx_redirect_or_ok(request, "/exceptions")

    @app.post("/mapping/reject")
    def mapping_reject():
        video_id = request.form["video_id"]
        city_slug = request.form["city_slug"]
        with dbmod.connect() as conn:
            reject_mapping(conn, city_slug, video_id)
        return _htmx_redirect_or_ok(request, "/exceptions")

    return app


def _env_int(key: str) -> int | None:
    raw = os.environ.get(key)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _htmx_redirect_or_ok(req, target: str):
    """Respect HTMX's `HX-Redirect` header for in-page navigation; otherwise
    a 303 See Other keeps browsers from reposting on refresh."""
    if req.headers.get("HX-Request") == "true":
        return ("", 200, {"HX-Redirect": target})
    return redirect(target, code=303)


def main() -> None:  # pragma: no cover
    port = _env_int("DASHBOARD_KPI_PORT") or 8787
    # 127.0.0.1 bind is load-bearing per task-08 spec — never 0.0.0.0 on MVP.
    create_app().run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":  # pragma: no cover
    main()
