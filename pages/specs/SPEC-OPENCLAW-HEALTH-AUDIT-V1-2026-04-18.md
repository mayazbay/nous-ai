---
type: spec
id: SPEC-OPENCLAW-HEALTH-AUDIT-V1-2026-04-18
title: "OpenClaw + Factory 3-Lens Health Audit v1 (SAFE / HEALTHY / SYNCED)"
tags: [spec, audit, openclaw, factory, health, 3-lens, karpathy, elon-5-step, session-48, 2026-04-18]
date: 2026-04-18
source_count: 0
status: reviewed
last_updated: 2026-04-18
owner: claude-code-mac
related:
  - audit
  - infrastructure
  - HANDOFF-AUTO-2026-04-18-session-47
  - HANDOFF-AUTO-2026-04-18-session-48
  - AUDIT-OPENCLAW-HEALTH-2026-04-18
---

# SPEC — OpenClaw + Factory 3-Lens Health Audit v1

**Session:** 48, 2026-04-18 (Mac, Opus 4.7). Scope = **S2 + S6** of session-48 decomposition (health audit + sync parity). S3 (apply slowdown-fix), S4 (GStack UX), S5 (Ops Manager skill), S1 (eval harness) all deferred to subsequent sessions, driven by evidence from THIS audit.

**Driver:** Madi, session 48: *"is it safe? are openclaw and hermes at 100%?"* — applied to OUR stack (not external Hermes/Nous Research).

**Decision standard:** Elon 5-step (question-requirement → delete → simplify → accelerate → automate-LAST) × Karpathy (compounding substrate) × Tan (pay-down-debt, close-loops) × Stanford agent-eval adversarial (Berkeley RDI 2026 anti-exploit) × billion-dollar-solopreneur velocity (ship-evidence-every-session).

## 1. Purpose & Non-Purpose

**Purpose:** Produce an adversarially-scored snapshot of OpenClaw + factory + LiteLLM + Telegram poller + gbrain + QMD + wiki-sync state, answering on evidence:

- **SAFE** — can we apply known slowdown-fix patterns without breaking our stack? Are secrets / tokens / hooks in good shape?
- **HEALTHY** — is the substrate actually functional end-to-end (not just "Up")?
- **SYNCED** — is every compound-gated surface (hooks, skills, gbrain, QMD, launchd, container) in true parity, including working-tree drift invisible to HEAD checks?

**Non-purpose:** NOT building a monitoring tool this session. Elon step 5 — automation LAST, and only from evidence. Session 49 decides automation from this session's findings. NOT a new skill file — extend existing `audit` skill. RULE ZERO — 0 new LESSON files.

## 2. Three Lenses (adversarial probes)

### 2a. SAFE — "what might I break unknowingly?"

| ID | Probe | Commands | Pass criterion |
|---|---|---|---|
| P-SAFE-01 | Cron/launchd bloat | `ssh air 'launchctl list \| grep com.nous \| wc -l'` + per-job last-exit via `launchctl print gui/501/<job>` | ≤20 jobs; all consistent exit status; any consistently-failing job flagged red |
| P-SAFE-02 | `--light-context` on crons | `ssh air 'grep -l "light-context" ~/Library/LaunchAgents/com.nous*.plist'` vs full list | Report which have/don't; identify S3 candidates |
| P-SAFE-03 | Session records accumulating | `ssh air 'find ~/.claude -name "*.jsonl" -size +1M \| wc -l'` + total session dir size | Report raw counts; flag >500 sessions or >1GB dir as slowdown contributor |
| P-SAFE-04 | Prompt input bloat (MEMORY / CLAUDE / SKILL) | `wc -l MEMORY.md CLAUDE.md pages/skills/*/SKILL.md \| sort -n \| tail -15` + total in bytes | Top-10 reported; flag any single file >25 KB; MEMORY.md trim requires AMD-006 veto |
| P-SAFE-05 | APK_BOT_TOKEN rotation state | Check Air launchd plist env + git log for token rotation commits | Flag if no rotation commit in >30 days; cross-ref 5-session carryover |
| P-SAFE-06 | Secret perms (world-readable) | `ssh air 'find ~/nous-agaas -name "*.env" -exec ls -la {} \;'` + VPS same | Any world-readable secret = 🔴 |
| P-SAFE-07 | Hook bypass surface | `git reflog --date=iso --all \| grep -i "no-verify"` (last 30 days) across Mac+Air+VPS | Expect 0; any hit = 🔴 |

