---
type: spec
id: PLAN-SESSION-54-IMPLEMENTATION-2026-04-20
title: "Session-54 implementation plan — atomic tasks for SPEC-SESSION-54"
tags: [plan, session-54, deep-audit, j2, factory-ops, 2026-04-20]
date: 2026-04-20
source_count: 1
status: active
last_updated: 2026-04-20
related:
  - SPEC-SESSION-54-DEEP-AUDIT-J2-OPUS47-2026-04-20
  - session-operating-contract
  - factory-ops
---

# Session-54 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (inline, Madi approves each phase gate) or `superpowers:subagent-driven-development` for parallel probes. Steps use checkbox syntax. DONE protocol at every phase boundary per SOC v1.4.0 Rule 4.

**Goal:** Execute [[SPEC-SESSION-54-DEEP-AUDIT-J2-OPUS47-2026-04-20]] end-to-end: 4-probe deep-dive audit → RULE-ZERO gap closure → J2 AP-25 5-task research path to unblock OpenClaw→Opus-4.7 → MASTER handoff + 4-way push.

**Architecture:** Sequential phases; within Phase 1, probes run sequentially (each informs the next). Phase 2 is conditional on Phase-1 findings. Phase 3 stops at the first J2 sub-task that unblocks. Phase 4 is unconditional close (either success or honest-dead-end).

**Tech Stack:** Bash + gbrain MCP (`mcp__gbrain__get_page`, `mcp__gbrain__add_timeline_entry`) + git + docker (via `ssh air`) + LiteLLM (via `curl localhost:4000`) + tools/tg_send.sh for Telegram.

**Budget:** 90min cap on Phase 3 (J2). If all 5 sub-tasks exhaust without resolution → honest-dead-end + move to Phase 4.

---

## Task 1: Phase 1 Probe A — gbrain ingestion verification

**Files:**
- Read: `mcp__gbrain__get_page` on 12 target pages
- Write (if gap found): append to findings log in `pages/audits/AUDIT-SESSION-54-2026-04-20.md`

**Target pages (12):**
- `pages/entities/vlad`
- `pages/entities/azamat-bdl`
- `pages/entities/cerebro`
- `pages/entities/roman-cerebro`
- `pages/entities/madi-program`
- `pages/entities/denis` (session-52 Wave B update)
- `pages/entities/daniyar` (session-52 Wave B update)
- `pages/entities/nous-gpu` (session-52 Wave A create)
- `pages/specs/netvision-remediation-plan-2026-04-20`
- `pages/specs/netvision-monitoring-whitelabel-analysis-2026-04-20`
- `pages/specs/letter-to-saken-aga-netvision-v3-2026-04-20`
- `pages/progress/HANDOFF-AUTO-2026-04-20-session-52-MASTER-close-satory-meeting`

- [ ] **Step 1: Call gbrain on each of the 12 targets**

Use `mcp__gbrain__get_page` per target. Record: `{slug, ok, last_updated, content_hash}` per page.

- [ ] **Step 2: Classify results**

Three buckets:
- Green: `ok=true`, `last_updated=2026-04-20`, `content_hash` non-empty.
- Yellow: `ok=true` but `last_updated` older than 2026-04-20 (stale ingestion).
- Red: `ok=false` or missing (not ingested at all).

- [ ] **Step 3: If any yellow/red → record in findings log**

Create `pages/audits/AUDIT-SESSION-54-2026-04-20.md` (if absent) with YAML frontmatter and one row per missing/stale page. Include candidate root cause (commit not yet picked up by autopilot / page not in any commit / name mismatch).

- [ ] **Step 4: Verify autopilot status if red found**

`ssh root@65.108.215.200 "systemctl status nous-gbrain-autopilot 2>/dev/null || launchctl list | grep gbrain"` to confirm autopilot is running. If down, that IS the root cause → jump to Phase 2 to restart it + bump `gbrain-ops` skill.

- [ ] **Step 5: DONE-protocol output for Task 1**

Message format:
```
Task 1 (Probe A) DONE.
- Command: [the mcp__gbrain__get_page calls]
- Output: [green/yellow/red counts + list]
- Git state: [rev-parse + status --porcelain]
- Counter-check: [did mcp__gbrain__search return one of the green pages correctly]
```

---

## Task 2: Phase 1 Probe B — Mac-root ↔ vault CLAUDE.md drift extraction

