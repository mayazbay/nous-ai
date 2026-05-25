---
type: spec
id: SPEC-2026-05-20-telegram-consult-command-design
title: "/consult Telegram slash command — wrap multi-model-consult skill for iPad-only mode"
date: 2026-05-20
status: ready-for-codex-impl
owner: claude-opus-4-7
priority: p0-ipad-only-unblocker
tags: [spec-kit, telegram, consult, multi-model-consult, command-center, ipad-only, codex-lane-impl]
related:
  - [[2026-05-19-multi-model-consult-skill-design]]
  - [[HANDSHAKE-2026-05-20-ipad-only-presidential-7-day-plan-0820]]
  - [[skills/command-center]]
  - [[skills/ceo-hierarchy]]
---

# /consult Telegram command spec

Day 4 of the 7-day iPad-only ladder. Codex lane impl (command_center.py). This spec is the Opus drop-in — Codex applies + ships.

## Constitution

Madi 2026-05-20 ~10:15 KZT: "work with gpt and grok" — use multi-model-consult LIVE for planning. Currently Mac-only invocation; for iPad-only mode Madi needs Telegram-fired multi-model brain.

Cross-model consult on the spec itself (consult_id `81df9bac`): Opus won, $0.1008 total, Codex transient-unavailable. Opus's recommendation captured below.

## Specify

`/consult <question>` Telegram slash command in `@nousAGaaSbot`:
1. Madi (or any allowed sender) sends `/consult <question>` from iPhone.
2. Bot acks immediately: `🧠 consulting CEO panel…` (threaded reply via `reply_to_message_id`).
3. Bot spawns `tools/multi_model_consult.py --question "..." --output-file /tmp/consult_<id>.json` subprocess.
4. On completion (~30s), bot sends final reply with: winner answer + winner model + agree/dissent count + total cost.
5. On timeout (>180s), bot sends `⏱ /consult timed out (>180s); see /tmp/consult_<id>.json on Air`.
6. On cost-cap exceeded, bot sends `💰 cost cap $0.05 hit; winner answer truncated below` + partial result.

## Clarify (Madi-decision before T1 fires)

1. **Allowlist**: who can call `/consult`? Recommend **Madi DM (chat_id=110793056) only** initially; later widen to Satory group after AP-44/45 gate validation.
2. **Cost cap per call**: recommend **$0.05** (3× p95 of observed $0.005-$0.016 envelope; one $0.10 outlier observed today on long-format question). Hard-fail or truncate? Recommend **truncate** (return partial answer with cost note).
3. **Group routing**: should `/consult` work in Satory group too? Recommend **NO** initially — group is operator-facing, consults are CEO judgment. Add later if needed.
4. **Threading**: confirm threaded reply (`reply_to_message_id=msg_id`) — Opus's recommendation. Easier to scroll back through consult history in Telegram.

## Musk delete/reduce

What this **deletes**:
- Need to run multi_model_consult.py from Mac terminal — can fire from iPhone now
- Implicit "ask Opus → ask Codex → ask Grok manually" cognitive load on Madi

What this **adds**:
- ~30 lines in `command_center.py`
- 1 line in `/help` reply
- 1 entry in command dispatch table

**Net cognitive debt**: low. Single new slash command, isolated handler, doesn't change any existing route.

## Plan (Opus's design via multi-model-consult `81df9bac`)

### Hook location
`tools/command_center.py` — wherever `/ask`, `/codex`, `/code` are registered. Same command dispatch table.

### ~30-line patch shape

```python
# tools/command_center.py

import asyncio
import shlex
import subprocess
import time
from pathlib import Path

CONSULT_TIMEOUT_S = 180           # Opus + Grok + DeepSeek arbitration is slow
CONSULT_COST_CAP_USD = 0.05       # ~3x p95 of observed envelope

async def handle_consult(chat_id: int, msg_id: int, sender: str, prompt: str) -> None:
    if not prompt.strip():
        await _send_telegram_message(
            chat_id, "Usage: /consult <question>", reply_to=msg_id
        )
        return

    # ACK (threaded reply)
    await _send_telegram_message(chat_id, "🧠 consulting CEO panel…", reply_to=msg_id)
    t0 = time.time()

    # Spawn the consult subprocess
    consult_id_path = f"/tmp/consult_{int(time.time())}.json"
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "tools/multi_model_consult.py",
            "--question", prompt,
            "--output-file", consult_id_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=CONSULT_TIMEOUT_S)
    except asyncio.TimeoutError:
        await _send_telegram_message(
            chat_id,
            f"⏱ /consult timed out (>{CONSULT_TIMEOUT_S}s); see {consult_id_path} on Air",
            reply_to=msg_id,
        )
        return

    reply = _format_consult_reply(consult_id_path, elapsed=time.time() - t0)
    await _send_telegram_message(chat_id, reply, reply_to=msg_id, parse_mode="Markdown")


def _format_consult_reply(json_path: str, elapsed: float) -> str:
    """Format the consult JSON for compact Telegram display."""
    import json
    with open(json_path) as f:
        d = json.load(f)
    answer = d.get("actionable_answer", "(no answer)")[:3500]
    winner = d.get("arbitration", {}).get("winner_model", "none")
    agree = d.get("arbitration", {}).get("agree_count", 0)
    cost = d.get("total_cost_usd", 0)
    unavail = d.get("model_unavailable", [])
    return (
        f"*🧠 CEO consult result* (~{elapsed:.0f}s)\n"
        f"Winner: `{winner}` ({agree}/3 agree)\n"
        f"Cost: ${cost:.4f}\n"
        f"Unavailable: {unavail or 'none'}\n\n"
        f"{answer}"
    )
```

