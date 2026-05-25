---
type: spec
id: SPEC-2026-05-23-moonlit-pnueli-execution
title: "Moonlit-Pnueli execution prompt — self-driving /goal payload"
tags: [spec, goal, moonlit-pnueli, execution, hermes-nr, grok-x, sat-council, business-tooling]
date: 2026-05-23
source_count: 4
status: ready
last_updated: 2026-05-23
related: [[ceo-hierarchy]], [[session-operating-contract]], [[musk-algorithm]], [[karpathy-loop]], [[karpathy-coding-principles]], [[architecture-quickref]], [[HERMES-CANARY-METRICS-SCHEMA-2026-05-23]]
---

# Moonlit-Pnueli execution prompt — self-driving /goal payload

> **Purpose:** copy-paste this entire body into a `/goal` Telegram message OR a fresh Claude Code / Codex / Hermes session. It is self-contained enough for the worker to execute all six phases of the [moonlit-pnueli plan](/Users/madia/.claude/plans/before-doing-the-plan-moonlit-pnueli.md) without stopping, posting a Telegram digest after each phase, halting only on acceptance-criteria completion, HARD-RULE violation, or explicit Madi `abort`.

---

## /goal payload (paste below the slash command)

```
GOAL: MOONLIT-PNUELI — execute 6-phase plan to completion. Don't stop until ALL 8 acceptance criteria pass or you write a definitive HALT audit explaining why. Compound every fix into SKILL.md + gbrain timeline (RULE ZERO — NO new LESSON files). Bad-news-loud. Math not vibe.

# Authoritative artifacts
- Plan: /Users/madia/.claude/plans/before-doing-the-plan-moonlit-pnueli.md (DRAFT-3, Madi-approved 2026-05-23)
- Spec: pages/specs/2026-05-23-moonlit-pnueli-execution-prompt.md (this doc, canonical)
- Metrics schema (Hermes-NR canary): pages/audits/HERMES-CANARY-METRICS-SCHEMA-2026-05-23.md
- Doctrine: session-operating-contract v1.17.0, musk-algorithm v1.4.0, karpathy-loop v1.12.0, ceo-hierarchy v1.10.14, karpathy-coding-principles v1.1.0
- Architecture: pages/systems/architecture-quickref.md

# HARD RULES (immediate STOP + halt audit if violated)
- HR1: Telegram MCP token check before any Telegram MCP call (use tools/tg_send.sh from any host; never call mcp__plugin_telegram__* if its token == @nousAGaaSbot token)
- HR2: NEVER deploy/alias/redirect satory.nousagaas.com. Asset must stay index-BSiWURaO.js. Pre-flight check before any phase: curl -s "https://satory.nousagaas.com/" | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1
- HR3: gbrain IS connected (mcp__gbrain__*). Never claim it isn't.
- HR4: Read latest HANDOFF-AUTO-* in pages/progress/ before touching code.
- HR5: Verify claims before declaring done (4-artifact DONE: cmd + output + git rev + counter-check, per SOC v1.17 Rule 1).
- HR6: RULE ZERO. Every fix → SKILL.md + gbrain timeline. NEVER new LESSON-NNN file (pre-commit hook rejects).
- HR7: HARD-bans per SOC: no persona cosplay, no "done" without proof, no "let me know if you want me to continue", no Telegram MCP in Claude Code with @nousAGaaSbot token.

# OWNER MAP
- Codex (gpt-5.5 subscription via ssh air codex exec OR /codex from Telegram): P0-A, P0-B, P0-D, P0-F, P1.2, P1.3, P1.4, P1.5, P2.1, P2.2, P2.3, P2.4, P2.5, P2.6, P2.7, P3.2, P3.3 implementation, P3.4, P3.5, P5.2, P5.4, P6.2
- Opus (Claude Code session via /code OR Mac terminal): P0-C, P0-E (split w/ Codex), P2.8 mid-canary, P2.9 verdict, P2.10 SOC port, P3.1 doctrine decision, P4 all, P5.1 council, P5.3, P6.1, P6.3, P6.4
- Madi (human approval gates): P0-G ack, P2.0 metrics-schema ack, irreversible action approvals (ceo-hierarchy v2.0 bump, Hermes-NR KEEP verdict, any production cutover)

# PHASE 0 — Close last week's debt (P0-G blocks P1; rest parallel)

P0-G [Madi or auto] /codex --health returns ok (Codex CLI 0.130.0 + auth.json present on Air — verified 2026-05-23 GREEN).

P0-A [Codex] Fix Todoist control-plane hard-gate (receipt name "hermes Todoist↔Notion sync failure" is misleading — NOT a Notion bug). Root: 2 risks (1 missing_department + 1 missing_labels) in 107 active Todoist tasks block the cycle. Action: run tools/satory_todoist_deep_audit.py OR tools/todoist_review_owner_labels.py to identify the 2 specific tasks; either fill missing fields OR reclassify those legacy classes from hard-gate to soft-warn. Exit gate: 24h green hermes_factory_watchdog.py cycle + RECEIPT in pages/audits/RECEIPT-todoist-hard-gate-fix-*.md.

P0-B [Codex] Fix tools/goal_runner.py rapid-fire (9 trips/3 min vs target 1/4hr) — AP-35. Likely launchd interval bug or missing lockfile. Exit: 24h single-cycle-per-interval proof in pages/audits/RECEIPT-goal-runner-rate-fix-*.md.

P0-C [Opus] Fix Google Drive OAuth 403 OR pivot to vault-native proof links (pages/audits/PROOF-*.md rendered via QMD). Exit: first real proof attached in next Telegram report.

P0-D [Codex] Close Codex Layer-2 spec gaps in pages/specs/2026-05-19-single-beam-substrate-bus-design.md: (1) JSON event schema, (2) per-source×per-target fan-out matrix, (3) falsifiable acceptance criteria, (4) rollback path, (5) "GStack meaning" disambiguation. Exit: spec v1.1 shipped with all 5 closed.

P0-E [Opus + Codex split] 7-day iPad-only ladder Days 3-6 per HANDSHAKE-2026-05-20-ipad-only-presidential-7-day-plan-0820.md: factory event push → Hermes WebUI Kanban (Opus), /ask --tier ceo|cheap toggle in Telegram (Codex), Air dirty-WT auto-commit hardening (Codex), notification policy ≤5/day (Opus). Exit: each day's gate per HANDSHAKE.

P0-F [Codex] Russianize control-plane: wire tools/check_russian_control_plane_docs.py into control-plane-sync cycle. Exit: Russian /help, Russian labels on all new Todoist tasks, one Russian-language Telegram digest proof.

PHASE 0 EXIT: single Telegram digest via tools/tg_send.sh with all 7 items 4-artifact DONE'd. Until then, P2-P5 may NOT run; P1 may.

# PHASE 1 — Grok / X Premium in OpenClaw (after P0-G; parallel w/ P0-A..F)

P1.1 [DONE 2026-05-23] xAI Imagine API spec verified:
  - Image: POST https://api.x.ai/v1/images/generations, model="grok-imagine-image-quality" (CRITICAL: -pro deprecated 2026-05-15, do NOT use)
  - Video: POST https://api.x.ai/v1/videos/generations, model="grok-imagine-video", async (poll GET /v1/videos/{request_id} every 5s, 10min timeout)
  - Video edit: POST /v1/videos/edits; extend: POST /v1/videos/extensions
  - Bonus: Voice API (TTS + STT) — useful for Telegram audio I/O
  - X post search: NOT in xAI public API; needs separate X/Twitter API auth (flagged, do NOT ship adapter, document blocker)
  - Auth: Bearer XAI_API_KEY (already in ~/nous-agaas/.env on Air)

P1.2 [Codex] Create pages/skills/xai-premium-tools/SKILL.md v1.0.0 with: tool list, cost gates ($0.10/image + $0.50/video pre-flight cap pending Madi billing confirmation), Subscription-First amendment, sample curl calls, async polling helper pattern, failure modes. Register in pages/skills/_gbrain/RESOLVER.md.

P1.3 [Codex] Add OpenClaw adapters: tools/grok_image_gen.py, tools/grok_video_gen.py (with async polling). Cost gates via existing litellm_cost_alarm.py pattern. x_post_search BLOCKED — write stub that returns "needs X API auth, flagged P1.1".

P1.4 [Codex] Telegram commands /grok-image <prompt> and /grok-video <prompt> wired into tools/telegram_poll.py routing. Test from Madi's chat_id 110793056.

P1.5 [Codex] Notification accounting: P1 outbound rolled into existing daily cost-alarm digest, not separate pings. Keep ≤5 notifications/day per P0-E target.

PHASE 1 EXIT: /grok-image and /grok-video each produce one real artifact from Madi's Telegram in test; daily cost report under $5/day cap; xai-premium-tools skill registered in _gbrain/RESOLVER.md; gbrain timeline entry.

# PHASE 2 — Hermes-NR canary (after PHASE 0; parallel w/ P3-P5)

PRE-CONDITION: Madi acknowledges pages/audits/HERMES-CANARY-METRICS-SCHEMA-2026-05-23.md via Telegram "ack metrics schema" before P2.3 runs. If thresholds unacceptable, edit schema file + bump last_updated.

P2.1 [Codex] Doctrine PR: rename internal canary to factory-hermes-canary throughout vault; reserve nous-hermes (or hermes-nr) for the Nous Research framework. Add pre-commit hook flagging unqualified "Hermes" mentions in new commits.

P2.2 [Codex] Snapshot Air state: ~/.openclaw → ~/.openclaw-backup-2026-05-23/. Document in pages/audits/.

P2.3 [Codex] Install Hermes-NR v0.14.0 (MIT, verified real): curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash — on Air, into new hermes-nouscanary profile (matches existing nouscanary pattern per ceo-hierarchy v1.10.14 §0b). Bare-metal, NOT Docker. Installer auto-handles uv, Python 3.11, Node.js, ripgrep, ffmpeg.

P2.4 [Codex] hermes claw migrate --dry-run --preset user-data against backup. Capture full diff to pages/audits/.

P2.5 [Codex] Wire ONE canary workload only = morning brief generation. Schedule hermes-nouscanary side at same time as existing factory-side morning brief. Both write JSONL row per schema. EXCLUDED from canary: openbrain re-summarization (vault pollution risk).

P2.6 [Codex] 7-day measurement window, JSONL at ~/nous-agaas/logs/hermes-canary.jsonl with schema {date, run_id, side, workload, input_hash, output_hash, model_used, cost_usd, latency_ms, stability_ok, recall_score, ...}. Daily Telegram check-in.

P2.7 [Codex] Write tools/hermes_canary_halt.sh kill switch: stops hermes-nouscanary profile, reverts morning-brief launchd job target to factory, writes pages/audits/HERMES-CANARY-HALT-*.md. Test on Day 0 (intentional trigger).

P2.8 [Opus] Day-3 mid-canary checkpoint: compute M1-M4 from days 1-3. Abort early (REVERT) if M1<60% OR M4≥2 OR Madi pulls plug. If green, optionally add vault-tagging workload days 4-7.

P2.9 [Opus] Day-7 verdict: write pages/audits/AUDIT-hermes-nr-canary-2026-05-30.md per pre-committed thresholds (KEEP-AND-EXPAND if M1≥90% AND M2≤1.2× AND M4=0 AND M3≤1.5× AND M5≥1; HYBRID if M1≥75% AND M2≤1.5× AND M4≤1; otherwise REVERT). Pure math.

P2.10 [If KEEP, Opus] Port full session-operating-contract v1.17.0 + RULE ZERO + musk-algorithm + karpathy-loop into Hermes memory. NOT Felix 5.0 abbreviation.

PHASE 2 EXIT: signed audit doc with verdict + measurable data table.

# PHASE 3 — 3-Layer hierarchy + Sat-council ‖ PHASE 2

P3.1 [Opus, gated] ceo-hierarchy v1.10.14 → v2.0.0 ONLY if P3.2 yields ≥1 production-ready open-source model. L1 = decision-replacement-of-Madi (Grok-4.3 today; wrapped-in-nous-hermes pending P2 KEEP); L2 = Karpathy-council reasoning (Opus 4.7 + Codex GPT-5.5); L3 = Composer worker swarm (best open-source).

P3.2 [Codex] PREREQ: fix nous-GPU Tailscale ACL (pages/entities/nous-gpu.md status yellow-offline). Then pages/skills/composer-tier/SKILL.md v1.0.0 with task-class matrix: DeepSeek V4 Flash (default) vs Qwen 3 vs Kimi K2 vs MiniMax M2 vs Composer (Cursor-tier) on codegen / RAG / vision / summarization / Russian-language / agent-loop. Target nous-GPU RTX 5070 for local inference.

P3.3 [Codex] Saturday 03:00 KZT weekly model council — deliverables:
  (a) tools/multi_model_consult.py bumped to v1.5.0 with 5 new adapters: _call_gemini, _call_deepseek_pro, _call_kimi, _call_qwen, _call_composer (~30 lines each, mirror existing _call_grok)
  (b) tools/weekly_model_council.py (~300 LOC, imports consult())
  (c) tools/launchd/com.nous.weekly-model-council.plist (Weekday=6 Hour=3 Minute=0 TZ=Asia/Almaty, EnvironmentVariables: NOUS_PAID_API_ALLOWED=1, NOUS_PAID_API_CAP_USD=3.00, NOUS_PAID_API_REASON="weekly council per ceo-hierarchy v2.0 P3.3"). Plist copy at /Users/madia/Library/LaunchAgents/.
  (d) Prompt template: 5 numbered Qs (family changes, swap recs, capability gaps, cost/perf shifts, risks) ending with `## VERDICT` deterministic line `KEEP-ALL | SWAP L<n>: <out>→<in> | URGENT: <reason>`
  (e) Hybrid synthesis: deterministic regex tally per VERDICT line (≥4-of-8 majority required for swap); Opus narrative pass writes prose only, can flag dissent but CANNOT override vote (prevents conflict where one model verdicts its own tier)
  (f) Floor: 4-of-8 succeeded = valid run; below = YELLOW report + Telegram alert "council degraded"
  (g) Wallclock cap ≤9 min (8 models × 60s + 90s synthesis)
  (h) Cost ~$0.31/run expected, soft-warn $1.50, hard cap --cap-usd 3.00; monthly ≈$13
  (i) Per-model raw cached at pages/audits/council-cache/<run_id>/<model>.json
  (j) Output: pages/audits/WEEKLY-MODEL-COUNCIL-YYYY-MM-DD.md (≤300 lines) + Telegram digest ≤500 chars
  (k) JSONL ledger at pages/systems/weekly-model-council-ledger.jsonl

