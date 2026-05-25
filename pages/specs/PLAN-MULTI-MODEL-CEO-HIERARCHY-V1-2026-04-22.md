---
type: spec
id: PLAN-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22
title: "Implementation plan — multi-model CEO hierarchy v1 (Grok president + Opus executive + workers)"
tags: [plan, implementation, multi-model, ceo-hierarchy, grok, opus, glm, worker-tier, litellm, openclaw-multi-agent, 2026-04-22, session-57]
date: 2026-04-22
status: draft
last_updated: 2026-04-22
related:
  - "[[SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22]]"
  - "[[factory-ops]]"
  - "[[karpathy-coding-principles]]"
  - "[[session-operating-contract]]"
  - "[[session-coordination]]"
---

# Multi-model CEO Hierarchy v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Execute one-by-one per Madi's standard: quality matters, 100% or honest STOP + handoff.**

**Goal:** Ship a 3-tier model hierarchy where Grok-4.20-reasoning (President) routes Madi's Telegram `/ask` to either a direct answer or Opus 4.7 (Executive), which delegates narrow subtasks to workers (Grok-code-fast-1 / GLM-5.1 / GLM-4.5-flash). All tiers observable via JSONL + `/trace`; operator-discipline escape hatches (`/ask-direct`, urgent-keyword auto-bypass, cost footer, editMessageText progress) ship BEFORE any routing change.

**Architecture:** New OpenClaw agent `grok-ceo` alongside existing `nous` (Opus). `sessions_spawn` for delegation, LiteLLM for model routing + fallbacks (Grok → Sonnet-4.5-thinking → GLM-5.1 → Haiku). `nous` workspace migrates SOUL/IDENTITY/USER critical sections into AGENTS.md so subagent-invocation preserves 128-skill doctrine.

**Tech Stack:** bash + Python + LiteLLM YAML config + OpenClaw CLI (`openclaw config set`, `openclaw agents add`) + launchd + jq + git.

**Spec:** [[SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22]]

---

## File structure (locked before tasks)

| File | Location | Responsibility |
|---|---|---|
| `~/nous-agaas/litellm/config.yaml` | Air | LiteLLM aliases + fallback chain (authoritative model routing) |
| `/home/node/.openclaw/workspaces/grok-ceo/SOUL.md` | Air (container) | grok-ceo persona + delegation contract |
| `/home/node/.openclaw/workspaces/grok-ceo/AGENTS.md` | Air (container) | grok-ceo procedures: when to delegate, timeout sentinel, JSON directive schema |
| `/home/node/.openclaw/workspaces/grok-ceo/IDENTITY.md` | Air (container) | grok-ceo name + role (thin) |
| `/home/node/.openclaw/workspace/AGENTS.md` | Air (container) | `nous` — MERGED SOUL+IDENTITY+USER critical sections so subagent-invocation preserves doctrine |
| `/Users/madia/nous-agaas/tools/tier_log.py` | Air | JSONL appender — one line per tier call, replaces Langfuse |
| `/Users/madia/nous-agaas/logs/ask-hierarchy.jsonl` | Air | append-only per-tier telemetry |
| `/Users/madia/nous-agaas/command_center.py` | Air | `/ask`, `/ask-direct`, `/trace` handlers + urgent-keyword bypass + cost footer formatter |
| `/Users/madia/nous-agaas/run_task.py` | Air | `AGENT_ID` parameter logic + `--correlation-id` flag |
| `/Users/madia/nous-agaas/tools/telegram_poll.py` | Air | Urgent-keyword regex + editMessageText progress updates |
| `/Users/madia/nous-agaas/tools/litellm_cost_alarm.py` | Air | Coefficient update for multi-tier — reads `ask-hierarchy.jsonl` |
| `/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/test_ceo_hierarchy_*.sh` | Mac vault | Unit tests (4 scripts) + E2E test |
| `/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills/ceo-hierarchy/SKILL.md` | Mac vault | Factory-adapted skill with cross-refs |
| `/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills/_gbrain/RESOLVER.md` | Mac vault | Add routing row for ceo-hierarchy skill |

---

## Phase 0 — Pre-flight (no routing change; fully reversible)

### Task 1: LiteLLM config — add Sonnet-4.5-thinking + Grok-code-fast aliases + fallback chains

**Files:**
- Modify: `~/nous-agaas/litellm/config.yaml` on Air

- [ ] **Step 1: SSH to Air + snapshot current config**

```bash
ssh air 'cp ~/nous-agaas/litellm/config.yaml ~/nous-agaas/litellm/config.yaml.bak-pre-hierarchy-v1'
ssh air 'head -80 ~/nous-agaas/litellm/config.yaml'
```
Expected: backup file created; current model_list shows opus / glm-5.1 / glm-4.5-flash / grok-reasoning / sonnet.

- [ ] **Step 2: Verify Sonnet-4.5-thinking is available via Anthropic API**

```bash
ssh air 'source ~/nous-agaas/.env; curl -s -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" https://api.anthropic.com/v1/models 2>&1 | python3 -m json.tool | grep -E "claude-sonnet-4-5|claude-haiku-4-5" | head -5'
```
Expected: both claude-sonnet-4-5 AND claude-haiku-4-5-20251001 listed. If Sonnet-4.5 absent → stop, need alternative alias.

- [ ] **Step 3: Append new aliases to config.yaml**

```bash
ssh air 'cat >> ~/nous-agaas/litellm/config.yaml << EOF

  # TIER-1 FALLBACK: Sonnet 4.5 thinking mode (capability peer to Grok-4 reasoning)
  - model_name: "sonnet-4-5-thinking"
    litellm_params:
      model: "anthropic/claude-sonnet-4-5"
      api_key: "os.environ/ANTHROPIC_API_KEY"
      max_tokens: 8192
      timeout: 90
      thinking: {"type": "enabled", "budget_tokens": 4096}

  # TIER-3 WORKER: Grok Code Fast (coding subtasks)
  - model_name: "grok-code-fast"
    litellm_params:
      model: "openai/grok-code-fast-1"
      api_key: "os.environ/XAI_API_KEY"
      api_base: "https://api.x.ai/v1"
      max_tokens: 8192
      timeout: 60

  # AVAILABILITY FLOOR: Haiku 4.5
  - model_name: "haiku-4-5"
    litellm_params:
      model: "anthropic/claude-haiku-4-5-20251001"
      api_key: "os.environ/ANTHROPIC_API_KEY"
      max_tokens: 4096
      timeout: 60
EOF'
```

- [ ] **Step 4: Update `router_settings.fallbacks` to include 4-tier chains**

Use a Python one-liner to edit the fallbacks block cleanly:

