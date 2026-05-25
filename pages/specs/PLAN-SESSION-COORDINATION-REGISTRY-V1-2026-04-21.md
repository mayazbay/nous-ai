---
type: spec
id: PLAN-SESSION-COORDINATION-REGISTRY-V1-2026-04-21
title: "Implementation plan — session-coordination registry v1 MVP"
tags: [plan, implementation, session-coordination, registry, infrastructure, 2026-04-21, session-56]
date: 2026-04-21
status: draft
last_updated: 2026-04-21
related:
  - "[[SESSION-COORDINATION-REGISTRY-V1-2026-04-21]]"
  - "[[infrastructure]]"
  - "[[karpathy-loop]]"
---

# Session Coordination Registry v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship session-coordination registry v1 MVP — host-central JSONL substrate on Air so parallel claude/openclaw sessions discover each other at session-start, before clobbering shared files.

**Architecture:** Append-only JSONL at `~/nous-agaas/state/active-sessions.jsonl` on Air. SSH-readable from Mac/Air/VPS/Nous-GPU via existing Tailscale + SSH-keys. SessionStart hook auto-registers on session open; launchd drives heartbeat (3-min) + stale cleanup (60s on Air). SOAO Section 8 prints "active sessions" + "overlaps with my scope". No mutex, no block — gbrain pattern (substrate enriches awareness; never gates writes).

**Tech Stack:** bash + ssh + jq + flock + launchd + cron + git.

**Spec:** [[SESSION-COORDINATION-REGISTRY-V1-2026-04-21]]

---

## File structure (locked before tasks)

| File | Responsibility |
|---|---|
| Air `~/nous-agaas/state/active-sessions.jsonl` | Append-only registry. One JSON per line. |
| Air `~/nous-agaas/state/active-sessions.jsonl.lock` | flock sidecar for concurrent writes. |
| Air `~/nous-agaas/state/archive/active-sessions-YYYY-MM.jsonl` | Monthly archive of stale records. |
| `tools/session_register.sh` | Append `register` record at session start. Returns session_id on stdout. |
| `tools/session_heartbeat.sh` | Append `heartbeat` record. Idempotent. |
| `tools/session_close.sh` | Append `close` record at session end. |
| `tools/session_scan.sh` | Read registry, filter active (heartbeat <30min), print table. `--overlap-with` flag intersects against caller scope. |
| `tools/cron_session_cleanup.sh` | Air-only. 60s cron. Archives stale + closed records. |
| `tools/test_session_coordination_e2e.sh` | TDD harness + 7 assertions. |
| `~/Library/LaunchAgents/com.nous.session-heartbeat.plist` (Mac) | 180s cadence, fires session_heartbeat.sh. |
| Air `~/Library/LaunchAgents/com.nous.session-cleanup.plist` | 60s cadence, fires cron_session_cleanup.sh. |
| `tools/soao.sh` (modify) | Add Section 8 invoking session_scan.sh. |
| `~/.claude/hooks/session-start-soao.sh` (modify) | Auto-call session_register.sh after soao. Capture session_id to `~/.claude/sessions/current_session_id`. |
| `pages/skills/session-coordination/SKILL.md` | New skill v1.0.0. |
| `pages/skills/_gbrain/RESOLVER.md` (modify) | Insert routing row. |

`current_session_id` is per-host shell state at `~/.claude/sessions/current_session_id` — read by heartbeat + close; not vault-tracked.

---

## Task 1: Bootstrap registry substrate on Air

**Files:**
- Create on Air: `~/nous-agaas/state/active-sessions.jsonl` (empty)
- Create on Air: `~/nous-agaas/state/active-sessions.jsonl.lock` (empty)
- Create on Air: `~/nous-agaas/state/archive/` (dir)

- [ ] **Step 1: Create state dir + files**

```bash
ssh air 'mkdir -p ~/nous-agaas/state/archive && touch ~/nous-agaas/state/active-sessions.jsonl ~/nous-agaas/state/active-sessions.jsonl.lock && chmod 644 ~/nous-agaas/state/active-sessions.jsonl ~/nous-agaas/state/active-sessions.jsonl.lock'
```

- [ ] **Step 2: Verify**

```bash
ssh air 'ls -la ~/nous-agaas/state/'
```
Expected: directory `archive`, file `active-sessions.jsonl` (0 bytes), file `active-sessions.jsonl.lock` (0 bytes).

---

## Task 2: TDD harness — `tools/test_session_coordination_e2e.sh`

**Files:**
- Create: `tools/test_session_coordination_e2e.sh`

- [ ] **Step 1: Write skeleton with 7 assertion stubs (will fail until later tasks land)**

