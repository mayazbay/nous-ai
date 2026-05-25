---
tier: 2
type: skill
name: bdl-cerebro-replacement-gate
id: SKILL-BDL-CEREBRO-REPLACEMENT-GATE
version: 1.4.0
last_updated: 2026-05-25
status: active
description: "v1.4.0 - BDL/Cerebro replacement proof gate doctrine. Codifies the 9-check + 2-rollup proof gate (tools/bdl_cerebro_replacement_gate.py), the receipt-JSON green-flip protocol (pages/systems/satory-bdl-external-proof-receipt.json), the operational escalation runner (tools/satory_bdl_external_blocker_ping.py + Mon-Fri 08:00 KZT LaunchAgent), and the single load-bearing unblock path: Asyl PSK / endpoint proof OR Denis HTTP-200 egress probe from inside Satory. v1.1.0 closes AP-4 residual #3: ping template is now Russian (Cyrillic Асыл/Денис; technical tokens HTTP-200/BDL/Cerebro/PSK/KZT/proof gate retained in English) because the Satory operators group is Russian-first; AP-5 codifies audience-language discipline per [[session-operating-contract]] Rule 13. v1.2.0 codifies AP-6: gate-check state transitions must land in skill Timeline same-session — closes the drift class observed 2026-05-25 when data plane transitioned RED→GREEN between AUDIT-2026-05-15 and the live gate run, leaving the skill body implying data plane was still the blocker. v1.3.0 codifies AP-7: column-sum gate checks must apply per-row freshness filter — closes the silent-failure class where 38 stale-online rows propped fleet_health at YELLOW for 20+ days while ground truth was 0 online (AUDIT-fleet-zero-online-20day-silent-outage-2026-05-25). v1.4.0 extends AP-7 to the other 3 vulnerable column-sum checks audited the same session: raw_intake (parsed/quarantined SUMs now filtered by received_at), law002_classification (count split into count_total + count_fresh), erap_queue (per-status counts split into count_total + count_fresh). _event_ingestion_check was already CLEAN (MAX-only). Substrate gap closer: prior to this skill, doctrine lived only in tools/ code + 4 dated audit docs; now retrievable as a single skill page. Use when Madi asks 'is the Satory replacement done', 'BDL gate', 'Cerebro gate', 'flip the receipt', 'why is BDL still RED', or schedules anything that should escalate the external-proof blocker."
triggers:
  - "BDL/Cerebro replacement"
  - "Satory replacement gate"
  - "flip the receipt"
  - "BDL still RED"
  - "Cerebro still RED"
  - "Asyl PSK"
  - "Denis HTTP-200 egress"
  - "satory-bdl-external-proof-receipt"
tools: [Bash, Read, mcp__gbrain__*]
mutating: true
related: [control-plane-sync, library-grade-audit, satory-daily-operator-brief, satory-dashboard, session-coordination]
absorbs_lessons: []
tags: [skill, satory, bdl, cerebro, replacement, proof-gate, asyl, denis, escalation, ping, launchd]
title: "bdl-cerebro-replacement-gate v1.4.0"
---

# bdl-cerebro-replacement-gate v1.4.0

## Purpose

Madi asks variants of *"is the Satory BDL/Cerebro replacement done? what's blocking it?"* repeatedly. Each agent rediscovers the same diagnosis chain by reading audit-2026-05-15 → audit-2026-05-16 → gate code → receipt JSON. This skill codifies the chain so the substrate inherits it.

**Output of the gate:** GREEN means BDL+Cerebro are truthfully replaceable. RED means at least one of (data plane, fleet, classification, queue, external proof) is unproven. There is no aggregate-dashboard substitute.

## Architecture

```
Satory cameras / APK
   |
   v (transport — unproven, awaiting external proof)
VPS listener :9080  ──┐
operator portal :8090 ─┼─→ tools/bdl_cerebro_replacement_gate.py --json
sqlite events.db ──────┘     |
                             v
                        9 checks + 2 rollups + replacement_definition
                             |
                             v
                        overall: RED/YELLOW/GREEN
```

## Runtime contract