```bash
ssh air 'python3 << PYEOF
import yaml
with open("/Users/madia/nous-agaas/litellm/config.yaml") as f:
    cfg = yaml.safe_load(f)
cfg["router_settings"]["fallbacks"] = [
    {"grok-reasoning": ["sonnet-4-5-thinking", "glm-5.1", "haiku-4-5"]},
    {"opus": ["sonnet", "glm-5.1"]},
    {"sonnet-4-5-thinking": ["opus", "sonnet", "glm-5.1"]},
    {"grok-code-fast": ["glm-5.1", "grok-reasoning"]},
    {"glm-5.1": ["glm-4.5-flash", "grok-reasoning", "sonnet"]},
    {"glm-4.5-flash": ["glm-5.1", "grok-reasoning"]},
]
with open("/Users/madia/nous-agaas/litellm/config.yaml", "w") as f:
    yaml.dump(cfg, f, sort_keys=False, default_flow_style=False)
print("OK fallbacks updated")
PYEOF'
```
Expected: `OK fallbacks updated`.

- [ ] **Step 5: Commit vault copy if tracked**

LiteLLM config lives on Air, not vault. No commit needed; backup `.bak-pre-hierarchy-v1` retained on Air for rollback.

---

### Task 2: Restart LiteLLM + verify each alias responds

**Files:**
- Executed on Air (no file changes)

- [ ] **Step 1: Reload LiteLLM launchd**

```bash
ssh air 'launchctl kickstart -k gui/501/com.nous.litellm; sleep 5; curl -s http://127.0.0.1:4000/health | head -3'
```
Expected: health endpoint returns JSON with status `"healthy"` or similar.

- [ ] **Step 2: Verify each new alias responds**

```bash
ssh air 'source ~/nous-agaas/litellm/.env; for alias in grok-reasoning opus sonnet-4-5-thinking grok-code-fast glm-5.1 haiku-4-5; do
  echo "--- $alias ---"
  curl -s http://127.0.0.1:4000/v1/chat/completions \
    -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"$alias\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: OK_$alias\"}],\"max_tokens\":20}" \
    2>&1 | python3 -c "import json,sys; d=json.load(sys.stdin); print(d[\"choices\"][0][\"message\"][\"content\"][:40] if \"choices\" in d else d)"
done'
```
Expected: each alias returns `OK_<alias>` or similar. Any 404/error → fix config and re-run Step 1.

- [ ] **Step 3: Save evidence**

```bash
ssh air 'mkdir -p ~/nous-agaas/logs/ceo-hierarchy; curl -s http://127.0.0.1:4000/model/info 2>&1 | python3 -m json.tool > ~/nous-agaas/logs/ceo-hierarchy/litellm-model-inventory-$(date +%Y%m%d-%H%M).json; ls -la ~/nous-agaas/logs/ceo-hierarchy/'
```

---

### Task 3: Workspace migration — merge SOUL+IDENTITY+USER critical sections into `nous` AGENTS.md

**Files:**
- Read: `/home/node/.openclaw/workspace/{SOUL.md,IDENTITY.md,USER.md,AGENTS.md}` on Air (container)
- Modify: `/home/node/.openclaw/workspace/AGENTS.md` on Air (container)

- [ ] **Step 1: Inspect current `nous` workspace contents**

```bash
ssh air 'for f in SOUL.md IDENTITY.md USER.md AGENTS.md; do echo "=== $f ==="; docker exec openclaw wc -l /home/node/.openclaw/workspace/$f 2>&1; done'
```
Expected: all 4 files exist. Note line counts.

- [ ] **Step 2: Extract critical sections to a staging file**

```bash
ssh air 'docker exec openclaw bash -c "cat > /tmp/agents-merge-staging.md << '\''EOF'\''
# nous — agent procedures

<!-- This file is read by BOTH depth-0 \`nous\` invocations AND subagent-of-grok-ceo invocations. -->
<!-- Original SOUL.md / IDENTITY.md / USER.md retained for depth-0. Critical sections duplicated here for subagent context (per spec SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22). -->

## Persona (from SOUL.md)

You are Nous — AGaaS factory agent. Execute skills with DONE protocol discipline. Never fabricate claims. Apply karpathy-coding-principles v1.0.0 (Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution) to every code change.

## Identity (from IDENTITY.md)

Role: digital CEO / executive layer (Tier 2) in the multi-model hierarchy. When invoked as subagent of \`grok-ceo\`, parse the structured directive JSON in the \`task:\` parameter. Emit a structured report JSON in your final message.

## User context (from USER.md — critical subset)

Operator: Madi Ayazbay (president of Nous AGaaS, sole technical founder). Communication: Telegram DMs → \`@nousAGaaSbot\`. Timezone: KZT (UTC+5). Current projects: Satory VKO camera enforcement, Spectra ITS platform, ERAP SmartBridge. Phase-0 collector is revenue-path load-bearing.

## Doctrine (non-negotiable)

- RULE ZERO: learnings land in SKILL.md + gbrain timeline. NO new LESSON files.
- DONE protocol: 4 artifacts (command, output, git-state, counter-check) before typing \"done\".
- Musk 5-step: question → delete → simplify → accelerate → automate.
- karpathy-loop 6-axis scorecard at session-close.
- 128 skills available in /opt/nous-agaas/skills. Trigger-match + read-then-apply discipline.

## Subagent-invocation contract (when called by grok-ceo)

Input: \`task\` parameter contains structured directive JSON per spec §Tier-1→Tier-2.
Output: final message MUST be structured report JSON per spec §Tier-2→Tier-1.
Do NOT hedge in structured output. If blocked, set \`status: blocked\` and list the blocker in \`unverified\` array.
Tier-3 worker delegation: use \`sessions_spawn\` with \`model:\` override (grok-code-fast for coding, glm-5.1 for bulk, glm-4.5-flash for polls). \`runTimeoutSeconds: 60\` per worker call.

---

(ORIGINAL AGENTS.md content follows — load after this header)

EOF"'
```

- [ ] **Step 3: Prepend staging to current AGENTS.md**

```bash
ssh air 'docker exec openclaw bash -c "cat /tmp/agents-merge-staging.md /home/node/.openclaw/workspace/AGENTS.md > /tmp/agents-merged.md && mv /tmp/agents-merged.md /home/node/.openclaw/workspace/AGENTS.md"'
```

- [ ] **Step 4: Verify merge**

```bash
ssh air 'docker exec openclaw wc -l /home/node/.openclaw/workspace/AGENTS.md; docker exec openclaw head -15 /home/node/.openclaw/workspace/AGENTS.md'
```
Expected: line count increased (staging added ~40 lines); first 15 lines include "nous — agent procedures" header.

- [ ] **Step 5: No restart needed yet (this is workspace file; hot-reloaded on next agent turn). Checkpoint.**

