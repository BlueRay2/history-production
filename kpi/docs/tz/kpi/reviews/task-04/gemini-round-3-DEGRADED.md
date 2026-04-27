# Round 3 Review — task-04-nightly-ingest-job (Gemini DEGRADED)

**Reviewer:** Gemini 3.1-pro (delegation attempted; capacity-degraded)
**Date:** 2026-04-27T12:03+03:00
**Commit reviewed:** 1396c58
**Verdict:** REVIEW_BLOCKED (gemini-r3-degraded, retroactive audit queued)

## Provenance — Gemini capacity-exhaustion chain

Three review attempts at the latest commit, all 429 with the same upstream
classifier signature:

1. `gemini -p "$LARGE_PROMPT"` from `cd /repo` →
   `rc=41, classifier=auth_interactive`,
   `Error authenticating: FatalAuthenticationError: Manual authorization is required but the current session is non-interactive` (the same false-auth error that originally appeared on the r2 attempt before flash-fallback flipped it to substantive review)
2. `gemini -p "$LARGE_PROMPT"` from `cd ~` (the dir that previously got past auth) →
   `Policy generation failed: _GaxiosError: No capacity available for model gemini-2.5-flash on the server`. `_ConsecaSafetyChecker.getPolicy` couldn't get a flash slot, so the request never reached pro.
3. Short-prompt direct call (one paragraph, no review request boilerplate) →
   `Attempt 1 failed with status 429 ... "message": "No capacity available for model gemini-3.1-pro-preview on the server", "reason": "MODEL_CAPACITY_EXHAUSTED"`. After backoff, attempt 2 same error. Pro itself is at capacity, not just the safety-checker fallback.

Cross-validation: Yaroslav's screenshot (msg 7927) shows quota only 3% used,
plan = Google One AI Ultra → not a per-account quota issue. This is a
**Google-side capacity exhaustion** affecting both gemini-2.5-flash (safety
policy) and gemini-3.1-pro-preview (review generation) at this hour.

This matches the discipline in
`memory/feedback_delegation_outage_memory.md` — citing rc, log line, and
classifier signature, NOT wrapper alert text. The classifier output is
`MODEL_CAPACITY_EXHAUSTED`, not auth — the earlier r2/r3 auth_interactive
error was a misleading symptom of a transient flash-side capacity glitch that
forced refreshAuth retries to an interactive flow.

## Delta from r2 commit

Gemini r2 ACCEPTED commit f3e75d7. The only delta to commit 1396c58 is one
block in `kpi/ingest/nightly.py`:

```python
# Before (channel:live except Exception):
_close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
result.failures.append(f"channel:live:{type(exc).__name__}")
result.sub_runs.append(sub)

# After:
_close_run(conn, sub, status="api_failure", error_text=str(exc)[:500])
result.sub_runs.append(sub)
raise
```

Plus the test `test_channel_failure_aborts_orchestrator_with_api_failure`
already exercises this exact propagation path (channel-level Exception →
orchestrator api_failure terminal). Codex r3 (5.5 xhigh, real review with
disk-read access) ACCEPTED this delta as resolved with no new findings.

## Audit queue

Re-queued in `kpi/docs/tz/kpi/codex-retroactive-queue.md` for Gemini r3
audit when 3.1-pro / 2.5-flash capacity returns. Estimated turnaround:
hours-to-day depending on Google-side load.
