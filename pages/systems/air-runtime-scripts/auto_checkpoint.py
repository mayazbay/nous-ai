#!/usr/bin/env python3
"""
auto_checkpoint.py v3 — SMART + DIAGNOSABLE.

Skips if no new task-results since last checkpoint. Writes HANDOFF-AUTO-*.md
via GLM-5.1 only when there's actual activity to summarize.

Runs 8×/day via launchd. Typical days: ~2-3 actual writes (working hours),
rest are fast no-op checks. Saves tokens + wiki clutter.

v3 changes (LESSON-108 — error reporting discipline):
  - Persist FULL stdout+stderr of every RUN attempt to
    logs/auto-checkpoint-runs/checkpoint-{ts}.log so post-mortems are possible.
  - On failure, SCAN stderr for real error lines (Traceback, Exception,
    RuntimeError, ERROR, FATAL) and surface those — not the first 300 chars
    of INFO/WARNING log noise.
  - Explicitly catch subprocess.TimeoutExpired and distinguish from agent
    failure in the alert.
"""
import sys, os, re, subprocess, json, urllib.request
from pathlib import Path
sys.path.insert(0, "/Users/madia/nous-agaas")
from datetime import datetime, timezone, timedelta
try:
    from dotenv import load_dotenv
    load_dotenv("/Users/madia/nous-agaas/.env", override=True)
except ImportError:
    pass

KZ_TZ = timezone(timedelta(hours=5))
PYTHON = "/opt/homebrew/bin/python3"
RUN_TASK = "/Users/madia/nous-agaas/run_task.py"
TASK_RESULTS_DIR = Path("/Users/madia/nous-agaas/wiki/pages/task-results")
STATE_FILE = Path("/Users/madia/nous-agaas/logs/auto-checkpoint-state.json")
RUNS_DIR = Path("/Users/madia/nous-agaas/logs/auto-checkpoint-runs")
TIMEOUT = 600

# Patterns that indicate a REAL error in run_task.py stderr (not INFO noise).
ERROR_PATTERNS = re.compile(
    r"(Traceback|Exception|RuntimeError|ERROR|FATAL|failed|not found|status=error|budget_exceeded)",
    re.IGNORECASE,
)


def _telegram_notify(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return
    try:
        payload = json.dumps({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload, headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[auto_checkpoint] Telegram notify failed: {e}")


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {"last_checkpoint": "", "last_task_result": ""}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def latest_task_result() -> str:
    """Most recent task-result filename (or empty)."""
    try:
        files = sorted(TASK_RESULTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime)
        return files[-1].name if files else ""
    except Exception:
        return ""


def _persist_run_log(ts: str, stdout: str, stderr: str, returncode: int,
                     reason: str) -> Path:
    """Persist full subprocess output for post-mortem. Returns path."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    p = RUNS_DIR / f"checkpoint-{ts}.log"
    with p.open("w") as fh:
        fh.write(f"=== auto_checkpoint run @ {ts} ===\n")
        fh.write(f"outcome: {reason}\n")
        fh.write(f"returncode: {returncode}\n")
        fh.write(f"\n--- STDOUT ({len(stdout)} chars) ---\n{stdout}\n")
        fh.write(f"\n--- STDERR ({len(stderr)} chars) ---\n{stderr}\n")
    return p


def _extract_real_error(stderr: str, stdout: str) -> str:
    """Pull the ACTUAL error lines from subprocess output.

    Scans stderr+stdout for lines matching ERROR_PATTERNS. If any match,
    returns those lines joined (up to 400 chars). Otherwise returns the
    LAST 400 chars of stderr (where real crashes usually land — the first
    300 chars are INFO/WARNING log noise in Python logging's default layout).
    """
    combined = (stderr or "") + "\n" + (stdout or "")
    matches = [ln.strip() for ln in combined.splitlines() if ERROR_PATTERNS.search(ln)]
    if matches:
        # Deduplicate consecutive identical lines, keep last ~5 unique
        seen, unique = set(), []
        for ln in matches[-10:]:
            if ln and ln not in seen:
                seen.add(ln)
                unique.append(ln)
        out = "\n".join(unique[-5:])
        return out[:400]
    # Fallback: last 400 chars of stderr (or stdout if stderr empty)
    tail_source = stderr.strip() if stderr and stderr.strip() else stdout.strip()
    return tail_source[-400:] if tail_source else "(no output)"


def checkpoint() -> None:
    state = _load_state()
    latest = latest_task_result()
    if latest and latest == state.get("last_task_result"):
        print(f"[auto_checkpoint] SKIP: no new task-results since last checkpoint ({latest})")
        return

    ts = datetime.now(KZ_TZ).strftime("%Y-%m-%d-%H-%M")
    wiki_path = f"pages/progress/HANDOFF-AUTO-{ts}.md"
    prompt = (
        f"Write a concise factory checkpoint and save it as {wiki_path} via write-back. "
        "Include: (1) systems verified working today with timestamps from pages/task-results/, "
        "(2) top 3 next actions, (3) active blockers with owners. Under 150 lines. Facts only."
    )
    print(f"[auto_checkpoint] Writing checkpoint: {wiki_path}", flush=True)

    try:
        result = subprocess.run(
            [PYTHON, RUN_TASK, prompt],
            capture_output=True, text=True, timeout=TIMEOUT,
            cwd="/Users/madia/nous-agaas",
        )
    except subprocess.TimeoutExpired as e:
        log_path = _persist_run_log(
            ts,
            (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
            (e.stderr or b"").decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or ""),
            -1,
            f"TIMEOUT after {TIMEOUT}s",
        )
        msg = (
            f"❌ Auto-checkpoint TIMEOUT at {ts} ({TIMEOUT}s exceeded)\n"
            f"Full log: {log_path}"
        )
        print(f"[auto_checkpoint] {msg}", flush=True)
        _telegram_notify(msg)
        return

    if result.returncode == 0:
        _persist_run_log(ts, result.stdout, result.stderr, 0, "ok")
        print(f"[auto_checkpoint] DONE: {wiki_path}", flush=True)
        state["last_checkpoint"] = ts
        state["last_task_result"] = latest
        _save_state(state)
        if os.environ.get("CHECKPOINT_NOTIFY_SUCCESS", "0") == "1":
            _telegram_notify(f"✅ Auto-checkpoint saved: {wiki_path}")
        return

    # Non-zero returncode path — real error. Pull the actual error lines, not
    # the first 300 chars of INFO/WARNING noise (LESSON-105).
    log_path = _persist_run_log(ts, result.stdout, result.stderr,
                                result.returncode, "non_zero_returncode")
    real_err = _extract_real_error(result.stderr, result.stdout)
    alert = (
        f"❌ Auto-checkpoint FAILED at {ts} (exit={result.returncode})\n\n"
        f"{real_err}\n\n"
        f"Full log: {log_path}"
    )
    print(f"[auto_checkpoint] ERROR:\n{alert}", flush=True)
    _telegram_notify(alert)


if __name__ == "__main__":
    checkpoint()
