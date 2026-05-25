---
tier: 2
type: skill
name: command-center
version: 2.12.29
description: "v2.12.29 — Wire @nousAGaaSbot Telegram natural language and commands to the factory. Private chat can be plain language; addressed group messages like 'Фабрика, ...', 'Nous, ...', '@nousAGaaSbot ...', trailing '@nousAGaaSbot', or 'AI: ...' are mapped deterministically to /status, /goal, /codex, /code, or /ask. Satory full-chat groups also route unaddressed operator action requests when the text is both actionable and domain-specific, including production-environment config requests with Public IP/порт/протокол/prod/test fields, while credential-shaped group asks/configs bypass models: the group gets one owner-handoff confirmation and Madi gets an owner-only DM with the raw context. Standalone bot mentions latch to the adjacent same-sender payload in either direction, while greetings, human @mentions, meta-forwarding chatter, and factory proof comments remain memory-only. Group media/capture acknowledgements and route-progress notices use message reactions or a single emoji fallback, not noisy plumbing text; captured group media also gets an immediate inbox note with raw path and image preview so files are retrievable without waiting for a nonexistent Air ingest cron. Group model replies hide Codex/OpenClaw cost/token footers and must never expose raw Codex-cap/internal mandatory-route diagnostics; if Codex is capped, group replies use Russian local proof or a Russian degraded fallback. Credential-shaped text must be redacted before inbox persistence and before direct Telegram task-result receipts, including normalized admin/<password> summaries and ERAP/APK test/prod password fields. Direct /codex, /code, and /ask Codex-escalated replies must always write a redacted pages/task-results receipt, even when the Telegram-visible reply is short. Explicit /ask --tier ceo is Codex GPT-5.5 subscription-first and Madi-DM only; explicit /ask --tier cheap is MLX/DeepSeek-only and must not touch the paid council. Post-/ask inbox classification must pin telegram_ingest_persist mutable paths to the active Air wiki before side effects, so loaded runtime-root shadows cannot write to or read from a stale Mac checkout. Group LLM requests carry sender provenance plus current-sender/neutral salutation instructions, and outbound group sends neutralize or block stale personal salutations unless sender proof exists. Evidence audits must preserve conflicts between bot-ingested messages and fuller human transcripts instead of over-correcting from partial inbox data. Satory event-intake visibility questions are answered locally from the camera freshness API before model routing, and mandatory Codex proof routes precheck the Codex call/token cap before attempting GPT. Satory APK/ERAP/camera/VAR external operator proof questions now route to /codex GPT-5.5 subscription instead of routine OpenClaw when available, with capped group fallback in Russian. KEONA counterparty email drafts must honor the requested language pair from memory/vault before copy-paste output; the current default for Lim/Aigerim live-thread replies is Korean + Russian, not English fallback. Explicit top-tier/second-brain/customer-transformation requests also route to /codex first, with Codex instructed to delegate durable work to OpenClaw/factory only when needed and to write destination-first human replies. Root command_center.py must stay hash-aligned with tools/command_center.py and wiki/tools/command_center.py after every Telegram-facing router patch, because legacy imports and truth gates still check the runtime-root shadow. Telegram/OpenClaw production truth is now gated separately from Air runtime root release-hygiene dirt, host remote-name differences are not allowed to create false REDs, live /ask E2E proof must observe Air logs without starting a second getUpdates poller or matching stale /ask lines without the nonce, OpenClaw agent zero-byte stdout must recover from session JSONL before returning an operator-facing error, and transient Telegram getUpdates network timeouts must not poison launchd health for a one-shot poller cycle while 409 Conflict remains hard RED."
triggers:
  - user sends a message starting with /ask, /codex, /code, /goal, /goal-list, /status, /report, /health, /handoff, /help to @nousAGaaSbot
  - user wants Telegram to work without slash commands
  - user asks for natural-language factory control
  - operator debugging factory Telegram routing
  - operator adding a new slash command
  - intermittent Telegram message loss or silent drops
tools: [Bash, Read, Edit, Write, Grep]
mutating: true
absorbs_lessons: [LESSON-062, LESSON-063, LESSON-081, LESSON-087, LESSON-088, LESSON-098]
absorbs_laws: [LAW-010, LAW-016, AMENDMENT-003]
related: [SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]
last_updated: 2026-05-22
title: "command-center v2.12.29"
---

# command-center v2.12.29

## Purpose

Routes natural Telegram requests and explicit commands from `@nousAGaaSbot` to the right factory backend:
- private DM plain text → deterministic natural command router
- addressed group text (`Фабрика, ...`, `Nous, ...`, `@nousAGaaSbot ...`, `AI: ...`) → deterministic natural command router
- `/ask <query>` → OpenClaw `grok-ceo` router → `nous`/Opus or worker tiers as needed
- `/ask --tier ceo <query>` → Codex GPT-5.5 subscription-first; Madi DM only; no paid API council by default
- `/ask --tier cheap <query>` → local MLX model first, DeepSeek fallback; no Codex/Grok/Opus route
- `/ask-direct <query>` → OpenClaw `nous`/Opus directly, bypassing Tier-1
- `/codex <task>` → OpenAI Codex CLI on Air, `gpt-5.5`, subscription-only, no hidden API fallback
- `/code <task>` → Claude Code headless → Sonnet 4.6 with full tools (Bash, Read, Edit, Write, Grep, Glob), $5/day cap
- `/goal <goal> [by YYYY-MM-DD]` → Create a persistent GOAL page + Todoist task, then kick `com.nous.goal-cycle`
- `/goal-list` → List active persistent GOAL pages
- `/status` → Air runtime Docker state, disk, memory
- `/report` → Today's cost report
- `/health` → Air factory health (OpenClaw Docker + native LiteLLM + local disk)
- `/trace` → Tier timeline from `ask-hierarchy.jsonl`
- `/handoff` → Writes `HANDOFF-AUTO-*.md` checkpoint via GLM-5.1
- `/help` → Lists all commands
- Quiet-hours guard → non-urgent `/ask`, `/ask-direct`, `/code`, and `/codex` are saved to `pages/personal/boundary-queue-YYYY-MM-DD.md` instead of running after 00:30 Almaty.

Unaddressed group chatter → persisted to `pages/inbox/...` when full-chat observe mode is enabled, but not executed. Anything else → captured to `wiki/raw/pending/` for `ingest_pending.py` to process.

## Contract

**Inputs:** Raw Telegram message from `telegram_poll.py`, carrying `bot_token`, `chat_id`, `msg_id`, `text`.

**Outputs:** Always one Telegram reply (may be two messages for long-running commands: "⏳ Routing…" then result). Long responses >4000 chars save full text to `wiki/pages/task-results/` and reply with link+summary.

**Side effects:**
- Writes to `~/nous-agaas/logs/run_task.log` (via run_task.py)
- `/code` writes cost to `~/nous-agaas/logs/claude_code_cost.json`
- `/codex` writes usage counts to `~/nous-agaas/logs/codex_usage.json`
- `/handoff` writes wiki page, git commit + push
- All invocations logged.

**Guarantees:** The command router is side-effect-only at the Telegram level. It does NOT write to the vault except when explicitly commanded. No message is processed twice (state tracked via `telegram_poll_state.json` atomic write — LESSON-088).

## Current rules (compiled truth)

### AP-54 — KEONA counterparty drafts preserve requested language pair before copy-paste

**Trigger:** On 2026-05-22 Codex pasted only the English half of an EN/KO draft after Madi asked for the copy-paste email, even though memory says KEONA live-thread replies should be Korean + Russian and the user immediately corrected the miss.

**Root cause:** the vault artifact itself was stale/wrong (`EN_KO`, `languages: [en, ko]`), and the agent trusted the artifact title/body instead of cross-checking memory + task-result language requirements before producing a user-facing copy-paste message.

**Rule:** before producing any KEONA counterparty copy-paste email, verify the requested language pair from memory and the latest live vault artifact. If memory says Korean + Russian, the chat output and artifact must be KO/RU only unless Madi explicitly requests English. Do not paste a single-language body when the artifact contains multiple languages. If artifact metadata and user/memory conflict, fix the artifact first, then answer.

**Detector:** `rg -n "languages: \\[en, ko\\]|english, korean|KEONA_Lim_Concise_Reply_2026-05-22_EN_KO" pages/communications pages/projects/keona-pilot pages/task-results/2026-05-22-keona-may21-gmail-pdf-reconciliation.md` must return no active current-draft references before replying.

### AP-53 — KEONA/Satory group packages are Russian-first and topic-bound before send

**Trigger:** The 2026-05-22 KEONA Gmail attachment package was first posted with English operator headings and then still leaked English action phrases after a correction. The Telegram UI screenshot also made the post look indistinguishable from a General-topic package to the operator.

**Root cause:** the reusable forum sender guaranteed `message_thread_id`, but it accepted arbitrary free-form text. There was no KEONA domain wrapper, no Cyrillic gate, no banned English operator phrase check, and no automation prompt telling OpenClaw/Hermes/Codex/Claude to use a Russian-first KEONA package path.

**Rule:** every internal KEONA package to the Satory Telegram group must use `tools/keona_telegram_package.py`, not ad hoc free-form text. The wrapper must target chat `-1002064137259`, topic `1357`, pass every Gmail attachment with repeated `--file`, and require Cyrillic. Product/company names and IDs may stay Latin, but headings and operator instructions must be Russian. Banned visible operator phrases include `Next`, `Files attached`, `revised contract`, `site prep`, `installation manual`, `tax certificate`, and `heater + tax certificate`. If a wrong-language or wrong-topic KEONA post appears, delete the visible package, repost through the wrapper, then update Obsidian, Notion, gbrain, OpenBrain, Todoist, and Git proof with the corrected message ids.

**Detector:** `python3 -m unittest tools/tests/test_telegram_topic_send.py tools/tests/test_keona_telegram_package.py` plus a live UI readback of `tg://privatepost?channel=2064137259&post=<text_message_id>` showing title `Keon-A`, Russian-facing text, and every expected PDF below it.

### AP-52 — Group chat must never surface Codex cap or mandatory-route internals

**Trigger:** After AP-51, the Satory group still saw two operator-hostile replies: raw `Daily /codex token cap reached: 312163 / 250000 observed tokens` and then `This request is mandatory /codex only ... No answer was generated by the cheap worker route`. The immediate cause was split-brain Air runtime copies (`/Users/madia/nous-agaas/tools/command_center.py` drifted from root/wiki), plus a source branch that treated capped mandatory Codex as a user-visible stop instead of a degraded group answer.

**Rule:** external Telegram groups must never receive raw Codex quota text, `mandatory /codex only`, `Codex budget/auth`, cheap-worker-empty diagnostics, route labels, or English internal failure text. For Satory event visibility (`Видишь события?`, `поток подали`, `маршрут настроили`) answer locally from the camera freshness API before any model route. For other mandatory Codex proof routes when Codex is capped, send a Russian degraded notice and call grok-ceo Tier-1 with an explicit Russian/no-internals instruction. `_tg_send()` also sanitizes banned internal markers as the last line of defense.

**Deployment gate:** after any Telegram-facing router patch, all three Air copies must be byte-identical: `/Users/madia/nous-agaas/command_center.py`, `/Users/madia/nous-agaas/tools/command_center.py`, and `/Users/madia/nous-agaas/wiki/tools/command_center.py`. Clear `__pycache__` and `launchctl kickstart -k gui/$(id -u)/com.nous.telegram-poll` after deploy; the poller imports once per running process.

**Detector:** `python3 -m pytest tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_short_satory_event_visibility_question_uses_local_api_not_codex_cap_path tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_group_internal_codex_error_sanitizer_returns_russian_reply tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_mandatory_satory_proof_falls_back_to_grok_with_russian_notice_in_group -q`.

### AP-51 — Satory event-intake status must be local proof, not model routing

**Trigger:** In the Satory group on 2026-05-20, Asyl asked whether the VAR/radar route was visible and whether the event stream had started. The first ambiguous `Что видишь? Маршрут настроили` fell to routine OpenClaw and returned a stale `wg-satory` answer; later event-flow questions routed to Codex but the daily token cap returned raw `/codex cap reached` text to the group.

**Rule:** group questions about Satory event intake visibility (`видишь события`, `поток подали`, `маршрут настроили`, `получать события`, `9080`, `camera/hxml`) are live status checks, not reasoning prompts. Answer them locally from `https://api.nousagaas.com/api/cameras` `data_freshness` before OpenClaw/Codex routing. The reply must include `events_last_seen`, `events_age_seconds`, `events_recent_count`, `poll_last_run`, and explicitly state intake-only / no ERAP submission.

Mandatory external-proof routes that still need Codex must check `codex_usage.json` call/token caps before attempting `_run_codex()`. If Codex is capped in an external group, AP-52 overrides the old blocked-message behavior: answer in Russian through the degraded group fallback and never expose raw internal router text.

**Detector:** `python3 -m pytest tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_satory_event_visibility_query_bypasses_models_and_reports_api_snapshot tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_satory_route_configured_question_reports_stale_intake_without_openclaw_guess tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_mandatory_satory_proof_blocks_cleanly_when_codex_token_cap_reached -q`.

### AP-50 — Explicit /ask tier overrides are subscription-first or cheap-only, never silent paid council

**Trigger:** Madi asked for the factory to use subscriptions wherever possible and stop silently spending API credits when a subscription/local path exists.

**Rule:** `/ask --tier ceo <query>` is Madi-DM only and routes Codex GPT-5.5 subscription-first. It must not invoke OpenClaw, Grok API, Opus API, or multi-model consult by default. If Codex auth/quota fails, return the visible Codex failure; do not silently downgrade to cheap workers. A paid council can be added only through an explicit approved route that records cap, reason, and billing surface.

`/ask --tier cheap <query>` is local MLX first, DeepSeek fallback. It must never call Codex, Grok, Opus, or the multi-model paid council. The default `/ask <query>` path remains unchanged.

**Detector:** `python3 -m pytest tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_ask_tier_ceo_is_codex_first_and_not_openclaw tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_ask_tier_ceo_rejects_non_madi_without_model_call tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_ask_tier_cheap_uses_local_mlx_route_and_never_codex_grok_or_opus -q`.

### AP-36 — Mirror Telegram router patches into Air runtime-root shadow before truth-gate proof

**Symptom:** `telegram_openclaw_factory_truth_gate.py --json --skip-factory-probe` returned RED for `air_command_center_parity` while OpenClaw, LiteLLM, launchd, and wiki HEAD parity were green. The tracked `tools/command_center.py` and Air wiki copy had the new `_tg_send sent OK` log line, but the legacy Air runtime-root shadow at `/Users/madia/nous-agaas/command_center.py` still had the stale shorter `_tg_send` block.

