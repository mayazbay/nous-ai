---
tier: 2
name: planning-discipline
description: "Use BEFORE any non-trivial task. Forces plan → atomic steps → 100%-or-stop → save+sync. Absorbs Musk 5-step filter + GOD_PROMPT §1 iron laws + final mental checklist. Triggers on 'plan', 'scope', 'implement', 'build', 'ship', 'refactor', 'migrate'."
type: skill
id: SKILL-PLANNING-DISCIPLINE
version: 1.6.0
status: active
absorbs_laws: [LAW-004, LAW-006, LAW-011]
absorbs_lessons: [LESSON-029, LESSON-054, LESSON-110]
tags: [skill, planning, discipline, musk-filter, pre-task, god-prompt, 2026-04-15]
date: 2026-04-15
source_count: 0
last_updated: 2026-04-15
related: [SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15, agent-quality, mistake-to-skill, evidence-verification]
title: "planning-discipline v1.6.0"
---

# planning-discipline v1.6.0

## Current rules (compiled truth)

1. **No plan = no execution.** Before writing any code or taking any external action, write a plan with: TASK / WHY / MUSK-CHECK / SUBTASKS (numbered, atomic) / SUCCESS / RISKS / ROLLBACK / ESTIMATE. No exceptions for "simple" tasks — every failure I've seen was someone skipping this for a "simple" task.
2. **Execute 1-by-1, never in parallel within a plan.** Pick subtask 1, complete, test, checkpoint, then subtask 2. If subtask 1 fails, do NOT start subtask 2 — root-cause first.
3. **Quality = 100% or stop.** After each subtask, run the self-check (next section). If <100%, stop and either fix or write a HANDOFF.
4. **Save+sync after EVERY subtask.** Not batched. Not end-of-session. After each completed subtask: wiki file + git commit + push + gbrain index.
5. **Musk 5-step filter runs BEFORE Phase P0 of any new task.** If the requirement fails step 1 (nobody will use the output), reject the task.

## P1 — Plan template (write this before coding)

```
TASK:       [one sentence]
WHY:        [what human outcome does this serve?]
MUSK CHECK: [1) who asked 2) can delete 3) can simplify 4) can accelerate 5) can automate]
SUBTASKS:   [numbered, atomic, testable, <30 min each]
  1. ...
  2. ...
  3. ...
SUCCESS:    [concrete, measurable, provable]
RISKS:      [what could go wrong]
ROLLBACK:   [how to undo]
ESTIMATE:   [n subtasks, complexity]
```

Save this to `pages/progress/plans/<slug>-YYYY-MM-DD.md` before execution begins.

## P2 — Musk 5-step filter (apply in order)

1. **Question the requirement.** Who asked? Is it physics-justified or tradition? Does it serve ERAP / Satory / revenue or is it busywork? If nobody will use the output → REJECT the task.
2. **Delete.** What can I remove and still deliver the outcome? If I didn't delete anything, I didn't try hard enough. Add back ≤10% if I cut too much.
3. **Simplify.** Can I do this with if/else instead of an LLM? Can I do it in 1 file instead of 5? Can a regex replace the model? Deterministic > probabilistic, always.
4. **Accelerate.** Now that it's simple, how do I make it fast? Only optimize what survived steps 1-3.
5. **Automate.** Can this be triggered by an event instead of a cron? Can a pre-commit hook catch this instead of me? NEVER automate a broken process.

## P3 — Per-subtask self-check (deterministic, no AI-judging-AI)

After each subtask:
- [ ] Does it compile / run without errors?
- [ ] Do existing tests still pass?
- [ ] Did I actually TEST the change (not just read the code)?
- [ ] Would this survive `pytest --tb=short` right now?
- [ ] If frontend: did I click every button? (LESSON-047)
- [ ] If data: did I verify with real values, not assumptions?

If any → NO, stop. Do not proceed to subtask N+1.

## P4 — Final mental checklist (before declaring task complete)

- [ ] Did I plan before executing?
- [ ] Did I execute 1-by-1, not in parallel?
- [ ] Did I test each step with real output (not "should work")?
- [ ] Did I checkpoint / save+sync after each subtask?
- [ ] Did I check lessons + skills for known patterns before starting?
- [ ] Did I save new knowledge to gbrain + Obsidian (lesson or skill)?
- [ ] Is quality 100%? If not, did I hand off cleanly?
- [ ] Did I verify all facts against source documents (not memory)?

## Anti-patterns

### AP-1: "This task is simple, skip the plan"
**What goes wrong:** 80% of failures I've seen came from skipping the plan on a "simple" task. "Simple" tasks hide assumptions that the plan template surfaces.
**Fix:** Write the plan even if it's 3 lines. The discipline is the point.