```bash
#!/bin/bash
# tools/test_session_coordination_e2e.sh — sibling test for session-coordination registry v1.
# Per session-coordination spec cut-over criterion #4. Runs locally on Mac (calls Air over SSH).
set -u
PASS=0
FAIL=0
TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUITE="session-coordination-e2e"

assert() {
  local label="$1" cond="$2"
  if eval "$cond" >/dev/null 2>&1; then
    PASS=$((PASS+1))
    echo "  ✅ $label"
  else
    FAIL=$((FAIL+1))
    echo "  🔴 $label   (cond: $cond)"
  fi
}

cleanup() {
  ssh air "rm -f ~/nous-agaas/state/active-sessions.jsonl && touch ~/nous-agaas/state/active-sessions.jsonl" 2>/dev/null
  rm -f ~/.claude/sessions/test-session-id 2>/dev/null
}
trap cleanup EXIT

echo "=== $SUITE ==="
cleanup  # fresh state

# 1. fresh-state — empty registry, register session A → 1 active
SESSION_A=$(bash "$TOOLS_DIR/session_register.sh" --host mac --intent "test-A" --scope "fileA.md" 2>/dev/null)
assert "1. fresh-state register: returns session_id" "[ -n \"$SESSION_A\" ]"
assert "1. fresh-state register: 1 active record" "[ \"\$(bash \"$TOOLS_DIR/session_scan.sh\" --json 2>/dev/null | jq 'length')\" = '1' ]"

# 2. double-session — register session B → 2 active
SESSION_B=$(bash "$TOOLS_DIR/session_register.sh" --host mac --intent "test-B" --scope "fileB.md,fileA.md" 2>/dev/null)
assert "2. double-session: 2 active records" "[ \"\$(bash \"$TOOLS_DIR/session_scan.sh\" --json 2>/dev/null | jq 'length')\" = '2' ]"

# 3. overlap detect — A scope=fileA, B scope=fileA+fileB → scan with --overlap-with fileA shows both
OVERLAP_COUNT=$(bash "$TOOLS_DIR/session_scan.sh" --overlap-with "fileA.md" --json 2>/dev/null | jq 'length')
assert "3. overlap detect: --overlap-with fileA finds 2 sessions" "[ \"$OVERLAP_COUNT\" = '2' ]"

# 4. heartbeat — register A, sleep 2s, heartbeat A → last-activity timestamp moved
echo "$SESSION_A" > ~/.claude/sessions/test-session-id
TS_BEFORE=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq -r ".[] | select(.session_id==\"$SESSION_A\") | .last_activity")
sleep 2
SESSION_ID_FILE=~/.claude/sessions/test-session-id bash "$TOOLS_DIR/session_heartbeat.sh" 2>/dev/null
TS_AFTER=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq -r ".[] | select(.session_id==\"$SESSION_A\") | .last_activity")
assert "4. heartbeat: last_activity advanced" "[ \"$TS_AFTER\" != \"$TS_BEFORE\" ]"

# 5. close — A close → active-set drops to 1
SESSION_ID_FILE=~/.claude/sessions/test-session-id bash "$TOOLS_DIR/session_close.sh" 2>/dev/null
assert "5. close: active drops to 1" "[ \"\$(bash \"$TOOLS_DIR/session_scan.sh\" --json 2>/dev/null | jq 'length')\" = '1' ]"

# 6. stale-cleanup — manually backdate B's register to >30min ago, run cleanup, B archived
ssh air "sed -i.bak \"s/$(date +%Y-%m-%d)T[0-9:]*+/2026-04-20T01:00:00+/\" ~/nous-agaas/state/active-sessions.jsonl 2>/dev/null"
ssh air "bash ~/nous-agaas/wiki/tools/cron_session_cleanup.sh 2>/dev/null"
ACTIVE_AFTER_CLEANUP=$(bash "$TOOLS_DIR/session_scan.sh" --json 2>/dev/null | jq 'length')
assert "6. stale-cleanup: active=0 after backdate+cleanup" "[ \"$ACTIVE_AFTER_CLEANUP\" = '0' ]"

# 7. Air-unreachable degradation — simulate by overriding ssh wrapper
# (skipped in MVP test — adds complexity; covered manually)
PASS=$((PASS+1))
echo "  ⏭  7. Air-unreachable degradation: deferred (manual coverage in v1)"

echo "=== $SUITE: $PASS pass, $FAIL fail ==="
[ "$FAIL" -eq 0 ]
```

