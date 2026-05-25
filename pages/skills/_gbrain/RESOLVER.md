---
type: note
id: RESOLVER
title: "RESOLVER"
date: 2026-04-30
last_updated: 2026-05-17
status: ingested
---

# GBrain Skill Resolver

This is the dispatcher. Skills are the implementation. **Read the skill file before acting.** If two skills could match, read both. They are designed to chain (e.g., ingest then enrich for each entity).

## Always-on (every message)

| Trigger | Skill |
|---------|-------|
| Every inbound message (spawn parallel, don't block) | `skills/_gbrain/signal-detector/SKILL.md` |
| Any brain read/write/lookup/citation | `skills/_gbrain/brain-ops/SKILL.md` |
| Any brain-aware skill about to start (search-before / save-after pattern, gstack v0.18.0.0) | `skills/_gbrain/BRAIN-AWARE-INVOCATION.md` |

## Brain operations

| Trigger | Skill |
|---------|-------|
| "What do we know about", "tell me about", "search for", "look up", citation lookup | `skills/_gbrain/query/SKILL.md` |
| Creating/enriching/updating a person, company, or brain page | `skills/_gbrain/enrich/SKILL.md` |
| Where does a new file go? Filing rules | `skills/_gbrain/repo-architecture/SKILL.md` |
| Fix broken citations in brain pages | `skills/_gbrain/citation-fixer/SKILL.md` |
| "Research", "track", "extract from email", "investor updates", "donations" | `skills/_gbrain/data-research/SKILL.md` |
| Share a brain page as a link | `skills/_gbrain/publish/SKILL.md` |

## Content & media ingestion

| Trigger | Skill |
|---------|-------|
| User shares a link, article, tweet, idea, or says "write this to the wiki" | `skills/_gbrain/idea-ingest/SKILL.md` |
| Web URL needs clean markdown extraction (article/blog/doc page) — token-saving alternative to WebFetch; skip for `.md` URLs | `skills/defuddle/SKILL.md` |
| Video, audio, PDF, document, book, YouTube, screenshot; ingest/process a typed media artifact | `skills/_gbrain/media-ingest/SKILL.md` |
| Reading a book/chapter/PDF with Madi as a memory-aware thinking partner; "read this book with me"; "talk to the book"; full-text collaborative nonfiction reading | `skills/collaborative-reading/SKILL.md` |
| Meeting transcript received | `skills/_gbrain/meeting-ingestion/SKILL.md` |
| Generic "ingest this" (auto-routes to above) | `skills/_gbrain/ingest/SKILL.md` |

## Thinking skills (from GStack — invoke via `Skill` tool, not mental simulation)

**MANDATORY:** any plan >2h / >3 subsystems / >200 lines / new doctrine skill → invoke the 4-role multi-reviewer via `Skill` tool (NOT mental simulation). Session-64 root-caused the drift: mental simulation doesn't count, doesn't compound, and isn't falsifiable. See `karpathy-loop` AP-5.

| Trigger | gstack Skill to invoke |
|---------|-------|
| "Brainstorm", "I have an idea", "is this worth building", "office hours" | `Skill(office-hours)` |
| "CEO review", "rethink scope", "is this ambitious enough", "plan review strategic" | `Skill(plan-ceo-review)` |
| "DX review", "developer experience audit", "API design review", "SDK review" | `Skill(plan-devex-review)` |
| "Design review of the plan", "designer's eye", "visual plan review" | `Skill(plan-design-review)` |
| "Eng review", "architecture review", "lock in the plan", "catch arch issues" | `Skill(plan-eng-review)` |
| "Auto review", "run all 4 reviews", "review this plan automatically" | `Skill(autoplan)` — dispatches all 4 above + aggregates |
| "LLM Council", "5-advisor", "council pass", "adversarial review", "domain expert review" | `skills/karpathy-loop/SKILL.md` AP-5 Rule 6 + AP-12 — only when AP-5 also hits IR/cost/security/single-ablation/lock-in predicates |
| "IR methodology review", "retrieval methodology", "eval design rigor", "RRF", "HyDE", "MRR", "nDCG" | `skills/karpathy-loop/SKILL.md` AP-12 IR predicate — dispatch Domain Expert advisor and synthesize into the fold-list |
| "cost arithmetic review", "call-graph projection", "novel latency", "shared key blast radius" | `skills/karpathy-loop/SKILL.md` AP-12 cost predicate — dispatch Cost/Latency Hawk advisor |
| "prompt injection review", "billing isolation", "shared API key risk", "security isolation" | `skills/karpathy-loop/SKILL.md` AP-12 security predicate — dispatch Adversarial Skeptic advisor |
| "Second opinion", "codex review", "challenge my code", "ask codex" | `Skill(codex)` |
| "Debug", "fix", "broken", "investigate error", "root cause this" | `Skill(investigate)` |
| "Retro", "what shipped this week", "retrospective" | `Skill(retro)` |
| "Ship", "create PR", "push to main", "deploy" | `Skill(ship)` — full ship workflow |
| "Land and deploy", "merge and verify" | `Skill(land-and-deploy)` |
| "Design review of live site", "visual QA", "polish the look" | `Skill(design-review)` |
| "QA test this", "find bugs", "test and fix" | `Skill(qa)` or `Skill(qa-only)` |
| "Security review", "CSO mode", "threat model", "OWASP" | `Skill(cso)` or `Skill(security-review)` |
| "Make PDF", "turn markdown into publication-quality PDF" | `Skill(make-pdf)` |
| "Review this PR", "pre-landing review", "check my diff" | `Skill(review)` |
| "Guard mode", "careful mode", "freeze edits to this dir" | `Skill(guard)` / `Skill(careful)` / `Skill(freeze)` |

> All of these skills are installed via the `superpowers` / `andrej-karpathy-skills` / `gstack` plugins at `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.0.7/`. Invoke via `Skill(<name>)` — NOT via Read of the skill file, NOT via mental simulation of the role. See `karpathy-loop` AP-5.

## Operational

| Trigger | Skill |
|---------|-------|
| Task add/remove/complete/defer/review; "add task:"; pending tasks | `skills/_gbrain/daily-task-manager/SKILL.md` |
| Todoist "god level" · no no-section · task owner/department/priority/hashtags · Todoist/Notion documentation in Russian · Todoist human-owner daily reminders · Todoist control-plane sync · global Todoist hygiene audit | `skills/todoist-control-plane/SKILL.md` |
| Durable Notion + Todoist + Obsidian/gbrain + GitHub + LangSmith + Telegram/factory sync loop · "control plane sync" · "keep everything updated automatically" · hourly/3-hour operating-system sync · Hermes/OpenClaw supervision · human-owner reminder freshness | `skills/control-plane-sync/SKILL.md` |
| Morning prep, meeting context, day planning | `skills/_gbrain/daily-task-prep/SKILL.md` |
| Daily briefing, "what's happening today" | `skills/_gbrain/briefing/SKILL.md` |
| Cron scheduling, quiet hours, job staggering | `skills/_gbrain/cron-scheduler/SKILL.md` |
| After-hours response gating; health goals; bedtime/quiet hours; deciding whether Telegram/OpenClaw should answer now or hold for morning | `skills/operator-boundaries/SKILL.md` |
| Save or load reports | `skills/_gbrain/reports/SKILL.md` |
| "Create a skill", "improve this skill" | `skills/_gbrain/skill-creator/SKILL.md` |
| Cross-modal review, second opinion | `skills/_gbrain/cross-modal-review/SKILL.md` |
| "Validate skills", skill health check | `skills/_gbrain/testing/SKILL.md` |
| Webhook setup, external event processing | `skills/_gbrain/webhook-transforms/SKILL.md` |
| Satory dashboard health, camera freshness, "portal broken", "cameras not reflecting", LAW-016, Satory АПК / ЕРАП status, ПО работает с АПК, фиксирует ли АПК, аппаратно-программный комплекс | `skills/satory-dashboard/SKILL.md` |
| Storing/rotating an API token or bot token · deploying `.env` to VPS/Air · "pipe-never-variable" · "Keychain" · secrets hygiene | `skills/secrets-management/SKILL.md` |
| **Need a credential / API token / API key** · "what's the X token" · before asking user to paste · third-party service auth · "I don't have the token" | `skills/credentials-discovery/SKILL.md` (Tier 2 — manifest-first lookup, NEVER paste-from-Madi) |
| "Audit Obsidian + gbrain + OpenClaw together" / "library-grade scorecard" / "is retrieval working" / "/audit library" / "are we synced" / "brain_score not moving" / "extract creates 0 links/timeline" / "btree row size exceeds 2704" | `skills/library-grade-audit/SKILL.md` |

## Setup & migration

| Trigger | Skill |
|---------|-------|
| "Set up GBrain", first boot | `skills/_gbrain/setup/SKILL.md` |
| "Install GBrain" (DEPRECATED — file redirects to setup) | `skills/_gbrain/install/SKILL.md` |
| "Migrate from Obsidian/Notion/Logseq" | `skills/_gbrain/migrate/SKILL.md` |
| Brain health check, maintenance run | `skills/_gbrain/maintain/SKILL.md` |
| "Extract links", "build link graph", "populate timeline" | `skills/_gbrain/maintain/SKILL.md` (extraction sections) |
| "Brain health", "what features am I missing", "brain score" | Run `gbrain features --json` |
| "Set up autopilot", "run brain maintenance", "keep brain updated" | Run `gbrain autopilot --install --repo ~/brain` |
| Agent identity, "who am I", customize agent | `skills/_gbrain/soul-audit/SKILL.md` |

## Identity & access (always-on)

| Trigger | Skill |
|---------|-------|
| Non-owner sends a message | Check `ACCESS_POLICY.md` before responding |
| Agent needs to know its identity/vibe | Read `SOUL.md` |
| Agent needs user context | Read `USER.md` |
| Operational cadence (what to check and when) | Read `HEARTBEAT.md` |

## Disambiguation rules

When multiple skills could match:
1. Prefer the most specific skill (meeting-ingestion over ingest)
2. If the user mentions a URL, route by content type (link → idea-ingest, video → media-ingest)
3. If the user mentions a person/company, check if enrich or query fits better
4. Chaining is explicit in each skill's Phases section
5. When in doubt, ask the user
6. Do not choose broad always-on rows (`_gbrain/brain-ops`, signal-detector, brain-aware invocation) when a specific operational/domain row matches.
7. `/ask` routes to `ceo-hierarchy`; `/status`, `/health`, `/handoff`, `/code`, and outbound Telegram commands route to `command-center`.
8. Brain write/capture/idea/link/article requests route to `_gbrain/idea-ingest`; brain lookup/search/citation requests route to `_gbrain/query`; task add/remove/complete/defer/review routes to `_gbrain/daily-task-manager`.
9. Air + SSH/Tailscale reachability routes to `air-ssh-access`; Mac Tailscale logged-out/version-mismatch/dual-install routes to `tailscale-stability`.
10. GOST, ERAP, ВШЭП, SOAP, and SmartBridge signing routes to `smartbridge-soap-client`.
11. Task-execution planning such as "plan the task", "what should I do next?", or scope/spec discipline routes to `planning-discipline`; calendar/morning/meeting/day prep routes to `_gbrain/daily-task-prep`; skillify/lock-as-skill/turn-bug-into-skill routes to `mistake-to-skill`.

## Conventions (cross-cutting)

These apply to ALL brain-writing skills:
- `skills/_gbrain/conventions/quality.md` — citations, back-links, notability gate
- `skills/_gbrain/conventions/brain-first.md` — check brain before external APIs
- `skills/_gbrain/_brain-filing-rules.md` — where files go
- `skills/_gbrain/_output-rules.md` — output quality standards



## AGaaS Factory (Nous AGaaS project-specific)

These skills are project-specific to the Nous AGaaS factory. They are stored in `~/nous-agaas/skills/` (NOT `skills/_gbrain/`).

| Trigger | Skill |
|---------|-------|
| Multi-day/multi-week build · significant integration/migration/research task · autonomous build manager doctrine · best-in-class end-to-end execution bar | `skills/autonomous-build-manager/SKILL.md` |
| LiteLLM/open-model harness tuning · DeepSeek/Kimi/OpenRouter performance · prefix-cache/session pinning · provider fallback/capability flags · open-model cost optimization | `skills/agent-harness-optimization/SKILL.md` |
| Every new session — read FIRST before any work · runtime behavioral contract · DONE protocol (4 artifacts) · trigger words (`prove it` / `честно` / `delete?` / `kill`) · Musk 5-step step-2-first discipline · AP-1 "golden prompt" treadmill tripwire | `skills/session-operating-contract/SKILL.md` |
| Every session close (apply 6-axis scorecard) · any plan beyond single-edit (invoke multi-virtual-reviewer GStack CEO/DevEx/Designer/Eng) · "do we have the karpathy loop?" · about to write "Karpathy 6/6" in a handoff · new AP identified (run compound-chain cross-layer check) · Tan/Karpathy/Finn + Musk 5-step + billion-dollar-solopreneur framing | `skills/karpathy-loop/SKILL.md` |
| Agent-session topology · one-driver-many-crons pattern · 1+3+dispatch · Stream-A lock · parallel Claude/Codex sessions on the same vault · session architecture | `skills/session-architecture/SKILL.md` |
| Every non-trivial engineering decision · about to simplify/optimize without first deleting · requirement arrives unsigned ("docs say" / "API says" / "always been done") · timeline feels long → parallelize · bottleneck investigation (attack the constraint) · inventing a new acronym · claiming something "impossible" (ask "what would it take?") · computing cost/complexity (Idiot Index + Magic-Wand-Number) · The Algorithm 5 steps in order · "physically impossible not to work like this" enforcement pattern | `skills/musk-algorithm/SKILL.md` |
| Every session start (read SOAO Section 8 parallel-session scan) · about to declare or expand session scope · about to edit a known-shared file (any SKILL.md, MEMORY.md, RESOLVER.md, soao.sh, hooks, CLAUDE.md) · need to query "who is working on X right now" · SOAO reports 🟡 PARALLEL active session(s) | `skills/session-coordination/SKILL.md` |
| Before any code edit / code write / refactor / "fix"/"add"/"implement"/"build" / multi-step coding task / before committing · user feedback about scope-creep or overcomplication | `skills/karpathy-coding-principles/SKILL.md` |
| User asks "how do I do X" / "find a skill for X" / "is there a skill that can..." / expresses interest in extending capabilities / wants to search tools/templates/workflows | `skills/find-skills/SKILL.md` |
| User DMs /ask on Telegram (routes via Tier-1 grok-ceo → Tier-2 nous/opus → Tier-3 workers) · /ask-direct bypass · /trace <msg_id> · cost transparency for multi-tier queries · debugging tier routing · rollback/tune hierarchy | `skills/ceo-hierarchy/SKILL.md` |
| "I don't know" · "what is the latest" · "current best practice for" · "compare X vs Y" · "research before deciding" · `/consult` · "ask all three models" · "multi-model this" · any AP-12 Council escalation trigger (IR/retrieval, novel cost/latency, security/billing isolation, single-ablation evidence, lock-in risk) | `skills/multi-model-consult/SKILL.md` |
| Grok/xAI Premium image gen · Grok video gen · xAI Imagine API · `/grok-image` · `/grok-video` · `grok-imagine-image-quality` · `grok-imagine-video` · `grok-imagine-image-pro` deprecation (refuse) · xAI Voice API (TTS+STT) · x_post_search (NOT in public API) · xAI cost gate · `tools/grok_image_gen.py` · `tools/grok_video_gen.py` | `skills/xai-premium-tools/SKILL.md` |
| Deals / tenders / pipeline · `pages/deals/` · `DEAL-<date>-<slug>.md` · Russian stages (ведущий/квалифицированный/предложение/переговоры/выигран/проигран) · gbrain-native CRM · weekly Telegram digest Sat 09:00 KZT · `tools/deals_pipeline_view.py` · `com.nous.pipeline-weekly-digest` · lost-deal post-mortem council · stuck-deal detection >14d · Madi's tender pipeline | `skills/gbrain-deals/SKILL.md` |
| About to declare done / claiming something works / testing | `skills/agent-quality/SKILL.md` |
| Any task — read this first before acting | `skills/agent-quality/SKILL.md` |
| Deploy/restart/upgrade factory components (OpenClaw, LiteLLM, launchd, Docker); deploy new factory component | `skills/infrastructure/SKILL.md` |
| LiteLLM running / LiteLLM down / LiteLLM check / restart OpenClaw container / upgrade Docker / launchd job failing | `skills/infrastructure/SKILL.md` |
| Factory audit, /audit SUBSYSTEM | `skills/audit/SKILL.md` |
| Telegram operational commands, /code, /status, /handoff, /health, /health check | `skills/command-center/SKILL.md` |
| Send telegram message / send telegram / DM Madi / push to Madi / outbound telegram | `skills/command-center/SKILL.md` |
| /resume <lane> · failover ledger · orphan sweep · provider probe · resume prompt v2 · OpenBrain capture per failure · mistake-to-skill ledger append · cross-host parity drift · `MODEL-FAILOVER-LATEST.md` · `parity-latest.json` · `parity-manifest.txt` · `_mutate_state` · model timeout/rate-limit/crash/abandoned | `skills/model-failover/SKILL.md` |
| gbrain upgrade, context poisoning, brain maintenance/operations | `skills/gbrain-ops/SKILL.md` |
| Unified library graph · library health dashboard · resolver reachability · canonical registry · RRF search · OpenBrain bidirectional sync · Obsidian/gbrain/OpenBrain retrieval library | `skills/library-graph/SKILL.md` |
| OpenBrain projection · OpenBrain bridge · projection gap · capture_thought mirror · OpenBrain to Obsidian/gbrain/OpenClaw · Nate B Jones OpenBrain · openbrain-projection | `skills/openbrain-projection/SKILL.md` |
| Air SSH access, "how do I SSH to Air", Tailscale SSH device-verification, macOS SSH issues | `skills/air-ssh-access/SKILL.md` |
| Mac Tailscale "logged out every few hours" / version-mismatch warning / dual-install | `skills/tailscale-stability/SKILL.md` |
| Camera health check, camera count, ISAPI event subscribe, Hikvision CRUD, violation threshold LAW-002, АПК фиксация, камера/радар фиксирует событие | `skills/camera-management/SKILL.md` |
| Hikvision device offline / camera offline / camera unreachable / camera flapping | `skills/camera-management/SKILL.md` |
| Camera event query · last plate/photo · Satory event intake visibility · latest camera event/photo lookup from Telegram | `skills/camera-event-query/SKILL.md` |
| Website satory.nousagaas.com — deploy, rollback, fingerprint lock | `skills/website-deploy/SKILL.md` |
| Factory workflow, stop/start factory, stopping/starting factory, task queue, watchdog | `skills/factory-ops/SKILL.md` |
| Metrology calibration tracking, camera expiry, legally-void violations | `skills/metrology-cert-tracker/SKILL.md` |
| SmartBridge SOAP, submit violation to ERAP, ВШЭП ЭЦП integration, GOST signing, GOST 34.10-2015 | `skills/smartbridge-soap-client/SKILL.md` |
| Video archival, retention policy, violation footage retention, КоАП 90d/7d/indefinite | `skills/storage-retrieval/SKILL.md` |
| Error classification (L1-L4), retry strategy, escalation thresholds | `skills/error-classification/SKILL.md` |
| Classify this error / what type of error is X / HTTP 502 / HTTP 5xx classification | `skills/error-classification/SKILL.md` |
| Evidence-based verification, anti-slop, "prove it works" before declaring done | `skills/evidence-verification/SKILL.md` |
| Is this evidence sufficient / verify photo evidence / verify the evidence / sufficient evidence | `skills/evidence-verification/SKILL.md` |
| Kazakhstan regulatory — ГОСТы, КоАП/KoAP, speeding fine, fine for speed zone, NIT certification, ISAPI2 compliance | `skills/kazakhstan-regulatory/SKILL.md` |
| Lesson→skill pipeline · /skill-capture · 7-day absorption SLA · collision prevention · Tan-pattern verb "skillify" / "skillify it" / "skillify this" / "make this a skill" / "remember this as a skill" / "lock this in as a skill" / "turn this bug into a skill" / "save this as a skill" / "absorb this into a skill" / "absorb lesson" — runs the full RULE ZERO 3-edit ritual (SKILL.md AP/Timeline + gbrain timeline + commit) | `skills/mistake-to-skill/SKILL.md` |
| Planning discipline — brainstorm before code, spec before plan, plan before impl, "what should I do next? plan the task" | `skills/planning-discipline/SKILL.md` |
| Satory daily operator brief, Camera Doctor, camera fleet brief, daily camera report, erap-mirror, camera offline brief | `skills/satory-daily-operator-brief/SKILL.md` |
| Camera Doctor not firing / brief not sent / dry-run to live cutover / flip to live mode | `skills/satory-daily-operator-brief/SKILL.md` |
| Goal Mode · /goal · goal_runner.py · persistent goal · goal-cycle · GOAL page · goal worker · goal progress · set a goal once · agent revisits · /goal-list · /goal-done · /goal-pause · Todoist task creation · com.nous.goal-cycle · launchd goal cycle | `skills/goal-mode/SKILL.md` |
| BDL/Cerebro replacement gate · Satory external proof · Asyl PSK · Asyl endpoint proof · Denis HTTP-200 egress probe · satory-bdl-external-proof-receipt · "is the Satory replacement done" · "why is BDL still RED" | `skills/bdl-cerebro-replacement-gate/SKILL.md` |
| OpenClaw worker canary · zero-byte stdout · worker sentinel leakage · live probe isolation · prevent internal probe tokens reaching Telegram users | `skills/openclaw-probe-isolation/SKILL.md` |
| Lane lock · active session scope · cross-agent advisory coordination · lock token · queue OpenBrain dedup · session heartbeat/reaper | `skills/lane-lock/SKILL.md` |
| Dirty generated files · launchd writer leaves tracked artifacts dirty · MEMORY-mercury/facts.jsonl drift · generator should no-op or commit its own outputs · clean-boundary writer | `skills/generated-artifact-hygiene/SKILL.md` |
| Bootstrap new factory host · onboard new АПК host · factory-reset macOS · install OpenClaw+LiteLLM+Telegram on new host · apk-mergenovskii bootstrap · apk-bootstrap · register new host in RESOLVER | `projects/apk-bootstrap/bootstrap.sh` + `pages/entities/apk-mergenovskii.md` |
| Substrate split · public/private mirror · GitHub mirror · "where is the public version" · "share skills externally" · credential added to public path · sync_public_mirror.sh · scan_credentials.py · new top-level directory needs classification · GitHub PR flowing back · audit reveals private content synced to mirror · two-repo doctrine · god-level compounding | `skills/substrate-split-mirroring/SKILL.md` |
