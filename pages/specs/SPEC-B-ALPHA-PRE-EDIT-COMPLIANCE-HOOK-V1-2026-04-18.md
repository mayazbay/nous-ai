---
type: spec
id: SPEC-B-ALPHA-PRE-EDIT-COMPLIANCE-HOOK-V1
title: "SPEC — B-α Pre-Edit Compliance Injection Hook (Mac Claude Code, v1)"
tags: [spec, b-alpha, pre-edit-hook, compliance, ap-15, ap-16, ap-43, karpathy, tan, musk-5-step, 2026-04-18]
date: 2026-04-18
source_count: 0
status: review
last_updated: 2026-04-18
owner: claude-code-mac
related:
  - session-operating-contract
  - mistake-to-skill
  - audit
  - infrastructure
  - AMD-006-auto-memory-session-continuity-substrate
  - LAW-005-obsidian-master
---

# SPEC — B-α Pre-Edit Compliance Injection Hook (v1)

## Summary

Pre-edit compliance injection hook for Mac Claude Code sessions. When Claude is about to Edit/Write/MultiEdit a codified-doctrine file (`pages/skills/*/SKILL.md`, `pages/laws/*.md`, `pages/progress/claude-memory/MEMORY.md`, `feedback_*.md`, any `CLAUDE.md`), the hook surfaces the rules governing that file **before** the edit executes. **Warn-only in v1**; dual-log adversarial telemetry; 2-week babysit evidence → decide v2 escalation.

Closes the **AP-15 defect class** (codification ≠ self-application — agent writes a rule at time T, violates it on an edit at T+30min). Mechanical generalization of the RULE-4 pre-commit pattern to the pre-edit layer.

Conforms to [[session-operating-contract]] v1.0.0. Augments (does not duplicate) existing gates per [[audit]] AP-16 Rule 2.

## Problem

Session 46 evidence: Claude codified AMD-006 Rule 2 (MEMORY.md top-block-prepend) in Phase J at 11:45 KZT, then at 12:20 KZT wrote a MEMORY.md block that violated Rule 2. Round-1 deep-audit did not catch it; Round-2 deep-audit caught it. Absorbed as `audit` AP-15. Same session: `audit` v1.13 bumped with Timeline entry describing AP-14 but never added the AP-14 bullet to Anti-Patterns section — orphan rule. Existing pre-commit RULE 4 gate caught neither at commit time because neither triggers a version-parity drift; both are semantic compliance drifts.

**Existing gates cover:**
- **pre-commit RULE 4** (`infrastructure` AP-43): SKILL.md frontmatter↔H1 parity at commit time
- **pre-push parity** (`infrastructure` AP-35): hook MD5 parity at push time
- **pre-receive** (VPS bare): LESSON count guard + LESSON rename guard

**Uncovered gap:** semantic compliance with recently-codified rules DURING an edit. No mechanical gate fires between "rule written" and "edit made." AP-15 is the doctrine; this spec is the mechanical gate.

## Goals

- Reduce AP-15-class drifts to zero during babysit
- Make rule-surfacing mechanical, not discipline-dependent
- Preserve auditor-target independence ([[audit]] AP-16 Rule 4) → warn-only, Claude decides
- Ship adversarial telemetry ([[audit]] AP-16 Rule 3) → measurable precision, not theater
- Zero production-breaking incidents (never block an edit inadvertently)

## Non-goals (deferred)

- **B-β Air factory pre-task injection** — scope for post-babysit (extend to `context_injector_v3` on Air)
- **Blocking mode** — requires independent-actor design that does not violate AP-16 Rule 4
- **Cross-agent coverage** — Mac Claude Code only in v1
- **Flag-file bypass** — deleted per Musk step-2 discipline; add back only if babysit shows need
- **Tag-retrofit on existing rules** — Option A from Q5 rejected; v1 uses disk-read + regex extraction (Option B)

## Architecture — Shape A (shell-script)

Single-script design per Musk step-3 simplify + Tan GStack minimalism. Python helper deferred to v2 only if rule-format diversity makes bash extraction fragile.

```
~/.claude/hooks/b-alpha-pre-edit.sh        # PreToolUse hook (~150 lines bash)
~/.claude/hooks/b-alpha-drift-scan.sh      # nightly scanner (~50 lines bash)
~/.claude/logs/b-alpha/firings.jsonl       # pre-edit firings log (append-only)
~/.claude/logs/b-alpha/drifts.jsonl        # post-edit compliance log (append-only)
```

No flag-file bypass. No Python runtime dependency. No config file (mapping inline in script for v1).

## Components

