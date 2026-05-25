#!/bin/bash
# test_skill_bump_requires_gbrain_timeline.sh
#
# Hybrid enforcement detector (session-68p, 2026-04-23, Madi directive
# "hybrid has to be physically impossible to bypass").
#
# RULE: every commit that BUMPS a SKILL.md version (frontmatter + H1 + Timeline
# per mistake-to-skill AP-11) MUST include gbrain timeline evidence in the
# commit message, matching the Tan/Karpathy/Finn RULE ZERO architecture:
#   - SKILL.md  = doctrine (read at runtime, flat-file wiki layer)
#   - gbrain    = structured evidence (queryable, graph + vector layer)
#
# Without this gate, sessions silently ship skill doctrine to the wiki that
# never lands in gbrain → search broken → future agents can't root-cause →
# compound decays. The hybrid becomes wiki-only (flat, unscalable, what
# Madi explicitly flagged as unacceptable).
#
# Evidence tokens accepted in commit message (any one):
#   gbrain-timeline-ok: <slug-or-skill-name>
#   gbrain entry id <NNN>                     (from mcp__gbrain__add_timeline_entry return)
#   gbrain timeline {status: ok}              (verbatim status line)
#   {status: ok}                              (bare — weakest but accepted)
#   gbrain-timeline-deferred: <reason>        (explicit bypass for MCP-down)
#
# Cross-refs:
#   - musk-algorithm AP-3 (physically-impossible-violated): this detector IS
#     the physical enforcement layer analogous to pre-commit RULE ZERO.
#   - karpathy-loop 6-axis scorecard axis-2 (gbrain timeline push): this gate
#     operationalizes axis-2 at commit-time instead of session-close honesty.
#   - gbrain-ops AP-33 (MCP-down CLI fallback): the `deferred:` bypass exists
#     for when both MCP and CLI paths fail simultaneously.
#   - mistake-to-skill AP-11 (3-edit ritual): triggers on SAME condition.
#
# Invoked by: .git/hooks/commit-msg (which passes $1 = commit message file).
# Standalone test: MSG_FILE=/tmp/msg.txt bash tools/test_skill_bump_requires_gbrain_timeline.sh
#
# Bypass: `git commit --no-verify` (operator-owned risk, same as other rules).

set -u

# Commit-msg hook passes message file as $1; fallback paths for testing.
MSG_FILE="${1:-${MSG_FILE:-.git/COMMIT_EDITMSG}}"

# SKIP merge commits (auto-generated messages don't carry gbrain evidence;
# merges don't introduce new skill bumps — they propagate already-gated commits).
# Detect via .git/MERGE_MSG existence OR message prefix.
if [ -f ".git/MERGE_MSG" ] || head -1 "$MSG_FILE" 2>/dev/null | grep -qE "^(Merge branch|Merge remote-tracking|Merge pull request)"; then
  exit 0
fi

# Find staged SKILL.md files with version: line changed
BUMPED_SKILLS=()
while IFS= read -r file; do
  [ -z "$file" ] && continue
  if git diff --cached "$file" 2>/dev/null | grep -qE '^[-+]version:\s'; then
    BUMPED_SKILLS+=("$file")
  fi
done < <(git diff --cached --name-only --diff-filter=AM 2>/dev/null | grep -E 'SKILL\.md$' || true)

if [ ${#BUMPED_SKILLS[@]} -eq 0 ]; then
  exit 0
fi

if [ ! -f "$MSG_FILE" ]; then
  echo "🔴 test_skill_bump_requires_gbrain_timeline: MSG_FILE not found ($MSG_FILE)" >&2
  echo "   This detector must be invoked from commit-msg hook or with MSG_FILE env var." >&2
  exit 1
fi

MSG=$(cat "$MSG_FILE")

# Accepted evidence patterns
if echo "$MSG" | grep -qE "gbrain-timeline-(ok|deferred):|gbrain entry id [0-9]+|gbrain timeline \{status: ok\}|\{status: ok\}|\{\"status\": \"ok\"\}"; then
  exit 0
fi

echo "🔴 BLOCKED: SKILL.md version bump without gbrain timeline evidence in commit message" >&2
echo "" >&2
echo "Bumped skills in this commit:" >&2
for s in "${BUMPED_SKILLS[@]}"; do echo "  - $s" >&2; done
echo "" >&2
echo "Hybrid enforcement (musk-algorithm AP-3 + karpathy-loop axis-2):" >&2
echo "every skill version bump MUST have matching gbrain timeline push." >&2
echo "" >&2
echo "FIX — push timeline FIRST, then add one of these tokens to commit message:" >&2
echo "" >&2
echo "  Via MCP:" >&2
echo "    mcp__gbrain__add_timeline_entry slug=<skill-slug> date=$(date +%F) summary='...'" >&2
echo "" >&2
echo "  Via CLI fallback (gbrain-ops AP-33, when MCP down):" >&2
echo "    ssh root@65.108.215.200 /opt/nous-agaas/gbrain/bin/gbrain timeline-add \\" >&2
echo "      --slug pages/skills/<name>/skill --date $(date +%F) --summary '...'" >&2
echo "" >&2
echo "Then commit message MUST contain one of:" >&2
echo "  gbrain-timeline-ok: <slug-or-skill-name>" >&2
echo "  gbrain entry id <NNN>" >&2
echo "  {status: ok}    (verbatim from gbrain response)" >&2
echo "  gbrain-timeline-deferred: <reason>    (explicit bypass when gbrain unreachable)" >&2
echo "" >&2
echo "Bypass this rule (operator risk): git commit --no-verify" >&2
exit 1
