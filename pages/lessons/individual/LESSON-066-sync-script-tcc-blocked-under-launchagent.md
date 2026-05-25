---
type: lesson
id: LESSON-066
title: "Mac↔VPS sync script silently failing under LaunchAgent/cron due to macOS TCC block on /bin/bash"
tags: [lesson, sync, launchagent, cron, tcc, full-disk-access, macos, git, observability, root-cause]
date: 2026-04-08
source_count: 0
status: implicit-already-in-skill
absorbed_into: [infrastructure]
absorbed_at: 2026-04-16
last_updated: 2026-04-08
related: [sync-repair-2026-04-08, LAW-005-obsidian-master, AUDIT-024-physical-enforcement-of-law5, AUDIT-027-god-level-alignment-vs-trefethen-mempalace-brain, LESSON-064-silent-ack-success-path]
integrated_into: infrastructure
---

# LESSON-066 — Mac↔VPS sync script silently failing under LaunchAgent/cron due to macOS TCC block on `/bin/bash`

## What happened (short)

The Mac-side bidirectional sync (`/Users/madia/.local/bin/nous-obsidian-sync.sh`) was failing silently every 60 seconds under both its LaunchAgent and a duplicate crontab entry. The script was swallowing errors via `2>/dev/null || return 0`, exiting 0, and `launchctl list` reported "exit code 0" — so externally it looked fine. But the script hadn't actually pushed Mac changes to the VPS bare repo since **2026-04-07 23:38:11** (last "nous ok" log line), giving a 12+ hour window where vault writes accumulated on Mac without reaching VPS. During Madi's 2026-04-08 session-close audit (request: *"Audit everything. Make sure everything is saved in Obsidian... no hallucination"*), the divergence was caught: Mac HEAD `0918b33`, VPS HEAD 19 auto-sync commits ahead, Mac working tree 218 uncommitted files.

## Root cause stack (3 layers)

### Layer 1 — macOS TCC blocks `/bin/bash` from reading `~/Documents/` when launched by launchd

Under macOS's Transparency, Consent and Control framework, a process needs **Full Disk Access (FDA)** to read files in user-protected directories (`~/Documents/`, `~/Desktop/`, `~/Downloads/`, iCloud, etc.). FDA is keyed by the **bundle identifier + code signature** of the process that's running.