### Component 1 — `b-alpha-pre-edit.sh` (PreToolUse hook)

Fires on `Edit` / `Write` / `MultiEdit` tool calls via Claude Code PreToolUse hook spec.

**Inputs (from hook env):** `tool_name`, `file_path` (absolute path).

**Flow:**
1. **Tool filter.** If `tool_name` not in {Edit, Write, MultiEdit} → exit 0 silent.
2. **Path filter.** If `file_path` does not match any narrow-path pattern → exit 0 silent. Patterns:
   - `*/pages/skills/*/SKILL.md`
   - `*/pages/laws/*.md`
   - `*/pages/progress/claude-memory/MEMORY.md`
   - `*/pages/progress/claude-memory/feedback_*.md`
   - `**/CLAUDE.md` (project + vault + any nested)
3. **Mapping lookup.** Inline dispatch: path pattern → list of applicable skill pages.
4. **Disk read + regex extract.** For each applicable skill, read current `SKILL.md` from Mac vault; regex-extract rule headlines matching three patterns:
   - `^- \*\*AP-([0-9]+): ([^.]+)\.\*\*` (AP bullets)
   - `^### AP-([0-9]+): (.+)$` (AP headings)
   - `^([0-9]+)\. \*\*([^.]+)\.\*\*` (numbered "Current rules")
5. **Format.** Plain stderr markdown-lite:
   ```
   ⚠ B-α pre-edit check — N rules apply to <path>:

     [<skill>:<rule-id>] <headline>
     ...

   (non-blocking · logged · warn-only v1)
   ```
6. **Hard byte cap.** If total formatted output > 2048 bytes, truncate rule list with `(...N more; cap 2KB)`.
7. **Log.** Append JSON line to `firings.jsonl`:
   ```json
   {"ts":"<iso8601>","tool":"Edit","path":"<file_path>","rules_surfaced":["mistake-to-skill:AP-11","audit:AP-15"],"bytes":487,"exit":0}
   ```
8. **Exit 0** (warn-only; edit proceeds).

**Graceful failure** (all exit 0):
- File read fails → log `exit_status:"source_unavailable"` and continue
- Regex extraction fails or produces zero rules → log `exit_status:"extraction_empty"` and continue
- Mapping miss → log `exit_status:"no_rules_for_path"` and continue
- Script crash (unexpected) → trap handler logs `exit_status:"crash"` and exits 0

### Component 2 — `b-alpha-drift-scan.sh` (nightly adversarial scanner)

Fires via launchd `com.nous.b-alpha-drift-scan`, `StartCalendarInterval` 04:15 KZT daily.

**Purpose** ([[audit]] AP-16 Rule 3): verify whether surfaced rules actually prevented drift. Without this, `firings.jsonl` is self-theater.

**Flow:**
1. Read `firings.jsonl` entries from last 24h.
2. For each entry, dispatch to a post-edit compliance probe by path class:
   - **`pages/skills/*/SKILL.md`** → run `tools/test_skill_version_parity.sh` on the edited file; pass = no drift
   - **`pages/progress/claude-memory/MEMORY.md`** → parse H2 block headers; extract per-block date + HEAD reference from banner/body; verify reverse-chronological ordering per AMD-006 Rule 2. Drift = out-of-order blocks.
   - **`pages/laws/*.md`** → verify `id:` frontmatter matches filename convention (AMD-NNN or LAW-NNN); H1 matches `id:`
   - **`*/CLAUDE.md`** → byte-growth check (growth > 20% from last commit triggers review flag); grep for "rule"/"never"/"always" patterns that might belong in SKILL.md
   - **`feedback_*.md`** → minimal (frontmatter present + non-empty)
3. Append result to `drifts.jsonl`:
   ```json
   {"ts":"<iso8601>","firing_ts":"<ref>","path":"<file_path>","post_edit_compliance":"pass|fail","drift_detected":false,"detail":"..."}
   ```
4. If `drift_detected == true`: Telegram alert via `tools/telegram_send.sh` (follows LESSON-086 state-change-only pattern; no alert on clean runs).

**Independence ([[audit]] AP-16 Rule 4):** scanner runs from cron on Air (separate actor than the Claude Code session that made the edit). Not the same process, not the same model, not the same memory. This is the independent-verifier AP-16 Rule 4 requires. 

### Component 3 — Path → skill mapping (inline in `b-alpha-pre-edit.sh`)