P3.4 [Codex] /ask --tier toggle (from P0-E) ships with L1/L2/L3 names matching ceo-hierarchy v2.0.

P3.5 [Codex] 3-stage dry-run BEFORE first scheduled Saturday fire:
  (a) Mon 2026-05-25 14:00 KZT: --dry-run (validates plist, paths, Telegram reachability, no model calls)
  (b) Wed 2026-05-27 14:00 KZT: --cap-usd 1.00 --skip-telegram (real calls all 8 adapters, no Telegram push)
  (c) Thu 2026-05-28 14:00 KZT: full live with --telegram (weekday so Madi watches logs)
  (d) ONLY THEN launchctl bootstrap gui/501 plist for Sat 2026-05-30 03:00 first scheduled invocation

PHASE 3 EXIT: first scheduled Sat-council report 2026-05-30 04:00 KZT with one swap rec or "KEEP-ALL — all tiers optimal".

# PHASE 4 — Book of Elon (2026) verification ‖ P2/P3

P4.1 [Opus] WebFetch + WebSearch: confirm "The Book of Elon (2026)" exists with ISBN/author/publisher. If hallucinated, skip + rely on existing musk-algorithm v1.4.0 (already covers 69 Core Musk Methods from Isaacson + Patel).

P4.2 [Opus] For each NEW principle not in v1.4.0: add as AP or "Current rules" bullet in pages/skills/musk-algorithm/SKILL.md. Bump version. gbrain timeline entry. NEVER new LESSON file (RULE ZERO).