### AP-2: Batching subtask completions
**What goes wrong:** "I'll commit all three when I'm done" → subtask 2 breaks subtask 1 silently → you don't find out until step 3.
**Fix:** Save+sync after EACH subtask. Non-negotiable.

### AP-3: "It should work" without probe
**What goes wrong:** LESSON-085 — declaring done without end-to-end test.
**Fix:** Success = verified probe output, not "code compiles". See skill: `evidence-verification`.

### AP-4: Parallelizing within a plan
**What goes wrong:** Subtask 3 written before subtask 1 verified → rework when subtask 1 spec changes.
**Fix:** Strictly sequential. Parallelism only between INDEPENDENT plans.

### AP-5: Writing action packets to government entities as if they were commercial vendors
**LESSON-110.** Wrote a full technical VPN action packet to Asyl asking him to get a PSK from NIT. Asyl: "NIT is government, they will never give this." The packet was technically sound but addressed to the wrong class of entity.

**Fix:** Before writing ANY action packet that requests access/credentials from an external entity, classify that entity first:

| Entity type | Appropriate channel | Expected timeline |
|---|---|---|
| Commercial vendor (SaaS, API, cloud host) | Technical support ticket | Hours to days |
| Government / regulatory (NIT, MVD, ERAP, MCRIAP) | Route via commercial party with existing contract, or find an operational workaround that avoids the access entirely | Months to never |
| Individual operator (Denis, DevOps contacts) | Coordination only; they can do what they already have rights to | Same day if they agree |

**Signal of a government entity:** a blocker tracked unchanged for months across multiple sessions. Multi-month immobility is structural, not scheduling. Stop packaging it as a coordination problem.

### AP-6: Budget-unit ambiguity (day vs month vs year) (LESSON-029)

**LESSON-029.** Claude heard "$1K–5K" from Madi and wrote plans assuming PER-DAY spend. Actual budget: PER-MONTH. $1K/month = ~$33/day. Every plan built on the $1K/day assumption was 30× over-scoped — 5-agent Council at $125/day ($3.75K/month) looked affordable when it was a third of the entire monthly budget.

**Fix:** In the MUSK-CHECK phase of any plan that touches money, explicitly resolve budget UNIT before sizing:
- `TOTAL_BUDGET: $1K–5K PER MONTH` (not just `$1K–5K`)
- Convert to per-day for LLM cost comparisons: `$33–$167/day`
- Cross-check with `evidence-verification` before any "we can afford X" claim in plans or outbound comms.

If Madi says "$N" without a unit, STOP and ask: "per day, per month, per year, or one-time?" before continuing. Ambiguity on money units destroys plans silently — the plan looks right to both parties but resolves to different budgets.

### AP-8: MVP = Minimum Viable RUNNING Service (not Minimum Viable Code). First slice MUST include entry point + live probe + deploy artifact. (session 41, 2026-04-17)

**Symptom:** Session 41 wrote a 33-task TDD plan for the APK status bot, sliced it into T01-T22 for "this session" (Tan-sized MVP ships fast). Executed 22 tasks, 83/83 pytest green, 24 commits pushed to GitHub + cloned to VPS + Air. Called it "MVP shipped." User then asked: **"is the bot working?"** Honest answer: NO — the deferred tasks T24 (bot polling loop), T30 (systemd units), and T32 (crons) are what makes it a RUNNING service. Without them: inert code on disk. No process on any host listens to Telegram. No alert ever fires. No digest ever sends. The 83 passing tests measure modules that will never execute in production without the deferred entry points.

**Root cause (5-whys):**
1. Why call it "shipped" when nothing runs? I scoped "ship" as "code done + tests pass."
2. Why that scope? Followed Tan's "ship fast" heuristic — but Tan's MVP is "user can USE it," not "code is built and tested."
3. Why mis-scope Tan? Conflated "minimum viable code" with "minimum viable service." Different artifacts.
4. Why plan ordered entry points LAST? TDD-first bias: pure logic (classifier, state machine) is easier to TDD than integration wiring (polling loop, cron jobs). Front-loaded the easy dopamine.
5. Why not notice during slicing? Sliced at a "natural module boundary" (end of pure-logic modules) instead of a "natural service boundary" (first running end-to-end loop).

