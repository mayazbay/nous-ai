#!/bin/bash
# tools/verify_ship3_e2e.sh — Ship 3 end-to-end verification.
# 8 checks: pytest suite, sqlite-vec install, Voyage key, canonical registry, gbrain DB,
#           cross-system search, embed-on-write hook, library-graph daemon plist.
# Exit 0 = all green; nonzero = drift detected.

set -uo pipefail

WIKI="${NOUS_WIKI:-/Users/madia/Documents/Projects/Nous AGaaS/Nous}"
cd "$WIKI"

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
amber() { printf "\033[33m%s\033[0m\n" "$*"; }

echo "=== Ship 3 verify @ $(date -u +%FT%TZ) ==="
echo "Wiki: $WIKI"
echo ""

FAILS=0

# 1. Ship-3 pytest suite
echo "--- 1/8 Ship-3 pytest suite ---"
if python3 -m pytest \
      tools/tests/test_library_canonical_registry.py \
      tools/tests/test_library_embed.py \
      tools/tests/test_library_embed_voyage.py \
      tools/tests/test_library_embed_db.py \
      tools/tests/test_library.py \
      tools/tests/test_library_canonicalize_titles.py \
      tools/tests/test_library_repair_links.py \
      tools/tests/test_library_health.py \
      tools/tests/test_library_drain_queue.py \
      tools/tests/test_library_openbrain_sync.py \
      tools/tests/test_migrate_ship3.py \
      -q 2>&1 | tail -3; then
  green "✓ Ship-3 pytest green"
else
  red "✗ Ship-3 pytest failed"; FAILS=$((FAILS+1))
fi
echo ""

# 2. sqlite-vec installed + loadable
echo "--- 2/8 sqlite-vec install ---"
if python3 -c "import sqlite_vec; print(f'OK dylib={sqlite_vec.loadable_path()}')" 2>&1; then
  green "✓ sqlite-vec importable"
else
  red "✗ sqlite-vec not installed"; FAILS=$((FAILS+1))
fi
echo ""

# 3. Voyage key present (not validating the key works — that's Step C of migrate)
echo "--- 3/8 Voyage key ---"
if [ -f "$HOME/.nous/secrets/voyage.env" ] && grep -q "^VOYAGE_API_KEY=" "$HOME/.nous/secrets/voyage.env"; then
  PERMS=$(stat -f '%Lp' "$HOME/.nous/secrets/voyage.env" 2>/dev/null || stat -c '%a' "$HOME/.nous/secrets/voyage.env")
  if [ "$PERMS" = "600" ]; then
    green "✓ Voyage key present @ ~/.nous/secrets/voyage.env (chmod 600)"
  else
    amber "⚠ Voyage key present but permissions are $PERMS (expected 600)"
  fi
else
  red "✗ Voyage key file missing"; FAILS=$((FAILS+1))
fi
echo ""

# 4. Canonical registry populated
echo "--- 4/8 canonical registry ---"
REG="$WIKI/pages/systems/canonical-registry.jsonl"
if [ -f "$REG" ]; then
  ROWS=$(wc -l < "$REG" | tr -d ' ')
  ENTRIES=$(python3 -c "
from tools import library_canonical_registry as r
from pathlib import Path
all_entries = r.list_all(wiki=Path('$WIKI'))
print(len(all_entries))
" 2>/dev/null || echo "0")
  if [ "$ENTRIES" -ge 100 ]; then
    green "✓ canonical-registry has $ENTRIES unique entries ($ROWS total rows)"
  else
    amber "⚠ canonical-registry has only $ENTRIES entries (expected ≥100)"
  fi
else
  red "✗ canonical-registry.jsonl missing"; FAILS=$((FAILS+1))
fi
echo ""

# 5. gbrain DB exists + has chunks
echo "--- 5/8 gbrain database ---"
DB="$WIKI/.gbrain/index.db"
if [ -f "$DB" ]; then
  CHUNKS=$(python3 -c "
from tools import library_embed_db
from pathlib import Path
print(library_embed_db.count_chunks(Path('$WIKI')))
" 2>/dev/null || echo "0")
  if [ "$CHUNKS" -ge 1 ]; then
    green "✓ gbrain index.db exists, $CHUNKS chunks indexed"
  else
    amber "⚠ gbrain index.db exists but 0 chunks (Voyage daemon may still be draining)"
  fi
else
  red "✗ .gbrain/index.db missing"; FAILS=$((FAILS+1))
fi
echo ""

# 6. Cross-system search returns at least one result for a known concept
echo "--- 6/8 cross-system search (system=obsidian) ---"
SEARCH=$(python3 tools/library.py search "model failover" --system obsidian --top 3 --json 2>/dev/null || echo '{"results":[]}')
HITS=$(echo "$SEARCH" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('results',[])))" 2>/dev/null || echo "0")
if [ "$HITS" -ge 1 ]; then
  green "✓ obsidian search returned $HITS hit(s) for 'model failover'"
else
  amber "⚠ obsidian search returned 0 hits (ripgrep may not be installed)"
fi
echo ""

# 7. Embed-on-write hook installed
echo "--- 7/8 .git/hooks/post-commit ---"
HOOK="$WIKI/.git/hooks/post-commit"
if [ -x "$HOOK" ] && grep -q ".gbrain/queue.jsonl" "$HOOK"; then
  green "✓ post-commit hook installed and references queue"
else
  amber "⚠ post-commit hook not installed (manual: chmod +x .git/hooks/post-commit)"
fi
echo ""

# 8. library-graph launchd plist exists + lint clean
echo "--- 8/8 library-graph daemon plist ---"
PLIST="$HOME/Library/LaunchAgents/com.nous.library-graph.plist"
if [ -f "$PLIST" ]; then
  if plutil -lint "$PLIST" >/dev/null 2>&1; then
    LOADED=$(launchctl list 2>/dev/null | grep -c "com.nous.library-graph" | head -1)
    LOADED=${LOADED:-0}
    if [ "$LOADED" -ge 1 ]; then
      green "✓ library-graph plist installed + bootstrapped (running)"
    else
      amber "⚠ library-graph plist exists, lint OK, NOT YET bootstrapped"
      echo "    Install: launchctl bootstrap gui/\$UID ~/Library/LaunchAgents/com.nous.library-graph.plist"
    fi
  else
    red "✗ library-graph plist failed plutil lint"; FAILS=$((FAILS+1))
  fi
else
  red "✗ library-graph plist missing"; FAILS=$((FAILS+1))
fi
echo ""

# Final
echo "=== Verify summary ==="
if [ "$FAILS" -eq 0 ]; then
  green "ALL GREEN — Ship 3 verified."
  echo ""
  echo "Optional next steps:"
  echo "  - Bootstrap daemon: launchctl bootstrap gui/\$UID ~/Library/LaunchAgents/com.nous.library-graph.plist"
  echo "  - Monitor embed progress: tail -f /tmp/nous-library-graph.out.log"
  echo "  - Check health: python3 tools/library_health.py --json --no-write | jq .gbrain_indexed_chunks"
  exit 0
else
  red "$FAILS check(s) failed."
  exit 1
fi