P4.3 [Opus] Audit doc pages/audits/AUDIT-book-of-elon-2026-source-check-2026-05-23.md lists source verification + every absorbed principle.

PHASE 4 EXIT: audit doc landed; musk-algorithm bumped if applicable.

# PHASE 5 — Business tooling reassessment ‖ P3/P4

P5.1 [Opus] Run multi-model-consult (Opus + Codex GPT-5.5 + Grok-4 + Gemini 2.5 + DeepSeek V4 Pro) on council Q:
  "For Nous AI / Spectra ITS / Satory (Almaty KZ; Russian team of 5-10; one $23M gov contract live + multiple 1B+ tenge tenders in pipeline; current stack=Telegram+Todoist+Obsidian+gbrain+gstack+OpenBrain; broken: Notion sync + Drive OAuth; missing: pipeline/revenue visibility, Russian /help, lightweight CRM): what's the single highest-ROI tooling change in the next 30 days? Compare specifically: (i) Bitrix24 (Russian-native, KZ gov-tender modules native, Telegram-integrated), (ii) Salesforce, (iii) gbrain-native deal-entity layer (pages/deals/<deal>.md with QMD pipeline view), (iv) lightweight Todoist `Pipeline / Воронка продаж` section. Skip Slack (Telegram wins). Skip Linear (Todoist + Codex tracking sufficient at this team size)."
  Verdict → pages/audits/COUNCIL-2026-05-23-business-tooling.md.

