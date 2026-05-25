---
type: spec
id: SPEC-2026-05-20-ipad-only-proof-flight-design
title: "iPad-only proof flight — Day 6 acceptance smoke test before Day 7 promotion"
date: 2026-05-20
status: ready-for-execution
owner: claude-opus-4-7
priority: p0-promotion-gate
tags: [spec-kit, ipad-only, proof-flight, smoke-test, telegram, hermes, day-6, promotion-gate]
related:
  - [[HANDSHAKE-2026-05-20-ipad-only-presidential-7-day-plan-0820]]
  - [[2026-05-20-telegram-consult-command-design]]
  - [[2026-05-19-multi-model-consult-skill-design]]
---

# iPad-only proof flight

Day 6 of the 7-day iPad-only ladder. **Falsifiable test sequence Madi runs from iPhone Telegram (no Mac terminal, no SSH, no laptop interaction) before Day 7 promotion.**

If all 10 tests below GREEN within 60 minutes total from iPhone alone, the system is presidentially-iPad-ready. ANY single RED → diagnose + fix + re-run that test.

## Constitution

Madi 2026-05-19 ~17:45 KZT: "Madi can leave Macs at home in 7 days." 2026-05-20 ~08:15 KZT: "leave my MacBook Pro and MacBook Air at home ... only have iPad and iPhone with me ... presidential place with CEO and top tier models with cheap labor."

This proof flight is the binary acceptance test. Pass = promote. Fail = identify which test failed, fix, retry. No partial credit.

## Pre-flight setup (Madi does once)

1. Laptops physically at home, plugged in, lid open (Air + Mac Pro).
2. iPhone has Telegram open to `@nousAGaaSbot` DM thread.
3. (Optional) Hermes WebUI app open on iPhone via Safari: `http://192.168.1.197:8787` (same-WiFi) or Tailscale phone-url if logged in.
4. Madi physically walks to a different room, OR closes the Mac terminal apps. The proof is: **everything below works without Madi touching a Mac**.

## The 10 tests (in order; each ≤ 5 min)

### T1 — bot alive (1 min)

**Send**: `/status` to `@nousAGaaSbot`
**Expect**: reply within 2s with Air runtime health summary (docker status, disk, mem)
**Pass if**: reply lands; health is HEALTHY/GREEN
**Catches**: telegram_poll launchd dead, command_center.py broken, Air SSH unreachable

### T2 — /ask cheap-tier worker (3 min)

**Send**: `/ask How many active goals does the factory currently track?`
**Expect**: reply within 30s from DeepSeek V4 Flash via OpenClaw worker
**Pass if**: reply contains a number + cost footer ≤ $0.005
**Catches**: OpenClaw container down, LiteLLM broken, OpenRouter API rate-limit, AP-44 routing broken

### T3 — /codex CEO-tier (5 min)

**Send**: `/codex Read /Users/madia/nous-agaas/wiki/pages/skills/factory-ops/SKILL.md and reply with exactly the version number on a single line.`
**Expect**: reply within 60s from gpt-5.5 via Codex CLI on Air
**Pass if**: reply contains the actual SKILL.md version (e.g., "v1.36.8" or current)
**Catches**: Codex CLI on Air not authenticated, --skip-git-repo-check issue (fixed at c4b9eda5), subscription cap

### T4 — /code Claude Code on Air (5 min)

**Send**: `/code List the 3 most recent commits on main with one-line summaries.`
**Expect**: reply within 60s from Sonnet 4.6 / Claude Code spawn on Air
**Pass if**: reply has 3 commits with SHA prefixes + summaries
**Catches**: Air-side Claude Code CLI broken, $5/day cap hit, session preamble broken

### T5 — /goal persistent goal cycle (5 min)

**Send**: `/goal proof-flight-2026-05-20-iphone-only`
**Expect**: ack within 5s confirming goal created + Todoist task created + goal cycle kicked
**Pass if**: ack lands with a Todoist task URL; within 10 min Madi sees the next /goal cycle update mention this slug
**Catches**: goal_runner broken, Todoist API broken, control_plane_sync broken

### T6 — /consult multi-model brain (5 min) [PENDING — depends on Codex T2-T6 of /consult spec]

**Send**: `/consult In one sentence, what is the smallest action Madi could do right now to prove the iPad-only system works end-to-end?`
**Expect**: ack `🧠 consulting CEO panel…` within 2s; final answer within 60s
**Pass if**: final reply has winner model + cost + actionable answer; cost ≤ $0.05
**Catches**: multi-model-consult skill broken, Codex CLI 1-in-3 race, Anthropic API throttled, /consult dispatch missing
**Note**: this test requires /consult Telegram hook (`ad59c710` spec → Codex impl pending)

### T7 — Hermes WebUI dashboard (5 min)

**Browser on iPhone**: open `http://192.168.1.197:8787` (same Wi-Fi as Air) OR Tailscale phone-url if logged in
**Expect**: WebUI prompts for password (from `~/nous-agaas/secrets/hermes-webui.env`); after login, Kanban view + factory events visible
**Pass if**: at least one factory event from today shows in `/api/factory-events` endpoint or Kanban
**Catches**: Hermes canary down, /api/factory-events broken (fixed at 905563d8), iOS TestFlight build broken

### T8 — /handoff session transfer (5 min)