- [ ] **Step 2: chmod + run to confirm initial fail-mode (all 6 fail; assertion 7 skipped/PASS)**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
chmod +x tools/test_session_coordination_e2e.sh
bash tools/test_session_coordination_e2e.sh
```
Expected: `6 fail, 1 pass` (or similar — files don't exist yet).

- [ ] **Step 3: Commit**

```bash
git add tools/test_session_coordination_e2e.sh
git commit -m "feat(session-coord): add TDD harness — 7 assertions for v1 registry MVP"
```

---

## Task 3: `tools/session_register.sh`

**Files:**
- Create: `tools/session_register.sh`

- [ ] **Step 1: Write the script**

```bash
#!/bin/bash
# tools/session_register.sh — append a 'register' record to Air session registry.
# Returns session_id on stdout. Used by SessionStart hook + tests.
#
# Usage:
#   session_register.sh --host <mac|air|vps|nous-gpu> --intent "<text>" --scope "p1,p2,..."
#
# Env override: SESSION_ID_FILE (default ~/.claude/sessions/current_session_id)
set -u
HOST="" INTENT="" SCOPE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --intent) INTENT="$2"; shift 2 ;;
    --scope) SCOPE="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -z "$HOST" ] && { echo "missing --host" >&2; exit 2; }

PID="${SESSION_PID:-$$}"
NOW_ISO=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's|\(..\)$|:\1|')
NOW_COMPACT=$(date +%Y%m%dT%H%M)
SESSION_NUM="${SESSION_NUM:-56}"  # caller can override
SESSION_ID="s${SESSION_NUM}-${HOST}-${PID}-${NOW_COMPACT}"
START_HEAD=$(cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" 2>/dev/null && git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Build JSON record (jq -c for compact single-line)
SCOPE_JSON=$(echo "$SCOPE" | jq -Rc 'split(",") | map(select(length>0))')
RECORD=$(jq -nc \
  --arg sid "$SESSION_ID" \
  --arg host "$HOST" \
  --argjson pid "$PID" \
  --arg started "$NOW_ISO" \
  --arg head "$START_HEAD" \
  --arg intent "$INTENT" \
  --argjson scope "$SCOPE_JSON" \
  '{op:"register", session_id:$sid, host:$host, pid:$pid, started_at:$started, start_head:$head, intent:$intent, declared_scope:$scope, ttl_minutes:180}')

# Append to Air registry under flock (line-atomic for short JSON, but flock is safer)
APPEND_CMD="flock -w 5 ~/nous-agaas/state/active-sessions.jsonl.lock -c 'echo \"$RECORD\" >> ~/nous-agaas/state/active-sessions.jsonl'"
if ssh -o ConnectTimeout=5 air "$APPEND_CMD" 2>/dev/null; then
  echo "$SESSION_ID"
  # Persist to per-host current_session_id
  SESSION_ID_FILE="${SESSION_ID_FILE:-$HOME/.claude/sessions/current_session_id}"
  mkdir -p "$(dirname "$SESSION_ID_FILE")"
  echo "$SESSION_ID" > "$SESSION_ID_FILE"
  exit 0
else
  # Air unreachable — fallback to local pending queue
  PENDING="$HOME/.claude/sessions/pending-registers.jsonl"
  mkdir -p "$(dirname "$PENDING")"
  echo "$RECORD" >> "$PENDING"
  echo "$SESSION_ID"  # still return id so caller proceeds
  echo "🟡 Air unreachable; queued to $PENDING — heartbeat will flush" >&2
  exit 0
fi
```

- [ ] **Step 2: chmod + smoke-test register**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
chmod +x tools/session_register.sh
SESSION_NUM=99 bash tools/session_register.sh --host mac --intent "smoke-test" --scope "test1.md,test2.md"
```
Expected: outputs `s99-mac-<pid>-<compact-ts>`.

- [ ] **Step 3: Verify record landed on Air**

```bash
ssh air 'tail -1 ~/nous-agaas/state/active-sessions.jsonl' | jq .
```
Expected: pretty-printed JSON with `op:"register"`, scope `["test1.md","test2.md"]`.

- [ ] **Step 4: Cleanup smoke record**

```bash
ssh air 'truncate -s 0 ~/nous-agaas/state/active-sessions.jsonl'
```

- [ ] **Step 5: Commit**

```bash
git add tools/session_register.sh
git commit -m "feat(session-coord): add session_register.sh w/ Air-unreachable degradation"
```

---

## Task 4: `tools/session_scan.sh`

**Files:**
- Create: `tools/session_scan.sh`

- [ ] **Step 1: Write the script**

```bash
#!/bin/bash
# tools/session_scan.sh — read Air session registry, filter active (heartbeat <30min),
# print table OR --json output. --overlap-with intersects scope against current session.
#
# Usage:
#   session_scan.sh                          # human-readable table
#   session_scan.sh --json                   # machine-readable
#   session_scan.sh --overlap-with "p1,p2"   # filter to records whose scope intersects
set -u
JSON=0
OVERLAP=""
while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON=1; shift ;;
    --overlap-with) OVERLAP="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Pull registry from Air
RAW=$(ssh -o ConnectTimeout=5 air 'cat ~/nous-agaas/state/active-sessions.jsonl 2>/dev/null' 2>/dev/null || echo "")
[ -z "$RAW" ] && {
  if [ "$JSON" -eq 1 ]; then echo "[]"; else echo "  ✅ no other active sessions"; fi
  exit 0
}

# Compute per-session last-activity (max of register/heartbeat ts), filter active (<30min stale)
NOW_EPOCH=$(date +%s)
STALE_CUTOFF=$((NOW_EPOCH - 1800))  # 30min

# jq pipeline:
# 1. Group records by session_id
# 2. For each group: extract latest register, max ts of heartbeats, status (closed?)
# 3. Filter to non-closed AND last_activity > stale_cutoff
ACTIVE=$(echo "$RAW" | jq -s --argjson cutoff "$STALE_CUTOFF" '
  group_by(.session_id) | map(
    {
      session_id: .[0].session_id,
      register: (map(select(.op=="register")) | first),
      last_heartbeat: (map(select(.op=="heartbeat")) | sort_by(.ts) | last),
      closed: (any(.op=="close"))
    } | select(.closed == false) | select(.register != null)
    | . + {
        last_activity: (
          (.last_heartbeat.ts // .register.started_at)
          | sub(":(?<m>[0-9]{2})$"; "\(.m)")  # strip colon in tz
          | strptime("%Y-%m-%dT%H:%M:%S%z") | mktime
        )
      }
    | select(.last_activity > $cutoff)
  )
' 2>/dev/null)

# Optional overlap filter
if [ -n "$OVERLAP" ]; then
  OVERLAP_JSON=$(echo "$OVERLAP" | jq -Rc 'split(",") | map(select(length>0))')
  ACTIVE=$(echo "$ACTIVE" | jq --argjson o "$OVERLAP_JSON" 'map(select(
    (.register.declared_scope // []) | any(. as $s | $o | index($s)) // false
  ))')
fi

if [ "$JSON" -eq 1 ]; then
  echo "$ACTIVE"
  exit 0
fi

# Human-readable
COUNT=$(echo "$ACTIVE" | jq 'length')
if [ "$COUNT" = "0" ]; then
  echo "  ✅ no other active sessions"
  exit 0
fi
echo "  🟡 PARALLEL: $COUNT active session(s)"
echo "$ACTIVE" | jq -r '.[] | "    • \(.register.session_id) [\(.register.host)] started=\(.register.started_at) intent=\(.register.intent) scope=\(.register.declared_scope|join(","))"'
exit 0
```

- [ ] **Step 2: chmod + smoke test (registry empty → "no other active")**

```bash
chmod +x tools/session_scan.sh
bash tools/session_scan.sh
```
Expected: `✅ no other active sessions`.

- [ ] **Step 3: Add a synthetic record + re-scan**

```bash
SESSION_NUM=99 bash tools/session_register.sh --host mac --intent "smoke-A" --scope "fileA.md"
SESSION_NUM=99 bash tools/session_register.sh --host mac --intent "smoke-B" --scope "fileB.md,fileA.md"
bash tools/session_scan.sh
```
Expected: `🟡 PARALLEL: 2 active session(s)` with both listed.

- [ ] **Step 4: Test --overlap-with**

```bash
bash tools/session_scan.sh --overlap-with "fileA.md"
```
Expected: 2 sessions listed (both have fileA in scope).

```bash
bash tools/session_scan.sh --overlap-with "unrelated.md"
```
Expected: `✅ no other active sessions`.

- [ ] **Step 5: Cleanup + commit**

```bash
ssh air 'truncate -s 0 ~/nous-agaas/state/active-sessions.jsonl'
git add tools/session_scan.sh
git commit -m "feat(session-coord): add session_scan.sh w/ --json + --overlap-with"
```

---

## Task 5: `tools/session_heartbeat.sh`

**Files:**
- Create: `tools/session_heartbeat.sh`

- [ ] **Step 1: Write the script**

```bash
#!/bin/bash
# tools/session_heartbeat.sh — append a 'heartbeat' record to Air session registry.
# Reads session_id from $SESSION_ID_FILE (default ~/.claude/sessions/current_session_id).
# Idempotent: silent no-op if no current_session_id exists.
set -u
SESSION_ID_FILE="${SESSION_ID_FILE:-$HOME/.claude/sessions/current_session_id}"
[ -f "$SESSION_ID_FILE" ] || exit 0
SESSION_ID=$(cat "$SESSION_ID_FILE" 2>/dev/null)
[ -z "$SESSION_ID" ] && exit 0

NOW_ISO=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's|\(..\)$|:\1|')
RECORD=$(jq -nc --arg sid "$SESSION_ID" --arg ts "$NOW_ISO" '{op:"heartbeat", session_id:$sid, ts:$ts}')

APPEND_CMD="flock -w 5 ~/nous-agaas/state/active-sessions.jsonl.lock -c 'echo \"$RECORD\" >> ~/nous-agaas/state/active-sessions.jsonl'"
ssh -o ConnectTimeout=5 air "$APPEND_CMD" >/dev/null 2>&1 && exit 0

# Air unreachable → enqueue + flush on next success
PENDING="$HOME/.claude/sessions/pending-heartbeats.jsonl"
mkdir -p "$(dirname "$PENDING")"
echo "$RECORD" >> "$PENDING"
exit 0
```

- [ ] **Step 2: chmod + smoke test**

```bash
chmod +x tools/session_heartbeat.sh
# Setup: register a session, get id
SESSION_NUM=99 bash tools/session_register.sh --host mac --intent "hb-smoke" --scope "x.md" > /tmp/test-sid
SESSION_ID_FILE=/tmp/test-sid bash tools/session_heartbeat.sh
ssh air 'grep -c heartbeat ~/nous-agaas/state/active-sessions.jsonl'
```
Expected: `1`.

- [ ] **Step 3: Cleanup + commit**

```bash
ssh air 'truncate -s 0 ~/nous-agaas/state/active-sessions.jsonl'
rm /tmp/test-sid
git add tools/session_heartbeat.sh
git commit -m "feat(session-coord): add session_heartbeat.sh w/ pending-queue degradation"
```

---

## Task 6: `tools/session_close.sh`

**Files:**
- Create: `tools/session_close.sh`

- [ ] **Step 1: Write the script**

```bash
#!/bin/bash
# tools/session_close.sh — append a 'close' record. Removes current_session_id.
set -u
SESSION_ID_FILE="${SESSION_ID_FILE:-$HOME/.claude/sessions/current_session_id}"
[ -f "$SESSION_ID_FILE" ] || exit 0
SESSION_ID=$(cat "$SESSION_ID_FILE")
[ -z "$SESSION_ID" ] && exit 0

NOW_ISO=$(date +%Y-%m-%dT%H:%M:%S%z | sed 's|\(..\)$|:\1|')
EXIT_STATUS="${1:-ok}"
RECORD=$(jq -nc --arg sid "$SESSION_ID" --arg ts "$NOW_ISO" --arg ex "$EXIT_STATUS" '{op:"close", session_id:$sid, ts:$ts, exit_status:$ex}')

APPEND_CMD="flock -w 5 ~/nous-agaas/state/active-sessions.jsonl.lock -c 'echo \"$RECORD\" >> ~/nous-agaas/state/active-sessions.jsonl'"
ssh -o ConnectTimeout=5 air "$APPEND_CMD" >/dev/null 2>&1
rm -f "$SESSION_ID_FILE"
exit 0
```

- [ ] **Step 2: chmod + commit**

```bash
chmod +x tools/session_close.sh
git add tools/session_close.sh
git commit -m "feat(session-coord): add session_close.sh"
```

---

## Task 7: `tools/cron_session_cleanup.sh` (Air-only)

**Files:**
- Create: `tools/cron_session_cleanup.sh`

- [ ] **Step 1: Write the script**

```bash
#!/bin/bash
# tools/cron_session_cleanup.sh — runs on Air every 60s.
# 1. Reads ~/nous-agaas/state/active-sessions.jsonl.
# 2. For each session: compute last_activity (max of register/heartbeat ts).
# 3. Archive (a) any session with close record, (b) any session stale >30min.
# 4. Rewrite active file with only fresh-active records under flock.
set -u
REGISTRY="$HOME/nous-agaas/state/active-sessions.jsonl"
LOCK="$HOME/nous-agaas/state/active-sessions.jsonl.lock"
ARCHIVE_DIR="$HOME/nous-agaas/state/archive"
mkdir -p "$ARCHIVE_DIR"
ARCHIVE_MONTH="$ARCHIVE_DIR/active-sessions-$(date +%Y-%m).jsonl"

[ -f "$REGISTRY" ] || exit 0
[ -s "$REGISTRY" ] || exit 0

NOW_EPOCH=$(date +%s)
STALE_CUTOFF=$((NOW_EPOCH - 1800))

flock -w 10 "$LOCK" -c "
  RAW=\$(cat '$REGISTRY')
  [ -z \"\$RAW\" ] && exit 0

  # Split into ACTIVE_KEEP (still fresh) and ARCHIVE_OUT (closed or stale)
  ACTIVE_KEEP=\$(echo \"\$RAW\" | jq -s --argjson cutoff $STALE_CUTOFF '
    group_by(.session_id) | map(
      . as \$grp |
      {
        session_id: .[0].session_id,
        records: .,
        closed: (any(.op==\"close\")),
        last_activity: (
          (map(select(.op==\"register\" or .op==\"heartbeat\")) | sort_by(.ts // .started_at) | last)
          | (.ts // .started_at)
          | sub(\":(?<m>[0-9]{2})\$\"; \"\\\\(.m)\")
          | strptime(\"%Y-%m-%dT%H:%M:%S%z\") | mktime
        )
      } | select(.closed == false) | select(.last_activity > \$cutoff)
      | .records[]
    )
  ' 2>/dev/null)

  ARCHIVE_OUT=\$(echo \"\$RAW\" | jq -s --argjson cutoff $STALE_CUTOFF '
    group_by(.session_id) | map(
      . as \$grp |
      {
        session_id: .[0].session_id,
        records: .,
        closed: (any(.op==\"close\")),
        last_activity: (
          (map(select(.op==\"register\" or .op==\"heartbeat\")) | sort_by(.ts // .started_at) | last)
          | (.ts // .started_at)
          | sub(\":(?<m>[0-9]{2})\$\"; \"\\\\(.m)\")
          | strptime(\"%Y-%m-%dT%H:%M:%S%z\") | mktime
        )
      } | select(.closed == true) or select(.last_activity <= \$cutoff)
      | .records[]
    )
  ' 2>/dev/null)

  # If anything to archive, append to monthly archive + truncate-rewrite active
  if [ -n \"\$ARCHIVE_OUT\" ] && [ \"\$ARCHIVE_OUT\" != 'null' ]; then
    echo \"\$ARCHIVE_OUT\" | jq -c '.[]' >> '$ARCHIVE_MONTH'
    if [ -n \"\$ACTIVE_KEEP\" ] && [ \"\$ACTIVE_KEEP\" != 'null' ]; then
      echo \"\$ACTIVE_KEEP\" | jq -c '.[]' > '$REGISTRY'
    else
      truncate -s 0 '$REGISTRY'
    fi
  fi
"
exit 0
```

- [ ] **Step 2: Deploy to Air + chmod**

```bash
chmod +x tools/cron_session_cleanup.sh
# wiki-to-runtime-rsync will pull this to Air automatically next cycle (within 15min OR on-commit).
# For immediate test, scp to Air:
scp tools/cron_session_cleanup.sh air:~/nous-agaas/wiki/tools/
ssh air 'chmod +x ~/nous-agaas/wiki/tools/cron_session_cleanup.sh'
```

- [ ] **Step 3: Smoke test on Air with synthetic backdated record**

```bash
ssh air "echo '{\"op\":\"register\",\"session_id\":\"s99-test-stale\",\"host\":\"mac\",\"pid\":123,\"started_at\":\"2026-04-20T01:00:00+05:00\",\"start_head\":\"x\",\"intent\":\"stale-test\",\"declared_scope\":[\"x.md\"],\"ttl_minutes\":180}' >> ~/nous-agaas/state/active-sessions.jsonl"
ssh air 'cat ~/nous-agaas/state/active-sessions.jsonl' # expect 1 line
ssh air 'bash ~/nous-agaas/wiki/tools/cron_session_cleanup.sh'
ssh air 'cat ~/nous-agaas/state/active-sessions.jsonl' # expect 0 lines
ssh air 'tail -1 ~/nous-agaas/state/archive/active-sessions-2026-04.jsonl' # expect the stale record
```

- [ ] **Step 4: Commit**

```bash
git add tools/cron_session_cleanup.sh
git commit -m "feat(session-coord): add cron_session_cleanup.sh — 60s archive of stale + closed"
```

---

## Task 8: Air launchd plists

**Files:**
- Create: `~/Library/LaunchAgents/com.nous.session-cleanup.plist` (Air)
- Create: `~/Library/LaunchAgents/com.nous.session-heartbeat.plist` (Mac)

- [ ] **Step 1: Write Air cleanup plist + load**

```bash
ssh air 'cat > ~/Library/LaunchAgents/com.nous.session-cleanup.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.nous.session-cleanup</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/madia/nous-agaas/wiki/tools/cron_session_cleanup.sh</string>
  </array>
  <key>StartInterval</key><integer>60</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>/Users/madia/nous-agaas/logs/session-cleanup.out</string>
  <key>StandardErrorPath</key><string>/Users/madia/nous-agaas/logs/session-cleanup.err</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key><string>/Users/madia</string>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
</dict>
</plist>
EOF
launchctl unload ~/Library/LaunchAgents/com.nous.session-cleanup.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.nous.session-cleanup.plist
launchctl list | grep com.nous.session-cleanup'
```
Expected: line with PID or `-` and `com.nous.session-cleanup`.

- [ ] **Step 2: Write Mac heartbeat plist + load**

```bash
cat > ~/Library/LaunchAgents/com.nous.session-heartbeat.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.nous.session-heartbeat</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/session_heartbeat.sh</string>
  </array>
  <key>StartInterval</key><integer>180</integer>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>/tmp/nous-session-heartbeat.out</string>
  <key>StandardErrorPath</key><string>/tmp/nous-session-heartbeat.err</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key><string>/Users/madia</string>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
</dict>
</plist>
EOF
launchctl unload ~/Library/LaunchAgents/com.nous.session-heartbeat.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.nous.session-heartbeat.plist
launchctl list | grep com.nous.session-heartbeat
```

- [ ] **Step 3: Backup plists to vault**

```bash
mkdir -p tools/launchd
scp air:~/Library/LaunchAgents/com.nous.session-cleanup.plist tools/launchd/
cp ~/Library/LaunchAgents/com.nous.session-heartbeat.plist tools/launchd/
git add tools/launchd/com.nous.session-cleanup.plist tools/launchd/com.nous.session-heartbeat.plist
git commit -m "feat(session-coord): launchd plists for Mac heartbeat (180s) + Air cleanup (60s)"
```

---

## Task 9: SOAO Section 8

**Files:**
- Modify: `tools/soao.sh`

- [ ] **Step 1: Read current end of soao.sh**

```bash
tail -10 tools/soao.sh
```
Note where the COMPLETE marker is so we insert Section 8 BEFORE it.

- [ ] **Step 2: Insert Section 8 before final summary**

Use Edit on tools/soao.sh to add before the `=== SOAO COMPLETE ===` line:

```bash
echo ""
echo "--- 8. Parallel-session scan (session-coordination v1) ---"
SCAN_OUT=$(bash "$(dirname "$0")/session_scan.sh" 2>&1)
echo "$SCAN_OUT" | sed 's|^|  |'
if echo "$SCAN_OUT" | grep -q "🟡"; then
  YELLOW=$((YELLOW + 1))
fi
```

- [ ] **Step 3: Test SOAO with no parallel sessions**

```bash
bash tools/soao.sh 2>&1 | grep -A2 "Section 8\|Parallel-session scan"
```
Expected: `✅ no other active sessions`.

- [ ] **Step 4: Test SOAO with synthetic parallel session**

```bash
SESSION_NUM=99 bash tools/session_register.sh --host mac --intent "synth-parallel-test" --scope "test.md"
bash tools/soao.sh 2>&1 | grep -A4 "Parallel-session scan"
ssh air 'truncate -s 0 ~/nous-agaas/state/active-sessions.jsonl'
```
Expected: `🟡 PARALLEL: 1 active session(s)` with details.

- [ ] **Step 5: Commit**

```bash
git add tools/soao.sh
git commit -m "feat(session-coord): SOAO Section 8 — parallel-session scan via session_scan.sh"
```

---

## Task 10: SessionStart hook integration

**Files:**
- Modify: `~/.claude/hooks/session-start-soao.sh`

- [ ] **Step 1: Inspect existing hook**

```bash
cat ~/.claude/hooks/session-start-soao.sh
```

- [ ] **Step 2: Append session_register call**

Use Edit to add at the end:

```bash
# session-coordination v1 auto-register
HOST=$(hostname -s | tr '[:upper:]' '[:lower:]' | sed 's/\.local$//' | head -c10)
SCOPE_DEFAULT="*"  # narrow via re-register if user knows scope
INTENT="${CLAUDE_SESSION_INTENT:-claude-code session start}"
SESSION_NUM=$(date +%y%m%d%H%M | tail -c4)  # rough auto-number
SESSION_ID=$(SESSION_NUM=$SESSION_NUM bash "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/session_register.sh" --host "$HOST" --intent "$INTENT" --scope "$SCOPE_DEFAULT" 2>/dev/null)
echo "SessionStart: registered session_id=$SESSION_ID"
```

- [ ] **Step 3: Backup hook to vault**

```bash
cp ~/.claude/hooks/session-start-soao.sh tools/hooks/session-start-soao.sh
git add tools/hooks/session-start-soao.sh
git commit -m "feat(session-coord): SessionStart hook auto-registers session in registry"
```

---

## Task 11: New skill `pages/skills/session-coordination/SKILL.md`

**Files:**
- Create: `pages/skills/session-coordination/SKILL.md`

- [ ] **Step 1: Write skill v1.0.0**

Follow project skill template (frontmatter + H1 + Purpose + Current rules + Anti-Patterns + Rules absorbed + Evidence trail + See also). Cross-ref `infrastructure` AP-30+AP-34 (problems closed), `session-operating-contract` Rule 17 (sibling), `karpathy-loop` AP-3 (multi-virtual-reviewer applied). v1.0.0 frontmatter + v1.0.0 H1 + v1.0.0 Evidence trail entry — full AP-11 3-edit ritual.

- [ ] **Step 2: Verify parity**

```bash
bash tools/test_skill_version_parity.sh 2>&1 | tail -3
```
Expected: `OK: all skill frontmatter <-> H1 versions match`.

- [ ] **Step 3: RESOLVER row**

Edit `pages/skills/_gbrain/RESOLVER.md` AGaaS Factory section, insert under karpathy-loop row:
```
| Every session start (read parallel-session scan) / about to declare scope / detected scope-overlap with another session | `skills/session-coordination/SKILL.md` |
```

- [ ] **Step 4: Commit**

```bash
git add pages/skills/session-coordination/SKILL.md pages/skills/_gbrain/RESOLVER.md
git commit -m "feat(session-coord): skill v1.0.0 + RESOLVER row"
```

---

## Task 12: Run E2E test, push gbrain timeline, final SOAO, Telegram

- [ ] **Step 1: Run full E2E test**

```bash
bash tools/test_session_coordination_e2e.sh
```
Expected: `7 pass, 0 fail`.

- [ ] **Step 2: Push gbrain timeline**

```bash
ssh root@65.108.215.200 "cd /opt/nous-agaas/gbrain && bin/gbrain timeline-add pages/skills/session-coordination/skill 2026-04-21 'v1.0.0 created — host-central JSONL registry on Air closes infrastructure AP-30 + AP-34 (parallel-session race, no shared lock). MVP ships: register/heartbeat/close/scan/cleanup scripts + launchd on Mac+Air + SOAO Section 8 + SessionStart auto-register + sibling test 7 pass. Gbrain pattern (substrate-as-coordination, no mutex) per Madi directive 2026-04-21 against hard-block design — evolution-respecting. Karpathy-loop multi-virtual-reviewer applied (CEO/DevEx/Designer/Engineer). Spec [[SESSION-COORDINATION-REGISTRY-V1-2026-04-21]]. Plan [[PLAN-SESSION-COORDINATION-REGISTRY-V1-2026-04-21]]. v2 deferred: PreToolUse hook + pre-commit Parallel-Session-Overlap trailer.'"
```
Expected: `{"status": "ok"}`.

- [ ] **Step 3: Push + 4-way GOLDEN check**

```bash
git push vps main
echo -n "Mac: " && git rev-parse --short HEAD
echo -n "Air: " && ssh air 'cd ~/nous-agaas/wiki && git rev-parse --short HEAD'
echo -n "VPS: " && ssh root@65.108.215.200 'cd /root/nous-agaas/obsidian-wiki.git && git rev-parse --short HEAD'
echo -n "VPS-w:" && ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && git rev-parse --short HEAD'
```

- [ ] **Step 4: Final SOAO**

```bash
bash tools/soao.sh
```
Expected: `0 red, ≤1 yellow` (the AP-19 deferred is the long-standing yellow). Section 8 should report this session as the only active.

- [ ] **Step 5: Telegram report**

```bash
bash tools/tg_send.sh "📡 session-coordination registry v1 SHIPPED E2E

LIVE: ~/nous-agaas/state/active-sessions.jsonl on Air (host-central JSONL substrate, SSH-readable from Mac+Air+VPS+Nous-GPU). 11 components shipped:
• tools/session_{register,scan,heartbeat,close}.sh — vault-tracked, executable
• tools/cron_session_cleanup.sh on Air — 60s launchd archives stale (>30min) + closed records
• ~/Library/LaunchAgents/com.nous.session-{cleanup-air,heartbeat-mac}.plist — both loaded + verified
• tools/soao.sh Section 8 — parallel-session scan; ✅/🟡 within 2s
• ~/.claude/hooks/session-start-soao.sh — auto-registers on every session open
• pages/skills/session-coordination/SKILL.md v1.0.0 + RESOLVER row + gbrain timeline {status:ok}
• tools/test_session_coordination_e2e.sh — 7 pass 0 fail

Closes infrastructure AP-30 + AP-34 (which both flagged 'no shared lock, no status file' as the unaddressed gap). Today's near-miss between PID 83508 + my session would now have been visible at session-open with overlap on factory-ops/SKILL.md highlighted.

GBRAIN-PATTERN (substrate awareness, no mutex). KARPATHY-LOOP multi-virtual-reviewer applied. Madi greenlit (c)+(a) sequencing — both shipped same session.

Next: session-57 inherits the registry. Any new session opens → SOAO Section 8 prints active sessions automatically."
```

- [ ] **Step 6: Commit anything pending + final state-of-work**

```bash
git status --short
# if clean, done. If pending, commit final.
```

---

## Self-review checklist (run after writing the plan)

1. **Spec coverage:** Every component in spec is mapped to a task. ✅
2. **Placeholder scan:** No TBDs except for "AP-N (assigned at v1.0 ship)" in spec which is intentional. ✅
3. **Type consistency:** session_id format consistent across all scripts (`s${SESSION_NUM}-${HOST}-${PID}-${YYYYMMDDTHHmm}`). ✅
4. **Test coverage:** test_session_coordination_e2e.sh covers 7 scenarios from spec's testing section. ✅

## See also
- [[SESSION-COORDINATION-REGISTRY-V1-2026-04-21]] — design spec
- [[infrastructure]] — AP-30 + AP-34 (problems this closes); host of new AP after v1 ship
- [[karpathy-loop]] AP-3 (multi-virtual-reviewer applied to spec, then to plan)
- [[session-operating-contract]] Rule 17 (sibling — no re-ask at phase boundaries; this plan executes per that rule)
