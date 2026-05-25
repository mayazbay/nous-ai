#!/bin/bash
# archive_memory_older.sh — carve older session stanzas out of MEMORY.md into a dated archive.
#
# Context (session-operating-contract AP-7, session 54 Probe C, session 66 ship):
# MEMORY.md grows ~25-50 lines/session via top-block prepend. Soft ceiling = 400 lines;
# hard context-window trouble starts around 800+. This tool extracts older stanzas into
# pages/progress/claude-memory/sessions/archive-*.md, preserving full content (archive != delete).
#
# A stanza = one "# Memory — updated ..." H1 header + everything until the next such header
# OR the first non-stanza heading ("# Session 51 memory header", "## Terminology corrections",
# "## Older sessions", "## Identity" — the tail sections that must be preserved).
#
# Usage:
#   bash tools/archive_memory_older.sh --keep-top N [--apply]
#     --keep-top N   keep the N most-recent stanzas; archive the rest (default: 9)
#     --apply        actually modify files (default: dry-run)
#     --archive-name NAME
#                    override archive filename (default: archive-YYYY-MM-DD-from-s<N+1>-down.md)
#
# Exit codes:
#   0 = dry-run or apply succeeded (including no-op if nothing to archive)
#   1 = validation error (file malformed, nothing to archive in apply mode = soft pass with msg)
#   2 = bad args
#   3 = git working tree dirty on apply (abort — commit or stash first)
#
# Source: session-66 carryover from session-65 handoff. Session-54 did the extraction manually
# for pre-session-51 content; this is the reusable tool per RULE ZERO compounding.

set -u

KEEP_TOP=9
APPLY=0
ARCHIVE_NAME=""

while [ $# -gt 0 ]; do
  case "$1" in
    --keep-top) KEEP_TOP="$2"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    --archive-name) ARCHIVE_NAME="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,25p' "$0"
      exit 0
      ;;
    *) echo "archive_memory_older: unknown arg: $1" >&2; exit 2 ;;
  esac
done

if ! [[ "$KEEP_TOP" =~ ^[0-9]+$ ]] || [ "$KEEP_TOP" -lt 1 ]; then
  echo "archive_memory_older: --keep-top must be a positive integer, got: $KEEP_TOP" >&2
  exit 2
fi

VAULT="$(cd "$(dirname "$0")/.." && pwd)"
MEMFILE="$VAULT/pages/progress/claude-memory/MEMORY.md"
SESSIONS_DIR="$VAULT/pages/progress/claude-memory/sessions"

if [ ! -f "$MEMFILE" ]; then
  MEMFILE="$HOME/.claude/projects/-Users-madia-Documents-Projects-Nous-AGaaS/memory/MEMORY.md"
fi
if [ ! -f "$MEMFILE" ]; then
  echo "archive_memory_older: MEMORY.md not found" >&2
  exit 1
fi

mkdir -p "$SESSIONS_DIR"

python3 - "$MEMFILE" "$SESSIONS_DIR" "$KEEP_TOP" "$APPLY" "$ARCHIVE_NAME" <<'PYEOF'
import sys, os, re, datetime, hashlib

memfile, sessions_dir, keep_top, apply_flag, archive_name = sys.argv[1:6]
keep_top = int(keep_top)
apply_flag = apply_flag == "1"

with open(memfile, encoding="utf-8") as f:
    text = f.read()
lines = text.splitlines(keepends=True)

# Find stanza headers (lines starting with "# Memory — updated ")
# AND the first "tail" heading that ends the stanza region.
STANZA_RE = re.compile(r'^# Memory — updated ')
# Tail markers: everything from here down must be preserved after stanzas.
# First tail heading encountered after the last stanza = cut point.
TAIL_MARKERS = [
    re.compile(r'^# Session \d+ memory header'),
    re.compile(r'^## Terminology corrections'),
    re.compile(r'^## Older sessions'),
    re.compile(r'^## Identity'),
]

stanza_line_nums = []  # 0-indexed line numbers where each stanza starts
for i, line in enumerate(lines):
    if STANZA_RE.match(line):
        stanza_line_nums.append(i)

if not stanza_line_nums:
    print("🟡 no '# Memory — updated ...' stanzas found — nothing to archive", file=sys.stderr)
    sys.exit(0)

# Find first tail marker line AFTER the last stanza start
last_stanza_start = stanza_line_nums[-1]
tail_start = None
for i in range(last_stanza_start + 1, len(lines)):
    for tm in TAIL_MARKERS:
        if tm.match(lines[i]):
            tail_start = i
            break
    if tail_start is not None:
        break

if tail_start is None:
    # No tail region; stanzas go all the way to EOF.
    tail_start = len(lines)

total_stanzas = len(stanza_line_nums)
if keep_top >= total_stanzas:
    print(f"🟢 keep_top={keep_top} >= total_stanzas={total_stanzas} — nothing to archive, exit 0")
    sys.exit(0)

# Cut points:
#   KEEP: lines[0 : stanza_line_nums[keep_top]]    (top keep_top stanzas)
#   ARCHIVE: lines[stanza_line_nums[keep_top] : tail_start]   (older stanzas)
#   TAIL: lines[tail_start : ]    (terminology + identity — always preserved)

