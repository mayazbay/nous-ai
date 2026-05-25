---
tier: 2
type: skill
name: library-graph
id: SKILL-LIBRARY-GRAPH
title: "Library Graph — unified Obsidian + gbrain + OpenBrain"
version: 1.5.3
status: active
date: 2026-05-20
last_updated: 2026-05-22
description: "Ship 3 doctrine for the unified library graph: canonical ULID registry, embed-on-write hook, Voyage-3-lite vector index in sqlite-vec, RRF cross-system search (Obsidian + gbrain + OpenBrain), bidirectional OpenBrain sync, link/title canonicalization with multi-match human triage, library-health snapshot, parity-manifest extension. AP-10 requires queue/index backlog to be reported as yellow, not golden, even when Obsidian/gbrain/OpenBrain probes are otherwise green. AP-11 requires a real launchd drain path and rate-limit deferral so one Voyage 429 does not fan out across the whole queue. AP-12 requires registry update operations to be value-idempotent so daemon passes cannot create timestamp-only git dirt. AP-13 requires residual-only queue compaction, live Voyage dimension detection, and free-tier pacing before claiming backlog repair. AP-14 requires the daemon to git-writeback tracked registry changes so readiness gates do not keep red-drifting after every drain slice. AP-15 requires writeback commits to use path-scoped --only so unrelated staged work cannot bleed into daemon commits. AP-16 allows local embedding backlog drain when Voyage is rate-limited pending billing upgrade. Use when writing into the vault, debugging title drift / broken wikilinks, extending the embed pipeline, adding a new search source, or auditing whether retrieval is actually working."
absorbs_laws: []
absorbs_lessons: []
tags: [skill, library-graph, ship-3, embeddings, canonical-uuid, voyage, sqlite-vec, 2026-05-20]
source_count: 0
related: [model-failover, lane-lock, mistake-to-skill, musk-algorithm, openbrain-projection]
---

# library-graph v1.5.3

## Why this exists

Before Ship 3, the three knowledge systems were isolated lies:

- **Obsidian vault** was healthy but isolated (3,043 markdown files, no cross-system search).
- **gbrain** was a directory cache of 45 skill names that printed "embedded N chunks" without embedding anything. The audit called this "embedding theatre."
- **OpenBrain** (Nate B Jones MCP) worked but was a parallel universe — 39 thoughts that didn't link to anything in the vault.

There was no canonical title. The same concept appeared as `MODEL-FAILOVER-LATEST.md` in Obsidian, `model-failover-latest` as a hypothetical gbrain slug, and absent from OpenBrain entirely. No search router. No bidirectional sync. The user's directive was: "go atomic, golden, no lies."

Ship 3 deleted the theatre and built three connected layers:

- **Source of truth**: the Obsidian vault git repo.
- **Derived vector index**: `.gbrain/index.db` (sqlite + sqlite-vec extension), populated by the embed-on-write pipeline.
- **Atomic-thought log**: OpenBrain remains the peer system; bidirectional sync via `library_openbrain_sync`.

Joined by `canonical_uuid` (ULID, lexicographic-sortable, deterministic).

## Current rules