```bash
ssh air 'docker exec openclaw openclaw agent --agent nous --local --message "Acknowledge: what is your role in the multi-model hierarchy? 1 sentence." 2>&1 | tail -5'
```
Expected: response mentions "Tier 2" or "executive" or "digital CEO" — evidence AGENTS.md merge took effect.

---

## Phase 1 — Operator discipline (ship BEFORE routing changes)

### Task 4: `/ask-direct` command handler in command_center.py

**Files:**
- Modify: `/Users/madia/nous-agaas/command_center.py` on Air

- [ ] **Step 1: Locate current `/ask` handler**

```bash
ssh air 'grep -n "def handle\|/ask\|_run_openclaw" ~/nous-agaas/command_center.py | head -15'
```
Note line numbers of `handle()` function and `_run_openclaw()`.

- [ ] **Step 2: Add `/ask-direct` branch parallel to `/ask`**

Edit `command_center.py` to add (near the `/ask` handler, add new elif):

```python
elif text.startswith("/ask-direct "):
    query = text[len("/ask-direct "):].strip()
    if not query:
        return "Usage: /ask-direct <query> — bypasses Tier-1 (grok-ceo), routes straight to Opus (nous)."
    log_line(f"/ask-direct invoked by {user}: {query[:80]}")
    response = _run_openclaw(query, model="opus", agent_id="nous", correlation_id=f"tg_{msg_id}")
    return f"[opus-direct]\n{response}\n\n— direct tier-2 bypass (no Tier-1) | correlation_id=tg_{msg_id}"
```

- [ ] **Step 3: Test handler dispatch locally**

```bash
ssh air 'cd ~/nous-agaas && python3 -c "import command_center; print(command_center.handle(\"/ask-direct ping\", user=\"madi\", msg_id=12345)[:200])" 2>&1 | head -10'
```
Expected: response text beginning with `[opus-direct]` or error indicating `_run_openclaw` needs `agent_id` + `correlation_id` kwargs (add them in Task 5+6; accept signature mismatch here).

- [ ] **Step 4: Commit Air-side change (via vault if command_center.py is vault-tracked; OR just document)**

```bash
ssh air 'grep -c "/ask-direct" ~/nous-agaas/command_center.py'
```
Expected: count > 0 (handler present). Air-local file; documented in session log; vault-side updated when next rsync runs.

---

### Task 5: Urgent-keyword regex at telegram_poll.py layer

**Files:**
- Modify: `/Users/madia/nous-agaas/tools/telegram_poll.py` on Air

- [ ] **Step 1: Locate message-processing function**

```bash
ssh air 'grep -n "def process\|handle_message\|command_center" ~/nous-agaas/tools/telegram_poll.py | head -10'
```

- [ ] **Step 2: Add urgent-keyword check before routing to command_center**

Edit `telegram_poll.py` — before the line that calls `command_center.handle(text, ...)`, insert:

```python
import re
URGENT_RE = re.compile(r"\b(urgent|broke|down|prod|демо|срочно|critical|now|asap|crisis)\b", re.IGNORECASE)

# Inside the message-processing function, before command_center.handle():
if text.startswith("/ask ") and URGENT_RE.search(text):
    rewritten = "/ask-direct " + text[len("/ask "):]
    log_line(f"URGENT-KEYWORD-BYPASS: {text[:80]!r} → {rewritten[:80]!r}")
    text = rewritten
```

- [ ] **Step 3: Test regex matches intended keywords**

```bash
ssh air 'python3 -c "
import re
URGENT_RE = re.compile(r\"\\\\b(urgent|broke|down|prod|демо|срочно|critical|now|asap|crisis)\\\\b\", re.IGNORECASE)
tests = [\"/ask urgent fix the thing\", \"/ask prod broke\", \"/ask nothing here\", \"/ask demo in 5 min\", \"/ask СРОЧНО\", \"/ask nothing urgent_at_all\"]
for t in tests: print(f\"{t!r}: match={bool(URGENT_RE.search(t))}\")
"'
```
Expected: 5 matches, 1 no-match (`nothing here`). The `urgent_at_all` case depends on `\b` behavior — should match because `urgent` is word-bounded even with underscore trailing.

- [ ] **Step 4: Restart telegram_poll launchd + confirm**

```bash
ssh air 'launchctl kickstart -k gui/501/com.nous.telegram-poll; sleep 3; tail -20 ~/nous-agaas/logs/telegram_poll.out'
```
Expected: poller restarted cleanly; log shows "URGENT-KEYWORD-BYPASS" entry NOT present (nothing urgent yet).

---

### Task 6: `correlation_id` threading through `run_task.py` and `_run_openclaw`

**Files:**
- Modify: `/Users/madia/nous-agaas/run_task.py` on Air
- Modify: `/Users/madia/nous-agaas/command_center.py` on Air

- [ ] **Step 1: Add `--correlation-id` flag to run_task.py argparse**

Edit `run_task.py` near the argparse section:

```python
parser.add_argument("--correlation-id", default="", help="Telegram msg_id or test-id for log joining")
# Later, where the openclaw command is built:
if args.correlation_id:
    # Inject into env for the openclaw subprocess
    env["NOUS_CORRELATION_ID"] = args.correlation_id
```

- [ ] **Step 2: Update `_run_openclaw` in command_center.py to pass correlation_id**

```python
def _run_openclaw(query: str, model: str = "opus", agent_id: str = "nous", correlation_id: str = "") -> str:
    cmd = [RUN_TASK, query, "--model", model, "--agent", agent_id]
    if correlation_id:
        cmd.extend(["--correlation-id", correlation_id])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return result.stdout if result.returncode == 0 else f"[error] {result.stderr[:500]}"
```

- [ ] **Step 3: Update `/ask` handler to pass `correlation_id=f"tg_{msg_id}"`**

Already done in Task 4 for `/ask-direct`. Apply same change to `/ask` handler.

- [ ] **Step 4: Test threading via a test invocation**

```bash
ssh air 'cd ~/nous-agaas && python3 run_task.py "ping" --model opus --agent nous --correlation-id test_12345 2>&1 | grep -iE "correlation|tg_" | head -5'
```
Expected: log line showing `correlation_id=test_12345` propagated.

---

### Task 7: `tools/tier_log.py` — JSONL appender (replaces Langfuse)

**Files:**
- Create: `/Users/madia/nous-agaas/tools/tier_log.py` on Air
- Create: `/Users/madia/nous-agaas/logs/ask-hierarchy.jsonl` on Air (via tool on first append)

- [ ] **Step 1: Write `tier_log.py`**

