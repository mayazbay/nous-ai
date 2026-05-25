---
type: spec
id: SPEC-OPEN-QUESTIONS-DOCTRINE-V1
title: "SPEC — Open-Questions doctrine v1 (Neo-Sparks absorption, pure-doctrine extension)"
tags: [spec, brainstorm-output, bs6, open-questions, neo-sparks, karpathy-compounding, session-50, v1]
date: 2026-04-19
last_updated: 2026-04-19
source_count: 3
status: draft-awaiting-bs8-review
related: [DRAFT-BS5C-OPEN-QUESTIONS-DESIGN-2026-04-19, audit, mistake-to-skill, session-operating-contract, infrastructure]
---

# SPEC — Open-Questions Doctrine v1 (2026-04-19)

## Status

**Draft — awaiting BS8 user review.** This spec is the final output of brainstorming. Implementation is blocked behind Madi's sign-off (BS8) + writing-plans invocation (BS9) + ship in a fresh-context session. **No SKILL.md mutations, no scanner deploys, no hook changes land from this overnight session.**

## Summary

Absorb the Neo/Karpathy-Sparks write-time-capture insight into Nous AGaaS as a pure-doctrine extension. Every skill Timeline entry must conclude with `Open questions:` — either explicit `none` or a tagged nested-bullet list. Zero new tables, crons, CLIs, or frontmatter fields. Three skill edits + one new scanner (with sibling test) + one pre-commit rule.

**Source:** Session-50 3-repo Karpathy-wiki research surfaced Neo's `NeoSpark` table as the only genuinely novel compounding primitive not yet in Nous AGaaS. Applied Musk step-1/2 elimination aggressively — dropped Neo's SQL schema, 30-min resolver cron, and blind-judge panel. Kept only the write-time-capture + provenance discipline.

**Pressure-tested:** Grok-reasoning adversarial review (LiteLLM `grok-reasoning`, 2026-04-19). Critique integrated: tightened scanner (structural-position check, not just presence), two-tier session-open scan (recent + global), expanded tag vocabulary (5→7), `Resolves:` convention for resolution traceability, soft warning on `none` for major bumps.

## Scope (what ships)

6 artifacts:

1. `pages/skills/mistake-to-skill/SKILL.md` v1.11 → v1.12 (AP-13 new + P1 step 2 extension)
2. `pages/skills/audit/SKILL.md` v1.18 → v1.19 (AP-19 new — two-tier SOAO point 6b)
3. `pages/skills/session-operating-contract/SKILL.md` v1.1 → v1.2 (Rule 12 new)
4. `tools/test_open_questions_gate.sh` (new, ~100 lines bash — 3 modes: staged / --all / --audit-none)
5. `tools/test_test_open_questions_gate.sh` (new sibling test, 7 fixtures A–G)
6. `tools/pre-commit-hook-tan-pattern.sh` (RULE 6 appended; redeploy to 4 hook targets)

## Non-goals (explicitly out of scope)

- ❌ No new SQL table, no separate `OPEN_QUESTIONS.md` file. Timeline entries are the sole location.
- ❌ No resolver cron. Resolution is human-authored in next Timeline entry via `Resolves:` convention.
- ❌ No blind-judge panel or voting mechanism.
- ❌ No new frontmatter field. Questions bind to Timeline entry (write-time provenance).
- ❌ No backfill of historical ~200 Timeline entries.
- ❌ No automatic tag classifier. Author picks from 7-tag vocab.

## Architecture

One-sentence architecture: **three existing skills gain small edits, one new scanner + its sibling test land in `tools/`, pre-commit gains one new rule, four hook targets redeploy.** No subsystem added. No daemon. No new cron.

**Data flow (6-step lifecycle):**

```
[1] WRITE — author bumps skill via AP-11 5-edit ritual (was 4-edit). New 5th edit:
    Open questions: block as final nested-bullet of new Timeline entry.

[2] COMMIT — `git add` → pre-commit RULE 6 runs test_open_questions_gate.sh (staged mode)
    → for each modified SKILL.md that adds a new Timeline entry:
      verify the STAGED file's latest Timeline entry has Open questions: as its LAST
      immediately-nested bullet. Structural position, not just presence.
    → REJECT with fix-hint if missing.
    → WARN (non-blocking) if version bump is "major" (new AP/Phase/≥3 rules) AND
      Open questions: is just `none`.

[3] PUSH — auto-sync cron commits+pushes to VPS bare → fan-out to 3 wiki working copies.
    4-way HEAD parity maintained as today.

[4] INGEST — gbrain autopilot re-embeds on next 5-min cycle. Nested bullets preserved
    as searchable chunks in compiled_truth.

[5] SURFACE — next session opens → AP-17 SOAO point 6b (new AP-19):
    Tier 1 (recent): awk+grep last 5 modified skills' latest Timeline entries for tagged bullets.
    Tier 2 (global): grep ALL 21 skills for `[contradiction]` / `[weak-edge]` tags. No head truncation.
    Agent sees both at session-open briefing; Tier 2 high-priority called out explicitly.

[6] RESOLVE — agent picks up a question during session work, or defers.
    Resolution uses structured convention:
      Resolves: <skill-slug> <YYYY-MM-DD> v<X.Y.Z> [<tag>] — <one-line reason>
    Placed in the resolving skill's new Timeline entry. Grep-able across vault.
```

## Tag vocabulary (7 types, extensible)

Ported 5 from Neo + 2 from Grok critique:

| Tag | Meaning |
|---|---|
| `[open-question]` | Author noticed they don't know the answer (default when unsure) |
| `[contradiction]` | Two claims that can't both be right |
| `[weak-edge]` | Cross-reference feels thin |
| `[isolated-node]` | Skill isn't cross-referenced where it probably should be |
| `[thin-domain]` | Subject-area coverage is sparse |
| `[dependency-risk]` | **(NEW v1)** Assumption about external system that may not hold (e.g., ZAI resource pkg, BDL client feed, Tailscale auth) |
| `[model-drift]` | **(NEW v1)** Underlying LLM/infra changed, downstream effects unmapped |

**Default when unsure:** `[open-question]`. Prefer `none` over inventing a bad question.

**Extensibility:** future sessions may add tags via AP bullet in `mistake-to-skill`. Not a closed set. Scanner regex allows any `[a-z-]+` inside the backticks (per `grep -E '^    - \`\[[a-z-]+\`\]'`).

## Format specification

### Base form (explicit null — for cosmetic bumps, clarifications, parity checks)

```
- **2026-04-19** | v1.12.0 — Session 50: <one-line what + why>. <details prose>. No new LESSON (RULE ZERO).
  - Open questions: none
```

### Tagged form (for substantive bumps — new AP, new Phase, ≥3 rule changes)

