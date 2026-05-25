---
tier: 1
name: evidence-verification
description: "Use BEFORE claiming any task is done, any number is correct, any status is current. Triggers on: 'done', 'complete', 'verified', 'confirmed', 'works', 'online', 'status', 'data', 'freshness', claim, assertion, proof."
type: skill
id: SKILL-EVIDENCE-VERIFICATION
version: 1.7.1
status: active
absorbs_laws: [LAW-008, LAW-013]
absorbs_lessons: [LESSON-085, LESSON-103, LESSON-123, LESSON-109]
tags: [skill, evidence, verification, anti-slop, data-freshness, truth, read-only-probes, 2026-04-17]
date: 2026-04-16
source_count: 0
last_updated: 2026-05-21
related: [SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15, agent-quality, satory-dashboard, LAW-008-anti-hallucination, LAW-013-100-percent-truth]
title: "evidence-verification v1.7.1"
---

# evidence-verification v1.7.1

## Current rules (compiled truth)

1. **Never claim "done" without a verified probe.** "Done" means: test output pasted (not "tests passed"), curl/screenshot/terminal output showing it works, actual API response (not "should work"), compared against original requirement. LESSON-085 codifies this. LAW-013 mandates 100% truth.

2. **Every factual number must have a source.** The source is one of: (a) wiki file path, (b) live measurement command + output, (c) cited API response, (d) egov.kz or official document. NEVER cite from memory — verify every number against source.

3. **data_freshness envelope on EVERY status API response.** Per LESSON-103 (Satory dashboard lied when data stale): every endpoint returning status data MUST include `{data_as_of: ISO timestamp, data_age_seconds: int, is_stale: bool}`. Stale threshold: 86400 seconds (24h) unless domain requires tighter.

4. **Never use lexicographic string compare for timestamps.** LESSON-109: `"2026-04-15" > "2026-04-14"` works by accident. `"2026-04-15T09:00:00" > "2026-04-15T10:00:00"` FAILS (string compare, not datetime). Always parse to `datetime` object first, then compare.

5. **If a fact is >7 days old and not re-verified, label it STALE** in any user-facing output. Do not present it as "current" without re-checking. This is cross-cutting — applies to dashboards, API responses, and text answers.

6. **100% truth = "I don't know" is a valid answer.** Hedge-language ("I believe", "I think", "it should") is not truth. Either cite a source or say "I don't know" and propose how to find out. LAW-013.

7. **User-facing links must be probed before being presented as working.** Before sending any public, tunnel, localhost, preview, or dev-server URL as "working", run a reachability probe from the relevant context and keep the status in the answer. Use `python3 tools/verify_user_facing_links.py --json` on draft text, or an equivalent `curl -fsSIL --max-time 10 <url>` / browser probe. If the URL fails, do not dress it up as working; say `verified: no`, include the status/error, and name the next command.

8. **Hermes and every agent profile needs an honesty overlay, not agreement bias.** Standing instructions must force uncertainty labels, source discipline, number freshness, recent-event verification, people/quote caution, and an agreement gate. A simple "yes" is allowed only after checking what could make it false and naming the proof or missing proof.

## P1 — "Done" proof checklist (run before claiming ANY task complete)

- [ ] Test output pasted (verbatim, not "tests passed")
- [ ] curl / screenshot / terminal output showing it works in practice
- [ ] Actual API response or real values (not "should work")
- [ ] Compared against original requirement — does it match?
- [ ] If frontend: clicked every button (LESSON-047)
- [ ] If data: verified with real values, not assumptions

**All must be checked. If ANY is NO → not done.**

## P2 — Citation format

| Source type | Format |
|---|---|
| In-vault wiki page | `[[wikilinks]]` |
| Raw source file | `[Source: raw/path/to/file.ext]` |
| Live measurement | `[verified: ssh air 'command' → output]` |
| External URL | `[Source: url, accessed YYYY-MM-DD]` |

## P3 — Stale-fact detection (manual or automated)

```bash
# Find wiki pages with last_updated > 7 days ago
cd "/path/to/vault"
find pages/ -name "*.md" -exec grep -l "last_updated:" {} \; | while read f; do
  date=$(grep "last_updated:" "$f" | head -1 | sed 's/last_updated: //')
  age=$(( ($(date +%s) - $(date -d "$date" +%s 2>/dev/null || echo 0)) / 86400 ))
  [ "$age" -gt 7 ] && echo "STALE ($age days): $f"
done
```