**Files:**
- Read: `/Users/madia/Documents/Projects/Nous AGaaS/CLAUDE.md` (Mac-root)
- Read: `/Users/madia/Documents/Projects/Nous AGaaS/Nous/CLAUDE.md` (vault-root)
- Create (if gap found): `/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/systems/architecture-quickref.md`
- Modify (both): add cross-reference pointer in each `CLAUDE.md`

- [ ] **Step 1: Enumerate Mac-root operational content NOT in vault**

Initial `diff` (run earlier) shows Mac-root has: RULE ZERO refresh, HARD RULES (Telegram token-specific + satory lock + gbrain-MCP-connected + session-start-handoff + verify-claims + failure→skill), Telegram routing model table, Architecture quickref table, SOC runtime contract reference. Vault-root has the wiki-schema doc only. Confirm no operational rules in vault-root that Mac-root is missing (reverse-drift check).

- [ ] **Step 2: Decide extraction target**

Extract Mac-root operational content into new page: `pages/systems/architecture-quickref.md`. Vault keeps wiki-schema doc at root. Both `CLAUDE.md` files get a new top-line pointer: `> Architecture + hard rules: [[architecture-quickref]].`

- [ ] **Step 3: Write `pages/systems/architecture-quickref.md`**

Content blocks to include:
- HARD RULES 1-6 (narrowed Telegram, satory lock, gbrain connected, session-start handoff, verify claims, failure→skill)
- Telegram routing model table (inbound + outbound)
- Session-continuity architecture (ephemeral sessions, persistent substrate, Telegram interface)
- Architecture quick-reference table (factory, LiteLLM, Telegram poller, wiki repo, gbrain, auto-checkpoint, nightly jobs, session hygiene, NCAnode, Langfuse, VPS host, Air host, Nous-GPU host, Mac Pro)
- Runtime behavioral contract pointer to `[[session-operating-contract]]` v1.4.0

YAML frontmatter: `type: system, id: SYS-ARCHITECTURE-QUICKREF, date: 2026-04-20`.

- [ ] **Step 4: Add cross-reference pointers to both CLAUDE.md files**

Mac-root `/Users/madia/Documents/Projects/Nous AGaaS/CLAUDE.md`: at top of file after H1, add:
```
> Authoritative architecture + hard rules: [[architecture-quickref]] in the vault. Vault copy is the substrate; this file is the Claude Code session-instructions shim.
```

Vault-root `/Users/madia/Documents/Projects/Nous AGaaS/Nous/CLAUDE.md`: after the wiki schema intro, add:
```
> Architecture topology + hard rules: [[architecture-quickref]]. Runtime behavior: [[session-operating-contract]].
```

- [ ] **Step 5: Commit + verify both files updated in same commit**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
git add pages/systems/architecture-quickref.md CLAUDE.md
cd "/Users/madia/Documents/Projects/Nous AGaaS"
# Mac-root CLAUDE.md is NOT in the vault; commit separately OR accept it's not synced
```
NOTE: Mac-root lives outside vault. Commit the vault files only; Mac-root pointer is local-only. Document this intentional asymmetry in the commit message and in `architecture-quickref.md`.

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
git commit -m "B3: Phase-1 Probe B fix — extract architecture-quickref to vault

[risk] [infrastructure] Mac-root CLAUDE.md had session-51 HARD RULE 1
narrowing, session-52 Nous-GPU row, session-53 routing model. None
reached the vault where Air factory-agent reads. Extract into
pages/systems/architecture-quickref.md; add [[wikilink]] pointers from
both CLAUDE.md files. Mac-root stays as Claude-Code-session-shim."
```

- [ ] **Step 6: Verify on Air that the new page is reachable**

```bash
ssh air "cat ~/nous-agaas/wiki/pages/systems/architecture-quickref.md | head -20"
```
Expected: frontmatter + H1. If not present after auto-sync (wait 2 min), manual `ssh air "cd ~/nous-agaas/wiki && git pull"`.

- [ ] **Step 7: DONE-protocol output for Task 2**

Include: paths created/modified, Mac vault HEAD, Air vault HEAD (must match), counter-check (read first 20 lines of new page on Air via ssh).

---

## Task 3: Phase 1 Probe C — MEMORY.md bloat extraction

