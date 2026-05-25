---
type: skill
id: generated-artifact-hygiene
title: "Generated Artifact Hygiene"
tier: 2
version: 1.0.0
status: active
date: 2026-05-21
last_updated: 2026-05-21
tags: [git, generated-artifacts, launchd, mercury, clean-worktree]
---

# generated-artifact-hygiene v1.0.0

Use this skill when a background job, launchd task, sync loop, memory generator, dashboard builder, or proof writer leaves tracked files dirty in a shared Nous checkout.

## Purpose

Generated files are allowed, but they must not become anonymous peer dirt. A scheduled writer either writes deterministically and no-ops when unchanged, or writes through a clean publish boundary that commits only its own outputs.

## Contract

Inputs: dirty generated paths, the suspected writer, and the current session registry.

Outputs: root cause, deterministic/no-op generation where possible, clean-boundary writer where mutation is required, focused tests, and a skill/gbrain timeline entry.

## Procedure

1. Trace the writer before editing:
   ```bash
   rg -n "dirty-file-name|generator-name" tools pages /Users/madia/Library/LaunchAgents
   launchctl list | rg 'job-label'
   git diff --word-diff -- path/to/generated
   ```
2. Classify the diff:
   - Volatile metadata: date, session id, HEAD, latest handoff, timestamps.
   - Semantic generated content: changed source facts, proof rows, new task state.
   - Peer WIP: human/agent-authored edits outside the generator's output contract.
3. Fix at the writer:
   - Preserve existing metadata for unchanged generated facts.
   - Render to a temp file and `cmp` before replacing tracked output.
   - Keep live runtime context out of tracked generated files unless the writer also publishes it.
   - Add a wrapper that skips when non-owned dirty paths exist.
   - If output really changes, commit only declared output paths; never `git add -A`.
4. Verify with a repeated run:
   ```bash
   <generator> --apply
   git status --porcelain -- declared/output/paths
   <generator> --apply
   git status --porcelain -- declared/output/paths
   ```

## Anti-Patterns

### AP-1 — Launchd generator writes tracked volatile context without a publish boundary

**Symptom:** a session close reports unrelated dirty generated files such as `pages/mercury/facts.jsonl` or `pages/progress/claude-memory/MEMORY-mercury.md`.

**Root cause:** a scheduled job regenerated tracked files directly in the shared Mac vault. `mercury_seed.py` stamped unchanged permanent facts with today's date, and `mercury_inject.py` persisted volatile session-id/HEAD/latest-HANDOFF context into tracked `MEMORY-mercury.md`. `com.nous.mercury-refresh` ran this every 30 minutes without checking for peer dirt or committing its own outputs.

**Rule:** scheduled generators must be clean-boundary writers. They may not write tracked files when non-owned dirty paths exist. They must no-op on byte-identical output, strip volatile runtime context from tracked output, and commit only their declared generated paths when a real generated delta exists.

**Mechanical detector:** run the generator twice in a row and require the second run to leave `git status --porcelain -- <declared-output-paths>` empty. Then run the wrapper with a fake non-owned dirty path and require it to skip without touching generated outputs.

## Timeline

- **2026-05-21** | v1.0.0 — Created after Mercury launchd left `pages/mercury/facts.jsonl` and `pages/progress/claude-memory/MEMORY-mercury.md` dirty in the Mac checkout. Shipped deterministic Mercury seeding, stable tracked Mercury memory output, and `tools/mercury_refresh.py` clean-boundary wrapper.