## Anti-patterns

### AP-1: Hedge language
**Problem:** "I believe the service is running" → if wrong, Madi loses trust. If right, the hedging was noise.
**Fix:** Either `ssh air 'curl -s localhost:18789/healthz'` and cite the output, or say "I don't know — let me check."

### AP-2: "X is ONLINE" without probe
**Problem:** LESSON-103 — Satory dashboard said "156/243 cameras ONLINE" while polling had been dead 27 days. The number was from a 27-day-old snapshot, not a live probe.
**Fix:** Every status claim must include `data_as_of` timestamp. If `data_age_seconds > stale_threshold` → label STALE, not ONLINE.

### AP-3: Citing a skill/lesson without reading it
**Problem:** "Per LESSON-085..." but LESSON-085 says something different from what you cited.
**Fix:** Read the actual file before citing. Don't paraphrase from memory.

### AP-4: Paraphrasing past outputs from memory
**Problem:** "Last time we ran that probe it returned 18.5 KB" — maybe, but that was 2 hours ago. State changes.
**Fix:** Re-run the probe. Real-time output > remembered output.

### AP-5: Drawing structural conclusions from a LIMIT-N sample
**Problem:** Session 43 ran `sqlite3 ... 'SELECT camera_ip FROM camera_status LIMIT 5;'`, got 5 rows all in `10.170.*`, declared "registry has 10.170.* IPs but events.db has 10.235.* — IP MISMATCH BLOCKER." Confidently. In Markdown. With emoji. Then logged it as a session-43 finding for the project page. Reality: `camera_status` has BOTH `10.170.*` AND `10.235.*` IPs. Alphabetic sort puts `10.170.*` first; `LIMIT 5` clipped before reaching `10.235.*`. The "mismatch" was an artifact of sample size, not a real structural drift. Triggered a 30-min false-alarm + corrupted my Phase 9 conclusion in the session 43 atomic audit.

**Root cause (5-whys):**
1. Why wrong conclusion? `LIMIT 5` returned a non-representative slice; I treated it as representative.
2. Why `LIMIT 5`? Wanted a quick sanity peek at IP format.
3. Why not GROUP BY all subnets? Didn't think to. Default-thinking: "first few rows show me the shape."
4. Why no double-check before declaring "BLOCKER"? Confirmation bias: Madi had said "no lie, no BS" — felt urgency to deliver findings. Picked the first plausible explanation.
5. Why anchor on first plausible? When you're hunting for problems, the FIRST candidate problem looks like signal. It's actually noise until you've enumerated alternatives.

**Rule (amends AP-2 + AP-4):** Before declaring any STRUCTURAL claim about a dataset (schema mismatch, IP-range drift, missing column, broken join, "X is empty", "Y has only Z"), enumerate the WHOLE relevant set or use an aggregate. NEVER from a `LIMIT 5` sample. Specifically:
- "Schema X has only column Y" → `.schema X` or `PRAGMA table_info(X)`, not `SELECT * FROM X LIMIT 1`.
- "Table X has IP range Y" → `SELECT DISTINCT substr(ip, 1, 8), COUNT(*) FROM X GROUP BY ...`, not `LIMIT 5`.
- "DB Y has 0 rows in window W" → `SELECT COUNT(*) WHERE ...`, AND verify against the OPPOSITE filter to rule out window bug.
- "Tables X and Y don't overlap" → `SELECT COUNT(*) FROM X JOIN Y ON ...`, not "looked at first 5 of each, no match seen."

**Verification contract:** After making any structural claim, re-state with the GROUP BY / aggregate / JOIN COUNT that proved it. If you can't re-state the proof, the claim is unverified.

**Concrete fix applied 2026-04-17 (session 43):** Re-ran with `GROUP BY subnet`. Found camera_status has BOTH `10.170.*` (mostly offline 17 days) AND `10.235.*` (51 emitting cameras, 43 in registry, 8 truly unknown). Bot's data model is CORRECT. The "BLOCKER" was a sample-size artifact — retracted in Phase 9 of session 43 audit + absorbed here.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline. The original LIMIT-5 query output (saved in session 43 transcript) is the receipt.

### AP-6: Verification probes MUST be read-only