P5.2 [Codex] Defaults (adjust per 5.1 verdict): (a) FIX Notion sync root cause (don't replace — it's wired); (b) Add pipeline view per council pick (default = Todoist `Pipeline / Воронка продаж` section + daily pipeline-digest to Telegram + vault) UNLESS council recommends Bitrix24/gbrain-native; (c) Russian /help; (d) NO Slack, NO Salesforce.

P5.3 [Opus] If Drive OAuth not fixable in P0-C, pivot to vault-native PROOF-*.md links (rendered via QMD).

P5.4 [Codex] Pipeline view live with at least one tender tracked end-to-end (Lead → Qualified → Proposal → Negotiation → Won/Lost).

PHASE 5 EXIT: council verdict landed; Notion sync green 24h; pipeline view live with ≥1 tender; Russian /help returns Russian text.

# PHASE 6 — AI Council audit of THIS plan (AFTER P0, BEFORE P1+)

P6.1 [Opus] multi-model-consult on the plan file. Models: Opus 4.7 + Codex GPT-5.5 + Grok-4-reasoning + Gemini 2.5 Pro + DeepSeek V4 Pro. Question: "Here's a 6-phase plan. (a) Is the sequencing right? (b) What's missing? (c) What's overscoped? (d) Where's the highest risk? (e) What would you delete (Musk step 2)? (f) Does The Book of Elon (2026) exist as a real publication (ISBN/author/publisher) and what unique principles would it add to musk-algorithm v1.4.0?"

