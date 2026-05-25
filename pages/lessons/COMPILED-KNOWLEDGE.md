---
type: compiled
id: COMPILED-001
title: "Compiled Knowledge — What Every Agent Must Know"
tags: [compiled, critical, must-read, summary]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 0
status: reviewed
---
# Compiled Knowledge — The 10 Things That Matter Most

This is compiled from 34 lessons, 16 RCAs, and 7 audits. Read THIS first.
Individual files have full details if you need them.

## 1. DONE means VISIBLE IN BROWSER, not "code merged"
97 tasks marked done were all reverted. Only verify by curl or Playwright. (LESSON-006, LESSON-019)

## 2. Same SWR key with different fetchers = BLACK SCREEN CRASH
Header and Dashboard both used /api/proxy/cameras but different transforms. Always use unique SWR keys. (LESSON-016)

## 3. Smoke test was the root cause of ALL 97 reverts
SPA HTML shell = 446 bytes. Old threshold was 500. Every deploy "failed" smoke. Fixed to check API health + 200 bytes. (LESSON-019)

## 4. Validator must see FULL FILE, not just diff
Coder adds API call but leaves Math.random. Diff looks good. Full file has fake data. Validator approved. Now has 13 banned patterns in Python code. (LESSON-022, LESSON-025)

## 5. Never killall. Always kill by specific PID.
killall python3 killed production ISAPI listener + police dashboard + portal. (LESSON from mistakes #17)

## 6. excess = speed - limit. NO additional subtraction.
Backend had double-subtraction bug. 76 in 60 = 16 excess = fine. Not 6. (LAW-002)

## 7. ЛУ cameras online but 0 events — not configured to push
145 LU cameras answer pings but dont send ISAPI notifications. Need subscription setup. (LESSON-021)

## 8. Two wiki directories diverged silently
wiki/ and obsidian-wiki/ had different laws. Agents read one, validation checked other. Now synced. (AUDIT-006)

## 9. CEO at 1% brain capacity burns $40 on busywork
CEO had 4-line prompt and 10K tokens context. Now has strategic prompt and 91K tokens with full source code. (UPGRADE-001)

## 10. Writing a law is 10%. Enforcing it in code is 90%.
14 laws documented, only 7 had Python gates. Now 14/14 have enforcement. Prompts get ignored. Code gates cannot be hallucinated away. (ROOT-CAUSE-SESSION)

## See also
- [[AUDIT-006-flow-audit-traced-factory-execution-path-start-to|AUDIT-006]]
- [[cameras|Camera Network]]
- [[LAW-002-autofine|LAW-002]]
- [[LESSON-006-done-means-visible-in-browser|LESSON-006]]
- [[LESSON-016-swr-cache-collision-critical|LESSON-016]]
- [[LESSON-019-smoke-test-caused-all-97-reverts-root-cause-found|LESSON-019]]
- [[LESSON-021-145-0-root-cause|LESSON-021]]
- [[LESSON-022-validator-rubber-stamps-0-effective-quality|LESSON-022]]
- [[LESSON-025-validator-root-cause-my-fault-not-gemini|LESSON-025]]
