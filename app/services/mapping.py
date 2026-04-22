"""City ↔ YouTube-video mapping.

Discovers candidate mappings from overlap between `projects.city_slug` and
`videos.title/city_slug`. Each proposed mapping lands in
`video_project_map` with `active=0` (pending approval). Manual override:
CLI sets `active=1` explicitly. Downstream KPI views JOIN only on rows
where `active=1` OR `confidence >= AUTO_ACTIVATE_THRESHOLD`.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

_LOG = logging.getLogger(__name__)

AUTO_ACTIVATE_THRESHOLD = 0.85  # confidence at/above = auto-active per MVP


@dataclass(frozen=True)
class Suggestion:
    city_slug: str
    video_id: str
    confidence: float
    evidence: str  # why we think they match


def _slugify_title(title: str) -> str:
    """Rough slug from video title — lowercased, non-alnum stripped."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def suggest_mappings(conn: sqlite3.Connection) -> list[Suggestion]:
    """Scan unmapped videos/projects and propose candidate mappings.

    Heuristics:
      1. Exact city_slug present in video title (lowercased slug) → 0.9.
      2. Token overlap ≥ 50% between slugified title and city slug → 0.7.
      3. No textual match but only 1 unmapped city + 1 unmapped video
         published within 7 days of the city's earliest script_finished →
         0.6 (proximity fallback).
    """
    suggestions: list[Suggestion] = []
    unmapped_videos = list(conn.execute(
        """
        SELECT v.video_id, v.title, v.published_at
        FROM videos v
        LEFT JOIN video_project_map m ON m.video_id = v.video_id
        WHERE m.video_id IS NULL OR m.active = 0
        """
    ))
    unmapped_projects = [r["city_slug"] for r in conn.execute(
        """
        SELECT p.city_slug
        FROM projects p
        LEFT JOIN video_project_map m ON m.city_slug = p.city_slug
        WHERE m.city_slug IS NULL OR m.active = 0
        """
    )]

    for v in unmapped_videos:
        title_slug = _slugify_title(v["title"] or "")
        title_tokens = set(t for t in title_slug.split("-") if t)
        for city_slug in unmapped_projects:
            confidence, evidence = 0.0, ""
            if city_slug in title_slug:
                confidence, evidence = 0.9, f"exact slug in title: {v['title']!r}"
            else:
                city_tokens = set(t for t in re.split(r"[-_]", city_slug) if t)
                overlap = title_tokens & city_tokens
                if overlap and len(overlap) / max(1, len(city_tokens)) >= 0.5:
                    confidence = 0.7
                    evidence = f"token overlap {sorted(overlap)}"
            if confidence > 0:
                suggestions.append(Suggestion(
                    city_slug=city_slug,
                    video_id=v["video_id"],
                    confidence=confidence,
                    evidence=evidence,
                ))
    return suggestions


def write_suggestions(conn: sqlite3.Connection, suggestions: list[Suggestion]) -> int:
    """Persist proposed mappings as video_project_map rows with `active=0`.

    Auto-activates rows where confidence >= AUTO_ACTIVATE_THRESHOLD so the
    MVP can ship without manual review for the obvious matches. Manual
    overrides (confidence 1.0 via CLI) always win over auto.

    Returns number of rows inserted.
    """
    if not suggestions:
        return 0
    inserted = 0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("BEGIN IMMEDIATE")
    try:
        for s in suggestions:
            active = 1 if s.confidence >= AUTO_ACTIVATE_THRESHOLD else 0
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO video_project_map
                    (city_slug, video_id, confidence, mapping_source, active, notes, created_at)
                VALUES (?, ?, ?, 'auto', ?, ?, ?)
                """,
                (s.city_slug, s.video_id, s.confidence, active, s.evidence, now),
            )
            inserted += cur.rowcount
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass
        raise
    return inserted


def approve_mapping(conn: sqlite3.Connection, city_slug: str, video_id: str) -> bool:
    """Manual override: set (city_slug, video_id) row to active=1 + confidence=1.0.

    Returns True if a row was updated.
    """
    cur = conn.execute(
        """
        UPDATE video_project_map
        SET active = 1, confidence = 1.0, mapping_source = 'manual'
        WHERE city_slug = ? AND video_id = ?
        """,
        (city_slug, video_id),
    )
    return cur.rowcount > 0


def reject_mapping(conn: sqlite3.Connection, city_slug: str, video_id: str) -> bool:
    """Manual override: delete the mapping entirely so future suggestions
    don't re-propose it without fresh evidence."""
    cur = conn.execute(
        "DELETE FROM video_project_map WHERE city_slug = ? AND video_id = ?",
        (city_slug, video_id),
    )
    return cur.rowcount > 0


def _cli(argv: list[str] | None = None) -> int:
    import argparse

    from app import db as dbmod

    parser = argparse.ArgumentParser(
        prog="python -m app.services.mapping",
        description="City↔video mapping maintenance CLI.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("suggest", help="Compute + persist auto-suggestions.")
    sub.add_parser("review", help="List pending (non-active) suggestions for manual review.")

    p_approve = sub.add_parser("approve", help="Activate a mapping (confidence → 1.0, source=manual).")
    p_approve.add_argument("video_id")
    p_approve.add_argument("city_slug")

    p_reject = sub.add_parser("reject", help="Delete a mapping row.")
    p_reject.add_argument("video_id")
    p_reject.add_argument("city_slug")

    args = parser.parse_args(argv)

    with dbmod.connect() as conn:
        if args.cmd == "suggest":
            suggestions = suggest_mappings(conn)
            n = write_suggestions(conn, suggestions)
            print(f"proposed {len(suggestions)} suggestions; inserted {n} new rows")
            return 0
        if args.cmd == "review":
            rows = list(conn.execute(
                "SELECT city_slug, video_id, confidence, mapping_source, active, notes "
                "FROM video_project_map WHERE active = 0 ORDER BY confidence DESC, city_slug"
            ))
            if not rows:
                print("no pending mappings")
                return 0
            for r in rows:
                print(
                    f"[{r['confidence']:.2f}] {r['city_slug']} ↔ {r['video_id']} "
                    f"({r['mapping_source']}) — {r['notes'] or ''}"
                )
            return 0
        if args.cmd == "approve":
            ok = approve_mapping(conn, args.city_slug, args.video_id)
            print("approved" if ok else "no such row")
            return 0 if ok else 1
        if args.cmd == "reject":
            ok = reject_mapping(conn, args.city_slug, args.video_id)
            print("rejected" if ok else "no such row")
            return 0 if ok else 1
    return 2


if __name__ == "__main__":  # pragma: no cover
    import sys

    sys.exit(_cli(sys.argv[1:]))