### 2b. HEALTHY — "substrate could be lying about being up"

| ID | Probe | Commands | Pass criterion |
|---|---|---|---|
| P-HEALTH-01 | OpenClaw container | `ssh air 'docker ps --format "{{.Names}} {{.Status}}" \| grep openclaw'` + `docker inspect openclaw --format '{{.State.Health.Status}}'` | `healthy` + uptime ≥1h |
| P-HEALTH-02 | OpenClaw /ask roundtrip (adversarial — beyond /health) | trivial /ask probe returning a specific token | 200 + evidence-bearing response |
| P-HEALTH-03 | LiteLLM liveliness | `ssh air 'curl -sf http://localhost:4000/health/liveliness'` | `"I'm alive!"` |
| P-HEALTH-04 | LiteLLM actual completion (adversarial — beyond /liveliness) | minimal chat completion with GLM-5.1 | Non-empty non-error token output |
| P-HEALTH-05 | Telegram poller state + recency | `launchctl print gui/501/com.nous.telegram-poll` → LastExitStatus + last log line mtime | exit 0 + last log <5 min old |
| P-HEALTH-06 | Per-launchd-job exit status (17 jobs) | loop `launchctl print` across all `com.nous.*` | 0 (or intentional 1 for oneshots) per job |
| P-HEALTH-07 | gbrain health + spot-sample | `mcp__gbrain__get_health` + `get_stats` + `get_chunks` on 3 newest timeline entries | embed_coverage ≥98%; sampled chunks roundtrip |
| P-HEALTH-08 | QMD freshness | `mcp__nous-wiki-qmd__status` compared to `git log -1 --format=%cd` | lag ≤6h |
| P-HEALTH-09 | HARD-RULE-1 violation check (Telegram 409) | `ssh air 'tail -100 ~/Library/Logs/com.nous.telegram-poll.err.log \| grep -i 409'` | 0 hits |

### 2c. SYNCED — "HEAD parity hides working-tree drift"

| ID | Probe | Commands | Pass criterion |
|---|---|---|---|
| P-SYNC-01 | 4-way HEAD parity | `git rev-parse HEAD` × Mac vault + Air wiki + VPS wiki + VPS bare | All 4 identical |
| P-SYNC-02 | 4-way working-tree drift (adversarial — beyond HEAD) | `git status --porcelain \| wc -l` × all 4 | 0 across all |
| P-SYNC-03 | Hook MD5 parity (pre-commit / pre-push / pre-receive / TaskCompleted) | `md5` across all targets | Match session-47 recorded values |
| P-SYNC-04 | Skill runtime MD5 — container probe (AP-13 closure) | `md5 pages/skills/*/SKILL.md` (vault) vs Air `~/nous-agaas/skills/*/SKILL.md` vs `docker exec openclaw md5sum /opt/nous-agaas/skills/*/SKILL.md` | All 3 paths match vault per-skill |
| P-SYNC-05 | Skill frontmatter ↔ H1 parity | `bash tools/test_skill_version_parity.sh` | `OK:` clean |
| P-SYNC-06 | SKILL.md MD5 citation ↔ reality | `bash tools/test_skill_md5_citations.sh` | `OK:` clean |
| P-SYNC-07 | gbrain H1 ↔ wiki H1 parity (all 20 skills) | `mcp__gbrain__get_page` first H1 vs wiki first H1 per skill | All 20 match |
| P-SYNC-08 | Carryover disk-reality mapping | F1 (wg-satory handshake state), M3 (backup.sh Desktop path), APK_BOT_TOKEN rotation | Each carryover still reflects real disk/runtime state |

**Total probes: 24** (7 SAFE + 9 HEALTHY + 8 SYNCED).

## 3. Scoring rubric (Berkeley RDI anti-exploit)

Each lens independently scored.

- **100%** — every probe passed AND the audit explicitly tried to catch the substrate lying (P-HEALTH-02 actual roundtrip beyond /health, P-HEALTH-04 completion beyond /liveliness, P-SYNC-02 working-tree beyond HEAD, P-SYNC-04 container MD5 beyond vault, P-SYNC-07 gbrain-vs-wiki H1 beyond MD5-of-vault). If only liveliness + HEAD probes ran, it is NOT 100% regardless of pass count.
- **Yellow-N** — N probes returned inconclusive / lag-recoverable.
- **Red-N** — N probes caught real drift.

Report includes full probe list (passed + failed), evidence snippets per probe, not just the headline. Silent success = exploit surface per Berkeley RDI 2026.

