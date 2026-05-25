#!/usr/bin/env python3
"""
run_task.py — OpenClaw agent task runner

Sends a task to the Nous agent via the OpenClaw gateway.
Integrates ACTIVE-TASK.md checkpoint (crash recovery) and 15-iteration
budget kill switch via active_task.ActiveTask.

Usage:
  python3 run_task.py "Do this task"
  python3 run_task.py --session abc123 "Continue this"
  echo "task text" | python3 run_task.py

Exit codes: 0=success, 1=agent error, 2=system error
"""

import json
import logging
import os
import subprocess
import sys
import re
import time
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/Users/madia/nous-agaas")
from active_task import ActiveTask
from context_injector import get_context
from model_escalator import ModelEscalator
try:
    from langsmith_observer import emit_event as _langsmith_emit, text_digest as _langsmith_text_digest
except Exception:
    _langsmith_emit = None
    _langsmith_text_digest = None

KZ_TZ = timezone(timedelta(hours=5))
LOG_FILE = "/Users/madia/nous-agaas/logs/run_task.log"
CONTAINER = "openclaw"
AGENT_ID = "nous"
DEFAULT_TIMEOUT = 600  # seconds
CHECKPOINT_FILE = "/Users/madia/nous-agaas/ACTIVE-TASK.md"
MAX_ITERATIONS = 15

WIKI_PATH = "/Users/madia/nous-agaas/wiki"
TASK_RESULTS_DIR = f"{WIKI_PATH}/pages/task-results"
WRITEBACK_LOCK_TIMEOUT = int(os.environ.get("NOUS_RUN_TASK_WRITEBACK_LOCK_TIMEOUT", "180"))
WRITEBACK_LOCK_STALE_AFTER = int(os.environ.get("NOUS_RUN_TASK_WRITEBACK_LOCK_STALE_AFTER", "600"))
WRITEBACK_GIT_TIMEOUT = int(os.environ.get("NOUS_RUN_TASK_GIT_TIMEOUT", "90"))

LITELLM_URL = "http://127.0.0.1:4000/v1/chat/completions"
def _read_env_value(path: str, key: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == key:
                    return v.strip().strip("\"").strip("'")
    except OSError:
        return ""
    return ""


def _litellm_master_key() -> str:
    return os.environ.get("LITELLM_MASTER_KEY", "") or _read_env_value(
        "/Users/madia/nous-agaas/litellm/.env", "LITELLM_MASTER_KEY"
    )


LITELLM_KEY = _litellm_master_key()
# Models that bypass OpenClaw and call LiteLLM directly.
#
# Important distinction:
# - Explicit --agent routes (for example grok-ceo) must stay inside OpenClaw
#   because the selected unit is the agent, not the escalator's model.
# - Default scheduled work may use direct DeepSeek so selected_model == executed_model
#   instead of silently running the default OpenClaw agent's Opus model.
DIRECT_LITELLM_MODELS = {
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "glm-5.1",
    "grok-reasoning",
    "sonnet",
    "opus",
}
NON_OPENCLAW_MODELS = DIRECT_LITELLM_MODELS  # backwards-compatible name

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ]
)
log = logging.getLogger(__name__)


def _ensure_log_dir():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


# ─── T14-γ: async-await shim (SPEC-MULTI-MODEL-CEO-HIERARCHY-V1 Phase 3).
# OpenClaw `agent --local` exits on first turn-yield. When parent (grok-ceo)
# calls sessions_spawn + sessions_yield awaiting child announce, proc.stdout
# returns JSON with payloads=[] even though the session jsonl receives the
# final assistant text shortly after. Poll session jsonl for text.