**Problem:** Running `sqlite3 /opt/nous-agaas/apk_health.db 'SELECT COUNT(*) FROM apk_health_current'` against a *nonexistent* path returns `no such table: apk_health_current` AND creates the file as a 0-byte stub (sqlite3 CLI treats a missing path as "create new DB"). Session 44 (2026-04-17) audit: probed the wrong path, got an empty-file result, nearly absorbed a phantom "orphan stub DB" drift before realizing the CLI itself had created the stub 0.001s before reading it. File birth time matched the audit query timestamp to the millisecond — the probe made its own answer.

**Root cause (5-whys):**
1. Why an empty 0-byte DB at the wrong path? My own audit query created it.
2. Why did my audit query create it? `sqlite3 <path> '<query>'` auto-creates the path if missing — no error, no prompt.
3. Why did I assume the CLI was read-only? Familiarity bias — `sqlite3 a.db 'SELECT...'` FEELS read-only. It isn't.
4. Why no guard? Habitual usage pattern from dev machines where the DB is always present.
5. Why this is dangerous in audit context: the probe mutated the very state it was measuring, and a subsequent probe would read the mutation and conclude "drift." Classic observer-effect.

**Rule:** Every audit/verification probe MUST be either read-only OR check-existence-first:

| Tool | Unsafe | Safe |
|---|---|---|
| sqlite3 | `sqlite3 /path '...'` (creates) | `sqlite3 -readonly /path '...'` OR `test -s /path && sqlite3 /path '...'` |
| file state | `touch /path`, `cat >> /path` | `stat /path`, `ls -la /path` |
| git state | `git fetch` (mutates FETCH_HEAD) | `git log`, `git rev-parse`, `git ls-remote` |
| network | `curl -o /tmp/x url` (creates) | `curl -I url` OR `curl -s -o /dev/null -w '%{http_code}' url` |
| docker | `docker run`, `docker start`, `docker pull` | `docker ps`, `docker inspect`, `docker images` |
| sqlite schema | `sqlite3 /path '.schema'` (creates) | `test -s /path && sqlite3 -readonly /path '.schema'` |

**Verification contract:** Before running any probe in an audit, ask "can this CREATE a file, change a timestamp, or start a process?" If yes, wrap in a pre-test (`test -s /path`) or use the tool's read-only flag (`sqlite3 -readonly`, `curl -I`). If you can't guarantee read-only, state that in the finding ("measurement may have side-effect X").

**Amends AP-4 (paraphrase from memory).** AP-4 says "re-run the probe — real-time > remembered." AP-6 adds: the re-run itself MUST NOT be what changes the state. Otherwise you're measuring your own footprint.

**First hit:** Session 44, 2026-04-17 — `/opt/nous-agaas/apk_health.db` created as 0-byte stub by audit's own `sqlite3 <wrong_path> 'SELECT COUNT(*)'` probe; birth time 16:46:54 matched query time. Deleted post-absorption. Real DB was always at `/opt/nous-agaas/apk-status-bot/data/apk_health.db` (602KB, 11 tables, 3,952 daily rows). No phantom drift; audit probe mis-measured by mutating.

**Why no new LESSON file:** RULE ZERO. Evidence lives here + gbrain timeline.

### AP-7: User-facing bot/email/webhook messages require a ROUND-TRIP verification, not just a code-path test

**Problem:** Session 42 T22 shipped `apk-status-bot`'s `/start` WELCOME. Unit tests asserted `dispatch_command("/start", ...)` returned a non-None WELCOME string (9/9 green). Service was active, received Madi's `/start`, dispatched reply. Claim: "service is ACTIVE; bot is responding." Madi tested `/start` — saw nothing. Root cause: Telegram's MarkdownV2 parser rejected the WELCOME payload with HTTP 400 because `Привет!` had an unescaped `!` (MarkdownV2 reserves `! _ * [ ] ( ) ~ \` > # + - = | { } . !`). `send_message` got the 400, logged a WARNING to journald, returned — but agent claimed "works" without ever watching for that warning path.

