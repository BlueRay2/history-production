# task-02 — YouTube API client (OAuth + typed wrapper)

**Status:** `pending`
**Dep:** 01
**Risk:** High

## Scope

1. GCP Console one-time setup (done by Ярослав):
   - Enable YouTube Data API v3 + YouTube Analytics API.
   - Create OAuth 2.0 Client ID (Desktop app).
   - Scopes: `youtube.readonly`, `yt-analytics.readonly`, `yt-analytics-monetary.readonly`.
   - Download `client_secret.json` → place at `/home/aiagent/.config/youtube-api/client_secret.json` (chmod 600).
2. `scripts/bootstrap_youtube_oauth.py` — interactive first-run: prints URL → user opens in browser → approves → pastes code back → tool writes refresh token to `/home/aiagent/.config/youtube-api/.env` (chmod 600) with var `YOUTUBE_REFRESH_TOKEN=...` + `GCP_PROJECT=...`. Idempotent on re-run (refuses to overwrite unless `--rotate` flag).
3. `ingest/youtube_client.py`:
   - Loads `.env` via `python-dotenv` (or std-lib parse).
   - Builds authorized client via `google-auth-oauthlib` + `googleapiclient.discovery.build`.
   - Typed wrappers: `get_videos(channel_id)`, `get_channel_analytics(start_date, end_date, metrics, dimensions=None)`, `get_video_analytics(video_id, start_date, end_date, metrics, dimensions='day')`, `get_retention(video_id, start_date, end_date)`.
   - Auto refresh-token renewal on 401; retry on 5xx with exponential backoff (existing `scripts/lib/with-retry.sh` pattern — replicate in Python as `app/lib/retry.py`).
4. Quota accounting: every call logs `quota_units` estimate to `ingestion_runs` row via task-03's ingest helper (dep forward-ref).

## Golden fixtures

Per consensus `debate/round-2.md`:
- `tests/fixtures/youtube_cassettes/channel_overview.yaml` (vcrpy-format) — replay of `get_channel_overview`.
- `tests/fixtures/youtube_cassettes/channel_analytics_7d.yaml` — replay of `get_channel_analytics` for 7-day window.
- `tests/fixtures/youtube_cassettes/video_retention_<video_id>.yaml` — one representative video's retention curve.
- Auth flow smoke-test: mock a token-refresh 401 → retry succeeds.

## Test plan

- `tests/test_youtube_client.py`: cassette playback → assertions on parsed shape.
- `tests/test_auth_refresh.py`: mock 401 → retry → success.
- `tests/test_bootstrap.py`: input mocking for OAuth code paste; idempotent re-run refused without `--rotate`.

## Files touched

- `scripts/bootstrap_youtube_oauth.py` (new)
- `ingest/__init__.py`, `ingest/youtube_client.py` (new)
- `app/lib/retry.py` (new)
- `tests/fixtures/youtube_cassettes/*.yaml` (new, recorded once by Ярослав via cassette recorder)
- `tests/test_youtube_client.py`, `tests/test_auth_refresh.py`, `tests/test_bootstrap.py` (new)
- `pyproject.toml` (add `google-api-python-client`, `google-auth-oauthlib`, `vcrpy`, `python-dotenv`)

## Review loop

- [ ] Codex round-1 → `reviews/task-02/codex-round-1.md`
- [ ] Gemini round-1 → `reviews/task-02/gemini-round-1.md` (F-01: specifically validate 2-day-lag / preliminary-flag assumption when Gemini returns)
- [ ] `ready-to-merge` | `ready-to-merge (gemini-degraded)`
- [ ] `merged`

## Security notes

- Never log `client_secret.json` contents or refresh token.
- `.env` file perms enforced by bootstrap script (chmod 600 + owner check).
- OAuth scopes explicitly `readonly` — no channel write capability.
