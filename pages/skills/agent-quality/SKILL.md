---
tier: 1
type: skill
name: agent-quality
version: 1.20.0
description: "Rules every agent (Claude Code, OpenClaw/GLM-5.1, Codex, any LLM) must follow to avoid false declarations, fake data, hallucinations, untested completions, and review-loop theater. The single most universal skill — load it before any task. v1.20.0 adds AP-38 (Phase-0 spec-vs-disk gate), AP-39 (frontmatter name-collision pre-check), AP-40 (launchd StartInterval first-fire), AP-41 (file:line citations over prose in cross-model autoplan)."
triggers:
  - about to declare a feature done
  - about to claim something is working
  - designing a solution (read wiki first)
  - about to show data in a UI
  - about to recommend a tool, plugin, or library
  - code review
  - writing a test
  - any agent task
tools: [Bash, Read, Grep, WebSearch]
mutating: false
absorbs_lessons: [LESSON-005, LESSON-006, LESSON-011, LESSON-017, LESSON-018, LESSON-022, LESSON-025, LESSON-031, LESSON-032, LESSON-036, LESSON-042, LESSON-043, LESSON-049, LESSON-060, LESSON-064, LESSON-078, LESSON-079, LESSON-082, LESSON-083, LESSON-085, LESSON-096]
lesson_notes: "LESSON-042 absorbed as AP-13 (already present); session 36 added LESSON-011/018/032/049 as AP-19..22."
absorbs_laws: [LAW-003, LAW-004, LAW-008, LAW-013]
related: [SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]
last_updated: 2026-04-30
title: "agent-quality v1.20.0"
---

# agent-quality v1.20.0

## Purpose

The rules in this skill prevent the most expensive class of errors in AGaaS: declaring done when not done, showing fake data, and recommending things that don't exist. These failures erode Madi's trust in the system and have cost dozens of burned cycles and hours of manual recovery.

**Apply this skill proactively** — before declaring done, before showing data, before recommending tools.

## Contract

**Inputs:** Any task where an agent produces output, makes a recommendation, or declares completion.

**Outputs:** An output that is honestly earned — tested end-to-end, showing only real data, recommending only verified tools.

**Invariants:**
- Never claim done without the end-to-end test passing
- Never show a number that isn't from a real API or database
- Never recommend a tool without verifying it exists in its registry
- Every critical path must log both success and failure (no silent success)
- Context (wiki/memory) is always read before designing

## Current rules (compiled truth)

### Phase 1 — Before starting any design or implementation

1. **Read wiki + memory FIRST.** Before designing anything, read the relevant wiki pages and memory context. The problem you're about to solve may already have been attempted and failed. The fix may already exist. (LESSON-005)
   ```bash
   # Search wiki before designing:
   mcp__gbrain__search "topic of the task"
   # Read the handoff:
   # pages/progress/HANDOFF-*.md
   ```

2. **Understand the full scope.** Read requirements from the task, not just the latest message. CEOs and users often drop requirements; you must track them from the original spec. (LESSON-035)

### Phase 2 — During implementation

3. **Only show real data.** If an API endpoint doesn't exist yet, show an empty state: `"Данные недоступны"`. Never hardcode fake numbers — they erode trust when operators discover them. (LESSON-017)

4. **Review the FULL file, not just the diff.** A diff showing "API call added" doesn't prove "fake data removed." The old fake data may still exist in a branch the diff doesn't cover. Read the full file. (LESSON-025)

5. **Test banned patterns against the real codebase before deploying.** A banned pattern that matches legitimate code will block real work. Grep the codebase first. (LESSON-036)

### Phase 3 — Before claiming done

6. **Done = end-to-end tested from the user's actual channel.** Not "tests passed." Not "code looks correct." Not "tested with curl." Done means:
   - Sent a real message from Telegram → received correct answer back. (LESSON-085, LESSON-006)
   - Or: opened the browser → saw working pages with real data. (LESSON-006)
   - There are NO other acceptable proofs.

7. **Verify the CORRECT system, not a proxy.** The Claude Code MCP Telegram plugin sends via a different bot than @nousAGaaSbot. When testing the factory bot, use `command_center._tg_send()` with the factory token — not the MCP plugin. (LESSON-082)

8. **Run an outcome test, not just a mechanism test.** FACTORY_OK proves the plumbing works. It does NOT prove the agent gives correct answers. Before declaring "ready," run a real question with a known expected answer:
   ```bash
   # ❌ mechanism test (not enough)
   python3 run_task.py "Reply: FACTORY_OK"
   
   # ✅ outcome test (required)
   python3 run_task.py "Who is handling НИИС application #455466 and at which platform?"
   # Expected: mention of Nazel and/or newcab.kazpatent.kz
   ```
   If the agent says "I have zero information," the system is NOT ready. (LESSON-083)

9. **Component existence ≠ chain working.** If search is wired but not tested, it's not wired. If escalation is coded but not triggered, it's not working. Test each feature via its full chain, not just one component. (LESSON-085)

### AP-1 — Don't design without reading wiki + memory first
**LESSON-005.** Building a solution that was already tried and failed because you didn't read the history. Every design session starts with: search gbrain → read handoff → read relevant skill → then design.

### AP-2 — Don't declare done without end-to-end test from Telegram
**LESSON-085, LESSON-006.** Done = user opens URL and sees working page, OR sends Telegram message and receives correct answer. "Tests passed" + "deployed" ≠ done. No exceptions.

```
❌ "The feature is deployed and tests pass"
✅ "Sent /ask from @nousAGaaSbot, received: [correct answer]"
```

### AP-3 — Don't show hardcoded or fake data
**LESSON-017.** Operators trust the UI. Fake numbers (Math.random, hardcoded arrays, static statistics) that look real are discovered eventually and destroy trust permanently. If no real data: show `"Данные недоступны"`. Never invent.

```tsx
// ❌ WRONG
const cameras = 243;  // hardcoded

// ✅ RIGHT
const cameras = data?.total ?? null;
// Render: {cameras !== null ? cameras : "Данные недоступны"}
```

### AP-4 — Don't review only the diff
**LESSON-022, LESSON-025.** A diff showing new API calls doesn't prove old fake data was removed. A code review must include reading the FULL file, not just changed lines. If you can't read the full file (too large), at least grep for banned patterns:

```bash
grep -n "Math.random\|hardcoded\|placeholder data\|fake" src/components/**.tsx
# Expect: no matches
```

### AP-5 — Don't deploy banned patterns that match legitimate code
**LESSON-036.** `placeholder` appears legitimately as an HTML attribute. `Math.random()` may be used for test seeding. Before adding a banned pattern, grep the codebase to see where it currently appears. Make patterns specific: `"placeholder data"` not `"placeholder"`.

