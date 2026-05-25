---
type: system
id: SYS-ARCHITECTURE-QUICKREF
title: "Architecture quick-reference + hard rules — vault mirror of Mac-root Claude/Codex session shims"
tags: [system, architecture, hard-rules, session-start, telegram-routing, session-continuity, 2026-04-20]
date: 2026-04-20
source_count: 2
status: reviewed
last_updated: 2026-04-27
related:
  - SYS-ARCH
  - session-operating-contract
  - infrastructure
  - factory-ops
  - LAW-005
  - LAW-016
---

# Architecture Quick-Reference + Hard Rules (vault mirror)

> **What this is.** The project-root `/Users/madia/Documents/Projects/Nous AGaaS/CLAUDE.md` file on the Mac is what Claude Code reads in its session-open system prompt, and `/Users/madia/Documents/Projects/Nous AGaaS/AGENTS.md` is the matching Codex session-shim. This vault page is the **substrate mirror** of that same operational content so that **Air-side agents** (OpenClaw factory, `/codex`-spawned Codex CLI, `/code`-spawned Claude CLI) can see the same hard rules, architecture topology, Telegram routing model, and session-continuity design without depending on files that live outside the vault.
>
> **Why this exists.** Session-51 narrowed HARD RULE 1 (Telegram-MCP ban), session-52 added the Nous-GPU row, session-53 refined the routing model. All three changes landed in Mac-root CLAUDE.md ONLY — they never reached the vault where Air-side agents substrate-read. Probe B of session-54 surfaced the drift; this file closes it.
>
> **Source of truth.** When the vault and Mac-root CLAUDE.md / AGENTS.md diverge, reconcile by hand. The authoritative version of any given rule is whichever file is newer AND has a corresponding entry in the relevant skill timeline. Drift-detection gate: `tools/test_claude_md_parity.sh`.

## HARD RULES (violations block work)

### 1. Telegram MCP tools — TOKEN-scoped ban (narrowed session-51, 2026-04-20)

The ban is on **same-token polling**, not on the tool class. `@nousAGaaSbot` (token id `8799328101`) is polled exclusively by `telegram_poll.py` on Air (`com.nous.telegram-poll` launchd, 60s interval). Any other process polling the SAME token → HTTP 409 Conflict + message duplication + dual-agent drift (broke sessions 15, 16 — see LESSON-087).

**CC-MCP plugin (`mcp__plugin_telegram_telegram__*`) is SAFE when:** `~/.claude/channels/telegram/.env` uses a DIFFERENT token from Air's `~/nous-agaas/.env`. Session-51 verified CC-MCP uses bot id `8613073660` (independent BotFather bot for Madi's DMs) — no 409 risk.

**Mechanical pre-flight:**
```bash
CC_TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/.claude/channels/telegram/.env 2>/dev/null | cut -d= -f2-)
AIR_TOKEN=$(ssh air 'grep TELEGRAM_BOT_TOKEN ~/nous-agaas/.env 2>/dev/null | cut -d= -f2-')
if [ -z "$CC_TOKEN" ] || [ "$CC_TOKEN" = "$AIR_TOKEN" ]; then
  echo "🔴 BANNED — same token as @nousAGaaSbot (or CC-MCP .env missing) → 409 risk"
else
  echo "✅ SAFE — CC-MCP uses a different bot (id=$(echo $CC_TOKEN | cut -d: -f1))"
fi
```

**Banned when check fails:** `mcp__plugin_telegram_telegram__{reply,edit_message,react,download_attachment}`.
**Permitted when check passes:** same tools — use freely for DMs to Madi's `chat_id=110793056`.

See [[LESSON-087]], [[session-operating-contract]] Rule 7.

### 2. NEVER deploy, alias, or redirect `satory.nousagaas.com`

Locked deployment: `satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app`
Asset fingerprint: `index-BSiWURaO.js`

