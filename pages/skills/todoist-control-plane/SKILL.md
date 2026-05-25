---
type: skill
id: todoist-control-plane
title: "todoist-control-plane v1.8.9"
tier: 2
version: 1.8.9
status: active
date: 2026-05-13
last_updated: 2026-05-21
tags: [todoist, control-plane, tasks, sections, owners, priorities, labels]
---

# todoist-control-plane v1.8.9

Use this skill whenever Madi asks for Satory Todoist to be "god level", "all tasks assigned", "no no-section", "owner/department/priority/hashtags", "Notion/Todoist sync", "control-plane sync", or any Satory factory hygiene audit.

## Scope Boundary

The operational control plane is Satory-only unless Madi explicitly names another project in the same request.

- Allowed Todoist project: `Фабрика Satory ВКО` (`6gJ5j8PRVVCWpgCq`).
- Out of scope by default: `Личное`, `Мои задачи`, `Семья`, `Дом / стройка`, `Korea Trade`, `Satory AI`, and every other personal/non-Satory project.
- In a Satory/Nous lane, do not ask Madi to approve personal-project deletions, archives, merges, or cleanup greenlights even as recommendations. If a broad audit finds personal noise, record it as out-of-scope context only and stop at the Satory actionable slice.
- `tools/todoist_control_plane_audit.py`, `tools/todoist_control_plane_export.py`, `tools/todoist_russianize.py`, and `tools/human_owner_reminder.py` must filter the live Sync payload to the allowed project before building mutation/export/reminder plans.
- Todoist labels are global. Do not rename global label objects as part of Satory cleanup; update labels on Satory tasks only.
- If an older agent already mutated non-Satory content, use `tools/todoist_scope_revert.py` first in dry-run, then apply only receipt-backed rows whose `before` values exist and whose live project is not Satory. The post-apply dry-run must be idempotent: already-reverted rows must be skipped as `already reverted`, not reported as still pending.
- If non-Satory tasks still contain factory metadata labels (`исполнитель:`, `отдел:`, `проект:`, `owner:`, `department:`, `project:`), strip those labels from the non-Satory task instead of renaming global label objects. Global labels are shared with Satory; renaming them can break the allowed project.
- For task rollback/removal, use Todoist Sync API `item_update`, not REST `POST /tasks/{id}`. REST can return success while leaving `content`, `description`, or `labels` unchanged on some items.
- Todoist Sync API can return HTTP 429/502/503/504 during bulk cleanup. Respect `Retry-After` where present and retry transient read/write calls with backoff. If a write chunk still fails after retries, return row-level errors instead of crashing with a traceback.
- Bulk task cleanup must batch Todoist Sync API `item_update` commands. Do not send one Sync request per task when the plan contains many task rows.
- The rollback planner must strip factory metadata labels from the expected target even after the live task is already clean. Otherwise the post-cleanup dry-run can falsely ask to add factory labels back to personal tasks.
- When multiple receipts exist for the same non-Satory task field, resolve the target once per task using the earliest recorded `before` value, then compare current state. Do not skip an early matching receipt and let a later receipt flip the task back.

## Operating Rule

Todoist is an execution control plane, not a scratchpad. A task is not operationally clean unless it has:

- a valid project
- a valid section for every root task
- owner or assignee information
- a department label
- at least one topical/project label
- non-default priority

Subtasks may inherit section context from their parent, but root tasks may not remain sectionless. "No section" is a red finding.

## Russian-Language Rule

Todoist is read by the Satory/team operators. All human-facing Todoist text must be Russian by default:

- project names, section names, task titles, task descriptions, status labels, owner labels, department labels, register headings, and factory instructions must be Russian;
- preserve product/company/model names where the Latin form is the real name, for example Todoist, Notion, Obsidian, gbrain, OpenBrain, OpenClaw, LangSmith, GitHub, KEONA, SPECTRA, Satory, BDL, NCANode, NVIDIA, Tesla;
- preserve IDs, URLs, dates, money amounts, source slugs, proof paths, and API/model identifiers exactly;
- do not add fake descriptions just to remove the yellow `no_description_or_note` count;
- when translating existing Todoist content, write a rollback/audit artifact that stores `before` and `after` for every mutation.

Use `tools/todoist_russianize.py` for Satory language cleanup. Default mode is dry-run; live apply requires `--apply`. After applying, rerun the control-plane sync so Notion, Obsidian registers, gbrain/OpenBrain projection, GitHub, and Telegram receipts see the same Russian-facing state.

If the local LiteLLM OpenAI-compatible route returns `No connected db` during Russianization, do not leave the task-content queue as a permanent factory residual. Use the direct OpenRouter route configured in `tools/todoist_russianize.py` (`deepseek/deepseek-v4-flash` by default) with provider-specific API-key selection and the certifi/curl fallback. This lane is for translation only: preserve facts, IDs, URLs, owners, dates, and product names; never invent missing descriptions.

