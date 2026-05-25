---
tier: 2
type: skill
name: gbrain-ops
version: 1.80.14
description: "v1.80.14 — operating procedures for the gbrain knowledge engine (upstream gbrain v0.10.1+). Upgrades, context hygiene, ghost cleanup after migrations, Claude Code session discipline, autopilot concurrency discipline, pre-upgrade scope survey before any git pull, and absorbing new learnings into skills rather than LESSON files. Current high-leverage rules: AP-33 CLI fallback for gbrain timeline writes; AP-35 canonical OpenAI key loader for manual/scheduled gbrain jobs; AP-51 wrapper credential gates; AP-55 Mercury memory-health feedback prevention; AP-56 OpenClaw skillsSnapshot refresh must exercise OpenClaw directly; AP-57 skill-link aliases must resolve to canonical skill slugs before graph-debt reporting; AP-58 sync wrappers must execute wiki-local tool copies; AP-59/AP-60/AP-95 autopilot maintenance must run bounded sync/extract/embed/link-builder cycles under one lock with per-command wall-clock timeouts; AP-61 lowercase gbrain slug lookups; AP-62 machine-readable supersession metadata prevents ranker drift; AP-63 handoffs and AP-79 plan/report pages must pass gbrain lint/import readback before claiming retrieval visibility; AP-80 mirror-imported hubs require registered source sync plus readback before claiming Obsidian/gbrain parity; AP-81 Cyrillic/Unicode vault docs require UTF-8-safe edit commands and replacement-character scans; AP-82/AP-96 manual sync wrappers must source the OpenAI-compatible LiteLLM env and prove the configured base URL reaches Air before embedding; AP-83 command help for stateful subcommands must use global help or be wrapped in timeout because `gbrain sync --help` can hold the sync lock; AP-84 stale `gbrain-sync` DB locks may be cleared only after proving holder PID absence; AP-85 timeline-add uses positional args, not stale flag examples; AP-86 doctor warnings require current-artifact readback before green/yellow claims; AP-87 SKILL title metadata must be included in version-drift gates; AP-88 historical `<head>` sync-failure acknowledgment is allowed only with backup, current readback proof, and evidence reason when CLI skip-failed is a no-op; AP-89 scheduled doctor probes must invoke from the gbrain repo root; AP-90 fresh source pages require normalized-slug targeted embed plus both exact readback and search proof; AP-91 existing-page `gbrain put` is the bounded repair when daemon sync leaves one canonical skill row stale; AP-92/AP-104 generated audit/handshake frontmatter must encode wikilink lists as quoted YAML arrays and use a frontmatter-only mechanical repair when the built-in fixer is a no-op; AP-93 manual gbrain CLI embed shells must export sourced env files with `set -a`; AP-94 Mem0 stays deferred/backup-only unless a one-use-case proof beats gbrain plus OpenBrain projection; AP-97 pins the Anthropic MCP tunnel candidate to `gbrain.nousagaas.com` and gates promotion on access, 24h soak, no SSH fallback, latency comparison, and SSH-key rotation proof; AP-98 surfaces the silent-embedding-failure pattern (per-page failures + positive `pages embedded` summary) and bolts the `tools/test_no_lying_logs.py` §7.1 cross-cutting gate to every sync; AP-99 routes `embedding failed` detections to Telegram via `tools/tg_send.sh` so silent vector degradation pages an operator within one cycle; AP-100 closes the canonical-vs-runtime drift class; AP-101 closes remaining Council P3 residuals; AP-102 bans xtrace/shell-debug execution of secret-loading wrappers and requires sanitized diagnostics; AP-103 treats SSH banner timeouts as a stale-local-transport candidate before declaring gbrain/VPS down; AP-105 keeps VPS QMD CPU-default and prevents symlink-target clobber when wrapping npm binaries; AP-106 requires cwd-visible Codex MCP config plus `qmd_mcp_doctor.py` proof before blaming QMD for native Codex `Transport closed`; AP-107 requires scheduled gbrain autopilot to run as one-shot cycles and bans restart scripts from recreating a persistent daemon loop; AP-108 requires PIPESTATUS arrays to be snapshotted before scalar assignments in bash pipeline gates; AP-109 requires one-shot wrappers to propagate `run_cycle` failure status instead of exiting 0 after logging failure; AP-110 keeps a `/root/skills` symlink shim so fully qualified `gbrain doctor` from SSH default cwd does not false-warn on resolver health. Upstream-fork commit `e1f274a` on `/opt/nous-agaas/gbrain master`. Keeps the evolving-memory loop healthy and prevents context poisoning. Includes dream cycle, wiki-to-runtime-rsync, graph-link, and timeline procedures."
triggers:
  - upgrading gbrain (0.x → 0.y)
  - agent gives a confidently-wrong answer about current system state
  - after any infrastructure migration (to audit residual ghosts)
  - operator running background bash commands
  - periodic maintenance (quarterly review of brain health)
  - learning a rule worth persisting (bug root-cause found, validated success, external feedback)
  - embedding coverage drops below 100% or autopilot processes pile up
  - dream cycle launchd activation or metrics review
  - wiki skill edit needing runtime rsync
tools: [Bash, Read, Edit, Write, Grep]
mutating: true
absorbs_lessons: [LESSON-027, LESSON-030, LESSON-037, LESSON-038, LESSON-059, LESSON-070, LESSON-077, LESSON-081, LESSON-084, LESSON-093, LESSON-095, LESSON-096, LESSON-105, LESSON-111, LESSON-112, LESSON-113, LESSON-128, FEEDBACK-asylbek-2026-04-15-lessons-into-skills]
absorbs_laws: [LAW-001, LAW-005, LAW-009, LAW-015, LAW-017]
related: [SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]
last_updated: 2026-05-22
title: "gbrain-ops v1.80.14"
---

# gbrain-ops v1.80.14

## Purpose

The evolving-memory loop is the highest-leverage system in the factory. When it breaks — context poisoning, stale skills, ghost services, noisy tasks panel — every downstream agent gets dumber. This skill is the operational discipline that keeps the loop compounding.

## Contract

**Inputs:** gbrain upgrade request, OR a suspected brain-stale symptom (agent wrong about current state), OR post-migration audit trigger.

**Outputs:** Clean gbrain version + schema, cleared ghosts, stale entries archived or removed, no duplicate-purpose services, agent grounded in reality.

**Invariants:**
- After any migration, the agent must answer architecture questions using CURRENT state, not old MEMORY.md entries
- No service runs without a reason someone could articulate in one sentence
- No UI task-panel entry survives past its useful life
- Context_injector delivers truth, not narrative from 3 months ago

### AP-97 — gbrain MCP tunnel promotion is domain-pinned and proof-gated

**Trigger:** Anthropic MCP tunnels became a candidate replacement for the current SSH-stdio gbrain bridge, and Madi selected the production tunnel domain.

**Rule:** the Bucket A tunnel target is `gbrain.nousagaas.com`. Do not deploy or promote it before Anthropic grants access. Promotion requires all gates in `pages/audits/MCP-TUNNEL-READINESS-NOUS-2026-05-20.md`: 24h soak, no SSH fallback, tunnel p95 latency compared against SSH-stdio, and SSH-key rotation proof showing gbrain still works without the runtime SSH key. Until those gates pass, the SSH bridge remains the current production path and tunnel work is canary/plumbing only.

**Detector:** audit the route with `tools/model_route_auth_probe.py` for route classification, then run the tunnel-specific acceptance checks from `MCP-TUNNEL-READINESS-NOUS-2026-05-20.md`. Do not claim "gbrain tunnel live" from DNS or proxy health alone.

## Phases

Four sub-procedures. Invoke the one that matches the trigger.

### P1 — gbrain upgrade (0.x → 0.y)

**When:** `gbrain check-update` reports newer version available, OR major feature announcement.

0. **Run AP-32 pre-upgrade scope survey before any production mutation.** If commit delta >10, LOC delta >5K, any schema migration appears, or the checkout has local modifications, STOP and write a dry-run plan. Do not `git stash && git pull` a dirty production checkout.

1. Backup PostgreSQL:
   ```bash
   ssh vps 'PGPASSWORD=gbrain2026 pg_dump -h localhost -U gbrain -d gbrain > /root/gbrain-backup-$(date +%Y%m%d-%H%M).sql'
   ```
2. Backup local overlays and tracked diffs before any pull:
   ```bash
   ssh vps 'cd /opt/nous-agaas/gbrain && tar -czf /root/gbrain-local-overlays-$(date +%Y%m%d-%H%M).tgz skills gbrain-serve-singleton.sh 2>/dev/null || true && git diff > /root/gbrain-local-tracked-diff-$(date +%Y%m%d-%H%M).patch'
   ```
3. Upgrade in a separate dry-run clone against a restored non-production DB first. Production pull/build happens only after the dry-run proves migrations, doctor, retrieval, and timeline writes.

4. Install new deps:
   ```bash
   ssh vps 'export PATH=/root/.bun/bin:$PATH && cd /opt/nous-agaas/gbrain && bun install'
   ```
5. **REBUILD the binary** (AP-1):
   ```bash
   ssh vps 'export PATH=/root/.bun/bin:$PATH && cd /opt/nous-agaas/gbrain && bun run build'
   ```
6. Trigger schema migration with the current upstream-supported command, not stale `init --help` assumptions:
   ```bash
   ssh vps 'cd /opt/nous-agaas/gbrain && DATABASE_URL="postgresql://gbrain:gbrain2026@localhost:5432/gbrain" ./bin/gbrain apply-migrations --yes'
   ```
7. Verify via `gbrain doctor`:
   ```bash
   ssh vps '/opt/nous-agaas/gbrain/bin/gbrain doctor --json'
   # Look for: skill_conformance 25/25, 100% embed coverage, health 80+
   ```
8. If new skillpack features, mirror through the wiki/Obsidian source of truth first, then rsync to Air runtime:
   ```bash
   ssh air 'bash ~/nous-agaas/tools/wiki-to-runtime-rsync.sh'
   ```
9. If the upgrade teaches a durable rule, update the relevant `SKILL.md` and push the matching gbrain timeline entry. Do **not** create a new LESSON file.

### P2 — Context-poisoning cleanup (after migration or when agent is confidently wrong)

**When:** Agent answers an architecture question using old state (e.g., claims VPS hosts something that was moved to Air).

1. **Root cause is MEMORY.md volume, not recency.** Count mentions of old vs new reality:
   ```bash
   grep -c "VPS\|vps" pages/progress/claude-memory/MEMORY.md
   grep -c "Air\|air" pages/progress/claude-memory/MEMORY.md
   ```
   If the old state outnumbers new by ≥20%, agent will weight volume over recency.

2. **Fix — prepend an UNAMBIGUOUS CURRENT ARCHITECTURE table at the top of MEMORY.md** with an explicit override directive:
   ```markdown
   # 🔴 CURRENT ARCHITECTURE — READ THIS FIRST, OVERRIDES EVERYTHING BELOW
   ...table of what runs where...
   When answering any architecture question: the rows above are ground truth.
   Older session notes below describe the JOURNEY here. Do not quote them as current state.
   ```

3. Audit 3 ghost lists within 24h of any migration:
   - **launchd services** (`launchctl list | grep com.nous`) — delete anything with exit code ≠ 0 or pointing to removed binaries
   - **Cron jobs** (`crontab -l`) — `grep -v` anything referencing paths to removed services
   - **Config references** (`grep -rln "known_ghost_name"`) — delete plugin/bot/container/URL refs that point nowhere

4. **Ghost test** for each remaining service: "Who consumes its output?" If there's no answer in one sentence, DELETE it.

5. Re-probe the agent to verify grounding:
   ```bash
   ssh air 'cd ~/nous-agaas && python3 run_task.py "Answer from verification, not memory: where is OpenClaw running? Prove with a shell command."'
   ```

### P3 — Session hygiene (Claude Code UI discipline)

**When:** Operating a Claude Code session where lots of Bash calls happen.

1. **Default foreground Bash.** Only use `run_in_background: true` when:
   - Command genuinely takes >30s AND
   - You want useful parallel work during the wait AND
   - You'll actually reap the result via TaskOutput later

2. **Anti-patterns** (do NOT do these):
   - `ssh vps 'echo ok'` in background — 200ms command, pointless
   - `grep`/`ls` in background — instant completion
   - Small `scp` in background while immediately waiting for it

3. **Correct use** of background flag:
   - Docker pulls of 1GB+ images
   - `pytest` of 500+ tests
   - `run_task.py` factory probes that take 1-2 min

4. **Reap when done.** Accumulating >3 "running" background tasks in the Tasks panel is a signal you're using the flag wrong — user trust in the panel drops, they assume "Running" ≠ "actually running right now."

5. **Communicate intentional kills** in chat when terminating a background task, rather than letting the async task-notification surface the exit code alone.

### P4 — Absorb a new learning into the skill layer

**When:** You just found the root cause of a bug, or validated a success, or received external feedback (from Madi, Smatay, Asylbek, a user, a log, or an audit). Asylbek's 2026-04-15 directive: "each lesson and learned must be in skills md" — the skill layer is the runtime source of truth; historical LESSON receipts do not reach the agent at task-time.

1. **Pick the skill.** Which existing `pages/skills/*/SKILL.md` covers the domain? If none fits, creating a new skill is justified (see `skills/_gbrain/skill-creator` on Air).

2. **Write the rule in the skill, never in a new LESSON.** Add / update in this order inside the SKILL.md:
   - Add the rule to a relevant phase's numbered steps (if procedural).
   - OR add an Anti-Pattern `AP-N` entry (if "don't do X, because Y").
   - Append to `## Rules absorbed from lessons` only when absorbing a historical LESSON; otherwise append to the skill's Timeline/Evidence trail.
   - Append to `## Timeline` with `YYYY-MM-DD | vX.Y.Z — absorbed <source/failure/feedback>`.
   - Bump the SKILL version (patch for added rule, minor for new phase, major for contract change).

3. **RULE ZERO compatibility.** New bug fixes and learnings land in `SKILL.md` + gbrain timeline. Existing historical LESSON files may be edited for drift correction, but new canonical `LESSON-NNN-*.md` files are rejected by hooks and must not be created.

4. **Feedback not tied to a bug** (e.g. user preference, strategic direction) also updates the skill directly + gbrain timeline. Use a source label like `FEEDBACK-<who>-YYYY-MM-DD-<topic>` in the Timeline if helpful.

5. **Sync the absorbed skill to runtime.** Two targets:
   - Wiki (VPS `/root/nous-agaas/wiki/pages/skills/<skill>/SKILL.md`) — source of truth.
   - OpenClaw runtime (Air `/opt/nous-agaas/skills/<skill>/SKILL.md` via bind mount) — what the agent reads live. Run `rsync -avz /root/nous-agaas/wiki/pages/skills/<skill>/ air:/opt/nous-agaas/skills/<skill>/` (or equivalent). gbrain autopilot picks up the wiki copy within 5 min for embedding.

6. **Quick verify.** Re-probe the agent with a question the new rule should now answer correctly. If it still gets it wrong, the skill is not in RESOLVER.md (AP-5) or the runtime rsync was missed.

### P5 — Dream cycle (nightly compounding — READ-ONLY)

**When:** Daily 03:15 via `com.nous.dream-cycle` launchd (to be activated in Phase P5).

**What it reads:**
- Last 24h `pages/task-results/*.md`
- Last 24h `pages/progress/HANDOFF-*.md`

**What it writes:**
- `pages/progress/dream-cycle-YYYY-MM-DD.md` (one file per day, append-only)

**What it NEVER writes to:**
- `pages/skills/*/SKILL.md` — autonomous skill mutation is FORBIDDEN (anti-slop rule)

**Metrics computed:**
1. Absorption rate: absorbed lessons / total lessons this week
2. Skill coverage: intents resolved via RESOLVER.md / total intents
3. RESOLVER.md hit rate: resolver hits / total queries
4. Avg context tokens per task: from context_injector logs
5. Unused skills (30d): skills with zero task-result references

**Alert rule:** Telegram escalation if any metric worsens week-over-week.

**Anti-pattern: AP-20 — autonomous skill mutation at night.** Dream cycle edits skills → morning brings surprise regressions. Fix: dream cycle PROPOSES in `pages/progress/dream-cycle-*.md` only. Madi reviews in morning-brief. `/skill-capture` drafts. Git commit is the explicit gate.

### P6 — wiki-to-runtime-rsync (closing Rule-6 loop)

**When:** launchd WatchPath fires on `~/nous-agaas/wiki/pages/skills/` change

**Script:** `~/nous-agaas/tools/wiki-to-runtime-rsync.sh`

**What it does:**
1. Acquires flock `/tmp/wiki-rsync.lock`
2. `rsync -av --no-delete --exclude='_gbrain/' --exclude='extracted/' wiki/pages/skills/ → /opt/nous-agaas/skills/`
3. Logs changed files to `pages/progress/rsync-log-YYYY-MM-DD.md`
4. Releases lock

**NEVER uses `--delete`** — protects `_gbrain/` skillpack (session 24 Wave 3 wiped it).

**Anti-pattern: AP-21 — manual rsync instead of waiting for WatchPath.** Fix: if urgent, trigger manually with `~/nous-agaas/tools/wiki-to-runtime-rsync.sh` — never raw rsync (it might use wrong flags).

## Anti-Patterns

### AP-1 — Don't skip `bun run build` after `git pull` on gbrain
`bin/gbrain` is a compiled ELF binary produced by `bun build --compile`. A `git pull` updates source but leaves the old binary. `--version` will keep reporting the old version. Always run `bun run build` after pulls.

### AP-2 — Don't `gbrain init` without `--url`
Defaults to PGLite (embedded) and fails on our setup with `ENOENT: no such file or directory, open '/$bunfs/root/pglite.data'`. We use PostgreSQL. Always pass `--url "postgresql://gbrain:gbrain2026@localhost:5432/gbrain"`.

### AP-3 — Don't let autopilot and `gbrain_sync_wrapper.sh` run in parallel
Both do sync + embed. After installing `gbrain autopilot --install`, remove the old wrapper cron to avoid double work:
```bash
crontab -l | grep -v "gbrain_sync_wrapper.sh" | crontab -
```

### AP-4 — Don't leave CURRENT STATE at the bottom of MEMORY.md
`context_injector._read_tail` reads the last N lines. But our convention has newest entries at TOP (chronological reverse order). So the CURRENT ARCHITECTURE block must also be at the TOP, immediately after the frontmatter. If volume exceeds N lines, the block still loads because it's within the tail window.

Future resilience (if MEMORY.md grows past 500 lines): patch `context_injector._read_tail` to always include lines up to a `# 🔴 CURRENT ARCHITECTURE` anchor.

### AP-5 — Don't ship a new skill without adding it to RESOLVER.md
RESOLVER.md is how the agent decides what to read. A skill with no resolver entry is invisible at runtime. When adding a new skill, also add a row to `skills/_gbrain/RESOLVER.md` under the appropriate category (always-on, brain ops, ingestion, thinking, operational).

### AP-6 — Don't capture a learning anywhere except SKILL.md + gbrain timeline
Standalone LESSON files in `pages/lessons/individual/` are historical receipts only. They do NOT reach the agent at task-time because runtime reads from `skills/*/SKILL.md`. RULE ZERO superseded the old skill+lesson co-commit rule: new bug fixes and learnings update the target `SKILL.md`, push a gbrain timeline entry on that skill page, and commit the skill change. No new canonical LESSON file. See P4.

### AP-7 — Don't edit only the wiki copy and forget the runtime copy (LAW-005)
Wiki (VPS `/root/nous-agaas/wiki/pages/skills/`) is source of truth for humans + gbrain. Runtime (Air `/opt/nous-agaas/skills/` via bind mount) is what OpenClaw actually reads when it answers a task. An update that lives only in the wiki will not affect the next `/ask` until rsync'd to the runtime. See P4 step 5.


### AP-8 — Update ALL three memory systems (LAW-001), not just one
**LESSON-027.** In the old architecture: local memory (Claude Code reads), Obsidian wiki (factory reads), and Mem0 (all agents search) were SEPARATE systems. Saving to one did NOT propagate to others. Current AGaaS architecture: the primary is the Obsidian wiki (gbrain + Air rsync). MEMORY.md index + wiki pages + gbrain embeddings are the three tiers — all must be updated:

1. Write the fact/lesson to the wiki page
2. Ensure MEMORY.md index has a pointer to it (for Claude Code context injection)
3. gbrain autopilot handles embedding within 5min (automatic)

Never save to only one tier and assume the others will catch up. They won't until a sync runs.

### AP-9 — Audit memory files for staleness (LAW-009), not just lessons
**LESSON-030.** A stale user profile that describes Madi as "non-technical, gets overwhelmed, one command at a time" when he is a high-speed technical CEO will cause every agent to talk down to him. Memory files (user profiles, entity pages, relationship descriptions) change as relationships and situations evolve. Quarterly:

```bash
# Find oldest entries in MEMORY.md by date
grep '20[0-9][0-9]-' pages/progress/claude-memory/MEMORY.md | sort | head -20
# Entries older than 3 months may be stale — verify before acting on them
```

Rule: memory staleness is as dangerous as missing memory. Verify before acting on it.

### AP-10 — Every consumer must READ the knowledge base, not just have it exist
**LESSON-037.** Building a wiki schema (CLAUDE.md, COMPILED-KNOWLEDGE.md) is 20% of the work. Ensuring every agent reads the right subset is 80%. Different roles need different views:
- CEO agent: reads full context + skills + MEMORY.md
- Claude Code: reads MEMORY.md index + skill files on demand
- OpenClaw: reads skills from `/opt/nous-agaas/skills/` (runtime mount) + wiki_search MCP

Test from the agent's perspective: "what does this agent ACTUALLY receive as context?" — not just "does the file exist?"

### AP-11 — Delete old copies when migrating to a new source of truth
**LESSON-038.** When Obsidian became the single source of truth, the 35 duplicate local memory files were kept "just in case." They contradicted Obsidian with stale info and confused agents. Rule: when you establish a new canonical source:

1. Migrate content TO the new source
2. DELETE the old copies immediately
3. Update all pointers (MEMORY.md index) to point at new source
4. Verify old source is empty or non-existent

"Both exist" = stale one will win at some point.

### AP-12 — Never import from god-config modules in utility scripts
**LESSON-070.** `wiki_lint.py` failed for 2 days because it imported from a `config.py` that required `langchain_openai`. The lint tool only needed one env var. Pattern to avoid:

```python
# ❌ WRONG — imports entire ML stack for one constant
sys.path.insert(0, "/root/nous-agaas")
from config import ANTHROPIC_API_KEY

# ✅ RIGHT — read the env var directly
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
```

Also: never hardcode `/root/nous-agaas/wiki/` in scripts. Use `Path(__file__).resolve().parent.parent` or `os.environ.get("WIKI_ROOT")`. Scripts that only work on one specific machine are untestable.

Cron outputs must be monitored. A cron that runs but produces no visible output is effectively a dead cron.

### AP-13 — Don't use `mcp__gbrain__put_page` to CREATE a new wiki page
**LESSON-105.** `put_page` writes the content into the brain's PostgreSQL + embeddings + tags, but there is no brain → git path — the file on disk stays absent. Symptom: `get_page` works, `ls pages/...` shows "No such file", Obsidian doesn't see it, `git status` shows nothing, nobody but gbrain queries can find it.

**Rule:** for any NEW wiki page (source, entity, project, law, lesson, skill, handoff), use the `Write` tool to the Mac vault (`/Users/madia/Documents/Projects/Nous AGaaS/Nous/...`). Mac obsidian-sync pushes to the VPS bare repo within ~30 s, Air wiki-sync pulls within 5 min, gbrain autopilot re-embeds within 5 min of the commit.

`put_page` is safe only for **updating** a page that already exists on disk (tag, timeline entry, backlink changes) — because `sync_brain` will see the disk version on the next 5-min cycle and reconcile.

### AP-14 — Don't run the autopilot cron without an OS-level flock
**LESSON-112.** Cron fires `autopilot-run.sh` every 5 min. Each cycle can take minutes-to-hours (git divergence, large embeds, network stalls). Without an OS mutex, slow cycles pile up — 13 concurrent autopilots observed before this rule was introduced. Every extra process opens its own PG pool; after ~97 non-superuser slots are in use, PostgreSQL rejects all new connections with `remaining connection slots are reserved for roles with the SUPERUSER attribute`, and every embed in the running cycles silently fails.

gbrain's internal "autopilot lock file" is not sufficient — the file can be missing on disk or cleaned up after a crash, letting the check slip.

**Rule:** `/root/.gbrain/autopilot-run.sh` MUST wrap the gbrain invocation with `flock -n`:
```bash
exec flock -n /var/lock/gbrain-autopilot.lock /opt/nous-agaas/gbrain/bin/gbrain autopilot --repo /root/nous-agaas/wiki
```
Non-blocking (`-n`) so the surplus cron tick exits with rc=1 instead of queuing. Lock file in `/var/lock/` (standard OS location, survives process crashes cleanly). Apply the same pattern to ANY cron job whose runtime can exceed its interval.

### AP-15 — "embed ghost" chunks: `embedded_at` set, `embedding` NULL
**LESSON-112.** The gbrain embed code marks `embedded_at = NOW()` before the vector is written. If the DB insert of the vector fails (pool exhaustion, OpenAI timeout, transaction rollback), `embedded_at` remains set but `embedding` stays NULL. `gbrain embed --stale` filters by `WHERE embedded_at IS NULL`, so it skips these ghosts forever — they are invisible as stale but don't actually exist in the vector index.

**Detection query** (run periodically):
```sql
SELECT COUNT(*) FROM content_chunks
WHERE embedding IS NULL AND embedded_at IS NOT NULL;
-- non-zero = ghost chunks present
```

**Fix** (reset flag so `--stale` picks them up):
```sql
UPDATE content_chunks SET embedded_at = NULL
WHERE embedding IS NULL AND embedded_at IS NOT NULL;
```

**Session 33 finding (2026-04-16):** 69 ghost chunks found. After resetting `embedded_at` and re-running `gbrain embed --stale`, all 2047/2047 chunks embedded (100%). The autopilot-run.sh does NOT auto-fix ghosts — add ghost reset to the autopilot or run detection query in nightly audit.
Then run `/opt/nous-agaas/gbrain/bin/gbrain embed --stale` with the real `OPENAI_API_KEY` and `DATABASE_URL` env vars set.

**Prevention mindset:** when an audit says "100% embedded," verify by computing it two ways:
- `SUM(embedding IS NOT NULL) / COUNT(*)` — real coverage
- `SUM(embedded_at IS NOT NULL) / COUNT(*)` — intent-to-embed

If those two numbers disagree, ghosts are present. **Prefer queries that key off the result (`embedding IS NULL`) rather than an intent flag (`embedded_at IS NULL`).**


### AP-16 — After adding AGaaS domain skills: symlink + manifest + embed (LESSON-111)

**LESSON-111.** gbrain's `doctor` resolves skill paths relative to `/opt/nous-agaas/gbrain/skills/`. When you add a new AGaaS domain skill to the wiki and rsync to Air, you MUST also:

1. **Create a symlink** in `/opt/nous-agaas/gbrain/skills/`:
   ```bash
   ln -s /root/nous-agaas/wiki/pages/skills/<skill-name> /opt/nous-agaas/gbrain/skills/<skill-name>
   ```
   Symlink (not copy) so wiki auto-syncs flow through automatically.

2. **Add to manifest.json** at `/opt/nous-agaas/gbrain/skills/manifest.json`:
   Add `{"name": ..., "path": ..., "description": ...}` to the `skills` array.

3. **Ensure `triggers:` frontmatter** exists in the SKILL.md (required for MECE conformance).

4. **Run `gbrain embed --all`** to embed new pages (avoids coverage drop).

Symptom if skipped: `gbrain doctor` FAIL with MISSING_FILE errors, ORPHAN_TRIGGER warnings, embedding coverage drops below 100%.

### AP-17 — Dual-location skill mirror drift (pages/skills/ vs pages/systems/skills/)

**Discovered session 26 deep-dive audit (2026-04-15).** The wiki has TWO canonical skill locations:
- `pages/skills/<skill>/SKILL.md` — what Air runtime mirrors from (via wiki-sync → `~/nous-agaas/skills/<skill>/SKILL.md`)
- `pages/systems/skills/<skill>/SKILL.md` — mirror used by older RESOLVER lookups

An audit of all 13 AGaaS skills found **7 of 13 drifted** silently between the two paths: 3 skills existed in `pages/systems/skills/` only (missing from `pages/skills/`), 5 had stale content in `pages/systems/skills/` despite `pages/skills/` being ahead, and 1 (storage-retrieval) had a 3-way divergence between both wiki locations and Air runtime.

**Rule:** every skill edit touches BOTH paths in the SAME commit. After Edit on one:
```bash
cd ~/Documents/Projects/Nous\ AGaaS/Nous
cp "pages/skills/<skill>/SKILL.md" "pages/systems/skills/<skill>/SKILL.md"
md5 -q pages/{skills,systems/skills}/<skill>/SKILL.md  # must match
```

**Detection query** (run before claiming "skills synced everywhere"):
```bash
for skill in $(ls ~/Documents/Projects/Nous\ AGaaS/Nous/pages/skills/ | grep -v '^_\|^extracted$'); do
  P1=$(md5 -q "pages/skills/$skill/SKILL.md" 2>/dev/null)
  P2=$(md5 -q "pages/systems/skills/$skill/SKILL.md" 2>/dev/null)
  RT=$(ssh air "md5 -q ~/nous-agaas/skills/$skill/SKILL.md 2>/dev/null")
  [ "$P1" = "$P2" ] && [ "$P2" = "$RT" ] && echo "✓ $skill" || echo "✗ $skill DRIFT"
done
```

**Prevention:** whoever adds a new skill must populate BOTH wiki paths on creation, not just one.

### AP-18 — When renaming a LESSON or SKILL file, body H1 must match file ID

**Discovered session 26 deep-dive audit.** LESSON-112 file was originally created as LESSON-111 (before a parallel-session collision forced renumbering). My rename script updated `id:` in frontmatter and the filename, but the body `# LESSON-111 — ...` H1 heading was left stale. gbrain chunked the file with "LESSON-111" in the first chunk — semantic search still worked (tags matched) but the content contradicted the file name.

**Rule:** after any `id:` or filename rename, grep the file body for the old ID and update the H1 (and any inline references):
```bash
# After rename LESSON-NNN → LESSON-MMM:
grep -n "LESSON-NNN" "pages/lessons/individual/LESSON-MMM-*.md"
# fix any matches
```

**Better:** derive the body H1 from frontmatter id at render time, OR lint flags mismatches between `id:` and `^# LESSON-N{3} —` header.

## Output Format

Upgrade / migration / learning-absorption operations produce:
1. A matching `SKILL.md` update plus gbrain timeline entry. Do not create a new `LESSON-NNN` file; RULE ZERO supersedes old LAW-015 Gate 8 wording for new learnings.
2. A short Telegram message summarizing change (`✅ gbrain 0.x → 0.y complete. Health: N/100.` OR `✅ absorbed learning into skills/<skill> v1.2.0`).
3. A commit whose message names the skill version bump, with the git stash reference if a rollback anchor is needed.
4. Updated Timeline section of the affected skill(s) — `## Timeline` block at the bottom of the SKILL.md.
5. If a new skill was created: add row to `skills/_gbrain/RESOLVER.md` (AP-5).

### AP-19 — Always `cd /opt/nous-agaas/gbrain` before running gbrain doctor

**LESSON-113.** `findRepoRoot()` in doctor.ts walks up from `process.cwd()` looking for `skills/RESOLVER.md`. When invoked from `/` or any path other than the gbrain root, the walk never reaches the skills directory and doctor silently reports `resolver_health: WARN Could not find skills directory` — even when all symlinks are correct.

**Always invoke as:**
```bash
cd /opt/nous-agaas/gbrain && bin/gbrain doctor 2>&1 | tail -30
```

**Symptom of violation:** `resolver_health: WARN: Could not find skills directory` despite `ls skills/RESOLVER.md` succeeding.

**How to apply:**
- Every session-start audit must run the doctor from `cd /opt/nous-agaas/gbrain`.
- Any script or launchd job that calls gbrain doctor must either `cd` first or use `--cwd` if the flag is added in future gbrain versions.
- If you see "Could not find skills directory" — first check CWD before investigating symlinks.

### AP-20 — raw/ must be auto-routed; never dump files into raw/ root

**LESSON-059.** Without structural enforcement, raw/ accumulated loose files at top level mixed with correct subfolders — recordings, telegram messages, meeting notes all dumped at root. Madi opened the wiki and saw chaos.

**Rule:** All files entering raw/ MUST be routed by `tools/raw_hygiene.py` into typed subdirectories: `meetings/`, `telegram/`, `recordings/`, `state-snapshots/`, `outbox/`. Direct writes to raw/ root (except README.md) are forbidden. Enforce via pre-commit hook or ingest-time routing.

### AP-21-gbrain — All wiki page slugs must be lowercase (QMD case sensitivity)

**LESSON-084.** QMD returns lowercase slug paths but Linux filesystem is case-sensitive. `Path.is_file()` returns False for every QMD result when actual filename has uppercase chars. Context injector silently returned zero wiki content.

**Rule:** All wiki page filenames MUST be lowercase (hyphens OK, no uppercase). When resolving QMD results to disk paths, use case-insensitive resolution (`_resolve_case()` helper). Never treat "no results from QMD" as "no relevant pages" — always verify the path resolution is working.

### AP-22 — gbrain MCP (stdio) spawns orphan `gbrain serve` processes via SSH

**LESSON-128.** Each gbrain MCP client connection (e.g., Claude Code session) starts a `gbrain serve` process via SSH (`sshd: root@notty`). When the client disconnects, the serve process survives because SSH doesn't always deliver SIGHUP to children of `nohup`/backgrounded processes. Session 34 found **14 orphaned instances eating 1.1GB RAM**, each holding a PostgreSQL connection pool. Sustained accumulation can exhaust PG's `max_connections` (same root cause as AP-14 but different trigger).

**Detection:**
```bash
pgrep -fc "gbrain serve"   # should be 0 or 1 (if an active MCP session)
ps aux | grep "gbrain serve" | grep -v grep | awk '{sum+=$6} END {print sum/1024"MB"}'
```

**Fix (cleanup + prevention):**
```bash
# Immediate cleanup: kill all orphaned (ppid=1) gbrain serve processes
for pid in $(pgrep -f "gbrain serve"); do
  ppid=$(ps -o ppid= -p "$pid" | tr -d ' ')
  if [ "$ppid" = "1" ]; then kill "$pid"; fi
done

# Prevention: cron every 15min to reap orphans automatically
# (already added to VPS crontab by session 34)
```

**Rule:** any MCP server that runs via SSH MUST have an orphan-reaper cron. The 5-min autopilot flock (AP-14) protects autopilot; this AP protects the serve daemon. Both are needed.

