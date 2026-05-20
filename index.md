---
type: index
id: WIKI-INDEX
title: "Satory VKO Knowledge Base — Content Catalog"
tags: [index, navigation, root, catalog]
date: 2026-04-06
---

# Satory VKO — Content Catalog

Read [[CLAUDE|Schema]] first. Read [[COMPILED-KNOWLEDGE|Top 10 Things]] before working.

## Entities (People & Orgs)
### Core people
- [[madi-profile]] — **Madi Ayazbay full profile** — work + personal + operating principles (compiled 2026-04-09 from Claude.ai memory export)
- [[daniyar]] — Daniyar Kuvatov — **Satory CEO** (corrected from "Project Director" 2026-04-09)
- [[saken-rayo]] — Satory co-shareholder, GR / government relations ⚠️ **contradiction flagged 2026-04-09** (Saken Rayo vs Saken Orazalin)
- [[denis]] — Denis — Camera/DevOps Engineer
- [[nazel-lawyer]] — **Назель** (NOT Nazerke) — Satory Lawyer / Юрист (КоАП verification)
- [[ruslan-genetinov]] — Руслан Генетинов — Chief Engineer (government side, APK camera spreadsheet source)
- [[roza-sadyrova]] — Роза Sadyrova — Satory Security / Legal / GR director (ЭЦП owner)

### Core orgs
- [[nous-ai]] — Nous AI — AGaaS Holding Company (БИН 260240032631)
- [[spectra-its]] — Spectra ITS — Government VMS/ERAP Contractor (БИН 070640013540)
- [[satory]] — Satory Company LTD — Client / General Contractor (БИН 040940014188)
- [[maru-systems]] — Maru Systems — Data center / large-infra subsidiary of Satory
- [[satory-network]] — Satory Network — Fiber / network infrastructure division
- [[maru-analytics]] — Maru Analytics — 50/50 JV with KeyHorse (VMS/AI analytics, Astana Hub)
- [[satory-gas]] — Satory Gas — LPG company (Tulpar Gaz / LP Gaz, Turkestan, 2012)
- [[tdc-trading-dmcc]] — TDC Trading DMCC — Dubai commodity trading arm

### Tools + frameworks
- [[openclaw]] — **OpenClaw** — Multi-channel AI agent gateway (355K stars, 138+ CVEs, use as hardened single-agent gateway only)
- [[hermes-agent]] — **Hermes Agent** — Self-improving agent framework by Nous Research (55.6K stars, SSH backend, agentskills.io)
- [[gbrain-garrytan]] — **GBrain (garrytan/gbrain)** — Knowledge brain for AI agents (Postgres + pgvector, Karpathy wiki extended, already deployed)
- [[glm-5-1]] — **GLM-5.1 (Z.ai)** — Open-source coding model (744B MoE, MIT, 58.4 SWE-Bench Pro, 7.5x cheaper than Sonnet)

### Partners + competitors
- [[netline]] — NetLine (ООО НетЛайн, Samara) — Russian VMS / Safe City partner via Saken Rayo intro
- [[coram-ai]] — **Coram AI** — VMS partnership target (top priority, white-label Kazakhstan/Central Asia)
- [[keyhorse]] — KeyHorse — 50/50 JV partner via Maru Analytics (intersection AI excluded)
- [[keona-it]] — Keona Information Technology — Korean APK camera future partner (MOU signed, -40°C blocker)
- [[scylla]] — Scylla — US AI Computer Vision Partner
- [[sergek-group]] — Sergek Group / Көркем Телеком — **primary competitor, NEVER partner**
- [[global-vision-technologies]] — ТОО «Global Vision Technologies» — **APK→ЕРАП integration competitor**. 98M KZT / 243 APK / 7–20 days. Contact: Ефременко Г.А. (Николай) +7 747 500 0364

### Personal (family)
- [[family]] — Madi's immediate + extended family (Akmarzhan, Tamerlan, Shona, Smatay)

## Dashboards
- [[active-blockers]] — все нерешённые блокеры (live)
- [[recent-lessons]] — последние lessons learned
- [[audits-index]] — все аудиты
- [[sources-recent]] — последние ingested sources
- [[wiki-health]] — wiki health overview
- [[today]] — что важно сейчас

## Concepts (Technologies)
- [[glossary]] — Acronyms & domain terms (ERAP, АПК, ЛУ/ПРК, BDL, VMS, etc.)
- [[vault-model-decision]] — Two vaults, hub-and-spoke, why we chose it
- [[hybrid-model-routing]] — **Hybrid Model Routing (90/10 Rule)** — GLM-5.1 routine + Sonnet escalation + Opus rare
- [[skills-not-agents]] — **Skills, Not Agents** — Why depth (skills) beats width (more agents)
- [[agent-harness-ownership]] — **Agent Harness Ownership** — Memory IS the harness, open > closed
- [[factory-redesign-claude-as-ceo]] — Factory CEO upgrade proposal (Option B: Sonnet, Option A: agentic)
- [[competitors]] — Competitive Landscape — TargetAI, Sergek, Presight
- [[erap-concept]] — ERAP — Government Violation Processing System
- [[isapi-concept]] — ISAPI — Camera Event Protocol
- [[locked-decisions]] — Locked Decisions — Cannot Change
- [[smartbridge-concept]] — SmartBridge / ШЭП — Government Security Gateway
- [[vms-concept]] — VMS — Video Management System