**Root cause:** a Telegram-facing router fix landed in the tracked tools module but was not mirrored into the root compatibility copy that some legacy imports and the strict truth gate still check. Import order protected the live poller, but the split-brain hash is still a production-proof failure because a future legacy path could import the wrong copy.

**Rule:** any change to `tools/command_center.py` that affects Telegram routing, sends, cost caps, `/ask`, `/codex`, `/code`, `/goal`, `/status`, or operator-facing proof must leave these three files hash-identical on Air before claiming the factory truth gate is green:

```bash
/Users/madia/nous-agaas/command_center.py
/Users/madia/nous-agaas/tools/command_center.py
/Users/madia/nous-agaas/wiki/tools/command_center.py
```

**Detector:** run:

```bash
python3 tools/telegram_openclaw_factory_truth_gate.py --json --skip-factory-probe
```

The `air_command_center_parity` check must be GREEN. If it is RED, compare the three SHA-256 hashes before debugging OpenClaw, Telegram, or LiteLLM.

**Recovery:** mirror the tracked tools router into the runtime-root shadow, run `python3 -m py_compile` on all three copies, rerun the truth gate, and only then continue with broader factory probes. Do not classify this as generic Air runtime-root dirt; command-center hash drift is a production-proof red.

### AP-37 — Satory APK/ERAP external proof questions must bypass routine OpenClaw

Short external operator questions can be high-risk even when they are under 100 characters. If the text is a Satory/Asyl-style APK question (`from asyl`, `asyl`, `assyl`, `асиль`, etc.) plus `апк`/`apk` plus proof/readiness language (`фиксирует`, `фиксац`, `ерап`, `заявк`, `оскемен`, `evidence`, `proof`), route it to `/codex` GPT-5.5 subscription before OpenClaw can draft a reply.

Why: `tg_1655` asked "from asyl: ... ПО работает с Апк? фиксирует что-то?" and routine `/ask` routed to OpenClaw `grok-ceo`. The skill injector had not yet matched the Satory dashboard context, so the model answered about `gbrain`/Todoist/internal AI tracking and even treated APK as a possible mobile app. That was wrong for the business context: АПК means аппаратно-программный комплекс for ERAP/evidence readiness.

Detector: `tools/tests/test_factory_orchestration_policy.py::test_satory_apk_external_operator_query_routes_to_chatgpt_codex`, `tools/tests/test_factory_orchestration_policy.py::test_satory_var_camera_access_query_routes_to_chatgpt_codex`, `tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_short_satory_apk_erap_external_query_routes_to_codex`, and `tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_satory_var_camera_access_query_routes_to_codex`.

### AP-38 — Top-tier second-brain and destination-first replies route to Codex first

When the operator explicitly asks for top-tier GPT, second brain, best CTO/CEO, Karpathy/Tan/Elon-style judgment, bulletproof review, or customer-transformation framing, the Telegram path must route to `/codex` GPT-5.5 subscription before routine OpenClaw. Codex is the supervisor brain for these cases; OpenClaw/factory remains the durable worker substrate.

The `/codex` preamble must teach the spawned Codex lane to: answer at the outcome level first; create Goal/Todoist/OpenClaw worker state only when follow-through is needed; use Opus/Grok/Hermes as named evidence-backed lanes; and write team/customer replies destination-first. For non-technical recipients, the result/proof/next observable change is the island; internal tools are the plane.

Detector: `tools/test_telegram_poll.py::TestImplicitAsk::test_private_top_tier_second_brain_routes_to_codex`, `tools/tests/test_factory_orchestration_policy.py::test_top_tier_second_brain_routes_to_chatgpt_codex_supervisor`, and `tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_top_tier_second_brain_ask_routes_to_codex`.

### AP-39 — Full-chat inbox persistence must redact credential-shaped text before git

**Symptom:** Satory group full-chat capture persisted a LU100 APK access line containing an admin password into `pages/inbox/...`. GitHub accepted the bad commit before the VPS pre-receive secret gate rejected it.

**Root cause:** AP-24 correctly made unaddressed group chatter memory-only, but the memory boundary wrote raw message text to the vault before any secret scrub. The secret gate lived at VPS push time, which is too late for other mirrors.

**Rule:** every Telegram inbox write must pass through a redaction boundary before title/frontmatter/body creation. Preserve operational context such as APK IP, object, sender, and message id, but replace password/token/API-key-shaped values with `[REDACTED]`. ERAP/APK environment fields named `test:`, `prod:`, `production:`, `тест:`, or `прод:` are credential labels when the value is secret-like; redact those too. Do not solve this by disabling full-chat observability; the factory still needs context, just not raw credentials in git.

**Detector:** `python3 -m pytest tools/tests/test_telegram_ingest_persist_redaction.py -q` must prove `10.145.1.2 admin <password>`, normalized `admin/<password>`, and Satory `test:`/`prod:` environment password fields are redacted in both the pure sanitizer and the persisted inbox note.

**Recovery:** if a secret reaches git, rewrite the affected branch history, force-with-lease any mirror that accepted it, sync Air/VPS working copies to the redacted head, and rotate the real credential because the chat itself exposed it.

### AP-40 — Group human mentions are not AI addresses

**Symptom:** Satory group message `@Riza1207 Nazel` was captured as full-chat context and then incorrectly routed as `/ask Nazel`, producing bot replies in the group even though Madi was tagging a human teammate.

**Root cause:** `_strip_factory_address()` treated any leading `@username` as an AI address. That was too broad for real team chats, where `@person` is normal human-to-human routing.

**Rule:** in group chats, only explicit factory addresses may execute: `@nousAGaaSbot`, `Фабрика, ...`, `Nous, ...`, `AI: ...`, or slash commands. All other leading `@username` mentions are observed and persisted only when full-chat observe mode is enabled; they must not call OpenClaw, Codex, or send an ACK.

**Detector:** `python3 -m pytest tools/test_telegram_poll.py -q` must include `test_group_human_mention_is_observed_not_executed` and `test_group_bot_mention_routes_to_ask`.

**Recovery:** if a human mention is misrouted, fix the deterministic address parser first. Do not tune the model prompt; the model should never see unaddressed human mention chatter as an execution request.

### AP-41 — Group replies require current-sender UX and conflict-aware evidence

**Symptom:** The LU100 group handoff was first audited as a wrong-addressee bug because bot-ingested `msg_id=1747` showed Assylbek as sender of a merged object/IP note. Madi later supplied the fuller Telegram transcript showing Denis had requested the endpoint and posted the LU100 details. That made a Denis-directed reply explainable from thread context, but still bad group UX when the visible message directly before the bot was from Assylbek: the bot looked like it did not know who it was talking to.

**Root cause:** two boundaries were missing. The first audit overfit to partial bot-ingested evidence. The runtime still lacked a current-sender reply guard: group LLM routes carried sender provenance but did not instruct/enforce "greet current sender or stay neutral," and manual `tg_send.sh` group sends could open with a stale person name without sender proof.

**Rule:** explicit group AI requests include sender provenance plus this visible-reply constraint before LLM execution: if greeting anyone, greet the current sender or use `Коллеги`; never greet another person from surrounding context. `@nousAGaaSbot` can appear at the beginning or end of the message; human `@username` mentions remain observe-only. Outbound group responses from `command_center.py` must neutralize a stale leading personal salutation to `Коллеги, ...` when the current sender context disagrees. Manual group sends through `tg_send.sh` must use neutral wording by default; a named addressee requires explicit bypass/proof. When bot-ingested messages and a fuller human transcript disagree about who said what, preserve that conflict in the source/audit instead of pretending one capture is complete.

**Detector:** `python3 -m pytest tools/test_telegram_poll.py::TestAllowedGroupRouting::test_group_trailing_bot_mention_routes_with_sender_context tools/test_operator_boundaries.py::GroupAddresseeGuardTests -q` plus `AUTONOMY_BYPASS=1 bash tools/test_tg_send_manual_group_addressee_guard.sh`.

**Recovery:** if an addressee looks wrong, first compare bot-ingested inbox, poller logs, and the human-visible Telegram transcript. If evidence conflicts, mark the transcript as authoritative for human-facing interpretation and keep the inbox as a partial machine capture. In live group replies, choose `Коллеги, ...` unless the addressee is anchored to the current sender or an explicit threaded target.

### AP-42 — Transient getUpdates timeouts retry before launchd failure

**Symptom:** Daily proof pack showed contradictory Telegram health: Mac-side no-drift saw the poller running, while Air-side control-plane saw `com.nous.telegram-poll` last exit `1`. Direct Air logs showed the latest cycle exited immediately after one Telegram `getUpdates` read timeout, even though the same poller had processed real DM/group updates earlier that day.

**Root cause:** `telegram_poll.py` treated the first transient `getUpdates` exception as a hard process failure. That made launchd health red for routine Telegram/network flakiness. The hard failure rule is still correct for `409 Conflict`, because that proves a second poller may be using the same bot token.

**Rule:** retry transient `getUpdates` network errors inside the same 50-second poller cycle. Keep `409 Conflict` as immediate RED. If an entire cycle has only transient failures and zero successful polls, return nonzero so launchd still reports a real outage.

**Detector:** `python3 -m pytest tools/test_telegram_poll.py::TestGetUpdatesErrorHandling -q` must prove one timeout is retried and that `409 Conflict` remains a hard failure.

**Recovery:** if daily proof pack reports Telegram red, inspect `launchctl list | grep com.nous.telegram-poll` and the last `telegram_poll.err` lines. Distinguish transient timeout retries from split-poller `409 Conflict` before restarting or changing bot tokens.

### AP-43 — One-shot Telegram poller transient-only cycles stay launchd green

**Symptom:** The final daily proof pack still saw a red from `factory_no_drift_probe.sh`: `com.nous.telegram-poll crashed exit=1`. A control-plane dry-run in the same minute later saw the poller running with `pid=18144`, while `launchctl print` showed `state=running` and stale `last exit code = 1`. Logs showed two transient Telegram read timeouts, not a 409 conflict or duplicate poller.

**Root cause:** AP-42 fixed the first-timeout immediate failure but still returned `1` when a 50-second one-shot cycle had only transient timeouts. Launchd then retained `last_exit=1` across the next healthy/running cycle. The substrate probe also treated a running job with stale nonzero `last_exit` as RED.

**Rule:** for the one-shot Telegram poller, transient-only `getUpdates` cycles log warning evidence but return `0`; repeated network flakiness is a degraded signal, not a crash. Keep `409 Conflict` and malformed Telegram API responses as hard nonzero. Launchd probes must treat a numeric running PID as live even when `last_exit` is stale and nonzero; only idle `pid=-` with nonzero last exit is red.

**Detector:** `python3 -m pytest tools/test_telegram_poll.py::TestGetUpdatesErrorHandling tools/test_daily_0300_substrate_sync.py::test_launchd_status_running_pid_is_green_despite_stale_last_exit tools/test_daily_0300_substrate_sync.py::test_launchd_status_idle_nonzero_exit_remains_red -q`.

**Recovery:** when Telegram health flips red, compare `launchctl list`, `launchctl print gui/501/com.nous.telegram-poll`, fresh log lines, and lock/heartbeat age. Do not classify a running poller with stale `last_exit=1` as down unless the heartbeat is stale or a hard error such as `409 Conflict` is present.

### AP-44 — Satory group action requests answer; group plumbing stays reaction-only

**Symptom:** Asyl wrote in the Satory group, `с этой группе можешь писать. дай мне логин и пароль для отправки нарушения в ЕРАП...`, but the poller only persisted it as inbox `msg_id=1764` and did not route it because the message did not address `@nousAGaaSbot`. The next photo generated a visible `[captured into vault] ... ingest_pending.py` ACK, so the group saw internal capture plumbing while the operator request looked ignored. Codex routes also exposed `Routing bounded execution...`, spend, token, and provider footers in the group.

**Root cause:** AP-40/AP-41 correctly prevented arbitrary group chatter and human mentions from executing, but the rule became too strict for the now-configured Satory group responder. Full-chat observation had no second gate for actionable Satory operator asks. Capture ACKs and route-progress messages used `sendMessage`, which is appropriate for private DM proof but too noisy for operator group UX.

**Rule:** in full-chat Satory groups, unaddressed messages may execute only when deterministic gates prove both: (a) an actionable request word such as `дай`, `можешь`, `проверь`, `нужно`, `?`; and (b) a Satory/domain word such as `ЕРАП`, `АПК`, `БДЛ`, `заявка`, `логин`, `пароль`, `доступ`, `камера`. Bot proof comments, human mentions, and greetings remain observe-only. Group capture ACKs and route-progress notices must use Telegram `setMessageReaction` with `👍` or a one-emoji fallback. Visible group answers must not include internal Codex/OpenClaw routing, spend, token, provider, or ingest-pipeline footers. Group media captures must also create an immediate `pages/inbox/YYYY-MM-DD/<msg_id>-media-*.md` note with sender, raw file path, caption, and image preview when applicable; do not promise a 60-second `ingest_pending.py` path unless that runner is actually deployed and supports the file type.

**Detector:** `python3 -m pytest tools/test_telegram_poll.py::TestAllowedGroupRouting::test_satory_operator_action_request_without_credentials_still_routes tools/test_telegram_poll.py::TestAllowedGroupRouting::test_group_photo_capture_acks_with_reaction_not_verbose_message tools/test_telegram_poll.py::TestAllowedGroupRouting::test_full_chat_group_photo_gets_retrievable_inbox_note tools/test_telegram_poll.py::TestAllowedGroupRouting::test_persist_media_inbox_writes_raw_path_and_photo_preview tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_group_codex_route_uses_reaction_and_hides_internal_footer -q`.

**Recovery:** if a Satory operator says the bot ignored them, inspect the inbox note for `chat_id`, `msg_id`, and `sender`, then replay the message through `telegram_poll.process_message()` with network calls mocked. Fix the deterministic group gate first; do not compensate by making all group chatter implicit `/ask`, because that reopens bot loops and token spam.

### AP-45 — Standalone bot mentions latch to adjacent payloads in both directions

**Symptom:** Madi sent `@nousAGaaSbot` as `msg_id=1766`, then immediately sent the actual Satory production-environment config as `msg_id=1767` (`test:`, `prod:`, Public IP, port, protocol, checkbox, "нужно точно также... продуктивная среда"). Air captured both as inbox notes but did not route either, so the group saw no OpenClaw taken signal.

**Root cause:** the prior split-message recovery handled only "payload first, mention second" by looking backward when the current message was a standalone mention. It did not handle the opposite Telegram UX pattern: "mention first, payload second." The Satory operator domain gate was also too narrow for production-environment config fields, and the redactor did not treat `test:`/`prod:` as credential labels.

