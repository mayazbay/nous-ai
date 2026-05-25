---
type: skill
id: control-plane-sync
title: "Control Plane Sync"
tier: 2
version: 1.1.5
status: active
date: 2026-05-13
last_updated: 2026-05-22
tags: [control-plane, todoist, notion, github, langsmith, factory, model-bakeoff]
---

# control-plane-sync v1.1.5

Use this skill whenever Madi asks for the whole operating system to keep Todoist, Notion, Obsidian, gbrain, GitHub, LangSmith, Telegram, Goal Mode, or the AI factory synced without manual reminders.

## Purpose

The control plane is the operational scoreboard. It must show what is working, what is in progress, what is done, what is not done, and what is blocked. The loop is a deterministic automation first, not a chat prompt. Models receive explicit slices only after code and APIs establish the current state.

## Runtime Contract

- Durable runner: `com.nous.control-plane-sync` on Air every 3 hours unless Madi explicitly promotes it to hourly.
- Entrypoint: `tools/control_plane_sync_loop.py`.
- Status page: `pages/systems/control-plane-sync-status.md`.
- Todoist register: `pages/systems/todoist-control-plane-register.md`, `pages/systems/todoist-control-plane-register.json`, `pages/exports/todoist-control-plane-register.csv`.
- Todoist source-enrichment queue: `pages/systems/todoist-context-enrichment-queue.md`.
- Satory deep task/comment/proof audit: `pages/systems/satory-todoist-deep-audit.json` plus `pages/audits/AUDIT-satory-todoist-deep-*.md`.
- gbrain-friendly Satory audit index: `pages/systems/satory-todoist-deep-audit-index.md`.
- Cycle receipts: `pages/audits/CONTROL-PLANE-SYNC-*.md`.
- Local event log: `/Users/madia/nous-agaas/logs/control-plane-sync.jsonl`.
- Telegram receipt: `tools/tg_send.sh` after every live cycle.
- LangSmith mirror: `tools/langsmith_observer.py`, project `nous-agaas-control-plane`.
- Human reminder loop: `com.nous.human-owner-reminder` daily 09:15 KZT, status at `pages/systems/human-owner-reminder-status.md`, supervised by Hermes.
- Todoist comment sweep: `com.nous.todoist-comment-sweep` hourly, same status/ledger, runs `tools/human_owner_reminder.py --apply --comment-sweep-only` so `AI:` comments can enter the factory without hourly human-reminder spam.

## State Semantics

- `in_progress`: the cycle is currently running.
- `working`: a worker slice was assigned and has not yet produced proof.
- `done`: the component was verified with live command output in the current cycle.
- `not_done`: the component has a deterministic next action but was not fully applied.
- `blocked`: API/runtime/git proof failed; factory or operator action is required.
- `skipped`: intentionally skipped by dry-run or cadence guard.

Do not mark a state green because a document exists. A status is green only when the runtime path was probed in the current cycle.

## Procedure

1. Start with a clean wiki checkout, resolve the canonical remote for that checkout (`NOUS_CANONICAL_REMOTE`, else first existing of `origin`, `vps`, `bare`), fetch exactly `main:refs/remotes/<remote>/main`, and rebase onto that exact OID. Do not use unattended `git pull`.
2. Mirror Notion Satory rows through `tenants.satory.agents.notion_to_gbrain`; write real artifacts under `pages/tenants/satory/`.
3. Run `tools/todoist_control_plane_audit.py --json`; apply only deterministic hard-gate repairs. Treat `no_description_or_note` as yellow until a real source artifact can be attached.
4. Run `tools/todoist_control_plane_export.py --json`; write the Markdown/JSON/CSV task register plus the Russian source-enrichment queue. A green aggregate audit is not enough: humans and agents need the per-task register with status, owner, department, priority, labels, links, context state, and idiot-proof source lookup instructions.
5. Run `tools/satory_todoist_deep_audit.py --json` after the register export. This audit must enumerate every active Satory task and every Todoist comment/attachment visible through the Sync API, classify the factory route, and enforce the close/delete proof gate.
6. Run substrate probes and `tools/factory_no_drift_probe.sh`.
   - Treat optional Nous-GPU collector reachability as yellow unless the cycle is explicitly GPU-bound (`NOUS_GPU_REQUIRED=1`).
