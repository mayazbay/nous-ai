---
tier: 2
type: skill
name: credentials-discovery
id: SKILL-CREDENTIALS-DISCOVERY
version: 1.2.0
last_updated: 2026-05-07
status: active
description: "v1.2.0 — Doctrine for how agents find credentials in the Nous AGaaS substrate. NEVER paste-from-Madi when the substrate can serve. Manifest-first lookup: pages/secrets-manifest.md is the registry of every active key with host/path/service/rotation. Runtime tool: tools/credentials_discovery.py (built by Pane 2 Codex 2026-05-05). Pre-commit drift gate enforces manifest-actuals parity. v1.1 adds local-host collapse for Air/VPS watchdogs and redacted connector-config discovery. v1.2 closes cross-host transport drift: every logical host has a remote target, and tests declare their local fixture host explicitly so Air/Mac suites agree."
triggers:
  - any agent task that needs an API token, password, or secret
  - dispatching subagents that will call external services (Todoist/Notion/OpenAI/etc.)
  - debugging missing-credential errors before pasting from user
  - adding new third-party integration to the stack
  - rotating an existing key
tools: [Read, Bash, Grep, Glob]
mutating: false
related:
  - secrets-manifest
  - secrets-management
  - autonomous-build-manager
  - session-operating-contract
  - agent-quality
tags: [skill, credentials, secrets, substrate, root-cause-2026-05-05, tier-2, never-paste-from-user]
title: "credentials-discovery v1.2.0"
---

# credentials-discovery v1.2.0

## Purpose

Encode the discipline that **agents NEVER ask the user to paste a credential** when the substrate can serve. The substrate has 6 `.env` files across Mac/Air/VPS holding ~35 distinct credentials. Every credential is documented in `pages/secrets-manifest.md`. Every agent has Bash access to read those files and SSH access to remote hosts. There is no scenario where "I don't have the token" is a valid agent statement when the manifest exists.

## When this skill loads

- **Always** at session-start for Tier-2 (per `_gbrain/TIER-CONVENTION.md`).
- **Especially** when the dispatching prompt mentions a third-party service (Todoist, Notion, OpenAI, Anthropic, Telegram, Vercel, GitHub, etc.).
- **At trigger** the moment an agent thinks the words "I need the token" or "can you paste".

## Mandate

**Manifest first. Substrate second. User never.**

1. Need a credential? Read `pages/secrets-manifest.md` first. Find the row.
2. Run `python3 tools/credentials_discovery.py find <KEY>` for structured output of where it lives.
3. SSH or `source` the right `.env` file.
4. Use the credential. Never log or print its value in stdout/stderr.

If the credential is NOT in the manifest, that's a substrate gap — fix the gap (add the row, find the actual `.env` file holding it, commit the manifest update), then proceed. Do not bypass the manifest by asking the user.

## The 7 anti-patterns (forbidden)

### AP-1 — Asking the user to paste a credential

**Pattern:** Agent says "Drop your TODOIST_API_TOKEN in chat between backticks like this: \`abc123\`" or "Reply with the token to continue."

**Why forbidden:**
- Substrate already has the value. Manifest tells you where.
- Pasting in chat creates a leaked-token blast radius (transcript copies, browser history, accidental screenshots).
- User pastes wrong key, wrong project, expired key — agent doesn't know.
- Trains the user that the substrate is unreliable, when actually the agent didn't read it.

**Correct behavior:** Read manifest. Find row. SSH the host. Source the file. Done in 60 seconds without user involvement.

### AP-2 — Generating a fresh credential when one exists

**Pattern:** Agent generates a new password / API key / token because it didn't find an existing one.

**Why forbidden:**
- Existing credentials have downstream consumers (cron jobs, services, other agents). New ones break them silently.
- Manifest is the source of truth for what exists. If you didn't find it, you didn't look in all 6 `.env` files.

**Correct behavior:** Run `python3 tools/credentials_discovery.py audit` to see what's actually present. If a credential is genuinely needed and missing, propose it (Decision Rights protocol if it has rotation cost), don't unilaterally generate.

### AP-3 — Logging or printing credential values

**Pattern:** Agent runs `cat .env` or `echo $TOKEN` in a way that exposes the value to the transcript.

**Why forbidden:**
- Transcripts get pasted into other AI sessions, copied to other people, indexed by tools.
- Once a value is in the transcript, treat it as compromised → forced rotation cost.