### AP-6 — Don't recommend a tool without verifying it's in its registry
**LESSON-060.** GitHub existence ≠ registry listing. A plugin/package on GitHub may not be in the Obsidian community registry, npm, PyPI, Homebrew, etc. Before recommending `brew install X`, `pip install X`, or "install plugin X" — verify the name exists in the target registry:

```bash
# Obsidian plugins
curl -sL https://raw.githubusercontent.com/obsidianmd/obsidian-releases/HEAD/community-plugins.json | jq '.[] | select(.name | test("claude"; "i"))'

# npm
npm view <package-name> version 2>/dev/null && echo "exists" || echo "NOT FOUND"

# PyPI
pip index versions <package-name> 2>/dev/null | head -1

# Homebrew
brew info <formula> 2>/dev/null | head -1
```

If not found: say "this does not appear to be in the registry — alternatives are X." Do not direct-install unregistered packages.

### AP-7 — Don't use silent success on critical paths
**LESSON-064.** A function that sends a message, writes a file, or calls an API must log success WITH evidence (message_id, file path, response body). Silent success = no audit trail = no proof it happened. When Madi asks "did it work?" you must be able to point to a log line.

```python
# ❌ WRONG — no logging on success
try:
    telegram_api("sendMessage", {...})
except Exception as e:
    log.error(e)

# ✅ RIGHT — log success with evidence
result = telegram_api("sendMessage", {...})
if result.get("ok"):
    log.info(f"ACK sent OK: msg_id={result['result']['message_id']}")
else:
    log.warning(f"API ok:false — {result}")
```

### AP-8 — Don't solve coordination problems by adding more agents
**LESSON-079.** Four consecutive multi-agent architectures failed. EvoClaw benchmark: agents drop from >80% isolated task score to 13.37% in continuous development. The rule: ONE agent + good skills + persistent knowledge (wiki/gbrain) beats sixteen agents coordinating.

If you're tempted to "add another agent," instead:
- Add a SKILL.md to the existing agent
- Add a tool (wiki_search, bash command, MCP call)
- Add a cron that writes back to wiki

Width (more agents) does not substitute for depth (better skills + knowledge).

### AP-9 — Don't test a proxy when you need to test the real system
**LESSON-082.** Claude Code's Telegram MCP plugin sends via a different bot token than @nousAGaaSbot. Verifying MCP plugin works ≠ verifying factory bot works. Always test via the actual token and actual chat_id:

```python
# ❌ WRONG — uses MCP plugin (different bot)
# mcp__plugin_telegram_telegram__reply(...)

# ✅ RIGHT — uses factory token directly
from command_center import _tg_send
import os
_tg_send(os.environ['TELEGRAM_BOT_TOKEN'], int(os.environ['TELEGRAM_CHAT_ID']), "test")
```

### AP-10 — Don't declare "ready" based on mechanism tests alone
**LESSON-083.** Mechanism test: "FACTORY_OK returned." Outcome test: "Agent correctly answered a real question from project context." Only outcome tests prove readiness. For any system that produces answers, the test must include a known-correct expected output for real project data.

### AP-11 — Don't fabricate or assume personal relationships
**LESSON-031.** Данияр = CEO of Satory (client). Smatay = Madi's father and OWNER of Nous. Madi = CEO of Nous LTD. These are distinct people with distinct roles. Never assume family ties, never confabulate relationships. Verify from `pages/entities/` before writing any outbound communication.

### AP-12 — Don't evaluate tools by popularity, evaluate by evidence
**LESSON-078.** Star count tells you popularity. CVE count tells you risk. User reports tell you reality. EvoClaw benchmarks tell you what actually works at scale. Before adopting any tool for production: check CVE database, read GitHub Issues, search for real user production reports, check maintainer activity, look for benchmarks on your use case.

### AP-13 — Code-gate banned patterns must be specific, not broad

**LESSON-042.** LAW-008's original `setTimeout(() =>` pattern blocked legitimate React debounce code — false positives that make good code fail and erode trust in the gate entirely. The actual anti-pattern is fake async (pretending to fetch data with a timer), not async itself.

When writing or updating banned-pattern gates:
1. Write the most specific string that matches the bad pattern (`setTimeout(() => setLoading(false)` instead of `setTimeout(() =>`).
2. Test the new pattern against 5 legitimate uses before adding. If it triggers on any, narrow it further.
3. A false positive that blocks ship is worse than a missing gate — false positives destroy trust in the entire quality system.
4. Comment every banned pattern with the LESSON reference so future maintainers know the origin.

### AP-14 — Evidence chain before reporting any number or status (LAW-008)

**LAW-008.** Every claim must have evidence. Every number must have a source. Before reporting ANY number or claiming a status, answer all three:

1. **WHERE** does this number come from? (DB query result, API response body, exact file path + line)
2. **WHEN** was it last verified? (timestamp of the check — not "recently")
3. **CAN** someone else reproduce it? (the exact command or URL to run)

If you cannot answer all 3 → do NOT report the number. Say "I don't know — I haven't verified this against the source."

Evidence violations that cost real money:
- Said "955 LU cameras" — was 109 (counted Excel rows, not unique IDs)
- Said "89% complete" — was 78% (claimed before auditing)
- Said "everything works" — 6 pages had hardcoded data

### AP-15 — 100% truth: report real status, not hoped status (LAW-013)

**LAW-013.** No sugarcoating. No BS. No lies. No cheating. If it is broken, say it is broken. If it is not done, say it is not done.

Anti-patterns that are violations of this law:
- "Seems to work" — this is not done
- "I think it is fixed" — this is not done
- "Should be good now" — this is not done
- "89% complete" when audit shows 78%
- "Everything works" when 6 pages have hardcoded data
- "Bulletproof" when 97 tasks were all reverted

If something is broken and you do not know how to fix it: say "X is broken, I do not know the fix yet." That is the correct response. Silence, optimism, or false confidence wastes Madi's money and time.

### AP-16 — 5 commandments before any agent deployment (LAW-004)

**LAW-004.** In order:

1. **AUDIT BEFORE AUTOMATE** — Map the ACTUAL process, not the idealized one. Include undocumented exceptions, edge cases, real data formats. Mistake: built factory without auditing real camera workflow — 101 bugs.
2. **FIX DATA FIRST** — Single source of truth, strict schemas, validation gates before giving agent access to data. Mistake: MRGN IDs vs IP addresses with no mapping — mismatched reports across every page.
3. **THROUGHPUT MATTERS** — If an agent multiplies production volume, humans get overwhelmed with reviews. Mistake: CEO marked 97 tasks done, nobody reviewed, all reverted.
4. **OBSERVABILITY DAY ONE** — Independent verification. NEVER trust agent self-reporting. Mistake: factory said "done", site was a black screen.
5. **SCOPE AUTHORITY** — Clear guardrails, strict permissions, no working outside the defined scope. Mistake: Coder edited wrong directory, killall killed production.