**Send**: `/handoff trigger`
**Expect**: ack within 5s confirming handoff written; latest HANDOFF-AUTO-YYYY-MM-DD-HH-MM.md commits to vault within 60s
**Pass if**: substrate has the new handoff committed; Madi can read it via `/code cat last handoff`
**Catches**: auto-checkpoint cron broken, wiki-sync broken, AP-32 substrate-handshake broken

### T9 — Real Satory question end-to-end (5 min)

**Send**: `/ask Asyl needs the current production ERAP endpoint configuration. Where is it documented in the vault?`
**Expect**: reply within 45s from grok-ceo or DeepSeek with a wiki path
**Pass if**: reply contains a `pages/...` path; that path actually exists in vault (Madi taps `/code cat <path>` to verify)
**Catches**: gbrain semantic search broken, library_*_scan.py broken, vault wikilink resolution broken

### T10 — Operator-visible notification policy holds (15 min)

**Action**: Madi watches Telegram for 15 min after T9 with NO additional commands sent
**Expect**: ≤ 1 routine background ping (digest format only, NOT individual queue checkpoints / goal cycles / auto-syncs)
**Pass if**: Telegram inbox quiet during the 15-min window (notification policy `fe3ad661` SUPPRESS rules holding)
**Catches**: notification-policy not gating cron output, factory-self-heal escalating false RED, Hermes watchdog over-pinging

## Promotion gate

ALL 10 tests GREEN within 60 minutes → **Day 7 PROMOTED**: Madi leaves Macs at home for 24 hours, factory stays GREEN, no Mac access required. Confirmed by **absence** of any Mac-side `Author: Madi Ayazbay <madia@Mac.localdomain>` commit during the 24-hour window (only Air-side auto commits + Codex/Opus session commits should appear).

If ANY test fails:
- Diagnose root cause via `/ask trace <test-id>` (uses gbrain to surface the failure)
- Fix in Opus/Codex lane via substrate handshake
- Re-run ONLY that test
- Promotion gate held until 10/10 GREEN consecutive

## Musk delete/reduce

What this spec **deletes**:
- "Madi randomly tries things from iPhone" → replaces with deterministic 10-test sequence
- "We'll know it works when it works" → falsifiable per-test pass/fail criteria

What this spec **adds**:
- 10 explicit test cases (60 min total)
- 1 promotion gate (binary pass/fail)
- 1 rollback path (per-test retry)

Net cognitive debt: small. Single proof-flight doc. Already-shipped commands.

## Tasks

- [ ] **T-PROOF-1** — Codex ships `/consult` impl (so T6 unblocks). Depends on Codex pickup of `ad59c710` spec.
- [ ] **T-PROOF-2** — Codex ships daily-evolution `com.nous.daily-evolution.plist` (so the 03:00 KZT cron actually fires). Depends on Codex T6 of cron spec.
- [ ] **T-PROOF-3** — Madi answers Q1-Q4 + Q-canary + Q-desktop (so R1+R4 unblock and don't block the proof flight).
- [ ] **T-PROOF-4** — Opus pre-flight check: run T1-T5 + T7-T10 from Mac terminal as dry-run (skipping T6 which needs `/consult` impl) → confirm all currently-shipped commands work.
- [ ] **T-PROOF-5** — Madi schedules a 60-min iPhone-only window for the live proof flight.
- [ ] **T-PROOF-6** — Live execution: Madi runs T1-T10 from iPhone, captures screenshots, posts to vault as `pages/audits/IPAD-ONLY-PROOF-FLIGHT-RESULTS-YYYY-MM-DD.md`.
- [ ] **T-PROOF-7** — On 10/10 GREEN: Day 7 promotion fires. Madi leaves Macs at home for 24h. Opus + Codex track substrate during the window.

## Acceptance criteria (binding, falsifiable)

1. T1-T10 completion within 60 min of first send
2. Zero Mac-terminal interaction by Madi during the proof flight
3. ≤ 1 routine background ping during the 15-min T10 quiet window
4. All 10 test results captured in `pages/audits/IPAD-ONLY-PROOF-FLIGHT-RESULTS-YYYY-MM-DD.md` with screenshot or substrate evidence
5. 24-hour post-promotion Mac-author-commit count = 0 (only Air + agent commits)

## Rollback path

If proof flight fails at any test:
- DON'T promote
- Open `pages/audits/IPAD-ONLY-PROOF-FAILURE-T<N>-YYYY-MM-DD.md` with the failing test
- Hand to Opus/Codex via substrate
- Re-attempt within 24h once fix lands

If 24h post-promotion Mac-author commit count > 0:
- Madi reverted to Mac for some reason → identify the unmet capability
- Open spec for the missing capability
- Cycle back to Day N where N = step that needs the capability

## See also

- `[[HANDSHAKE-2026-05-20-ipad-only-presidential-7-day-plan-0820]]` — parent ladder (this is Day 6)
- `[[2026-05-20-telegram-consult-command-design]]` — /consult command spec (unblocks T6)
- `[[2026-05-19-multi-model-consult-skill-design]]` — skill being wrapped
- `[[skills/command-center]]` — host of all slash commands tested
- `[[skills/ceo-hierarchy]]` — CEO/cheap-labor tier under test in T2-T3

## Timeline

- **2026-05-20 10:23 KZT** — This proof-flight spec authored by Opus. 10 tests + 1 promotion gate + 5 tasks queued. Awaiting Codex pickups + Madi's 6 Q's + Madi's 60-min iPhone window for live execution.