Todoist comments are part of the operator surface. `tools/todoist_russianize.py` must audit and translate active-task comments/notes too, using the same dry-run/apply/rollback artifact flow. Preserve URLs, source paths, file names, and evidence slugs. Real English instructions inside comments must become Russian; evidence paths may stay Latin.

The Russianization audit must not treat proof-library evidence as English operator text. Ignore URLs, absolute paths, Obsidian `pages/...` paths, Notion links, source/audit/goal/proof slugs, file names, model/API identifiers, and real product/company names when computing the remaining English exposure. If a dry-run proposes only punctuation changes on an already-Russian Todoist comment, skip it; Todoist may reject punctuation-only comment rewrites with HTTP 400, and that is not a language failure.

Never apply a Russianization row that changes, truncates, or drops an evidence reference. Obsidian paths, source slugs, proof filenames, audit filenames, and task-result IDs are identity links, not prose. If the model translates surrounding text but mutates one of those references, skip that row and record it as a safe skip; rerun with a better model or manually rewrite only the prose around the untouched reference.

Todoist may reject updates to comments authored by another user with HTTP 400. Do not add a second "Russian version" comment as a fallback. If a comment is immutable, skip that row and record `update_note_immutable_skipped` in the audit. Human operational comments that are already mostly Russian but include product names or a few Latin words (`Keon-A`, `NOUS`, `SPECTRA`, `Maru systems`) must not be rewritten or echoed; they must be interpreted as task/action signals by the comment/factory pipeline.

## Russian Documentation Sync Gate

Any Todoist/Notion/control-plane documentation meant for people or factory operators must be Russian-facing before the cycle can be called synced. This includes:

- `pages/systems/todoist-control-plane-register.md`
- `pages/systems/todoist-context-enrichment-queue.md`
- `pages/systems/control-plane-sync-status.md`
- Notion mirror summaries and task bodies created from Todoist/Obsidian state
- Telegram receipts that summarize Todoist/Notion/control-plane status

Run this gate after exporting registers and before saying Notion/Obsidian/gbrain/OpenBrain/GStack are aligned:

```bash
python3 tools/check_russian_control_plane_docs.py --wiki . --json
```

The gate checks generated operator headings/instructions. It does not fake-translate arbitrary task titles. If task titles/descriptions remain English, create or continue a Russian factory translation slice with exact Todoist IDs and source-preservation rules.

## Procedure

1. Run the Satory-only read-only audit:
   ```bash
   python3 tools/todoist_control_plane_audit.py --env-file ~/nous-agaas/.env --json
   ```
2. Review `audit.risk_counts` before mutating anything.
3. Only when the requested scope is explicit and the dry-run plan is deterministic, apply:
   ```bash
   python3 tools/todoist_control_plane_audit.py --env-file ~/nous-agaas/.env --apply --json
   ```
4. Rerun the read-only audit. The hard-gate counts must be zero:
   - `missing_project`
   - `invalid_section`
   - `root_no_section`
   - `subtask_no_section_inherited`
   - `missing_owner`
   - `missing_department`
   - `missing_labels`
   - `default_priority`
5. Treat `no_description_or_note` as yellow, not red. Do not add generic comments just to make the number zero. Attach real files/comments only when there is a source artifact that belongs to the task.
6. Save the evidence into `pages/audits/` and update the Notion mirror when the user asks for cross-system sync.

## Source-Backed Intake Rule

When Madi forwards a human update, PDF, offer, or meeting note that contains operational work, do not leave it as chat history. Convert it into the execution spine:

1. Create or update the Obsidian source/status page with the exact source text, extracted facts, owner, department, status, and evidence links.
2. Create or update a Notion task in the correct project data source with project, department, priority, status, due date, source URL, and a body that names the human owner even when Notion person assignment is unavailable.
3. Create or update the Todoist task in the correct project and section. The task must include:
   - `исполнитель:<owner>` or `owner:<owner>`
   - `отдел:<department>`
   - `проект:<project>`
   - a topical/subproject label
   - non-default priority
   - a real description or source-backed comment
4. Rerun `todoist_control_plane_audit.py --json`. If `plan` is non-empty, apply only deterministic repairs and rerun until `plan` is empty or the remaining change requires human judgment.
5. Do not add fake descriptions to clear `no_description_or_note`. Attach real artifacts only.

The simple operating model is: projects are ownership/area boundaries, sections are task state, labels are sparse cross-cutting facets, and filters are dashboards. Do not encode every source/person/topic as a permanent project or label. If an account-wide audit finds broad personal/project sprawl during a Satory lane, record the counts as context only and keep mutation inside the Satory project.

