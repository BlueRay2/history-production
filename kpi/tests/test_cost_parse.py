"""Tests for ingest.cost_parse — COST_ESTIMATE.md parser.

Fail-closed discipline: missing/ambiguous files → None, never fabricated
numbers. Supports both `{city}/COST_ESTIMATE.md` and `{city}/docs/COST_ESTIMATE.md`
per consensus F-07.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ingest.cost_parse import parse_city_cost, scan_all_cities


def _mk_repo(tmp_path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


def test_canonical_total_usd(tmp_path):
    repo = _mk_repo(tmp_path)
    (repo / "istanbul").mkdir()
    (repo / "istanbul" / "COST_ESTIMATE.md").write_text(
        "# Cost\n| a | b |\n**Total: $42.50**\n", encoding="utf-8"
    )
    result = parse_city_cost(repo, "istanbul")
    assert result is not None
    assert result.total_value == 42.5
    assert result.unit == "USD"
    assert result.city_slug == "istanbul"


def test_canonical_total_credits(tmp_path):
    repo = _mk_repo(tmp_path)
    (repo / "kyoto").mkdir()
    (repo / "kyoto" / "COST_ESTIMATE.md").write_text(
        "**Итого: 1250 credits**\n", encoding="utf-8"
    )
    result = parse_city_cost(repo, "kyoto")
    assert result is not None
    assert result.total_value == 1250.0
    assert result.unit == "credits"


def test_docs_subfolder_location(tmp_path):
    """F-07: parser checks both {city}/COST_ESTIMATE.md and {city}/docs/COST_ESTIMATE.md"""
    repo = _mk_repo(tmp_path)
    (repo / "quanzhou" / "docs").mkdir(parents=True)
    (repo / "quanzhou" / "docs" / "COST_ESTIMATE.md").write_text(
        "**Grand total: $78.00**\n", encoding="utf-8"
    )
    result = parse_city_cost(repo, "quanzhou")
    assert result is not None
    assert result.total_value == 78.0


def test_fail_closed_on_missing_file(tmp_path):
    repo = _mk_repo(tmp_path)
    # No istanbul folder at all
    assert parse_city_cost(repo, "istanbul") is None


def test_fail_closed_on_subtotal_only(tmp_path):
    """Subtotals that look like totals must NOT be picked up as canonical."""
    repo = _mk_repo(tmp_path)
    (repo / "nagasaki").mkdir()
    (repo / "nagasaki" / "COST_ESTIMATE.md").write_text(
        "## Seedance\nSubtotal: $10\n## Kling\nSubtotal: $5\n", encoding="utf-8"
    )
    result = parse_city_cost(repo, "nagasaki")
    assert result is None, "subtotals must NOT be parsed as canonical total"


def test_fail_closed_on_malformed_number(tmp_path):
    repo = _mk_repo(tmp_path)
    (repo / "broken").mkdir()
    (repo / "broken" / "COST_ESTIMATE.md").write_text(
        "**Total: $notanumber**\n**Итого: abc credits**\n", encoding="utf-8"
    )
    result = parse_city_cost(repo, "broken")
    assert result is None


def test_scan_all_cities_skips_reserved(tmp_path):
    repo = _mk_repo(tmp_path)
    (repo / "docs").mkdir()
    (repo / "docs" / "COST_ESTIMATE.md").write_text("**Total: $100**", encoding="utf-8")
    (repo / "scripts").mkdir()
    (repo / "scripts" / "COST_ESTIMATE.md").write_text("**Total: $200**", encoding="utf-8")
    (repo / "valid_city").mkdir()
    (repo / "valid_city" / "COST_ESTIMATE.md").write_text("**Total: $42**", encoding="utf-8")
    results = scan_all_cities(repo)
    city_slugs = {r.city_slug for r in results}
    assert "valid_city" in city_slugs
    assert "docs" not in city_slugs
    assert "scripts" not in city_slugs


def test_scan_all_cities_tolerates_cities_without_cost_file(tmp_path):
    repo = _mk_repo(tmp_path)
    (repo / "city_a").mkdir()
    (repo / "city_a" / "COST_ESTIMATE.md").write_text("**Total: $42**", encoding="utf-8")
    (repo / "city_b").mkdir()
    # city_b has no COST_ESTIMATE.md at all
    results = scan_all_cities(repo)
    assert len(results) == 1
    assert results[0].city_slug == "city_a"
