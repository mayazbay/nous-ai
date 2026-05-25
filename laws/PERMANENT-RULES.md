---
type: rules
id: RULES
title: "18 Permanent Rules"
status: permanent
enforcement: mixed
tags: [rules, permanent, all-agents, claude-code]
related: [LAW-001, LAW-003, LAW-008]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
---
# PERMANENT RULES — NEVER BREAK THESE
Applies to Claude Code AND all factory agents.
Updated: 2026-04-06

## RULE 1: CEO = Claude Opus 4.6. ALWAYS.
Never downgrade. CEO needs 100% brain capacity.

## RULE 2: Quality over everything
1 task shipped > 100 tasks reverted.

## RULE 3: Never say "done" unless VERIFIED IN PRODUCTION
See LAW-003 for definition of "done."

## RULE 4: Same mistake = never twice
Every failure → lesson in wiki. Validator enforces.

## RULE 5: Frontend code is in satory-frontend/, NOT src/
src/ was deleted April 6.

## RULE 6: API is /api/ not /api/v1/

## RULE 7: VKO coordinates (49.9N, 82.6E), not Almaty

## RULE 8: Tests BEFORE deploy
Merge → pytest → IF PASS → build → deploy → smoke.

## RULE 9: Agents must read wiki BEFORE working
Every agent reads wiki/laws/ at cycle start. No exceptions.

## RULE 10: Own mistakes, dont audit forever
After 2-3 audit rounds, STOP and FIX.

## RULE 11: /root/ (factory) vs /opt/ (production) are DIFFERENT

## RULE 12: Never send to real Telegram without asking Madi

## RULE 13: Clean wiki weekly — remove stale data

## RULE 14: Hard-coded safety > prompt instructions
Code gates cannot be hallucinated away. Prompts can.

## RULE 15: ONE task at a time. Verify. Commit. Then next.
Added April 6. Violated pattern D: parallel without verification.

## RULE 16: NEVER killall. Kill by specific PID only.
killall python3 killed production services.

## RULE 17: Check RAM (free -m) before heavy operations.
npm build OOM-killed the server.

## RULE 18: Git commit IMMEDIATELY after every code change.
Working copy is ephemeral. Bug returned 4x because of this.

## See also
- [[LAW-001-evolution|LAW-001]]
- [[LAW-003-continuous-audit|LAW-003]]
- [[LAW-008-anti-hallucination|LAW-008]]