- Gate predicate: `tools/bdl_cerebro_replacement_gate.py` (read-only verifier, SSH-queries VPS sqlite or accepts local fixtures via `--fixture-events-db/--fixture-health-db/--fixture-queue-db`)
- Receipt: `pages/systems/satory-bdl-external-proof-receipt.json` (JSON file the human flips to flip the gate check GREEN)
- Allowed external proof sources (set in code, `ALLOWED_EXTERNAL_PROOF_SOURCES`): `asyl_psk`, `asyl_endpoint_proof`, `denis_http_200_egress_probe`
- Escalation runner: `tools/satory_bdl_external_blocker_ping.py` (Mon-Fri 08:00 KZT only by default, sends Telegram group message via `tools/tg_send.sh --chat $TELEGRAM_GROUP_CHAT_ID`)
- LaunchAgent: `com.nous.satory-bdl-external-blocker-ping` on Air; plist at `tools/launchd/com.nous.satory-bdl-external-blocker-ping.plist`
- Uninstall: `tools/uninstall_satory_bdl_external_blocker_ping.sh`
- Tests: `tools/tests/test_bdl_cerebro_replacement_gate.py`, `tools/tests/test_satory_bdl_external_blocker_ping.py`

## The 9 gate checks + 2 rollups

| # | Check | GREEN means |
|---|---|---|
| 1 | `listener` | VPS health :9080 returns HTTP 200 with `OK` |
| 2 | `operator_portal` | Spectra portal :8090 `/api/health` returns HTTP 200 |
| 3 | `event_ingestion` | `vehicle_events` latest row newer than `fresh_hours` (default 24h) |
| 4 | `raw_intake` | `raw_events parsed > 0` recently (quarantined-only = YELLOW, not GREEN) |
| 5 | `fleet_health` | ≥ 85% of `camera_status` rows show `online=1` with `latest_check < health_fresh_hours` (default 2h) |
| 6 | `law002_classification` | At least 1 LAW-002-classified violation against a fresh event |
| 7 | `erap_queue` | `submission_queue` has state transitions newer than `fresh_hours` |
| 8 | `external_proof_receipt` | Receipt JSON `status == received` AND `source` in allowed set AND `evidence`, `received_at` populated |
| 9 | `bdl_replacement` (rollup) | All 8 above are GREEN |
| 10 | `cerebro_replacement` (rollup) | `bdl_replacement` is GREEN |

**Gate is the source of truth.** Do not build parallel "is replacement done?" surfaces (dashboards, Notion mirrors, Telegram digests) that can disagree with the gate. See AP-1.

## How to flip the gate GREEN (receipt protocol)

When Asyl delivers PSK + endpoint proof OR Denis delivers HTTP-200 egress probe from inside Satory:

```bash
# Edit pages/systems/satory-bdl-external-proof-receipt.json (Mac vault) — example for Denis path:
cat > pages/systems/satory-bdl-external-proof-receipt.json <<'JSON'
{
  "status": "received",
  "source": "denis_http_200_egress_probe",
  "received_at": "2026-05-19T11:32:00+05:00",
  "owner": "Denis",
  "evidence": "curl -v --max-time 5 http://65.108.215.200:9080/health from Satory ops laptop -> HTTP/1.1 200 OK / body {\"status\":\"ok\"}",
  "http_status": 200,
  "endpoint": "http://65.108.215.200:9080/health",
  "requested_at": "2026-05-17T11:17:00+05:00",
  "instructions": "Flip status to received only after Asyl provides PSK/endpoint proof or Denis provides an HTTP-200 egress probe from inside Satory."
}
JSON
git add pages/systems/satory-bdl-external-proof-receipt.json
git commit -m "satory: flip BDL/Cerebro external-proof receipt to received (Denis HTTP-200 egress)"
git push vps main && git push github main

# Then verify:
python3 tools/bdl_cerebro_replacement_gate.py --json | jq '.checks[] | select(.check=="external_proof_receipt") | .status'
# expect: "GREEN"
```

For Asyl PSK path use `"source": "asyl_psk"` (or `"asyl_endpoint_proof"`) and put the PSK setup evidence in `evidence`. **Never commit the PSK itself** — point to a secret-bearing artifact (`raw/secrets-pending/asyl-psk-2026-05-NN.txt`) that's gitignored.

