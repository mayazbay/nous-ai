---
type: reference
id: RCA-INDEX
title: "Root Cause Analysis Collection"
tags: [reference, rca, root-cause, analysis]
date: 2026-04-06
last_updated: 2026-04-06
source_count: 1
status: reviewed
---
# Root Cause Analysis - Permanent Lessons

## RCA-001: VPN Dies Silently
**Root Cause:** xl2tpd L2TP tunnel drops without alert. ppp0 goes down. ISAPI listener stays active but receives zero events.
**Fix:** Add VPN ping check to watchdog. If ping 10.235.0.36 fails -> restart xl2tpd + routes + Telegram alert. Monitor event flow rate.
**LESSON:** NEVER trust service status alone. Verify ACTUAL DATA is flowing.

---

## RCA-002: GLM-5 Death Loop
**Root Cause:** API balance exhausted. 429 error throws exception. retry_count never increments. Infinite loop burns tokens.
**Fix:** Health monitor preflight. Circuit breaker (3 errors = skip). Always increment retry in except block.
**LESSON:** NEVER assume API balance is infinite. ALWAYS handle 429s. ALWAYS increment retries in finally/except.

---

## RCA-003: Wrong Test Paths Block All Merges
**Root Cause:** Tests assert files at wrong paths. Every merge rolls back. Factory writes tests based on assumptions not reality.
**Fix:** Coder MUST read actual file before writing test. Verify paths with file_tree.
**LESSON:** Tests with wrong assertions are WORSE than no tests.

---

## RCA-004: ISAPI Timeout Misconception
**Root Cause:** Hikvision kills persistent STREAMS over VPN after 5min. VPN itself is fine. Push model works.
**Fix:** Build edge-push listener (camera POSTs, we return 200 OK). VPN stays as transport.
**LESSON:** Do NOT conflate transport (VPN) with application (ISAPI stream). Push works over VPN.

---


## RCA-005: Factory Marks Tasks Done But Code Gets Reverted
**Root Cause:** CEO marks tasks done after Coder writes code. But post-merge tests often fail and auto-rollback reverts the commit. The task stays marked done even though net code change is ZERO. 9 reverts in 24 hours. Same task retried 7 times with same approach.
**Why Not Caught:** No check that merged code actually STAYS merged. CEO only sees Coder output, not git revert history.
**Permanent Fix:** 1) Task is NOT done until code survives post-merge without revert. 2) If same task fails 3 times, CEO must CHANGE APPROACH, not repeat. 3) Track revert count per task.
**LESSON:** Done means DEPLOYED AND WORKING IN PRODUCTION. Not just code written.

## RCA-006: No Browser-Level Testing
**Root Cause:** Factory validates with pytest (Python tests only). React/TSX crashes happen in the BROWSER — undefined properties, API format mismatches, rendering errors. Pytest cannot catch these.
**Why Not Caught:** No Playwright/Puppeteer/browser testing in the pipeline. Validator judges Python test results, not actual page rendering.
**Permanent Fix:** Add browser smoke test: after deploy, curl each page route via Vercel, check for JS errors in server-rendered output. Or add Playwright headless checks.
**LESSON:** Frontend code MUST be tested in a browser context, not just with Python unit tests.

## RCA-007: Validator Auto-Pass Made It Useless (MOST CRITICAL)
**Root Cause:** Code in graph.py ALWAYS overrode Validator's FAIL judgment when pytest had 0 errors. Even when Validator said "this code will crash," the system auto-passed it because pytest (Python tests) can't detect React/browser crashes.
**Impact:** 9 reverts in 24 hours. Validator was a decoration — its opinion never mattered.
**Fix:** Validator judgment is now RESPECTED for functional concerns. Auto-pass ONLY for pure style issues when ALL tests (including failures) are zero.
**LESSON:** If you build a quality gate then override it every time, you have no quality gate. TRUST YOUR VALIDATOR.

## RCA-008: CEO Marked Reverted Tasks as Done
**Root Cause:** CEO saw validation=PASSED, approval=APPROVED and concluded task was done. It never checked if post-merge rollback happened. Git reverted the code but CEO already updated SQLite to status=done.
**Impact:** 91 tasks marked done, but many produced ZERO net code changes.
**Fix:** CEO now checks for ROLLBACK status. Task is NOT done if code was reverted.
**LESSON:** Done = code is ON main AND deployed AND working. Not just "code was written."

## RCA-009: No Frontend Testing = Blind Factory
**Root Cause:** Only pytest (Python) runs in the pipeline. React/TSX crashes happen in the browser. The factory has zero visibility into whether pages actually render.
**Impact:** Dashboard attempted 7 times, MapView crashed, Cameras empty — pytest said 222 passed for all of them.
**Fix:** Need Playwright or at minimum curl-based smoke tests for each frontend route after deploy.
**LESSON:** Test the ACTUAL PRODUCT, not just the backend code.

