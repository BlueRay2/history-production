"""Parse {city}/COST_ESTIMATE.md for cost-per-video KPI.

Fail-closed: if the file is missing or no canonical total line is found,
returns `None`. Never fabricates numbers from partial subtotals (per
consensus finding F-02 J-03 discipline).

Accepted canonical total-line patterns (case-insensitive):
  - `**Total: $X.XX**`
  - `**Grand total: $X.XX**`
  - `**Итого: N credits**`
  - `**Total: N credits**`
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

_LOG = logging.getLogger(__name__)

# Accepted canonical total-line regexes. Each captures (value, unit).
_TOTAL_PATTERNS = [
    re.compile(r"\*\*\s*(?:grand\s+)?total\s*:\s*\$\s*([\d.,]+)\s*\*\*", re.IGNORECASE),
    re.compile(r"\*\*\s*(?:grand\s+)?total\s*:\s*([\d.,]+)\s+credits?\s*\*\*", re.IGNORECASE),
    re.compile(r"\*\*\s*итого\s*:\s*([\d.,]+)\s+credits?\s*\*\*", re.IGNORECASE),
    re.compile(r"\*\*\s*итого\s*:\s*\$\s*([\d.,]+)\s*\*\*", re.IGNORECASE),
]


@dataclass(frozen=True)
class CostEstimate:
    city_slug: str
    total_value: float
    unit: str            # 'USD' or 'credits'
    source_path: str     # absolute path of the COST_ESTIMATE.md file
    source_line: str     # the raw matched line


def _parse_file(path: Path, city_slug: str) -> CostEstimate | None:
    """Scan a single COST_ESTIMATE.md file for a canonical total line.

    Returns None if no canonical line matches (fail-closed). Logs warning.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for i, pattern in enumerate(_TOTAL_PATTERNS):
            m = pattern.search(line)
            if m:
                raw_val = m.group(1).replace(",", "")
                try:
                    value = float(raw_val)
                except ValueError:
                    continue
                unit = "USD" if i in (0, 3) else "credits"
                return CostEstimate(
                    city_slug=city_slug,
                    total_value=value,
                    unit=unit,
                    source_path=str(path),
                    source_line=line,
                )
    _LOG.warning("no canonical total line in %s (fail-closed)", path)
    return None


def parse_city_cost(repo_root: Path, city_slug: str) -> CostEstimate | None:
    """Search both conventional locations for a city's COST_ESTIMATE.md.

    Per consensus F-07: supports both `{city}/COST_ESTIMATE.md` (current
    nagasaki-v2 / istanbul convention) and `{city}/docs/COST_ESTIMATE.md`
    (future convention). Returns the first successful parse or None.
    """
    candidates = [
        repo_root / city_slug / "COST_ESTIMATE.md",
        repo_root / city_slug / "docs" / "COST_ESTIMATE.md",
    ]
    for path in candidates:
        if path.exists():
            parsed = _parse_file(path, city_slug)
            if parsed is not None:
                return parsed
    return None


def scan_all_cities(repo_root: Path) -> list[CostEstimate]:
    """Iterate all top-level folders that look like city slugs and parse cost.

    Reserved non-city folders (docs/, scripts/, etc.) are skipped.
    """
    reserved = {
        "docs", "scripts", "tests", "app", "ingest", "db", "reviews",
        ".claude", ".github", ".entire", "previews", "shorts", "tiktok", "assets",
    }
    results: list[CostEstimate] = []
    for entry in sorted(repo_root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name in reserved:
            continue
        parsed = parse_city_cost(repo_root, entry.name)
        if parsed is not None:
            results.append(parsed)
    return results
