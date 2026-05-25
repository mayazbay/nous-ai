---
type: spec
id: SPEC-FACTORY-CODER-PROMPT-FIX
title: "Fix factory graph.py Coder prompt to use bare src/ paths (remove satory-frontend/ prefix)"
date: 2026-04-08
tags: [spec, factory, graph.py, coder, prompt, fix, req, ops]
source_count: 0
status: reviewed
last_updated: 2026-04-08
priority: p1
related: [phase-3-bdl-replacement-reqs-2026-04-08, LESSON-048-phantom-directory-disaster, LESSON-052-file-ops-double-prefix-phantom]
historical: true
---

# SPEC — Factory graph.py Coder prompt fix (bare `src/...` paths)

## Problem

The factory's Coder agent prompt in `/root/nous-agaas/graph.py` lines 557-558 tells the LLM to output file paths in the format `satory-frontend/src/...`. For example:

```python
sys = (f"Senior React/TS dev. Output JSON only:\n"
       f'{{"files":[{{"path":"satory-frontend/src/...","content":"full content"}}]}}\n'
       f"Complete files, not patches. Only satory-frontend/src/. "
       f"Protected ({', '.join(PROTECTED)}): no >30% shrink.\n"
       ...)
```

And line 582 enforces:

```python
for f in files:
    path, content = f.get("path",""), f.get("content","")
    if not path.startswith("satory-frontend/"): continue
```

**The issue:** after the LESSON-052 `file_ops` double-prefix fix, `file_ops.write_file()` can handle BOTH formats cleanly:
- `satory-frontend/src/foo.tsx` (old, prefixed)
- `src/foo.tsx` (bare, relative to FRONTEND_PATH)

But the prompt still tells the LLM to output the prefixed form. This creates two problems:

1. **The prompt "lies" to the LLM** — it implies the prefix is required when in fact both work. LLMs confused by mismatched constraints hallucinate more.
2. **File paths in Coder output are noisier than necessary** — `satory-frontend/src/components/Cameras.tsx` is harder to scan than `src/components/Cameras.tsx`.

Madi flagged this in the 2026-04-08 next-session priorities list: *"Update Coder prompt in graph.py (lines 511/512/612) to return bare src/... paths — the file_ops fix tolerates both formats but the prompt still lies to the LLM."*

(Line numbers in Madi's note are from an older graph.py version. The CURRENT lines are 557, 558, 582 — verified via `sed` 2026-04-08 17:25 Almaty.)

## Proposed fix (3 surgical edits to `/root/nous-agaas/graph.py`)

### Edit 1 — Line 557: Prompt JSON format example

**Before:**
```python
       f'{{"files":[{{"path":"satory-frontend/src/...","content":"full content"}}]}}\n'
```

**After:**
```python
       f'{{"files":[{{"path":"src/...","content":"full content"}}]}}\n'
```

### Edit 2 — Line 558: Prompt scope constraint

**Before:**
```python
       f"Complete files, not patches. Only satory-frontend/src/. "
```

**After:**
```python
       f"Complete files, not patches. Only src/ under the frontend (file_ops resolves paths automatically). "
```

### Edit 3 — Line 582: Path acceptance check

**Before:**
```python
for f in files:
    path, content = f.get("path",""), f.get("content","")
    if not path.startswith("satory-frontend/"): continue
```

**After:**
```python
for f in files:
    path, content = f.get("path",""), f.get("content","")
    # Accept both bare (src/...) and prefixed (satory-frontend/src/...) per LESSON-052 file_ops fix.
    if not (path.startswith("src/") or path.startswith("satory-frontend/")): continue
```

## Validator-side check (line 658 — consider also)

Line 658 in the Validator node has a similar string reference:

```python
f"3. Only edits satory-frontend/src/?\n"
```

This one is for the VALIDATOR LLM asking the Coder's work a verification question. Changing it to `"Only edits src/ under the frontend?"` aligns with the relaxed prompt. NOT urgent — Validator checks both formats would still pass.

## Test plan

1. **Backup first**: `cp /root/nous-agaas/graph.py /root/nous-agaas/graph.py.backup.$(date +%Y%m%d_%H%M%S)`
2. Apply the 3 edits (Edit 1, Edit 2, Edit 3).
3. Syntax check: `python3 -c "import ast; ast.parse(open('/root/nous-agaas/graph.py').read())"` should succeed.
4. Start a factory cycle with a known-good REQ task (e.g., REQ-090 from [[phase-3-bdl-replacement-reqs-2026-04-08]]).
5. Verify Coder's first output: path should be `src/components/LivePlayerErrorBoundary.tsx` not `satory-frontend/src/components/LivePlayerErrorBoundary.tsx`.
6. Verify file is written to the correct location on disk (the FRONTEND_PATH target).
7. Verify the commit message references the REQ tag (LAW-006 gate).
8. Roll back if anything explodes: `cp /root/nous-agaas/graph.py.backup.<ts> /root/nous-agaas/graph.py`.

## Risk assessment

- **Code change risk**: LOW. Three surgical edits, both "old" and "new" path formats are accepted by file_ops.
- **Prompt behavior risk**: LOW. Simpler prompts → less LLM confusion → fewer bad outputs.
- **Factory uptime risk**: MEDIUM. Factory is currently stopped (awaiting Anthropic credit). When Madi restarts after credit top-up, the first cycle under the new prompt is the riskiest. Have the backup ready.
- **Rollback**: INSTANT via `cp` from backup.

## Why NOT apply this change today

I (Claude Code) am deferring this change to next session because:
1. Factory is currently stopped — can't verify the fix end-to-end without running it.
2. Running the factory costs Anthropic credits that Madi has paused.
3. A broken Coder prompt would silently hallucinate and consume a full cycle's tokens before we notice.
4. Better to apply + test in a dedicated session with Madi present to react to the first cycle results.

**When to apply:** first factory session after Anthropic credit top-up, BEFORE any real task runs. Apply → start factory → watch the first cycle carefully → if Coder outputs bare `src/...` paths that write to the correct location, ship it.

## See also
- [[phase-3-bdl-replacement-reqs-2026-04-08]] — Phase 3 REQs that depend on a non-idling factory
- [[LESSON-048-phantom-directory-disaster]] — the original phantom directory bug
- [[LESSON-052-file-ops-double-prefix-phantom]] — the file_ops fix that enabled the bare-path approach
- [[AUDIT-019-session-close-apr7]] — original flag of this issue
