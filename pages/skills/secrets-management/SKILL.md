---
tier: 2
type: skill
name: secrets-management
version: 1.9.0
description: "Mac-primary secrets storage + deploy pattern for Nous AGaaS. Apple Keychain (login) is SoT; iCloud sync is blocked by macOS entitlement policy on /usr/bin/swift and deferred; pipe-never-variable deploy to VPS/Air .env files; manifest at pages/secrets-manifest.md. AP-11 v1.4 — every .env MUST be 0600 regardless of contents; scanned via tools/test_secret_perms.sh (paired AP-36 sibling-test) across all hosts; pre-commit RULE 6 enforces mechanically. AP-12 v1.6 — runtime scripts must read secrets from env files, never hardcode master/API keys. AP-13 v1.7 — GitHub/private mirrors must pass a current-tree secret scan and use sanitized snapshot export when history contains old secret literals. AP-14 v1.8 — never run shell xtrace on scripts that source secrets. AP-15 v1.9 — rotate embedded GitHub credentials by proving a parallel non-token remote first, then switching, verifying, and only then revoking."
triggers:
  - storing a new API token / bot token / webhook secret
  - rotating an existing secret
  - deploying secrets to a new service
  - auditing whether a target .env matches manifest
tools: [Bash, tools/secrets-*.sh, tools/secrets-*.swift]
mutating: true
parameters:
  service: manifest service name (e.g., apk-status-bot)
  target: vps or air
absorbs_lessons: []
related: [SPEC-SECRETS-MANIFEST-V1-2026-04-17, secrets-manifest, audit]
last_updated: 2026-05-12
title: "secrets-management v1.9.0"
---

# secrets-management v1.9.0

## Purpose

One tool + one pattern + one audit story for storing the small number of secrets Nous AGaaS needs on VPS/Air. APK_BOT_TOKEN today; webhook tokens, Jira basic-auth, camera credentials later — all under the same flow.

## Flow

1. **Register** the secret in `pages/secrets-manifest.md` (schema doc; non-secret).
2. **Store** the value in macOS Keychain via `tools/secrets-keychain-add.swift` (stdin → Keychain).
3. **Deploy** to target via `tools/secrets-deploy.sh <service> <target>`.
4. **Verify** via `tools/secrets-deploy.sh --audit <service> <target>`.
5. **Rotate** by repeating step 2 with `--update` then step 3 then `systemctl restart <svc>`.

## Usage

```bash
# Register (manifest edit, then commit)
# Store
echo -n "$TOKEN" | tools/secrets-keychain-add.swift nous-agaas/APK_BOT_TOKEN --icloud
# Deploy
tools/secrets-deploy.sh apk-status-bot vps
# Audit
tools/secrets-deploy.sh --audit apk-status-bot vps
# Rotate
echo -n "$NEW_TOKEN" | tools/secrets-keychain-add.swift nous-agaas/APK_BOT_TOKEN --icloud --update
tools/secrets-deploy.sh apk-status-bot vps
ssh root@VPS 'systemctl restart apk-alert-sender'
```

## Anti-Patterns