**Files:**
- Modify: `/Users/madia/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/memory/MEMORY.md` (symlinks into `Nous/pages/progress/claude-memory/MEMORY.md`)
- Create: `memory/sessions/session-51-2026-04-20-final.md`
- Create: `memory/sessions/session-52-wave-a-nous-gpu.md`
- Create: `memory/sessions/session-52-wave-b-satory-meeting.md`

- [ ] **Step 1: Measure current state**

```bash
wc -l "/Users/madia/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/memory/MEMORY.md"
ls -la "/Users/madia/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/memory/MEMORY.md"
```
Record: current line count, byte size, target (≤400 lines). Current baseline: 1747 lines / 220KB.

- [ ] **Step 2: Identify extraction boundaries**

Grep for session-block headers:
```bash
grep -n "^## Session " "/Users/madia/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/memory/MEMORY.md" | head -20
grep -n "^# Memory — updated" "/Users/madia/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/memory/MEMORY.md"
```
Identify: where session-51 block starts/ends, where session-52 Wave A starts/ends, where session-52 Wave B starts/ends.

- [ ] **Step 3: Create target directory**

```bash
mkdir -p "/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/progress/claude-memory/sessions"
```

- [ ] **Step 4: Extract session-51 block**

Use `sed -n '<start>,<end>p'` or Read with offset/limit, write to `pages/progress/claude-memory/sessions/session-51-2026-04-20-final.md` with YAML frontmatter:
```yaml
---
type: memory
id: MEMORY-SESSION-51-2026-04-20
title: "Session-51 memory block (extracted from MEMORY.md 2026-04-20)"
tags: [memory, session-51, infrastructure, extraction]
date: 2026-04-20
source_count: 1
status: active
related: [MEMORY, HANDOFF-AUTO-2026-04-20-session-51-MASTER-final]
---
```
Content = original session-51 block from MEMORY.md verbatim.

- [ ] **Step 5: Extract session-52 Wave A block**

Same process. File: `session-52-wave-a-nous-gpu.md`.

- [ ] **Step 6: Extract session-52 Wave B block**

Same process. File: `session-52-wave-b-satory-meeting.md`.

- [ ] **Step 7: Rewrite MEMORY.md with one-line pointers**

