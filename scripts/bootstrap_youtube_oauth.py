#!/usr/bin/env python3
"""Interactive OAuth bootstrap for YouTube Data + Analytics APIs.

First-run flow (per task-02 spec):
  1. Expects `client_secret.json` at /home/aiagent/.config/youtube-api/client_secret.json (chmod 600).
  2. Prints the consent URL; user opens in browser, approves scopes, pastes the
     resulting auth code back into this script.
  3. Exchanges the code for an access+refresh token pair.
  4. Writes refresh token + GCP project id into `/home/aiagent/.config/youtube-api/.env` (chmod 600).

Subsequent calls:
  - Refuse to overwrite an existing `.env` unless `--rotate` is passed.
  - With `--rotate`, back up the old `.env` to `.env.bak.<timestamp>` before
    replacing.

Usage:
  bootstrap_youtube_oauth.py [--rotate] [--client-secret PATH] [--env PATH]

Security:
  - Never logs client_secret.json contents or refresh token values.
  - Enforces 0600 perms on both files.
  - Owner check: refuses to run if client_secret.json owner != current user.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import stat
import sys
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]

DEFAULT_CLIENT_SECRET = Path("/home/aiagent/.config/youtube-api/client_secret.json")
DEFAULT_ENV = Path("/home/aiagent/.config/youtube-api/.env")


def _enforce_600(path: Path) -> None:
    mode = path.stat().st_mode & 0o777
    if mode != 0o600:
        os.chmod(path, 0o600)


def _owner_check(path: Path) -> None:
    if path.stat().st_uid != os.getuid():
        raise SystemExit(
            f"refusing to read {path} — owner uid {path.stat().st_uid} != current uid {os.getuid()}"
        )


def _load_gcp_project(client_secret_path: Path) -> str:
    payload = json.loads(client_secret_path.read_text(encoding="utf-8"))
    # installed-app or web schemas both carry `project_id` under `installed` or `web`.
    for key in ("installed", "web"):
        if key in payload and "project_id" in payload[key]:
            return str(payload[key]["project_id"])
    raise RuntimeError("client_secret.json missing project_id under installed/web")


def _write_env(env_path: Path, refresh_token: str, project_id: str) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)
    # O_EXCL prevents the TOCTOU where another writer creates the file first.
    fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(
            fd,
            (
                "# YouTube API OAuth — written by scripts/bootstrap_youtube_oauth.py\n"
                f"YOUTUBE_REFRESH_TOKEN={refresh_token}\n"
                f"GCP_PROJECT={project_id}\n"
                f"YOUTUBE_SCOPES={','.join(SCOPES)}\n"
            ).encode("utf-8"),
        )
    finally:
        os.close(fd)
    # Defensive chmod in case umask widened.
    os.chmod(env_path, 0o600)


def _run_oauth_flow(client_secret_path: Path):
    # Lazy import: dependency only exists when task-02 pyproject is installed.
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), scopes=SCOPES)
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    auth_url, _state = flow.authorization_url(
        access_type="offline",
        prompt="consent",  # force refresh_token issuance
        include_granted_scopes="true",
    )
    print()
    print("=" * 72)
    print("Open this URL in a browser on any machine, approve the scopes:")
    print()
    print(auth_url)
    print()
    print("Google will show an authorisation code. Paste it below.")
    print("=" * 72)
    print()
    code = input("Authorisation code: ").strip()
    if not code:
        raise SystemExit("empty authorisation code — aborted")
    flow.fetch_token(code=code)
    creds = flow.credentials
    if creds.refresh_token is None:
        raise SystemExit(
            "no refresh_token returned — ensure the OAuth client is Desktop-app type "
            "and prompt=consent was used (existing grants may need revoking first)"
        )
    return creds.refresh_token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rotate", action="store_true", help="Replace existing .env (backs up old).")
    parser.add_argument("--client-secret", type=Path, default=DEFAULT_CLIENT_SECRET)
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args(argv)

    cs_path: Path = args.client_secret
    env_path: Path = args.env

    if not cs_path.exists():
        print(f"ERROR: client_secret.json not found at {cs_path}", file=sys.stderr)
        print("Download it from GCP Console → APIs → Credentials → Desktop OAuth client,", file=sys.stderr)
        print(f"save to {cs_path} with chmod 600.", file=sys.stderr)
        return 2

    _owner_check(cs_path)
    _enforce_600(cs_path)

    if env_path.exists() and not args.rotate:
        print(f"ERROR: {env_path} already exists. Pass --rotate to replace (old will be backed up).", file=sys.stderr)
        return 3

    if env_path.exists() and args.rotate:
        backup = env_path.with_suffix(
            env_path.suffix + f".bak.{_dt.datetime.now().strftime('%Y%m%dT%H%M%S')}"
        )
        shutil.copy2(env_path, backup)
        os.chmod(backup, 0o600)
        print(f"[bootstrap] backed up existing .env → {backup}", file=sys.stderr)

    project_id = _load_gcp_project(cs_path)
    refresh_token = _run_oauth_flow(cs_path)
    _write_env(env_path, refresh_token, project_id)
    print(f"[bootstrap] wrote refresh token → {env_path} (0600)", file=sys.stderr)
    print(f"[bootstrap] GCP project: {project_id}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
