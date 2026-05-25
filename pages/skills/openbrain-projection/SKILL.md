---
tier: 2
type: skill
name: openbrain-projection
id: SKILL-OPENBRAIN-PROJECTION
version: 1.4.5
last_updated: 2026-05-21
status: active
description: "v1.4.5 — OpenBrain projection doctrine for Nate B. Jones/OB1-style OpenBrain MCP captures: mirror durable captures into Obsidian, make projection failures visible, dedupe identical content, redact credential-shaped captures before wiki write, preserve clear retrieval titles/H1s, and verify the Obsidian -> git -> gbrain -> OpenClaw path. AP-14 makes projection titles use a concise pre-colon operator summary instead of truncating sentences, so regenerated files remain library-grade. AP-13 forces curl HTTP/1.1 for SSE JSON-RPC calls after Air/Mac dry-runs failed with HTTP/2 framing errors while the same request succeeded with `--http1.1`. AP-12 requires ingester-touched skills to carry `last_updated`, not only `date`. AP-11 keeps automation-facing CLI flags in the ingester parser. AP-10 closes prose-form credential reintroduction; AP-1..AP-9 cover projection-runner failure modes."
triggers:
  - "OpenBrain projection"
  - "OpenBrain bridge"
  - "projection gap"
  - "capture_thought mirror"
  - "OpenBrain to Obsidian"
  - "OpenBrain to gbrain"
  - "openbrain-projection"
  - "Nate B Jones OpenBrain"
tools: [Bash, Read, Edit, mcp__open_brain__*, mcp__gbrain__*]
mutating: true
related: [library-grade-audit, factory-ops, session-coordination, gbrain-ops, architecture-quickref]
tags: [skill, openbrain, projection, obsidian, gbrain, openclaw, bridge, 2026-05-11]
title: "openbrain-projection v1.4.5"
---

# openbrain-projection v1.4.5

## Purpose

OpenBrain captures are useful only when they leave the transient MCP/database lane and become retrievable by the durable substrate: Obsidian files, VPS-bare git sync, gbrain retrieval, and OpenClaw readable mounts.

This skill owns that projection path. It exists because the original GitHub Contents API plan did not match the live topology: the canonical wiki remote is the self-hosted VPS bare repo, not GitHub.

## Current architecture

- Capture source: OpenBrain MCP `capture_thought` / `list_thoughts`.
- Projection runner: `tools/openbrain_project_to_wiki.py`.
- Scheduler: Air LaunchAgent `com.nous.openbrain-projection`, every 5 minutes at staggered minutes `2,7,12,...,57`.
- Output path: `pages/inbox/openbrain/YYYY-MM-DD/openbrain-<openbrain_uuid>.md`.
- Canonical sync: Air wiki -> VPS bare `main` -> Mac/VPS working copies -> gbrain/OpenClaw.
- Secret storage: Air-only `~/nous-agaas/secrets/openbrain-projection.env`; never commit the MCP URL or key.

## Projection file contract

Every projected file must have frontmatter fields:

- `openbrain_id`
- `content_hash`
- `source: openbrain`
- `created_at`
- `projected_at`
- `correlation_id`
- `status: projected`

The filename uses the full OpenBrain UUID. If the MCP ever stops exposing IDs, the runner must fail with `projection_failed` rather than invent weak IDs.

## Verification chain

For a live canary:

1. `mcp__open_brain__capture_thought` returns a row ID.
2. Air runner log reports `created: 1`, `projection_failed: false`.
3. The mirror file exists under `pages/inbox/openbrain/YYYY-MM-DD/`.
4. 4-way HEAD parity is Mac = Air = VPS working copy = VPS bare.
5. `gbrain search "<canary>"` and semantic `gbrain query "<canary intent>"` return the mirror path.
6. `docker exec openclaw cat /opt/nous-agaas/wiki/<path>` reads the same content.
7. Duplicate capture of identical content reports `duplicate_content` and creates no second mirror file.

## Anti-Patterns

### AP-1 - GitHub Contents API over the wrong source of truth

Do not write OpenBrain projection to GitHub unless a GitHub-to-VPS-bare sync path has already been proven by a canary. Current canonical memory is the VPS bare repo. GitHub was not in the sync chain on 2026-05-11.

Detector: `git remote -v` in the wiki shows only `vps`/`origin` pointing at `root@65.108.215.200:/root/nous-agaas/obsidian-wiki.git`.

