---
type: prompt
id: GOAL-sonnet-factory-100-closeout-2026-05-12
title: "Sonnet Goal Prompt: Factory 100% Closeout"
tags: [prompt, goal-mode, sonnet, factory, openrouter, todoist, openbrain, gbrain, openclaw, handoff]
date: 2026-05-12
status: active
last_updated: 2026-05-12
related: [handoff-codex-openrouter-todoist-openbrain-2026-05-12, handoff-auto-2026-05-12-10-50, factory-ops, session-operating-contract]
---

# Sonnet Goal Prompt: Factory 100% Closeout

Copy/paste everything below into Claude Sonnet / Claude Code. It is written as a goal-mode command: work until the stop condition is met, or stop only on a real blocker that requires Madi's account-side action.

**Scope:** This is a **one-shot closeout**, not a continuous monitor. The session walks gates 1-8 once, writes a final handoff, and stops with `DONE` or `BLOCKED`. For continuous monitoring, use a launchd job (e.g. `com.nous.factory-pulse`), not an interactive `/goal` session — agents in chat sessions cannot meaningfully sleep between pulses.

**Codex review (2026-05-12) applied:** Step 6 gbrain check now classifies cosmetic warnings (e.g. `resolver_health`) separately from real failures; exit criterion 6 accepts `status=healthy OR (status=warnings AND only cosmetic checks are non-ok)`.

```text
/goal

You are Claude Sonnet operating in Nous AGaaS Goal Mode.

Mission:
Close the Nous AGaaS factory residual loop to a verifiable 100% state for 2026-05-12. Do not stop at summaries. Verify the runtime truth, repair drift if found, save the proof into the Obsidian/wiki/gbrain substrate, and stop only when every exit criterion below is met or when a hard external blocker requires Madi's action.

Operator standard (billion-dollar-solopreneur / Musk + Karpathy/Tan + Nate B Jones lineage):
- No lies, no vibes, no "probably". Evidence-first; surface bad news loudly. (Musk: "physics doesn't care".)
- **Musk Algorithm in order:** (1) question every requirement — who signed it, by name; (2) DELETE unnecessary work / parts / processes — if you do not add ≥10% back later, you deleted too little; (3) simplify only the remainder; (4) accelerate only the simplified remainder; (5) automate ONLY LAST. Most agents break this order. See `pages/skills/musk-algorithm/SKILL.md` v1.3.0; mechanical detector at `tools/test_musk_step_2.sh`.
- **Karpathy / Garry Tan / Alex Finn substrate doctrine:** skills ARE the prompts. New reusable failure mode → update `pages/skills/<skill>/SKILL.md` (3-edit ritual: frontmatter version + H1 version + Timeline) + `mcp__gbrain__add_timeline_entry`. NEVER create a new `LESSON-NNN-*.md` file — the pre-commit hook rejects it. Skills compound, lessons rot.
- **Nate B Jones / OpenBrain capture-first paradigm:** thought capture via whichever OpenBrain MCP `capture_thought` tool is exposed is the cheap front-door; projection runner (`tools/openbrain_project_to_wiki.py` + Air launchd `com.nous.openbrain-projection`) is the durable back-door into Obsidian. Gate 4 below verifies the back-door is alive; if a thought is captured but not projected/visible/retrievable from gbrain + OpenClaw, the capture didn't happen (library-grade definition).
- **Library-grade test (used in Gate 6):** every page is linked, synchronized across Mac/Air/VPS/VPS-bare, has a clear title, and is retrievable via gbrain semantic query at score ≥0.85 within 5 minutes of landing. See `pages/skills/library-grade-audit/SKILL.md` v1.4.0 for the 7-gate falsifiable scorecard and 7-class debugging tree.
- Surgical changes only. Do not sweep unrelated dirty files (Karpathy AP-3).
- Work one gate at a time, but do not ask Madi tactical questions you can answer with evidence (NO-DEFER rule, `ceo-hierarchy` v1.1.0).

Start ritual:
1. `cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous"`
2. Read:
   - `../AGENTS.md`
   - `pages/skills/session-operating-contract/SKILL.md`
   - latest `pages/progress/HANDOFF-AUTO-*.md`
   - `pages/progress/HANDOFF-CODEX-OPENROUTER-TODOIST-OPENBRAIN-2026-05-12.md`
   - this prompt file: `pages/prompts/GOAL-sonnet-factory-100-closeout-2026-05-12.md`