## Meta-Lesson: Why Agents Weren't Evolving
The agents read error_lessons from Mem0 but the lessons were about CODE bugs, not PROCESS bugs. Nobody stored lessons about the pipeline itself being broken. The factory was optimizing code quality while the process silently sabotaged every merge.
Fix: Store PROCESS lessons alongside code lessons. CEO must read both.

## RCA-010: Factory Rewrote App.tsx — Destroyed Entire Application (WORST FAILURE)
**Root Cause:** The Coder agent completely replaced the 186-line App.tsx (containing Sidebar, Header, 8 page routes, ErrorBoundary, auth, everything) with an 83-line react-router skeleton that only had CamerasPage. Every other page vanished. The factory committed this, it passed tests (pytest doesn't test React rendering), Validator auto-passed it, and it was deployed.
**Impact:** ALL pages except Dashboard broken. 5 of 8 pages stopped rendering entirely. This was blamed on 'data format issues' when the real cause was the entire routing/layout being deleted.
**Why Not Caught:** No test checks that App.tsx still contains all page imports. No test verifies page count. Validator was auto-overridden. No human reviewed the diff.
**Fix Applied:** Restored App.tsx from git history (commit 5023a16).
**LESSON:** CRITICAL FILES must be PROTECTED. App.tsx, index.html, vercel.json, and core layout files should NEVER be fully rewritten by agents. Only targeted edits. Add a pre-commit check: if a critical file shrinks by more than 50%, REJECT the commit.

## RCA-011: Coder Keeps Rewriting App.tsx When Fixing Individual Components
**Root Cause:** When assigned "Fix ViolationsPage", the Coder generates a new App.tsx alongside the component fix. It thinks fixing a page means rewriting the entire routing. Protected files guard caught 2 attempts (57% and 82% reduction).
**Fix Needed:** Add explicit rule to Coder prompt: "NEVER output App.tsx, index.html, or any file not listed in FILES TO MODIFY. Only edit the specific component assigned."
**LESSON:** The Coder needs strict file scope constraints. Task says fix Violations.tsx = only touch Violations.tsx.

## RCA-012: CEO Marks Task Done When Build Fails
**Root Cause:** License plate task #530 — Coder wrote code, 7 tests failed, build FAILED, code NOT deployed. But CEO still marked it 'done' because approval_status was 'approved' (max retries reached → auto-approve). CEO doesn't check if build actually succeeded.
**Fix Needed:** CEO must check deploy status. If deploy FAILED or build FAILED, task is NOT done regardless of approval_status.
**LESSON:** done = code ON main + build passes + deploy succeeds + smoke test passes. Not just 'approved'.

## RCA-013: Max Retries Auto-Approves Failed Code
**Root Cause:** When retry_count >= 3, route_after_validation sends to approval node regardless of validation result. Validator says FAIL 3 times with real functional issues, but the system says 'ship it anyway.' This is how 7-test-failure code gets deployed.
**Fix:** Max retries now marks task as FAILED, not approved. The approval node sees the failure flag and does NOT merge.
**LESSON:** Failed validation × 3 = task is STUCK and needs a different approach. It does NOT mean the code is good enough to ship.

## RCA-014: Coder Retries Same Failing Approach
**Root Cause:** Retry loop was Validator→Debugger→Coder→repeat. Debugger analyzes the error but doesn't change the fundamental approach. Coder gets same feedback 3 times, writes same broken code. Nobody calls Researcher for a new strategy. Nobody asks CEO to decompose differently.
**Fix:** New retry flow: Fail1 → Debugger → Coder (fix the specific error). Fail2 → RESEARCHER → Coder (find completely new approach). Fail3 → STOP, mark failed.
**LESSON:** If the same approach fails twice, the approach is wrong. Don't retry — research a new solution. This is how humans solve problems: try, fail, THINK DIFFERENTLY, try again.

## RCA-015: Routing Fix Crashed the Factory (KeyError: researcher)
**Root Cause:** I added 'researcher' as a routing option from validator but the graph edges didn't include it. The graph.add_conditional_edges only had 'approval' and 'debugger' as valid targets. Adding 'researcher' to the route function without adding it to the edges caused KeyError crash.
**Impact:** Factory crashed, skipped validation, deployed unvalidated code. Website broke AGAIN. 12 test failures introduced.
**Fix:** Reverted to simple working routing. No fancy redirects.
**LESSON:** NEVER change graph routing without testing the ENTIRE flow first. Every route target must exist in the conditional_edges mapping. Test graph changes in isolation before deploying to production.

## RCA-016: Same Website Problem Keeps Coming Back
**Root Cause:** Every time the factory runs, it can modify frontend files and deploy. The original design gets overwritten by factory commits. No mechanism to lock the design permanently.
**LESSON:** The frontend design must be versioned and LOCKED. Factory can only ADD functionality (data wiring) to existing components, never rewrite them. This is iOS-style updates — features on top, design unchanged.

## See also
- [[cameras|Camera Network]]
