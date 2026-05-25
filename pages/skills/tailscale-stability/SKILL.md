---
tier: 2
name: tailscale-stability
description: "Keep Tailscale on Mac reliable. Diagnose and permanently eliminate the 'every few hours, I have to re-auth' failure mode. Covers dual-install detection, client/daemon version alignment, key-expiry lockout, and auto-heal."
type: skill
version: 1.2.0
owner: infra
created: 2026-04-17
tags: [skill, tailscale, networking, macos, infrastructure, stability]
when_to_invoke:
  - "Tailscale SSH to Air fails and Mac prompts for re-auth"
  - "`tailscale status` shows 'Logged out' but you did not log out"
  - "`tailscale status` prints a client/daemon version mismatch warning"
  - "`ssh air` hangs where it used to work — before blaming sshd/PAM, check Tailscale"
  - "Any task that previously worked via Tailnet but today does not"
title: "tailscale-stability v1.2.0"
---

# tailscale-stability v1.2.0

## Scope

This skill covers **the Mac client**, which is the chronic failure point. Linux VPS Tailscale (Debian package + systemd) has been rock-solid — do not apply this skill to the VPS without a separate audit.

Related but distinct skills:
- `skills/air-ssh-access/SKILL.md` — how to reach Air (assumes Tailscale works)
- `skills/infrastructure/SKILL.md` — launchd, OpenClaw, LiteLLM

## Root causes (there are TWO, stacked)

Confirmed session 36, 2026-04-17.