7. Smoke LangSmith with `tools/langsmith_observer.py --smoke`. LangSmith is a mirror; local JSONL remains the source of truth.
8. Run the weekly model bakeoff when the last bakeoff is older than 7 days. Compare `deepseek-v4-flash`, `deepseek-v4-pro`, `kimi-k2.6`, and `glm-5.1` through live LiteLLM aliases. Dry-runs must skip this spend. If every candidate fails or times out, report `not_done`; never call an all-error bakeoff green because the script exited 0.
9. Write the status page and audit receipt.
10. Commit scoped artifacts with hooks disabled, then push the resolved canonical remote `main` and GitHub `main`.
11. Send the Telegram receipt. If Telegram fails, keep the cycle audit and report `not_done` for notification only.
12. Generated control-plane/status/audit commits must not trigger paid GitHub Codex review loops. Keep `.github/workflows/codex-landed-commit-loop.yml` manual-only through `workflow_dispatch`; do not reintroduce push triggers, repo-variable gates, or commit-message gates for this paid landed-review job.
13. Human-owned Todoist tasks must not silently stall. The daily reminder loop pings stale/overdue/blocked human-owner tasks once per day through Todoist comments and Telegram digests where chat IDs exist. Do not spam every cycle; the ledger is the guardrail.
14. Todoist/Notion business data is Satory-only by default. The loop must not mutate, export, mirror, Russianize, or remind personal projects unless Madi names a project exception in the same request. The allowed project is `Фабрика Satory ВКО` / `6gJ5j8PRVVCWpgCq`.

## Model Routing Rule

Do not route every cycle through GPT. The standing hierarchy is:

- `/ask`: OpenClaw Grok CEO/router path.
- `/codex`: explicit GPT-5.5/Codex high-judgment path.
- `/goal`: durable GOAL page plus OpenClaw worker slice, not direct GPT.
- Routine sync/build labor: DeepSeek V4 Flash by default; DeepSeek V4 Pro only for failed or high-judgment slices.
- Kimi remains a measured candidate through weekly bakeoff until live results justify broader use.

## Failure Handling

When a cycle fails:

1. Save the failing command, output, and status in the cycle audit.
2. If the same failure class repeats twice, update the owning skill and add a gbrain timeline entry.
3. Retry only after the rule or automation has been improved.
4. Never add generic Todoist notes or fake Notion mirrors to make dashboards look clean.

## Anti-Patterns

### AP-1 — Air-local probes must not SSH to Air

When a loop runs on Air, factory probes must use local launchctl/curl/git commands for Air services. SSHing to `air` from Air can fail even when OpenClaw, LiteLLM, Telegram poller, and Goal Mode are healthy, creating false red status and hiding the real blocker.

### AP-2 — Launchd exit code is runner health, not business status

The launchd process should exit 0 when the cycle executed, wrote status, and emitted receipts, even if the control-plane status is `blocked` or `not_done`. Business/system state belongs in `pages/systems/control-plane-sync-status.md` and the cycle audit. Nonzero exit is reserved for automation crashes that prevent a cycle receipt.

### AP-3 — Generated commits must not spend GPT review quota by default

High-frequency control-plane, auto-sync, auto-checkpoint, and goal-mode commits are operational receipts, not events that justify paid landed-commit GPT review. If the GitHub workflow runs `openai/codex-action` on every `main` push, a normal sync burst becomes dozens of failed "Quota exceeded" emails and hides real CI signal.

Rule: the landed-commit Codex workflow must be manual-only. Allow only `workflow_dispatch`; do not allow push events, `CODEX_LANDED_REVIEW_ENABLED`, commit markers, or generated-commit skip lists because those still create noisy skipped runs and can be reconfigured into quota burn. Preserve a deterministic guard: `python3 tools/test_codex_landed_workflow_gate.py`.

### AP-4 — Optional GPU lane must not block Todoist/Notion sync

The control plane exists to keep the operating surface current. A degraded optional compute lane can be important, but it must not mark Todoist, Notion, LangSmith, GitHub, gbrain, and Goal Mode as blocked when those paths are green.

Rule: `tools/daily_0300_substrate_sync.py` reports `Nous-GPU` as `YELLOW` when `com.nous.nous-gpu-collector-health` is red unless `NOUS_GPU_REQUIRED=1` is set for a GPU-bound run. Escalate the GPU task separately with owner/remediation; do not let it suppress the every-3-hour control-plane sync receipt.