### AP-17 — Default to foreground Bash in Claude Code; background only when justified

**LESSON-096.** Using `run_in_background: true` reflexively for SSH checks, greps, and quick commands fills the Tasks panel with ghost entries that never clear. Madi saw ~30 perpetual "Running" entries and lost trust in the panel.

**Rule:** Only use `run_in_background: true` when ALL three conditions hold:
1. The command genuinely takes >30 seconds (Docker pull, big SCP, model call).
2. You plan to do useful work during the wait.
3. You will actually reap the result with TaskOutput later.

If the command returns in <30 seconds or you are about to wait for it anyway, run foreground.



### AP-18 — Always run tsc --noEmit before declaring a TypeScript project done

**LESSON-043.** `npm run build` (vite/esbuild) does syntax checks only — it does NOT run TypeScript type-checking. 183 type errors leaked to production because nobody ran `tsc --noEmit`. Vite is fast precisely because it skips types.

**Rule:** Before declaring any TypeScript project "done" or "deployable," run `npx tsc --noEmit`. Use a baseline approach: record current error count, block if count increases, auto-update baseline on decrease.

```bash
# Mandatory pre-deploy type check
npx tsc --noEmit 2>&1 | tail -5
# If errors > baseline: STOP, fix new type errors before deploying
```

### AP-19 — Run code once before committing (LAW-004 enforcement, triple-violation)

**LESSON-032.** Playwright check was added to `deploy_node` but the `failed_checks` variable was referenced before being defined → `UnboundLocalError` on every deploy → ALL golden-deploy gates silently skipped. The safety gate itself was broken. This is the THIRD time an agent wrote code without running it once (LAW-004 violation).

**Rule:** Before committing ANY new branch of code, execute the function at least once in the same environment it will run in (unit test, local repl, `python -c "..."`, container exec). "It compiles" is not "it runs." `UnboundLocalError`, `NameError`, and `AttributeError` are caught on first execution, not by linters.

```bash
# ❌ BAD: wrote Playwright check, committed, deployed, discovered break on next cycle
# ✅ GOOD: python3 -c "from deploy import deploy_node; deploy_node('dummy-node')"
```

### AP-20 — After every site change, verify the site loads before the next change (LESSON-018)

**LESSON-018.** Fixed Header with new SWR hook → cache collision → TypeError → BLACK SCREEN. Fix #2 (string cleanup) and Fix #3 (remove fake data) went fine. Pattern: *adding new SWR hooks is HIGH-RISK*, *removing hardcoded strings is LOW-RISK*. Stacking multiple risky changes without verifying between them → never know which one broke it.

**Rule:** After each code change that could affect runtime behavior (new hook, new API call, new fetch, new component wiring), open the site in a browser and confirm it loads BEFORE making the next change. "Build succeeded" ≠ "site works." Vite can produce a working bundle that crashes on mount. This is just Madi's LAW-003 at a finer granularity: continuous audit during a session, not only at the end.

### AP-21 — Prefer Python/AST over sed for code transformations (LESSON-011)

**LESSON-011.** `sed` with regex on TypeScript breaks on quotes, special characters, multi-line constructs. It also did "delete old" without "add new", leaving orphan state. Python (or any AST-aware tool) handles quotes, multi-line, and atomic replace reliably.

**Rule:** For code edits beyond a single literal token, use a Python script (or Tree-sitter / Babel / TS-AST) rather than `sed`. After any mechanical transformation, `grep` the target pattern to confirm the rewrite landed as expected — never trust `sed`'s silent-on-no-match behavior.

### AP-22 — Test with a real logged-in session, never rely on fallback defaults (LESSON-049)

**LESSON-049.** Backend session dict used key `"user"`, but `police_dashboard.py` read `session.get("username")`. Missing key → fell through to default `"system"`. All 5 approve/reject actions attributed to `"system"` instead of the logged-in admin. The code LOOKED fine (HTTP 200, `ok: true`) — the bug was invisible unless you checked *who* the action was attributed to.

**Rule:** When an endpoint touches session data, test it end-to-end with a real login flow, and verify every user-derived field (user id, name, role, audit trail) matches the logged-in identity — not a generic default. Defaults on session `.get()` are a footgun: prefer `session["user"]` (KeyError → caught) over `session.get("user", "system")` (silent default, attribution lost). Also grep both the write site (`create_session`) and every read site (`session.get(...)`) to confirm key names match.

### AP-23 — Confusion Protocol: stop at ambiguous forks, ask before guessing (gstack v0.18.0.0, 2026-04-17)

**Karpathy's #1 AI coding failure mode:** the agent confidently picks the wrong path at an ambiguous decision point → 10+ min of rework. The fix: notice the ambiguity, state both interpretations back, ask a scoped 2-to-4-option question, then wait.

**Applies when** the fork can't be recovered cheaply:
- Multiple files match the edit target ("`auth.py` or `auth_v2.py`?")
- Two valid interpretations of the request ("refactor" = rename or restructure?)
- Destructive operation with unclear scope ("clean up" — which files?)
- New feature placement when two architectures would both work

**Does NOT apply** to routine decisions already covered by existing APs — don't turn every step into an interrogation.

**How to phrase:** "Hit a fork: (A) X or (B) Y — which?" Not "what do you want?" Not "I'll proceed unless you object."

### Brain-aware invocation (gstack v0.18.0.0, 2026-04-17)

Before touching a file for a fix/feature, run `mcp__gbrain__search` with task keywords (fast BM25, NOT the expensive hybrid `mcp__gbrain__query`) to surface prior findings — the last agent who touched this file may have already found the root cause. After completion, `mcp__gbrain__add_timeline_entry slug="pages/skills/agent-quality/skill" date=YYYY-MM-DD summary="..."` so the next agent benefits. See [[skills/_gbrain/BRAIN-AWARE-INVOCATION]].

### AP-24 — slop-scan advisory before commit (gstack v0.18.0.0, 2026-04-17)

**Pattern (gstack `/review`):** AI-generated code tends to produce recognizable "slop" — dead code paths, unreachable branches, over-generalized helpers, unused parameters, vestigial imports. A quick pattern-match catches most of it before merge.

**Rule:** Before every commit touching code, pass the staged diff through a slop check:

```
git diff --staged > /tmp/diff.patch
slop-scan /tmp/diff.patch   # if binary on PATH — gstack v0.18.0.0
# otherwise: self-check — read the diff, flag dead code / unreachable branches / unused params
```