Fix: use the Air/VPS runner path.

### AP-2 - Projection failures hidden as log-only success

`capture_thought` succeeding does not prove projection. The runner must emit JSON with `projection_failed: true|false`, counts, and per-row statuses. A failed projection is a red audit row, not a swallowed warning.

Detector: any run lacking `projection_failed` in stdout/logs is not acceptable proof.

Fix: run `python3 tools/openbrain_project_to_wiki.py --wiki . --dry-run --json`.

### AP-3 - UUID-only idempotency creates duplicate mirrors

OpenBrain may return a new UUID for identical content. Filename idempotency by UUID alone therefore creates duplicate mirror files.

Detector: duplicate capture of the same canary content must result in `duplicate_content: 1` and `duplicate_uuid_file_count=0`.

Fix: keep `content_hash` as the duplicate guard while preserving full UUID filenames for non-duplicate captures.

### AP-4 - LaunchAgent Python does not match interactive Python

macOS LaunchAgents can run `/usr/bin/python3`, which may lack `tomllib` or other modules present in Homebrew Python.

Detector: `~/nous-agaas/logs/openbrain-projection/err.log` shows `ModuleNotFoundError: No module named 'tomllib'`.

Fix: plist uses `/usr/bin/env python3` with PATH set; runner also tolerates missing `tomllib` when the Air secret env file is present.

### AP-5 - Direct gbrain sync over SSH misses embedding secrets

Calling `/opt/nous-agaas/gbrain/bin/gbrain sync` directly over SSH can miss `OPENAI_API_KEY` and falsely report sync failure.

Detector: `OPENAI_API_KEY environment variable is missing or empty` in sync output.

Fix: use `bash tools/gbrain_sync_wrapper.sh` or the installed autopilot wrapper, which loads the VPS embedding environment first.

### AP-6 - Captures are orphans until ingested into a parent skill (24h SLO)

Projection is necessary but not sufficient. A capture that lands in `pages/inbox/openbrain/YYYY-MM-DD/openbrain-<uuid>.md` with no backlink is invisible to gbrain (orphan rule — [[library-grade-audit]] AP-5) and does not compound into the substrate. The learning loop closes only when each capture is linked to one or more parent skills via an evidence-trail entry that contains `[[openbrain-<uuid>]]`.

**Rule:** every OpenBrain capture has a 24-hour ingestion SLO. Within 24h of `projected_at`, the capture must either:
1. Be linked from at least one `pages/skills/<name>/SKILL.md` evidence-trail entry, OR
2. Be marked `deferred` (low-signal capture, manually triaged), OR
3. Be archived if no longer relevant.

**Mechanical detector + auto-linker:** `tools/ingest_openbrain_to_skills.py` runs the loop.

- Reads every orphan in `pages/inbox/openbrain/*/openbrain-*.md`
- Strips OpenBrain chrome (the `# OpenBrain Capture` header + `## Projection` housekeeping section that is identical across every capture and would otherwise mass-false-positive to `openbrain-projection` itself)
- Builds a keyword set per skill from skill name + hyphen-split tokens + frontmatter title (length-≥4, stopword-filtered)
- Counts hits per skill, applies 3-gate rule (top-1 hits ≥2 absolute floor, top1-top2 margin ≥1 for single-skill link, multi-skill link when results are exactly tied at top)
- For each matched skill: detects the trailing log heading (`## Evidence trail` or `## Timeline`), inserts exactly one `- **YYYY-MM-DD openbrain** | <80-char summary> [[openbrain-<uuid>]]` line, bumps `last_updated`, validates YAML round-trip + bounded line-delta + bounded char-delta before write.

**Why keyword frequency instead of gbrain FTS:** gbrain `search` is keyword-based FTS, not semantic. On long capture bodies it returns "No results" (TF-IDF dilution). On short bodies it ranks the capture file itself above any skill page. The 40-skill registry is small enough that local keyword matching against skill names + their split tokens produces deterministic, falsifiable rankings without an external service in the hot path.

**Idempotency:** the script greps every SKILL.md for `[[openbrain-<uuid>]]` before processing — already-linked captures are skipped. Safe to re-run on cron.

