#!/bin/bash
# Test: wiki-to-runtime-rsync.sh must:
# 1. Copy pages/skills/ content to runtime dir
# 2. NEVER use --delete
# 3. Sync _gbrain/ additively + exclude extracted/
# 4. Use flock for concurrency safety
set -euo pipefail

TEST_SRC=$(mktemp -d)
TEST_DST=$(mktemp -d)
trap "rm -rf $TEST_SRC $TEST_DST /tmp/wiki-rsync-test.lock" EXIT
VAULT="${VAULT:-$(cd "$(dirname "$0")/.." && pwd)}"

# Seed fake wiki skills
mkdir -p "$TEST_SRC/pages/skills/foo" "$TEST_SRC/pages/skills/_gbrain" "$TEST_SRC/pages/skills/extracted"
echo "foo skill content" > "$TEST_SRC/pages/skills/foo/SKILL.md"
echo "should-not-sync" > "$TEST_SRC/pages/skills/_gbrain/skill-creator"
echo "draft" > "$TEST_SRC/pages/skills/extracted/bar-SKILL.md"

# Seed existing runtime skill (MUST NOT be deleted by rsync)
mkdir -p "$TEST_DST/existing-skill"
echo "pre-existing content" > "$TEST_DST/existing-skill/SKILL.md"

# Run the script with overridden paths
WIKI_SKILLS_DIR="$TEST_SRC/pages/skills" \
RUNTIME_SKILLS_DIR="$TEST_DST" \
LOCK_FILE="/tmp/wiki-rsync-test.lock" \
LOG_DIR="/tmp" \
bash "$VAULT/tools/wiki-to-runtime-rsync.sh"

# Assertions
[ -f "$TEST_DST/foo/SKILL.md" ] || { echo "FAIL: foo not synced"; exit 1; }
grep -q "foo skill content" "$TEST_DST/foo/SKILL.md" || { echo "FAIL: foo content wrong"; exit 1; }
[ -f "$TEST_DST/_gbrain/skill-creator" ] || { echo "FAIL: _gbrain not synced"; exit 1; }
grep -q "should-not-sync" "$TEST_DST/_gbrain/skill-creator" || { echo "FAIL: _gbrain content wrong"; exit 1; }
[ ! -f "$TEST_DST/extracted/bar-SKILL.md" ] || { echo "FAIL: extracted leaked through"; exit 1; }
[ -f "$TEST_DST/existing-skill/SKILL.md" ] || { echo "FAIL: existing skill was deleted (--delete used!)"; exit 1; }
grep -q "pre-existing content" "$TEST_DST/existing-skill/SKILL.md" || { echo "FAIL: existing content modified"; exit 1; }

echo "PASS: all 5 assertions green"
