"""Flask app for KPI metrics-vault monitoring (task-07).

Reads exclusively from views and tables defined by migrations 001 (task-01)
and 002 (task-06). Renders 6 monitoring pages plus /api/health JSON.

This is the **monitoring-focused** UI replacing the legacy analytical
dashboard. Explicit principle (per task-07 spec): "this is plumbing
health, not channel performance".

Run:
    python -m app.monitoring  # binds 127.0.0.1:8787
"""

from __future__ import annotations

import os
from flask import Flask

from app.monitoring.routes import bp as monitoring_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(monitoring_bp)
    app.config["KPI_DB"] = os.environ.get(
        "KPI_DB", "/home/aiagent/assistant/state/kpi.sqlite"
    )
    return app


def main() -> None:
    app = create_app()
    host = os.environ.get("KPI_MONITORING_HOST", "127.0.0.1")
    port = int(os.environ.get("KPI_MONITORING_PORT", "8787"))
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
