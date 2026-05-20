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
WIKI_ROOT = Path("/Users/madia/nous-agaas/wiki")
TASK_RESULTS_DIR = Path("/Users/madia/nous-agaas/wiki/pages/task-results")
STATE_FILE = Path("/Users/madia/nous-agaas/logs/auto-checkpoint-state.json")
RUNS_DIR = Path("/Users/madia/nous-agaas/logs/auto-checkpoint-runs")
TIMEOUT = 600
DAILY_0300_TASK = "Reply with exactly: DAILY_0300_OK"
DAILY_0300_SLUG = "reply-with-exactly-daily-0300-ok"

# Patterns that indicate a REAL error in run_task.py stderr (not INFO noise).
ERROR_PATTERNS = re.compile(
    r"(Traceback|Exception|RuntimeError|ERROR|FATAL|failed|not found|status=error|budget_exceeded)",
    re.IGNORECASE,
)
SECRET_PATTERNS = [
    re.compile(r"https://[^@\s]+@github\.com/", re.IGNORECASE),
    re.compile(r"(github_pat_[A-Za-z0-9_]+)"),
    re.compile(r"(gh[opsu]_[A-Za-z0-9_]+)"),
]


def _sanitize_git_output(text: str) -> str:
    cleaned = text or ""
    for pattern in SECRET_PATTERNS:
        if "github.com" in pattern.pattern:
            cleaned = pattern.sub("https://***@github.com/", cleaned)
        else:
            cleaned = pattern.sub("[redacted-token]", cleaned)
    return cleaned


def _git(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(WIKI_ROOT), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _remote_exists(name: str) -> bool:
    return _git(["remote", "get-url", name], timeout=15).returncode == 0


def _run_git_step(args: list[str], *, timeout: int = 60, notify_on_failure: bool = True) -> bool:
    result = _git(args, timeout=timeout)
    if result.returncode == 0:
        return True
    output = _sanitize_git_output((result.stderr or "") + (result.stdout or ""))
    msg = (
        f"Auto-checkpoint mirror step failed: git {' '.join(args)} "
        f"(exit={result.returncode})\n{output[-800:]}"
    )
    print(f"[auto_checkpoint] {msg}", flush=True)
    if notify_on_failure:
        _telegram_notify(f"⚠️ {msg}")
    return False


def _post_checkpoint_sync(ts: str) -> None:
    """Mirror fresh checkpoint commits to VPS origin and GitHub without force-push.

    Claude Code routines clone GitHub, while the live wiki writes to Air/VPS.
    This sync keeps GitHub current after HANDOFF writes. If the routine has
    already pushed proof-card commits to GitHub, rebase local checkpoint commits
    on top first instead of overwriting them.
    """
    try:
        status = _git(["status", "--porcelain"], timeout=15)
        if status.returncode != 0:
            output = _sanitize_git_output((status.stderr or "") + (status.stdout or ""))
            msg = f"Auto-checkpoint mirror skipped at {ts}: git status failed\n{output[-800:]}"
            print(f"[auto_checkpoint] {msg}", flush=True)
            _telegram_notify(f"⚠️ {msg}")
            return
        if status.stdout.strip():
            msg = (
                f"Auto-checkpoint mirror skipped at {ts}: wiki worktree not clean after "
                "HANDOFF write; leaving sync to auto-sync."
            )
            print(f"[auto_checkpoint] {msg}\n{status.stdout}", flush=True)
            _telegram_notify(f"⚠️ {msg}")
            return

        if not _run_git_step(["fetch", "origin", "main"], timeout=120):
            return
        if not _run_git_step(["pull", "--rebase", "--autostash", "origin", "main"], timeout=180):
            return

        if not _remote_exists("github"):
            if _run_git_step(["push", "origin", "main"], timeout=180):
                print(f"[auto_checkpoint] Mirror sync at {ts}: pushed origin; github remote missing", flush=True)
            return

        if not _run_git_step(["fetch", "github", "main"], timeout=180):
            return

        github_ref = _git(["rev-parse", "--verify", "github/main"], timeout=15)
        if github_ref.returncode == 0:
            ancestor = _git(["merge-base", "--is-ancestor", "github/main", "HEAD"], timeout=15)
            if ancestor.returncode != 0:
                rebase = _git(["rebase", "github/main"], timeout=180)
                if rebase.returncode != 0:
                    _git(["rebase", "--abort"], timeout=30)
                    output = _sanitize_git_output((rebase.stderr or "") + (rebase.stdout or ""))
                    msg = (
                        f"Auto-checkpoint GitHub mirror blocked at {ts}: "
                        f"rebase on github/main failed\n{output[-800:]}"
                    )
                    print(f"[auto_checkpoint] {msg}", flush=True)
                    _telegram_notify(f"⚠️ {msg}")
                    return

        if not _run_git_step(["push", "origin", "main"], timeout=180):
            return
        if not _run_git_step(["push", "github", "main"], timeout=180):
            return
        print(f"[auto_checkpoint] Mirror sync at {ts}: origin + github main updated", flush=True)
    except Exception as e:
        msg = f"Auto-checkpoint mirror sync crashed at {ts}: {e}"
        print(f"[auto_checkpoint] {msg}", flush=True)
        _telegram_notify(f"⚠️ {msg}")


def _telegram_notify(text: str) -> None:
    # AP-4 gate (session 68p/70, musk-algorithm v1.2.0) — block deference-dressed-as-autonomy
    import os as _os_ap4, subprocess as _sub_ap4
    if not _os_ap4.environ.get("AUTONOMY_BYPASS"):
        _det_ap4 = "/Users/madia/nous-agaas/tools/test_agent_autonomy.sh"
        if _os_ap4.path.exists(_det_ap4):
            try:
                _r_ap4 = _sub_ap4.run(["bash", _det_ap4, "--stdin"], input=text, capture_output=True, text=True, timeout=5)
                if _r_ap4.returncode != 0:
                    print(f"[{__name__}] AP-4 BLOCKED: {text[:100]!r}")
                    return None
            except Exception:
                pass
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


def _task_result_head(path: Path) -> str:
    try:
        in_task = False
        with path.open() as fh:
            for ln in fh:
                s = ln.strip()
                if s.startswith("## Task"):
                    in_task = True
                    continue
                if in_task and s:
                    return s[:80]
    except Exception:
        pass
    return ""


def _task_result_timestamp(path: Path) -> datetime | None:
    match = re.match(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})-", path.name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d-%H-%M-%S").replace(tzinfo=KZ_TZ)
    except ValueError:
        return None