3. Register your lane before writes. The env vars must be on the same logical line as the script call (use `\` line continuation), otherwise they are NOT exported to the child process:
   ```bash
   SESSION_INTENT="sonnet goal-mode factory 100 closeout verification + repair" \
   SESSION_SCOPE="pages/progress/,pages/prompts/,pages/audits/,pages/skills/,tools/,air:~/nous-agaas/,vps:/opt/nous-agaas/gbrain" \
   bash tools/session_self_register.sh --force
   ```
4. Run:
   ```bash
   bash tools/session_scan.sh
   ```
   Confirm no scope collision. If another lane owns the same file, do not edit that file; choose a new handoff file.

Known prior baseline (DO NOT trust the exact hash — verify live in Gate 1):
- 4-way HEAD parity was green a few minutes before this prompt was written.
- OpenRouter `Nous AGaaS` was capped at $5/day, `open-brain` at $1/day, both `disabled=false`.
- Todoist Satory had 0 active tasks missing owner signal.
- OpenBrain projection dry-run had `would_create=0`, `would_update=0`.
- OpenClaw Docker was healthy.
- gbrain doctor reported healthy state.

Re-run every gate below from scratch. Treat the bullets above as context only.

Step 1 — Sync/parity gate.
Run:
```bash
MAC=$(git -C "/Users/madia/Documents/Projects/Nous AGaaS/Nous" rev-parse HEAD)
AIR=$(ssh air 'cd ~/nous-agaas/wiki && git rev-parse HEAD' 2>/dev/null)
VPS_W=$(ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && git rev-parse HEAD' 2>/dev/null)
VPS_B=$(ssh root@65.108.215.200 'git --git-dir=/root/nous-agaas/obsidian-wiki.git rev-parse main' 2>/dev/null)
printf 'MAC=%s\nAIR=%s\nVPS_W=%s\nVPS_B=%s\n' "$MAC" "$AIR" "$VPS_W" "$VPS_B"
[ "$MAC" = "$AIR" ] && [ "$MAC" = "$VPS_W" ] && [ "$MAC" = "$VPS_B" ] && echo PARITY=GREEN || echo PARITY=RED
```
If red:
- inspect dirt with `git status --short` on Mac/Air/VPS working copies.
- use `git pull --ff-only` only when the working copy is clean.
- never reset or checkout user changes.
- verify parity again.

Step 2 — OpenRouter spend-cap gate.
Do not print secrets. Load keys from `/Users/madia/Documents/Projects/Nous AGaaS/.env`.
Verify both runtime key and management list:
```bash
python3 - <<'PY'
from pathlib import Path
import os, subprocess, json, tempfile
p=Path('/Users/madia/Documents/Projects/Nous AGaaS/.env')
for line in p.read_text(errors='ignore').splitlines():
    if not line.strip() or line.lstrip().startswith('#') or '=' not in line:
        continue
    k,v=line.split('=',1)
    if k in ('OPENROUTER_API_KEY','OPENROUTER_MANAGEMENT_KEY'):
        os.environ[k]=v.strip().strip("'\"")
def curl_json(url, token):
    tmp=tempfile.NamedTemporaryFile(delete=False); tmp.close()
    cp=subprocess.run(['curl','-sS','-o',tmp.name,'-w','%{http_code}','-H','Authorization: Bearer '+token,'-H','Accept: application/json',url], text=True, capture_output=True, timeout=30)
    body=Path(tmp.name).read_text(errors='ignore')
    try: data=json.loads(body)
    except Exception: data={'raw': body[:500]}
    return cp.stdout, data
cur_s, cur = curl_json('https://openrouter.ai/api/v1/key', os.environ.get('OPENROUTER_API_KEY',''))
keys_s, keys = curl_json('https://openrouter.ai/api/v1/keys', os.environ.get('OPENROUTER_MANAGEMENT_KEY',''))
out={'current_status':cur_s,'keys_status':keys_s}
if cur_s=='200':
    d=cur.get('data',cur)
    out['current']={k:d.get(k) for k in ['label','limit','limit_reset','limit_remaining','usage_daily','usage_monthly','disabled']}
if keys_s=='200':
    out['keys']=[{k:item.get(k) for k in ['name','label','limit','limit_reset','limit_remaining','usage','usage_daily','usage_monthly','disabled']} for item in keys.get('data',[])]
else:
    out['keys_error']=keys
print(json.dumps(out, ensure_ascii=False, indent=2))
PY
```
Pass condition:
- `keys_status=200`.
- `Nous AGaaS` has `limit=5`, `limit_reset=daily`, `disabled=false`.
- `open-brain` has `limit=1`, `limit_reset=daily`, `disabled=false`.
- current runtime key has `limit=5`, `limit_reset=daily`.

If any OpenRouter key is uncapped:
- use `python3 tools/set_openrouter_cap.py`; do not hand-roll PATCH unless necessary.
- for `Nous AGaaS`, cap is `$5/day`.
- for `open-brain`, cap is `$1/day`.
- always send both `limit` and `limit_reset=daily`; never send `limit` alone.
- verify again with `/api/v1/keys` and `/api/v1/key`.

Step 3 — Todoist hygiene gate.
Run the Air truth path with EXPLICIT env path (do not rely on the script's
fallback chain — fail loud if env missing):
```bash
ssh air 'cd ~/nous-agaas/wiki && python3 tools/todoist_review_owner_labels.py --env-file /Users/madia/nous-agaas/.env'
```
Pass condition:
- `Total active tasks: 122` or current truthful count.
- `Tasks missing owner signal: 0`.

If local Mac direct run fails because local env lacks Todoist token, do not mark Todoist red. Use Air path as source of truth.
If Air path finds missing owner labels:
- do not mutate blindly.
- create an explicit scoped repair plan listing task IDs and proposed owner labels.
- apply only if owner can be inferred from existing task labels/content or Madi explicitly approves.
- read back after mutation.

Step 4 — OpenBrain projection gate.

**Primary truth: the Air projection dry-run below.** OpenBrain MCP tool names (e.g. `mcp__bf0b333e-...__thought_stats`) are server-instance-specific and can rotate — never rely on a specific MCP tool name as the green signal. If an OpenBrain MCP tool happens to be exposed in your session, treat its output as a bonus cross-check, not the primary gate.

Run:
```bash
ssh air 'cd ~/nous-agaas/wiki && python3 tools/openbrain_project_to_wiki.py --dry-run'
ssh air 'launchctl list | grep -i openbrain || true; tail -80 ~/nous-agaas/logs/openbrain-projection/*.log 2>/dev/null | tail -120'
```
Pass condition:
- dry-run returns `ok=True`.
- `would_create=0`.
- `would_update=0`.
- launchd `com.nous.openbrain-projection` exists.
- recent logs show no unhandled projection failure.

If projection finds new real thoughts:
- apply the projection runner, not GitHub Contents API.
- verify files land in `pages/inbox/openbrain/...`.
- sync to gbrain and query by content.

Step 5 — OpenClaw / LiteLLM / factory gate.
Run:
```bash
ssh air 'docker ps --filter name=openclaw --format "{{.Names}} {{.Status}}"; launchctl list | grep -E "com.nous.(litellm|telegram-poll|auto-checkpoint|litellm-cost-alarm|openbrain-projection)" || true'
```
Pass condition:
- `openclaw` is `healthy`.
- `com.nous.telegram-poll`, `com.nous.auto-checkpoint`, `com.nous.litellm-cost-alarm`, and `com.nous.openbrain-projection` are listed.
- LiteLLM has a live PID or a clearly healthy launchd state. If launchctl shows old `-15`, interpret it as last exit only after confirming current process/port.

If LiteLLM is not running:
- inspect logs before restarting.
- restart with the existing launchd service only.
- verify port/model route after restart.

Step 6 — gbrain / Obsidian retrieval gate (library-grade definition).
This gate is the "retrieval like a library" check from `pages/skills/library-grade-audit/SKILL.md` v1.4.0 Gate 6. Always `cd /opt/nous-agaas/gbrain` first so config loads correctly. Run:
```bash
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain doctor --json'
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain query "Sonnet Goal Prompt Factory 100 Closeout OpenRouter Todoist OpenBrain" --no-expand | head -20'
```
Pass condition (classified):
- **Green:** `status=healthy` AND `health_score=100` AND embeddings `100% coverage, 0 missing`.
- **Green-with-cosmetic-warning:** `status=warnings` AND `health_score >= 95` AND the ONLY non-ok checks are in the cosmetic set `{resolver_health, frontmatter_lint_warnings}`. Acknowledge the cosmetic warning in the handoff. Do not block.
- **Red (requires fix):** Any other non-ok check — embedding miss, btree corruption, FTS broken, sync_failed, schema mismatch. These need repair before exit.
- This prompt or the final handoff is retrievable via gbrain semantic query.

Cosmetic-vs-real classifier (`cd` first into the gbrain dir so config loads correctly):

A check is "cosmetic" ONLY when ALL of these are true:
1. It is already documented as cosmetic in a previous handoff or relevant skill AP.
2. It does NOT mention any of: `sync_failures`, `embeddings`, `schema_version`, `frontmatter_integrity`, `connection`, `pgvector`, `queue_health`.
3. The detail message does not include words like "missing", "corrupt", "stale", "broken", "drift".

If any of those three conditions fail, treat the check as RED.

```bash
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain doctor --json' | python3 -c "
import sys, json
d = json.load(sys.stdin)
REAL_KEYWORDS = ('sync_failures', 'embeddings', 'schema_version', 'frontmatter_integrity', 'connection', 'pgvector', 'queue_health')
RED_FLAGS = ('missing', 'corrupt', 'stale', 'broken', 'drift', 'failed', 'error')
DOCUMENTED_COSMETIC = {'resolver_health'}  # only with explicit prior handoff acknowledgement

non_ok = [c for c in d.get('checks', []) if c.get('status') != 'ok']
real = []
cosmetic = []
for c in non_ok:
    name = c.get('name', '')
    msg = (c.get('detail') or c.get('message') or '').lower()
    is_documented = name in DOCUMENTED_COSMETIC
    has_real_keyword = any(k in name.lower() for k in REAL_KEYWORDS)
    has_red_flag = any(k in msg for k in RED_FLAGS)
    if is_documented and not has_real_keyword and not has_red_flag:
        cosmetic.append(name)
    else:
        real.append((name, msg[:120]))

if not non_ok:
    print('GREEN')
elif not real:
    print(f'GREEN_COSMETIC: {cosmetic} (must be acknowledged in handoff)')
else:
    print(f'RED: {real}')
    sys.exit(1)
"
```

If you need to sync/embed:
```bash
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain sync --source wiki'
ssh root@65.108.215.200 'set -a; . /root/.gbrain/openai-compatible.env; set +a; cd /opt/nous-agaas/gbrain && bin/gbrain embed --stale'
```
Never run manual `bin/gbrain embed --stale` without sourcing `/root/.gbrain/openai-compatible.env`; that known failure produces `OPENAI_API_KEY missing`.

Step 7 — If a new reusable failure mode is found.
Follow RULE ZERO:
- update the closest `pages/skills/<skill>/SKILL.md`;
- bump version in frontmatter and H1;
- add timeline/evidence entry in that skill;
- add gbrain timeline entry for the same skill page;
- commit only the scoped skill change.
Do not create a new LESSON file.

gbrain timeline entry — prefer MCP, fall back to CLI:
```
# Primary (MCP):
mcp__gbrain__add_timeline_entry  slug="pages/skills/<skill>/skill"  date="2026-05-12"  summary="..."

# Fallback if MCP unavailable:
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain timeline-add pages/skills/<skill>/skill 2026-05-12 "<summary>"'
```
Commit message MUST include `gbrain-timeline-ok: <slug>` trailer (or `gbrain-timeline-deferred: <reason>` for explicit bypass).

Step 8 — Final handoff.
Write a new handoff file:
`pages/progress/HANDOFF-SONNET-GOAL-FACTORY-100-CLOSEOUT-2026-05-12.md`

It must include:
- exact commands run;
- exact important outputs;
- current OpenRouter key caps;
- Todoist count and missing-owner count;
- OpenBrain dry-run summary;
- OpenClaw/LiteLLM launchd status;
- gbrain doctor summary and retrieval query;
- 4-way HEAD parity;
- git status;
- residuals, if any, with exact owner/action.

Commit and sync:
```bash
git add pages/progress/HANDOFF-SONNET-GOAL-FACTORY-100-CLOSEOUT-2026-05-12.md
git commit -m "Add Sonnet factory 100 closeout handoff" -- pages/progress/HANDOFF-SONNET-GOAL-FACTORY-100-CLOSEOUT-2026-05-12.md
git push vps main
ssh air 'cd ~/nous-agaas/wiki && git pull --ff-only origin main'
ssh root@65.108.215.200 'cd /root/nous-agaas/wiki && git pull --ff-only bare main'
# (VPS working copy remote is named `bare`, not `origin`. Confirm with `git remote -v` if unsure.)
```

Then sync gbrain:
```bash
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain sync --source wiki'
ssh root@65.108.215.200 'set -a; . /root/.gbrain/openai-compatible.env; set +a; cd /opt/nous-agaas/gbrain && bin/gbrain embed --stale'
ssh root@65.108.215.200 'cd /opt/nous-agaas/gbrain && bin/gbrain query "Sonnet factory 100 closeout handoff OpenRouter Todoist OpenBrain" --no-expand | head -20'
```

**Known race (gbrain HEAD-drift):** if `bin/gbrain sync` reports a `sync_failures: ... at <hash>` entry, first verify (a) live 4-way HEAD parity is GREEN, (b) `bin/gbrain get <handoff-slug>` returns the new content, (c) `bin/gbrain doctor` shows 100% embeddings and the page is retrievable via semantic query at score ≥0.85. Only then acknowledge the HEAD-drift entry in the final handoff with an explicit provenance reason ("sync ran at <T0>, commit landed at <T0+dt>, content verified retrievable at <T1>"). Do NOT acknowledge real file parse / frontmatter / pgvector / schema failures the same way — those need repair, not a footnote. See `gbrain-ops` AP family for the underlying race and `openbrain-projection` AP-5 for the embed-without-env failure mode.

Exit criteria. You may stop only when all are true:
1. Mac/Air/VPS working copy/VPS bare HEAD parity is GREEN.
2. OpenRouter `Nous AGaaS` and `open-brain` keys both have daily caps and are not disabled.
3. Todoist Satory owner-label missing count is `0`.
4. OpenBrain projection dry-run has `would_create=0` and `would_update=0`.
5. OpenClaw is healthy and required launchd services are visible.
6. gbrain doctor is GREEN or GREEN_COSMETIC per the classifier in Step 6 (cosmetic warnings explicitly acknowledged in the handoff).
7. Final Sonnet handoff exists in Obsidian/wiki and is retrievable through gbrain semantic query.
8. Git status has no uncommitted changes from your work. Any unrelated dirty files must be listed and not swept.

If a hard blocker remains, stop with:
- `BLOCKED`;
- exact command;
- exact output;
- why it cannot be fixed from this session;
- what Madi must do;
- what is already safe/green.

Do not end with "let me know if you want me to continue." Continue until the exit criteria are met or blocked.
```