**Correct behavior:** Use sed `s/=.*/=<REDACTED>/` when listing keys. Use `tools/credentials_discovery.py find <KEY>` (returns paths, never values). Source the env into a subshell that uses the value but doesn't echo it.

### AP-4 — Not updating the manifest when adding a new credential

**Pattern:** Agent edits an `.env` file to add a new key but doesn't update `pages/secrets-manifest.md`.

**Why forbidden:**
- Future agent (you, in a new session) won't find it via manifest lookup.
- Pre-commit drift gate will reject the commit anyway (Pane 2 Codex enforcement).
- Substrate-as-source-of-truth requires the manifest to track reality.

**Correct behavior:** Add the row to manifest BEFORE editing the `.env` file. Row is the contract. Stage both in same commit.

### AP-5 — Grepping secret-bearing app configs without redaction

**Pattern:** Agent runs broad `rg` over app config/session directories for connector setup and stdout includes full connector URLs or access keys.

**Why forbidden:**
- Connector URLs often embed bearer-style access keys in query params.
- Local transcripts are still transcripts; once a key is printed, rotation becomes a decision instead of a clean optional maintenance task.
- The right goal is "prove connector exists," not "show every byte of connector config."

**Correct behavior:** First use `rg -l` to identify candidate files. Then parse with a small redacting script that prints only booleans, host/project ids, tool names, or `***REDACTED***` placeholders. Never print the raw connector URL.

### AP-6 — SSHing to the same host from a host-local watchdog

**Pattern:** A launchd job running on Air audits `host=air` by shelling out to `ssh air cat /Users/madia/nous-agaas/.env`. In launchd context this can fail with `ssh_exit_255`, creating false credential drift. The same class can hit VPS-local cron if it SSHes to `root@65.108.215.200` instead of reading local files.

**Why forbidden:**
- Host labels are logical inventory names, not proof that remote transport is required.
- Self-SSH depends on agent/user SSH setup and launchd environment, not on credential substrate correctness.
- False drift alerts train agents to ignore the watchdog.

**Correct behavior:** Credential readers must detect the current host (`air`, `mac`, `vps`) and collapse matching logical host reads to direct file reads. Use SSH only for different hosts. Regression: `tools/tests/test_credentials_discovery.py::test_read_env_file_uses_local_path_when_running_on_air`.

### AP-7 — Logical host without a transport target

**Pattern:** A tool accepts `host in {mac, air, vps}` but its remote-target map only defines Air and VPS. On Air, a manifest row for `Mac` then raises an unhandled `KeyError` instead of a redacted read error. Tests accidentally pass on Mac because `Mac` is local, then fail on Air.

**Why forbidden:**
- The manifest's host column is a contract. If the CLI accepts a host, transport resolution must be total for that host.
- Cross-host audits should degrade to `read_errors`, not crash before reporting drift.
- Tests that depend on "current host" must set that host explicitly; otherwise the same suite tells different stories on Mac and Air.

**Correct behavior:** `REMOTE_SSH_TARGETS` must include every accepted logical host (`mac`, `air`, `vps`) with env overrides. Unit tests that use local fixture files must set `CREDENTIALS_DISCOVERY_LOCAL_HOST` explicitly. Regression: `tools/tests/test_credentials_discovery.py` must pass from both Mac and Air.

## Lookup workflow (every credential need follows this)

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│ 1. cat pages/secrets-manifest.md → grep <KEY>                │
│    ↓                                                         │
│ 2. Found a row? → note host(s) + path                        │
│    ↓                                                         │
│ 3. python3 tools/credentials_discovery.py find <KEY>         │
│    → JSON {key, paths:[...], services:[...], rotation}       │
│    ↓                                                         │
│ 4. ssh <host> 'source <path> && <command-using-$KEY>'        │
│    OR                                                        │
│    python3 tools/credentials_discovery.py source <KEY>       │
│    --host <host> | source /dev/stdin                         │
│    ↓                                                         │
│ 5. Use the credential. Never log its value.                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