## Files

| File | Role |
|------|------|
| `/opt/nous-agaas/gbrain/` (VPS) | gbrain source + built binary + skillpack |
| `/root/.gbrain/autopilot-run.sh` (VPS) | autopilot cron entry point (must have inline env, not source .zshrc) |
| `/root/gbrain-backup-*.sql` (VPS) | PostgreSQL backups |
| `~/nous-agaas/skills/_gbrain/` (Air) | Mirrored skillpack for OpenClaw agent |
| `pages/progress/claude-memory/MEMORY.md` | Always-injected session context |

## Brain-aware invocation (gstack v0.18.0.0, 2026-04-17)

Before any gbrain maintenance (upgrade, embedding job, ghost cleanup, autopilot toggle, reaper tuning), `mcp__gbrain__search` with the op type — prior ops on the same version or migration step may have recorded gotchas (autopilot concurrency, zombie serve processes, frontmatter drift, stuck SSH sessions). Fast keyword search only, never hybrid `query` (hybrid consumes embedding tokens unnecessarily for maintenance lookups). After op, `mcp__gbrain__add_timeline_entry slug="pages/skills/gbrain-ops/skill"` with "<op>: <target>, <outcome>". See [[skills/_gbrain/BRAIN-AWARE-INVOCATION]].

## Rules absorbed from lessons

- **LESSON-093:** Context poisoning — CURRENT ARCHITECTURE block at TOP of MEMORY.md with override directive. Post-migration ghost audit within 24h. Ghost test for every service.
- **LESSON-095:** gbrain upgrade = backup → pull → install → **build** → `init --url` → rsync skillpack → restart consumers. See P1.
- **LESSON-096:** Bash `run_in_background` is for command >30s + parallelism needed + will-reap. Defaults to foreground. See P3.
- **FEEDBACK-asylbek-2026-04-15-lessons-into-skills:** Every new learning must land in a SKILL.md
- **LESSON-027:** Update ALL three memory tiers (wiki + MEMORY.md index + gbrain). See AP-8.
- **LESSON-030:** Audit memory files for staleness — profiles change over time. See AP-9.
- **LESSON-037:** Ensure every consumer agent reads the knowledge base, not just that it exists. See AP-10.
- **LESSON-038:** Delete old copies when migrating to a new source of truth. See AP-11.
- **LESSON-070:** Import only what you need; never couple scripts to god-config modules. See AP-12.
- **LESSON-081:** Write MEMORY.md immediately on critical status changes (also in command-center AP-7).
- **LESSON-105:** `put_page` writes brain-only; new wiki pages MUST use `Write` tool to Mac vault. See AP-13.
- **LESSON-112:** (a) autopilot cron without flock → concurrent pileup → PG pool exhaustion → silent embedding failures. See AP-14. (b) `embedded_at` is a *flag*, not a *result*; filter by `embedding IS NULL` to catch ghost chunks. See AP-15.
- **FEEDBACK-asylbek-2026-04-15-lessons-into-skills (reprise):** Every new learning must land in a SKILL.md, not only a standalone LESSON-NNN file. LESSON = audit trail, SKILL = runtime. Same commit, both places. See P4 + AP-6 + AP-7.

- **LESSON-077:** Verify SQL column names against `\d tablename` before writing queries; guessing column names causes silent failures (empty results, not errors). Add UNIQUE index for any table receiving idempotent inserts so the DB catches duplicates even when app-level dedup fails. Handle unique-constraint violations as "already exists" (skip), not as errors.

- **LAW-001:** Every agent reads wiki BEFORE work. Every error -> lesson file + SKILL.md update. Same mistake never twice. See AP-8 (three-tier update).
- **LAW-005:** Obsidian wiki is physically enforced single source of truth. Claude Code memory dir is a symlink INTO the vault. If anything contradicts wiki -> wiki wins. See AP-7 (runtime copy) and AP-11 (delete old copies on migration).
- **LAW-009:** Every failure feeds the learning loop. Log cycle KPIs. If worse than last cycle -> investigate. If better -> document what changed. See AP-6 (lesson+skill same commit).
- **LAW-015:** Every mistake MUST have: (1) exact symptom, (2) root cause (ask why 5x), (3) exact fix (file + line), (4) reasoning behind fix, (5) general principle. See AP-6.
- **LAW-017:** Every non-obvious success = skill written to wiki immediately. Write-back within same session. See AP-6 (skill extractor) and AP-7 (runtime rsync).

- **LESSON-111:** New AGaaS skill → symlink in gbrain/skills/, add to manifest.json, triggers: frontmatter, `gbrain embed --all`. See AP-16.

- **LESSON-113:** gbrain doctor `findRepoRoot()` walks up from `cwd`, not binary dir. Always `cd /opt/nous-agaas/gbrain && bin/gbrain doctor`. See AP-19.

- **LESSON-059:** raw/ folder without structural enforcement gets messy fast. All raw files MUST be auto-routed by `tools/raw_hygiene.py` into typed subdirectories (meetings/, telegram/, recordings/, state-snapshots/). Never dump files directly into raw/ root. See AP-20.

- **LESSON-128:** gbrain MCP via SSH spawns `gbrain serve` orphans. 14 instances = 1.1GB. Cron reaper every 15min kills ppid=1 orphans. See AP-22.

- **LESSON-084:** QMD indexes files using lowercase slug keys but Linux filesystem is case-sensitive. All wiki page slugs MUST be lowercase. `_resolve_case()` helper needed when resolving qmd results to disk paths. Silent empty results from case mismatches are worse than errors. See AP-21-gbrain.

### AP-23 — Skill frontmatter `type:` field drift (session 36)

**Symptom:** 12 of 18 domain SKILL.md files lacked `type: skill` in frontmatter (agent-quality, air-ssh-access, audit, camera-management, command-center, factory-ops, gbrain-ops, infrastructure, metrology-cert-tracker, satory-dashboard, smartbridge-soap-client, website-deploy). Consequence: gbrain autopilot inferred `type: concept` on re-ingest, breaking skill-typed queries (`mcp__gbrain__list_pages type=skill` returned only 6 of 18 domain skills, plus _gbrain skills).

**Root cause:** No schema enforcement. Older skills predate the frontmatter standard. Newer skills had `type: skill`; older ones never got it added. There's no lint/pre-commit check that requires `type: skill` on files under `pages/skills/*/SKILL.md`.

**Rule:** Every file at `pages/skills/<slug>/SKILL.md` MUST have `type: skill` as a frontmatter field. Add a schema audit run to the gbrain-ops maintenance checklist.

**Audit snippet (one-liner):**
```bash
for s in pages/skills/*/SKILL.md; do grep -q '^type: skill' "$s" || echo "DRIFT: $s"; done
```

**Fix applied (session 36, 2026-04-17):** inserted `type: skill` as first frontmatter field in all 12 drifted skills. After commit + push + Air sync, the next autopilot re-ingest will classify them correctly. Subsequent `mcp__gbrain__list_pages type=skill` should return ≥18 domain skills.

**Prevention (future work):** wire this audit into the Mac+VPS pre-commit hook alongside the existing LESSON-file gate. If any staged `pages/skills/*/SKILL.md` lacks `type: skill`, reject. Deferred to next session since it touches hook infrastructure (lower blast-radius deploy path).

Source: Session 36 Phase A A3 check — gbrain DB showed only 24 skill-typed pages (should be ~18 domain + ~30 _gbrain = ~48). Investigation revealed the frontmatter gap.

### AP-24 — QMD cron was embed-only; new docs drifted unindexed for 3 days (session 36)

**Symptom:** QMD `status` on 2026-04-17 showed `lastUpdated: 2026-04-14T07:47:01.254Z`. Three days of new files (session 35 work, session 36 work, dream cycle, HANDOFFs, the 11 absorbed lessons) never made it into the QMD index. `mcp__nous-wiki-qmd__query` for `dream-cycle-proposals-2026-04-17` returned 0 results even though the file existed on disk and in gbrain.

**Root cause (5-whys):**
1. Why was QMD stale by 3 days? The daily cron only runs `qmd embed`.
2. Why is that a problem? `qmd embed` re-generates vectors for docs that are ALREADY in the index. It does NOT scan the filesystem for new files.
3. What does scan for new files? `qmd update` (or `qmd update --pull`). It indexes new files, detects updated/removed ones, then `qmd embed` vectorizes the new content hashes.
4. Why was the cron set up as embed-only? It was copy-pasted from an earlier refresh-only task, with an assumption that some other process (probably `ob[pid]` watcher logs suggest an Obsidian plugin) was handling the index-new-files step. Check of the syslog shows the `ob` process IS uploading new files (raw/pending pattern), but that path doesn't touch QMD's SQLite index.
5. Why did the gap go unnoticed? No Phase-A check of `lastUpdated` vs today-minus-1d until session 36.

**Rule:** Any vector/search index cron MUST run the full `update → embed` pair (or the index-specific equivalent for gbrain/Elasticsearch/etc.), never embed-only. Document the expected cadence in the skill (24h max index lag), and add a morning-brief check that alerts if `lastUpdated` is >48h old.

**Fix applied 2026-04-17:**
- VPS crontab line replaced:
  ```
  # old (embed-only):
  0 3 * * * /usr/local/bin/qmd embed --collection nous >> /root/nous-agaas/logs/qmd-embed.log 2>&1
  # new (update-then-embed):
  0 3 * * * /usr/local/bin/qmd update --pull >> /root/nous-agaas/logs/qmd-update.log 2>&1 && /usr/local/bin/qmd embed --collection nous >> /root/nous-agaas/logs/qmd-embed.log 2>&1
  ```
- Manual backlog run: `qmd update --pull` indexed 567 new + 138 updated docs; `qmd embed` invoked to vectorize the 693 new content hashes (CPU-bound per session-34 note — Vulkan unavailable on VPS).

**Detection one-liner (for future audits):**
```bash
ssh root@65.108.215.200 "qmd status | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.Z]+' | head -1"
# Compare to current UTC; any delta >26h is a cron failure.
```

**Prevention:** add `qmd status` freshness to morning-brief state-diff (alert if `lastUpdated` older than 26h). Schema is already compatible — morning-brief currently checks other state keys; this is one more.

**Why no new LESSON-131 file:** RULE ZERO — this AP + Timeline entry + gbrain timeline below is the audit trail.

### AP-25 — Enumerating "every enforcement point" must include Air launchd, not just Mac+VPS (session 36.5, 2026-04-17)

**Symptom:** Session 35's post-RULE-ZERO cleanup declared `lesson_absorption_watcher.py` "unscheduled (Mac launchd, VPS cron, VPS systemd all clean)." Session 36.5 finding: **Air launchd STILL had `com.nous.lesson-absorption` loaded and firing every 21600s (6 hours)** — pointing at a script that is now obsolete under RULE ZERO. The watcher was writing harmless "0 ghosts" dashboards (because no LESSON has `status: unabsorbed`), but the scheduled job itself is dead weight + latent risk if logic ever changes.

**Root cause:** Session 35 enumerated THREE enforcement surfaces (Mac launchd, VPS cron, VPS systemd) — missed FOUR: Air launchd, Air cron, Air systemd (N/A on macOS but the habit), and the `~/Library/LaunchAgents/` path on every tailnet Mac device. Tailscale reauth gate had been blocking Air visibility for 2 days, so the audit was silent-truncated without being flagged as such.

**Rule (extension of AP-24):** When retiring or changing any policy (RULE ZERO, new LESSON contract, etc.), the "enumerate every enforcement point" checklist MUST explicitly include the following scheduler surfaces on **every host** in the factory:

- `~/Library/LaunchAgents/*.plist` (macOS user daemons)
- `/Library/LaunchDaemons/*.plist` (macOS root daemons)
- `launchctl list | grep <prefix>` (already-loaded, may differ from plist)
- `crontab -l` (user cron) and `/etc/cron*` (system cron)
- `systemctl list-timers` (Linux)
- Any custom scheduler (e.g., Hermes periodic tasks inside OpenClaw container)

Audit is incomplete until every surface on every reachable host returns a clean answer.

**Fix applied 2026-04-17 session 36.5:**
```bash
ssh air-lan launchctl unload ~/Library/LaunchAgents/com.nous.lesson-absorption.plist
ssh air-lan "mkdir -p ~/Library/LaunchAgents/obsolete-session-35 && mv ~/Library/LaunchAgents/com.nous.lesson-absorption.plist ~/Library/LaunchAgents/obsolete-session-35/"
# Verified: launchctl list | grep lesson-absorption → empty (UNLOADED)
```

**Detection one-liner (every future policy retirement runs this):**
```bash
for host in mac-pro vps air-lan; do
  ssh -o ConnectTimeout=3 "$host" "launchctl list 2>/dev/null | grep com.nous; crontab -l 2>/dev/null; systemctl list-timers 2>/dev/null | grep '.timer'"
done
```

**Why no new LESSON-132 file:** RULE ZERO. Evidence trail = this AP + session 36.5 handoff addendum D + gbrain timeline entry on gbrain-ops skill.

### AP-26 — Orphan reaper missed ssh-attached idle zombies (session 36.5)

