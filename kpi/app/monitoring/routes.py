"""Routes for the monitoring UI (task-07).

All routes are read-only except `/schema-drift/<id>/ack` (POST) which
flips an `acknowledged_at` timestamp on a single drift entry.

Database access is per-request via a thin `_db()` helper. We DO NOT
share connections across requests (Flask's threading model + SQLite
WAL = each request opens its own short-lived connection).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, jsonify, render_template, request, abort

bp = Blueprint("monitoring", __name__)


# ---------------------------------------------------------------------------
# DB helper
# ---------------------------------------------------------------------------


def _db() -> sqlite3.Connection:
    """Open a per-request SQLite connection in strict read-only mode."""
    path = current_app.config["KPI_DB"]
    if not Path(path).exists():
        # Fail loud — don't silently let SQLite create a writable empty DB.
        abort(503, description=f"KPI_DB not found at {path}")
    conn = sqlite3.connect(
        f"file:{path}?mode=ro",
        uri=True,
        timeout=5.0,
        isolation_level=None,
    )
    conn.row_factory = sqlite3.Row
    return conn


# A 'running' ingestion run that started >2h ago is treated as stuck/failed
# for health classification (avoids stuck poller hiding as in-progress).
STUCK_RUNNING_HOURS = 2.0


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _humanize(jd: float | None) -> str:
    """Convert julianday float to relative-time string ('12 minutes ago')."""
    if jd is None:
        return "—"
    try:
        # julianday 2440587.5 = unix epoch
        epoch_seconds = (jd - 2440587.5) * 86400.0
        dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return "—"
    delta = _now_utc() - dt
    s = int(delta.total_seconds())
    if s < 60:
        return f"{s}s ago"
    if s < 3600:
        return f"{s // 60}m ago"
    if s < 86400:
        return f"{s // 3600}h ago"
    return f"{s // 86400}d ago"


def _status_class(status: str) -> str:
    return {
        "ok": "green",
        "partial": "yellow",
        "api_failure": "red",
        "db_failure": "red",
        "auth_failed": "red",
        "quota_exhausted": "orange",
        "schema_drift": "yellow",
        "running": "gray",
    }.get(status, "gray")


# ---------------------------------------------------------------------------
# Page 1: 24h ingest summary
# ---------------------------------------------------------------------------


@bp.route("/")
def index() -> str:
    conn = _db()
    try:
        # Per-source last run + 24h counts
        rows = conn.execute(
            """
            SELECT
                source,
                COALESCE(source_detail, '') AS source_detail,
                MAX(started_at)             AS last_started_at,
                (SELECT status FROM ingestion_runs r2
                  WHERE r2.source = ir.source AND r2.source_detail IS ir.source_detail
                  ORDER BY started_at DESC LIMIT 1) AS last_status,
                SUM(CASE WHEN julianday(started_at) >= julianday('now', '-1 day') THEN 1 ELSE 0 END) AS count_24h_total,
                SUM(CASE WHEN julianday(started_at) >= julianday('now', '-1 day')
                          AND status NOT IN ('ok', 'running') THEN 1 ELSE 0 END) AS count_24h_failed,
                SUM(CASE WHEN julianday(started_at) >= julianday('now', '-1 day') THEN rows_written ELSE 0 END) AS rows_24h
            FROM ingestion_runs ir
            GROUP BY source, source_detail
            ORDER BY last_started_at DESC
            """
        ).fetchall()

        # Top-level health badge
        last_orch = conn.execute(
            "SELECT MAX(started_at) AS last_run FROM ingestion_runs WHERE source='nightly_orchestrator'"
        ).fetchone()
        hours_since = _hours_since(last_orch["last_run"] if last_orch else None)
        any_recent_non_ok = any(
            _is_failing(r["last_status"], r["last_started_at"]) and
            _hours_since(r["last_started_at"]) is not None and
            _hours_since(r["last_started_at"]) <= 24
            for r in rows
        )
        if hours_since is None or hours_since > 26:
            health = "down"
            health_emoji = "🔴"
        elif any_recent_non_ok:
            health = "degraded"
            health_emoji = "⚠️"
        else:
            health = "ok"
            health_emoji = "✅"

        rendered = []
        for r in rows:
            rendered.append({
                "source": r["source"],
                "source_detail": r["source_detail"],
                "last_started_relative": _humanize_isots(r["last_started_at"]),
                "last_status": r["last_status"] or "—",
                "status_class": _status_class(r["last_status"] or ""),
                "count_24h_total": r["count_24h_total"] or 0,
                "count_24h_failed": r["count_24h_failed"] or 0,
                "rows_24h": r["rows_24h"] or 0,
            })

        return render_template(
            "summary.html",
            rows=rendered,
            health=health,
            health_emoji=health_emoji,
            hours_since=round(hours_since, 1) if hours_since is not None else None,
        )
    finally:
        conn.close()


def _hours_since(iso_ts: str | None) -> float | None:
    if not iso_ts:
        return None
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (_now_utc() - dt).total_seconds() / 3600.0


def _is_failing(status: str | None, started_at: str | None) -> bool:
    """A run counts as failing if status is non-ok, OR if it's been
    'running' longer than STUCK_RUNNING_HOURS (poller stuck / crashed)."""
    if status is None:
        return False
    if status == "ok":
        return False
    if status == "running":
        h = _hours_since(started_at)
        return h is not None and h > STUCK_RUNNING_HOURS
    return True


def _humanize_isots(iso_ts: str | None) -> str:
    if not iso_ts:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return "—"
    delta = _now_utc() - dt
    s = int(delta.total_seconds())
    if s < 60:
        return f"{s}s ago"
    if s < 3600:
        return f"{s // 60}m ago"
    if s < 86400:
        return f"{s // 3600}h ago"
    return f"{s // 86400}d ago"


# ---------------------------------------------------------------------------
# Page 2: per-metric freshness (two-tier)
# ---------------------------------------------------------------------------


@bp.route("/freshness")
def freshness() -> str:
    conn = _db()
    try:
        prefix = (request.args.get("q") or "").strip()
        stale_min_str = (request.args.get("stale") or "").strip()
        # Whitelist: only the documented dropdown values are honoured.
        # Anything else (negative, inf, garbage) silently falls back to no filter.
        STALE_ALLOWED = {"1", "3", "7"}
        stale_min = float(stale_min_str) if stale_min_str in STALE_ALLOWED else None
        show_all = (request.args.get("all") or "") == "1"

        # Top tier: dimension_key='' only, sorted by stalest first
        sql = (
            "SELECT metric_key, days_since_last_obs, observation_count, last_obs_jd "
            "FROM v_metric_freshness "
            "WHERE dimension_key = '' "
        )
        params: list[Any] = []
        if prefix:
            sql += "AND metric_key LIKE ? "
            params.append(prefix + "%")
        if stale_min is not None:
            sql += "AND days_since_last_obs >= ? "
            params.append(stale_min)
        sql += "ORDER BY days_since_last_obs DESC"
        if not show_all:
            sql += " LIMIT 200"
        rows = conn.execute(sql, params).fetchall()

        rendered = []
        for r in rows:
            d = r["days_since_last_obs"]
            badge = (
                "green" if d is not None and d <= 1 else
                "yellow" if d is not None and d <= 3 else
                "orange" if d is not None and d <= 7 else
                "red"
            )
            rendered.append({
                "metric_key": r["metric_key"],
                "days": round(d, 2) if d is not None else None,
                "obs_count": r["observation_count"],
                "badge": badge,
                "last_obs_relative": _humanize(r["last_obs_jd"]),
            })
        return render_template(
            "freshness.html",
            metrics=rendered,
            query=prefix,
            stale=stale_min_str,
            show_all=show_all,
        )
    finally:
        conn.close()


@bp.route("/freshness/<path:metric_key>")
def freshness_drilldown(metric_key: str) -> str:
    """HTMX-loaded second tier: per-dimension freshness for a metric_key."""
    conn = _db()
    try:
        dim_prefix = (request.args.get("dim") or "").strip()
        show_all = (request.args.get("all") or "") == "1"
        sql = (
            "SELECT dimension_key, days_since_last_obs, observation_count "
            "FROM v_metric_freshness "
            "WHERE metric_key = ? AND dimension_key != '' "
        )
        params: list[Any] = [metric_key]
        if dim_prefix:
            sql += "AND dimension_key LIKE ? "
            params.append(dim_prefix + "%")
        sql += "ORDER BY days_since_last_obs DESC"
        if not show_all:
            sql += " LIMIT 30"
        rows = conn.execute(sql, params).fetchall()
        return render_template(
            "_freshness_drilldown.html",
            dims=[
                {
                    "dimension_key": r["dimension_key"],
                    "days": round(r["days_since_last_obs"], 2) if r["days_since_last_obs"] is not None else None,
                    "obs_count": r["observation_count"],
                }
                for r in rows
            ],
            metric_key=metric_key,
            dim_prefix=dim_prefix,
            show_all=show_all,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Page 3: quota usage
# ---------------------------------------------------------------------------


@bp.route("/quota")
def quota() -> str:
    conn = _db()
    try:
        today_rows = conn.execute(
            "SELECT api_name, units_used, request_count FROM v_quota_today"
        ).fetchall()
        # Last 7 days of quota_usage per api_name for sparkline
        since = (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()
        seven_d = conn.execute(
            "SELECT date_utc, api_name, units_used FROM quota_usage "
            "WHERE date_utc >= ? ORDER BY date_utc",
            (since,),
        ).fetchall()
        # Pivot for chart: {api: [(date, units), ...]}
        series: dict[str, list[dict[str, Any]]] = {}
        for r in seven_d:
            series.setdefault(r["api_name"], []).append(
                {"date": r["date_utc"], "units": r["units_used"]}
            )
        return render_template(
            "quota.html",
            today=[
                {
                    "api": r["api_name"],
                    "used": r["units_used"],
                    "requests": r["request_count"],
                    "pct": min(100, round(100.0 * r["units_used"] / 10000.0, 1)),
                }
                for r in today_rows
            ],
            series=series,
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Page 4: schema drift log
# ---------------------------------------------------------------------------


@bp.route("/schema-drift")
def schema_drift() -> str:
    conn = _db()
    try:
        source = request.args.get("source")
        drift_type = request.args.get("type")
        sql = (
            "SELECT id, detected_at, source, drift_type, identifier, notes, "
            "       acknowledged_at, acknowledged_by "
            "FROM schema_drift_log WHERE 1=1 "
        )
        params: list[Any] = []
        if source:
            sql += "AND source=? "
            params.append(source)
        if drift_type:
            sql += "AND drift_type=? "
            params.append(drift_type)
        sql += "ORDER BY detected_at DESC LIMIT 200"
        rows = conn.execute(sql, params).fetchall()
        return render_template(
            "schema_drift.html",
            rows=[dict(r) for r in rows],
            source=source or "",
            drift_type=drift_type or "",
        )
    finally:
        conn.close()


@bp.route("/schema-drift/<int:drift_id>/ack", methods=["POST"])
def schema_drift_ack(drift_id: int) -> Any:
    """Acknowledge a drift entry. Writes acknowledged_at + acknowledged_by."""
    # Re-open in writable mode (overrides ?mode=ro of _db())
    path = current_app.config["KPI_DB"]
    conn = sqlite3.connect(path, timeout=5.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        existing = conn.execute(
            "SELECT id FROM schema_drift_log WHERE id=?", (drift_id,)
        ).fetchone()
        if not existing:
            abort(404)
        ack_by = request.form.get("by") or (request.json.get("by") if request.is_json else None) or "ui"
        # Idempotent: only stamp the FIRST acknowledgement; subsequent POSTs
        # against an already-acknowledged row no-op but still return 204.
        conn.execute(
            "UPDATE schema_drift_log SET acknowledged_at=?, acknowledged_by=? "
            "WHERE id=? AND acknowledged_at IS NULL",
            (datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
             ack_by, drift_id),
        )
        return ("", 204)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Page 5: per-video coverage
# ---------------------------------------------------------------------------


@bp.route("/videos")
def videos() -> str:
    conn = _db()
    try:
        rows = conn.execute(
            """
            SELECT video_id, title, published_at,
                   metrics_pulled_7d, last_pulled_jd, days_since_last_pull
              FROM v_video_coverage_7d
             ORDER BY COALESCE(last_pulled_jd, 0) ASC
             LIMIT 500
            """
        ).fetchall()
        rendered = []
        for r in rows:
            recent_video = False
            if r["published_at"]:
                try:
                    pub_dt = datetime.fromisoformat(r["published_at"].replace("Z", "+00:00"))
                    recent_video = (_now_utc() - pub_dt) < timedelta(days=90)
                except ValueError:
                    pass
            metrics = r["metrics_pulled_7d"] or 0
            stale_red = recent_video and metrics == 0
            rendered.append({
                "video_id": r["video_id"],
                "title": (r["title"] or "")[:40],
                "metrics_7d": metrics,
                "last_pulled_relative": _humanize(r["last_pulled_jd"]),
                "stale_red": stale_red,
            })
        return render_template("videos.html", rows=rendered)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Page 6: errors register (last 50 failed runs)
# ---------------------------------------------------------------------------


@bp.route("/errors")
def errors() -> str:
    conn = _db()
    try:
        source = request.args.get("source")
        status = request.args.get("status")
        sql = (
            "SELECT run_id, started_at, source, source_detail, status, error_text "
            "FROM ingestion_runs "
            "WHERE status NOT IN ('ok', 'running') "
        )
        params: list[Any] = []
        if source:
            sql += "AND source=? "
            params.append(source)
        if status:
            sql += "AND status=? "
            params.append(status)
        sql += "ORDER BY started_at DESC LIMIT 50"
        rows = conn.execute(sql, params).fetchall()
        return render_template(
            "errors.html",
            rows=[
                {
                    "run_id": r["run_id"],
                    "started_at": r["started_at"],
                    "source": r["source"],
                    "source_detail": r["source_detail"] or "—",
                    "status": r["status"],
                    "status_class": _status_class(r["status"]),
                    "error_text_full": r["error_text"] or "",
                    "error_text": (r["error_text"] or "")[:200],
                }
                for r in rows
            ],
            source=source or "",
            status=status or "",
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# /api/health (JSON)
# ---------------------------------------------------------------------------


@bp.route("/api/health")
def api_health():
    conn = _db()
    try:
        last_orch = conn.execute(
            "SELECT MAX(started_at) AS t FROM ingestion_runs WHERE source='nightly_orchestrator'"
        ).fetchone()
        last = last_orch["t"] if last_orch else None
        hours = _hours_since(last)

        # Failing sources: any source whose latest run is non-ok, OR a
        # 'running' run that's been stuck >STUCK_RUNNING_HOURS.
        latest = conn.execute(
            """
            SELECT source, status, started_at FROM (
              SELECT source, status, started_at,
                     ROW_NUMBER() OVER (PARTITION BY source ORDER BY started_at DESC) AS rn
                FROM ingestion_runs
            ) WHERE rn=1
            """
        ).fetchall()
        failing = [
            r for r in latest
            if _is_failing(r["status"], r["started_at"])
            and (
                # /api/health and / agree on the 24h freshness window:
                # ancient failures aren't 'currently' degraded.
                _hours_since(r["started_at"]) is None
                or _hours_since(r["started_at"]) <= 24
            )
        ]

        # Today's quota
        today_rows = conn.execute(
            "SELECT api_name, units_used FROM v_quota_today"
        ).fetchall()
        quota_today = {r["api_name"]: r["units_used"] for r in today_rows}

        unack = conn.execute(
            "SELECT COUNT(*) AS n FROM schema_drift_log WHERE acknowledged_at IS NULL"
        ).fetchone()

        if hours is None or hours > 26:
            status = "down"
        elif failing:
            status = "degraded"
        else:
            status = "ok"

        return jsonify({
            "status": status,
            "last_orchestrator_run": last,
            "hours_since_last_run": round(hours, 1) if hours is not None else None,
            "failing_sources": sorted({r["source"] for r in failing}),
            "quota_used_today": quota_today,
            "schema_drift_unacknowledged": unack["n"] if unack else 0,
        })
    finally:
        conn.close()