**Rule:** in full-chat groups, a standalone `@nousAGaaSbot` message creates a short-lived address latch for the same sender and chat. The next non-empty same-sender payload within 120 seconds routes as the addressed request. The reverse direction remains supported by AP-6/AP-44. Production config fields such as `Public IP`, `Порт`, `Протокол`, `HTTPS`, `продуктивная среда`, `prod`, and `test` count as Satory domain markers only when paired with an action word. Group routing still sends only a reaction/progress signal, not internal text.

**Detector:** `python3 -m pytest tools/test_telegram_poll.py::TestSplitMentionRecovery::test_mention_then_payload_routes_current_body tools/test_telegram_poll.py::TestAllowedGroupRouting::test_satory_production_config_credentials_go_to_owner_handoff_raw tools/tests/test_telegram_ingest_persist_redaction.py -q`.

**Recovery:** when a group operator says "I tagged the bot and it ignored me," inspect adjacent inbox messages from the same sender before deciding the router failed. Replay the pair with `command_center.handle` mocked. If any note contains raw `test:`/`prod:` values, rewrite the note through `telegram_ingest_persist.redact_sensitive_text()` before sync/commit.

### AP-46 — Meta-forwarding mentions are not bot commands

**Symptom:** after the mention-first repair, Madi wrote `Send it to me and i will forward @nousAGaaSbot` in the Satory group. The router treated the trailing bot mention as an execution request, reacted with `👍`, and then spent a full OpenClaw turn on meta-chatter. A replay returned an internal Claude-Code task block instead of an operator-safe group reply.

**Root cause:** `_strip_bot_mentions_anywhere()` intentionally made trailing `@nousAGaaSbot` executable, but the classifier did not distinguish direct bot address from human coordination about forwarding something to the bot. The factory was doing the wrong work faster: it acknowledged the message, then routed non-work into OpenClaw.

**Rule:** a group message that contains `@nousAGaaSbot` plus forwarding language (`forward`, `forwarding`, `перешлю`, `перешли`, `пересл...`) is observed only unless it begins with a direct factory address or slash command. It may receive a reaction as sign-of-life, but it must not call OpenClaw/Codex or produce a model answer. Real trailing requests like `проверь доступ @nousAGaaSbot` still route.

**Detector:** `python3 -m pytest tools/test_telegram_poll.py::TestAllowedGroupRouting::test_group_forwarding_bot_mention_is_observed_not_executed tools/test_telegram_poll.py::TestAllowedGroupRouting::test_group_trailing_bot_mention_routes_with_sender_context -q`.

**Recovery:** when group routing looks silent, first classify the source message as command, direct address, adjacent-payload latch, Satory operator action, or observe-only meta-chatter. Do not use a model call to decide whether the bot was addressed; deterministic address parsing owns that boundary.

### AP-47 — Credential-shaped group text goes to owner DM, not model routing

**Symptom:** after AP-44, Asyl's ERAP login/password ask could be answered safely in principle, but the generated answer lived in LangSmith without a matching Telegram send for `msg_id=1764`. The later owner-forward directive (`Send it to me and i will forward`) only received a reaction; no owner DM path existed.

**Root cause:** AP-44 solved "should this group ask route?" but still treated credential requests as normal `/ask` work. That mixed three responsibilities: public group acknowledgement, owner-only credential transfer, and model answer generation. The model could generate a safe sentence, but it was the wrong layer for credential transport and could not receive raw secrets after AP-39 redaction.

**Rule:** in full-chat Satory groups, any message containing credential-shaped text (`логин`, `пароль`, `password`, `credential`, `secret`, token/API-key markers, or `test:`/`prod:` environment credential fields) bypasses OpenClaw/Codex. The group receives one short confirmation: `Принято. Доступы в общем чате не публикуем. Передано владельцу (@madi_ayazbay); он перенаправит ответственному.` The owner DM (`chat_id=110793056` unless `TELEGRAM_OWNER_CHAT_ID` overrides it) receives `[OWNER-ONLY: forward to operator]` plus source group, `msg_id`, sender, and the raw unredacted body from `telegram_poll.py`. Do not ask the group "кому передать"; Madi owns the routing decision. Do not echo Public IP/port/protocol/test/prod values into the group reply.

**Detector:** `python3 -m pytest tools/test_telegram_poll.py::TestAllowedGroupRouting::test_satory_credential_request_routes_to_owner_handoff_without_model tools/test_telegram_poll.py::TestAllowedGroupRouting::test_satory_production_config_credentials_go_to_owner_handoff_raw tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_group_credential_request_routes_to_owner_handoff_before_codex tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_owner_credential_handoff_never_echoes_group_env_config -q`.

**Recovery:** if a credential ask gets a reaction but Madi does not receive the owner-only DM, inspect `telegram_poll.err` for `Owner credential handoff routed` and `_tg_send sent OK: chat=110793056`. If the model path ran instead, replay the raw body through `telegram_poll.process_message()` with network calls mocked and fix the pre-redaction owner handoff gate before touching prompts.

### AP-48 — Direct Codex/Code Telegram replies always write task-result receipts

**Symptom:** a Satory group message (`msg_id=1772`) correctly received a reaction and a Telegram reply through the `/ask` → ChatGPT/Codex execution route, but the reply did not create a `pages/task-results/...` receipt. Only `telegram_poll.err` showed `_tg_send sent OK` and `/ask routed to ChatGPT/Codex execution`; the actual answer was not recoverable from Obsidian/gbrain/OpenBrain.

**Root cause:** run_task/OpenClaw paths already write `pages/task-results`, and explicit `/codex`/`/code` only wrote a receipt when the response exceeded Telegram's message limit. The newer `/ask` Codex-escalation branches reused `_run_codex()` directly and relied on LangSmith digests plus Telegram delivery, leaving short operator-visible Codex answers outside the durable vault.

**Rule:** every direct spawned-model Telegram reply that bypasses `run_task.py` must write a redacted `pages/task-results` receipt before sending or truncating the Telegram reply. This includes explicit `/codex`, explicit `/code`, `/ask-auto-codex`, `/ask-langgraph-codex-execution`, and `/ask-auto-codex-high-judgment`. The receipt must include `source: telegram:tg_<msg_id>:<route>`, model/via fields, redacted task text, and redacted response text. Use the same redaction boundary as inbox persistence before writing to git; `test:`/`prod:` fields and password/token-shaped values must not survive in receipts.

**Detector:** `python3 -m pytest tools/tests/test_command_center_task_result_receipts.py tools/test_telegram_poll.py tools/tests/test_factory_orchestration_policy.py -q`.

**Recovery:** if Telegram shows a model reply but no matching task-result file exists, search `telegram_poll.err` for the `msg_id`, identify whether it went through `run_task.py` or direct `_run_codex()`/`_run_claude_code()`, backfill a redacted receipt from available safe logs if possible, and fix the direct route rather than adding another notification.

### AP-49 — Post-/ask inbox classification must pin mutable ingest paths to the active wiki

**Symptom:** latest Satory group replies (`msg_id=1773`, `1775`, `1778`, `1780`) were routed and answered, but `telegram_poll.err` logged `classify_inbox_post_ask failed: FileNotFoundError: /Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/inbox/...` on Air. The inbox notes remained `classifier_model: pending` even though the group path was otherwise live.

**Root cause:** `command_center._classify_inbox_post_ask()` imported `telegram_ingest_persist`, but the Air process may already have loaded the runtime-root shadow module. That module's mutable globals (`VAULT`, `INBOX_ROOT`, `TASKS_FILE`, `MERCURY_FACTS`) can point at a stale Mac checkout because `_vault_root()` falls back to `/Users/madia/Documents/Projects/Nous AGaaS/Nous` when present. The active poller wiki is `/Users/madia/nous-agaas/wiki`.

**Rule:** before calling `telegram_ingest_persist.classify()` from command_center, set `_tip.VAULT`, `_tip.INBOX_ROOT`, `_tip.TASKS_FILE`, and `_tip.MERCURY_FACTS` to the active `NOUS_WIKI`/`_wiki_root()` paths. Runtime-root shadows may exist for import compatibility, but post-/ask side effects must read/write the same wiki checkout that captured the inbox note.

**Detector:** `python3 -m pytest tools/tests/test_command_center_task_result_receipts.py::test_post_ask_classifier_pins_runtime_ingest_paths_to_wiki -q`.

**Recovery:** if `classify_inbox_post_ask` logs a Mac-path `FileNotFoundError` on Air, do not restart Telegram first. Patch the path pinning, replay the classifier with a mocked intent result, then rerun the Telegram/OpenClaw truth gate.

### Phases

1. **Recognize** — `is_command(text)` returns True for slash-prefixed commands.
2. **Route** — `handle()` dispatches on prefix.
3. **Ack** — Send "⏳ Routing…" for long commands (`/ask`, `/code`).
4. **Execute** — Spawn the appropriate backend:
   - `/ask` → `subprocess.run([python, run_task.py, --agent grok-ceo, query])` → OpenClaw hierarchy
   - `/ask-direct` → `subprocess.run([python, run_task.py, --model opus, --agent nous, query])` → Tier-2 direct
   - `/codex` → `subprocess.run([codex, exec, -m, gpt-5.5, ...])` → OpenAI Codex on Air
   - `/code` → `subprocess.run([claude, -p, task, ...], env=minimal_env)`
   - `/goal` → `_create_goal_page()` + `_create_todoist_task()` + `_kick_goal_cycle()` → OpenClaw goal worker loop
   - `/status` → Inline shell calls (docker, df, vm_stat)
5. **Respond** — Telegram reply, truncating to 4000 chars if needed.
6. **Log** — Record chat_id, query_len, response_len to `command_center.log`.

### HANDOFF format (rigid)

Every HANDOFF file (`pages/progress/HANDOFF-*.md`) MUST contain these 13 fields:

```
SESSION ID:      [timestamp or session number]
STATUS:          [completed | blocked | partial]
COMPLETED:       [list of done subtasks WITH proof per item]
IN PROGRESS:     [current subtask + exact state]
BLOCKED BY:      [specific blocker + evidence why it blocks]
NEXT ACTIONS:    [exactly what next session does FIRST — numbered]
FILES CHANGED:   [list with full paths]
TESTS STATUS:    [last test run output, verbatim]
NEW SKILLS:      [any skills created or extended this session, with versions]
NEW LESSONS:     [any LESSON-NNN files written this session]
WARNINGS:        [gotchas for next session — things that might surprise]
GBRAIN SYNCED:   [yes/no — was gbrain sync_brain called?]
OBSIDIAN SYNCED: [yes/no — was git push to vps successful?]
```

#### Anti-pattern: HANDOFF with missing required fields

**Problem:** Next session starts with incomplete context → rework. Session 14 handoff was missing FILES CHANGED → session 15 re-read 20 files to figure out what had been touched.
**Fix:** This template is enforced. If any field genuinely has nothing, write "none" — never omit the field itself.

### AP-1 — Don't use Telegram MCP from Claude Code sessions
**LESSON-087.** The Air `telegram_poll.py` is the ONLY authorized process that calls Telegram Bot API for `@nousAGaaSbot`. If a Claude Code session also uses `mcp__plugin_telegram_telegram__*` tools against the same bot token, you get HTTP 409 Conflict (two pollers), duplicate messages, and a dual-agent situation. Banned in CLAUDE.md as HARD RULE. Do NOT lift this.

### AP-2 — Don't inherit parent env when spawning `claude`
**LESSON-098.** Claude Code CLI checks `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` env vars BEFORE OAuth creds. Our `.env` has these populated with invalid/stale keys. Additionally 14 other API-key env vars (OpenAI, Google, xAI, Moonshot, etc.) cause intermittent 401/hangs even when Anthropic vars are filtered out.

**Rule:** Build up a MINIMAL env (`HOME`, `PATH`, `LANG`, `SHELL`, `USER`, `TERM`), never filter down a bloated one.

```python
# ❌ WRONG — filter-down (leaks 100+ inherited vars, flaky)
claude_env = {k: v for k, v in os.environ.items()
              if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}

# ✅ RIGHT — build-up (exactly what claude needs)
claude_env = {
    "HOME": os.environ.get("HOME", "/Users/madia"),
    "PATH": "/Users/madia/.npm-global/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
    "LANG": os.environ.get("LANG", "en_US.UTF-8"),
    "SHELL": os.environ.get("SHELL", "/bin/bash"),
    "USER": os.environ.get("USER", "madia"),
    "TERM": "xterm-256color",
}
```

### AP-3 — Don't put prompt after variadic `--tools` arg
`claude --tools <tools...>` is variadic. If prompt is after `--tools`, claude treats prompt as a tool name and errors. Put prompt RIGHT AFTER `-p`, variadic last:

```python
# ❌ WRONG
[CLAUDE_CMD, "-p", "--tools", "Bash,Read,...", task]
# ✅ RIGHT
[CLAUDE_CMD, "-p", task, "--tools", "Bash,Read,Edit,Write,Grep,Glob"]
```

### AP-4 — Don't skip the /code daily cost cap
`/code` uses Max subscription quota. Respect `CLAUDE_DAILY_CAP_USD` (default $5/day). Cost tracking persists in `~/nous-agaas/logs/claude_code_cost.json` with date-based reset at midnight Almaty.

### AP-5 — Filter zero-byte and tiny files before any ingest/processing API call
**LESSON-062.** `ingest_pending.py` burned 440 Anthropic API calls on a single 0-byte file, each returning HTTP 400 and retrying. Any queue-processing script must gate on file size BEFORE calling any external API:

```python
# At the top of any ingest/queue processor:
MIN_SIZE = 10  # bytes — anything smaller is likely empty/corrupted
for f in files:
    if f.stat().st_size < MIN_SIZE:
        target = UNSORTED / f"empty-{f.name}"
        shutil.move(str(f), str(target))
        log.info(f"Moved empty file to unsorted: {f.name}")
        continue
    # proceed with API call
```

Also: a 400 error from an API should log the response body verbatim — not just be classified as "credit exhausted." Different 400 causes need different handling.