### AP-5 — Aggregate Todoist green is not a control-plane register

A Todoist audit with `missing_owner=0`, `missing_department=0`, and `root_no_section=0` only proves structural hygiene. It does not let people or agents see the work queue, completed work, blockers, or source context.

Rule: every control-plane cycle must write a per-task register from live Todoist state. Required artifacts are `pages/systems/todoist-control-plane-register.md`, `pages/systems/todoist-control-plane-register.json`, and `pages/exports/todoist-control-plane-register.csv`. The register must include active tasks, recent completed tasks, status counts, owner, department, project, section, priority, labels, Todoist links, and context state. Never call Todoist/Notion "god level" from aggregate counts alone.

### AP-6 — Drive read/search access is not Drive write proof

Google Drive can look connected while still unable to publish the register. On 2026-05-13, the Codex Google Drive connector could read/search but spreadsheet import failed with `403 Forbidden` on the Drive upload endpoint. Local and Air `rclone` both had `gdrive:` configured, but `rclone lsf gdrive:` failed with `empty token found`.

Rule: Drive is green only after a real upload/import returns a Drive URL. Until then, keep Obsidian/GitHub/gbrain as source of truth, update Notion with the exact Drive blocker, and create one Todoist blocker task with owner, department, priority, and evidence. Do not mark Drive green because a connector exists.

### AP-7 — Contextless Todoist tasks become a source-backed factory queue, not fake notes

Todoist tasks with no description and no comments are yellow because the factory lacks context. The fix is not to add generic filler. The fix is to expose them as work the factory can take one by one.

Rule: every control-plane export must write `pages/systems/todoist-context-enrichment-queue.md`. For each `needs_source` task, the queue must include Russian step-by-step instructions: open Todoist, search Obsidian/gbrain/Notion/Gmail/Drive/GitHub by title and project, add a real source-backed Todoist description/comment only when evidence exists, create a receipt in `pages/task-results/`, and leave an honest blocker when no source is found.

Verification: `tools/tests/test_todoist_control_plane_export.py` asserts the queue is written and contains `Инструкция фабрике`; live export on 2026-05-13 produced `104` contextless tasks in the queue with hard gates still `0`.

### AP-8 — Human-owned Todoist tasks need a daily reminder lane, not passive dashboards

If a task is assigned to a human owner and is overdue, due today, blocked, P4, or stale, the factory cannot wait for Madi to remember it manually. A clean register is not enough; the owner needs a daily nudge and the system needs a receipt.

Rule: run `tools/human_owner_reminder.py --apply` daily under launchd label `com.nous.human-owner-reminder`. The script must:

1. read live Todoist through the same v1 API substrate;
2. select only human owners such as `Мади`, `Данияр`, `Асылбек`, and `Асыл`;
3. add at most one Todoist reminder comment per task per day using `pages/systems/human-owner-reminder-ledger.json`;
4. send Telegram digests to known chat IDs, and skip direct human Telegram when a chat ID is not configured instead of guessing;
5. write `pages/systems/human-owner-reminder-status.md` and `pages/audits/HUMAN-OWNER-REMINDER-YYYY-MM-DD.md`;
6. let Hermes supervise freshness and kick the hourly comment sweep launchd job if status is missing or older than 4 hours.

This is deterministic escalation, not model judgment. OpenClaw remains the worker factory; Hermes supervises the reminder lane.

### AP-11 — Todoist comments need hourly factory intake, not only daily reminders

Daily reminders are not enough for active operations. If Daniyar/Assylbek/Asyl writes `AI:` in a Satory Todoist comment, the factory must react in the next hourly sweep, not wait for the next morning digest.

Rule: `com.nous.todoist-comment-sweep` runs hourly and calls `tools/human_owner_reminder.py --apply --comment-sweep-only`. In this mode the script must skip reminder digests, read comments on Satory tasks, dispatch explicit `AI:` comments through OpenClaw/run_task, write the result or blocker back into the same Todoist task, and ledger the comment id so it never repeats the same work.

### AP-12 — Done means human-checkable proof, not an agent comment

