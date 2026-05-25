---
type: skill
title: Cross-Session Handoff System Design
version: 1.0.0
extracted_from: 2026-04-14-16-38-57-every-single-time-i-m-fixing-up-and-writ.md
extracted_by: vps-skill-extractor (2026-04-14)
---

## When to Use
When a user needs to preserve context and seamlessly continue work across multiple AI sessions, tools, or instances—especially when one session degrades and must be replaced mid-task.

## Framework

1. **Identify the bridge medium** — Find existing shared storage (wiki, git repo, shared drive) that both source and destination sessions can read/write. Avoid new connections; reuse what's already syncing.

2. **Separate automatable from human-judgment signals** — Distinguish what the system can detect (time elapsed, token count) from what only the user can perceive (quality degradation, hallucination). The degradation trigger must come from the human; design for that reality.

3. **Implement dual-layer checkpoints**:
   - **Manual trigger** (e.g., `/handoff` command): User-initiated when they notice slippage. Fast, targeted, captures the "why" of the transition.
   - **Automatic cron** (periodic interval): Insurance for when the user doesn't catch degradation in time. Lightweight, timestamped, always running.

4. **Standardize the handoff document** — Each checkpoint must include: what was done, what's next, current state/blockers, and any decisions made. Name with pattern like `HANDOFF-{type}-{timestamp}.md` for discoverability.

5. **Map the latency chain** — Document the full flow from trigger to new-session-readiness, including sync delays (e.g., "wiki syncs in 60s"). Set expectations accordingly.

6. **Validate the new session picks it up** — Ensure the receiving session's startup routine automatically reads the latest handoff from the bridge medium. Zero copy-paste is the goal.