### AP-6 — Verify which Claude client an MCP tool targets before recommending it
**LESSON-063.** Claude Code (`~/.claude.json`) and Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`) are different clients with different MCP config files. A plugin or tool may target Claude Desktop only. Before recommending any MCP server installation:

1. Check the plugin/tool README for "Claude Desktop" vs "Claude Code" in the installation section
2. Check which config file the installer writes to
3. Claude Code needs `~/.claude.json` updated; Claude Desktop needs the other

For `nous-wiki-qmd`: Claude Code already has full vault access via this MCP server (configured in `~/.claude.json`). DO NOT recommend installing any Obsidian plugin for vault access — it's already working.

### AP-7 — Write MEMORY.md immediately on critical status changes, don't defer to handoff
**LESSON-081.** If Madi says "Anthropic is topped up," "contract signed," "API key updated," or similar — this changes a blocker status. If context compression happens before the handoff write, the update is LOST.

Rule: when Madi gives a status update that changes any BLOCKER, CONSTRAINT, or STATE in MEMORY.md:
1. Write MEMORY.md update NOW (before next tool call)
2. Say explicitly: "Updated MEMORY.md: [what changed]"
3. Do not accumulate for the end-of-session handoff

Critical categories that trigger immediate write:
- Blocker resolved ("Anthropic topped up")
- Service status changed ("container X is up/down")
- Decision reversed ("use X not Y")
- Credential updated

### AP-15 — Quiet-hours doctrine must be enforced before spawning LLM work

`operator-boundaries` is not real if it is only prose. Before starting any long-running or token-spending Telegram LLM command (`/ask`, implicit `/ask`, `/ask-direct`, `/code`, `/codex`), the command center must check Almaty quiet hours (`00:30-08:00`). If the request is non-urgent, save it to `pages/personal/boundary-queue-YYYY-MM-DD.md`, reply briefly, and do not call OpenClaw/Codex/Claude. Urgent/client/family/safety/legal/revenue keywords bypass and are logged as an urgent boundary bypass. Status/health/report/help/trace remain available because they are operational checks, not deep-work loops.

### AP-8 — Never inflect or extend a proper name without a source
Before writing a person name in any outbound message (Telegram reply, email, Word doc, wiki page), grep pages/entities/ for the canonical spelling. Do not append honorifics, suffixes, or patronymics (-бек, -ага, -ович, -евич) that are not in a source. If the only record is in Latin, keep it Latin in the target language draft or transliterate exactly by known rules. Also applies to company names, place names, product names. Example failure 2026-04-15: agent wrote Даниярбек when the canonical name is Данияр — caught by Madi. Fix: verify against pages/entities/daniyar.md first.

### AP-9 — Escalation-only: one daily summary, not per-event Telegram spam (LAW-010)

**LAW-010.** The Telegram bot (@nousAGaaSbot) exists for escalation, NOT narration. Madi must not be pinged for every factory event.

Rules:
- **One daily summary at 23:00 Almaty (18:00 UTC)** in Russian covering completed tasks, failures, and cost
- **P0/P1 immediate alerts only:** factory down, ZAI balance exhausted, VPS unreachable, production site down
- **Presidential-level decisions only** for async questions: money, contracts, government submissions, architecture changes affecting revenue
- **Everything else** goes to CEO autonomously. Does NOT ping Madi.
- **Anti-spam gate:** same message content must NOT be sent within 30 min (hash message body, skip duplicate)

### AP-10 — Pre-send fact-check for outbound partner messages (LAW-016)

**LAW-016.** Every outbound partner message (email, Telegram letter to a partner, proposal, call cheat sheet) containing factual claims MUST be verified claim by claim BEFORE it is handed to the user for sending.

A "factual claim" = any specific, falsifiable assertion: numbers, dates, statuses, names, addresses, prices, counts, percentages, URLs, endpoints, uptime figures. Opinions and recommendations do not count.

Steps for every partner draft:
1. List every factual claim in the draft
2. For each claim, find the source: a vault file path, a live API response in this session, a specific cell in an xlsx, or a direct Madi statement in this conversation
3. Mark confidence: "verified" (source found + confirmed) or "unverified" (no source)
4. Flag unverified claims inline with "[UNVERIFIED: reason]" and ask Madi to confirm or delete
5. Never send a draft with unverified claims without explicit Madi sign-off

"Based on my understanding" is NOT a source. A past session memory is NOT a source.

### AP-11 — Sanitize tags before using in file paths (slash-in-command captured as tag)

**Session 70, 2026-04-23. Root cause of intermittent Telegram silence observed 13:20–18:47 KZT.**

**Symptom:** `telegram_poll.py` crashes with `FileNotFoundError` when writing a message file whose path has an intermediate directory that was never created. Messages silently drop; next launchd cycle advances `last_update_id` so the crash window leaves a gap in captured messages.

**Mechanism:** Any message body starting with `/<word>` for which `command_center.is_command()` returns True but `handle()` returns False (or that matches no routed command) falls through to the `write_text` capture path. `parse_caption()` splits the body into whitespace tokens and stores each as a raw tag — including tokens starting with `/`. Joining raw tags into `tags_suffix` embeds a literal `/` in the filename; `write_text` treats that as a directory separator; the intermediate directory does not exist → crash.

**Concrete case (from 13:20 / 13:21 crash traceback):**
- body = `"/audit ..."`
- `parse_caption` → `tags = ['/audit', ...]`
- `tags_suffix = "-/audit-..."` (literal slash)
- filename = `telegram-TS-<slug>-/audit-....md`
- `FileNotFoundError: [Errno 2] No such file or directory: '.../telegram-...-audit-/audit.md'`

**Fix (`telegram_poll.py:212`):**

```python
# Before (vulnerable):
tags_suffix = "-".join(parsed["tags"][:3]) if parsed["tags"] else ""

# After (slugify strips / and other non-safe chars via regex [^a-zA-Z0-9\s-]):
tags_suffix = "-".join(slugify(t) for t in parsed["tags"][:3] if slugify(t)) if parsed["tags"] else ""
```

**General rule:** any user-derived string used in a file path MUST pass through `slugify()` (or equivalent allow-listing sanitizer) before being interpolated into the path. Never compose paths from raw message tokens, captions, filenames, or URL fragments. `os.path.join` / `pathlib /` operators treat `/` as a directory separator silently — defense must happen at the sanitization boundary, not at write time.

**Belt-and-suspenders alternative (not shipped; noted):** `out_file.parent.mkdir(parents=True, exist_ok=True)` before every `write_text` call survives any other path-construction bug, but masks root causes. Prefer the allow-listing sanitizer as the primary defense.

**Verification (session 70):** Regression test — 6 cases including `/audit`, `/audit do deep dive`, `/status ping`, `/health`, `audit please`, plain text — all produce flat filenames post-fix. E2E — `process_message({"text": "/audit regression test s70"})` returned `success=True, kind="text"`, wrote flat-path file, no FileNotFoundError. Launchd re-spawned poller (PID 32000, 22:09 KZT) with fixed code.

### AP-12 — Telegram poller regression tests must be repo-local runnable (session 75, 2026-04-26)

**Symptom:** During the Codex Telegram staleness trace, `python3 -m unittest tools/test_telegram_poll.py` failed on Mac with `ModuleNotFoundError: No module named 'telegram_poll'`, then failed again importing `command_center` dependencies absent from the vault checkout. The production AP-11 fix was present, but the detector could not prove it from the current repo.

**Root cause:** `tools/test_telegram_poll.py` only inserted old runtime paths (`/opt/nous-agaas`, `/root/nous-agaas/tools`) into `sys.path`, and imported the real `command_center.py`, which depends on Air runtime modules not present in the Mac wiki checkout. The test was accidentally Air/VPS-shaped, not repo-shaped.

**Rule:** Telegram poller regression tests must:

1. Add `Path(__file__).resolve().parent` to the front of `sys.path` so local `tools/telegram_poll.py` wins over stale legacy runtime paths like `/root/nous-agaas/tools`.
2. Stub runtime-only dependencies (`dotenv`, `command_center`) before importing `telegram_poll`.
3. Include a specific `/audit` fallback-capture assertion that inspects the actual written path and proves the file is a direct child of `PENDING`, not merely that `Path.name` has no `/`.
4. Pass with `python3 -m unittest tools/test_telegram_poll.py` from the repo root before trusting AP-11.

**Verification:** Session 75 reran the test after the harness fix: 8 tests passed, including `/audit deep dive` producing flat filename `telegram-...-audit-deep-dive-audit-deep-dive.md` and a tempdir E2E assertion that exactly one direct child file was written. VPS failure exposed stale `/root/nous-agaas/tools/telegram_poll.py`; backflowed the safe wiki copy there too.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/command-center/skill`.

### AP-13 — Telegram-facing health/help must match the live host-role split

**Session 2026-04-26. Root cause of `/health` trust leak during Telegram control-plane audit.**

**Symptom:** `command_center._run_health()` returned a red factory-health message claiming Docker `litellm`, `langfuse`, `langfuse-db`, `ncanode`, and `/root` were failing on Air. After that was fixed, the same command still marked disk red because Python `shutil.disk_usage("/")` on macOS APFS showed 94% raw used while `df -h /` showed the root volume at 32% capacity with 26 GiB available. The actual Air architecture has OpenClaw in Docker, LiteLLM as native launchd on port 4000, and Langfuse/NCANode on VPS. `/help` also still described `/ask` as "Opus 4.6" even though `/ask` now routes through `grok-ceo`.

**Root cause:** `factory_health.py` was copied from the VPS-era stack into Air runtime and then patched in place, but it never became a vault-managed `tools/` file. Because Obsidian/gbrain could not see the live helper, architecture changes updated `architecture-quickref` and `ceo-hierarchy` while `/health` kept checking old host responsibilities.

**Rule:** any Telegram-facing command output is operator truth, not decoration. Before calling a command healthy:

1. Its human text (`/help`, progress messages, footers) must name the actual route/model/host roles.
2. Its health checks must match the current architecture table: Air checks Air-owned services; VPS checks VPS-owned services; tenant checks stay tenant-scoped. On macOS/APFS, disk red must be based on actionable free GB, not raw `shutil` percent-used.
3. Any imported helper used by `command_center.py` must live under vault `tools/` and be synced or root-symlinked into Air runtime. Runtime-only helpers are invisible to Obsidian/gbrain and will drift.
4. Verification must include a command-level self-test, not just Python syntax: `/health` should fail only on real current constraints, not retired topology.

**Fix pattern:** move the helper into `wiki/tools/`, rsync to `~/nous-agaas/tools/`, and make the root runtime import a symlink when `command_center.py` imports by module name.

### AP-14 — Keep OpenAI Codex subscription auth and API fallback isolated

**Session 2026-04-27. Root cause of "Telegram with OpenAI 5.5" gap.**

**Symptom:** Air had the Codex binary at `/Applications/Codex.app/Contents/Resources/codex`, and `~/.codex/auth.json` existed, but `codex exec -m gpt-5.5` failed with `401 Unauthorized`, `token_expired`, and `refresh_token_reused`. Telegram `/ask` worked through OpenClaw, but there was no Telegram route to Codex/OpenAI 5.5, and `/code` still meant Claude Code Sonnet.

**Root cause:** Air's default Codex subscription auth was stale/reused, and `command_center.py` had no OpenAI Codex dispatch branch. The Mac Codex app was healthy and configured as `model = "gpt-5.5"`, but the always-on Air runtime could not use that session directly. Copying Mac `~/.codex/auth.json` to Air would risk refresh-token collision; do not do that.

**Rule:** Telegram control-plane must expose backend reality explicitly:

1. `/ask` remains the OpenClaw factory route.
2. `/codex` is the OpenAI Codex route (`gpt-5.5`) and must say which auth path it used: subscription or API fallback.
3. `/code` remains the legacy Claude Code route until intentionally migrated; never silently repoint `/code` during a cost/root-cause incident.
4. Air subscription auth (`~/.codex`) and API fallback auth (`~/.codex-api`) must stay separate. Use `CODEX_HOME=/Users/madia/.codex-api` for API fallback so a noninteractive repair does not overwrite the subscription login.
5. If subscription auth fails with `token_expired`, `refresh token`, or `401`, retry once with the isolated API fallback if it exists. The Telegram footer must disclose API fallback use.
6. Daily `/codex` calls must be capped (`CODEX_DAILY_CAP_CALLS`, default 12) and counted in `~/nous-agaas/logs/codex_usage.json`.
7. `/codex` startup context must read the same continuity substrate as `/code`: newest HANDOFF-AUTO, MEMORY.md top-block, `session-operating-contract`, and `command-center`. Codex sessions are disposable; substrate carries continuity.

**Verification:** Air `CODEX_HOME=$HOME/.codex-api codex exec --ephemeral -m gpt-5.5 ... "Reply exactly CODEX_AIR_API_OK"` returned `CODEX_AIR_API_OK`. Air default `~/.codex` failed with `refresh_token_reused`, proving the subscription auth needs one-time re-login via `ssh -t air '/Applications/Codex.app/Contents/Resources/codex login --device-auth'`.

### AP-16 — `/codex` route must not depend on one Mac app path or call-count-only caps

**Trigger:** Nightly review flagged `/codex` as low severity because the route had a Mac-specific binary path (`/Applications/Codex.app/Contents/Resources/codex`) and a soft daily cap based only on call count.

**Root cause found 2026-04-28:** AP-14 proved the first working Air route through the app-bundled Codex binary, then froze that exact path into the router. That was fine as proof, but not as durable infrastructure: Air can have Codex installed through the app bundle, Homebrew, npm/global, or PATH. The route also tracked observed tokens but did not enforce a token ceiling.

**Rule:** Slash-command runners must resolve executables by policy, not one proof-machine path. `/codex` resolution order is: `CODEX_CMD` env override, known Air app/Homebrew/npm paths, then `PATH`. The daily guard must include both call count and observed token ceiling (`CODEX_DAILY_CAP_TOKENS`, default 250000). Token counting is best-effort from CLI output, so the call cap remains a second guard.

**Implementation:** `tools/command_center.py` now uses `_resolve_codex_cmd()`, returns a repair message that names the resolved command, exposes the token cap in `/codex` usage/help, and blocks before subprocess spawn when observed tokens already meet the cap.