- Every `pages/**/*.md` write triggers `.git/hooks/post-commit` (non-blocking) → appends to `.gbrain/queue.jsonl`. The `com.nous.library-graph` launchd daemon drains in bounded slices under provider rate limits.
- Embedding model: `voyage-3-lite` (live response currently 512-dim, $0.02/1M tokens) via `~/.nous/secrets/voyage.env`. Fallback: `all-MiniLM-L6-v2` local (384-dim, requires `sentence-transformers`). Final fallback: `EmbedderStub` (deterministic synthetic vectors for tests).
- `pages/systems/canonical-registry.jsonl` is append-only JSONL; current state = last row per ULID. Idempotent `add(path)` returns existing UUID for known paths, and `update_field(uuid, field, value)` must no-op when the current value already equals `value`.
- Cross-system search via `tools/library.py search "<q>"`: parallel queries (Obsidian ripgrep + gbrain sqlite-vec cosine + OpenBrain MCP), deduplicated by canonical_uuid, fused via Reciprocal Rank Fusion (RRF k=60).
- Bidirectional OpenBrain sync: `tools/library_openbrain_sync.py --direction both`. Up = vault → MCP capture_thought (fire-and-forget). Down = MCP search_thoughts tag=`nous-vault-inbox` → `pages/inbox/openbrain/<date>-<id>.md` with `status: needs-promotion` for human triage.
- Title drift and broken wikilinks are surfaced (not auto-fixed) by `library_canonicalize_titles.py` and `library_repair_links.py`. Audits land in `pages/library/` (NOT `pages/audits/` which is peer scope). Auto-rewrite only on single-canonical-match; multi-match or unknown → human review.
- Health snapshot at `pages/systems/library-health.json` + `LIBRARY-HEALTH.md` (rendered by `library_health.py`); fail-soft for every field.
- Parity manifest extended at `pages/systems/parity-manifest.txt` includes the 4 Ship-3 spine paths. Drift detection via `tools/parity_check.py --verify` after every git pull on Air/VPS.
- "Golden library" claims require backlog truth: `python3 tools/library_health.py --no-write --json` must report the queue/index state, and a large `.gbrain` queue or low indexed-chunk coverage is YELLOW even when Obsidian git, gbrain doctor, QMD freshness, and OpenBrain projection are green.

## Anti-Patterns

### AP-1: Embedding theatre

**Symptom:** A log line says "embedded N chunks" when N is zero or when no actual vector store write happened. Downstream callers trust the receipt; debugging takes hours because the success line was a lie.

**Why this happened:** The original gbrain shell at `~/.claude/skills/gstack/.gbrain/skills/` was 45 empty skill-name directories masquerading as a vector index. Its embed function printed counts unconditionally at the end of the function body, never checking whether anything actually landed in a `vec_chunks_*` table.

**Fix:** Never print "embedded N chunks" when N is zero or when no actual vector store write happened. If your code claims a count, it must back it up with a write to `vec_chunks_<dim>` and verify with a follow-up `SELECT COUNT(*)`. The Ship 3 embed pipeline (`library_embed_db.upsert_chunks`) returns the row count it actually wrote; the caller logs that number, not a hardcoded one.

### AP-2: Embed-on-write hook blocks commits

**Symptom:** `git commit` hangs for 5+ seconds (or fails outright) because the post-commit hook is waiting on Voyage API, on a write-locked queue file, or on a missing Python interpreter.

**Why this happened:** Hook authors naturally write the "happy path" — Voyage up, queue writable, Python on PATH — and forget that post-commit runs on every commit, including commits made when the network is down, the disk is full, or Python isn't installed (e.g. during a rebase on a stripped-down recovery environment).

**Fix:** Post-commit MUST exit 0 in ~10ms even when Voyage is down, the queue file is unwritable, or anything else fails. Latency budget is hard. The daemon will pick up next pass. Wrap every operation in `try` and fall through to `exit 0`. Never `wait` on a subprocess inside the hook.

### AP-3: Synchronous OpenBrain capture from a vault-write path

**Symptom:** A vault write blocks for 5-30 seconds while OpenBrain MCP is slow or down; the user retries the write, doubling the load on the already-slow side-channel; the original write never completes.

**Why this happened:** Same shape as Ship 1's failover OpenBrain capture (AP-4). A `subprocess.run(..., timeout=...)` or `.wait()` call inside a vault-write helper makes the vault write depend on MCP availability.

**Fix:** Same rule as Ship 1: fire-and-forget via `subprocess.Popen(start_new_session=True)`, output to `logs/openbrain-sync.log`. Never `.wait()`. Vault writes must never depend on MCP availability. `library_openbrain_sync.up_one` always returns immediately after spawning; the spawned subprocess inherits the env but is fully detached.

### AP-4: Auto-rewriting multi-match wikilinks