**Initial run, 2026-05-14:** 17 orphans scanned → 4 single-linked + 1 multi-linked (5 captures linked, touching 6 SKILL.md files) + 12 deferred (thin captures like first-test pings; correct deferral). Zero YAML failures, zero validation failures.

**Cross-ref:** [[library-grade-audit]] AP-5 (orphan rule that makes ingestion necessary), [[gbrain-ops]] (FTS vs semantic distinction), [[mistake-to-skill]] AP-11 (3-edit ritual — this AP is the 3rd edit alongside the frontmatter bump and Timeline append below).

### AP-7 — Deferred-marker writeback (the AP-6 literal "be marked deferred" was a script-internal label, not file frontmatter)

**Failure mode** caught by [[library-grade-audit]] Gate 7.1 v1.6.0 on day 1 of ship (2026-05-14, peer session s108-mac-97229): AP-6 codified three terminal states for an OpenBrain capture — `linked`, `marked deferred`, `archived`. The original auto-linker in v1.1.0 only WROTE the `linked` state (evidence-line append to a parent SKILL.md). The `deferred` state was a script-internal classification (`deferred:no_keyword_matches`, `deferred:top1_hits_below_floor_1`) that NEVER touched the capture's own frontmatter. Gate 7.1 (orphan rate ≤ 5% over last 7d) read the gap correctly: 12 of 18 captures lived as `status: projected` with no skill-side backlink → **66.67% orphan rate** at the literal doctrine. Session s1729-mac-87156 surfaced this in real-time during the peer's same-session ship.

**Why this matters more than it looks:** AP-6 has THREE terminal states for a reason. `archived` and `deferred` are *intentional* triage outcomes — a low-signal "first test from Claude Desktop" capture SHOULD NOT keep showing up as a fresh-orphan every audit. Without explicit `status: deferred` on the file, every future Gate 7.1 run re-counts the same captures as orphans, even after the auto-linker decided "no skill matches." The library-grade scorecard rots into permanent-RED.

**Rule:** every `deferred:<reason>` decision from `tools/ingest_openbrain_to_skills.py` MUST also write three fields into the capture's own frontmatter:
- `status: deferred` (overrides the `status: projected` set by the projection runner — this is the canonical lifecycle move)
- `deferred_reason: <reason>` (e.g. `no_keyword_matches`, `top1_hits_below_floor_1`, `empty_body`, `margin_hits_below_1`)
- `deferred_at: YYYY-MM-DD`