- **AP-1: Never assign a secret to a bash variable.** Use a single pipe from Keychain read to ssh stdin. `VAR=$(security ...)` is forbidden — `set -x`, crash dumps, or inherited env can leak it.
- **AP-2: Always stage `.env.new` in the same directory as `.env`.** POSIX atomic rename requires same filesystem. `mv /tmp/.env.new /opt/.../env` is not atomic.
- **AP-3: Never `-o StrictHostKeyChecking=no` in deploy.** Bail if host unknown. First-run: run `ssh-keyscan <host> >> ~/.ssh/known_hosts` out-of-band and verify fingerprint.
- **AP-4: Single-service bot rotation has a ~30–60s outage.** BotFather `/revoke` kills the old token immediately; systemd restart takes seconds. Schedule rotation for low-traffic windows; name the gap.
- **AP-5: systemd units MUST use `EnvironmentFile=/opt/nous-agaas/.env`, not inline `Environment=`.** The inline form leaks the value to journald on service start.
- **AP-6: Audit = file presence + 0600 perms + age.** Never MD5-of-value — reveals info about short tokens. The `--audit` flag uses `stat` only.
- **AP-7: Trap EXIT in deploy scripts to `rm -f` staging files.** A crashed deploy must not leave `.env.new` readable on the target.
- **AP-9: HTTP-client debug/INFO loggers leak tokens embedded in URLs into journald.** (session 42 T22, 2026-04-17) Telegram Bot API embeds the token in the URL path (`/bot<TOKEN>/getUpdates`). `httpx` default INFO logger emits `HTTP Request: GET https://api.telegram.org/bot<TOKEN>/...` for every call. When the process runs under systemd, those log lines land in journald as plaintext — persisted indefinitely, readable by anyone with `systemd-journal` group or root. AP-5 covers systemd's `EnvironmentFile=` for startup-env safety; it does NOT cover library-level logging. **Rule:** at startup of any service that hits a URL-embedded-token API, explicitly silence the HTTP-client INFO logger: `logging.getLogger("httpx").setLevel(logging.WARNING); logging.getLogger("httpcore").setLevel(logging.WARNING)`. Same for `requests` → `"urllib3"`. For an auditable-logs requirement, log ONLY the method + path template (`GET /getUpdates`) never the full URL. **Detection:** `journalctl -u <service> | grep -E "bot[0-9]+:[A-Za-z0-9_-]+"` should return zero lines. **First hit:** APK_BOT_TOKEN logged twice in journald before fix landed; rotation compulsory.
- **AP-10: Bot-owned WARNING/ERROR handlers that stringify httpx exceptions leak URL-with-token into journald — even when httpx INFO is silenced per AP-9.** (session 46-B A3, 2026-04-18) Evidence: during APK_BOT_TOKEN rotation the pre-bootout PID logged two `getUpdates failed: Client error '401 Unauthorized' for url 'https://api.telegram.org/bot8783930917:AAHhf0Vr...'` WARNING lines — the httpx exception `__str__` includes the full URL. Old token was already revoked so damage was self-mitigating, but the same code path would leak a still-valid token on any 401 (rate limit, server-side revoke, network glitch). AP-9 silenced httpx INFO logs; AP-10 extends to ALL bot-owned loggers that stringify httpx exceptions via `f"… {e}"` / `str(e)`. **Rule:** in any bot service's exception handler for URL-embedded-token APIs, never log the raw exception. Allowed forms: `e.response.status_code + safe_path_only` OR `str(e).replace(TOKEN, '***')` OR a structured-logger auto-redact filter. Paired with `test_bot_polling_no_token_leak.py` sibling-test asserting log records for 401 URL errors do NOT contain the token. Code-change target: `apk-status-bot/apk_status_bot/bot_polling.py` exception handler. **Detection:** `journalctl -u <service> | grep -E 'bot[0-9]+:[A-Za-z0-9_-]{30,}'` — any hit in a bot service's journal is an AP-10 violation (same detector as AP-9 but scoped to WARNING/ERROR level too, not just INFO). Amends AP-9. Full-session evidence of first hit in Timeline `v1.2.0 → v1.3.0` entry. (Bullet added session 48 Mac-interactive deep audit as cross-session corrective action — the v1.3.0 bump's Timeline described AP-10 but no matching bullet was added to the AP list, violating `mistake-to-skill` AP-11 v1.9 4th check.)
- **AP-11: Any `.env` file anywhere in the stack (Mac / Air / VPS / container) MUST be 0600 regardless of contents. Eye-audit misses what mechanical scanners catch.** (session 48 W2, 2026-04-18) My session-48 manual audit (P-SAFE-06) scored Air secrets GREEN after inspecting `/Users/madia/nous-agaas/.env` (0600 ✓) and `/Users/madia/nous-agaas/litellm/.env` (**0644 — which I missed in the quick-scan output**). The W2 sibling-test `tools/test_secret_perms.sh` — written directly after the audit as paired AP-36 artifact — caught it on first run. `litellm/.env` contains the LiteLLM `MASTER_KEY` I'd used for P-HEALTH-04 chat-completion probing during the same audit. Human eyes also missed VPS `/root/nous-agaas/codebase/.env` + `/root/nous-agaas/codebase/satory-frontend/.env` (session 47 handoff + session 46 deep-audit + session 45 close all missed these). The scanner caught all 3 on first pass. **Rule:** every `*.env` file is 0600. Exclusions only for template files (`.env.example` / `.env.template` / `.env.sample` — never contain real values). **Detection + enforcement:** `bash tools/test_secret_perms.sh [TARGET_DIR]` → exit 0 clean / exit 2 drift. Runs locally OR piped via `ssh <host> 'bash -s <path>' < tools/test_secret_perms.sh`. Paired with `tools/test_secret_perms_self.sh` (4-test sandbox validation — AP-36 sibling-test). **Mechanical gate:** `infrastructure` v2.37 → v2.38 absorbs AP-45 — pre-commit RULE 6 invokes the scanner on any staged `*.env` changes; REJECT if scanner exits non-zero. 7th compounding gate in the chain (AP-35 / AP-36 / AP-43 / AP-44 / pre-receive / TaskCompleted / this). Evidence: session 48 W1+W4 executed, caught + fixed 3 real drifts (Air litellm/.env, VPS 2x codebase/.env). Cross-ref AP-6 (file-presence + perms + age audit). No new LESSON (RULE ZERO).

- **AP-12: Runtime scripts must read secrets from env files, never hardcode master/API keys.** (session 76 paid-provider audit, 2026-04-26) A provider/cost audit found the LiteLLM master key literal embedded in multiple tracked Air runtime scripts (`run_task.py`, `light-probe.sh`, `nightly-audit.sh`, `morning-brief.sh`, `llm_judge_routing.py`). That defeats AP-11's file-permission discipline: the env file can be 0600 while the same secret is still copied into executable code, git history, backup files, and audit output. **Rule:** scripts may hardcode env variable names and env file paths; they must not hardcode secret values. For Air LiteLLM access, source `/Users/madia/nous-agaas/litellm/.env` or read `LITELLM_MASTER_KEY` via a small env parser. If a script must run on multiple hosts, fail closed with "missing key" rather than falling back to a committed literal. **Detection:** `rg -n "sk-|Bearer [A-Za-z0-9_-]{20,}|api_key *= *[\"'][A-Za-z0-9_-]{20,}" tools pages/skills` should return zero live secret literals; allow-list docs that mention variable names only. **Rotation note:** removing literals stops future leakage, but any literal that lived in git history should be rotated in a controlled window after all consumers read env files. No new LESSON (RULE ZERO).