**Primary root cause (the "every few hours" pattern): OAuth refresh-token churn.** Tailscale.app on Mac joins the tailnet via **user-OAuth** (browser redirect to Google / GitHub / SSO). That login grants the device a short-lived access token + a refresh token. Every few hours the refresh flow runs; if the underlying OAuth provider session is stale, revoked, or rate-limited, the device transitions to `state: NeedsLogin` and CLI reports "Logged out" — while `tailscale debug prefs` still shows `"LoggedOut": false` (user didn't intentionally logout). Clicking the displayed login URL re-establishes the OAuth session for another few hours. This is why the problem recurs cyclically on Mac and **never on the Debian VPS** — the VPS joined with a reusable, non-expiring preauth key that doesn't require OAuth refresh.

**Secondary root cause (amplifier): dual Tailscale install.** Two concurrent `tailscaled` daemons own overlapping responsibilities, causing state-desync and delaying the CLI's awareness of recovery after an OAuth hiccup. The dual-install doesn't cause the logout — it makes recovery from a logout slower and noisier, and introduces version-mismatch warnings that mask the real signal.

**Symptom pattern:**
```
$ tailscale status
Warning: client version "1.94.2-t..." != tailscaled server version "1.96.2-t..."
Logged out.
Log in at: https://login.tailscale.com/a/<hash>
```
yet simultaneously the daemon's own `prefs` reports:
```
$ tailscale debug prefs
"WantRunning": true,
"LoggedOut": false,
```
Most authoritative read of all:
```
$ tailscale ip
no current Tailscale IPs; state: NeedsLogin
```
**`state: NeedsLogin` while `LoggedOut: false`** is the fingerprint of OAuth-refresh failure. If you see both together, the primary root cause is confirmed and you need a preauth key (see Fix 3), not just the dual-install cleanup.

**The two installs:**

| Install | CLI | Daemon | Controlled by |
|---|---|---|---|
| Tailscale.app (Mac App Store) | *(not installed as `/usr/local/bin/tailscale` by default)* | `/Applications/Tailscale.app/Contents/PlugIns/IPNExtension.appex/Contents/MacOS/IPNExtension` (runs as `madia`) | Mac App auto-update (version "current") |
| Homebrew `tailscale` formula | `/opt/homebrew/bin/tailscale` (the one `$PATH` finds) | `/opt/homebrew/opt/tailscale/bin/tailscaled` (runs as `root` via `/Library/LaunchDaemons/homebrew.mxcl.tailscale.plist`) | `brew upgrade` (version "stale-by-default") |

The Mac App's IPNExtension wins the race for the TUN network interface and for `/var/run/tailscaled.socket`, so it is **the actual tailscaled**. brew's tailscaled sits in the background uselessly, its logs fill with socket-busy errors. The brew CLI at `/opt/homebrew/bin/tailscale` is what you invoke — it talks to whichever daemon socket is listening (the App's). Since the brew CLI is pinned at an older version than the App's daemon, IPN state reads get partial desyncs, and periodically the CLI reports "Logged out" even when the App is actively connected. Clicking the displayed auth URL re-primes the CLI's state and things work for a few hours until the next drift.

**Why "every few hours" and not "constantly":** IPN state cache TTL and DERP re-handshake intervals line up roughly with the window.

## Permanent fix (four steps)

### Fix 1 — Unload the brew daemon (reversible, no reboot)
```bash
# If root-level /Library/LaunchDaemons plist exists:
sudo launchctl unload /Library/LaunchDaemons/homebrew.mxcl.tailscale.plist 2>/dev/null
# And/or user-level:
launchctl unload ~/Library/LaunchAgents/homebrew.mxcl.tailscale.plist 2>/dev/null
# Confirm only Tailscale.app daemon remains:
ps aux | grep -iE 'tailscaled|IPNExtension' | grep -v grep
```
Expected: only the `IPNExtension` process remains. No `/opt/homebrew/.../tailscaled`.

### Fix 2 — Align CLI version with daemon
Option A (easiest): `brew upgrade tailscale` — pulls CLI 1.96.4+, matches daemon 1.96.2.
Option B (clean): `brew uninstall tailscale` + install the App's CLI via the menu-bar **Preferences → Install CLI** action. This symlinks `/usr/local/bin/tailscale` to the App-bundled CLI and makes the install truly single-source.

Option B is the gold-standard fix; Option A is acceptable and lower-risk. Run `tailscale status` immediately after — expect no version-mismatch warning.

### Fix 3 — Switch Mac from OAuth to preauth key (THE PERMANENT FIX)
This is the one that stops "every few hours" for good. Without this, Fix 1 + Fix 2 buy you a cleaner CLI experience but the OAuth refresh will still fail periodically.

One-time Madi-gated steps:
1. Open <https://login.tailscale.com/admin/settings/keys>
2. **Generate auth key** with these settings:
   - Reusable: ✅
   - Ephemeral: ❌
   - Pre-approved: ✅ (if device-approval is on in your tailnet)
   - Tags: `tag:madi-devices` (or whatever your Mac device tag is)
   - Expiration: **No expiration** (or 90 days if your tailnet policy forbids non-expiring keys — then add a calendar reminder to rotate)
3. Copy the `tskey-auth-...` value.
4. Store in macOS Keychain (do NOT write to disk):
   ```bash
   security add-generic-password -a "$USER" -s tailscale-authkey -w "tskey-auth-PASTE_HERE"
   ```
5. Re-auth the Mac with the preauth key:
   ```bash
   tailscale logout
   tailscale up --authkey="$(security find-generic-password -w -s tailscale-authkey)" --ssh
   ```
6. Also (belt-and-suspenders): <https://login.tailscale.com/admin/machines> → Mac device → "…" → **Disable key expiry**.

After this, the device authenticates without OAuth, OAuth refresh is no longer in the failure path, and the "every few hours" pattern stops. The Linux VPS has used this pattern since day one and has zero re-auth incidents on record.

### Fix 4 — Auto-heal launchd agent (optional hardening)
Detect "logged out" state and silently re-up using a reusable preauth key stored in Keychain.

```bash
# One-time: generate reusable, non-expiring preauth key at
#   https://login.tailscale.com/admin/settings/keys  (check Reusable + Pre-approved, uncheck Ephemeral)
security add-generic-password -a "$USER" -s tailscale-authkey -w "<PASTE_KEY>"

# Heal script — $HOME/bin/tailscale-heal.sh
#!/bin/zsh
if tailscale status 2>&1 | grep -q "Logged out"; then
    KEY=$(security find-generic-password -w -s tailscale-authkey 2>/dev/null)
    [[ -n "$KEY" ]] && /usr/local/bin/tailscale up --authkey="$KEY" --ssh --reset
fi

# launchd agent — ~/Library/LaunchAgents/com.nous.tailscale-heal.plist
# Runs every 300s. See Appendix A for full plist.
```

Only apply Fix 4 **after** Fix 1 + 2 hold for 24h. If Fix 1+2 fully eliminate the problem, Fix 4 is belt-and-suspenders.

## Current rules (session 36 and later)

- **Never install Tailscale via both brew and Tailscale.app on the same Mac.** Pick one. Tailscale.app is preferred on macOS because it handles the System Extension + Network Extension approvals that brew cannot replicate cleanly.
- **Before debugging "SSH to Air is broken", always first check `tailscale status` on the Mac for a version-mismatch warning.** If present, go to Fix 1+2 before touching sshd or air-ssh-access AP-1.
- **Never rely on Tailscale SSH device-verification for unattended flows.** `ssh -o PreferredAuthentications=publickey` + traditional SSH keys bypasses the "Tailscale SSH requires an additional check" browser gate. Use that for Claude Code → Air automation paths.
- **Never run `tailscale up` with no args in an unattended session.** It will prompt. Always use `--authkey=$(security find-generic-password -w -s tailscale-authkey)` in scripts.
- **If you touch Mac Tailscale, sync this skill — and bump the version.** This is rule 6 (CLAUDE.md RULE ZERO): no LESSON file, update SKILL.md + gbrain timeline.

## Anti-patterns

### AP-1: Clicking the "Log in at https://login.tailscale.com/a/..." URL and calling it a fix
The auth URL re-primes the CLI cache but does **nothing to fix the dual-install state-desync**. Inside a few hours, the same CLI will show "Logged out" again. This is the single most common wasted-effort pattern — sessions 15, 16, 35, and the first attempt at 36 all did this. **Go to Fix 1 instead.** The auth URL is OK as a stop-gap only if you need tailnet access RIGHT NOW and can't do Fix 1 in this session.

### AP-2: Treating `tailscale status` output as ground truth
When a version-mismatch warning is printed, ALL state the CLI reports is suspect. `LoggedOut: false` from `tailscale debug prefs` is the authoritative source (it reads straight from the daemon), not `tailscale status`. Cross-check both before deciding anything.

### AP-3: Debugging Air SSH before confirming Mac Tailscale is healthy
If `ssh air` hangs or returns "Permission denied", the first hypothesis must be **Mac Tailscale is desynced**, not sshd/PAM/keys on Air. LESSON-089 already warns against deep sshd debugging — extend that to: check Mac Tailscale first, air-ssh-access second.

### AP-4: Treating Tailscale SSH's "additional check" as a Mac-side problem
"Tailscale SSH requires an additional check. To authenticate, visit: ..." is emitted by the **target host's** Tailscale SSH, not by the Mac. It is a feature of Tailscale SSH device-verification and is orthogonal to the dual-install issue on Mac. The fix is either to disable device-verification on Air (admin → ACLs) OR to use traditional SSH key auth with `-o PreferredAuthentications=publickey` for unattended flows. Do not conflate this with the dual-install bug.

### AP-5: Treating "brew upgrade tailscale" as a complete fix
It aligns versions (step 2) but does not stop the brew tailscaled from fighting the App's daemon (step 1). Both steps are required. Fix 1 without Fix 2 also partial — CLI still reports a mismatch warning until upgraded.

### AP-6: Treating a handed-off `login.tailscale.com/a/<code>` URL as a share invite (v1.2.0, 2026-04-20, session 52)

**Pattern.** You receive a new host from another party (Asyl, Alex, a vendor). They hand over host credentials PLUS a URL like `https://login.tailscale.com/a/1a8332010179c5`. You assume the URL is a "share invite" — click it to join the device to your tailnet. It returns `Error 400: This authentication link could not be located. It may have expired`. You conclude the share is broken.

**Root cause.** Confusion between two distinct URL classes in Tailscale:

- **Device-auth URL** (`login.tailscale.com/a/<code>`): One-shot token produced by `sudo tailscale up` on the target device. Used EXACTLY ONCE to bind the device to a specific tailnet account. **Consumed** the moment any user completes auth against it. If the provisioner already ran `tailscale up` successfully (i.e. the device has a Tailscale IP assigned — which you can verify via `tailscale status` on the device), this URL is already spent. Clicking it later returns Error 400.
- **User-or-device share invite** (email, not URL hand-off): Sent via Tailscale admin → `⋯` → `Share` → recipient's email. Persistent, re-clickable, scoped, revocable.

**Fix — when receiving a host from another owner:**

1. If the device already has a Tailscale IPv4 (check `tailscale status` on the device, or just confirm the handoff doc says "Tailscale IP: 100.x.y.z"), treat the accompanying `login.tailscale.com/a/<code>` URL as ALREADY CONSUMED. Do not click.
2. Ask the provisioner to choose one:
   - **Option A (preferred — shared, keeps their ownership):** Tailscale admin → Machines → find the device → `⋯` → `Share` → your email. You accept the email invite; device appears in your tailnet's peer list under the "Shared" section.
   - **Option B (transfer ownership):** On the device: `sudo tailscale logout && sudo tailscale up`. Produces a fresh one-shot URL. Provisioner gives YOU that URL; you click it while logged into your own Tailscale account; device joins your tailnet.
3. If you already clicked and got Error 400, no damage done — just confirms the URL was consumed. Proceed with Option A or B.

**Detector (session 52+ candidate, not yet wired):** Extend `tools/soao.sh` point 2 with a provisioning-URL freshness gate. During host-onboarding tasks, any `login.tailscale.com/a/<N>` URL in the session transcript or a handoff page that's >10 minutes old, OR paired with a host that already has a Tailscale IP assigned, should be flagged as CONSUMED.

**Evidence — session 52, 2026-04-20:** Asyl handed Madi the new `nous-gpu` box with `Tailscale IP: 100.70.222.21/32` (so Asyl had already authenticated the device) PLUS the URL `https://login.tailscale.com/a/1a8332010179c5`. Madi attempted to click the URL; Tailscale returned `Error 400`. Root cause correctly diagnosed: URL was the GPU's own one-shot device-auth token, consumed at `tailscale up` by Asyl, not a share invite. Corrected path: Asyl will share `nous-gpu` via Tailscale admin → Machines → Share. See [[nous-gpu]] §BLOCKED Options A/B/C. No new LESSON file (RULE ZERO).

**Cross-ref:** AP-1 (different URL usage — that's the Mac's OWN auth URL during dual-install desync; this AP is about URLs from OTHER owners during host handoff). No conflict.

## Diagnostic one-liner (save to memory)

Paste into any Mac terminal. Green = healthy, red = dual-install.
```bash
python3 -c '
import subprocess as s
def grep(cmd, pat):
    r=s.run(cmd,shell=True,capture_output=True,text=True)
    return pat in (r.stdout+r.stderr)
mismatch = grep("tailscale status 2>&1", "client version")
dual = grep("ps auxc | grep -v grep", "tailscaled") and grep("ps auxc | grep -v grep", "IPNExtension")
brew_plist = grep("ls /Library/LaunchDaemons/ ~/Library/LaunchAgents/ 2>/dev/null", "homebrew.mxcl.tailscale")
print(f"version-mismatch: {mismatch}")
print(f"dual-daemon:      {dual}")
print(f"brew-plist loaded: {brew_plist}")
print("RED — run Fix 1+2 from tailscale-stability skill" if (mismatch or (dual and brew_plist)) else "GREEN")
'
```

## Appendix A — auto-heal launchd plist (reference)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.nous.tailscale-heal</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-c</string>
    <string>/Users/madia/bin/tailscale-heal.sh &gt;&gt; /Users/madia/Library/Logs/tailscale-heal.log 2&gt;&amp;1</string>
  </array>
  <key>StartInterval</key><integer>300</integer>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
```

## Timeline

- **2026-04-17** | v1.0.0 — skill created, session 36. Dual-install identified (brew tailscale 1.94.2 + Tailscale.app 1.96.2 both running tailscaled). Partial fix applied: user-level LaunchAgent unloaded, brew CLI upgraded 1.94.2 → 1.96.4. Registered in `_gbrain/RESOLVER.md`.
- **2026-04-17** | v1.1.0 — root cause refined during same session. Dual-install is the **amplifier**, not the primary cause. Primary cause: Mac App uses OAuth user-login, which requires a refresh-token cycle every few hours; when the underlying OAuth session is stale, device falls to `state: NeedsLogin` while `LoggedOut: false` (the fingerprint). Fix 3 rewritten: permanent cure is switching Mac from OAuth to a reusable preauth key, matching the Linux VPS pattern that has never logged out. Fix 3 is Madi-gated (admin console + Keychain store).
- **2026-04-20** | v1.2.0 — Session 52 absorbed AP-6 (handed-off `login.tailscale.com/a/<code>` URL ≠ share invite). Trigger: Asyl provisioned `nous-gpu` (RTX 5070, [[nous-gpu]]); handoff included URL `https://login.tailscale.com/a/1a8332010179c5`. Madi clicked, got `Error 400: authentication link could not be located / may have expired`. Root cause: URL was the GPU's one-shot device-auth URL consumed by Asyl at `tailscale up`, not a share invite. Fix path (Option A): Asyl shares `nous-gpu` via Tailscale admin → Machines → Share → Madi's email. Doctrine adds: when receiving a host with existing Tailscale IP, treat the accompanying `login.tailscale.com/a/<code>` URL as ALREADY CONSUMED. Detector candidate: `tools/soao.sh` provisioning-URL freshness gate (session 53+). RULE ZERO upheld (0 new LESSON). Cross-ref: `session-operating-contract` Rule 6 (failure → skill) applied in motion — root cause captured + codified BEFORE Asyl's next response.
