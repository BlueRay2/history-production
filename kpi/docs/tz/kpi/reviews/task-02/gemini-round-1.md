# Round 1 Review — task-02
**Reviewer:** Gemini
**Verdict:** ACCEPTED
## Summary
The `decommission_dashboard.sh` script correctly and safely implements all requirements for decommissioning the legacy KPI dashboard as specified in `task-02-decommission-old-dashboard.md`. The implementation includes robust pre-flight checks, a secure backup-and-retire procedure for the legacy database, and mechanisms for idempotent execution. The concerns raised in the prior Codex r1 review appear to be fully addressed in the latest commit (`c42bf54`).

## Findings
None. The script is well-written, prioritizes safety, and aligns with the task specification.

## Evidence
- **Backup Integrity (SHA-256):** The script computes and verifies SHA-256 hashes of the source database and the backup, exiting with a non-zero status code on mismatch. This gate (`decommission_dashboard.sh:68-71`) is critical and correctly implemented.
- **Pre-flight Gates:** The script validates four key conditions before executing destructive operations:
    1. The new monitoring service (`claude-kpi-monitoring.service`) is active, preventing a service outage (`decommission_dashboard.sh:42-44`).
    2. The new KPI vault has a successful run flag (`kpi-vault-first-success.flag`) whose age meets the required verification window (`decommission_dashboard.sh:48-65`).
    3. The new KPI vault has a successful heartbeat flag (`kpi-vault-first-heartbeat.flag`) whose age also meets the requirement (`decommission_dashboard.sh:48-65`).
    4. The backup's SHA256 hash matches the source DB's hash, preventing data loss before the original is moved (`decommission_dashboard.sh:70-71`).
- **Safe Retirement (`mv-not-rm`):** The script safely retires the legacy database by renaming it to a `.retired-YYYY-MM-DD` path using `mv`, not `rm`, preserving the file for a 7-day rollback window (`decommission_dashboard.sh:162-165`).
- **Rollback Plan:** A clear and viable rollback plan is documented in `kpi/docs/tz/kpi/task-02-decommission-old-dashboard.md`, covering restoration from both the retired file and the deep-memory archive.
- **Deep-Memory Archive:** The backup is committed to the separate `deep-memory` git repository, and the commit message correctly includes the file's SHA-256 hash for auditing (`decommission_dashboard.sh:74-78`).
- **Harmless Deprecation:** Deprecation headers in `kpi/app/main.py` and `kpi/app/services/weekly_view.py` are implemented as comments, leaving the code fully functional to facilitate a potential rollback without introducing runtime side effects.
- **Durable Cron Deletion:** The issue of durable cron entries (noted in Codex r1) is now addressed. The script detects lingering entries and ensures they will be reconciled by the `SessionStart` drift hook, which is an appropriate solution given the tool's operational constraints (`decommission_dashboard.sh:139-155`).

## Commands
```bash
# File content review only. No commands executed.
read_file /home/aiagent/assistant/git/history-production/kpi/scripts/decommission_dashboard.sh
read_file /home/aiagent/assistant/git/history-production/kpi/app/main.py
read_file /home/aiagent/assistant/git/history-production/kpi/app/services/weekly_view.py
read_file /home/aiagent/assistant/git/history-production/kpi/CHANGELOG.md
read_file /home/aiagent/assistant/git/history-production/kpi/tests/test_decommission_script.py
read_file /home/aiagent/assistant/git/history-production/kpi/docs/tz/kpi/task-02-decommission-old-dashboard.md
read_file /home/aiagent/assistant/git/history-production/kpi/docs/tz/kpi/reviews/task-02/codex-round-1.md
```

## Risks
The inherent risks of this destructive operation are well-mitigated.
- **Data Loss:** Mitigated by the verified SHA-256 backup to a separate `deep-memory` repository before the original file is touched.
- **Service Outage:** Mitigated by the pre-flight check ensuring the replacement monitoring service is active.
- **Irreversibility:** Mitigated by using `mv` instead of `rm` and documenting a clear 7-day rollback plan.

## Recommended Handoff
Handoff to Claude for merge.