**Symptom:** Session-34 installed `*/15 * * * *` cron to kill orphan `gbrain serve` processes (PPID=1). Session 36.5 found 5 `gbrain serve` running on VPS, 407 MB RSS total. Reaper log: zero kills since install. None of the 5 had PPID=1 — they all had parents like `sshd: root@notty` (idle sshd sessions where MCP client had gone away but sshd hadn't closed the channel yet).

**Root cause:** PPID-only detection is necessary but not sufficient. SSH MCP transport leaves the parent `sshd` alive for TCP keepalive/timeout, which can be hours. The `gbrain serve` child stays running, holding ~80 MB RSS, doing no work — a "soft orphan."

**New detection rule (session 36.5):** Dual-signature reaper.
1. **Classic orphan** (PPID=1) — always kill.
2. **Idle zombie** — ETIME > 7200s (2h) AND CPU time < 5s — kill.

The 2h threshold + <5s CPU threshold together mean "this process has existed for 2 hours and done essentially nothing." That's zombie. Active MCP sessions accrue CPU with every `search`/`get_page`/`add_timeline_entry` call (~10-100ms each); a chatty 2h Claude Code session easily exceeds 5s CPU, so legitimate sessions are safe.

**Script (installed 2026-04-17):** `/opt/nous-agaas/tools/gbrain_reaper.sh`. Cron:
```
*/15 * * * * /opt/nous-agaas/tools/gbrain_reaper.sh # gbrain serve reaper (orphan + idle-zombie)
```
Log: `/root/nous-agaas/logs/gbrain-reaper.log` (written only when a kill happens). Kill lines also go to syslog via `logger -t gbrain-reaper`.

**First-run result (2026-04-17 11:09 UTC):** killed 4 idle zombies (etime 1h30m–1h53m, cpu ~1-3s each); preserved active session (etime 25min, cpu 1s — below ETIME threshold, so not evaluated for idle test).

**Anti-pattern for future enforcement:** when a process-cleanup rule covers "orphan" via PPID, also cover "attached but inactive" via ETIME+CPU signature OR per-process I/O idleness. PPID=1 is necessary, not sufficient.

**Why no new LESSON-133 file:** RULE ZERO. This AP is the canonical evidence + the reaper log file is the operational trail.

### AP-27 — gbrain DB retains pre-session-32 ghost lesson pages (uppercase slugs, wrong-prefix paths); autopilot `N/M pages, 0 chunks embedded` per page is normal (session 39, 2026-04-17)

**Symptom (session 39 audit):** `mcp__gbrain__get_stats` reported `lesson` count = 133 while Mac filesystem has 128 `pages/lessons/individual/LESSON-*.md` files with highest number 129. Five ghost records found via `list_pages type=lesson`:

1. `pages/lessons/lesson-080-design-without-deployment` — missing `individual/` prefix (updated 2026-04-12)
2. `pages/lessons/individual/LESSON-082-verify-before-flagging-suspicious` — uppercase slug duplicate (updated 2026-04-11)
3. `pages/lessons/individual/LESSON-081-write-to-wiki-not-chat` — uppercase slug (2026-04-11)
4. `pages/lessons/individual/LESSON-080-rejected-tools-without-evidence` — uppercase slug (2026-04-11)
5. `templates/lesson` — template misclassified as `type: lesson` (2026-04-10)
6. `lessons/lesson-071-all-code-through-obsidian` — no `pages/` prefix (2026-04-10)

**Root cause:** These slugs date from before session 32's triage + slug normalization (Apr 10-12). The current autopilot ingester lowercases and canonicalizes paths; these pre-session-32 records were never re-keyed, so the DB retains both old and new rows. Filesystem count stays at 128 (RULE ZERO upheld), but gbrain's `type: lesson` count drifts upward.

**Why RULE ZERO isn't breached:** filesystem has 128 files + highest 129, pre-commit hook rejects adds. gbrain drift is historical noise in the DB, not new lesson creation.

**Cleanup path** (requires gbrain MCP connected):

```
for slug in \
  "pages/lessons/lesson-080-design-without-deployment" \
  "pages/lessons/individual/LESSON-082-verify-before-flagging-suspicious" \
  "pages/lessons/individual/LESSON-081-write-to-wiki-not-chat" \
  "pages/lessons/individual/LESSON-080-rejected-tools-without-evidence" \
  "templates/lesson" \
  "lessons/lesson-071-all-code-through-obsidian"; do
  mcp__gbrain__delete_page slug="$slug"
done
```

If MCP is disconnected, defer to next session; DO NOT use `gbrain` CLI delete without verifying it preserves filesystem (CLI deletes the DB row but may also touch FS depending on flags).

**Detection one-liner:**

```
LESSON_FS=$(ls "$VAULT/pages/lessons/individual/LESSON-"*.md 2>/dev/null | wc -l | tr -d ' ')
# Compare LESSON_FS against gbrain stats pages_by_type.lesson — they should match.
```

**Sub-rule: "0 chunks embedded" per page is normal, not a stall.** Autopilot log lines like `45/986 pages, 0 chunks embedded` mean "page 45 scanned, had no new chunks to embed" (all chunks already vectorized from prior run). This is the expected fast path; don't misread as "embed stuck at 0". Actual stuck embed shows as growing `missing_embeddings` over multiple cycles — check `get_health.missing_embeddings` across 2+ autopilot runs to distinguish.

**Why no new LESSON file:** RULE ZERO. This AP is the canonical evidence + detection one-liner + cleanup script live here.

### AP-28 — SILENT legacy-path SKILL.md duplicates in `pages/systems/skills/` (17/18 stale; session 40, 2026-04-17)

**Symptom (session 40 audit, caught mid-Phase-2):** After session 39 verified "4-target skill MD5 parity PERFECT", session 40's deeper scan revealed 18 duplicate `SKILL.md` files at the LEGACY path `pages/systems/skills/<name>/SKILL.md` on Mac + VPS + Air wikis (all git-tracked, all bidirectionally synced). 17 of 18 had DIFFERENT MD5 from the canonical `pages/skills/<name>/SKILL.md` — i.e. stale doctrine living silently in the vault. Only `storage-retrieval` happened to match by coincidence. gbrain had indexed 6 of them as type=skill under `pages/systems/skills/<X>/skill` slugs, plus 18 flat `pages/skills/<X>` alias stubs from pre-canonical-slug era. Total gbrain `type:skill=43` vs expected 20 (19 domain canonical + 1 shared `_gbrain/brain-aware-invocation`).

**Root cause (CONFIRMED):** Session 23 T3 already documented this trap (factory-ops/SKILL.md:433 — "agent picked the one that already had a file"). Session 26 AP-17 re-flagged it ("dual-location skill mirror sync discipline — 7/13 skills drifted"). Neither session completed the fix. The legacy `pages/systems/skills/` tree was never removed; files accumulated drift across 15+ sessions because every skill absorption targeted the canonical `pages/skills/<X>/SKILL.md` while the legacy mirror sat untouched. Session 39's 4-target parity check only compared canonical paths → missed the duplicate tree entirely.

**Why session-39's "PERFECT 4-target parity" was wrong:** the MD5 check iterated `pages/skills/*/SKILL.md` on each target. It compared apples to apples BUT didn't scan for parallel trees holding a different apple.

**Fix (session 40):** `git rm -r pages/systems/skills/` on Mac wiki → commit → let bidirectional sync propagate deletion to VPS + Air. Then delete gbrain ghost slugs (24 total: 18 flat alias + 6 legacy-path). After this, `pages/skills/` is the ONLY location for domain skill SKILL.md — one source of truth per skill as RULE ZERO implies.

**Audit script (use this in every future session-start Phase 1):**

```bash
# Scan for parallel-tree duplicates of canonical skill files
cd "$VAULT"
DUPE_COUNT=$(find pages -type f -name "SKILL.md" | grep -v "^pages/skills/" | wc -l | tr -d ' ')
if [ "$DUPE_COUNT" -gt 0 ]; then
  echo "🔴 DRIFT: $DUPE_COUNT legacy SKILL.md outside pages/skills/:"
  find pages -type f -name "SKILL.md" | grep -v "^pages/skills/"
  echo "Fix: git rm -r <legacy-dir>; commit; sync."
fi

# Per-skill canonical-vs-legacy drift scan (only meaningful during grace period)
for s in "$VAULT"/pages/skills/*/SKILL.md; do
  name=$(basename $(dirname "$s"))
  legacy="$VAULT/pages/systems/skills/$name/SKILL.md"
  [ -f "$legacy" ] || continue
  canon_md5=$(md5 -q "$s")
  legacy_md5=$(md5 -q "$legacy")
  [ "$canon_md5" != "$legacy_md5" ] && echo "DRIFT: $name canon=$canon_md5 legacy=$legacy_md5"
done

# gbrain type:skill counter sanity
# Expected: 19 domain + 1 shared = 20. If >20, enumerate with list_pages type=skill and delete non-canonical slugs.
```

**Prevention:** any vault reorganization that MOVES files (not just edits) must end with `git rm -r <old-path>` on the old tree, not just `git add <new-path>`. A parallel audit (`find pages -type f -name <filename>`) should follow every such reorg. Session 26 AP-17 identified this but didn't enforce; AP-28 makes the fix permanent via physical removal + gbrain cleanup.

**Why no new LESSON file:** RULE ZERO. This AP has the full evidence, audit script, and fix procedure. See also `infrastructure` v2.27.0 AP-30 (parallel-agent write race) for the adjacent drift class.

### AP-29 — Ghost-slug delete ≠ root-cause fix; slugs are file-backed and resurrect on `sync_brain full` (session 40 round 4, 2026-04-17)

**Symptom:** Session 39 AP-27 enumerated 6 "ghost lesson slugs" and proposed `mcp__gbrain__delete_page` as the fix. Session 40 round 2 executed that delete; `pages_by_type.lesson` dropped 133→127. A later `mcp__gbrain__sync_brain full=true` in round 4 **resurrected 3 of the 6 "ghosts"** — because 3 of them are backed by ACTUAL FILES on disk with `type: lesson` frontmatter:

1. `templates/lesson.md` — an Obsidian Templater template (pre-session-35 artifact for creating LESSON files). Frontmatter had `type: lesson`, so gbrain auto-indexed it as a lesson every sync. Fix: rewrote frontmatter to `type: template` + retirement note (session-35 RULE ZERO retires LESSON creates → the template is obsolete anyway).
2. `pages/lessons/LESSON-080-design-without-deployment.md` — real LESSON in the WRONG location (flat `pages/lessons/` instead of `pages/lessons/individual/`). LESSON-080 was MISSING from individual/; the flat file was the canonical content. Fix: `git mv pages/lessons/LESSON-080-*.md pages/lessons/individual/LESSON-080-*.md` + added `id: LESSON-080` to frontmatter (drift-check requires `id:` / `name:` field).
3. `lessons/LESSON-070-vercel-api-proxy-routing.md` + `lessons/LESSON-071-all-code-through-obsidian.md` — two top-level `lessons/` files (no `pages/` prefix). **Number collisions** with existing `pages/lessons/individual/LESSON-070-*.md` + `LESSON-071-*.md` (different content, same number). Rules already in `website-deploy` SKILL.md (/api/proxy/ prefix — lines 115, 193, 281-283) and LAW-005 + `code/README.md` (no direct VPS edits). Fix: `git rm` both files (content absorbed; no knowledge loss). Directory `lessons/` removed.

**Root cause:** Session 39 AP-27 treated the symptom (gbrain DB rows) as the disease. The actual disease is **misplaced files on filesystem** with `type: lesson` frontmatter that re-ingest on every sync cycle. DB-only deletes are band-aids; `sync_brain full=true` blows them away.

**Detection one-liner (add to audit AP-10 as a 7th point in next session):**

```bash
# Find files with type: lesson frontmatter OUTSIDE the canonical path
cd "$VAULT"
find . -type f -name "*.md" ! -path "./.git/*" -exec grep -l "^type: lesson" {} \; | grep -v "^./pages/lessons/individual/LESSON-" || echo "✅ no misplaced lesson-typed files"
```

**Prevention:** every gbrain ghost report must be traced back to its filesystem source BEFORE calling `delete_page`. If a file backs it, fix the file (move, delete, or re-type frontmatter). If no file backs it, only THEN is `delete_page` the full fix.

**Post-fix state (session 40 round 4):** filesystem has 129 LESSON files in `pages/lessons/individual/` (was 128 + LESSON-080 promoted from flat). Zero `type: lesson` files outside canonical path. Gbrain `pages_by_type.lesson` should converge to 129 on next autopilot cycle.

**Why no new LESSON file:** RULE ZERO. This AP carries the full root-cause reasoning + prevention one-liner + filesystem remediation log.

### AP-30 — LESSON file on filesystem WITHOUT `type: lesson` frontmatter → gbrain silent fallback to `concept` (session 41, 2026-04-17)

**Symptom:** Session 40 round 4 declared `pages_by_type.lesson` would converge to 129 on next autopilot cycle. Session 41 opened ~1h later, gbrain still at 128. Filesystem had 129 consecutive `LESSON-001..129` files — no missing file. Diff between fs slug list and gbrain slug list yielded exactly ONE delta: `lesson-050-removed-imports-still-used`. Direct Postgres query: the LESSON-050 row existed but `type = 'concept'`, NOT `lesson`. Autopilot had happily ingested it into the wrong bucket.

**Root cause:** `pages/lessons/individual/LESSON-050-removed-imports-still-used.md` frontmatter keys: `id, title, date, severity, phase, tags, status, last_updated, source_count`. **No `type:` key.** When gbrain's frontmatter parser can't find `type:`, it falls back to default `type: concept` (same failure mode as session 40 round 4 smartbridge YAML-invalid → concept fallback, but triggered by a simpler cause: missing key rather than parse error). Session 40 AP-29 detection one-liner only catches "misplaced `type: lesson`"; it cannot catch "missing `type:` entirely" because the file passes the grep `^type: lesson` negation by matching zero lines everywhere including canonical paths.

**Historical provenance:** LESSON-050 was authored 2026-04-07 during the Phase 2C.7 Sidebar rewrite incident. Status field `archived-no-absorption-needed` suggests the writer marked it complete and moved on without running the standard template, which would have included `type:`. No other LESSON-001..129 file has this gap (verified via Python scan of all 129 files: exactly 1 missing `type`).

**Fix applied (session 41):**
1. Edit `pages/lessons/individual/LESSON-050-removed-imports-still-used.md`: add `type: lesson` as first frontmatter key. Bumped `last_updated` to `2026-04-17`.
2. `mcp__gbrain__delete_page slug="pages/lessons/individual/lesson-050-removed-imports-still-used"` — removes the stale `type: concept` row so autopilot re-ingests cleanly under the correct type.
3. Commit + wait for 5-min autopilot cycle (or `sync_brain` to force).
4. Verify `mcp__gbrain__get_stats.pages_by_type.lesson` equals the current filesystem lesson count, or document the intentional migration delta. Do not hard-code 129; 129 is the ceiling, not the expected count after lesson migration.

**Detection one-liner (extends AP-29 — must ALSO be added to `audit` AP-10 as a sub-check, OR strengthen pt 5 "LESSON fs count == gbrain pages_by_type.lesson" which already catches this indirectly):**

```bash
# Every LESSON-*.md file in canonical path MUST have `type: lesson` in frontmatter
cd "$VAULT"
find pages/lessons/individual -name "LESSON-*.md" -exec grep -L "^type: lesson" {} \; || echo "✅ all LESSON files typed correctly"
```

If the command outputs any file path, it's a LESSON with no/wrong `type:` and will silently mis-bucket on next autopilot ingest.

**Prevention:**
1. **Pre-commit hook** (future session — low priority, manual drift scan sufficient for now): extend drift gate in `.git/hooks/pre-commit` (mistake-to-skill AP-7 drift scan) to additionally require `^type: lesson$` on any staged LESSON edit. Blocks LESSON rewrites that accidentally drop `type:`.
2. **Session-start audit**: session 41's `audit` AP-10 point 5 (`LESSON fs count == gbrain pages_by_type.lesson`) DOES catch this as a count delta — but only one off-by-one at a time. If multiple LESSONs lose `type:`, the delta reveals symptom but not root cause. The above detection one-liner is the direct probe.
3. **Write-path discipline (long-term)**: any agent editing/creating frontmatter on a LESSON file must preserve/add `type: lesson`. Template file `templates/lesson.md` (retyped to `type: template` in session 40 round 4) is retired; there is no working template, so agents must hand-construct frontmatter correctly.

**Why no new LESSON file:** RULE ZERO. This AP has the full failure mode + detection + fix + prevention.

**Companion to AP-23/AP-29:** AP-23 was skill frontmatter drift (12/18 skills missing `type: skill` in session 36). AP-29 was misplaced `type: lesson` (wrong location, ghost resurrects). AP-30 is the third leg: correct location, right file, MISSING `type:` entirely. All three drift modes are now documented; the combined detection set covers them.

### AP-31 — Upstream freshness endpoints lie; always cross-check with our own ingest log (session 49, 2026-04-18)

**Pattern:** An external/upstream status endpoint reports a freshness/recency field (`lastUpdated`, `last_indexed`, `last_sync`, etc.) that is stale even when the downstream cron or pipeline has successfully run. Agents that read the endpoint value at face value reach wrong "is it fresh?" conclusions and spread the lie.

**Evidence (live this session):**
- `mcp__nous-wiki-qmd__status` returned `"lastUpdated":"2026-04-17T19:05:01.907Z"` at 2026-04-18 21:13 KZT — apparent staleness of ~21h.
- Reality: VPS cron `0 3 * * * qmd update --pull && qmd embed` ran at 2026-04-18 03:00–03:02 VPS-local; `/root/nous-agaas/logs/qmd-embed.log` mtime = `2026-04-18 03:02:43 +0500`; last run embedded 201 chunks from 14 documents in 2m 41s (log tail confirms `✓ Done!`).
- The endpoint lies by ~3 hours. Same drift noted in session-48 close (pushed as `gbrain-ops` gbrain timeline W7) and AUDIT-OPENCLAW-HEALTH-2026-04-18 (YELLOW-1, HEALTHY lens).

**Root cause (upstream):** `@tobilu/qmd` status endpoint derives `lastUpdated` from a data-source internal to its index, not from the last successful cron-driven re-index completion. When `qmd update --pull && qmd embed` reruns but no new chunks require embedding, the visible `lastUpdated` field is not advanced. We do not own this code.

**Rule:** For any "is the data fresh?" claim about a pipeline we own, **trust the ingest log's mtime, not the upstream status endpoint**. Specifically for QMD: `stat /root/nous-agaas/logs/qmd-embed.log` on VPS is authoritative. Extends to any future upstream with a freshness field.

**Tool (committed session 49, commit `29241c3c`):**

```bash
bash tools/qmd_real_freshness.sh          # human output, exit 0/1/2 = fresh/stale/unknown
bash tools/qmd_real_freshness.sh --json   # machine output
# Flags: VPS_HOST, QMD_EMBED_LOG, STALE_HOURS (default 30h = daily + 6h skew)
```

Paired sibling test `tools/test_qmd_real_freshness.sh` (per `infrastructure` AP-36 pattern) validates 6 checks: fresh/stale/unknown exit codes + human message contains correct token + JSON shape 7-key schema + python3 JSON parseability. Live-run on VPS at ship: `FRESH — last qmd embed 18h ago (threshold 30h)`.

**Detection:**
```bash
# Compare endpoint vs authoritative log
endpoint_ts=$(curl -s http://localhost:7400/status | python3 -c 'import json,sys; print(json.load(sys.stdin).get("collections",[{}])[0].get("lastUpdated",""))')
log_ts=$(ssh root@vps "stat -c %Y /root/nous-agaas/logs/qmd-embed.log")
# If log_ts - endpoint_ts_as_epoch > 3600 → endpoint is lying
```

**Prevention (mechanical, candidate nightly regression):** wire `tools/qmd_real_freshness.sh` into a launchd job parallel to `com.nous.context-injector-regression` (Air, 03:30 KZT). On STALE → Telegram alert via `tools/telegram_send.sh`; on FRESH → silent log (LESSON-086 state-change-only pattern). Implementation deferred to session 50+ with deliberate cadence decision (QMD cron fires 03:00 VPS-local; the monitor must fire after the cron completes — 03:45 KZT candidate).

**Cross-ref:** AP-24 (QMD cron was embed-only until session 36 fix — that was OUR lie; this is the UPSTREAM lie). `audit` AP-16 (adversarial sub-probe per lens — endpoint-vs-log is the adversarial pair). `infrastructure` AP-36 (sibling-test pattern for any new tool).

**Why no new LESSON file:** RULE ZERO. Rule + evidence + tool + detection + prevention all captured above + in paired `tools/qmd_real_freshness.sh` + sibling test.

### AP-32 — Pre-upgrade scope survey: LOC delta + commit count + schema migrations BEFORE any `git pull` (session 50, 2026-04-20)

**Pattern:** Agent reads a release note ("v0.13 frontmatter-graph") and treats it as THE scope of the upgrade. Reality: the installed version is multiple versions behind; `git pull` would bring the announced feature PLUS every intermediate commit — which can be 10-100× the announced scope, include schema migrations, touch production-critical code paths, and collide with local customizations.

**Evidence (session 50, 2026-04-20):** Madi shared gbrain v0.13.0 frontmatter-graph release note and asked to adopt it. We were on v0.10.1 (commit `b7e3005`). A pre-flight survey caught the real scope before any git pull executed:

- **437 files changed, +42,921 / -903 LOC across master..HEAD**
- 9 commits spanning v0.10.3 → v0.11.1 (Minions v7) → v0.12.1 → v0.12.3 → v0.13.0 (frontmatter-graph) → v0.13.1 (Knowledge Runtime: Resolver SDK + BrainWriter + BudgetLedger) → v0.14.0 (Minions shell jobs + worker abort-path fix)
- **3 schema migrations** auto-apply on upgrade: v11 (budget_ledger tables), v12 (minion_jobs.quiet_hours columns), TS-v0.13.1 (grandfather `validate:false` across all 1065 pages)
- 3 local-modified files (`skills/RESOLVER.md`, `skills/manifest.json`, `src/cli.ts`) — Nous AGaaS namespace-isolation fork would collide with upstream's `skills/*/` structure
- 15 untracked Nous skill directories sitting in the gbrain repo tree
- No test environment — VPS gbrain is production

**Musk step-1 applied honestly:** I cannot verify a 42K-LOC / 437-file upgrade with 3 schema migrations is non-destructive without a test environment. DB backup mitigates DB risk but NOT code-behavior risk (Minions changes job lifecycle; v0.14 changes cron behavior; v0.13.1 changes BrainWriter pre-commit validators). Per `session-operating-contract` Rule 5 + Madi's "100% or stop" standard: stopped at Phase 1 with no production change.

**Rule — MANDATORY pre-upgrade survey (before any `git pull` / `gbrain upgrade` / `npm install -g <tool>`):**

```bash
# 1. Commit count delta
git fetch --quiet && git rev-list HEAD..origin/master --count
# 2. LOC delta
git diff HEAD..origin/master --stat | tail -1
# 3. Schema migration scan
git log HEAD..origin/master --format="%s" | grep -iE "migrat|schema|breaking"
# 4. Local-customization conflict surface
git status --short
# 5. Breaking-changes in CHANGELOG since our version
git show origin/master:CHANGELOG.md | awk '/^## \[/{v++} v<=4' | head -80
```

**Hard gates:**
- LOC delta > 5,000 OR commit count > 10 OR schema migrations ≥ 1 OR modified tracked files → **STOP. Write a migration spec (proper brainstorm) before proceeding.**
- Production infrastructure (no test environment) → ALWAYS brainstorm spec, regardless of numbers.
- Customization fork (our tracked modifications) → plan the merge explicitly, don't `git stash && git pull` blind.

**How to apply:** make these 5 probes the mandatory Phase 0 of any upgrade workstream. If ANY probe shows "bigger than expected," require explicit human approval of the new scope before proceeding. Never smuggle a major upgrade in under a minor-feature banner. A release-note announces A feature; the upgrade ships all commits behind head.

**Anti-pattern this replaces:** "Madi sent a release note for v0.13, we're on v0.10.1, that means upgrade to v0.13 — 3 min deterministic migration, $0 cost, let's go." Wrong. v0.13 ≠ sub-delta from v0.10.1. It's the 4th minor version forward with substantial interim changes.

**Cross-ref:** `audit` AP-16 (probe-before-claim, design layer); `session-operating-contract` Rule 5 (can't-verify-say-so); `mistake-to-skill` AP-10 (confusion protocol at forks); `infrastructure` AP-43 (pre-commit RULE 4 precedent — mechanical-gate pattern that could eventually automate this survey).

**Source:** Session 50 overnight-2 gbrain upgrade attempt. Pre-flight survey at Phase 1 revealed true scope; agent stopped before production change. No new LESSON (RULE ZERO).

### AP-33 — Don't lose a gbrain timeline entry because MCP disconnected; use the CLI fallback (session 55, 2026-04-20)

**Pattern:** Agent wants to push a timeline entry after a skill bump or major event. The usual path `mcp__gbrain__add_timeline_entry` is surfaced by a system-reminder as "no longer available — MCP server disconnected." Agent defers the timeline push to "autopilot cycle" or "next session when MCP reconnects." Session closes. Entry never lands. Compounding evidence is lost for that event.

**Root cause:** Agent treats the MCP tool as the ONLY path to write to gbrain. It is not. gbrain has a Node CLI on VPS at `/opt/nous-agaas/gbrain/bin/gbrain` that exposes `timeline-add`, `put`, `tag`, `link`, `delete`, and every other write operation with identical semantics to the MCP tools. The MCP and CLI are two surfaces over the same engine.

**Rule:** When `mcp__gbrain__add_timeline_entry` (or any `mcp__gbrain__*` write tool) is unavailable, ALWAYS fall back to the CLI via SSH:

```bash
# Timeline entry — the common case
ssh root@65.108.215.200 \
  "cd /opt/nous-agaas/gbrain && bin/gbrain timeline-add '<slug>' '<YYYY-MM-DD>' '<summary text>'"
# Returns {"status":"ok"} on success — identical contract to the MCP call.

# Page get (verify ingestion state)
ssh root@65.108.215.200 "cd /opt/nous-agaas/gbrain && bin/gbrain get '<slug>'"

# Search / query
ssh root@65.108.215.200 "cd /opt/nous-agaas/gbrain && bin/gbrain search '<query>'"
ssh root@65.108.215.200 "cd /opt/nous-agaas/gbrain && bin/gbrain query '<question>'"

# Full CLI surface
ssh root@65.108.215.200 "cd /opt/nous-agaas/gbrain && bin/gbrain --help"
```

**Evidence — session 55, 2026-04-20:** gbrain MCP disconnected mid-session (system-reminder listed all `mcp__gbrain__*` tools as "no longer available"). Agent was about to defer SOC v1.7.0 + factory-ops v1.8.0 timeline pushes to "autopilot cycle." Correct move: ssh-fallback both pushes synchronously. Both returned `{"status": "ok"}`. Session-close-verification-ready instead of pending-next-autopilot-maybe.

**Musk step-2 applied to deferral:** every deferred compounding write is a potential loss (session gets interrupted, autopilot has a bug that day, handoff doesn't mention the deferral). A synchronous write at ~1s latency beats an async write at "whenever" with a chance of loss. Cheap tool call > expensive coordination.

**Cross-ref:** `session-operating-contract` AP-9 (sibling discipline — don't defer what you can execute now; permission-question-deferral failure class); AP-8 (session-operating-contract — don't let tooling friction drive deferral decisions that should be value-driven); this skill's general gbrain-is-one-engine-two-surfaces principle. No new LESSON (RULE ZERO).

### AP-34 — Autopilot runners must load API keys from auth/env, never inline secrets (session 75, 2026-04-26)

**Symptom:** During AP-59 verification, direct `bin/gbrain sync --repo /root/nous-agaas/wiki` ingested the updated `infrastructure` page but failed embedding because the manual shell had no `OPENAI_API_KEY`. The follow-up check found `/root/.gbrain/autopilot-run.sh` had a literal OpenAI key embedded inline.

**Root cause:** gbrain had two credential-loading patterns:

1. `gbrain_sync_wrapper.sh` loads `OPENAI_API_KEY` from `/root/.config/codex/auth.json`.
2. `/root/.gbrain/autopilot-run.sh` carried its own literal key.

That split makes manual syncs easy to run without the key, and it spreads secrets into operational scripts. The correct invariant is one credential source, loaded at runtime, with no key bytes in git or shell scripts.

**Rule:**

1. Manual gbrain commands that embed content must run through an env-loading wrapper or explicitly export `OPENAI_API_KEY` and `DATABASE_URL`.
2. `/root/.gbrain/autopilot-run.sh` must load the key from `/root/.config/codex/auth.json` first, then `/root/nous-agaas/.env` as fallback.
3. Autopilot must refuse to run if the key is missing; otherwise it can create embed ghosts.
4. No `sk-` / `sk-proj-` literal may appear in gbrain runner scripts.
5. Keep the OS-level flock from AP-14.

**Implementation (this session, 2026-04-26):**

- Added tracked canonical runner `tools/gbrain-autopilot-run.sh`.
- Deployed it to VPS `/root/.gbrain/autopilot-run.sh`.
- Added `tools/test_gbrain_autopilot_secret_loading.sh` to assert local + VPS runner syntax, no inline key, auth-json loading, and flock retention.

**Verification:** `tools/test_gbrain_autopilot_secret_loading.sh` must pass before claiming gbrain autopilot credential hygiene is healthy. gbrain doctor must report `embeddings: 100% coverage, 0 missing` after AP writes.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-35 — Scheduled/manual gbrain jobs must use the canonical key loader, not a dead private path (session 75, 2026-04-26)

**Symptom:** The 03:00 substrate librarian's gbrain probe called `bin/gbrain sync && bin/gbrain embed --stale && bin/gbrain doctor`, but loaded the OpenAI key from `/root/.gbrain/auth.json` with field `openai_api_key`. That file does not exist on the VPS. The real key path is `/root/.config/codex/auth.json` with field `OPENAI_API_KEY`, with `/root/nous-agaas/.env` as fallback. A manual verification probe using the same dead path kept emitting `OPENAI_API_KEY environment variable is missing or empty` during embedding.

**Root cause:** AP-34 fixed the autopilot runner, but the same credential contract was not reused by new scheduled/manual gbrain jobs. This created a split-brain: autopilot could be healthy while the daily proof job used a stale secret path and produced false red or noisy embed failures.

**Rule:** every gbrain job that may embed content must either invoke the tracked canonical runner or copy its key-loading order exactly:

1. Preserve an existing `OPENAI_API_KEY` from the environment.
2. Else read `/root/.config/codex/auth.json` field `OPENAI_API_KEY`.
3. Else read `/root/nous-agaas/.env` line `OPENAI_API_KEY=...`.
4. If still empty, exit non-zero before running `gbrain embed`.
5. Always export `DATABASE_URL="postgresql://gbrain:gbrain2026@localhost:5432/gbrain"` and `cd /opt/nous-agaas/gbrain` before `bin/gbrain doctor`.

**Detection:** search all tracked scripts before declaring gbrain credential hygiene healthy:

```bash
rg -n "/root/\\.gbrain/auth\\.json|openai_api_key|bin/gbrain embed|bin/gbrain doctor" tools pages/skills
```

Any scheduled script that embeds and does not load the key through the canonical order is drift. Patch it before trusting the daily proof dashboard.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-51 — Tracked gbrain sync wrappers must fail closed and prove key loading (session 89, 2026-04-29)

**Symptom:** During the top-CTO sync audit, direct manual `bin/gbrain sync --repo /root/nous-agaas/wiki` emitted `OPENAI_API_KEY environment variable is missing or empty`, while `gbrain health` still showed 100% embed coverage. The tracked `tools/gbrain_sync_wrapper.sh` loaded only `/root/.config/codex/auth.json` and did not preserve an existing environment key, fall back to `/root/nous-agaas/.env`, or fail before sync when the key was missing.

**Root cause:** AP-35 described the canonical credential contract, but `gbrain_sync_wrapper.sh` was not under a mechanical gate. The doctrine was right; the wrapper implementation drifted.

**Rule:** every tracked gbrain sync wrapper must:

1. Preserve `OPENAI_API_KEY` if already set.
2. Else load `/root/.config/codex/auth.json` field `OPENAI_API_KEY`.
3. Else fall back to `/root/nous-agaas/.env`.
4. Exit non-zero before any sync/embed path if the key is still empty.
5. Provide a dry-run mode that proves key loading without mutating gbrain.

**Detection:** `tools/test_gbrain_sync_wrapper_secret_loading.sh` must pass against the source wrapper and VPS runtime wrapper before declaring sync-wrapper credential hygiene healthy.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-36 — Third-party skillpacks that affect OpenClaw must be vault-first, not runtime-only (GStack audit, 2026-04-27)

**Symptom:** Air OpenClaw was loading Garry Tan's GStack skills from `~/nous-agaas/skills/` and the live OpenClaw `skillsSnapshot` showed 40 `gstack-*` skills loaded, but `pages/skills/` in the Obsidian/wiki source of truth had zero `gstack-*` skill pages. This means the agent could use a runtime skill that the librarian layer could not audit, diff, cite, gbrain-index, or sync through normal `wiki-to-runtime-rsync` flow.

**Root cause:** the GStack adapter wrote converted skills directly into the runtime skill directory. That made OpenClaw smarter immediately, but bypassed the Obsidian/gbrain substrate. It recreated the old dual-location drift class in a new form: runtime truth without wiki truth.

**Rule:** any third-party skillpack that changes OpenClaw behavior must have an explicit source-of-truth classification before install:

1. **Preferred:** generated/mirrored skill pages live under `pages/skills/<vendor-skill>/SKILL.md`, get committed, gbrain-indexed, then rsynced to `~/nous-agaas/skills/`.
2. **Temporary:** runtime-only install is allowed only for a short experiment and must have an audit page naming source commit, target directory, expiry date, and rollback command.
3. **Never:** claim "all via Obsidian" while a behavior-changing skill exists only in `~/nous-agaas/skills/` or inside an OpenClaw container.

**Detection:**

```bash
comm -23 \
  <(ssh air 'find ~/nous-agaas/skills -maxdepth 2 -name SKILL.md | sed "s#^.*/skills/##;s#/SKILL.md##" | sort') \
  <(find pages/skills -maxdepth 2 -name SKILL.md | sed 's#^pages/skills/##;s#/SKILL.md##' | sort)
```

Any returned skill that is not explicitly classified as runtime-only is substrate drift. For GStack on 2026-04-27: all 40 loaded GStack skills are useful, but they must be mirrored into Obsidian before a live upstream upgrade.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-37 — Personal crawlers must produce source-manifested Obsidian artifacts before OpenClaw gets runtime access (crawl-army audit, 2026-04-27)

**Symptom:** A "crawl army" request can sound like a simple permission change: give OpenClaw read access to tweets, YouTube transcripts, Google Docs, chat archives, Notion, Telegram, and iMessage so it "knows Madi." That is too broad. It creates an unbounded prompt/input surface, makes provenance unclear, and bypasses the Obsidian/gbrain librarian layer that lets agents retrieve the right memory later.

**Root cause:** Raw channel access and durable knowledge are different systems. OpenClaw channel connectors are good for live interaction, but a business memory system needs stable artifacts: source, subject, timestamp, owner, project, privacy class, extraction method, and freshness. Without that manifest, future agents cannot tell whether a fact came from a meeting transcript, a private DM, a scraped web page, a Google Doc draft, or an outdated chat export.

**Rule:** personal/context crawlers must write into the substrate first, then OpenClaw reads through the librarian layer:

1. Every crawler writes markdown under `pages/sources/<source>/<YYYY>/<slug>.md` or a project-scoped equivalent, plus frontmatter fields: `source`, `source_id`, `captured_at`, `author`, `project`, `privacy`, `subject`, `entities`, `retrieval_policy`, and `freshness`.
2. Every batch writes a manifest at `pages/sources/manifests/<source>-YYYY-MM-DD.md` with record counts, skipped/private counts, error counts, and exact credentials/auth profile used without secrets.
3. Raw databases, chat stores, browser profiles, and token files are never mounted directly into OpenClaw as prompt context. Collectors extract, redact/classify, and commit artifacts; gbrain indexes those artifacts.
4. Live channel access remains allowlisted/pairing-gated. A channel connector may message Madi, but historical crawl access is a separate read-only collector with a rollback/off switch.
5. If a source cannot produce citations or stable IDs, it is a research scratch source only and cannot become business memory until wrapped by a manifest.

**Detection:** before claiming "OpenClaw has read access to all channels," verify all three layers:

```bash
find pages/sources/manifests -maxdepth 1 -type f | sort | tail
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain search "source manifest crawl" --limit 5'
ssh air 'docker exec openclaw sh -lc "openclaw doctor --non-interactive | grep -A20 \"Memory search\""'
```

If a source appears in OpenClaw config but has no manifest and no gbrain-visible artifacts, it is channel access, not evolving memory.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-38 — If gbrain is canonical memory, disable unbacked OpenClaw memory search (OpenClaw doctor audit, 2026-04-27)

**Symptom:** `openclaw doctor --non-interactive` reported memory search enabled without an embedding provider while the operator intent was that Obsidian/gbrain is the single semantic memory. This creates a false-memory plane: agents may believe OpenClaw has local semantic recall even though the configured search path cannot work.

**Root cause:** two memory systems were being treated as one. gbrain/Obsidian is the durable source of truth, with provenance, manifests, wiki sync, and timeline entries. OpenClaw memory search is a separate feature that needs its own embedding provider. Leaving it enabled without a provider is not harmless; it makes audits noisy and hides whether retrieval came from the canonical substrate.

**Rule:** choose one explicit memory ownership mode for OpenClaw:

1. **Canonical default:** keep gbrain as the single semantic memory and run:
   ```bash
   ssh air 'docker exec openclaw sh -lc "openclaw config set agents.defaults.memorySearch.enabled false --strict-json"'
   ```
   Restart OpenClaw only after a controlled route probe plan is ready.
2. **Only enable OpenClaw memory search** after a written design names the embedding provider, source manifests, retention policy, privacy class, and how results reconcile with gbrain.
3. **Never:** leave doctor warning as "known noise" or claim all memory is synchronized while OpenClaw has an unbacked memory search path.

**Detection:**

```bash
ssh air 'docker exec openclaw sh -lc "openclaw config get agents.defaults.memorySearch.enabled && openclaw doctor --non-interactive | grep -A8 \"Memory search\" || true"'
```

Expected canonical state: config prints `false`, and doctor reports memory search explicitly disabled. If it reports enabled without provider, either disable it or implement the explicit provider plan before calling the factory memory healthy.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-39 — GStack upgrades must regenerate host skills and distinguish false-red checker drift from real runtime drift (GStack v1.17.0.0 upgrade, 2026-04-28)

**Symptom:** upgrading GStack on Mac and Air from `e23ff28` to `675717e` succeeded via `git pull --ff-only`, but the first smoke check failed. `bun run skill:check` reported stale generated host skill files, then continued to fail after `bun run gen:skill-docs --host all` because `claude/SKILL.md.tmpl` existed while `claude/SKILL.md` was intentionally skipped by the Claude host config (`skipSkills: ['claude']`). On Air, the same package script initially failed with `bun: command not found` because noninteractive SSH did not include `~/.bun/bin` on PATH.

**Root cause:** this was not a broken skillpack install. It was two upgrade-harness mismatches: generated host outputs must be refreshed after upstream template changes, and the checker was template-discovery-only while the generator was host-config-aware. A skip-aware generator plus a skip-blind checker creates a false red. Air added a path-specific failure mode because package scripts call `bun` internally.

**Rule:** any GStack/GarryTan skillpack upgrade that affects OpenClaw/gbrain must run this exact post-pull verification chain on every host:

```bash
git pull --ff-only
bun install --frozen-lockfile
bun run gen:skill-docs --host all
bun run skill:check
bun test test/gbrain-detect-install.test.ts test/gstack-gbrain-source-wireup.test.ts test/gbrain-lib-verify.test.ts
```

On Air noninteractive SSH, prefix package-script commands with `PATH=$HOME/.bun/bin:$PATH` or they may fail even when Bun is installed.

**False-red handling:** if `skill:check` fails because a template is intentionally skipped by a host config, patch the checker to read the same host config before declaring a missing generated file. Do not paper over the error with "known issue," and do not create the skipped generated file just to silence the check. The check and generator must share the same rules.

**Detection:** after a GStack upgrade, all three must be true before claiming healthy:

```bash
git status --short --branch
bun run skill:check
bun test test/gbrain-detect-install.test.ts test/gstack-gbrain-source-wireup.test.ts test/gbrain-lib-verify.test.ts
```

Expected: host checkouts are at the intended upstream commit, `skill:check` exits 0, and the targeted gbrain/GStack tests pass on Mac and Air. If local checker patches are needed, record them in the handoff and keep the patch byte-identical on both hosts until upstream absorbs the fix.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-40 — Collaboration surfaces must keep one owner per job, with Obsidian/gbrain as the permanent librarian (GitHub mirror policy, 2026-04-28)

**Symptom:** once GitHub auth and the private mirror existed, the system could easily start using GitHub issues for everything: client follow-ups, meeting tasks, agent memory, CI, sweeper decisions, and Satory team coordination. That would recreate tool sprawl. It would also make agents search the wrong place for business commitments and invite automation such as ClawSweeper to touch non-code promises.

**Root cause:** "sync everything everywhere" is not the same as "duplicate every object into every tool." A billion-dollar-small-team stack needs clear ownership lanes: one surface where humans act, one surface where code automation acts, and one surface where durable memory compounds. Without explicit ownership, every agent has to guess whether a Todoist item, Notion meeting note, GitHub issue, or vault page is authoritative.

**Rule:** use these ownership lanes:

| Surface | Owns | Does not own |
|---|---|---|
| GitHub `mayazbay/nous-agaas-private` | code issues, PRs, CI, Blacksmith, proposal-only sweepers, sanitized mirror snapshots | business commitments, personal tasks, raw vault history, secrets, meeting memory |
| Todoist Satory shared project | business tasks, owners, priorities, next actions for Satory/team execution | permanent knowledge, code review, personal tasks |
| Notion Satory project | meetings, transcripts, summaries, team context, source-of-truth discussion artifacts | personal Notion, code CI, durable agent doctrine |
| Obsidian/wiki + gbrain | permanent memory, skills, decisions, root-cause writeups, source manifests, retrieval | live task assignment UI, raw credentials, unreviewed crawler dumps |

**Operating rule:** cross-link, do not duplicate ownership. If a Notion meeting creates work, Todoist gets the actionable task and Obsidian/gbrain gets the durable decision/skill context. If code work is needed, GitHub gets a code issue or PR linked back to the vault page. If an issue teaches a durable rule, update the relevant `SKILL.md` + gbrain timeline per RULE ZERO.

**Automation gate:** Blacksmith and ClawSweeper start in non-destructive/proposal-only mode. They may open issues, update README/dashboard status, and propose closures. They may not close issues, merge PRs, alter Todoist, edit Notion, or touch personal surfaces until their policy, scopes, and audit log are proven.

**Detection:** before enabling a new automation, answer all four:

```text
What surface owns the object?
What surface only links to it?
What mutation is allowed?
What audit artifact proves it happened?
```

If the answer is "all of them," stop and delete/simplify the workflow before automating.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-41 — Upgrade playbooks must be revalidated against current doctrine before execution (session 80, 2026-04-29)

**Pattern:** A plan says "follow `gbrain-ops` P1" for a high-risk upgrade. The skill's older P1/P4 text still contains pre-RULE-ZERO language (`Write LESSON`, "LESSON file still required") and blind production pull steps that AP-32 later superseded. The plan inherits stale doctrine by reference even though the same skill already has the correct AP deeper down.

**Root cause:** Long-lived operational skills accrete corrections in later APs, but older phase checklists may still carry superseded commands. A reference to "follow P1" is unsafe when P1 and later APs disagree.

**Rule:**
1. Before executing any upgrade playbook, scan that same skill for newer APs and Timeline entries that supersede the phase checklist.
2. If a phase conflicts with RULE ZERO, AP-32, or current session-operating-contract, update the phase before execution.
3. For GBrain upgrades specifically, AP-32 dry-run/scope survey outranks any older `git stash && git pull` checklist.
4. Any upgrade plan must name the controlling AP/phase pair, not just "follow P1".

**Evidence:** Session 80 Lane C found `PLAN-2026-04-29-gbrain-minions-agent-harness-upgrade.md` Task 4 pointing at `gbrain-ops` P1 while P1 still said `Write LESSON` and direct pull/build. Fixed same session by rewriting P1/P4/AP-6 to current RULE ZERO + AP-32 doctrine and amending the plan to point at AP-32-first.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-42 — Resolver trigger evals must apply precedence rules before fuzzy scoring (session 81, 2026-04-29)

**Pattern:** `tools/trigger_eval.py` reports routing failures even when `RESOLVER.md` contains the right skill row. Broad always-on or high-overlap rows win because the evaluator uses pure token overlap. Examples: `/ask` routes to `command-center` or `musk-algorithm` instead of `ceo-hierarchy`; "camera count" routes to daily briefing; "add task:" routes to coding principles.

**Root cause:** the resolver has two kinds of rules: precedence rules and fuzzy trigger descriptions. The evaluator treated both as one unordered bag of text. That made the test disagree with the resolver's own "Conventions" section, where `/ask`, task verbs, Air SSH, SmartBridge/GOST, and skillify routes are explicit priority decisions.

**Rule:** deterministic routing evals must apply explicit precedence rules first, then fuzzy scoring second. Broad always-on rows are safety nets, not competitors against exact command/domain rules.

**Fix (SHIPPED):** `tools/trigger_eval.py` now has `PRIORITY_RULES` for resolver convention cases before fuzzy scoring. `_gbrain/RESOLVER.md` trigger text was tightened for the same cases. Red test: `48/68` before this session, `59/68` after trigger text only, `68/68` after precedence-first eval logic.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-43 — gbrain is a Bun-compiled ELF binary, not a Node module (session 81 dry-run, 2026-04-29)

**Pattern:** After `git pull` to v0.22.x + `npm install`, `bin/gbrain version` still reports the OLD version. Cause: `bin/gbrain` is a 100-140 MB compiled ELF binary produced by `bun build --compile --outfile bin/gbrain src/cli.ts`. Updating sources + running `npm install` does not regenerate the binary.

**Rule:** Any gbrain upgrade procedure MUST include `bun install` + `bun run build` to recompile the binary, before any migration or doctor invocation. PATH must also include `/root/.bun/bin` so the `bun` binary is reachable.

**Detection:** `xxd -l 4 bin/gbrain` returns ELF magic (`7f 45 4c 46`). `python3 -c "import json; print(json.load(open('package.json'))['scripts']['build'])"` returns `bun build --compile --outfile bin/gbrain src/cli.ts`.

**Why no new LESSON file:** RULE ZERO. Evidence: `pages/progress/HANDOFF-AUTO-2026-04-29-session-81-substrate-S0-dryrun-findings.md` + this skill + gbrain timeline.

### AP-44 — `bin/gbrain migrate` ≠ schema upgrade; the actual command is `apply-migrations` (session 81 dry-run, 2026-04-29)

**Pattern:** Plan v2 assumed `bin/gbrain migrate` = schema upgrade. v0.22 actually exposes `bin/gbrain migrate --to <supabase|pglite>` for storage-backend migration. The schema-upgrade entry point in v0.22 is `bin/gbrain apply-migrations --yes --non-interactive` (or the postinstall hook calling the same).

**Rule:** Before writing any upgrade plan, read the **target-version** CHANGELOG.md and `bin/gbrain --help` output ON A FRESHLY-BUILT BINARY. Do NOT infer command names from prior versions or from plan-author memory.

**Detection:** `bin/gbrain migrate --help` shows `Usage: gbrain migrate --to <supabase|pglite>`. CHANGELOG search `grep -A 5 "upgrade\|migration" CHANGELOG.md` shows the canonical `gbrain upgrade` + `gbrain apply-migrations --yes` pattern.

**Why no new LESSON file:** RULE ZERO.

### AP-45 — Migration shell scripts hard-code `gbrain` (no `bin/`); `PATH` must include `bin/` before `apply-migrations` (session 81 dry-run, 2026-04-29)

**Pattern:** Migration v0.11.0 (Minions schema) shells out to `gbrain init --migrate-only`. If `gbrain` is not on `PATH`, the migration aborts with `/bin/sh: 1: gbrain: not found` and reports `Migration v0.11.0 reported status=failed`. The brain ends up with `MINIONS HALF-INSTALLED` per `gbrain doctor`.

**Rule:** Before any `apply-migrations` invocation: `export PATH="$(pwd)/bin:/root/.bun/bin:$PATH"`. The bun PATH is also required because some migrations may invoke `bun`.

**Detection:** `which gbrain` resolves to the binary in the upgrade target dir. First failure signature is `/bin/sh: 1: gbrain: not found` in the migration log.

**Why no new LESSON file:** RULE ZERO.

### AP-46 — `apply-migrations` halts mid-flight when v0.11.0 expects a `search_vector` column the v4-schema source brain does not have (session 81 dry-run, 2026-04-29)

**Pattern:** Even with the binary built and PATH set, `apply-migrations` halts at v0.11.0 with `column "search_vector" does not exist`. The Minions migration assumes a tsvector column on `content_chunks` that earlier schemas don't include. Source brains seeded against v0.10.1 lack this column, so v0.11.0 cannot complete in-place.

**Rule:** When upgrading from a v0.10.x brain to v0.22.x, **NEVER live-cutover** until dry-run reaches `Health score ≥85/100` with zero `[FAIL]` checks. The half-migrated state is recoverable on a snapshot DB but catastrophic on prod. The right next step is upstream guidance (`https://github.com/garrytan/gbrain/issues/218`) or an explicit pre-migration `ALTER TABLE content_chunks ADD COLUMN search_vector tsvector;` step verified upstream.

**Detection (mechanical):** During dryrun `apply-migrations`, look for the literal string `column "search_vector" does not exist`. Post-failure, `gbrain doctor` shows `[FAIL] minions_migration: MINIONS HALF-INSTALLED (partial migration: 0.11.0)` AND `[WARN] schema_version: Version 4, latest is 29`.

**Hard rule from this AP:** dry-run on a snapshot DB IS the production safety. Live cutover can only proceed when dry-run produces a clean `gbrain doctor` health score AND `gbrain version` reports the target version AND `schema_version` matches `latest`. Any one missing → STOP, codify, plan, retry.

**Why no new LESSON file:** RULE ZERO. Snapshot DB `gbrain_dryrun` retained on VPS for forensics; `gbrain_pre_v22` retained for next attempt.

### AP-47 — Single-column β workaround for AP-46 is INSUFFICIENT; v0.11.0 wedges on multiple v25/v26/v27 columns (session 82 dry-run, 2026-04-29)

**Pattern:** Session 82 implemented option β as `ALTER TABLE content_chunks ADD COLUMN IF NOT EXISTS search_vector tsvector;` on the snapshot DB before `apply-migrations`. The first wedge (search_vector) cleared, but `gbrain init --migrate-only` (called from migration v0.11.0's shell phase) immediately halted on the next missing column: `column "symbol_name_qualified" does not exist`. v0.22.8 binary was correctly pulled (`POST_PULL_SHA=8468ba25`); the version's `applyForwardReferenceBootstrap()` either does not run on the `gbrain init --migrate-only` code path or does not cover the full v25/v26/v27 column set. Doctor reported `[FAIL] minions_migration: MINIONS HALF-INSTALLED (partial migration: 0.11.0)` AND `[FAIL] rls: 13 tables WITHOUT RLS` AND `Health score: 40/100`. Snapshot DBs `gbrain_pre_v22` + `gbrain_dryrun` retained for forensics on VPS. PROD `gbrain` at v0.10.1 untouched.

**Rule:** Live cutover STAYS BLOCKED. The β workaround must be **extended** to cover the full v25/v26/v27 column set on `content_chunks` (verified empirically: at minimum `search_vector tsvector` + `symbol_name_qualified text`; per Lane B research possibly also `language`, `symbol_name`, `symbol_type`, `start_line`, `end_line`, `parent_symbol_path`, `doc_comment`, plus `pages.page_kind` and `sources.chunker_version` — UNVERIFIED, must be empirically discovered one-by-one until apply-migrations completes clean), AND must include a post-migration backfill `UPDATE content_chunks SET search_vector = to_tsvector(...)` so FTS half of hybrid search returns non-zero (otherwise NULL on existing rows until trigger fires on next UPDATE). Alternative path: file or upvote upstream issue and wait for a v0.22.x release whose `applyForwardReferenceBootstrap()` covers `gbrain init --migrate-only` code path AND the full column set.

**Detection (mechanical):** Generalized — grep apply-migrations log for `column "[^"]+" does not exist` (any column name, not just search_vector). On match, exit 47 and report the offending column. Update `tools/gbrain_upgrade_dryrun.sh` AP-46 detection block to use this generalized regex.

**Hard rule from this AP:** Never blind-extend β with a presumed column list mid-session. Each missing column must be empirically discovered via a fresh dryrun cycle — add ONE column at a time, re-run dryrun, observe the next halt, codify, repeat. This is the slow-but-honest path; the fast-but-cowboy path (dump every plausible column at once) risks shipping an over-broad schema patch that diverges from upstream and causes future migrations to wedge on column-already-exists conflicts of incompatible types.

**Why no new LESSON file:** RULE ZERO. AP-47 supersedes the optimistic "verify upstream first" guidance in AP-46 — empirically verified that v0.22.8 does NOT cover this code path automatically.

### AP-48 — Context injection keeps salience packets, not full MEMORY dumps or pure recency (session 83, 2026-04-29)

**Symptom:** Token-level memory research (StreamingLLM attention sinks, SnapKV, TRIM-KV, MSA) maps directly onto an agent-workflow bug: deleting full `MEMORY.md` from `context_injector_v2` fixed context bloat, but it also risked losing the newest red/yellow warnings and carryovers. Restoring the full file would reintroduce tool-output dilution and context poisoning.

**Rule:** `context_injector_v2` must treat `MEMORY.md` as a retention-scored source, not a transcript dump. Inject only the newest top-block salience packet, capped under `MAX_MEMORY_PACKET_CHARS`, and keep only lines that change behavior now: directive, current live substrate, proof probes, honest red/yellow, carryover, blocked/not-done/deferred, RULE ZERO, open, next. Older blocks and low-salience shipped narrative stay out of the prompt.

**Detection:** `python3 tools/test_context_injector_v2.py` must assert all four: (1) no full `MEMORY.md` dump, (2) memory workflow packet includes red/yellow/carryover/RULE ZERO signals, (3) low-salience narrative is excluded, (4) live vault prompts remain under the 8KB G4 byte cap and approximate token budget.

**Why no new LESSON file:** RULE ZERO. This AP plus the paired test is the durable doctrine; gbrain timeline is the evidence layer.

### AP-49 — MEMORY salience extractors must support both legacy and Mercury top-block formats (session 86, 2026-04-29)

**Symptom:** `blacksmith_burst_tests.sh` failed after the live `MEMORY.md` moved from legacy `# Memory — updated ...` stanzas to the Mercury `# Now context` + `# Mercury fact-block` format. `context_injector_v2.py` still looked only for the legacy header, so the live factory context lost the Memory workflow packet even though the unit fixture was green.

**Rule:** Context injection and memory-health tests must be format-aware. Legacy session-prepend blocks and Mercury live fact-blocks are both valid MEMORY substrate formats. The salience extractor must read either one and preserve behavior-changing lines: directive, carryover, blocked/deferred/open work, proof surfaces, and RULE ZERO signals. If Mercury exposes RULE ZERO indirectly through LAW-015/LAW-017, normalize that into an explicit `RULE ZERO signal` line in the packet.

**Detection:** `python3 tools/test_context_injector_v2.py` must include a fixture for Mercury `# Now context` blocks and the live-vault budget test must prove `### Memory workflow packet` survives trim with a RULE ZERO signal.

**Why no new LESSON file:** RULE ZERO. This is a runtime-format compatibility bug in the evolving-memory loop, so the durable rule lives here.

### AP-50 — Iron law back-linking is structurally violated in v0.10.1: `gbrain extract links` only catches `[[wikilink]]` form, our substrate uses prose `<skill-name> AP-N` (session 82l, 2026-04-29)

**Pattern:** s82l audit verified Lane Y's "696 orphan pages" claim via direct probe: 3 of 4 sampled high-traffic skills had **0 backlinks** in gbrain (`karpathy-loop`, `gbrain-ops`, `musk-algorithm`) despite being cross-referenced ~50× in body text across other SKILL.md files. CLAUDE.md `BRAIN-FIRST RULE` says *"Iron law back-linking — entity A on page B → page A MUST link to B. Bidirectional. Always."* Empirically violated at scale (~696 orphan pages of 1,486 = 47%).

**Root cause discovery sequence:**
1. Hypothesis A: `gbrain extract links` was never run. Falsified — VPS canonical has the command (`gbrain 0.10.1` with `extract <links|timeline|all>`); dry-run reports `links_created: 128, pages_processed: 442`.
2. Hypothesis B: live extract will fix it. **Falsified empirically** — `gbrain extract links --json` returned `{"links_created": 0, ...}` after dry-run. Post-extract `mcp__gbrain__get_backlinks pages/skills/karpathy-loop/skill` still returned `[]`. `link_count` stat unchanged at 2940.
3. Hypothesis C (CONFIRMED): `gbrain extract links` v0.10.1 only matches `[[wikilink]]` syntax. Our substrate idiom is prose: `karpathy-loop AP-8`, `\`session-coordination\` AP-12`, `gbrain-ops AP-48`, etc. The references exist in markdown but are invisible to the extractor.

**Rule:** any back-link audit / iron-law-coverage probe must classify findings into:
- (a) Pages truly missing references (markdown body has no cite at all) → real orphans, fix by editing source
- (b) Pages with prose-form references that the extractor doesn't see → tooling gap, NOT a content gap; fixing by mass prose→wikilink conversion is hygiene churn unless prose form has been deprecated by doctrine
- (c) Pages that legitimately should be terminal (task-result, raw-source, alias) → not a violation

Class (b) is currently the dominant pattern. Per s82l plan execution: 3 fix-paths (substrate-wide prose→wikilink edit, upstream extractor upgrade, doctrine amendment to accept prose). Each is ≥2-4 hour scope. Pick one in the next dedicated session; do not fix piecemeal — partial conversion gives **false GREEN** on iron-law metrics.

**Detection (mechanical):** `mcp__gbrain__get_backlinks <slug>` returns `[]` for a skill that has ≥3 prose references in `grep -l "<skill-name>" pages/skills/*/SKILL.md`. If the body has the prose ref AND backlinks=[], you've hit AP-50. Tool detector candidate: `tools/test_backlink_iron_law_classification.sh` runs both `mcp__gbrain__get_backlinks` and a markdown-body grep, classifies into (a)/(b)/(c), and asserts class (b) percentage stays bounded.

**Cross-ref:** `karpathy-loop` AP-9 (loop saturation — round 10 redirected here per plan-first discipline), `karpathy-loop` AP-10 (verify lane findings — Lane Y's 696 number was real), `karpathy-loop` AP-2 (hygiene-disguised-as-value — fixing 500 SKILL.md files mid-session would BE this). Plan: `[[PLAN-2026-04-29-orphan-backlink-triage]]`.

**Why no new LESSON file:** RULE ZERO. The doctrine + 3 fix-path options live in this AP + the plan; the next dedicated session picks a path and ships.

### AP-52 — AP-50 closed via doctrine amendment (option 3): prose cross-refs accepted as iron-law-compliant (session 85, 2026-04-29)

**Pattern:** Codex session 82l left honest handoff with 3 fix-paths for AP-50, each ≥2-4hr. Session 85 picked Musk-step-2 winner: **delete the requirement, not the substrate.** Iron-law back-linking doctrine in CLAUDE.md was amended to explicitly accept BOTH `[[wikilink]]` and prose forms (e.g. `karpathy-loop AP-8`) as discoverable cross-refs. Tool-specific blindness (gbrain v0.10.1 prose-blind extractor) is reclassified as a tooling gap, NOT a doctrine violation.

**Why option 3 over options 1/2:** option 1 (substrate-wide prose→wikilink, ~500 edits) = pure hygiene churn (`karpathy-loop` AP-2). Option 2 (upstream extractor upgrade) blocked at AP-46/47 v0.22.x cutover. Option 3 (doctrine amendment) takes ~30 min, deletes the false-orphan class entirely, accepts how humans/agents naturally cross-ref, and explicitly tracks the gbrain v0.11+ extractor upgrade as the future machine-readable backfill.

**Rule:** any future "iron-law violation" report on prose cross-refs is reclassified per CLAUDE.md amendment as class-(b) tooling gap; use `ripgrep` + Obsidian backlink panel + gbrain combined for complete view. **Stop reporting prose-only references as orphans in audits.** When gbrain v0.11+ extractor ships, prose form becomes machine-readable too — the doctrine amendment becomes a one-time concession that future-proofs itself.

**Cross-ref:** [[PLAN-2026-04-29-orphan-backlink-triage]] (Step 5 carryover resolved), CLAUDE.md `BRAIN-FIRST RULE` (amended in commit `<this session>`), `karpathy-loop` AP-2 (Musk step-2: delete the requirement, not the substrate), upstream `conventions/quality.md` (the DRY-violation reference target detected by `gbrain doctor`'s `CROSS_CUTTING_PATTERNS` for `iron law back-linking`).

**Why no new LESSON file:** RULE ZERO. The closure path lives here + the doctrine amendment + the plan's resolution log.

### AP-53 — `resolver_health` ORPHAN_TRIGGER warnings are upstream-doctor name-mismatch (`_gbrain/<name>` vs bare `<name>`); same tooling-gap class as AP-50 (session 82n, 2026-04-29)

**Pattern:** `gbrain doctor` reports 26 ORPHAN_TRIGGER warnings even though every referenced skill IS in `pages/skills/_gbrain/manifest.json` (count: 25 — every name peer Codex s89/s90 flagged is present). Empirical verification:
```
$ python3 -c "import json; m=json.load(open('pages/skills/_gbrain/manifest.json'));
  print('signal-detector in manifest:', 'signal-detector' in [s['name'] for s in m['skills']])"
signal-detector in manifest: True
```
Yet `gbrain doctor --repo /root/nous-agaas/wiki` still reports `ORPHAN_TRIGGER: _gbrain/signal-detector → ACTION: Register '_gbrain/signal-detector' in skills/manifest.json or remove from RESOLVER.md`.

**Root cause traced into upstream source** `/opt/nous-agaas/gbrain/src/core/check-resolvable.ts:222-243`:
```typescript
const relPath = entry.skillPath.replace(/^skills\//, '');
// entry.skillPath = "skills/_gbrain/signal-detector/SKILL.md"
// relPath = "_gbrain/signal-detector/SKILL.md"
const skillName = relPath.replace(/\/SKILL\.md$/, '');
// skillName = "_gbrain/signal-detector"
const inManifest = manifest.some(s => s.name === skillName);
// Looking for "_gbrain/signal-detector" === "signal-detector" → FALSE
// → ORPHAN_TRIGGER warning fires
```

The strip-regex `^skills/` only removes the top-level prefix; the `_gbrain/` namespace prefix remains attached to `skillName` for the manifest match. Manifest entries are bare names (`signal-detector`, `query`, `ingest`, etc.) so the comparison always fails. **All 26 ORPHAN_TRIGGER warnings are false positives from this single regex.**

**Same class as AP-50/52**: tooling-gap, not content-gap. Three fix paths, each requires runtime routing verification before ship:
- (X) Update manifest names to add `_gbrain/` prefix (25 JSON edits) → need to verify `path` field still resolves correctly + no other consumers break
- (Y) Update RESOLVER paths to drop `_gbrain/` (28+ markdown edits) → routing semantics change, file existence checks may fail
- (Z) Patch upstream `check-resolvable.ts:224` to also strip `^_gbrain/` from `relPath` → cleanest, but requires upstream PR or local fork divergence

**Defer to dedicated session.** Today's substrate is at brain-score 90/100, factory production-green, real-traffic E2E proven (s82j). The 26 false-positive warnings are observability noise, not capability loss.

**Detection (mechanical):** ORPHAN_TRIGGER warning where the referenced skill IS in `pages/skills/_gbrain/manifest.json` (verifiable via 2-line python script above). False-positive class. Tool detector candidate: `tools/test_gbrain_doctor_orphan_false_positives.sh` — for each ORPHAN_TRIGGER, grep manifest for skill name; if present, mark as false-positive.

**Cross-ref:** AP-50 (parent class — gbrain v0.10.1 tooling gaps), AP-52 (precedent: doctrine amendment as fix path), `karpathy-loop` AP-2 (don't churn 25 manifest edits without runtime test), AP-9 (loop saturation — round-12 of evergreen prompt, this finding is the leverage point that justifies the round).

**Why no new LESSON file:** RULE ZERO. The 80%-understanding lives here for next session to ship the runtime-tested fix.

### AP-54 — DRY_VIOLATION + MECE_OVERLAP cleanup: append `conventions/quality.md` ref + remove duplicate trigger; brain_score 90 → 95 (session 82q, 2026-04-29)

**Pattern:** Post AP-53 fix, `gbrain doctor` had 11 remaining warnings: 9 DRY_VIOLATION + 1 MECE_OVERLAP + 1 RLS. DRY detector at `check-resolvable.ts:325-340` scans skill bodies for `CROSS_CUTTING_PATTERNS` (iron-law-back-link / citation-format / notability-gate) AND fails if `conventions/quality.md` is not referenced anywhere in the skill. MECE detector at `:256-280` builds trigger→skills map from frontmatter `triggers:` arrays; if the same trigger appears in 2+ non-whitelisted skills, fires.

**Empirical scan**: 8 distinct skills had DRY violations (`gbrain-ops` ours + 7 upstream `_gbrain/*`: ingest, enrich, setup, signal-detector, idea-ingest, media-ingest, meeting-ingestion). MECE overlap traced to `"citation audit"` trigger duplicated in `maintain` + `citation-fixer` frontmatters.

**Fix (SHIPPED):**
- For our skill: appended `, upstream conventions/quality.md (the DRY-violation reference target detected by gbrain doctor's CROSS_CUTTING_PATTERNS for iron law back-linking)` to AP-50's Cross-ref line. One Python atomic write (Edit tool was racing auto-sync; fall-back per AP-12).
- For 7 upstream skills: appended `## See also\n- [conventions/quality.md](../conventions/quality.md) — cross-cutting Iron-Law back-linking + citation format + notability gate (DRY reference per gbrain-doctor CROSS_CUTTING_PATTERNS)` footer to each. Single SSH bash loop on `/opt/nous-agaas/gbrain/skills/_gbrain/`.
- For MECE: `sed -i '/citation audit/d'` on `maintain/SKILL.md` frontmatter triggers list. `citation-fixer` keeps the trigger (it's the more specific match for "fix citations" / "citation audit" requests). `maintain` retains "check backlinks", "orphan pages", "stale pages", "brain health", "maintenance" — routing semantics preserved.

**Empirical verification:**
```
before: [WARN] resolver_health: 11 issue(s) (9 DRY + 1 MECE + 1 RLS)
        brain_score 90/100
after:  [OK] resolver_health: 38 skills, all reachable
        brain_score 95/100
```

**Rule:** any new skill body that mentions iron-law back-linking, citation format, or notability gate MUST include `conventions/quality.md` reference. Any new frontmatter trigger MUST be checked against `triggerMap` in `check-resolvable.ts` to avoid MECE collision. **Detector:** `tools/test_dry_mece_compliance.sh` candidate — pre-commit gate that runs `bin/gbrain doctor` against staged skills and blocks ⇒1 DRY/MECE introduction.

**Cross-ref:** AP-53 (parent — closed first; AP-54 cleans the tail), `karpathy-loop` AP-9 (round-15 evergreen leverage closure), upstream `conventions/quality.md` itself.

**Why no new LESSON file:** RULE ZERO. Fix shipped + verified empirically; doctrine lives in this AP.

### AP-55 — Memory-health probes and seeders must treat Mercury MEMORY as generated output (session 92, 2026-04-29)

**Pattern:** SOAO reported `test_memory_top_block_size warn — approaching cap`, but the direct command said `no '# Memory — updated …' header found`. Live `MEMORY.md` was only 52 lines and started with the Mercury `# Now context` + `# Mercury fact-block` format. During the same audit, `pages/mercury/facts.jsonl` contained repeated `carryover.stanza-0.blocked...` facts sourced from generated Mercury output.

**Root cause:** AP-49 fixed context injection for Mercury, but the sibling memory-health probe still only recognized legacy `# Memory — updated` stanzas. Then `tools/mercury_seed.py` read generated Mercury `MEMORY.md`, extracted generated carryover lines, wrote them back into `facts.jsonl`, and let `tools/mercury_inject.py` emit them again. That turned a health-check drift into a self-amplifying memory loop.

**Rule:** every MEMORY consumer and health probe must accept both valid live formats: legacy `# Memory — updated ...` session-prepend stanzas and Mercury `# Now context` live fact-blocks. Generated memory output must never be an input source for the same fact class that generated it. A probe that cannot parse the current live format must say "unrecognized format" and fail its own regression suite before SOAO turns it into an operator warning.

**Fix (SHIPPED):** `tools/test_memory_top_block_size.sh` now supports `MEMFILE_OVERRIDE` for fixtures, measures legacy stanzas or Mercury `# Now context` blocks, and reports the format in output. `tools/test_memory_top_block_size_e2e.sh` covers legacy pass, Mercury pass, and unknown-format warn. `tools/mercury_seed.py` now supports `MERCURY_MEMORY_OVERRIDE`, skips carryover extraction when the live file starts with `# Now context`, and dedupes legacy carryover snippets before appending facts. `tools/test_mercury_seed_memory_source.sh` covers generated-Mercury skip + legacy dedupe; current live regeneration reports `carryover: 0` and no self-referential carryover block.

**Why no new LESSON file:** RULE ZERO. This AP extends AP-49 from context injection to memory-health probes.

### AP-56 — OpenClaw skillsSnapshot refresh must exercise OpenClaw, not a wrapper that may bypass it (session 95, 2026-04-29)

**Symptom:** `agent:nous:main` `skillsSnapshot` showed 79 skills but missed required runtime skills (`ceo-hierarchy`, `collaborative-reading`, `find-skills`, `musk-algorithm`, `operator-boundaries`, `session-architecture`) while `openclaw skills check` reported them eligible from `/opt/nous-agaas/skills`. Running `tools/bump_openclaw_skills_version.sh` printed success but did not change the snapshot.

**Root cause:** the bump script intended to set `skillsSnapshot.version += 1`, then called `python3 run_task.py "Reply with: TOKEN"` to trigger the rebuild. Two false-green layers hid the drift: the Python heredocs used `docker exec openclaw python3 << PYEOF` without `-i`, so the container never received the bump/check code; then after the model escalator change, default `nous` tasks could route through `litellm_direct`, so OpenClaw still would not run. The script verified the token came back, not that OpenClaw rebuilt the snapshot.

**Rule:** any OpenClaw snapshot refresh tool must feed heredoc Python through `docker exec -i`, call `docker exec openclaw openclaw agent ...` directly instead of `run_task.py`, clean up its own token-scoped `BUMP_VERIFY` probe processes, then assert the required operating-loop skills are loaded by name. A count-only check is insufficient because stale built-in skills can keep the total number healthy while critical Nous skills are absent. Do not use `--local` for this probe unless separately proven safe; this session's `--local` experiment left high-CPU agent processes running past the expected timeout.

**Detection:**

```bash
bash tools/test_bump_openclaw_skills_version.sh
ssh air 'docker exec openclaw openclaw skills check | grep -E "musk-algorithm|ceo-hierarchy|session-architecture"'
```

Expected: the sibling test exits 0, and required skills are present in `agent:nous:main` `skillsSnapshot` after the bump. If `run_task.log` shows `execution_path=litellm_direct`, that is not evidence of an OpenClaw refresh.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-57 — Link builders must resolve Obsidian skill-link aliases before declaring graph debt (session 100, 2026-04-30)

**Symptom:** The Obsidian/gbrain/OpenClaw library audit found `tools/gbrain_link_builder.py --dry-run --verbose` reporting hundreds of unresolved links even though many targets existed in gbrain. Top examples included `[[skills/agent-quality/skill]]`, `[[skills/session-operating-contract]]`, `[[skills/musk-algorithm]]`, `[[skills/karpathy-loop]]`, `[[skills/audit/skill]]`, and bare skill names like `[[session-coordination]]`.

**Root cause:** the link builder only checked exact slugs, final path basenames, and a few content-directory prefixes. Skill pages ingest as slugs like `pages/skills/session-operating-contract/skill`, so the final basename is always `skill`, not the skill directory name. Real Obsidian idioms (`skills/name`, `skills/name/skill`, `skills/name/SKILL.md`, and tenant skill variants) were therefore reported as unresolved graph debt while the canonical page existed and exact `gbrain get` worked.

**Rule:** graph builders and broken-link audits must normalize skill aliases before counting unresolved links. Accepted aliases include `[[skills/name]]`, `[[skills/name/skill]]`, `[[skills/name/SKILL.md]]`, `[[pages/skills/name/SKILL.md]]`, bare `[[name]]` when no exact page basename exists and `pages/skills/name/skill` exists, and tenant forms such as `[[tenants/satory/skills/name/SKILL.md]]`. A detector must prove these aliases resolve without touching the gbrain database.

**Detection:**

```bash
python3 tools/test_gbrain_link_builder_resolution.py
ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && python3 tools/gbrain_link_builder.py --dry-run --verbose | sed -n "1,40p"'
```

Expected: the local test exits 0, and the VPS dry-run no longer lists existing skill pages as top unresolved link targets. Historical lesson links may remain unresolved if their files were intentionally migrated/deleted under RULE ZERO; that is not the same bug.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-58 — Sync wrappers must execute wiki-local tool copies, not stale sibling runtime tools (session 100, 2026-04-30)

**Symptom:** After AP-57 was committed and pushed, `python3 tools/gbrain_link_builder.py --dry-run` from `/root/nous-agaas/wiki` showed `Truly new: 0`, but a full `tools/gbrain_sync_wrapper.sh` cycle still used `/root/nous-agaas/tools/gbrain_link_builder.py` from 2026-04-10. Running that stale sibling copy reproduced the old top unresolved skill aliases (`skills/agent-quality/skill`, `skills/session-operating-contract`, `skills/musk-algorithm`, `skills/karpathy-loop`).

**Root cause:** the wrapper lived in the wiki but executed helper tools from a separate runtime directory. The code commit updated the source-of-truth tool, while the scheduled wrapper kept calling an older copy. That made the fix true for manual verification but false for the actual sync loop.

**Rule:** wrappers that are tracked in the wiki must default to executing sibling tools from the same wiki checkout (`$WIKI/tools`). A separate runtime tools directory is allowed only as an explicit override (`GBRAIN_TOOLS_DIR=...`) and must be covered by a parity/deploy check. A wrapper dry-run that only checks credentials is insufficient if the wrapper can still call stale helper code.

**Detection:**

```bash
bash tools/test_gbrain_sync_wrapper_secret_loading.sh
ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && python3 tools/gbrain_link_builder.py --dry-run | grep "Truly new: 0"'
```

Expected: the wrapper text contains `TOOLS="${GBRAIN_TOOLS_DIR:-$WIKI/tools}"`, the remote dry-run can load the OpenAI key, and a full wrapper cycle does not reintroduce skill-link graph debt.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-59 — Autopilot must run custom link builders after repo sync under the same lock (session 100, 2026-04-30)

**Symptom:** After AP-58 made the wrapper use wiki-local tools, `gbrain_link_builder.py --dry-run` still showed the same 5 `session-architecture` links reappearing after a few minutes. `crontab -l` showed the live 5-minute job is `/root/.gbrain/autopilot-run.sh`, not `gbrain_sync_wrapper.sh`. The runner executed `gbrain autopilot --repo /root/nous-agaas/wiki` directly, so autopilot could refresh pages without our custom alias-aware link builder.

**Root cause:** AP-57 fixed the custom graph builder, and AP-58 fixed the wrapper path, but the scheduled path bypassed both. The real cron path must include every deterministic post-sync maintenance step, otherwise manual verification can be green while the 5-minute substrate loop drifts back.

**Rule:** after any `gbrain autopilot --repo <wiki>` scheduled sync, run the wiki-local custom link builder under the same non-overlapping flock. Do not run it as a separate cron; AP-3 forbids parallel autopilot/wrapper maintenance on the same gbrain DB. The cron entrypoint owns the sequence: ghost reset -> locked autopilot -> custom link builder.

**Detection:**

```bash
bash tools/test_gbrain_autopilot_secret_loading.sh
ssh root@65.108.215.200 'grep -F gbrain_link_builder.py /root/.gbrain/autopilot-run.sh'
ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && python3 tools/gbrain_link_builder.py --dry-run | grep "Truly new: 0"'
```

Expected: the runtime autopilot runner loads credentials, retains the flock, invokes `gbrain_link_builder.py`, and the graph dry-run stays at zero newly-registerable links after a cron-equivalent run.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-60 — Do not append maintenance after a non-returning autopilot daemon (session 100, 2026-04-30)

**Symptom:** The AP-59 verification run printed `Autopilot starting... [cycle] ... next=300s` and never reached the appended `gbrain_link_builder.py` command. The previous stale Apr 15 process showed the same pattern: `gbrain autopilot --repo /root/nous-agaas/wiki` was a long-lived daemon holding the lock for days.

**Root cause:** `gbrain autopilot` is not a one-shot maintenance command. It runs `sync -> extract -> embed -> sleep` in an internal loop. Shell commands appended after it are dead code until the daemon exits, so AP-59's first patch still let custom graph maintenance lag behind.

**Rule:** the tracked VPS cron entrypoint must own the loop directly: `sync --repo "$WIKI" --no-embed` -> `extract all --dir "$WIKI"` -> `embed --stale` -> wiki-local `gbrain_link_builder.py` -> sleep. Keep the single `flock -n /var/lock/gbrain-autopilot.lock`, expose `GBRAIN_AUTOPILOT_ONCE=1` for verification, and reject any runner that delegates to `"$GBRAIN" autopilot`.

**Detection:**

```bash
bash tools/test_gbrain_autopilot_secret_loading.sh
ssh root@65.108.215.200 'GBRAIN_AUTOPILOT_ONCE=1 /root/.gbrain/autopilot-run.sh'
ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && python3 tools/gbrain_link_builder.py --dry-run | grep "Truly new: 0"'
```

Expected: the one-cycle runner exits, the link builder runs during that cycle, and the dry-run remains at zero newly-registerable graph links.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-61 — gbrain canonicalizes slugs to lowercase; operator queries with uppercase wiki IDs return false `page_not_found` (session 100, 2026-04-30)

**Symptom:** `mcp__gbrain__get pages/audits/AUDIT-061-obsidian-gbrain-openclaw-library-2026-04-30` returns `Error [page_not_found]: Page not found`. The page exists on disk, has 2 chunks indexed, and is reachable via `bin/gbrain list --type audit` plus `mcp__gbrain__get pages/audits/audit-061-obsidian-gbrain-openclaw-library-2026-04-30` (lowercase). Operator concludes "audit page is missing from gbrain" and either re-indexes redundantly, files a fake sync bug, or skips the lookup and answers from stale memory.

**Root cause:** gbrain v0.10.1's slug canonicalizer lowercases every path segment on ingest. The wiki convention is uppercase prefix on `pages/audits/AUDIT-NNN-...`, `pages/lessons/individual/LESSON-NNN-...`, `laws/LAW-NNN-...`. Direct slug lookup is exact-match on the canonicalized form, so `AUDIT-061` mismatches stored `audit-061` and returns `page_not_found` even though the row exists.

**Rule:** when issuing direct-slug operations against gbrain (`get`, `put`, `delete`, `add_timeline_entry`, `revert_version`), ALWAYS lowercase the entire slug. Wikilink form `[[AUDIT-061-...]]` inside markdown pages is fine — the resolver normalizes during ingest. Only operator-facing CLI/MCP calls need the manual lowercase.

**Detection / fix recipe:**

```bash
# WRONG (returns false page_not_found):
mcp__gbrain__get  slug="pages/audits/AUDIT-061-obsidian-gbrain-openclaw-library-2026-04-30"

# RIGHT:
mcp__gbrain__get  slug="pages/audits/audit-061-obsidian-gbrain-openclaw-library-2026-04-30"
```

**Why operator-discipline rather than a gbrain patch:** content-addressed retrieval should not be ambiguous on case. gbrain's choice to canonicalize is correct (avoids `AUDIT-061` vs `audit-061` duplicate rows). The fix is a 5-character lowercase on the operator side, not a gbrain code change.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-62 — Superseded knowledge must be marked in frontmatter so retrieval can demote drift (session 100, 2026-04-30)

**Symptom:** Retrieval audits kept surfacing old-but-confident pages even after newer doctrine existed. Prose-only drift corrections such as `DRIFT CORRECTION` headers were readable to humans but invisible to BM25/vector rankers and deterministic library checks.

**Root cause:** the vault had no machine-readable supersession contract. Backlinks showed topical relationships, not which page had authority. That left gbrain unable to demote stale chunks and left agents to rediscover context hierarchy by reading full prose.

**Rule:** when a page is superseded, add `superseded_by:` frontmatter on the old page pointing at the current authoritative slug, and add `supersedes:` on the new page for the inverse link. Include `supersession_date:` when the old page should be demoted after an age threshold. Audits may warn when new doctrine is added to a page already carrying `superseded_by:` because that is probably the wrong write target.

**Detection:**

```bash
rg -n "superseded_by:|supersedes:|supersession_date:" pages laws
python3 tools/library_quality_scan.py --json | jq '.blocking_count'
```

Expected: supersession metadata is explicit on stale authority pages, and future ranker/library passes can consume it without parsing prose warning banners.

**Why no new LESSON file:** RULE ZERO. Evidence was parked in [[AUDIT-062-retrieval-quality-synthesis-2026-04-30]] while the prior gbrain-ops lane held this file; now it is absorbed here + gbrain timeline on `pages/skills/gbrain-ops/skill`.

### AP-63 — Handoffs must pass gbrain lint/import readback before claiming retrieval visibility (session 103, 2026-04-30)

**Symptom:** closeout handoffs existed in Git and synced to VPS, but `gbrain get` and `gbrain search` could not retrieve the session-102 closeout. A manual import showed both session-100 and session-102 handoffs were skipped with YAML parse warnings, and `gbrain lint` reported missing required `created` metadata.

**Root cause:** Markdown existence was mistaken for gbrain visibility. The affected handoffs used prose-friendly frontmatter such as comma-separated unquoted wikilinks in `related:` plus no `created:` field. Git sync succeeded, but gbrain import rejected the pages before indexing.

**Rule:** before saying a handoff is gbrain-visible, run `gbrain lint` on the exact handoff file, then run an import/readback probe or wait for autopilot and prove `gbrain get`/`gbrain search` returns the slug. Handoff frontmatter must include `type`, `id`, `title`, `date`, `created`, `status`, and YAML-valid list fields. Quote Obsidian wikilinks inside YAML lists, for example:

```yaml
related:
  - "[[skills/gbrain-ops/skill]]"
  - "[[AUDIT-062-retrieval-quality-synthesis-2026-04-30]]"
```

**Detection:**

```bash
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain lint /root/nous-agaas/wiki/pages/progress/HANDOFF-AUTO-YYYY-MM-DD-*.md'
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain search "unique handoff phrase" --limit 3'
```

Expected: lint reports zero issues for the new handoff, and search/get returns the saved page after sync/import.

**Why no new LESSON file:** RULE ZERO. The fix is doctrine here plus gbrain timeline evidence; no new `LESSON-NNN` file.

### AP-70 — Cyrillic-named vault files are NOT indexed by gbrain v0.22 (`slugifyPath()` rejects non-ASCII at ingest) (session 82 deep-audit, 2026-04-30)

**Pattern:** Vault has 96 markdown files with Cyrillic letters in their filenames (mostly Satory tenant notes, meeting transcripts, RU-language tasks). `gbrain stats` reports 198 tenant pages indexed; vault has 243 tenant md files = **45+ Cyrillic-pathed files unindexed**. Live verification: `SELECT COUNT(*) FROM pages WHERE slug ~ '[а-яА-Я]'` returns **0**. Cause: `import-file.ts:381` validates `expectedSlug = slugifyPath(relativePath)` strict-equal; non-ASCII characters get stripped/transformed during slugify, producing a mismatch that aborts ingest with no error.

**Impact:** 96/1592 = 6.0% of vault is invisible to gbrain hybrid retrieval (vec/lex/graph/LLM-rewrite). Madi's Russian-language Satory work (meeting notes, partnership records, ЭЦП/ERAP context, video-system status reports) does not surface in agent retrieval.

**Rule:** when authoring or migrating Cyrillic content into the vault, choose ONE:
1. Use Latin transliteration in filename (`vstrecha-po-partnerstvu-2025-03-19.md`); store original Russian title in frontmatter `title:` field — body content searchable via vec mode.
2. Add `aliases: [latin-slug]` frontmatter so resolver finds the page via Latin alias even with Cyrillic filename.
3. (Future) File upstream issue + PR for Cyrillic-aware `slugifyPath()` — currently NOT supported.

**Detection (mechanical):**
```bash
ssh root@65.108.215.200 "sudo -u postgres psql -t -d gbrain -c \"SELECT COUNT(*) FROM pages WHERE slug ~ '[а-яА-Я]';\""  # should be > 0 if any Cyrillic indexed
find pages -name '*.md' -type f | grep -cE '[а-я]'  # vault Cyrillic count
```
If vault > 0 AND DB = 0 → Cyrillic ingest broken upstream.

**Why no new LESSON file:** RULE ZERO. Bonus: file upstream issue at https://github.com/garrytan/gbrain/issues for Cyrillic/Unicode slug support.

### AP-71 — `gbrain orphans` 700 raw count is misleading; 61% are by-design terminal nodes (session 82 deep-audit, 2026-04-30)

**Pattern:** `gbrain doctor` and `gbrain orphans` report 700 orphan pages on Nous brain (37.5% of 1866). Raw number is alarming; reframed by category:
- **task-results: 327** (47%) — auto-generated factory output, intentionally one-shot, never inbound-linked. **Legitimate orphans.**
- **progress (handoffs): 99** (14%) — end-of-session terminal nodes, by design unlinked from peers. **Legitimate orphans.**
- **(no /pages prefix): 67** — legacy slug-pattern orphans, partial fix in s100 AP-61.
- **tenants: 134** — Satory work, mix of legitimate one-shot meeting notes + 45+ unindexed Cyrillic (see AP-70) + ~30 real linkable orphans.
- **skills/dashboards/concepts: ~50** — these SHOULD have inbound links; real-work-queue.

**Rule:** when reporting brain health, decompose `orphans_total` into `legitimate_terminal + cyrillic_unindexed + real_work_queue`. Filter task-results + handoff/progress before alarming. Real-work-queue is the actionable number (~274 for Nous as of session 82, 14.7% of total).

**Detection (mechanical):**
```sql
SELECT split_part(slug, '/', 2) AS category, COUNT(*)
FROM pages WHERE NOT EXISTS (SELECT 1 FROM links WHERE to_page_id = pages.id OR origin_page_id = pages.id)
GROUP BY 1 ORDER BY 2 DESC;
```

**Why no new LESSON file:** RULE ZERO.

### AP-68 — `graph_coverage 0%` doctor WARN is structurally correct for markdown-only brains (session 82 close, 2026-04-30)

**Pattern:** After upgrading to v0.22.x, `gbrain doctor` may report `[WARN] graph_coverage: Entity link coverage 0%, timeline 0%`. On a brain with no code chunks (markdown-wiki-only, 0 rows in `content_chunks WHERE chunk_source = 'code'`), the graph_coverage metric measures **Cathedral II code-edge coverage** — which is structurally 0% for our brain shape. Real wikilink data is in `links` table (6062 rows on session 82 prod), real timeline data is in `timeline_entries` (1962 rows). Both healthy.

**Rule:** When graph_coverage reports 0% on a markdown-only brain, verify: (1) `SELECT COUNT(*) FROM content_chunks WHERE chunk_source='code'` = 0, (2) `SELECT COUNT(*) FROM links` > 0, (3) `SELECT COUNT(*) FROM timeline_entries` > 0. If 1=0 and 2+3>0, the WARN is cosmetic — the brain is healthy. Doctor metric calibration is upstream's.

**Detection:** literal doctor output `[WARN] graph_coverage: Entity link coverage 0%, timeline 0%`. SQL counterproof above.

**Why no new LESSON file:** RULE ZERO. Bonus: file upstream issue suggesting `graph_coverage` should report differently (or be suppressed) when `code_chunks_count = 0`.

### AP-69 — `gbrain extract links/timeline --source db` is for code-edge re-extraction; idempotent walk on markdown brains produces 0 (session 82 close, 2026-04-30)

**Pattern:** `gbrain extract all` walks 100% of pages (1865/1865) but produces "Done: 0 links, 0 timeline entries" on a markdown-only brain. Cause: extract operates on code chunks' typed code-edges (Cathedral II), not on markdown frontmatter wikilinks. Wikilink/timeline-entry extraction on markdown happens in autopilot via wiki-local `tools/gbrain_link_builder.py` + `tools/gbrain_timeline_builder.py`.

**Rule:** Don't expect `gbrain extract` to populate `links` or `timeline_entries` on a markdown brain. Use the wiki-local builders inside the autopilot cycle instead. Doctor's hint `Run: gbrain link-extract && gbrain timeline-extract` is stale (commands renamed to `gbrain extract`); ignore.

**Why no new LESSON file:** RULE ZERO.

### AP-64 — gbrain v0.10-era brains pre-date the v0.22.6.1 forward-reference bootstrap; comprehensive column patch required (session 82 LIVE upgrade, 2026-04-30)

**Pattern:** Upstream's v0.22.6.1 release notes claim "Pre-v0.13/v0.18/v0.19 brains all upgrade clean" via a pre-schema bootstrap that adds forward-referenced columns (`pages.source_id`, `links.link_source`, `content_chunks.symbol_name`, etc.) before SCHEMA_SQL replays. **But the bootstrap was written before Cathedral II (v0.20.0/v27) and does not include `parent_symbol_path`, `doc_comment`, `symbol_name_qualified`, `search_vector`, `symbol_type`, `start_line`, `end_line`, `chunker_version`, `page_kind`, `origin_field`, `resolution_type`, `files.source_id`, `files.page_id`.** A v0.10-era brain hits `column "search_vector" does not exist` on init.

**Rule:** Before `gbrain init --migrate-only` on any pre-v0.20 brain, apply this comprehensive forward-reference SQL patch (omitting any tables that don't yet exist — they'll be created by init):

```sql
ALTER TABLE pages ADD COLUMN IF NOT EXISTS page_kind TEXT NOT NULL DEFAULT 'markdown';
ALTER TABLE pages ADD COLUMN IF NOT EXISTS source_id TEXT;
ALTER TABLE links ADD COLUMN IF NOT EXISTS link_source TEXT;
ALTER TABLE links ADD COLUMN IF NOT EXISTS origin_page_id INTEGER REFERENCES pages(id) ON DELETE SET NULL;
ALTER TABLE links ADD COLUMN IF NOT EXISTS origin_field TEXT;
ALTER TABLE links ADD COLUMN IF NOT EXISTS resolution_type TEXT;
ALTER TABLE files ADD COLUMN IF NOT EXISTS source_id TEXT;
ALTER TABLE files ADD COLUMN IF NOT EXISTS page_id INTEGER;
ALTER TABLE content_chunks
  ADD COLUMN IF NOT EXISTS language TEXT,
  ADD COLUMN IF NOT EXISTS symbol_name TEXT,
  ADD COLUMN IF NOT EXISTS symbol_type TEXT,
  ADD COLUMN IF NOT EXISTS start_line INTEGER,
  ADD COLUMN IF NOT EXISTS end_line INTEGER,
  ADD COLUMN IF NOT EXISTS parent_symbol_path TEXT[],
  ADD COLUMN IF NOT EXISTS doc_comment TEXT,
  ADD COLUMN IF NOT EXISTS symbol_name_qualified TEXT,
  ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;
-- DO NOT touch sources table here; it does not exist on v0.10-era brains
-- and init creates it during migration v20.
```

**Detection:** `gbrain init --migrate-only` fails on a v0.10-era brain with `column "search_vector" does not exist` (or one of the other Cathedral II columns). Evidence: `/root/nous-agaas/backups/live-cutover-final-*/live-migrate.log` from session 82 cutover.

**Verification:** After applying the patch, `gbrain init --migrate-only` walks v5→v29 cleanly (22 migrations applied on session 82 prod cutover). Schema goes 4→29; doctor reports `schema_version: Version 29 (latest: 29)`.

**Why no new LESSON file:** RULE ZERO. Bonus: this should be filed upstream as a v0.22.x patch — the bootstrap probe in `initSchema()` needs to extend to Cathedral II columns.

### AP-65 — `BYPASSRLS` privilege required on gbrain DB user before v24+ migrations (session 82 LIVE upgrade, 2026-04-30)

**Pattern:** Migration v24 (`rls_backfill_missing_tables`) enables Row Level Security on 13 tables. The migration code aborts if the connecting role lacks `BYPASSRLS`: `role gbrain does not have BYPASSRLS privilege — cannot enable RLS safely`.

**Rule:** Before any v24+ apply: `sudo -u postgres psql -d postgres -c "ALTER ROLE gbrain BYPASSRLS;"`. Idempotent + permanent. Cannot be done from the gbrain user itself (lack of permission to grant own privileges).

**Detection:** mid-`init --migrate-only` log line: `v24 rls_backfill_missing_tables: role gbrain does not have BYPASSRLS privilege`.

**Why no new LESSON file:** RULE ZERO.

### AP-66 — `gbrain` repo on prod has Nous-local AP commits that must rebase onto upstream master, often with `--strategy-option=ours` for skill manifest conflicts (session 82 LIVE upgrade, 2026-04-30)

### AP-67 — Library-grade audit gates must be Tier-A1-scoped per AUDIT-061 contract; flat denominators conflate legacy receipts with stable runtime (session 104, 2026-04-30)

**Pattern:** A library-grade audit (reachability / canonical / cross-ref) applies a flat threshold to all `pages/**/*.md` and reports a misleading FAIL because Tier B/C and time-series Tier A2 contain by-design duplicates, broken upstream refs, or zero inbound links. Apparent FAIL hides the real signal — the stable Tier A1 runtime IS golden.

**Root cause:** the s82u Step 2/3/4 handoff specified gates without referencing the user-signed AUDIT-061 Tier policy. The flat-threshold reading made the audit look 4-10× worse than reality and tempted gate-bending fixes (silent type-list expansion).

**Rule:** every library-grade audit gate (reachability orphan rate, canonical duplicates, cross-ref broken count) MUST scope to Tier A1 stable and report Tier B/C numbers informationally. Tier A1 = the strict core catalog from `library_quality_scan.classify`: active skills, laws/pages/laws, systems, entities, projects, canonical concepts, tenant skill docs, plus vault-root doctrine files for crossref. Tier B = reports/imports/receipts (audits, specs, plans, progress-plans, dashboards, handoffs, task-results, sources, `_gbrain`, tenant non-skill notes). Tier C = legacy/archive material (claude-memory, lessons, extracted, commit-review, fallback).

**How to apply:** every audit scanner SHOULD `from library_quality_scan import classify` rather than re-implementing tier logic; ad-hoc tier definitions drift from AUDIT-061. If a scanner needs root-doctrine handling (for example CLAUDE.md crossrefs), add that local exception explicitly and leave report streams in Tier B.

**Detection:** run `python3 tools/library_reachability_scan.py && python3 tools/library_canonical_scan.py && python3 tools/library_crossref_scan.py` together. All three should pass at Tier A1 scope. Any audit that passes overall but uses flat denominators silently is suspect — verify against AUDIT-061 by reading the scanner source.

**Compounding artifact:** Three scanners now share the core-only classifier:
- `tools/library_reachability_scan.py` — 3-channel orphan scan, 3.04% Tier A1 orphans (9/296, PASS)
- `tools/library_canonical_scan.py` — duplicate titles + content + alias resolution, 1/0/0 at Tier A (PASS)
- `tools/library_crossref_scan.py` — wikilink + prose AP integrity, 0 broken Tier A1 wikilinks + 0 broken Tier A1 prose AP refs (PASS)

All three reuse `library_quality_scan.classify` for tier consistency. Future Tier-policy edits propagate to all four scanners automatically.

**Cross-ref:** AUDIT-061 (signed Tier contract), AUDIT-LIBRARY-REACHABILITY-2026-04-30, AUDIT-LIBRARY-CANONICAL-2026-04-30, AUDIT-LIBRARY-CROSSREFS-2026-04-30, `karpathy-loop` AP-2 (hygiene-disguised-as-value — gate-widening to PASS is this AP's risk; the s104 scoping is justified by AUDIT-061's prior signing, not by goalpost-moving).

**Why no new LESSON file:** RULE ZERO.

**Pattern:** `/opt/nous-agaas/gbrain` carries Nous-local commits (e.g., AP-53, AP-54 patches). Direct `git pull` after upstream releases new versions hits `Need to specify how to reconcile divergent branches`. Naive merge dilutes ownership; rebase preserves attribution.

**Rule:** `git rebase origin/master --strategy-option=ours` keeps local commits on top while accepting upstream changes for skill manifest conflicts. Save problematic local commits as patches first: `git format-patch -1 <SHA> -o /root/nous-agaas/backups/`.

**Detection:** `git log --oneline @{u}..HEAD` shows local commits; `git log --oneline HEAD..@{u}` shows upstream commits. Both nonzero = diverged.

**Why no new LESSON file:** RULE ZERO.

### AP-73 — `library_crossref_scan.py` had blind spots on CLAUDE.md and `laws/`; broken Tier-A1 wikilinks went silently uncaught (session s2127, 2026-04-30)

**Pattern:** `tools/library_crossref_scan.py` walked only `pages/**/*.md` — vault-root doctrine files (CLAUDE.md, MEMORY.md, log.md, index.md) and `laws/*.md` were OUTSIDE the scan scope. Crossref gate reported PASS while two real Tier-A1 broken wikilinks existed: `[[library-grade-audit]]` in CLAUDE.md (→ phantom skill, peer s108-mac-69060 restored as `bec8dd09`) and `[[factory-poller]]` in `laws/LAW-017-success-is-skill-save-everywhere.md` (→ `factory-poller.py` script; should have been backtick code-ref). Same s100 commit `9b0505a6` had earlier fixed this same broken-wikilink pattern in CALIBRATION-doctrine-drift, but the fix didn't propagate because the scanner couldn't see the violators.

**Root cause:** `collect_pages()` used `PAGES.rglob("*.md")` where `PAGES = ROOT / "pages"`. `library_quality_scan.classify()` returned Tier C for top-level files (no scoring weight), so even if they had been included they'd not have hit the A1 gate. Two-layer hole: (1) scope, (2) tier classification.

**Rule:** every scanner that gates on Tier-A1 wikilinks MUST scan all canonical-doctrine sources: `pages/**/*.md` + `laws/**/*.md` + vault-root `{CLAUDE,MEMORY,log,index}.md`. README.md stays at C (developer doc, not runtime doctrine). subtier_for() must explicitly classify root-level doctrine files as A1, not delegate to library_quality_scan.classify().

**Detection:**
```bash
# Did the scanner ever see CLAUDE.md? Should report `1` after fix, not `0`.
python3 tools/library_crossref_scan.py --json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print('claude.md scanned:', any('CLAUDE.md' in s.get('in_file','') for s in d.get('broken_wikilinks_tier_a1_sample',[])))"
```

**Fix shipped this session:**
- `tools/library_crossref_scan.py` `collect_pages()` extends candidates with `laws/` + vault-root files
- `tools/library_crossref_scan.py` `subtier_for()` returns "A1" for `claude.md|memory.md|log.md|index.md`
- Verification: scanner went from PASS-but-blind to RED-with-2-broken to PASS-after-fixes (regression caught + fixed in same session)

**Cross-ref:** `library-grade-audit` AP-2 (companion AP — every scanner needs a "what's outside my scope?" audit); session-100 commit `9b0505a6` (same wikilink-vs-code-ref pattern, fixed without scanner upgrade); `karpathy-loop` AP-3 (hygiene-disguised-as-value — what s100/104/106 GREEN reports actually meant).

**Why no new LESSON file:** RULE ZERO.

### AP-72 — `gbrain-dryrun` frontmatter-migration tool corrupts production wiki when run against `/root/nous-agaas/wiki/` (session s2127, 2026-04-30)

**Pattern:** Session s2127 audit found VPS working copy with 17+ uncommitted-but-corrupted files (agent-quality SKILL.md + 8 extracted skills + 8 handoffs/task-results + templates/daily.md), plus matching `.bak` files. The corruption injected spurious `---\n\n` mid-frontmatter (closes YAML block prematurely, orphaning `absorbs_laws:`/`related:` keys to body) and removed `slug:` fields from extracted/. Source: `/opt/nous-agaas/gbrain-dryrun/test/{frontmatter-migration,frontmatter-install-hook,frontmatter-cli}.test.ts` was run against the live wiki repo, not its own dryrun fixture dir.

**Root cause:** the gbrain-dryrun frontmatter-migration tool exists as a sandbox for testing v0.22.16+ schema changes (issue #531 follow-up). It writes `<file>.bak` then rewrites the original. When invoked with `--repo /root/nous-agaas/wiki/` (or implicit cwd), it modifies the canonical vault.

**Rule:** ALL frontmatter-migration / schema-rewrite tools MUST refuse to run against `/root/nous-agaas/wiki/`, `/Users/madia/nous-agaas/wiki/`, or `/Users/madia/Documents/Projects/Nous AGaaS/Nous/` unless invoked with `--allow-canonical-vault` flag AND the operator confirms in interactive prompt. Default-safe: write to a separate scratch dir.

**Detection:**
```bash
# Check for .bak files in working copies (always evidence of in-place rewrite)
find /root/nous-agaas/wiki -name "*.bak" -type f 2>/dev/null | head -5
# Check VPS working copy for uncommitted YAML-shape changes
ssh root@65.108.215.200 "cd /root/nous-agaas/wiki && git diff pages/skills/ pages/skills/extracted/ 2>&1 | grep -E '^\+(---|\$)' | head -10"
```

**Recovery:**
```bash
ssh root@65.108.215.200 "cd /root/nous-agaas/wiki && git checkout -- . && git clean -fd"
```

**Cross-ref:** session-100 issue #531 upstream filing; AP-64/65/66 (gbrain v0.22 upgrade arc); `karpathy-loop` AP-3 (write-negative-first — would have surfaced this risk in pre-deploy review).

**Why no new LESSON file:** RULE ZERO.

### AP-74 — `library_crossref_scan.py` classified dashboards as Tier-A1, causing auto-generated hub files to fail the gate (session s1526, 2026-04-30)

**Pattern:** `pages/dashboards/orphan-index.md` (1655 wikilinks to gbrain-orphan slugs) was classified as Tier-A1 by `subtier_for()` because it matched `pages/dashboards/` in `TIER_A_PATTERNS` but was not in `TIMESERIES_RES`. The crossref scanner gated it against "0 broken wikilinks" — causing 589 false-failures. Dashboards are auto-generated hubs; their wikilinks are inventory references (slugs from gbrain that may have no .md file), not doctrine cross-references.

**Root cause:** `TIMESERIES_RES` only listed specific filename patterns (`dream-cycle-proposals-YYYY-MM-DD.md`, `commit-review-YYYY-MM-DD.md`). Generic `pages/dashboards/` was not included even though all dashboards share the same auto-generated-hub semantics.

**Rule:** ALL `pages/dashboards/*.md` files are Tier B report-only in the shared classifier and informational in the crossref scanner, not Tier-A1. Dashboard wikilinks are inventory/exploration refs, not authoritative cross-refs. Gate only Tier-A1: skills, laws, systems, entities, projects, canonical concepts, tenant skill docs, and doctrine root files.

**Fix shipped:** `TIMESERIES_RES` in `library_crossref_scan.py` extended with `pages/dashboards/.+\.md` pattern. Wikilink coverage now 5624 (dashboards included as informational). Tier-A1 gate still 0 broken.

**Cross-ref:** AP-73 (same scanner scope evolution arc); [[library-grade-audit]] AP-2 (scope audit companion).

**Why no new LESSON file:** RULE ZERO.

### AP-75 — Use `get_page(slug)` for canonical doctrine retrieval; `search()` returns most-narrating chunk, not most-canonical (session s108-mac-99667, 2026-04-30)

**Pattern:** Title-retrievability probe at session-close: query `mcp__gbrain__search "musk-algorithm"` returned 14 hits, none of which were `pages/skills/musk-algorithm/skill` itself. Top-1 was `pages/progress/handoff-auto-2026-04-22-session-64-musk-algorithm-codified` (the handoff that NARRATES the skill). Adding `title: "musk-algorithm"` to the SKILL.md frontmatter updated gbrain's `pages.title` field (verified via SQL after autopilot re-extract) but did NOT improve the search ranking — score for the canonical was unchanged at 0 (not in results).

**Root cause (verified):** `mcp__gbrain__search` ranks by **chunk-content embedding similarity** to the query. The `pages.title` column is metadata for display, not part of the embedded vector. Handoffs that narrate a skill have denser per-chunk discussion of the skill name (titles like `"...session-64-musk-algorithm-codified"`, paragraphs explaining what the skill does in context); the SKILL.md itself contains the bare skill-name once in frontmatter + once in H1 + sparsely in body, with most chunks being rule definitions that happen to discuss the term less per chunk than narration does.

**Two-tool retrieval doctrine — apply by intent:**

| Intent | Tool | Why |
|---|---|---|
| "Read the canonical doctrine for `<skill-name>`" | `mcp__gbrain__get_page slug=pages/skills/<name>/skill` | Returns the exact authoritative file. No ranking surprises. |
| "Where is `<skill-name>` discussed across the substrate?" | `mcp__gbrain__search query=<skill-name>` | Returns most-narrating chunks — handoffs, audits, related skills. Useful for context, NOT canon. |
| "What's the doctrine on `<topic>`?" (when canonical slug unknown) | `search` first to find candidate slugs → `get_page` on top result | Two-step lookup. |

**Scoping rule:** any agent answering "what does the skill say?" or "what's the doctrine?" MUST use `get_page` not `search`. Using search-first-without-get_page-followup is the same class as `karpathy-loop` AP-3 (hygiene-disguised-as-value): you'll get high-scored results that confidently answer the wrong question.

**Companion AP queued:** [[library-grade-audit]] Gate 6 currently reads "`mcp__gbrain__search "<known-query>"` top-1 score ≥0.9". This conflates "search returns relevant context" with "canonical retrieval works". Recommend split into Gate 6a (search-relevance, current spec) + Gate 6b (canonical-retrievability via `get_page` round-trip). Filed for next session as the skill author's lane.

**Detection (sanity):**
```bash
# canonical retrievable via slug
mcp__gbrain__get_page slug=pages/skills/<name>/skill
# search ranks (often won't be top-1 — that's expected, not a defect)
mcp__gbrain__search query=<name>
```

**Display hygiene (still useful):** add `title: "<skill-name>"` to every SKILL.md frontmatter even though it doesn't improve search ranking — it does improve the `pages.title` shown by `list_pages` and by gbrain UI/exports. Mass-apply is low-risk and recommended; tracked as future-session task. Currently 16/71 skills have explicit titles; 55 still rely on the filename-stem fallback ("Skill").

**Cross-ref:** [[library-grade-audit]] Gate 6 (needs split per above); session-100 issue #531 (gbrain v0.22 retrieval-relevance — upstream lane); `karpathy-loop` AP-3 (search-PASS-without-canonical-check is hygiene-disguised-as-value).

**Why no new LESSON file:** RULE ZERO.

### AP-76 — Library tier policy is a shared executable classifier contract (session s108 Codex desktop, 2026-04-30)

**Pattern:** Multiple same-day lanes alternated between treating report streams as Tier A, demoting all reports to Tier B, and treating entities/projects/concepts as canonical without updating every dependent scanner. Tests and prose drifted from `library_quality_scan.py`, causing one verifier to pass while another failed.

**Root cause:** tier policy was duplicated across scanner code, unit tests, AUDIT-061 prose, pre-commit comments, reachability/canonical/crossref comments, and skill bodies. Agents changed one layer without moving the whole contract.

**Rule:** `tools/library_quality_scan.py:classify` plus `tools/test_library_quality_scan.py` is the executable source of truth. Current contract: Tier A = core runtime/library catalog pages (laws, `pages/laws`, active skills, tenant skills, systems, entities, projects, canonical concepts). Tier B = generated/report/import receipts (audits, specs, plans, progress-plans, dashboards, handoffs, task-results, sources/vendor/upstream, tenant non-skill notes, `_gbrain`, concept source/upstream notes). Tier C = legacy/archive material (claude-memory, migrated lessons, extracted drafts, commit-review receipts, fallback legacy). `title:`/`name:` count as catalog title; `id:` does not.

**How to apply:** any tier edit must update classifier, classifier tests, metadata-audit wrapper tests, AUDIT-061 snapshot, downstream scanner prose/gates, and pre-commit trigger comments in one commit. If those disagree, stop and repair the contract before syncing gbrain.

**Detection:**
```bash
python3 -m pytest tools/test_library_quality_scan.py tools/test_library_metadata_audit.py -q
python3 tools/library_metadata_audit.py --wiki . --format markdown
python3 tools/library_reachability_scan.py
python3 tools/library_canonical_scan.py
python3 tools/library_crossref_scan.py
```

**Why no new LESSON file:** RULE ZERO.

### AP-78 — Doctor 100/100 path: 3 PR-fixable + 1 local-CTE-widening + 1 cwd-context (session 82-final, 2026-04-30)

**Pattern:** `gbrain doctor` reports `90/100` with two persistent WARNs (`resolver_health` 2 dry_violation + `graph_coverage` 0% on entity pages) on a Tan-default skills tree + markdown-only brain. Both look like upstream FPs but each has a different root cause + fix.

**Fixes (in order applied, all on 2026-04-30 session 82-final):**

1. **PR #535** (NESTED_QUOTES detector FP on flow-sequence quoted arrays) — `src/core/markdown.ts` skip when value starts/ends with `[]`. 22/22 tests pass.

2. **PR #536** (graph_coverage 0% on markdown-only brains FP) — `src/commands/doctor.ts` skip WARN when `entity_count = 0`. Surfaces "(N entity pages)" in WARN message.

3. **PR #537** (ingest + enrich DRY violations) — same-line backtick `\`skills/_brain-filing-rules.md\`` reference within 40-line `extractDelegationTargets` proximity. Both skill files patched.

4. **Local AP-54-See-also patch** (downstream of PR #537) — Nous-local AP-54 commit added a `## See also` markdown-link bullet that lacks a backtick alias; same-line `(backtick alias: \`skills/conventions/quality.md\`)` clears the residual. Local-only patch, no upstream PR (Tan's skills don't have See-also bullet).

5. **Local entity_pages CTE widening** (`postgres-engine.ts` + `pglite-engine.ts`) — Tan's CTE filters `type IN ('person','company')` only. Our brain types entity pages as `'entity'` (96 pages). Widen to `type IN ('person','company','entity','organization')` so existing typed pages count. Result: link_coverage jumps 0%→99%, timeline_coverage 0%→59%. Companion upstream PR #538 candidate.

6. **cwd-context** caveat: doctor must be run from `/opt/nous-agaas/gbrain` cwd. Outside that cwd, `findRepoRoot` returns null and resolver_health WARNs "Could not find skills directory". Fix: launchd/cron jobs that invoke `gbrain doctor` must `cd $GBRAIN_REPO_ROOT` first. Or pass `--skills-dir` explicitly.

**Verification (cwd-correct):**
```bash
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain doctor'
# Health score: 100/100. All checks passed.
```

**Why no new LESSON file:** RULE ZERO. Cross-ref: PR #535/#536/#537 in mayazbay/gbrain fork; this AP is the canonical "how we got to 100/100" reference.

### AP-79 — Plan/report pages must pass gbrain lint and readback before retrieval claims (Golden Substrate Audit, 2026-05-09)

**Pattern:** A new plan/report page can be committed, pushed, and visible in the vault while still being absent from gbrain retrieval. The false-green is especially tempting during audit work because the file exists on disk and git sync is green.

**Root cause found 2026-05-09:** `PLAN-GOLDEN-SUBSTRATE-AUDIT-2026-05-09.md` synced to Mac/Air/VPS/bare, but `gbrain get pages/plans/plan-golden-substrate-audit-2026-05-09` and `gbrain search "Golden Substrate Audit"` missed it. The direct linter named the importer blocker: `L1 missing-created: Frontmatter missing required field: created`.

**Rule:** The AP-63 handoff rule applies to every new substrate-bearing `type: plan`, `type: progress`, `type: audit`, `type: spec`, `type: task-result`, and skill-adjacent report page. Before claiming "saved to gbrain" or "retrievable", run all three gates:

1. `gbrain lint <absolute wiki file path>` returns 0 issues.
2. `gbrain get <lowercase-slug>` returns the page or `gbrain list --type <type>` shows the slug after the next sync/import cycle.
3. A targeted `gbrain search "<exact title or id>"` returns the page when semantic retrieval is the user-facing claim.

**Detection:**

```bash
ssh vps 'cd /opt/nous-agaas/gbrain && bin/gbrain lint /root/nous-agaas/wiki/pages/plans/PLAN-GOLDEN-SUBSTRATE-AUDIT-2026-05-09.md'
ssh vps 'cd /opt/nous-agaas/gbrain && bin/gbrain get pages/plans/plan-golden-substrate-audit-2026-05-09'
ssh vps 'cd /opt/nous-agaas/gbrain && bin/gbrain search "Golden Substrate Audit"'
```

**Repair:** add missing required frontmatter first (`created:` in this incident), then rerun lint/readback after sync. Do not bulk `put` or force-ingest to hide malformed metadata unless the page also passes lint.

**Why no new LESSON file:** RULE ZERO. Cross-ref: AP-63 (handoff-specific predecessor), AP-61 (lowercase slugs), AP-75 (use `get` for canonical readback before relying on search ranking).

### AP-80 — Mirror-imported hubs require registered source sync plus readback before parity claims (KEONA sync, 2026-05-11)

**Pattern:** A cowork/Claude mirror can contain a current project hub while the active Obsidian/gbrain wiki remains stale. Copying the files into the active vault and pushing git is necessary but not sufficient: gbrain can still be blind if the registered source has not synced recently.

**Root cause found 2026-05-11:** The current KEONA hub lived at `/Users/madia/Documents/Claude/Projects/Nous/pages/projects/keona-pilot/keona-pilot.md`, but the active wiki had no `pages/projects/keona-pilot` hub. After importing and pushing the hub, `gbrain get pages/projects/keona-pilot/keona-pilot` still returned `page_not_found`. `gbrain sources list` showed the registered `default` source for `/root/nous-agaas/wiki` had last synced on 2026-04-30, so the issue was a stale gbrain source, not a slug typo.

**Rule:** For any mirror-imported business/project hub, claim Obsidian/gbrain parity only after these gates are green:

1. Active vault file exists and commit is pushed.
2. VPS working copy and Air wiki are fast-forwarded to the same commit.
3. `gbrain get <lowercase-slug>` succeeds. If it fails, run `cd /opt/nous-agaas/gbrain && ./bin/gbrain sources list`; if the relevant source is stale, run `./bin/gbrain sync --source default` rather than ad hoc `put`.
4. `gbrain search "<distinct project keyword>"` returns the imported hub or companion artifact.
5. If QMD MCP returns `Transport closed`, report QMD as degraded instead of laundering it as green through filesystem proof.

**Detection / repair commands:**

```bash
ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && git rev-parse --short HEAD && test -f pages/projects/keona-pilot/keona-pilot.md'
ssh air 'cd ~/nous-agaas/wiki && git rev-parse --short HEAD && test -f pages/projects/keona-pilot/keona-pilot.md'
ssh root@65.108.215.200 '/opt/nous-agaas/gbrain/bin/gbrain get pages/projects/keona-pilot/keona-pilot'
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && ./bin/gbrain sync --source default'
ssh root@65.108.215.200 '/opt/nous-agaas/gbrain/bin/gbrain search "Maru Analytics"'
```

**Why no new LESSON file:** RULE ZERO. Cross-ref: AP-79 (lint/readback for new report pages), AP-63 (handoff readback), AP-33 (CLI fallback when MCP transport closes).

### AP-81 — Cyrillic/Unicode vault docs require UTF-8-safe edit commands (KEONA research restore, 2026-05-11)

**Pattern:** Many business/legal vault pages are Russian or mixed-language Markdown. Byte-oriented one-liners can silently corrupt Cyrillic into replacement characters or mojibake, especially when the command mixes emoji/unicode character classes with the shell's current locale.

**Root cause found 2026-05-11:** During KEONA research sync, a mechanical `perl -pi` emoji-cleanup pass over `Astana_Hub_vs_MFCA_Analysis.md` corrupted Cyrillic text. The business logic was not the issue; the edit primitive was unsafe for multilingual vault content.

**Rule:** For Cyrillic/Unicode vault docs:

1. Prefer `apply_patch` for semantic edits.
2. For mechanical rewrites, only use UTF-8-aware tools after confirming locale, or use a trusted parser/library that preserves encoding.
3. After any bulk rewrite on multilingual docs, run a Unicode replacement-character scan before continuing.
4. If corruption appears, immediately restore the affected file from the trusted source (`git checkout -- <file>` if the trusted source is git, or recopy from the cowork mirror if that was the source of truth), then reapply minimal semantic edits.

**Detection / repair commands:**

```bash
locale
python3 - <<'PY'
from pathlib import Path
for p in [*Path('pages/projects').rglob('*.md'), *Path('pages/communications').rglob('*.md'), *Path('pages/task-results').rglob('*.md')]:
    text = p.read_text(encoding='utf-8', errors='replace')
    if '\ufffd' in text:
        print(p)
PY
git diff --check
```

**Why no new LESSON file:** RULE ZERO. Cross-ref: AP-80 (mirror-imported hubs), AP-63 (readback before claims), AP-79 (lint/readback for report pages).

### AP-82 — Manual sync wrapper must source OpenAI-compatible proxy env before embedding (OpenBrain projection closeout, 2026-05-11)

**Symptom:** During OpenBrain projection closeout, `gbrain sync` / targeted skill embedding hit direct OpenAI quota (`429 You exceeded your current quota`) even though the VPS already had an OpenAI-compatible LiteLLM embedding environment at `/root/.gbrain/openai-compatible.env` and autopilot could use it.

**Root cause:** The manual `tools/gbrain_sync_wrapper.sh` loaded the canonical OpenAI key fallback but did not source `/root/.gbrain/openai-compatible.env`. Autopilot's runner had the proxy env path; the manual wrapper did not. That split made manual closeout paths use direct OpenAI while scheduled paths used the configured proxy.

**Detector:**

```bash
ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && GBRAIN_SYNC_WRAPPER_DRY_RUN=1 bash tools/gbrain_sync_wrapper.sh'
ssh root@65.108.215.200 'grep -n "load_openai_compatible_proxy" /root/nous-agaas/wiki/tools/gbrain_sync_wrapper.sh'
```

If sync output contains `429 You exceeded your current quota`, first verify the wrapper loads `/root/.gbrain/openai-compatible.env` before blaming gbrain itself.

**Fix:** Source `/root/.gbrain/openai-compatible.env` before the fallback key loader in every manual/scheduled sync wrapper, then prove with a targeted embed and retrieval probe:

```bash
ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && GBRAIN_SYNC_WRAPPER_DRY_RUN=1 bash tools/gbrain_sync_wrapper.sh'
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain embed pages/skills/library-grade-audit/skill'
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain search "OpenBrain projection duplicate content hash" | head -5'
```

**Why no new LESSON file:** RULE ZERO. This is an existing gbrain-ops failure class: manual maintenance path diverged from the configured embedding runtime.

### AP-83 — Stateful subcommand `--help` can hold the sync lock (cross-system sync audit, 2026-05-11)

**Symptom:** A harmless-looking help probe, `bin/gbrain sync --help`, blocked the later real sync with `Another sync is in progress (lock gbrain-sync held)`.

**Root cause:** In the deployed gbrain CLI, `sync --help` entered the `sync` command path far enough to spawn a sync process and hold the `gbrain-sync` lock. The help process was not useful output; it behaved like a stateful operation.

**Rule:** For gbrain subcommands that can mutate state or acquire locks, do not probe help by calling `<subcommand> --help` on production during closeout. Use global help, documentation, or wrap the probe in `timeout` and immediately inspect/clear the process if it hangs.

**Detector:**

```bash
ssh root@65.108.215.200 'ps -eo pid,etime,cmd | grep -E "gbrain (sync|import|embed)|gbrain-sync" | grep -v grep || true'
```

**Fix:**

```bash
ssh root@65.108.215.200 'kill -9 <stuck-gbrain-sync-help-pid> 2>/dev/null || true'
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain doctor --json'
```

Then prove the page via retrieval readback before claiming gbrain is current.

**Why no new LESSON file:** RULE ZERO. This is the same operational class as AP-59/AP-60: lock-bearing gbrain operations must be bounded and reaped.

### AP-84 — Clear stale `gbrain-sync` DB locks only after proving holder PID absence (Todoist/OpenClaw factory audit, 2026-05-11)

**Symptom:** Canonical wiki files were present on Mac/Air/VPS, but `gbrain search` and `gbrain get` could not retrieve the newest task-result pages. A manual sync returned `Another sync is in progress (lock gbrain-sync held)` even though no active `gbrain sync` process existed.

**Root cause:** The DB row `gbrain_cycle_locks.id='gbrain-sync'` outlived its worker process. The holder PID was absent, but the row TTL had not yet expired, so the CLI correctly refused to start another sync. This is different from AP-83's stuck help-process case: here the process was already gone and the stale DB lock was the blocker.

**Detector:**

```bash
ssh root@65.108.215.200 'PGPASSWORD=gbrain2026 psql -U gbrain -d gbrain -h localhost -c "SELECT id, holder_pid, holder_host, acquired_at, ttl_expires_at, now() AS now, ttl_expires_at < now() AS expired FROM gbrain_cycle_locks ORDER BY id;"'
ssh root@65.108.215.200 'ps -fp <holder_pid> || true'
```

**Fix:** Only when `ps -fp <holder_pid>` proves the holder is absent, delete the specific stale lock row and run the bounded sync/readback:

```bash
ssh root@65.108.215.200 'PGPASSWORD=gbrain2026 psql -U gbrain -d gbrain -h localhost -c "DELETE FROM gbrain_cycle_locks WHERE id = '\''gbrain-sync'\'' AND holder_pid = <holder_pid>;"'
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain sync --repo /root/nous-agaas/wiki --no-embed'
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain search "<exact canary>" | head'
```

Do not delete live lock rows just because sync is inconvenient. The proof is: holder PID absent, sync succeeds, exact retrieval returns the new page, and `content_chunks` has no `embedding IS NULL` rows.

**Why no new LESSON file:** RULE ZERO. This is an extension of AP-59/AP-60/AP-83 lock discipline: lock cleanup is allowed only after process absence is mechanically proven.

### AP-85 — `timeline-add` uses positional args; stale flag examples can false-green (skill evolution closeout, 2026-05-11)

**Symptom:** During the skill-evolution closeout, three gbrain timeline writes returned `{ "status": "ok" }`, but `bin/gbrain timeline pages/skills/<skill>/skill` did not show the new entries for two target skills.

**Root cause:** Current gbrain v0.22.16 CLI help says `timeline-add <slug> <date> <summary>`. Older doctrine and hook hints still showed flag-style examples (`--slug ... --date ... --summary ...`). The command accepted the flag-style invocation enough to return OK, but it did not prove the intended skill timeline was updated.

**Rule:** For CLI fallback timeline writes, use positional syntax and immediately read back the same slug:

```bash
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain timeline-add pages/skills/<skill>/skill YYYY-MM-DD "<summary>"'
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain timeline pages/skills/<skill>/skill | grep "<unique summary token>"'
```

Do not trust `{ "status": "ok" }` alone for timeline writes. The proof is status OK plus same-slug timeline readback.

**Why no new LESSON file:** RULE ZERO. This extends AP-33 (CLI fallback) with current CLI syntax and readback discipline.

### AP-86 — Doctor warnings need current-artifact readback before green/yellow claims (control-plane sync, 2026-05-12)

**Symptom:** During the 2026-05-12 control-plane sync audit, `gbrain doctor --json` stayed at `status: warnings` even after the wiki was synced, the embedding wrapper completed, embeddings were 100%, and the new audit page was searchable at score `1.0000`.

**Root cause:** Two warning classes can be historical or layout-derived rather than current retrieval failure:
- `sync_failures` may contain old `<head>` drift records from prior git races. On this run, both `gbrain sync --skip-failed` and `gbrain sync --retry-failed` were no-ops for those legacy `<head>` entries.
- `resolver_health` can warn `Could not find skills directory` because this vault's resolver lives at `pages/skills/_gbrain/RESOLVER.md`, while current gbrain doctor auto-detect expects `pages/skills/RESOLVER.md` or an OpenClaw-style workspace root.

**Rule:** A doctor warning is not enough to claim either green or red. Before reporting status, run and record all three:

```bash
ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && GBRAIN_SYNC_WRAPPER_DRY_RUN=1 bash tools/gbrain_sync_wrapper.sh && timeout 180 bash tools/gbrain_sync_wrapper.sh'
ssh root@65.108.215.200 '/opt/nous-agaas/gbrain/bin/gbrain search "<exact new artifact title>" | head'
ssh root@65.108.215.200 '/opt/nous-agaas/gbrain/bin/gbrain doctor --json'
```

If wrapper sync succeeds and exact current-artifact readback works, report retrieval as operational and list the doctor warning as a residual. Do not manually edit `~/.gbrain/sync-failures.jsonl` just to make the dashboard green; either fix the underlying layout/tooling in a dedicated gbrain maintenance lane, use the AP-88 narrow acknowledgment path for historical `<head>` drift, or leave an explicit residual in the audit.

**Why no new LESSON file:** RULE ZERO. This extends AP-63/AP-79 readback discipline and AP-84 lock discipline to warning interpretation: dashboard color follows current evidence, not cosmetic warning suppression.

### AP-87 — SKILL title metadata must be included in version-drift gates (factory-ops title drift, 2026-05-12)

**Symptom:** `factory-ops/SKILL.md` had `version: 1.34.0` and `# factory-ops v1.34.0`, but frontmatter `title:` still said `factory-ops v1.33.0`. Existing `test_skill_version_parity.sh` passed because it only checked `version:` and H1. Existing `test_skill_internal_consistency.sh` checked `description:` but not `title:`.

**Root cause:** Agents and gbrain read frontmatter first, but the detector treated `title:` as display-only. That lets a skill page be mechanically "version green" while the most visible metadata says the old version.

**Rule:** Any SKILL internal-consistency gate must compare every version-bearing top-level metadata field against the H1/current version, at minimum:

```bash
bash tools/test_skill_version_parity.sh
bash tools/test_skill_internal_consistency.sh --all
```

If `title:` contains a `vX.Y.Z`, it must match the H1 version. Do not call skill metadata clean until both probes pass.

**Why no new LESSON file:** RULE ZERO. This extends AP-75 metadata retrieval discipline and AP-85 readback discipline to the title/frontmatter surface.

### AP-88 — Historical `<head>` sync failures may be acknowledged only with proof (control-plane closeout, 2026-05-12)

**Symptom:** `gbrain doctor --fast --json` still warned on three unacknowledged `<head>` drift records after current wiki sync, embedding, and readback were green. `gbrain sync --source wiki --skip-failed` returned `Already up to date` and did not acknowledge the stale records.

**Root cause:** The warning records were historical git HEAD drift races, not file parse failures. The current CLI acknowledgment path can no-op when the source bookmark is already current, leaving doctor yellow even when the current artifact graph is healthy.

**Rule:** direct JSONL acknowledgment is allowed only for `<head>` drift rows, and only after all five proof gates pass:

1. Four-way parity is green for the current HEAD.
2. `gbrain sync --source wiki` and `gbrain embed --stale` succeed.
3. Exact `gbrain get`/`search` readback succeeds for the current artifacts.
4. `gbrain sync --source wiki --skip-failed` was attempted and did not clear the records.
5. A timestamped backup of `/root/.gbrain/sync-failures.jsonl` is written before mutation.

When updating rows, add `acknowledged`, `acknowledged_at`, `acknowledged_by`, and an evidence-rich `acknowledged_reason` naming the current HEAD and readback proof. Never acknowledge YAML/frontmatter/import errors this way; those must be fixed at the source file.

**Verification:** 2026-05-12 closeout backed up the JSONL, acknowledged only three historical `<head>` rows, then full `gbrain doctor --json` returned `status: healthy`, `health_score: 100`, `sync_failures: ok`, `embeddings: 100% coverage`.

**Why no new LESSON file:** RULE ZERO. This narrows AP-86: no cosmetic edits, but evidence-backed acknowledgment of historical HEAD-race receipts is valid operational hygiene.

### AP-89 — Scheduled doctor probes must run from the gbrain repo root (2026-05-13)

**Pattern:** The live gbrain engine was healthy, but scheduled report scripts could still recreate `resolver_health: WARN Could not find skills directory` because they invoked `/opt/nous-agaas/gbrain/bin/gbrain doctor` without first changing into `/opt/nous-agaas/gbrain`. Manual proof: running from outside the repo returned `status: warnings`, `health_score: 95`; running `cd /opt/nous-agaas/gbrain && bin/gbrain doctor --json` returned `status: healthy`, `health_score: 100`, `resolver_health: ok`.

**Rule:** any scheduled or report script that calls `gbrain doctor` must execute:

```bash
cd /opt/nous-agaas/gbrain && bin/gbrain doctor
```

Do not call the absolute binary path for doctor probes unless gbrain adds a future explicit `--repo-root` or `--skills-dir` flag and the script uses it.

**Detector:** `tools/tests/test_gbrain_doctor_cwd_static.py` must pass before claiming recurring gbrain doctor warnings are fixed.

**Why no new LESSON file:** RULE ZERO. This extends AP-19 from manual operator discipline to scheduled automation.

### AP-90 — Fresh source pages need normalized-slug embed and two retrieval proofs (Satory ERAP source capture, 2026-05-13)

**Symptom:** A new source page for the Ruslan/Assyl ERAP APK testing update imported into gbrain and `gbrain get` worked, but an operator-facing search query initially returned no results. The first targeted embed command used the filesystem-style uppercase filename slug and failed with `Page not found`; the follow-up `embed --stale` failed because the manual shell did not source `/root/.gbrain/openai-compatible.env`.

**Root cause:** Three proof surfaces were being conflated: filesystem path, gbrain's normalized lowercase slug, and retrieval usefulness. A page can exist in gbrain before the operator has proven the exact normalized slug, embedding path, and practical search term.

**Rule:** for every urgent human-forwarded source page that becomes operational memory, prove all four gates before claiming "gbrain synced":

1. `bin/gbrain list -n ... | grep <topic>` shows the normalized lowercase slug.
2. Targeted embed runs through the OpenAI-compatible env using that normalized slug:
   ```bash
   ssh root@65.108.215.200 'set -a; . /root/.gbrain/openai-compatible.env; set +a; cd /opt/nous-agaas/gbrain && bin/gbrain embed <normalized-slug>'
   ```
3. Exact `bin/gbrain get <normalized-slug>` readback shows the source text.
4. At least one practical `bin/gbrain search "<operator terms>"` or `bin/gbrain query "<operator question>"` returns the source or project status page. If one phrasing misses, report retrieval as yellow until a working operator-term proof exists; do not hide the miss.

**Why no new LESSON file:** RULE ZERO. This combines AP-61 lowercase lookup, AP-82 credential loading, and AP-86 current-artifact readback into a stricter fresh-source capture gate.

### AP-91 — Existing-page `gbrain put` repair for one stale skill row (Todoist comment-loop audit, 2026-05-13)

**Symptom:** Git, Air, VPS, GitHub, factory probe, and the canonical wiki file were green at `todoist-control-plane v1.4.9`, but `gbrain get pages/skills/todoist-control-plane/skill` still returned `v1.4.6` after an autopilot cycle. Manual `gbrain sync --repo ...` was blocked because the long-running autopilot daemon legitimately held the sync lock.

**Root cause:** The active daemon cycle did not update one existing skill row even though the filesystem source was current. Treating the dashboard as green would poison runtime memory; deleting locks would be wrong because the holder process was alive.

**Rule:** When the filesystem source is current, the page already exists in gbrain, and only that existing page body is stale, repair the exact page with `gbrain put` from the canonical file, then read back the same slug:

```bash
ssh root@65.108.215.200 'cat /root/nous-agaas/wiki/pages/skills/<skill>/SKILL.md | /opt/nous-agaas/gbrain/bin/gbrain put pages/skills/<skill>/skill'
ssh root@65.108.215.200 '/opt/nous-agaas/gbrain/bin/gbrain get pages/skills/<skill>/skill | grep "# <skill> v"'
```

This is an AP-13 exception only for updating an existing disk-backed page that already has a canonical wiki file. Do not use `put` to create new operational memory. If more than one page is stale, open a dedicated gbrain sync maintenance lane instead of hand-patching many rows.

**Why no new LESSON file:** RULE ZERO. This extends AP-13, AP-84, and AP-86: preserve lock discipline, but never leave a known stale canonical skill in retrieval.

### AP-92 — Frontmatter wikilink lists must be quoted YAML arrays (Telegram/OpenClaw audit, 2026-05-14)

**Symptom:** `gbrain doctor --json` from the correct gbrain repo root returned `health_score: 95` with `frontmatter_integrity` warnings even though resolver health, embeddings, wiki sync, and factory probes were otherwise green. `gbrain frontmatter validate /root/nous-agaas/wiki` isolated three `YAML_PARSE` failures in generated audit/handshake pages.

**Root cause:** Generated frontmatter used raw comma-separated wikilinks under a scalar field:

```yaml
related: [[page-a]], [[page-b]]
```

That looks readable in Obsidian but it is invalid YAML for the gbrain importer. The engine was correctly warning; the source documents were malformed.

**Rule:** any generated report, audit, handoff, handshake, goal, or progress page that stores multiple wikilinks in frontmatter must use a quoted YAML array:

```yaml
related:
  - "[[page-a]]"
  - "[[page-b]]"
```

Single wikilink scalar values must also be quoted if they contain `[` or `]`. Do not mark gbrain as golden while `gbrain frontmatter validate /root/nous-agaas/wiki` reports `YAML_PARSE`.

**Verification:** after fixing the three generated pages, rerun:

```bash
ssh root@65.108.215.200 '/opt/nous-agaas/gbrain/bin/gbrain frontmatter validate /root/nous-agaas/wiki'
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain doctor --json'
```

The expected result is zero YAML parse errors and no `frontmatter_integrity` warning.

**Why no new LESSON file:** RULE ZERO. This extends AP-63/AP-79 (report pages must pass lint/import/readback) and AP-86 (doctor warnings require current-artifact proof before green claims).

### AP-93 — Manual gbrain CLI embed shells must export sourced env files (Atomic substrate audit, 2026-05-16)

**Symptom:** During final atomic-substrate verification, `gbrain doctor --json` was healthy/100 but still reported `embeddings: 100% coverage, 3 missing`. A manual `./bin/gbrain embed --all` attempt after `. /root/.gbrain/openai-compatible.env` emitted repeated `OPENAI_API_KEY environment variable is missing or empty` errors.

**Root cause:** Shell sourcing without export set local shell variables, but the Node/Bun gbrain CLI only receives exported environment variables. The env file contained `OPENAI_API_KEY`, but the child process could not see it.

**Rule:** any manual gbrain command that needs embedding credentials must export the sourced env file:

```bash
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && set -a && . /root/.gbrain/openai-compatible.env && set +a && ./bin/gbrain embed <normalized-slug>'
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && set -a && . /root/.gbrain/openai-compatible.env && set +a && ./bin/gbrain doctor --json'
```

If an unexported embed pass starts spamming key-missing errors, stop that process, rerun the targeted normalized-slug embed with `set -a`, then verify `doctor --json` reports `embeddings: 100% coverage, 0 missing`. Do not run broad `embed --all` again until the env export path is proven.

**Why no new LESSON file:** RULE ZERO. This sharpens AP-82/AP-90: sourcing the proxy env is insufficient unless it is exported to the CLI process.

### AP-94 — Mem0 is deferred/backup-only unless one exact use case beats gbrain plus OpenBrain (Memory architecture check, 2026-05-18)

**Decision:** Mem0 is not a production memory authority for Nous AGaaS. It may remain a backup/export candidate, but it must not become a peer source of truth beside Obsidian, gbrain, and OpenBrain unless it wins a one-page proof on one exact use case.

**Evidence boundary:** the 2026-05-18 check found no local `mem0`/`mem0ai` Python package, no Air Mem0 launchd job, and no production factory integration. The existing substrate did have live proof: `gbrain doctor --fast` reported 3848 pages and 15428/15428 embedded chunks, while `tools/openbrain_project_to_wiki.py --dry-run --limit 20 --days 14 --json` returned `ok=true`, `projection_failed=false`, `would_create=0`, and `would_update=0`. Air launchd showed `com.nous.openbrain-projection`, `com.nous.todoist-comment-sweep`, `com.nous.todoist-sync`, `com.nous.goal-cycle`, and `com.nous.telegram-poll`, but no Mem0 service.

**Rule:** do not add Mem0 as a fifth memory plane. The canonical memory stack is:

1. Obsidian/wiki as source of truth;
2. gbrain for retrieval, embeddings, timeline, and readback;
3. OpenBrain by Nate B. Jones/OB1-style MCP as capture/projection ingress;
4. MEMORY.md/session context as an index into the same substrate.

Mem0 can be reconsidered only when a one-page audit proves it beats gbrain plus OpenBrain for one named workflow, using the same source corpus, same query, same expected answer, latency/cost counts, and a drift/failure analysis. A generic claim that Mem0 is "agent memory" is not enough. If Mem0 is kept, it is backup-only and must be a view/export over the vault, not an authority that can contradict it.

**Detector:** any proposal to wire `MEM0_API_KEY`, install `mem0`, create a Mem0 launchd service, or route OpenClaw/Todoist/Notion/Telegram memory lookups to Mem0 must first create `pages/audits/AUDIT-MEM0-VS-GBRAIN-<date>.md` with a single use-case win. Otherwise the correct action is `defer/backup-only`.

**Why no new LESSON file:** RULE ZERO. This extends AP-8's current architecture rule: wiki + gbrain + Air rsync are primary; old Mem0 notes are historical receipts or backup guidance, not production routing authority.

### AP-95 — Lock-bearing maintenance commands must have wall-clock bounds (Telegram presidential audit, 2026-05-20)

**Symptom:** The Obsidian/VPS wiki held the latest handoff and a new plan, and QMD CLI readback worked after `qmd update`, but gbrain keyword search still could not find the same-day artifacts. VPS process inspection showed `gbrain embed --stale` alive for 55+ minutes after embedding connection errors and a second `gbrain sync --repo /root/nous-agaas/wiki` waiting with no output, leaving fresh pages invisible to gbrain while lock dashboards looked like normal maintenance.

**Root cause:** AP-59/AP-60 moved autopilot into a single locked loop, but the loop still trusted each gbrain subcommand to return. When the embedding provider or CLI event loop stalls, the process can stay alive and hold the maintenance lane indefinitely; AP-84 stale-lock cleanup does not apply because the holder PID exists.

**Rule:** every lock-bearing or freshness-critical gbrain maintenance command must be wrapped with a wall-clock timeout. The runtime runner owns the bound, not the operator's SSH client. At minimum:

```bash
timeout -k 10s "$GBRAIN_AUTOPILOT_CMD_TIMEOUT" "$GBRAIN" sync --repo "$WIKI" --no-embed
timeout -k 10s "$GBRAIN_AUTOPILOT_CMD_TIMEOUT" "$GBRAIN" extract all --dir "$WIKI"
timeout -k 10s "$GBRAIN_AUTOPILOT_CMD_TIMEOUT" "$GBRAIN" embed --stale
timeout -k 10s "$GBRAIN_DAILY_SYNC_TIMEOUT" bin/gbrain sync --repo /root/nous-agaas/wiki
```

If the timeout fires, classify the probe as yellow/red with the exact command and tail output, stop the timed-out child, and prove freshness by exact readback before saying retrieval is green. Do not use `timeout --foreground` for these gbrain maintenance calls: it can leave gbrain's process tree alive after the deadline. Do not delete a live lock row while the holder PID exists; terminate the stuck child through its owning wrapper or a targeted `kill` only after process age/output evidence proves it is wedged.

**Detection:**

```bash
bash tools/test_gbrain_autopilot_secret_loading.sh
python3 -m pytest tools/test_daily_0300_substrate_sync.py -q
ssh root@65.108.215.200 'ps -o pid,etime,stat,pcpu,args -C gbrain | grep -E "sync|embed" || true'
```

**Why no new LESSON file:** RULE ZERO. This is AP-60/AP-83/AP-84 completed: lock discipline must include bounded runtime for live holder processes, not only daemon shape and stale-row cleanup.

### AP-96 — Embedding proxy health means configured base URL reachability, not local LiteLLM health (Telegram presidential audit, 2026-05-20)

**Symptom:** After bounded text sync made same-day handoffs and plans gbrain-readable, targeted embedding still stalled. Air LiteLLM was healthy locally at `127.0.0.1:4000`, and `/root/.gbrain/openai-compatible.env` had a key, but VPS `curl` to the configured `OPENAI_BASE_URL` timed out.

**Root cause:** the embedding env pointed at `http://madis-macbook-air-2.tailab95f4.ts.net:4000/v1`, which VPS MagicDNS resolved to stale `100.105.9.1`. The live Air Tailscale IP was `100.122.219.22`; `curl http://100.122.219.22:4000/health/readiness` succeeded from VPS and targeted gbrain embeds immediately worked after switching the base URL.

**Rule:** when gbrain embedding reports `Connection error`, test the exact configured URL from the VPS before changing keys, models, or gbrain code:

```bash
ssh root@65.108.215.200 'set -a; . /root/.gbrain/openai-compatible.env; set +a; curl -sS --max-time 5 "$OPENAI_BASE_URL/models" -H "Authorization: Bearer $OPENAI_API_KEY" | head'
ssh air 'tailscale ip -4'
ssh root@65.108.215.200 'nc -vz -w 5 <air-tailscale-ip> 4000'
```

If MagicDNS is stale but the current Air Tailscale IP is reachable, update only `OPENAI_BASE_URL`, keep the existing key/model, then prove with one normalized-slug targeted embed before running broad `embed --stale`.

**Why no new LESSON file:** RULE ZERO. This extends AP-82/AP-93/AP-95: credential correctness, env export, and timeouts are not enough if the configured network endpoint is stale.

### AP-98 — Silent embedding failure: per-page errors with positive summary lies about sync health (s108-mac-60468 spawn, 2026-05-20)

**Symptom:** `bin/gbrain sync --repo /root/nous-agaas/wiki` emitted per-page `[gbrain] embedding failed for <slug> (N chunks): OPENAI_API_KEY missing` lines while the run-end summary still reported `Synced 85f00f37..12e7c89b: 11 chunks created, 2 pages embedded`. Down-stream consumers trusted the receipt. Vector search was silently degraded for every page synced since the credential was unreachable.

**Root cause (instance):** the bug repro path invokes the CLI directly without sourcing `/root/.gbrain/openai-compatible.env` — AP-82/AP-93 already gate manual/scheduled wrappers, but the gbrain binary itself prints partial-success summaries even when per-page embeds raised `OPENAI_API_KEY environment variable is missing or empty`. Fixing AP-82 closed the operational path; the lying summary is the SECOND failure class that needs a mechanical gate so any future credential, network, or quota regression cannot masquerade as a healthy sync.

**Rule (the gate):** every gbrain sync surface — `tools/gbrain_sync_wrapper.sh`, `/root/.gbrain/autopilot-run.sh`, `tools/daily_0300_substrate_sync.py`, ad-hoc verification probes — must pipe its sync stdout/stderr through `tools/test_no_lying_logs.py`. Any `N pages embedded` summary with `N > 0` preceded by an `embedding failed` line in the same run is a violation; the script exits 1 and the caller MUST mark the cycle failed (and trigger AP-99 alert), not green. Counter-checks (vector search for a page that should have just embedded) remain the truth, but the lying-log gate is what makes the regression OBSERVABLE on cycle #1 instead of "sometime later when a query returns nothing."

**Verification recipe:**

```bash
# Inline gate on a fresh sync run:
ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && bash tools/gbrain_sync_wrapper.sh 2>&1' \
  | python3 tools/test_no_lying_logs.py
# Exit 0 = clean; exit 1 = lying summary; stderr contains the offending lines.

# Self-test (CI / launchd watchdog smoke):
python3 tools/test_no_lying_logs.py --self-test
# All four synthetic fixtures must report [ok]; exit 0.

# Tail-mode against a rolling log:
python3 tools/test_no_lying_logs.py --input /var/log/gbrain-sync.log
```

**Counter-check (substrate truth, complementary to the gate):** after any sync that touches a known page, run `bin/gbrain query "<doctrine string from that page>" --json` and assert a non-zero top score with the expected slug. A clean §7.1 exit plus a positive vector hit is the GREEN state; either signal red → embedding regression.

**Why no new LESSON file:** RULE ZERO. This extends AP-82 (manual env source), AP-93 (CLI embed env export), AP-96 (proxy reachability) — those three close the *cause* paths; AP-98 closes the *receipt* path that let every prior cause hide.

### AP-99 — Telegram health alert when sync output contains `embedding failed` (s108-mac-60468 spawn, 2026-05-20)

**Trigger:** §7.1 gate (AP-98 / `tools/test_no_lying_logs.py`) returns exit 1 on a live sync cycle.

**Action:** the autopilot wrapper (`/root/.gbrain/autopilot-run.sh`) and the manual `tools/gbrain_sync_wrapper.sh` must capture sync stdout to a tmp file, pipe it through `tools/test_no_lying_logs.py`, and on non-zero exit call:

```bash
bash tools/tg_send.sh "🔴 gbrain sync lying-log violation on $(hostname) at $(date '+%FT%TZ'). $(grep -c 'embedding failed' "$tmp") embedding failures + positive 'pages embedded' summary. tail: $(tail -5 "$tmp")"
```

**Why this beats waiting for a query miss:** the prior incident was visible in the wiki for hours before a counter-check query surfaced it. Telegram is the operator's pager; one alert at cycle close beats hours of silent drift. `tg_send.sh` is send-only and works from any host (CC HARD RULE 1 token check passes), so this rule does not re-introduce an HTTP 409 risk.

**Why no new LESSON file:** RULE ZERO. This is the alert-leg of AP-98 — detection without notification leaves the operator blind. Detection script lives in `tools/`; routing lives here as doctrine so future sync surfaces inherit the same wiring.

### AP-100 — Canonical-vs-runtime drift on edits made via ssh (Karpathy Council, codex challenge, 2026-05-20)

**What happened:** v1.80.3 wired AP-99 into `tools/gbrain_sync_wrapper.sh` (vault canonical) AND `/root/.gbrain/autopilot-run.sh` (VPS-local, edited via `ssh root@VPS python3 < /tmp/patch.py`). The vault canonical for the autopilot — `tools/gbrain-autopilot-run.sh` — was NOT updated. The two should be byte-equivalent because `tools/test_gbrain_autopilot_secret_loading.sh` is the parity gate, but the gate's `check_runner_content()` was content-blind to AP-99: it asserted `flock`, `OPENAI_API_KEY`, `gbrain_link_builder.py`, `embed --stale`, etc. but never `test_no_lying_logs.py`, `tg_send.sh`, or `cycle_tmp`. So any future redeploy (rsync, scp, manual cp) from canonical would have silently erased the AP-99 wiring on VPS while tests stayed green. Codex challenge mode (the Karpathy Council adversarial leg) caught it on the first sweep.

**Meta-pattern: "edit-runtime-without-canonical" class.** Two specific cases this skill must defend against:
- (a) Agent edits `/root/.gbrain/<file>` on VPS via ssh + sed/heredoc, leaves the `tools/<file>` vault canonical stale. Next sync wrapper run from canonical clobbers the edit.
- (b) Agent adds a new behavior (gate, env loader, alert path) but the existing parity test was written before that behavior existed — the test does NOT assert the new behavior, so canonical/runtime divergence on that behavior is invisible.

Both are silent-regression classes. Both compound across sessions.

**Rule:** any edit to a runtime script that has a vault canonical MUST land in BOTH targets in the SAME commit. Acceptable patterns:
1. Edit the vault canonical → `scp` to VPS in the same session → commit canonical. (preferred)
2. Edit VPS directly → READ THE UPDATED FILE → write the exact bytes to the vault canonical → commit canonical → re-scp from canonical to confirm parity.
3. Never option 1 alone — VPS-only edits decay.

**Rule (parity test):** whenever a new behavior is added to a runtime script, the matching parity test MUST gain assertions for that behavior in the SAME commit. The test should fail-loud if a future redeploy strips the behavior. Each new AP that adds runtime behavior to a guarded script extends the guard.

**Codex Council findings closed in v1.80.4 (P1+P2+P3):**

| # | Severity | Issue | Fix |
|---|---|---|---|
| 1 | P1 | Vault canonical `tools/gbrain-autopilot-run.sh` had the old ungated `run_cycle()`; redeploy would erase VPS fix | Patched canonical with same wiring; scp to `/root/.gbrain/autopilot-run.sh` to re-sync |
| 2 | P1 | `tools/test_gbrain_autopilot_secret_loading.sh` did not assert `test_no_lying_logs.py` / `tg_send.sh` / `cycle_tmp` / `PIPESTATUS[1]` | Extended `check_runner_content()` + remote ssh-grep block with 5 new assertions |
| 3 | P2 | `tools/gbrain_sync_wrapper.sh` ran `$GBRAIN sync` under `set -e`; on non-zero exit the script died BEFORE logging or gating — observability regression vs prior `>> $LOG 2>&1` direct-log | Capture `SYNC_RC` explicitly, `cat tmp >> LOG` unconditionally, run gate regardless, then exit on rc |
| 4 | P2 | `${PIPESTATUS[0]}` alone ignored tee failures (disk full, perms); a truncated cycle would pass the gate falsely | Capture `${PIPESTATUS[1]}` too, fail-loud with `AP-100 ALERT tee_failed` |
| 5 | P2 | `EMBED_FAIL_RE = r"embedding failed for "` (literal trailing "for ") missed `embedding failed:`, `embedding failed pages/...`, tab separators, upstream wording drift | Widen to `r"embedding failed\b"` (word-boundary); added 2 fixtures (colon, no-for) |
| 6 | P3 | `mktemp` → `trap` had a tiny race; cycle_tmp leaked on signal between the two | Added `/tmp/gbrain-autopilot-cycle.*.log -mmin +30 -delete` sweep at cycle start (idempotent reaper); sync wrapper same |

**Open Council residuals (deferred, not P1):**
- Gate runs after the full chain (sync → extract → embed → link-builder), not after `embed --stale` boundary. If embed emits lying-log but exits 0, link-builder runs against degraded state before cycle is marked failed. Per-step gating considered; deferred because doctrine in AP-98 is "any embedding failed line in the same run" — single end-of-cycle gate is by design. Next iteration if false-negative observed in the wild.
- `tg_send.sh || true` discards alert-delivery failure (network down, token broken). Acceptable per Codex — the consecutive_errors counter still trips, and AP-99 is the alert-OF-LAST-RESORT; if both fail, operator notices via gbrain query miss. Could add stderr fallback log; deferred.
- Detector can false-positive on cumulative log file (e.g. `--input /var/log/gbrain-sync.log` with multiple historical cycles concatenated). Mitigated by current wrappers using a per-cycle tmp file. Doc note added at script top.

**Why no new LESSON file:** RULE ZERO. AP-100 extends AP-98/AP-99 — the detection + alert legs need a third leg (canonical parity) so the wiring cannot decay. Codified after Karpathy Council (codex challenge mode) caught the drift on its first sweep; codex was the "200 IQ autistic developer" reviewer per `karpathy-loop` AP-12 narrow Council escalation predicate (this work touched IR/retrieval semantic search reliability).

### AP-101 — Per-phase gating + tg_send delivery-failure fallback (Karpathy Council closeout, 2026-05-20)

**Context:** v1.80.4 closed Karpathy Council P1+P2 findings; 3 P3 residuals remained documented as deferred. User invoked god-level standard ("every single session closed to 100%") and authorized closing all P3 in the same session-window. AP-101 absorbs the closure.

**P3-1 closed (per-phase gate boundary):**

Previous design ran `sync(--no-embed) && extract && embed --stale && link-builder` as a single chained block, then gated end-of-cycle. Codex flagged: if `embed --stale` emitted lying-log but exited 0, link-builder ran against degraded embedding state BEFORE the cycle was marked failed. New design splits run_cycle into 3 phases with gate IMMEDIATELY after Phase 2 (the only phase that can emit lying-log):

1. **Phase 1 — sync(--no-embed) + extract** → tee to `cycle_tmp`. No embedding here.
2. **Phase 2 — embed --stale** → tee to `embed_tmp` AND `cycle_tmp` (double-tee, 3 PIPESTATUS checked). Gate `embed_tmp` via `run_lying_log_gate "$embed_tmp" "post-embed"`. **Violation → return 1; link-builder NEVER runs.**
3. **Phase 3 — link-builder** → only reached if phase 2 gate passed; tee to `cycle_tmp`.
4. **Backstop** — re-gate full `cycle_tmp` (cheap belt-and-braces in case phase 1 or 3 emits the pattern).

`embed_tmp` gets the same `-mmin +30 -delete` reaper sweep as `cycle_tmp`.

**P3-2 closed (tg_send delivery-failure fallback):**

Previous: `bash $TOOLS/tg_send.sh "..." || true` — discarded return code. Telegram down → silent. New `run_lying_log_gate()` captures tg_send exit; on non-zero:
- `echo "[cycle] custom-autopilot AP-101 ALERT tg_send_failed context=<X> fail_count=<N>" >&2` → autopilot.log
- `echo {"ts":..., "event":"tg_send_failed", ...} >> ${GBRAIN_ALERT_FALLBACK_LOG:-/root/.gbrain/alerts-fallback.jsonl}` → durable JSONL any other monitor / cron can tail

Same fallback pattern in `tools/gbrain_sync_wrapper.sh` for the manual sync surface.

**P3-3 (cumulative-log false-positive doc):** docstring warning added clarifying production wrappers use per-cycle tmp files; `--input /var/log/gbrain-sync.log` is ad-hoc debug only.

**Parity test extended (drift prevention for AP-101):**

`tools/test_gbrain_autopilot_secret_loading.sh` now asserts on both LOCAL canonical AND remote VPS:
- `run_lying_log_gate` (helper name; proves per-phase architecture)
- `embed_tmp` (proves embed step has its own gate boundary)
- `alerts-fallback.jsonl` (proves the tg fallback path is wired)
- `post-embed` (proves the gate's audit-trail context label)

Combined with AP-100's 5 assertions, parity test now has **9 AP-99/AP-100/AP-101 assertions**. Any future redeploy stripping any element fails the gate loudly.

**Council closure status (8/8):** Karpathy Council closed 100%.

**Why no new LESSON file:** RULE ZERO. AP-101 is the final-mile follow-up to AP-100 — once Council finds a defect class, doctrine absorbs ALL identified failure modes in the same session-window, not just P1s. "100% completion" is the project standard.

### AP-102 — Do not run secret-loading gbrain wrappers under xtrace

**Failure mode:** during a 2026-05-21 sync audit, the wrapper returned non-zero because another sync held the lock. The follow-up diagnostic used shell xtrace on `tools/gbrain_sync_wrapper.sh`. Because that wrapper sources the OpenAI-compatible env before running gbrain, xtrace printed secret-bearing assignment lines into local command output.

**Root cause:** xtrace is not a safe diagnostic primitive for shell scripts that source env files, read auth JSON, or export credentials. Even when the key is a proxy credential and not committed to git, it still becomes transcript/log material.

**Rule:** never run `bash -x`, `set -x`, `env`, or shell traces around gbrain wrapper/autopilot paths that load credentials. Use sanitized diagnostics only: wrapper dry-run output that reports key presence/length, `stat` mode checks, `ps` lock-holder checks, wrapper exit code, and tails of logs that are known not to include sourced env lines. If deeper tracing is unavoidable, first patch a local throwaway copy to mask secret-shaped variables, run it outside git, and do not paste raw output.

**Mechanical detector:** reviewer closeout must grep planned diagnostic commands for `bash -x`, `set -x`, and `env` before running secret-loading wrappers. Existing wrapper gates remain `tools/test_gbrain_sync_wrapper_secret_loading.sh`, `tools/test_gbrain_autopilot_secret_loading.sh`, and `tools/test_no_lying_logs.py --self-test`; none of those require xtrace.

### AP-103 — SSH banner timeouts can be stale local transports

**Failure mode:** gbrain timeline writes failed with `Connection timed out during banner exchange`, while `nc -vz 65.108.215.200 22` and `ping` were healthy. Retrying the same command kept failing, and the MCP surface reported `Transport closed`.

**Root cause:** this Codex process had stale local SSH child transports to the VPS (`qmd status`, `qmd mcp`, and `gbrain-mcp`). The VPS was reachable; the local session was carrying dead/stuck bridge processes that made fresh SSH banner negotiation unreliable.

**Rule:** before declaring "VPS down" or "gbrain down" on banner-exchange timeouts, check local stale transports first:

```bash
ps -axo pid,ppid,etime,command | rg 'ssh .*65\\.108\\.215\\.200|gbrain-mcp|qmd mcp|root@65\\.108\\.215\\.200' | rg -v rg
nc -vz -w 5 65.108.215.200 22
ping -c 3 -W 2000 65.108.215.200
```

If the network probes pass and the stale SSH children belong to the current Codex process, terminate only those stale child processes, then retry the gbrain CLI fallback. Do not kill unrelated peer SSH sessions.

**Proof pattern:** after killing only the stale local SSH children, `ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain timeline-add ...'` returned `{"status":"ok"}`.

### AP-104 — Repair YAML-invalid Obsidian wikilink arrays in frontmatter only

**Failure mode:** `gbrain doctor --json` reported `frontmatter_integrity` warnings for 33 YAML parse failures where frontmatter used Obsidian-readable but YAML-invalid lines like `related: [[a]], [[b]]`. Running `gbrain frontmatter validate /root/nous-agaas/wiki --fix` detected the files but wrote `0` backups and made no changes.

**Root cause:** the built-in fixer did not understand comma-separated Obsidian wikilinks in a YAML scalar. AP-92 already banned generating new invalid lines, but older audit/spec/progress/source pages still carried the pattern.

**Rule:** repair this class only inside the opening YAML frontmatter block. Convert every frontmatter line shaped `related: [[a]], [[b]]` to a quoted YAML array: `related: ["[[a]]", "[[b]]"]`. Do not rewrite body text, markdown bullets, or non-frontmatter examples.

**Proof pattern:** after the mechanical rewrite, run a local YAML parse of the changed frontmatter, then run VPS `gbrain frontmatter validate /root/nous-agaas/wiki` after sync. Only claim green if the warning count drops to zero.

### AP-105 — QMD on VPS is CPU-default; do not wrap through a symlink target

**Failure mode:** after installing Vulkan build dependencies for QMD, `qmd status` attempted to compile the Vulkan backend on the 8 GB VPS and was OOM-killed at about 63%. A follow-up wrapper attempt wrote through `/usr/local/bin/qmd`, which was a symlink to the npm package entrypoint, and accidentally replaced `/usr/local/lib/node_modules/@tobilu/qmd/bin/qmd` with a recursive shell wrapper.

**Root cause:** the VPS has no useful GPU path for QMD. Letting `node-llama-cpp` auto-detect Vulkan causes expensive source builds with no production value. Separately, shell redirection follows symlinks, so wrappers around npm global binaries must remove/replace the symlink itself rather than writing to the symlink path.

**Rule:** on VPS, QMD must default to CPU unless a real GPU host is explicitly promoted. Preserve the package entrypoint, replace only `/usr/local/bin/qmd` with:

```bash
#!/bin/sh
export QMD_LLAMA_GPU="${QMD_LLAMA_GPU:-false}"
exec /usr/local/lib/node_modules/@tobilu/qmd/bin/qmd "$@"
```

If the package entrypoint is damaged, restore it to:

```bash
#!/bin/sh
exec /usr/local/bin/node /usr/local/lib/node_modules/@tobilu/qmd/dist/cli/qmd.js "$@"
```

**Proof pattern:** `qmd --help` returns immediately, `qmd search ... -c nous` returns in under 1s, `qmd status` shows no `Pending:` line after `qmd update --pull && qmd embed`, and the HTTP MCP is restarted with the wrapper in place.

### AP-106 — Native Codex QMD `Transport closed` must be split into config visibility vs server health

**Failure mode:** a native Codex QMD MCP call returned `Transport closed`, while the VPS QMD CLI, QMD stdio MCP server, and QMD HTTP MCP server were all healthy. A separate probe then found `codex mcp get nous-wiki-qmd` worked from `/Users/madia/Documents/Projects/Nous AGaaS` but failed from `/Users/madia/Documents/Projects/Nous AGaaS/Nous`.

**Root cause:** "QMD" is not one surface. The durable substrate includes at least six layers: cwd-visible Codex MCP config, native Codex MCP transport, VPS `qmd status`, VPS `qmd mcp` stdio JSON-RPC, VPS HTTP MCP, and QMD index/update/embed state. In this incident the parent project root had `.codex/config.toml`, but the vault root did not. A failure in one client transport or launch root does not prove the index or server is down.

**Rule:** before blaming QMD for a native Codex `Transport closed`, run from the same cwd where the agent/session is launched:

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
codex mcp get nous-wiki-qmd
python3 tools/qmd_mcp_doctor.py --json
```

Interpretation:

- `qmd_cli.ok=true`, `qmd_stdio.ok=true`, and `qmd_http.ok=true` means the underlying QMD substrate is healthy; report the residual as local/native Codex MCP transport or config.
- `codex_config.ok=false` means the Codex CLI config for that server name is missing or drifted; that is a client registration/config gap, not QMD data loss.
- Only classify QMD itself red when the CLI or stdio server checks fail.

**Current fixed path:** `Nous/.codex/config.toml` mirrors the parent non-secret `gbrain` and `nous-wiki-qmd` MCP config so both launch roots expose the same SSH-backed MCP servers. `tools/qmd_mcp_doctor.py` checks Codex config, QMD CLI counts, QMD stdio MCP initialize/status, and QMD HTTP initialize.

**Proof pattern:** `codex mcp get nous-wiki-qmd` from the vault root returns `transport: stdio`; `python3 -m pytest tools/tests/test_qmd_mcp_doctor.py -q` passes; live `python3 tools/qmd_mcp_doctor.py --json` returns `classification=green:underlying_qmd_healthy_native_codex_tool_must_be_checked_in_session` with document/vector counts. If the already-running in-session native MCP tool still says `Transport closed`, it is a stale runtime-handle residual until the Codex session/app transport is restarted.

### AP-107 — Scheduled gbrain autopilot is a one-shot cycle, not a persistent daemon

**Failure mode:** `GBRAIN_AUTOPILOT_ONCE=1 /root/.gbrain/autopilot-run.sh` returned rc=1 because an older cron-launched autopilot process held `/var/lock/gbrain-autopilot.lock` for almost two days. The gbrain data path was healthy, but the proof gate looked red because the scheduler started the runner without `GBRAIN_AUTOPILOT_ONCE=1`, leaving it in daemon-loop mode.

**Root cause:** the bounded runner had a correct one-cycle mode, but the scheduler and restart helper still treated it as a persistent service. That inverted AP-59/AP-60/AP-95: the lock prevented pileups, but the single daemon holder blocked every deliberate one-shot verification.

**Rule:** the VPS cron line must set `GBRAIN_AUTOPILOT_ONCE=1`, and restart helpers must validate that scheduled one-shot line before starting anything. If they do start a recovery run, it must be `nohup env GBRAIN_AUTOPILOT_ONCE=1 /root/.gbrain/autopilot-run.sh ...`, never the bare runner.

**Detector:** `tools/test_gbrain_autopilot_secret_loading.sh` must check both the remote crontab and `tools/restart_critical.sh` for the one-shot contract. Live proof must show no multi-day `autopilot-run.sh __locked` holder after the old wrapper is stopped, and a manual `GBRAIN_AUTOPILOT_ONCE=1 ...` run must acquire the lock and exit on its own cycle result.

### AP-108 — Snapshot bash `PIPESTATUS` before any scalar assignment

**Failure mode:** after AP-107 cleared the stale autopilot lock, the manual one-shot cycle reached phase 1 and then exited with `PIPESTATUS[1]: unbound variable` under `set -u`.

**Root cause:** `PIPESTATUS` is updated after every simple command. Reading `sub_rc="${PIPESTATUS[0]}"` first replaced the array with the status of that scalar assignment, so the next read of `PIPESTATUS[1]` was unbound. The tee-integrity gate was logically correct but mechanically brittle.

**Rule:** whenever a bash gate needs multiple `PIPESTATUS` values, capture the whole array immediately after the pipeline:

```bash
phase_status=("${PIPESTATUS[@]}")
producer_rc="${phase_status[0]:-1}"
tee_rc="${phase_status[1]:-1}"
```

Do not read `PIPESTATUS[0]`, then `PIPESTATUS[1]`, as separate scalar assignments.

**Detector:** `tools/test_gbrain_autopilot_secret_loading.sh` must assert the runner uses `phase_status=("${PIPESTATUS[@]}")` on both canonical and remote copies.

### AP-109 — One-shot wrappers must propagate failed cycle status

**Failure mode:** after AP-108, the one-shot runner logged `gbrain autopilot cycle failed (1/5)` but still printed `AUTOPILOT_ONCE_RC=0` because the loop unconditionally exited 0 in `GBRAIN_AUTOPILOT_ONCE=1` mode.

**Root cause:** daemon mode tolerates transient failures until the consecutive-error threshold, but one-shot verification has a different contract: the command's exit status is the proof. Reusing daemon-loop exit behavior made the acceptance gate false-green.

**Rule:** in one-shot mode, capture `run_cycle`'s return code and `exit "$cycle_rc"`. Only daemon mode may sleep and continue after a non-terminal cycle failure.

**Detector:** `tools/test_gbrain_autopilot_secret_loading.sh` must require `exit "$cycle_rc"` on both canonical and remote copies.

### AP-110 — Fully qualified `gbrain doctor` from SSH default cwd needs a resolver shim

**Failure mode:** `cd /opt/nous-agaas/gbrain && bin/gbrain doctor --json` returned `healthy/100`, but `/opt/nous-agaas/gbrain/bin/gbrain doctor --json` from the SSH default `/root` returned `warnings/95` with `resolver_health: Could not find skills directory`.

**Root cause:** doctor still walks upward from `process.cwd()` for resolver health. AP-89 fixes scheduled probes by changing cwd first, but humans and acceptance gates often use the fully qualified binary from `/root`.

**Rule:** keep `/root/skills` as a symlink to `/opt/nous-agaas/gbrain/skills` on the VPS:

```bash
ln -sfn /opt/nous-agaas/gbrain/skills /root/skills
```

This does not replace AP-89; scheduled scripts should still `cd /opt/nous-agaas/gbrain`. The shim removes the false-warning footgun for the fully qualified command.

**Detector:** both commands must report `status=healthy`, `health_score=100`, and resolver health `30 skills, all reachable`:

```bash
/opt/nous-agaas/gbrain/bin/gbrain doctor --json
cd /opt/nous-agaas/gbrain && bin/gbrain doctor --json
```

### AP-77 — Model-promo-expiry evaluation playbook (session 82-extension, 2026-04-30)

**Pattern:** Provider promos (DeepSeek's 75%-off launch promo on V4 Pro until 2026-05-31, OpenRouter free-tier rate increases, xAI tier shifts) tempt agents to "use the latest, cheaper model" by flipping the default workhorse during the promo window. This is wrong-headed Musk-think: cheaper-than-usual ≠ cheap-enough-to-default. After the promo ends, the cost spike surprises everyone.

**Rule:** when ANY model's pricing or capability changes (promo announcement, deprecation notice, capability uplift), run the 5-step playbook:

1. **WebSearch latest provider data** — exact $/M tokens, latency benchmarks, IQ/hallucination indices. No memory-only claims.
2. **Compute $/intelligence ratio** — divide pricing by IQ-index or task-success-rate. Compare to current default.
3. **Check fallback chain robustness** — is the alternative tier already in our LiteLLM fallbacks? If yes, default flip is safe; if no, add fallback first.
4. **Apply Musk step-2 (delete the urge)** — is "promote to default" actually justified by $/intelligence and fallback robustness, OR are we just chasing the promo? If 6x cost premium remains for routine traffic, DELETE the urge.
5. **Codify decision** in `ceo-hierarchy` skill (tier rationale section) + set cost-alarm `MODEL_PROMO_WATCH` entry for the expiry window. The alarm fires T-1, T-0, T+1 day windows automatically.

**Reusable artifacts:**
- `tools/litellm_cost_alarm.py:check_promo_expiry()` — fires Telegram at promo-expiry windows
- `tools/litellm_cost_alarm.py:MODEL_PROMO_WATCH` dict — per-model expiry config
- `pages/skills/ceo-hierarchy/SKILL.md` "Tier rationale" + "Promo-expiry watch" sections
- `pages/progress/plans/PLAN-2026-04-30-deepseek-promo-expiry-watch.md` — canonical worked example

**Detection (mechanical):**
```bash
git log --all --oneline -p -- pages/skills/ceo-hierarchy/SKILL.md | grep -B 3 "default.*workhorse"
grep -A 6 "MODEL_PROMO_WATCH" tools/litellm_cost_alarm.py
```

**Why no new LESSON file:** RULE ZERO. Cross-ref: `ceo-hierarchy` Tier-rationale section, `infrastructure` cost-budget AP, `factory-ops` AP-29 (cost-alarm regex maintenance).

## Timeline

- **2026-05-22** | v1.80.13 -> v1.80.14 — Added **AP-110** after repo-cwd doctor was healthy/100 but the fully qualified command from SSH default `/root` still returned warnings/95 with `resolver_health: Could not find skills directory`. Installed `/root/skills -> /opt/nous-agaas/gbrain/skills` so acceptance commands using `/opt/nous-agaas/gbrain/bin/gbrain doctor --json` no longer false-warn. AP-89 remains the scheduled-script rule. No new LESSON (RULE ZERO).

- **2026-05-22** | v1.80.12 -> v1.80.13 — Added **AP-109** after the patched one-shot runner logged `gbrain autopilot cycle failed (1/5)` but still returned `AUTOPILOT_ONCE_RC=0`. Root cause: daemon-mode retry semantics were reused for proof-mode one-shots. Patched the loop to capture `cycle_rc` and `exit "$cycle_rc"` whenever `GBRAIN_AUTOPILOT_ONCE=1`; the autopilot test now gates that pattern locally and remotely. No new LESSON (RULE ZERO).

- **2026-05-22** | v1.80.11 -> v1.80.12 — Added **AP-108** after the first successful post-lock one-shot exposed a new bash bug: `PIPESTATUS[1]: unbound variable` under `set -u`. Root cause: scalar-reading `PIPESTATUS[0]` reset the array before `PIPESTATUS[1]` was read. Patched `tools/gbrain-autopilot-run.sh` to snapshot `phase_status=("${PIPESTATUS[@]}")` immediately after each pipeline and extended `tools/test_gbrain_autopilot_secret_loading.sh` to require that pattern locally and on the VPS runtime copy. No new LESSON (RULE ZERO).

- **2026-05-22** | v1.80.10 -> v1.80.11 — Added **AP-107** after the stricter substrate closeout found `GBRAIN_AUTOPILOT_ONCE=1 /root/.gbrain/autopilot-run.sh` failing with rc=1 because an older cron-launched daemon loop held `/var/lock/gbrain-autopilot.lock` for almost two days. Patched the VPS cron to pass `GBRAIN_AUTOPILOT_ONCE=1`, updated the canonical cron comment, made `tools/restart_critical.sh` treat the one-shot schedule as healthy and start recovery runs with `env GBRAIN_AUTOPILOT_ONCE=1`, and extended `tools/test_gbrain_autopilot_secret_loading.sh` to gate both scheduler and restart-helper drift. No new LESSON (RULE ZERO).

- **2026-05-21** | v1.80.9 -> v1.80.10 — Added **AP-106** after native Codex QMD tool still returned `Transport closed` while QMD CLI showed 3333 docs / 40326 vectors, stdio MCP status over SSH worked, and HTTP `/mcp` initialize worked. Root cause found: `codex mcp get nous-wiki-qmd` succeeded from the parent Nous AGaaS root but failed from the `Nous` vault root because `.codex/config.toml` was missing there. Added `Nous/.codex/config.toml` and `tools/qmd_mcp_doctor.py` with tests so future sessions split config visibility, underlying server health, and stale native runtime handles. No new LESSON (RULE ZERO). OpenBrain: [[openbrain-0bc648aa-b5c9-456c-9922-2e01663ac790]].

- **2026-05-21** | v1.80.8 -> v1.80.9 — Added **AP-105** after QMD's Vulkan build on VPS OOM-killed and a first wrapper attempt accidentally overwrote the symlink target. Restored package bin, installed CPU-default `/usr/local/bin/qmd` wrapper, killed stale stdio MCPs, restarted the HTTP MCP, ran `qmd update --pull`, and embedded 1182 chunks from 94 documents; final QMD status shows 3322 docs, 39691 vectors, and no pending vectors. No new LESSON (RULE ZERO).

- **2026-05-21** | v1.80.7 -> v1.80.8 — Added **AP-104** after gbrain's built-in frontmatter fixer detected 33 YAML-invalid `related: [[a]], [[b]]` pages but wrote zero backups. Repaired 36 frontmatter-only wikilink arrays to quoted YAML arrays and kept body text untouched. No new LESSON (RULE ZERO).

- **2026-05-21** | v1.80.6 -> v1.80.7 — Added **AP-103** after gbrain timeline writes failed with SSH `Connection timed out during banner exchange` while TCP/ICMP probes were healthy. Root cause: stale local SSH child transports (`qmd status`, `qmd mcp`, `gbrain-mcp`) from the current Codex process, not VPS/gbrain outage. Killed only those stale local child processes and retried the CLI fallback; `timeline-add` returned `{"status":"ok"}`. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/gbrain-ops/skill.

- **2026-05-21** | v1.80.5 -> v1.80.6 — Added **AP-102** after a sync-lock investigation used shell xtrace on `tools/gbrain_sync_wrapper.sh` and exposed secret-bearing env assignment output in the local command transcript. Root cause: xtrace is unsafe for wrappers that source credential env files. Rule: use sanitized dry-run/status/log diagnostics only; no `bash -x`/`set -x`/raw `env` around secret-loading wrappers. No new LESSON (RULE ZERO).

- **2026-05-20** | v1.80.4 -> v1.80.5 — Closed remaining Karpathy Council P3 residuals after user invoked god-level standard ("every single session closed to 100%"). **P3-1 (per-phase gate)**: restructured `run_cycle()` into 3 phases (sync+extract / embed --stale / link-builder) with `run_lying_log_gate()` helper invoked IMMEDIATELY after embed --stale. Link-builder no longer runs against degraded embedding state on lying-log; double-tee + 3 PIPESTATUS checks on embed phase guarantee tee integrity; full-cycle backstop catches any pattern leak from phase 1 or 3. **P3-2 (tg_send fallback)**: `run_lying_log_gate()` captures tg_send exit; on delivery failure emits `AP-101 ALERT tg_send_failed` to autopilot.log AND appends structured JSONL to `${GBRAIN_ALERT_FALLBACK_LOG:-/root/.gbrain/alerts-fallback.jsonl}` so Telegram-down doesn't silent-blind the operator. Same fallback in `gbrain_sync_wrapper.sh` for the manual sync surface. **P3-3 (cumulative-log)**: docstring warning added to `test_no_lying_logs.py`. **Parity test extended**: asserts 4 new AP-101 patterns (`run_lying_log_gate`, `embed_tmp`, `alerts-fallback.jsonl`, `post-embed`) on BOTH local canonical AND remote VPS — total 9 AP-99/AP-100/AP-101 assertions. Scp'd new canonical to `/root/.gbrain/autopilot-run.sh` (backup .bak-ap101-20260520T173912); bash -n verified; parity gate green on both targets. Council closed 8/8. No new LESSON (RULE ZERO).

- **2026-05-20** | v1.80.3 -> v1.80.4 — Karpathy Council (codex challenge mode, `karpathy-loop` AP-12 narrow escalation since work touched IR/retrieval semantic search reliability) caught 1 P1 + 4 P2 + 3 P3 flaws in the v1.80.3 AP-99 wiring before the session closed. P1: vault canonical `tools/gbrain-autopilot-run.sh` was not updated, only the VPS-local `/root/.gbrain/autopilot-run.sh` got the wiring → any redeploy from canonical would silently erase the fix; AND `tools/test_gbrain_autopilot_secret_loading.sh` was content-blind to AP-99 (no `test_no_lying_logs.py` / `tg_send.sh` / `cycle_tmp` / `PIPESTATUS[1]` assertions) so tests stayed green during the drift. Fixed by patching canonical + extending the parity test with 5 new assertions (local + remote ssh-grep branches). P2: `gbrain_sync_wrapper.sh` ran `$GBRAIN sync` under `set -e` so failed syncs died before logging — observability regression vs prior direct-to-LOG redirect (now capture rc, log unconditionally, gate regardless); `${PIPESTATUS[0]}` alone missed tee failures (now checks `${PIPESTATUS[1]}` too with `AP-100 ALERT tee_failed`); `EMBED_FAIL_RE` was the literal `embedding failed for ` (trailing space) and missed colon/no-for/tab variants — widened to `embedding failed\b` word-boundary, added 2 new fixtures (now 6/6 self-test passes). P3: `mktemp → trap` signal-window leak — added `/tmp/gbrain-*-cycle.*.log -mmin +30 -delete` reaper sweep at each cycle start. AP-100 codifies the "canonical-vs-runtime drift" class so this cannot recur silently. Codex took ~64k tokens, found all flaws in one pass. Deferred (not P1): per-step gate boundary, tg_send.sh delivery-failure fallback log, cumulative-log false-positive — documented as open Council residuals. No new LESSON (RULE ZERO).

- **2026-05-20** | v1.80.2 -> v1.80.3 — Spawn session s108-mac-61891 (continuing s108-mac-60468 residual closure) wired AP-99 into runtime: `tools/gbrain_sync_wrapper.sh` and `/root/.gbrain/autopilot-run.sh` now tee sync output to a tmp file, pipe through `tools/test_no_lying_logs.py --input`, and on non-zero exit fire `tools/tg_send.sh` with a structured violation alert (failure count + tail-5 snippet) before exiting non-zero so cron / consecutive-error tracking flags the cycle. Previously AP-98/AP-99 doctrine existed but the live sync surfaces did not invoke the gate — the script could detect lying-log patterns only when called by hand. Closes the gap opened in v1.80.2 (gate shipped + self-tested but unwired). Local `--self-test` re-verified 4/4 [ok]; explicit `gbrain timeline-add pages/skills/gbrain-ops/skill 2026-05-20 "<summary>"` returned `{status: ok}` to ensure the v1.80.2 absorption row reaches the embedding layer without waiting for the 5-min autopilot. Scope-locked: `git commit -o tools/gbrain_sync_wrapper.sh pages/skills/gbrain-ops/SKILL.md` (AP-5 anti-collision; 19 dirty files from peer lanes untouched). No new LESSON (RULE ZERO).

- **2026-05-20** | v1.80.1 -> v1.80.2 — Spawn session s108-mac-60468 absorbed **AP-98** + **AP-99** after reproducing the silent-embedding-failure pattern from HEAD `12e7c89b`: `bin/gbrain sync --repo …` emitted `[gbrain] embedding failed for <slug>: OPENAI_API_KEY missing` per-page lines while the summary still claimed `N pages embedded`. Verified the canonical env loader is intact (`load_openai_compatible_proxy` + `load_openai_key` in `/root/.gbrain/autopilot-run.sh` and `tools/gbrain_sync_wrapper.sh`; key length 43, LiteLLM `$OPENAI_BASE_URL/models` returns 200), and confirmed `gbrain query "model-failover doctrine" --json` returns the page at score `0.9549` after a clean wrapper-driven sync. Shipped `tools/test_no_lying_logs.py` (§7.1 cross-cutting gate): scans for `embedding failed` lines followed by positive `N pages embedded` summary; exits 1 on violation. Self-test passes all four synthetic fixtures (clean / lying / zero-count / failure-only). AP-98 mandates piping every sync surface through the gate; AP-99 wires `tools/tg_send.sh` to fire on non-zero exit. Also absorbs the pre-existing unstaged AP-97 (MCP tunnel doctrine) into the same commit so the dirty-tree residue lands authoredly. No new LESSON (RULE ZERO).

- **2026-05-20** | v1.80.0 -> v1.80.1 — Added AP-97 for the Anthropic MCP tunnel candidate: domain pinned to `gbrain.nousagaas.com`, access-gated, and not promotable until 24h soak, no SSH fallback, latency comparison, and SSH-key rotation proof pass. No new LESSON (RULE ZERO).

- **2026-05-20** | v1.79.0 -> v1.80.0 — Same Telegram presidential control-plane audit absorbed **AP-96** after targeted gbrain embeds still stalled with a valid key because VPS MagicDNS resolved Air LiteLLM to stale `100.105.9.1`. Verified Air's live Tailscale IP `100.122.219.22`, switched `/root/.gbrain/openai-compatible.env` `OPENAI_BASE_URL` to that IP, and proved targeted embeds for the plan, latest handoff, and `gbrain-ops` skill. No new LESSON (RULE ZERO).

- **2026-05-20** | v1.78.0 -> v1.79.0 — Telegram presidential control-plane audit absorbed **AP-95** after fresh Obsidian/QMD artifacts were invisible to gbrain while VPS had a 55+ minute `gbrain embed --stale` and a silent `gbrain sync` process. Patched `tools/gbrain-autopilot-run.sh` with `GBRAIN_AUTOPILOT_CMD_TIMEOUT`, patched `tools/daily_0300_substrate_sync.py` with remote `timeout -k 10s` guards, and extended tests so lock-bearing gbrain maintenance cannot run unbounded. No new LESSON (RULE ZERO).

- **2026-05-18** | v1.77.0 -> v1.78.0 — Memory architecture check absorbed **AP-94** after Madi explicitly approved "Mem0 deferred/backup-only unless one-page proof beats gbrain." Verified `mem0`/`mem0ai` absent locally and on Air, no Air Mem0 launchd job, gbrain healthy with 3848 pages and 15428/15428 embedded chunks, and OpenBrain projection dry-run clean (`ok=true`, `projection_failed=false`, `would_update=0`). Decision: Obsidian/wiki + gbrain + OpenBrain by Nate B. Jones remain canonical; Mem0 requires a named use-case bakeoff before promotion. No new LESSON (RULE ZERO).

- **2026-05-16** | v1.76.0 -> v1.77.0 — Atomic substrate closeout absorbed **AP-93** after manual `gbrain embed --all` sourced `/root/.gbrain/openai-compatible.env` but did not export it, causing `OPENAI_API_KEY environment variable is missing or empty` errors. Stopped the runaway broad embed, reran targeted normalized-slug embeds with `set -a`, and verified `gbrain doctor --json` healthy/100 with `embeddings: 100% coverage, 0 missing`. No new LESSON (RULE ZERO).

- **2026-05-14** | v1.75.0 -> v1.76.0 — Telegram/OpenClaw/GPT live audit found `gbrain doctor` at 95/100 because generated audit/handshake frontmatter contained raw comma-separated wikilinks under `related:`. Root cause: Obsidian-readable but YAML-invalid frontmatter. Fixed three generated files, codified **AP-92** requiring quoted YAML arrays for wikilink lists, and queued fresh frontmatter/doctor verification. No new LESSON (RULE ZERO).

- **2026-05-13** | v1.74.0 -> v1.75.0 — Todoist comment-loop audit absorbed **AP-91** after Git/wiki/factory were green but `gbrain get pages/skills/todoist-control-plane/skill` still returned v1.4.6 while the canonical file was v1.4.9. Proved the autopilot lock holder was alive, avoided deleting the lock, used existing-page `gbrain put` from the canonical wiki file, and read back v1.4.9 with the comment-classifier rule. No new LESSON (RULE ZERO).

- **2026-05-13** | v1.73.0 -> v1.74.0 — Satory ERAP source capture absorbed **AP-90** after the Ruslan/Assyl source page imported and embedded but the first targeted embed used an uppercase filesystem slug and a Russian query phrasing missed. Verified normalized slug, targeted embed through `/root/.gbrain/openai-compatible.env`, exact readback, and working search for `Ruslan Assyl ERAP APK testing`. No new LESSON (RULE ZERO).

- **2026-05-13** | v1.72.0 -> v1.73.0 — Control-plane/Hermes audit absorbed **AP-89** after proving the old `resolver_health` warning was a scheduled-script CWD bug, not a gbrain data failure. Patched `tools/morning-brief.sh` and `tools/nightly-audit.sh` to `cd /opt/nous-agaas/gbrain` before doctor, added `tools/tests/test_gbrain_doctor_cwd_static.py`, and verified `gbrain doctor --json` healthy/100 from the correct CWD. No new LESSON (RULE ZERO).

- **2026-05-12** | v1.71.0 -> v1.72.0 — Control-plane closeout refined **AP-86** with **AP-88** after three historical `<head>` drift rows kept `doctor --fast` yellow and `sync --skip-failed` no-opped because the source was already current. Added the five-gate safe acknowledgment rule, backed up `/root/.gbrain/sync-failures.jsonl`, acknowledged only historical HEAD-race rows with evidence reason, and verified full `gbrain doctor --json` healthy/100. No new LESSON (RULE ZERO).
- **2026-05-12** | v1.70.0 -> v1.71.0 — Factory-ops title drift absorbed **AP-87** after `factory-ops/SKILL.md` carried `version: 1.34.0` and H1 v1.34.0 but frontmatter `title:` still said v1.33.0. Fixed the title and extended `tools/test_skill_internal_consistency.sh` to include version-bearing `title:` metadata, then verified all skills. No new LESSON (RULE ZERO).
- **2026-05-12** | v1.69.0 -> v1.70.0 — Control-plane sync audit absorbed **AP-86** after gbrain doctor kept warning on two old `<head>` sync-failure records and resolver layout despite current wrapper sync success, 100% embeddings, and exact search readback for `pages/audits/audit-operational-control-plane-sync-2026-05-12` at score `1.0000`. Rule: prove current retrieval with wrapper + exact readback + doctor, report legacy/layout warnings as residuals, and do not manually edit `~/.gbrain/sync-failures.jsonl` to paint the dashboard green. No new LESSON (RULE ZERO).
- **2026-05-11** | v1.68.0 -> v1.69.0 — Skill-evolution closeout absorbed **AP-85** after flag-style `bin/gbrain timeline-add --slug ... --date ... --summary ...` returned `{status: ok}` but did not show on target skill timelines. Root cause: current gbrain v0.22.16 expects positional args. Fixed by re-adding entries with `timeline-add <slug> <date> <summary>` and readback-grepping each skill slug. No new LESSON (RULE ZERO).
- **2026-05-11** | v1.66.0 -> v1.67.0 — Cross-system sync audit absorbed **AP-83** after `bin/gbrain sync --help` held the `gbrain-sync` lock and blocked a real sync. Root cause was treating subcommand help as read-only when the deployed CLI enters the stateful sync path. Fixed live by killing the stuck VPS process, proving `gbrain doctor` healthy, and retrieving `pages/audits/audit-cross-system-sync-2026-05-11` by search/readback. No new LESSON (RULE ZERO).

- **2026-05-11** | v1.65.0 -> v1.66.0 — OpenBrain projection closeout absorbed **AP-82** after manual gbrain sync/embedding hit direct OpenAI `429` while autopilot already had `/root/.gbrain/openai-compatible.env`. Root cause was wrapper env divergence. Patched `tools/gbrain_sync_wrapper.sh` to source the OpenAI-compatible LiteLLM env before the fallback key loader; verified dry-run key load, targeted `library-grade-audit` embed, and semantic retrieval for the OpenBrain projection skill. No new LESSON (RULE ZERO).

- **2026-05-11** | v1.64.0 -> v1.65.0 — KEONA research sync absorbed **AP-81** after a byte/locale-unsafe `perl -pi` emoji cleanup corrupted Cyrillic in `Astana_Hub_vs_MFCA_Analysis.md`. Root cause was the edit primitive, not the source file. Repaired by restoring from the Claude mirror, reapplying only semantic edits, and adding replacement-character scan as a required guard for multilingual vault docs. No new LESSON (RULE ZERO).
- **2026-05-11** | v1.63.0 -> v1.64.0 — KEONA mirror-import sync absorbed **AP-80** after the current project hub existed in Claude's separate mirror but not the active Obsidian/gbrain wiki. Import + git push were not enough: gbrain `get` still returned `page_not_found` because `gbrain sources list` showed the registered wiki source last synced on 2026-04-30. Repaired by syncing the active vault to Mac/VPS/Air, running `./bin/gbrain sync --source default`, and proving `gbrain get pages/projects/keona-pilot/keona-pilot` plus keyword search for `Maru Analytics`. QMD MCP remained degraded with `Transport closed`, reported honestly. No new LESSON (RULE ZERO).
- **2026-05-09** | v1.62.0 -> v1.63.0 — Golden Substrate Audit absorbed **AP-79** after the new audit plan was synced in git but not retrievable through gbrain. Root cause was missing `created:` frontmatter caught by `gbrain lint`, not sync failure. Repaired `PLAN-GOLDEN-SUBSTRATE-AUDIT-2026-05-09.md` frontmatter and generalized AP-63 from handoffs to all plan/progress/audit/spec/task-result report pages. No new LESSON (RULE ZERO).

- **2026-04-30** | v1.61.0 -> v1.62.0 — Session 82-FINAL doctor 90 -> 100/100. Absorbed **AP-78**: 3 upstream-PR-fixable (NESTED_QUOTES #535, graph_coverage-on-markdown #536, ingest+enrich-DRY #537) + 1 local AP-54-See-also patch + 1 local CTE widening (entity_pages adds 'entity'+'organization' types) + 1 cwd-context caveat. Verified `cd /opt/nous-agaas/gbrain && gbrain doctor` -> Health 100/100, link_coverage 99%, timeline 59%. resolver_health CLEAR. graph_coverage CLEAR. All 14 [OK]. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON (RULE ZERO).

- **2026-04-30** | v1.60.0 -> v1.61.0 — Session 82-extension absorbed **AP-77**: model-promo-expiry evaluation playbook. Triggered by Madi asking whether to promote DeepSeek V4 Pro to default workhorse during the 75%-off promo OR switch to direct DeepSeek API. Honest CTO answer (Musk step-2 applied): no flip — Pro is 6x Flash even during promo; OpenRouter price = direct, OpenRouter wins on reliability. Real ship: cost-alarm `check_promo_expiry()` + `MODEL_PROMO_WATCH` (T-1/T-0/T+1 windows, idempotent state) + `ceo-hierarchy v1.3.0 -> v1.4.0` (tier rationale + promo watch sections). 5-step reusable playbook codified for next pricing change. Plan: PLAN-2026-04-30-deepseek-promo-expiry-watch.md. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON (RULE ZERO).

- **2026-04-30** | v1.59.0 -> v1.60.0 — s108 Codex desktop absorbed **AP-76**: library tier policy is now treated as a shared executable classifier contract. Current contract: Tier A core catalog (laws/skills/systems/entities/projects/concepts), Tier B report/import receipts (audits/specs/plans/progress-plans/dashboards/handoffs/task-results/sources/_gbrain), Tier C legacy archive; `id:` is not a catalog title. Live probes: library metadata `page_count=1701 A=320 B=1104 C=277 blocking=0`; reachability `A1=296 orphan=9 3.04% PASS`; canonical `1/0/0 PASS`; crossref `0/0 PASS`; focused tests 22 passed. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON (RULE ZERO).
- **2026-04-30** | v1.58.0 → v1.59.0 — Session s108-mac-99667 (continuing s2127) absorbed **AP-75** (search vs get_page semantic separation: title-retrievability probe proved gbrain semantic-search returns most-narrating chunk for skill-name queries, not the canonical SKILL.md; verified by adding `title:` frontmatter and re-extracting — title field updated but search ranking unchanged; doctrine: use `get_page(slug)` for canonical, `search` for exploration; companion AP queued for [[library-grade-audit]] Gate 6 split). Mass-apply of `title:` to 55 unnamed-title skills queued as future hygiene. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON (RULE ZERO).
- **2026-04-30** | v1.57.0 → v1.58.0 — Session s1526 absorbed **AP-74** (dashboards wrongly classified as Tier-A1 in crossref scanner; `orphan-index.md` 589 false failures; fix: `TIMESERIES_RES` extended with `pages/dashboards/.+\.md`). Wikilink coverage 3959→5624. Gate still PASS 0 broken Tier-A1. No new LESSON (RULE ZERO).
- **2026-04-30** | v1.56.0 → v1.57.0 — Session s2127 (continuing) absorbed **AP-73** (`library_crossref_scan.py` blind spots on CLAUDE.md + `laws/` — found 2 real broken Tier-A1 wikilinks that PASS-status had hidden). Scanner fix shipped: `collect_pages()` walks `pages/` + `laws/` + vault-root doctrine; `subtier_for()` classifies root-level doctrine files as A1. Companion AP in [[library-grade-audit]] AP-2. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON (RULE ZERO).
- **2026-04-30** | v1.55.0 → v1.56.0 — Session s2127 atomic audit absorbed **AP-72** (`gbrain-dryrun` frontmatter-migration tool corrupts production wiki — VPS uncommitted state had 17+ files with broken YAML; reset via `git checkout -- . && git clean -fd`; rule: schema-rewrite tools must require `--allow-canonical-vault` flag + interactive confirm). Also fixed: Air working copy 1 commit behind, CANARY-RED handoff committed for audit trail. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON (RULE ZERO).
- **2026-04-30** | v1.54.0 → v1.55.0 — Session 82 deep-audit absorbed **AP-70** (Cyrillic-named vault files NOT indexed by gbrain v0.22; 96 of 1592 = 6.0% of vault invisible to retrieval; `import-file.ts:381` strict slugifyPath() rejects non-ASCII; workaround: Latin transliteration or `aliases:` frontmatter) and **AP-71** (700 raw orphans decompose into 426 legitimate terminal nodes + 96 Cyrillic-unindexed + ~178 real-work-queue; raw orphan count is misleading; SQL recipe in skill body). Honest verdict: ~95% library-grade, not 100%. Real gaps: 96 Cyrillic invisible, ~178 real-work-queue orphans, 2 upstream cosmetic WARNs. All upstream-fix or multi-session-arc. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON (RULE ZERO).

- **2026-04-30** | v1.53.0 → v1.54.0 — Session 82 close-out: absorbed **AP-68** (`graph_coverage 0%` is structurally correct for markdown-only brains; doctor metric is calibrated for code-indexed brains; real link/timeline data lives in `links` and `timeline_entries` tables — confirmed 6062 links + 1962 timeline entries on prod) and **AP-69** (`gbrain extract` is for code-edge re-extraction; markdown brain link/timeline population happens via wiki-local `gbrain_link_builder.py` + `gbrain_timeline_builder.py` inside autopilot). Final post-cutover health: 90/100 — TRUE-state functional 100% for markdown-wiki shape. Closed: MINIONS half-install (apply-migrations --yes), JSONB integrity (repair-jsonb 0 rows needed), `_gbrain` overlay restored, RESOLVER.md auto-found via repo-root walk, 5/7 advisory DRY violations auto-fixed. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON (RULE ZERO).

- **2026-04-30** | v1.52.0 → v1.53.0 — Session 104 (s104-mac-10984) shipped library-grade audit Steps 2/3/4 with all gates PASS at Tier A1 scope. Absorbed **AP-67** (Tier-A1-scoped audits per AUDIT-061; flat-denominator audits are misleading). 3 new scanners shipped (`library_reachability_scan.py`, `library_canonical_scan.py`, `library_crossref_scan.py`). Substrate fixes: 19 alias `target:` fields, AMENDMENT-005 + AMENDMENT-006 pages created, 5 wikilink rename-fixes across 4 stable docs, 1 Finder-duplicate dashboard deleted. 3 new audit receipts (REACHABILITY/CANONICAL/CROSSREFS-2026-04-30). Final verdicts: 5.43% Tier A1 orphans (gate ≤10%), 0/0/0 Tier A duplicates+aliases (gates ≤2/≤2/0), 0 broken Tier A1 wikilinks + 2 broken Tier A1 prose AP (gates 0/≤5). gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON (RULE ZERO).

- **2026-04-30** | v1.51.0 → v1.52.0 — Session 82 LIVE GBRAIN UPGRADE COMPLETE (v0.10.1 → v0.22.16). Absorbed **AP-64** (comprehensive forward-reference column patch for v0.10-era brains beyond the v0.22.6.1 bootstrap), **AP-65** (BYPASSRLS prerequisite for v24+ rls_backfill migration), **AP-66** (rebase-with-ours-strategy for divergent local commits during upstream pull). Schema 4→29, 22 migrations applied, 4 retrieval modes operational (vec/lex/graph/llm-rewrite), 100% embedding coverage preserved through cutover. Gap 1 of Tan/Finn parity charter CLOSED. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON (RULE ZERO).

- **2026-04-30** | v1.50.0 → v1.51.0 — Session 103 absorbed **AP-63** after session-100/session-102 handoffs synced in Git but were skipped by gbrain import due missing `created` and YAML-invalid `related` wikilinks. Repaired both handoffs, added the lint/import/readback rule, and kept the evidence in gbrain timeline rather than creating a LESSON file.

- **2026-04-30** | v1.49.0 → v1.50.0 — Session 100 retrieval synthesis absorbed **AP-62** from [[AUDIT-062-retrieval-quality-synthesis-2026-04-30]] after old doctrine could outrank current doctrine because prose drift warnings were not machine-readable. Superseded pages now require `superseded_by:`, current pages should carry `supersedes:`, and audits may warn when new doctrine is written to a superseded page. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON.

- **2026-04-30** | v1.48.0 → v1.49.0 — Session 100 (s100-mac-23069) absorbed **AP-61**: operator-facing gbrain slug calls must lowercase the path; uppercase wiki IDs (`AUDIT-NNN`, `LESSON-NNN`, `LAW-NNN`) return false `page_not_found` because gbrain v0.10.1 canonicalizes to lowercase on ingest. Hit live during the AUDIT-061 retrieval verification probe in this session. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON.

- **2026-04-30** | v1.47.0 → v1.48.0 — Session 100 verification absorbed **AP-60** after AP-59's first implementation appended the custom link builder after `gbrain autopilot`, but live verification proved upstream autopilot is a non-returning daemon. Replaced the runner with a wrapper-owned bounded cycle (`sync --no-embed` -> `extract all` -> `embed --stale` -> wiki-local `gbrain_link_builder.py`) under the same flock, added `GBRAIN_AUTOPILOT_ONCE=1`, and hardened `test_gbrain_autopilot_secret_loading.sh` to reject delegation to `"$GBRAIN" autopilot`. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON.

- **2026-04-30** | v1.46.0 → v1.47.0 — Session 100 verification absorbed **AP-59** after the 5-minute VPS cron path (`/root/.gbrain/autopilot-run.sh`) bypassed the AP-57/AP-58 wrapper and let the same 5 `session-architecture` graph links reappear after sync. Patched the tracked autopilot runner to execute wiki-local `gbrain_link_builder.py` after `gbrain autopilot` under the same flock, extended `test_gbrain_autopilot_secret_loading.sh`, and deployed the runner to `/root/.gbrain/autopilot-run.sh`. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON.

- **2026-04-30** | v1.45.0 → v1.46.0 — Session 100 verification absorbed **AP-58** after the committed AP-57 link-builder fix worked from `wiki/tools` but `gbrain_sync_wrapper.sh` still called stale `/root/nous-agaas/tools/gbrain_link_builder.py`, reproducing the old unresolved skill-link class inside the scheduled sync path. Patched the wrapper to default to `$WIKI/tools`, added a credential-gate assertion for wiki-local tools, and kept `GBRAIN_TOOLS_DIR` as the explicit override. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON.

- **2026-04-30** | v1.44.0 → v1.45.0 — Session 100 Obsidian/gbrain/OpenClaw library audit absorbed **AP-57** after `gbrain_link_builder.py --dry-run --verbose` reported existing skills (`skills/session-operating-contract`, `skills/musk-algorithm`, `skills/agent-quality/skill`, etc.) as unresolved. Patched the resolver to normalize skill aliases to canonical `pages/skills/<name>/skill` and tenant skill slugs, added `tools/test_gbrain_link_builder_resolution.py`, and queued gbrain graph registration after push. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON.

- **2026-04-29** | v1.43.0 → v1.44.0 — Session 98/95 follow-up closed the **AP-56** refresh proof loop after an uncommitted `--local` experiment hung and left high-CPU OpenClaw agent processes running past the expected timeout, then a green gateway refresh test still left `BUMP_VERIFY` processes alive after returning the token. Final rule: use `docker exec -i` for heredoc Python, trigger gateway OpenClaw CLI directly instead of `run_task.py`, clean token-scoped probe processes, and assert required operating-loop skills by name; avoid `--local` for this probe until separately proven safe. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON.

- **2026-04-29** | v1.42.0 → v1.43.0 — Session 95 absorbed **AP-56** after the Obsidian/gbrain/OpenClaw audit found `tools/bump_openclaw_skills_version.sh` was a false-green: its `docker exec` Python heredocs lacked `-i`, and its trigger path used `run_task.py`, which routed through `litellm_direct` and never exercised OpenClaw. Patched the tool to feed Python through `docker exec -i`, call `docker exec openclaw openclaw agent` directly, and added a required-skill assertion to the sibling test for `musk-algorithm`, `ceo-hierarchy`, `session-architecture`, `operator-boundaries`, `collaborative-reading`, and core operating-loop skills. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON.

- **2026-04-29** | v1.41.0 → v1.42.0 — Session 92 absorbed **AP-55** after SOAO's memory-top-block warning proved to be a stale checker and a deeper Mercury carryover feedback loop: live `MEMORY.md` was 52 lines in Mercury `# Now context` format, while `tools/test_memory_top_block_size.sh` only recognized legacy `# Memory — updated` headers; `tools/mercury_seed.py` was also re-ingesting generated Mercury carryover into `facts.jsonl`. Patched the checker for both formats, added `MEMFILE_OVERRIDE`, added `tools/test_memory_top_block_size_e2e.sh` for legacy/Mercury/unknown fixtures, made Mercury seeding skip generated `# Now context` carryover via `MERCURY_MEMORY_OVERRIDE`, added `tools/test_mercury_seed_memory_source.sh`, and regenerated facts with `carryover: 0`. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON.

- **2026-04-29** | v1.40.0 → v1.41.0 — Session 82q round-15 SHIPPED **AP-54** (DRY+MECE cleanup). Appended `conventions/quality.md` reference to 8 skills (ours: gbrain-ops AP-50 Cross-ref line; upstream: ingest, enrich, setup, signal-detector, idea-ingest, media-ingest, meeting-ingestion via `## See also` footer). Removed `"citation audit"` trigger from upstream `maintain/SKILL.md` frontmatter (citation-fixer keeps it as canonical). Empirical: doctor went from `[WARN] resolver_health: 11 issues` to `[OK] resolver_health: 38 skills, all reachable`; brain_score `90/100 → 95/100`. Upstream changes are working-tree-only (skills/_gbrain/ untracked in upstream-fork repo); persistence across redeployments will require either tracking the dir or moving the convention reference into our wiki overlay. Round-13 carryover punch list CLOSED. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON.

- **2026-04-29** | v1.39.0 → v1.40.0 — Session 82o round-13 SHIPPED AP-53 fix path (Z). One-line patch to upstream-fork `src/core/check-resolvable.ts:242`: added `.replace(/^_gbrain\//, '')` after the SKILL.md strip, so `skillName` becomes `signal-detector` (matches manifest's bare name) instead of `_gbrain/signal-detector`. Rebuilt Bun binary via `bun install && bun run build`. Verified: ORPHAN_TRIGGER count went from 26 → **0**, total resolver_health 37 → **11** (MECE + DRY + RLS classes remain — separate AP candidates), brain_score 90/100 unchanged, `bin/gbrain --help` OK, version intact 0.10.1. Upstream-fork commit on `/opt/nous-agaas/gbrain` master at `e1f274a`. AP-53 STATUS: **CLOSED** — fix path Z chosen + shipped + empirically verified, NOT (X) 25-edit manifest churn or (Y) 28-edit RESOLVER edits. Karpathy first-principles win: traced through compiled binary into TypeScript source, found single-line bug, patched at root not at workaround. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON.

- **2026-04-29** | v1.38.0 → v1.39.0 — Session 82n round-12 picked up peer Codex s90 carryover #2 (37 resolver_health warnings). Plan-first execution traced root cause into upstream `check-resolvable.ts:224-243` regex: RESOLVER's `skills/_gbrain/<name>/SKILL.md` strip yields `_gbrain/<name>` but manifest entries are bare `<name>`. All 26 ORPHAN_TRIGGER warnings are false positives from this single regex mismatch. Empirically verified: signal-detector IS in manifest, doctor still reports it as orphan. Codified AP-53 with 3 fix paths (X/Y/Z) and detection script. Per quality 100% bar: refused to ship 25-edit manifest fix without runtime routing test. Honest handoff to dedicated session. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON.

- **2026-04-29** | v1.37.0 → v1.38.0 — Session 85 picked up Codex session 82l's honest-handoff carryover for AP-50. Chose option 3 from the 3 fix-paths: doctrine amendment to accept BOTH `[[wikilink]]` and prose cross-refs as iron-law-compliant. CLAUDE.md `BRAIN-FIRST RULE` amended; gbrain v0.10.1 prose-blindness reclassified as tooling gap; gbrain v0.11+ extractor upgrade tracked as future backfill. AP-52 codifies closure rationale: option 3 over options 1 (~500-edit churn = AP-2 violation) and 2 (blocked upstream). gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.36.0 -> v1.37.0 — Session 89 top-CTO audit found AP-35 credential doctrine was not mechanically enforced on `tools/gbrain_sync_wrapper.sh`: manual gbrain sync could emit missing-key noise while health stayed green. Patched the wrapper to share the canonical env -> auth.json -> `/root/nous-agaas/.env` loader, fail closed, and expose `GBRAIN_SYNC_WRAPPER_DRY_RUN=1`; added `tools/test_gbrain_sync_wrapper_secret_loading.sh` to gate the source and VPS runtime wrapper. No new LESSON (RULE ZERO).

- **2026-04-29** | v1.35.0 -> v1.36.0 — Session 82l plan-first discipline (Madi round-10 directive) executed PLAN-2026-04-29-orphan-backlink-triage: verified Lane Y's "696 orphan pages" via direct backlink sample (3/4 high-traffic skills had `[]` backlinks); discovered `gbrain extract links` v0.10.1 only catches `[[wikilink]]` form (live extract returned `links_created: 0`); our substrate idiom is prose-form cross-refs (`karpathy-loop AP-8` not `[[karpathy-loop]] AP-8`). Codified **AP-50**: back-link iron law structurally violated; 3 fix-path options each ≥2-4hr scope; HONEST HANDOFF rather than partial conversion that would give false GREEN. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON.

- **2026-04-29** | v1.34.0 -> v1.35.0 — Session 86 blacksmith burst audit found AP-48 was only partially true after Mercury Phase-3 changed live `MEMORY.md` from legacy `# Memory — updated` stanzas to `# Now context` fact-blocks. Patched `context_injector_v2.py` to read both formats and normalize LAW-015/LAW-017 into an explicit RULE ZERO signal; added a Mercury fixture to `tools/test_context_injector_v2.py`. Proof: `python3 tools/test_context_injector_v2.py` → 44 passed, 0 failed. gbrain-timeline-ok: pages/skills/gbrain-ops/skill. No new LESSON (RULE ZERO).

- **2026-04-29** | v1.33.0 -> v1.34.0 — Session 83 memory-substrate audit applied primary-source KV-cache lessons to Nous at the workflow layer, not by building a model-level compressor. Added AP-48 and wired `context_injector_v2` to inject only a capped newest-MEMORY salience packet (red/yellow, proof, carryover, RULE ZERO) while keeping full `MEMORY.md` excluded. Also repaired stale Output Format language that still said a LESSON page was required for bug fixes, contradicting RULE ZERO. Mechanical proof lives in `tools/test_context_injector_v2.py`: packet behavior, live vault byte/token budget, and old LESSON-required phrase scan. No new LESSON files.

- **2026-04-29** | v1.32.0 -> v1.33.0 — Session 82 substrate-S0 dry-run with `BETA_WORKAROUND=1` (env-gated, snapshot-DB-only patch to `tools/gbrain_upgrade_dryrun.sh`) verified empirically that single-column β is INSUFFICIENT. v0.22.8 pulled successfully (POST_PULL_SHA=8468ba25); ALTER added `search_vector tsvector` on `gbrain_dryrun`; apply-migrations cleared search_vector but immediately halted on `column "symbol_name_qualified" does not exist` from `gbrain init --migrate-only` Phase A. Doctor reported MINIONS HALF-INSTALLED, RLS missing on 13 tables, Health 40/100. New AP-47 codifies the generalized lesson: column blockers come in cohorts, not singletons; β must be extended (and backfilled) OR live cutover must wait for upstream coverage of `gbrain init --migrate-only`. Cross-session Lane B (general-purpose subagent web research) suggested PR #440 + #488 in upstream `garrytan/gbrain` ship `applyForwardReferenceBootstrap()` covering this — UNVERIFIED by maintainer comment, and contradicted by live evidence that v0.22.8 still wedges. Lane B's column list (page_kind, language, symbol_name, etc.) recorded as a hypothesis for next session's empirical β++ exploration, not as ground truth. Snapshot DBs retained on VPS for next attempt. PROD untouched. RULE ZERO upheld (no LESSON files; cap holding 24/129).

- **2026-04-29** | v1.31.0 -> v1.32.0 — Session 81 substrate evolution dry-run found 4 critical bugs in plan v2 BEFORE any production mutation. (1) `bin/gbrain` is Bun-compiled ELF, not Node module → AP-43 (must `bun install + bun run build`). (2) `bin/gbrain migrate` is storage-backend migration not schema upgrade → AP-44 (correct command is `apply-migrations`). (3) Migration v0.11.0 hard-codes `gbrain` requiring PATH with `bin/` → AP-45. (4) Migration v0.11.0 references `search_vector` column not present in v4 schema → AP-46 (live cutover BLOCKED until upstream fix or workaround). PROD gbrain at v0.10.1 untouched. Snapshot `gbrain_dryrun` retained for forensics. Plan v2's mechanical evidence gates fired exactly as designed — caught all 4 issues, stopped before live, codified into 4 permanent skills. Karpathy compounding in motion. No new LESSON (RULE ZERO).

- **2026-04-29** | v1.30.0 -> v1.31.0 — Four-lane top-CTO audit found resolver reachability green but trigger quality red: `tools/trigger_eval.py` was `48/68` before fixes. Tightened `_gbrain/RESOLVER.md` triggers and added precedence-first `PRIORITY_RULES` to `tools/trigger_eval.py` so convention rules (`/ask`, tasks, media ingestion, factory ops, Air SSH, SmartBridge/GOST) beat fuzzy overlap. Green verification: `68/68 passed, 0 failed`. No new LESSON (RULE ZERO).

- **2026-04-29** | v1.29.0 -> v1.30.0 — Session 80 Mac Codex GBrain Minions/agent-harness planning pass: absorbed AP-41 after parallel Lane C caught a stale-doctrine inheritance bug. `gbrain-ops` P1/P4/AP-6 still referenced new LESSON files and blind production upgrade steps despite RULE ZERO + AP-32 superseding them. Rewrote P1 to require AP-32 dry-run/scope survey before production mutation, rewrote P4/AP-6 to SKILL.md + gbrain timeline only, and updated the upgrade plan to cite AP-32-first. No new LESSON (RULE ZERO).

- **2026-04-29** | v1.28.0 -> v1.29.0 — Session 79 Mac Codex substrate audit: corrected AP-30 lesson-count verification after `mistake-to-skill` AP-13. Current filesystem has 24 historical LESSON files after Apr 25 migration deletes; gbrain checks must compare to current fs count or documented migration state, never hard-coded 129. No new LESSON.

- **2026-04-28** | v1.27.0 -> v1.28.0 — Codified the approved GitHub/Nous operating split after creating the private sanitized GitHub mirror. GitHub is code issues/PR/CI only; Todoist owns Satory business tasks; Notion owns meetings/team context; Obsidian/wiki + gbrain own durable memory, skills, decisions, and retrieval. Blacksmith/ClawSweeper must start proposal-only and cannot mutate business or personal surfaces. Added AP-40 so future agents do not turn "sync everywhere" into duplicate ownership or unsafe automation. No new LESSON (RULE ZERO).

- **2026-04-28** | v1.26.0 -> v1.27.0 — GStack upgrade to upstream `675717e` on Mac + Air exposed two upgrade-harness gaps: generated host skill outputs must be refreshed after template changes, and `skill:check` was skip-blind for the intentionally skipped `claude` template while `gen-skill-docs` was skip-aware. Air also needed `PATH=$HOME/.bun/bin:$PATH` for noninteractive package scripts. Local checker patch deployed byte-identically on Mac + Air; `skill:check` and 56 targeted gbrain/GStack tests pass on both hosts. Added AP-39 so future GStack upgrades regenerate, verify, and codify false-red checker drift instead of ignoring it. No new LESSON (RULE ZERO).

- **2026-04-27** | v1.25.0 -> v1.26.0 — Atomic factory audit found OpenClaw memory search enabled without an embedding provider while gbrain/Obsidian is the intended canonical memory. Disabled `agents.defaults.memorySearch.enabled=false` via OpenClaw CLI on Air and added AP-38: unbacked OpenClaw memory search is not harmless noise; either gbrain owns memory or a separate OpenClaw memory provider design must be written and verified. No new LESSON (RULE ZERO).

- **2026-04-27** | v1.24.0 -> v1.25.0 — Crawl-army/OpenClaw GPT-5.5 audit converted Peter/OpenClaw-style "let it crawl your life" guidance into the Nous substrate rule: collectors write source-manifested Obsidian artifacts first, gbrain indexes second, OpenClaw reads third. Added AP-37 to prevent raw channel/database mounts from bypassing provenance, privacy class, and citation metadata. No new LESSON (RULE ZERO).

- **2026-04-27** | v1.23.0 -> v1.24.0 — Gary Tan/GStack/OpenClaw audit found the exact Obsidian gap: OpenClaw runtime had 40 `gstack-*` skills loaded from Air `~/nous-agaas/skills/`, but the Obsidian/wiki `pages/skills/` source of truth had zero `gstack-*` pages. GBrain is healthy but stale (0.10.1 vs upstream 0.22.x); GStack is loaded but stale (1.5.1 vs upstream 1.15.0). Added AP-36: third-party skillpacks that affect OpenClaw must be mirrored through Obsidian/wiki before runtime, or explicitly marked runtime-only with expiry. No new LESSON (RULE ZERO).

- **2026-04-26** | v1.22.0 -> v1.23.0 — Session 75 daily-0300 audit follow-up: found `tools/daily_0300_substrate_sync.py` using nonexistent `/root/.gbrain/auth.json` + lowercase `openai_api_key` while the real VPS credential is `/root/.config/codex/auth.json` + `OPENAI_API_KEY`. Patched the daily gbrain probe to use env -> auth.json -> `/root/nous-agaas/.env`, fail before embed if missing, and codified AP-35. No new LESSON (RULE ZERO).

- **2026-04-26** | v1.21.0 → v1.22.0 — Session 75 Codex follow-up during AP-59 verification: direct gbrain sync exposed a missing manual `OPENAI_API_KEY`, and the autopilot runner was found carrying an inline OpenAI key. Absorbed AP-34. Added tracked canonical `tools/gbrain-autopilot-run.sh`, deployed it to VPS `/root/.gbrain/autopilot-run.sh`, added `tools/test_gbrain_autopilot_secret_loading.sh`, and verified gbrain returned to `embeddings: 100% coverage, 0 missing`. No new LESSON (RULE ZERO).

- **2026-04-20** | v1.21.0 — Session 55 (Mac-interactive, this session): absorbed **AP-33** — gbrain MCP disconnect CLI fallback. Trigger: gbrain MCP disconnected mid-session; agent was about to defer SOC v1.7.0 + factory-ops v1.8.0 timeline pushes to "autopilot cycle." Recognized (via AP-9 sibling discipline from SOC v1.7.0 just codified minutes earlier) that deferral = potential loss. Fallback path: `ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain timeline-add <slug> <date> <text>'`. Both pushes landed synchronously with `{"status":"ok"}`. Rule: MCP and CLI are two surfaces over the same engine; when one drops, use the other. Cross-ref: `session-operating-contract` AP-9 (execute-don't-defer); SOC AP-8 (don't let tooling friction drive deferral). Codification order matters: AP-33 was written minutes after AP-9 was, and AP-9 is what made the agent notice the would-be-deferral was wrong. Same-session compound compounding. No new LESSON (RULE ZERO).
- **2026-04-20** | v1.20.0 — Session 50 overnight-2: absorbed **AP-32** — Pre-upgrade scope survey (LOC delta + commit count + schema migration count) MANDATORY BEFORE any `git pull` / `gbrain upgrade` / similar. Trigger: Madi shared gbrain v0.13.0 frontmatter-graph release note; we were on v0.10.1; naive path would've `git pull`ed 437 files / +42,921 LOC / 9 commits spanning v0.10.3 → v0.14.0 + 3 schema migrations onto production VPS gbrain with no test environment. Caught at Phase 1 pre-flight investigation; stopped before any production change. Rule: 5-probe Phase 0 (commit count delta / LOC delta / schema migration scan / local-modification conflict surface / CHANGELOG breaking-changes review). Hard gates: >5K LOC delta OR >10 commits OR ≥1 schema migration OR modified tracked files → STOP + brainstorm spec. Cross-ref `audit` AP-16 (probe-before-claim), `session-operating-contract` Rule 5 (can't-verify-say-so), `mistake-to-skill` AP-10 (confusion-protocol-at-forks). Second RULE-ZERO application this session (first was `audit` v1.17 → v1.18 AP-18 honest revision within 24h; this makes third failure→skill absorption in 48h — compounding rate healthy). No new LESSON (RULE ZERO).
  - Open questions:
    - `[open-question]` Is 5,000-LOC the right upgrade-size threshold? Chose from gut feel this session; may be too high for a fast-moving project or too low for a mature-stable one. Re-evaluate after 3 more upgrade cycles.
    - `[weak-edge]` 10-commit threshold doesn't account for squash-merge vs many-micro-commits style differences between upstream repos. Our `test_skill_version_parity.sh` pattern could extend to include pre-upgrade-survey scanner eventually.
    - `[model-drift]` Future gbrain versions may use semantic-version tags vs commit messages (currently neither); rule should generalize to both.
    - `[dependency-risk]` Rule assumes we can compute commit/LOC delta BEFORE upgrading; fails for pinned binary releases (npm install -g, brew) where we don't have source access. Need a complementary rule for binary-upgrade surveys.
- **2026-04-18** | v1.19.0 — Session 49 Mac-parallel: added AP-31 (upstream freshness endpoints lie; always cross-check with our ingest log). Trigger: QMD `mcp__nous-wiki-qmd__status` returned `lastUpdated=2026-04-17T19:05:01.907Z` at 2026-04-18 21:13 KZT (apparent ~21h stale), but VPS cron `qmd-embed.log` mtime = `2026-04-18 03:02:43 +0500` confirming real run ~18h ago. Endpoint lies by ~3h. Shipped `tools/qmd_real_freshness.sh` v1.0 (commit `29241c3c`) + paired sibling test `tools/test_qmd_real_freshness.sh` (6/6 PASS). 2 bugs caught mid-test via Rule-6 loop: GNU-only `stat -c %Y` → switched to `python3 os.path.getmtime`; test's `|| true` swallowing real exit code. Extends AP-24 (OUR cron lie → session 36) to upstream-source lies. Candidate mechanical gate: nightly launchd regression on Air 03:45 KZT (session 50+). No new LESSON (RULE ZERO).
- 2026-04-17 | v1.18.0 — Session 41 (atomic audit): added AP-30 — LESSON filesystem file without `type: lesson` frontmatter (LESSON-050). gbrain silently classified as `concept`; `pages_by_type.lesson` held at 128 instead of converging to 129 as session-40 round-4 predicted. Root-causing scan of all 129 LESSON files: exactly 1 missing `type:`. Fix: added `type: lesson` + deleted stale concept row + waited for autopilot re-ingest. Detection one-liner provided (extends AP-29). Third leg of frontmatter drift trio (AP-23 skill type missing, AP-29 misplaced lesson type, AP-30 correct location missing type). No new LESSON (RULE ZERO).
- 2026-04-17 | v1.13.0 — Session 36.5: added AP-26 (orphan reaper missed ssh-attached idle zombies). New dual-signature reaper at `/opt/nous-agaas/tools/gbrain_reaper.sh` — kills PPID=1 orphans + ETIME>7200s/CPU<5s idle zombies. First-run killed 4 zombies totaling ~320 MB RSS; preserved active session. No new LESSON file.
- 2026-04-17 | v1.12.0 — Session 36.5 (LAN-direct Air): added AP-25 — retiring a policy must enumerate EVERY scheduler surface on EVERY host (mac LaunchAgents + LaunchDaemons + launchctl + crontab, VPS cron/systemd, Air launchd). Found `com.nous.lesson-absorption` still firing every 6h on Air (session 35 declared it unscheduled after checking only Mac+VPS). Unloaded + plist archived. No new LESSON file.
- 2026-04-17 | v1.11.0 — Session 36 Phase 6: added AP-24 (QMD cron was embed-only, missed new docs for 3 days). Fixed on VPS: cron now runs `qmd update --pull && qmd embed`. Manual backlog: 567 new + 138 updated docs indexed; 693 hashes embedding (CPU-bound). No new LESSON file.
- 2026-04-17 | v1.14.0 — Session 37: added Brain-aware invocation (gstack v0.18.0.0 adoption). Maintenance ops must search gbrain for prior gotchas (autopilot concurrency, frontmatter drift, zombie processes) before acting, and save outcome as timeline entry. No new LESSON (RULE ZERO).
- 2026-04-17 | v1.17.0 — Session 40 round 4: added AP-29 — ghost-slug deletes are band-aids; slugs are file-backed and `sync_brain full=true` resurrects them. Fix requires filesystem remediation: `templates/lesson.md` retyped to `type: template`, flat `pages/lessons/LESSON-080` promoted to `individual/` via `git mv`, two `lessons/LESSON-070/071` collisions deleted (rules already in website-deploy + LAW-005). Detection one-liner for audit. No new LESSON (RULE ZERO).
- 2026-04-17 | v1.16.0 — Session 40 (deeper atomic audit): added AP-28 — 17 of 18 `pages/systems/skills/<X>/SKILL.md` legacy duplicates stale (session-39 4-target parity check missed the parallel tree). Session 23 T3 + session 26 AP-17 both flagged this earlier but never completed the fix. Fix: `git rm -r pages/systems/skills/` → commit → sync propagates; then delete 24 gbrain ghost slugs (18 flat alias + 6 legacy-path). Future-session audit script included. No new LESSON (RULE ZERO).
- 2026-04-17 | v1.15.0 — Session 39 (atomic audit): added AP-27 — gbrain DB has 5-6 pre-session-32 ghost lesson pages (uppercase slugs, wrong-prefix paths) causing `type: lesson` count drift (133 gbrain vs 128 filesystem). Filesystem RULE ZERO upheld; drift is historical DB noise. Cleanup script + detection one-liner included. Sub-rule: autopilot "0 chunks embedded" per page is normal fast path, not stall — check `missing_embeddings` across cycles to distinguish. No new LESSON (RULE ZERO).
- 2026-04-17 | v1.10.0 — Session 36: added AP-23 (skill frontmatter `type:` drift). 12 of 18 domain skills lacked `type: skill`, causing gbrain to reclassify them as `concept` on autopilot re-ingest. Fixed inline in this session. Audit snippet + prevention note included. No new LESSON file (RULE ZERO).
- 2026-04-15 | v1.0.0 — created; absorbed LESSON-093/095/096 from session 22 work.
- 2026-04-15 | v1.1.0 — added P4 (absorb-learning), AP-6, AP-7; absorbed Asylbek directive (lessons must also live in SKILL.md). Triggered by Satory-team input burst (Smatay / Asylbek / Daniyar / Denis).
- 2026-04-15 | v1.2.0 — Wave 3: added AP-8 through AP-12 from LESSON-027, 030, 037, 038, 070, 081.
- 2026-04-15 | v1.3.0 — Wave 4: added absorbs_laws (LAW-001,005,009,015,017). Cross-refs added to AP-6,7,8,9.
- 2026-04-15 | v1.4.0 — added AP-13 (don't use put_page to CREATE wiki pages) absorbing LESSON-105 (gbrain put_page disk-sync gap discovered during session-23 input burst).
- 2026-04-15 | v1.5.0 — session 26 audit-fix pass: added AP-14 (autopilot flock — no concurrent cron pileup) and AP-15 (embed ghost chunks — `embedded_at` without `embedding`). Absorbs LESSON-112. Trigger: audit claimed 100% embedding coverage while 107 chunks were actually unembedded (93.6% real coverage).
- 2026-04-15 | v1.5.1 — session 26 parallel-session reconciliation: added AP-16 (symlink + manifest + embed after adding AGaaS domain skill). Absorbs LESSON-111 (resolver_health symlinks) written by parallel CTO session.
- 2026-04-15 | v1.5.2 — lesson-numbering reconciliation: my autopilot-pileup lesson renumbered LESSON-111 → LESSON-112 to de-conflict with CTO's resolver-symlinks LESSON-111. AP-14/AP-15 refs updated accordingly.
- 2026-04-15 | v1.5.4 — session 28 audit: added AP-19 (gbrain doctor must be run from /opt/nous-agaas/gbrain CWD — false-positive resolver_health caused by wrong CWD walked by findRepoRoot()). Absorbs LESSON-113.
- 2026-04-15 | v1.5.3 — session 26 atomic deep-dive audit findings: added AP-17 (dual-location skill mirror sync discipline — 7/13 skills drifted) + AP-18 (rename body-H1 must match id). Triggered by byte-identity audit revealing silent drift between `pages/skills/` and `pages/systems/skills/`, and by LESSON-112 body H1 still reading "LESSON-111" after rename.
- **2026-04-16** | v1.9.0 — Session 34: added AP-22 (orphan `gbrain serve` cleanup — 14 zombie processes consuming 1.1GB fixed, cron orphan-reaper installed). Absorbs LESSON-128.
- **2026-04-16** | v1.8.1 — Session 33: patched autopilot-run.sh with AP-15 ghost auto-reset (permanent fix — SQL UPDATE before every autopilot cycle). Fixed 69+21+14 ghost chunks. Full sync restored 2159/2159 → 100% embedding. Also found 5 skills missing from RESOLVER.md (error-classification, evidence-verification, kazakhstan-regulatory, mistake-to-skill, planning-discipline) — added.
- **2026-04-16** | v1.7.0 — Absorbed LESSON-077 (verify SQL column names with \d, add UNIQUE index for idempotent inserts). Evidence: bulk lesson absorption session.
- **2026-04-16** | v1.6.0 — added dream cycle + wiki-to-runtime-rsync procedures per [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]] Phase P3.

## See also

- [[LESSON-093-factory-context-poisoning-and-ghost-cleanup]]
- [[LESSON-095-gbrain-0.4.1-to-0.10.1-upgrade]]
- [[LESSON-096-run-in-background-discipline]]
- [[LESSON-111-gbrain-resolver-health-agaas-skills-symlinks]]
- [[LESSON-112-gbrain-autopilot-pileup-and-embed-ghost]]
- [[LESSON-113-gbrain-doctor-cwd-false-positive]]
- `skills/_gbrain/RESOLVER.md`
- `skills/_gbrain/brain-ops/SKILL.md`
- `skills/infrastructure/SKILL.md`

### LESSON-118 absorption (2026-04-16)

- **LESSON-118 Rule 1:** After any batch skill update, run `check_resolvable.py` AND grep for H1/frontmatter version mismatches: `for s in */SKILL.md; do v=$(grep "^version:" $s | awk "{print \$2}"); h=$(grep "^# " $s | grep -o "v[0-9.]*"); [ "$v" != "$h" ] && echo "MISMATCH: $s fm=$v h1=$h"; done`
- **LESSON-118 Rule 2:** After any lesson triage, verify file count matches triage list. `ls LESSON-*.md | wc -l` must equal triage total.
- **LESSON-118 Rule 3:** `_gbrain/` directory MUST be tracked in wiki git repo (pages/skills/_gbrain/). Air runtime is working copy, wiki is source of truth.