**Symptom:** `library_repair_links.py` rewrites `[[factory-ops]]` to `[[pages/systems/factory-ops]]` silently, even though `pages/skills/factory-ops.md` is equally valid as a canonical target. The peer skill page is now orphaned; the audit trail loses a backlink; nobody notices until a future search returns "0 hits" for `factory-ops`.

**Why this happened:** Naive link-repair scripts pick the first canonical match they find. With two equally-valid targets, "first" is order-dependent on the filesystem listing — a non-determinism that is worse than the original broken link.

**Fix:** NEVER pick one silently when a wikilink resolves to multiple canonical entries. The `factory-ops` case (`pages/systems/factory-ops.md` vs `pages/skills/factory-ops.md`) is the canonical example. Always surface multi-match in `pages/library/broken-links-YYYY-MM-DD.md` for human triage. Auto-rewrite ONLY on single-canonical-match.

### AP-5: Skipping content_hash dedup

**Symptom:** Every `library_drain_queue` pass re-embeds every queued file, even files whose content hasn't changed since the last embed. Voyage credits burn for nothing; the parity manifest hash flips on every run because the registry's `last_embedded_at` timestamp updates.

**Why this happened:** Drain authors model the queue as "embed everything you see" and skip the dedup check because "the queue should be small". In reality the queue can spike (e.g. after a bulk import) and re-embedding 700 unchanged files costs real money.

**Fix:** `library_drain_queue.drain_once` MUST skip files whose `content_hash` already matches the registry entry's `content_hash` AND the entry has been embedded (`embed_dim > 0`). Re-embedding unchanged files wastes Voyage credits and bumps the parity hash unnecessarily. Idempotency is the contract.

### AP-6: Truncating the queue on partial failure

**Symptom:** Drain pass embeds 50 of 100 queued files, then hits a Voyage 429 rate-limit; the drain handler "cleans up" by truncating `.gbrain/queue.jsonl`; the remaining 50 files are now lost from the queue and never get embedded; only a future write to those files will re-queue them.

**Why this happened:** Naive cleanup logic treats "drain pass complete" as "queue empty" and truncates unconditionally. The right model is "queue contains the residual; truncate ONLY when the residual is empty."

**Fix:** If any file's embed returns `auth_missing` (Voyage key absent) OR any error occurs, preserve the failed/current row plus unhandled residual rows for the next pass. Truncate only when no residual remains. Better to embed slowly than to lose work, but do not retry already-handled rows forever.

### AP-7: gbrain shell resurrection

**Symptom:** Someone notices `~/.claude/skills/gstack/.gbrain/skills/` is gone and "fixes" it by recreating the directory tree. Now the agent has two competing gbrains: the real `.gbrain/index.db` (sqlite-vec) and the empty directory cache. Search hits the empty one first.

**Why this happened:** The original gbrain path was wired into agent skills and CLI tools; deleting it broke discoverability for callers who hadn't been updated. A well-meaning fix recreates the directory rather than redirecting the callers.

**Fix:** Never recreate `~/.claude/skills/gstack/.gbrain/skills/` as a directory cache. The real index lives at `<vault>/.gbrain/index.db`. The legacy path is archived at `skills.archived-ship3-<date>/` with a README pointing readers to the real one. If you find a caller still hitting the legacy path, fix the caller — do not regenerate the lie.

### AP-8: Canonical UUID generation from a path

**Symptom:** A file gets renamed (e.g. `MODEL-FAILOVER.md` → `model-failover.md`) and every backlink to its UUID breaks because the UUID was derived from the path (`sha256(path)`). The new path generates a new UUID; the registry now has two rows for the same logical entity; deduplication code can't tell they're the same.

**Why this happened:** UUID-from-path looks attractive (no need to persist anything; pure function of input) but it conflates identity with location. Files move; identity shouldn't.