The receipt JSON is the ONLY mutation that flips `external_proof_receipt` GREEN. Any other "we got the proof" claim must be backed by this file.

## Operational state today (as of 2026-05-17)

```
overall=RED reds=4 yellows=4
listener                GREEN  HTTP 200 :9080
operator_portal         GREEN  HTTP 200 :8090
event_ingestion         RED    vehicle_events last_event=2026-04-05 age=997h+
raw_intake              YELLOW raw_events parsed=0 quarantined=9 (cameras pushing, parser rejecting)
fleet_health            YELLOW 38/281 cameras online (13.5%)
law002_classification   YELLOW 100 events classified, all stale
erap_queue              YELLOW 3 pending, oldest 60 days stale
external_proof_receipt  RED    status=requested
bdl_replacement         RED
cerebro_replacement     RED
```

**Diagnosis (from audit chain 2026-05-15 + 2026-05-16):** the 41-day `vehicle_events` drought is a *symptom* of the missing transport proof, not a separate fire. Cameras try to push (9 quarantined raw events confirm this). The parser quarantines because the transport (network path) isn't approved. Once Asyl PSK or Denis HTTP-200 lands, the parser config can be updated to accept the new transport, events flow, fleet/event/law002/erap checks all roll forward.

**The single load-bearing fact needed:** Asyl PSK + endpoint OR Denis HTTP-200 egress from inside Satory. That's it.

## Anti-Patterns

### AP-1 - Gate is the source of truth; do not invent parallel "replacement done" surfaces

Before this skill shipped, agents repeatedly built parallel "replacement status" claims — Notion mirrors, dashboard widgets, Telegram digests, "factory is GREEN therefore Satory is GREEN" deductions. The 2026-05-15 audit explicitly built `bdl_cerebro_replacement_gate.py` as the antidote: "intentionally stricter than 'website works' or 'OpenClaw healthy'... only turns GREEN when the actual replacement path is proven."

Rule: any surface that claims "BDL/Cerebro replaced" or "Satory data plane healthy" MUST quote the current `bdl_cerebro_replacement_gate.py --json` output. Surfaces that disagree with the gate are wrong by definition.

Detector: a future scanner (deferred) would grep `pages/audits/`, `pages/systems/`, and recent Notion/Telegram exports for "BDL replaced" / "Cerebro replaced" / "Satory green" + flag any instance not accompanied by the JSON gate output.

Source: [[AUDIT-bdl-cerebro-replacement-gate-2026-05-15]].

### AP-2 - The 41-day event drought is a symptom of the proof gap, not a separate parser fire

Agents (including this session in its first SP3 audit) misread the gate output and treat the 41-day `vehicle_events` drought as a separate problem requiring its own investigation (root-cause the parser, audit the APK upload pipeline, blame the cameras). This is wrong:

- Cameras ARE pushing (9 quarantined `raw_events` confirm)
- The parser IS doing its job (rejecting traffic via an unapproved transport)
- The fix is at the transport layer (PSK / HTTP-200), not the parser

Rule: do not propose investigating the parser, the APK upload code, or "what happened on 2026-04-05" as a separate workstream. The proof-receipt protocol IS the unblock. Skill AP-2 says: cite the audit chain, do not split workstreams.

Source: [[AUDIT-bdl-cerebro-replacement-gate-2026-05-15]] §"Next Physical Unblock", [[AUDIT-atomic-substrate-openbrain-bdl-2026-05-16-2207]] §"Root causes" point 1, [[SP3-BDL-PING-RESCOPED-2026-05-17]] §"Self-correction".

### AP-3 - Brain-first violation: read the audit chain before opining on the gate

The first SP3 audit (commit `7696c5a6`) was based on reading the gate code without first reading the 2 prior audits ([[AUDIT-bdl-cerebro-replacement-gate-2026-05-15]] + [[AUDIT-atomic-substrate-openbrain-bdl-2026-05-16-2207]]) that ALREADY established the diagnosis + remediation. It recommended a wrong path (investigate parser drought first). [[SP3-BDL-PING-RESCOPED-2026-05-17]] §"Self-correction" captures the correction.