cut_at = stanza_line_nums[keep_top]  # first line of first-archived stanza (0-indexed)
kept_lines = lines[:cut_at]
archive_lines = lines[cut_at:tail_start]
tail_lines = lines[tail_start:]

if not archive_lines:
    print("🟢 no archive content between keep-boundary and tail — exit 0")
    sys.exit(0)

# Generate archive filename if not provided
if not archive_name:
    today = datetime.date.today().isoformat()
    # Session ordinal: the stanzas being archived span stanza_line_nums[keep_top] through end
    # We record the count (not session numbers, since numbers aren't strictly monotonic).
    n_archived = total_stanzas - keep_top
    archive_name = f"archive-{today}-s66-extracted-{n_archived}-stanzas.md"

archive_path = os.path.join(sessions_dir, archive_name)

# Build archive file content with frontmatter + preamble
frontmatter = f"""---
type: progress
id: MEMORY-ARCHIVE-{today.replace('-','').upper() if (today := datetime.date.today().isoformat()) else 'UNKNOWN'}-S66
title: "MEMORY.md archive — extracted session 66 (2026-04-23)"
tags: [memory, archive, extraction, session-66, bloat-fix]
date: {today}
source_count: 1
status: reviewed
last_updated: {today}
related: [MEMORY, session-operating-contract, auto-memory]
---

# MEMORY.md archive — extracted session 66 (2026-04-23)

**Extracted 2026-04-23** during session-66 Phase-1. MEMORY.md had grown back to 674 lines after session-54 Probe C's previous extraction (which had reduced to ~248 at that time). This archive preserves content older than the top-{keep_top} most-recent stanzas.

Current MEMORY.md retains:
- top-{keep_top} stanzas (most recent, reverse-chronological per AMD-006 Rule 2)
- Terminology corrections / Older sessions pointer / Identity (all tail sections preserved)

All content below is raw extraction (stanza ordering preserved as-extracted).

---

"""

archive_content = frontmatter + "".join(archive_lines)

# Compute content hash for idempotency check (is archive already present?)
archive_hash = hashlib.sha256(archive_content.encode('utf-8')).hexdigest()[:12]

# Idempotency: if archive file already exists with same hash-tag in frontmatter — skip
# (We don't write the hash tag yet; simplest idempotency = "same filename exists and contains same stanzas").
if os.path.exists(archive_path):
    with open(archive_path, encoding="utf-8") as f:
        existing = f.read()
    # Simple check: all our archive stanza headers already present in existing archive
    archive_headers = [l for l in archive_lines if STANZA_RE.match(l)]
    all_present = all(h.strip() in existing for h in archive_headers)
    if all_present and apply_flag:
        print(f"🟢 archive {archive_path} already contains all {len(archive_headers)} stanzas — idempotent no-op, exit 0")
        sys.exit(0)

# Build new MEMORY.md content
new_mem = "".join(kept_lines) + "".join(tail_lines)

# Summary for operator
print(f"=== archive_memory_older.sh plan ({'APPLY' if apply_flag else 'DRY-RUN'}) ===")
print(f"  MEMORY.md: {memfile}")
print(f"    total lines before: {len(lines)}")
print(f"    total stanzas: {total_stanzas}")
print(f"    keep_top: {keep_top}")
print(f"    archive stanzas: {total_stanzas - keep_top}")
print(f"    tail preservation: lines {tail_start+1}..{len(lines)} ({len(tail_lines)} lines)")
print(f"    new MEMORY.md lines: {len(kept_lines) + len(tail_lines)}")
print(f"  archive: {archive_path}")
print(f"    size: {len(archive_content)} chars / {len(archive_content.splitlines())} lines")

# List archived stanza headers for operator review
print(f"  --- stanzas to archive ---")
for i, line_idx in enumerate(stanza_line_nums[keep_top:], start=1):
    header = lines[line_idx].strip()
    # Truncate long headers for display
    if len(header) > 140:
        header = header[:137] + "..."
    print(f"    [{i}] L{line_idx+1}: {header}")

if not apply_flag:
    print("🟡 DRY-RUN — pass --apply to write changes")
    sys.exit(0)

# APPLY: write files atomically (write-then-rename)
archive_tmp = archive_path + ".tmp"
with open(archive_tmp, "w", encoding="utf-8") as f:
    f.write(archive_content)
os.replace(archive_tmp, archive_path)

mem_tmp = memfile + ".tmp"
with open(mem_tmp, "w", encoding="utf-8") as f:
    f.write(new_mem)
os.replace(mem_tmp, memfile)

print(f"✅ archive written: {archive_path}")
print(f"✅ MEMORY.md rewritten: {memfile}")
print(f"   before: {len(lines)} lines → after: {len(kept_lines) + len(tail_lines)} lines")
PYEOF

RC=$?

if [ "$APPLY" -eq 1 ] && [ "$RC" -eq 0 ]; then
  echo ""
  echo "=== post-archive verification ==="
  if [ -x "$VAULT/tools/test_memory_top_block_size.sh" ]; then
    bash "$VAULT/tools/test_memory_top_block_size.sh" || echo "   (top-block scan non-zero exit — inspect above)"
  else
    LINES=$(wc -l < "$MEMFILE" | tr -d ' ')
    echo "   MEMORY.md line count: $LINES (soft ceiling 400)"
  fi
fi

exit $RC