**Fix:** ULIDs are random + monotonic — they survive file renames. If you derive UUIDs from paths (e.g., `sha256(path)`), every rename creates a new identity and breaks every backlink. Always use a randomness-backed ULID. `library_canonical_registry.add(path)` mints a fresh ULID on first sight and pins it to the path; subsequent renames update the `path` field on the same ULID row.

### AP-9: Generated library dashboards and top-level skills must be resolver-grade

**Symptom:** The 2026-05-21 library quality gate reported blocking issues even though the underlying files existed: `pages/systems/LIBRARY-HEALTH.md` had no YAML frontmatter/title, and several top-level skills were missing from `pages/skills/_gbrain/RESOLVER.md`.

**Root cause:** the dashboard renderer optimized for human markdown and forgot the vault metadata contract; new skills were useful by path but invisible to the resolver-based runtime. This creates a bad library: humans can browse it, but agents cannot retrieve it reliably.

**Rule:** every generated Tier-A dashboard must render valid YAML frontmatter with at least `type`, `id`, `title`, `date`, and `status`. Every top-level skill under `pages/skills/<name>/SKILL.md` must have a resolver trigger unless it is intentionally private/deprecated and listed as an exception.

**Mechanical detector:** `python3 tools/library_quality_scan.py --json` must report `blocking_count=0` for resolver and metadata gates after any library graph change. `python3 -m pytest tools/tests/test_library_health.py -q` proves `LIBRARY-HEALTH.md` renders frontmatter.

### AP-10: Queue backlog is a library-golden blocker, not a harmless detail

**Symptom:** A cross-surface audit calls Obsidian/gbrain/QMD/OpenBrain "golden" while `library_health.py` still reports hundreds of pending queue entries and only a small sqlite-vec chunk count. Runtime search may work for old or lucky documents, but the unified library graph is not caught up.

**Root cause:** The system has multiple retrieval layers. It is easy to prove each surface separately and miss the derived local index backlog. That creates a false-green: OpenBrain projection can be current, QMD embeddings can be fresh, and VPS gbrain doctor can be 100/100 while the local library graph still has delayed embed-on-write work.

**Rule:** Separate surface health from library-graph completion. Report the library as:

- GREEN only when queue backlog is drained or explicitly within the current drain SLO and indexed coverage is consistent with the registry.
- YELLOW when `.gbrain/queue.jsonl` has a material backlog, launchd tracking is unclear, or `gbrain_indexed_chunks` is obviously behind the canonical registry.
- RED when the queue is being lost, truncated on partial failure, or the index path is missing/unreadable.

Do not "fix" AP-10 by blocking commits or making OpenBrain sync synchronous. The queue remains asynchronous; the obligation is honest reporting plus daemon/root-cause repair.

**Mechanical detector:**

```bash
python3 tools/library_health.py --no-write --json
launchctl list | grep com.nous.library-graph || true
python3 tools/library.py search "Hermes proof sprint"
```

If the first command reports a material queue backlog, the final answer must say library graph is yellow even when the sprint artifact is otherwise retrievable through Obsidian/QMD/gbrain/OpenBrain.

### AP-11: Queue drain needs a real service and rate-limit deferral

**Symptom:** The doctrine claimed `com.nous.library-graph` drained `.gbrain/queue.jsonl`, but the tracked plist and installed LaunchAgent were missing. The queue grew to 957 lines. Running a manual Voyage drain previously produced many `http_429` rows because the script kept processing every queued file after the first rate-limit failure.

**Root cause:** Two separate misses compounded: the service contract existed only in prose, and the drain loop treated `http_429` like an isolated per-file error instead of an upstream backpressure signal.

**Rule:** `tools/launchd/com.nous.library-graph.plist` must exist and be installed on Mac when the local library graph is expected to stay current. It must use `/opt/homebrew/bin/python3` because that interpreter has both `certifi` and `sqlite_vec`; the project venv has `certifi` but can rewrite `.gbrain/manifest.json` with `sqlite_vec_loaded: false`. `library_drain_queue.py` must stop the current pass after `http_429`, `timeout`, or provider/network exceptions, leave the queue intact, and mark the remaining files as deferred. The LaunchAgent must log compact `--summary-json`, not the full per-file queue body. Do not keep hammering Voyage after a rate-limit or TLS failure, and do not truncate the queue on partial failure.

