---
id: SPEC-SECRETS-MANIFEST-V1-2026-04-17
type: spec
title: "Secrets Manifest v1 — Mac-primary secrets architecture for Nous AGaaS (Apple Keychain SoT, iCloud-sync opt-in, pipe-never-variable deploy)"
date: 2026-04-17
status: reviewed
last_updated: 2026-04-17
owner: claude-code-mac (Opus 4.7 1M) + Madi Ayazbay
tags: [spec, secrets, keychain, icloud, apk-status-bot, mac-primary, session-42, rule-zero]
source_count: 4
related:
  - SPEC-APK-STATUS-BOT-A-2026-04-17
  - HANDOFF-AUTO-2026-04-17-session-42-atomic-audit
  - HANDOFF-AUTO-2026-04-17-session-38-spec-a-apk-bot
  - audit
---

# Secrets Manifest v1 — Mac-primary Secrets Architecture

**Scope:** Minimal secrets storage + deploy pattern that unblocks APK_BOT_TOKEN today, captures doctrine for future secrets, and aligns with Madi's "Mac Pro primary, then Air, then VPS, then GitHub for safety" vision. Does NOT solve the broader gbrain/QMD Mac-primary migration (that is Spec B from session 38, still a separate brainstorm).

**Author context:** Session 42 Madi directive — "bulletproof, future-proof, everything will work, nothing will break, everything will be safe." Plus hard preference for Apple-native tools (Apple Passwords / iCloud Keychain) over paid external services (1Password etc.).

## 0. Goal + non-goals

### Goal

One tool, one pattern, one audit story for storing the small number of secrets Nous AGaaS needs on VPS/Air machines. APK_BOT_TOKEN today; webhook tokens, Jira basic-auth, and others later — all under the same flow.

### Non-goals (explicitly deferred)

- Not a full HSM / Hashicorp Vault deployment (overkill for ≤20 secrets).
- Not a gbrain/QMD Mac-primary migration (that is Spec B).
- Not a general secrets-sharing system between Madi and humans (this is for services).
- Not camera credential rotation (flagged in `AGAAS-ARCHITECTURE-DECISION-v2-GOLDEN` §10 — follow-up work, uses the same pattern once ready).

## 1. Locked decisions

| # | Decision | Value | Rationale |
|---|---|---|---|
| 1 | Source of truth | macOS Keychain (`login.keychain-db`) on Mac Pro | Mac-primary per Madi; native; free; encrypted at rest by macOS login password. |
| 2 | iCloud sync | Opt-in per secret via `kSecAttrSynchronizable: true` | Madi chose "yes" session 42; widens attack surface to Apple devices but adds disaster-recovery path. Each secret opts in via manifest `icloud: yes/no`. |
| 3 | Helper language | Swift (Apple Security framework, via `/usr/bin/swift`) | Already installed with Command Line Tools. `security` CLI can't cleanly set `kSecAttrSynchronizable`. ~30-line helper. |
| 4 | Deploy mechanism | Bash script piping Keychain read → ssh → file write | Value never lands in a shell variable; atomic rename; 0600 mode before rename. |
| 5 | Manifest location | `pages/secrets-manifest.md` in vault (git-synced) | Non-secret doctrine — names, targets, rotation policy. Never values. |
| 6 | Script location | `tools/secrets-*.sh` / `tools/secrets-*.swift` in vault | Git-tracked shape/logic; Mac-only runtime guard. Reconnaissance concern considered and rejected (service names + paths already in Spec A). |
| 7 | Skill layer | New `pages/skills/secrets-management/SKILL.md` v1.0 | RULE ZERO compliant — doctrine lives in skill, evidence in gbrain timeline. Registered in `_gbrain/RESOLVER.md`. |
| 8 | Audit approach | File presence + `stat -f '%Sp'` == `-rw-------` + age < N days | MD5-of-value rejected (leaks info about short tokens). |
| 9 | Rotation outage | Named gap: ~30–60s when restarting single-service bots | Not fixed in v1; documented as known limitation. |
| 10 | First secret | APK_BOT_TOKEN + APK_BOT_ADMIN_DM_CHAT_ID + (later) APK_BOT_GROUP_CHAT_ID | APK_BOT_ADMIN_DM_CHAT_ID is not a secret; included for unit cohesion (it lives in the same .env file). |
| 11 | Distribution target for v1 | VPS only (`root@65.108.215.200:/opt/nous-agaas/.env`) | Air gets only non-sensitive mirror keys (APK_SELF_HEAL_BUDGET_USD etc.) — added in a future iteration when self-heal lands. |
| 12 | Recovery story | Mac Pro loss → Time Machine (primary) OR iCloud Keychain on iPad (secondary, only for `icloud: yes` items) OR re-issue from source (tertiary) | Explicit three-tier fallback; Madi picks Time Machine discipline in follow-up. |

