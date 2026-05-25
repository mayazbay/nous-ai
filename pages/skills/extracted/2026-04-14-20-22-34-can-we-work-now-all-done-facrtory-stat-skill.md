---
type: skill
title: Factory Status Audit
version: 1.0.0
extracted_from: 2026-04-14-20-22-34-can-we-work-now-all-done-facrtory-stat.md
extracted_by: vps-skill-extractor (2026-04-14)
---

## When to Use
When a user asks "is everything working?", "factory status", "can we work now?", or any system-health check. Produces an honest, structured audit instead of a vague "yes."

## Framework

1. **Check actual state** — Don't confirm assumptions. Query live systems, verify claims against reality.

2. **Organize into three tiers:**
   - **✅ WORKING** — Systems live and verified. Group by function (core chain, memory loop, learning loop, session continuity). Include concrete details (costs, sync intervals, counts).
   - **⚠️ NOT WORKING YET** — Deployed but untested, or partially functional. Flag what needs live verification.
   - **🔴 BLOCKED** — Not technical blockers. Table format: `| Blocker | Owner | Unblocks |`. Name humans responsible.

3. **Answer the real question** — End with a direct yes/no/almost to the user's actual question, with the one critical caveat if any.

4. **No bullshit rule** — If something is untested, say so. If a blocker is a person, name them. Honesty > reassurance.