## Specifications
- [[bdl_features]] — BDL Replacement Checklist
- [[cerebro_bdl_vms_requirements]] — 89 VMS Requirements
- [[cerebro_requirements]] — Cerebro Core Modules
- [[erap_requirements]] — ERAP Integration Requirements
- [[shep-client-registration-2026-04-08]] — ШЭП/ВШЭП client registration form values for sb.egov.kz KPSISU-S-5827 (Asyl to paste, 2026-04-08, FINAL login `spectraerap2026` after 3-step evolution from satoryerap→spectra_erap_2026→spectraerap2026, test env 65.108.215.200:443 HTTPS)
- [[phase-3-bdl-replacement-reqs-2026-04-08]] — Phase 3 factory REQ specs (REQ-090 through REQ-105) to prevent factory idling on restart; error boundary + lazy HLS previews + CommandPalette + StrongSwan + mediamtx + SOAP client
- [[factory-coder-prompt-fix-src-paths-2026-04-08]] — graph.py Coder prompt fix spec (bare src/ paths, lines 557/558/582) — NOT APPLIED
- [[remove-worker-task-filter-systemd-2026-04-08]] — systemd drop-in cleanup spec (remove WORKER_TASK_FILTER=frontend dead config) — NOT APPLIED
- [[website-restore-runbook-2026-04-09]] — **RUNBOOK** — one-line fix to restore `satory.nousagaas.com` from any broken state (`vercel alias set satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app satory.nousagaas.com`), verification commands, fingerprint table of 7 deploy IDs, fallback sequence, permanent deletion commands for Madi, rebuild-from-source section, troubleshooting. Read this when production is broken — do NOT use `vercel rollback`.
- [[audit-026-phase-2-to-5-execution-plan-2026-04-08]] — consolidated AUDIT-026 Phase 2-5 plan: Telegram channel, scheduled-tasks, agent teams, full exercise
- [[bdl-mergen-violation-card-schema-2026-04-08]] — reverse-engineered BDL/Mergen 2.0 violation card schema (10 tabs, field types, data sources) from Madi's 2026-04-08 screenshot — structural only, no PII — ground truth for Satory VKO drop-in replacement
- [[god-prompt-v1-design-2026-04-15]] — **DESIGN SPEC** — GOD_PROMPT v1.0 layered evolution-loop architecture (SOUL + AGENTS + HEARTBEAT + 15 skills + audit trail) replacing current lesson-heavy factory. 6 layers, 5 new skills + 4 extensions, 5 automation scripts, 8-phase migration with rollback, 10 verification gates. Aligns Karpathy SPL + Garry Tan SKILLPACK + Anthropic Agent Skills. **Status: APPROVED 2026-04-15** — implementation plan written.
- [[god-prompt-v1-implementation-2026-04-15]] — **PLAN** — 33 atomic tasks across 9 phases (P0 pre-flight, P1-P8 migration, POST audit trail) implementing the GOD_PROMPT v1.0 spec. Each task has complete content (no placeholders), TDD where applicable, save+sync discipline, 100%-or-STOP quality gate. **Status: draft awaiting Madi approval** — no execution until user picks subagent-driven vs inline.

## Skills
- [[planning-discipline]] — SKILL v1.0.0 — plan before touching, Musk 5-step filter, 100%-or-stop, per-subtask save+sync
- [[error-classification]] — SKILL v1.0.0 — L0-L4 error severity levels, classification protocol, response matrix
- [[mistake-to-skill]] — SKILL v1.0.0 — the evolution engine: lesson→skill→runtime pipeline + /skill-capture command
- [[kazakhstan-regulatory]] — SKILL v1.0.0 — KZ traffic law, МРП, ERAP fines, BINs, GOST, camera types, data residency
- [[evidence-verification]] — SKILL v1.0.0 — proof before assertion, data_freshness envelope, "I don't know" is valid, no hedge-language

## Systems
- [[nous-agent-soul]] — **SOUL** — Nous agent identity + hard limits (Layer 1 of 6-layer architecture per [[god-prompt-v1-design-2026-04-15]])
- [[nous-agent-user]] — **USER.md** — Madi model: business context, preferences, pressure points, family why, and operating style
- [[nous-agent-procedures]] — **AGENTS.md** — Nous agent procedure pointer (Layer 2 per [[god-prompt-v1-design-2026-04-15]])
- [[nous-agent-heartbeat]] — **HEARTBEAT** — cron catalog (Layer 4 per [[god-prompt-v1-design-2026-04-15]])
- [[api_routes]] — API Routes — api.nousagaas.com
- [[architecture]] — VPS Architecture
- [[cameras]] — Camera Network — 243 Cameras
- [[erap]] — ERAP Pipeline Technical
- [[runbook-claude-export-ingest]] — **Runbook: Claude.ai Data Export → Obsidian (Pathway 2)** — how to re-run the memories/projects/conversations ingest on every new export