**Verification:** `python3 -m unittest tools/test_operator_boundaries.py` includes `/codex` resolver and token-cap tests.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/command-center/skill`.

### AP-20 — Classifier ack lands as a footer on the existing /ask reply, never a second message

**Phase 2.5 wiring rule.** The intent-classifier post-/ask hook must append `📥 Saved as <intent> in [[<slug>]]<side-effect-summary>` to the existing reply text, not send a second Telegram message. Two messages is noisy (push-notification spam), splits the trace, and makes the user's chat history harder to skim. Wire `_classify_inbox_post_ask(msg_id, query)` between `_compose_cost_footer()` and the `MAX_MSG_LEN` truncate check so it shares the same envelope. If the truncate check fires, the classifier footer is dropped (acceptable; `/ask` reliability > ack visibility).

**Kill-switch:** `TELEGRAM_INGEST_CLASSIFY=0|off|false` disables the hook (default ON). Same shape as Phase 2's `TELEGRAM_INGEST_PERSIST`. The hook's try/except returns `""` on any failure (LiteLLM down, inbox file missing, classifier import fails) — never propagates.

**Confidence floor:** the hook returns `""` when intent is `unknown` OR confidence < 0.5 — no footer, no side-effects. The hourly `inbox_walker.py` retries low-conf candidates next cycle; do NOT spam the user with low-confidence guesses.

### AP-21 — LiteLLM null-content is a real failure mode; graceful-degrade the classifier

**Discovered on Madi's real msg 1123** (2026-04-30 22:14 KZT, 2665B, mixed RU/EN with typos and multi-topic). DeepSeek V4 Flash returned `data["choices"][0]["message"]["content"] = None` (not empty string, not error — actual JSON null). The original `intent_classifier.py:115` did `data["choices"][0]["message"]["content"].strip()` which raised `AttributeError: 'NoneType' object has no attribute 'strip'` — NOT caught by the existing `(KeyError, IndexError, TypeError)` tuple, so it propagated up and crashed `inbox_walker.py` mid-loop, killing the whole hourly run.

**Fix in `tools/intent_classifier.py`:** check `if text is None` explicitly (return `intent: unknown, rationale: "litellm returned null content"`), and add `AttributeError` to the catchall except tuple as belt-and-suspenders.

**Fix in `tools/inbox_walker.py`:** wrap `process_one()` in per-file try/except so one classifier crash does not kill the whole run. Each file gets its own `process-error` log entry; the loop continues.

**General rule for any LiteLLM integration in this codebase:** treat `content` as nullable. Long, ambiguous, multi-topic, or filter-tripping prompts can produce `null` content even on 200 OK responses. Always check before `.strip()`/regex/json-parse.

### AP-22 — Persistent slash commands must start or schedule their durable runner visibly

**Symptom:** `/goal` returned "Goal created" but no work started immediately; the first OpenClaw slice waited for the next 4-hour launchd interval. The operator experienced that as the command stopping.

**Root cause:** The command handler persisted state but did not kick `com.nous.goal-cycle`, and the launchd plist was Air-local rather than tracked in the vault.

**Rule:** If a slash command promises persistence (`/goal`, future `/research`, future `/campaign`), command creation must either start or schedule the durable runner and include the runner result in the Telegram reply. Silent background assumptions are invalid.

**Detector:** focused test must assert the handler calls the kick/schedule helper and the reply contains `Runner: ...` or `Runner not started: ...`.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/command-center/skill`.

### AP-23 — Group chats must be explicit, allowlisted, and non-spammy

**Symptom:** Madi already had a Satory team Telegram group, but the Air poller only trusted `TELEGRAM_CHAT_ID`, which is Madi's private DM. Adding the bot to the group would be ignored as non-allowed. A naive fix would be worse: every normal group message could become an implicit `/ask`.

**Rule:** group operation is allowed only through an explicit allowlist and explicit operator intent. Slash syntax is not the product:

- `TELEGRAM_CHAT_ID` remains Madi's private DM.
- `TELEGRAM_ALLOWED_CHAT_IDS` and/or `TELEGRAM_GROUP_CHAT_ID` may add the Satory group chat id after the bot is added and a probe message exposes the id in logs.
- Group slash commands with bot suffix are normalized, e.g. `/status@nousAGaaSbot` -> `/status`.
- Normal group chatter is ignored; it must not become implicit `/ask`.
- Group work requests must be addressed to the factory naturally (`Фабрика, ...`, `Nous, ...`, `@nousAGaaSbot ...`) or use `AI: ...`. Slash commands remain a power-user fallback, not the expected UX.

This keeps the existing group usable without turning the company chat into an accidental token-burning router.

### AP-24 — Full-chat group observe mode is memory, not auto-execution

**Symptom:** The group route can be "working" for `/status@bot` but still fail Madi's real goal: the factory misses team chatter because Telegram bot privacy mode hides normal group messages, or because the poller ignores non-command group text to avoid token burn.

**Rule:** Satory group full-chat mode requires three gates:

- Telegram-side: BotFather privacy mode must be disabled for `@nousAGaaSbot`, and the team must know the bot reads the Satory group.
- Config-side: the group id must be present in `TELEGRAM_ALLOWED_CHAT_IDS` and in `TELEGRAM_FULL_CHAT_CHAT_IDS` or `TELEGRAM_GROUP_OBSERVE_CHAT_IDS`.
- Runtime-side: every group text message is persisted to `pages/inbox/...` with sender provenance, but normal chatter is not routed to OpenClaw. Commands and explicit `AI:` requests still execute. The inbox walker/classifier can turn observed messages into tasks/facts/decisions later.

This is the scalable path: full memory first, capped action second, proof before closing tasks. It avoids both first-stage "only listens when tagged" behavior and reckless "LLM on every message" chaos.

### AP-30 — Natural-language operator surface; slash commands are implementation detail

**Symptom:** Madi pushed back on slash-command UX: the desired interface is to talk naturally to a god-level second brain, not memorize `/ask`, `/goal`, `/codex`, etc. The previous group rule was safe but too primitive: commands and `AI:` were operator syntax, not the finished product.

**Root cause:** The command router exposed its internal API as the human interface. That violates the Musk step-2 rule: the best part is no part. Slash commands are useful inside code, but they are unnecessary human friction for normal operation.

**Rule:** `telegram_poll.py` owns a deterministic natural-language router before `command_center.handle()`:
- Private DM plain text maps to the right internal command.
- Addressed group text (`Фабрика, ...`, `Nous, ...`, `@nousAGaaSbot ...`, `AI: ...`) maps to the right internal command.
- Natural status words route to `/status`, `/health`, or `/report`.
- Natural goal words (`цель:`, `goal:`, `создай цель ...`) route to `/goal`.
- Natural top-GPT words (`use gpt 5.5`, `codex`, `top tier gpt`) route to `/codex`.
- Everything else intentional routes to `/ask`.
- Unaddressed group chatter remains context-only and must not execute.

**Detector:** `python3 -m pytest tools/test_telegram_poll.py -q` must include natural DM status, natural DM goal, natural DM GPT/Codex, addressed group ask, addressed group status, and unaddressed group chatter not executing.

**Recovery:** if operators complain "I have to use slash," add a deterministic natural phrase to `natural_command()` or `_strip_factory_address()` and a regression test. Do not solve this by LLM-classifying every group sentence; that recreates token burn and accidental execution.

### AP-31 — Root command router shadow must not lag behind tracked tools router

**Symptom:** LangGraph/Todoist routing was implemented in `tools/command_center.py`, but `tools/test_operator_boundaries.py` imported root `command_center.py` and failed: missing `_codex_daily_budget_ok`, missing OpenClaw identity fast-path, and `/ask` long-work/bounded-execution payloads still fell through to `_run_openclaw`.

**Root cause:** The repo still has a legacy root `command_center.py` for runtime compatibility, while new command-center work landed only in `tools/command_center.py`. AP-26 fixed poller import precedence, but tests and some direct runtime imports still target root. That creates split-brain router behavior: live path can be newer than direct import path, or vice versa.

**Rule:** any command-center routing change must keep both import surfaces coherent until the root shadow is deleted or replaced with a tiny import shim:

- edit `tools/command_center.py` as the source implementation;
- mirror the exact implementation to root `command_center.py`, or convert root to a deliberate shim in the same commit;
- `telegram_poll.py` must load the tools router explicitly when a non-tools `command_center` is already preloaded, without replacing `sys.modules["command_center"]` for other tests/processes that already hold the root module;
- run `python3 -m pytest tools/test_telegram_poll.py tools/test_operator_boundaries.py -q` or the focused operator gate before claiming Telegram routing works.

**Detector:** `diff -u command_center.py tools/command_center.py` must be empty for implementation-copy mode. If root becomes a shim, the detector must instead assert root imports and exposes `_run_codex`, `_codex_daily_budget_ok`, `_factory_orchestration_decision`, and `_is_openclaw_identity_question`.

**Recovery:** if operator tests fail on missing command-center helpers, check root/tools drift before debugging policy logic.

### AP-32 — Production truth gate must separate live Telegram/OpenClaw health from Air runtime root release dirt

**Symptom:** A `/codex` audit claimed the factory was not 100% because the outer Air runtime repo at `/Users/madia/nous-agaas` was dirty, even while the live Telegram/OpenClaw path, wiki parity, launchd poller, and command-center hashes were green. That mixed three layers: canonical wiki, live Air runtime import path, and release-hygiene residue.

**Root cause:** The audit used generic `git status` cleanliness as a production-health proxy. In this substrate the production truth is not "Air runtime root is clean"; it is "the launchd poller imports the tracked tools router, command-center copies match, wiki mirrors are converged, and the factory probe is green." Air runtime root dirt is still real, but it is release hygiene unless it changes the files the production path actually imports.

**Rule:** before saying Telegram/OpenClaw is red because of local dirt, run:

```bash
python3 tools/telegram_openclaw_factory_truth_gate.py --json
```

The gate is RED only for production failures: wiki HEAD/parity drift, dirty canonical wiki worktrees, command-center hash drift across runtime root/tools/wiki, wrong launchd poller path, wrong poller import order, or `factory_no_drift_probe` RED. Air runtime root dirt is reported as YELLOW `release_dirty` unless `--strict-runtime-root` is explicitly requested for a release-cleaning lane.

**Detector:** `python3 -m pytest tools/tests/test_telegram_openclaw_factory_truth_gate.py -q` proves dirty runtime root is YELLOW by default, strict mode can make it RED, command-center split-brain hashes are RED, and poller import order must prefer tracked tools.

**Recovery:** if the truth gate is RED, fix the specific red check. If only `air_runtime_root_hygiene` is YELLOW, do not block Telegram/OpenClaw production status; open or continue a separate release-cleaning lane for `/Users/madia/nous-agaas`.

### AP-33 — Truth gates must not assume identical git remote names on Mac, Air, and VPS

**Symptom:** The first live Air run of `tools/telegram_openclaw_factory_truth_gate.py` returned a false RED for `wiki_head_parity`: the production checks and factory probe were green, but the script tried `git ls-remote vps` from Air where the canonical mirror is named `origin`, not `vps`.

**Root cause:** The gate encoded the Mac remote naming convention instead of probing the authoritative substrate directly. In this repo, Mac has `vps`, Air has `origin`, and VPS working copy may have `bare`/`vps`.

**Rule:** cross-host truth gates must not rely on local remote aliases for canonical infrastructure. Probe VPS bare with the direct host path (`git --git-dir=/root/nous-agaas/obsidian-wiki.git rev-parse refs/heads/main`) and use local aliases only where they are known to exist, such as the GitHub mirror alias in wiki checkouts.

**Detector:** every new truth gate must be run from the host it is meant to validate, not just from Mac. For this gate the required live command is:

```bash
ssh air 'cd ~/nous-agaas/wiki && python3 tools/telegram_openclaw_factory_truth_gate.py --json'
```

**Recovery:** if a host parity check fails with `fatal: '<remote>' does not appear to be a git repository`, fix the probe to read the authoritative path or configurable remote. Do not classify the factory red until the corrected probe still fails.

### AP-34 — Telegram `/ask` E2E proof must be observer-only and include reply-delivery evidence

A green `telegram_poller` launchd check proves the poller is alive; it does not prove the operator-facing `/ask` path completed. A real `/ask` E2E proof needs all five signals for one nonce:

1. Air `telegram_poll.py` log saw an inbound message containing the nonce.
2. The log exposed the Telegram `msg_id`.
3. `ask-hierarchy.jsonl` contains `correlation_id=tg_<msg_id>` with `decision=ok`.
4. Air log contains `/ask handled` after the nonce-bearing inbound was seen.
5. `command_center._tg_send()` logged successful `sendMessage` with `reply_to=<msg_id>`.

Never start a second `getUpdates` client to prove this. Use `tools/telegram_ask_e2e_probe.py`, which optionally sends one outbound request through `tg_send.sh` and then watches Air logs only. If no human-originated inbound arrives, classify the proof YELLOW instead of faking a green result. A stale `/ask handled` line from another message is not evidence; the harness must first bind the nonce to a concrete `msg_id`.

### AP-35 — OpenClaw agent zero-byte stdout must recover from session JSONL before failing Telegram `/ask`

**Symptom:** nonce-bound `/ask` proof `E2E-CODEX-20260517101432` reached Air, routed to `openclaw-agent:grok-ceo`, and OpenClaw wrote assistant text into the `grok-ceo` session JSONL, but `tools/run_task.py` logged `Failed to parse agent JSON output: Expecting value: line 1 column 1 (char 0)` because `openclaw agent --json` returned exit 0 with empty stdout for that invocation. Telegram then returned an error reply instead of the assistant answer.

**Root cause:** `run_task.py` only used the async-await session JSONL recovery path after successfully parsing JSON with empty `payloads=[]`. It did not run the same recovery path when stdout was empty or non-JSON, even though the session JSONL could already contain the completed assistant turn.

**Rule:** for OpenClaw agent routes, `run_task.py` must treat `returncode=0` plus empty/non-JSON stdout as a recoverable transport anomaly. Before raising a parser error, poll the agent session JSONL from the pre-run line count. If assistant text appears, synthesize an `ok` result with payload source `async-await-empty-stdout` or `async-await-nonjson-stdout`; only fail if no session text is recoverable.

**Detector:** keep a regression that mocks `subprocess.run()` returning `returncode=0, stdout=""` and verifies `run_task()` returns recovered text from `_poll_for_async_announce()` instead of raising.

**Recovery:** after this fires in production, rerun the nonce-bound `tools/telegram_ask_e2e_probe.py` and require all five AP-34 checks to pass. Do not declare Telegram `/ask` green from a direct OpenClaw CLI canary alone.

### AP-25 — Telegram `/status` must be launchd-PATH safe and host-accurate

**Symptom:** `/status@nousAGaaSbot` worked in the Satory group but replied with `memory error: [Errno 2] No such file or directory: 'sysctl'` and an old "Checking VPS health..." waiting line. The command was running on Air under launchd, where `PATH` can omit `/usr/sbin`, so macOS `sysctl` was not resolvable by bare name.

**Rule:** Telegram-facing status commands must not depend on an interactive shell PATH. Use `shutil.which()` plus absolute fallbacks for platform tools (`/usr/sbin/sysctl`, `/usr/bin/vm_stat`, `/bin/df`) and make the user-facing label match the actual host role (`factory health`, not stale `VPS health`).

**Detector:** unit tests must simulate a minimal launchd PATH by making `shutil.which()` return `None`, then assert `/status` still reports memory without `memory error` and the wait message says `factory health`.

### AP-26 — Telegram poller must import the tracked command router before runtime-root shadows

