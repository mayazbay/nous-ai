---
type: spec
id: SPEC-2026-05-19-daily-evolution-cron-design
title: "03:00 KZT daily self-update cycle (`com.nous.daily-evolution`) — Spec-Kit /specify"
date: 2026-05-19
status: draft
owner: claude-opus-4-7
priority: p0
tags: [spec-kit, daily-evolution, self-update, launchd, canary, rollback, openclaw, litellm, mission-2026-05-19]
related:
  - [[MISSION-2026-05-19-always-on-satory-ai-factory]]
  - [[skills/factory-ops]]
  - [[skills/musk-algorithm]]
---

# SPEC — 03:00 KZT daily self-update cycle

Spec-Kit shape. **Do not implement until Madi approves this spec.**

`[[MISSION-2026-05-19-always-on-satory-ai-factory]]` required implementation #4. Madi verbatim: "Add 03:00 self-update cycle: check package/tool versions, canary upgrades only, rollback snapshot, run proof pack, promote only if green."

## Constitution (rules this spec inherits)

- `[[MISSION-2026-05-19-always-on-satory-ai-factory]]` rule 4 — 03:00 self-update is canary-only with rollback.
- `[[skills/factory-ops]]` v1.36.8 + supervisor `tools/factory_self_heal.py` — the supervisor handles ongoing drift; this cron is the **daily upgrade promotion lane**, not a drift catcher.
- `[[skills/musk-algorithm]]` step 2 — delete-before-add. Reuse existing canary infra (`hermes_promotion_runner.py`, `model_promotion_gate.py`, `factory_self_heal.py`) rather than reinventing.
- AP-21 — canary gates 24h before production. AP-29 — fixture wins required for model promotion.
- RULE ZERO — durable learning lands in SKILL.md + gbrain timeline, not new LESSON files.
- "No fake green": every promotion step writes proof or rolls back.

## Specify (what we're building)

A **single launchd job** `com.nous.daily-evolution` that fires once at **03:00 KZT** on Air. It:

1. **Snapshots** current state: git head SHAs (Mac+Air+VPS+GitHub), launchd job exit statuses, LiteLLM model list hash, OpenClaw container image SHA, Codex CLI version, gbrain version, OpenBrain projection counts.
2. **Pulls** substrate from `vps` to all hosts; resolves any auto-mergeable conflicts; aborts on real conflicts (notifies Madi with exact merge command).
3. **Checks** versions of canary-eligible packages: OpenClaw (current v2026.5.18 vs npm latest), Codex CLI, gbrain, MLX, deepseek-v4-flash via OpenRouter availability, Anthropic SDK.
4. **For each upgrade candidate**: writes a canary tag, runs `factory_no_drift_probe.sh --quiet`, runs `tools/model_promotion_gate.py` if model-related, runs `tools/hermes_promotion_runner.py` if Hermes-related. Cap: 1 canary upgrade per cycle (Musk step 2: ship one thing well).
5. **Runs the proof pack**: `tools/factory_no_drift_probe.sh`, `tools/test_skill_internal_consistency.sh`, `tools/test_musk_step_2.sh`, factory 6-axis health (telegram-poll/queue-runner/litellm/openbrain/gbrain/sync).
6. **Promotes** the canary if all proofs GREEN. **Rolls back** if any RED. Records both paths in `pages/audits/DAILY-EVOLUTION-YYYY-MM-DD.md`.
7. **Notifies Madi only if** (a) an upgrade requires login/cred refresh, (b) a rollback fired and supervisor can't auto-repair, (c) a brand-new vulnerability flagged. Otherwise SILENT — daily compact digest at 09:00 KZT alongside the operator digest summarizes the cycle.

## Clarify (open questions for Madi)

1. **Upgrade scope.** Start with what subset of packages? Recommend MVP: **OpenClaw + Codex CLI + MLX model version only** for first 7-day canary. After proof, widen to all npm/pip pinned tools.
2. **Cadence on rollback**. If rollback fires, do we retry the same upgrade next day OR skip it for 7 days (back-off)? Recommend: **skip 7 days** to avoid daily-rollback loop on a chronically-broken upgrade.
3. **OpenClaw v2026.5.18 → next**. Already on .18; rule on Madi's plan-mode addendum said "OpenClaw v2026.5.18 is current latest; upgrade only through canary + rollback." Confirm `com.nous.daily-evolution` is the canary that runs that upgrade gate.
4. **Code-language upgrades** (Python, Node, Bun). Defer? Recommend: **yes defer** (those are infrastructure-level, manual rollback complex). Stay package-level only.
5. **MLX model upgrade** (e.g., Qwen3 → Qwen4 when available). Recommend: only after AP-29 bakeoff explicitly fires on the new model and wins. Cron only triggers the bakeoff; promotion requires Madi explicit greenlight for model-class changes.
6. **iPad/phone notification preferences**. When daily digest fires at 09:00 KZT, surface it via Telegram DM to Madi (per MISSION rule "Madi gets only presidential pings") OR via dashboard pull-only? Recommend: **Telegram DM, compact format**, since you already get the morning brief at that time.