**Root cause (5-whys):**
1. Why did Madi see nothing? Telegram rejected the bot's reply (HTTP 400 MarkdownV2 parse error).
2. Why did the parser reject it? Unescaped `!` in WELCOME.
3. Why wasn't this caught before shipping? Unit tests only verified the string came out of `dispatch_command` — never verified Telegram's renderer accepted it.
4. Why no round-trip test? "Done" was declared from systemd `active` + unit tests green. The user-facing delivery path was never exercised end-to-end.
5. Why is this a recurring class of failure? Any "compiled output consumed by an external parser" (HTML email, Slack Block Kit, Telegram MarkdownV2, Mermaid diagram syntax, LaTeX, SVG) silently rejects malformed payloads at render time. Code-path tests that stop at "we built the string" systematically miss render-side errors.

**Rule:** For every user-facing message format, the "done" test must include a round-trip through the actual renderer:

| Format | Unit-test-only is NOT enough | Must verify |
|---|---|---|
| Telegram MarkdownV2 | `assert reply.startswith("👋")` | `send_message(client, chat_id=TEST_CHAT, text=reply)` returns HTTP 200 |
| HTML email | `assert "<h1>" in body` | Actually send to a capture inbox + retrieve + render |
| Slack Block Kit | Schema passes | POST to Slack API (test channel) and get `ok:true` |
| Markdown for GitHub | Renders locally | Open the PR preview, screenshot, file an evidence file |
| LaTeX / Mermaid | Parses | Compile via real toolchain, check PDF/PNG produced |

**Verification contract for bots specifically:**

```bash
# Before declaring a bot command is "working":
# 1. Invoke dispatch_command() → get reply string
# 2. Call send_message() with that string to YOUR OWN chat_id
# 3. Assert HTTP 200 and ok:true
# 4. Visually confirm the message RENDERS (not just arrives) in the client
```

