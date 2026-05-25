---
tier: 1
type: skill
name: karpathy-coding-principles
id: SKILL-KARPATHY-CODING-PRINCIPLES
version: 1.2.0
last_updated: 2026-05-19
status: active
description: "The 4 coding-behavior principles from Andrej Karpathy's critique of LLM coding tools, codified by Forrest Chang into a single CLAUDE.md file (44k+ GitHub stars in 7 days). Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution. Addresses the specific behaviors Karpathy called out: wrong assumptions without checking, overcomplicated code, unrelated edits as side effects, loose success criteria. Complementary to karpathy-loop (meta-scorecard + compounding) — this is the code-behavior layer. Read BEFORE any code-editing task. v1.2.0 adds the ship+learn gate: factory agents must leave proof and explanation, not just close tasks."
triggers:
  - about to edit code
  - about to write code
  - about to refactor
  - user asks to "fix", "add", "implement", "build"
  - multi-step task on code
  - about to commit
  - user feedback about scope-creep or overcomplication
tools: [Read, Edit, Write, Bash]
mutating: false
absorbs_sources:
  - "https://github.com/forrestchang/andrej-karpathy-skills"
  - "Andrej Karpathy 2026 post on LLM coding pitfalls (source for the 4 principles)"
related: [karpathy-loop, agent-quality, evidence-verification, session-operating-contract, mistake-to-skill, planning-discipline]
tags: [skill, coding-behavior, karpathy, forrestchang, 4-principles, claude-code, think-simplicity-surgical-goals, 2026-04-21]
title: "karpathy-coding-principles v1.2.0"
---

# karpathy-coding-principles v1.2.0

## Purpose

Runtime behavior rules for LLM agents writing or editing code. Direct absorption of [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) — a single `CLAUDE.md` file that rewires Claude Code behavior based on Karpathy's honest critique of AI coding tools.

**Why this is a separate skill from `karpathy-loop`:** `karpathy-loop` is **meta-doctrine** (6-axis session-close scorecard + multi-virtual-reviewer + Tan/Karpathy/Finn compounding pattern). This skill is **code-behavior** — specific rules for what to do and not do when editing a file. Orthogonal. Both should be active.

Complementary with `agent-quality` (runtime truthfulness — don't lie about work done) + `evidence-verification` (don't claim without proof) + `session-operating-contract` (session-start ritual + DONE protocol). These four together form Nous's full runtime behavioral contract for code work.

## The 4 principles (verbatim from Forrest Chang / Karpathy)

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: *"Would a senior engineer say this is overcomplicated?"* If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: *every changed line should trace directly to the user's request.*

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- *"Add validation"* → *"Write tests for invalid inputs, then make them pass"*
- *"Fix the bug"* → *"Write a test that reproduces it, then make it pass"*
- *"Refactor X"* → *"Ensure tests pass before and after"*

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## May-2026 extension: 12-rule operating layer

Madi forwarded the May-2026 extension to the original Karpathy/Forrest 4-rule baseline after OpenBrain/Claude/Codex multi-session audits exposed newer failure modes: stale lanes, hook cascades, silent success, weak tests, and long-running task drift. Keep the original 4 rules as the floor; apply these eight as the agent-orchestration layer.

| # | Rule | Nous interpretation |
|---|---|---|
| 5 | Use the model only for judgment calls | Use LLMs for classification, drafting, summarization, extraction, and tradeoff judgment. Do not use LLMs for routing, retries, status-code handling, or deterministic transforms. If code can answer, code answers. |
| 6 | Token budgets are not advisory | Long loops need explicit checkpoints and a handoff/resume path. If context is saturating, summarize current truth and continue from substrate instead of pushing through confused context. |
| 7 | Surface conflicts; do not average them | When repo patterns contradict, choose the more recent or more tested pattern, explain why, and flag the other for cleanup. Never blend two incompatible conventions. |
| 8 | Read before writing | Before adding code, read the file exports, immediate caller, and obvious shared utilities. Duplicating adjacent code because it was not read is a failure. |
| 9 | Tests verify intent, not just behavior | A passing test is insufficient if it would not fail on the real business-rule regression. Encode why behavior matters, not only what value is returned. |
| 10 | Checkpoint after every significant step | After each meaningful step, state what changed, what was verified, and what remains. Do not continue from a state you cannot describe back. |
| 11 | Match codebase conventions | Conformance beats taste inside an existing codebase. If a convention is harmful, surface it separately; do not silently fork style or architecture. |
| 12 | Fail loud | "Done" is false if anything important was skipped, hidden, or unverified. Surface uncertainty and skipped checks explicitly. |

**Compression rule:** do not paste long article text into `AGENTS.md` or every `SKILL.md`. The durable form is compact rules here, plus exact source capture in `pages/sources/user-forwarded/skills-are-the-prompts-2026-05-11.md`.

## Ship + Learn Gate

For factory code and operator automation, success has two metrics:

- `shipped`: the concrete code path, runner, digest, queue, proof file, or task update exists and was verified by command.
- `learned`: the agent records why the change works, what it deletes/replaces, what could still break, and which test/proof would catch a regression.

Agents must not trade comprehension for speed on core substrate changes. For multi-subsystem work, write the Spec-Kit-style `/specify` artifact first, then implement the smallest verifiable slice. For Satory-facing automation, explanation must be operator-simple: status, blocker, next action, owner, proof. Internal model/router bookkeeping stays in audit files unless the operator asked for it.

## How to know it's working