If step 2 returns no row:
- It's a substrate gap, not a missing credential. SSH the most-likely host, grep the `.env` files for the key. Found it? Add to manifest, commit, then proceed.
- Genuinely missing? Need decision: do we need a new key? If yes, propose via Decision Rights protocol (if rotation has business cost) or just generate (if it's an internal-only auth). Always update the manifest in the same commit.

## Adding a new credential (workflow)

```
1. Decide: needed? Why? Cost of rotation?
2. Add row to pages/secrets-manifest.md (key, description, service, host, rotation)
3. Stage manifest. Pre-commit hook will demand the .env update is in the same commit.
4. Generate / obtain the value out-of-band (vendor portal, openssl rand, etc.).
5. Add to the right .env file on the right host.
6. If multi-host, sync to all listed hosts.
7. Commit both files atomically.
8. Restart any service that reads the .env (launchd jobs, Docker containers).
```

## Tier-2 placement rationale

This skill is Tier 2, not Tier 1, because:
- It loads on demand (when triggers match), not on every message
- It's domain-specific (credentials), not universal doctrine
- But it MUST load before any third-party-service work — hence Tier 2 not Tier 3

If a session starts without loading this skill and then asks the user for a credential, that's a session-defect. The manifest is the contract; the skill is the discipline.

## Cross-references (handshake with Pane 2 Codex tooling)

This skill (Opus, doctrine) and the runtime tool (Codex, mechanism) form a handshake:

- `pages/secrets-manifest.md` v2 — registry data (Opus 2026-05-05)
- `pages/skills/credentials-discovery/SKILL.md` — discipline (this file, Opus 2026-05-05)
- `tools/credentials_discovery.py` — runtime CLI (Pane 2 Codex 2026-05-05)
- `.git/hooks/pre-commit` — drift gate (Pane 2 Codex 2026-05-05)
- (optional) `tools/credentials_drift_check.sh` — daily watchdog (Pane 2 Codex Slice 3)

Bidirectional cross-references in finished artifacts = the handshake completes.

## Timeline

- **2026-05-07** v1.2.0 — Codex audit found `tools/tests/test_credentials_discovery.py` failing 4/34 on Air after v1.1 local-host collapse: `mac` was an accepted logical host but absent from `REMOTE_SSH_TARGETS`, and tests implicitly assumed Mac-local fixtures even when running on Air. Fix: add `CREDENTIALS_DISCOVERY_SSH_MAC`/`mac` transport target and an autouse fixture declaring `CREDENTIALS_DISCOVERY_LOCAL_HOST=mac`; targeted suite passes locally (`34 passed`). gbrain-timeline-ok: pages/skills/credentials-discovery/skill. No new LESSON (RULE ZERO).
- **2026-05-06** v1.1.0 — Codex GPT-5.5 session-start substrate verify absorbed AP-5 and AP-6. Root cause 1: a broad local config `rg` printed an Open Brain connector URL with access key while looking for MCP capability evidence. Root cause 2: Air `com.nous.credentials-drift` fired at 03:30 and failed with `ssh_exit_255` because `tools/credentials_discovery.py audit --hosts air,vps` SSHed to Air from Air; alert send also failed because the watchdog required `tg_send.sh` to be executable even though it invokes via `bash`. Fix: `credentials_discovery.py` now collapses host-local reads via `current_host_alias()`, `credentials_drift_check.sh` accepts readable `tg_send.sh`, tests pass, Air live watchdog exits 0 and `launchctl list` reports `- 0 com.nous.credentials-drift`. gbrain-timeline-ok: pages/skills/credentials-discovery/skill. No new LESSON (RULE ZERO).
- **2026-05-05** v1.0.0 — Born from Pane 3 Opus incident: agent asked Madi to paste `TODOIST_API_TOKEN` between backticks despite the value living at `/Users/madia/nous-agaas/.env` on Air for ~18 days (added the day Codex shipped Todoist sync, ~2026-04-25). Manifest v1 was a 2-row stub from 2026-04-17. Audit revealed 6 `.env` files, ~35 keys, all undocumented in the manifest. v1.0.0 ships with 4 anti-patterns + lookup workflow + handshake with Pane 2 Codex (`tools/credentials_discovery.py`). RULE ZERO compliance: SKILL.md doctrine + gbrain timeline entry, no LESSON file. Lease: `pages/progress/LEASE-claude-opus-credentials-substrate-2026-05-05.md`.

## See also

- [[secrets-manifest]] — the registry (data)
- [[skills/secrets-management]] — deploy/rotate/audit (legacy ops)
- [[skills/autonomous-build-manager]] — Tier-1 dispatch doctrine (this skill is what AP-1 of credentials should look like)
- [[skills/agent-quality]] — overlapping AP about not asking redundant questions
- [[laws/LAW-013-100-percent-truth]] — agent must say "I have it" only when verified, never optimistic