P6.2 [Codex] codex challenge adversarial mode on the plan: "find the biggest hole."

P6.3 [Opus] Skill(karpathy-loop) — REAL Skill invocation, not vibe (AP-1, AP-5 gates).

P6.4 [Opus] Update plan based on council findings BEFORE P1+ executes. Write changes to pages/audits/COUNCIL-2026-05-23-plan-review.md.

P6.5 EXIT: (a) karpathy-loop ≥4/6 on plan axes; AND (b) zero "critical-missing" flags from Codex challenge — defined as: any phase missing falsifiable exit gate / any irreversible action without rollback / any cost gate undefined / any HARD-RULE violation. Anything else = WARN flag (proceed but track).

# REPORTING DISCIPLINE

- After EVERY phase exits (or fails): post Telegram digest via `bash tools/tg_send.sh "<msg>"` with 4-artifact DONE (cmd + output + git rev + counter-check) per SOC v1.17 Rule 1.
- After every skill version bump: `mcp__gbrain__add_timeline_entry slug="pages/skills/<skill>/skill" date=YYYY-MM-DD summary="..."`. RULE ZERO.
- If any HARD RULE violation detected → STOP, write pages/audits/HALT-MOONLIT-PNUELI-*.md, Telegram alert.
- Daily Telegram check-in even mid-phase to surface progress (one digest per day max unless RED).

# COST CEILINGS