Rule (extends CLAUDE.md BRAIN-FIRST RULE): for any topic that has dated audit docs in `pages/audits/`, read the most-recent dated audit on that topic BEFORE reading the underlying code, and BEFORE opining. The audit chain is the substrate's accumulated diagnosis; rediscovering it from code costs time and produces wrong recommendations.

Mechanical detector (deferred): a future linter would scan agent-session transcripts and flag any "let me read the code first" pattern when an audit doc dated within last 14 days exists for the same topic-tag.

### AP-4 - Ping fires only on workday window + only when proof not received + only when gate not GREEN; deferred residuals

Current `tools/satory_bdl_external_blocker_ping.py` fires Mon-Fri 08:00 KZT exactly (single launchd `StartCalendarInterval` per weekday). Stop condition: all 7 required checks GREEN. Override: `--force` for off-window manual test.

Deferred residuals (acknowledged in [[SP3-BDL-PING-RESCOPED-2026-05-17]] §"Residuals"):

1. **14-day circuit breaker** - if receipt has been `status: requested` for ≥14 days, stop pinging the group and instead send a single "escalation failed for 14 days" digest to Madi's DM. Prevents indefinite group spam.
2. **Atomic per-workday ledger** - currently relies on launchd firing exactly once per weekday. If the LaunchAgent is `kickstart -k`'d manually inside the workday, a second ping fires. Atomic ledger at `~/nous-agaas/logs/satory-bdl-blocker-ping-ledger.json` would dedupe.
3. **Russian-language message variant** ~~- current message is English. Satory operators are Russian-first. Add a `--lang ru` flag with a Russian message template referencing the same evidence/source/endpoint fields.~~ **CLOSED in v1.1.0 (AP-5).** Default template is now Russian (Cyrillic Асыл/Денис, technical tokens retained); flag-gated bilingual mode deferred because no current consumer needs English. Codified as AP-5 below.
4. **Verify `tg_send.sh` autonomy-gate (AP-4) doesn't block the live message** - dry-run doesn't exercise the gate. Need a Monday-08:00 first-fire counter-check + a fallback `named-author-required` hall-pass phrase in the message if the gate fires.

Backlog ticket (when picked up): bump this skill to v1.1.0 with new AP-5 codifying the chosen residual implementation. **CLOSED 2026-05-21 → AP-5 below.**

### AP-7 - Column-sum gate checks must apply per-row freshness filter (2026-05-25, v1.3.0)

**What happened:** `_fleet_health_check` summed `status='online'` across ALL `camera_status` rows including ones whose `last_check` was 55+ days stale. When the probe iteration set dropped subnet `10.235.X.X` (38 cameras) on or around 2026-03-31, those rows remained in the table with `status='online'` frozen at `last_check=2026-03-31`. The gate happily counted them as still online: `online_pct=38/281=13.5%` → YELLOW. The fleet_health YELLOW threshold (`<85%`) doesn't trip RED unless `total=0`. Ground truth (verified by ssh + sqlite query during AUDIT-fleet-zero-online-20day-silent-outage-2026-05-25): 0 cameras have current `last_check` AND `status='online'`. The fleet has been dark for at least 20 consecutive days. Probe runs every 5min reporting `online=0, offline=243` — but the gate's column-sum read the stale 38 and called it "current but degraded." Silent 20+ day revenue outage.

**Rule:** any column-sum gate check (`SUM(CASE WHEN status='X' THEN 1 ELSE 0 END)`) must add a per-row freshness clause matching the gate's overall freshness window: `... AND last_check >= '<now − fresh_hours>'`. The stale count gets surfaced in the detail string separately (`stale_online=N`) so operators see both "live ground truth" and "what's lurking in the table." A row whose `last_check` is older than the freshness window has UNKNOWN current status regardless of what its `status` column says — treat the cell as untrusted.