## Source-Finder Loop (the right answer for `needs_source_enrichment`)

When `needs_source_enrichment` accumulates, the answer is never to invent source documents. The route name IS doctrine: "without a source, do not invent description" (see [[AUDIT-satory-todoist-deep-2026-05-14-145214]]). The right substrate response is a mechanical source-finder, not a synthetic-source fabricator:

1. For each `needs_source_enrichment` task, query gbrain hybrid (`mcp__gbrain__query`) + QMD + Notion MCP with the task title.
2. If a hit scores ≥ 0.5: post a Todoist comment with the source URL/wikilink and flip `context_state` to `source_backed`.
3. If no hit: post a structured "needs human" comment naming what was searched (gbrain, QMD, Notion) and what's missing. Do not invent.
4. **Sub-tasks inherit the parent's source-backing.** If `parent_id` of a yellow task resolves to a `source_backed` parent (e.g., 8 site smoke tasks under "Все 9 страниц сайта работают"), the yellow status is a classifier defect, not a real source gap. Route → `ready_for_ai_factory_inherited` plus a Phase-3 runtime check (Playwright/curl).
5. Codify any classifier defect in `control-plane-sync` as a new AP; codify the doctrine for the substrate in this skill.

`tools/todoist_source_finder.py` implements this loop (shipped 2026-05-14 in session s1729, commit `651da179`). Idempotent via `Источник: source-finder` marker prefix; `--dry-run` and `--apply` modes; writes JSON receipt. Run from Air with `--env-file /Users/madia/nous-agaas/.env`. First live run posted 26/26 source-link comments with 0 errors (receipt: `pages/audits/RECEIPT-todoist-source-finder-2026-05-14.json`); deep-audit verification showed `contextless_tasks: 26 → 0`, `needs_source_enrichment` route eliminated entirely, `proof_counts.notion: 15 → 27`.

## Automation Gate

`tools/daily_0300_substrate_sync.py` must prefer the Satory Todoist control-plane audit over stale project-local checks. A daily green claim is false if Satory hard-gate counts are nonzero.

`tools/control_plane_sync_loop.py` must run the Russian documentation gate and include `russian_docs_gate` in the cycle status before writeback. A sync cycle is not green if operator-facing generated docs regress to English headings or English factory instructions.

`tools/check_russian_control_plane_docs.py` must never pin this skill to a stale exact version string. It should require the current `# todoist-control-plane vX.Y.Z` heading shape, not a specific historical version, otherwise a valid skill bump creates a false `blocked` control-plane cycle.

`tools/human_owner_reminder.py` must run daily for human-owned tasks. It may add Russian reminder comments for stale/overdue/blocked/P4 human tasks, because that is execution escalation, not fake context. It must not add source claims or generic descriptions. The per-day ledger prevents duplicate pings.

The human-owner Telegram digest must never present a Todoist task URL as `Proof`. Todoist is the task handle, not evidence. Each digest row must include a Russian `Проверка фабрики` line derived from the task description, comments, attachments, and source markers, separating `source_backed`, `human_checkable`, and `close_ready` states. Use the Todoist URL only as `Todoist:`. If no source/proof is found, say that clearly and route the next step to source-finder or a real evidence upload.

The same per-day ledger must suppress both Todoist comments and Telegram digests. A same-day rerun may not resend a Telegram digest for rows already marked in `sent[day][owner][task_id]`. Telegram output is built only from rows newly marked during the current run; if all rows were already pinged, the safe result is `telegram_sent=0`.

`tools/human_owner_reminder.py --apply --comment-sweep-only` must run hourly under `com.nous.todoist-comment-sweep`. This mode reads Todoist comments without sending daily reminder digests. It exists so humans can write one comment in Todoist and the factory can react without waiting until the 09:15 daily reminder pass.

The human-owner reminder loop must also read Todoist comments/notes on active human-owned tasks. A task comment is an execution signal, not decoration. When a recent non-AI comment says `готово`, `в работе`, `заблокировано`, or asks a question, the loop must add one Russian reply on that task explaining the next step: close the task, write the blocker/next owner/date, or add next step/deadline. When a recent comment starts with `AI:`, the loop must dispatch exactly one bounded OpenClaw/run_task factory slice, then write the Russian result or blocker back into that same Todoist task. Use a per-comment ledger (`comment_replies`) so each human comment is answered once and never spammed.

The comment classifier must ignore source/context/template comments. Do not reply to comments whose job is to preserve evidence, mirror Notion/Obsidian/GitHub/proof links, carry instruction templates such as `Если блокировано, написать блокер...`, or store checklist bullets such as `подготовить вопросы`. Those comments may contain words like `blocked`, `заблокировано`, or `вопросы`, but they are not human status updates. Only actual human replies, direct questions, or explicit `AI:` requests should receive an AI-factory reply.