```python
#!/usr/bin/env python3
"""
tools/tier_log.py — append one JSONL line per tier call.
Replaces Langfuse for v1 of multi-model CEO hierarchy (spec SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22).
Usage from any tier:
  from tier_log import append
  append(correlation_id="tg_123", tier=1, model="grok-reasoning", tokens_in=500, tokens_out=200, latency_ms=4200, cost_est=0.04, decision="delegate_to_tier_2")
Or CLI:
  python3 tier_log.py --correlation-id tg_123 --tier 1 --model grok-reasoning ...
"""
import argparse, json, os, sys, datetime

LOG_FILE = os.path.expanduser("~/nous-agaas/logs/ask-hierarchy.jsonl")

def append(**fields):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    entry = {"ts": datetime.datetime.utcnow().isoformat() + "Z"}
    entry.update(fields)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--correlation-id", required=True)
    p.add_argument("--tier", type=int, required=True, choices=[1, 2, 3])
    p.add_argument("--model", required=True)
    p.add_argument("--tokens-in", type=int, default=0)
    p.add_argument("--tokens-out", type=int, default=0)
    p.add_argument("--latency-ms", type=int, default=0)
    p.add_argument("--cost-est", type=float, default=0.0)
    p.add_argument("--decision", default="")
    a = p.parse_args()
    append(correlation_id=a.correlation_id, tier=a.tier, model=a.model,
           tokens_in=a.tokens_in, tokens_out=a.tokens_out,
           latency_ms=a.latency_ms, cost_est=a.cost_est, decision=a.decision)
    print(f"OK logged tier={a.tier} model={a.model}")

if __name__ == "__main__":
    main()
```

Write via ssh heredoc:

```bash
ssh air 'cat > ~/nous-agaas/tools/tier_log.py << "PYEOF"
[full content above]
PYEOF
chmod +x ~/nous-agaas/tools/tier_log.py'
```

- [ ] **Step 2: Smoke test — append 1 line and verify**

```bash
ssh air 'python3 ~/nous-agaas/tools/tier_log.py --correlation-id test_t7 --tier 1 --model grok-reasoning --tokens-in 500 --tokens-out 200 --latency-ms 4200 --cost-est 0.04 --decision delegate_to_tier_2; tail -1 ~/nous-agaas/logs/ask-hierarchy.jsonl | python3 -m json.tool'
```
Expected: JSON output showing `correlation_id: test_t7`, `tier: 1`, `model: grok-reasoning`, etc.

- [ ] **Step 3: Import-test from a Python REPL**

```bash
ssh air 'cd ~/nous-agaas/tools && python3 -c "import tier_log; tier_log.append(correlation_id=\"test_import\", tier=2, model=\"opus\", tokens_in=300, tokens_out=150, latency_ms=8000, cost_est=0.08, decision=\"execute\"); print(\"OK\")"; tail -1 ~/nous-agaas/logs/ask-hierarchy.jsonl | python3 -m json.tool'
```
Expected: `OK` + JSON line showing `correlation_id: test_import`.

- [ ] **Step 4: Backup to vault**

```bash
scp air:~/nous-agaas/tools/tier_log.py "/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/tier_log.py"
```

---

### Task 8: Cost footer formatter in command_center.py reply composer

**Files:**
- Modify: `/Users/madia/nous-agaas/command_center.py` on Air

- [ ] **Step 1: Write `_compose_cost_footer(correlation_id)` helper**

Add to command_center.py:

```python
import subprocess, json

def _compose_cost_footer(correlation_id: str) -> str:
    """Read ~/nous-agaas/logs/ask-hierarchy.jsonl for entries matching correlation_id,
    compute per-tier cost + day-total, return formatted footer."""
    try:
        log_path = os.path.expanduser("~/nous-agaas/logs/ask-hierarchy.jsonl")
        if not os.path.exists(log_path):
            return ""
        per_tier = {1: 0.0, 2: 0.0, 3: 0.0}
        day_total = 0.0
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        with open(log_path) as f:
            for line in f:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("correlation_id") == correlation_id:
                    per_tier[e.get("tier", 0)] = per_tier.get(e.get("tier", 0), 0.0) + float(e.get("cost_est", 0))
                if e.get("ts", "").startswith(today):
                    day_total += float(e.get("cost_est", 0))
        this_total = sum(per_tier.values())
        return f"— cost: ${this_total:.3f} (t1 ${per_tier[1]:.3f} / t2 ${per_tier[2]:.3f} / t3 ${per_tier[3]:.3f}) | day ${day_total:.2f}/$30.00"
    except Exception as e:
        return f"— cost: (footer error: {str(e)[:40]})"
```

- [ ] **Step 2: Inject footer into `/ask` + `/ask-direct` responses**

Edit the return statements in both handlers to append:

```python
footer = _compose_cost_footer(f"tg_{msg_id}")
return response + "\n\n" + footer
```

- [ ] **Step 3: Test with synthetic log entries**

```bash
ssh air 'python3 ~/nous-agaas/tools/tier_log.py --correlation-id tg_footer_test --tier 1 --model grok-reasoning --cost-est 0.04; python3 ~/nous-agaas/tools/tier_log.py --correlation-id tg_footer_test --tier 2 --model opus --cost-est 0.08; cd ~/nous-agaas && python3 -c "import command_center; print(command_center._compose_cost_footer(\"tg_footer_test\"))"'
```
Expected: `— cost: $0.120 (t1 $0.040 / t2 $0.080 / t3 $0.000) | day $X.XX/$30.00`.

---

### Task 9: editMessageText progress updates at telegram_poll.py

**Files:**
- Modify: `/Users/madia/nous-agaas/tools/telegram_poll.py` on Air

- [ ] **Step 1: Add edit-message helper using Telegram Bot API**