```
- **2026-04-19** | v1.12.0 — Session 50: <one-line what + why>. <details prose>. No new LESSON (RULE ZERO).
  - Open questions:
    - `[open-question]` Does X hold under condition Y?
    - `[weak-edge]` Cross-ref to [[skill-Z]] needs validation
    - `[dependency-risk]` Depends on BDL feed that's currently unguaranteed
```

**Rule:** `Open questions:` must be the FINAL immediately-nested bullet (2-space indent) of the Timeline entry. Children (4-space indent tagged lines) nest under it.

### Resolution form (when a later Timeline entry resolves a prior question)

```
- **2026-05-14** | v1.13.0 — Session 62: <prose>. Resolves: audit 2026-04-19 v1.18 [open-question] — confirmed via strace that bash-init failure was fd-exhaustion, not TCC. No new LESSON (RULE ZERO).
  - Open questions: none
```

Grep-able: `grep -r "^Resolves:" pages/skills/*/SKILL.md`

## Components — exact artifacts

### Artifact A — `pages/skills/mistake-to-skill/SKILL.md` v1.11.0 → v1.12.0

**A.1 — Frontmatter edits**
- `version: 1.11.0` → `version: 1.12.0`
- `last_updated: 2026-04-15` → `last_updated: 2026-04-19`

**A.2 — H1 edit**
- `# mistake-to-skill v1.11.0` → `# mistake-to-skill v1.12.0`

**A.3 — P1 protocol step 2 extension (insert after existing bullets)**

> - **NEW (AP-13, v1.12+):** Append an indented `Open questions:` bullet as the FINAL immediately-nested line of that Timeline entry. Either `  - Open questions: none` (explicit null, OK for cosmetic bumps) OR the tagged form:
>   ```
>     - Open questions:
>       - `[<tag>]` <question text>
>   ```
>   Valid tags: `[open-question]` / `[contradiction]` / `[weak-edge]` / `[isolated-node]` / `[thin-domain]` / `[dependency-risk]` / `[model-drift]`. Default when unsure: `[open-question]`. Pre-commit RULE 6 enforces mechanically; WARN (non-blocking) if bump is major (new AP/Phase/≥3 rule changes) AND block is just `none`.

**A.4 — New AP-13 bullet (insert in Anti-Patterns section after AP-12)**

```markdown
### AP-13: Timeline entries MUST conclude with `Open questions:` bullet — write-time-capture doctrine (session 50, 2026-04-19)

**Pattern:** Agent bumps a skill and writes a Timeline entry describing what changed. Agent forgets or declines to record what they DIDN'T resolve — contradictions noticed but not chased, weak-edges spotted but not cross-linked, dependencies assumed but unverified, questions that could shape the next session's work. Those residual questions evaporate when the session closes. Next-session agent lacks the fresh-context "here's what I noticed but didn't answer" signal.

**Why it matters:** This is the Neo/Karpathy-Sparks insight applied doctrine-only. Neo's key observation: LLM context at WRITE-TIME is the best window to capture "questions the system owes itself" — at close-time the agent is tired and focused on closing. A persistent-priority-ranked-scheduler-consumed table (Neo's `NeoSpark`) is over-engineered for our ~1-3 sessions/day scale, but the WRITE-TIME capture is the compounding ratchet. Forcing the author to explicitly state `Open questions:` — even if `none` — is the Karpathy-evidence discipline preventing silent drift.

**Rule — exact format:**

Every NEW skill Timeline entry MUST conclude with `Open questions:` as the FINAL immediately-nested bullet (2-space indent). Either:

```
  - Open questions: none
```

...OR the tagged form with 4-space-indent children:

```
  - Open questions:
    - `[<tag>]` <question text>
    - `[<tag>]` <question text>
```

**Valid tag vocabulary (7 types, extensible):**
- `[open-question]` — author noticed they don't know the answer
- `[contradiction]` — two claims that can't both be right
- `[weak-edge]` — cross-reference feels thin
- `[isolated-node]` — skill isn't cross-referenced where it should be
- `[thin-domain]` — subject-area coverage is sparse
- `[dependency-risk]` — assumption about external system that may not hold
- `[model-drift]` — underlying LLM / infra changed, downstream effects unmapped

Default when unsure: `[open-question]`. Prefer `none` over inventing a bad question.

**"None" anti-abuse guard:** Pre-commit WARN (non-blocking) when ALL of:
- Diff adds `+### AP-N`, `+### Phase`, OR ≥3 `+- ` lines in Current Rules / Rules section
- AND Open questions block is just `none`.

Soft pressure: the reviewer sees a yellow flag suggesting real questions should exist for a major change. Operator can override; agent cannot skip mechanically.

**Resolution convention (grep-able, no separate table):**

When a later Timeline entry resolves a prior open question, use the structured form in its prose:

```
Resolves: <skill-slug> <YYYY-MM-DD> v<X.Y.Z> [<tag>] — <one-line reason>
```

Example:
```
- **2026-05-14** | v1.13.0 — Session 62: debug confirmed via strace. Resolves: audit 2026-04-19 v1.18 [open-question] — bash-init failure was fd-exhaustion, not TCC. No new LESSON (RULE ZERO).
  - Open questions: none
```

Global grep finds all resolutions: `grep -rhE "^Resolves: " pages/skills/*/SKILL.md | sort`.

**Why not a frontmatter field:** breaks the write-time-capture-with-provenance principle. Questions bind to the Timeline entry that PRODUCED them, not to a skill-level aggregate. Each question has a tight link to the context in which it was noticed.

**Why not a separate resolution table:** violates Musk step-2. Timeline IS the resolution log. Grep over 21 skills is <100ms.

**Mechanical enforcement:** `tools/test_open_questions_gate.sh` (wired to pre-commit RULE 6). Structural-position check — verifies Open questions is the LAST 2-space-indented bullet of the staged entry, not just anywhere in the file. Backfill-safe: historical entries are not re-checked; only NEW additions enforced. Known-limits on git amends/rebases/cherry-picks documented in scanner SKIP output.

**AP-11 extension:** The prior 4-edit ritual (frontmatter + H1 + Timeline + AP-bullet parity) becomes a 5-edit ritual with this rule adding Open questions bullet as final line of each new Timeline entry.

**Known limits (v1 doctrine — honest, shipped as-is):**
- Recency bias on Tier 1 session-open surfacing (mitigated by Tier 2 global scan — see `audit` AP-19).
- Resolution tracking is convention-only (grep-able, no mechanical backlink).
- `none` can become lazy default for cosmetic bumps — acceptable; weekly `--audit-none` scan flags skills with ≥3 consecutive `none` as review candidates.
- Diff fragility on `git amend` / `rebase` / `cherry-pick` — scanner SKIPs ambiguous patterns rather than false-reject.
- No mechanical priority queue for `[contradiction]` — v1 is manual escalation; v2+ if evidence demands.