The human-owner reminder job is not green until both the external actions and the writeback are green. If Todoist comments or Telegram digests are sent but the final git push races another writer, the job must retry pull/rebase/push once and print `writeback_ok=false` plus a short error in non-JSON launchd output. A summary like `comments=16 telegram=2` without writeback state is not sufficient proof.

When non-Madi owner DM chat IDs are missing, the job must not pretend direct Telegram is green. Load Telegram routing keys from the same `--env-file` used for Todoist, because launchd/non-interactive shells may not expose `~/nous-agaas/.env` as process environment. If `TELEGRAM_GROUP_CHAT_ID`, `TELEGRAM_FULL_CHAT_CHAT_IDS`, or `TELEGRAM_GROUP_OBSERVE_CHAT_IDS` is configured, send the missing-owner digest to that approved group as a fallback and report `missing_direct_owner_chats` plus `telegram_group_fallback_sent`. Personal DM remains yellow until the owner starts the bot or a real owner chat id is added to Air env. Never set an owner chat id to the group id and call it direct.

Todoist `AI:` comments must use the same factory route policy as Telegram. `tools/human_owner_reminder.py` calls `tools/factory_orchestration_policy.py` before it dispatches OpenClaw/run_task:

- decision/comment strategy prompts -> `grok-reasoning`;
- long or multi-step comments -> `deepseek-v4-flash` first, with escalation/fallback tracked by the policy;
- bounded execution comments -> one OpenClaw factory slice on `deepseek-v4-flash`, not hidden unbounded Codex spend from the hourly comment sweeper;
- the Todoist reply must include the route and model used.

This keeps Todoist orchestration real without turning the hourly comment-sweep into an uncapped GPT-5.5 loop. `/ask` can still use Codex for bounded execution because the Telegram path has explicit spend gates and user-visible status.

## One-Beam Queue Gate

Todoist is not allowed to remain a passive reminder board. `ready_for_ai_factory`, explicit `AI:` comments, and Satory BDL/APK/ERAP source-enrichment work must enter the same execution spine:

1. `tools/satory_todoist_deep_audit.py` must classify every Satory task with `execution_state`, `queue_reason`, `delete_candidate_reason`, `human_digest_eligible`, `latest_human_signal`, and `next_action_compact`.
2. `tools/satory_ai_factory_queue.py` consumes only queue-eligible rows, writes an idempotent event ledger, and dispatches one bounded OpenClaw slice per event. It must skip delete/merge candidates until a human or reviewer cleans them.
3. Human-facing Telegram output is digest-only by default: one compact Russian operator digest with status, blocker, next action, owner, and proof. Generic per-task Todoist reminder comments are opt-in via `--todoist-reminder-comments`; the default is no comment spam.
4. If `factory_orchestration_policy.py` classifies the event as mandatory Codex/GPT (`chatgpt_execution`), the queue must fail closed unless the run explicitly permits Codex (`--allow-codex`). Do not answer external proof questions through a cheap worker.
5. Every factory result must write a proof comment back to Todoist and a durable Obsidian receipt. Closing still requires Notion + Google Drive proof; an AI comment saying `готово` is never enough.
6. Hermes is observer/canary only for this spine until the AP-21/28 gates pass. Hermes may supply review evidence, but it cannot be the production router.
7. The Air LaunchAgent for the Satory queue may include `--allow-codex` only after a live Air Codex smoke test succeeds (`codex exec -m gpt-5.5 --sandbox read-only --ephemeral ...`). Without that proof, leave the job fail-closed; with that proof, load the job so BDL/APK/ERAP tasks actually execute instead of sitting as audit labels. Keep `--dry-run` as an explicit operator alias for the default read-only mode.
8. Queue idempotence must ignore the factory's own proof comments. A Todoist proof comment beginning `AI-фабрика взяла задачу...` with `Event:` and `Proof:` is context, not a new human `AI:` request. If no fresh human signal exists, any prior ledger entry for the same task blocks another run.
9. A failed queue event is not completion. The ledger may suppress successful events, but failed events must remain retryable until a bounded attempt cap is reached. Store `attempts`, `last_error`, `todoist_comment_id`, and `todoist_comment_error` in the ledger/audit so transient LiteLLM/OpenClaw failures can self-repair without losing proof or looping forever.
10. A successful runner return code is not a successful factory slice. If the worker output says `Статус: заблокировано`, contains a blocker section, says proof is absent, reports a missing/unmounted workspace, or returns the generic no-response text, record the result as blocked (`openclaw_blocked` / `codex_blocked`) and keep it in the failed-attempt lane. The queue success counter must measure useful task progress, not merely that OpenClaw/Codex executed.
11. If a queue row or its latest comments mention Air-vault paths (`pages/...`, `tools/...`, `briefs/...`, `raw/...`), the queue runner must inject small snippets from those files into the worker prompt before calling OpenClaw/Codex. OpenClaw sandbox workers may not have the Air wiki mounted; asking them to read paths they cannot see creates fake blockers. Missing referenced files should be listed explicitly in the prompt so the blocker is real, not guessed.
12. Proof-heavy Satory queue slices must use a tool-capable route. If the queued row or its recent comments mention live-tool markers such as smoke/health checks, browser/Playwright/screenshots, curl/HTTP/API/endpoints, VPS/SSH, dashboard/map/camera/events/logs, or metrology/certification, `tools/satory_ai_factory_queue.py` must force `chatgpt_execution` and fail closed unless `--allow-codex` is present. Do not trigger this rule from generic "must leave proof" boilerplate, Notion/Drive source links, or the close-gate text alone. The Codex route must have real shell/network capability (`CODEX_SANDBOX`, default `danger-full-access`) because `read-only`/`workspace-write` sandboxes can block DNS/network proof on Air. Because `danger-full-access` can also create side effects, the prompt must ban file/git/Todoist/Notion/Drive/Telegram writes, worker text that claims such writes must be classified as blocked, and any worker-created `pages/audits/SATORY-*-SLICE-YYYY-MM-DD.md` proof file must be absorbed into queue writeback so Air never stays dirty. Local MLX stays for routine drafting/classification, not for claims that require live commands or external proof.