Three observable signals (from Forrest's README):
1. **Diffs are cleaner.** Only what was asked shows up. No reformatted functions. No renamed variables. No improved comments that weren't requested.
2. **Clarifying questions come BEFORE implementation.** Agent stops guessing. Less time throwing away wrong work.
3. **Code is simpler the first time.** No rewrites because of overengineered solutions. No abstractions nobody asked for.

**The tradeoff (stated explicitly):** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## Cross-refs to our doctrine

- `karpathy-loop` v1.0.0 — meta-scorecard layer (6-axis, multi-reviewer, compounding). This skill is the code-behavior layer.
- `agent-quality` — don't-lie-about-work discipline (DONE artifact). Complementary.
- `evidence-verification` — prove before claim. Complementary.
- `session-operating-contract` Rule 4 (Plan → Execute → Verify with 4-artifact DONE) — sibling at session-lifecycle layer.
- `session-operating-contract` Rule 15 (execute tactical decisions; escalate only scope/destructive/true-ambiguity) — EXTREMELY close sibling; they can pair-conflict on "Think Before Coding / Ask" vs "don't re-ask at phase boundaries". The resolution: **Principle 1 applies when assumptions are not yet surfaced**; **Rule 15 applies once assumptions have been stated and user has approved**. No conflict in steady state.
- `planning-discipline` — brainstorm → spec → plan → implementation. Principle 4 maps to the implementation phase's goal-driven loop.

## Deployment (honest state)

Installed 2026-04-21 session-56 across the full surface:

| Surface | Path | Status |
|---|---|---|
| Factory runtime (Air via wiki-to-runtime-rsync) | `~/nous-agaas/skills/karpathy-coding-principles/SKILL.md` | ✅ next wiki-rsync cycle |
| Mac Claude Code (this tool, next session) | `~/.claude/skills/karpathy-coding-principles/SKILL.md` | ✅ auto-discovers at next session start |
| Air Claude Code (`/code` spawned sessions) | `~/.claude/skills/karpathy-coding-principles/SKILL.md` on Air | ✅ next session spawn |
| Vault root CLAUDE.md pointer | `Nous/CLAUDE.md` top block | ✅ |
| Mac-root CLAUDE.md merge | `/Users/madia/Documents/Projects/Nous AGaaS/CLAUDE.md` | ✅ 4 principles appended under Runtime behavioral contract section |
| Source-of-truth archive | `pages/concepts/forrestchang-karpathy-claudemd-source-2026-04-21/CLAUDE.md` | ✅ verbatim upstream file preserved |
| Official plugin via Claude Code CLI | `/plugin marketplace add forrestchang/andrej-karpathy-skills` + `/plugin install andrej-karpathy-skills@karpathy-skills` | ⏳ user-run (not Claude-invokable; documented in CLAUDE.md for Madi to type) |

## Evidence trail

- **2026-05-19** | v1.1.0 -> v1.2.0 — Added the Ship + Learn Gate after Madi forwarded the cognitive-debt warning and required Spec-Kit-style specs before implementation. Root cause: the factory was closing/reporting too much without teaching future agents what changed, what was deleted, and how to verify it. Rule: every substrate change tracks shipped and learned, with operator-simple Satory output and internal reasoning preserved in audits. No new LESSON (RULE ZERO). gbrain-timeline-ok via VPS CLI fallback after Codex MCP transport closed.
- **2026-05-11** | v1.1.0 — Added the May-2026 12-rule operating extension after Madi forwarded the newer Claude/Codex failure-mode article. Root cause: the original 4-rule baseline was present, but the eight newer agent-orchestration rules were only in chat/audit prose, not in this runtime code-behavior skill. Kept it compact to avoid AGENTS.md/CLAUDE.md bloat. Source captured at `pages/sources/user-forwarded/skills-are-the-prompts-2026-05-11.md`. No new LESSON (RULE ZERO).
- **2026-04-21** | v1.0.0 created. Session 56 (Mac-interactive). Trigger: Madi forwarded a thread about the 44k-star `forrestchang/andrej-karpathy-skills` repo with Karpathy's full critique + the 4-principle CLAUDE.md solution. Directive: *"if yes, do we have it? if no, then tell me and why... deploy EVERYWHERE so everything is up to date, everything is evolving."* Absorption: (a) upstream CLAUDE.md fetched verbatim via VPS (Mac + Air DNS blocked raw.githubusercontent.com at the moment — sidecar path through VPS worked; `gbrain-ops` AP-33 CLI-fallback pattern applied at HTTP layer); (b) source archived at `pages/concepts/forrestchang-karpathy-claudemd-source-2026-04-21/CLAUDE.md` verbatim; (c) this skill wraps + integrates with our substrate (cross-refs `karpathy-loop`, `agent-quality`, `evidence-verification`, `session-operating-contract`); (d) deployed to Mac + Air + factory via rsync. Distinction from `karpathy-loop`: meta-scorecard (karpathy-loop) vs code-behavior (this). Non-conflicting with Rule 15 (Principle 1 applies at pre-assumption-surface; Rule 15 applies post-approval). No new LESSON (RULE ZERO). Upstream repo: `forrestchang/andrej-karpathy-skills`, 44k stars in 7 days per Madi's forwarded thread.

## See also

- Upstream: [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills)
- [[karpathy-loop]] — meta-scorecard sibling
- [[agent-quality]] — runtime truthfulness sibling
- [[evidence-verification]] — prove-before-claim sibling
- [[session-operating-contract]] — session-lifecycle rules (Rules 4, 15)
- [[planning-discipline]] — upstream of Principle 4 (plan before code)
- [[mistake-to-skill]] — RULE ZERO absorption pattern used to bring this in