## 2. Components

### 2.1 `tools/secrets-keychain-add.swift`

**Purpose:** Add a generic password to macOS Keychain with optional iCloud sync. Replaces raw `security add-generic-password` (which can't set the synchronizable attribute cleanly).

**Contract:**
```
./secrets-keychain-add.swift <service-name> [--icloud] [--update]
# reads value from stdin (never argv — argv is visible to other processes via ps)
# writes to login.keychain-db (iCloud keychain if --icloud, else local-only)
# exit 0 = success; exit 1 = not on Mac; exit 2 = keychain error; exit 3 = already exists (unless --update)
```

Implementation sketch (~30 lines):
```swift
import Foundation
import Security

// Read value from stdin (never argv)
let value = FileHandle.standardInput.readDataToEndOfFile()

let service = CommandLine.arguments[1]   // e.g., "nous-agaas/APK_BOT_TOKEN"
let icloud  = CommandLine.arguments.contains("--icloud")
let update  = CommandLine.arguments.contains("--update")

var query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrService as String: service,
    kSecAttrAccount as String: "nous",
    kSecValueData as String: value,
    kSecAttrSynchronizable as String: icloud
]

var status = SecItemAdd(query as CFDictionary, nil)
if status == errSecDuplicateItem && update {
    let searchQuery: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: service,
        kSecAttrSynchronizable as String: icloud
    ]
    status = SecItemUpdate(searchQuery as CFDictionary,
                           [kSecValueData as String: value] as CFDictionary)
}
exit(status == errSecSuccess ? 0 : 2)
```

**Security properties:**
- Value arrives via stdin — never on command line, never in environment.
- Single-process lifetime; value never persisted to a temp file.
- After `SecItemAdd`, value is in `login.keychain-db` (encrypted).

### 2.2 `tools/secrets-keychain-read.sh`

**Purpose:** Read a generic password from Keychain to stdout. Exists only to give the deploy script a stable interface.

**Contract:** `secrets-keychain-read.sh <short-name>` → stdout has the value (no trailing newline). Exit 0 = success; 1 = not on Mac; 2 = not found.

```bash
#!/bin/bash
set -euo pipefail
[[ "$(uname -s)" == "Darwin" ]] || { echo "FAIL: Mac-only" >&2; exit 1; }
exec security find-generic-password -s "nous-agaas/$1" -a nous -w
```

The `exec` is deliberate — no shell wrapper between `security` and stdout, so the value passes through in a single pipe.

### 2.3 `tools/secrets-deploy.sh`

**Purpose:** Deploy one service's secrets to one target machine. Pipe-never-variable discipline throughout.

**Contract:** `secrets-deploy.sh <service> <target>` where:
- `<service>` = manifest entry (e.g., `apk-status-bot`).
- `<target>` = `vps` or `air`.

**Behavior:**
1. Guard: Mac-only via `uname -s == Darwin`.
2. Parse manifest → list of (key, icloud, destination-path, non-secret-bool, constant-value-if-non-secret).
3. Pre-flight: for every secret entry, confirm Keychain has the item (without printing value): `security find-generic-password -s nous-agaas/X -a nous -g >/dev/null 2>&1`.
4. Resolve target:
   - `vps` → `root@65.108.215.200`, `/opt/nous-agaas/.env`, `deploy:deploy` ownership, `0600` mode.
   - `air` → `madia@air` (Tailscale), `~/nous-agaas/.env`, `madia:staff`, `0600`.
5. Stream env file over one pipe (ssh as root; `chown` runs server-side within the same remote command, before the atomic rename):
   ```bash
   {
     printf '# Generated %s by secrets-deploy.sh for service=%s target=%s\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$service" "$target"
     printf '# DO NOT EDIT BY HAND. Rotate via Keychain + re-deploy.\n\n'
     # For each non-secret constant: print literal key=value
     # For each secret: printf 'KEY='; tools/secrets-keychain-read.sh KEY; echo
   } | ssh -o StrictHostKeyChecking=yes -o BatchMode=yes -o ConnectTimeout=10 \
         root@"$target_host" \
         "umask 077 && cat > '$dest.new' && \
          chown '$owner' '$dest.new' && \
          chmod 600 '$dest.new' && \
          mv '$dest.new' '$dest'"
   ```
   `$owner` for VPS = `deploy:deploy`; for Air = `madia:staff`. The `chown` runs while the file has 0077 (umask) — no world-readable window. Order matters: chown before mv so the final `.env` is owned correctly from the moment it exists.
6. Post-deploy verify (without cat-ing value): `ssh target "stat -c '%a %U:%G %s' $dest"` (GNU stat on Linux VPS; on Air swap for `stat -f '%Lp %Su:%Sg %z'`) → expect `600 <owner> <size>` matching expected byte range.
7. EXIT trap: on failure, `ssh target "rm -f $dest.new"` to sweep staging.

**Flags:**
- `--dry-run` — print what WOULD happen; no ssh writes. Good for staging new services.
- `--audit` — runs only step 6 (post-deploy verify against existing `.env`); no read/write.

### 2.4 `pages/secrets-manifest.md`

**Purpose:** Non-secret registry. What secrets exist, where they go, rotation policy, last-added. No values.

**Format (markdown table):**
```
| key                     | description                           | service         | target(s) | type    | icloud | rotation   | added      | last_rotated |
|-------------------------|---------------------------------------|-----------------|-----------|---------|--------|------------|------------|--------------|
| APK_BOT_TOKEN           | BotFather token @NousAPKstatusbot     | apk-status-bot  | vps       | secret  | yes    | as-needed  | 2026-04-17 | 2026-04-17   |
| APK_BOT_ADMIN_DM_CHAT_ID| Madi Telegram chat_id for alerts      | apk-status-bot  | vps       | constant| n/a    | never      | 2026-04-17 | —            |
```

**target(s) semantics:** the column lists where the key SHOULD currently land. v1 deploys only to `vps`. When self-heal ships on Air (future iteration), `APK_BOT_ADMIN_DM_CHAT_ID` gets appended to the Air row so the next `secrets-deploy.sh apk-status-bot air` carries it over. Until then, Air is not in the row.

Constants (non-secrets) live in the manifest so the deploy script has a single source-of-truth for what goes in an `.env`. Values for constants are in the manifest (public — it's a chat ID, not a token). Values for secrets are NOT.

### 2.5 `pages/skills/secrets-management/SKILL.md` v1.0

New skill. Registered in `_gbrain/RESOLVER.md` for brain-aware invocation. Invariant: any future secret follows this skill's flow (anti-patterns AP-1..AP-7 are enforceable rules).

**AP-1:** Never assign a secret to a bash variable. Always pipe.
**AP-2:** Always stage `.env.new` in the same directory as `.env` (same filesystem). Atomic rename requires it.
**AP-3:** Never use `StrictHostKeyChecking=no` in deploy. Bail if host unknown.
**AP-4:** Single-service bot rotation has a ~30–60s outage. Name it when rotating; schedule for low-traffic windows.
**AP-5:** systemd units must use `EnvironmentFile=/opt/nous-agaas/.env`, not inline `Environment=`. The inline form leaks to journald on startup.
**AP-6:** Audit = file presence + 0600 perms + age. NEVER MD5-of-value (short tokens brute-forceable).
**AP-7:** Trap EXIT in deploy scripts to `rm -f` staging files on any failure path.

## 3. Data flow

```
┌──────────────────────────────────┐
│ Madi's terminal                  │
│ `!` prompt → pastes token once   │
└───────────┬──────────────────────┘
            │ stdin
            ▼
┌──────────────────────────────────┐
│ tools/secrets-keychain-add.swift │
│ SecItemAdd(kSecAttrSync: true)   │
└───────────┬──────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│ Mac Pro login.keychain-db        │ ─── iCloud Keychain ──→ iPad, iPhone
│ (encrypted, Apple iCloud sync)   │                         (read-only visibility)
└───────────┬──────────────────────┘
            │ (only on Mac Pro; secrets-keychain-read.sh)
            ▼
┌──────────────────────────────────┐
│ tools/secrets-deploy.sh          │
│ pipe-never-variable              │
│ ssh ... 'cat > .env.new; mv ...' │
└───────────┬──────────────────────┘
            │ ssh (StrictHostKeyChecking=yes)
            ▼
┌──────────────────────────────────┐
│ VPS /opt/nous-agaas/.env         │
│ 0600 deploy:deploy               │
└───────────┬──────────────────────┘
            │ systemd EnvironmentFile=
            ▼
┌──────────────────────────────────┐
│ apk-alert-sender.service         │
│ reads APK_BOT_TOKEN at start     │
└──────────────────────────────────┘
```

## 4. Error handling

| Failure | Behavior | Recovery |
|---|---|---|
| Keychain missing entry | Deploy script fails pre-flight; prints which key is missing; exits non-zero before any SSH attempt. | Run `secrets-keychain-add.swift <key> [--icloud]` (feeds stdin). |
| SSH host key unknown | Deploy script exits; prints `StrictHostKeyChecking` hint. | Run `ssh-keyscan <host> >> ~/.ssh/known_hosts` manually, verify fingerprint out-of-band. |
| SSH mid-stream drop | `.env.new` may exist on target (possibly empty or partial). EXIT trap runs `ssh target 'rm -f .env.new'`. Real `.env` untouched. | Re-run deploy. |
| `cat > .env.new` fails (disk full) | `mv` never happens. Real `.env` untouched. | Free disk space, re-run. |
| `mv` fails (permission denied) | `.env.new` stuck with 0600 but wrong owner. EXIT trap removes. | Check target user matches expected (`deploy:deploy`). |
| Swift helper not available | First-time-only: check at top of `secrets-keychain-add.swift` for `/usr/bin/swift`. Exit 1 with install hint. | `xcode-select --install` (already done on Madi's Mac). |
| Rotation mid-flight | Bot 401s for ~30–60s between old-token-revoke and systemd-restart-complete. | Schedule for low-traffic; or restart systemd BEFORE BotFather revoke (then new token is live before old one dies — but requires both tokens working briefly, BotFather doesn't allow). |

## 5. Testing

### 5.1 Unit (Mac-side)

- `tests/test_keychain_add.sh`: add → read → verify value matches; delete; verify absent. Uses a throwaway `nous-agaas/test-<timestamp>` name.
- `tests/test_deploy_dry_run.sh`: `--dry-run` against a manifest with 2 secrets; assert output has expected keys, no SSH attempts.
- `tests/test_deploy_trap.sh`: inject a fake SSH failure mid-stream; assert `.env.new` cleanup ran.

### 5.2 Integration (staging)

- Deploy APK_BOT_TOKEN to a staging path on VPS (`/tmp/env-test-<ts>/.env`). Verify: file exists, 0600, contents match what Keychain has (via local read).
- Repeat with `--audit` flag: verify idempotent check without read/write.

### 5.3 Recovery drill (quarterly)

- Simulate: delete local `login.keychain-db` entry for APK_BOT_TOKEN.
- Verify: iPad Keychain Access still shows it (if `icloud: yes`).
- Restore: run `secrets-keychain-add.swift --update` with value re-fetched from iPad.
- Verify: deploy still works end-to-end.

## 6. Install runbook (first-time setup, Mac Pro)

```bash
# 1. Create tools directory (likely already exists)
mkdir -p "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools"
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"

# 2. Write the three scripts (done by implementation plan)
# tools/secrets-keychain-add.swift
# tools/secrets-keychain-read.sh
# tools/secrets-deploy.sh
chmod +x tools/secrets-keychain-add.swift tools/secrets-keychain-read.sh tools/secrets-deploy.sh

# 3. Self-test (Madi)
echo "test-value-$(date +%s)" | tools/secrets-keychain-add.swift nous-agaas/TEST --icloud
tools/secrets-keychain-read.sh TEST   # should print test-value-<ts>
security delete-generic-password -s nous-agaas/TEST -a nous >/dev/null

# 4. Write manifest (pages/secrets-manifest.md) — initial row for APK_BOT_TOKEN
# 5. Write skill (pages/skills/secrets-management/SKILL.md) + register in RESOLVER
# 6. Commit — shape/logic in git; no secret values ever committed
git add tools/secrets-*.{sh,swift} pages/secrets-manifest.md pages/skills/secrets-management/
git commit -m "feat(secrets): v1 manifest + deploy + skill [risk] REQ-042-secrets-arch"
```

## 7. Uninstall / rollback

```bash
# Keychain entries (per secret):
security delete-generic-password -s nous-agaas/APK_BOT_TOKEN -a nous

# Target file (per target):
ssh root@VPS 'rm -f /opt/nous-agaas/.env'

# Scripts + manifest + skill: git revert the introducing commit.
```

## 8. Security properties summary

| Property | Satisfied? | How |
|---|---|---|
| Secrets never in git | ✅ | Manifest tracks names/targets only; deploy script reads Keychain, never values from files. |
| Secret never in bash variable | ✅ | `printf 'K='; keychain-read.sh K` → piped to ssh stdin. |
| Secret never on command line / argv | ✅ | Swift helper reads from stdin; `security find-generic-password -w` takes service via `-s`, not value. |
| `.env` always 0600 on target | ✅ | `chmod 600 .env.new` before `mv`. |
| Atomic swap | ✅ | Same-dir staging + POSIX rename. |
| Host-key enforcement | ✅ | `StrictHostKeyChecking=yes` — no first-connection bypass. |
| Failed-mid-deploy cleanup | ✅ | EXIT trap removes `.env.new`. |
| journald doesn't log token | ✅ (enforced by systemd spec, AP-5) | Units use `EnvironmentFile=`, not inline. |
| Mac Pro compromise = full compromise | ⚠ accepted limit | v1 trust model: Mac Pro IS the SoT. Mitigated by FileVault + login password + Time Machine. |
| iCloud device compromise | ⚠ accepted for opt-in secrets | Per-secret flag; high-risk secrets can set `icloud: no`. |
| Rotation has ~30–60s outage | ⚠ documented | AP-4; schedule for low-traffic windows. |
| Short token brute-force via audit MD5 | ✅ avoided | Audit uses file stat, not value hash. |

## 9. Open items

| # | Item | Owner | Blocking? |
|---|---|---|---|
| S1 | Time Machine discipline — Madi confirms Mac Pro has an enabled Time Machine target (external drive or NAS). If not, Mac-loss recovery for `icloud: no` secrets = re-issue only. | Madi | Non-blocking for v1 deploy; blocking for full "bulletproof" claim. |
| S2 | known_hosts pre-population — `ssh-keyscan 65.108.215.200 >> ~/.ssh/known_hosts` if not already done. | Madi / deploy script | First-deploy blocking. |
| S3 | VPS `deploy` user exists with home dir + SSH key. Spec A assumed it; verify before first deploy. | claude-code | First-deploy blocking. |
| S4 | APK_BOT_GROUP_CHAT_ID — filled after Madi creates group chat "Nous APK Status" (item 4 of Madi's list). Manifest row added then. | Madi | Blocks group-digest; not bot-startup. |
| S5 | JIRA_BASIC_AUTH — when Daniyar sends URL + creds, a second secret uses the same pattern. | Daniyar | Non-blocking for APK bot. |

## 10. Success criteria (acceptance gates)

1. `tools/secrets-keychain-add.swift` stores values from stdin with `kSecAttrSynchronizable` when `--icloud`. Verified via `security dump-keychain | grep -A2 APK_BOT_TOKEN | grep svce`.
2. `tools/secrets-keychain-read.sh APK_BOT_TOKEN` prints value (single execution, piped).
3. `tools/secrets-deploy.sh apk-status-bot vps` creates `/opt/nous-agaas/.env` on VPS with 0600, deploy:deploy, matching keys per manifest.
4. `--dry-run` prints plan without SSH.
5. `--audit` verifies existing `.env` without reading/writing.
6. Unit tests pass (`tests/test_keychain_add.sh`, `tests/test_deploy_dry_run.sh`, `tests/test_deploy_trap.sh`).
7. Manifest has one row for APK_BOT_TOKEN + one for APK_BOT_ADMIN_DM_CHAT_ID.
8. New `secrets-management` skill registered in `_gbrain/RESOLVER.md` and passes `audit` v1.9 AP-10 4-target MD5 parity.
9. No new LESSON files (RULE ZERO).
10. gbrain timeline entry on the new skill page.

## 11. Relation to Spec B (gbrain Mac-primary)

Spec B (session 38) covers gbrain + QMD migration to Mac Pro + 4-remote git origin + Tailscale preauth fix + broader self-heal. **Independent of this spec.** This spec establishes the SECRETS layer; Spec B establishes the DATA + SERVICE layer. Both converge on "Mac Pro primary" as the organizing principle.

When Spec B adds new services with secrets (e.g., Claude API key for Mac-hosted Hermes), they register under this manifest — zero change to the storage pattern.

## 12. Rule compliance

| Rule | Status |
|---|---|
| RULE ZERO (no new LESSON files) | ✅ new skill only; gbrain timeline for evidence |
| LAW-005 (Obsidian SoT) | ✅ manifest + skill + spec in vault; secrets NOT in vault |
| LAW-015 (root-cause evolution) | ✅ pattern derives from real review — 3 show-stoppers + 6 strong flaws named + fixed |
| LAW-016 (Satory frontend lock) | ✅ no frontend touch |
| Session 42 Madi directive ("bulletproof, future-proof") | ✅ explicit trust model, documented gaps, recovery tiers |
| Karpathy / Tan / Finn (skills compound) | ✅ secrets-management skill as primary artifact; not a LESSON |

## 13. See also

- [[SPEC-APK-STATUS-BOT-A-2026-04-17]] — Spec A §10.3 `.env` layout (this spec formalizes the how)
- [[HANDOFF-AUTO-2026-04-17-session-42-atomic-audit]] — session 42 context including parallel-agent deploy of apk-status-bot code
- [[HANDOFF-AUTO-2026-04-17-session-38-spec-a-apk-bot]] — session 38 design session (scope split)
- [[audit]] v1.9+ — AP-10 parity check will cover the new skill
- [[CLAUDE.md]] — RULE ZERO anchor
- [[AGAAS-ARCHITECTURE-DECISION-v2-GOLDEN]] §10 — camera-credential rotation is the next customer of this pattern