## Timeline

- 2026-05-21: v1.8.8 -> v1.8.9 after post-audit launchd proof exposed another 100% blocker: the daily ledger suppressed duplicate Todoist comments but the Telegram section still iterated over the full reminder plan, so a same-day rerun could resend the same human digest. Patched `tools/human_owner_reminder.py` to build Telegram digests only from rows newly marked in the current run, and added regression tests for duplicate suppression plus fresh-row send behavior. No new LESSON (RULE ZERO).
- 2026-05-21: v1.8.7 -> v1.8.8 after the daily Satory Telegram digest exposed a false proof surface: `tools/human_owner_reminder.py` printed `Proof: https://todoist.com/showTask...`, which made the digest Todoist-link-dependent instead of evidence-dependent. Patched reminder rows to compute source/proof/close-gate state from task text, comments, attachments, and source markers; digest rows now show `Проверка фабрики` plus `Todoist:` separately. Focused tests: `python3 -m pytest Nous/tools/tests/test_human_owner_reminder.py -q` -> 23 passed. Live preview against Todoist sync: 20 reminders, 9 source-backed, 8 human-checkable, 0 close-ready. No new LESSON (RULE ZERO).
- 2026-05-19: v1.8.6 -> v1.8.7 after the live launchd queue selected three thin Satory AI proof tasks and all three blocked through `local-mlx-coder`. Root cause: the queue treated `openclaw_routine` as a capability route even when the slice needed shell/browser/API/VPS proof. Patched proof-heavy row detection so those slices force the Codex/GPT tool route with fail-closed budget/auth behavior, while local MLX remains for routine work. Follow-up live proof showed Codex `read-only`/`workspace-write` sandboxes could not produce DNS/network evidence on Air, while `danger-full-access` could; the queue now uses configurable `CODEX_SANDBOX` defaulting to `danger-full-access` for proof slices. Second follow-up exposed side effects: Codex wrote a slice proof file and claimed a direct Todoist comment, leaving Air dirty. Added prompt bans, side-effect classification, and queue writeback absorption for worker-created `SATORY-*-SLICE` proof files. Also codified the simple Todoist model: projects=areas, sections=state, labels=sparse facets, filters=dashboards; account-wide personal sprawl is context-only in a Satory lane. No new LESSON (RULE ZERO).
- 2026-05-19: v1.8.5 -> v1.8.6 after Madi rejected a broad Todoist Musk-cleanup proposal that asked for destructive greenlights on personal projects during a Nous/Satory-only lane. Tightened the scope boundary: personal cleanup may be observed as out-of-scope context but must not be presented as an approval checklist; only Satory actionable tasks can proceed. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/todoist-control-plane/skill.
- 2026-05-19: v1.8.4 -> v1.8.5 after live queue status showed `OK: 1`, `Blocked/failed: 2` because OpenClaw workers reported missing Air-vault files even though those paths existed in the Air wiki. Root cause: `tools/satory_ai_factory_queue.py` sent path references into a sandbox that cannot read the mounted wiki. Patched prompt construction to inject bounded Air-vault snippets for referenced `pages/...`, `tools/...`, `briefs/...`, and `raw/...` files, and to list truly missing refs. No new LESSON (RULE ZERO).
- 2026-05-19: v1.8.3 -> v1.8.4 after live AP-34 proof showed `local-mlx-coder` queue events counted as `OK` even when the returned worker text said `Статус: заблокировано`, `Proof: нет`, missing/unmounted workspace, or generic no-response. Root cause: `tools/satory_ai_factory_queue.py` trusted process `ok` instead of classifying worker output. Patched worker-output failure classification so these become `openclaw_blocked` / `codex_blocked` and stay retryable under the failed-attempt cap. No new LESSON (RULE ZERO). gbrain-timeline-ok.
- 2026-05-19: v1.8.2 -> v1.8.3 after a live launchd tick selected 3 Satory slices and one `long_work_goal` slice failed from transient LiteLLM `Remote end closed connection without response`. Root cause: the queue ledger recorded the failed event as already-run, so future ticks would skip it instead of retrying once. Patched failed-event retry semantics with an attempt cap and persisted Todoist comment ids/errors into ledger/audit receipts. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/todoist-control-plane/skill.
- 2026-05-19: v1.8.1 -> v1.8.2 after the first loaded Satory queue run exposed a feedback loop: the deep audit classified the factory's own proof comments as fresh `ai_request` signals, changing event fingerprints and re-running the same task through Codex. Patched proof comments to classify as context and added a task-level ledger guard when no fresh human signal exists. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/todoist-control-plane/skill.
- 2026-05-19: v1.8.0 -> v1.8.1 after the always-on mission exposed a queue deployment gap: the Satory queue plist existed but was not loaded, and the first real BDL/APK/ERAP candidate required GPT/Codex. Proved Air Codex `gpt-5.5` with a read-only smoke test, added explicit `--dry-run` CLI support, and updated `com.nous.satory-ai-factory-queue` to permit Codex only after proof. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/todoist-control-plane/skill.
- 2026-05-19: v1.7.3 -> v1.8.0 after Madi required a single Todoist/OpenClaw/GPT/Satory execution beam, not repetitive 09:15 spam and audit-only labels. Added the One-Beam Queue Gate: deep audit now emits execution metadata, `tools/satory_ai_factory_queue.py` consumes queue-eligible tasks with an idempotent ledger, human reminders default to compact digest-only, mandatory Codex routes fail closed without `--allow-codex`, and Hermes stays canary-only. No new LESSON (RULE ZERO). gbrain-timeline-ok via VPS CLI fallback after Codex MCP transport closed.
- 2026-05-15: v1.7.2 -> v1.7.3 after Madi required Todoist to be part of the OpenClaw/ChatGPT/LangGraph factory instead of a passive task pile. Added policy-routed `AI:` comment dispatch: `tools/human_owner_reminder.py` now classifies each request through `tools/factory_orchestration_policy.py`, passes an explicit `--model` to `run_task.py`, and writes the route/model into the Todoist reply. This preserves cheap worker execution for hourly sweeps while Telegram `/ask` keeps Codex behind spend-gated explicit execution. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/todoist-control-plane/skill.
- 2026-05-15: v1.7.1 -> v1.7.2 after the 09:15 daily reminder proved Todoist comments were green but 3 owner direct Telegram DMs were skipped because Данияр/Асылбек/Асыл chat ids were absent and launchd-style runs did not load Telegram routing keys from `--env-file`. Added env-file loading for Telegram routing, approved Satory group fallback for missing direct DMs, explicit counters, and tests; personal DM remains yellow until real owner chat ids exist. Also fixed `pages/secrets-manifest.md` drift for the four live Telegram group env keys. No new LESSON (RULE ZERO).
- 2026-05-14: v1.7.0 -> v1.7.1 after session s1729 shipped `tools/todoist_source_finder.py` (commit `651da179`) and ran it in `--apply` mode on Air. Receipt: 26/26 comments posted, 0 errors (`pages/audits/RECEIPT-todoist-source-finder-2026-05-14.json`). Verification deep audit ([[AUDIT-satory-todoist-deep-2026-05-14-1920]]): `contextless_tasks: 26 → 0`, `needs_source_enrichment: 26 → 0`, `ready_for_ai_factory: 20 → 37` (+17 AI-owned now factory-ready), `human_owner_reminder: 53 → 62` (+9 KEONA Subgroup C, human-assignee), `proof_counts.notion: 15 → 27` (+12 Notion URLs detected by classifier), `hard_gate_risk_total: 0`. Subgroup E tasks (#11 + #14) carry explicit "needs Madi clarification" comments — yellow-by-honest-ask, never fabricated. Source-Finder Loop section updated to remove "to be shipped" qualifier. No new LESSON (RULE ZERO).
- 2026-05-14: v1.6.2 -> v1.7.0 after session s1729-mac-87156 ran source-finder dry-run for the 26 `needs_source_enrichment` Satory tasks ([[AUDIT-satory-26-source-finder-dryrun-2026-05-14]]). Found 24 of 26 had findable sources (Notion + vault), 3 were mislabeled (vault source indexed in gbrain at score 0.99), and 8 site smoke tasks were sub-tasks of a `source_backed` parent — none required fabrication. Codified the Source-Finder Loop section: never invent source, query gbrain+QMD+Notion+, post structured "needs human" comments on misses, propagate parent source-backing to sub-tasks. Cross-ref `control-plane-sync` AP-15 (classifier must check gbrain). No new LESSON (RULE ZERO).
- 2026-05-14: v1.6.1 -> v1.6.2 after the daily human-owner reminder launchd job sent Todoist comments/Telegram digests but exited 2 because the final git writeback could race concurrent factory writers and the non-JSON output hid the writeback detail. Added a one-retry pull/rebase/push path and `writeback_ok` launchd summary. No new LESSON (RULE ZERO).
- 2026-05-14: v1.6.0 -> v1.6.1 after Madi caught a bad Todoist correction comment that merely repeated Daniyar's already-Russian four-point action list. Removed the immutable-comment fallback that posted `Русская версия предыдущего комментария:`; mixed Russian human comments are no longer Russianization candidates and immutable comments are skipped with an audit count. No new LESSON (RULE ZERO).
- 2026-05-13: v1.5.9 -> v1.6.0 after Madi clarified that Todoist comments must not only be answered but can explicitly hand work to the factory. Added hourly `com.nous.todoist-comment-sweep`, `--comment-sweep-only`, and guarded `AI:` comment dispatch through OpenClaw/run_task with per-comment ledger proof and no personal-project mutation. No new LESSON (RULE ZERO).
- 2026-05-13: v1.5.8 -> v1.5.9 after four non-Satory tasks oscillated between English and Russian because later receipts overrode an early matching `before` value. The planner now aggregates earliest `before` values first and checks idempotence after aggregation. No new LESSON (RULE ZERO).
- 2026-05-13: v1.5.7 -> v1.5.8 after Todoist returned a transient HTTP 503 during batched Sync API rollback. Added 502/503/504 retry handling and chunk-level error reporting so the factory tool fails visibly instead of crashing. No new LESSON (RULE ZERO).
- 2026-05-13: v1.5.6 -> v1.5.7 after four non-Satory task titles stayed changed even though REST returned success. Moved all task rollback fields (`content`, `description`, `labels`) to batched Todoist Sync API `item_update`. No new LESSON (RULE ZERO).
- 2026-05-13: v1.5.5 -> v1.5.6 after live Todoist samples proved labels were clean but dry-run still reported 91 rows. Fixed expected-target logic so factory labels are always stripped for non-Satory rollback, including post-cleanup idempotence. No new LESSON (RULE ZERO).
- 2026-05-13: v1.5.4 -> v1.5.5 after one-by-one Sync API label removal spent minutes in 429 backoff. Batched `item_update` commands for rollback label cleanup to reduce request count and keep the factory cycle bounded. No new LESSON (RULE ZERO).
- 2026-05-13: v1.5.3 -> v1.5.4 after the Sync API cleanup hit HTTP 429. Added `Retry-After` aware backoff around Todoist sync reads and Sync API label writes so Hermes/factory can recover from rate limits. No new LESSON (RULE ZERO).
- 2026-05-13: v1.5.2 -> v1.5.3 after REST `POST /tasks/{id}` returned success but did not remove labels from Todoist tasks. Switched rollback label updates to Todoist Sync API `item_update` and added a regression test. No new LESSON (RULE ZERO).
- 2026-05-13: v1.5.1 -> v1.5.2 after post-rollback verification found 15 non-Satory rows where Todoist kept global factory metadata labels. Added the rule and tool behavior to strip factory metadata labels from non-Satory tasks while preserving real personal labels, instead of renaming shared global labels. No new LESSON (RULE ZERO).
- 2026-05-13: v1.5.0 -> v1.5.1 after post-rollback dry-run still reported 127 rows even though live Todoist had been restored. Added idempotence checks so `tools/todoist_scope_revert.py` skips rows already equal to their recorded `before` state and added regression coverage. No new LESSON (RULE ZERO).
- 2026-05-13: v1.4.9 -> v1.5.0 after Madi caught scope drift: the global cleanup path touched personal projects. Added the Satory-only scope boundary, hardened audit/export/Russianization/reminder scripts to filter `Фабрика Satory ВКО` before planning, stopped global label renames, and added `tools/todoist_scope_revert.py` for receipt-backed personal rollback. No new LESSON (RULE ZERO).
- 2026-05-13: v1.4.8 -> v1.4.9 after the second comment-aware dry-run showed a checklist item containing `вопросы` being misread as a human question. Narrowed question detection to actual questions (`?`, `у меня вопрос`, `вопрос:`, `подскажи`, etc.) and kept checklist bullets silent. No new LESSON (RULE ZERO).
- 2026-05-13: v1.4.7 -> v1.4.8 after the first comment-aware dry-run showed source/context comments being falsely classified as human blockers/questions. Added the source/context/template skip rule for `tools/human_owner_reminder.py`: Notion/proof/Obsidian/GitHub/source comments and instruction templates are ignored unless the comment starts with an explicit `AI:` request. No new LESSON (RULE ZERO).
- 2026-05-13: v1.4.6 -> v1.4.7 after Madi clarified that the looping Todoist AI must check and answer task comments, not only remind stale tasks. Extended `tools/human_owner_reminder.py` to classify recent non-AI comments (`готово`, `в работе`, `заблокировано`, questions, `AI:` requests), reply once per comment with Russian next-step instructions, and store a `comment_replies` ledger to prevent spam. No new LESSON (RULE ZERO).
- 2026-05-13: v1.4.5 -> v1.4.6 after Todoist rejected a live comment rewrite with HTTP 400 for an existing human-authored note. Added a guarded fallback: when comment update is immutable but the task id is known, add a Russian correction comment on the task and record it as `add_note_translation`. No new LESSON (RULE ZERO).
- 2026-05-13: v1.4.4 -> v1.4.5 after final LLM verification proposed a good Russian rewrite that silently truncated an Obsidian `pages/projects/GOAL-...md` path. Added evidence-reference extraction and a hard `acceptable_translation` guard so Russianization rows that damage proof paths/source slugs are skipped, not applied. No new LESSON (RULE ZERO).
- 2026-05-13: v1.4.3 -> v1.4.4 after comment Russianization exposed a false-yellow detector: the audit still counted `pages/...`, Notion links, source slugs, file names, and protected product names as English, and one already-Russian comment failed HTTP 400 on a punctuation-only rewrite. Tightened `tools/todoist_russianize.py` to ignore proof-library evidence and added regression tests for path/Notion/comment cases. No new LESSON (RULE ZERO).
- 2026-05-13: v1.4.2 -> v1.4.3 after the free-form task pass left Todoist comments outside the language gate. Extended `tools/todoist_russianize.py` to include active-task comments/notes in candidate detection, audit exposure, rollback plans, and guarded `update_note` apply via Todoist comments API. No new LESSON (RULE ZERO).
- 2026-05-13: v1.4.1 -> v1.4.2 after the free-form Todoist translation queue stalled: the docs gate was green, but `tools/todoist_russianize.py` still defaulted through a local LiteLLM path returning `No connected db`, and direct OpenRouter failed on Air's Python certificate store. Switched Russianization to direct OpenRouter/DeepSeek by default, added provider-key selection plus certifi/curl fallback, and kept fake-description filling banned. No new LESSON (RULE ZERO).
- 2026-05-13: v1.4.0 -> v1.4.1 after a control-plane sync falsely blocked because the Russian docs gate still required `# todoist-control-plane v1.3.0` while the live skill was v1.4.0. Patched the gate to accept the versioned heading shape and codified version-neutral documentation gates. No new LESSON (RULE ZERO).
- 2026-05-13: v1.3.0 -> v1.4.0 after Madi clarified that Todoist must actively remind human owners, not only display clean fields. Added the Human Owner Reminder automation gate: daily Russian comments/digests for stale human-owned tasks, no fake context, ledger guarded. No new LESSON (RULE ZERO).
- 2026-05-13: v1.2.0 -> v1.3.0 after Madi clarified that Todoist/Notion documentation itself must be Russian and mechanically checked across Obsidian, gbrain, OpenBrain, GStack-visible skill routing, GitHub, and Telegram. Added Russian Documentation Sync Gate and `tools/check_russian_control_plane_docs.py`; wired the gate into `control_plane_sync_loop.py`. No new LESSON (RULE ZERO).
- 2026-05-13: v1.1.0 -> v1.2.0 after live Todoist audit found the board structurally clean but English-heavy for a Russian-speaking team. Added Russian-Language Rule plus `tools/todoist_russianize.py` as the guarded migration path: preserve IDs/links/source slugs, translate user-facing text, keep fake context banned, and write rollback/audit artifacts. No new LESSON (RULE ZERO).
- 2026-05-13: v1.0.0 -> v1.1.0 after Satory ERAP testing update proved the needed pattern: forwarded Daniyar/Asyl chat plus two PDF offers must become Obsidian source/status pages, Notion tasks, Todoist tasks with owner/department labels, and a clean post-create Todoist audit. Added Source-Backed Intake Rule. No new LESSON (RULE ZERO).
- 2026-05-13: v1.0.0 created after global Todoist cleanup found the old daily audit was Satory-scoped only. Added global hard gates for project, section, owner, department, label, and priority hygiene.