- When you launch `/bin/bash` from **Terminal.app** or **Claude Code**, the resulting bash process INHERITS those parent apps' TCC permissions. Terminal has FDA on most developer machines, so the bash has read access to `~/Documents/`.
- When `launchd` launches `/bin/bash` from a LaunchAgent or `cron` fires it from a crontab entry, the bash is a CHILD of launchd/cron — which do NOT have FDA by default. The bash inherits no TCC permission on `~/Documents/`.
- The visible symptom: every git call from the script fails with `fatal: Unable to read current working directory: Operation not permitted` (git's `getcwd()` returns EPERM).
- Subtle detail: bash's `[ -r "$file" ]` test uses the `access()` syscall which is **NOT** TCC-gated — it returns "readable" even when the actual `read()` call would be blocked. This means naive bash probes like `if [ -r "$vault/.git/HEAD" ]` will wrongly report the file as readable, and the real failure doesn't surface until git tries to `open()` it.

### Layer 2 — script swallowed errors silently

The original script pattern was:

```bash
git fetch vps main -q 2>/dev/null || return 0
```

Three compounding bad habits in one line:
1. **`-q` quiet mode** — hides git's normal status messages
2. **`2>/dev/null`** — discards git's error messages entirely
3. **`|| return 0`** — on any non-zero exit, return success from the function

Result: the script reported "success" via exit code 0 for every run, for 12+ hours, while doing nothing. `launchctl list` dutifully reported `exit code 0` for the LaunchAgent. The script's own success log (`/tmp/obsidian-sync.log`) simply had no new entries — but nothing in the LaunchAgent ecosystem said "hey, this should be logging success lines and isn't."

This is the same anti-pattern as [[LESSON-064-silent-ack-success-path]] (telegram_poll.py's `send_ack` had a silent success path). **You cannot audit what you cannot log.**

### Layer 3 — duplicate sync mechanisms racing

The session-close investigation also discovered that BOTH a LaunchAgent (`com.nous.obsidian-sync`) AND a Mac `crontab` entry (`* * * * * /bin/bash /Users/madia/.local/bin/nous-obsidian-sync.sh`) were running the same script every minute. They raced each other. Both failed the same TCC check. Both accumulated the same "Unable to read cwd" spam in `/tmp/obsidian-sync-stderr.log` and `/tmp/obsidian-sync-cron.log`. Removing one doesn't help (they both fail); having both is unnecessary complexity.

Root cause of Layer 3: the LaunchAgent was the original mechanism; someone (possibly me in an earlier session) added the crontab entry as a backup, forgot the LaunchAgent existed, and never removed it.

## Prevention rules (durable)

### For any sync / background automation script

1. **Never use `2>/dev/null || return 0` on the main operation.** If a step can silently fail, you need to know. Redirect stderr to a log file, not `/dev/null`:
   ```bash
   git fetch vps main -q 2>>"$LOG"
   ```
2. **Log a start AND finish line every run**, even on failure:
   ```bash
   log_line "run started"
   # ... work ...
   log_line "run finished (nous=$STATUS)"
   ```
   If the log has no start line for the last hour, the script hasn't been running. If it has start but no finish, it crashed mid-run.

3. **Actually read a byte** when checking file access. Don't rely on `[ -r $file ]` (uses `access()` syscall, not TCC-gated). Use:
   ```bash
   if ! head -c 1 "$file" >/dev/null 2>&1; then
       echo "TCC-BLOCK or read failure"
   fi
   ```

4. **Rate-limit failure logs** so they don't flood disk. One actionable line per 10 minutes is plenty. Use a marker file with an epoch timestamp:
   ```bash
   NOW=$(date +%s); LAST=$(cat /tmp/last-error.epoch 2>/dev/null || echo 0)
   if [ $((NOW - LAST)) -ge 600 ]; then
       log_line "error: ..."
       echo "$NOW" > /tmp/last-error.epoch
   fi
   ```

5. **One sync mechanism per task.** If you're adding a new cron/LaunchAgent, first check whether an existing one is already doing the job. Two mechanisms for the same task cause races, duplicate failures, and confusion about which one is "authoritative."

### For macOS LaunchAgent / cron scripts specifically

6. **Assume the LaunchAgent's bash does NOT have TCC access to user-protected directories.** If your script needs to touch `~/Documents/`, `~/Desktop/`, `~/Downloads/`, or iCloud paths, plan for one of these:
   - Grant `/bin/bash` Full Disk Access explicitly (requires UI action by the user)
   - Run the sync from a different mechanism that inherits TCC (e.g., a script fired by Terminal.app, tmux session, or Claude Code)
   - Move the target directory OUT of TCC-protected locations (awkward — breaks Obsidian Sync + iCloud Drive)
   - Use a sync mechanism that doesn't need to read the files itself (e.g., a cloud-based sync service that runs in-process inside an already-TCC-blessed app)

7. **Add a TCC-failure detector at the top of every script that touches protected paths.** The goal is to turn an opaque 12-hour silent failure into an actionable "grant FDA to /bin/bash" line on the first run.

## The fix applied in this session (2026-04-08)

### Code changes

**Script** (`/Users/madia/.local/bin/nous-obsidian-sync.sh`):
1. Removed all `2>/dev/null || return 0` error swallowing. All git stderr goes to `/tmp/obsidian-sync.log` now.
2. Added a TCC-failure probe at the top using `head -c 1` (real read, not just `access()`):
   ```bash
   if ! head -c 1 "$NOUS_VAULT/.git/HEAD" >/dev/null 2>&1; then
       # 10-minute rate-limited log line with actionable fix instructions
       ...
       exit 0
   fi
   ```
3. Uses `git -C "$vault"` for every git call (no cwd dependency).
4. Writes start/finish log lines every run.
5. Removed Brain vault logic (vault was deleted 2026-04-07).

**Plist** (`~/Library/LaunchAgents/com.nous.obsidian-sync.plist`):
1. Added `WorkingDirectory=/tmp` (launchd starts bash with cwd=/tmp rather than inheriting a TCC-blocked path)
2. Added explicit `EnvironmentVariables` (PATH, HOME, PWD)

**Crontab**: removed the duplicate `* * * * * /bin/bash /Users/madia/.local/bin/nous-obsidian-sync.sh` entry. Backup saved at `/tmp/crontab.backup`.

### State reconciliation

Mac had 218 uncommitted files + 1 local commit (`41280f3` from an earlier partial sync run) + a zombie `.git/MERGE_HEAD` from an aborted merge. VPS was 20 commits ahead of the merge base. Reconciliation:

1. `git merge --abort; rm -f .git/MERGE_HEAD .git/MERGE_MSG .git/MERGE_MODE` — clean up zombie state
2. `git commit -m "progress: 4th Asyl update..."` — commit the fresh Asyl edit
3. `git merge vps/main` — merge VPS's 20 commits into Mac
4. Resolve `tools/backfill_frontmatter.py` add/add conflict (content identical, only file mode differed; accepted local 755)
5. `git push vps main` — push Mac's state to VPS bare repo
6. Trigger `wiki_to_bare.sh` on VPS — VPS working tree catches up to Mac's HEAD (`93e0573`)

Final state: **Mac HEAD == VPS HEAD == `93e0573 merge: reconcile Mac session work with VPS auto-sync commits (backfill_frontmatter.py mode=755, content identical)`**.

## Workaround until Madi grants FDA

While FDA is NOT yet granted to `/bin/bash`:

- The LaunchAgent will run every 60 seconds and log a single `TCC-BLOCK: ... grant Full Disk Access to /bin/bash ...` line every 10 minutes. It will NOT push anything. This is intentional — loud failure beats silent failure.
- **Claude Code sessions MUST run the sync manually** before ending each turn, via:
  ```bash
  bash /Users/madia/.local/bin/nous-obsidian-sync.sh
  ```
  This works because Claude Code's bash inherits TCC from Claude Code.app (which has FDA).
- **Madi's Obsidian app writes** are NOT synced automatically until FDA is granted. Madi either needs to:
  - Open Terminal and run `bash /Users/madia/.local/bin/nous-obsidian-sync.sh` manually after an Obsidian session, OR
  - Open a Claude Code session, which can sync as part of its normal workflow, OR
  - **Grant FDA to /bin/bash** (permanent fix — see next section)

## Permanent fix — how to grant Full Disk Access to `/bin/bash`

Madi's action (once, ~60 seconds):

1. Open **System Settings** → **Privacy & Security** → **Full Disk Access**
2. Click the **+** button (may require authentication with Touch ID or password)
3. Press **Cmd+Shift+G** in the file picker → type `/bin/bash` → Enter
4. Select `bash` → **Open**
5. Toggle the switch next to `bash` to enable
6. Back in Terminal, restart the LaunchAgent:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.nous.obsidian-sync.plist
   launchctl load ~/Library/LaunchAgents/com.nous.obsidian-sync.plist
   launchctl kickstart -k gui/$(id -u)/com.nous.obsidian-sync
   ```
7. Verify via log:
   ```bash
   tail -5 /tmp/obsidian-sync.log
   # Expected: "nous OK: <hash> <msg>" entries, not TCC-BLOCK
   ```

**Why this is safe:** `/bin/bash` is a system binary shipped with macOS. Granting it FDA doesn't expose any new privilege to an application — it just lets scripts run from launchd/cron access the same files Madi can normally access through Terminal. No third-party code gets elevated.

**Why this is necessary:** there's no way to grant TCC to a specific script or LaunchAgent directly on macOS. You can only grant TCC to executables. The LaunchAgent spawns `/bin/bash` which runs the script, so `/bin/bash` is what needs the grant.

## What's at risk if this breaks again (or FDA is never granted)

1. **Data loss window:** Mac vault writes between two `bash /path/to/script.sh` runs from a TCC-enabled shell are NOT on VPS. If Mac disk fails in that window, those writes are gone. The window is typically minutes (I run the sync at end of each turn) but could grow.
2. **Merge conflicts grow:** the longer Mac and VPS drift, the harder the merge. Today's reconcile took ~15 minutes of careful git work. A 2-day drift could take an hour.
3. **Silent failure risk returns if someone edits the script to re-add `2>/dev/null`.** The fixed script logs everything. If anyone removes the logging, the clock starts over.
4. **Madi's Obsidian writes (from his Mac app, not via Claude Code) don't reach VPS automatically.** If Madi edits a note in Obsidian and closes the app, that note only lives on his Mac until the next manual sync.

## Test plan for future modifications

Before declaring any sync change "working":

1. **Kill + reload the LaunchAgent:**
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.nous.obsidian-sync.plist
   launchctl load ~/Library/LaunchAgents/com.nous.obsidian-sync.plist
   launchctl kickstart -k gui/$(id -u)/com.nous.obsidian-sync
   ```
2. **Wait 5 seconds, then check the log:**
   ```bash
   tail -10 /tmp/obsidian-sync.log
   ```
3. **Verify a `nous OK: <commit>` line exists for the current time** (not a TCC-BLOCK line).
4. **Confirm Mac↔VPS HEAD convergence:**
   ```bash
   cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"
   echo "Mac: $(git rev-parse HEAD)"
   git fetch vps main -q
   echo "VPS: $(git rev-parse vps/main)"
   ```
   Both must match.
5. **Make a trivial commit on Mac, wait 60s, confirm it's on VPS:**
   ```bash
   echo "test $(date)" >> /tmp/sync-test
   cp /tmp/sync-test "/Users/madia/Documents/Projects/Nous AGaaS/Nous/sync-test.md"
   sleep 90
   ssh root@65.108.215.200 'ls /root/nous-agaas/wiki/sync-test.md'
   # Then clean up: rm the file and commit the deletion
   ```

## See also
- [[sync-repair-2026-04-08]] — the full investigation + fix session log
- [[LAW-005-obsidian-master]] — the enforcement law this sync protects
- [[AUDIT-024-physical-enforcement-of-law5]] — physical symlink enforcement (memory side, independent of git sync)
- [[AUDIT-027-god-level-alignment-vs-trefethen-mempalace-brain]] — the audit session this fix happened inside
- [[LESSON-064-silent-ack-success-path]] — same "silent success" anti-pattern in telegram_poll.py
- [[session-close-2026-04-08-audit]] — session digest