A systemd unit being `active` means the **process** is alive. It does NOT mean the **delivery** works. `active` + 0 `recv` errors in the journal is ALSO not sufficient — `send_message` may be failing silently at WARNING level (we don't fail-loud on send errors because bots must keep polling).

**Amends AP-1 (hedge language) + AP-4 (paraphrase from memory).** The specific amendment: "done" for user-facing text outputs requires renderer-side proof, not just producer-side proof. A hand-escape of MarkdownV2 without a round-trip test is "should work" language dressed up as code.

**First hit:** Session 42 T22 bot_polling.py — Привет! unescaped `!` → Telegram 400 → Madi saw nothing → I claimed "service active, waiting for /start" without the round-trip. The patch at commit `06d2822` added (a) the `!` escape, (b) a regression unit test scanning WELCOME for unescaped MDv2 reserved chars, and (c) a pre-deploy send_message call to admin DM (HTTP 200 verified) before restarting the service. Evidence: message_id=11 received in Madi's chat post-fix. Absorbed here. No new LESSON (RULE ZERO).

### AP-8: Never delegate investigation to the user when the agent has the access to run the probe

**Problem:** Session 42, after the /status bot reply showed `0/0 работают`, my v1.3 no-data fix wrote: "⚠ Нет данных ... вероятно, поток событий приостановлен. Проверьте ингест ISAPI/VMS." Madi's pushback (exact words, session 42): "Instead of writing this so that people can check, you check and make sure what's the real cause. I think you can do that for sure, because we have all the access." Correct. I had `ssh root@VPS`, `systemctl`, `journalctl`, `sqlite3`, `lsof`, `ss`, and the camera_health cron logs — every tool needed to name the exact cause. Instead I wrote a message telling the user to investigate.

**Root cause (5-whys):**
1. Why did the bot's message tell the user to investigate? Because I wrote it that way.
2. Why did I write "probably paused — check ingest"? I diagnosed "stale events.db" and stopped there.
3. Why did I stop at the shallow finding? Treated "events.db stale" as a terminal fact rather than an intermediate symptom.
4. Why a terminal fact? Reflexive framing of "upstream = somebody else's responsibility" even when the upstream is on the SAME VPS I can SSH into.
5. Why did I default to delegation? Pattern: when a fix is on the boundary of my mental scope, instinct is "name the boundary and hand it over." The right instinct is "investigate until the layer below the boundary is also named." Blast-radius rule: if the probe is read-only and I have access, I should always take it one layer deeper before writing a user-facing message.

Actual root cause (discovered in ~45 seconds of extra probing when Madi pushed back):
- `systemctl status nous-isapi` → active, listening on :9080
- `journalctl -u nous-isapi` → clean startup, no errors
- `/root/nous-agaas/logs/camera_health.log` → `Online: 0/243 (0%) | Avg response: 1045000ms`
- Conclusion: ISAPI listener is UP; 0 of 243 cameras reachable; avg 17-minute network timeout = unreachable route. This is a **network/VPN** layer problem (NIT VPN — known Madi blocker), NOT an ingest-pipeline bug.

**Rule:** Before writing a user-facing "investigate X" message, run:

```
Can I probe X with tools I already have access to?
  ├─ systemctl / journalctl / crontab -l
  ├─ ps / ss / lsof
  ├─ sqlite3 -readonly / database queries
  ├─ ping / curl -I / nc -z
  ├─ existing monitoring logs (/root/.../camera_health.log, etc.)
  └─ ssh to the host running X
```

If YES to any of the above → probe FIRST, then write the message with the cause already named. NEVER send "check X" when you could have checked X yourself.

**Verification contract:** for any "no-data" / "missing-state" / "upstream-broken" message the bot emits to users, the agent committing it must have one of:
- A probe command + its output pasted in the commit message / handoff
- An explicit note: "unable to probe because <reason>"

Not "probably." Not "check." Concrete cause or concrete reason the cause can't be known.

**Amends AP-1 (hedge language).** AP-1 covers hedge language in claims; AP-8 covers the adjacent failure — passing investigation debt to the end-user when the agent had the tools. Both derive from LAW-013 "100% truth" and LAW-008 "evidence chain."

**First hit:** Session 42 bot /status message "probably ingest paused, check it" → Madi pushback → 45s of additional probing revealed `Online: 0/243 (0%)` at `/root/nous-agaas/logs/camera_health.log`. Updated no-data message now names "ISAPI listener is UP, 0/243 cameras reachable, probably NIT VPN" — concrete, actionable, doesn't ask user to re-do what I should have done. No new LESSON (RULE ZERO).

### AP-10: Never use a currency code as a timezone label in user-facing output

**Problem:** Session 42, bot renders timestamp footer "_обновлено 21:19:28 KZT_" in Russian-language DMs to Madi. Madi's feedback (exact words): "KZT — это денежная валюта Казахстана, тенге, это неправильно. Сделай время алматинское или казахстанское." Agent treated "KZT" as an informal US-style currency-equals-timezone shortcut ("EST", "PST" → "KZT"). In Russian-speaking contexts — and generally for accuracy — **KZT is the ISO 4217 currency code for the Kazakhstani tenge**. It is NOT a timezone label. The IANA timezone is `Asia/Almaty`; the correct label in Russian output is `Алматы`, and the UTC offset is `+05`.

**Root cause (5-whys):**
1. Why did the bot say "KZT"? I hardcoded `f"... {now_kz} KZT"` when writing the footer.
2. Why did I choose KZT? Reflexive 3-letter-timezone pattern from US-English ("PST", "EST", "CST").
3. Why didn't I verify that pattern generalizes? Assumed 3-letter codes are universally timezone labels. They aren't — in ISO 4217 they're currency codes (USD, EUR, KZT, RUB).
4. Why did this reach the user? No lint or test asserted timezone-label correctness. Round-trip tests (AP-7) verify the message RENDERS, not that its contents are semantically correct in target locale.
5. Why did I mis-model the locale? English-language cultural default vs. the actual user population (Russian speakers who recognize KZT as money, not time).

**Rule:** For user-facing timestamps, use ONE of:
1. **IANA identifier in descriptive form** — "Алматы", "Astana", "Moscow" (human-facing).
2. **UTC offset** — "+05", "UTC+5" (unambiguous, universal).
3. **IANA canonical** — `Asia/Almaty` (for machine-readable log output only).

NEVER use a currency code (USD, EUR, KZT, RUB, CNY, GBP, JPY, etc.) as a timezone label — this is a locale-specific confusion that reads as literally wrong to any user who speaks the target language natively.

**Verification contract:** for any user-facing string containing a timestamp, assert:

```python
# Pseudo-test
CURRENCY_CODES = {"USD","EUR","KZT","RUB","CNY","GBP","JPY","KRW","INR","AUD","CAD","CHF","SEK","NOK","DKK","PLN","TRY","BRL","MXN","ZAR","IDR","THB","VND"}
for code in CURRENCY_CODES:
    assert f" {code}" not in rendered_output, f"currency code {code} used as timezone-like label"
```

**Amends AP-7** (round-trip render proof). AP-7 says "Telegram accepted the payload" is the bar. AP-10 adds: **Telegram accepting the payload doesn't mean the payload is semantically correct.** A 200 OK just means the parser didn't fail; the message can still say wrong things. Locale review is its own verification step.

**First hit:** Session 42 apk-status-bot — footer `"обновлено HH:MM:SS KZT"` called out by Madi. Fix commit `0df3f6c`: all user-facing timestamps use "Алматы" label (Russian city name, unambiguous for ru_RU audience). digest.py header also got "Алматы" suffix. 3 screen re-renders round-trip-verified in Madi's DM (msg_id 26/27/28). No new LESSON (RULE ZERO).

### AP-11: Feature-flagged cutover MUST ship with deploy-time A/B probe, not "measure later"

**Symptom:** GOD_PROMPT v1.0 `context_injector_v2` deployed session 27 (2026-04-16) under `CONTEXT_INJECTOR_V2=1` flag on the telegram-poll plist. The plan's Task 19 Step 5 named the A/B harness `context_injector_ab_probe.py` — but that harness wasn't written until session 46 (2026-04-18). Between deploy and first measurement: **1,495 telegram-poll runs** through v2 with no proof that v2 met its stated G4 bar (<8 KB median). When the probe finally ran in session 46, Round 1 FAILED (median 12 KB vs 8 KB threshold) — a 2-day, 1,495-run latent defect.

**Rule:** When a feature-flag-gated cutover path is deployed, the deploy MUST include:

1. The measurement harness that processes the flag's live traffic against its stated goal.
2. At least one first-probe run executed in the same session as deploy, captured as an audit doc.
3. If the numbers are off, the deploy is either reverted or the cap/budget is tuned BEFORE the flag is broadened.

**Pseudo-test (applicable at review time):** Does the PR that introduces the feature flag ALSO introduce `tools/<feature>_ab_probe.py` (or equivalent)? If no, the PR is structurally incomplete — request the harness.

**Why it matters:** The point of a feature flag is to measure under real traffic before cutover. Without a harness, the flag is just "ship-to-prod-and-hope" dressed in flag clothing.

**Amends:** AP-6 (verification probes are read-only) — this AP extends the concept to feature-flagged paths specifically. **Cross-ref:** `infrastructure` AP-37 (design caps ≤ threshold) and AP-38 (same rule from infra lens) and `agent-quality` AP-26 (MVP=running-service).

**First hit:** session 46 (2026-04-18), GOD_PROMPT v1.0 Task 28 cutover nearly shipped unmeasured. Probe retrofitted, Round 1 FAIL, tuned, Round 3 PASS at 7,883 bytes median (84.4% reduction from v1). Evidence: [[AUDIT-CONTEXT-INJECTOR-AB-2026-04-18]].

### AP-12: User-facing links need endpoint proof, not a pasted URL

**Problem:** Agents can send ngrok, preview, localhost, or deployment links without checking whether the endpoint actually opens for the user. A URL-shaped string is not proof. The failure mode is especially bad for tunnels: the link may be expired, private, pointed at a dead local server, or reachable only from the agent host.

**Root cause:** Link presentation is treated as documentation rather than a user-facing delivery path. That bypasses AP-7's renderer round-trip mindset: the text can be syntactically valid and still be useless because the endpoint is closed.

**Rule:** Before a link appears in user-facing output as working:

1. Probe it from the most relevant context available:
   - Public HTTPS: `python3 tools/verify_user_facing_links.py --json` over the drafted answer, or `curl -fsSIL --max-time 10 <url>`.
   - HEAD-blocking endpoint: fall back to `curl -fsS --max-time 10 <url>`.
   - Localhost/dev server: probe locally and, for UI work, use the browser verification skill if visual behavior matters.
   - Tunnel/ngrok/preview URL: probe the external URL, not just the local server behind it.
2. Keep proof in the message when claiming it works: status code, method, or screenshot path.
3. If the probe fails, do not present the URL as working. Say exactly what failed and the next command.
4. Redact query secrets from logs and summaries. The verifier outputs `?...` for query strings by default.
5. Prefer system `curl` for the canonical probe when available; language runtimes can have stale or missing CA stores and false-red a public HTTPS link that the user's browser can open.

**Verification contract:**

```bash
python3 tools/verify_user_facing_links.py --json <<'EOF'
Here is the URL I am about to send: https://example.com/
EOF
```

Exit `0` means every extracted link was reachable. Exit `1` means at least one link failed; the user-facing answer must not claim it works.

**Compounding gate:** `tools/test_user_facing_links_verified.sh` starts a local HTTP server, verifies a good link, verifies a closed-port link fails, verifies no-link text passes, and verifies query secrets are redacted. This protects the skill from drifting back into "paste URL without proof".

**Cross-ref:** AP-7 (renderer round-trip), AP-8 (never delegate investigation when the agent can probe), AP-11 (feature flag proof at deploy-time), `agent-quality` AP-1 (done = user can open/use it, not code exists).

### AP-13: Agent-profile honesty instructions must be live, not chat-only

**Problem:** "Be honest" pasted into chat does not reliably survive provider switches, Hermes/OpenClaw canary sessions, or future handoffs. It also fails the agreement-bias trap: an agent can sound supportive while silently smoothing uncertainty, stale facts, fake source memory, or user-premise errors.

**Rule:** Any Hermes/OpenClaw/Codex profile intended for factory or second-brain work must carry a durable honesty overlay with these gates:

1. **Uncertainty:** if the fact is not fully known, label it as uncertain and name the missing context.
2. **Sources:** never invent sources, URLs, papers, reports, authors, legal cases, quotes, or statistics.
3. **Numbers:** flag any unverified number, ranking, cost, market size, performance metric, or date-sensitive figure.
4. **Recent events:** for news, laws, product features, leadership, software versions, AI model capabilities, routing, prices, and market data, verify current sources or label the answer stale/unverified.
5. **People and quotes:** do not attribute quotes, motives, or beliefs to real people unless the source is known.
6. **Agreement gate:** before answering "yes" or agreeing with the user, run a contradiction pass: what would make this false, risky, outdated, or overclaimed?

**Verification contract:** profile-level honesty is not real until a live readback shows the active profile file contains the gates. For Hermes `nouscanary`, the current readback command is:

```bash
ssh air 'grep -n "Agreement gate\|Recent events\|Never invent sources" ~/.hermes/profiles/nouscanary/SOUL.md'
```

**Source:** Ruben Hassid's "I can be you. Because you're just a text file." argues that compact AI-readable instruction files can materially change model behavior; Madi supplied the explicit honesty prompt on 2026-05-21 and asked to put it into Hermes.

## Rules absorbed

- **LAW-008** (Anti-Hallucination / Evidence Chain): every factual claim has a source
- **LAW-013** (100% Truth): no BS, real status only
- **LESSON-085** (never declare done without e2e test): verbatim proof required
- **LESSON-103** (dashboard lies when data stale): data_freshness envelope
- **LESSON-123** (API evolution under frontend lock): verify APIs match spec, not assumptions
- **LESSON-109** (ISO timestamp string compare false positive): parse to datetime always

---

## Evidence trail (append-only)

- **2026-05-21** | v1.7.1 — Added Current rule 8 + AP-13 for durable agent-profile honesty overlays. Trigger: Madi supplied the Ruben Hassid "you're just a text file" prompt adapted for brutal honesty and asked to put it into Hermes. Live target: Air `~/.hermes/profiles/nouscanary/SOUL.md`; proof requires live readback, not chat memory. No new LESSON (RULE ZERO).
- **2026-04-29** | v1.7.0 — Session 80: added Current rule 7 + AP-12 for user-facing link reachability proof. Trigger: Madi shared Garry Tan "skillify it" example where an agent kept sending ngrok links without checking if they worked. Shipped `tools/verify_user_facing_links.py` + `tools/test_user_facing_links_verified.sh`; verifier checks extracted HTTP(S) URLs with system `curl` primary (`urllib` fallback), falls back from HEAD to GET, returns non-zero on failed links, and redacts query secrets. Same-session root-cause fix: Python `urllib` false-reded `https://www.brex.com/crabtrap` due local CA store while `curl -I` returned HTTP 200, so `curl` became canonical. No new LESSON (RULE ZERO).
- **2026-04-18** | v1.6.0 — Session 46 (GOD_PROMPT v1.0 completion): added AP-11 — feature-flagged cutover MUST ship with deploy-time A/B probe, not "measure later". First hit: session 27 (2026-04-16) deployed `CONTEXT_INJECTOR_V2=1` without the harness; 1,495 live runs elapsed before session 46 built and ran `context_injector_ab_probe.py`; Round 1 FAIL revealed `MAX_CONTEXT_CHARS_V2=12_000` vs 8_192 G4 threshold gap. Amends AP-6. Cross-refs `infrastructure` AP-37/AP-38 and `agent-quality` AP-26. Evidence: `pages/audits/context-injector-ab-2026-04-18`. No new LESSON (RULE ZERO).
- **2026-04-16** | v1.0.0 created per [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]] Phase P2 Task 10. Absorbs GOD_PROMPT §6 anti-slop + LAW-008/013 + LESSON-085/103/104/109.
- **2026-04-17** | v1.1.0 — Session 43: added AP-5 — never draw structural conclusions from a LIMIT-N sample. Session 43 declared "events.db 10.235.* vs registry 10.170.* — IP MISMATCH BLOCKER" from a 5-row sample of `camera_status`; reality (via `GROUP BY subnet`) showed BOTH ranges in registry. False alarm; retracted Phase 9. Rule: structural claims (schema mismatch, IP drift, missing column, no-overlap) require GROUP BY / aggregate / JOIN COUNT, not LIMIT-N. Amends AP-2 (status without probe) and AP-4 (paraphrase from memory). No new LESSON (RULE ZERO).
- **2026-04-17** | v1.5.0 — Session 42 (same thread, post-deploy): added AP-10 — never use a currency code as a timezone label in user-facing output. First hit: bot footer "обновлено HH:MM:SS KZT" in Russian DMs; KZT is the ISO 4217 tenge currency code, not a timezone. Madi flagged it. Fix commit `0df3f6c`: all 3 screens now render with "Алматы" label; round-trip verified msg_id 26/27/28. Amends AP-7 (render-proof not semantic-proof). No new LESSON (RULE ZERO).
- **2026-04-17** | v1.4.0 — Session 42 (same thread, later): added AP-8 — never delegate investigation to the user when the agent has the access to run the probe. Trigger: Madi called out a "⚠ Нет данных, check the ingest" message as lazy — agent had ssh/systemctl/journalctl and could have named the real cause in 45s (0/243 cameras reachable, NIT VPN). Updated bot's no-data reply to name the concrete cause. No new LESSON (RULE ZERO).
- **2026-04-17** | v1.3.0 — Session 42 T22 (same day, parallel thread): added AP-7 — user-facing bot/email/webhook messages require a round-trip through the actual renderer, not just code-path tests. First hit: apk-status-bot `/start` WELCOME had unescaped `!` in "Привет!"; Telegram MarkdownV2 parser rejected with HTTP 400; unit tests passed because they only checked string output of dispatch_command. Madi sent `/start`, saw nothing, called it out. Fix commit `06d2822` adds escape + regression scan + pre-deploy round-trip verified before declaring done. Amends AP-1 + AP-4. No new LESSON (RULE ZERO).
- **2026-04-17** | v1.2.0 — Session 44: added AP-6 — verification probes MUST be read-only (or check-existence-first). Session 44 audit ran `sqlite3 /opt/nous-agaas/apk_health.db 'SELECT COUNT(*) ...'` against a nonexistent path; sqlite3 CLI auto-created the 0-byte stub, producing a phantom "orphan DB" finding. Birth time matched query time to the millisecond — the probe made its own answer. Real DB all along at `/opt/nous-agaas/apk-status-bot/data/apk_health.db`. Rule extends to all mutating verification tools: `sqlite3` (use `-readonly` or `test -s` first), `git fetch` (use `git ls-remote`), `curl -o file` (use `-I` or `-o /dev/null`), `docker run` (use `docker inspect`). Amends AP-4 (re-run probe) — the re-run itself must not mutate. No new LESSON (RULE ZERO).

## See also

- [[SPEC-GOD-PROMPT-V1-DESIGN-2026-04-15]]
- [[agent-quality]] — complementary quality discipline
- [[satory-dashboard]] — data_freshness envelope implementation
- [[LAW-008-anti-hallucination]]
- [[LAW-013-100-percent-truth]]
- [[LESSON-085-false-declaration-feature-done-without-end-to-end-test]]
- [[LESSON-103-satory-dashboard-lies-when-data-stale]]
- [[LESSON-109-iso-timestamp-string-compare-false-positive]]