**Cross-ref:** `audit` AP-19 (read-time surfacing SOAO point 6b); `session-operating-contract` Rule 12 (binding doctrine); `infrastructure` pre-commit RULE 6 (write-time gate); Neo project (`dallasrose/neo-agent-knowledge`) — conceptual ancestor. Grok-reasoning adversarial critique session-50 2026-04-19 shaped the refinement loop.

**Source:** Session 50 BS5 design after 3-repo Karpathy-wiki research (Neo / llm-wiki-compiler / claude-obsidian). Full research + refinement evidence in [[DRAFT-BS5C-OPEN-QUESTIONS-DESIGN-2026-04-19]]. Musk step-1/2 elimination explicit: dropped Neo's table/scheduler/judge, kept write-time capture doctrine. No new LESSON (RULE ZERO).
```

**A.5 — Evidence trail entry (insert at top of `## Evidence trail` section)**

```markdown
- **2026-04-19** | v1.12.0 — Session 50: absorbed **AP-13** — Timeline entries MUST conclude with `Open questions:` bullet as last immediately-nested line. Neo-Sparks doctrine, pure-doctrine extension. 7 tags (5 from Neo + `[dependency-risk]` + `[model-drift]` from Grok critique). Mechanical gate via `infrastructure` pre-commit RULE 6 + `tools/test_open_questions_gate.sh` (structural-position check) + sibling test per AP-36 (7 fixtures A-G). Read-time surfacing via `audit` AP-19 (two-tier SOAO point 6b — recent window + global contradiction/weak-edge scan). Doctrine mandate in `session-operating-contract` Rule 12. Resolution convention: `Resolves: <skill> <date> v<X.Y.Z> [<tag>] — <reason>` (grep-able). `None`-for-major WARN (non-blocking). Forward-only backfill — historical ~200 entries unchanged. Source: BS5 3-repo research (Neo / llm-wiki-compiler / claude-obsidian) + Grok adversarial critique. Refinements from critique: structural-position check (vs mere presence), two-tier session-open scan (vs recency-biased single tier), 7-tag vocab (vs 5), `Resolves:` convention, SKIP on ambiguous diffs. Cross-ref AP-11 (4→5-edit ritual), `audit` AP-19, `session-operating-contract` Rule 12, `infrastructure` RULE 6. Karpathy-primary: substrate measurably smarter — write-time capture + two-tier read-time surfacing = compounding ratchet at doctrine cost only. No new LESSON (RULE ZERO).
  - Open questions:
    - `[open-question]` After 30 sessions, will tag distribution match the 7-type split — or converge to mostly `[open-question]`, revealing taxonomy is too fine-grained?
    - `[weak-edge]` Weekly `--audit-none` cron not yet wired at v1 ship; if not wired within 3 sessions, the anti-abuse guard is ritual-only.
    - `[dependency-risk]` Pre-commit RULE 6 deployment to 4 hook targets assumes SSH + `cp` stay functional on all 3 hosts; one TCC regression or auth flap silently breaks a target's gate.
    - `[model-drift]` Grok-reasoning was used for critique via LiteLLM fallback chain; token/quality floor if Grok and Opus both unavailable (fallback `glm-5.1`) is untested for this kind of adversarial review.
```

---

### Artifact B — `pages/skills/audit/SKILL.md` v1.18.0 → v1.19.0

**B.1 — Frontmatter edits**
- `version: 1.18.0` → `version: 1.19.0`
- `last_updated: 2026-04-19` (unchanged)
- description append: `+ SOAO point 6b two-tier Open-questions carryover scan (AP-19, v1.19).`

**B.2 — H1 edit**
- `# audit v1.18.0` → `# audit v1.19.0`

**B.3 — New AP-19 bullet (insert after AP-18 bullet, before `## Rules` section)**