**Symptom:** `tools/command_center.py` was fixed and copied to Air, but the live poller still returned the old `/status` memory error. Root cause: runtime `telegram_poll.py` inserted `/Users/madia/nous-agaas` before importing `command_center`, so Python loaded stale `/Users/madia/nous-agaas/command_center.py` instead of tracked `/Users/madia/nous-agaas/tools/command_center.py`.

**Rule:** `telegram_poll.py` must put its own `tools/` directory before the runtime root on `sys.path` before importing `command_center`. Runtime root shadow files may exist for legacy reasons, but they must not win over the tracked tool module.

**Detector:** `tools/test_telegram_poll.py` must assert the poller's `tools/` directory appears before `/Users/madia/nous-agaas` in `sys.path`.

### AP-27 — Do not mix main factory bot proof with APK camera-status bot proof

**Symptom:** A Satory group proof showed two bot replies at the same timestamp: `Nous AGaaS` from main `@nousAGaaSbot` and `Nous AI` from the separate APK status bot. Treating both as one Telegram system hid the real boundary: main factory routing was healthy except for `/status` memory rendering, while APK camera status was a separate VPS camera-health product.

**Rule:** every Telegram audit must name the bot identity and host before diagnosing:

- `@nousAGaaSbot` / `Nous AGaaS` = main factory bot on Air (`com.nous.telegram-poll`): OpenClaw, Hermes, Todoist/Notion, `/ask`, `/goal`, `/status`.
- APK status bot / `Nous AI` = separate VPS camera/APK monitoring bot (`apk-bot-polling.service`): camera reachability, ISAPI/APK health, NIT VPN diagnosis.

Do not call APK camera status "factory health." Do not call main factory `/status` broken because a separate APK bot reports no camera data. If both replies appear in one Telegram screenshot, split the incident into two tracks and verify each with its own runtime path.

**First-try detector:** a Telegram group change is not done until all three are proven from the live runtime:

1. normal non-command group text persisted to `pages/inbox/...` with `chat_id`, `msg_id`, and sender;
2. command output renders from the same launchd import path used in production;
3. the reply text names the correct subsystem and next failing layer.

### AP-28 — Exact live-command verification must route to `/codex`, not OpenClaw `/ask`

**Symptom:** Madi sent a `VERIFY:` task asking the bot to run exact commands (`ssh air`, `launchctl`, `pytest`, `factory_no_drift_probe`, Google Drive upload, gbrain/OpenBrain readback). Telegram routed it as `/ask` to OpenClaw `grok-ceo`, which runs in `/home/node/.openclaw/workspaces/grok-ceo` and does not have Air SSH, launchd, pytest, or Drive access. The worker honestly returned `BLOCKED`, but the router had already chosen the wrong execution lane.

**Rule:** `/ask` remains the low-token Grok/OpenClaw CEO path for reasoning, classification, drafting, and delegation. If the payload starts with `VERIFY:` or asks to `Run exact commands` / `save outputs` and includes live shell markers (`ssh air`, `launchctl`, `python3 -m pytest`, `factory_no_drift_probe`, `control_plane_sync_loop`, `git rev-parse`, `curl`, Google Drive, gbrain readback, OpenBrain projection), `command_center.py` must auto-escalate to `/codex` on Air before calling `_run_openclaw`.

**Detector:** `tools/test_operator_boundaries.py::OperatorBoundaryQueueTests::test_shell_verification_ask_auto_escalates_to_codex` asserts that such a `/ask` payload calls `_run_codex()` exactly once and never calls `_run_openclaw()`.

**Boundary:** Do not auto-escalate ordinary questions that contain the word "verify". The detector is intentionally narrow: exact-command verification only. Broad auto-GPT for all `/ask` traffic would violate the low-token CEO routing policy.

### AP-29 — Combined Telegram/operator tests must not inherit a fake `command_center` module

**Failure mode:** `tools/test_telegram_poll.py` installs a lightweight `command_center` stub so it can unit-test poller routing without importing the full runtime router. When pytest collects `tools/test_telegram_poll.py` before `tools/test_operator_boundaries.py`, that stub can remain in `sys.modules`. The operator-boundary suite then imports the fake module and reports false missing attributes (`_run_codex`, `_operator_boundary_decision`, `_tg_send`, goal helpers), even though the tracked Air router is correct and each suite passes alone.

**Rule:** any test file that validates the real Telegram command router must evict a pre-existing stub before `import command_center`. The guard is simple: if `sys.modules["command_center"]` exists and does not expose `_run_codex`, remove it and import the real `tools/command_center.py`.

**Detector:** run the combined gate, not only the individual suites:

```bash
python3 -m pytest tools/test_telegram_poll.py tools/test_operator_boundaries.py -q
```

The expected result is `34 passed`. If the individual suites pass but the combined gate fails, treat it as test-isolation drift before declaring Telegram routing verified.

### AP-19 — `/code` and `/codex` must register outer runtime sessions mechanically

**Trigger:** Session 83 Lane B audit found that v2.9.3 made the handshake visible in prompt text, but production runtime would still depend on the spawned agent following instructions. The live Air router was also behind until sync, so the only durable fix is to make the command router itself register and close spawned work.

**Root cause:** A startup preamble is useful context, but it is not a control-plane fact. The registry is the control plane. If the registry only updates when a child agent voluntarily runs `session_register.sh`, `/code` and `/codex` sessions can be invisible during exactly the broad coding tasks where collision awareness matters.

**Rule:** Telegram-spawned coding sessions have an outer registry lifecycle owned by `command_center.py`:

1. After cost/call caps pass and before spawning the child process, call `tools/session_register.sh --host air --intent "Telegram /code|/codex: <task preview>" --scope "*"`.
2. Inject the returned `session_id` into the child prompt as runtime coordination evidence.
3. Close that exact outer session in a `finally` block with `tools/session_close.sh --session-id <session_id> <status>`.
4. Child agents may still register narrower helper lanes, but they do not own the outer session lifecycle.

This preserves the thin-registry design from `session-coordination`: no mutex, no new queue, just truthful visibility around the actual subprocess boundary.

**Implementation:** `tools/command_center.py` adds `_register_spawned_session`, `_close_spawned_session`, and `_spawned_session_note`; `_run_claude_code()` and `_run_codex()` now wrap subprocess execution with register/close. `tools/test_operator_boundaries.py` verifies both routes call register/close and inject the returned session id into the prompt.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/command-center/skill`.

### AP-18 — Spawned `/code` and `/codex` agents must receive the coordination handshake directly

**Trigger:** Session 83 top-CTO workflow audit after Madi asked for four simultaneous Codex/Claude Code sessions that help each other without breaking each other.

**Root cause:** `/code` and `/codex` startup preambles told spawned agents to read HANDOFF, MEMORY, and doctrine, but did not explicitly include the mechanical session coordination commands. A spawned agent could be well-intentioned, read too shallowly, and edit files without registering scope or checking overlap. That made the four-session handshake true in `session-coordination`, but not unavoidable at the Telegram spawn boundary.

**Rule:** Every Telegram-spawned coding/reasoning agent must receive the coordination handshake in the injected preamble, not only by reference:

1. Read `session-coordination/SKILL.md`.
2. Before any file edit, broad audit, or helper-agent dispatch, run `bash tools/session_register.sh --host air --intent "<short task>" --scope "<files/dirs>"`.
3. Run `bash tools/session_scan.sh --overlap-with "<files/dirs>"`.
4. Use `git commit -o <paths>` for only owned edits.
5. Close with `bash tools/session_close.sh --session-id <session_id> ok`.

This is the Musk/Tan/Karpathy shape: do not add a new coordination system; put the existing thin registry harness at the first point where agents receive intent.

**Implementation:** `tools/command_center.py` now injects the handshake into both `SESSION_CONTEXT_PREAMBLE` (`/code`) and `CODEX_CONTEXT_PREAMBLE` (`/codex`). `tools/test_operator_boundaries.py` blocks drift by asserting both preambles contain the coordination skill and the register/scan/path-limited-commit/close commands.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/command-center/skill`.

### AP-17 — Claude auth status is not proof that `/code` can run

**Trigger:** 2026-04-29 `/code` smoke after the Claude path fix reached `/Users/madia/.npm-global/bin/claude` 2.1.122, but `claude -p` returned HTTP 401 invalid credentials. `claude auth status` still printed `loggedIn: true`, while `~/.claude/.credentials.json` had `expiresAt` on 2026-04-16.

**Root cause:** Claude auth metadata can remain present after the usable first-party token/refresh path is dead. A status command that only reads local state is not an end-to-end proof. The production path is print mode (`claude -p`) from the same minimal environment used by `/code`.

**Rule:** `/code` auth repair is green only when a print-mode exact-response smoke passes:

```bash
ssh air 'cd ~/nous-agaas && python3 -c "
import command_center
print(command_center._run_claude_code(\"Reply exactly: CODE_AUTH_OK\"))
"'
```

If it returns 401, run the human reauth path on the Air host:

```bash
ssh -t air '$HOME/.npm-global/bin/claude auth login --claudeai --email mayazbay@gmail.com'
```

Then rerun the exact-response smoke. Do not mark `/code` operational from `claude auth status` alone. A stale OAuth file is a credential blocker, not a router code bug, once binary path and version parity are proved.

**Implementation:** `command_center.py` now detects Claude 401/authentication errors and replies with the exact Air reauth command instead of returning a generic truncated API error.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline on `pages/skills/command-center/skill`.

## Output Format

**`/ask`:** Plain text from OpenClaw. >4000 chars saves full to wiki + link returned.

**`/code`:** Agent response followed by footer:
```
<response text>

—
💰 $X.XXX | ⏱️ N.Ns | today: $X.XX/5.00 (N calls)
```

**`/status`:** HTML-formatted with `<b>` headers and `✅`/`❌` icons.

## Files

| File | Role |
|------|------|
| `~/nous-agaas/command_center.py` | Core module (`is_command`, `handle`, `_run_openclaw`, `_run_claude_code`, `_run_status`) |
| `~/nous-agaas/tools/telegram_poll.py` | Polls Telegram every 60s; routes commands before vault capture |
| `~/nous-agaas/tools/factory_health.py` | Air `/health` helper; root import should symlink here |
| `~/nous-agaas/run_task.py` | Calls OpenClaw via `docker exec` |
| `~/nous-agaas/logs/claude_code_cost.json` | Daily /code cost tracker |
| `~/nous-agaas/logs/codex_usage.json` | Daily /codex call/token counter |
| `CODEX_CMD` or resolved Codex executable | Air Codex CLI binary |
| `~/.codex` / `~/.codex-api` | Codex subscription auth / isolated API fallback auth |
| `~/Library/LaunchAgents/com.nous.telegram-poll.plist` | Runs telegram_poll every 60s |

## Verification

```bash
# /ask path
ssh air 'cd ~/nous-agaas && python3 -c "
import command_center
print(command_center._run_openclaw(\"Reply UP\"))
"'  # expect: UP

# /code path (direct test, bypasses Telegram)
ssh air 'cd ~/nous-agaas && python3 -c "
import command_center
print(command_center._run_claude_code(\"reply UP\"))
"'  # expect: UP + cost footer

# /codex path (direct test, bypasses Telegram)
ssh air 'cd ~/nous-agaas && python3 -c "
import command_center
print(command_center._run_codex(\"reply UP\"))
"'  # expect: UP + OpenAI Codex footer

# End-to-end
# Send "/ask Reply UP" to @nousAGaaSbot → UP reply
# Send "/codex reply UP" to @nousAGaaSbot → UP + OpenAI Codex footer
# Send "/code reply UP" to @nousAGaaSbot → UP + cost footer
```

## Brain-aware invocation (gstack v0.18.0.0, 2026-04-17)

Before adding / editing / debugging a slash command route (e.g., `/ask`, `/code`, `/status`), `mcp__gbrain__search` with the command name + "telegram" — prior routing incidents (LESSON-087 Telegram MCP ban, dedup, poller state file path) usually have a precedent. Fast keyword search only. After change, `mcp__gbrain__add_timeline_entry slug="pages/skills/command-center/skill"` with "<command>: <change>". See [[skills/_gbrain/BRAIN-AWARE-INVOCATION]].

## Rules absorbed from lessons

- **LESSON-087:** Never use Telegram MCP from any Claude Code session; Air telegram_poll owns the bot.
- **LESSON-088:** Save `last_update_id` BEFORE slow handler runs (atomic `os.replace()`) to prevent duplicate routing.
- **LESSON-098:** Use minimal build-up env for `claude` subprocess, not filter-down of inherited env.
- **LESSON-062:** Filter zero-byte files before any ingest API call; inspect 400 response body. See AP-5.
- **LESSON-063:** Verify Claude client target (Code vs Desktop) before recommending MCP tools. See AP-6.
- **LESSON-081:** Write MEMORY.md immediately on critical status changes, not at session end. See AP-7.

- **LAW-010:** One daily summary at 23:00 Almaty. P0/P1 immediate alerts only. Presidential decisions only for Madi. Anti-spam 30min gate. See AP-9.
- **LAW-016:** Pre-send fact-check all outbound partner messages. Verified-claims required. Flag [UNVERIFIED]. See AP-10.
- **AMENDMENT-003 (Memory Sync):** Critical status changes must be written to MEMORY.md immediately, not deferred to end-of-session handoff. Already enforced by AP-7 (immediate MEMORY write on critical status changes). This amendment is the formal codification.

---

## Evidence trail (append-only)