**Detector:**

```bash
launchctl list | grep com.nous.library-graph || true
python3 tools/library_health.py --no-write --json
python3 -m pytest tools/tests/test_library_drain_queue.py -q
```

### AP-12: Timestamp-only registry churn dirties the presidential gate

**Symptom:** `presidential_readiness_gate.py` stays red only because `pages/systems/canonical-registry.jsonl` is dirty, even though the diff contains duplicate latest-state rows with identical values and only new `updated` timestamps.

**Root cause:** `library_drain_queue.py` legitimately calls `registry.update_field()` several times per processed file (`content_hash`, `embed_model`, `embed_dim`, `gbrain_chunk_ids`). `update_field()` appended a row even when the requested value was already current. A background drain could therefore mutate the tracked registry without changing library state.

**Rule:** registry writes are append-only only for real state transitions. `library_canonical_registry.update_field()` must return success without appending when the value is unchanged. Do not paper over this by ignoring the registry in git status or by repeatedly committing timestamp-only rows.

**Detector:**

```bash
python3 -m pytest tools/tests/test_library_canonical_registry.py -q
git diff -- pages/systems/canonical-registry.jsonl
```

### AP-13: Whole-queue preservation hides real drain progress

**Symptom:** `library_health.py --no-write --json` keeps reporting a high `gbrain_pending_queue` even though manual or launchd drain passes exit 0. The queue line count barely moves, while `gbrain_indexed_chunks` may increase only when a rare full pass succeeds.

**Root cause:** The May 22 queue fix stopped hammering Voyage after the first provider failure, but still preserved the entire original queue on partial failure. With Voyage's reduced no-payment-method limits (`3 RPM / 10K TPM`), a single `http_429` could cause hundreds of already-skipped or already-processed rows to be retried forever. A second mismatch made the local index look healthier than it was: `voyage-3-lite` returned 512-dimensional vectors while the code declared 1024, so chunk rows could exist without matching vector-table rows.

**Rule:** Queue preservation means preserving unfinished work, not preserving the original file forever. `library_drain_queue.py` must compact `.gbrain/queue.jsonl` to failed/current plus unhandled residual rows on every partial pass. Voyage draining must use `/opt/homebrew/bin/python3`, live response dimensions, conservative request pacing, and a bounded `--max-files` launchd slice unless paid-account limits are proven higher. Do not call a backlog fixed just because the daemon is installed; prove queue count down and indexed chunk count up.

**Detector:**

```bash
/opt/homebrew/bin/python3 tools/library_drain_queue.py --summary-json --prefer voyage --max-files 6
/opt/homebrew/bin/python3 tools/library_health.py --no-write --json
/opt/homebrew/bin/python3 - <<'PY'
import sqlite3
import sqlite_vec
con = sqlite3.connect(".gbrain/index.db")
con.enable_load_extension(True)
sqlite_vec.load(con)
con.enable_load_extension(False)
print(con.execute("select count(*) from chunks").fetchone()[0])
print(con.execute("select count(*) from vec_chunks_512").fetchone()[0])
PY
```

### AP-14: Background drain must write back tracked registry state

**Symptom:** `presidential_readiness_gate.py` turns red again minutes after cleanup because `com.nous.library-graph` processes a valid slice and leaves `pages/systems/canonical-registry.jsonl` dirty in the Mac worktree.

**Root cause:** AP-13 made queue drain progress real and bounded, but the LaunchAgent only ran the drain. It did not commit/push the tracked registry rows produced by successful embedding, so a healthy background process looked like unowned local dirt.

**Rule:** When `com.nous.library-graph` runs from the tracked Mac vault, it must pass `--git-writeback --git-push-remotes vps,github`. `library_drain_queue.py` must commit only tracked library graph state, use exact-OID fetch/rebase rather than compound `git pull`, and push to configured remotes. If writeback fails, the summary JSON must include `git_writeback.status=failed` so the next gate sees a real residual, not silent dirt.

