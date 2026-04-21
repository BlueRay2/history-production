"""Minimal .env parser — std-lib only, no python-dotenv dependency for reading.

Updated r1 per Gemini MED finding: handle quoted values and inline `#`
comments so the parser survives manual edits or files produced by other
tools. Scope still intentionally narrow — we parse `KEY=VALUE` lines with
`#` comments, plus single/double-quoted values, with NO variable expansion
or multi-line values (those aren't needed for our use case).
"""

from __future__ import annotations

from pathlib import Path


def _strip_inline_comment(value: str) -> str:
    """Remove an inline `#` comment. Respects quoted regions.

    Examples:
        `foo # comment`  -> `foo`
        `"foo # bar"`    -> `"foo # bar"`  (inside quotes)
        `foo#bar`        -> `foo#bar`      (no space before `#`)
    Only treat `#` as a comment delimiter when preceded by whitespace AND
    not inside quotes. This matches dotenv de-facto semantics.
    """
    in_single = False
    in_double = False
    prev_whitespace = False
    for i, ch in enumerate(value):
        if ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == "#" and not in_single and not in_double and prev_whitespace:
            return value[:i].rstrip()
        prev_whitespace = ch.isspace()
    return value


def _unquote(value: str) -> str:
    """Strip a single layer of matching surrounding quotes."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def load_env(path: Path) -> dict[str, str]:
    """Parse a `.env`-style file into a dict.

    Supported:
      - `KEY=VALUE` lines
      - whole-line `# comment` lines
      - inline `# comment` (requires whitespace before `#`)
      - single- or double-quoted values (quotes stripped)
      - empty lines

    Not supported:
      - variable expansion (`$VAR`, `${VAR}`)
      - multi-line values
      - escape sequences inside quotes
    """
    out: dict[str, str] = {}
    if not path.exists():
        raise FileNotFoundError(f"env file not found: {path}")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = _strip_inline_comment(value.strip())
        value = _unquote(value.strip())
        out[key.strip()] = value
    return out