**Mechanical detector:** `mark_deferred()` helper in `tools/ingest_openbrain_to_skills.py` (added in this skill's v1.2.0 ship). Idempotent — captures already at `status: deferred` are skipped on re-run. JSON summary surfaces three new counters: `deferred_marked` (this run), `deferred_already_marked` (idempotent skip), `deferred_mark_failed` (validation reject).

**Gate 7.1 PASS evidence (post-ship, 2026-05-14):** dry-run after for-real run reports `orphans_scanned=18, linked=0+0=0 new + 6 skipped_already_linked + 12 deferred_already_marked = 18 accounted, 0 unaccounted. Gate 7.1 = 0.00% orphan rate, PASS.`

**Forward gap (intentional, not closed in this AP):** when a `deferred` capture later DOES match a new skill (because a new skill was added or keywords were broadened), the script links it but doesn't currently clear `status: deferred` from the capture frontmatter — the file would carry both a backlink AND `status: deferred`. Mostly harmless for the gate (linked > deferred in the orphan-counting order), but a future v1.3.0 should clear `status: deferred` + `deferred_*` fields on transition to linked. Tracking as a follow-up; not a v1.2.0 blocker.

**Cross-ref:** [[library-grade-audit]] Gate 7.1 + AP-10 (the gate that surfaced this gap on day 1), AP-6 above (the doctrine being completed), [[mistake-to-skill]] AP-11 (3-edit ritual — this AP body is the 3rd edit alongside frontmatter v1.1.0→v1.2.0 + Evidence trail entry below).

### AP-8 — Projection runner clobbers downstream lifecycle state on every cron firing (5-min chase loop)

**Failure mode** caught immediately after AP-7 shipped (2026-05-14, session s1729-mac-87156): even with `tools/ingest_openbrain_to_skills.py` writing `status: deferred` + `deferred_reason` + `deferred_at` into capture frontmatter, the next `com.nous.openbrain-projection` cron firing (every 5 minutes) **clobbered all three fields back to `status: projected`**. Diff of commit `bdf2ba8c` showed the projection runner removed `status: deferred`, `deferred_reason`, and `deferred_at` from a capture I had just marked. Gate 7.1 was therefore in a chase loop: PASS for ~5 minutes after each ingester run, then FAIL when projection cron fires.

**Root cause:** `tools/openbrain_project_to_wiki.py::project_thought()` re-renders a canonical markdown template from the `Thought` dataclass on EVERY pass, then writes if `existing != markdown`. The canonical template hardcodes `status: projected` (line 196 of v1.2.0) and emits no `deferred_*` fields. So any downstream lifecycle annotation makes `existing != markdown` and triggers an overwrite — even though `content_hash` already proves the actual content is unchanged.

**Why this matters more than AP-7:** AP-7 alone would have left Gate 7.1 permanently AMBER — PASS just after every ingester run, FAIL just after every projection cron. The substrate would have looked GREEN on demand but RED-on-cron-cycle. Karpathy-loop axis-2 (mechanical detection) would have caught it eventually, but the chase loop is the kind of false-PASS that erodes trust in the gate.

**Rule:** when `tools/openbrain_project_to_wiki.py::project_thought()` finds an existing file with `status: (deferred | ingested | archived)` AND matching `content_hash`, it MUST short-circuit before re-rendering. The content_hash match already proves the file is canonical at the source-of-truth (OpenBrain MCP) level; the lifecycle state is downstream metadata that the projection runner does NOT own.

**Mechanical detector:** post-AP-8 dry-run of the projection runner after an ingester run reports `would_update=0`. Before AP-8 (i.e. v1.2.0 with manually-marked captures): would have reported `would_update=N` where N = count of deferred captures. The number of would-update operations is the mechanical drift signal.

**Gate 7.1 stability post-AP-8 (2026-05-14):** orphans_scanned=19, linked_effective=6, deferred_on_disk=13, new_marks=0, unaccounted=0 → 0.00% PASS. Projection runner dry-run: `would_update=0, exists=19`. Loop closed; substrate is steady-state stable across cron firings.

**Forward consideration (not closed in this AP):** the same chase-loop pattern would apply to a future `status: ingested` or `status: archived` lifecycle move. AP-8 already covers all three states in the regex. If a NEW status value is ever introduced (e.g. `status: superseded`), the regex must be updated in lockstep. Cross-ref this AP in the relevant lifecycle skill at that time.

**Cross-ref:** AP-7 above (the writeback that this AP protects), [[library-grade-audit]] Gate 7.1 (the gate this AP keeps green across cron cycles), [[mistake-to-skill]] AP-11 (3-edit ritual — this AP body is the 3rd edit alongside frontmatter v1.2.0→v1.3.0 + Evidence trail entry below).

### AP-9 — OpenBrain projection must redact credential-shaped thoughts before wiki write

**Failure mode** caught during the 2026-05-18 auto-checkpoint incident repair: the Telegram inbox writer had already learned to redact `IP admin <password>` text, but the OpenBrain projection runner re-rendered the same captured thought from OpenBrain MCP and wrote the credential back into `pages/inbox/openbrain/...`. The VPS pre-receive hook correctly rejected the checkpoint push, which proved the branch was not safe even though the Telegram writer was fixed.

**Root cause:** `tools/openbrain_project_to_wiki.py::render_markdown()` wrote `thought.content` verbatim. OpenBrain is a second memory ingress path, so fixing only `telegram_ingest_persist.py` left a parallel write path that could reintroduce secrets.

**Rule:** projection runners must redact credential-shaped text before rendering markdown body or title. At minimum, redact:
- `password|pass|pwd|пароль|token|secret|api_key` key-value forms.
- Camera/APK shorthand like `<ip> admin <password>`.
- Normalized model summaries like `admin/<password>`.
- Standalone `admin <password>` when the second token looks secret-like.

**Mechanical detector:** `python3 -m pytest tools/tests/test_openbrain_project_to_wiki.py -q` includes `test_projection_redacts_camera_credentials`, proving rendered markdown contains `[REDACTED]` and not the original secret tokens across space-form, slash-form, and key-value credentials.

**Cross-ref:** [[command-center]] AP-39 (Telegram inbox redaction) and [[camera-management]] AP-21 (camera credentials never belong in git history).

### AP-10 — Redact prose-form credential mentions, not only key-value credentials

**Failure mode** caught during the 2026-05-19 one-beam Satory queue closeout: AP-9 correctly redacted `password: value`, `<ip> admin <password>`, and `admin/<password>`, but an OpenBrain projected note still carried a human prose phrase shaped like `Hikvision pwd <secret>`. The tip tree was easy to redact manually, but Air's OpenBrain projection cron re-rendered the source thought and auto-sync pushed the bad ancestry back to VPS/GitHub.

**Root cause:** `tools/openbrain_project_to_wiki.py::redact_sensitive_text()` treated `pwd` as a key only when followed by `:` or `=`, not when used as an inline noun followed by a secret token. AP-9's detector did not include that prose form, so the regression suite was green while the live source leaked.

**Rule:** projection redaction must cover both machine-ish key-value forms and operator prose forms:
- `password|pass|pwd|пароль|token|secret|api_key: <secret>`
- `password|pass|pwd|пароль|token|secret|api_key <secret>`
- existing AP-9 camera shorthand and `admin/<password>` forms.

**Mechanical detector:** `python3 -m pytest tools/tests/test_openbrain_project_to_wiki.py -q` now includes a synthetic `Hikvision pwd ExamplePwd_2026` fixture and asserts the rendered markdown contains `pwd [REDACTED]` and never the original token.

### AP-11 — Automation-facing CLI flags must be accepted by the parser, not only written in plans

**Failure mode** caught during the 2026-05-20 substrate golden audit implementation: the approved acceptance plan required `python3 tools/ingest_openbrain_to_skills.py --dry-run --json`, but the ingester parser only accepted `--dry-run` and `--limit`. The script already emitted JSON, so the failure was not ingestion logic; it was CLI contract drift between the documented gate and the executable parser.

**Rule:** every flag used by an audit/acceptance command for OpenBrain projection or ingestion must be owned by the corresponding tool parser, even when the flag is a compatibility no-op. A plan-only flag is a false gate: the workflow fails before checking the substrate.

**Mechanical detector:** `python3 -m pytest tools/tests/test_ingest_openbrain_to_skills_cli.py -q` runs `ingest_openbrain_to_skills.py --dry-run --json --limit 1`, asserts exit code is not argparse error `2`, and parses stdout as JSON.

### AP-12 — Ingester-touched skills need `last_updated`, not only `date`

**Failure mode** caught during the 2026-05-20 substrate golden closure: `tools/ingest_openbrain_to_skills.py --dry-run --json` linked and deferred captures correctly, but full-corpus validation still returned `errors=1` because `pages/skills/multi-model-consult/SKILL.md` had `date: 2026-05-20` and no `last_updated`. The skill looked fresh to a human, but the automation gate checks the field that runtime skills use for freshness.

**Rule:** every skill touched or validated by the OpenBrain ingester must carry `last_updated: YYYY-MM-DD` in frontmatter. `date` is creation/history metadata, not freshness metadata. Do not weaken the validator to accept `date` as a fallback; fix the skill metadata.

**Mechanical detector:** `python3 tools/ingest_openbrain_to_skills.py --dry-run --json` must return `errors: 0` and an empty `validation_failures` list before any OpenBrain ingestion closeout can be called green.

### AP-13 — OpenBrain SSE JSON-RPC must force HTTP/1.1 when curl hits HTTP/2 framing errors

**Failure mode** caught during the 2026-05-21 library sync audit: both Mac and Air `python3 tools/openbrain_project_to_wiki.py --wiki . --dry-run --json --limit 20 --days 7` failed with `curl rc=16: HTTP2 framing layer`, while the same `list_thoughts` JSON-RPC body succeeded on Air when curl used `--http1.1`.

**Root cause:** the OpenBrain MCP endpoint speaks SSE-style responses reliably over HTTP/1.1 in this environment, but curl may negotiate HTTP/2 and then fail before the projection runner can parse the response. Treating that as an OpenBrain data failure leaves `com.nous.openbrain-projection` red even though the backend is reachable.

**Rule:** all projection-runner curl calls to the OpenBrain SSE JSON-RPC endpoint must include `--http1.1`. Do not hide this behind retry churn; the protocol choice is the root cause.

**Mechanical detector:** `python3 -m pytest tools/tests/test_openbrain_project_to_wiki.py -q` includes `test_mcp_call_forces_http11_for_sse_endpoint`, and live closeout must re-run `python3 tools/openbrain_project_to_wiki.py --wiki . --dry-run --json --limit 20 --days 7`.

### AP-14 — Projection titles and H1s must be retrieval-grade, not truncated sentence stubs

**Failure mode** caught during the 2026-05-21 residual cleanup closeout: the OpenBrain capture was successfully mirrored into Obsidian, but `tools/openbrain_project_to_wiki.py` generated `title: "2026-05-21 residual cleanup: Codex repaired Nous AGaaS substrate residu..."` and `# OpenBrain Capture - 2026-05-21`. Manual cleanup was not durable because the projection runner can regenerate the file.

**Root cause:** the title generator only truncated the first 72 characters of body text, and the H1 ignored the generated title entirely. For retrieval/library behavior, the stable title must be a concise subject, not a clipped sentence or generic capture label.

**Rule:** projection titles must prefer the concise pre-colon operator summary when present, and the H1 must match that title. When the first sentence is clear but bloated by implementation details in parentheses, strip the long trailing parenthetical before falling back to truncation. Only fall back to truncation when the capture has no clear summary prefix or concise first sentence. Manual edits to generated OpenBrain files are not the durable fix; patch the renderer.

**Mechanical detector:** `python3 -m pytest tools/tests/test_openbrain_project_to_wiki.py -q` asserts a capture like `KEONA / SPECTRA latest email correction, 2026-05-11: ...` renders both frontmatter title and H1 as `KEONA / SPECTRA latest email correction, 2026-05-11`, and long parenthetical implementation details do not force a clipped title.

## Evidence trail

- **2026-05-21** | v1.4.4 -> v1.4.5 — Absorbed **AP-14** after the residual cleanup OpenBrain projection generated a truncated title and generic H1, then regenerated over a manual title cleanup. Patch: `title_from_content()` now prefers concise pre-colon summaries, strips long trailing parentheticals from otherwise clear first-sentence titles, and `render_markdown()` uses that title as H1; regression pins frontmatter title and H1. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/openbrain-projection/skill.
- **2026-05-21** | v1.4.3 -> v1.4.4 — Absorbed **AP-13** after OpenBrain projection dry-runs failed on Mac/Air with `curl rc=16: HTTP2 framing layer`; Air counter-check of the same JSON-RPC body succeeded with `--http1.1`. Patch: force HTTP/1.1 in `call_mcp_tool()` and add a regression that asserts curl receives `--http1.1`. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/openbrain-projection/skill.
- **2026-05-20** | v1.4.2 -> v1.4.3 — Absorbed **AP-12** after the substrate golden closure found full-corpus OpenBrain ingestion validation failing on `multi-model-consult`: the skill had `date: 2026-05-20` but no `last_updated`, so the validator correctly returned `last_updated_not_today_got=none`. Patch: add `last_updated: 2026-05-20` to the skill and codify that ingester-touched skills must use `last_updated` as freshness metadata. No new LESSON (RULE ZERO).
- **2026-05-20** | v1.4.1 -> v1.4.2 — Absorbed **AP-11** after the substrate golden audit acceptance command exposed parser drift: `tools/ingest_openbrain_to_skills.py` emitted JSON but rejected the plan-required `--json` flag. Patch: accept `--json` as an automation compatibility no-op and add `tools/tests/test_ingest_openbrain_to_skills_cli.py` to prove the command parses and returns JSON. No new LESSON (RULE ZERO).
- **2026-05-19** | v1.4.0 -> v1.4.1 — Absorbed **AP-10** after Air's OpenBrain projector reintroduced a prose-form credential phrase while the one-beam Satory queue branch was being synced. Patch: `redact_sensitive_text()` now redacts `pwd <secret>` / `password <secret>` style prose forms; regression extends `test_projection_redacts_camera_credentials` with a synthetic `Hikvision pwd ExamplePwd_2026` fixture. No new LESSON (RULE ZERO).
- **2026-05-18** | v1.3.0 → v1.4.0 — Codex shipped **AP-9** after manual auto-checkpoint no longer crashed but failed VPS push because OpenBrain projection reintroduced a Telegram-posted APK credential into `pages/inbox/openbrain`. Fix: `tools/openbrain_project_to_wiki.py` redacts credential-shaped content before markdown render; regression `test_projection_redacts_camera_credentials` covers camera/APK shorthand, normalized slash-form summaries, and key-value password forms. No new LESSON (RULE ZERO).
- **2026-05-14** | v1.2.0 → v1.3.0 — session s1729-mac-87156 shipped **AP-8** (projection-preserves-non-projected-status). 4-line patch to `tools/openbrain_project_to_wiki.py::project_thought()`: when an existing file has `status: (deferred | ingested | archived)` AND content_hash matches the new Thought, short-circuit before re-rendering. Closes the 5-minute projection/ingestion chase loop diagnosed when the post-AP-7 verification revealed `bdf2ba8c openbrain: project captured thoughts` had clobbered all 12 status:deferred markers within ~10 minutes of my AP-7 commit. Post-AP-8 verification: ingester re-marks 13 captures, projection dry-run reports `would_update=0 exists=19`, Gate 7.1 = 0.00% PASS and STABLE across cron firings. 3-edit ritual: frontmatter v1.2.0→v1.3.0 + AP-8 body + this entry. No new LESSON (RULE ZERO).
- **2026-05-14** | v1.1.0 → v1.2.0 — session s1729-mac-87156 shipped `mark_deferred()` in `tools/ingest_openbrain_to_skills.py` + **AP-7** (deferred-marker writeback). Triggered by [[library-grade-audit]] Gate 7.1 reading 66.67% orphan rate on day 1 of peer's v1.6.0 ship: AP-6 literal said "be marked deferred" but v1.1.0 only tracked deferred as a script-internal counter. v1.2.0 writes `status: deferred` + `deferred_reason: <reason>` + `deferred_at: <today>` into 12 capture frontmatters (the deferred set from today's run); idempotent on re-run. Post-ship verification: Gate 7.1 = 0.00% orphan rate, PASS (18 captures = 0 new-linked + 0 new-multi + 6 skipped_already_linked + 12 deferred_already_marked + 0 unaccounted). 3-edit ritual: frontmatter v1.1.0→v1.2.0 + AP-7 body + this entry. No new LESSON (RULE ZERO).
- **2026-05-14 openbrain** | OpenBrain Capture - 2026-05-14 Round-2 ship 2026-05-14 s108-mac-74559 — OpenBra… [[openbrain-66a969be-9528-4752-b567-7bd03a76fa1b]]
- **2026-05-14** | v1.0.0 → v1.1.0 — session s108-mac-74559 shipped `tools/ingest_openbrain_to_skills.py` + **AP-6** (24h ingestion SLO + auto-link rule). Initial run: 17 orphans → 5 linked (4 single + 1 multi) + 12 deferred (thin captures). 6 SKILL.md files received evidence-trail entries (this skill, autonomous-build-manager, satory-daily-operator-brief, control-plane-sync, session-coordination, and this skill again via the canary capture). Zero YAML failures, zero validation failures. Closes the OpenBrain write-only-capture gap diagnosed in the round-2 audit. 3-edit ritual: frontmatter v1.0.0 → v1.1.0 + AP-6 body + this timeline entry. gbrain-timeline-ok pending push. No new LESSON (RULE ZERO).
- **2026-05-14 openbrain** | OpenBrain Capture - 2026-05-11 SUBSTRATE_CANARY_2026-05-11_OPENBRAIN_PROJECTION… [[openbrain-82b0b7ab-c7aa-4cdc-b6b7-2dfe8d5bc825]]
- **2026-05-14 openbrain** | OpenBrain Capture - 2026-05-11 KEONA / SPECTRA source-of-truth closeout 2026-05… [[openbrain-0ba58441-f774-4dc1-854c-83ef9eaeb31f]]
- **2026-05-11** | v1.0.0 created. Codex implemented the Air/VPS projection runner, patched OpenBrain MCP list/capture output to expose UUIDs, backfilled 12 captures, installed `com.nous.openbrain-projection` on Air, and proved canary `82b0b7ab-c7aa-4cdc-b6b7-2dfe8d5bc825` through Obsidian, VPS bare git, gbrain exact/semantic retrieval, and OpenClaw. Duplicate capture produced a second OpenBrain row but no second mirror file because the runner reported `duplicate_content`.

## See also

- [[library-grade-audit]]
- [[factory-ops]]
- [[session-coordination]]
- [[gbrain-ops]]
- [[architecture-quickref]]