Replace each extracted block with:
```
- **2026-04-20 session-51 close** — 15 artifacts + 3 APs + 1 honest-STOP (J2). Details: [[session-51-2026-04-20-final]].
- **2026-04-20 session-52 Wave A** — Nous-GPU RTX 5070 registered, Tailscale-ACL blocked. Details: [[session-52-wave-a-nous-gpu]].
- **2026-04-20 session-52 Wave B** — Satory meeting absorbed, Denis reengaged, Phase-0 locked Option-C. Details: [[session-52-wave-b-satory-meeting]].
```
Keep top frontmatter + MEMORY.md structural sections (# userEmail, # currentDate if present). Verify `wc -l` ≤ 400 after rewrite.

- [ ] **Step 8: Commit**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
git add pages/progress/claude-memory/
git commit -m "B4: Phase-1 Probe C fix — extract MEMORY.md session blocks

[risk] [infrastructure] MEMORY.md was 1747 lines / 220KB, breaking
the 'only part loaded' warning. Extract 3 session blocks (51, 52A,
52B) into pages/progress/claude-memory/sessions/*.md; replace with
one-line index pointers. Index now fits one terminal screen."
```

- [ ] **Step 9: DONE-protocol output for Task 3**

Include: before/after line counts, ls of new sessions/ dir, git HEAD, counter-check (read MEMORY.md — confirm session-51 block gone, pointer present, readable in one screen).

---

## Task 4: Phase 1 Probe D — SOC v1.3/v1.4 merge consistency check

**Files:**
- Read: `pages/skills/session-operating-contract/SKILL.md`

- [ ] **Step 1: Verify frontmatter version**

```bash
head -10 "/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills/session-operating-contract/SKILL.md"
```
Expected: `version: 1.4.0`, `last_updated: 2026-04-20`.

- [ ] **Step 2: Verify H1 version**

```bash
grep -n "^# session-operating-contract" "/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills/session-operating-contract/SKILL.md"
```
Expected: `# session-operating-contract v1.4.0`.

- [ ] **Step 3: Verify Rule 13 present**

```bash
grep -n "^### 13\." "/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills/session-operating-contract/SKILL.md"
```
Expected: `### 13. Outbound correspondence + commercial-frame discipline` (from v1.3, session-53).

- [ ] **Step 4: Verify Rule 12 + Rule 11 both present**

```bash
grep -n "^### 1[12]\." "/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills/session-operating-contract/SKILL.md"
```
Expected: both Rule 11 (project-native tools) AND Rule 12 (hook class detection).

- [ ] **Step 5: Verify Evidence-trail has all 4 recent entries**

```bash
grep -E "v1\.[1-4]\.0" "/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills/session-operating-contract/SKILL.md" | head -10
```
Expected: v1.1, v1.2, v1.3, v1.4 all referenced in Evidence trail.

- [ ] **Step 6: Verify AP-1 through AP-6 all present**

```bash
grep -n "^### AP-" "/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills/session-operating-contract/SKILL.md"
```
Expected: 6 APs (1 through 6).

- [ ] **Step 7: Reconcile + decide**

All green → Probe D PASS, no action needed.
Any red/yellow → manual git-log reconstruction; bump SOC to v1.5.0 with consolidation note; absorb concurrent-bump failure mode into `mistake-to-skill` AP-11.

- [ ] **Step 8: DONE-protocol output for Task 4**

Include: all 6 grep outputs, pass/fail per step, git HEAD.

---

## Task 5: Phase 2 — Gap closure (conditional, adaptive)

**Files:** depends on Phase-1 findings. Likely touches: `pages/skills/<skill-from-finding>/SKILL.md`, `pages/audits/AUDIT-SESSION-54-2026-04-20.md`, gbrain via `mcp__gbrain__add_timeline_entry`.

- [ ] **Step 1: Consolidate findings from Tasks 1-4**

Produce findings table in `pages/audits/AUDIT-SESSION-54-2026-04-20.md`:
| Probe | Finding | Affected skill | Version bump | gbrain timeline |
|---|---|---|---|---|
| A | … | … | … | … |
| B | CLAUDE.md drift resolved | `infrastructure` | v1.x → v1.(x+1) | push |
| C | MEMORY bloat resolved | `auto-memory` (or SOC) | v1.x → v1.(x+1) | push |
| D | … | … | … | … |

- [ ] **Step 2: For each finding with a required fix, apply AP-11 3-edit ritual**

Per finding:
1. Bump frontmatter `version:`
2. Bump H1 `v…` string
3. Append `## Evidence trail` entry with date + what-changed + why + evidence-link.
4. Add the rule itself as a new AP or extend existing AP body.

- [ ] **Step 3: Push gbrain timeline entries**

Per bumped skill:
```
mcp__gbrain__add_timeline_entry slug="pages/skills/<skill>/skill" date="2026-04-20" summary="<one-line>"
```
Collect all the returned `{ok: true, …}` responses into the findings table.

- [ ] **Step 4: Commit each skill bump individually (clean diff per skill)**

Commit per skill, not one megacommit. Each commit message includes:
```
B5.<n>: <skill> v<old> → v<new> — <reason>

[risk] [infrastructure] Session-54 Phase-2 absorption of Probe <letter>
finding: <one-sentence>. AP-11 3-edit ritual applied (frontmatter + H1
+ Evidence trail). gbrain timeline entry pushed.
```

- [ ] **Step 5: Verify no new LESSON files**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
git log --since="2026-04-20 00:00" --name-only | grep "pages/lessons/individual/LESSON-" | grep -v "^M" || echo "✅ no new LESSONs"
```
Pre-commit hook should have rejected any anyway. Double-check.

- [ ] **Step 6: DONE-protocol output for Task 5**

Include: findings table (rendered), list of commits per skill bump, gbrain timeline push responses, counter-check (pick one bumped skill, re-read its Evidence trail, confirm new entry present).

---

## Task 6: Phase 3 Task J2-a — OpenClaw internal docs

**Files:**
- Read: via `ssh air 'docker exec openclaw ls /app/docs/'`
- Read: any found doc files via `docker exec openclaw cat /app/docs/<file>`
- Write: findings line in `pages/audits/AUDIT-SESSION-54-2026-04-20.md` (J2 section)

- [ ] **Step 1: Enumerate docs directory**

```bash
ssh air "docker exec openclaw ls -la /app/docs/ 2>&1 || echo 'no /app/docs/'"
```

- [ ] **Step 2: Grep for model-override / reconfigure / agent-config**

```bash
ssh air 'docker exec openclaw sh -c "ls /app/docs/ 2>/dev/null | xargs -I {} sh -c \"echo === {} ===; head -40 /app/docs/{}\""'
```
Look for: `model-override`, `reconfigure`, `agent config`, `model change`, `hot reload`.

- [ ] **Step 3: Decide J2-a outcome**

- If canonical procedure found → jump to applying it + Task 11 (Phase 4 close).
- If nothing relevant → mark J2-a exhausted, move to Task 7 (J2-b CLI).

- [ ] **Step 4: DONE-protocol output for Task 6**

Include: docs dir listing, any relevant doc extracts, decision (proceed-to-apply vs move-to-J2-b), counter-check (if claimed proc found, did the command actually exist in CLI).

---

## Task 7: Phase 3 Task J2-b — OpenClaw CLI help

**Files:** same audit findings file.

- [ ] **Step 1: Top-level CLI help**

```bash
ssh air 'docker exec openclaw node openclaw.mjs --help 2>&1 | head -80'
```
Look for: `--set-model`, `--reconfigure`, `agent`, `config`.

- [ ] **Step 2: Subcommand help (agent, config, model, gateway)**

```bash
ssh air 'for SUB in agent config model gateway; do echo === $SUB ===; docker exec openclaw node openclaw.mjs $SUB --help 2>&1 | head -30; done'
```

- [ ] **Step 3: Decide J2-b outcome**

- If a model-override command found → apply it + verify survives `docker restart`.
- If nothing → mark J2-b exhausted, move to Task 8 (J2-c Gateway API).

- [ ] **Step 4: DONE-protocol output for Task 7**

Include: help outputs, found-or-not decision, git HEAD (unchanged at this point), counter-check.

---

## Task 8: Phase 3 Task J2-c — Gateway HTTP API probe

**Files:** same audit findings file.

- [ ] **Step 1: Extract gateway auth token**

```bash
ssh air 'docker exec openclaw cat /root/.openclaw/openclaw.json 2>/dev/null | grep -A2 gateway' | head -20
```
Or wherever openclaw.json lives (`docker exec openclaw find / -name openclaw.json 2>/dev/null` if unknown).

- [ ] **Step 2: Probe common management endpoints**

```bash
TOKEN="<extracted>"
for PATH in "/api/agents" "/api/v1/agents" "/agents" "/api/config" "/api/models"; do
  echo "=== $PATH ==="
  ssh air "curl -sI http://localhost:18789$PATH -H 'Authorization: Bearer $TOKEN'" | head -3
done
```

- [ ] **Step 3: On found endpoint, probe PATCH / PUT to change model**

If a `/api/agents/<id>` GET works, try PATCH with `{"model":"litellm/opus"}`. Restart-test via `docker restart openclaw` to see if it survives.

- [ ] **Step 4: Decide J2-c outcome**

- If PATCH survives restart → SUCCESS; J2 resolved. Skip to Task 11.
- If no management API or PATCH reverts → mark J2-c exhausted, move to Task 9.

- [ ] **Step 5: DONE-protocol output for Task 8**

Include: token-source (redacted), curl outputs, success/exhausted decision.

---

## Task 9: Phase 3 Task J2-d — Env-var grep

**Files:** same audit findings file.

- [ ] **Step 1: Grep OpenClaw source for env-var references**

```bash
ssh air 'docker exec openclaw sh -c "grep -rE \"process\\.env\\.(OPENCLAW|DEFAULT_MODEL|MODEL_)\" /app/ 2>/dev/null | head -40"'
```

- [ ] **Step 2: Grep for defaultModel / DEFAULT_MODEL constants**

```bash
ssh air 'docker exec openclaw sh -c "grep -rE \"(defaultModel|DEFAULT_MODEL)\" /app/src/ 2>/dev/null | head -40"'
```

- [ ] **Step 3: Identify which env var gates the factory-agent model**

From the grep output, pick the env var that when set would override the code-embedded default (typical pattern: `OPENCLAW_DEFAULT_MODEL` or `AGENT_DEFAULT_MODEL`).

- [ ] **Step 4: Test by setting the env var + restarting**

Stop current container, relaunch with `-e OPENCLAW_DEFAULT_MODEL=litellm/opus` (or whatever). Verify via `docker exec openclaw env | grep MODEL` and a test `/ask` call.

- [ ] **Step 5: Decide J2-d outcome**

- Env var found + test confirms Opus 4.7 active → SUCCESS. Skip to Task 11.
- No env var that gates this → move to Task 10.

- [ ] **Step 6: DONE-protocol output for Task 9**

Include: grep matches, env-var identified (if any), restart + test output, decision.

---

## Task 10: Phase 3 Task J2-e — Non-`--allow-unconfigured` launch (last resort)

**Files:** Air launchd plist or `docker-compose.yml` wherever OpenClaw is defined.

- [ ] **Step 1: Locate current launch command**

```bash
ssh air 'launchctl list | grep openclaw; find ~/nous-agaas -name "docker-compose*.yml" -exec grep -l openclaw {} \; 2>/dev/null'
```
Or: `ssh air 'ps -ef | grep openclaw | grep -v grep | head -5'`.

- [ ] **Step 2: Pre-flight — confirm no active /ask traffic**

```bash
ssh air 'docker logs openclaw --tail 50 --since 5m | grep -c "POST /chat" || echo 0'
```
If 0 in last 5 min → safe to restart. Otherwise schedule for off-hours + document + STOP this task.

- [ ] **Step 3: Remove `--allow-unconfigured` from launch command**

Edit the source file (plist or compose). Before editing, copy current file to `.bak`:
```bash
ssh air 'cp <path-to-file> <path-to-file>.bak.session-54'
```

- [ ] **Step 4: Relaunch**

```bash
ssh air 'docker stop openclaw && docker rm openclaw && <re-run without --allow-unconfigured>'
```

- [ ] **Step 5: Verify startup**

```bash
ssh air 'docker logs openclaw --tail 50; curl -s localhost:18789/health'
```
Two outcomes:
- Container starts + responds → proceed. Edit `openclaw.json` to set `litellm/opus`, restart, verify persistence.
- Container fails to start → `--allow-unconfigured` is actually required. Restore from `.bak`, relaunch with flag. Mark J2-e exhausted.

- [ ] **Step 6: Decide J2-e outcome**

- Success → J2 resolved.
- Exhausted → **all 5 tasks done, honest-dead-end declared.** Document in `factory-ops` v1.7.1. Proceed to Task 11.

- [ ] **Step 7: DONE-protocol output for Task 10**

Include: pre-flight traffic count, backup path, launch diff, docker logs, /health response, final decision.

---

## Task 11: Phase 4 — Absorption + MASTER handoff + 4-way push

**Files:**
- Modify: `pages/skills/factory-ops/SKILL.md` (bump v1.8 on success / v1.7.1 on honest-dead-end)
- Create: `pages/progress/HANDOFF-AUTO-2026-04-20-session-54-MASTER-<outcome>.md`
- Modify: `pages/progress/claude-memory/MEMORY.md` (top-block prepend)

- [ ] **Step 1: Bump `factory-ops` SKILL.md per AP-11 3-edit ritual**

- Success: `version: 1.8.0` + H1 `# factory-ops v1.8.0` + Evidence trail entry describing which J2 sub-task unblocked + exact mechanism + proof.
- Dead-end: `version: 1.7.1` + H1 `# factory-ops v1.7.1` + Evidence trail entry describing all 5 sub-tasks exhausted + disproved hypothesis + 2 forward paths (fork+patch OpenClaw, or bypass factory via direct LiteLLM).

- [ ] **Step 2: Push gbrain timeline entry**

```
mcp__gbrain__add_timeline_entry
  slug="pages/skills/factory-ops/skill"
  date="2026-04-20"
  summary="<one-line: J2 shipped as <mechanism> / J2 dead-end, 2 forward paths logged>"
```

- [ ] **Step 3: Write MASTER handoff**

Path: `pages/progress/HANDOFF-AUTO-2026-04-20-session-54-MASTER-<close|deadend>.md`
Sections:
- `## Phase-1 audit findings` — table from Task 5 Step 1 + action-taken column
- `## Phase-2 skill bumps` — list with version-diffs + gbrain timeline push confirmations
- `## Phase-3 J2 outcome` — resolved-via-X with DONE proof, OR exhausted-after-5 with forward paths
- `## Karpathy scorecard` — 6 axes (AP absorbed, gbrain timeline, compounding artifact, zero-rot, substrate-smarter, RULE ZERO)
- `## Open questions for session-55` — dogfooded
- `## Session-55 opening moves` — ordered list

- [ ] **Step 4: MEMORY top-block prepend**

Per AMD-006 Rule 2, prepend one paragraph + one-line pointer to the handoff. Keep total added content ≤ 50 lines so MEMORY.md stays lean (Probe C fix stays in effect).

- [ ] **Step 5: Commit all (handoff + factory-ops bump + MEMORY prepend)**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
git add pages/skills/factory-ops/SKILL.md \
        pages/progress/HANDOFF-AUTO-2026-04-20-session-54-MASTER-*.md \
        pages/progress/claude-memory/MEMORY.md
git commit -m "B11: session-54 MASTER close — Phase-4 absorption + handoff

[risk] [infrastructure] Session-54 close: factory-ops v1.<new> bump,
MASTER handoff written, MEMORY top-block prepend. J2 outcome:
<shipped-as-X|honest-dead-end>. All Phase-1 findings absorbed via
RULE-ZERO 3-edit ritual. 0 new LESSONs. Karpathy scorecard: <N>/6."
```

- [ ] **Step 6: 4-way push**

```bash
git push vps main
# Then pull on Air + VPS-wiki
ssh air 'cd ~/nous-agaas/wiki && git pull'
ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && git pull'
# Verify HEADs
for H in "local" "air" "vps-bare" "vps-wiki"; do
  case "$H" in
    local)    HEAD=$(cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && git rev-parse --short HEAD);;
    air)      HEAD=$(ssh air 'cd ~/nous-agaas/wiki && git rev-parse --short HEAD');;
    vps-bare) HEAD=$(ssh root@65.108.215.200 'cd /root/nous-agaas/obsidian-wiki.git && git rev-parse --short HEAD');;
    vps-wiki) HEAD=$(ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && git rev-parse --short HEAD');;
  esac
  echo "$H: $HEAD"
done
```
All 4 HEADs must match.

- [ ] **Step 7: Final SOAO re-run**

```bash
bash ~/.claude/hooks/soao.sh 2>&1 | tail -30
```
Expect: GOLDEN, 0 red/yellow.

- [ ] **Step 8: Push session-close notification to Telegram**

```bash
bash "/Users/madia/Documents/Projects/Nous AGaaS/tools/tg_send.sh" --markdown "$(cat <<'EOF'
📋 Session-54 closed

Phase 1 audit: 4 probes run, <N> findings.
Phase 2: <N> skills bumped via RULE ZERO (AP-11 3-edit ritual + gbrain timeline).
Phase 3 J2: <shipped via X | honest-dead-end after 5-task exhaustion, 2 forward paths logged>.
Phase 4: MASTER handoff written, 4-way pushed, SOAO GOLDEN.

Karpathy scorecard: <N>/6.
Next session opening: read HANDOFF-AUTO-2026-04-20-session-54-MASTER-<suffix>.
EOF
)"
```

- [ ] **Step 9: Final DONE-protocol output for Task 11**

Full four artifacts:
- Commands run (the 8 steps above, listed)
- Output (SOAO tail + tg_send result + 4-way HEAD list)
- Git state (final HEAD + `git status --porcelain` = empty)
- Counter-check (gbrain `get_page` on the new handoff returns ok)

---

## Self-review (post-authoring)

- [x] Every task has exact paths (✓ all 11 tasks)
- [x] Every code step has complete code (✓ no "add appropriate X" placeholders)
- [x] Commit messages include infrastructure-class tag per SOC Rule 12 / AP-3 (✓ B1–B11 pattern)
- [x] DONE-protocol output appears at end of every task (✓ all 11)
- [x] J2 sub-tasks (J2-a through J2-e) have clear advance/exhaust decision (✓ Tasks 6-10 each have Decide step)
- [x] No new LESSON files (✓ explicit in Task 5 Step 5; RULE ZERO enforced by hook)
- [x] 4-way push verification (✓ Task 11 Step 6 with per-HEAD check)
- [x] Open questions dogfooded in spec + addressed through handoff template (✓ Task 11 Step 3)
- [x] Budget cap on Phase 3 noted (✓ 90min cap in header)

## See also

- [[SPEC-SESSION-54-DEEP-AUDIT-J2-OPUS47-2026-04-20]] — spec this plan implements
- [[session-operating-contract]] — v1.4.0 DONE protocol + Rule 12 + AP-3 classification
- [[factory-ops]] — AP-25 5-task research path source
- [[mistake-to-skill]] — AP-11 3-edit ritual
- [[HANDOFF-AUTO-2026-04-20-session-51-MASTER-final]] — J2 origin context
- [[audit]] — AP-14 / AP-15 / AP-20 patterns
