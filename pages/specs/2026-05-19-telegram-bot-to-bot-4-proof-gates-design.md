---
type: spec
id: SPEC-2026-05-19-telegram-bot-to-bot-4-proof-gates-design
title: "Telegram bot-to-bot — 4 proof gates spec (loop-depth + dedupe + rate-limit + kill-switch)"
date: 2026-05-19
status: draft
owner: claude-opus-4-7
priority: p1-blocked-by-design
tags: [spec-kit, telegram, bot-to-bot, proof-gates, kill-switch, rate-limit, dedupe, loop-depth, command-center, mission-2026-05-19, residual-R1, ladder-step-2-specify]
related:
  - [[HANDSHAKE-2026-05-19-residuals-onebyone-codex-opus-1822]]
  - [[2026-05-19-nous-operating-loop-design]]
  - [[skills/command-center]]
  - [[MISSION-2026-05-19-always-on-satory-ai-factory]]
---

# SPEC — Telegram bot-to-bot 4 proof gates

## Constitution (step 1)

Madi verbatim 2026-05-19: "Telegram bot-to-bot should not be enabled until loop-depth, dedupe, rate-limit, and kill-switch proof exists." This spec defines the 4 proof gates. **No implementation lands until Madi greenlights this spec.**

Residual R1 of 4-residual handshake `[[HANDSHAKE-2026-05-19-residuals-onebyone-codex-opus-1822]]`.

## Specify (step 2)

Bot-to-bot = a Nous-controlled bot (currently `@nousAGaaSbot`) sending a Telegram message to another Nous-controlled bot (or to itself in a different chat context). Prerequisite for: cross-agent coordination via Telegram channels, automated proof relays between factory workers, multi-bot orchestration.

**Threat model (Bad-News-Loud per musk-algorithm):**
- **Loop denial-of-budget** — bot A replies to bot B, bot B replies to bot A, recursion until token cap exhausted. Worst case: $5/day Codex cap burned in <30s.
- **Duplicate-reply collision** — two Nous bots both reply to the same operator message (the 16:31 KZT incident, AP-46 audit).
- **API quota burn** — Telegram bot API rate limits (`30 msg/sec global; 1 msg/sec per chat`); sustained bot-bot exceeds.
- **Silent-state-corruption** — bot B's reply to bot A overwrites bot A's inbox classification because both share `@nousAGaaSbot` token namespace.

## Clarify (step 3 — open questions for Madi)

1. **Scope of "bot-to-bot".** Single shared token (`@nousAGaaSbot`) talking to itself across chats, OR distinct second bot (`@nousFactoryEcho` etc) with its own token? Recommend **distinct second bot** — tokens are the security boundary, AP-41 / HARD RULE 1 already pivots on token identity. Single-token bot-to-self is a special case of distinct-token bot-bot and should not be allowed (collapses dedupe gate).
2. **Allowed message types.** Only `/<cmd>` slash commands? Free-text? Photos? Recommend **slash-prefixed only** initially — narrows surface, easier dedupe, no NL classification ambiguity.
3. **Kill-switch enforcement layer.** Pre-commit hook + runtime check + plist `EnvironmentVariables`? Recommend **all three** — defense-in-depth; runtime check is authoritative (read on every send), plist is fallback, pre-commit hook prevents accidental enable.
4. **Loop-depth threshold.** Default N=2 means bot A → bot B → bot A is the LAST allowed exchange (depth 2 from origin). Operator-initiated chains exempt. Recommend **N=2 with operator-bypass via explicit `/handoff <bot> <task>` slash command** (operator authorship resets depth to 0).

## Musk delete/reduce (step 4)

What this spec **deletes/replaces**:
- Implicit assumption in `command-center` AP-44 that "operator commands originate from human" — replaces with explicit `sender_kind ∈ {human, bot, system}` field on every routed event.
- Ad-hoc rate-limit logic scattered in `telegram_poll.py` retry loops — consolidates into one `BotToBotRateLimiter` class.

What this spec **adds**:
- 4 falsifiable gate functions + their test fixtures
- 1 `BOT_TO_BOT_ENABLED` env flag + 1 `/kill bot-to-bot` operator command

**Net LOC estimate post-impl:** +~250 (gates + tests), -~80 (consolidated rate-limit), net +170 LOC. Cognitive-debt acceptable because gates are isolated module, not woven through hot path.

## Plan (step 5 — architecture)