- **2026-04-13** | v1.0.0 — initial Telegram routing for /ask, /status, /help (VPS era).
- **2026-04-14** | v1.0.0 patched with /handoff + state dedup (LESSON-088).
- **2026-04-15** | v2.0.0 — migrated to Air; added /code (Claude Code Sonnet 4.6 with tools); absorbed LESSON-087, LESSON-098 rules in conformance format per Garry Tan v0.10.
- **2026-04-15** | v2.1.0 — added AP-8 (name-inflection guard) absorbed from Daniyar/Даниярбек confabulation 2026-04-15.
- **2026-04-15** | v2.2.0 — Wave 3: added AP-5 (empty file gate), AP-6 (MCP client target), AP-7 (immediate MEMORY write). Absorbed LESSON-062, 063, 081.
- **2026-04-15** | v2.3.0 — Wave 4: added AP-9 (escalation-only LAW-010), AP-10 (pre-send fact-check LAW-016).
- **2026-04-16** | v2.4.0 — added rigid HANDOFF schema + compiled-truth template per [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]] Phase P3.
- **2026-04-17** | v2.5.0 — Session 37: added Brain-aware invocation (gstack v0.18.0.0 adoption). Slash-command routing changes must search gbrain for prior routing incidents (LESSON-087 ban, dedup, poller state) before editing, and save outcome as timeline entry. No new LESSON (RULE ZERO).
- **2026-04-23** | v2.6.0 — Session 70: added AP-11 (sanitize tags before file paths). Root cause of intermittent Telegram message loss — `parse_caption` stored raw `/`-prefixed command tokens as tags, which embedded a literal `/` in filenames and crashed `write_text` with `FileNotFoundError`. Fixed `telegram_poll.py:212` to run each tag through existing `slugify()` before join. Regression + E2E tests pass 6/6 cases including the 13:20/13:21 crash payload. General rule codified: all user-derived path components must pass a sanitizer boundary, not rely on mkdir rescue at write time. No new LESSON (RULE ZERO).
- **2026-04-26** | v2.6.0 → v2.6.1 — Session 75 Codex Telegram staleness trace: current poller was alive and AP-11 production fix already present, but the regression test had rotted on Mac import paths. Absorbed AP-12. Patched `tools/test_telegram_poll.py` to import repo-local `telegram_poll` with precedence over legacy runtime paths, stub `dotenv` and `command_center`, and assert `/audit deep dive` writes exactly one direct child file under `PENDING` (not just a safe basename). VPS test initially failed by importing stale `/root/nous-agaas/tools/telegram_poll.py`; backflowed safe wiki copy there. `python3 -m unittest tools/test_telegram_poll.py` passes 8/8. No new LESSON (RULE ZERO).
- **2026-04-26** | v2.6.1 → v2.7.0 — Telegram control-plane audit: token preflight safe (`~/.claude` bot id 8613073660 != Air bot id 8799328101), poller launchd loaded exit 0, Mac/Air poller tests 8/8, but `/health` used a VPS-era helper, macOS APFS disk math created a false red, and `/help` had stale `/ask` copy. Absorbed AP-13. Added vault-managed `tools/factory_health.py`, changed Air health defaults to OpenClaw Docker + native LiteLLM + existing local disk mounts with APFS free-GB threshold, and updated `/help` to reflect Grok CEO router, `/ask-direct`, and `/trace`. No new LESSON (RULE ZERO).
- **2026-04-27** | v2.7.0 → v2.8.0 — Codex/OpenAI 5.5 Telegram bridge audit. `/ask` through Air `command_center.handle()` returned `TELEGRAM_OPENCLAW_OK` via OpenClaw `grok-ceo`; Mac Codex CLI returned `CODEX_MAC_OK` with `gpt-5.5`; Air default Codex auth failed with `refresh_token_reused`; isolated `~/.codex-api` API fallback returned `CODEX_AIR_API_OK`. Absorbed AP-14 and added `/codex` route with subscription-first/API-fallback execution, daily call counter, and explicit footer when fallback is used. No new LESSON (RULE ZERO).
- **2026-04-27** | v2.8.0 → v2.8.1 — Continuity tightening after user directive "work from here, Claude Code, or Telegram without losing anything." Patched `/codex` preamble to read MEMORY.md top-block in addition to newest HANDOFF-AUTO and doctrine skills, so Telegram-spawned Codex starts from the same substrate as `/code`. Updated root Mac shims (`AGENTS.md`, `CLAUDE.md`) and `architecture-quickref` to name `/codex` explicitly. No new LESSON (RULE ZERO).
- **2026-04-27** | v2.8.1 → v2.9.0 — Implemented operator-boundary quiet-hours gate in `tools/command_center.py`. Non-urgent `/ask`, implicit `/ask`, `/ask-direct`, `/code`, and `/codex` during `00:30-08:00 Asia/Almaty` are queued to `pages/personal/boundary-queue-YYYY-MM-DD.md` and do not spawn token-spending work; urgent/override keywords bypass. Added `tools/test_operator_boundaries.py` and included it in the Blacksmith portable suite. No new LESSON (RULE ZERO).
- **2026-04-28** | v2.9.0 → v2.9.1 — Morning-review audit absorbed AP-16. Root cause: AP-14 froze the first working Air Codex app-bundle path into `/codex`, and the daily guard observed tokens but capped only calls. Patched `tools/command_center.py` to resolve Codex via `CODEX_CMD`/known paths/PATH and to block before subprocess spawn once `CODEX_DAILY_CAP_TOKENS` is reached. Added resolver + token-cap tests to `tools/test_operator_boundaries.py`. gbrain-timeline-ok: pages/skills/command-center/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v2.9.1 -> v2.9.2 — Morning Telegram audit absorbed AP-17. Root cause: `/code` reached the current Claude binary after the path fix, but print mode failed with 401 while `claude auth status` still claimed logged in; the credential file had expired on 2026-04-16. Patched `command_center.py` to return an exact Air reauth command on Claude auth failures and codified print-mode smoke as the only valid `/code` auth proof. gbrain-timeline-ok: pages/skills/command-center/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v2.9.2 -> v2.9.3 — Session 83 top-CTO workflow audit absorbed AP-18. `/code` and `/codex` already read continuity substrate, but their injected preambles did not force the coordination handshake at spawn time. Patched both preambles to include `session-coordination`, `session_register.sh`, `session_scan.sh`, `git commit -o <paths>`, and `session_close.sh`; added `SpawnedAgentPreambleTests` in `tools/test_operator_boundaries.py` so the boundary cannot drift silently. gbrain-timeline-ok: pages/skills/command-center/skill. No new LESSON (RULE ZERO).
- **2026-04-29** | v2.9.3 -> v2.9.4 — Session 83 Lane B audit absorbed AP-19. Prompt-level handshake was insufficient: `/code` and `/codex` sessions must be visible in the registry by construction. Added mechanical register/close wrappers around `_run_claude_code()` and `_run_codex()`, inject the returned outer `session_id` into child prompts, and test both routes. gbrain-timeline-ok: pages/skills/command-center/skill. No new LESSON (RULE ZERO).

## See also

- [[LESSON-087-never-use-telegram-mcp-in-claude-code]]
- [[LESSON-086-polling-dedup-save-state-before-slow-handler]]
- [[LESSON-098-claude-code-env-var-vs-oauth]]
- [[LESSON-062-ingest-burns-anthropic-on-empty-files]]
- [[LESSON-063-mcp-tools-targets-claude-desktop-not-claude-code]]
- [[LESSON-081-mid-session-facts-lost-on-context-compression]]
- [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]]
- [[nous-gpu]] — new RTX 5070 compute host (2026-04-20); host-health monitoring scope candidate
- `skills/_gbrain/RESOLVER.md` — dispatcher that routes to this skill


## Timeline