Pre-flight:
```bash
CURRENT_JS=$(curl -s "https://satory.nousagaas.com/" | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1)
if [ "$CURRENT_JS" = "index-BSiWURaO.js" ]; then echo "LOCKED VERSION LIVE"; else echo "🔴 WRONG — RESTORE"; fi
```

See [[LAW-016]], [[LESSON-076]].

### 3. gbrain MCP IS connected — never claim it isn't

`mcp__gbrain__*` tools are available in every session. If they appear in the deferred tools list, load them with `ToolSearch` and they will work. Never SSH directly to the wiki to write skills while claiming gbrain is disconnected. Session-17 post-mortem.

### 4. Session start — read handoff first

Every new session MUST read the latest handoff from the wiki before any code:
```bash
ssh root@65.108.215.200 "ls -t /root/nous-agaas/wiki/pages/progress/HANDOFF-AUTO-*.md | head -3"
```
Then read the most recent via `mcp__gbrain__get_page` or `mcp__nous-wiki-qmd__get`.

### 5. Verify claims before declaring done

[[LESSON-085]] — never declare a feature "done" without end-to-end test.
[[LESSON-086]] — in polling loops, save state BEFORE slow handler.

Full DONE protocol: [[session-operating-contract]] Rule 4.

### 6. Every learning → SKILL.md + gbrain timeline (NOT a LESSON file)

RULE ZERO from `CLAUDE.md`. No new LESSON-NNN files. LESSON ceiling is 129, but current filesystem count may be lower after migration/deletion. Pre-commit hook physically rejects new lesson files.

## Telegram routing model (session-51, 2026-04-20)

One bot (`@nousAGaaSbot`), one token, unified interface. Sessions ephemeral; substrate compounds; Madi broadcasts intent via Telegram → any agent on any host picks up → pushes result back.

### Inbound — Madi DMs `@nousAGaaSbot`

| Prefix | Routes to | Agent | Context source | Use when |
|---|---|---|---|---|
| `/ask <query>` | factory | OpenClaw router + DeepSeek V4 worker tier | injected context-v2 | daily broadcasts, questions, status checks |
| `/codex <task>` | ephemeral OpenAI Codex CLI on Air | Codex `gpt-5.5` (subscription first, API fallback while Air auth is stale) | **auto-injected** HANDOFF-AUTO + MEMORY.md + `session-operating-contract` + `command-center` skill | coding/reasoning tasks where Madi wants Codex/OpenAI 5.5 from Telegram |
| `/code <task>` | ephemeral Claude Code CLI on Air | Sonnet 4.6 ($5/day cap) | **auto-injected** HANDOFF-AUTO + MEMORY.md + `session-operating-contract` skill (I-B, session-51) | coding tasks wanting full tool set + session-continuity |
| `/status`, `/report`, `/health`, `/handoff`, `/help` | factory command handlers | — | — | infra/operational signals |
| (no prefix) | implicit `/ask` → factory | OpenClaw router + DeepSeek V4 worker tier | same as `/ask` | simplest path — just forward |

**Polling is exclusive to `telegram_poll.py` on Air.** See HARD RULE 1.

### Outbound — agents push to Madi

| Path | Tool | Auth | Use |
|---|---|---|---|
| Any agent → Madi's phone | `bash tools/tg_send.sh "<text>"` | token auto-resolved from env / `~/nous-agaas/.env` / `ssh air` | push notifications, session-close summaries, alerts |
| Agent reply within `/ask`, `/codex`, or `/code` flow | already wired (factory/Codex/Claude returns text, telegram_poll sends it) | — | normal task response |

`tg_send.sh` is send-only — no `getUpdates`, zero HTTP 409 risk, works from any host (Mac, Air, VPS) because token is fetched lazily.

### Session-continuity architecture