```
pages/skills/*/SKILL.md            → mistake-to-skill, infrastructure (AP-43), audit (AP-10/14/15/16)
pages/laws/*.md                    → mistake-to-skill, LAW-005
pages/progress/claude-memory/MEMORY.md → AMD-006, audit (AP-15)
pages/progress/claude-memory/feedback_*.md → (minimal — append-mostly; surface: "feedback memory; edits rare; preserve tone")
CLAUDE.md (any location)           → RULE ZERO (top of CLAUDE.md), LAW-005, session-operating-contract
```

~5 entries. Trivially extended; babysit-review tunes based on which surfacings correlate with drift prevention.

## Data flow

**Pre-edit path (synchronous):**
```
Claude tool call (Edit/Write/MultiEdit)
  ↓
Claude Code PreToolUse hook dispatcher
  ↓
b-alpha-pre-edit.sh
  ├─ tool filter → exit 0 if not edit-class
  ├─ path filter → exit 0 if not substrate
  ├─ mapping lookup (inline)
  ├─ disk read SKILL.md(s)
  ├─ regex extract headlines
  ├─ format stderr (≤2 KB)
  ├─ append firings.jsonl
  └─ exit 0
  ↓
Claude Code proceeds with the tool call
  ↓
Edit happens; Claude sees stderr in context as tool feedback
```

**Post-edit adversarial path (asynchronous, daily):**
```
launchd com.nous.b-alpha-drift-scan @ 04:15 KZT
  ↓
b-alpha-drift-scan.sh
  ├─ read firings.jsonl (last 24h)
  ├─ per entry: dispatch probe by path class
  │   ├─ SKILL.md    → test_skill_version_parity.sh
  │   ├─ MEMORY.md   → block-ordering check
  │   ├─ pages/laws/ → id ↔ filename ↔ H1 parity
  │   ├─ CLAUDE.md   → byte-growth + rule-pattern grep
  │   └─ feedback_*  → minimal existence check
  ├─ append drifts.jsonl
  └─ on drift_detected: telegram_send.sh alert
```

## Error handling

Per [[session-operating-contract]] Rule 5 (`graceful fail`):

- Hook-layer crash / file unavailable / extraction empty → exit 0 + log `exit_status` field + continue
- Drift-scan failure → log, alert on transition only (LESSON-086)
- No edit is ever blocked by hook infrastructure failure

Single escape: `mv ~/.claude/hooks/b-alpha-pre-edit.sh ~/.claude/hooks/b-alpha-pre-edit.sh.disabled` (manual file-rename disables the hook entirely). Documented in spec; not a scripted flag-file.

## Testing (ships WITH v1, not after)

Per [[session-operating-contract]] Rule 10 (tiny-team leverage) + [[audit]] AP-16 Rule 3 (adversarial):

- **`tools/test_b_alpha_extraction.sh`** — unit tests: feed fixture SKILL.md files, assert expected rule headlines extracted. Covers each of 3 regex patterns. Pass = extract count matches expected; fail = count mismatch or wrong headline text.
- **`tools/test_b_alpha_integration.sh`** — integration test: synthesize a test MEMORY.md with known out-of-order H2 blocks → run `b-alpha-drift-scan.sh` against a synthetic firings entry → assert `drift_detected == true`. Adversarial: proves the scanner actually catches drift, not just passes theatrically.
- **`tools/test_b_alpha_graceful.sh`** — failure-mode tests: feed missing file, malformed SKILL.md, mapping-miss path → assert hook exits 0 with correct `exit_status` field in log.

All three test harnesses extend the pattern from `tools/test_pre_receive_lesson_count_guard.sh` (session 45 shipped): sandbox-invoke-assert-cleanup. No new test framework.

## Rollout plan

1. **BS6 (this doc)** — spec written + committed + 4-way synced
2. **BS7** — spec self-review: AP-1 persona grep, placeholder scan, internal consistency check
3. **BS8** — Madi reviews committed spec
4. **BS9** — invoke `writing-plans` skill to produce implementation plan
5. **Implementation in a fresh session** (current session is long; fresh context makes DONE-protocol verification cleaner):
   - Ship Shape A hook + drift scanner + 3 test harnesses
   - Deploy: `~/.claude/hooks/b-alpha-pre-edit.sh` installed, `com.nous.b-alpha-drift-scan` plist loaded on Air
   - Dry-run: trigger 3 synthetic edits on fixture files, verify firings.jsonl populated, drift scanner runs clean
6. **Babysit phase — 14 days:**
   - Daily: glance at firings.jsonl + drifts.jsonl
   - End of babysit: review:
     - Firings count per rule (prune rules that fire zero times as noise)
     - Drifts count (non-zero drift in covered paths = v1 working; zero drift could = either clean behavior OR the scanner is insufficient)
     - Agent-behavior: did surfaced rules actually change what Claude did? (adversarial self-evaluation; record in follow-up spec)
