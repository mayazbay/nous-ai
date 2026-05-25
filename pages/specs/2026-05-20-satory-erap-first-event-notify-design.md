---
type: spec
id: SPEC-2026-05-20-satory-erap-first-event-notify-design
title: "Satory/ERAP first-event-notify handler — observer→operator-ping when Denis's egress goes live"
date: 2026-05-20
status: ready-for-impl
owner: claude-opus-4-7
priority: p1-bdl-cerebro-R4
tags: [spec-kit, satory, erap, bdl, cerebro, first-event, notify, asyl, denis, telegram, observer-mode, R4]
related:
  - [[HANDSHAKE-2026-05-20-bdl-cerebro-external-blocker-opus-codex-0815]]
  - [[skills/command-center]]
  - [[skills/factory-orchestration-policy]]
---

# Satory/ERAP first-event-notify spec

R4 of the BDL/Cerebro residual handshake. Asyl directive 2026-05-20 12:39 KZT (msg_id 1795):

> "Тебе Денис построить маршрут, только ты сразу в Ерап не отправляй события. Дай знать как начнет что-то приходить"

Translation: Denis is building the egress route. Bot must NOT auto-send events to ERAP. Bot MUST notify Asyl when events start arriving (observer-only mode until Asyl explicitly greenlights forward-routing).

## Constitution

- Asyl is the operator-of-record for ERAP routing in Satory ВКО
- Denis is building the egress (incoming events FROM Satory infrastructure TO Nous bot/ERAP)
- Bot stays OBSERVER until operator (Asyl) explicitly flips to forward-routing mode
- First event arrival = operator-visible signal (Telegram message to Asyl)
- AP-41 holds: no creds in group; AP-39 redaction on first-event content before any persistence

## Specify

A small handler in `tools/satory_erap_observer.py` (NEW file, ~80 LOC):

**Inputs**:
- Stream/file/HTTP endpoint where Denis's route will deposit incoming events
- Operator chat_id (Asyl: needs lookup or Madi DM-relay) + handle (@aliakbar_asylbek)
- "First event" detection state file: `pages/systems/satory-erap-observer-state.json`

**Behavior**:
1. **Pre-greenlight (observer mode)** — current state:
   - Watch Denis's egress endpoint for any HTTP POST or file write
   - On FIRST event: append to `pages/systems/satory-erap-observer-events.jsonl` (AP-39 redacted)
   - SEND Telegram to Satory group OR Madi DM: `📨 Первое событие пришло от Denis маршрута — посмотри: <ts>`
   - Set state.first_event_received_at = <ISO timestamp>
   - DO NOT forward to ERAP. DO NOT auto-process beyond capture.
2. **Subsequent events** (after first):
   - Capture to ledger silently (no Telegram per event)
   - State.event_count++
   - If event_count crosses threshold (default 10), send compact digest to Asyl: `📊 N событий получено с момента <first_ts>; форвардинг в ЕРАП всё ещё OFF`
3. **Post-greenlight (Asyl flips switch)** — future state, NOT in scope of this spec:
   - Asyl sends `/erap-forward on` (or similar) — Codex's command-center wires the toggle
   - Forward-mode starts routing events to ERAP after AP-39 redaction
   - Out of scope for R4; this spec only covers observer→first-event-notify

## Clarify (Madi-decision items)

1. **Recipient of first-event ping**: Satory group `-1002064137259` OR Madi DM `110793056`? Recommend **Satory group** since Asyl is the operator and asked to be told; group means Asyl sees it on Madi's behalf.
2. **Denis egress format**: HTTP POST endpoint? Local file write? Recommend ask Asyl/Denis when they're ready; spec accommodates both via pluggable adapter pattern (`tools/satory_erap_adapters/`).
3. **Redaction scope**: AP-39 redactor handles passwords/tokens. Should we also redact license plates / vehicle IDs / personal IDs in observer ledger? Recommend **YES** by default per Satory tenant-isolation doctrine; operator can disable per-event with `--no-redact` flag.
4. **Threshold for digest ping** (after first): default 10 events. Recommend **yes** until Asyl tunes.

## Musk delete/reduce

What this spec **deletes**:
- The risk of auto-routing events to ERAP without Asyl's confirmation (Asyl explicitly flagged this risk at 12:39)
- The need for Madi to manually check on Denis's progress (notify-on-first-event is the trigger)

What this spec **adds**:
- 1 new tool (`tools/satory_erap_observer.py`)
- 1 new ledger (`pages/systems/satory-erap-observer-events.jsonl`)
- 1 new state file (`pages/systems/satory-erap-observer-state.json`)

Net: 1 tool, 2 state files, fault-tolerant (soft-fail on Telegram or Denis-endpoint failure; ledger is local-first).

## Plan

### Files