- **2026-05-22** | v2.12.28 -> v2.12.29 — Added AP-54 after Codex pasted the English body from a stale EN/KO KEONA draft despite memory requiring Korean + Russian. Fixed durable artifact to `KEONA_Lim_Concise_Reply_2026-05-22_KO_RU.md`, updated project/task-result references, and set the rule that KEONA counterparty copy-paste replies must verify memory/vault language pair before output. No new LESSON (RULE ZERO).
- **2026-05-22** | v2.12.27 -> v2.12.28 — Added AP-53 after the KEONA Gmail attachment package leaked English operator text into the Russian-speaking Satory group. Fix: `tools/telegram_topic_send.py` now has a Cyrillic guard and certifi-backed TLS, `tools/keona_telegram_package.py` pins KEONA packages to chat `-1002064137259` topic `1357`, requires Russian-facing copy, and sends every provided attachment. Live repair deleted mixed-language messages `1845/1846/1847` and reposted Russian package `1848/1849/1850`; UI readback showed title `Keon-A` and both PDFs. No new LESSON (RULE ZERO).
- **2026-05-20** | v2.12.26 -> v2.12.27 — Added AP-52 after Satory group still saw raw Codex cap / mandatory-route stop text. Root cause was Air `command_center.py` split-brain plus a capped mandatory-Codex branch that treated external group proof as a hard stop. Fix: group replies now use local Satory API proof first, capped mandatory Codex falls back to grok-ceo with a Russian/no-internals prompt, `_tg_send()` sanitizes banned internal markers, and deploy proof requires hash parity across Air root/tools/wiki plus poller restart. Regression covered in `tools/test_operator_boundaries.py`. No new LESSON (RULE ZERO).
- **2026-05-20** | v2.12.25 -> v2.12.26 — Added AP-51 after Satory group event-flow questions either hallucinated stale `wg-satory` context via routine OpenClaw or exposed raw `/codex token cap reached` text while the live events watcher later proved intake had resumed. Fix: Satory event-intake visibility asks now answer locally from the camera freshness API before model routing; mandatory Codex proof routes precheck `codex_usage.json` call/token caps and return a controlled blocked message instead of invoking capped Codex or falling back to cheap workers. Regression covered in `tools/test_operator_boundaries.py`. No new LESSON (RULE ZERO).
- **2026-05-20** | v2.12.24 -> v2.12.25 — Added AP-50 and implemented subscription-first `/ask --tier ceo` plus cheap-only `/ask --tier cheap`. CEO tier is Madi-DM only and calls Codex GPT-5.5 subscription first with no paid API council by default; cheap tier calls local MLX first then DeepSeek and never calls Codex/Grok/Opus. Regression covered in `tools/test_operator_boundaries.py`. No new LESSON (RULE ZERO).
- **2026-05-19** | v2.12.23 -> v2.12.24 — Added AP-49 after live Air logs showed post-/ask inbox classification reading `/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/inbox/...` instead of the active Air wiki. Fix: command_center pins telegram_ingest_persist mutable VAULT/INBOX/TASKS/MERCURY paths to `NOUS_WIKI` before classification side effects. No new LESSON (RULE ZERO).
- **2026-05-19** | v2.12.22 -> v2.12.23 — Added AP-48 after live Satory group `msg_id=1772` routed through `/ask` -> ChatGPT/Codex and replied in Telegram but left no `pages/task-results` receipt. Fix: direct `/codex`, `/code`, and `/ask` Codex-escalation paths now always write redacted task-result receipts before Telegram truncation/send. No new LESSON (RULE ZERO).
- **2026-05-19** | v2.12.21 -> v2.12.22 — Added AP-47 after live Telegram proof showed Asyl's credential ask generated a safe answer in LangSmith but no Telegram `_tg_send` delivery and no owner-DM path. Fix: credential-shaped group messages bypass OpenClaw/Codex, send one safe group owner-handoff confirmation, and DM Madi the raw owner-only context before redaction/model routing. gbrain-timeline-ok. No new LESSON (RULE ZERO).
- **2026-05-19** | v2.12.20 -> v2.12.21 — Added AP-46 after live Satory group `msg_id=1771` (`Send it to me and i will forward @nousAGaaSbot`) routed as a trailing bot mention and wasted an OpenClaw turn on meta-chatter; safe replay returned an internal Claude-Code task block. Fix: meta-forwarding mentions are observe-only, preserving real trailing bot requests. No new LESSON (RULE ZERO).
- **2026-05-19** | v2.12.19 -> v2.12.20 — Added AP-45 after Madi's live Satory group `msg_id=1766` (`@nousAGaaSbot`) + `msg_id=1767` (production ERAP/APK config) were captured but not routed. Fix: forward split-mention latch routes the next same-sender payload within 120s, production-config fields count as Satory domain markers, and `test:`/`prod:` secret-looking values are redacted before inbox write and before model route. Live repair: redacted `1767` inbox note and sent compact group reply `msg_id=1768`. gbrain-timeline-ok. OpenBrain: cc1f01ab-bb1a-4336-aca8-f17f9c91c7ba. No new LESSON (RULE ZERO).
- **2026-05-19** | v2.12.18 -> v2.12.19 — Extended AP-44 after live Air inspection showed `raw/pending/telegram-2026-05-19_160203-photo.jpg` still pending and no `com.nous.ingest-pending` service on Air. Fix: full-chat group media captures now get an immediate retrievable inbox note with raw path and image preview; the visible Telegram ACK remains reaction-only. gbrain-timeline-ok. No new LESSON (RULE ZERO).
- **2026-05-19** | v2.12.17 -> v2.12.18 — Added AP-44 after live Satory group `msg_id=1764` from `@aliakbar_asylbek` was captured but not routed because it lacked a bot mention, while a following photo produced noisy `[captured into vault]` text. Fix: deterministic Satory operator action gate for unaddressed full-chat messages, group capture/progress reactions, and group footer stripping for Codex/OpenClaw internals. Regression covers Asyl ERAP login request, photo ACK reaction-only behavior, and group Codex route footer hiding. gbrain-timeline-ok. No new LESSON (RULE ZERO).
- **2026-05-19** | v2.12.16 -> v2.12.17 — Added AP-43 after the final daily proof pack found a second Telegram false-red path: a transient-only one-shot poller cycle returned `1`, then launchd retained stale `last_exit=1` while the next poller process was already running. Fix: transient-only getUpdates cycles return `0`, 409 stays hard RED, and daily launchd probes treat a numeric running PID as live even with stale last_exit. No new LESSON (RULE ZERO).
- **2026-05-19** | v2.12.15 -> v2.12.16 — Added AP-42 after the daily proof pack found Telegram health flapping red because `telegram_poll.py` exited `1` on the first transient `getUpdates` read timeout. Fix: transient network errors retry inside the same 50-second cycle, full-cycle transient failure stays nonzero, and `409 Conflict` remains hard RED for same-token dual-poller risk. No new LESSON (RULE ZERO).
- **2026-05-18** | v2.12.14 -> v2.12.15 — Tightened AP-39 after OpenBrain/model summaries normalized a camera credential as `admin/<password>`, which the first Telegram redactor did not match. `telegram_ingest_persist.py` now redacts slash-form admin credentials; regression covers the exact normalized shape without using a real secret. No new LESSON (RULE ZERO).
- **2026-05-18** | v2.12.13 -> v2.12.14 — Extended AP-37 detector coverage from "АПК фиксирует" to Satory VAR/radar camera access questions after group context clarified LU100 can be a landmark/switch context, not necessarily the target camera. Route stays Codex/GPT-5.5 first for evidence-backed live proof; dashboard-domain topology rule lives in `satory-dashboard` AP-15. No new LESSON (RULE ZERO).
- **2026-05-18** | v2.12.12 -> v2.12.13 — Finalized AP-41 after the LU100 group UX still failed under the fuller transcript: Denis context existed, but visible group replies must greet the current sender or stay neutral. Added sender-context salutation neutralization in `command_center.py`, strengthened group LLM prompt injection, and added a manual `tg_send.sh` group named-addressee guard. No new LESSON (RULE ZERO).
- **2026-05-18** | v2.12.11 -> v2.12.12 — Corrected AP-41 after Madi supplied the fuller LU100 transcript: Denis had requested the endpoint and provided LU100 details, so the previous "wrong addressee" verdict overfit to partial bot-ingested evidence. Removed the overbroad named-salutation block while preserving trailing `@nousAGaaSbot` routing and sender-provenance injection. No new LESSON (RULE ZERO).
- **2026-05-18** | v2.12.10 -> v2.12.11 — Superseded by v2.12.12. Initially added AP-41 after the LU100 group reply appeared to use `Денис, ...` from partial inbox evidence; the durable part was trailing `@nousAGaaSbot` routing and sender-provenance injection, while the named-salutation block was later removed as overbroad. No new LESSON (RULE ZERO).
- **2026-05-18** | v2.12.9 -> v2.12.10 — Added AP-40 after live Satory group `msg_id=1736` (`@Riza1207 Nazel`) was wrongly routed to `/ask Nazel`. Root cause: `_strip_factory_address()` treated every leading `@username` as a factory address. Fix: only `@nousAGaaSbot` is an AI mention; other human mentions are observe-only full-chat memory. Regression covers both human mention no-execute and bot mention execute. No new LESSON (RULE ZERO).
- **2026-05-18** | v2.12.8 -> v2.12.9 — Added AP-39 after LU100 group full-chat capture persisted a Telegram-posted APK admin password into inbox history. Root cause: `telegram_ingest_persist.py` wrote raw text before secret scrub; GitHub accepted the bad commit while the VPS pre-receive hook correctly rejected it. Fix: inbox writes now call `redact_sensitive_text()` before title/body creation, regression covers `10.145.1.2 admin <password>`, and branch history was rewritten to redacted head `eadf4ebf`. No new LESSON (RULE ZERO).
- **2026-05-18** | v2.12.7 -> v2.12.8 — Added AP-38 after Madi required the second brain to put GPT/Codex at the top. Fix: natural Telegram top-tier/second-brain language routes to `/codex`; `/ask` policy escalates explicit top-tier/customer-transformation requests to Codex; Codex preamble tells the spawned lane to delegate durable work to OpenClaw/factory only when needed and to write destination-first replies. No new LESSON (RULE ZERO).
- **2026-05-18** | v2.12.6 -> v2.12.7 — Added AP-37 after `tg_1655` produced a bad Asyl/APK answer. Root cause was route + context: short external Satory APK proof query fell through to routine OpenClaw and previously did not match Satory dashboard context. Fix: deterministic policy escalates Satory APK/ERAP external proof questions to `/codex` GPT-5.5 subscription; regression covers the exact Asyl sentence at policy and command-center layers. No new LESSON (RULE ZERO).
- **2026-05-18** | v2.12.5 -> v2.12.6 — Added AP-36 after the strict Telegram/OpenClaw truth gate caught Air `command_center.py` split-brain: `tools/command_center.py` and wiki copy had the `_tg_send sent OK` proof log, but runtime-root `/Users/madia/nous-agaas/command_center.py` still had the stale block. Recovery mirrored the router shadow, `python3 -m py_compile` passed on all three Air copies, and SHA-256 hashes matched. No new LESSON (RULE ZERO).
- **2026-05-17** | v2.12.4 -> v2.12.5 — Added AP-35 and patched `tools/run_task.py` after live Telegram `/ask` proof `E2E-CODEX-20260517101432` showed inbound/reply transport working but `openclaw-agent:grok-ceo` failed with JSON parse `char 0` while the OpenClaw session JSONL contained the assistant response. Root cause: async-await recovery only handled parsed JSON with empty payloads, not exit-0 empty stdout. Fix: recover session JSONL text before raising parse errors. Regression: `python3 tools/test_run_task_resilient.py` -> 7 tests OK; Telegram harness/operator gates still green locally. No new LESSON (RULE ZERO).
- **2026-05-17** | v2.12.3 -> v2.12.4 — Tightened AP-34 after the first live timeout run of `tools/telegram_ask_e2e_probe.py` correctly found no inbound nonce but the initial parser still matched an old `/ask handled` line. Fix: classify `/ask handled` and reply-send evidence only after the nonce-bearing inbound message is seen and bound to `msg_id`. Regression updated so a stale `/ask handled` line with no nonce remains YELLOW with `ask_handled_logged=false`. No new LESSON (RULE ZERO).
- **2026-05-17** | v2.12.2 -> v2.12.3 — Added AP-34 and `tools/telegram_ask_e2e_probe.py` after the factory Telegram/OpenClaw/Hermes/LangGraph audit correctly left `/ask` E2E unproven while daemon probes were green. Root cause: `factory_no_drift_probe.sh` checks poller liveness, not an operator-facing inbound `/ask` round trip, and `_tg_send()` did not log successful `sendMessage` ids, so reply delivery could not be proven from logs. Fix: `_tg_send()` now logs `bot_msg_id`/`reply_to` on success; the new probe never calls `getUpdates`, optionally prompts Madi through send-only `tg_send.sh`, then watches Air logs for nonce, `msg_id`, `correlation_id=tg_<msg_id>`, `/ask handled`, and reply send success. Regression: `python3 -m py_compile tools/telegram_ask_e2e_probe.py tools/command_center.py` and `python3 -m pytest tools/tests/test_telegram_ask_e2e_probe.py -q` -> 3 passed. No new LESSON (RULE ZERO).
- **2026-05-16** | v2.12.1 -> v2.12.2 — First live Air run of the new truth gate exposed a false RED: Air wiki uses `origin`, not Mac's `vps` remote alias, so `git ls-remote vps` failed while production checks were green. Added AP-33 and changed the gate to read VPS bare through `git --git-dir=/root/nous-agaas/obsidian-wiki.git rev-parse refs/heads/main`. No new LESSON (RULE ZERO).
- **2026-05-15** | v2.12.0 -> v2.12.1 — Added AP-32 and `tools/telegram_openclaw_factory_truth_gate.py` after repeated "not done" reports mixed live Telegram/OpenClaw production health with Air runtime root release dirt. New gate verifies wiki HEAD parity, canonical wiki cleanliness, Air command-center hash parity across runtime root/tools/wiki, launchd poller path, poller import order, and `factory_no_drift_probe`; runtime-root dirt is YELLOW `release_dirty` unless strict release mode is requested. Regression: `python3 -m pytest tools/tests/test_telegram_openclaw_factory_truth_gate.py -q` -> `10 passed`. No new LESSON (RULE ZERO).
- **2026-05-15** | v2.11.9 -> v2.12.0 — Runtime self-audit found LangGraph policy present and `langgraph==1.2.0`, but the direct root import surface was stale: `tools/command_center.py` had `_codex_daily_budget_ok`, LangGraph route handling, long-work Goal/Todoist conversion, and OpenClaw identity fast-path while root `command_center.py` did not. This made the operator gate fail `61 passed, 5 failed`. Mirrored `tools/command_center.py` to root `command_center.py`; combined Telegram/operator gate then exposed a second import-order root cause where `telegram_poll.py` reused a preloaded root `command_center` from `sys.modules`. Added an explicit tools-module alias import for that case, added AP-31, and reran the gates. Focused orchestration: `66 passed, 3 warnings`; combined Telegram/operator: `43 passed, 2 warnings`. gbrain-timeline-deferred: MCP/CLI gbrain write unavailable from this sandbox; local skill evidence recorded here. No new LESSON (RULE ZERO).
- **2026-05-14** | v2.11.8 → v2.11.9 — Added AP-30 after Madi rejected slash-command UX and asked for the factory to feel like a natural god-level second brain. Root cause: command-center exposed internal slash APIs as the human surface. Fix: `telegram_poll.py` now maps private plain language and addressed group text (`Фабрика, ...`, `Nous, ...`, `@nousAGaaSbot ...`, `AI: ...`) to internal `/status`, `/goal`, `/codex`, `/code`, or `/ask`; unaddressed group chatter remains inbox context only. Regression: `tools/test_telegram_poll.py` now covers natural DM status/goal/Codex, addressed group ask/status, and non-addressed group no-execute. No new LESSON (RULE ZERO).
- **2026-05-14** | v2.11.7 → v2.11.8 — Fixed the Telegram/operator regression gate after live verification showed `tools/test_telegram_poll.py` and `tools/test_operator_boundaries.py` each passed alone but failed together. Root cause: the poller unit test leaves a fake `command_center` stub in `sys.modules`; the operator suite then imports the fake module and reports false missing runtime helpers. Added AP-29 and a pre-import stub eviction guard in `tools/test_operator_boundaries.py`; combined gate now must return `34 passed`. Also corrected `/codex` wording to subscription-only/no hidden API fallback, matching `tools/command_center.py`. No new LESSON (RULE ZERO).
- **2026-05-14** | v2.11.6 → v2.11.7 — Added AP-28 and router guard after task `tg_1451` was sent to OpenClaw for shell/SSH verification. Root cause: exact-command verification was routed to text-only `/ask`, so the OpenClaw sandbox truthfully blocked on missing Air SSH. Fix: narrow `_requires_codex_verification_route()` auto-escalates `VERIFY:`/`Run exact commands` payloads with shell markers to `/codex` before `_run_openclaw`; regression proves Codex called and OpenClaw not called. No new LESSON (RULE ZERO).
- **2026-05-14** | v2.11.5 → v2.11.6 — Added AP-27 after Madi correctly separated main `@nousAGaaSbot` from the separate APK camera-status bot. Root cause of the first-try miss: the audit grouped two Telegram bot identities together and did not require live proof of normal group persistence plus command rendering plus subsystem naming before user-visible closeout. No new LESSON (RULE ZERO).
- **2026-05-14** | v2.11.4 → v2.11.5 — Follow-up live smoke showed the v2.11.4 `/status` fix was present in `tools/command_center.py` but not live because Air runtime root had a stale `command_center.py` shadow file and `telegram_poll.py` imported runtime root first. Fixed poller import precedence to prefer its tracked `tools/` directory, added regression assertion, and deployed the router to both tools and root runtime paths for compatibility. No new LESSON (RULE ZERO).
- **2026-05-14** | v2.11.3 → v2.11.4 — Satory group live proof showed full-chat ingestion working (`1715-unknown.md`) and `/status` routing working, but `/status` emitted `memory error: sysctl not found` under launchd plus stale "VPS health" wording. Root cause: bare macOS tools under launchd's minimal PATH. Fix: resolve `docker`/`df`/`sysctl`/`vm_stat`/`free` through `shutil.which()` plus absolute fallbacks, rename wait text to "factory health", and add regression tests. No new LESSON (RULE ZERO).
- **2026-05-14** | v2.11.2 → v2.11.3 — Madi rejected command-only group use and required full-chat team observability. Root cause: group allowlisting alone still misses normal group chatter when Telegram privacy mode is on or when the poller intentionally ignores non-command text. Fix: added Satory-only full-chat observe mode via `TELEGRAM_FULL_CHAT_CHAT_IDS` / `TELEGRAM_GROUP_OBSERVE_CHAT_IDS`; group text is persisted to inbox with sender provenance, while execution remains gated to commands or explicit `AI:`. No new LESSON (RULE ZERO).
- **2026-05-14** | v2.11.1 → v2.11.2 — Added explicit Satory group support to `telegram_poll.py`: multi-chat allowlist (`TELEGRAM_ALLOWED_CHAT_IDS` / `TELEGRAM_GROUP_CHAT_ID`), `/command@bot` normalization, `AI:` group request routing, and safe ignore for normal group chatter. Root cause was a private-DM-only chat gate. No new LESSON (RULE ZERO).
- **2026-05-11** | v2.11.0 → v2.11.1 — `/goal` now visibly starts/schedules its durable OpenClaw runner: command handler calls `_kick_goal_cycle()` after GOAL/Todoist creation, reply includes `Runner: ...` or `Runner not started: ...`, and the canonical `tools/launchd/com.nous.goal-cycle.plist` is tracked. Root cause was state creation without runner kick plus Air-local launchd drift. No new LESSON (RULE ZERO).
- **2026-05-01** | v2.10.0 → v2.11.0 — Shipped Phase 2.5 + Gap 3 of telegram-ingest-pipeline. **Phase 2.5:** `tools/intent_classifier.py` (~150 lines) shared classifier via direct LiteLLM `deepseek-v4-flash` call (~$0.0001/msg, <2s latency, never raises). Wired into `command_center.handle()` `/ask` path via new `_classify_inbox_post_ask(msg_id, query)` helper that appends `📥 Saved as <intent> in [[<slug>]]<side-effects>` footer between cost-footer and truncate check. Kill-switch `TELEGRAM_INGEST_CLASSIFY=0|off|false`. Smoke 5/5 intents @ 0.95 conf. **Gap 3:** `tools/inbox_walker.py` (~190 lines) walks `pages/inbox/<last-N-days>/*-unknown.md` hourly via launchd `com.nous.inbox-walker` (`:15` minute, offset from auto-checkpoint), classifies via shared classifier, applies side-effects through `telegram_ingest_persist.classify()`. Idempotent, capped at 20/run, exit-0 always (no cron retry loops). Smoke 3/3 elevated (task→TASKS.md, fact→mercury fact-00399, decision→pages/decisions/), idempotent re-run found 0 candidates. Real backlog elevation: 2026-04-30 8887183 + 9998856 → note (0.95, 0.85). Surfaced + fixed AP-21 (LiteLLM null content on Madi's real 1123). Absorbed AP-20 (footer-not-second-message) + AP-21 (null-content graceful-degrade). gbrain-timeline-ok: pages/skills/command-center/skill. Plan: PLAN-2026-05-01-phase-2.5-and-gap-3.md. No new LESSON (RULE ZERO).
- **2026-04-30** | v2.9.4 → v2.10.0 — Shipped Phase 2 of telegram-ingest-pipeline (charter Gap 2). `tools/telegram_ingest_persist.py` (313 lines) persists every plain-text inbound to `pages/inbox/YYYY-MM-DD/<msg-id>-unknown.md` BEFORE the existing /ask route. Wired into telegram_poll.py line 232 elif-block via subprocess (10s timeout, kill-switched via TELEGRAM_INGEST_PERSIST env, graceful-degrade try/except so /ask stays reliable). LIVE end-to-end verified: real msg_id=1123 from Madi at 2026-04-30 22:14:36 KZT captured in inbox (2665 bytes, full FM). 4-intent classifier subcommand (note/task/fact/decision/question) tested 4/4: task → TASKS.md append, fact → mercury/facts.jsonl append (≥0.8 confidence gate), decision → pages/decisions/YYYY-MM-DD/, note → inbox-only. Phase 2.5 (OpenClaw factory in-prompt classifier feedback loop) deferred. Plan: PLAN-2026-04-30-telegram-ingest-pipeline.md. gbrain-timeline-ok: pages/skills/command-center/skill. No new LESSON (RULE ZERO).