## 4. Execution model — MAC RUNS THE PROBES (correction 2026-04-18 mid-session)

**Correction absorbed:** the v0 of this spec proposed delegating to GLM-5.1 on Air factory. **That violates the Berkeley RDI adversarial rubric** — factory is IN the audit scope (P-HEALTH-01/02/04 + P-SYNC-04 container-MD5). A substrate auditing itself is the canonical exploit. Classic trap: "factory says it's healthy" = tautology.

**Right pattern:** Mac (Opus 4.7, this session) runs all 24 probes against Air/VPS targets via ssh / curl / mcp. Mac is *independent* of the audited substrate. Factory is *probed by* Mac, never *running* Mac's audit. This preserves the adversarial lens.

**Catching this mid-flight is itself evidence** that the adversarial-lens discipline works. Absorbed as AP-16 rule (see §5): "the auditor MUST be independent of the audit target; delegation to the target IS the exploit."

**Probe-is-broken vs target-is-broken distinction:** if Mac's probe command fails (syntax error, host unreachable, ssh auth broken), score = `red` with `evidence_detail="probe-itself-broken"`. Distinguishes my tooling breaking from the substrate breaking.

**Adversarial redundancy (retained from v0):** for HEALTH probes with primary + secondary (e.g., P-HEALTH-03 /liveliness + P-HEALTH-04 actual completion), run BOTH. Discrepancy → red.

**Raw output format:** YAML to `pages/audits/AUDIT-OPENCLAW-HEALTH-2026-04-18-raw.yaml`, schema:

```yaml
audit_id: AUDIT-OPENCLAW-HEALTH-2026-04-18
run_host: mac (Opus 4.7, session 48)
run_timestamp: YYYY-MM-DDTHH:MM:SS+06:00
spec_version: SPEC-OPENCLAW-HEALTH-AUDIT-V1-2026-04-18
probes:
  - id: P-SAFE-01
    cmd: "<exact command>"
    exit: <int>
    stdout: "<trimmed, ≤20 lines>"
    stderr: "<trimmed>"
    score: green|yellow|red
    evidence_detail: "<one-line summary>"
headline:
  safe: "100%" | "yellow-N" | "red-N"
  healthy: "..."
  synced: "..."
overall: "100%" | "yellow" | "red"
```

## 5. Absorption path (evidence-dependent)

- **If ≥1 real drift caught:** extend `audit` skill v1.14 → v1.15 with **AP-16** (OpenClaw/factory 3-lens audit — when to run, how to score, delegation pattern). gbrain timeline entry on `pages/skills/audit/skill`.
- **If 0 drift caught:** absorb AP-16 as lighter rule (negative result IS evidence substrate is in good shape; codify so future agents know the probe was tried + clean). Skill still bumps v1.14 → v1.15.
- **Either way:** write `pages/audits/AUDIT-OPENCLAW-HEALTH-2026-04-18.md` with interpreted findings, per-lens scores, absorbed rule text.

## 6. Explicit deferrals (Elon step 5)

- **No tool build this session.** Session 49 decides automation *from this session's evidence*.
- **No new skill file.** `audit` is canonical home.
- **S3 (apply slowdown-fix) deferred.** Evidence from P-SAFE-01..04 will drive S3 scope next session.
- **S5 (Ops Manager skill upgrade) deferred.** Compare to our probe set; may already overlap heavily with `audit` + `infrastructure`.
- **S4 (GStack UX) deferred.** Orthogonal to health — queue as separate brainstorm.
- **S1 (eval harness) deferred.** Biggest strategic value but premature; benefits from a clean substrate.

## 7. Success criteria for session 48

1. This spec committed + synced 4-way.
2. Delegation run completed (Air factory returns evidence YAML), OR Mac-fallback audit completed if factory unreachable (carryover flagged).
3. `AUDIT-OPENCLAW-HEALTH-2026-04-18.md` written with findings.
4. `audit` skill bumped to v1.15 with AP-16 absorbed + gbrain timeline entry.
5. `HANDOFF-AUTO-2026-04-18-session-48.md` written with evidence, carryovers, session-49 first step.
6. RULE ZERO upheld — 0 new LESSON files.
7. 4-way HEAD parity + 4-target hook MD5 at close.

## 8. Timeline

- **2026-04-18** | Spec drafted session 48. Decision (E) approved by Madi. Scope = S2+S6 only. Billion-dollar-solopreneur + Elon 5-step + Karpathy compounding standard applied. [[HANDOFF-AUTO-2026-04-18-session-48]]