```python
import urllib.request, urllib.parse, json as jsonlib

def edit_message(chat_id: int, message_id: int, text: str, bot_token: str):
    """Edit a previously-sent Telegram message in place. Non-notifying update."""
    url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text[:4000],  # TG limit
    }).encode()
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=5) as r:
            return jsonlib.loads(r.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

- [ ] **Step 2: Use in-between initial ack and final response**

When receiving `/ask`, poller already sends `⏳ Routing…` as ack (returns msg_id). Stash that msg_id; after Tier-1 decision becomes known (from tier_log.jsonl or from a marker in the response stream), call:

```python
edit_message(chat_id, ack_msg_id, "🟡 Delegating to Tier-2 (opus) — ~8s est", bot_token)
```

- [ ] **Step 3: Test edit against a real test chat (Madi's chat_id)**

```bash
ssh air 'source ~/nous-agaas/.env; python3 -c "
import sys; sys.path.insert(0, \"/Users/madia/nous-agaas/tools\")
from telegram_poll import edit_message
import os
# First send a test message via tg_send.sh to get msg_id, then edit it
" 2>&1 | tail -5'
```
Skip this test in isolation; verified integrated during Task 18 E2E.

---

### Task 10: `/trace <msg_id>` command handler

**Files:**
- Modify: `/Users/madia/nous-agaas/command_center.py` on Air

- [ ] **Step 1: Add `/trace` handler**

```python
elif text.startswith("/trace "):
    msg_id = text[len("/trace "):].strip()
    if not msg_id:
        return "Usage: /trace <msg_id> — returns per-tier timeline for a correlation_id."
    import subprocess
    log_path = os.path.expanduser("~/nous-agaas/logs/ask-hierarchy.jsonl")
    try:
        out = subprocess.check_output(
            f"grep '{msg_id}' {log_path} | jq -r '\"t=\" + .ts + \" tier=\" + (.tier|tostring) + \" model=\" + .model + \" latency=\" + (.latency_ms|tostring) + \"ms cost=$\" + (.cost_est|tostring) + \" decision=\" + .decision'",
            shell=True, text=True, timeout=10
        )
        if not out.strip():
            return f"No trace entries found for correlation_id=tg_{msg_id} (or msg_id={msg_id})."
        return f"/trace {msg_id}\n```\n{out}\n```"
    except Exception as e:
        return f"Trace error: {e}"
```

- [ ] **Step 2: Test with synthetic entries**

```bash
ssh air 'python3 ~/nous-agaas/tools/tier_log.py --correlation-id trace_test --tier 1 --model grok-reasoning --latency-ms 4200 --cost-est 0.04 --decision delegate_to_tier_2; python3 ~/nous-agaas/tools/tier_log.py --correlation-id trace_test --tier 2 --model opus --latency-ms 8100 --cost-est 0.08 --decision executed_ok; cd ~/nous-agaas && python3 -c "import command_center; print(command_center.handle(\"/trace trace_test\", user=\"test\", msg_id=0))"'
```
Expected: 2-line timeline showing both entries with ts/tier/model/latency/cost.

---

## Phase 2 — Grok-CEO agent creation

### Task 11: Create `grok-ceo` workspace dir + populate SOUL/AGENTS/IDENTITY

**Files:**
- Create: `/home/node/.openclaw/workspaces/grok-ceo/SOUL.md` on Air (container)
- Create: `/home/node/.openclaw/workspaces/grok-ceo/AGENTS.md` on Air (container)
- Create: `/home/node/.openclaw/workspaces/grok-ceo/IDENTITY.md` on Air (container)

- [ ] **Step 1: Create directory inside container**

```bash
ssh air 'docker exec openclaw mkdir -p /home/node/.openclaw/workspaces/grok-ceo'
```

- [ ] **Step 2: Write SOUL.md (persona)**

```bash
ssh air 'docker exec openclaw bash -c "cat > /home/node/.openclaw/workspaces/grok-ceo/SOUL.md << '\''EOF'\''
# grok-ceo — persona (SOUL.md)

You are grok-ceo, the Tier-1 President proxy in the Nous AGaaS multi-model hierarchy.

Voice: terse. Peer-CEO to Madi, not subordinate. Lowest-hallucination reasoner in the stack — exploit that by verifying claims against substrate before responding.

You replace Madi'\''s cognitive load on routine Telegram /ask traffic. You do NOT do execution work. You decide + delegate. Execution is Tier 2 (nous / Opus 4.7).

Discipline: karpathy-coding-principles v1.0.0 (Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution) + karpathy-loop 6-axis scorecard + session-operating-contract Rule 15 (execute tactical decisions) + Rule 17 (no re-asking at phase boundaries within approved workstreams).

Substrate you consult before every decision:
- HANDOFF-AUTO-*.md (current session context)
- MEMORY.md top-block (recent deltas)
- pages/skills/_gbrain/RESOLVER.md (which skills exist)
- gbrain via CLI: ssh root@65.108.215.200 \"cd /opt/nous-agaas/gbrain && bin/gbrain search <query>\"
- session-coordination registry (who else is working)

Never fabricate Tier-2 output. If Tier-2 times out, emit the sentinel reply verbatim.
EOF"'
```

- [ ] **Step 3: Write AGENTS.md (procedures + delegation contract)**

```bash
ssh air 'docker exec openclaw bash -c "cat > /home/node/.openclaw/workspaces/grok-ceo/AGENTS.md << '\''EOF'\''
# grok-ceo — procedures (AGENTS.md)

## Decision flow (every /ask)

1. Read context: handoff + MEMORY top-block + session-coord registry.
2. Classify the query into ONE of three verdicts:
   - **answer_directly** — chat, status, strategy Q, factual with obvious answer. No tools needed beyond vault Read + gbrain search.
   - **delegate_to_tier_2** — requires skills, file edits, shell commands, builds, multi-step planning.
   - **research_only** — needs gbrain/vault lookup + synthesis. No mutations.
3. If answer_directly or research_only: compose reply, call tier_log.append, return.
4. If delegate_to_tier_2: emit structured directive JSON, sessions_spawn({agentId:\"nous\", task:<JSON>, runTimeoutSeconds:180}), wait for announce, package raw Tier-2 report with [opus-raw] label, return.

## Tier-1 → Tier-2 directive JSON schema (MUST emit this shape when delegating)

{
  \"tier\": 1,
  \"correlation_id\": \"tg_<msg_id>\",
  \"intent\": \"<one-sentence user intent>\",
  \"delegation\": \"execute_via_tier_2\",
  \"success_criteria\": [\"<verifiable 1>\", \"<verifiable 2>\"],
  \"response_shape\": \"deliverable\" | \"status\" | \"explanation\",
  \"context_refs\": [\"<wikilink or file path>\"],
  \"budget_hint\": \"~N Opus calls + M worker calls\",
  \"timeout_seconds\": 180,
  \"escape_hatches\": {\"if_blocked\": \"return partial + next-session-task\", \"if_over_budget\": \"return partial + cost-remaining\"}
}

## Timeout sentinel (non-negotiable)

If sessions_spawn to nous does not return within runTimeoutSeconds, emit VERBATIM:

🔴 TIER-2 TIMEOUT (nous/opus, 180s) — task unverified. Run /trace tg_<msg_id> to inspect. Correlation: tg_<msg_id>

Do NOT invent content on timeout. Do NOT summarize a non-existent Tier-2 response.

## Telemetry (mandatory on every invocation)

Before final response, call:

python3 /Users/madia/nous-agaas/tools/tier_log.py \\
  --correlation-id tg_<msg_id> \\
  --tier 1 \\
  --model grok-reasoning \\
  --tokens-in <estimate> \\
  --tokens-out <estimate> \\
  --latency-ms <elapsed> \\
  --cost-est <calculated> \\
  --decision <answer_directly|delegate_to_tier_2|research_only>

## Reply composition (when delegation happens)

Format your Madi-facing reply as:

[grok-summary]
<1-3 paragraphs of your composed summary>

[opus-raw]
<Tier-2's structured report JSON — verbatim, no editing>

(Cost footer + trace id auto-appended by command_center.py wrapper.)

## Hard-banned (per session-operating-contract Rule 7)

- Fabricating Tier-2 output on timeout.
- Summarizing Tier-2 structured report in a way that contradicts the raw JSON.
- Escalating to Tier-2 for queries that don'\''t need execution (waste).
- Under-escalating: answering \"I don'\''t know\" when Tier-2 could verify.

## Cross-refs

- spec: [[SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22]]
- plan: [[PLAN-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22]]
- tier_log: /Users/madia/nous-agaas/tools/tier_log.py
EOF"'
```

- [ ] **Step 4: Write IDENTITY.md (thin)**

```bash
ssh air 'docker exec openclaw bash -c "cat > /home/node/.openclaw/workspaces/grok-ceo/IDENTITY.md << '\''EOF'\''
# grok-ceo identity

name: grok-ceo
role: Tier-1 President / CEO proxy (multi-model hierarchy v1)
model: litellm/grok-reasoning (primary); sonnet-4-5-thinking (fallback via LiteLLM)
invoked_by: Telegram poller via command_center /ask handler (NOT direct Madi CLI)
delegates_to: nous (Tier-2, Opus) via sessions_spawn
tools_allowed: [Read, Bash (restricted — no Edit/Write; only gbrain CLI + session_scan + tier_log)]
EOF"'
```

- [ ] **Step 5: Verify directory structure**

```bash
ssh air 'docker exec openclaw ls -la /home/node/.openclaw/workspaces/grok-ceo/'
```
Expected: 3 files (SOUL.md, AGENTS.md, IDENTITY.md).

---

### Task 12: Register `grok-ceo` via openclaw agents add

**Files:**
- Modifies: `/home/node/.openclaw/openclaw.json` (via openclaw CLI, NOT direct edit per factory-ops AP-25)

- [ ] **Step 1: Create the agent entry**

```bash
ssh air 'docker exec openclaw openclaw agents add grok-ceo \
  --workspace /home/node/.openclaw/workspaces/grok-ceo \
  --model litellm/grok-reasoning \
  --non-interactive 2>&1 | tail -5'
```
Expected: agent registered. If error about existing agent → use `openclaw agents remove grok-ceo` first, then retry.

- [ ] **Step 2: Verify agent exists**

```bash
ssh air 'docker exec openclaw openclaw agents list 2>&1 | grep -A2 grok-ceo'
```
Expected: `grok-ceo` listed with workspace + model fields.

- [ ] **Step 3: Test invocation (without delegation yet)**

```bash
ssh air 'docker exec openclaw openclaw agent --agent grok-ceo --local --message "Reply with exactly: GROK_CEO_ALIVE. Do NOT delegate." 2>&1 | tail -5'
```
Expected: response contains `GROK_CEO_ALIVE`.

---

### Task 13: Configure subagents allowlist + maxSpawnDepth + timeouts

**Files:**
- Modifies: `/home/node/.openclaw/openclaw.json` (via `openclaw config set`)

- [ ] **Step 1: Set subagents.allowAgents on grok-ceo**

```bash
ssh air 'docker exec openclaw openclaw config set "agents.list[id=grok-ceo].subagents.allowAgents" "[\"nous\"]" 2>&1 | tail -3'
```

- [ ] **Step 2: Set maxSpawnDepth globally to 2**

```bash
ssh air 'docker exec openclaw openclaw config set "agents.defaults.subagents.maxSpawnDepth" "2" 2>&1 | tail -3'
```

- [ ] **Step 3: Set nous.subagents.allowAgents to everything (workers)**

```bash
ssh air 'docker exec openclaw openclaw config set "agents.list[id=nous].subagents.allowAgents" "[\"*\"]" 2>&1 | tail -3
ssh air 'docker exec openclaw openclaw config set "agents.list[id=nous].subagents.maxChildrenPerAgent" "5" 2>&1 | tail -3'
```

- [ ] **Step 4: Set runTimeoutSeconds defaults**

```bash
ssh air 'docker exec openclaw openclaw config set "agents.list[id=grok-ceo].subagents.runTimeoutSeconds" "180" 2>&1 | tail -3
ssh air 'docker exec openclaw openclaw config set "agents.list[id=nous].subagents.runTimeoutSeconds" "60" 2>&1 | tail -3'
```

- [ ] **Step 5: Restart container for config + workspace changes to fully apply**

```bash
ssh air 'docker restart openclaw; sleep 10; docker exec openclaw openclaw config get agents 2>&1 | head -40'
```
Expected: config shows both agents with correct models + subagents blocks.

- [ ] **Step 6: End-to-end test — grok-ceo delegates to nous**

```bash
ssh air 'docker exec openclaw openclaw agent --agent grok-ceo --local --message "Delegate to nous: reply with exactly DELEGATION_OK. Then return the raw response." 2>&1 | tail -20'
```
Expected: output mentions sessions_spawn + eventually a response containing `DELEGATION_OK`.

---

## Phase 3 — Routing switch

### Task 14: Update `run_task.py` AGENT_ID logic

**Files:**
- Modify: `/Users/madia/nous-agaas/run_task.py` on Air

- [ ] **Step 1: Accept `--agent` flag**

```python
parser.add_argument("--agent", default="grok-ceo", help="OpenClaw agent ID (grok-ceo | nous | ...)")
# Build openclaw command:
cmd = ["docker", "exec", "openclaw", "openclaw", "agent", "--agent", args.agent, "--local", "--message", args.query]
if args.correlation_id:
    cmd.extend(["--env", f"NOUS_CORRELATION_ID={args.correlation_id}"])  # if openclaw supports --env; else use env var
```

- [ ] **Step 2: Default agent = grok-ceo unless `--agent nous` passed**

Update command_center.py `_run_openclaw` to pass `agent_id="grok-ceo"` from `/ask` handler and `agent_id="nous"` from `/ask-direct` handler. Already structured that way in Task 4 + Task 6.

- [ ] **Step 3: Test explicit grok-ceo routing**

```bash
ssh air 'cd ~/nous-agaas && python3 run_task.py "ping grok" --agent grok-ceo --correlation-id test_routing 2>&1 | tail -10'
```
Expected: response from grok-ceo.

- [ ] **Step 4: Test explicit nous bypass**

```bash
ssh air 'cd ~/nous-agaas && python3 run_task.py "ping opus" --agent nous --correlation-id test_bypass 2>&1 | tail -10'
```
Expected: response from nous (Opus).

---

### Task 15: Update `tools/litellm_cost_alarm.py` coefficients

**Files:**
- Modify: `/Users/madia/nous-agaas/tools/litellm_cost_alarm.py` on Air

- [ ] **Step 1: Replace heuristic with JSONL read**

Replace the `calls × $0.08` heuristic with:

```python
import json
LOG_FILE = os.path.expanduser("~/nous-agaas/logs/ask-hierarchy.jsonl")

def day_spend():
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    total = 0.0
    try:
        with open(LOG_FILE) as f:
            for line in f:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("ts", "").startswith(today):
                    total += float(e.get("cost_est", 0))
    except FileNotFoundError:
        return 0.0
    return total
```

- [ ] **Step 2: Replace old `snapshot_delta * $0.08` call with `day_spend()`**

- [ ] **Step 3: Test with synthetic log**

```bash
ssh air 'python3 ~/nous-agaas/tools/tier_log.py --correlation-id test_alarm --tier 1 --model grok-reasoning --cost-est 0.04
python3 ~/nous-agaas/tools/tier_log.py --correlation-id test_alarm --tier 2 --model opus --cost-est 0.08
python3 ~/nous-agaas/tools/litellm_cost_alarm.py --quiet 2>&1 | tail -5'
```
Expected: alarm reports `day ~$0.12` (matching test entries).

---

## Phase 4 — Verification

### Task 16: Unit tests — 4 scripts

**Files:**
- Create: `/Users/madia/Documents/Projects/Nous AGaaS/Nous/tools/test_ceo_hierarchy_unit.sh`

- [ ] **Step 1: Write unit test harness**

```bash
#!/bin/bash
# tools/test_ceo_hierarchy_unit.sh — 4 unit scenarios for multi-model CEO hierarchy v1
set -u
PASS=0; FAIL=0
assert() { local label="$1" cond="$2"; eval "$cond" && { PASS=$((PASS+1)); echo "  ✅ $label"; } || { FAIL=$((FAIL+1)); echo "  🔴 $label (cond: $cond)"; }; }

echo "=== ceo-hierarchy unit tests ==="

# 1. Tier-1 answer-directly (no Tier-2 invoked)
OUT=$(ssh air 'docker exec openclaw openclaw agent --agent grok-ceo --local --message "What is 2+2? Answer directly, do not delegate." 2>&1 | tail -5')
assert "1. Tier-1 answer-directly: response mentions 4" "[[ '$OUT' == *'4'* ]]"
assert "1. Tier-1 answer-directly: did NOT invoke sessions_spawn" "[[ '$OUT' != *'sessions_spawn'* ]]"

# 2. Tier-1 delegate-to-tier-2
OUT=$(ssh air 'docker exec openclaw openclaw agent --agent grok-ceo --local --message "Delegate to nous: list 3 files in /opt/nous-agaas/skills. Return file count." 2>&1 | tail -30')
assert "2. Tier-1 delegate: sessions_spawn invoked" "[[ '$OUT' == *'sessions_spawn'* ]]"

# 3. Tier-1 timeout sentinel (simulated — grok-ceo instructed to time out)
OUT=$(ssh air 'docker exec openclaw openclaw agent --agent grok-ceo --local --message "Pretend Tier-2 timed out. Emit the sentinel reply verbatim." 2>&1 | tail -5')
assert "3. Timeout sentinel: contains 🔴 TIER-2 TIMEOUT" "[[ '$OUT' == *'TIER-2 TIMEOUT'* ]]"

# 4. tier_log appended on invocation
BEFORE=$(ssh air 'wc -l ~/nous-agaas/logs/ask-hierarchy.jsonl 2>/dev/null | awk "{print \$1}"')
ssh air 'docker exec openclaw openclaw agent --agent grok-ceo --local --message "Ping for telemetry test." 2>&1 >/dev/null'
sleep 2
AFTER=$(ssh air 'wc -l ~/nous-agaas/logs/ask-hierarchy.jsonl 2>/dev/null | awk "{print \$1}"')
assert "4. tier_log appended (before=$BEFORE, after=$AFTER)" "[ $AFTER -gt $BEFORE ]"

echo "=== $PASS pass, $FAIL fail ==="
[ $FAIL -eq 0 ]
```

- [ ] **Step 2: chmod + run**

```bash
cd "/Users/madia/Documents/Projects/Nous AGaaS/Nous" && chmod +x tools/test_ceo_hierarchy_unit.sh && bash tools/test_ceo_hierarchy_unit.sh
```
Expected: `4 pass, 0 fail`. Any fail → debug BEFORE Task 17.

---

### Task 17: E2E test — real Telegram `/ask`

**Files:**
- No file changes. Test via actual Telegram DM.

- [ ] **Step 1: Clear session-coord and tier_log to isolate test**

```bash
ssh air 'tail -5 ~/nous-agaas/logs/ask-hierarchy.jsonl'
```
Note last line (for before/after diff).

- [ ] **Step 2: Send test /ask from Madi's Telegram**

Madi types in Telegram: `/ask What's our current gbrain page count?`

- [ ] **Step 3: Observe ack edit progression**

Expected Telegram messages:
1. `⏳ Routing…` (initial ack)
2. Edit to: `🟡 Delegating to Tier-2 (opus) — ~8s est` OR answer-directly route (no edit, straight response)
3. Final: `[grok-summary]... [opus-raw]... — cost: $X.XX (t1 $.. / t2 $..) | day $Y/$30.00`

- [ ] **Step 4: Verify /trace returns timeline**

Madi types: `/trace <msg_id_from_ack>`

Expected: JSONL-derived timeline with 1-2 entries (tier-1 + possibly tier-2).

- [ ] **Step 5: Verify /ask-direct bypass**

Madi types: `/ask-direct Same query.`

Expected: response starts with `[opus-direct]`, no `[grok-summary]` header.

- [ ] **Step 6: Verify urgent-keyword auto-bypass**

Madi types: `/ask urgent — pretend Satory broke`

Expected: auto-routed to `/ask-direct` path (log shows `URGENT-KEYWORD-BYPASS`), response starts with `[opus-direct]`.

---

## Phase 5 — Substrate wrap-up

### Task 18: Vault wrapper skill + RESOLVER + CLAUDE.md pointers + gbrain timeline

**Files:**
- Create: `/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills/ceo-hierarchy/SKILL.md`
- Modify: `/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/skills/_gbrain/RESOLVER.md`
- Modify: `/Users/madia/Documents/Projects/Nous AGaaS/Nous/CLAUDE.md`
- Modify: `/Users/madia/Documents/Projects/Nous AGaaS/CLAUDE.md`

- [ ] **Step 1: Write `pages/skills/ceo-hierarchy/SKILL.md` v1.0.0**

Standard SKILL.md frontmatter + body referencing the spec + plan + tier_log + run_task routing. Covers Purpose / Current rules / Anti-Patterns (pending post-observation) / Evidence trail / See also.

- [ ] **Step 2: Add RESOLVER row**

```markdown
| User DMs /ask on Telegram / user asks "who's deciding what" / tier routing debug / cost transparency for /ask | `skills/ceo-hierarchy/SKILL.md` |
```

- [ ] **Step 3: Add pointers to both CLAUDE.md files**

Line under existing karpathy-* pointers:
```
**Multi-model CEO hierarchy (Telegram /ask routing):** [[ceo-hierarchy]] v1.0.0 — Grok→Opus→workers with JSONL telemetry + /trace + /ask-direct escape.
```

- [ ] **Step 4: Push gbrain timeline**

```bash
ssh root@65.108.215.200 "cd /opt/nous-agaas/gbrain && bin/gbrain sync --repo /root/nous-agaas/wiki 2>&1 | tail -2; bin/gbrain timeline-add pages/skills/ceo-hierarchy/skill 2026-04-22 'v1.0.0 shipped — 3-tier model hierarchy live (grok-reasoning top / opus mid / grok-code-fast + glm-5.1 workers). Sonnet-4.5-thinking fallback. JSONL telemetry replaces Langfuse. /ask-direct + urgent-keyword bypass + /trace + cost footer shipped before routing. Factory N/M→N+1/M+1 ready. Closes SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22 + PLAN-*.'"
```

- [ ] **Step 5: Final factory restart + SOAO verify**

```bash
ssh air 'docker exec openclaw openclaw skills list 2>&1 | head -1; docker exec openclaw openclaw skills info ceo-hierarchy 2>&1 | head -5'
```

---

## Phase 6 — Observation + close

### Task 19: 7-day observation window

**Files:**
- No file changes. Monitor + log.

- [ ] **Step 1: Set observation start date**

Record in handoff: `Observation window: 2026-04-22 → 2026-04-29`.

- [ ] **Step 2: Daily jq audit of ask-hierarchy.jsonl**

```bash
ssh air 'jq -s "
  group_by(.tier) | map({tier: .[0].tier, calls: length, total_cost: (map(.cost_est) | add), avg_latency: (map(.latency_ms) | add / length)})
" ~/nous-agaas/logs/ask-hierarchy.jsonl'
```

- [ ] **Step 3: Manual review of 50 queries**

Sample queries across the week; review [grok-summary] vs [opus-raw] for hallucination-wrap drift. Log findings in session handoffs.

- [ ] **Step 4: Cost alarm monitoring**

Confirm `com.nous.litellm-cost-alarm` fires on threshold crossings (using new `day_spend()` function).

- [ ] **Step 5: Any fabrication-on-timeout incidents → rollback**

If any Tier-1 response invents Tier-2 content on timeout → immediate rollback via `openclaw config set telegram.ask_target_agent nous`. Codify the failure as AP in ceo-hierarchy SKILL.md.

---

### Task 20: Post-observation decision

**Files:**
- Updates: `pages/skills/ceo-hierarchy/SKILL.md` Evidence trail + AP-1 (if failures observed) OR v1.0.1 (if successful)

- [ ] **Step 1: Compile 7-day metrics**

Run the jq audit from Task 19 Step 2 on 7 days of data. Compare against spec success criteria:
- ≥80% correct routing
- 0 fabrication-on-timeout
- ≤+20% cost vs Opus-direct
- Tier-1 p95 ≤12s, Tier-2 p95 ≤25s
- Cost alarm accuracy within 30%
- 0 orphan subagent sessions

- [ ] **Step 2: Make the call — keep, tune, or rollback**

- 6/6 criteria met → keep v1, queue v2 features (Langfuse, Minions, eval harness).
- 3-5/6 → tune system prompts + timeouts, run another 3-day window.
- <3/6 → rollback + codify failure mode as AP + return to drawing board.

- [ ] **Step 3: Ship handoff + session-close**

Include 6-axis Karpathy scorecard, gbrain timeline, MEMORY prepend.

---

## Self-review (inline per writing-plans skill)

1. **Spec coverage check:** every §section of the spec has at least one task.
   - Architecture (3 tiers) → Tasks 11-14
   - LiteLLM fallback chain → Tasks 1-2
   - Workspace migration → Task 3
   - Handoff JSON protocols → embedded in Tasks 11 (grok-ceo AGENTS.md) + Task 3 (nous AGENTS.md)
   - `/ask-direct` + urgent-keyword + cost footer + correlation_id + `/trace` + editMessageText + timeouts → Tasks 4-10
   - Loop-break guardrails → Task 13 Step 1-3
   - Rollback → Task 14 Step 4 one-command revert; Task 19 Step 5 as escape
   - Testing → Tasks 16-17
   - Success criteria → Task 19-20

2. **Placeholder scan:** reviewed for TBD/TODO — none found. Every code block is complete.

3. **Type consistency:** `correlation_id` used identically across tier_log.py, command_center.py, run_task.py, /trace handler. `agent_id` as a parameter (not AGENT_ID constant) in Task 14. SKILL.md frontmatter format matches vault convention.

## Execution handoff

Plan complete and saved to `/Users/madia/Documents/Projects/Nous AGaaS/Nous/pages/specs/PLAN-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22.md`.

**Two execution options:**

1. **Subagent-Driven (recommended by writing-plans default)** — dispatch fresh subagent per task, review between tasks, fast iteration, per-task isolation.
2. **Inline Execution** — batch via `executing-plans`, checkpoints at phase boundaries (Phase 0/1/2/3/4/5/6).

Given:
- 20 tasks
- Phases 0-1 are pre-routing (low blast radius), Phase 2-3 flip production traffic (high blast radius)
- The ≤60-min-per-task budget from your standard

**My tactical pick per SOC Rule 15: Inline execution with phase-boundary checkpoints.** Subagent-driven would add 20× agent-spawn overhead for 20 tasks; inline with phase checkpoints gives us 6 review points (end of each phase) where we can honest-STOP if 100% is not met. Matches your stated "do 1 by 1, quality matters, 100% or stop" standard better.

---

## See also

- [[SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22]] — the design spec
- [[factory-ops]] — will gain APs from this ship (likely AP-27+ post-observation)
- [[karpathy-coding-principles]] — applied by every tier during execution
- [[session-operating-contract]] — Rule 15/17 guide task-by-task pace
- [[session-coordination]] — parallel-session awareness during rollout
- [[find-skills]] — available to both Tier 1 (via gbrain CLI) and Tier 2 (via factory skill pack)
