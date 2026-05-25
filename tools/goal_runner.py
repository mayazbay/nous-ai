#!/usr/bin/env python3
"""goal_runner.py — Goal Mode v1 cycle engine (s108-mac, 2026-05-10)

Every 4 hours (via launchd com.nous.goal-cycle), and immediately when
command_center.py kicks that launchd job after /goal creation, scans the wiki
for active GOAL pages and dispatches one progress worker per goal.

Goal pages live at:
  wiki/pages/projects/GOAL-YYYYMMDD-HHMMSS-<slug>.md

Frontmatter keys used:
  status: active | paused | done | abandoned
  deadline: YYYY-MM-DD  (or "none")
  last_progress_at: YYYY-MM-DD HH:MM  (or null)

Each cycle:
  1. Find all GOAL-*.md pages with status: active
  2. For each goal, dispatch run_task.py with a targeted progress prompt
  3. goal_runner.py appends the worker result to the GOAL page + commits
  4. Rebase/push all changes to VPS bare repo
  5. Send Telegram digest summary to Madi
"""

from contextlib import contextmanager
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, "/Users/madia/nous-agaas")
try:
    from langsmith_observer import emit_event as _langsmith_emit, text_digest as _langsmith_text_digest
except Exception:
    _langsmith_emit = None
    _langsmith_text_digest = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s goal-runner %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/Users/madia/nous-agaas/logs/goal-runner.log", mode="a"),
    ],
)
log = logging.getLogger(__name__)

WIKI = Path("/Users/madia/nous-agaas/wiki")
GOALS_DIR = WIKI / "pages" / "projects"
RUN_TASK = "/Users/madia/nous-agaas/run_task.py"
VENV_PYTHON = "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
TG_SEND = "/Users/madia/nous-agaas/tools/tg_send.sh"
ALMATY_TZ = timezone(timedelta(hours=5))
MADI_CHAT_ID = "110793056"
GOAL_CYCLE_LOCK = Path("/Users/madia/nous-agaas/logs/goal-cycle.lock")
GIT_INDEX_LOCK = WIKI / ".git" / "index.lock"
MAX_GOAL_CONTEXT_CHARS = int(os.environ.get("NOUS_GOAL_CONTEXT_CHARS", "12000"))
GOAL_WORKER_MODEL = os.environ.get("NOUS_GOAL_WORKER_MODEL", "grok-reasoning").strip()


def _load_env() -> dict:
    env = dict(os.environ)
    env_file = Path("/Users/madia/nous-agaas/.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env.setdefault(k.strip(), v.strip())
    return env


def _now_almaty() -> datetime:
    return datetime.now(tz=ALMATY_TZ)


def _cycle_lock_pid() -> int | None:
    try:
        text = GOAL_CYCLE_LOCK.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"\bpid=(\d+)\b", text)
    return int(match.group(1)) if match else None


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _tg_send(text: str, env: dict) -> None:
    try:
        subprocess.run(
            ["bash", TG_SEND, text],
            env=env, capture_output=True, timeout=20,
        )
        log.info(f"tg_send: {text[:80]}")
    except Exception as e:
        log.warning(f"tg_send failed: {e}")