def _find_agent_session_jsonl(agent_id: str, container: str = "openclaw"):
    """Find the current most-recently-updated session jsonl path inside container."""
    try:
        r = subprocess.run(
            ["/usr/local/bin/docker", "exec", container,
             "openclaw", "sessions", "--agent", agent_id, "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
        sessions = data.get("sessions", [])
        if not sessions:
            return None
        latest = max(sessions, key=lambda s: s.get("updatedAt", 0))
        sid = latest.get("sessionId")
        if not sid:
            return None
        return f"/home/node/.openclaw/agents/{agent_id}/sessions/{sid}.jsonl"
    except Exception:
        return None


def _extract_latest_assistant_text_from_jsonl(
    jsonl_container_path: str,
    since_line: int = 0,
    container: str = "openclaw",
):
    """Read session jsonl from since_line. Return (latest_text, new_line_count)."""
    try:
        r = subprocess.run(
            ["/usr/local/bin/docker", "exec", container, "cat", jsonl_container_path],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return ("", since_line)
        lines = r.stdout.splitlines()
        new_count = len(lines)
        if new_count <= since_line:
            return ("", new_count)
        latest_text = ""
        for line in lines[since_line:]:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("type") != "message":
                continue
            msg = e.get("message", {})
            if msg.get("role") != "assistant":
                continue
            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    t = block.get("text", "")
                    if t:
                        latest_text = t
        return (latest_text, new_count)
    except Exception:
        return ("", since_line)


def _poll_for_async_announce(agent_id: str, since_line: int,
                              max_wait_seconds: int = 90,
                              poll_interval: float = 0.5) -> str:
    """Poll until new assistant text appears in session jsonl."""
    import time
    jsonl = _find_agent_session_jsonl(agent_id)
    if not jsonl:
        return ""
    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        text, _ = _extract_latest_assistant_text_from_jsonl(jsonl, since_line=since_line)
        if text:
            return text
        time.sleep(poll_interval)
    return ""


def _snapshot_agent_session_line_count(agent_id: str) -> int:
    """Return current session jsonl line count, or 0 if none."""
    jsonl = _find_agent_session_jsonl(agent_id)
    if not jsonl:
        return 0
    _, cnt = _extract_latest_assistant_text_from_jsonl(jsonl, since_line=0)
    return cnt


def _append_log(entry: dict):
    _ensure_log_dir()
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _bridge_to_tier_log(entry)
    _bridge_to_langsmith(entry)


_PRICE_PER_M = {
    "deepseek-v4-flash": (0.435, 0.435),
    "deepseek-v4-pro": (0.435, 0.87),
    "deepseek-v4-pro:nitro": (0.435, 0.87),
    "grok-reasoning": (3.0, 15.0),
    "grok-code-fast": (0.5, 1.5),
    "opus": (15.0, 75.0),
    "claude-opus-4-7": (15.0, 75.0),
    "sonnet": (3.0, 15.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "sonnet-4-5-thinking": (3.0, 15.0),
    "haiku-4-5": (1.0, 5.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "glm-5.1": (0.5, 1.5),
    "glm-4.5-flash": (0.0, 0.0),
    "gpt-5.5": (5.0, 15.0),
}


def _estimate_cost(entry: dict) -> float:
    model = (entry.get("model") or entry.get("model_selected") or "").lower()
    in_p, out_p = _PRICE_PER_M.get(model, (0.0, 0.0))
    in_tok = entry.get("input_tokens", 0) or 0
    out_tok = entry.get("output_tokens", 0) or 0
    return round(in_tok / 1e6 * in_p + out_tok / 1e6 * out_p, 6)


def _bridge_to_tier_log(entry: dict):
    corr = os.environ.get("NOUS_CORRELATION_ID", "")
    if not corr:
        return
    try:
        from tier_log import append as _tier_append
        _tier_append(
            correlation_id=corr,
            tier=2,
            model=entry.get("model") or entry.get("model_selected", "unknown"),
            tokens_in=entry.get("input_tokens", 0) or 0,
            tokens_out=entry.get("output_tokens", 0) or 0,
            latency_ms=entry.get("duration_ms", 0) or 0,
            cost_est=_estimate_cost(entry),
            decision=entry.get("status", ""),
        )
    except Exception as e:
        log.warning("tier_log bridge failed (non-fatal): %s", e)


def _bridge_to_langsmith(entry: dict):
    if _langsmith_emit is None:
        return
    try:
        message = entry.get("message", "")
        inputs = (
            {"message": _langsmith_text_digest(message)}
            if _langsmith_text_digest is not None
            else {"message_preview": str(message)[:200]}
        )
        _langsmith_emit(
            "nous.run_task",
            inputs=inputs,
            outputs={
                "status": entry.get("status", "unknown"),
                "model": entry.get("model") or entry.get("model_selected"),
                "execution_path": entry.get("execution_path"),
            },
            metadata={k: v for k, v in entry.items() if k != "message"},
            tags=[
                "nous",
                "run_task",
                str(entry.get("execution_path") or "unknown"),
                str(entry.get("source") or "no-source"),
            ],
            status=str(entry.get("status", "unknown")),
        )
    except Exception as e:
        log.warning("langsmith observer bridge failed (non-fatal): %s", e)


def _frontmatter_string(value: str) -> str:
    return json.dumps(str(value).replace("\n", " ")[:200], ensure_ascii=False)


def run_task(
    message: str,
    session_id: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    model: str | None = None,
    agent_id: str = AGENT_ID,
) -> dict:
    """
    Send a task to the Nous agent. Returns parsed JSON result.
    Raises RuntimeError on failure.

    Args:
        model: Override model. If None, the ModelEscalator picks based on history.
               Pass "deepseek-v4-flash", "deepseek-v4-pro", "sonnet", or "opus" to force a specific tier.
    """
    _corr = os.environ.get("NOUS_CORRELATION_ID", "")
    cmd = [
        "/usr/local/bin/docker", "exec",
        "-e", f"NOUS_CORRELATION_ID={_corr}",
        CONTAINER,
        "openclaw", "agent",
        "--agent", agent_id,
        "--message", message,
        "--json",
        "--timeout", str(timeout),
    ]
    if session_id:
        cmd += ["--session-id", session_id]
    # Note: openclaw agent has no --model flag; model is set per-agent in openclaw.json

    log.info(f"Sending task to agent '{agent_id}' (timeout={timeout}s)")
    log.debug(f"Command: {' '.join(cmd[:6])} ... [message omitted]")

    _pre_lines = _snapshot_agent_session_line_count(agent_id)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 30,  # outer timeout > inner
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"docker exec timed out after {timeout + 30}s")
    except FileNotFoundError:
        raise RuntimeError("docker not found — is this running on the VPS?")

    if proc.returncode != 0:
        raise RuntimeError(
            f"openclaw agent exited {proc.returncode}: {proc.stderr.strip()[:500]}"
        )

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        recovered_text = _poll_for_async_announce(
            agent_id, since_line=_pre_lines, max_wait_seconds=90
        )
        if recovered_text:
            source = (
                "async-await-empty-stdout"
                if not proc.stdout.strip()
                else "async-await-nonjson-stdout"
            )
            log.warning(
                "async-await: recovered %d chars after invalid agent JSON stdout "
                "(stdout_len=%d, source=%s)",
                len(recovered_text), len(proc.stdout or ""), source,
            )
            return {
                "status": "ok",
                "summary": "recovered-from-session-jsonl",
                "result": {
                    "payloads": [{"text": recovered_text, "source": source}],
                    "meta": {
                        "durationMs": 0,
                        "agentMeta": {
                            "sessionId": "",
                            "provider": "openclaw-session-jsonl",
                            "model": model or f"openclaw-agent:{agent_id}",
                            "lastCallUsage": {
                                "input": 0,
                                "output": 0,
                                "cacheRead": 0,
                                "cacheWrite": 0,
                                "total": 0,
                            },
                        },
                    },
                },
            }
        stdout_preview = proc.stdout[:500] if proc.stdout else "<empty>"
        stderr_preview = proc.stderr[:500] if proc.stderr else "<empty>"
        raise RuntimeError(
            f"Failed to parse agent JSON output: {e}\n"
            f"stdout={stdout_preview}\nstderr={stderr_preview}"
        )

    try:
        _payloads = result.get("result", result).get("payloads", None)
        if _payloads is not None and len(_payloads) == 0:
            log.info(
                "async-await: payloads empty for agent=%s, polling session jsonl (pre_lines=%s)",
                agent_id, _pre_lines,
            )
            _text = _poll_for_async_announce(agent_id, since_line=_pre_lines, max_wait_seconds=90)
            if _text:
                log.info("async-await: recovered %d chars from session jsonl", len(_text))
                target = result.get("result", result)
                target.setdefault("payloads", []).append({"text": _text, "source": "async-await-shim"})
    except Exception as _exc:
        log.warning("async-await shim skipped: %s", _exc)

    return result


# ── Resilient OpenClaw wrapper (s2148, 2026-04-30) ──────────────────────────
# Container restarts produce two infrastructure errors that are NOT LLM-API
# failures, so the LiteLLM fallback chain doesn't catch them:
#   1. "openclaw agent exited 137" — SIGKILL/OOM during gateway warmup
#   2. "docker exec timed out after Ns" — gateway not yet ready
# This wrapper retries once after a short sleep, then signals the caller to
# fall back to LiteLLM-direct (sonnet-4-5-thinking is grok-reasoning's #1
# fallback per litellm/config.yaml).
_INFRA_FAILURE_PATTERNS = ("exited 137", "timed out after", "exited 139", "exited 143")


class OpenClawInfraFailure(RuntimeError):
    """Raised when OpenClaw container is unreachable (OOM, timeout, restart)."""


def run_task_resilient(
    message: str,
    session_id: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    model: str | None = None,
    agent_id: str = AGENT_ID,
    retry_delay: int = 5,
) -> dict:
    """Wrap run_task with one retry on infra failure. Real LLM errors propagate.

    Raises:
        OpenClawInfraFailure: if BOTH attempts fail with infra-class errors.
            Caller should fall back to LiteLLM-direct.
        RuntimeError: any other error (LLM/JSON/etc) — propagate immediately.
    """
    try:
        return run_task(message, session_id=session_id, timeout=timeout,
                        model=model, agent_id=agent_id)
    except RuntimeError as e:
        msg = str(e)
        is_infra = any(p in msg for p in _INFRA_FAILURE_PATTERNS)
        if not is_infra:
            raise
        log.warning("openclaw infra failure: %s — retry in %ds", msg[:120], retry_delay)
        time.sleep(retry_delay)
        try:
            return run_task(message, session_id=session_id, timeout=timeout,
                            model=model, agent_id=agent_id)
        except RuntimeError as e2:
            msg2 = str(e2)
            if any(p in msg2 for p in _INFRA_FAILURE_PATTERNS):
                raise OpenClawInfraFailure(
                    f"openclaw unreachable after retry — first: {msg[:200]} | second: {msg2[:200]}"
                ) from e2
            raise


def _call_litellm_direct(message: str, model: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Call LiteLLM API directly — bypasses openclaw. Used for escalation (Grok, Sonnet, Opus).

    Returns the reply text string. Raises RuntimeError on failure.
    """
    import urllib.request as _url_req
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 8192,
    }, ensure_ascii=False).encode("utf-8")
    req = _url_req.Request(
        LITELLM_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LITELLM_KEY}",
        },
        method="POST",
    )
    try:
        with _url_req.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            choice = data["choices"][0]
            content = choice.get("message", {}).get("content")
            if not isinstance(content, str) or not content.strip():
                finish = choice.get("finish_reason", "")
                raise RuntimeError(
                    f"LiteLLM direct call returned empty content "
                    f"(model={model}, finish_reason={finish!r})"
                )
            return content
    except Exception as e:
        raise RuntimeError(f"LiteLLM direct call failed ({model}): {e}")


def _call_litellm_direct_with_escalation(
    message: str,
    chosen_model: str,
    escalator: ModelEscalator,
    explicit_model: bool,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[str, str]:
    """Call a direct LiteLLM model, retrying the escalated tier once for automatic routes."""
    attempted: set[str] = set()
    current_model = chosen_model
    errors: list[str] = []

    while True:
        attempted.add(current_model)
        try:
            return _call_litellm_direct(message, current_model, timeout=timeout), current_model
        except RuntimeError as e:
            errors.append(f"{current_model}: {e}")
            if explicit_model:
                raise

            escalator.record_failure(current_model)
            next_model = escalator.pick()
            if (
                next_model in DIRECT_LITELLM_MODELS
                and next_model not in attempted
                and next_model != current_model
            ):
                log.warning(
                    "direct LiteLLM model %s failed; retrying escalated model %s",
                    current_model,
                    next_model,
                )
                current_model = next_model
                continue

            raise RuntimeError(
                "LiteLLM direct call failed after escalation attempts: "
                + " | ".join(errors)
            ) from e


def _subprocess_error_text(exc: BaseException) -> str:
    stderr = getattr(exc, "stderr", None)
    if isinstance(stderr, bytes):
        stderr = stderr.decode(errors="replace")
    stdout = getattr(exc, "stdout", None)
    if isinstance(stdout, bytes):
        stdout = stdout.decode(errors="replace")
    msg = stderr or stdout or str(exc)
    return msg[:500]


@contextmanager
def _wiki_writeback_lock(timeout: int = WRITEBACK_LOCK_TIMEOUT,
                         stale_after: int = WRITEBACK_LOCK_STALE_AFTER):
    """Serialize run_task git write-back across parallel factory calls."""
    lock_dir = os.path.join(WIKI_PATH, ".git")
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, "run_task_writeback.lock")
    deadline = time.monotonic() + timeout
    payload = f"pid={os.getpid()} ts={datetime.now(KZ_TZ).isoformat()}\n"

    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            break
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(lock_path)
            except OSError:
                age = 0
            if age > stale_after:
                try:
                    os.unlink(lock_path)
                    log.warning("write-back: removed stale lock %s age=%.1fs", lock_path, age)
                except FileNotFoundError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for {lock_path}")
            time.sleep(0.25)

    try:
        yield
    finally:
        try:
            os.unlink(lock_path)
        except FileNotFoundError:
            pass


def _write_back_to_wiki(message: str, response: str, ts, model: str,
                        input_tokens: int, output_tokens: int,
                        source: str = "") -> None:
    """Write task result to wiki as a markdown page, then git commit."""
    slug = re.sub(r"[^a-z0-9]+", "-", message[:40].lower()).strip("-")
    ts_str = ts.strftime("%Y-%m-%d-%H-%M-%S")
    filename = f"{ts_str}-{slug}.md"
    os.makedirs(TASK_RESULTS_DIR, exist_ok=True)
    filepath = os.path.join(TASK_RESULTS_DIR, filename)
    date_str = ts.strftime("%Y-%m-%d")
    source_line = f"source: {_frontmatter_string(source)}\n" if source else ""
    content = (
        f"---\ntype: task-result\ndate: {date_str}\n"
        f"model: {model}\n{source_line}input_tokens: {input_tokens}\noutput_tokens: {output_tokens}\n---\n\n"
        f"## Task\n\n{message}\n\n## Response\n\n{response}\n"
    )
    with open(filepath, "w") as f:
        f.write(content)
    try:
        with _wiki_writeback_lock():
            relpath = f"pages/task-results/{filename}"
            subprocess.run(["git", "-C", WIKI_PATH, "-c", "core.hooksPath=/dev/null",
                            "add", relpath],
                           check=True, capture_output=True, timeout=WRITEBACK_GIT_TIMEOUT)
            subprocess.run(["git", "-C", WIKI_PATH, "-c", "core.hooksPath=/dev/null",
                            "commit", "--no-verify", "-o", relpath,
                            "-m", f"task-result: {ts_str}"],
                           check=True, capture_output=True, timeout=WRITEBACK_GIT_TIMEOUT)
            log.info("write-back: committed %s to wiki", filename)
            # Pull --rebase then push (LESSON-100: gbrain autopilot may push to VPS
            # bare repo while we process; always pull first to avoid rejection)
            try:
                subprocess.run(["git", "-C", WIKI_PATH, "-c", "core.hooksPath=/dev/null",
                                "pull", "--rebase", "origin", "main"],
                               check=True, capture_output=True, timeout=WRITEBACK_GIT_TIMEOUT)
                subprocess.run(["git", "-C", WIKI_PATH, "-c", "core.hooksPath=/dev/null",
                                "push", "origin", "main"],
                               check=True, capture_output=True, timeout=WRITEBACK_GIT_TIMEOUT)
                log.info("write-back: pushed %s to VPS", filename)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                log.warning("write-back: push failed: %s", _subprocess_error_text(e))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, TimeoutError) as e:
        log.warning("write-back: git commit failed: %s",
                    _subprocess_error_text(e))


def extract_text(result: dict) -> str:
    """Pull the agent reply text out of the result JSON."""
    try:
        payloads = result["result"]["payloads"]
        texts = [p["text"] for p in payloads if p.get("text")]
        return "\n".join(texts)
    except (KeyError, TypeError):
        return json.dumps(result)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Send a task to the Nous OpenClaw agent")
    parser.add_argument("message", nargs="?", help="Task message (or pipe via stdin)")
    parser.add_argument("--session-id", help="Reuse an existing agent session")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout in seconds")
    parser.add_argument("--json", action="store_true", dest="output_json", help="Print full JSON result")
    parser.add_argument("--model", help="Override model (deepseek-v4-flash, deepseek-v4-pro, opus, glm-5.1, grok-reasoning, sonnet)")
    parser.add_argument("--no-context", action="store_true", dest="no_context",
                        help="Skip wiki context injection (for health checks, FACTORY_OK tests)")
    parser.add_argument("--correlation-id", default="", dest="correlation_id",
                        help="Telegram msg_id or test-id for per-tier log joining")
    parser.add_argument("--source", default=os.environ.get("NOUS_TASK_SOURCE", ""),
                        help="Optional caller/source label for logs and task-result frontmatter")
    parser.add_argument("--agent", default=AGENT_ID, dest="agent",
                        help=f"OpenClaw agent ID (default: {AGENT_ID!r})")
    args = parser.parse_args()

    # Read message from arg or stdin
    if args.message:
        message = args.message
    elif not sys.stdin.isatty():
        message = sys.stdin.read().strip()
    else:
        parser.error("Provide a message as argument or pipe via stdin")

    if not message:
        parser.error("Message is empty")

    ts = datetime.now(KZ_TZ).isoformat()

    # ── Context injection — prepend Obsidian wiki state to every task ───────
    enriched_message = get_context(message, inject=not args.no_context)

    # ── Route/model selection ────────────────────────────────────────────────
    escalator = ModelEscalator()
    chosen_agent = args.agent if getattr(args, "agent", "") else AGENT_ID
    explicit_model = bool(getattr(args, "model", ""))
    if hasattr(args, "model") and args.model:
        chosen_model = args.model
        log.info("model override via --model flag: %s", chosen_model)
    elif chosen_agent != AGENT_ID:
        # Agent routes have their model configured in OpenClaw. Do not pretend
        # the model escalator selected a direct model for this path.
        chosen_model = f"openclaw-agent:{chosen_agent}"
        log.info("agent route via --agent flag: %s", chosen_agent)
    else:
        chosen_model = escalator.pick()
    log.info("route selected: %s", chosen_model)
    # Log original (unenriched) message so logs stay readable
    log_entry = {"ts": ts, "message": message[:200], "session_id": args.session_id,
                 "model_selected": chosen_model, "model_intent": chosen_model,
                 "agent_selected": chosen_agent}
    source = args.source.strip()
    if source:
        log_entry["source"] = source

    if getattr(args, "correlation_id", ""):
        os.environ["NOUS_CORRELATION_ID"] = args.correlation_id
        log.info("correlation_id set: %s", args.correlation_id)

    # ── Checkpoint: crash recovery + budget enforcement ──────────────────────
    task = ActiveTask(checkpoint_path=CHECKPOINT_FILE, max_iterations=MAX_ITERATIONS)

    # Detect leftover from previous crash — resume the session if possible
    session_id = args.session_id
    stale = task.load_stale()
    if stale and not session_id:
        recovered_session = stale.get("session_id") or ""
        if recovered_session and recovered_session != "null":
            session_id = recovered_session
            log.warning(
                "Resuming stale task (iter=%s, session=%s): %s",
                stale.get("iteration"), session_id, stale.get("description", "?")[:60],
            )

    # Check budget before starting
    if task.is_over_budget():
        log.error("Task budget already exhausted (%d iterations). Clear ACTIVE-TASK.md to reset.", MAX_ITERATIONS)
        log_entry["status"] = "budget_exceeded"
        _append_log(log_entry)
        sys.exit(2)

    # Write checkpoint before the call (use enriched message for accurate recovery)
    task.start(enriched_message, session_id=session_id)
    task.checkpoint(1, session_id=session_id, notes="calling openclaw agent")

    if chosen_model in DIRECT_LITELLM_MODELS:
        # ── Direct model path: selected model physically equals executed model ─
        log.info("direct: calling LiteLLM with model=%s", chosen_model)
        log_entry["execution_path"] = "litellm_direct"
        try:
            text, model_used = _call_litellm_direct_with_escalation(
                enriched_message,
                chosen_model,
                escalator,
                explicit_model,
                timeout=args.timeout,
            )
            status = "ok"
        except RuntimeError as e:
            log.error(str(e))
            task.fail(str(e))
            log_entry["status"] = "error"
            log_entry["error"] = str(e)
            _append_log(log_entry)
            sys.exit(2)
        duration_ms = 0
        out_session_id = ""
        if model_used != chosen_model:
            log_entry["fallback_from"] = chosen_model
            log_entry["fallback_reason"] = "direct_model_error"
        input_tokens = max(1, len(enriched_message) // 4)
        output_tokens = max(1, len(text) // 4)
        task.complete(result_summary=text[:200])
        if not explicit_model:
            escalator.record_success(model_used)
    else:
        # ── OpenClaw agent path: model is configured per agent in OpenClaw ────
        log_entry["execution_path"] = "openclaw_agent"
        try:
            result = run_task_resilient(enriched_message, session_id=session_id, timeout=args.timeout, model=chosen_model, agent_id=chosen_agent)
        except OpenClawInfraFailure as e:
            # Both attempts hit infra-class errors (OOM/timeout/restart).
            # Fall back to LiteLLM-direct using grok-reasoning's #1 fallback.
            fb_model = "sonnet-4-5-thinking" if chosen_agent == "grok-ceo" else "deepseek-v4-flash"
            log.warning("openclaw infra failure after retry — falling back to %s via LiteLLM-direct: %s", fb_model, str(e)[:200])
            log_entry["execution_path"] = "litellm_direct_fallback"
            log_entry["fallback_from"] = chosen_agent
            log_entry["fallback_reason"] = "openclaw_infra"
            try:
                text = _call_litellm_direct(enriched_message, fb_model, timeout=args.timeout)
                result = {"status": "ok", "result": {"payloads": [{"text": text}], "meta": {"agentMeta": {"model": fb_model, "sessionId": ""}, "durationMs": 0}}}
                log.info("fallback succeeded via %s (%d chars)", fb_model, len(text))
            except RuntimeError as fb_err:
                log.error("fallback also failed: %s", fb_err)
                task.fail(f"openclaw + fallback both failed: {fb_err}")
                log_entry["status"] = "error"
                log_entry["error"] = f"openclaw+fallback: {fb_err}"
                _append_log(log_entry)
                sys.exit(2)
        except RuntimeError as e:
            log.error(str(e))
            task.fail(str(e))
            if chosen_model in DIRECT_LITELLM_MODELS and not explicit_model:
                escalator.record_failure(chosen_model)
                log.warning("escalator: recorded failure for %s", chosen_model)
            log_entry["status"] = "error"
            log_entry["error"] = str(e)
            _append_log(log_entry)
            sys.exit(2)

        text = extract_text(result)
        status = result.get("status", "unknown")
        meta = result.get("result", {}).get("meta", {})
        agent_meta = meta.get("agentMeta", {})
        duration_ms = meta.get("durationMs", 0)
        out_session_id = agent_meta.get("sessionId", "")
        model_used = agent_meta.get("model", "deepseek-v4-flash")
        usage = agent_meta.get("lastCallUsage", {})
        # Some providers return 0/missing usage from LiteLLM — fall back to char-based estimate.
        input_tokens = usage.get("input") or max(1, len(message) // 4)
        output_tokens = usage.get("output") or max(1, len(text) // 4)
        task.complete(result_summary=text[:200])
        if chosen_model in DIRECT_LITELLM_MODELS and status == "ok" and not explicit_model:
            escalator.record_success(chosen_model)
        elif chosen_model in DIRECT_LITELLM_MODELS and not explicit_model:
            escalator.record_failure(chosen_model)

    log_entry["status"] = status
    log_entry["duration_ms"] = duration_ms
    log_entry["session_id_out"] = out_session_id
    log_entry["model"] = model_used
    log_entry["model_matches_intent"] = (
        chosen_model == model_used if chosen_model in DIRECT_LITELLM_MODELS else None
    )
    log_entry["input_tokens"] = input_tokens
    log_entry["output_tokens"] = output_tokens
    _append_log(log_entry)

    # ── Write result back to wiki ─────────────────────────────────────────
    _write_back_to_wiki(message, text, datetime.now(KZ_TZ), model_used,
                        input_tokens, output_tokens, source=source)

    if args.output_json and chosen_model not in DIRECT_LITELLM_MODELS:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(text)

    if status not in ("ok",):
        log.warning(f"Agent returned status={status}")
        sys.exit(1)


if __name__ == "__main__":
    main()