7. **Post-babysit v2 decisions** (separate SPEC when evidence warrants):
   - Prune noisy rules
   - Add or remove paths per evidence
   - Consider escalation: blocking mode with independent verifier
   - Extend to Air factory (B-β) — integrate into `context_injector_v3`

## Success criteria

Minimum for "v1 succeeded":

- ✅ Hook fires on ≥10 real substrate edits during 14-day babysit
- ✅ `drifts.jsonl` records ≥1 probe-run per firing (proves adversarial loop fires)
- ✅ Zero production-breaking incidents — no edit inadvertently blocked
- ✅ No AP-1 regression (hook stays infrastructure-focused; no persona framing)
- ✅ 4-way parity maintained throughout babysit (Mac = VPS bare = VPS wiki = Air wiki)

Stretch (evidence for v2 design):

- Correlation visible between rule surfacings and reduced drift on matched paths
- Rules prune-able with evidence (e.g., "rule X fired 40 times, drift rate unchanged → noise")
- Pattern for v2 scope emerges (medium-path expansion? blocking escalation?)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Alert fatigue — I skim past surfacings, they become noise | Dual-log prune at end of babysit; noisy rules removed with evidence |
| Wrong rules surface for a path | Start with 5-entry narrow mapping; babysit-review tunes |
| Hook crashes inadvertently block edits | Graceful-fail (exit 0 on error) + trap handler; single manual file-rename disables |
| Self-theater (firings log without drift log) | AP-16 Rule 3 adversarial scanner ships IN v1, not deferred |
| Auditor-target independence violation (AP-16 Rule 4) | Warn-only in v1; scanner runs from separate cron actor; no self-attestation |
| AP-1 persona regression | Spec grep-check on commit; no "god-level" framing in hook, docs, logs |
| Rule format diverges (break bash regex) | Three regex patterns cover current formats; diversification triggers Shape B Python migration |

## Conformance to [[session-operating-contract]] v1.0.0

| Contract rule | Applied |
|---|---|
| R1 session-start | N/A for spec; binds implementation session |
| R2 ground-truth | All file paths + hook MD5s + test names cite actual files |
| R3 RULE ZERO | Zero new LESSON; spec delta + skill bumps are the audit trail |
| R4 DONE protocol | Binds implementation; spec-write closes with DONE artifacts |
| R5 can't-verify | Implementation will cite exact commands for post-deploy probes |
| R6 failure → skill | Built into B-α itself (drift detected → skill absorption trigger) |
| R7 hard-banned | No persona, no "done-without-proof", no Telegram MCP, no LESSON, no vibe-100% |
| R8 triggers | N/A |
| R9 Musk 5-step | Applied: deleted flag-file bypass, deleted Shape C static-index, kept minimum |
| R10 tiny-team leverage | Hook is new gate; drift scanner extends `test_skill_version_parity.sh`; tests extend pre-receive harness pattern |
| AP-1 treadmill | Hook named `b-alpha-pre-edit`, not a persona; docs reference infrastructure |

## See also

- [[session-operating-contract]] — the binding runtime contract this spec conforms to
- [[audit]] — AP-14/AP-15/AP-16 drift discipline; AP-16 Rule 3 adversarial probe + Rule 4 independence
- [[mistake-to-skill]] — AP-11 4-check ritual (surfaced by this hook on SKILL.md edits)
- [[infrastructure]] — AP-43 pre-commit RULE 4 precedent
- [[AMD-006-auto-memory-session-continuity-substrate]] — governs MEMORY.md edits (surfaced by this hook)
- [[LAW-005-obsidian-master]] — vault as master
- [[planning-discipline]] — brainstorm → spec → plan → implementation
- [[HANDOFF-AUTO-2026-04-18-session-46-POST-DEEP-AUDIT-compounding-gates]] — the session that produced AP-15 (the defect class this spec closes)

## Timeline

- **2026-04-18** | v1.0 spec drafted — session 46 Round-2 post-deep-audit brainstorm with Madi. Filters applied: Elon 5-step (step-2 delete eliminated flag-file bypass + Shape C static-index + Python helper for v1) + Karpathy minimalism + Tan GStack shell-script doctrine + Stanford calibration discipline + Perplexity citation-precision + lean-founder tiny-team (Levels/Cursor/Midjourney). Conforms to [[session-operating-contract]] v1.0.0 + [[audit]] AP-16 v1.15. Addresses AP-15 defect class caught in session 46 Round-2 (AMD-006 Rule 2 violation within 35 min of codification). No new LESSON (RULE ZERO).