- xAI Premium: $5/day total (P1 tools); pre-flight $0.10/image, $0.50/video caps until Madi confirms billing rate
- Sat-council weekly: $3/run cap, $13/month ceiling
- Hermes-NR canary: M2 metric ≤ 1.2× factory baseline for KEEP verdict (per pages/audits/HERMES-CANARY-METRICS-SCHEMA-2026-05-23.md)
- Subscription-first: Opus + GPT-5.5 ($200/mo each) used first; paid API ONLY with `NOUS_PAID_API_ALLOWED=1 + NOUS_PAID_API_CAP_USD=X + NOUS_PAID_API_REASON=...`

# ACCEPTANCE CRITERIA (goal is DONE when ALL 8 hold)

1. PHASE 0 — Telegram digest with all 7 items 4-artifact DONE'd
2. PHASE 1 — /grok-image and /grok-video each produced one real artifact from Madi's Telegram; xai-premium-tools skill registered
3. PHASE 2 — pages/audits/AUDIT-hermes-nr-canary-2026-05-30.md landed with verdict (KEEP/HYBRID/REVERT)
4. PHASE 3 — first scheduled Sat-council report 2026-05-30 04:00 KZT landed; ceo-hierarchy bumped to v2.0 (only if composer-tier spike qualified)
5. PHASE 4 — Book of Elon audit doc landed
6. PHASE 5 — business tooling council verdict landed; Notion sync green 24h; pipeline view live with ≥1 tender
7. PHASE 6 — plan council audit + Codex challenge complete; karpathy-loop ≥4/6
8. Final Telegram digest summarizing all 6 phases + closing commit git rev

# HALT CONDITIONS (do NOT silently continue)

- Any phase BLOCKS >24h without progress → post HALT audit + Telegram alert
- Any HARD RULE violation → STOP immediately
- Madi sends "abort" / "stop" / "halt" / "стоп" via Telegram → write halt audit, run hermes_canary_halt.sh if applicable, Telegram confirmation
- Cost ceiling breached → pause + Telegram alert (do not auto-bypass)
- Hermes-NR Day-3 mid-canary fails REVERT thresholds → run halt, write audit, do not continue P2

# SUBSTRATE REFERENCES

- Vault Mac: /Users/madia/Documents/Projects/Nous AGaaS/Nous/
- Vault VPS: /root/nous-agaas/wiki/ (bare repo at /root/nous-agaas/obsidian-wiki.git)
- Vault Air: /Users/madia/nous-agaas/wiki/
- gbrain MCP: mcp__gbrain__add_timeline_entry, mcp__gbrain__search, mcp__gbrain__get_page
- Telegram outbound (any host): bash tools/tg_send.sh "<msg>" (default chat_id 110793056 = Madi); token auto-resolved
- Codex CLI from Air: ssh air "codex exec <prompt>" OR /codex from Telegram routes via factory
- Opus from Air: /code from Telegram routes via factory, OR Mac Claude Code session
- Cost ledger: ~/nous-agaas/logs/ask-hierarchy.jsonl + litellm_cost_alarm.py
- HANDOFF auto-checkpoint: pages/progress/HANDOFF-AUTO-YYYY-MM-DD-session-NN.md (8×/day via launchd com.nous.auto-checkpoint)

# DOCTRINE QUICK-REFS (REQUIRED reads before any phase)

- pages/skills/session-operating-contract/SKILL.md v1.17.0 (23 rules, 4-artifact DONE, Musk-step-2 audit, failure→skill, hard-banned patterns)
- pages/skills/musk-algorithm/SKILL.md v1.4.0 (5-step exact order, 69 Core Musk Methods, Idiot Index, Magic Wand Number, Bad-News-Loud, Close-the-RL-Loop)
- pages/skills/karpathy-loop/SKILL.md v1.12.0 (6-axis scorecard, AP-1 no vibe-only, AP-5 no mental simulation, AP-11 skills-as-prompts runtime gate)
- pages/skills/karpathy-coding-principles/SKILL.md v1.1.0 (think-before-coding, simplicity-first, surgical changes, goal-driven)
- pages/skills/ceo-hierarchy/SKILL.md v1.10.14 (current tier routing; bumps to v2.0 in P3.1 conditionally)
- RULE ZERO (in CLAUDE.md): every fix → SKILL.md + gbrain timeline. NEVER new LESSON file. Pre-commit hook enforces.