## Legal
- [[koap_speed_fines]] — KoAP Speed Fines (Art 592)
- [[smartbridge-vshp-client-credentials-2026-04-08]] — 🔴 SENSITIVE: generated ШЭП client login + test/prod passwords for Satory VKO → ЕРАП integration (2026-04-08, rotation due 2026-07-07)

## Lessons
- [[LESSON-001-factory-rebuilt]] — Factory rebuilt
- [[LESSON-002-ceo-must-create-tasks-not-just-pick-them]] — CEO must CREATE tasks, not just PICK them
- [[LESSON-003-deploy-revert-comparison-bug]] — Deploy revert comparison bug
- [[LESSON-004-telegram-must-not-spam]] — Telegram must NOT spam
- [[LESSON-005-claude-must-read-mem0-wiki-before-designing]] — Claude must read Mem0+Wiki BEFORE designing
- [[LESSON-006-done-means-visible-in-browser]] — Done means VISIBLE in browser
- [[LESSON-007-6-website-pages-need-wiring]] — 6 website pages need wiring
- [[LESSON-008-vercel-deploys-use-uploaded-source-not-local-dist]] — Vercel deploys use UPLOADED source, not local dist
- [[LESSON-009-api-field-names-frontend-types-always-transform]] — API field names != frontend types — always transform
- [[LESSON-010-verify-deploy-with-content-not-just-http-200]] — Verify deploy with CONTENT, not just HTTP 200
- [[LESSON-011-sed-is-fragile-for-code-modifications]] — sed is fragile for code modifications
- [[LESSON-012-never-report-row-count-as-camera-count]] — Never report row count as camera count
- [[LESSON-013-factory-revert-loop-overwrites-manual-deploys]] — Factory revert loop overwrites manual deploys
- [[LESSON-014-command-palette-was-initialized-to-open]] — Command palette was initialized to open
- [[LESSON-015-registry-mrgn-ids-camera-ips]] — Registry MRGN IDs != Camera IPs
- [[LESSON-016-swr-cache-collision-critical]] — SWR cache collision — CRITICAL
- [[LESSON-017-show-nothing-rather-than-fake-data]] — Show NOTHING rather than FAKE data
- [[LESSON-018-every-fix-can-break-something-else]] — Every fix can break something else
- [[LESSON-019-smoke-test-caused-all-97-reverts-root-cause-found]] — SMOKE TEST caused ALL 97 reverts — ROOT CAUSE FOUND
- [[LESSON-020-reports-must-use-single-source-of-truth]] — Reports must use SINGLE source of truth
- [[LESSON-021-145-0-root-cause]] — 145 ЛУ камер онлайн но 0 событий — ROOT CAUSE
- [[LESSON-022-validator-rubber-stamps-0-effective-quality]] — Validator rubber-stamps — 0% effective quality
- [[LESSON-023-apk-not-camera-type]] — АПК это НЕ тип камеры — исправлено Сатори
- [[LESSON-024-ids-2cd9396-bis]] — Модель камеры iDS-2CD9396-BIS — откуда взялась
- [[LESSON-025-validator-root-cause-my-fault-not-gemini]] — Validator root cause — MY fault, not Gemini
- [[LESSON-026-camera-types-three-types-not-two]] — Camera types — THREE types not two
- [[LESSON-027-mem0-is-separate-from-local-memory-was-bypassed]] — Mem0 is SEPARATE from local memory — was bypassed
- [[LESSON-028-create-task-missing-ceo-looped-on-no-pending-tasks]] — create_task missing — CEO looped on No pending tasks
- [[LESSON-029-budget-correction-per-month-not-per-day]] — Budget CORRECTION — per MONTH not per DAY
- [[LESSON-030-stale-user-profile-dangerous]] — Stale user profile — DANGEROUS
- [[LESSON-031-is-not-madi-father]] — Данияр is NOT Madi father
- [[LESSON-032-claude-playwright-code-had-unboundlocalerror]] — Claude Playwright code had UnboundLocalError
- [[LESSON-033-command-palette-bug-returned-third-time]] — Command palette bug returned THIRD TIME
- [[LESSON-034-command-palette-bug-4x-root-cause-uncommitted-fixe]] — Command palette bug 4x — ROOT CAUSE: uncommitted fixes
- [[LESSON-035-ceo-drops-req-from-assignment]] — CEO drops REQ-xxx when writing assignment
- [[LESSON-036-placeholder-false-positive]] — Banned pattern placeholder caused false positive
- [[LESSON-037-agents-blind-to-wiki-schema]] — All agents except CEO blind to wiki schema
- [[LESSON-038-local-memory-cleanup]] — Local memory had 35 duplicates contradicting Obsidian
- [[LESSON-039-duplicate-factory-processes-doubled-budget]] — Duplicate factory processes doubled budget burn
- [[LESSON-040-zombie-tasks-cause-ceo-duplicates]] — Zombie in_progress tasks cause CEO duplicates
- [[LESSON-041-components-deployed-but-not-wired-into-router]] — Components deployed but not wired into router
- [[LESSON-042-law008-too-broad-blocked-legitimate-code]] — LAW-008 setTimeout pattern was too broad
- [[LESSON-043-tsc-strict-not-checked-183-type-errors-leaked]] — TypeScript strict not checked, 183 errors leaked
- [[LESSON-044-factory-watchdog-auto-restart]] — Factory has TWO watchdogs that auto-restart it
- [[LESSON-045-factory-git-add-all-steals-work]] — Factory git add -A steals uncommitted manual edits
- [[LESSON-046-mrgn-ip-mismatch]] — camera_registry uses MRGN ids, vehicle_events use IPs, no mapping
- [[LESSON-047-photo-retention-shorter-than-violations]] — Photo retention shorter than violation retention
- [[LESSON-048-phantom-directory-disaster]] — Phantom directory: factory wrote to nested INNER never deployed
- [[LESSON-049-session-key-username-vs-user]] — session.get(username) silent fallback to system