**Detector:**

```bash
/opt/homebrew/bin/python3 tools/library_drain_queue.py --summary-json --prefer stub --max-files 1 --git-writeback --git-push-remotes vps,github
python3 -m pytest tools/tests/test_library_drain_queue.py -q
```

### AP-15: Writeback commits are path-scoped with `--only`

**Symptom:** While testing AP-14, the shared Mac worktree already had an unrelated staged KEONA rename. A plain daemon commit after `git add pages/systems/canonical-registry.jsonl` would have committed that unrelated staged work together with the library registry.

**Root cause:** `git add <owned paths>` narrows what the daemon stages, but `git commit -m ...` still commits everything already staged by any writer in the shared index.

**Rule:** Automated library writeback must commit with `git commit --only -- <owned paths>` after staging owned paths. This preserves unrelated staged/unstaged work while still allowing the daemon to commit its tracked registry state. Never use a plain `git commit -m ...` from a background daemon in the shared vault.

**Detector:**

```bash
python3 -m pytest tools/tests/test_library_drain_queue.py -q
```

### AP-16: Local backlog drain is allowed when Voyage billing is rate-limited

**Symptom:** The library graph queue drains a few rows, then repeatedly logs `http_429` from `voyage-3-lite`. With Voyage on reduced no-payment-method limits (`3 RPM / 10K TPM`), the daemon can stay yellow for hours while wasting cycles on predictable rate limits.

**Root cause:** AP-13 correctly paced Voyage and compacted residual work, but the installed launchd job still preferred Voyage for every slice. That is the right quality target after billing is upgraded, but the wrong default while the backlog is large and the account is throttled.

**Rule:** When Voyage returns repeated 429s and the backlog is material, switch the drain service to the supported local embedder (`--prefer local`) with bounded larger slices (`--max-files 25`) until `.gbrain/queue.jsonl` is drained. Local vectors are honest indexed retrieval, not a fake green: record `embed_model`/`embed_dim` in the registry, keep the queue count visible, and plan a later Voyage refresh only after paid limits are proven. Do not keep hammering Voyage just because it is the ideal model.

**Detector:**

```bash
tail -40 logs/library-drain.log | grep http_429 || true
/opt/homebrew/bin/python3 tools/library_drain_queue.py --summary-json --prefer local --max-files 25 --git-writeback --git-push-remotes vps,github
python3 tools/library_health.py --no-write --json
```

## Timeline