**Rule:** When slicing a multi-task plan into "ship now" vs "defer later," the first slice MUST include AT MINIMUM these three artifacts, regardless of task count budget:
1. **One entry point.** CLI `python -m pkg.main`, or a bare systemd ExecStart, or a single cron line. Doesn't have to be the final one — a 20-line smoke_main.py that exercises ONE end-to-end path counts.
2. **One live-system probe.** A command that proves the entry point is alive against REAL services (not mocks): `curl localhost:8000/health`, `sqlite3 .tables`, `ps aux | grep`, `echo /status | telegram send`. Must return non-trivial output — a 200 OK with empty body is NOT a probe.
3. **One deployment artifact.** Even minimal — a launchd plist, a cron line in a file, a `systemctl enable <unit>` stanza. Running on your laptop ≠ running in production. Deployment = it auto-restarts on reboot without human intervention.

**Verification contract (answer these before claiming "MVP shipped"):**
- Q1: Is there a running process on the target host right now? (`ps aux | grep <service>` returns a PID)
- Q2: Did it respond to ONE real input in the last hour? (log file mtime within 1h; DB row inserted; Telegram message received)
- Q3: Will it survive a reboot? (`systemctl is-enabled` returns `enabled`, or launchd `RunAtLoad=true`, or cron entry exists)

If ANY answer is "no" → NOT shipped. Say "prototype on dev machine, not shipped yet" clearly. Don't sugarcoat as "MVP."

**How this refines Tan's "ship fast":** Tan says 1-session MVP and "talk to users before day 2." But "talk to users" presumes users can USE the thing. An 83-test-green codebase that nobody can call from Telegram isn't a user-testable MVP — it's an engineer-testable module set. Tan's rule applies only when user contact IS possible.

**Paired absorption:** `agent-quality` AP-26 captures the same root cause from the "don't confuse plan-executed with goal-met" angle. Together they form one discipline: code completeness ≠ service aliveness.

**Why no new LESSON:** RULE ZERO. Evidence lives here + `agent-quality` AP-26 + gbrain timeline on `pages/skills/planning-discipline/skill`.

### AP-7: Confusion Protocol — stop at ambiguous planning forks (gstack v0.18.0.0, 2026-04-17)

**Karpathy's #1 AI coding failure mode:** the agent confidently picks the wrong interpretation at a decision point → 10+ min of wasted planning. In planning scope, asymmetric-cost forks include:
- **Scope decomposition:** new ask arrives mid-plan — absorb into active plan or spin off separate plan? (Wrong choice = cross-contamination or missed deadline.)
- **Priority order:** three workstreams could all go first — which first? (Wrong pick delays the critical path.)
- **Decomposition depth:** one plan covering 4 phases vs 4 separate plans? (Wrong lumping forces re-plan.)
- **Stakeholder ambiguity:** "Madi said approve" — approve what exactly? The plan as written, or the direction? (Wrong read = executing unapproved scope.)

**Rule:** At asymmetric forks — ASK. Phrase: "Hit a fork: (A) X or (B) Y. Which path?" Don't "proceed unless objected." AP-6's budget-unit stop is a specific instance of this general rule.

**Non-examples (just proceed):** writing a TaskCreate for a clearly scoped step; adding a detail inside an already-approved phase.

### Brain-aware planning (gstack v0.18.0.0, 2026-04-17)

Before drafting a plan, `mcp__gbrain__search` for the topic or subsystem — a prior plan may already contain phases/TaskCreate scaffolds that can be reused or extended. Cheaper to reuse a proven decomposition than invent a new one. After the plan is approved, `mcp__gbrain__add_timeline_entry slug="pages/skills/planning-discipline/skill"` with the plan id + top decisions. See [[skills/_gbrain/BRAIN-AWARE-INVOCATION]].

### CEO review reinforcement (gstack v0.18.0.0, 2026-04-17)

**REVIEW ONLY — NO CODE CHANGES.** At every STOP point of the plan/design flow (after presenting the design, before writing the plan doc, after writing, before execution) — wait for the CEO's approval. Do NOT "start implementing while we discuss." Madi's explicit pattern (session 37): "plan then execute one by one — each phase separately." This reinforcement repeats at every STOP because agents slide into impl during planning. The planning work is done WHEN Madi says done, not when the plan doc is written.

### Autoplan-then-review flow (Garry Tan pro tip, session 37.5)

Garry Tan shared: "autoplan in Claw/Hermes (faster), then drop the plan and do plan-eng-review in Claude Code."

**Our mapping:**

| Step | Where | Why |
|---|---|---|
| Office hours brainstorm | Claude Code (Opus) — deep | Requires Madi dialogue |
| Autoplan (first-pass structured plan) | **OpenClaw `/ask` → GLM-5.1** | Fast + cheap (Opus would overthink) |
| Plan-eng-review (expand + fork resolution) | **Claude Code (Opus)** | Strongest reasoning, domain context |
| Write to brain project page | Claude Code edit | `pages/projects/<PROJECT>-YYYY-MM-DD.md` |
| Paste into Claude Code (for impl) | Madi manual | Human control point |