Warnings are ADVISORY not blocking. Review each, fix obvious hits, note any exceptions in the commit message. If `slop-scan` is absent on the current host (as of session 37 it isn't installed on Mac/Air/VPS), do the mental pass — the discipline of reading your own diff before commit is the point.

**Install follow-up:** once `slop-scan` binary is installed on the dev hosts, wire it into the pre-commit hook as an advisory step (non-blocking). Tracked separately; not a blocker for this AP.

### AP-25 — Risk-weighted subagent review: mechanical tasks get ONE combined review, not two (session 41, 2026-04-17)

**Symptom:** Session 41 executed 22 apk-status-bot MVP tasks via `superpowers:subagent-driven-development`. For the first ~3 tasks (T01 scaffold, T02 DB schema, T03 config), I dispatched the full 3-subagent cycle (impl + spec reviewer + code reviewer) even though the impl was verbatim-copied from the plan file (no judgment exercised by the implementer). Net cost: ~6 extra subagent dispatches (~2 min + tokens) producing only ceremonial "APPROVED" verdicts. For T05-T09 (all pure functions with exact-match tests to plan code), the same pattern would have burned another ~10 dispatches.

**Root cause (5-whys):**
1. Why waste dispatches? I followed `subagent-driven-development`'s "Never skip reviews" rule rigidly.
2. Why rigid? The skill explicitly lists "Skip reviews" as a red flag.
3. Why not risk-weight? Skill treats all tasks uniformly — doesn't distinguish verbatim-from-plan scaffolds from integration logic.
4. Why didn't I adapt? Tension between "follow the skill" and "use judgment." I chose slavish rule-following over risk-weighted adaptation.
5. Why that choice? Defaulting to ceremony felt safer than justifying a shortcut. But ceremony without risk coverage IS waste.

**Rule:** When executing a plan with subagents, classify each task before dispatch:
- **Mechanical / verbatim-from-plan:** implementer copies code from plan with no invention (scaffolds, boilerplate, pure functions whose body is fully specified in the plan's Step 3 block, SQL schema files). → **ONE combined review subagent** (spec + code quality in one call) AFTER implementation. Saves ~50% dispatch cost.
- **Integration / judgment-required:** implementer composes multiple modules, makes routing decisions, wires state machines, handles errors. → **FULL 2-stage review** (separate spec + code quality subagents).
- **If in doubt → default to full 2-stage.** False-positive ceremony costs dispatches; false-negative skipped review costs bugs. Bugs cost more.

**Verification contract:** At the end of a plan execution, the ratio of (combined-review dispatches) : (full-2-stage dispatches) should correlate with (mechanical : integration tasks) count. If you did 20 mechanical tasks and 2 integration tasks, you should have ~20 combined + 4 full-2-stage = 24 review dispatches, not 44 (= 22×2).

**How this amends `subagent-driven-development`:** The external superpowers skill is strict — this AP doesn't override it, it refines the "never skip" rule. "Combined single-call review" IS still review. It's not a skip. It's a risk-appropriate compression.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-26 — Don't confuse "plan executed" with "user's goal met"; check acceptance criteria at each session slice, not just task completion (session 41, 2026-04-17)

**Symptom:** Session 41 completed 22 of 33 planned tasks (T01-T22). Reported the Tan-sliced MVP as "shipped" with 83/83 tests passing. User asked "is the bot working?" Honest answer: NO — the deferred tasks included the bot polling loop (T24), systemd units (T30), and cron entries (T32). Without those, the bot is inert code on disk — no process listening to Telegram, no alerts ever fire, no digest ever sent.

**Root cause (5-whys):**
1. Why call it "shipped" when nothing runs? I scoped "ship" as "code done + tests pass."
2. Why that scope? Following Tan's "MVP ships fast" heuristic — but Tan's MVP is "user can USE it," not "code is built."
3. Why did I mis-scope Tan? Confused "minimum viable code" with "minimum viable service." These are DIFFERENT artifacts.
4. Why not notice during planning? The 33-task plan bucketed entry points (polling, systemd, crons) at the END (T24/T30/T32), not the FRONT. Plan-order bias: front-loaded pure logic because it's easier to TDD.
5. Why TDD-first over run-first? TDD feels productive (tests go green, dopamine hits). "Does it actually run?" requires an entry point + a live smoke test — more friction, less immediate satisfaction.

**Rule:** MVP = Minimum Viable **RUNNING** Service. When slicing a multi-task plan into "ship this session" vs "defer to next session," the first slice MUST include at minimum:
1. **One entry point** (CLI `python -m package.entrypoint`, or a systemd unit, or a bare cron line). Doesn't have to be the final one — even a 10-line `smoke_main.py` that wires one real code path end-to-end counts.
2. **One live-system probe** (`curl`, `sqlite3 .tables`, or `echo /status | telegram-cli`) that exercises the entry point against REAL services, not mocks.
3. **Deployment artifact** (`systemd` or `cron` stub, even if minimal). Running on your laptop ≠ running in production.

**Verification contract:** Before claiming "MVP shipped," answer:
- Q1: Is there a running process on the target host? (`ps aux | grep <service>`)
- Q2: Did it respond to ONE real input in the last hour? (log file modified; DB row written; Telegram reply received)
- Q3: Will it auto-restart on reboot? (`systemctl is-enabled <svc>`; launchd `RunAtLoad=true`)

If any answer is "no" → it is NOT shipped. It's a prototype on a dev machine. Say so.

**Where this bites hardest:** TDD-heavy plans with deferred "wiring." The impulse to say "classifier + state machine + alert queue + webhook + digest all green, 83/83 tests" is strong. But if no cron ever fires the aggregator, those 83 tests are measuring a module that will never run in production. Coverage ≠ aliveness.

**Why no new LESSON:** RULE ZERO. Evidence lives here + `planning-discipline` AP-8 (paired absorption) + gbrain timeline.

### AP-27 — Review findings must close through a fix PR + validator + reviewer rerun, not a comment graveyard (Codex review loop, 2026-04-29)

**Pattern:** A system can "run Codex review" on commits or PRs, post comments, and still fail to improve. Findings become a queue nobody owns; auto-fixes can create new regressions; agents can loop forever if review and repair keep disagreeing.

**Rule:** Any automated code-review loop that finds an actionable issue must produce a closed state machine:

1. **Finding artifact:** comment or issue with target commit/PR, file/line, severity, and minimal fix.
2. **Fix artifact:** a separate fix commit/PR, preferably on a `codex/*` branch for Codex-owned patches.
3. **Validator rerun:** deterministic checks rerun after the fix (`tools/blacksmith_burst_tests.sh` or narrower equivalent).
4. **Reviewer rerun:** Codex/review agent reviews the fix PR again before merge.
5. **Loop ceiling:** stop after 5 repair passes and escalate as human-review-required. Infinite self-repair is forbidden.
6. **Authority boundary:** review bots may comment, open issues, and open fix PRs. They may not merge, close business tasks, mutate Todoist/Notion, or touch raw vault history/secrets.
7. **Rule Zero:** if the finding exposes a durable failure class, update the owning `SKILL.md` + gbrain timeline before claiming the loop is complete.

**Implementation evidence:** `.github/workflows/codex-landed-commit-loop.yml` reviews pushes to `main`, creates a review issue when findings exist, and opens a `codex/review-fix-<sha>-loop-1` PR after validators pass. `.github/workflows/codex-pr-review-loop.yml` reviews PRs, comments findings, repairs only same-repo `codex/*` branches, and enforces `MAX_CODEX_REVIEW_LOOPS=5`. `tools/test_codex_review_loop_workflows.sh` verifies the wiring and is included in `tools/blacksmith_burst_tests.sh`.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-28 — CI cache knobs must prove a real manifest exists before entering an agent loop (GitHub Actions, 2026-04-29)

**Failure mode:** A workflow looks "efficient" because it adds dependency caching, but the sanitized mirror has no `requirements.txt` or `pyproject.toml`. `actions/setup-python` then fails during environment setup and the agent review loop never reaches Codex.

**Rule:** In portable mirror workflows, do not enable dependency-manager caches unless the workflow also proves the cache key source exists in that checkout. For small dependency sets, prefer installing the two or three portable tools directly over adding a fragile cache. Efficiency that aborts the loop before review is negative throughput.

**Mechanical gate:** `tools/test_codex_review_loop_workflows.sh` rejects `cache: "pip"` in the Codex review workflows until the mirror grows a real Python dependency manifest.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-29 — Codex Action model defaults are part of the contract; pin them when the model rejects defaults (GitHub Actions, 2026-04-29)

**Failure mode:** `openai/codex-action@v1` successfully installs and starts Codex, but `gpt-5.2-codex` rejects the CLI/action default `text.verbosity=low` because that model only accepts `medium`. The workflow looks wired, yet the review loop dies before producing a finding artifact.

**Rule:** For GitHub Codex Action workflows, treat model, effort, and verbosity as a single tested contract. If the chosen model has narrower supported values than the action default, pin those values explicitly in the workflow using action inputs and `codex-args`; do not rely on hidden defaults.

**Mechanical gate:** `tools/test_codex_review_loop_workflows.sh` requires `CODEX_EFFORT: medium`, `CODEX_ACTION_ARGS`, `model_verbosity=\"medium\"`, and `codex-args: ${{ env.CODEX_ACTION_ARGS }}` in both Codex review workflows while they default to `gpt-5.2-codex`. Declaring the env var is not enough; the gate must prove it is wired into the `openai/codex-action@v1` invocation.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-30 — `openai/codex-action` with `drop-sudo` is one-per-job; repair passes use `codex exec` or a fresh job (GitHub Actions, 2026-04-29)

**Failure mode:** A workflow invokes `openai/codex-action@v1` once to review, then invokes it again in the same job to repair findings. The first action intentionally removes passwordless sudo. The second action tries to run its own `drop-sudo` setup and fails with `Unexpected: passwordless sudo not available` before repair starts.

**Rule:** In a single GitHub Actions job, use `openai/codex-action@v1` with `openai-api-key` once to install Codex, start the proxy, and drop sudo. Any later repair pass in that same job must call `codex exec` directly using the already-running proxy, or move the repair pass to a fresh job. Do not stack two drop-sudo action invocations in one job.

**Mechanical gate:** `tools/test_codex_review_loop_workflows.sh` requires exactly one `uses: openai/codex-action@v1` per Codex review workflow and requires repair lanes to call `codex exec --sandbox workspace-write`.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-31 — Repair-loop commits must exclude workflow scratch files and explicitly dispatch reviewer reruns (GitHub Actions, 2026-04-29)

**Failure mode:** A forced repair smoke removes the intentional bad file, but the repair commit also includes workflow scratch files (`pr.json`, `.codex`). The same pass also proves a `GITHUB_TOKEN` push does not automatically trigger the next `pull_request` review run, so the "reviewer rerun" promise is false unless dispatched explicitly.

**Rule:** Workflow scratch files live in `$RUNNER_TEMP`, not the repository checkout. Before any automated repair commit, delete known tool state (`.codex`, `pr.json`) and inspect `git status --porcelain`. After creating a fix PR or pushing a repair commit with `GITHUB_TOKEN`, explicitly trigger the PR review workflow via `workflow_dispatch` and grant `actions: write`.

**Mechanical gate:** `tools/test_codex_review_loop_workflows.sh` requires `$RUNNER_TEMP/codex-pr-meta.json`, cleanup of `.codex`/`pr.json`, `actions: write`, and explicit `workflow run codex-pr-review-loop.yml`.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-32 — Self-dispatched reviewer reruns must allow `github-actions[bot]` explicitly (GitHub Actions, 2026-04-29)

**Failure mode:** A repair workflow correctly dispatches the reviewer rerun, but `openai/codex-action@v1` rejects the run because the actor is `github-actions[bot]` and the action defaults to `allow-bots: false`. The repair landed, yet the promised reviewer rerun fails before Codex starts.

**Rule:** If a workflow uses `GITHUB_TOKEN` to dispatch a follow-up Codex review workflow, the receiving Codex Action step must explicitly allow `github-actions[bot]`. Keep the authority boundary elsewhere: only same-repo `codex/*` branches may be auto-repaired, loop count remains capped, and merge remains human-owned.

**Mechanical gate:** `tools/test_codex_review_loop_workflows.sh` requires `allow-bots: true` and `allow-bot-users: github-actions[bot]` on the PR reviewer action.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-33 — Review loops fail closed; green means repaired or no findings (GitHub Actions, 2026-04-29)

**Failure mode:** A Codex review loop can be "working" while still ending green with actionable findings: non-`codex/*` branches are commented but not blocked, no-patch repairs exit 0, loop ceiling writes a summary but exits 0, and explicit self-dispatch can cancel the still-running repair job when `cancel-in-progress: true`. Landed-commit reruns can also fail or duplicate work when the fixed branch already exists.

**Rule:** Automated review gates fail closed. If there are actionable findings and no repair commit/PR is produced, the workflow must exit nonzero and require human review. Self-dispatched reruns must not cancel the current repair run. Landed fix branches must be reusable/idempotent for the same commit.

**Mechanical gate:** `tools/test_codex_review_loop_workflows.sh` requires PR concurrency `cancel-in-progress: false`, human-review-required failure text, nonzero exits on no-patch/ceiling/non-repairable branches, and landed rerun reuse via `git ls-remote`, duplicate-commit skip, and `gh pr list --head`.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-34 — Runtime validators must resolve repo metadata from the canonical wiki (Air runtime, 2026-04-29)

**Failure mode:** A structural validator is correct in the wiki repo but false-reds from Air runtime because the runtime tree intentionally syncs executable tools/skills without repo-only metadata like `.github/workflows`.

**Rule:** If a validator checks repository metadata and is also invoked from `~/nous-agaas`, it must resolve the canonical wiki root (`~/nous-agaas/wiki`) when the runtime root lacks the metadata. Runtime tests should still execute the synced script copy, but inspect the authoritative repository files.

**Mechanical gate:** `tools/test_codex_review_loop_workflows.sh` now falls back from the runtime root to `wiki/.github/workflows` before checking Codex landed-commit and PR review workflow contracts; literal workflow snippets containing shell variables must be checked with single-quoted patterns under `set -u`.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-35 — GitHub-token repair loops cannot auto-push workflow-file edits (GitHub Actions, 2026-04-29)

**Failure mode:** The landed-commit repair loop can produce a valid patch that touches `.github/workflows/*`, pass portable validators, then fail only at `git push` because GitHub refuses `GITHUB_TOKEN` updates to workflow files without the elevated `workflows` permission.

**Rule:** Auto-repair loops running on `GITHUB_TOKEN` must detect staged workflow-file changes before commit/push. Those repairs are privileged CI-surface changes: fail closed with a human-review summary (or a future dedicated token with explicit workflows scope), not a late remote rejection.

**Mechanical gate:** `tools/test_codex_review_loop_workflows.sh` requires both PR and landed loops to contain the workflow-file guard string `GITHUB_TOKEN cannot push workflow updates`.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-36 — Codex repair heredocs must be quoted (GitHub Actions, 2026-04-29)

**Failure mode:** Live landed-commit run `25105699045` reached the direct `codex exec` repair lane, but the shell expanded Markdown backticks inside an unquoted `<<PROMPT` heredoc before Codex saw the prompt. The report path and `codex-fix-note.md` text were executed as command substitutions, leaving Codex with a blank "from" path and no actionable repair context.

**Rule:** Any workflow heredoc that feeds an agent prompt must use a quoted delimiter, for example `<<'PROMPT'`, when the prompt can contain Markdown backticks, dollar signs, or shell-looking text. GitHub expressions are resolved before the runner shell; the shell must not reinterpret the resulting prompt body.

**Mechanical gate:** `tools/test_codex_review_loop_workflows.sh` now requires both landed and PR repair lanes to use `--sandbox workspace-write <<'PROMPT'` and rejects the unquoted `<<PROMPT` variant.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-37 — Prove CI run identity before patching stale notifications (GitHub Actions, 2026-04-29)

**Failure mode:** A GitHub failure email or app notification can arrive after the repair has already landed. If an agent treats the notification text as current truth, it can reopen a solved incident, re-patch green workflows, and restart the repair loop.

**Rule:** Before changing CI workflow code in response to a reported failed run, prove the live identity chain: latest run list, current default-branch head SHA, check-runs for that head SHA, open PR list, queued/in-progress run list, and the reported failed run's `createdAt` compared with the newest successful run. Patch only when the current head or an open PR is actually failing.

**Mechanical gate:** Incident triage must capture the commands equivalent to `gh run list --repo <repo> --limit 20`, `gh repo view <repo> --json defaultBranchRef,pushedAt`, `gh api repos/<repo>/commits/<head>/check-runs`, `gh pr list --state open`, and queued/in-progress run checks before declaring the workflow still broken.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-38 — Phase-0 spec-vs-disk verification gate (cross-model autoplan, 2026-04-30)

**Failure mode:** A spec drafted off memory or summaries can encode a key contract that contradicts what's actually on disk. Both AP-61 v1 (claimed `status:` was free; 782 pages had it with 129 distinct values) and trigger-firing v1 (claimed schema field names that didn't match `context_injector_v2.py`) shipped to autoplan with the same self-similar bug, and both were caught only by the design/eng reviewer reading the actual files.

**Rule:** Before any spec leaves draft, run a Phase-0 verification pass that grounds every claim about an existing field, file, or contract in a `grep`/`rg` or `Read` on the live wiki + runtime path. Cite `path:line` in the spec body, not prose ("we already have X").

**Mechanical gate:** Spec author runs and pastes into the spec a "Phase-0 evidence" block: for each frontmatter field, schema field, file path, or runtime contract referenced, the exact `rg <field>: pages/ | wc -l` count and 1–3 sample paths. autoplan's eng reviewer rejects specs missing this block.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-39 — Frontmatter-field name-collision pre-check (cross-model autoplan, 2026-04-30)

**Failure mode:** Adding a new YAML frontmatter field (`status:`, `superseded_by:`, etc.) without surveying the existing vault first lets you ship a contract that collides with hundreds of pages and silently corrupts retrieval. AP-61 v1 hit this: 782 pages already had `status:` set to 129 distinct values, so a "presence-of-status means superseded" rule would have demoted half the corpus.

**Rule:** Before introducing or repurposing a frontmatter field name, survey existing usage:
```bash
rg "^${FIELD}:" pages/ -l | wc -l            # how many pages
rg "^${FIELD}:" pages/ | awk -F: '{print $3}' | sort -u | wc -l   # how many distinct values
rg "^${FIELD}:" pages/ | head -20            # sample
```
If `pages > 0`, the new contract MUST either (a) pick a different field name, (b) define a value-level discriminator (`status: superseded` not just `status:`), or (c) ship a one-time migration that normalizes existing values.

**Mechanical gate:** Spec must show the survey output for any field it introduces or repurposes. Specs proposing presence-only signals on collision-risk field names get rejected.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-40 — launchd StartInterval cron requires manual first-fire when RunAtLoad:false (Mercury Phase 1, 2026-04-30)

**Failure mode:** Deploying a launchd plist with `StartInterval` and `RunAtLoad: false` produces a job that is loaded, enabled, and looks healthy in `launchctl list` — but the first interval is measured from BOOT, not from load time, so the job can stay dormant for the full interval window before its first fire. Operator sees "deployed" + "enabled" and assumes running; agent sees `state=not_running` after `bootstrap` and incorrectly guesses misconfiguration.

**Rule:** After `launchctl bootstrap` + `enable` of an interval-driven plist, force the first fire explicitly with `launchctl kickstart -k gui/$(id -u)/<label>`, then verify exit 0 in the run log before declaring the cron deployed. Never declare a launchd cron "running" off `launchctl list` state alone — `state` reflects whether the job is currently executing, not whether it has ever executed.

**Mechanical gate:** Deploy script for any interval-driven plist must include a kickstart step + a tail of the run log + an exit-code grep. Skipping the kickstart or the log-tail is a deploy bug, not an optimization.

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

### AP-41 — File:line citations beat prose in cross-model autoplan synthesis (cross-model autoplan, 2026-04-30)

**Failure mode:** When Codex and Claude reviewer subagents return prose summaries of "what the file does," the cross-model synthesis step (CEO/eng/design merge) loses the ability to verify claims against the actual file, and disagreements degenerate into vibe arguments. Across 4 autoplan runs (Mercury, doctrine-drift, AP-61, trigger-firing), the runs that converged fastest were the ones where each reviewer cited `path:line` ranges; the runs that ran longest were ones where one reviewer used prose paraphrase.

**Rule:** Reviewer subagents in autoplan (CEO, design, eng, DX) must emit findings as `path:line-range — claim` triples. Prose claims about existing files without a citation get treated as unverified. Synthesis step diffs the citation sets to find disagreement; prose-only findings can't be diffed and are deprioritized.

**Mechanical gate:** autoplan synthesis prompt instructs reviewers: "Every claim about an existing file MUST cite `path:line` or `path:line-range`. Findings without citations are advisory-only."

**Why no new LESSON:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/agent-quality/skill`.

## Output Format

When completing a task, the output must include:
1. **Proof of done**: screenshot, log line, Telegram reply, or browser URL — not just "I implemented it"
2. **What was tested**: the specific input → expected output → actual output triplet
3. **What was NOT tested** (if anything): honest disclosure prevents future confusion

## Files

| File | Role |
|------|------|
| `pages/lessons/individual/LESSON-005*.md` | Read-wiki-first |
| `pages/lessons/individual/LESSON-017*.md` | No fake data |
| `pages/lessons/individual/LESSON-085*.md` | Done = end-to-end tested |
| `pages/entities/` | Who is who — verify before naming |

## Rules absorbed from lessons

- **LESSON-005:** Read wiki + memory BEFORE designing. See AP-1.
- **LESSON-006:** Done = visible in browser with real data. See AP-2.
- **LESSON-017:** Show empty state, never hardcoded/fake data. See AP-3.
- **LESSON-022:** Validator must check full file, not just diff; rubber-stamp approval is 0% quality. See AP-4.
- **LESSON-025:** Review full file after changes, not just the diff. See AP-4.
- **LESSON-031:** Verify personal relationships from entities/, never assume. See AP-11.
- **LESSON-036:** Test banned patterns against real codebase before deploying. See AP-5.
- **LESSON-060:** Verify tool/plugin is in its registry before recommending. See AP-6.
- **LESSON-064:** Every critical path must log success WITH evidence. Silent success = no proof. See AP-7.
- **LESSON-078:** Evaluate by CVEs + user reports + benchmarks, not star count. See AP-12.
- **LESSON-079:** One agent + skills beats sixteen coordinating agents. See AP-8.
- **LESSON-082:** Always test the actual system/token, not a proxy. See AP-9.
- **LESSON-083:** Ready = outcome test with real data passed, not mechanism test only. See AP-10.
- **LESSON-085:** Done = full chain tested from Telegram. Component existence ≠ chain working. See AP-2.
- **LESSON-042:** Code-gate patterns must be specific enough to avoid false positives. Narrow patterns preferred over broad catches. See AP-13.

- **LESSON-096:** Default to foreground Bash in Claude Code. Only use run_in_background when command takes >30s and you will reap the result. Ghost tasks in UI erode user trust. See AP-17.
- **LESSON-043:** tsc --noEmit must run before any TypeScript deploy. npm run build (vite) skips type checking. 183 type errors leaked undetected. See AP-18.

- **LAW-003:** DONE = real test from Telegram with real data; no browser-test = not done. See AP-2.
- **LAW-004:** Audit before automate, fix data first, observe from day one. See AP-16.
- **LAW-008:** Evidence chain — 3 questions before any number. See AP-14.
- **LAW-013:** 100% truth — report real status, not hoped status. See AP-15.

---

## Evidence trail (append-only)

- **2026-04-15** | v1.0.0 — created in Wave 3 migration; absorbed LESSON-005, 006, 017, 022, 025, 031, 036, 060, 064, 078, 079, 082, 083, 085. This is the most universally applicable skill in the factory.
- **2026-04-15** | v1.1.0 — Wave 4: added AP-14 (evidence chain LAW-008), AP-15 (100% truth LAW-013), AP-16 (5 commandments LAW-004). Absorbed LAW-003, LAW-004, LAW-008, LAW-013.
- **2026-04-16** | v1.3.0 — Absorbed LESSON-096 (foreground Bash default, AP-17). Evidence: bulk lesson absorption session.
- **2026-04-16** | v1.4.0 — Absorbed LESSON-043 (tsc strict not checked, AP-18). Session 32 orphan absorption.
- **2026-04-16** | v1.2.0 — adopted compiled-truth template per [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]] Phase P3. Structural only, no rule changes.
- **2026-04-17** | v1.5.0 — Session 36: absorbed 4 UNMATCHED dream-cycle lessons. AP-19 (run code once before commit, LESSON-032 / LAW-004 triple-violation), AP-20 (verify site loads between changes, LESSON-018), AP-21 (Python/AST over sed for code edits, LESSON-011), AP-22 (test with real session not default fallback, LESSON-049). LESSON-042 was already AP-13 (no duplicate). No new LESSON files (RULE ZERO).
- **2026-04-17** | v1.6.0 — Session 37: AP-23 Confusion Protocol (gstack v0.18.0.0 adoption). Addresses Karpathy's #1 AI coding failure mode: agent picks wrong path at ambiguous fork and loses 10+ min. Scoped to decisions that can't be recovered cheaply. No new LESSON (RULE ZERO).
- **2026-04-17** | v1.7.0 — Session 37: added Brain-aware invocation section (G2, gstack v0.18.0.0) + AP-24 slop-scan advisory (G3, gstack v0.18.0.0 `/review`). Brain-aware: `mcp__gbrain__search` before, `add_timeline_entry` after. Slop-scan: advisory check on staged diff before commit (binary install pending). No new LESSON (RULE ZERO).
- **2026-04-17** | v1.8.0 — Session 41: added AP-25 (risk-weighted subagent review — mechanical/verbatim tasks get ONE combined review, integration tasks get full 2-stage; amends `superpowers:subagent-driven-development` "never skip" rule with risk-appropriate compression) + AP-26 (MVP = Minimum Viable RUNNING Service, not code; plan slice MUST include one entry point + live-system probe + deployment artifact; tests passing ≠ service running). Evidence: session 41 wasted ~6 dispatches on verbatim-scaffold reviews, then called 22/33 plan tasks "shipped" when no process was actually listening on Telegram. Paired absorption with `planning-discipline` AP-8. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.9.0 — Codex/Peter-style review-loop audit added AP-27. Four-lane audit found local hooks and manual Blacksmith burst CI were strong, but the GitHub mirror lacked commit/PR -> Codex review -> fix PR -> review-agent rerun -> max-5-loop automation. Shipped `.github/workflows/codex-landed-commit-loop.yml`, `.github/workflows/codex-pr-review-loop.yml`, `tools/codex_review_loop.py`, and `tools/test_codex_review_loop_workflows.sh`; wired the test into `tools/blacksmith_burst_tests.sh`. The loop is code-only, secret-gated by `OPENAI_API_KEY`, repair-limited to same-repo `codex/*` branches, and cannot merge. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.10.0 — Added AP-28 after the first live GitHub dispatch proved `actions/setup-python` `cache: "pip"` fails when the sanitized mirror has no dependency manifest. Removed the fragile cache from Codex workflows and added a structural gate to keep the review loop from aborting before Codex runs. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.11.0 — Added AP-29 after the live Codex Action run reached `codex exec` and failed on `text.verbosity=low` for `gpt-5.2-codex`. Pinned `CODEX_EFFORT: medium` and `model_verbosity=\"medium\"` across review/fix Codex Action invocations, and taught the workflow gate to require both. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.12.0 — Added AP-30 after forced-finding smoke PR #5 proved repair failed when the workflow invoked `openai/codex-action@v1` twice in one job: first review dropped sudo, second repair action errored `Unexpected: passwordless sudo not available`. Repair lanes now use direct `codex exec` after the first action starts the proxy; the gate enforces exactly one action invocation per workflow. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.13.0 — Added AP-31 after repair smoke PR #5 proved Codex removed the bad `LESSON-130` file but committed workflow scratch (`pr.json`, `.codex`) and no automatic reviewer rerun appeared because `GITHUB_TOKEN` pushes do not trigger `pull_request` workflows. Workflows now write PR metadata to `$RUNNER_TEMP`, clean scratch before commit, and explicitly dispatch the PR review workflow after fix PR creation or repair push. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.14.0 — Added AP-32 after explicit reviewer rerun `25095921041` failed because `openai/codex-action@v1` rejected actor `github-actions[bot]` with `allow-bots: false`. PR reviewer action now allows `github-actions[bot]` explicitly while same-repo `codex/*` repair and five-loop ceiling keep authority scoped. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.14.1 — Tightened AP-29's mechanical gate after a read-only helper audit found it checked for `model_verbosity=\"medium\"` but not the actual `codex-args: ${{ env.CODEX_ACTION_ARGS }}` action wiring. The regression now fails if pinned verbosity exists only as an env declaration. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.14.1 → v1.15.0 — Session 86 helper-C audit absorbed **AP-33** after finding the Codex PR loop could self-cancel on explicit rerun and could end green with unrepaired findings. Patched PR workflow to avoid self-cancel, fail closed on no-patch/ceiling/non-repairable findings, and patched landed workflow to reuse existing fix branches/PRs while skipping duplicate commits for idempotent reruns. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.15.0 → v1.16.0 — Air runtime verification found `tools/test_codex_review_loop_workflows.sh` false-reded from `~/nous-agaas` because runtime sync intentionally omits `.github/workflows`; local rerun also caught a `set -u` literal-pattern bug around `$branch`. Absorbed **AP-34**: runtime-invoked repo-metadata validators resolve the canonical wiki root and quote literal workflow variables safely. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON.
- **2026-04-29** | v1.16.0 → v1.17.0 — Live GitHub run `25105315844` proved the old Codex Action verbosity crash was gone, then exposed **AP-35**: Codex generated a workflow-file repair and `GITHUB_TOKEN` remote-rejected it for lacking workflows permission. Added pre-push guards in both Codex repair loops and tightened the structural gate. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.17.0 → v1.17.1 — Live GitHub run `25105699045` kept workflow-file repair human-owned and surfaced an AP-33 edge: `git push --force-with-lease origin "$branch"` can fail without a remote-tracking ref. Landed loop now captures the remote branch SHA with `git ls-remote` and pushes with an explicit `--force-with-lease=refs/heads/$branch:$remote_sha` while preserving the fresh Codex patch. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.17.1 → v1.18.0 — Fresh failure audit of live run `25105699045` plus a read-only reviewer lane found the direct `codex exec` repair prompts used unquoted heredocs, so Markdown backticks were executed by the runner shell and stripped the review report path from the prompt. Quoted both repair heredocs and added a structural gate rejecting unquoted prompt heredocs. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.18.0 → v1.19.0 — Live incident follow-up showed the reported "same problem" was a stale notification for older failed runs, while current mirror head `10cc5e9` had a successful landed-commit loop run `25125093585`, no open PRs, no queued/in-progress runs, and green check-runs. Added **AP-37** so agents prove run identity and timestamp ordering before patching CI workflows. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON (RULE ZERO).
- **2026-04-30** | v1.19.0 → v1.20.0 — Session 100 cross-model autoplan run on the 5-spec retrieval-quality program (Mercury, doctrine-drift, AP-61, trigger-firing, query-rewriter) surfaced four self-similar failure modes worth codifying. **AP-38** (Phase-0 spec-vs-disk gate) — both AP-61 v1 and trigger-firing v1 shipped with claims that contradicted the live wiki/runtime; eng reviewer caught both only by reading actual files. **AP-39** (frontmatter-field name-collision pre-check) — AP-61 v1 proposed a presence-only `status:` signal without surveying existing usage; survey showed 782 pages × 129 distinct values, would have demoted half the corpus. **AP-40** (launchd StartInterval first-fire) — Mercury Phase 1 deploy looked healthy via `launchctl list` but never fired until manual `launchctl kickstart`; root-caused as macOS launchd measuring StartInterval from boot, not load. **AP-41** (file:line citations over prose in cross-model autoplan) — across 4 autoplan runs, citation-grounded reviews converged fastest, prose-paraphrase reviews degenerated into vibe arguments. gbrain-timeline-ok: pages/skills/agent-quality/skill. No new LESSON (RULE ZERO).

## See also

- [[LESSON-005-claude-must-read-mem0-wiki-before-designing]]
- [[LESSON-017-show-nothing-rather-than-fake-data]]
- [[LESSON-079-one-agent-not-sixteen]]
- [[LESSON-085-false-declaration-feature-done-without-end-to-end-test]]
- [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]]
- `skills/gbrain-ops/SKILL.md` — P4 (absorb learnings into skill layer)
- `skills/_gbrain/RESOLVER.md` — skill dispatcher