**Fix (shipped 2026-05-25, this commit):** `tools/bdl_cerebro_replacement_gate.py:_fleet_health_check` rewritten. SQL now returns three columns (total, online_fresh, stale_online) by inlining a `cutoff = now − health_fresh_hours` ISO timestamp. Detail string includes both. New RED tier: `online_fresh <= 0` returns RED with `"ZERO cameras online with current last_check"` — surfaces the silent-outage class regardless of how many stale rows linger. Backward-compatible with the existing `total<=0` and `age_h>fresh_hours` RED conditions. Verified post-change: overall went from RED 3 reds → RED 4 reds (fleet_health correctly upgraded YELLOW → RED).

**Detector (already-shipped sibling):** `tools/test_bdl_cerebro_skill_state_freshness.sh` (AP-6 mechanical detector from v1.2.0) continues to pass after this fix — it correctly recognizes fleet_health is in the Timeline. No new detector for AP-7 itself; the gate change IS the enforcement.

**v1.4.0 extension (2026-05-25, same session, follow-on Explore audit):** The same Explore audit was tasked with finding other column-sum checks in the file with the same bug shape. Result: 3 of 4 audited functions VULNERABLE (`_raw_intake_check`, `_law002_check`, `_erap_queue_check`), 1 CLEAN (`_event_ingestion_check` is MAX-only). Same fix pattern applied to all 3:
- `_raw_intake_check`: SUMs for `parse_status='parsed'` and `'quarantined'` now filtered by `received_at >= cutoff`. New `fresh_total` and `parsed_fresh` / `quarantined_fresh` columns surfaced; existing `total` retained for context. Live verify post-fix: GREEN `total=9135 fresh_total=1915 parsed_fresh=1915 quarantined_fresh=0` (1915 raw rows in last 2h, all parsed).
- `_law002_check`: COUNT now split into `count_total` (historical violations) + `count_fresh` (in fresh window). New RED tier `count_fresh <= 0` for the case where classification has stopped happening but historical violations still exist. Live verify: GREEN `count_total=1086 count_fresh=234`.
- `_erap_queue_check`: per-status COUNT now split into `count_total` + `count_fresh`. New YELLOW tier `fresh_total <= 0` for the "queue visible but ZERO fresh activity" case (the actual current state: 3 pending all from 2026-03-17 = 68d stale). Live verify: YELLOW `states={'pending': {'count_total': 3, 'count_fresh': 0}}; fresh_total=0; queue visible but ZERO fresh activity within 2.0h (all rows stale)`.

The rule generalizes: **any column-sum / column-COUNT / column-GROUP-BY-with-COUNT gate check that pairs with a separate `MAX(timestamp)` freshness signal must filter the row-level aggregation by the same per-row freshness condition.** Otherwise the aggregation reports historical state while the freshness signal reports "all good" — they describe different time horizons of the same data and a naive reader will conflate them.

**Cross-ref:** AP-6 (this skill — sibling discipline at the doctrinal layer, this one is at the code layer); [[session-operating-contract]] Rule 2 (ground-truth-over-recall — same anti-pattern at the always-on layer); [[karpathy-loop]] AP-4 (scorecard honesty); [[metrology-cert-tracker]] v1.2.0 AP-2 (sibling silent-failure class: schema-exists ≠ data-exists, here: row-exists ≠ row-fresh); AUDIT-fleet-zero-online-20day-silent-outage-2026-05-25 (the audit that surfaced this AP). No new LESSON (RULE ZERO).

### AP-6 - Gate-check state transitions must land in skill Timeline same-session (2026-05-25, v1.2.0)

**What happened:** Between AUDIT-bdl-cerebro-replacement-gate-2026-05-15 and the live gate run at 2026-05-25T05:21:55Z, four checks materially transitioned: `event_ingestion` RED (age_h=950, 41-day drought per AP-2) → GREEN (age_h=3.16, vehicle_events total=155517); `raw_intake` RED (parsed=0) → GREEN (parsed=9113/9135); `law002_classification` YELLOW (count=100 stale) → GREEN (count=1086, age_h=3); `fleet_health` YELLOW → YELLOW (still 38/281 online, 13.5%) — drought concept now applies to fleet uptime, not events. The doctrinal skill body at v1.1.0 still implied data plane was the blocker. Next agent reading the skill cold would have re-discovered the state via fresh gate run + audit reads — work already done two sessions earlier. Drift cost compounds across the (n-1) agents who don't read the gate first.