- **Ephemeral sessions:** Mac terminal Claude Code/Codex, `/codex`-spawned Codex CLI on Air, `/code`-spawned Claude CLI on Air — all die on disconnect. Don't try to keep them alive.
- **Persistent substrate:** `MEMORY.md` (AMD-006 top-block-prepend) + `HANDOFF-AUTO-*.md` (8×/day checkpoints) + `pages/skills/*/SKILL.md` (doctrine) + gbrain timeline (searchable evidence) + `laws/`.
- **Context flows via substrate, not session history.** Next session reads substrate → picks up where last session ended.
- **The president's interface is Telegram.** You broadcast direction; agents on any host read substrate, execute, push result via `tg_send.sh`. Your phone is the dashboard.

Evidence: I-A (`tools/tg_send.sh`), I-B (Air `command_center.py` `SESSION_CONTEXT_PREAMBLE` injection, Air-local not vault-tracked), I-C (this routing table, session-51 handoff).

## Architecture quick-reference

Factory runs on Air (M2 MacBook). VPS is gateway-only.

| Component | Location | Purpose |
|---|---|---|
| **Factory agent** (OpenClaw 2026.4.14) | **Air Docker**, port 18789 | DeepSeek V4 Flash/Pro via LiteLLM; handles `/ask` worker tasks |
| **LiteLLM** | Air native, port 4000, launchd `com.nous.litellm` | Routes to OpenRouter DeepSeek V4 Flash/Pro, Grok, Anthropic, and GLM fallback aliases |
| **Telegram poller** | Air launchd `com.nous.telegram-poll` (60s) | Handles `@nousAGaaSbot`, routes to factory |
| **Wiki git repo** (bare) | VPS `/root/nous-agaas/obsidian-wiki.git` | Single source of truth; Air + Mac push/pull |
| **Wiki (working copies)** | VPS `/root/nous-agaas/wiki/`, Air `~/nous-agaas/wiki/`, Mac `~/Documents/Projects/Nous AGaaS/Nous/` | All three bidirectionally synced |
| **gbrain** (v0.10.1 + autopilot every 5 min) | VPS `/opt/nous-agaas/gbrain/` | Semantic search + embeddings via `mcp__gbrain__*` |
| **Auto-checkpoint** | Air launchd `com.nous.auto-checkpoint` (8×/day smart-skip) | Writes `HANDOFF-AUTO-*.md` |
| **Skill extractor (legacy)** | VPS `/opt/nous-agaas/vps_skill_extractor.py` every 10 min | Extracts from task-results into `pages/skills/extracted/` |
| **Nightly jobs** | Air launchd: `morning-brief` 04:00, `morning-update-apply` 05:07, `qmd-freshness-regression` 03:45 | State-diff alerts + update checks + QMD regression. (`nightly-update-check` + `nightly-audit` were doc-only — `launchctl list` confirms not loaded as of session s1030 2026-05-20; coverage via `morning-update-apply` + `light-probe` 15 min + `staleness` hourly is sufficient.) |
| **Session hygiene** | Air launchd `light-probe` 15 min, `staleness` hourly, `log-rotate` Sun 03:00, `docker-desktop-watchdog` 5 min | Passive monitoring + Docker auto-recovery |
| **NCAnode** (ЭЦП crypto) | VPS Docker | ERAP-only cryptographic operations |
| **Langfuse** | VPS Docker | Observability (not yet wired to Air LiteLLM) |
| **VPS host** | `root@65.108.215.200` (Hetzner) | Gateway + gbrain + wiki repo + crypto |
| **Air host** | `ssh air` (Tailscale `100.122.219.22`) | Primary compute 24/7; see [[air-ssh-access]] |
| **Satory CEO-assistant** (tenant layer, 2026-04-21 session 57) | Air `~/nous-agaas/tenants/satory/` (runtime) + `pages/tenants/satory/` (vault) | **LIVE MVP v0:** Naution meeting transcript → `@nousAGaaSbot` forward → Grok-4.20-reasoning extraction → JSON proposals (title / owner / deadline / priority / research_needed) → **direct write to Todoist shared team project `6gJ5j8PRVVCWpgCq` ("Satory VKO Factory")**. 6 agents: extractor + approver (deleted from critical path — Madi: "too much bullshit") + writer + learner + researcher + notion_to_gbrain. LiteLLM `grok-reasoning` alias → `xai/grok-4.20-0309-reasoning`, `metadata.tenant=satory` cost attribution, ~$0.02/extraction. Karpathy loop: Madi edits/deletes in Todoist → `learner.py` observes → updates `pages/tenants/satory/skills/*/SKILL.md` + gbrain timeline (redesign pending — approver-deletion removed the signal; Todoist-diff cron is session-58+ target). **Tenant-isolation guardrail:** `satory-tenant-isolation/SKILL.md` v0.2.0 AP-1 — **pre-write `is_shared` check on any Todoist project** (session-57 near-miss: 8 of Madi's personal "Satory AI" project `6fhm35CG93P2jff9` tasks were soft-deleted when agent misread `is_shared`; full content-preserving restore executed). 3/3 mechanical `tests/test_satory_agent_isolation.sh` GOLDEN. Notion integration token pending Madi mint (blocks Phase v1 2nd-brain write + ingestion cron). See [[HANDOFF-AUTO-2026-04-22-session-57-MASTER-close-satory-ceo-assistant-live]] + [[tenants/satory/skills/tenant-isolation]]. |
| **Nous-GPU** (Assyl/Alex, 2026-04-20) | `nous-admin@100.70.222.21` (Tailscale) / LAN `192.168.8.64` / WG tunnel `10.99.99.1` | Local RTX 5070 / 12 GB / CUDA 13.0 compute. **Phase-1 LIVE (2026-04-21, session 56-EXT-WG):** WireGuard tunnel UP to Denis's new sniff-target server (`89.40.56.150:13231`, peer pubkey `2KfJdzhvO0vLkEk8ilpfgmpDzAw9uworOoDW2wO7bVE=`, us `10.99.99.1/24`, Denis `10.99.99.2/24`, handshake <30s). Container `nous-collector` re-bound to **`-i wg0`** writing `/pcap/wg0-collector.pcap`. Throughput ~1.9 Mbit/s sustained (Denis's "1-2 ГБ/с" resolved as Мбит/с shorthand; pcap-to-disk arch correct; 859 GB free = years retention). Hourly zstd rotation via `systemd-timer nous-collector-rotate.timer` (session 57), 7-day retention, disk-guard 85%. **Health probes:** (a) `tools/test_nous_gpu_wg0_collector_live.sh` 4-check wg0 validator — handshake-age + container-bind + pcap-delta + tshark-decode, auto-detects pcap path from container cmd (session 57); (b) `tools/test_nous_gpu_collector_tzsp.sh` Tailscale synthetic generator (session 57 — pre-WG era, kept for debug); (c) Air launchd `com.nous.nous-gpu-collector-health` 5-min cadence with state-change Telegram alerting. See [[nous-gpu]] + [[PHASE-0-COLLECTOR-DEPLOYMENT-2026-04-21]]. |
| **Mac Pro** | `/Users/madia/Documents/Projects/Nous AGaaS/` | Dev + Claude Code interactive; Madi travels with this |