A Todoist task is not complete just because an agent wrote `готово`, and the factory must not delete or close tasks that only have a chat-style answer. Humans need a place they can inspect: Notion for management context and Google Drive/Docs/Sheets for shareable proof.

Rule: every control-plane cycle runs `tools/satory_todoist_deep_audit.py`. The audit must enumerate every active Satory task and every Todoist comment, classify the task route (`ready_for_ai_factory`, `needs_source_enrichment`, `blocked`, `human_owner_reminder`, `human_owned_monitor`), and set `close_gate=ready_to_close` only when both Notion and Google Drive proof links are present. Otherwise the task stays open with `do_not_close_missing_notion_or_drive_proof` or an explicit blocker. Personal projects remain out of scope.

### AP-13 — Full audits need compact gbrain indexes

Large audit pages can be correct on disk and still be poor retrieval surfaces. A 200KB+ per-task audit is useful for forensic review, but gbrain/OpenBrain should not have to rank or embed that whole file just to answer "what is the current Satory Todoist state?"

Rule: every deep Satory Todoist audit writes both the full artifacts and `pages/systems/satory-todoist-deep-audit-index.md`. The index must stay short, include title/scope/counts/routes/proof gate, and link to the full JSON/Markdown audit. Claim gbrain parity from the index readback, not from a huge audit blob.

### AP-14 — `close_ready=0` after closure is not Drive failure

The Satory deep audit is an active-task close gate. If the only task carrying both Notion and Google Drive proof is closed after the gate passes, the next active-task audit will correctly return `close_ready=0` and `google_drive=0`. That does not mean Google Drive broke again; it means there are no currently active tasks with both proof links waiting to be closed.

Rule: approve the Drive proof path from three separate checks:

1. Mac and Air can list the target folder through `rclone`.
2. The target proof artifact is downloadable from the stored Google Drive URL without relying on a local session.
3. The next live control-plane run distinguishes active close-ready tasks from recent completed proof tasks instead of collapsing both into one number.

Do not report "Drive fixed because `close_ready=1`" after closing the task. Report the actual active-task count and the proof-path health separately.

Implementation shipped in `tools/satory_todoist_deep_audit.py`: every report now includes `proof_path_health.google_drive_storage` and `proof_path_health.interpretation` beside the active-task `proof_counts`. The expected post-closure state is explicit: `proof_counts.google_drive=0`, `proof_counts.close_ready=0`, and `proof_path_health.interpretation=drive_path_approved_no_active_task_ready_to_close`.

### AP-9 — Air sync lag is not GitHub mirror failure

`tools/factory_no_drift_probe.sh` can run on Air while Mac/VPS/GitHub have already advanced. If the probe uses Air's stale local `HEAD` as expected, it reports `github_mirror stale` even when GitHub is actually correct.

Rule: classify this as `air_sync_lag`. The probe must fetch `origin/main` and `github/main`, use the canonical origin/GitHub head for mirror checks, and expose a separate `air_sync_lag` check with remediation `git pull --rebase origin main`. Hermes may kick the pull and rerun the probe once. `github_mirror` is red only when GitHub differs from canonical or token-bearing remotes return.

### AP-10 — Satory-only control plane, personal projects are not cleanup targets

The control plane exists for Satory factory execution, not Madi's personal Todoist. A broad "god-level Todoist" request must not become a global mutation unless Madi explicitly says to include personal projects.

Rule: audit/export/Russianization/reminder paths filter the live Todoist Sync payload to `Фабрика Satory ВКО` before creating any plan. Personal project repair must use `tools/todoist_scope_revert.py` and recorded `before` values only.

### AP-15 — `needs_source` classifier must query gbrain before flagging

The Todoist deep-audit classifier (`tools/satory_todoist_deep_audit.py`) marks a task `needs_source` when description + comments don't reference Obsidian/Notion/Drive/GitHub by URL. That heuristic produces false positives: a real source can already exist in the vault and be indexed in gbrain at semantic score 0.99 without the Todoist task ever embedding its URL. On 2026-05-14, source-finder dry-run found 3 of 26 `needs_source` tasks resolved cleanly to `pages/sources/user-forwarded/SOURCE-SATORY-RUSLAN-APK-TESTING-2026-05-13.md` via one-shot `mcp__gbrain__query` at score 0.99 — the classifier missed them.

