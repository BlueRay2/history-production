#!/usr/bin/env python3
"""Interactive OAuth bootstrap for YouTube Data + Analytics APIs.

First-run flow (per task-02 spec, updated r1 per Codex HIGH + Gemini MED):
  1. Expects `client_secret.json` at /home/aiagent/.config/youtube-api/client_secret.json (chmod 600).
  2. Starts a local loopback HTTP server on a free port, prints consent URL.
     User opens URL in a browser (same machine or SSH-forwarded), Google
     redirects the auth code back to http://127.0.0.1:<port>/ which the flow
     captures programmatically — no copy/paste. (The legacy OOB flow
     `urn:ietf:wg:oauth:2.0:oob` is deprecated by Google as of 2022 and
     rejected for newly-created OAuth clients.)
  3. Exchanges the code for an access+refresh token pair.
  4. Writes refresh token + GCP project id into `/home/aiagent/.config/youtube-api/.env` (chmod 600).

Subsequent calls:
  - Refuse to overwrite an existing `.env` unless `--rotate` is passed.
  - With `--rotate`, back up the old `.env` to `.env.bak.<timestamp>` before
    writing the new file atomically via `os.replace()`.

Usage:
  bootstrap_youtube_oauth.py [--rotate] [--client-secret PATH] [--env PATH] [--port 0]

Security:
  - Never logs client_secret.json contents or refresh token values.
  - Enforces 0600 perms on both files.
  - First-write uses O_EXCL to close any TOCTOU between existence check and open.
  - Rotate path writes to a temporary file and atomically `os.replace()`s after backup.
  - Owner check: refuses to run if client_secret.json owner != current user.

SSH-tunnel hint:
  If running on a headless home server, start this script there, note the
  port it prints (e.g. 45723), and on your laptop run:
      ssh -L 45723:127.0.0.1:45723 user@home-server
  Then open the printed URL in your laptop's browser — the redirect hits
  your laptop's forwarded port which tunnels back to the server's flow.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
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


def _write_env_atomic(env_path: Path, refresh_token: str, project_id: str, *, rotate: bool) -> None:
    """Write .env atomically.

    First-create path: `O_WRONLY|O_CREAT|O_EXCL|O_TRUNC` (Codex MED finding —
    close the TOCTOU between main()'s exists-check and open).

    Rotate path: write to temp file with O_EXCL, then `os.replace()` onto the
    target. Atomic on the same filesystem.
    """
    env_path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "# YouTube API OAuth — written by scripts/bootstrap_youtube_oauth.py\n"
        f"YOUTUBE_REFRESH_TOKEN={refresh_token}\n"
        f"GCP_PROJECT={project_id}\n"
        f"YOUTUBE_SCOPES={','.join(SCOPES)}\n"
    ).encode("utf-8")

    if rotate:
        tmp_path = env_path.with_suffix(env_path.suffix + ".tmp")
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_TRUNC, 0o600)
        try:
            os.write(fd, content)
        finally:
            os.close(fd)
        os.chmod(tmp_path, 0o600)  # defensive in case umask widened
        os.replace(tmp_path, env_path)
    else:
        fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_TRUNC, 0o600)
        try:
            os.write(fd, content)
        finally:
            os.close(fd)
        os.chmod(env_path, 0o600)


def _run_oauth_flow(client_secret_path: Path, port: int = 0) -> str:
    """Run Google's supported installed-app flow with a local loopback server.

    Returns the refresh token. Raises SystemExit on missing refresh_token
    (happens if a previous grant already exists — user must revoke at
    https://myaccount.google.com/permissions first).
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), scopes=SCOPES)
    # run_local_server handles authorization_url + open_browser + waiting for
    # the loopback callback. We set open_browser=False so the URL is just
    # printed — works for both local runs and SSH-tunnel scenarios.
    print()
    print("=" * 72)
    print("Starting local OAuth callback server. Google will print a URL below.")
    print("Open it in any browser (laptop is fine — Google redirects to")
    print("127.0.0.1:<port>, SSH-tunnel that port from your laptop back to")
    print("this machine if running headless).")
    print("=" * 72)
    print()
    creds = flow.run_local_server(
        port=port,
        open_browser=False,
        authorization_prompt_message="  Authorize here: {url}",
        success_message="OAuth callback received — you may close this tab.",
        timeout_seconds=300,
        access_type="offline",
        prompt="consent",  # force refresh_token issuance even if granted before
        include_granted_scopes="true",
    )
    if creds.refresh_token is None:
        raise SystemExit(
            "no refresh_token returned — Google only emits one on first consent per grant. "
            "Revoke the existing grant at https://myaccount.google.com/permissions "
            "(under your OAuth client name) and re-run."
        )
    return creds.refresh_token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rotate", action="store_true", help="Replace existing .env (backs up old).")
    parser.add_argument("--client-secret", type=Path, default=DEFAULT_CLIENT_SECRET)
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument(
        "--port", type=int, default=0,
        help="Local loopback port for OAuth callback (0 = OS-assigned free port, default).",
    )
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
    refresh_token = _run_oauth_flow(cs_path, port=args.port)
    _write_env_atomic(env_path, refresh_token, project_id, rotate=args.rotate)
    print(f"[bootstrap] wrote refresh token → {env_path} (0600)", file=sys.stderr)
    print(f"[bootstrap] GCP project: {project_id}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