```markdown
- **AP-19: SOAO point 6b — Two-tier Open-questions carryover scan.** (session 50, 2026-04-19) Extends AP-17 point 6 (P-SYNC-08 carryover reality probe). Read-time surfacing of `mistake-to-skill` AP-13 write-time captures. **Two tiers run in parallel at session open:**

**Tier 1 — recent window (what's fresh):**
Last 5 modified skills' latest Timeline entries. For context on active threads.
```bash
cd "$NOUS_VAULT" && for skill in $(ls -t pages/skills/*/SKILL.md | head -5); do
    echo "=== $skill ==="
    awk '/^## (Timeline|Evidence trail)/,/^## [^T]/' "$skill" | \
        awk '/^- \*\*[0-9]{4}/{found=1; count=0} found{print; if(++count>30)exit}' | \
        grep -E "^    - \`\[[a-z-]+\`\]"
done
```

**Tier 2 — global high-priority scan (what's owed, no recency bias):**
Grep ALL skills for `[contradiction]` and `[weak-edge]` tags. No `head` truncation. These are the tags that most represent actionable silent drift.
```bash
cd "$NOUS_VAULT" && echo "=== Global [contradiction] + [weak-edge] across all skills ==="
grep -rhnE "^    - \`\[(contradiction|weak-edge)\`\]" pages/skills/*/SKILL.md | \
    sort -t: -k3 | tail -20   # most recent 20 by context
```

**Briefing format at session-open:**
Agent surfaces:
1. Total `[contradiction]` count across all skills + top-5 most recent.
2. Total `[weak-edge]` count across all skills + top-5 most recent.
3. Any `[dependency-risk]` tags in recent Tier 1 window.
4. Tier 1 all-tags list from 5 recent skills (summary count + first 5 per skill max).

**Why two tiers:** Tier 1 alone is recency-biased — high-value open questions may live in stable 5-of-21 oldest skills. Tier 2 catches global silent drift. Both tiers run in <1s across 21 skills.

**Forward-only rollout note:** expect thin results for ~2-3 sessions until new format fills the rolling window. Historical ~200 Timeline entries are not retroactively backfilled.

**Compounding gate:** add both scans to `tools/soao.sh` when it ships (session-50+ candidate). Session-51+ `~/.claude/hooks/session-start-soao.sh` auto-invokes. Doctrine today compounds when any agent reads this skill and runs the scans; mechanization ships later per Karpathy iterative hardening.

**Cross-ref:** AP-17 (SOAO 7-point ritual), `mistake-to-skill` AP-13 (source doctrine — write-time gate), `session-operating-contract` Rule 12 (binding), `infrastructure` pre-commit RULE 6 (write-time gate complementing AP-19 read-time). Grok critique session-50 identified the single-tier-recency-bias flaw; AP-19 two-tier design is the refined fix. No new LESSON (RULE ZERO).
```

**B.4 — Timeline entry (insert at top of `## Timeline` section)**

```markdown
- **2026-04-19** | v1.19.0 — Session 50 (overnight BS5 design block): absorbed **AP-19** — SOAO point 6b two-tier Open-questions carryover scan. Extends AP-17 point 6 (P-SYNC-08) with BOTH a recent-window scan (last 5 modified skills, full tagged bullets) AND a global high-priority scan (all 21 skills, `[contradiction]` + `[weak-edge]` only, no head truncation). Fix for Grok-identified single-tier recency-bias flaw: high-value questions in stable oldest skills would miss session-open surfacing. Two tiers run <1s each. Forward-only rollout — thin results for ~2-3 sessions until new format fills rolling window. Compounding gate candidate: add both scans to `tools/soao.sh` session-50+. Cross-ref AP-17 (SOAO 7-point), `mistake-to-skill` AP-13 (source doctrine), `session-operating-contract` Rule 12 (binding), `infrastructure` pre-commit RULE 6 (write-time gate). Third absorption this session (v1.17 AP-18 codified → v1.18 AP-18 revised → v1.19 AP-19 new) — iterative hardening pattern visible across same calendar day. No new LESSON (RULE ZERO).
  - Open questions:
    - `[open-question]` After 10 sessions, does Tier 2 `[contradiction]` scan actually surface meaningful items — or is `[contradiction]` used so rarely that Tier 2 is dead code?
    - `[weak-edge]` `tools/soao.sh` carryover from session 49 still unwired; AP-19 runs manually at session-open until soao.sh ships.
    - `[thin-domain]` Coverage of `[dependency-risk]` across stack: our 21 skills have many external-system assumptions (BDL feed, Tailscale auth, ZAI resource pkg, XAI key, etc.) — none currently tagged.
```

---

### Artifact C — `pages/skills/session-operating-contract/SKILL.md` v1.1.0 → v1.2.0

**C.1 — Frontmatter edits**
- `version: 1.1.0` → `version: 1.2.0`
- `last_updated: 2026-04-18` → `last_updated: 2026-04-19`

**C.2 — H1 edit**
- `# session-operating-contract v1.1.0` → `# session-operating-contract v1.2.0`

**C.3 — New Rule 12 (insert after Rule 11 in `## Current rules (binding)` section)**

```markdown
### 12. Open questions — every Timeline entry declares what's unresolved (v1.2, 2026-04-19, session 50)

Every skill Timeline entry you add MUST conclude with an `Open questions:` nested-bullet as the FINAL 2-space-indent line of the entry. Either explicit-null:

```
  - Open questions: none
```

...OR a tagged list (4-space-indent children):

```
  - Open questions:
    - `[open-question]` <what you noticed you don't know>
    - `[weak-edge]` <a related-to or cross-ref that's suspiciously thin>
    - `[contradiction]` <two claims that can't both be right>
    - `[isolated-node]` <this skill isn't cross-referenced where it should be>
    - `[thin-domain]` <subject-area coverage is sparse>
    - `[dependency-risk]` <assumption about external system that may not hold>
    - `[model-drift]` <underlying LLM/infra changed, downstream effects unmapped>
```

**Why:** Captures the Neo/Karpathy-Sparks insight at write-time when context is fresh. The next session's agent reads these at open via `audit` AP-19 (two-tier SOAO point 6b). Forces the author to state "yes, I considered what I don't know" instead of leaving silent drift. Eliminates the close-time-agent-tired failure mode.

**Resolution syntax (grep-able, no separate table):**

When a later Timeline entry resolves a prior open question, use the structured form in its prose:

```
Resolves: <skill-slug> <YYYY-MM-DD> v<X.Y.Z> [<tag>] — <one-line reason>
```

Timeline IS the resolution log.

**Mechanical enforcement:** pre-commit RULE 6 (registered in `infrastructure` skill as a new AP at implementation time — number assigned then) rejects commits that add a new Timeline entry without the `Open questions:` line in its final-bullet position. WARN (non-blocking) if bump is major (new AP/Phase/≥3 rule changes) AND block is just `none`. Backfill-safe — only flags NEW additions. See `mistake-to-skill` AP-13 for full doctrine + `tools/test_open_questions_gate.sh` + `tools/test_test_open_questions_gate.sh` sibling test.

**Default when unsure:** `[open-question]` is always a valid tag. Prefer `none` over inventing a bad question.

**Known limits (v1, shipped as-is):** recency bias in Tier 1 (mitigated by Tier 2 `[contradiction]` + `[weak-edge]` global scan); resolution tracking is convention-only; diff fragility on amends/rebases/cherry-picks (scanner SKIPs ambiguous cases). v2+ gates build on usage evidence, not speculation.

Cross-ref: `mistake-to-skill` AP-13 (source doctrine + P1 step 2 extension), `audit` AP-19 (read-time two-tier surfacing), `infrastructure` pre-commit RULE 6 (write-time gate), Neo project (conceptual ancestor `dallasrose/neo-agent-knowledge`).
```

**C.4 — Evidence trail entry (insert at top of `## Evidence trail` section)**

```markdown
- **2026-04-19** | v1.2.0 — Session 50 (overnight BS5 design block): absorbed **Rule 12** (Open questions — every Timeline entry declares what's unresolved). Karpathy/Neo-Sparks doctrine captured as pure-doctrine extension. Musk step-1/2 elimination: dropped Neo's SQL table + 30-min resolver cron + blind-judge panel; kept only write-time capture + provenance + grep-able resolution convention. Binds with `mistake-to-skill` AP-13 (P1 protocol step 2 extended — 4-edit → 5-edit ritual + full doctrine bullet), `audit` AP-19 (two-tier SOAO point 6b read-time surfacing), `infrastructure` pre-commit RULE 6 (mechanical write-time gate), `tools/test_open_questions_gate.sh` + sibling test per AP-36. 7-tag vocabulary (5 Neo + 2 from Grok adversarial critique). `Resolves: <skill> <date> v<X.Y.Z> [<tag>] — <reason>` resolution convention. `none`-for-major bump WARN. Source: BS5 3-repo Karpathy-wiki research (Neo / llm-wiki-compiler / claude-obsidian) → Grok adversarial critique (session-50 2026-04-19 via LiteLLM `grok-reasoning`) → refined design (Block 3 integration). Forward-only backfill (historical ~200 entries unchanged). Rule 6 (Failure → skill) applied at design-time twice: (1) session 49-bis AP-18 codified + session 50 AP-18 revised within 24h, (2) Grok critique reshaped this doctrine BEFORE ship. No new LESSON (RULE ZERO).
  - Open questions:
    - `[open-question]` At session-80 (~30 sessions post-ship), does usage evidence support the v2 mechanical-priority-queue for `[contradiction]` tags, or does manual escalation remain sufficient?
    - `[dependency-risk]` Rule 12 enforcement chain depends on all 3 wiki hosts' pre-commit hooks staying fresh; hook drift detection lives in AP-17 point 3 (session-cadence only, not real-time).
```

---

### Artifact D — `tools/test_open_questions_gate.sh` (new, ~110 lines bash)

**Modes:**
- Default (staged): called by pre-commit RULE 6. Checks staged diff for new Timeline entries + verifies Open questions is FINAL 2-space-indent bullet.
- `--all`: walks every skill's latest Timeline entry; reports compliance count (non-blocking, for audit).
- `--audit-none`: reports skills with ≥3 consecutive `none` Open questions entries as review candidates.

**Exit codes:**
- 0: PASS
- 1: REJECT (staged mode only)
- 2: INTERNAL ERROR

```bash
#!/bin/bash
# test_open_questions_gate.sh
#
# Enforces session-operating-contract Rule 12 / mistake-to-skill AP-13.
# Every NEW skill Timeline entry must include Open questions: as the FINAL
# immediately-nested bullet (2-space indent).
#
# Modes:
#   (default)      — check staged diff (pre-commit use)
#   --all          — audit every skill's latest Timeline entry (non-blocking)
#   --audit-none   — flag skills with ≥3 consecutive 'none' Open questions

set -euo pipefail

MODE="${1:-staged}"
case "$MODE" in
    --all) MODE=all ;;
    --audit-none) MODE=audit-none ;;
    staged|--staged) MODE=staged ;;
    *) echo "ERROR: unknown mode '$MODE' — use default, --all, or --audit-none" >&2; exit 2 ;;
esac

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
    echo "ERROR: not inside a git repo" >&2
    exit 2
fi
cd "$(git rev-parse --show-toplevel)"

# --- helpers ---

# Extract the LATEST Timeline entry from a skill file (first entry in ## Timeline
# or ## Evidence trail section). Returns the entry's lines (header + all child bullets).
extract_latest_entry() {
    local file="$1"
    awk '
        /^## (Timeline|Evidence trail)/{in_t=1; next}
        in_t && /^## [^T]/{exit}
        in_t && /^- \*\*[0-9]{4}/{
            if (found) exit
            found=1
        }
        found { print }
    ' "$file"
}

# Check the last 2-space-indent bullet of the entry block matches Open questions:
# Returns 0 if compliant, 1 otherwise.
check_entry_final_bullet() {
    local entry="$1"
    local last_bullet
    last_bullet=$(echo "$entry" | grep -E '^  - ' | tail -1 || true)
    if echo "$last_bullet" | grep -qE '^  - Open questions:'; then
        return 0
    fi
    return 1
}

# Check if a major-bump warning applies:
# - new AP added OR new Phase added OR ≥3 new rules added
# - AND Open questions block is just `none`
is_major_none_warn() {
    local file="$1"
    local diff_content added_ap added_phase rule_lines oq_lines
    diff_content=$(git diff --cached -- "$file")
    added_ap=$(echo "$diff_content" | grep -cE '^\+### AP-' || true)
    added_phase=$(echo "$diff_content" | grep -cE '^\+### Phase' || true)
    rule_lines=$(echo "$diff_content" | grep -cE '^\+- \*\*[A-Z]' || true)
    if [ "$added_ap" -eq 0 ] && [ "$added_phase" -eq 0 ] && [ "$rule_lines" -lt 3 ]; then
        return 1
    fi
    oq_lines=$(echo "$diff_content" | grep -cE '^\+  - Open questions: none' || true)
    if [ "$oq_lines" -gt 0 ]; then
        return 0
    fi
    return 1
}

# --- modes ---

if [ "$MODE" = "staged" ]; then
    CHANGED=$(git diff --cached --name-only --diff-filter=AM | \
              grep -E '^pages/skills/[^/]+/SKILL\.md$' || true)
    [ -z "$CHANGED" ] && { echo "OK: no skill SKILL.md files staged" >&2; exit 0; }

    REJECT=0
    for file in $CHANGED; do
        # Did this diff ADD a new Timeline entry header?
        added_entry=$(git diff --cached -- "$file" | \
                      grep -cE '^\+- \*\*[0-9]{4}-[0-9]{2}-[0-9]{2}\*\* \| v[0-9]+\.[0-9]+\.[0-9]+' || true)
        if [ "$added_entry" -eq 0 ]; then
            continue
        fi

        # Ambiguous-diff heuristic: if diff has >5 `+- **YYYY` entries AND matching `-` deletions,
        # likely amend/rebase — SKIP (non-blocking warn).
        del_entry=$(git diff --cached -- "$file" | \
                    grep -cE '^-- \*\*[0-9]{4}-[0-9]{2}-[0-9]{2}\*\* \| v[0-9]+\.[0-9]+\.[0-9]+' || true)
        if [ "$added_entry" -gt 5 ] && [ "$del_entry" -gt 0 ]; then
            echo "⚠️  SKIP: $file — ambiguous diff pattern (likely amend/rebase/cherry-pick). Manual verify recommended." >&2
            continue
        fi

        # Structural check: on the STAGED file, verify latest Timeline entry's
        # final 2-space bullet is Open questions:.
        staged_content=$(git show ":$file")
        latest_entry=$(echo "$staged_content" | awk '
            /^## (Timeline|Evidence trail)/{in_t=1; next}
            in_t && /^## [^T]/{exit}
            in_t && /^- \*\*[0-9]{4}/{
                if (found) exit
                found=1
            }
            found { print }
        ')
        if ! check_entry_final_bullet "$latest_entry"; then
            last_bullet=$(echo "$latest_entry" | grep -E '^  - ' | tail -1 || echo "(none found)")
            echo "❌ REJECT: $file — latest Timeline entry's FINAL 2-space bullet is not 'Open questions:'." >&2
            echo "   Found:    $last_bullet" >&2
            echo "   Expected: '  - Open questions:' or '  - Open questions: none'" >&2
            echo "   Doctrine: skills/session-operating-contract Rule 12 (v1.2+); skills/mistake-to-skill AP-13 (v1.12+)." >&2
            REJECT=1
            continue
        fi

        # Major-bump `none` WARN (non-blocking)
        if is_major_none_warn "$file"; then
            echo "⚠️  WARN: $file — major bump (new AP/Phase/≥3 rules) with 'Open questions: none'." >&2
            echo "   Consider whether real questions exist. Not blocking; operator discretion." >&2
        fi
    done

    [ "$REJECT" -eq 0 ] && echo "OK: all staged Timeline entries have Open questions: in final-bullet position" >&2
    exit $REJECT

elif [ "$MODE" = "all" ]; then
    TOTAL=0; COMPLIANT=0
    for file in $(find pages/skills -mindepth 2 -maxdepth 2 -name SKILL.md); do
        TOTAL=$((TOTAL + 1))
        entry=$(extract_latest_entry "$file")
        if check_entry_final_bullet "$entry"; then
            COMPLIANT=$((COMPLIANT + 1))
        fi
    done
    echo "AUDIT: $COMPLIANT/$TOTAL skills have 'Open questions:' in latest Timeline entry (forward-only rollout)." >&2
    exit 0

elif [ "$MODE" = "audit-none" ]; then
    echo "AUDIT-NONE: skills with ≥3 consecutive 'Open questions: none' Timeline entries:" >&2
    for file in $(find pages/skills -mindepth 2 -maxdepth 2 -name SKILL.md); do
        # Extract ALL entries, get the last 3 Open questions lines
        none_streak=$(awk '
            /^## (Timeline|Evidence trail)/{in_t=1; next}
            in_t && /^## [^T]/{exit}
            in_t && /^  - Open questions: none/{print}
        ' "$file" | head -3 | wc -l | tr -d ' ')
        if [ "$none_streak" -eq 3 ]; then
            echo "  $(echo "$file" | sed 's|pages/skills/||; s|/SKILL.md||')" >&2
        fi
    done
    exit 0
fi
```

---

### Artifact E — `tools/test_test_open_questions_gate.sh` (sibling test, 7 fixtures A-G)

```bash
#!/bin/bash
# test_test_open_questions_gate.sh — sibling test for test_open_questions_gate.sh
# Per infrastructure AP-36: every scanner has a sibling test that proves it works.
# 7 fixtures cover present / tagged / missing / 0-delta / wrong-case / amend / rebase.

set -euo pipefail

SCRIPT="$(cd "$(dirname "$0")" && pwd)/test_open_questions_gate.sh"

PASS=0; FAIL=0

assert_exit() {
    local name="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "✅ PASS: $name (expected $expected, got $actual)"
        PASS=$((PASS + 1))
    else
        echo "❌ FAIL: $name (expected $expected, got $actual)"
        FAIL=$((FAIL + 1))
    fi
}

make_fixture_repo() {
    local dir="$1"
    rm -rf "$dir"; mkdir -p "$dir/pages/skills/test-skill"
    ( cd "$dir" && git init -q && git config user.email t@t.com && git config user.name t )
    cat > "$dir/pages/skills/test-skill/SKILL.md" <<'EOF'
---
type: skill
name: test-skill
version: 1.0.0
---
# test-skill v1.0.0

## Timeline

- **2026-04-01** | v1.0.0 — created.
  - Open questions: none
EOF
    ( cd "$dir" && git add -A && git commit -q -m "initial" )
}

run_scanner() {
    local dir="$1"
    ( cd "$dir" && bash "$SCRIPT" >/dev/null 2>&1 ) && echo 0 || echo $?
}

append_entry_with_oq_none() {
    local dir="$1"
    cat >> "$dir/pages/skills/test-skill/SKILL.md" <<'EOF'
- **2026-05-01** | v2.0.0 — new entry with explicit-null.
  - Open questions: none
EOF
    sed -i.bak 's/version: 1.0.0/version: 2.0.0/' "$dir/pages/skills/test-skill/SKILL.md"
    sed -i.bak 's/# test-skill v1.0.0/# test-skill v2.0.0/' "$dir/pages/skills/test-skill/SKILL.md"
    rm -f "$dir/pages/skills/test-skill/SKILL.md.bak"
}

# Fixture A: new entry + `none` → PASS
test_A() {
    local d=/tmp/oq-test-A; make_fixture_repo "$d"; append_entry_with_oq_none "$d"
    ( cd "$d" && git add -A )
    assert_exit "A: new entry + 'none' (final bullet)" 0 "$(run_scanner "$d")"
}

# Fixture B: new entry + tagged bullets → PASS
test_B() {
    local d=/tmp/oq-test-B; make_fixture_repo "$d"
    cat >> "$d/pages/skills/test-skill/SKILL.md" <<'EOF'
- **2026-05-01** | v2.0.0 — new entry with tagged questions.
  - Open questions:
    - `[open-question]` is this test valid?
    - `[weak-edge]` cross-ref gap
EOF
    sed -i.bak 's/version: 1.0.0/version: 2.0.0/' "$d/pages/skills/test-skill/SKILL.md"
    sed -i.bak 's/# test-skill v1.0.0/# test-skill v2.0.0/' "$d/pages/skills/test-skill/SKILL.md"
    rm -f "$d/pages/skills/test-skill/SKILL.md.bak"
    ( cd "$d" && git add -A )
    assert_exit "B: new entry + tagged bullets" 0 "$(run_scanner "$d")"
}

# Fixture C: new entry + NO Open questions → REJECT
test_C() {
    local d=/tmp/oq-test-C; make_fixture_repo "$d"
    cat >> "$d/pages/skills/test-skill/SKILL.md" <<'EOF'
- **2026-05-01** | v2.0.0 — new entry WITHOUT open questions.
EOF
    sed -i.bak 's/version: 1.0.0/version: 2.0.0/' "$d/pages/skills/test-skill/SKILL.md"
    sed -i.bak 's/# test-skill v1.0.0/# test-skill v2.0.0/' "$d/pages/skills/test-skill/SKILL.md"
    rm -f "$d/pages/skills/test-skill/SKILL.md.bak"
    ( cd "$d" && git add -A )
    assert_exit "C: new entry WITHOUT Open questions" 1 "$(run_scanner "$d")"
}

# Fixture D: 0-delta Timeline (frontmatter-only change) → PASS (skip)
test_D() {
    local d=/tmp/oq-test-D; make_fixture_repo "$d"
    sed -i.bak 's/^type: skill$/type: skill\ndescription: updated/' "$d/pages/skills/test-skill/SKILL.md"
    rm -f "$d/pages/skills/test-skill/SKILL.md.bak"
    ( cd "$d" && git add -A )
    assert_exit "D: no new Timeline entry (frontmatter-only)" 0 "$(run_scanner "$d")"
}

# Fixture E: lowercase 'open questions:' → REJECT
test_E() {
    local d=/tmp/oq-test-E; make_fixture_repo "$d"
    cat >> "$d/pages/skills/test-skill/SKILL.md" <<'EOF'
- **2026-05-01** | v2.0.0 — new entry with WRONG CASE.
  - open questions: none
EOF
    sed -i.bak 's/version: 1.0.0/version: 2.0.0/' "$d/pages/skills/test-skill/SKILL.md"
    sed -i.bak 's/# test-skill v1.0.0/# test-skill v2.0.0/' "$d/pages/skills/test-skill/SKILL.md"
    rm -f "$d/pages/skills/test-skill/SKILL.md.bak"
    ( cd "$d" && git add -A )
    assert_exit "E: lowercase rejected" 1 "$(run_scanner "$d")"
}

# Fixture F: Open questions in WRONG POSITION (not final bullet) → REJECT
test_F() {
    local d=/tmp/oq-test-F; make_fixture_repo "$d"
    cat >> "$d/pages/skills/test-skill/SKILL.md" <<'EOF'
- **2026-05-01** | v2.0.0 — new entry.
  - Open questions: none
  - Another trailing bullet
EOF
    sed -i.bak 's/version: 1.0.0/version: 2.0.0/' "$d/pages/skills/test-skill/SKILL.md"
    sed -i.bak 's/# test-skill v1.0.0/# test-skill v2.0.0/' "$d/pages/skills/test-skill/SKILL.md"
    rm -f "$d/pages/skills/test-skill/SKILL.md.bak"
    ( cd "$d" && git add -A )
    assert_exit "F: Open questions NOT final bullet rejected" 1 "$(run_scanner "$d")"
}

# Fixture G: ambiguous amend-like diff (>5 added entries + matching deletions) → SKIP (PASS)
test_G() {
    local d=/tmp/oq-test-G; make_fixture_repo "$d"
    # Create a scenario with many added entries + many deletions (amend/rebase-like)
    cat > "$d/pages/skills/test-skill/SKILL.md" <<'EOF'
---
type: skill
name: test-skill
version: 3.0.0
---
# test-skill v3.0.0

## Timeline

- **2026-05-06** | v3.0.0 — entry 6.
  - Open questions: none
- **2026-05-05** | v2.5.0 — entry 5.
  - Open questions: none
- **2026-05-04** | v2.4.0 — entry 4.
  - Open questions: none
- **2026-05-03** | v2.3.0 — entry 3.
  - Open questions: none
- **2026-05-02** | v2.2.0 — entry 2.
  - Open questions: none
- **2026-05-01** | v2.1.0 — entry 1.
  - Open questions: none
EOF
    ( cd "$d" && git add -A )
    # This diff has 6 `+- **2026-05-` entries (new) AND is re-writing from `- **2026-04-01**` → many net-new.
    # Scanner should SKIP as ambiguous rather than processing.
    assert_exit "G: ambiguous amend-like diff SKIP" 0 "$(run_scanner "$d")"
}

test_A; test_B; test_C; test_D; test_E; test_F; test_G

echo ""
echo "==================================="
echo "RESULT: $PASS passed, $FAIL failed"
echo "==================================="

rm -rf /tmp/oq-test-*

[ $FAIL -eq 0 ]
```

---

### Artifact F — Pre-commit RULE 6 block

Append to `tools/pre-commit-hook-tan-pattern.sh` (then redeploy to 4 targets: Mac `.git/hooks/pre-commit`, Air wiki `.git/hooks/pre-commit`, VPS wiki `.git/hooks/pre-commit`, + `tools/pre-commit-hook-tan-pattern.sh` canonical backup):

```bash
# RULE 6 — Open questions gate (session-operating-contract Rule 12 / mistake-to-skill AP-13)
# Every NEW skill Timeline entry must have Open questions: as its final 2-space bullet.
# Handles major-bump `none` WARN (non-blocking) + ambiguous-diff SKIP (amend/rebase/cherry-pick).
if [ -x tools/test_open_questions_gate.sh ]; then
    if ! bash tools/test_open_questions_gate.sh; then
        echo "" >&2
        echo "Pre-commit RULE 6 FAILED — see fix hint above." >&2
        echo "(To override: operator-only, git commit --no-verify — NOT for agents.)" >&2
        exit 1
    fi
fi
```

**Deployment command:**

```bash
cp tools/pre-commit-hook-tan-pattern.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
ssh air 'f=~/nous-agaas/wiki/tools/pre-commit-hook-tan-pattern.sh; cp "$f" ~/nous-agaas/wiki/.git/hooks/pre-commit && chmod +x ~/nous-agaas/wiki/.git/hooks/pre-commit'
ssh root@65.108.215.200 'f=/root/nous-agaas/wiki/tools/pre-commit-hook-tan-pattern.sh; cp "$f" /root/nous-agaas/wiki/.git/hooks/pre-commit && chmod +x /root/nous-agaas/wiki/.git/hooks/pre-commit'
# Verify 4-target MD5 parity on new hook
md5 -q .git/hooks/pre-commit
ssh air 'md5 -q ~/nous-agaas/wiki/.git/hooks/pre-commit'
ssh root@65.108.215.200 'md5sum /root/nous-agaas/wiki/.git/hooks/pre-commit | awk "{print \$1}"'
```

All 4 MD5s must match. AP-17 SOAO point 3 picks up the new MD5 at next session-open.

---

## Implementation order (post-BS8 + BS9 ship session)

When Madi approves spec → BS9 `writing-plans` → new session executes this order:

1. Run `test_skill_version_parity.sh` (baseline clean state).
2. Edit `pages/skills/mistake-to-skill/SKILL.md` (A.1–A.5).
3. Edit `pages/skills/audit/SKILL.md` (B.1–B.4).
4. Edit `pages/skills/session-operating-contract/SKILL.md` (C.1–C.4).
5. Create `tools/test_open_questions_gate.sh` (Artifact D), `chmod +x`.
6. Create `tools/test_test_open_questions_gate.sh` (Artifact E), `chmod +x`.
7. Run sibling test `bash tools/test_test_open_questions_gate.sh` → expect `7 passed, 0 failed`. If any fail, STOP + iterate.
8. Append RULE 6 block to `tools/pre-commit-hook-tan-pattern.sh` (Artifact F).
9. Deploy updated hook to 4 targets (Mac + Air wiki + VPS wiki + tools/ canonical). Verify 4-target MD5 parity.
10. Stage all 6 files (3 skills + 2 tools + 1 hook canonical). Verify scanner passes on the staged changes (dogfood). The 3 skill edits each must have `Open questions:` in their new Timeline entries per Artifacts A.5, B.4, C.4 — which they do.
11. Commit with message:
    ```
    doctrine: open-questions write-time capture v1 — mistake-to-skill v1.12 + audit v1.19 + session-operating-contract v1.2 + pre-commit RULE 6 + scanner + sibling test
    ```
12. Auto-sync pushes to VPS bare; fan-out to VPS wiki + Air wiki; wiki-to-runtime-rsync to Air runtime. Verify 4-target HEAD parity + 4-target MD5 parity on the 3 skill files.
13. Wait 5 minutes for gbrain autopilot cycle. Verify 3 `mcp__gbrain__get_page` calls return new versions in `compiled_truth`.
14. Run session-close DONE protocol (AP-17 SOAO + all artifacts). Close at 100% or handoff.
15. Session 51+ SOAO will surface open questions via AP-19 two-tier scan. Monitor for ~30 sessions.

## Rollback plan

If design fails in production:
1. `git revert <commit-hash>` the 5-file commit.
2. Redeploy prior `tools/pre-commit-hook-tan-pattern.sh` (without RULE 6) to 4 targets.
3. Bump the 3 skills one more time with Timeline entries noting reversal + reason.
4. Update this spec's `status:` frontmatter to `reverted-<session-N>` with link to incident handoff.

**No data loss:** forward-only means nothing historical was mutated. All Timeline entries remain intact.

## Known limits shipped with v1 (honest)

Acknowledged in the doctrine — not hidden:

| Limit | Mitigation (v1) | Upgrade trigger (v2+) |
|---|---|---|
| Tier 1 recency bias | Tier 2 global `[contradiction]`/`[weak-edge]` scan | If Tier 2 surfaces >20 items session-open sustained over 5 sessions |
| Resolution is convention-only | `Resolves: <skill> <date> v<X.Y.Z> [<tag>] —` structured grep | If global grep shows orphan `[contradiction]` tags aged >10 sessions |
| `none` lazy default | `--audit-none` reports ≥3 consecutive; major-bump WARN | If `--audit-none` shows >50% of skills chronically `none` |
| Diff fragility on amend/rebase/cherry-pick | Scanner SKIPs ambiguous patterns; `--no-verify` operator-only | If 3+ false-REJECTs reported in a month |
| No mechanical priority queue for `[contradiction]` | Manual operator escalation at session-open | If `[contradiction]` count grows >30 across all skills |
| 7-tag vocabulary may not fit all cases | Default `[open-question]` catch-all; extensible via future AP | If post-30-sessions audit shows <5 tags actually used |

## Evolution path (v2+ triggers)

- **v2 candidates** (trigger-based, not speculative):
  - `OPEN_QUESTIONS.md` aggregate file with backlinks — IF v1 resolution-by-grep proves fragile after 30 sessions.
  - Mechanical `[contradiction]` priority queue (YAML field, not separate table) — IF v1 manual escalation misses.
  - Expanded tag vocabulary — IF audit shows v1 tags under-cover.
- **v3+ candidates** (only if v1+v2 insufficient):
  - Nightly resolver cron — IF the manual write-resolution loop degrades at >5 sessions/day scale.
  - Full Neo-style schema — IF the substrate genuinely needs what Neo's SQL provides.

Karpathy iterative hardening: ship v1, measure, earn v2 with evidence.

## Appendix — Grok adversarial critique summary (traceability)

Received 2026-04-19 via LiteLLM `grok-reasoning` (xAI Grok 4.20). 5 critique points, verdict "refine."

| # | Critique | Decision |
|---|---|---|
| 1 | Scanner checks presence, AP-19 expects position | **Accept.** Scanner now verifies FINAL 2-space bullet (structural position). |
| 2 | Resolution drift — no mechanical backlink | **Partial accept.** `Resolves: <skill> <date> v<X.Y.Z> [<tag>] —` structured convention, not separate table. |
| 3 | Diff fragility on amend/rebase/cherry-pick | **Accept.** Scanner SKIPs ambiguous patterns; 2 extra sibling-test fixtures (F, G). |
| 4 | `none` escape hatch → lazy default | **Partial accept.** `none` allowed for cosmetic bumps; WARN (non-blocking) for major bumps; `--audit-none` weekly flag. |
| 5 | Session-open surfacing recency-bias | **Accept.** AP-19 now two-tier: recent window + global `[contradiction]`/`[weak-edge]` scan. |

**Rejected:** Grok suggested "dedicated `OPEN_QUESTIONS.md` with backlinks." Reason: violates Musk step-2 (already deleted that). Ship v1 doctrine-only; earn v2 with evidence.

**Tag expansion from Grok:** added `[dependency-risk]` + `[model-drift]`. Rejected `[strategy-ambiguity]` (falls under `[contradiction]`/`[open-question]`) + `[incentive-misalignment]` (too meta for doctrine gate).

Full critique + refinement evidence in [[DRAFT-BS5C-OPEN-QUESTIONS-DESIGN-2026-04-19]] Block 2/3 sections.

## See also

- [[DRAFT-BS5C-OPEN-QUESTIONS-DESIGN-2026-04-19]] — full design package + Grok critique + refinements
- [[HANDOFF-AUTO-2026-04-19-session-49-bis-tcc-blocker-brainstorm-paused]] — brainstorm open context
- [[skills/audit/SKILL]] — AP-17 SOAO, AP-18 bash-cwd 0-th probe, AP-19 (this spec)
- [[skills/mistake-to-skill/SKILL]] — AP-13 (this spec), AP-11 (version parity base)
- [[skills/session-operating-contract/SKILL]] — Rule 12 (this spec), Rule 6 (failure→skill)
- [[skills/infrastructure/SKILL]] — AP-43 (pre-commit RULE 4 pattern, precedent for RULE 6)

## Meta — this spec's own Open questions

This spec introduces new APs + new Rule — it's a major bump per the doctrine. Therefore NOT `none`:

- Open questions:
  - `[open-question]` At session-80 (~30 sessions post-ship), what tag distribution have we actually used? If `[open-question]` is >70% of all tags, taxonomy is over-specified.
  - `[contradiction]` The spec says "ship v1 doctrine-only; earn v2 with evidence" but also pre-commits to specific v2+ trigger thresholds in the Known Limits table. Triggers ARE speculation — loosen if unearned by session-80.
  - `[weak-edge]` `tools/soao.sh` not yet shipped (session-49 carryover); AP-19 runs manually at session-open until soao.sh exists. Degrades gracefully but doesn't compound without soao.sh.
  - `[dependency-risk]` Weekly `--audit-none` cron not wired in v1; must be wired before anti-abuse WARN compounds into actual discipline.
  - `[model-drift]` Grok-reasoning was the adversarial critiquer; quality floor if Grok unavailable (LiteLLM falls back to `glm-5.1` or `sonnet`) is untested for this specific review class.
  - `[thin-domain]` Doctrine coverage is epistemic-layer-only; no AP captures pure-behavior drift (e.g., agent consistently picks wrong fork despite rule). That's a different AP class — tracked separately in `session-operating-contract` AP-1 (persona cosplay) + `agent-quality`, not here.