## Plan (architecture)

```
03:00 KZT (launchd com.nous.daily-evolution)
  │
  ├─ tools/daily_evolution_runner.py (NEW)
  │     ├─ phase 1: snapshot()
  │     │     - git heads (Mac/Air/VPS/GitHub)
  │     │     - launchd exit statuses
  │     │     - service version SHAs
  │     │     - write to pages/systems/daily-evolution-snapshot-pre.json
  │     │
  │     ├─ phase 2: pull_substrate()
  │     │     - git pull vps main on Mac+Air, resolve auto-mergeable
  │     │     - if real conflict → notify_madi + abort
  │     │
  │     ├─ phase 3: detect_upgrades()
  │     │     - openclaw --version vs `npm view openclaw version`
  │     │     - codex --version vs github releases latest
  │     │     - gbrain --version vs github tags
  │     │     - litellm via pip vs latest
  │     │     - return list[Upgrade]; cap at 1 per cycle
  │     │
  │     ├─ phase 4: canary_each_upgrade()
  │     │     - for upgrade in upgrades[:1]:
  │     │         backup_to_rollback_tag
  │     │         apply_upgrade
  │     │         run factory_no_drift_probe.sh --quiet
  │     │         run test_skill_internal_consistency.sh
  │     │         run hermes_promotion_runner.py (if Hermes)
  │     │         run model_promotion_gate.py (if model)
  │     │         if any RED: rollback_to_tag + record
  │     │         if all GREEN: promote + record
  │     │
  │     ├─ phase 5: proof_pack()
  │     │     - factory_no_drift_probe.sh
  │     │     - tools/test_musk_step_2.sh
  │     │     - 6-axis health: telegram-poll/queue/litellm/openbrain/gbrain/sync
  │     │
  │     ├─ phase 6: digest()
  │     │     - write pages/audits/DAILY-EVOLUTION-YYYY-MM-DD.md
  │     │     - if upgrade succeeded: include version delta + proof links
  │     │     - if rollback: include reason + escalation flag
  │     │     - if all green nothing-to-do: 3-line compact summary
  │     │
  │     └─ phase 7: notify(09:00 KZT alongside morning brief)
  │           - silent unless rule 7a/7b/7c above
  │           - else compact digest line in morning-brief
  │
  └─ Idempotent: same calendar day can re-run safely (state.json tracks)
```

### Files

- **New**: `tools/daily_evolution_runner.py` (~400 lines).
- **New**: `tools/daily_evolution_adapters/` — one module per upgrade target (`openclaw.py`, `codex.py`, `gbrain.py`, `litellm.py`, `mlx.py`).
- **New**: `tools/tests/test_daily_evolution_runner.py` — fixture-mode (no live upgrades).
- **New**: `pages/systems/daily-evolution-state.json` — durable state (last run, last 7 rollback skips, version manifest).
- **New**: `~/Library/LaunchAgents/com.nous.daily-evolution.plist` — fires at `StartCalendarInterval Hour=3 Minute=0` (KZT via TZ env).
- **Modify**: `tools/morning-brief.sh` — incorporate daily-evolution summary into the existing 09:00 KZT brief.
- **Modify**: `pages/skills/factory-ops/SKILL.md` — new AP for daily-evolution doctrine + escalation rules. RULE ZERO 3-edit ritual.

### Deletion (Musk step 2 first)

Existing scripts that should be CALLED-BY (not duplicated by) daily_evolution_runner:
- `tools/factory_no_drift_probe.sh` — KEEP, called by phase 4 + 5.
- `tools/factory_self_heal.py` — KEEP separate (handles ongoing drift; daily-evolution handles scheduled upgrades).
- `tools/hermes_promotion_runner.py` — KEEP, called by phase 4 when Hermes upgrade.
- `tools/model_promotion_gate.py` — KEEP, called by phase 4 when model upgrade.
- `tools/morning-brief.sh` — EXTEND, not replace.

Deletion candidates (if their function gets folded in):
- `tools/litellm_price_watch.sh` — possibly fold version check into daily_evolution. Defer to T7 audit.
- Ad-hoc weekly canary scripts (`tools/weekly_library_canary.sh`) — daily cycle subsumes weekly cadence; weekly script can deprecate after 14-day proof.