- `tools/satory_erap_observer.py` (NEW, ~80-100 LOC) — main observer loop + first-event detector
- `tools/satory_erap_adapters/__init__.py` + `tools/satory_erap_adapters/http_post.py` + `tools/satory_erap_adapters/file_watch.py` — pluggable ingest adapters (similar pattern to daily_evolution_adapters/)
- `pages/systems/satory-erap-observer-state.json` (NEW; created on first run)
- `pages/systems/satory-erap-observer-events.jsonl` (NEW; appended per event)
- `tools/tests/test_satory_erap_observer.py` (NEW, ~80 LOC, mock-only)

### Adapter contract (pluggable per Denis's chosen format)

```python
class ErapEgressAdapter(Protocol):
    def name(self) -> str: ...
    def watch(self) -> Iterator[dict]: ...  # yields event dicts as they arrive
```

For HTTP POST adapter: lightweight HTTP server on Air, port TBD by Asyl/Denis.
For file-watch adapter: inotify-equivalent on a directory Denis writes to.

### Wire-up

Standalone CLI:
```
python3 tools/satory_erap_observer.py --adapter http_post --port 9988
python3 tools/satory_erap_observer.py --adapter file_watch --dir /tmp/denis-egress
```

Launchd job (Codex's lane): `com.nous.satory-erap-observer.plist` — runs at boot, restarts on crash.

### Telegram message format (Russian, operator-friendly)

**First event**:
```
📨 Первое событие пришло от маршрута Denis — посмотри ленту:
ts: <ISO timestamp>
event_id: <id-or-hash>
adapter: <http_post|file_watch>
АP-39 redaction: applied
Форвардинг в ЕРАП: OFF (observer-only).
@aliakbar_asylbek, отправь /erap-forward on когда готов запустить.
```

**Threshold digest** (default every 10 events):
```
📊 N событий получено от маршрута Denis с момента <first_ts>.
Форвардинг в ЕРАП: OFF.
Ledger: pages/systems/satory-erap-observer-events.jsonl
```

## Tasks

- [ ] **T1** — Madi answers Clarify Q1-Q4
- [ ] **T2** — Madi confirms Denis's egress format (HTTP / file / other) before adapter impl
- [ ] **T3** — Opus implements `tools/satory_erap_observer.py` + 2 adapters + tests
- [ ] **T4** — Codex wires `com.nous.satory-erap-observer.plist` launchd on Air (his lane)
- [ ] **T5** — Asyl canary: Denis fires one synthetic event → observer captures → Telegram notify lands within 5s
- [ ] **T6** — 24h soak; threshold digest fires correctly at 10/20/30 events; no auto-ERAP-forward
- [ ] **T7** — When Asyl flips `/erap-forward on` (future Codex impl), this spec's scope ends; new spec for forward-mode

## Canary

T5: Asyl/Denis fires ONE event from inside Satory perimeter; observer captures + Telegram lands in Satory group.

## Proof gates (pre-T6)

1. ✅ First event triggers Telegram within 5s
2. ✅ Subsequent events DON'T fire Telegram per-event
3. ✅ Threshold digest fires exactly at the configured count (10 default)
4. ✅ Zero events forwarded to ERAP (no auto-send code paths exist)
5. ✅ AP-39 redaction applied — synthetic event with `password=secret123` in body → ledger entry has `password=[REDACTED]`
6. ✅ Observer survives Telegram outage (capture continues to local ledger)

## Skill/gbrain/OpenBrain sync (at T4)

- `pages/skills/factory-orchestration-policy/SKILL.md` AP fold for observer-mode doctrine
- gbrain timeline entry on factory-orchestration-policy skill
- OpenBrain capture: this spec URL + first observed event metadata (sans content)

## Acceptance criteria

1. Observer captures first event from Denis's egress
2. Telegram first-event ping lands in chosen recipient (Satory group OR Madi DM per Q1)
3. Zero events forwarded to ERAP (passes proof gate #4)
4. AP-39 redaction holds for synthetic high-risk event
5. 24h soak: ≤ 1 false-positive (i.e., notify fired without real event)
6. Asyl explicitly acknowledges receipt of first-event ping in Telegram

## Rollback path

`launchctl unload com.nous.satory-erap-observer.plist && rm -f pages/systems/satory-erap-observer-state.json`. Observer stops; no other system affected.

## See also

- `[[HANDSHAKE-2026-05-20-bdl-cerebro-external-blocker-opus-codex-0815]]` — parent BDL residual handshake (R4)
- `[[skills/command-center]]` — Codex's eventual host for `/erap-forward on` toggle (out of scope for this spec)
- `[[skills/factory-orchestration-policy]]` — observer-mode AP fold target

## Timeline

- **2026-05-20 12:39 KZT** — Asyl msg 1795 directive: Denis builds route, observer-only until Asyl flips switch
- **2026-05-20 12:43 KZT** — Bot AP-44 routed Asyl + replied (bot_msg_id 1796)
- **2026-05-20 12:55 KZT** — This R4 spec authored by Opus. Awaiting Madi Q1-Q4 + Denis's egress format confirmation before T3 impl.
