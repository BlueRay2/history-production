# Codex Round 2 Review — task-02-youtube-api-client

**Reviewer:** codex
**Date:** 2026-04-21T23:32:37+03:00
**Commit reviewed:** 290965a
**Verdict:** request changes
**Extraction:** Written inline by Codex because sandbox write to target path failed.

## Findings

- **[medium]** (`scripts/bootstrap_youtube_oauth.py:94`) `_write_env_atomic()` still leaves the rotate path in a bad state if anything fails after `.env.tmp` is created. The temp filename is fixed (`.env.tmp`), but there is no cleanup on `os.write`, `os.chmod`, or `os.replace` failure. A killed or failing `--rotate` run can therefore strand a partially-written temp file containing the new refresh token and make every later rotate attempt fail immediately with `FileExistsError`, because the next `O_EXCL` open sees the stale `.env.tmp`. Suggested fix: wrap the rotate branch in cleanup that unlinks the temp file on failure, or switch to a unique temp name plus best-effort cleanup before returning the error.

## Observations (non-blocking)

- The OAuth bootstrap finding is otherwise resolved. Google's installed-app guidance recommends the local loopback/server flow for desktop apps and deprecates manual OOB copy/paste; `InstalledAppFlow.run_local_server(..., open_browser=False)` is the supported replacement here, and `run_local_server(**kwargs)` does forward `access_type` / `prompt` through to `authorization_url()`. Sources: https://developers.google.com/identity/protocols/oauth2/native-app , https://googleapis.dev/python/google-auth-oauthlib/latest/_modules/google_auth_oauthlib/flow.html
- The code correctly refuses a missing refresh token after the auth exchange by raising `SystemExit` when `creds.refresh_token is None`.
- The new `tests/test_youtube_client.py` suite now exercises the actual `YouTubeClient` methods, retry classification, and kwargs wiring instead of only YAML-loading the cassettes. It still does not cover google-auth token refresh end-to-end, but for this module's thin wrapper the round-1 test gap is substantially reduced.
- `ingest/env_loader.py` now covers the common quoted-value and inline-comment cases that were missing in round 1, while explicitly documenting that multi-line values and escape handling remain out of scope.
- `_validate_metrics()` is applied to both analytics entry points, and the `[A-Za-z0-9_,]+` guard does not appear to reject legitimate YouTube Analytics metric identifiers.
- The unsupported Authorization-redaction claim was removed from the `YouTubeClient` docstring.
- I did not re-run `pytest` in this sandbox; the local shell wrapper was failing, so this is a static review of commit `290965a` plus current Google OAuth/library docs.

## Summary

Request changes. The round-1 OAuth, env parsing, metrics validation, docstring cleanup, and main client-method test gaps are substantively resolved, but the rotate-path temp-file cleanup is still missing.