Rule: before emitting `factory_route=needs_source_enrichment` on a task, the classifier must run a hybrid gbrain query on `task.content` with score threshold ≥ 0.5. Hits flip the route to `source_backed_inferred` and write the matched slug into `task.source` (overridable by human). The classifier must also resolve `parent_id` and propagate parent's `context_state=source_backed` to children before flagging them yellow.

Verification: extend `tools/tests/test_satory_todoist_deep_audit.py` with a fixture where a task with no description/comments has a high-scoring gbrain match — assert the classifier returns `source_backed_inferred`, not `needs_source`.

### AP-16 — Control-plane git preflight must rebase exact OIDs, not `git pull`

The factory drift probe already learned this class in `factory-ops` AP-58: unattended `git pull --rebase` is unsafe in Air's multi-writer wiki. On 2026-05-16 the 24h Hermes canary audit found the same bug in `tools/control_plane_sync_loop.py`: `git pull --rebase origin main` fetched `main` but failed with `There is no candidate for rebasing against among the refs that you just fetched.`

Rule: every control-plane git preflight and writeback must:

1. `git fetch <remote> main:refs/remotes/<remote>/main`;
2. read the exact OID with `git rev-parse --verify refs/remotes/<remote>/main`;
3. `git -c core.hooksPath=/dev/null rebase <exact_oid>`;
4. re-read the remote OID if another writer advanced it during the operation.

Do not use `git pull` in this automation. `pull` is a compound command and can resolve branch config, wildcard refspecs, or `FETCH_HEAD` differently across Mac, Air, and VPS.

Detector: `python3 -m pytest tools/tests/test_control_plane_sync_loop.py tools/tests/test_github_mirror_writers_static.py -q` must prove the control-plane loop has no `git pull --rebase` path and still rebases the GitHub mirror before pushing it.

### AP-17 — Control-plane canonical remote is checkout-local, not always `origin`

Mac, Air, and VPS wiki checkouts do not all use the same remote names. On 2026-05-16 the Mac active vault had `vps`, `github`, and `air` remotes while Air used `origin`; the control-plane dry-run blocked on `exact origin/main rebase failed` even though the live Air runner was healthy. That made the Mac audit surface look red for a tool-portability reason, not because the control plane was actually behind.

Rule: control-plane git preflight and writeback must resolve the canonical remote per checkout. Use `NOUS_CANONICAL_REMOTE` when explicitly set; otherwise prefer the first existing remote in this order: `origin`, `vps`, `bare`. Only after resolving the remote may the loop fetch `main:refs/remotes/<remote>/main`, rebase the exact OID, and push `<remote> main`.

Detector: `python3 -m pytest tools/tests/test_control_plane_sync_loop.py -q` must include a fixture where `origin` is absent and `vps` is selected, plus an override fixture for `NOUS_CANONICAL_REMOTE`.

### AP-18 — Air worktree stuck mid-merge on `.obsidian/workspace.json` needs receipt backup before recovery

When Air's wiki worktree enters a merge-in-progress state (`.git/MERGE_HEAD` present) and the only unmerged path is `.obsidian/workspace.json`, the writers self-pause: control-plane-sync, auto-checkpoint, goal-cycle, hermes-watchdog, human-owner-reminder, and other launchd jobs continue writing receipts on disk but their `git add + git commit` cycle stalls because git refuses to commit while unmerged paths exist. Receipts accumulate in the merge index as `Changes to be committed` for 30+ files. Factory probe goes RED on `air_sync_lag` and `github_mirror`, but the serving layer can stay green, so the drift looks smaller than it is.

