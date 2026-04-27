# Round 2 Review — task-04-nightly-ingest-job (Gemini DEGRADED)

**Reviewer:** Gemini 3.1-pro (delegation attempted; auth-degraded)
**Date:** 2026-04-27T11:13+03:00
**Commit reviewed:** 698d8c1
**Verdict:** REVIEW_BLOCKED (gemini-degraded, retroactive audit queued)

## Provenance — gemini auth chain that day

Three review attempts, three failures with the same classifier signature:

1. `gemini-agent.sh review` (default agent_ro mode) →
   `rc=41, classifier=auth_interactive`,
   log line: `[gemini-agent] auth_interactive detected (rc=41) — sleeping 10s and retrying once...` →
   `[gemini-agent] auth-transient retry still failing (class=auth_interactive, rc=41)`
2. `gemini-agent.sh --task-class prompt_only review` (no MCPs/extensions) →
   same `rc=41` + `auth_interactive` classifier
3. Direct `gemini -p "$LARGE_PROMPT"` (bypassing wrapper) →
   `rc=41`, log line:
   `Error authenticating: FatalAuthenticationError: Manual authorization is required but the current session is non-interactive. Please run the Gemini CLI in an interactive terminal to log in, provide a GEMINI_API_KEY, or ensure Application Default Credentials are configured.`

Cross-validation: a same-session probe `gemini -p "ping. one word: pong"`
returned `pong` immediately AFTER each failure above. So OAuth refresh is
intermittent — small prompts succeed (likely served by flash-fallback
without re-auth), large prompts trigger the re-auth path and hit the
non-interactive guard.

This matches the failure mode signature memorized as anti-pattern in
`memory/feedback_delegation_outage_memory.md` — citing `rc+log
line+classifier signature` directly, NOT wrapper alert text. Only
interactive `gemini auth login` (terminal session) can refresh the
refresh-token; cron-safe `gemini-auth-healthcheck.sh` will detect and alert
when it hits this state.

## Round-1 finding fixes — coordinator-side cross-check

Since Gemini r2 cannot validate, coordinator (Claude) cross-checks each
R1 finding against the diff in commit 698d8c1 and the new tests:

- **R1-HIGH (PK suffix invalid ISO 8601):** resolved.
  `_now_iso_micro()[:-1] + f"{col_idx:03d}Z"` inserts the suffix BEFORE
  the trailing Z (`...123456003Z`). Both occurrences in
  `_persist_analytics_result` and `_parse_and_upsert_reporting_csv`
  patched. Test `test_pk_collision_suffix_is_iso8601_valid` pins
  julianday() validity by counting rows where `julianday(observed_on) IS
  NOT NULL` after a forced collision — passes.
- **R1-HIGH (schema drift no-op for added types):** resolved.
  `_sync_schema_drift` now calls `client.ensure_jobs(added, conn=conn)`
  for newly detected types (with QuotaExhaustedError propagation +
  graceful soft-fail on other errors so drift entries survive for
  next-run retry). Test
  `test_schema_drift_auto_creates_jobs_for_added_types` pins ensure_jobs
  invocation with the expected ID list.
- **R1-MED (no Telegram alert):** resolved. New `_send_telegram_alert`
  helper parses BOT_TOKEN from `/home/aiagent/.claude/channels/telegram/.env`
  (with quote/comment/BOM hardening from task-08 runbook), invokes
  Bot API directly (no MCP — survives Claude downtime per CLAUDE.md
  pattern). Fired on: preflight quota cap (Phase 1), every `_abort` path
  (quota/auth/api/db), and non-ok orchestrator close (Phase 7), with
  emoji severity from STATUS_EMOJI table matching spec section "Status
  semantics". Test `test_telegram_alert_invoked_on_partial_status` pins
  invocation on partial close.
- **R1-MED (no pre-flight quota check):** resolved. New Phase-1 check
  reads `_today_total_units` and bails with `orchestrator_run_id="preflight"
  status="quota_exhausted"` BEFORE `_open_run`, avoiding a dangling
  ingestion_runs row. Test `test_preflight_quota_skips_orchestrator_open`
  pins the no-row outcome.
- **R1-MED (per-row autocommit slowdown):** resolved. New
  `_batched_writes(conn)` context manager wraps each persist call site
  (analytics, retention, video registry, reporting CSV) in
  BEGIN IMMEDIATE / COMMIT — collapses thousands of fsyncs into one
  transaction per sub-run. No nesting with quota_check_and_reserve
  (which commits before returning, so the next BEGIN is fresh).

## Coordinator new-finding scan (best-effort, not a substitute for Gemini r2)

None. Diff is surgical (additive: helpers + wrap calls + new tests),
no behavioural changes to existing code paths. Full suite 241 passing
(was 237 before fixes, +4 new tests).

## Audit queue

Added to `kpi/docs/tz/kpi/codex-retroactive-queue.md` (created if absent
this round). When Gemini auth is restored interactively (Ярослав runs
`gemini auth login` in a terminal), retroactive Gemini r2 review of
commit 698d8c1 should run via `gemini -p "$(cat r2-prompt.txt)"`.