**Concrete example:** session 37.5 ran the gstack token-compactor autoplan end-to-end — OpenClaw autoplan (9m48s on GLM-5.1, 8 phases rough), CEO review amended order + added specific commands + resolved 3 Confusion-Protocol forks, output at `pages/projects/TOKEN-COMPACTOR-2026-04-17.md`.

**Rule:** For any plan > 3 phases that isn't urgent same-session, use this flow. Saves Opus tokens on rough-outline work and forces the CEO-review discipline (keep Claude Code work on high-leverage reasoning, not boilerplate structure).

**Anti-pattern:** using Claude Code (Opus) to generate BOTH the rough outline AND the review. That's 2-3× the tokens for the same output. The factory has OpenClaw — use it.

## Rules absorbed from LAWs

- **LAW-004** (5 Commandments — scope, observability, audit, data quality, throughput): enforced via SUCCESS field in plan
- **LAW-006** (Task = Requirement): enforced via WHY + Musk step 1
- **LAW-011** (Business Gate): enforced via Musk step 1 reject

## Rules absorbed from lessons

- **LESSON-029:** Always resolve budget unit (day/month/year) before any cost plan. `$1K–5K` is not a budget until the unit is stated. See AP-6.
- **LESSON-054:** CEO must check for work before calling LLM; empty cycles burn $6/day.
- **LESSON-110:** Before writing any action packet asking external entity for access, classify entity first: government bodies require commercial-side routing, not direct technical asks. See AP-5.

---

## Evidence trail (append-only)

- **2026-04-17** | v1.3.0 — Session 37: AP-7 Confusion Protocol (gstack v0.18.0.0 adoption). Scope decomposition / priority order / decomposition depth / stakeholder-ambiguity forks must ASK, not guess. Generalizes AP-6 budget-unit-stop to all asymmetric-cost forks. No new LESSON (RULE ZERO).
- **2026-04-17** | v1.4.0 — Session 37: added Brain-aware planning (G2 gstack v0.18.0.0) + CEO review reinforcement (G4). Planning flow STOPs are review-only; agent must NOT implement during design dialogue. Madi bar: "plan then execute one by one." No new LESSON (RULE ZERO).
- **2026-04-17** | v1.5.0 — Session 37.5: added Autoplan-then-review flow (Garry Tan pro tip). Delegate rough outline to OpenClaw/GLM-5.1 (fast+cheap), do expansion + fork-resolution in Claude Code/Opus (deep reasoning). Demonstrated on `pages/projects/TOKEN-COMPACTOR-2026-04-17.md` end-to-end same day. Saves Opus tokens on boilerplate structure work. No new LESSON (RULE ZERO).
- **2026-04-17** | v1.6.0 — Session 41: added AP-8 — MVP = Minimum Viable RUNNING Service, not code. Session 41 shipped 22/33 tasks of apk-status-bot, 83/83 pytest green, called it "MVP shipped" — but T24 (bot polling loop) + T30 (systemd units) + T32 (crons) were deferred, so nothing actually runs on Telegram. Code on disk ≠ service alive. Rule: first slice of any multi-session plan MUST include (1) one entry point, (2) one live-system probe, (3) one deployment artifact. Paired with `agent-quality` AP-26 (don't confuse plan-executed with goal-met). No new LESSON (RULE ZERO).
- **2026-04-17** | v1.2.0 — Session 36: absorbed LESSON-029 (budget unit ambiguity, AP-6). Claude previously heard "$1K–5K" as per-day, Madi meant per-month; 30× over-scope. No new LESSON file (RULE ZERO).
- **2026-04-16** | v1.1.0 — Absorbed LESSON-110 (classify entity before access ask, AP-5). Government != vendor. Evidence: bulk lesson absorption session.
- **2026-04-15** | v1.0.0 created per [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]] Phase P2. Absorbs GOD_PROMPT §1 iron laws + §2 Musk 5-step + §10 mental checklist + LAW-004/006/011 + LESSON-054 (empty CEO loop $6/day burn).

## See also

- [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]]
- [[agent-quality]] — complementary, triggers DURING a task
- [[mistake-to-skill]] — what to do AFTER a debug session succeeds
- [[evidence-verification]] — how to prove "done"
- [[LAW-004-five-commandments]]
- [[LAW-006-task-equals-requirement]]
- [[LAW-011-business-gate]]
- [[LESSON-054-ceo-empty-queue-burns-money]]