Symptom signature (one-shot diagnosis from any host):
```bash
ssh air "cd ~/nous-agaas/wiki && git status | head -3 && ls -la .git/MERGE_HEAD 2>/dev/null && git ls-files --unmerged | head -5"
```
Hits if `MERGE_HEAD` exists AND `ls-files --unmerged` returns rows AND the unmerged path set is `{.obsidian/workspace.json}` (often the ONLY conflicted path, because business pages don't collide across writers — `workspace.json` is Obsidian-app UI state regenerated on every pane open/close).

Rule: surgical recovery, no receipt loss:
1. **Snapshot pre-state** to `~/nous-agaas/logs/air-recovery-YYYYMMDDTHHMMSS/`: `git status`, `git status --porcelain=v1 -uall`, `git ls-files -u`, `git diff`, and `git diff --cached`.
2. **Export the business receipts before any abort/reset.** Write `git diff --cached --binary -- . ":(exclude).obsidian/workspace.json"` to `staged-operational.patch`, and archive untracked receipt paths from `git status --porcelain` to `untracked-files.tgz`. `.obsidian/workspace.json` is UI state; exclude it from the receipt backup.
3. **Verify duplicate local history before dropping it.** `git cherry -v origin/main HEAD` must mark old Air commits as `-` patch-equivalent before they are allowed to disappear during rebase.
4. **Recover onto canonical.** If the merge state is stale, `git merge --abort` is acceptable only after step 2. Then `git rebase origin/main`, `git apply --index --3way staged-operational.patch`, restore the untracked archive, and commit the receipts.
5. **Race tolerance:** a control-plane-sync writer cycle may commit the restored receipts while your manual commit is in hooks. If `git commit` fails with `cannot lock ref 'HEAD': is at <new> but expected <old>`, do not retry blindly. Inspect the new HEAD; if it contains the receipt patch and the tree is clean, continue from that head and push/sync. 4-way HEAD parity (Mac = Air = VPS bare = VPS working = GitHub when required) is the success gate, not "my commit landed verbatim."

Pre-merge orphaned commits (Air's unique pre-merge chain) survive as content even if rebase flattens the topology: `git cherry -v origin/main HEAD` proves duplicate patches, and `git show --stat <receipt-commit>` plus spot-checks prove restored receipt files are present.

Cross-ref: AP-16 (exact-OID rebase), AP-17 (canonical-remote-per-checkout), [[architecture-quickref]] 4-way topology, [[session-operating-contract]] Rule 19 (authorial commits), [[gbrain-ops]] (workspace.json sync noise upstream).

Long-term fix (separate AP work): add `.obsidian/workspace.json` to `.gitignore` and untrack it after a dedicated audit — it is UI state, not business content, but removal touches shared vault behavior and should not be smuggled into recovery.

### AP-19 — Presidential readiness probes Air-only health on Air, not Mac

`tools/presidential_readiness_gate.py` is a scoreboard, not the control-plane runner. If it invokes Air-only sync proof from the Mac checkout, it creates false yellow/red output: local Mac does not own Air Todoist env, Docker, LiteLLM, launchd jobs, or `/Users/madia/nous-agaas/wiki`. The gate must run `tools/control_plane_sync_loop.py --dry-run --json --no-telegram --no-apply-todoist` on Air and classify the returned `overall_status`.

Satory queue dry-run is also not red/yellow just because `selected=0`. A zero-selection dry-run is green when queue diagnostics prove there are no unblocked candidates, or every eligible queued candidate is ledger-covered from a prior run without new human signal. It stays yellow only when unblocked candidates exist but were not selected, or when diagnostics are missing. This prevents noisy "empty queue" alarms without letting stuck queues hide.

OpenClaw canary checks must track the current production generation. Once production is `ghcr.io/openclaw/openclaw:2026.5.19` and healthy on 18789, the old 5.18 sidecar on 18790 is historical rollback evidence, not a readiness dependency. Keep a canary lane when a promotion plan requires it, but do not fail readiness on an obsolete stopped canary while production is green.

## Manual Verification

```bash
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 tools/control_plane_sync_loop.py --dry-run --json
launchctl list com.nous.control-plane-sync
launchctl list com.nous.todoist-comment-sweep
tail -50 /Users/madia/nous-agaas/logs/control-plane-sync.out.log
python3 tools/human_owner_reminder.py --comment-sweep-only --no-ai-dispatch --no-telegram --json
python3 tools/satory_todoist_deep_audit.py --dry-run --json
python3 tools/test_codex_landed_workflow_gate.py
python3 -m pytest tools/tests/test_todoist_control_plane_export.py -q
```

## Timeline

- 2026-05-22: v1.1.4 -> v1.1.5. Added AP-19 after presidential readiness stayed yellow from Mac-local `control_plane_sync_loop.py` dry-runs, `selected=0` Satory queue dry-runs, and stale OpenClaw 5.18 port-18790 canary checks while Air production was green. Patched the gate to run Air-only proof on Air, require queue diagnostics before judging zero-selection as idle, and verify current OpenClaw 2026.5.19 production health instead of obsolete 5.18 sidecar liveness. No new LESSON (RULE ZERO).
- 2026-05-17: v1.1.3 -> v1.1.4. Added AP-18 after Air worktree was stuck mid-merge on `.obsidian/workspace.json` while 30+ receipts accumulated in the index (control-plane audits, HANDOFFs, task-results, GOAL updates, status files, human-owner-reminder ledger, and an inbox note). Recovery snapshot: `/Users/madia/nous-agaas/logs/air-recovery-20260517T110311/`. Actual recovery: saved `staged-operational.patch` + `untracked-files.tgz`, verified Air's old commits were patch-equivalent with `git cherry`, ran `git merge --abort`, rebased onto `origin/main`, applied the receipt patch with `git apply --index --3way`, restored untracked receipts, then let the active control-plane writer finish the receipt commit after a `cannot lock ref HEAD` race. Final proof: `factory_no_drift_probe.sh --json --no-telegram --no-repair` returned GREEN, red=0, with Mac/Air/VPS/GitHub all at `8d4f4306`. No new LESSON (RULE ZERO).
- 2026-05-16: v1.1.2 -> v1.1.3. Added AP-17 after the atomic substrate audit found a Mac-only control-plane dry-run blocker: this active vault has `vps`/`github`/`air` remotes, so hardcoded `origin` made preflight fail even though the Air launchd path was healthy. Patched `tools/control_plane_sync_loop.py` to resolve the canonical remote per checkout (`NOUS_CANONICAL_REMOTE`, then `origin`/`vps`/`bare`) and added regression tests for `vps` fallback and env override. No new LESSON (RULE ZERO).
- 2026-05-16: v1.1.1 -> v1.1.2. Added AP-16 after the 24h Hermes canary audit exposed a control-plane dry-run blocker: `git pull --rebase origin main` failed on Air with "no candidate for rebasing" even though factory drift was green. Patched `tools/control_plane_sync_loop.py` to fetch exact remote refs and rebase exact OIDs for preflight and writeback, matching factory-ops AP-58. No new LESSON (RULE ZERO).
- 2026-05-14: v1.1.0 -> v1.1.1. Implemented AP-14 in `tools/satory_todoist_deep_audit.py` after Madi flagged that reports still read as "Drive broken" when `google_drive=0` and `close_ready=0`. The audit now emits a separate `proof_path_health` block: Drive storage approval is read from `AUDIT-google-drive-proof-path-2026-05-14-1812.md`, while active-task close gate remains strict (`close_ready` only when an active task has both Notion and Drive proof). Added regression coverage in `tools/tests/test_satory_todoist_deep_audit.py`. No new LESSON (RULE ZERO).
- 2026-05-14: v1.0.13 -> v1.1.0. Added AP-15 after source-finder dry-run for 26 Satory `needs_source_enrichment` tasks ([[AUDIT-satory-26-source-finder-dryrun-2026-05-14]]) found 3 mislabeled — vault source `SOURCE-SATORY-RUSLAN-APK-TESTING-2026-05-13.md` was indexed in gbrain at score 0.99 but the deep-audit classifier missed it because the Todoist task description/comments did not reference the URL. Classifier must run gbrain hybrid query before flagging `needs_source`; parent source-backing must propagate to sub-tasks. Cross-ref `todoist-control-plane` v1.7.0 (Source-Finder Loop). No new LESSON (RULE ZERO).
- 2026-05-14: v1.0.12 -> v1.0.13. Added AP-14 after Google Drive OAuth was repaired but the next live Satory audit still showed `google_drive=0` and `close_ready=0` because the proof-bearing OAuth blocker task had been closed and dropped out of the active-task audit. Rule: approve Drive proof path separately from active close-ready count. No new LESSON (RULE ZERO).
- **2026-05-14 openbrain** | OpenBrain Capture - 2026-05-14 Nous AGaaS audit handshake — session s108-mac-74… [[openbrain-8059b962-6a58-4492-9fde-8c3f2c2d336c]]
- 2026-05-14: v1.0.11 -> v1.0.12. Added AP-13 and the compact `satory-todoist-deep-audit-index.md` artifact after gbrain readback found the full deep audit was too large/unreliable as a retrieval target. Future cycles write both full forensic artifacts and a short gbrain-friendly index. No new LESSON (RULE ZERO).
- 2026-05-14: v1.0.10 -> v1.0.11. Added the Satory-only deep Todoist task/comment/proof audit and wired it into every control-plane cycle after the register export. The audit enumerates all active Satory tasks and comments, exposes factory routes, and blocks close/delete unless Notion + Google Drive proof exists. No personal Todoist projects are read into the factory mutation/export surface. No new LESSON (RULE ZERO).
- 2026-05-14: v1.0.9 -> v1.0.10. Re-audited Gmail GitHub notifications and confirmed the May 13 failure storm was `Codex Landed Commit Loop` running `openai/codex-action` on generated operational commits and failing with `Quota exceeded`. Removed all push triggers and repo-variable/commit-message gates from the paid landed-review workflow; it is now manual `workflow_dispatch` only, with a regression guard that fails if push gating returns.
- 2026-05-13: v1.0.8 -> v1.0.9. Added AP-11 and the hourly `com.nous.todoist-comment-sweep` lane after Madi clarified that Todoist comments must become factory work, not just daily reminder text. Hermes now treats stale comment-loop status as a sweep kick condition, while daily reminders remain once per day. No new LESSON (RULE ZERO).
- 2026-05-13: v1.0.0 created. Codified the 3-hour Air control-plane loop for Notion mirror, Todoist hard gates, substrate probes, factory no-drift, LangSmith smoke, weekly model bakeoff, GitHub mirror push, and Telegram receipts.
- 2026-05-13: v1.0.0 -> v1.0.1. Dry-run proof found three control-loop bugs before launchd install: Notion dry-run emits a trailing `DRY_RUN_OK`, Todoist full audit can exceed 120s, and Air-local `factory_no_drift_probe.sh` must not SSH to Air. Patched the loop parser/timeouts and made the factory probe Air-aware.
- 2026-05-13: v1.0.1 -> v1.0.2. First live launchd cycle wrote/pushed receipts but exited nonzero because the wider substrate status was `blocked` on Nous-GPU. Patched exit semantics so launchd reports runner health, while the status page reports operational blockers.
- 2026-05-13: v1.0.2 -> v1.0.3. Gmail/GitHub audit found `Codex Landed Commit Loop` firing on every generated main push and failing in `openai/codex-action` with `Quota exceeded`. Added an opt-in GitHub Actions gate, generated-commit skips, and `tools/test_codex_landed_workflow_gate.py` so routine sync commits no longer burn GPT quota or spam email.
- 2026-05-13: v1.0.3 -> v1.0.4. Control-plane Telegram reported `blocked` then `done` four minutes later because the optional Nous-GPU collector was red while Todoist/Notion/LangSmith/GitHub were green. Added AP-4 and patched the substrate probe to make GPU collector red block only GPU-bound runs (`NOUS_GPU_REQUIRED=1`).
- 2026-05-13: v1.0.4 -> v1.0.5. Added `tools/todoist_control_plane_export.py`, the per-task Todoist register artifacts, and loop wiring after finding that aggregate hard-gate green did not expose work to humans/agents. Also codified Drive write proof after connector import failed with 403 and `rclone` had an empty token; Drive blocker task `6gf3mQ3gFj4HFQhH` now tracks the OAuth reconnect.
- 2026-05-13: v1.0.6 -> v1.0.7. Added AP-8 and the daily human-owner reminder lane after Madi clarified that Daniyar/Assylbek/Madi tasks must be pinged once per day until updated, while OpenClaw handles agent work and Hermes supervises freshness. No new LESSON (RULE ZERO).
- 2026-05-13: v1.0.7 -> v1.0.8. Added AP-9/AP-10 after the factory emitted false `github_mirror` reds from Air-local lag and Madi caught global Todoist cleanup touching personal projects. Patched `factory_no_drift_probe.sh`, Hermes, and the Todoist control-plane scripts to classify `air_sync_lag` separately and enforce Satory-only mutation/export scope. No new LESSON (RULE ZERO).
- 2026-05-13: v1.0.5 -> v1.0.6. Added `pages/systems/todoist-context-enrichment-queue.md` so the 104 contextless Todoist tasks become Russian, source-backed factory instructions instead of fake note filler.