### Dispatch table line

```python
# In the command dispatch dict:
"/consult": handle_consult,
```

### `/help` reply update

```
/consult <q>  — fire multi-model CEO panel (Opus + Codex + Grok + DeepSeek arbitrator)
```

## Tasks

- [ ] **T1** — Madi answers Clarify Q1-Q4 (allowlist, cost cap, group routing, threading default).
- [ ] **T2** — Codex applies the ~30-line patch to `tools/command_center.py` (his lane scope).
- [ ] **T3** — Codex adds 1+ test in `tools/test_command_center.py` covering handle_consult dispatch + timeout path.
- [ ] **T4** — Codex bumps `pages/skills/command-center/SKILL.md` with AP-51 noting the consult hook.
- [ ] **T5** — Madi runs canary: `/consult test ping` from iPhone DM → expects threaded reply within 60s.
- [ ] **T6** — Opus AP-36 counter-check: verify cost ledger entry appended to `pages/systems/multi-model-consult-ledger.jsonl` per fired consult.
- [ ] **T7** — 7-day soak: track consult-per-day count + cost via ledger; promote allowlist to Satory group if `/consult` proves operator-safe.

## Canary

Madi's DM chat (chat_id=110793056) only for T5. NOT Satory group. Single user, single tier.

## Proof (falsifiable gates pre-T4)

- ✅ Allowlist gate works: `/consult` from non-Madi chat_id rejected with "not allowed"
- ✅ Threaded reply lands: bot reply has `reply_to_message_id` matching the user's msg
- ✅ Cost cap enforced: synthetic high-cost consult truncated at $0.05
- ✅ Timeout fires: synthetic 200s consult triggers timeout branch
- ✅ Ledger captures every fire: 5 consults → 5 jsonl lines

## Skill/gbrain/OpenBrain sync (at T4)

- `pages/skills/command-center/SKILL.md` AP-51 fold (Codex's lane)
- gbrain timeline entry via the VPS substrate-CLI (Codex uses gbrain-timeline-ok marker)
- OpenBrain capture: this spec URL + first 3 production consult ids

## Acceptance criteria (binding, falsifiable)

1. `/consult test` from Madi DM → bot replies within 90s with winner + cost + answer
2. `/consult` from non-allowlisted chat → bot rejects without firing subprocess
3. 10 consecutive `/consult` calls → 10 ledger entries; total spend < $1
4. Cost-cap synthetic test: 200% over-budget consult triggers truncation + cost-note in reply

## Rollback path

`launchctl unload com.nous.telegram-poll && remove handle_consult from dispatch + reload`. `/consult` simply unregisters; no other route affected. Existing `/ask` / `/codex` / `/code` continue to work.

## See also

- `[[2026-05-19-multi-model-consult-skill-design]]` — sibling spec, parent of the wrapped skill
- `[[skills/multi-model-consult]]` v1.0.0 — the impl this command wraps
- `[[HANDSHAKE-2026-05-20-ipad-only-presidential-7-day-plan-0820]]` — parent 7-day ladder (Day 4)
- `[[skills/command-center]]` — Codex's impl scope target (AP-51 fold)
- `[[skills/ceo-hierarchy]]` — CEO/cheap-labor tier doctrine

## Timeline

- **2026-05-20 10:15 KZT** — Madi: "work with gpt and grok" (use multi-model-consult live for planning)
- **2026-05-20 10:16 KZT** — Opus fired multi-model-consult on /consult wiring design (consult_id 81df9bac, winner=opus-4-7, $0.1008, Codex transient-unavailable)
- **2026-05-20 10:18 KZT** — This spec authored by Opus from Opus's consult answer + tightened to Spec-Kit format. Ready for Codex impl on his next command-center cycle.