## Obsidian = single source of truth (LAW-005)

- All notes, lessons, skills, handoffs → wiki at `/root/nous-agaas/wiki/` (VPS bare).
- Mac vault path: `/Users/madia/Documents/Projects/Nous AGaaS/Nous/`
- Memory dir `~/.claude/projects/.../memory/` symlinks INTO the vault.

**Skill-layer runtime path (rule-6 rsyncs):** `/Users/madia/nous-agaas/skills/<skill>/SKILL.md` on Air (bind-mounted into OpenClaw container as `/opt/nous-agaas/skills/<skill>/SKILL.md`). `/opt/nous-agaas/` is **container-internal only** — it does not exist on the Air host filesystem. AP-10 4-target parity MUST use host-side path `/Users/madia/nous-agaas/skills/`. See `docker inspect openclaw --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'` for authoritative mount map. Session-45 2026-04-17.

## Runtime behavioral contract

Every session reads [[session-operating-contract]] FIRST before any work. Authoritative runtime doctrine: session-start ritual, Plan→Execute→Verify with 4-artifact **DONE protocol**, Musk 5-step with step-2-first audit, failure→skill loop, hard-banned patterns (persona cosplay, `"done"` without proof, Telegram MCP same-token, new LESSON files, "let me know if you want me to continue"), outbound correspondence + commercial-frame discipline (Rule 13 / AP-4/5/6).

