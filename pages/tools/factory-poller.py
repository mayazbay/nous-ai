#!/usr/bin/env python3
"""
factory-poller.py — AGaaS Hermes learning loop
Runs every 5 min on M2 Air via launchd (com.nous.factory-poller).
Polls VPS for new task results and feeds them to Hermes for skill extraction.

Flow: new task-result in VPS wiki → Hermes analyzes → if novel, writes SKILL.md to VPS wiki → syncs everywhere
"""
import json
import os
import subprocess
import sys
from datetime import datetime

VPS = "root@65.108.215.200"
TASK_RESULTS_PATH = "/root/nous-agaas/wiki/pages/task-results/"
SKILLS_PATH = "/root/nous-agaas/wiki/pages/skills/extracted/"
WIKI_PATH = "/root/nous-agaas/wiki"
STATE_FILE = os.path.expanduser("~/.hermes/factory-poller-state.json")
LOG_FILE = os.path.expanduser("~/.hermes/factory-poller.log")
# Max log size 500KB — rotate by truncating old half
MAX_LOG_BYTES = 500_000


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_BYTES:
        with open(LOG_FILE, "rb") as f:
            data = f.read()
        with open(LOG_FILE, "wb") as f:
            f.write(data[MAX_LOG_BYTES // 2:])
    with open(LOG_FILE, "a") as f:
        f.write(line)
    print(line, end="", flush=True)


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_processed": ""}


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _ssh(cmd: str, timeout: int = 30) -> str:
    r = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
         "-o", "BatchMode=yes", VPS, cmd],
        capture_output=True, text=True, timeout=timeout,
    )
    return r.stdout


def _get_new_results(last_processed: str) -> list:
    """Return sorted list of new task-result filenames from VPS."""
    try:
        out = _ssh(f"ls {TASK_RESULTS_PATH} 2>/dev/null | sort")
        files = [f.strip() for f in out.splitlines() if f.strip().endswith(".md")]
        return [f for f in files if f > last_processed] if last_processed else files
    except Exception as e:
        _log(f"ERROR listing VPS results: {e}")
        return []


def _read_result(filename: str) -> str:
    try:
        return _ssh(f"cat {TASK_RESULTS_PATH}{filename}")
    except Exception as e:
        _log(f"ERROR reading {filename}: {e}")
        return ""


def _analyze_with_hermes(filename: str, content: str) -> None:
    """Ask Hermes to analyze a task result and extract a skill if warranted."""
    skill_filename = filename.replace(".md", "-skill.md")
    prompt = (
        f"You are the AGaaS learning agent. Analyze this completed factory task "
        f"for patterns worth capturing as a reusable SKILL.md.\n\n"
        f"File: {filename}\n\n{content}\n\n"
        f"Decision criteria — write a skill ONLY if:\n"
        f"  - The task required a non-obvious multi-step approach\n"
        f"  - The same type of task will likely recur\n"
        f"  - A skill would save >5 min next time\n\n"
        f"If YES: use your terminal tool to run these commands:\n"
        f"  ssh {VPS} 'mkdir -p {SKILLS_PATH}'\n"
        f"  # Then write the skill file via ssh heredoc\n"
        f"  ssh {VPS} 'cat > {SKILLS_PATH}{skill_filename}' << 'SKILLEOF'\n"
        f"  <your SKILL.md content here>\n"
        f"  SKILLEOF\n"
        f"  ssh {VPS} 'git -C {WIKI_PATH} add pages/skills/extracted/{skill_filename} "
        f"&& git -C {WIKI_PATH} commit -m \"skill: extracted from {filename}\"'\n\n"
        f"If NO skill warranted: reply exactly: NO_SKILL"
    )
    try:
        result = subprocess.run(
            ["hermes", "chat", "-q", prompt],
            capture_output=True, text=True, timeout=300,
        )
        reply = result.stdout.strip()[:200]
        _log(f"Hermes reply for {filename}: {reply}")
    except FileNotFoundError:
        _log("ERROR: hermes not found in PATH — check installation")
    except subprocess.TimeoutExpired:
        _log(f"TIMEOUT analyzing {filename}")
    except Exception as e:
        _log(f"ERROR running hermes for {filename}: {e}")


def main() -> None:
    _log("factory-poller: start")
    state = _load_state()
    new_files = _get_new_results(state["last_processed"])

    if not new_files:
        _log("factory-poller: no new tasks — done")
        return

    _log(f"factory-poller: {len(new_files)} new task(s): {new_files}")
    for filename in new_files:
        _log(f"analyzing: {filename}")
        content = _read_result(filename)
        if content.strip():
            _analyze_with_hermes(filename, content)
        state["last_processed"] = filename
        _save_state(state)

    _log("factory-poller: done")


if __name__ == "__main__":
    main()