- **AP-13: GitHub mirrors must be sanitized snapshots when vault history contains historical secret literals.** (session 2026-04-28, GitHub mirror gate) The first attempt to create `mayazbay/nous-agaas-private` correctly stopped at the secret-scan gate: old progress/handoff pages still contained literal Telegram, LiteLLM, Langfuse, and gateway tokens. Even if some values are stale or rotated, pushing full vault history to GitHub would preserve the literals forever and train future agents that broad mirroring is safe. **Rule:** before any GitHub mirror or external backup, run `tools/test_github_mirror_secret_scan.sh` against the current tree and fail closed on any hit. If history contains old secret literals, do **not** push repository history; create a sanitized snapshot export from the current clean tree instead. Exclude `raw/`, `.git/`, runtime `.env`, caches, Obsidian workspace UI state, and any generated payload directories. The GitHub mirror is for code review / CI / issue workflows, not for raw personal exports or credential-bearing operational history. **Detection:** `bash tools/test_github_mirror_secret_scan.sh <tree>` must pass before creating or updating a GitHub mirror. **Rotation note:** if the scan finds a still-live service token, rotate it before mirror work resumes. No new LESSON (RULE ZERO).

- **AP-14: Never run shell xtrace on scripts that source secrets.** (2026-05-07 gbrain proxy repair) `bash -x` prints every assignment from sourced env files, including values that otherwise live behind 0600 permissions. This bypasses AP-11 and AP-12 without writing a secret to git: the leak lands in terminal transcripts, CI logs, task logs, or support captures. **Rule:** do not run `bash -x`, `set -x`, or traced wrappers around scripts that source `.env`, Keychain output, or `/root/.gbrain/*.env`. If tracing control flow is necessary, run it with a dummy env file via an override such as `GBRAIN_OPENAI_COMPAT_ENV=/tmp/dummy.env`, or add explicit safe debug echoes that print key presence/length only. **Detection:** before any traced shell command, grep the target for `source`, `. `, `.env`, `set -a`, `security`, or `*_KEY`; if present, do not xtrace with live secrets. No new LESSON (RULE ZERO).