Acceptance gate (Musk step 2): net `tools/*.sh` + `tools/*.py` LOC flat or down after ship + 14 days of weekly-canary deprecation.

## Tasks (Spec-Kit ordered)

- [ ] **T1** — Madi answers Clarify Q1–Q6.
- [ ] **T2** — Author `tools/daily_evolution_runner.py` skeleton with snapshot, pull, detect-upgrades phases (no canary action yet). Test: fixture-mode runs end-to-end without applying any upgrade.
- [ ] **T3** — Author `tools/daily_evolution_adapters/openclaw.py` first (most critical upgrade target). Test: version probe returns current; apply path is dry-run-able.
- [ ] **T4** — Author the rollback tag mechanism (git tag + scriptable revert per adapter).
- [ ] **T5** — Wire `factory_no_drift_probe.sh` + `model_promotion_gate.py` + `hermes_promotion_runner.py` into canary phase 4.
- [ ] **T6** — Author launchd plist `com.nous.daily-evolution.plist` with `StartCalendarInterval Hour=3 Minute=0` (KZT-relative).
- [ ] **T7** — 24h dry-run: load plist, fire manually via `launchctl kickstart -k`, verify all 7 phases run without applying any real upgrade. No Madi notifications.
- [ ] **T8** — Extend `tools/morning-brief.sh` to surface daily-evolution digest line.
- [ ] **T9** — `pages/skills/factory-ops` SKILL.md AP for daily-evolution doctrine + escalation rules. RULE ZERO 3-edit ritual.
- [ ] **T10** — Promote to production after 7-day dry-run proves no false escalations.

## Implement (execution log — append as work happens)

(empty until Madi approves spec)

## Acceptance criteria (binding, falsifiable)

1. **Cron fires at exactly 03:00 KZT** verified by `pages/audits/DAILY-EVOLUTION-YYYY-MM-DD.md` timestamps within ±60s.
2. **No upgrade applied without rollback tag** — test fixture: corrupt an upgrade, verify rollback fires + tag exists.
3. **Madi notifications under 7/week** during steady state. If exceeded, false-positive rate is too high; tune thresholds.
4. **Net tool LOC flat or down** after ship + 14d weekly-canary deprecation (Musk step 2 gate).
5. **24h dry-run produces no false rollbacks** — fixture-mode runs daily for 7 days; rollback fires 0 times unless deliberately seeded.
6. **OpenClaw v2026.5.18 upgrade-canary path proven** — manual kickstart applies+rolls-back the same version; idempotent; ledger records both actions.

## Rollback path

- `launchctl unload com.nous.daily-evolution` → cron stops; existing services unaffected.
- Last successful daily-evolution snapshot at `pages/systems/daily-evolution-snapshot-pre.json` is the restore reference.
- All per-upgrade rollback tags persist in git; can manually revert any individual upgrade.
- No data loss; daily-evolution is read-mostly during snapshot phase, write-canary-only during upgrade phase.

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Canary upgrade breaks production silently | Low | High | Per-upgrade rollback tag + 6-axis proof pack must GREEN before promote |
| Cron fires while Madi is mid-debug | Med | Low | Manual override: `touch /tmp/daily-evolution-skip-YYYY-MM-DD` |
| Network down at 03:00 → no version-check upgrades available | High | Low | Skip cycle silently; record in state.json; retry next day |
| Git merge conflict during phase 2 substrate pull | Med | Med | Abort with explicit Madi notification (rule 7a); supervisor stays unaffected |
| OpenRouter / xAI API rate-limit during model upgrade canary | Low | Med | Per-adapter circuit breaker + per-day cost cap (defer model-class upgrades on rate-limit) |
| AP-21 24h canary gate skipped by ambitious upgrade ladder | Low | High | Cap 1 canary per cycle; explicit Musk step 2 gate before T10 promote |

## See also

- `[[MISSION-2026-05-19-always-on-satory-ai-factory]]` — required impl #4 origin
- `[[skills/factory-ops]]` v1.36.8 — supervisor doctrine (orthogonal to this cron)
- `[[skills/musk-algorithm]]` v1.3.0 — 5-step (this cron IS step 5 "automate" applied to the upgrade loop itself)
- `[[2026-05-19-multi-model-consult-skill-design]]` — escalation target if upgrade ambiguity needs multi-model judgment
- `[[CHEAP-POOL-BENCHMARK-2026-05-19]]` — example of the kind of bakeoff the daily-evolution cron will auto-fire for model upgrades

## Timeline

- **2026-05-19 16:05 KZT** — Spec authored by Claude Opus 4.7 lane. Awaiting Madi review.
