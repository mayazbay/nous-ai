---
type: skill
title: Automated Session Handoff Design
version: 1.0.0
extracted_from: 2026-04-14-16-36-28-every-single-time-i-m-fixing-up-and-writ.md
extracted_by: vps-skill-extractor (2026-04-14)
---

## When to Use
When a user wants to automate session continuity/handoffs between agent instances — eliminating manual copy-paste of context into new sessions.

## Framework
1. **Identify the manual loop**: Notice → Trigger → Write handoff → Copy to new session. Automate the trigger and write steps; eliminate copy via shared state.
2. **Choose trigger mechanism(s)**:
   - **Time-based (cron)**: Simple, reliable. Spawns isolated agent on interval to checkpoint state. Good baseline.
   - **Heartbeat-based**: Leverages existing polling. Detects degradation mid-session. Smarter but depends on heartbeat infrastructure.
   - **Context threshold**: Most precise. Triggers handoff at ~70-80% context window usage, before compression or quality loss. Requires token tracking.
3. **Combine for robustness**: Use cron as the safety net + context threshold as the precision trigger. Cron catches what threshold misses; threshold prevents premature or late handoffs.
4. **Eliminate copy-paste via shared wiki**: Handoff writes to wiki on VPS → wiki syncs to local machines → next session reads handoff from wiki at startup. No direct machine connection needed; the wiki IS the context bridge.
5. **Handoff output**: `HANDOFF-AUTO-YYYY-MM-DD-HH-MM.md` to wiki + update MEMORY.md with critical facts. Both are auto-ingested by new sessions.
