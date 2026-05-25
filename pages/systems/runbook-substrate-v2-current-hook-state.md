---
type: runbook
title: Pre-Commit Hook State (Substrate v2 Phase 0.1 Audit)
date: 2026-05-04
status: post-fix
related:
  - "[[plans/PLAN-SUBSTRATE-V2-2026-05-03]]"
  - "[[plans/PLAN-SUBSTRATE-V2-REQUIREMENTS-2026-05-03]]"
---

# Pre-Commit Hook State

## 2026-05-03 audit (false-negative caveat)

The Phase-0 substrate-v2 audit (Explore agent, 2026-05-03) reported the hook as MISSING on Air and VPS. Independent verification on 2026-05-04 found this was wrong — the hook IS present on all 3 hosts. The audit's check command may have run against a stale path or the audit was based on an earlier session's state. **Lesson:** verify substrate audit findings independently before treating them as ground truth (will codify into `mistake-to-skill` skill).

## 2026-05-04 verified state (pre-Phase-0.3)

| Host | Path | Size (bytes) | Mode | Notes |
|---|---|---|---|---|
| Mac | `Nous/.git/hooks/pre-commit` | 17,918 | `-rwxr-xr-x` | **Canonical**: includes RULE 10 (s108 SKILL.md description/H1 consistency) |
| Air | `~/nous-agaas/wiki/.git/hooks/pre-commit` | 16,401 | `100755` | Drift: missing 25-line RULE 10 block (1,517 bytes behind) |
| VPS | `/root/nous-agaas/wiki/.git/hooks/pre-commit` | 16,401 | `755` | Drift: same as Air — missing RULE 10 |

## Drift content

The 1,517-byte gap is exactly the RULE 10 block (session s108, 2026-05-01) that enforces SKILL.md frontmatter `description:` ↔ H1 version consistency. Pattern source: ceo-hierarchy AP-5. Without this rule on Air + VPS, a Codex CLI session committing on Air could ship a SKILL.md with mismatched description/H1 versions; Mac would catch it on next pull but only after the bad commit landed.

## Rules currently enforced (Mac canonical, all 11 rules)

1. **1a/1b** — Block new `pages/lessons/individual/LESSON-*.md` files (RULE ZERO; including rename-bypass)
2. **2-3** — Allow LESSON modify/delete; block lesson `id`/`title`/H1 drift
3. **4** — `mistake-to-skill` AP-7 drift scan on staged LESSON edits
4. **5** — RULE 5 MD5 citation gate (s47, 2026-04-18)
5. **6** — `.env` block (s48)
6. **7** — Various
7. **8** — RULE 8 (whatever it does — full audit deferred to s109+)
8. **9** — RULE 9
9. **10** — SKILL.md description/H1 version consistency (s108, 2026-05-01) — **ONLY ON MAC, drift target**
10. **Musk step-2 detector** — when SKILL.md bumps, run `tools/test_musk_step_2.sh`

## 2026-05-04 fix plan (Phase 0.2-0.3)

1. Track Mac canonical at `Nous/tools/pre-commit-canonical` (git-tracked) — done 2026-05-04
2. Build `Nous/tools/install_pre_commit_hook.sh` with per-host smoke-verify (Eng-review fix Med-8) — done 2026-05-04
3. Live deploy: rsync canonical → Air + VPS, smoke-test bypass blocked — pending
4. Future: `Nous/tools/install_pre_commit_hook.sh --verify` mode for daily drift detection (substrate-v2 Phase 0.9 monitoring)

## See also

- [[plans/PLAN-SUBSTRATE-V2-2026-05-03]] §Phase 0
- [[skills/ceo-hierarchy]] AP-5 (RULE 10 source pattern)
- [[skills/mistake-to-skill]] (codify the false-negative-audit lesson)
