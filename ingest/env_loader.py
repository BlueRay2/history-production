"""Minimal .env parser — std-lib only, no python-dotenv dependency for reading.

We only need KEY=VALUE lines with `#` comments. Avoids pulling a runtime dep
for a 10-line task.
"""

from __future__ import annotations

from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
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
        out[key.strip()] = value.strip()
    return out
