---
tier: 2
type: skill
name: karpathy-loop
id: SKILL-KARPATHY-LOOP
version: 1.12.0
last_updated: 2026-05-14
status: active
description: "v1.12.0 — the operating system Nous AGaaS runs by. Tan/Karpathy/Finn compounding pattern + Musk 5-step elimination + Software 3.0 spec-as-source discipline + GStack multi-virtual-reviewer planning workflow + 6-axis scorecard + billion-dollar-solopreneur framing. v1.10 added AP-11 (skills are the prompts). v1.11 ships `tools/test_multi_reviewer_invoked.sh`. v1.12 adds AP-12 + AP-5 Rule 6: a narrow Council adversarial/domain pass complements AP-5 when a plan has IR/retrieval, novel cost/latency, security/billing isolation, single-ablation evidence, or lock-in risk."
triggers:
  - every session close (apply 6-axis scorecard before declaring done)
  - any plan beyond a single-edit task (invoke multi-virtual-reviewer review)
  - about to recommend something to Madi as a yes-man (push back like a peer CEO)
  - drafting a handoff (the Karpathy 6/6 phrase is referenced — score ground-truth, don't assert)
  - new compounding artifact identified (run the compound-chain check — does this AP cascade to a sibling layer?)
  - learning a lesson worth persisting (RULE ZERO Tan/Karpathy/Finn — SKILL.md + gbrain timeline, no LESSON file)
tools: [Bash, Read, Edit]
mutating: false
absorbs_laws: [LAW-001, LAW-009, LAW-015, LAW-017, AMD-005, AMD-006]
related: [session-operating-contract, mistake-to-skill, audit, infrastructure, gbrain-ops, factory-ops, planning-discipline]
tags: [skill, doctrine, karpathy, tan, musk, gstack, billion-dollar-solopreneur, compounding, 6-axis-scorecard, compound-chain, multi-reviewer, 2026-04-21]
title: "karpathy-loop v1.12.0"
---

# karpathy-loop v1.12.0

## Purpose

The operating system Nous AGaaS runs by. Madi's standard for every agent on every host: behave like a top-tier CEO/CTO peer running a billion-dollar business with a tiny team + agents, not a junior engineer asking permission. This skill formalizes what was previously scattered across handoffs as the phrase *"Karpathy 6/6"* and across project `CLAUDE.md` as the *"Tan / Karpathy / Alex Finn pattern"*.

Three disciplines fuse into one operating loop:

1. **Tan / Karpathy / Finn — compounding via skills, not lessons.** RULE ZERO: every learning lands in `SKILL.md` + gbrain timeline; no new LESSON files. Skills compound, lessons rot.
2. **Elon Musk 5-step elimination — question, delete, simplify, accelerate, automate (in that order).** Step 2 (delete) is the one we skip; the loop forces it explicitly at every plan boundary.
3. **GStack multi-virtual-reviewer planning — heavy upfront planning, multiple reviewer roles (CEO + DevEx + Designer + Eng Manager) critique independently, ship one-shot to main.** Rework cost is paid in planning, not in the rebase.
4. **Software 3.0 / spec-as-source — natural language is source only when it is structured, versioned, tested, and compiled into behavior.** Prompts alone are not the product; executable specs, validators, and skills are.

The output of running this loop correctly = every session ends with the substrate measurably smarter, every plan ships to main with minimal rework, every agent that reads the substrate inherits sharper doctrine than the agent before.

## Contract

**Inputs:** A session, a plan, a piece of work being declared "done," or a bug just root-caused.

**Outputs:**
- The 6-axis scorecard run with evidence per axis (not asserted).
- Any new learning codified into the appropriate `SKILL.md` (per RULE ZERO + `mistake-to-skill` AP-11 3-edit ritual) + gbrain timeline pushed.
- Any major plan reviewed by multi-virtual-reviewer pass before approval (CEO + DevEx + Designer + Eng).
- Compound-chain check: did this new AP cascade to a sibling layer? If yes, codify the sibling AP same session (like AP-8 → AP-9 → AP-33 in session 55).

**Invariants:**
- Every session-close handoff cites the 6-axis scorecard with **evidence per axis**, not "6/6" as a vibe.
- Every codified rule passes the AP-15 self-application check (codification ≠ self-application — re-read same-session edits against newly-written rule).
- Every major plan that lands in main was reviewed by the multi-virtual-reviewer pass before approval (not just CEO single-pass).
- Yes-man behavior is hard-banned. Push back like a peer CEO when the proposal is wrong; offer better when honest disagreement exists. (See AP-1 in this skill.)

## The 6-axis Karpathy scorecard (formal definition)

Used at every session-close to score whether the session compounded or just executed. **All 6 axes must be cited with evidence in the handoff.** "6/6" without per-axis evidence is hard-banned (yes-man pattern; AP-1 here).

| # | Axis | Met when… | Evidence shape required |
|---|---|---|---|
| 1 | **AP ≥1 absorbed** | At least one new Anti-Pattern was codified in a `SKILL.md` this session via the AP-11 3-edit ritual. | Skill name + AP number + version delta (e.g., `session-operating-contract` v1.6 → v1.7 + AP-9). |
| 2 | **gbrain timeline ≥1 push** | At least one `mcp__gbrain__add_timeline_entry` (or CLI fallback `bin/gbrain timeline-add`) returned `{"status":"ok"}` for a skill bumped this session. | Slug + date + `{"status":"ok"}` payload (or "deferred to autopilot" with reason if MCP+CLI both unavailable — but see `gbrain-ops` AP-33: CLI fallback is mandatory before deferral). |
| 3 | **Compounding artifact ≥1** | At least one shipped artifact compounds across sessions: a new mechanical gate, a new probe wired into SOAO, a new test the pre-commit hook enforces, a new launchd cron, a new tool that any future session can call. | Path + how it compounds + count of sessions it would protect. |
| 4 | **Zero rot smuggled** | No "done" claim without the 4-artifact DONE protocol (SOC rule 4); no half-shipped feature presented as complete; no bypassed verification gate. Honest deferrals count as PASS — they're not rot, they're scoped honesty. | List of any deferrals + reason + carryover destination. If "no deferrals," that's the evidence. |
| 5 | **Substrate measurably smarter** | The next session's agent will know something this session's agent did not. Concrete: a probe that catches a class of drift, a CLI fallback path documented, a hypothesis disproved + replaced with truth, a workflow formalized. | What the next agent inherits + where they will read it (file path + line). |
| 6 | **RULE ZERO upheld** | Zero new `LESSON-NNN-*.md` files created. All learnings landed in `SKILL.md` updates + gbrain timelines. Pre-commit hook enforces this physically; manually verify in case the hook is bypassed. | Count current lessons, confirm highest `LESSON-NNN` is `<=129`, and confirm no added `pages/lessons/individual/LESSON-*.md` paths in `git diff --name-status --diff-filter=A`. Current count may be lower after migration. |

**Scoring:** 6/6 = compounding session. 5/6 = ship the handoff with the missing axis as a flagged carryover. ≤4/6 = stop, root-cause why this session didn't compound, codify the failure mode into THIS skill or `session-operating-contract`, then close.

**Anti-pattern:** writing "Karpathy 6/6" in a handoff without per-axis evidence is itself a yes-man pattern (claiming the score without doing the score). See AP-1.

## The compound-chain pattern (cross-layer AP cascading)

When you codify an AP at one layer (planning / execution / tooling / identity / substrate), check immediately whether the **same meta-class** of failure mode exists at the OTHER layers and codify those siblings same-session. Captured failures cluster by meta-class, not by isolated incident.

**Canonical session-55 example:**

| Layer | AP | Failure mode | Red-flag phrase |
|---|---|---|---|
| Planning | AP-8 (SOC v1.6) | Reshuffle spec-literal order to front-load easy wins | *"front-load certain wins"* / *"if X dead-ends we still have Y"* |
| Execution | AP-9 (SOC v1.7) | Ask permission on tactical decisions agent can decide | *"which do you prefer?"* / *"parallel or sequential — your call?"* |
| Tooling | AP-33 (gbrain-ops v1.21) | Defer write when MCP drops instead of CLI fallback | *"deferred to autopilot cycle"* / *"will catch up next session"* |

All three are flavors of the same meta-class: **self-protection-over-user-value**. They cascaded across one session because each new AP, once codified, made the next manifestation visible. The agent stops at one layer, the user catches the next layer, and the codification chain runs.

**The compound-chain check (apply on every new AP):**
1. Name the meta-class of the failure mode (e.g., "self-protection," "read-substrate-before-applying-defaults," "verify-the-gate-does-what-it-claims").
2. List the layers that meta-class CAN manifest in: planning, execution, tooling, identity, substrate, communication, deployment.
3. For each layer not yet covered, scan recent session work for the same failure shape. If found, codify the sibling AP same-session.
4. Cross-ref all siblings explicitly in each AP body (so the next-session agent reading any one AP discovers the whole family).

**Other compound chains observed in the substrate:**
- AP-1 (golden-prompt treadmill, identity layer) + AP-2 (generic-default reflex, user-interaction layer) + AP-4 (identity-from-substrate, outbound layer) — same *read-substrate-before-applying-generic-defaults* meta-class.
- `audit` AP-12 (read current skill before doctrine, execution layer) + AP-15 (codification ≠ self-application, substrate layer) + AP-16 (read skill before audit design, design layer) — same *consult-the-substrate-at-moment-of-action* meta-class.

## The Tan / Karpathy / Finn pattern (RULE ZERO formalized)

Already binding via project `CLAUDE.md` RULE ZERO + pre-commit hook RULE 4 (`infrastructure` AP-43). This skill formalizes the WHY:

- **Lessons rot.** A separate `LESSON-NNN-*.md` file is a doc the agent never re-reads after writing. The fix lives in the file but nobody runs into it again.
- **Skills compound.** A bullet under `## Anti-Patterns` in a `SKILL.md` is loaded EVERY time that skill is invoked. The same cognitive cost (writing the rule once) pays off N times instead of once.
- **Skills are the prompts.** If the same instruction must be pasted again, the runtime interface failed. Convert it into owner-skill doctrine or prove it is already encoded.
- **gbrain timeline = searchable evidence.** A timeline entry on the same skill page makes the rule's evidence chain searchable for future sessions doing root-cause work.

**The 3-edit ritual** (per `mistake-to-skill` AP-11):
1. Bump frontmatter `version:` (semver — minor for new rule/AP, patch for honest-revision of existing).
2. Bump H1 `# <skill-name> v…` to match.
3. Append `## Evidence trail` (or `## Timeline`) entry with date + version + trigger + rule + cross-refs.

Then push gbrain timeline (MCP if available; `bin/gbrain timeline-add` CLI fallback per `gbrain-ops` AP-33 if MCP is down).

**The LESSON ceiling is enforced mechanically.** Pre-commit hook physically rejects new LESSON files. SOAO checks the current count plus ceiling every session-open.

## Musk 5-step (in order, no decoration)

Already binding via SOC Rule 9. Restated here as the second leg of the loop. **Full doctrine + worked examples + Idiot Index + Magic Wand Number + Anti-Patterns + mechanical enforcement (`tools/test_musk_step_2.sh`) lives in [[musk-algorithm]] v1.0.0** (session 64, codified from The Book of Elon). This skill grades whether you applied it; musk-algorithm is the method.

1. **Question the requirement** (even Madi's; even your own).
2. **Delete the part.** Step 2 is the one we skip. Every plan audits for it explicitly. If you find yourself simplifying something that could be deleted, stop and delete. If you are automating something nobody reads, stop and kill.
3. **Simplify what remains.**
4. **Accelerate cycle time.** This is what AP-9 protects (don't ask permission on tactical decisions; user round-trips are cycle-time tax).
5. **Automate last.** Compounding gates / mechanical probes go AFTER the rule is validated by hand, not before.

**The `delete?` trigger word** (SOC Rule 8) invokes step 2 on demand. Use it on yourself before sending any plan: *"what could be deleted from this plan instead of just simplified?"*

## GStack multi-virtual-reviewer planning workflow (Madi's standard)

Madi's preferred planning pattern — heavy upfront review with multiple agent personas, then one-shot ship to main with minimal rework. Stated verbatim by Madi (session 55):

> *"I prefer to do a lot of work in planning and get it reviewed by my virtual CEO, DevEx manager, designer and Eng manager in GStack before clicking approve on a plan. But the upside is usually I can one shot land it to main with minimal rework."*

**The workflow:**

1. **Plan drafted** — by the executing agent (or by Madi). Spec written, design choices proposed, scope sized.
2. **CEO review** — *"Is this the highest-leverage move right now? What does it compound? What's the explicit Musk-step-2 (what can we delete)? What's the billion-dollar-solopreneur frame on this?"* This skill's role.
3. **DevEx review** — *"Can the next agent execute this without re-reading the whole spec? Are the file paths absolute? Are the commands copy-pasteable? Where does it break the existing developer workflow?"* `infrastructure` + `gbrain-ops` skill perspectives.
4. **Designer review** — *"Does this fit the user's mental model? Will Madi look at this and immediately know what to do? Is it a UI/UX change? Then frontend-design skill applies; mockups before code."* (Use the frontend-design superpower skill if visual.)
5. **Eng manager review** — *"Does this fit the existing architecture? Are we adding the right number of moving parts? What breaks downstream? What's the rollback plan if we're wrong?"* `audit` + `factory-ops` perspectives.
6. **One-shot ship** — only after all 4 roles approve OR explicit owner override. The plan goes to main without iteration; rework cost was paid in planning.

**Each role pushes back independently.** The agent playing a role MUST argue the role's POV honestly, not perform agreement. If CEO says "delete this whole step," DevEx might say "can't, we depend on it for X" — that's healthy disagreement that surfaces real constraints.

**When to use:**
- Any plan estimated >2h of work.
- Any plan that touches >3 files in different subsystems.
- Any plan that introduces a new mechanical gate / cron / launchd / probe.
- Any plan that changes user-facing behavior (factory `/ask` routing, Telegram interface, satory.nousagaas.com).

**When NOT to use:**
- One-edit tactical fixes (per Rule 15 / AP-9, just execute).
- Honest-revision of an already-shipped rule (the rule's existing review trail is the prior approval).
- SOAO-detected drift fixes (mechanical recovery, not new design).

## Billion-dollar-solopreneur framing (the standard for every action)

The frame Madi applies to every decision. Spelled out (verbatim, session 55):

> *"With the billion-dollar agent company, like you can see on the news, there are a couple of businesses with one or two employees with agents running their billion-dollar businesses. Would they do the same thing? I need you now to think like those best guys in the world, like Elon Musk's companies, Elon Musk's team, like the best CTO and CEO combined with Gary Tan and Karpathy from Stanford."*

**Operationalized as 4 questions before any non-trivial action:**

1. **Compound or one-off?** Will this work compound across future sessions / agents / customers, or does it pay off once? (Per Rule 10 of SOC — extend an existing gate or create a new one; never write throwaway scripts when a compounding version is the same effort.)
2. **Tiny-team-with-agents lens.** If we had only 2 humans + 50 agents, how would this be structured? (Centralizes the substrate; pushes work into mechanical gates and skill-codified doctrine instead of human-process.)
3. **Customer-value vs hygiene?** Per Rule 14 / AP-8 — value-creation goes first with time-box guardrail. Hygiene gets the remainder.
4. **What would Musk delete?** Per Rule 9 / step 2 — the most important question is which part doesn't need to exist at all.

**Anti-pattern:** doing work that's "good engineering" but doesn't fit any of the 4 frames. Probably hygiene-disguised-as-value. See AP-2.

## Top-CTO decision loop (thin harness, fat skills)

Madi's 2026-04-29 directive: operate like the best CEO+CTO at a two-human billion-dollar agent company. The answer is not "more agents everywhere." The answer is:

> **Thin harness, fat skills, deterministic gates, ruthless deletion, one substrate.**

That sentence is the default architecture choice. The harness should stay small and inspectable. Skills, tests, probes, handoffs, and GBrain timelines hold the compounding intelligence. LLM agents are labor and judgment; the substrate is the company memory and operating system.

**Every non-trivial action runs these 10 questions in order:**

1. **Outcome:** what business or factory outcome changes if this works?
2. **Named author:** who asked for this requirement, and is it still true?
3. **Delete:** what part, process, prompt, cron, dashboard, or human step can vanish?
4. **Deterministic first:** can a script, test, parser, rule, or Minions shell job do this with zero LLM reasoning?
5. **Skillify:** if this is a repeated failure or repeated instruction, which `SKILL.md` absorbs it?
6. **Gate:** what mechanical proof prevents this class from recurring?
7. **Agent ownership:** can independent agents work in parallel with disjoint files/responsibilities?
8. **Madi boundary:** is this tactical, reversible, and testable? If yes, execute. Escalate only money, credentials, irreversible actions, or true ambiguity.
9. **Proof:** what exact command/output/git state/counter-check will prove the claim?
10. **Sync:** where does the artifact land: Obsidian, GBrain timeline, Air runtime, VPS bare, handoff?

**Default choices:**

| Situation | Choose |
|---|---|
| Repeated mistake or repeated instruction | Skill update + GBrain timeline |
| Deterministic recurring job | Script/Minions shell job, not gateway LLM cron |
| User-facing URL or tunnel | Probe with `curl`/browser before presenting as working |
| Agent network access | Observe/report first, static policy before LLM judge, redact secrets |
| Quality of agent output | Outcome grader feeds tickets; no dashboard without bug pipeline |
| Production upgrade with schema/local overlays | Dry-run clone + restored DB + rollback proof before live mutation |
| Multi-subsystem plan | Multi-reviewer Skill invocation before execution |
| Tactical implementation choice | Decide and execute; don't ask Madi |

**What this deletes:**

- golden-prompt/persona rewrites,
- LLM tokens on pure API-fetch/write crons,
- green status from TCP-only probes,
- dashboards with no ticket/fix loop,
- "done" without proof,
- chat-only learnings that never enter skills,
- agent overlap on the same files without ownership.

**What this creates:** a system where every failure tightens the factory: detect, triage, fix, verify, skillify, sync, then retry.

## Software 3.0 / Spec-As-Source Loop

Karpathy's Software 3.0 frame means English becomes a programming surface. The Nous rule is stricter: English becomes source only when it is durable substrate, not chat vapor.

**Operating unit:** `intent -> spec -> validator -> agent lane -> artifact -> skill/gbrain update`.

**Rules:**

1. A prompt is not source until it lands in a durable artifact: `SKILL.md`, spec page, test, script, handoff, or tracked config.
2. Every agent-facing spec names success criteria before implementation starts.
3. Every spec has at least one validator: shell test, health probe, E2E command, screenshot check, or explicit counter-check.
4. Agent output is accepted only when the validator passes or the failure is codified.
5. Repeated natural-language instructions become skills; repeated validation commands become scripts or hooks.

**Default translation:** when Madi states an operating standard, convert it to a spec-as-source unit in the same turn:

| Madi says | Agent creates |
|---|---|
| "Think like the best CTO" | decision loop + Skill update + validator |
| "Do four sessions" | registered four-lane handshake + ownership map |
| "Stop asking tactical questions" | red phrase gate + self-test |
| "Make sure it is really working" | E2E command + counter-check + substrate evidence |

**Musk-step-2 guard:** delete motivational wording, named personas, and new prompt wrappers unless they compile into a validator or a skill rule. The best prompt is often no prompt; the best process is a durable spec plus a test.

## Anti-Patterns

### AP-1 — "Karpathy 6/6" as a vibe (yes-man marker)

**Pattern:** Agent writes *"Karpathy 6/6 sustained"* in a handoff, Telegram message, or session summary without per-axis evidence. The phrase becomes ritual rather than score. The next-session agent inherits a session marked "compounding" that may not have actually compounded.

**Root cause:** Same class as AP-8 (easy-path) — asserting compliance is cheaper than demonstrating it. The agent treats the 6-axis scorecard as a flag to wave rather than a scoring rubric to apply.

**Evidence:** Sessions 51-55 all closed with "6/6" claimed in handoff TL;DRs. Session 55 retrospective audit (this skill's first invocation) found that 4 of those 5 sessions did include per-axis tables in handoff bodies — but the Telegram messages and MEMORY top-blocks often used the phrase without backing. Substrate-side it landed; communication-side it became vibes.

**Fix:**
1. Every "6/6" or "Karpathy compounding" claim MUST be in a context that includes the per-axis table (handoff body) OR a one-line per-axis evidence snippet (Telegram/MEMORY).
2. If you can't cite evidence per axis, write the actual score (e.g., "5/6 — compound chain not cascaded this session, flagged as carryover") not the conventional 6/6.
3. Invoke this skill at session-close BEFORE writing the handoff TL;DR — score first, claim second.

**Detector (mechanical candidate, session-56+):** `tools/test_karpathy_score_cited.sh` — for each `Karpathy 6/6` or `Karpathy compounding` mention in `pages/progress/HANDOFF-*.md`, verify the same file contains a per-axis scorecard table (or a 6-line evidence list). Absent → flag for review.

**Cross-ref:** `session-operating-contract` Rule 4 (4-artifact DONE protocol — same shape: assert with evidence, never just assert); `audit` AP-15 (codification ≠ self-application — applying this skill to its own anti-pattern). No new LESSON (RULE ZERO).

### AP-2 — Hygiene work disguised as value-creation

**Pattern:** Agent ships a sequence of mechanical/cleanup work (test probes, drift detectors, log-rotation, format upgrades) and counts each as a "compounding artifact" in the 6-axis scorecard. Substrate ends the session bloated with hygiene infrastructure but no factory capability creation, no customer-facing improvement, no product shipped.

**Root cause:** Hygiene is easy to ship (mechanical, no novel decisions) and feels productive (visible artifacts). Value-creation is hard (requires Musk-step-2 thinking + capability-frame + customer lens). Agent that hasn't internalized the billion-dollar-solopreneur frame defaults to hygiene because it ships.

**Test:** before claiming "compounding artifact ≥1" on the 6-axis scorecard, classify each artifact as V (value-creation) or H (hygiene) per Rule 14 / AP-8. The session needs at least one V to count as compounding. All-H sessions are maintenance, not progress — name them honestly as such.

**Allowed exception:** if the session was explicitly scoped as a maintenance / drift-fix / audit session, all-H is correct. The frame matters; the work doesn't change.

**Cross-ref:** `session-operating-contract` Rule 14 (sequence value over hygiene); AP-8 (easy-path planning trap); Musk step 4 (accelerate is NOT the same as ship-easy-things-first).

### AP-3 — Skipping multi-virtual-reviewer for plans >2h or >3 subsystems

**Pattern:** Agent estimates a plan as "small enough to skip the multi-reviewer pass." Plan ships. Lands in main. Discovers in execution that the DevEx role would have caught the file-path break, OR the Eng-manager role would have caught the architectural collision, OR the Designer role would have caught the user-mental-model mismatch. Rework happens in main instead of in spec. Cycle time worse than if multi-reviewer pass had run.

**Rule:** any plan estimated >2h of work, OR touching >3 files across different subsystems, OR introducing a new mechanical gate/cron/probe, OR changing user-facing behavior — runs the 4-role pass per the workflow above. Each role argues independently.

**Compounding gate candidate (session-56+):** add a planning-discipline AP that triggers on Plan tool invocation when the plan exceeds the threshold, requiring explicit acknowledgment that 4-role review ran (or an explicit override).

### AP-4 — Scorecard write-negative-first; ANY weak axis means NOT 6/6 (session 60, 2026-04-22)

**Pattern:** Agent self-scores session-close Karpathy scorecard and rounds UP. Every axis gets a ✅ unless evidence is clearly missing. Sessions land as "6/6" when an honest cold read would find 2-3 axes that are weak, superseded, or ornamental. The scorecard becomes a congratulation ritual rather than a measurement.

**Evidence (session 59, 2026-04-22):** Initial session-59 handoff self-scored **6/6** with the framing *"own-bug-caught-mid-loop IS the compound proof."* Madi asked for cold review. On honest re-read:
- **AP absorbed:** pattern-field preservation was a feature observation, not a failure→rule (the real failure = pagination bug, which I deferred to recurrence-gate). Weak.
- **Compounding artifact:** session-57-ext's 4→8 recall shipped to prod WAS the compound; my 14-proposal dogfood was run-3 in a variance-heavy series. Weak — I documented someone else's compound, didn't produce one.
- **Substrate smarter:** my v0.2.1 SKILL edit superseded same-day by parallel-session v0.2.2. Net contribution ~40%. Weak.

Real honest score was **4/6**. The "own-bug-caught" framing specifically was slippery — catching your own pagination bug through paginated re-query is baseline epistemic hygiene, not compound artifact. Musk cold-eye: *"You shouldn't celebrate finding a bug you introduced through sloppiness."*

**Rules (write-negative-first discipline):**

1. **Order of drafting:** for each of the 6 axes, write the ⚠️weak case FIRST. Ask: "what would someone hostile to my contribution say about this axis?" Steel-man the critique. Only after that, write the ✅case if it survives the critique.

2. **Hard gate:** if ANY axis lands ⚠️weak after the write-negative pass, the session is **NOT 6/6**. Write the fractional score (4/6, 5/6) explicitly. Do not defer, do not round up, do not claim "legit 6/6" when any axis is weak.

3. **"N/A" is not an excuse for 6/6.** Session 58 closed "5/6 — AP N/A for clean-ship-after-existing-codification." That framing was honest. Agents who inherit "AP N/A ⇒ effectively 6/6" drift toward ornamental claims — prefer explicit fractional scoring.

4. **Forbidden self-congratulation phrases:** the following ARE AP-1 violators and also signal AP-4 write-positive-first:
   - *"own-bug-caught-mid-loop IS the compound"*
   - *"6/6 legit"*
   - *"Karpathy compounding confirmed"* (without per-axis evidence)
   - *"ratchet turned"* (without naming which rule compounded)

5. **What a real 6/6 session looks like:** (a) an AP actually absorbed from a failure in THIS session (not a feature-observation), (b) the AP codified with full 3-edit ritual + gbrain timeline, (c) a compounding artifact produced BY this session (not inherited), (d) zero rot smuggled (explicit weak-axis naming, explicit open caveats), (e) measurably smarter substrate that survives past the next parallel-session edit, (f) RULE ZERO upheld.

**Detector (mechanical, session-61+ candidate):** `tools/test_karpathy_score_honest.sh` — for each HANDOFF-*.md with a 6-axis table, flag if: (a) any axis is ✅ AND (b) the same handoff body contains phrases from the forbidden list, OR (c) the handoff claims "6/6" OR "legit 6/6" in TL;DR. Not a pass/fail check (soft-warn) — judgment remains human. Sibling to AP-1 detector `test_karpathy_score_cited.sh` (which checks per-axis citation presence); AP-4 detector checks honesty of the citations.

**Cross-ref:** AP-1 (vibe claim → AP-4 is the stricter standard; AP-1 says "cite," AP-4 says "cite honestly, negative-first"); `session-operating-contract` Rule 4 (DONE protocol — same pattern: assert with counter-check, never just assert); new SOC Rule 18 (no-defer-on-textbook-bug, session 60 — applied here to rule the pagination-bug deferral would have been dishonest under AP-4). No new LESSON (RULE ZERO).

### AP-5 — Multi-virtual-reviewer must be Skill-tool-invoked, not mentally simulated (session 64, 2026-04-22)

**Pattern:** Agent reads *"invoke GStack multi-virtual-reviewer (CEO/DevEx/Designer/Eng)"* in this skill's AP-3 / workflow section, understands the intent, and executes by MENTALLY simulating the 4 role POVs in a bullet list ("CEO says X, DevEx says Y, Designer says Z, Eng says W"), then declares the plan "all 4 approve → execute." No actual `Skill(plan-ceo-review)` / `Skill(plan-devex-review)` / `Skill(plan-design-review)` / `Skill(plan-eng-review)` / `Skill(autoplan)` tool invocation happens.

**Root cause (session 64):** v1.0-v1.2 of this skill described the workflow in prose ("invoke") without requiring the mechanical `Skill` tool call. Mental simulation is cheaper (no additional tool turn, no extra latency, no skill-internal prompts to follow), so agents default to it. Result: over 10+ sessions (55-64), ~1 handoff mentions a gstack skill being actually used; zero sessions have `Skill(plan-ceo-review)` tool-call evidence.

**Evidence:** Session-64 itself did multi-reviewer mentally for its own musk-algorithm creation plan. When Madi asked *"do we have gstack from gary tan all implemented and working?"* — audit found: 45 gstack skills available via `Skill` tool, 4 routed in RESOLVER.md (9% coverage), 1 mention across 10 recent handoffs, 0 actual `Skill` tool invocations in session-64's own plan.

**Meta-root-cause:** Step-5-automate-before-Step-3-simplify violation (musk-algorithm AP-1 at meta-layer). We wrote doctrine (Step 3 simplify/optimize) and jumped to "agents will do it" (Step 4 accelerate) without validating by hand first. Handoff `Karpathy 6/6 ✅` claims passed the AP-1 mental-simulation filter but nothing enforced Skill-tool-mechanical-invocation.

**Rules:**

1. **Mental simulation of the 4 roles is HARD-BANNED** for triggering plans (>2h / >3 subsystems / >200 lines added / new doctrine skill / new infra gate / user-facing behavior change).
2. **MUST invoke via `Skill` tool** — `Skill(plan-ceo-review)` + `Skill(plan-devex-review)` + `Skill(plan-design-review)` + `Skill(plan-eng-review)` sequentially, OR `Skill(autoplan)` once (which dispatches all 4 and aggregates).
3. **Handoff evidence required:** for every plan that triggered the multi-reviewer threshold, the handoff body must cite the Skill-tool invocations that ran, not a bulletpoint list of role POVs. Pattern: *"Skill(plan-ceo-review) → <recommendation + what changed>; Skill(plan-devex-review) → <...>; …"*
4. **Below-threshold plans (single-edit, tactical fixes, SOAO drift recoveries)** still don't need multi-reviewer — Rule 15 / AP-9 still applies. This AP narrows to the triggering cases only.
5. **`autoplan` is the default.** Prefer `Skill(autoplan)` for single-invocation of all 4 reviewers. Invoke individual reviewers only when you need just one lens.
6. **Council escalation:** when the triggering plan ALSO has ANY of {IR/retrieval methodology surface, novel cost/latency profile, security/billing-isolation claim, single-ablation evidence basis, architectural lock-in risk}, invoke a 5-advisor Council pass on top of the AP-5 reviewer gate. Council advisors are Pragmatic Implementer, Adversarial Skeptic, Long-term Strategist, Cost/Latency Hawk, and one Domain Expert relevant to the spec. Council output is critique-only; the driving session is the chairman and must synthesize, decide which critiques fold, and write the fold-list. Cross-model dispatch is preferred when routes are live; if a requested model route is unavailable, record the blocker and do not pretend.

**Detector (shipped 2026-05-14, v1.11.0):** `tools/test_multi_reviewer_invoked.sh` scans recent `pages/progress/HANDOFF-*.md` for triggering language (axis #3 / multi-reviewer / >2h / >3 subsystems / >200 lines / new doctrine / new infra gate / user-facing change) and, for each triggering handoff, greps session jsonl files in `~/.claude/projects/...AGaaS/*.jsonl` for `Skill(plan-{ceo,devex,design,eng}-review)` or `Skill(autoplan)` tokens. Missing evidence → exit 1 (AP-5 violation). Supports `--json` and `--since N` (days). Bash 3 compatible. Wiring into `com.nous.light-probe` for 15-min cadence on Air deferred to next ssh-to-Air session; standalone tool is callable now.

**Enforcement amplifier:** RESOLVER.md updated same session to add trigger rows for all major gstack Skills (17 rows covering plan-ceo-review / plan-devex-review / plan-design-review / plan-eng-review / autoplan / codex / investigate / office-hours / retro / ship / land-and-deploy / design-review / qa / cso / make-pdf / review / guard-careful-freeze). Agent intent-resolution now maps user trigger phrases DIRECTLY to `Skill(…)` invocations instead of leaving the 45-skill library orphan-visible.

**Cross-ref:** `musk-algorithm` AP-1 (optimize-before-delete — meta-applied here: we wrote doctrine then skipped to automate without validating), AP-3 (physically-impossible-violated — gstack-not-invoked is a canonical instance), AP-4 (agent-autonomy loop — research + implement, which is what session-64 did upon discovery). SOC Rule 4 (DONE protocol — requires 4-artifact evidence; Skill-tool invocations ARE the evidence for multi-reviewer).

### AP-6 — Billion-dollar-agent standard as speech instead of operating loop

**Pattern:** Agent gives an inspiring answer about Musk, Karpathy, Tan, one-person billion-dollar companies, "new standard," and "evolving agents," but does not convert the answer into a runtime decision loop, skill rule, or mechanical gate. The words feel right in the conversation and disappear by the next session.

**Root cause:** persona gravity. Big names create performance pressure, so the agent shifts into motivational framing instead of operational design. This is the same family as AP-1: claiming alignment is cheaper than proving alignment.

**Rule:** whenever Madi asks for *"best CTO / Elon / Karpathy / Garry Tan / billion-dollar agent company / new standard"* framing, respond with a decision loop and then codify it if Madi says "do it." The loop must include deletion, deterministic-first routing, skillification, proof, and sync. It must not create a new persona prompt.

**Self-test before final answer:** can the next agent execute a different decision because this rule exists? If no, the answer was speech, not substrate.

**Cross-ref:** AP-2 (hygiene disguised as value), AP-4 (write-negative-first), `session-operating-contract` Rule 10 (tiny-team leverage), `musk-algorithm` Step 2 (delete before simplify), `factory-ops` AP-38 (recent example: TCP-open probe deleted in favor of real `/healthz` proof).

No new LESSON (RULE ZERO).

### AP-7 — Top-CTO doctrine without a wiring gate

**Pattern:** the top-CTO loop exists in `session-operating-contract`, `karpathy-loop`, and `RESOLVER.md`, but no deterministic probe verifies that all three surfaces stay connected. A future edit can remove one trigger, rename one row, or drift the Codex `AGENTS.md` shim while every normal parity test stays green.

**Root cause:** documentation was treated as the gate. That is Step-5 drift in disguise: the operating loop was validated by a human reading the files, not by a reusable validator future sessions can run.

**Rule:** every cross-cutting doctrine that claims to be "the new standard" must have a small wiring probe. The probe should check the minimum runtime surfaces: the behavior contract, the doctrine skill, the resolver row, and any session shim that injects the doctrine into a tool family.

**Fix (SHIPPED):** `tools/test_top_cto_loop_wired.sh` verifies SOC Rule 20, this skill's Top-CTO loop, Software 3.0/spec-as-source loop, `session-coordination` four-session handshake, `_gbrain/RESOLVER.md` routing rows, and the Codex `AGENTS.md` shim. SOAO now runs it as a structural probe.

**Cross-ref:** AP-6 (speech vs operating loop), `session-operating-contract` Rule 20 (tiny-team action packets), `session-architecture` (1+3+dispatch instead of shared-writer chaos), `musk-algorithm` Step 5 (automate last, after validating the rule by hand).

No new LESSON (RULE ZERO).

### AP-8 — Substrate-evolution sessions must Musk-step-2 the plan's premises, not just task execution (session 82c, 2026-04-29)

**Pattern:** Sessions 81 + 82 dutifully optimized substrate-S0 (gbrain v0.10.1 → v0.22 upgrade) execution — wrote dryrun harness, codified AP-43..47, ran β workaround empirically — without ever asking *whether S0 belonged on the critical path.* Session 82c measured Mercury Phase 2 metrics live and discovered: v0.10.1 brain is already at 99% embedding coverage, brain_score 80/100, hybrid retrieval mostly already present. Meanwhile MEMORY.md is **18,192 tokens** loaded into every session-start — Mercury Phase 2 reduces that by **91.8%** (1,494 tokens, 51 facts). **The leverage was the unobserved one.** S0 was a *want* dressed as a *constraint*; Mercury Phase 2 was the actual constraint.

**Root cause:** when a multi-phase plan goes through plan-eng-review, reviewers focus on *whether each phase ships safely*, not on *whether each phase ships at all*. Musk step 2 ("delete the requirement") was applied to dryrun script options but never to the upgrade itself. This is "optimizing a thing that shouldn't exist" — the most expensive class of work.

**Rule:** for any session whose work touches durable substrate (skills, doctrine, infra, retrieval), the session MUST run an explicit Musk-step-2 pass on the *plan's premises*, not just on individual tasks within the plan. Concretely, before executing phase N: state the constraint phase N solves, name a measurable agent-capability gap that disappears when phase N ships, and check whether that gap is currently empirically painful or hypothetically painful. If hypothetical → defer phase N until concrete pain surfaces.

**Detection (mechanical):** plan v2 documents must have a `## Why this is on the critical path` section per phase, with at least one measured metric showing current pain (token count, p95 latency, error rate, missed-retrieval count). Plans that lack this section fail the gate. Tool detector candidate: `tools/test_plan_critical_path_justified.sh` greps phase headings for the "Why" section + at least one numeric metric.

**Empirical reference:** Mercury Phase 2 shadow #1 metrics, 2026-04-29 13:54 KZT — `pages/mercury/shadow-runs/shadow-1-2026-04-29-session-82c.txt`. Full MEMORY 18,192 tokens → Mercury 1,494 tokens = 91.8% reduction = the constraint that survived step-2.

**Cross-ref:** `musk-algorithm` Step 2 (delete the requirement), `session-operating-contract` Rule 8 (failure → skill — extended: weak-justification → defer), this skill AP-2 (hygiene-disguised-as-value), `session-coordination` AP-12 (4-lane writer parallelism — only worth spinning up when the plan's premises survive step-2).

**Why no new LESSON file:** RULE ZERO. Empirical evidence in [[HANDOFF-AUTO-2026-04-29-session-82-substrate-S0-beta-insufficient]] + Phase 2 shadow #1 metrics file.

### AP-9 — Same-prompt loop saturation: evergreen prompt fired N times = the prompt is the bug (session 82j, 2026-04-29)

**Pattern:** Madi's evergreen "best-CTO / Musk / Karpathy / Garry-Tan / billion-dollar-solopreneur — audit, do real research, 4 sessions, spam agents" prompt fired 8+ consecutive times across sessions 82e/f/g/h/i/j. Each round: re-acquire Stream-A, dispatch parallel Agent lanes, find a real bug or ship a real fix, codify, commit, push. Rounds 1-5 produced strict compounding (AP-8/12/13/14, Mercury Phase 2/3, mercury-refresh cron, auto-recovery). By round 8, marginal leverage was approaching zero — the substrate was already self-healing, cron-protected, cross-host green, factory production-green. Optimizing what's optimized = `karpathy-loop` AP-2 (hygiene-disguised-as-value) at meta-loop scale.

**Root cause:** evergreen prompts that worked early stop working late. Same input, different substrate state. The first 5 rounds had real drift to fix; rounds 6+ would be hygiene churn. The agent's job is not to mechanically re-execute the same harness — it's to detect when the harness has saturated and **redirect** to the highest-pending evidence gap.

**Rule:** when an evergreen prompt fires N≥3 times in one logical sitting and recent rounds shipped only ops polish (no new doctrine, no new bug-fix), STOP the loop pattern and ask: "what is the most evidence-deferred carryover I can close right now that prior rounds did NOT close?" Then close it. Common candidates:
- Real-traffic E2E test that's been "deferred to next session" for ≥2 sessions (this is what s82j did — fired the actual `/ask` curl through LiteLLM → DeepSeek-Flash → got `E2E_S82J_OK` back, closing memory's 4-session-old "Telegram /code E2E was not fired" gap)
- Multi-virtual-reviewer pass on the cumulative substrate change (when N rounds have shipped without one)
- Honest scorecard against the original problem statement, not against the prior round's progress

**Detection (mechanical):** count `--shadow` runs / `mercury_phase3_regen.sh` invocations / `git push` commits / Agent-tool dispatches per session. When a single session has ≥4 of any single category WITHOUT a new AP from Madi-supplied direction, the loop has saturated. Tool detector candidate: `tools/test_loop_saturation.sh` greps last-N-handoffs for the same evergreen-prompt fingerprint and flags ≥3 recurrences.

**Empirical reference (s82j live, 2026-04-29):** real-traffic E2E test fired through LiteLLM → DeepSeek-v4-Flash → received content `"E2E_S82J_OK"` verbatim, finish_reason=stop, tokens 17in/20out/37total, model=deepseek-v4-flash. Closed standing memory carryover "Telegram /code E2E was not fired from the phone in this lane" (carried sessions 81→82e→82f→82g→82h→82i — 6 rounds without firing).

**Cross-ref:** AP-2 (hygiene-disguised-as-value — same anti-pattern at task-level), AP-8 (Musk-step-2 the plan's premises — same anti-pattern at plan-level), `musk-algorithm` Step 1 (question the requirement — applies to evergreen prompts too).

**Why no new LESSON file:** RULE ZERO. AP-9 ships next to AP-2 / AP-8 as the meta-saturation closer.

### AP-10 — Subagent lane reports go stale within minutes; verify drift claims against current state before acting (session 82k, 2026-04-29)

**Pattern:** s82k spammed 5 parallel `Agent` lanes (X/Y/Z/AA/BB) for atomic Obsidian↔gbrain parity. Two of five returned drift findings that were either stale-by-30-seconds or fully hallucinated:
- **Lane AA** claimed "merge conflict on main, 1 commit ahead of vps/main, MEMORY.md added/deleted conflict, .obsidian/workspace.json conflict." Driver verified: `git status` showed clean rebase, branch up-to-date with vps/main, no unmerged files (`git ls-files -u` empty), no `.obsidian/workspace.json` modification. **Hallucinated entirely.**
- **Lane Z** claimed "session-coordination Mac↔Air MD5 drift (Mac `19a14ad9`, Air `2baaa1a1`)." Driver verified: 4-target MD5 (Mac vault, Air wiki, Air runtime, OpenClaw container) all returned `2baaa1a1cf19136d1ee5431b45e5015c`, version `1.18.1`. **Lane Z's snapshot was taken before auto-sync had pulled peer's v1.18.1 onto Mac (~30s later).**

Both findings would have caused real damage if acted on without verification: Lane AA's "merge conflict" would trigger a destructive `git checkout` or stash drop; Lane Z's "drift" would trigger an unnecessary rsync/scp that could clobber peer's correct content.

**Root cause:** subagent lanes capture state at time T, return after ~30-180s. Substrate is moving fast (auto-sync 60s cadence, peer commits, MD5 churn). By the time the lane reports, T is in the past and the "drift" has often converged. Hallucinations are a separate class — the lane misread `git status` output or fabricated structure that wasn't there.

**Rule:** treat all subagent lane drift claims as **hypotheses to verify**, not facts to act on. Specifically:
1. Before any `git stash`, `git checkout`, `rm`, `scp`, or `mv` triggered by a lane finding, the driver MUST re-run the same probe locally and confirm the drift still exists.
2. For numeric/timestamp claims (MD5, line counts, mtime), re-capture in the driver session and diff.
3. For structural claims ("merge conflict", "broken symlink", "missing file"), inspect with `ls -la`, `git status`, `cat`, etc. before believing.
4. For any lane that returns ≥1 hallucination per session, flag the lane class for retry (general-purpose research vs Explore vs domain-specific) — not all subagent types are equal at structural inspection.

**Detection (mechanical):** the driver session can dogfood by re-running 1 probe per lane finding before the integration commit. Tool detector candidate: `tools/test_lane_finding_verification.sh` — for the last N session handoffs, count how many "Lane X claims Y" findings were later refuted by the driver. >20% refute rate = retire that lane class.

**Cross-ref:** AP-9 (loop saturation — same wisdom at meta-level: don't act on stale signals), AP-2 (hygiene-disguised-as-value — fixing fake drift IS hygiene), `session-coordination` AP-12 (subagent research lanes are not write capacity — extends naturally: subagent research lanes are also not source-of-truth for current state).

**Why no new LESSON file:** RULE ZERO. Empirical evidence: s82k Lane AA + Lane Z findings refuted by driver in <2 min via direct `git status` + `md5 -q` checks.

### AP-11 — "Skills are the prompts" as a slogan instead of a runtime gate (session 108, 2026-05-11)

**Pattern:** Agent agrees with Garry Tan's framing ("skills are the prompts"), Skillify, Karpathy, Musk, and GStack in chat, but leaves the actual runtime unchanged. The next session still needs Madi to paste the same operating paragraph.

**Root cause:** The slogan was treated as inspiration rather than an interface contract. In Nous, a phrase only becomes source when it lands in a versioned skill, validator, plan, audit, or gbrain timeline.

**Rule:** When Madi forwards durable operating doctrine, run the following gate before final answer:
1. **Delete:** do not create a new god prompt or bloated `AGENTS.md` block if an owner skill exists.
2. **Skillify:** update the smallest owner skill(s) with compact AP/rule entries.
3. **Verify:** run skill version/YAML/pointer checks.
4. **Sync:** push to wiki, gbrain timeline, Air runtime, and OpenClaw mounted skills.
5. **Retrieve:** prove gbrain/OpenClaw can read the new rule by query or grep.

**Test:** The final answer must cite the exact owner skills and at least one retrieval proof. If it only says "we should use skills," AP-11 failed.

**Cross-ref:** `mistake-to-skill` AP-14 (repeated prompt loop means missing skill), `karpathy-coding-principles` v1.1.0 (May-2026 12-rule extension), `gbrain-ops` AP-33 (CLI fallback for timeline if MCP unavailable), `session-operating-contract` DONE protocol.

**Why no new LESSON file:** RULE ZERO. Source captured in `pages/sources/user-forwarded/skills-are-the-prompts-2026-05-11.md`; runtime rule lives here.

### AP-12 — Skipping the adversarial/domain Council pass on specs with IR, cost, security, single-ablation, or lock-in risk (session 108, 2026-05-14)

**Pattern:** A plan triggers AP-5, the standard reviewers run, and the spec looks well-folded, but the plan still carries high-severity blind spots in classes the AP-5 reviewer set does not cover by design: adversarial premise attack, cost arithmetic, call-graph projection, IR/retrieval methodology, eval-design statistical power, prompt-injection, billing isolation, or architectural lock-in.

**Root cause:** AP-5 reviewers are product-team perspectives. They ask how to scope, implement, design, and sequence a plausible plan. They do not reliably ask "what is the strongest case that this premise is false?" or "is the eval/cost/security math actually meaningful?" A plan can therefore pass AP-5 and still be wrong at the premise layer.

**Evidence:** [[AUDIT-llm-council-vs-karpathy-loop-eval-2026-05-14]] compared AP-5 against a 5-advisor Council on the same retrieval-shim spec. AP-5 produced useful folded additions; the Council surfaced additional P0/P1 issues in exactly the missing classes. Session 2026-05-14 also ran a live cross-model check ([[AUDIT-live-cross-model-council-karpathy-clean-worktree-2026-05-14]]) using Grok, Opus, Gemini 2.5 Pro, and GPT-5.5; the majority verdict was to adopt Council escalation narrowly, reject always-on council ceremony, and preserve peer-lane file ownership.

**Rules:**

1. **Council pass is required when BOTH conditions hold:** AP-5 is triggered AND the plan has any of these five surfaces: IR/retrieval methodology, novel cost/latency profile, security/billing-isolation claim, single-ablation evidence basis, or architectural lock-in/coupling-creep risk.
2. **Council is not AP-5 replacement.** AP-5 remains the default fold-list mechanism. Council adds adversarial/domain critique only for the five high-risk surfaces.
3. **Mental simulation is hard-banned.** Use real callable routes or actual parallel agent dispatch. If a named model is unavailable, mark that lane blocked. Do not write "Gemini/Grok/Claude said" unless that route was actually called.
4. **Chairman synthesis is mandatory.** A pile of advisor bullets is not a decision. The driving session must state the majority, rejected minority views, what gets deleted, what gets executed now, and what remains residual.
5. **Best part is no part.** Do not invoke Council for routine implementation, already-proven paths, documentation cleanup, or one-edit tactical fixes. Always delete performative ceremony before adding a process.

**Detector (queued):** `tools/test_council_pass_invoked.sh`, sibling to `tools/test_multi_reviewer_invoked.sh`. Candidate behavior: scan recent handoffs for AP-12 predicates and require evidence of actual advisor dispatches plus chairman synthesis. Defer detector implementation until the rule is exercised on at least one more production spec, so the detector encodes reality rather than premature ceremony.

**Cross-ref:** AP-5 (Skill-tool-invoked multi-reviewer), AP-10 (lane reports are hypotheses until verified), `musk-algorithm` Step 2 (delete process where AP-5 alone suffices), `session-coordination` AP-5 (path-scoped commits under parallel lanes). No new LESSON (RULE ZERO).

## Rules absorbed

- **RULE ZERO** (project `CLAUDE.md`, session 35, 2026-04-16): no new LESSON files; SKILL.md + gbrain timeline. THIS skill is the formalized "why."
- **LAW-001** (Evolution), **LAW-009** (Self-Evolution), **LAW-015** (Root-Cause Evolution), **LAW-017** (Success Is Skill).
- **AMD-005** (Skill-First Evolution — 7-day absorption SLA).
- **AMD-006** (Auto-memory as session-continuity substrate).
- **`mistake-to-skill` AP-11** (3-edit ritual — invoked by every skill bump this loop generates).
- **`mistake-to-skill` AP-10** (gstack v0.18.0.0 — Confusion Protocol; ASK at ambiguous absorption forks).
- **`session-operating-contract` Rule 4** (4-artifact DONE protocol — the evidence shape this skill scores).
- **`session-operating-contract` Rule 6** (failure → skill update — the loop's mid-execution form).
- **`session-operating-contract` Rule 9** (Musk 5-step — the second leg of this loop).
- **`session-operating-contract` Rule 14 + AP-8** (value-creation sequencing — fed into AP-2 here).
- **`session-operating-contract` Rule 15 + AP-9** (execute-don't-ask tactical decisions — informs the multi-reviewer "when NOT to use" list).
- **`audit` AP-15** (codification ≠ self-application — every loop invocation cross-checks same-session edits).
- **`gbrain-ops` AP-33** (MCP disconnect → CLI fallback — invoked when timeline-axis (#2) needs the fallback).
- **GStack thinking skills** (referenced in `_gbrain/RESOLVER.md`: office-hours, ceo-review, investigate, retro). The multi-virtual-reviewer workflow above is an explicit invocation of ceo-review (this skill) + investigate (debug skill) + office-hours (brainstorm).

## Evidence trail

- **2026-05-14** | v1.11.0 -> v1.12.0 — Absorbed **AP-12** + AP-5 Rule 6. Empirical basis: [[AUDIT-llm-council-vs-karpathy-loop-eval-2026-05-14]] and live cross-model check [[AUDIT-live-cross-model-council-karpathy-clean-worktree-2026-05-14]]. Decision: Council complements AP-5 only for five high-risk surfaces (IR/retrieval, novel cost/latency, security/billing isolation, single-ablation evidence, lock-in). Musk step-2 deletion: no always-on Council for routine work; AP-5 remains default. gbrain timeline pushed. No new LESSON (RULE ZERO).
- **2026-05-11** | v1.10.0 — Added AP-11 after Madi forwarded Garry Tan's "skills are the prompts" framing, Skillify workflow, Karpathy 12-rule extension, and CodeWiki note. Root cause: the substrate already had "thin harness, fat skills," but the newest doctrine could still remain a chat slogan unless the closeout gate forced skill update + gbrain timeline + runtime/OpenClaw retrieval proof. Cross-ref `mistake-to-skill` AP-14 and `karpathy-coding-principles` v1.1.0. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.8.0 -> v1.9.0 — Session 82k absorbed **AP-10** after 2 of 5 spammed audit lanes (AA + Z) returned drift findings refuted by driver in <2min: Lane AA hallucinated a non-existent "merge conflict" (`git ls-files -u` empty, branch clean); Lane Z's MD5 drift claim was stale-by-30s (auto-sync had already pulled peer's v1.18.1 to Mac, all 4 targets actually byte-identical at MD5 `2baaa1a1`). Codifies: subagent lanes are hypotheses, not source-of-truth; verify drift claims via direct probe before any destructive action. Cross-ref `session-coordination` AP-12 (subagent research ≠ write capacity, extended: ≠ truth either). gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.7.0 -> v1.8.0 — Session 82j absorbed **AP-9** after Madi's evergreen "best-CTO/Musk/Karpathy/Tan/billion-dollar-solopreneur — audit, real research, 4 sessions, spam agents" prompt fired 8 consecutive times across 82e/f/g/h/i/j. Rounds 1-5 produced strict compounding (AP-8/12/13/14, Mercury Phase 2/3, mercury-refresh cron, auto-recovery). Round 8 leverage approaching zero — substrate already self-healing + cron-protected + cross-host green + factory production-green. AP-9 codifies: when an evergreen prompt fires N≥3 times in one sitting and recent rounds shipped only ops polish, stop and close the highest-pending evidence gap instead. Empirical reference: s82j fired real-traffic E2E test through LiteLLM → DeepSeek-v4-Flash → received `"E2E_S82J_OK"` verbatim (finish_reason=stop, tokens 17/20/37), closing 4-session-old memory carryover "Telegram /code E2E was not fired from the phone in this lane." gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.6.1 -> v1.7.0 — Session 82c Mercury/Musk-step-2 audit added AP-8: substrate-evolution sessions must justify each plan phase as critical-path with measured pain before optimizing it. Mercury Phase 2 shadow #1 provided the concrete reference: full MEMORY 18,192 tokens → Mercury 1,494 tokens (91.8% reduction), while the gbrain upgrade path was not yet the live constraint. No new LESSON.

- **2026-04-29** | v1.6.0 -> v1.6.1 — Session 82 continuation after Madi asked why the loop stopped. Follow-up audit found the structural top-CTO probe still guarded only the older SOC/Karpathy/RESOLVER surfaces; it did not assert the newly named Software 3.0/spec-as-source loop or `session-coordination` four-session handshake. Extended `tools/test_top_cto_loop_wired.sh` and SOAO's probe label to cover both. `musk-step-2:` deleted the option for a second probe; one structural gate should protect the whole top-CTO doctrine surface. gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-04-29** | v1.5.0 -> v1.6.0 — Session 82 four-lane top-CTO continuation. Lane-4 audit found Software 3.0/spec-as-source was adjacent in doctrine but not named as a first-class operating rule. Added **Software 3.0 / Spec-As-Source Loop**: `intent -> spec -> validator -> agent lane -> artifact -> skill/gbrain update`. `musk-step-2:` deleted the option to create a new standalone "Software 3.0" skill; extended this existing meta-skill because karpathy-loop owns the operating-system layer. External research cross-check: YC AI Startup School 2025 centered the same speakers Madi named (Musk, Altman, Karpathy, Garry Tan as host), and current Software 3.0 discussion stresses that natural language needs structure, simulation, and continuous testing to become behavior. gbrain timeline pushed `{status: ok}`. No new LESSON.

- **2026-05-14** | v1.10.0 -> v1.11.0 — Shipped `tools/test_multi_reviewer_invoked.sh` per [[MADI-DECISIONS-2026-05-14-round2]] item #4 + session s1729 "do it" autonomy. Mechanical AP-5 enforcement: scans recent HANDOFFs for triggering language, greps session jsonl for `Skill(plan-*-review|autoplan)` evidence, exits 1 on missing. Bash 3 compatible (POSIX while-loop array fill, no `mapfile`). Self-test on today's 5 handoffs: 0 triggering, 0 violations, exit 0. Updated AP-5 doctrine row to remove "(queued session-65+)" qualifier — detector is live. Wiring into `com.nous.light-probe` deferred to next ssh-to-Air session; standalone tool is callable now. No new LESSON.

- **2026-04-29** | v1.4.0 -> v1.5.0 — Four-lane top-CTO implementation audit found the doctrine was present and resolver-reachable but not mechanically guarded. Added **AP-7** and shipped `tools/test_top_cto_loop_wired.sh`; SOAO now checks that SOC Rule 20, the karpathy-loop Top-CTO loop, `_gbrain/RESOLVER.md`, and the Codex `AGENTS.md` shim stay connected. This turns the "best CTO / Musk / Karpathy / Garry Tan" standard from prose into a regression gate. No new LESSON.

- **2026-04-29** | v1.3.1 -> v1.4.0 — Madi asked to make the best-CTO / Musk / Karpathy / Garry Tan / billion-dollar-agent-company standard the new operating baseline. Added the **Top-CTO decision loop** ("thin harness, fat skills, deterministic gates, ruthless deletion, one substrate") plus **AP-6** to ban motivational CTO speech that does not become runtime doctrine. The loop turns the standard into 10 ordered questions and default choices for skillification, deterministic jobs, proof, agent ownership, and sync. gbrain-timeline-ok: pages/skills/karpathy-loop/skill. No new LESSON.
- **2026-04-29** | v1.3.0 → v1.3.1 — Session 79 Mac Codex substrate audit corrected axis #6 evidence shape after `mistake-to-skill` AP-13. The scorecard still told agents to expect 129 lesson files, but Apr 25 migration commits deleted historical LESSON receipts and the live invariant is no new `LESSON-NNN` files plus ceiling `<=129`. Axis #6 now verifies highest ID, added paths, and current count without hard-coding 129 as an expected filesystem count. No new LESSON.
- **2026-04-22** | v1.2.0 → v1.3.0 — Session 64 extension (Madi-directed post-handoff-blocked: *"before handoff, do we have the gstack from gary tan all implemented and working?"* → honest audit answer = NO, partial only → Madi: *"all ! wtf why did it happen? all that went to shit... find root cause, fix it, try again. if worked great that is a new skill, save that. must be using obsidian and gbrain and karpathy so all are evolving and all sharing the skills."*). Absorbed **AP-5**: multi-virtual-reviewer MUST be `Skill`-tool-invoked, not mentally simulated. Root cause traced to 3 layers (prose-doctrine-not-requiring-Skill-call + RESOLVER-only-routing-4-of-45-gstack-skills + no-detector-flagging-mental-simulation), with meta-root = Step-5-automate-before-Step-3-simplify (musk-algorithm AP-1 at meta-layer). RESOLVER.md expanded same-session: 4 gstack rows → 17 rows covering plan-ceo-review / plan-devex-review / plan-design-review / plan-eng-review / autoplan / codex / investigate / office-hours / retro / ship / land-and-deploy / design-review / qa / cso / make-pdf / review / guard-careful-freeze. Detector `tools/test_multi_reviewer_invoked.sh` queued session-65+ (scans handoffs for Skill-tool-call evidence matching claimed multi-reviewer passes). No new LESSON (RULE ZERO). gbrain timeline pushed same-session.
- **2026-04-22** | v1.1.0 → v1.2.0 — Session 64 (Mac-interactive, Madi-directed: *"The+Book+of+Elon+Free+PDF.md — go over this all of it... physically impossible not to be working like that. so we are like elon musk company"*). Cross-linked new [[musk-algorithm]] v1.0.0 as the canonical engineering-doctrine reference. Previously the Musk 5-step section in this skill had a 5-bullet restatement + workflow integration but no full doctrine. New musk-algorithm skill holds the full doctrine (Idiot Index, Magic-Wand-Number, Thinking-in-Limits, Factory-is-Product, Attack-the-Constraint, Named-Person-Requirements, 10%-add-back rule, Bad-News-Loud, Ban-Acronyms, Close-the-RL-Loop, 69 Core Musk Methods reference) + 3 APs (optimize-before-delete, unsigned-requirement, physically-impossible-violated) + mechanical enforcement (`tools/test_musk_step_2.sh`). This skill stays lean: scorecard + multi-reviewer + compound-chain. No new LESSON (RULE ZERO). gbrain timeline pushed same-session.
- **2026-04-22** | v1.0.0 → v1.1.0 — Session 60 (deep-audit extension of session 59, Madi-directed: *"review the handoff... whether I'm being too generous with Karpathy 6/6"*). Absorbed **AP-4** (scorecard write-negative-first + ANY-weak-axis ⇒ NOT 6/6). Session 59 evidence: self-scored 6/6 via "own-bug-caught-mid-loop IS the compound" framing; honest cold re-read downgraded to 4/6 (3 axes weak: AP-absorbed = feature-obs-not-failure-rule; compound = inherited-not-produced; substrate = superseded-same-day). Fix codifies: draft ⚠️weak case first per axis; forbidden self-congratulation phrases list; detector sibling `tools/test_karpathy_score_honest.sh` queued. Cross-ref new SOC Rule 18 (no-defer-on-textbook-bug — session 60 companion rule). No new LESSON (RULE ZERO).
- **2026-04-21** | v1.0.0 — Created session 55 extension (Mac-interactive, 2026-04-20→2026-04-21 day-boundary). Trigger: Madi asked *"do we have the karpathy loop?"* — substrate audit found mechanics scattered across CLAUDE.md (RULE ZERO + Tan/Karpathy/Finn pattern), `mistake-to-skill` (AP-11 3-edit ritual + AP-10 gstack), `session-operating-contract` (Rules 4/6/9/14/15 + AP-8/9 + 6-axis cited but not defined), `audit` (AP-15 self-application), `gbrain-ops` (AP-33 MCP fallback) — no unifying skill. Madi pushed back: *"wtf? we must have it. when you claim or I ask, think and do it"* + *"I need to have top tier ceo with me — you. not just saying yes to all."* Created this skill as the canonical doctrine: 6-axis scorecard formal definition + compound-chain cross-layer pattern + Tan/Karpathy/Finn formalized + Musk 5-step restated + Madi's GStack multi-virtual-reviewer planning workflow + billion-dollar-solopreneur 4-question framing. Three Anti-Patterns absorbed at creation: AP-1 (vibe-only "6/6" claim), AP-2 (hygiene-disguised-as-value), AP-3 (skipping multi-reviewer on >2h / >3-subsystem plans). Will be cross-referenced from project + vault `CLAUDE.md` and from `_gbrain/RESOLVER.md` in the same session-55-extension commit. Karpathy compounding: every future agent that reads project CLAUDE.md or any of the 7 cross-referenced skills picks up the formalized loop instead of inheriting the convention. No new LESSON (RULE ZERO).

## See also

- [[session-operating-contract]] — runtime contract; this skill formalizes the doctrine SOC's rules implement
- [[mistake-to-skill]] — AP-11 3-edit ritual + AP-10 GStack Confusion Protocol; the absorption mechanism this loop uses
- [[audit]] — AP-15 codification ≠ self-application + AP-17/18 SOAO; the verification mechanism this loop uses
- [[infrastructure]] — AP-43 pre-commit RULE 4 mechanical enforcement of AP-11 / RULE ZERO
- [[gbrain-ops]] — AP-33 MCP disconnect CLI fallback (the timeline-push axis); BRAIN-AWARE-INVOCATION pattern
- [[factory-ops]] — AP-25 (openclaw config CLI) + AP-26 (LiteLLM cost alarm) — both shipped via this loop in session 55
- [[planning-discipline]] — brainstorm → spec → plan → implementation; the multi-virtual-reviewer workflow extends this
- [[LAW-001-evolution]]
- [[LAW-009-self-evolution]]
- [[LAW-015-root-cause-evolution]]
- [[LAW-017-success-is-skill]]
- [[AMENDMENT-005-skill-first-evolution]]
- [[AMENDMENT-006-auto-memory-session-continuity-substrate]]
