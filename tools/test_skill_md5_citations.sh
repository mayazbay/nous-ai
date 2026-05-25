#!/usr/bin/env bash
# Scan SKILL.md files for MD5 citation ↔ file-reality drift.
#
# Purpose (Tan/Karpathy 3rd compounding gate, infrastructure AP-44):
#   SKILL.md prose cites file MD5s (hooks, tools/*.sh). If the cited file drifts
#   without the citation updating, the doctrine silently lies. This gate rejects
#   such drift at commit time.
#
# Sibling gates:
#   - AP-35 (pre-push): live hook ↔ vault tools/ MD5 parity
#   - AP-43 (pre-commit RULE 4): SKILL.md frontmatter ↔ H1 version parity
#   - AP-44 (pre-commit RULE 5, THIS): SKILL.md MD5 citations ↔ file reality
#
# Usage:
#   bash tools/test_skill_md5_citations.sh               # scan all SKILL.md
#   SCAN_GLOB="/path/to/one.md" bash tools/test_skill_md5_citations.sh  # scan one file
#
# Exit codes:
#   0 = all citations match reality (or no citations found — vacuous pass)
#   2 = ≥1 drift detected (readable report printed; commit should be rejected)
#
# Citation detection:
#   - 32-char lowercase hex token
#   - Must appear within 250 chars of the keyword "md5" (case-insensitive) OR
#     "hook" OR "hash" in the surrounding window
#   - Must have a resolvable repo-relative file path in the same window
#   - SKIPS citations in transition context (X → Y, X -> Y) — those are historical
#   - SKIPS citations where path is Air-only (starts with ~/, /Users/madia/nous-agaas
#     without a vault equivalent, /opt/nous-agaas, etc.) since we can't verify from
#     the Mac/VPS vault pre-commit context
#
# Design notes:
#   - Python embedded for readable regex + hash logic
#   - Vault-relative paths only (tools/..., .git/hooks/..., pages/...)
#   - Falls back silent-pass on system errors (don't block commits on scanner bugs)

set -u
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo .)
cd "$REPO_ROOT"

python3 - <<'PY'
import os, re, sys, hashlib, glob

scan_glob = os.environ.get("SCAN_GLOB") or "pages/skills/*/SKILL.md"
files = [scan_glob] if os.path.isfile(scan_glob) else sorted(glob.glob(scan_glob))

hex32 = re.compile(r'(?<![0-9a-fA-F])([0-9a-f]{32})(?![0-9a-fA-F])')
vault_path = re.compile(
    r'(tools/[A-Za-z0-9_./-]+\.(?:sh|py|md)'
    r'|\.git/hooks/[A-Za-z0-9_./-]+'
    r'|pages/[A-Za-z0-9_./-]+\.(?:sh|py|md))'
)

# Transition markers (X → Y form)
# If an arrow sits between TWO 32-char hexes, both are historical.
# Window needs to be wide enough to catch both full 32-char hexes plus ~100 chars
# of prose between them. Use ±250 to be safe.
def in_transition(txt, hex_start, hex_end):
    window = txt[max(0, hex_start - 250):min(len(txt), hex_end + 250)]
    hexes = list(hex32.finditer(window))
    if len(hexes) < 2:
        return False
    # Any arrow or "->" between any two hex positions?
    for i in range(len(hexes) - 1):
        mid = window[hexes[i].end():hexes[i+1].start()]
        if '→' in mid or '->' in mid:
            return True
    return False

# Timeline-section detector: append-only historical block in SKILL.md.
# Returns list of (start, end) char ranges where citations should be skipped.
# A timeline range begins at `## Timeline` or `## History` and ends at the
# next `## ` header or EOF.
def timeline_ranges(txt):
    ranges = []
    section_re = re.compile(r'^## .*$', re.MULTILINE)
    timeline_markers = re.compile(r'^## (Timeline|History)\b', re.MULTILINE)
    for m in timeline_markers.finditer(txt):
        start = m.start()
        # Find next ^## header after start
        next_section = section_re.search(txt, pos=m.end())
        end = next_section.start() if next_section else len(txt)
        ranges.append((start, end))
    return ranges

def in_timeline(pos, ranges):
    return any(s <= pos < e for s, e in ranges)

drifts = []

for f in files:
    if not os.path.isfile(f):
        continue
    try:
        txt = open(f, "r", encoding="utf-8", errors="replace").read()
    except Exception:
        continue

    tl_ranges = timeline_ranges(txt)

    for m in hex32.finditer(txt):
        cited = m.group(1)
        # Skip Timeline-section citations (append-only history)
        if in_timeline(m.start(), tl_ranges):
            continue
        w_start = max(0, m.start() - 250)
        w_end = min(len(txt), m.end() + 250)
        window = txt[w_start:w_end]
        low = window.lower()
        # Gate on MD5/hook/hash keyword near the hex
        if 'md5' not in low and 'hook' not in low and 'hash' not in low:
            continue
        # Skip transition citations
        if in_transition(txt, m.start(), m.end()):
            continue
        # Find the nearest vault path in the window
        paths = [(p.start(), p.group(1)) for p in vault_path.finditer(window)]
        if not paths:
            continue
        hex_rel = m.start() - w_start
        paths.sort(key=lambda x: abs(x[0] - hex_rel))
        cand_path = paths[0][1]
        # Resolve path
        if not os.path.isfile(cand_path):
            # Not a vault-verifiable path (maybe Air-only) — skip
            continue
        try:
            actual = hashlib.md5(open(cand_path, "rb").read()).hexdigest()
        except Exception:
            continue
        if actual != cited:
            # Compute line number of the cited hex
            line_no = txt.count('\n', 0, m.start()) + 1
            drifts.append({
                "file": f,
                "line": line_no,
                "cited": cited,
                "actual": actual,
                "path": cand_path,
            })

if drifts:
    print("")
    print("============================================================")
    print("  BLOCKED: SKILL.md MD5 citation ↔ reality drift (infrastructure AP-44)")
    print("============================================================")
    print("")
    for d in drifts:
        print(f"  DRIFT {d['file']}:{d['line']}")
        print(f"    path:   {d['path']}")
        print(f"    cited:  {d['cited']}")
        print(f"    actual: {d['actual']}")
        print("")
    print("Fix one of:")
    print("  (a) Citation is stale — update SKILL.md prose with the actual MD5.")
    print("  (b) File drifted unexpectedly — investigate why (AP-35 parity).")
    print("")
    print("If the citation is historical/transitional and the scanner misclassified,")
    print("rewrite with an arrow context (X → Y) or move into the Timeline block.")
    print("============================================================")
    sys.exit(2)

# Success
print("OK: all SKILL.md MD5 citations match file reality")
sys.exit(0)
PY