```
tools/bot_to_bot_gates.py (NEW, ~120 LOC)
  │
  ├─ class LoopDepthGate:
  │     - Reads conversation thread for `via-bot` markers
  │     - count(via-bot) >= N → reject; else stamp with new via-bot marker
  │     - default N=2; configurable via SPEC env BOT_TO_BOT_MAX_DEPTH
  │
  ├─ class DedupeGate:
  │     - key = sha256(sender_bot_id + recipient_bot_id + normalized_body)
  │     - LRU cache, W=5min TTL
  │     - reject if seen
  │     - persistent to pages/systems/bot-to-bot-dedupe.json
  │
  ├─ class RateLimitGate:
  │     - Token bucket per (sender_bot_id, chat_id)
  │     - K=6 tokens/min default, configurable
  │     - reject when bucket empty
  │
  ├─ class KillSwitchGate:
  │     - reads env BOT_TO_BOT_ENABLED (default false)
  │     - reads pages/systems/bot-to-bot-runtime-override.json for `/kill` flag
  │     - both must be true→true to allow send; ANY false → reject
  │
  └─ pipeline(): gate the 4 in series, short-circuit on first reject; emit
                 ledger entry to pages/systems/bot-to-bot-ledger.jsonl

tools/command_center.py — call pipeline() before any bot-bot send
                          (NEW: detect target chat_id is a bot, NOT a human)

tools/tests/test_bot_to_bot_gates.py (NEW, ~150 LOC)
  - synthetic loop: assert reject at depth N+1
  - duplicate replay: assert reject within W
  - 7 sends in 1min: assert 6 pass + 1 reject
  - kill-switch toggles: assert all blocked when off
```

### Files

- **New**: `tools/bot_to_bot_gates.py` (~120 LOC), `tools/tests/test_bot_to_bot_gates.py` (~150 LOC)
- **New**: `pages/systems/bot-to-bot-dedupe.json`, `pages/systems/bot-to-bot-runtime-override.json`, `pages/systems/bot-to-bot-ledger.jsonl`
- **Modify**: `tools/command_center.py` — pipeline check before `_send_telegram_message()` if target is bot
- **Modify**: `pages/skills/command-center/SKILL.md` — fold AP-50 (bot-to-bot gate doctrine)
- **Modify**: `~/Library/LaunchAgents/com.nous.telegram-poll.plist` — add `BOT_TO_BOT_ENABLED=false` to `EnvironmentVariables`

### Deletion candidates (Musk step 2)

- Inline rate-limit retry loops in `telegram_poll.py:_send_with_retry()` — fold into `RateLimitGate` once consolidated.
- Manual `if sender == bot:` guards if any exist — pipeline replaces them.

## Tasks (step 6 — Spec-Kit ordered)

- [ ] **T1** — Madi answers Clarify Q1-Q4
- [ ] **T2** — Codex-1 (command-center scope holder) writes `tools/bot_to_bot_gates.py` with 4 gate classes
- [ ] **T3** — Codex-1 writes `tools/tests/test_bot_to_bot_gates.py` (4+ test fixtures, one per gate failure mode)
- [ ] **T4** — Codex-1 wires pipeline into `command_center.py` send-to-bot path
- [ ] **T5** — Opus AP-36 counter-check: run tests, verify all 4 gates trigger expected failure
- [ ] **T6** — Codex-1 folds AP-50 into `command-center/SKILL.md`, bumps version, gbrain-timeline-ok
- [ ] **T7** — Madi runs canary: enable BOT_TO_BOT_ENABLED in plist for 1 hour, watch ledger
- [ ] **T8** — 7-day soak with telemetry; if zero false-rejects + zero loop-escapes, promote (step 10)

## Canary (step 7 — deferred until T7)