@contextmanager
def _cycle_lock():
    """Prevent overlapping launchd kickstarts from processing the same goals."""
    GOAL_CYCLE_LOCK.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(GOAL_CYCLE_LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        try:
            age = _now_almaty().timestamp() - GOAL_CYCLE_LOCK.stat().st_mtime
        except OSError:
            age = 0
        lock_pid = _cycle_lock_pid()
        if lock_pid is not None and not _pid_is_alive(lock_pid):
            log.warning(f"removed stale goal cycle lock pid={lock_pid} age={age:.0f}s")
        elif age < 1800:
            raise RuntimeError(f"goal cycle already running (lock age {age:.0f}s)")
        GOAL_CYCLE_LOCK.unlink(missing_ok=True)
        fd = os.open(str(GOAL_CYCLE_LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)

    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(f"pid={os.getpid()} ts={_now_almaty().isoformat()}\n")
    try:
        yield
    finally:
        GOAL_CYCLE_LOCK.unlink(missing_ok=True)


def _parse_frontmatter(text: str) -> dict:
    """Parse simple YAML frontmatter (key: value pairs, no nesting)."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm: dict = {}
    for line in parts[1].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def _load_active_goals() -> list[dict]:
    """Return list of dicts for GOAL pages with status: active."""
    goals = []
    for path in sorted(GOALS_DIR.glob("GOAL-*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = _parse_frontmatter(text)
        if fm.get("status", "active").lower() != "active":
            continue
        goals.append({
            "path": path,
            "rel_path": str(path.relative_to(WIKI)),
            "id": fm.get("id", path.stem),
            "title": fm.get("title", path.stem),
            "deadline": fm.get("deadline", "none"),
            "last_progress_at": fm.get("last_progress_at", "null"),
            "text": text,
        })
    return goals


def _goal_page_context(goal: dict) -> str:
    text = goal.get("text", "")
    if len(text) <= MAX_GOAL_CONTEXT_CHARS:
        return text
    return (
        f"[truncated to last {MAX_GOAL_CONTEXT_CHARS} chars; older context omitted]\n"
        + text[-MAX_GOAL_CONTEXT_CHARS:]
    )


def _build_worker_prompt(goal: dict, now_str: str) -> str:
    return f"""You are a goal-cycle worker in the Nous AGaaS substrate. Produce ONE concrete progress slice for the goal below.

## Goal
{goal["title"]}

## Deadline
{goal["deadline"]}

## Last progress
{goal["last_progress_at"]}

## GOAL page path (relative to wiki root)
{goal["rel_path"]}
Full path: /Users/madia/nous-agaas/wiki/{goal["rel_path"]}

## GOAL page context (inline source of truth)
The worker route may not have filesystem tools. Use this inline page content as the source of truth before choosing the slice.

{_goal_page_context(goal)}

## Instructions

1. Read the inline GOAL page context above to understand what has already been done (## Progress log section). Do not claim you read files unless the context was provided inline here.
2. Produce EXACTLY ONE concrete progress slice. Choose the highest-leverage text-only output you can truthfully produce from the context you have:
   - Research synthesis from the injected substrate context
   - A concrete acceptance-criteria bullet set
   - A command checklist with expected pass/fail outputs
   - A draft artifact section
   - A blocker statement with evidence if execution requires shell/tools you do not have
3. Reply with ONE sentence in past tense summarising the slice. Do not say "I will", "I'll", "let me", or claim you edited files.

IMPORTANT: Do EXACTLY ONE slice. Do not try to complete the entire goal in one cycle.
IMPORTANT: goal_runner.py, not you, will update and commit the GOAL page.
"""


def _worker_command(goal: dict, prompt: str) -> list[str]:
    cmd = [VENV_PYTHON, RUN_TASK, "--source", f"goal-cycle:{goal['id']}"]
    if GOAL_WORKER_MODEL:
        cmd.extend(["--model", GOAL_WORKER_MODEL])
    cmd.append(prompt)
    return cmd


def _dispatch_worker(goal: dict, now_str: str, env: dict) -> str:
    """Run run_task.py for one goal. Returns first line of response."""
    prompt = _build_worker_prompt(goal, now_str)
    log.info(f"Dispatching worker for: {goal['id']} model={GOAL_WORKER_MODEL or 'model-escalator'}")
    try:
        result = subprocess.run(
            _worker_command(goal, prompt),
            env=env,
            capture_output=True,
            text=True,
            timeout=660,
        )
        output = (result.stdout or result.stderr or "(no output)").strip()
        log.info(f"Worker done for {goal['id']}: {output[:120]}")
        _observe_goal_event(
            "nous.goal.worker",
            goal,
            now_str,
            status="ok" if result.returncode == 0 else "error",
            outputs={"returncode": result.returncode, "output": _digest(output)},
        )
        return output[:800]
    except subprocess.TimeoutExpired:
        _observe_goal_event("nous.goal.worker", goal, now_str, status="timeout", outputs={"status": "timeout"})
        return "⏱ Worker timed out after 11 minutes."
    except Exception as e:
        log.error(f"Worker error for {goal['id']}: {e}")
        _observe_goal_event("nous.goal.worker", goal, now_str, status="error", outputs={"error": str(e)[:300]})
        return f"❌ Worker error: {e}"


def _digest(text: str):
    return _langsmith_text_digest(text) if _langsmith_text_digest else str(text)[:200]


def _observe_goal_event(
    name: str,
    goal: dict,
    now_str: str,
    status: str,
    outputs: dict | None = None,
) -> None:
    if _langsmith_emit is None:
        return
    try:
        _langsmith_emit(
            name,
            inputs={"goal_title": _digest(goal.get("title", ""))},
            outputs=outputs or {"status": status},
            metadata={
                "goal_id": goal.get("id"),
                "goal_path": goal.get("rel_path"),
                "deadline": goal.get("deadline"),
                "cycle_time": now_str,
            },
            tags=["nous", "goal-mode", str(goal.get("id") or "unknown")],
            status=status,
        )
    except Exception as exc:
        log.warning("langsmith goal observer failed (non-fatal): %s", exc)


def _progress_summary(progress: str, limit: int = 700) -> str:
    lines = [line.strip() for line in progress.splitlines() if line.strip()]
    summary = " ".join(lines) if lines else "(empty worker response)"
    summary = re.sub(r"\s+", " ", summary)
    if re.search(r"\b(i will|i'll|let me|going to)\b", summary, flags=re.IGNORECASE):
        summary = "Worker returned future-intent language instead of completed progress: " + summary
    return summary[:limit].rstrip()


def _update_goal_page(goal: dict, now_str: str, progress: str) -> None:
    path = goal["path"]
    text = path.read_text(encoding="utf-8")
    summary = _progress_summary(progress)
    text = re.sub(r"(?m)^last_progress_at:.*$", f"last_progress_at: {now_str[:16]}", text, count=1)

    entry = f"- **{now_str}** — {summary}\n"
    if "## Progress log" in text and "## Status" in text:
        text = text.replace("## Status", entry + "\n## Status", 1)
    else:
        text += f"\n\n## Progress log\n\n{entry}\n"

    status = (
        "Active. Last goal-cycle wrote a durable progress entry. "
        "Completion remains operator-controlled via frontmatter status."
    )
    if "## Status" in text:
        text = re.sub(r"(?s)## Status\n\n.*$", f"## Status\n\n{status}\n", text, count=1)
    else:
        text += f"\n\n## Status\n\n{status}\n"
    path.write_text(text, encoding="utf-8")


def _git_index_lock_writer_held() -> bool:
    result = subprocess.run(
        ["lsof", str(GIT_INDEX_LOCK)],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines()[1:]:
        cols = line.split()
        if len(cols) >= 4 and ("w" in cols[3] or "u" in cols[3]):
            return True
    return False


def _clear_stale_git_index_lock(max_age_seconds: int = 20) -> bool:
    if not GIT_INDEX_LOCK.exists():
        return False
    try:
        age = _now_almaty().timestamp() - GIT_INDEX_LOCK.stat().st_mtime
    except OSError:
        age = 0
    if age < max_age_seconds or _git_index_lock_writer_held():
        return False
    GIT_INDEX_LOCK.unlink(missing_ok=True)
    log.warning(f"removed stale git index lock age={age:.0f}s")
    return True


def _git_run(
    args: list[str],
    timeout: int,
    ok_returncodes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess:
    for attempt in range(6):
        _clear_stale_git_index_lock()
        proc = subprocess.run(
            ["git", "-C", str(WIKI), "-c", "core.hooksPath=/dev/null", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode in ok_returncodes:
            return proc
        stderr = proc.stderr or proc.stdout or ""
        if "index.lock" in stderr and attempt < 5:
            log.warning(f"git {' '.join(args)} hit index.lock; retrying attempt={attempt + 1}")
            time.sleep(2 + attempt * 2)
            continue
        raise subprocess.CalledProcessError(proc.returncode, proc.args, proc.stdout, proc.stderr)
    raise RuntimeError(f"git {' '.join(args)} failed after retries")


def _git_short(ref: str = "HEAD") -> str:
    proc = _git_run(["rev-parse", "--short", ref], timeout=30)
    return proc.stdout.strip()


def _git_fetch_remote_main_oid(remote: str = "origin", timeout: int = 90) -> str:
    _git_run(["fetch", remote, f"main:refs/remotes/{remote}/main"], timeout=timeout)
    proc = _git_run(["rev-parse", "--verify", f"refs/remotes/{remote}/main"], timeout=30)
    return proc.stdout.strip()


def _git_rebase_onto_remote_main(remote: str = "origin", timeout: int = 90) -> None:
    """Fetch one remote main ref and rebase onto that exact OID.

    `git pull --rebase <remote> main` is too compound for Air's multi-writer
    wiki: with wildcard fetch refspecs and concurrent writers it can fail with
    "Cannot rebase onto multiple branches." Exact-OID rebase keeps the target
    unambiguous.
    """
    before = _git_short()
    target = _git_fetch_remote_main_oid(remote, timeout=timeout)
    contains = _git_run(
        ["merge-base", "--is-ancestor", target, "HEAD"],
        timeout=30,
        ok_returncodes=(0, 1),
    )
    if contains.returncode != 0:
        _git_run(["rebase", target], timeout=timeout)

    target2 = _git_fetch_remote_main_oid(remote, timeout=timeout)
    if target2 != target:
        contains2 = _git_run(
            ["merge-base", "--is-ancestor", target2, "HEAD"],
            timeout=30,
            ok_returncodes=(0, 1),
        )
        if contains2.returncode != 0:
            _git_run(["rebase", target2], timeout=timeout)

    after = _git_short()
    log.info(f"exact rebase {remote}/main {before}->{after}")


def _git_push_with_exact_rebase(remote: str = "origin", timeout: int = 90) -> None:
    _git_rebase_onto_remote_main(remote=remote, timeout=timeout)
    try:
        _git_run(["push", remote, "main"], timeout=timeout)
    except subprocess.CalledProcessError as e:
        detail = e.stderr or e.stdout or ""
        if "non-fast-forward" not in detail and "fetch first" not in detail:
            raise
        _git_rebase_onto_remote_main(remote=remote, timeout=timeout)
        _git_run(["push", remote, "main"], timeout=timeout)


def _git_commit_and_push_goal_updates(rel_paths: list[str]) -> None:
    if not rel_paths:
        return
    try:
        _git_run(["add", *rel_paths], timeout=30)
        diff = _git_run(["diff", "--cached", "--quiet", "--", *rel_paths],
                        timeout=30, ok_returncodes=(0, 1))
        if diff.returncode == 0:
            log.info("no GOAL page changes to commit")
            return
        _git_run(["commit", "--no-verify", "-m", "goal-cycle: update active goals"], timeout=60)
        _git_push_with_exact_rebase(remote="origin", timeout=90)
        log.info("goal updates committed and pushed")
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.stdout or str(e)).strip()
        log.warning(f"goal update git write-back failed: {detail[:300]}")
    except Exception as e:
        log.warning(f"goal update git write-back failed: {e}")


def run_cycle(env: dict) -> None:
    try:
        lock = _cycle_lock()
        lock.__enter__()
    except RuntimeError as e:
        log.warning(str(e))
        return

    try:
        now = _now_almaty()
        now_str = now.strftime("%Y-%m-%d %H:%M KZT")
        log.info(f"=== Goal cycle starting at {now_str} ===")

        goals = _load_active_goals()
        if not goals:
            log.info("No active goals. Cycle done.")
            return

        log.info(f"Found {len(goals)} active goal(s)")
        if _langsmith_emit is not None:
            try:
                _langsmith_emit(
                    "nous.goal.cycle",
                    inputs={"active_goals": len(goals)},
                    outputs={"status": "started"},
                    metadata={"cycle_time": now_str},
                    tags=["nous", "goal-mode", "cycle"],
                    status="started",
                )
            except Exception as exc:
                log.warning("langsmith cycle observer failed (non-fatal): %s", exc)
        results: list[tuple[str, str]] = []

        for goal in goals:
            progress = _dispatch_worker(goal, now_str, env)
            _update_goal_page(goal, now_str, progress)
            _git_commit_and_push_goal_updates([goal["rel_path"]])
            results.append((goal["title"], progress))

        route = GOAL_WORKER_MODEL or "model-escalator"
        lines = [
            f"🎯 Goal cycle {now_str} — {len(results)} goal(s):",
            f"Маршрут: {route} (reasoning слой); GPT-5.5 — через /codex для явной эскалации.",
        ]
        for title, progress in results:
            short_title = title[:60] + ("…" if len(title) > 60 else "")
            first_line = _progress_summary(progress, limit=200)
            lines.append(f"\n• <b>{short_title}</b>\n  {first_line}")

        _tg_send("\n".join(lines), env)
        if _langsmith_emit is not None:
            try:
                _langsmith_emit(
                    "nous.goal.cycle",
                    inputs={"active_goals": len(results)},
                    outputs={"status": "complete", "digest": _digest("\n".join(lines))},
                    metadata={"cycle_time": now_str},
                    tags=["nous", "goal-mode", "cycle"],
                    status="ok",
                )
            except Exception as exc:
                log.warning("langsmith cycle observer failed (non-fatal): %s", exc)
        log.info(f"=== Goal cycle complete ({len(results)} goals processed) ===")
    finally:
        lock.__exit__(None, None, None)


if __name__ == "__main__":
    run_cycle(_load_env())