- **AP-15: Rotate embedded GitHub credentials by adding a proven non-token path before removing the old path.** (2026-05-12 GitHub OAuth remote hardening) An embedded OAuth/PAT in a git remote is a live secret in `.git/config`, terminal transcripts, and any copied routine prompt. Revoking it first can break GitHub mirror/checkpoint/routine paths. **Rule:** do not revoke or delete the old credential until a parallel replacement remote proves `git ls-remote` and `git push --dry-run`. Preferred replacement is SSH (`git@github.com:owner/repo.git`) using an existing authenticated key, a repo-scoped deploy key, or a GitHub App/connector secret. Migration order: (1) mask and inventory remotes on every writer host, (2) add a temporary non-token remote such as `github-ssh`, (3) prove `ls-remote` and `push --dry-run`, (4) switch the production `github` remote to the non-token URL, (5) push once if GitHub is behind, (6) verify token-pattern count is zero in `remote.*.url`, (7) only then revoke the old OAuth/PAT. **Cloud routine rule:** Claude/GitHub routines must use connector auth or secret-store variables, not token-bearing clone URLs in prompts or git remotes; if the routine UI is not locally writable, leave the old token alive until one scheduled run succeeds with the replacement. **Scanner rule:** secret scanners must print path-only failure output; never print the matching secret line.

- **AP-8: `--icloud` sync is unreachable via `/usr/bin/swift` — don't promise it.** (session 42 T18, 2026-04-17) Setting `kSecAttrSynchronizable=true` in `SecItemAdd` returns `errSecMissingEntitlement` (-34018) when the calling binary lacks `com.apple.developer.icloud-services`. `/usr/bin/swift` is an unsigned interpreter; `swiftc`-built binaries likewise unless code-signed with a provisioning profile from a paid Apple Developer account. **Reality:** v1 secrets are local-only Mac Keychain; iCloud sync to iPad/iPhone requires building a signed helper app (deferred). Manifest `icloud` column must reflect truth — if the add succeeded via our swift helper, the value is `no`. Recovery for local-only secrets: Time Machine backup OR re-issue from source (e.g., BotFather `/revoke`). First hit: APK_BOT_TOKEN session 42.

## Rules

1. The SCRIPT shape is public (in git). The SECRET values are not.
2. Every new secret gets a manifest row BEFORE the Keychain store — the row is the contract.
3. Deploy script runs ONLY on Mac (uname guard); targets push outward, never pull.
4. Rotation is always: update Keychain → re-deploy → restart service. In that order.
5. If `--audit` fails post-deploy, don't guess — read stderr, check target file perms manually.

## Rules absorbed from lessons

None yet. First consumer is APK_BOT_TOKEN session 42.

## Brain-aware invocation