- **2026-05-22** | v1.5.2 -> v1.5.3 — Added **AP-16** after the queue was no longer stuck but Voyage still returned `http_429` under reduced billing limits. Patch: tracked and installed `com.nous.library-graph` now use `--prefer local --max-files 25` so the backlog drains honestly without API hammering; later Voyage refresh remains a separate billing-backed quality pass. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/library-graph/skill.
- **2026-05-22** | v1.5.1 -> v1.5.2 — Added **AP-15** during AP-14 live proof after the shared Mac index already contained an unrelated KEONA rename. Root cause: a background daemon can stage only its owned paths but a plain `git commit` still absorbs unrelated staged work. Patch: library drain writeback now commits with `git commit --only -- <owned paths>` and the regression checks for `--only`. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/library-graph/skill.
- **2026-05-22** | v1.5.0 -> v1.5.1 — Added **AP-14** after the queue drain kept fixing `gbrain_pending_queue` while re-dirtying `pages/systems/canonical-registry.jsonl`, causing readiness gates to red-drift minutes after cleanup. Patch: `library_drain_queue.py` now supports `--git-writeback` with exact-OID fetch/rebase and one push retry, and the Mac LaunchAgent passes `--git-writeback --git-push-remotes vps,github`. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/library-graph/skill.
- **2026-05-22** | v1.4.0 -> v1.5.0 — Added **AP-13** after `library_health.py` still showed `gbrain_pending_queue=961+` despite the launchd drain being present. Patch: `library_drain_queue.py` now writes residual-only queues, supports bounded `--max-files`, uses live embedding dimensions; `library_embed_voyage.py` now paces requests for reduced Voyage limits and records live 512-dim vectors; the Mac LaunchAgent runs bounded slices every 180s. Queue proof moved 965 -> 733 and indexed chunks 313 -> 434 before commit. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/library-graph/skill.
- **2026-05-22** | v1.3.0 -> v1.4.0 — Added **AP-12** after `presidential_readiness_gate.py` re-dirtied on duplicate `canonical-registry.jsonl` rows minutes after cleanup. Patch: `library_canonical_registry.update_field()` now no-ops on unchanged values, with regression coverage in `test_update_field_same_value_noops`. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/library-graph/skill.
- **2026-05-22** | v1.2.0 -> v1.3.0 — Added **AP-11** after the Hermes promotion audit found the library graph still yellow: `.gbrain/queue.jsonl` had 957 pending lines and no tracked/installed `com.nous.library-graph` LaunchAgent. Patch: added tracked LaunchAgent, installed the service on Mac, changed `library_drain_queue.py` so `http_429`/`timeout`/provider exceptions defer the remaining queue instead of hammering Voyage across every queued file, made Voyage HTTPS use certifi when available because launchd hit macOS framework-Python CA failures, and pinned the service to Homebrew Python so sqlite-vec remains loaded. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/library-graph/skill.
- **2026-05-21** | v1.1.0 -> v1.2.0 — Added **AP-10** after the Hermes proof sprint found cross-surface health mostly green but `library_health.py --no-write --json` reported `gbrain_pending_queue=921` and only `gbrain_indexed_chunks=93`. Doctrine: queue/index backlog is a library-golden blocker and must be reported as yellow until drained/root-caused. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/library-graph/skill via VPS CLI fallback after MCP transport closed in this Codex session.
- **2026-05-21** | v1.0.0 -> v1.1.0 — Added **AP-9** after the library sync audit found `LIBRARY-HEALTH.md` missing YAML frontmatter and top-level skills missing resolver entries. Patch: `tools/library_health.py` now renders frontmatter, resolver entries were added for library-graph, camera-event-query, openclaw-probe-isolation, and lane-lock. No new LESSON (RULE ZERO). gbrain-timeline-ok: pages/skills/library-graph/skill.
- **2026-05-20** | v1.0.0 created by Ship 3 (final ship) of the god-tier 3-ship plan. APs absorbed from the original audit's "embedding theatre" finding + the Voyage rate-limit observation during Wave 8 migration. 90+ tests across 9 Ship-3 test files prove the doctrine. The library is real: 754 ULID-keyed entries, 93 Voyage-1024-d chunks indexed (rest draining via daemon). Plan: `pages/plans/from-gpt-implemented-the-delightful-riddle.md` §6 (mirror at `/Users/madia/.claude/plans/from-gpt-implemented-the-delightful-riddle.md`).

## See also

- [[model-failover]] — Ship 1's substrate; parity manifest joins all 3 ships.
- [[lane-lock]] — Ship 2's atomic coordination layer; embed-on-write hook respects lane locks via the canonical pre-commit chain.
- [[mistake-to-skill]] — 7-day SLA absorption catches new APs surfaced by library failures.
- [[musk-algorithm]] — 5-step elimination: AP-1 deleted the gbrain theatre; the new system has no lies.
- [[openbrain-projection]] — peer-owned skill that pre-existed; library-graph is the cross-system layer above it.
- `pages/plans/from-gpt-implemented-the-delightful-riddle.md` (mirror at `/Users/madia/.claude/plans/from-gpt-implemented-the-delightful-riddle.md`) — the operating plan §6 (Ship 3) is the wave-by-wave spec. As of this writing, ~742 of the vault's files are still queued to embed; the library-graph launchd daemon will complete the job at 3 files/min over ~4 hours wall-clock.