def _is_daily_0300_result(path: Path, head: str) -> bool:
    return DAILY_0300_SLUG in path.name or head == DAILY_0300_TASK


def _is_canonical_daily_0300_result(path: Path) -> bool:
    ts = _task_result_timestamp(path)
    if ts is None:
        return False
    minute_of_day = ts.hour * 60 + ts.minute
    return (2 * 60 + 55) <= minute_of_day <= (3 * 60 + 10)


def _format_task_result_line(path: Path, head: str) -> str:
    try:
        ts = datetime.fromtimestamp(path.stat().st_mtime, KZ_TZ).strftime("%Y-%m-%d %H:%M KZT")
        return (
            f"- `pages/task-results/{path.name}` @ {ts} — {head}"
            if head
            else f"- `pages/task-results/{path.name}` @ {ts}"
        )
    except Exception:
        return f"- `pages/task-results/{path.name}`"


def _recent_task_results(n: int = 8) -> str:
    # Pre-compute markdown bullet list of N most-recent task-results so the
    # checkpoint agent can cite real filenames in-context. Fixes day-8+
    # "missing pages/task-results/" sticky-blocked symptom: file-less LiteLLM
    # direct paths (opus/sonnet/grok-reasoning) had no way to read files;
    # openclaw paths had a CWD mismatch (workspace dir, not wiki). This
    # injects evidence INTO the prompt so all routing paths see it equally.
    # See pages/skills/factory-ops/SKILL.md AP-29.
    try:
        files = sorted(TASK_RESULTS_DIR.glob("*.md"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:
        return "(task-results listing failed)"
    if not files:
        return "(no recent task-results found)"
    normal: list[tuple[Path, str]] = []
    canonical_daily: list[tuple[Path, str]] = []
    daily_anomalies: list[tuple[Path, str]] = []
    for f in files[: max(n * 6, 50)]:
        head = _task_result_head(f)
        if _is_daily_0300_result(f, head):
            if _is_canonical_daily_0300_result(f):
                canonical_daily.append((f, head))
            else:
                daily_anomalies.append((f, head))
            continue
        normal.append((f, head))

    selected = normal[:n]
    if canonical_daily:
        # Always surface the latest canonical DAILY_0300_OK in the prompt.
        # Without this, it is silently excluded when >=n normal results exist,
        # causing the LLM to falsely report the signal as not observed.
        selected.append(canonical_daily[0])
    elif len(selected) < n:
        selected.extend(canonical_daily[: n - len(selected)])

    lines = [_format_task_result_line(f, head) for f, head in selected]
    if daily_anomalies:
        latest_ts = _task_result_timestamp(daily_anomalies[0][0])
        latest = latest_ts.strftime("%Y-%m-%d %H:%M KZT") if latest_ts else "unknown time"
        lines.append(
            f"- DAILY_0300_OK anomaly: {len(daily_anomalies)} non-03:00 repeats omitted "
            f"from checkpoint evidence (latest {latest})."
        )
    if not lines:
        return "(no recent task-results found)"
    return "\n".join(lines)


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


def _write_progress_handoff(ts: str, wiki_path: str, before_latest: str) -> bool:
    # AP-31 (s73, 2026-04-25): orchestrator owns file I/O. NON_OPENCLAW_MODELS
    # are file-less — they cannot write. Prior behavior asked the agent to
    # "save it as ... via write-back" and the agent CLAIMED success without
    # actually writing. Now: agent returns body text only; orchestrator
    # extracts response from the new task-result and writes it to the
    # progress/ path. Closes the agent-fabricated-write honesty gap.
    try:
        new_latest = latest_task_result()
        if not new_latest or new_latest == before_latest:
            print(f"[auto_checkpoint] AP-31: no new task-result after run_task; skipping HANDOFF write")
            return False
        src = TASK_RESULTS_DIR / new_latest
        raw = src.read_text()
        if "## Response\n\n" in raw:
            body = raw.split("## Response\n\n", 1)[1].strip()
        else:
            body = raw.strip()
        date_str = datetime.now(KZ_TZ).strftime("%Y-%m-%d")
        handoff_path = WIKI_ROOT / wiki_path
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            f"---\ntype: progress\n"
            f"id: HANDOFF-AUTO-{ts}\n"
            f'title: "Factory auto-checkpoint {ts} KZT"\n'
            f"tags: [handoff, auto-checkpoint, ap-31-orchestrator-write]\n"
            f"date: {date_str}\nstatus: auto\n"
            f"source: auto_checkpoint.py extracts run_task.py response (AP-31)\n"
            f"---\n\n# Factory auto-checkpoint — {ts} KZT\n\n"
            f"_Generated by `auto_checkpoint.py` extracting agent response from `{src.name}`._\n\n"
            f"{body}\n"
        )
        handoff_path.write_text(content)
        # Best-effort git commit; do NOT fail the checkpoint if git is racy
        _git(["add", wiki_path], timeout=15)
        _git(["commit", "-m", f"auto-checkpoint: {ts} HANDOFF (AP-31 orchestrator-written)"], timeout=15)
        print(f"[auto_checkpoint] AP-31 wrote HANDOFF: {wiki_path} ({len(content)} chars)")
        return True
    except Exception as e:
        print(f"[auto_checkpoint] AP-31 HANDOFF write failed: {e}")
        return False


def checkpoint() -> None:
    state = _load_state()
    latest = latest_task_result()
    fire_ts = datetime.now(KZ_TZ).strftime("%Y-%m-%d-%H-%M")
    if latest and latest == state.get("last_task_result"):
        print(f"[auto_checkpoint] SKIP: no new task-results since last checkpoint ({latest})")
        state["last_fire"] = fire_ts
        state["last_decision"] = "skip"
        state["last_skip_reason"] = f"no new task-results since {latest}"
        _save_state(state)
        return

    ts = fire_ts
    wiki_path = f"pages/progress/HANDOFF-AUTO-{ts}.md"
    recent = _recent_task_results(n=8)
    prompt = (
        f"Compose a concise factory checkpoint body. The orchestrator will save it as {wiki_path} (AP-31 — do not claim to write the file yourself).\n\n"
        f"Recent task-results in this wiki (cite at least 3 by filename + timestamp when relevant):\n\n"
        f"{recent}\n\n"
        "Signal hygiene: `DAILY_0300_OK` is canonical daily proof only near 03:00 KZT. "
        "Non-03:00 repeats are anomalies/noise, not scheduled-task proof. "
        "Include: (1) systems verified working today, (2) top 3 next actions, "
        "(3) active blockers with owners. Under 150 lines. Facts only. "
        "Do NOT fabricate filenames; cite ONLY paths from the list above. "
        "Return only the markdown body — orchestrator handles the file write."
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
        state["last_fire"] = ts
        state["last_decision"] = "timeout"
        state["last_error"] = f"timeout after {TIMEOUT}s; log={log_path}"
        _save_state(state)
        return

    if result.returncode == 0:
        _persist_run_log(ts, result.stdout, result.stderr, 0, "ok")
        # AP-31: orchestrator extracts agent body and writes the actual HANDOFF file
        wrote = _write_progress_handoff(ts, wiki_path, before_latest=latest)
        if wrote:
            _post_checkpoint_sync(ts)
        print(f"[auto_checkpoint] DONE: {wiki_path} (HANDOFF written: {wrote})", flush=True)
        state["last_checkpoint"] = ts
        state["last_task_result"] = latest_task_result() or latest
        state["last_fire"] = ts
        state["last_decision"] = "done"
        state.pop("last_skip_reason", None)
        _save_state(state)
        if os.environ.get("CHECKPOINT_NOTIFY_SUCCESS", "0") == "1":
            _telegram_notify(f"✅ Auto-checkpoint saved: {wiki_path}")
        return

    # Non-zero returncode path — real error. Pull the actual error lines, not
    # the first 300 chars of INFO/WARNING noise (LESSON-108).
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
    state["last_fire"] = ts
    state["last_decision"] = "error"
    state["last_error"] = f"exit={result.returncode}; log={log_path}"
    _save_state(state)


if __name__ == "__main__":
    checkpoint()