- [[LESSON-050-removed-imports-still-used]] — Sidebar import rewrite dropped Shield/Settings/etc, broke all routes
- [[LESSON-051-get-pending-tasks-hardcoded-project]] — Factory idle 10 cycles because CEREBRO project tasks were invisible
- [[LESSON-052-file-ops-double-prefix-phantom]] — Root cause of recurring phantom INNER: file_ops double-join
- [[LESSON-053-req005-tsc-baseline-creep]] — REQ-005 blocked by TSC baseline (deploy gate working)
- [[LESSON-054-ceo-empty-queue-burns-money]] — Empty CEO loop burned ~$6/day on hallucinated REQs
- [[LESSON-055-budget-hit-retry-loop]] — Budget gate returned but didn't sleep
- [[LESSON-056-anthropic-credit-exhausted-retry]] — Hard-stop missing on credit-low
- [[LESSON-057-ceo-swapped-opus-to-sonnet]] — CEO downgraded Opusu2192Sonnet, hard gate removed, 80% cost drop
- [[LESSON-058-erap-capture-mode]] — ERAP capture mode built (connect-and-extract leverage)
- [[LESSON-059-raw-folder-no-enforcement-got-messy]] — raw/ messiness root cause + auto-cleaner
- [[LESSON-060-plugin-hallucination-root-cause]] — recommended a plugin not in the Obsidian registry; verification rule for all ecosystem installs
- [[LESSON-061-claude-deleted-telegram-captures-during-rebase]] — Claude rm-ed Madi's 2 captured Telegram messages during a git rebase; recovered from history; new rule: never rm in raw/
- [[LESSON-062-ingest-burns-anthropic-on-empty-files]] — empty file in raw/pending/ burned ~440 wasted Anthropic API calls in 7 hours; ingest_pending.py patched to skip 0-byte files
- [[LESSON-063-mcp-tools-targets-claude-desktop-not-claude-code]] — recommended MCP Tools by Jack Steam for Claude Code without checking it actually targets Claude Desktop; Claude Code already has vault via nous-wiki-qmd
- [[LESSON-064-silent-ack-success-path]] — telegram_poll.py send_ack had silent success path; "you cannot audit what you cannot log"; fixed with explicit success/failure logging + plain-send fallback
- [[LESSON-065-wrong-project-detour]] — verify the deployed project before editing; Claude edited satory-frontend (inert fork) when the live site is satory-nextjs on Vercel; prevention rule: run `vercel project ls` + find `.vercel/` before touching frontend code
- [[LESSON-066-sync-script-tcc-blocked-under-launchagent]] — Mac↔VPS sync silently failed for 12h because LaunchAgent's `/bin/bash` lacks Full Disk Access to `~/Documents/`; error-swallowing `2>/dev/null || return 0` hid it; fix: TCC probe + loud logging + FDA grant instructions
- [[LESSON-067-next-build-passes-doesnt-mean-runtime-works]] — `next build` passing is necessary but NOT sufficient; client-side hydration crashes are invisible to the build step; deploy broke satory.nousagaas.com at 12:40, rolled back at 12:55; prevention: `next dev` + browser console smoke test + Vercel preview deploy before `--prod`
- [[LESSON-068-rollback-first-when-source-tree-unknown]] — when production breaks and you don't know which source tree built it, ROLLBACK to a fingerprint-matched prior deploy before hunting files. 6 rules: rollback-first, fingerprint via `vercel inspect` (bundle size + build outputs), verify HTML body never HTTP status alone, test backend integration after rollback, retain broken deploy ID for forensics, `ls` parent dir before declaring source unknown. **CORRECTED 2026-04-09** — original fix was wrong twice (wrong target + wrong command); see [[LESSON-069-vercel-rollback-doesnt-move-custom-domains]] for real root cause.
- [[LESSON-069-vercel-rollback-doesnt-move-custom-domains]] — `vercel rollback` only updates the Vercel project's default `<project>.vercel.app` subdomain, NOT custom domain aliases. For production custom domains like `satory.nousagaas.com`, ALWAYS use `vercel alias set <deploy-url> <custom-domain>`. The rollback command's success message is misleading when a custom domain is in play. Fixed the 2026-04-08/09 website crisis after LESSON-068's fix failed silently for hours.
- [[LESSON-078-surface-evaluation-not-evidence]] — Star count is not production readiness — evaluate by CVEs, user reports, and academic research (2026-04-11 architecture audit)
- [[LESSON-079-one-agent-not-sixteen]] — One agent with skills beats sixteen agents coordinating — EvoClaw 13.37% success rate + 4 failed multi-agent architectures (2026-04-11)
- [[LESSON-080-design-without-deployment]] — Design without deployment — Attempts 2+3 produced 449 messages of design, deployed nothing. 50-message rule. (2026-04-12)
- [[LESSON-082-audit-gaps-telegram-bot-verification]] — Audit declared Telegram ✅ via MCP bot (wrong bot); root causes: two-bot trap, lint 1/10 missed, banned_patterns.txt missing, LiteLLM restart not correlated; mandatory 8-step audit checklist. (2026-04-14)
- [[LESSON-084-qmd-lowercase-path-case-sensitivity]] — qmd returns lowercase slug paths; Linux fs is case-sensitive. _resolve_case() fix. Always test path resolution with is_file() before declaring integration working. (2026-04-14)
- [[LESSON-085-false-declaration-feature-done-without-end-to-end-test]] — Claiming features done without Telegram end-to-end test. Components existing ≠ full chain working. Four features were false-declared as done. (2026-04-14)
- [[LESSON-083-ready-declaration-without-outcome-test]] — Factory declared ready; first real task failed. Three root causes: mechanism test ≠ outcome test, MEMORY.md index ≠ content, agent has zero skills. Mandatory: run real-question test before any "ready" declaration. (2026-04-14)
- [[HANDOFF-2026-04-14-session10]] — Session 10 handoff: factory fully live, Grok+context wired, next = real tasks + implicit /ask forwarding (2026-04-14)
- [[HANDOFF-2026-04-14-session11]] — Session 11 handoff: factory cannot answer real questions yet — P0 = wire GBrain skill + outcome test before any "ready" declaration (2026-04-14)
- [[HANDOFF-2026-04-14-session12]] — Session 12 handoff: factory PRODUCTION-READY — 688 tests, NIIS question verified, wiki search wired, outcome smoke test live (2026-04-14)
## Audits
- [[AUDIT-011-karpathy-wiki-audit]] — Wiki health vs Karpathy pattern (7/10)
- [[AUDIT-012-overnight-failure-audit]] — Overnight factory audit, 5 root causes, 9 fixes
- [[AUDIT-013-frontend-triage-phase1]] — Frontend triage Phase 1 (OUTER vs INNER mapping)
- [[AUDIT-014-phase-2-execution]] — Phase 2 execution audit (in progress)
- [[AUDIT-015-phase-2-complete]] — Phase 2 complete: all 9+6 components real, factory back online
- [[AUDIT-016-brain-cli-evaluation]] — Karpathy LLM Wiki + brain CLI proposal evaluated against current Nous wiki
- [[AUDIT-017-brain-cli-adoption-complete]] — Lint cron + qmd + personal Brain scaffolded
- [[AUDIT-018-sync-and-lint-bulletproof]] — Lint contradictions resolved, bidirectional git sync wired
- [[AUDIT-019-session-close-apr7]] — Session close: vault model, meeting ingest, factory 2 RCs fixed, REQ-008 deployed
- [[AUDIT-020-factory-cost-leak-audit]] — Cost leak forensic + 4 fixes applied + factory paused awaiting Madi top-up
- [[AUDIT-021-strategic-reset-vpn-myth-factory-redesign]] — VPN myth busted, real blockers are OID/ECP/serviceId from KPSiSU
- [[AUDIT-022-nit-vpn-reversal-ceo-sonnet-leverage-strategy]] — NIT VPN reversal + Sonnet CEO swap + leverage strategy
- [[AUDIT-023-karpathy-llm-wiki-compliance-deep-audit]] — Karpathy compliance deep audit: 84% u2192 P0 fixes applied
- [[AUDIT-024-physical-enforcement-of-law5]] — 2026-04-08 physical enforcement of LAW-005 via symlink + tools mirror + telegram ACK + dead-plugin cleanup
- [[AUDIT-025-bot-mcp-tools-data-loss-audit]] — re-audit triggered by Madi: telegram bot end-to-end + MCP Tools client mismatch + 4 bugs found and fixed (data loss recovered)
- [[AUDIT-026-six-feature-strategic-fit]] — strategic fit of 6 features (TaskCompleted hook, native Telegram channel, /batch, agent teams, /loop+scheduled-tasks, custom setup); "Official bones, custom muscle"; Phase 1-5 migration plan
- [[AUDIT-027-god-level-alignment-vs-trefethen-mempalace-brain]] — god-level alignment audit: Nous wiki vs fuller production schema + MemPalace + brain CLI; 87% score (up from AUDIT-023's 84%); P0 CLAUDE.md upgrade + frontmatter backfill gated on Madi approval
- [[AUDIT-028-bulletproof-post-fda-and-physical-enforcement-gaps]] — bulletproof audit post-FDA grant. 85% today, 100% after `additionalDirectories` whitelist approval. Round-trip test passed at 88s Mac→VPS propagation.
- [[AUDIT-029-three-vpns-reconciled-camera-nit-firewall]] — 3-VPN definitive reconciliation: Camera IPsec (ESTABLISHED), NIT SmartBridge (PENDING via Asyl's form), MikroTik ACL (Denis pending). Revises AUDIT-021 per LAW-013.
- [[satory-expansion-3-regions]] — NEW core project: Satory expansion via Russian white-label partner
- [[saken-aga-netline-briefing-ru]] — Брифинг для Сакена ага по NetLine (RU, готов к выдаче)
- [[obsidian-plugins-install-guide-ru]] — Пошаговая инструкция установки Obsidian community plugins (RU)
- [[madi-personal-capture-workflow-ru]] — Полный workflow Madi от телефона/Telegram до Obsidian (RU)
- [[madi-workflow-corrections-v2-ru]] — V2 корректировки + Claude Code MCP в Obsidian + точные имена плагинов
- [[iphone-capture-shortcut-setup-ru]] — пошаговая установка iOS Shortcut для capture
- [[AUDIT-001-complete-frontend-audit-all-pages]] — Complete frontend audit — ALL pages
- [[AUDIT-002-honest-real-vs-fake-assessment]] — Honest real vs fake assessment
- [[AUDIT-003-atomic-audit-64-issues-found]] — ATOMIC AUDIT — 64 issues found
- [[AUDIT-004-atomic-law-enforcement-audit-14-fixes-applied]] — Atomic law enforcement audit — 14 fixes applied
- [[AUDIT-005-obsidian-structure-audit-10-issues-found-and-fixed]] — Obsidian structure audit — 10 issues found and fixed
- [[AUDIT-006-flow-audit-traced-factory-execution-path-start-to]] — Flow audit — traced factory execution path start to finish
- [[AUDIT-007-agent-by-agent-execution-trace-audit]] — Agent-by-agent execution trace audit
- [[AUDIT-008-will-factory-actually-work]] — Will the factory actually produce results?
- [[AUDIT-009-cycle1-live-test]] — Cycle 1 Live Test
- [[AUDIT-010-3-cycle-live-test]] — 3-Cycle Live Test Results

## Progress
- [[bdl-replacement-state-2026-04-07]] — Live BDL replacement state, blockers, money clock
- [[PROGRESS-001-frontend-pages-verified-working]] — Frontend pages verified working
- [[PROGRESS-002-camera-registry-live]] — Camera registry live
- [[PROGRESS-003-session-summary]] — Session summary
- [[PROGRESS-004-factory-restarted-smoke-test-fixed]] — Factory restarted — smoke test fixed
- [[PROGRESS-005-playwright-installed-server-upgraded]]
- [[HANDOFF-2026-04-07]] — RESUME-FROM-HERE session handoff (Phase 2 in progress) — Playwright installed + server upgraded
- [[HANDOFF-2026-04-07-EOD]] — End-of-day handoff + 2026-04-08 morning corrections section
- [[HANDOFF-2026-04-08]] — 2026-04-08 session close handoff (read FIRST in next session)
- [[session-20260408-0020-law5-physical-enforcement]] — Overnight autonomous session digest (2026-04-08 morning)
- [[todo-live-cameras-on-satory-frontend]] — P0 next session: live camera feeds on satory.nousagaas.com [demo]
- [[asyl-reply-shep-2026-04-08]] — Reply to Asyl with ШЭП client login + test/prod passwords + test env IP/port/protocol (delivered via @nousAGaaSbot 2026-04-08, 4 iterations: initial→satoryerap→spectra_erap_2026→FINAL spectraerap2026)
- [[camera-path-c-staging-2026-04-08]] — Camera Path C hls.js code staged on ~/Desktop/satory-nextjs/ (next build passes), pending vercel --prod approval
- [[session-close-2026-04-08-audit]] — Session-close digest tying every artifact from 2026-04-08 together (read FIRST in next session)
- [[sync-repair-2026-04-08]] — Mac↔VPS sync script root-cause audit + repair (TCC block on /bin/bash, 12h silent failure, reconciled at 93e0573, FDA instructions for Madi)
- [[HANDOFF-2026-04-08-EOD]] — **READ FIRST** — 2-hour autonomous run EOD handoff: 13 new pages, 10 phases, camera preview ready for visual verify, Phase 3 factory specs ready, physical enforcement proposal pending approval
- [[madi-personal-action-items-2026-04-08]] — 4 ready-to-forward Russian draft texts (BDL letter via Rose, Satory↔Spectra pilot contract skeleton, Denis Telegram for 59 camera creds, state authorization letter to КПСиСУ)
- [[shep-submission-confirmed-2026-04-08]] — MILESTONE: ШЭП/SmartBridge client registration Заявка №202611754060 submitted on `sb.egov.kz` at 08.04.2026 12:52, currently at step 2/6 (Согласование с владельцем), login `spectraerap2026`, test+prod passwords stored
- [[HANDOFF-2026-04-08-NIGHT]] — **READ FIRST NEXT SESSION** — definitive 2026-04-08 night close: website-crisis investigation (deployed build NOT from /Users/madia/Desktop/satory-nextjs — smoking gun), Telegram-spam audit (5 msgs to bot chat were noise), Karpathy self-audit (~88% compliant), dual-sync race decision pending, additionalDirectories approved-not-applied, 9 open items for new Claude
- [[session-start-instructions-2026-04-08]] — exact copy-paste prompt Madi pastes at start of new Claude Code conversation to force read-order + 6-point self-check before any action
- [[daniyar-response-draft-2026-04-09]] — Russian 3-point Telegram reply draft to Daniyar (Satory CEO): APK-Кордон VMS integration requirements + 30–40 min live demo offer + missing 3rd question
- [[roza-keona-kp-capability-list-2026-04-09]] — **★ КП capability list for Роза (90 highway average-speed complexes, due tonight): 25 violation types, 17 Keon-A product lines, −40°C cold-weather solution, 2019 ISC Almaty seatbelt/phone pilot, BOMs, pricing range $1.62M–$1.72M**
- [[MASTER-DECISIONS-2026-04-12]] — **MASTER DECISIONS** — Triple-AI validated build list: 8 skills, model routing, security, data residency, revenue model, this week's 7 actions
- [[SYNTHESIS-2026-04-12-three-ai-research]] — **Three AI synthesis** — Grok + Claude + Gemini research responses compared, disagreements resolved, updated architecture
- [[HANDOFF-2026-04-12-factory-rebuild-plan]] — **Factory rebuild deep dive + research prompts** — Root cause all 4 attempts, hybrid model strategy (GLM-5.1 + Sonnet), 4 research prompts for Gemini/Grok/Claude, Elon's 5 rules, skills-not-agents architecture
- [[HANDOFF-2026-04-11-architecture-audit]] — **Architecture deep audit + Garry Tan GBrain discovery** — OpenClaw CVEs, Hermes verification, GBrain identity resolved, corrected single-agent architecture, Garry Tan's setup philosophy from 7 screenshots
- [[MEMORY]] — Claude Code session auto-memory (symlinked into vault at `pages/progress/claude-memory/MEMORY.md`, read-first every new session, trimmed to 150 lines 2026-04-08 night)

## Roadmap
- [[multi_tenancy_spec]] — Multi-tenancy Spec (Post-Demo)
- [[scaling_to_billion]] — Scaling to Billion — AGaaS Roadmap

## Team
- [[blockers]] — Human Blockers — Updated April 6, 2026

## Sources
- [[source-gvt-meeting-2026-04-14]] — **Global Vision Technologies meeting (2026-04-14)** — Competitor intelligence: GVT doing same APK→ЕРАП integration. 98M KZT / 243 APK / 7-20 days / Hikvision / ISAP / "Klubtika" VPN
- [[source-claude-export-memories-2026-04-09]] — **Claude.ai Data Export (2026-04-09)** — memories.json (curated AI memory) + projects.json (8 Projects). Drove 5 entity updates + 14 new entity creates. Contradictions logged: factory architecture (CEO/Coder/Validator/Researcher vs Paperclip CEO/CTO/Frontend/CMO/Auditor vs CoS/Forge/Alpha/Nova/Echo/Lens) and Saken Rayo vs Saken Orazalin identity

### claude-history (from `conversations.json`, 294 conversations, 158 MB, 2024-08-31 → 2026-04-06)
- [[source-claude-history-index-2026-04-09|claude-history/index-2026-04-09]] — master index of all 294 conversations with topic, date, message counts, UUID
- [[topic-work-vms]] — 48 conversations — Satory VKO / ERAP / BDL / cameras / VMS / Coram AI / KeyHorse
- [[topic-family-personal]] — 25 conversations — Akmarzhan / Tamerlan / Shona / health / KIS
- [[topic-travel]] — 19 conversations — Seoul / Phuket / Belek / logistics
- [[topic-commodity-trading]] — 13 conversations — TDC Trading / phosphate / steel / freight
- [[topic-nous-factory]] — 12 conversations — Paperclip / CoS-Forge-Alpha / agents / multi-agent
- [[topic-deals-investments]] — 8 conversations — helium / 280MW gas turbine / water PPP / investment pipeline
- [[topic-restaurant-app]] — 1 conversation — Kazakhstan superapp
- [[topic-claude-code]] — 1 conversation — Claude Code usage
- [[topic-other]] — 167 conversations — uncategorized (classification tuning pending)

- [[source-smatay-asyl-madi-apr7]] — 3-way meeting unblocking VPN/ERAP/BDL (priority 1, April deadline)
- [[outreach-messages-2026-04-07]] — Russian Telegram messages for Asyl/Denis/Aidana/Roza/Tolgat (copy-paste ready)
- [[asyl-questions-2026-04-07]] — Copy-paste message for Asyl with the 4 questions Sergek must answer
- [[vpn-erap-deployment-checklist]] — Operational checklist for VPN+ERAP deployment (P0)
- [[source-apk-erap-apr3]] — Source: APK ERAP Integration Discussion
- [[source-asylbek-telegram-apr6]] — Source: Asylbek Telegram Messages (April 6, 2026)
- [[source-ecp-requirements-pdf-2026-04-08]] — Source: ЭЦП Usage Requirements PDF (ШЭП/ВШЭП rules reference for ЕРАП client integration, 2026-04-08)
- [[source-nit-vpn-tech-conditions-2026-04-08]] — Source: NIT IPSec/IKEv2 VPN Technical Conditions (7 requirements for вне ЕТС ГО clients, PEER IP 195.12.122.44, REVISES AUDIT-021's "no VPN" conclusion)
- [[source-autofix-pr-research-2026-04-08]] — Source: `/autofix-pr` research — feature doesn't exist as CLI slash command, it's Claude Code on the web cloud UI only, partial fit for our setup
- [[source-bdl-bypass-feb20]] — Source: BDL Bypass Strategy (Feb 20)
- [[source-bdl-replacement-apr2]] — Source: BDL Server Replacement & ERAP Integration
- [[source-consultation-mar19]] — Source: Technical Consultation (Mar 19)
- [[source-erap-decision-apr1]] — Source: ERAP Integration Decision via SmartBridge
- [[source-infrastructure-apr1]] — Source: Infrastructure Projects (Data Center + Gas Power)
- [[source-jacub-briefing-feb16]] — Source: Jacub Fura Audit Briefing (Feb 16, 2026)
- [[source-kiona-mar10]] — Source: KIONA Partnership Meeting (Mar 10, Seoul)
- [[source-master-state-apr1]] — Source: Spectra ITS Master State (April 1, 2026)
- [[source-scylla-meeting-mar7]] — Source: Scylla Partnership Meeting (March 7, 2026)
- [[source-smartbridge-apr3]] — Source: SmartBridge Integration & Mergen Diagnostics
- [[source-weekly-feb23]] — Source: Weekly Call Feb 23
- [[source-weekly-mar16]] — Source: Weekly Call Mar 16
- [[source-weekly-mar30]] — Source: Weekly Call Mar 30

## Other
- [[AMENDMENT-001-circuit-breaker]] — Circuit Breaker
- [[AMENDMENT-002-post-deploy-check]] — Post-Deploy Content Check
- [[AMENDMENT-003-memory-sync]] — Twice-Daily Wiki Sync
- [[COMPILED-KNOWLEDGE]] — Compiled Knowledge — What Every Agent Must Know
- [[INDEX]] — Laws and Rules Index
- [[LAW-001-evolution]] — The Evolution Law
- [[LAW-002-autofine]] — Violation Auto-Fine Rules
- [[LAW-003-continuous-audit]] — Continuous Audit
- [[LAW-004-5-commandments]] — 5 Commandments for Agent Deployments
- [[LAW-005-obsidian-master]] — Obsidian is Single Source of Truth
- [[LAW-006-task-equals-requirement]] — Every Task Must Trace to a Requirement
- [[LAW-007-hub-and-spoke]] — Hub-and-Spoke — CEO is the Hub
- [[LAW-008-anti-hallucination]] — Anti-Hallucination — Evidence Chain
- [[LAW-009-self-evolution]] — Self-Evolution — Agents Get Better Every Cycle
- [[LAW-010-escalation-only]] — Escalation-Only — Madi Out of the Loop
- [[LAW-011-business-gate]] — Business Gate — Every Task Must Have Business Outcome
- [[LAW-012-golden-deploy]] — Golden Deploy — All Checks Pass Before Production
- [[LAW-013-truth]] — 100% Truth
- [[LAW-014-watchdog]] — Watchdog — Independent Monitor
- [[LAW-015-root-cause-evolution]] — Every mistake must have root cause + fix + learning
- [[PERMANENT-RULES]] — 18 Permanent Rules
- [[auto_lessons]] — Auto-Generated Lessons Index
- [[log]] — Change Log
- [[model_economics]] — Factory Model Lineup and Costs
- [[overview]] — Satory VKO Project Overview
- [[root_cause_analysis]] — Root Cause Analysis Collection

## Dashboards
- [[audits-index]] — All audits (dataview)
- [[sources-recent]] — Recent ingested sources (dataview)
- [[recent-lessons]] — Recent lessons (dataview)
- [[satory-revenue-room-2026-04-27]] — Satory revenue room — president-level money loop dashboard

## Recent doctrine + operations (April 2026)

### Audits
- [[AUDIT-TELEGRAM-CONTROL-PLANE-2026-04-26]] — Telegram control plane audit (2026-04-26)
- [[AUDIT-057-sovereign-agaas-infra-dgx-spark-2026-04-28]] — Sovereign AGaaS infra DGX Spark eval (2026-04-28)
- [[AUDIT-054-morning-review-followup-2026-04-28]] — Morning review follow-up (2026-04-28)
- [[gbrain-weekly-2026-04-20]] — gbrain weekly health audit (2026-04-20)

### Specs
- [[two-track-erap-strategy-2026-04-16]] — Two-track ERAP strategy (2026-04-16)
- [[satory-assistant-search-tz-2026-04-29]] — Satory assistant search ТЗ (2026-04-29)
- [[SPEC-WEEKLY-DESKTOP-CLEANUP-2026-04-09]] — Weekly desktop cleanup spec (2026-04-09)

### Systems
- [[gstack-upgrade-state-2026-04-28]] — gstack upgrade state (2026-04-28)
- [[github-automation-state-2026-04-28]] — GitHub automation state (2026-04-28)

### Plans
- [[2026-04-14-grok-context-injection]] — Grok context injection plan (2026-04-14)