# CRITICAL FILES (must not break throughout)

- satory.nousagaas.com asset = index-BSiWURaO.js (HR2 pre-flight check before any phase)
- VPS bare repo /root/nous-agaas/obsidian-wiki.git (gbrain sync must stay green)
- ~/nous-agaas/.env on Air (XAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENROUTER_API_KEY, MOONSHOT_API_KEY, TELEGRAM_BOT_TOKEN, TODOIST_API_TOKEN, SATORY_NOTION_TOKEN)
- Air launchd: com.nous.litellm, com.nous.telegram-poll, com.nous.auto-checkpoint, com.nous.morning-brief, com.nous.morning-update-apply, com.nous.qmd-freshness-regression (must stay green)
- Mac LaunchAgent (NEW, P3.3): com.nous.weekly-model-council.plist

# START NOW

Step 1: Pre-flight HR2 + HR3 + HR6 check. If any fail, STOP.
Step 2: Read latest HANDOFF-AUTO. Confirm current state matches plan assumptions.
Step 3: Verify P0-G (codex 0.130.0 on Air, auth.json present). If unblocked, launch P0-A through P0-F + P1.1→P1.2→P1.3→P1.4→P1.5 in parallel with owner assignments above.
Step 4: After P0 EXIT, kick PHASE 6 council audit BEFORE PHASE 2-5 execute.
Step 5: After P6 EXIT, launch PHASE 2 + PHASE 3 + PHASE 4 + PHASE 5 in parallel.
Step 6: Daily Telegram digest. RULE ZERO on every fix. Math not vibe. Bad-news-loud.
Step 7: When all 8 acceptance criteria pass, write pages/audits/CLOSING-MOONLIT-PNUELI-2026-XX-XX.md + final Telegram digest. Goal DONE.

GO.
```

---

## Short version (≤4096 char Telegram-paste with reference)

```
/goal MOONLIT-PNUELI — execute 6-phase plan per pages/specs/2026-05-23-moonlit-pnueli-execution-prompt.md until ALL 8 acceptance criteria pass or HALT audit written.

OWNERS: Codex owns P0-A/B/D/F + P1.2-1.5 + P2.1-2.7 + P3.2-3.5 + P5.2/5.4 + P6.2. Opus owns P0-C/E + P2.8-2.10 + P3.1 + P4 + P5.1/5.3 + P6.1/6.3/6.4. Madi owns ack gates (P0-G, P2.0 metrics schema, irreversible bumps).

START: Pre-flight HR2 (satory.nousagaas.com=index-BSiWURaO.js) + HR3 (gbrain) + HR6 (no new LESSON). Verify P0-G (codex 0.130.0 GREEN on Air). Launch P0-A..F + P1 in parallel.

GATE between P0 and P2-P5: PHASE 6 council audit (Opus+Codex+Grok+Gemini+DeepSeek on plan file; karpathy-loop ≥4/6).

REPORT: 4-artifact DONE per phase via bash tools/tg_send.sh. RULE ZERO on every fix (SKILL.md + gbrain timeline). Cost: $5/day xAI cap, $3/run Sat-council cap. Math not vibe. Bad-news-loud.

HALT: any HR violation OR "abort"/"stop" Telegram OR cost breach OR Day-3 canary REVERT → write HALT audit + Telegram alert, do not silently continue.

DOCTRINE: session-operating-contract v1.17.0 + musk-algorithm v1.4.0 + karpathy-loop v1.12.0 + karpathy-coding-principles v1.1.0 + ceo-hierarchy v1.10.14 (→v2.0 gated on P3.2). RULE ZERO (CLAUDE.md). HARD RULES 1-7.

DONE = all 8 acceptance criteria pass + closing audit + final Telegram digest.

GO.
```

---

## Timeline

- **2026-05-23** | Spec authored by Opus from approved DRAFT-3 plan moonlit-pnueli. Self-contained /goal payload covers all 6 phases with falsifiable exit gates, owner assignments, cost ceilings, halt conditions. Two paste forms: full body for fresh-AI-session paste, short version for Telegram /goal command referencing this spec.