**Trigger words (instant, no confirmation):**
- `prove it` → re-run DONE protocol on most recent claim.
- `честно` → drop hedging; one-sentence real answer.
- `delete?` → Musk step 2 on current proposal; argue for removal first.
- `kill` → stop current task, dump state, exit.

**DONE protocol:** type `done/complete/fixed/deployed/ready/готово` ONLY when all four in same message:
- (a) exact command run (literal, not paraphrased)
- (b) exact output
- (c) git state: `git rev-parse --short HEAD` + `git status --porcelain`
- (d) one counter-check you actually ran

Missing any → `verified: X. unverified: Y. next: <exact-command>.`

**Failure → skill** (RULE ZERO in motion): on any sub-100%, codify fix into relevant `SKILL.md` via AP-11 3-edit ritual + push `mcp__gbrain__add_timeline_entry` on same skill page. Then retry.

Full doctrine: [[session-operating-contract]].

## Drift-detection note (session-54 observation)

This vault page is a **mirror** of Mac-root `CLAUDE.md`'s operational content, not a replacement. The Mac-root file is loaded as in-context session-open instructions; this vault page is substrate-reachable from any host.

When either is edited:
1. Prefer editing the vault page first.
2. Sync edits to Mac-root CLAUDE.md manually.
3. When session-operating-contract rule 13 (or similar doctrine) adds a new hard rule, update BOTH in the same commit if the Mac-root content lived in the vault; otherwise update the vault and accept a 1-session lag on Mac-root until next manual sync.
4. Drift-detection gate (`tools/test_claude_md_parity.sh`) deferred to session-55+.

Session-54 discovered: HARD RULE 1 narrowing (session-51), Nous-GPU row (session-52), Telegram routing model (session-51) lived in Mac-root only. This page closes that gap forward; prior drift unrecovered but historically documented in each session's handoff.

## Timeline

- **2026-04-20** | Created during session-54 Probe B. Extracts Mac-root `CLAUDE.md` operational content (HARD RULES, Telegram routing, architecture quickref, session-continuity design, runtime contract reference) into substrate-reachable form so Air-side agents can consult it. Drift-detection gate deferred. Source of extraction: Mac-root commit context as of `47e56b2f`. Cross-ref [[session-operating-contract]] v1.4.0 for runtime doctrine.

## See also

- [[SYS-ARCH]] — full system architecture (this page is the session-start-shim abstract; SYS-ARCH is the deep-dive)
- [[session-operating-contract]] — runtime behavioral contract; v1.4.0
- [[infrastructure]] — AP-43 pre-commit RULE 4 mechanical enforcement; candidate home for parity-gate AP
- [[factory-ops]] — Air Docker / OpenClaw / LiteLLM ops
- [[air-ssh-access]] — Air host access patterns
- [[nous-gpu]] — third peer compute host
- [[LAW-005]] — Obsidian as single source of truth
- [[LAW-016]] — satory.nousagaas.com lock
- [[LESSON-076]] — code/satory trap
- [[LESSON-085]] — never declare done without E2E
- [[LESSON-086]] — polling-loop state ordering
- [[LESSON-087]] — Telegram MCP 409 incident (drift-annotated session-51)