**Rule:** when ANY of the 9 checks transitions GREEN ↔ RED ↔ YELLOW, the skill Timeline gets a same-session entry naming the check, prior status, new status, evidence path (gate JSON snapshot OR commit hash that fixed it), and the resulting overall rollup state. The body sections that reference the old state (e.g. "data plane unproven") get reworded to the new reality with a bracketed `(as of YYYY-MM-DD)` qualifier so future drift is visible at a glance. The receipt JSON and the gate code itself are NOT touched by this rule — they are mechanical surfaces; this rule applies only to the doctrinal SKILL.md prose.

**Detector:** `tools/test_bdl_cerebro_skill_state_freshness.sh` (queued for slice-3) — runs `python3 tools/bdl_cerebro_replacement_gate.py --json`, parses per-check status, and asserts that for each check whose `status != "GREEN"` in the last 14d, the skill's most-recent Timeline entry from the same 14d window names that check or explicitly states "no transitions." Flags drift; classifier-AP, not hard-gate.

**Cross-ref:** [[session-operating-contract]] Rule 2 (ground-truth-over-recall — same anti-pattern at the always-on layer); [[karpathy-loop]] AP-4 (scorecard honesty — Timeline freshness IS the honesty signal at the skill layer); AP-2 (this skill — the 41-day drought of past tense; the transition to GREEN is the closure evidence for that AP); AP-3 (this skill — read the audit chain; this AP closes the loop by writing the transition INTO the skill so future agents don't repeat the chain-read). No new LESSON (RULE ZERO).

### AP-5 - Audience-language discipline: templated outbound matches recipient group's working language (2026-05-21)

**What happened:** AP-4 residual #3 (2026-05-17) deferred the Russian-language variant as backlog. On 2026-05-21 08:00 KZT the Mon-Fri ping fired the English template against the Satory operators group, which is Russian-first. Operators saw the English message and Madi escalated with "why is this again in eng? it must be in russian in that group". The deferred residual had become a production fire — exactly the cost SOC Rule 13b (scrub outbound; would I send this to a stranger) is meant to prevent at draft time, but here the script's output IS the outbound, so the test of "is this in the recipient's language" must be a mechanical assertion, not a vibe-check at deploy.

**Root cause class:** templated outbound emitted in a language different from the recipient group's working language. Same failure mode as AP-1 in other tenants would be (e.g. English message to a Russian APK reseller group, Russian message to an English Vercel ops channel). The fix isn't "translate this one message"; it's "make the template's audience-language a tested invariant".

**Rule:** any templated outbound (Telegram group ping, email blast, SMS) must:
1. Declare the recipient group's working language in the script's docstring / config.
2. Emit content in that language by default.
3. Have a unit test that asserts the language with positive markers (e.g. Cyrillic "Условие остановки:") AND negative markers (e.g. `"Stop condition:" not in message`) so language drift back to a default English template fails the test loudly.
4. If multi-language is needed, use an explicit `--lang` flag with a tested set of locales — not "default English, runtime translate".

**Proper-noun convention:** for Russian operators groups, address people in Cyrillic (Асыл, Денис, Мади) — matches their entity pages and Russian linguistic register. Technical tokens that operators recognize (HTTP-200, BDL/Cerebro, PSK, KZT, egress, proof gate, freshness) stay in English because translating them obscures the signal and may not match the codebase the operator is reading.

**Detector (mechanical, shipped this AP):** `tools/tests/test_satory_bdl_external_blocker_ping.py::test_message_names_asyl_denis_and_stop_condition` now asserts Cyrillic Асыл/Денис + "Условие остановки:" presence AND English `"Asyl:" / "Denis:" / "Stop condition: external-proof receipt"` absence. Future language-drift PR fails the test loudly.

**Cross-ref:** [[session-operating-contract]] Rule 13 (outbound correspondence + commercial-frame discipline), AP-4 above (residual #3 origin), [[satory-daily-operator-brief]] (sibling outbound surface — should be audited for the same class).

**Class detector (deferred):** future scanner would walk every `tools/*_ping*.py`, `tools/*_brief*.py`, `tools/*_digest*.py` for hardcoded English message strings without a corresponding Russian variant + test. Audit-and-fix in a single pass when shipped.

## Verification

### One-shot health check

```bash
python3 tools/bdl_cerebro_replacement_gate.py --json | jq '.overall, [.checks[] | {check, status}]'
```

### Run the ping in dry-run for testability

```bash
python3 tools/satory_bdl_external_blocker_ping.py --dry-run --json --now 2026-05-19T08:00:00+05:00
# expect: {"action": "would_send", "message": "...", "gate_overall": "RED"}
```

### Run the test suite

```bash
python3 -m pytest tools/tests/test_bdl_cerebro_replacement_gate.py tools/tests/test_satory_bdl_external_blocker_ping.py -q
```

### Inspect the LaunchAgent on Air

```bash
ssh air "launchctl print gui/\$(id -u)/com.nous.satory-bdl-external-blocker-ping" | head -30
```

## See also

- `tools/bdl_cerebro_replacement_gate.py` - the gate
- `tools/satory_bdl_external_blocker_ping.py` - the ping runner
- `tools/launchd/com.nous.satory-bdl-external-blocker-ping.plist` - LaunchAgent
- `pages/systems/satory-bdl-external-proof-receipt.json` - the receipt that flips the gate
- [[AUDIT-bdl-cerebro-replacement-gate-2026-05-15]] - original audit defining the gate
- [[AUDIT-atomic-substrate-openbrain-bdl-2026-05-16-2207]] - reaffirms unblock requirements
- [[SP3-BDL-PING-RESCOPED-2026-05-17]] - SP3 audit closure
- [[control-plane-sync]] v1.1.4 - upstream skill that owns the broader factory health
- [[satory-daily-operator-brief]] v1.2.2 - adjacent skill (camera-doctor daily 06:00 KZT)
- [[satory-dashboard]] - adjacent dashboard surface

## Musk Step-2 (skill creation)

musk-step-2: considered merging this skill into [[control-plane-sync]] (which already covers broader Satory ops). Rejected because (a) BDL/Cerebro gate is event-driven, not on the 3-hour control-plane cadence; (b) ownership is distinct (Asyl/Denis external proof, not OpenClaw workers); (c) Madi's retrieval query "is replacement done?" is a standalone topic that should resolve directly to this skill, not be buried inside a 17-AP control-plane skill. Also considered: making this a thin pointer to the audit doc [[SP3-BDL-PING-RESCOPED-2026-05-17]] — rejected because audit-doc content is dated and rots; SKILL.md compounds (per karpathy-loop AP-2). Also considered: dropping AP-4 (residuals) — rejected because AP-4 is the explicit handoff to whoever ships the circuit-breaker / atomic-ledger / Russian-message / autonomy-gate-hall-pass next; without AP-4 they get rediscovered from scratch.

## Timeline

- **2026-05-25** | v1.3.0 -> v1.4.0 — AP-7 extended to 3 other column-sum checks. Follow-on Explore audit (same session) found `_raw_intake_check`, `_law002_check`, `_erap_queue_check` all had the same column-sum-without-per-row-freshness bug shape; `_event_ingestion_check` was CLEAN (MAX-only). Same fix pattern applied to all 3: inline cutoff, per-row freshness filter in SQL, surface both `*_total` and `*_fresh` in detail. New RED tiers: `count_fresh<=0` in law002 (classification stopped) and `fresh_total<=0` in erap_queue (no fresh activity). Live verify post-fix: raw_intake now surfaces `parsed_fresh=1915` (last 2h); law002 surfaces `count_total=1086 count_fresh=234`; erap_queue surfaces `pending count_total=3 count_fresh=0` (now YELLOW with explicit "ZERO fresh activity" message instead of stale "states={'pending': {count: 3}}"). Authorial commit per SOC v1.17.0 Rule 19.

- **2026-05-25** | v1.2.0 -> v1.3.0 — AP-7 codified and shipped: `_fleet_health_check` now applies per-row `last_check` freshness filter to the `status='online'` sum. Closes silent 20+ day fleet outage class (see AUDIT-fleet-zero-online-20day-silent-outage-2026-05-25). State transition: fleet_health YELLOW (13.5% online, 38 stale rows propping count) → RED (online_fresh=0 stale_online=38; ZERO cameras online with current last_check). Gate overall: RED 3 reds → RED 4 reds (correct escalation; was masking ground truth). Detail string now surfaces `online_fresh` AND `stale_online` separately so operators see both live truth and what's lurking in the table. New RED tier `online_fresh <= 0` regardless of stale-row count. AP-7 generalizes: any column-sum gate check must filter by per-row freshness. Authorial commit per SOC v1.17.0 Rule 19.

- **2026-05-25** | v1.1.0 -> v1.2.0 — Live gate run captured material state transition since the 2026-05-15 audit. Data plane went LIVE: `event_ingestion` RED→GREEN (age_h 950→3.16; vehicle_events 155517); `raw_intake` RED→GREEN (parsed 0→9113/9135); `law002_classification` YELLOW→GREEN (count 100→1086, age_h 3). `fleet_health` YELLOW stable (38/281 online = 13.5% — operational issue, separate from this gate's doctrinal scope; flagged for operator triage). `erap_queue` YELLOW (3 pending, latest 2026-03-17, age_h 1642 = 68 days — separate stale-queue issue). Gate `overall=RED` still: only blocker is `external_proof_receipt` (`status=requested` since 2026-05-17; Asyl PSK / Denis HTTP-200 egress probe pending) + the rollup. Escalation runner `com.nous.satory-bdl-external-blocker-ping` fired today 08:00 KZT (Mon-Fri schedule respected; Russian template per v1.1.0 AP-5; msg_id 1853 to operators chat -1002064137259, gate_overall=RED). AP-6 codifies the rule that gate-check state transitions land in skill Timeline same-session so future agents don't re-discover state via audit-chain reads. Detector `tools/test_bdl_cerebro_skill_state_freshness.sh` queued. Authorial commit per SOC v1.17.0 Rule 19. 4-session handshake Lane 1 (s0952) Mission 3 slice 2.

- **2026-05-21** | v1.0.0 -> v1.1.0 — Madi escalated "why is this again in eng? it must be in russian in that group" after the Mon-Fri 08:00 KZT ping fired the English template against the Satory operators group at today's 08:00 cycle. AP-4 residual #3 (deferred 2026-05-17 as "Russian-language message variant") had become a production fire. Closed by switching `tools/satory_bdl_external_blocker_ping.py::_build_message()` default to Russian (Cyrillic Асыл/Денис, technical tokens HTTP-200/BDL/Cerebro/PSK/KZT/egress/proof gate/freshness retained in English because operators read the stack vocabulary), extending the test with positive Cyrillic markers AND negative English-drift assertions so the regression cannot recur silently. AP-5 codifies audience-language discipline per [[session-operating-contract]] Rule 13: templated outbound declares recipient working language + asserts it as a tested invariant + uses proper-noun Cyrillic for Russian groups. AP-4 residual #3 marked CLOSED; residuals #1 (14-day circuit breaker), #2 (atomic per-workday ledger), #4 (tg_send autonomy-gate hall-pass) remain open. Manual `--force` resend dispatched via ssh air after commit so operators receive the corrected Russian version without waiting for tomorrow's 08:00 cycle. No new LESSON (RULE ZERO).

- **2026-05-17** | v1.0.0 created. Substrate-gap closer: the gate has been shipping since 2026-05-15 (commit `bcc302f1` "bdl: require external Satory proof receipt") but doctrine lived only in code comments + 3 audit docs. Skill consolidates the doctrine, the receipt-flip protocol, the 9-check + 2-rollup contract, and 4 anti-patterns (AP-1 gate-as-source-of-truth, AP-2 drought-is-symptom, AP-3 brain-first-violation prevention, AP-4 ping residuals). Created post-SP3 (peer session shipped the implementation; this skill closes the substrate gap they didn't address). Source: [[SP3-BDL-PING-RESCOPED-2026-05-17]].