Before executing: `mcp__gbrain__search` for the secret's service name — past deploys of the same service may have left notes. After executing: `mcp__gbrain__add_timeline_entry slug="pages/skills/secrets-management/skill"` with a one-line "deployed <service> to <target> YYYY-MM-DD".

## Timeline

- **2026-05-12** | v1.8.0 → v1.9.0 — GitHub OAuth remote hardening added AP-15 after Mac/Air wiki remotes carried embedded GitHub credentials. Proved SSH auth and dry-run push on both hosts, switched `github` remotes to `git@github.com:mayazbay/nous-agaas-private.git`, pushed GitHub to current HEAD, and patched `tools/test_github_mirror_secret_scan.sh` to exclude nested `raw/` archives and print path-only failures so the scanner cannot leak matched secrets. gbrain-timeline-ok: pages/skills/secrets-management/skill. No new LESSON (RULE ZERO).
- **2026-05-07** | v1.7.0 → v1.8.0 — gbrain proxy repair exposed a LiteLLM proxy key to the local tool transcript by running `bash -x` on a secret-sourcing script. Codified AP-14: never xtrace scripts that source live secrets; use dummy env overrides or explicit safe debug output. gbrain-timeline-ok: pages/skills/secrets-management/skill. No new LESSON (RULE ZERO).
- **2026-04-28** | v1.6.0 → v1.7.0 — GitHub private mirror gate found historical secret literals in old progress/handoff pages before any GitHub push. Redacted the current tree, added `tools/test_github_mirror_secret_scan.sh`, and codified AP-13: GitHub mirrors use current-tree secret gates and sanitized snapshot export when vault history contains old literal secrets. No raw history push. No new LESSON (RULE ZERO).
- **2026-04-26** | v1.5.0 → v1.6.0 — Paid-provider audit found LiteLLM master-key literals in tracked Air runtime scripts even though `litellm/.env` existed and was the intended protected source. Patched `run_task.py`, `light-probe.sh`, `nightly-audit.sh`, `morning-brief.sh`, and `llm_judge_routing.py` to read `LITELLM_MASTER_KEY` from env / `/Users/madia/nous-agaas/litellm/.env` instead of a committed fallback. Added AP-12 so future subscription/provider audits scan for secret literals, not only `.env` permissions. Rotation is a separate controlled step after consumers prove env-based access. No new LESSON (RULE ZERO).
- **2026-04-18** | v1.4.0 → v1.5.0 — Session 48 Mac-interactive deep-audit: patched the AP-10 orphan. Session 46-B A3 had bumped v1.2 → v1.3 with Timeline describing AP-10 (bot-owned exception-stringification token leak, amends AP-9), but no matching `- **AP-10: …**` bullet was ever added to the AP list — `mistake-to-skill` AP-11 v1.9 4th check violation, invisible to pre-commit RULE 4 (grep-based parity only). Detection: extended Timeline↔AP-bullet orphan scanner run during `audit` AP-14 deep-audit; flagged `secrets-management claimed ['10'], existing ['1'..'9','11']`. Fix: inserted AP-10 bullet between AP-9 and AP-11, content distilled from v1.3.0 Timeline entry (detector one-liner + fix pattern + code-change target + cross-ref AP-9). **Compound-gate candidate (AP-47, carry to next session):** extend `tools/test_skill_version_parity.sh` with the Timeline↔AP-bullet parity scanner (re-run of this deep-audit script) + wire into pre-commit RULE 4 — mechanically enforces `mistake-to-skill` AP-11 v1.9 4th check; same AP-43 pattern that made AP-11 checks 1-3 mechanical. No new LESSON (RULE ZERO).
- **2026-04-18** | v1.3.0 → v1.4.0 — Session 48 W2+W3: absorbed **AP-11** — every `.env` file MUST be 0600 regardless of contents; mechanical sibling-test `tools/test_secret_perms.sh` catches what human eyes miss. Evidence: session 48 manual P-SAFE-06 audit scored Air GREEN after eye-scan of `ls -la` output; the scanner written minutes later flagged Air `/Users/madia/nous-agaas/litellm/.env` at 0644 (with `LITELLM_MASTER_KEY` set — the key I'd just used to probe P-HEALTH-04 chat completion during the same audit). Also caught VPS `codebase/.env` + `codebase/satory-frontend/.env` at 0644 that earlier audits missed for multiple sessions. All 3 fixed session-48 W1/W2; scanner now GREEN across all 3 hosts (Mac: N/A no runtime, Air: 2 files 0600, VPS: 3 files 0600). Companion: `tools/test_secret_perms_self.sh` (4-test sandbox validation, AP-36 sibling-test). Pre-commit RULE 6 wiring shipped session 48 W4 as `infrastructure` v2.38 AP-45 (7th mechanical compounding gate). No new LESSON (RULE ZERO).
- **2026-04-18** | v1.2.0 → v1.3.0 — Session 46-B A3 close: added AP-10 — bot-owned WARNING/ERROR handlers that embed httpx exceptions via `f"... {e}"` or `str(e)` LEAK URL-with-token into journald even when httpx INFO is silenced per AP-9. Evidence: during APK_BOT_TOKEN rotation, the pre-bootout PID logged 2 WARNING lines `getUpdates failed: Client error '401 Unauthorized' for url 'https://api.telegram.org/bot8783930917:AAHhf0Vr...'` — the httpx exception stringification includes the URL. Old token was already revoked so damage was self-mitigating, but the SAME code path would leak a still-valid token on any 401 (rate limit / server-side revoke / network glitch). Fix pattern: `e.response.status_code + safe_path_only` OR `str(e).replace(TOKEN, '***')` OR a structured-logger auto-redact filter + sibling test `test_bot_polling_no_token_leak.py` asserting log records for 401 URL errors don't contain the token. Code change belongs in `apk-status-bot/apk_status_bot/bot_polling.py` exception handler (handoff to session 47 with this AP as the spec). Amends AP-9: AP-9 silenced httpx INFO logs; AP-10 extends to ALL bot-owned loggers that stringify httpx exceptions. Detection: `grep -E 'bot[0-9]+:[A-Za-z0-9_-]{30,}' <journal>` — any hit in a bot service's journal is an AP-10 violation. No new LESSON (RULE ZERO).
- **2026-04-17** | v1.2.0 — Session 42 T22: added AP-9 — httpx/urllib3 INFO loggers leak URL-embedded tokens (Telegram bot token) into journald. Detection one-liner + mitigation (set httpx + httpcore loggers to WARNING). First hit: APK_BOT_TOKEN leaked twice to systemd journal before fix landed at `apk_status_bot/bot_polling.py`. Rotation mandatory.
- **2026-04-17** | v1.1.0 — Session 42 T18: added AP-8 — `--icloud` flag hits `errSecMissingEntitlement` (-34018) because `/usr/bin/swift` lacks iCloud entitlement. v1 is local-Mac-Keychain only; iCloud sync needs a signed helper app (deferred). APK_BOT_TOKEN stored local-only; manifest icloud column corrected to `no`.
- **2026-04-17** | v1.0.0 — created in session 42 per [[SPEC-SECRETS-MANIFEST-V1-2026-04-17]]. First consumer: APK_BOT_TOKEN for @NousAPKstatusbot.

## See also

- [[SPEC-SECRETS-MANIFEST-V1-2026-04-17]] — full spec with 12 locked decisions, security properties, recovery tiers
- [[secrets-manifest]] — non-secret registry of all keys
- [[SPEC-APK-STATUS-BOT-A-2026-04-17]] — first consumer
- [[audit]] — AP-10 4-target parity check covers this skill once registered
- [[skills/_gbrain/BRAIN-AWARE-INVOCATION]] — query-then-write protocol