Canary plan: enable on a single test chat (Madi's `chat_id=110793056` only, NOT Satory group `-1002064137259`) for 1 hour. Verify:
- Synthetic loop attempt (Madi triggers bot A → bot B via slash command) terminates at N=2 exactly
- Duplicate replay within 5min rejected
- 7+ sends in 1min: 7th rejected
- Toggle `BOT_TO_BOT_ENABLED=false` mid-canary: next bot-bot send blocked

## Proof (step 8 — falsifiable gates)

Pre-merge gates (must all pass before T6):
- ✅ `python3 -m pytest tools/tests/test_bot_to_bot_gates.py -q` → 4+ tests GREEN
- ✅ `grep -n 'BOT_TO_BOT_ENABLED' tools/bot_to_bot_gates.py tools/command_center.py ~/Library/LaunchAgents/com.nous.telegram-poll.plist` → all 3 places reference the flag
- ✅ Karpathy 6-axis score on bot_to_bot_gates.py: avg ≥1.5/2.0
- ✅ `tools/test_musk_step_2.sh tools/bot_to_bot_gates.py` → net LOC delta documented or `delete-considered:` annotation present

## Skill/gbrain/OpenBrain sync (step 9 — at T6)

- `pages/skills/command-center/SKILL.md` v2.12.24 → v2.12.25 with AP-50 (Symptom/Root cause/Rule/Detector/Recovery format)
- `mcp__gbrain__add_timeline_entry slug="pages/skills/command-center/skill" date="2026-05-XX"` via VPS CLI fallback
- OpenBrain capture: `mcp__claude_ai_Open_Brain__capture_thought` with this spec URL + Madi's verbatim residual

## Promotion (step 10 — at T8)

After 7-day canary soak with telemetry GREEN, flip `BOT_TO_BOT_ENABLED=true` in production plist. Acceptance criteria below must all hold.

## Acceptance criteria (binding, falsifiable)

1. **Loop terminates at depth N exactly** — synthetic fixture asserts depth=N+1 send rejected with `ERR_LOOP_DEPTH`.
2. **Dedupe window correct** — same (sender, recipient, body) within W=5min rejected with `ERR_DEDUPE`; same after W+1s passes.
3. **Rate cap holds under burst** — 7 sends in 60s yield 6 OK + 1 `ERR_RATE_LIMIT`.
4. **Kill-switch authoritative** — toggle off → next send rejected with `ERR_KILL_SWITCH` regardless of other gates.
5. **No state corruption during canary** — operator inbox classifications unchanged after 1h canary (`diff pages/inbox/2026-MM-DD/ pre/post canary`).
6. **Ledger captures every reject** — `wc -l pages/systems/bot-to-bot-ledger.jsonl` increments by exact count of rejects in test run.
7. **Kill-switch survives bot restart** — `launchctl unload && launchctl load com.nous.telegram-poll.plist` while flag=false → restart respects flag.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Loop-depth false-positive on operator-initiated chain | Med | Med | Operator-bypass via `/handoff` slash command resets depth=0 |
| Dedupe collision on legitimate retransmits (e.g., network retry) | Low | Low | Include `idempotency_key` field in send context; same key bypasses dedupe |
| Rate-limit too strict, blocks legitimate factory comms | Med | Med | Configurable K via env; observability ledger flags 95th percentile send rate per chat |
| Kill-switch file race (read mid-write) | Low | Low | Atomic file write (tmp + rename), fsync before send check |
| BOT_TO_BOT_ENABLED accidentally true in dev plist | Med | High | Pre-commit hook rejects plist diff that enables flag without `bot-to-bot:` annotation |

## Rollback path

1. `launchctl unload com.nous.telegram-poll.plist; sed -i '' 's/BOT_TO_BOT_ENABLED=true/BOT_TO_BOT_ENABLED=false/' plist; launchctl load plist` → flag off.
2. Worst-case nuclear: revert `command_center.py` to commit before pipeline call → bot-bot send path disabled entirely.
3. Ledger `pages/systems/bot-to-bot-ledger.jsonl` retained for forensics; nothing destructive.

## See also

- `[[HANDSHAKE-2026-05-19-residuals-onebyone-codex-opus-1822]]` — parent residual queue (R1)
- `[[2026-05-19-nous-operating-loop-design]]` — 10-step ladder governing this spec
- `[[skills/command-center]]` v2.12.24 — AP-50 fold target
- `[[AP-46-CREDS-OWNER-FORWARD-DOCTRINE-2026-05-19]]` — sibling Opus doctrine (operator-discipline)
- `[[skills/musk-algorithm]]` v1.4.0 — step-4 cognitive-debt guard applied above
- `[[MISSION-2026-05-19-always-on-satory-ai-factory]]` — parent mission rule 6 (Telegram behavior)

## Timeline

- **2026-05-19 18:22 KZT** — Madi delivered residual R1 in 4-residual handshake. Opus claimed.
- **2026-05-19 18:25 KZT** — This spec authored by Opus lane. Pre-action handshake: pages/specs/ Opus exclusive, no peer overlap. Awaiting Madi greenlight on Clarify Q1-Q4 before T2 fires.
