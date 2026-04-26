# Codex Round 1 Review — task-02-youtube-api-client

**Reviewer:** codex
**Date:** 2026-04-21T23:14:48+03:00
**Commit reviewed:** 8dc2bf5
**Verdict:** request changes
**Extraction:** Claude coordinator extracted verbatim from Codex agent_message in `reviews/task-02-codex-r1-raw.log` after sandbox write to target path failed.

## Findings

- **[high]** (scripts/bootstrap_youtube_oauth.py:93) The bootstrap hardcodes the deprecated out-of-band redirect (`urn:ietf:wg:oauth:2.0:oob`) and then asks the user to paste an auth code. Google's current desktop-app docs say manual copy/paste/OOB is no longer supported and the installed-app flow should use a local redirect URI / loopback listener instead. This makes the first-run install flow fail or get blocked for a production OAuth client even though `access_type=offline` and `prompt=consent` are set correctly. Suggested fix: switch to the supported desktop flow (`InstalledAppFlow.run_local_server(..., open_browser=False)` or equivalent loopback handler) and keep `access_type="offline"` plus `prompt="consent"`. Sources: https://developers.google.com/identity/protocols/oauth2/native-app , https://developers.google.com/identity/protocols/oauth2/resources/oob-migration

- **[medium]** (scripts/bootstrap_youtube_oauth.py:71) `_write_env()` claims `O_EXCL` prevents a TOCTOU overwrite, but the actual open flags are only `O_WRONLY | O_CREAT | O_TRUNC`. That leaves the existence check in `main()` racable and contradicts both the code comment and the commit message. Suggested fix: on first create, open with `O_EXCL`; on `--rotate`, write a new 0600 temp file and `os.replace()` it after the backup succeeds.

- **[medium]** (tests/test_youtube_client.py:99) The task's critical path is not actually tested. The only cassette test just YAML-loads the fixture files; it never instantiates `YouTubeClient`, never replays a real `googleapiclient` request, and never covers the required 401-refresh smoke path from the task spec. `pyproject.toml:16` also omits `vcrpy`, so the advertised cassette-playback mode cannot run. Suggested fix: add real `vcrpy`-backed tests for `get_channel_overview()` / analytics plus the missing auth-refresh case, and declare `vcrpy` in dev dependencies.

## Observations (non-blocking)

- `ingest/env_loader.py` intentionally supports only whole-line comments plus raw `KEY=VALUE` parsing. It preserves `KEY=value with spaces`, but it does not strip surrounding quotes or inline `#` comments. That is compatible with the bootstrap script's current output.
- `ingest/youtube_client.py` does tolerate the sparse-retention case: `get_retention()` returns the raw response untouched, so an empty `rows` list does not error in this layer.
- I did not re-run `pytest` in this sandbox; the shell wrapper was failing, so this is a static review of the committed files plus current Google OAuth docs.

## Summary

Request changes. The retry classification and empty-retention handling look fine, but the OAuth bootstrap uses an unsupported desktop flow and the cassette/auth-refresh coverage promised by the task is not actually present.
