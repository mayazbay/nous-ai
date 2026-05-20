#!/usr/bin/env python3
"""Execute Satory AI-owned Todoist work as bounded OpenClaw/Codex slices.

Default mode is read-only planning. `--dry-run` is accepted as an explicit
alias for the default. `--apply` writes the queue ledger, audit receipt, and
one concise Todoist proof comment per attempted slice.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any

from factory_orchestration_policy import (
    ROUTE_CHATGPT_EXECUTION,
    ROUTE_GROK_DECISION,
    ROUTE_LONG_WORK_GOAL,
    ROUTE_OPENCLAW_ROUTINE,
    classify_text,
)
from human_owner_reminder import add_todoist_comment, load_env_file, run, tail
from satory_todoist_deep_audit import DEFAULT_JSON, Todoist, build_deep_audit, token_from_env


ALMATY = dt.timezone(dt.timedelta(hours=5))
DEFAULT_WIKI = Path("/Users/madia/nous-agaas/wiki")
DEFAULT_LEDGER = Path("pages/systems/satory-ai-factory-queue-ledger.json")
DEFAULT_STATUS = Path("pages/systems/satory-ai-factory-queue-status.md")
DEFAULT_AUDIT_DIR = Path("pages/audits")
RUN_TASK = Path(os.environ.get("NOUS_RUN_TASK", "/Users/madia/nous-agaas/run_task.py"))
RUN_TASK_PYTHON = Path(os.environ.get("NOUS_RUN_TASK_PYTHON", sys.executable))
CODEX_CMD = os.environ.get("CODEX_CMD", "codex")
CODEX_MODEL = os.environ.get("CODEX_MODEL", "gpt-5.5")
CODEX_SANDBOX = os.environ.get("CODEX_SANDBOX", "danger-full-access")
LOCAL_MLX_WORKER_MODEL = "local-mlx-coder"
MAX_EVENT_ATTEMPTS = 2
MAX_CONTEXT_FILES = 6
MAX_CONTEXT_CHARS_PER_FILE = 1400
WRITEBACK_LOCK_TIMEOUT = 90
WRITEBACK_LOCK_STALE_AFTER = 300
PRIORITY_RE = re.compile(r"(?i)\b(bdl|бдл|cerebro|церебро|erap|ерап|apk|апк|mergen|мерген|var|вар|радар|лу\s*\d+|штраф|событ|endpoint)\b")
VAULT_REF_RE = re.compile(r"(?<![\w/])((?:pages|tools|briefs|raw)/[^\s`'\"<>)]+)")
PROOF_HEAVY_RE = re.compile(
    r"(?i)\b("
    r"playwright|browser|screenshot|curl|http|api|endpoint|vps|ssh|smoke|health|"
    r"dashboard|map|camera|events?|logs?|metrology|cert|calibration|"
    r"браузер|скриншот|смоук|дашборд|карта|камера|камеры|событ|лог|"
    r"метролог|сертификат|поверк|калибров"
    r")\b"
)
WORKER_CREATED_PROOF_RE = re.compile(r"^pages/audits/SATORY-[A-Za-z0-9_-]+-SLICE-\d{4}-\d{2}-\d{2}\.md$")
WORKER_SIDE_EFFECT_RE = re.compile(
    r"(?im)\b("
    r"todoist\s+proof\s+comment\s+posted|"
    r"posted\s+(?:a\s+)?todoist\s+comment|"
    r"git\s+commit|"
    r"wrote\s+.*pages/audits|"
    r"записал.*todoist|"
    r"оставил.*todoist"
    r")\b"
)
BLOCKED_STATUS_RE = re.compile(r"(?im)^\s*\**(?:Статус|Status)\**\s*:\**\s*\**(?:заблокировано|blocked|failed)\b")
NO_PROOF_RE = re.compile(r"(?im)^\s*\**(?:Proof|Доказательство)\**\s*:\**\s*\**(?:нет|не сделан|none|no proof|not done)\b")
WORKER_BLOCKER_RE = re.compile(
    r"^\s*\**(?:Блокер|Blocked|Blocker)\**\s*:|"
    r"Agent couldn't generate a response|"
    r"sandbox(?:-[\w]+)?\s+(?:без|without)\s+access|"
    r"workspace\s+(?:без|without)\s+access|"
    r"(?:не\s+примонтирован|not\s+mounted)|"
    r"(?:не\s+существует|does\s+not\s+exist)",
    re.IGNORECASE | re.MULTILINE,
)


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class QueueWritebackError(RuntimeError):
    pass


class queue_writeback_lock:
    """Serialize queue git write-back with run_task.py task-result commits."""

    def __init__(
        self,
        wiki: Path,
        *,
        timeout: int = WRITEBACK_LOCK_TIMEOUT,
        stale_after: int = WRITEBACK_LOCK_STALE_AFTER,
    ) -> None:
        self.lock_path = wiki / ".git" / "run_task_writeback.lock"
        self.timeout = timeout
        self.stale_after = stale_after

    def __enter__(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout
        payload = f"pid={os.getpid()} source=satory-ai-factory-queue ts={now_kzt().isoformat()}\n"
        while True:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(payload)
                return
            except FileExistsError:
                try:
                    age = time.time() - self.lock_path.stat().st_mtime
                except OSError:
                    age = 0
                if age > self.stale_after:
                    try:
                        self.lock_path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                if time.monotonic() >= deadline:
                    raise QueueWritebackError(f"timed out waiting for {self.lock_path}")
                time.sleep(0.25)

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass


def _git(args: list[str], wiki: Path, timeout: int = 180) -> dict[str, Any]:
    return run(["git", *args], cwd=wiki, timeout=timeout)


def worker_created_proof_paths_from_status(status_text: str) -> list[Path]:
    paths: list[Path] = []
    for raw in status_text.splitlines():
        if not raw.startswith("?? "):
            continue
        rel = raw[3:].strip()
        if WORKER_CREATED_PROOF_RE.fullmatch(rel):
            paths.append(Path(rel))
    return paths


def worker_created_proof_paths(wiki: Path) -> list[Path]:
    status = _git(["status", "--porcelain"], wiki)
    if not status.get("ok"):
        return []
    return worker_created_proof_paths_from_status(str(status.get("stdout") or ""))


def _require_git_ok(step: str, result: dict[str, Any]) -> None:
    if not result.get("ok"):
        raise QueueWritebackError(f"{step} failed: {tail(str(result.get('stderr') or result.get('stdout') or ''), 800)}")


def _exact_rebase_and_push(wiki: Path, remote: str) -> dict[str, Any]:
    _require_git_ok(f"fetch {remote}", _git(["fetch", remote, "main"], wiki))
    target = _git(["rev-parse", "FETCH_HEAD"], wiki)
    _require_git_ok(f"rev-parse {remote}", target)
    target_oid = str(target.get("stdout") or "").strip()
    _require_git_ok(
        f"rebase {remote}",
        _git(["-c", "core.hooksPath=/dev/null", "rebase", target_oid], wiki),
    )
    push = _git(["push", remote, "main"], wiki)
    _require_git_ok(f"push {remote}", push)
    return {"remote": remote, "target": target_oid[:12], "push": "ok"}


def git_writeback_queue_outputs(
    wiki: Path,
    relpaths: list[Path],
    *,
    push_remotes: list[str],
    message: str,
) -> dict[str, Any]:
    """Commit queue-owned proof files and push them so other writers can rebase.

    The queue runner writes ledger/status/audit files from launchd. If it leaves
    them unstaged, the next run_task.py checkpoint cannot rebase/push. This
    write-back commits only queue-owned paths and uses the same git lock as
    task-result write-back.
    """
    rel = sorted({path.as_posix() for path in relpaths})
    with queue_writeback_lock(wiki):
        status = _git(["status", "--porcelain", "--", *rel], wiki)
        _require_git_ok("status", status)
        if not str(status.get("stdout") or "").strip():
            return {"status": "skipped", "reason": "no queue output changes"}
        _require_git_ok("add", _git(["-c", "core.hooksPath=/dev/null", "add", "--", *rel], wiki))
        _require_git_ok(
            "commit",
            _git(["-c", "core.hooksPath=/dev/null", "commit", "--no-verify", "-m", message, "-o", *rel], wiki),
        )
        remaining = _git(["status", "--porcelain"], wiki)
        _require_git_ok("post-commit status", remaining)
        if str(remaining.get("stdout") or "").strip():
            raise QueueWritebackError(f"dirty tree remains after queue commit: {tail(str(remaining.get('stdout')), 800)}")
        pushed = [_exact_rebase_and_push(wiki, remote) for remote in push_remotes]
    return {"status": "ok", "committed": rel, "pushed": pushed}


def event_fingerprint(row: dict[str, Any]) -> str:
    signal = row.get("latest_human_signal") or {}
    payload = {
        "task_id": row.get("task_id"),
        "title": row.get("content"),
        "status": row.get("status"),
        "route": row.get("factory_route"),
        "queue_reason": row.get("queue_reason"),
        "signal_note_id": signal.get("note_id"),
        "signal_intent": signal.get("intent"),
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"todoist-task:{row.get('task_id')}:{digest}"


def ledger_attempts(entry: Any) -> int:
    if not isinstance(entry, dict):
        return 1 if entry else 0
    try:
        return max(1, int(entry.get("attempts") or 1))
    except (TypeError, ValueError):
        return 1


def ledger_entry_blocks_queue(entry: Any) -> bool:
    if not entry:
        return False
    if not isinstance(entry, dict):
        return True
    if entry.get("ok") is True:
        return True
    return ledger_attempts(entry) >= MAX_EVENT_ATTEMPTS


def already_ran(ledger: dict[str, Any], event_id: str) -> bool:
    return ledger_entry_blocks_queue(ledger.get("runs", {}).get(event_id))


def task_already_ran_without_new_signal(ledger: dict[str, Any], row: dict[str, Any]) -> bool:
    if row.get("latest_human_signal"):
        return False
    task_id = str(row.get("task_id") or "")
    if not task_id:
        return False
    for entry in ledger.get("runs", {}).values():
        if isinstance(entry, dict) and str(entry.get("task_id") or "") == task_id and ledger_entry_blocks_queue(entry):
            return True
    return False


def priority_score(row: dict[str, Any], priority: str) -> tuple[int, int, str]:
    text = " ".join(str(row.get(key) or "") for key in ("content", "description", "queue_reason", "next_action_compact"))
    operator = 0 if priority == "bdl-apk-erap" and PRIORITY_RE.search(text) else 1
    status_rank = 0 if row.get("status") in {"working", "in_progress"} else 1
    return (operator, status_rank, str(row.get("content") or "").casefold())


def _candidate_vault_refs(text: str) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for match in VAULT_REF_RE.finditer(text):
        ref = match.group(1).rstrip(".,;:]}»”")
        if ref and ref not in seen:
            refs.append(ref)
            seen.add(ref)
    return refs


def _row_context_text(row: dict[str, Any]) -> str:
    comments = row.get("comments") or []
    comment_text = "\n".join(str(comment.get("content") or "") for comment in comments[-5:])
    return "\n".join(
        str(row.get(key) or "")
        for key in ("content", "description", "queue_reason", "next_action_compact", "close_gate")
    ) + "\n" + comment_text


def _safe_context_paths(wiki: Path, ref: str) -> list[Path]:
    wiki_root = wiki.resolve()
    refs = sorted(wiki.glob(ref)) if any(ch in ref for ch in "*?[") else [wiki / ref]
    safe: list[Path] = []
    for path in refs:
        try:
            resolved = path.resolve()
            resolved.relative_to(wiki_root)
        except (OSError, ValueError):
            continue
        if resolved.is_file():
            safe.append(resolved)
    return safe


def vault_context_for_row(wiki: Path, row: dict[str, Any]) -> str:
    """Inject small Air-vault snippets for file-backed Todoist slices.

    OpenClaw workers run in a sandbox that may not mount the Air wiki. The queue
    runner has the vault locally, so it must pass referenced file contents into
    the worker prompt instead of asking the worker to read paths it cannot see.
    """
    refs = _candidate_vault_refs(_row_context_text(row))
    if not refs:
        return ""
    snippets: list[str] = []
    missing: list[str] = []
    included = 0
    for ref in refs:
        paths = _safe_context_paths(wiki, ref)
        if not paths:
            missing.append(ref)
            continue
        for path in paths:
            if included >= MAX_CONTEXT_FILES:
                break
            rel = path.relative_to(wiki.resolve()).as_posix()
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                missing.append(f"{rel} ({type(exc).__name__})")
                continue
            snippets.extend(
                [
                    f"### {rel}",
                    "```text",
                    text[:MAX_CONTEXT_CHARS_PER_FILE],
                    "```",
                    "",
                ]
            )
            included += 1
        if included >= MAX_CONTEXT_FILES:
            break
    if not snippets and not missing:
        return ""
    lines = ["## Injected Air vault context", ""]
    if snippets:
        lines.extend(snippets)
    if missing:
        lines.append("Missing referenced vault files:")
        lines.extend(f"- {ref}" for ref in missing[:8])
        lines.append("")
    return "\n".join(lines).strip()


def build_queue(report: dict[str, Any], ledger: dict[str, Any], *, limit: int, priority: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in report.get("tasks", []):
        if row.get("execution_state") != "queued":
            continue
        if row.get("delete_candidate_reason"):
            continue
        event_id = event_fingerprint(row)
        if already_ran(ledger, event_id) or task_already_ran_without_new_signal(ledger, row):
            continue
        candidates.append({"event_id": event_id, "task": row})
    candidates.sort(key=lambda event: priority_score(event["task"], priority))
    return candidates[:limit]


def factory_prompt(row: dict[str, Any], event_id: str, wiki: Path | None = None) -> str:
    comments = row.get("comments") or []
    latest_comments = "\n".join(
        f"- {comment.get('posted_at')} {comment.get('intent')}: {str(comment.get('content') or '')[:500]}"
        for comment in comments[-3:]
    )
    vault_context = vault_context_for_row(wiki, row) if wiki is not None else ""
    return f"""Ты Satory AI Factory worker inside Nous AGaaS.

Выполни ровно один маленький progress slice по Todoist-задаче. Не закрывай задачу. Не выдумывай proof.

Musk 5-step before action:
1. Требование: какой proof нужен?
2. Что можно удалить/не делать?
3. Самый простой следующий шаг.
4. Как ускорить без шума.
5. Что автоматизировать только после proof.

Task:
- event_id: {event_id}
- task_id: {row.get('task_id')}
- title: {row.get('content')}
- status: {row.get('status')}
- owner: {row.get('owner')}
- url: {row.get('todoist_url')}
- route: {row.get('factory_route')}
- queue_reason: {row.get('queue_reason')}
- next_action: {row.get('next_action_compact')}
- close_gate: {row.get('close_gate')}

Description:
{str(row.get('description') or '')[:1800]}

Latest comments:
{latest_comments or '(нет комментариев)'}

{vault_context}

Hard boundary:
- Do not write files.
- Do not run git.
- Do not call Todoist, Notion, Drive, or Telegram write APIs.
- Do not read `.env` files or secrets.
- The queue runner writes the Todoist comment and Obsidian proof from your stdout.

Output in Russian:
Статус: в работе | заблокировано
Что сделал:
Proof:
Следующий шаг:
Learned:
"""


def model_for_decision(decision: dict[str, Any]) -> str:
    if decision.get("route") == ROUTE_GROK_DECISION:
        return str(decision.get("first_pass_model") or "grok-reasoning")
    if decision.get("route") in {ROUTE_LONG_WORK_GOAL, ROUTE_OPENCLAW_ROUTINE}:
        return LOCAL_MLX_WORKER_MODEL
    return str(decision.get("worker_model") or "deepseek-v4-flash")


def row_requires_tool_verification(row: dict[str, Any]) -> bool:
    """True when a queued task needs shell/network/browser proof, not prose."""

    if row.get("execution_state") != "queued":
        return False
    comments = row.get("comments") or []
    comment_text = "\n".join(str(comment.get("content") or "") for comment in comments[-5:])
    text = "\n".join(
        str(row.get(key) or "")
        for key in ("content", "description", "queue_reason")
    ) + "\n" + comment_text
    return bool(PROOF_HEAVY_RE.search(text))


def decision_for_row(row: dict[str, Any]) -> dict[str, Any]:
    """Classify a queue row and force tool-capable routing for proof work."""

    text = "\n".join(
        str(row.get(key) or "")
        for key in ("content", "description", "queue_reason", "next_action_compact")
    )
    text = text + "\n" + _row_context_text(row)
    decision = classify_text(text).to_dict()
    if row_requires_tool_verification(row) and decision.get("route") == ROUTE_OPENCLAW_ROUTINE:
        decision["route"] = ROUTE_CHATGPT_EXECUTION
        decision["reason"] = "Satory proof-heavy queue slice requires tool-capable Codex/GPT execution"
        decision["todoist_action"] = "codex_execute_proof_slice"
    return decision


def worker_failure_reason(detail: str) -> str:
    """Classify successful process output that is still not successful work."""
    text = detail.strip()
    if not text:
        return "empty_output"
    if "Agent couldn't generate a response" in text:
        return "no_response"
    if BLOCKED_STATUS_RE.search(text):
        return "blocked_status"
    if NO_PROOF_RE.search(text):
        return "missing_proof"
    if WORKER_SIDE_EFFECT_RE.search(text):
        return "worker_side_effect"
    if WORKER_BLOCKER_RE.search(text):
        return "worker_blocker"
    return ""


def route_result(
    result: dict[str, Any],
    *,
    success_status: str,
    process_failure_status: str,
    worker_blocked_status: str,
) -> tuple[bool, str, str]:
    detail = tail(result["stdout"] or result["stderr"], 2500)
    if not result["ok"]:
        return False, process_failure_status, ""
    reason = worker_failure_reason(detail)
    if reason:
        return False, worker_blocked_status, reason
    return True, success_status, ""


def dispatch_event(
    wiki: Path,
    event: dict[str, Any],
    *,
    dry_run: bool,
    allow_codex: bool,
    timeout: int,
) -> dict[str, Any]:
    row = event["task"]
    event_id = event["event_id"]
    prompt = factory_prompt(row, event_id, wiki)
    decision = decision_for_row(row)
    source = event_id.replace(":", "-")
    if dry_run:
        return {
            "ok": True,
            "status": "dry_run",
            "event_id": event_id,
            "route": decision.get("route"),
            "model": "dry-run",
            "detail": "dry-run",
        }
    if decision.get("route") == ROUTE_CHATGPT_EXECUTION:
        if not allow_codex:
            return {
                "ok": False,
                "status": "blocked_codex_required",
                "event_id": event_id,
                "route": decision.get("route"),
                "model": f"codex:{CODEX_MODEL}",
                "detail": "Mandatory GPT/Codex route; rerun with --allow-codex after confirming budget/auth.",
            }
        cmd = [
            CODEX_CMD,
            "exec",
            "-m",
            CODEX_MODEL,
            "--sandbox",
            CODEX_SANDBOX,
            "--ephemeral",
            "-C",
            str(wiki),
            prompt,
        ]
        result = run(cmd, cwd=wiki, timeout=timeout + 60)
        ok, status, reason = route_result(
            result,
            success_status="codex_ran",
            process_failure_status="codex_failed",
            worker_blocked_status="codex_blocked",
        )
        return {
            "ok": ok,
            "status": status,
            "event_id": event_id,
            "route": decision.get("route"),
            "model": f"codex:{CODEX_MODEL}",
            "detail": tail(result["stdout"] or result["stderr"], 2500),
            "worker_failure_reason": reason,
            "returncode": result.get("returncode"),
        }
    if not RUN_TASK.exists():
        return {
            "ok": False,
            "status": "blocked_runner_missing",
            "event_id": event_id,
            "route": decision.get("route"),
            "model": model_for_decision(decision),
            "detail": f"run_task.py missing at {RUN_TASK}",
        }
    model = model_for_decision(decision)
    cmd = [
        str(RUN_TASK_PYTHON),
        str(RUN_TASK),
        "--source",
        source,
        "--timeout",
        str(timeout),
        "--model",
        model,
        prompt,
    ]
    result = run(cmd, cwd=wiki, timeout=timeout + 45)
    ok, status, reason = route_result(
        result,
        success_status="openclaw_ran",
        process_failure_status="openclaw_failed",
        worker_blocked_status="openclaw_blocked",
    )
    return {
        "ok": ok,
        "status": status,
        "event_id": event_id,
        "route": decision.get("route"),
        "model": model,
        "detail": tail(result["stdout"] or result["stderr"], 2500),
        "worker_failure_reason": reason,
        "returncode": result.get("returncode"),
    }


def todoist_result_comment(row: dict[str, Any], result: dict[str, Any], proof_path: str) -> str:
    status = "в работе" if result.get("ok") else "заблокировано"
    return (
        "AI-фабрика взяла задачу в one-beam очередь.\n"
        f"Статус: {status}\n"
        f"Маршрут: `{result.get('route')}`; модель: `{result.get('model')}`\n"
        f"Event: `{result.get('event_id')}`\n"
        f"Proof: `{proof_path}`\n"
        "Следующий шаг: смотреть proof и выполнить следующий операторский шаг; задачу не закрывать без Notion+Drive proof.\n\n"
        f"{tail(str(result.get('detail') or ''), 1600)}"
    )


def render_status(report: dict[str, Any], queue: list[dict[str, Any]], results: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "---",
            "type: system",
            "id: satory-ai-factory-queue-status",
            'title: "Satory AI Factory queue status"',
            f"last_updated: {now_kzt().isoformat()}",
            "status: active",
            "tags: [satory, todoist, openclaw, queue, one-beam]",
            "---",
            "",
            "# Satory AI Factory queue status",
            "",
            f"- Audit captured: `{report.get('captured_at', '')}`",
            f"- Queue selected: `{len(queue)}`",
            f"- Results: `{len(results)}`",
            f"- OK: `{sum(1 for result in results if result.get('ok'))}`",
            f"- Blocked/failed: `{sum(1 for result in results if not result.get('ok'))}`",
            "- Hermes boundary: `canary_only`.",
            "- GPT/Codex boundary: mandatory for external operator proof/top-tier routes; fail closed if not allowed.",
            "",
        ]
    )


def render_audit(report: dict[str, Any], queue: list[dict[str, Any]], results: list[dict[str, Any]]) -> str:
    lines = [
        "---",
        "type: audit",
        f"id: SATORY-AI-FACTORY-QUEUE-{now_kzt().strftime('%Y-%m-%d-%H%M%S')}",
        'title: "Satory AI Factory queue run"',
        f"date: {now_kzt().date().isoformat()}",
        "status: active",
        "tags: [satory, todoist, openclaw, codex, queue, proof]",
        "---",
        "",
        "# Satory AI Factory queue run",
        "",
        "## Summary",
        "",
        f"- Audit captured: `{report.get('captured_at', '')}`",
        f"- Selected: `{len(queue)}`",
        f"- Results: `{len(results)}`",
        f"- OK: `{sum(1 for result in results if result.get('ok'))}`",
        f"- Blocked/failed: `{sum(1 for result in results if not result.get('ok'))}`",
        "",
        "## Results",
        "",
    ]
    by_event = {result.get("event_id"): result for result in results}
    for event in queue:
        row = event["task"]
        result = by_event.get(event["event_id"], {})
        lines.extend(
            [
                f"### {row.get('content')} (`{row.get('task_id')}`)",
                "",
                f"- Event: `{event['event_id']}`",
                f"- Todoist: {row.get('todoist_url')}",
                f"- Queue reason: `{row.get('queue_reason')}`",
                f"- Result status: `{result.get('status', 'not_run')}`",
                f"- Route/model: `{result.get('route', '')}` / `{result.get('model', '')}`",
                f"- Todoist comment: `{result.get('todoist_comment_id', '')}`",
                f"- Todoist comment error: `{result.get('todoist_comment_error', '')}`",
                "",
                "```text",
                str(result.get("detail") or "")[:2500],
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def load_or_build_report(args: argparse.Namespace) -> tuple[dict[str, Any], Todoist | None]:
    if args.refresh or args.apply or not args.input_json.exists():
        client = Todoist(token_from_env(args.env_file))
        return build_deep_audit(client.sync()), client
    return load_json(args.input_json), None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--env-file", type=Path, default=Path.home() / "nous-agaas" / ".env")
    parser.add_argument("--input-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--status-page", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--audit-dir", type=Path, default=DEFAULT_AUDIT_DIR)
    parser.add_argument("--project", default="satory")
    parser.add_argument("--priority", default="bdl-apk-erap")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Explicit read-only mode; equivalent to omitting --apply.")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--allow-codex", action="store_true")
    parser.add_argument("--no-todoist-comments", action="store_true")
    parser.add_argument("--git-writeback", action="store_true", help="Commit and push queue-owned proof files after --apply.")
    parser.add_argument(
        "--git-push-remotes",
        default="origin,github",
        help="Comma-separated remotes for --git-writeback. Default: origin,github.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.apply and args.dry_run:
        raise SystemExit("Pass either --apply or --dry-run, not both.")
    if args.project != "satory":
        raise SystemExit("Only --project satory is supported in this canary.")
    runtime_env = os.environ.copy()
    runtime_env.update(load_env_file(args.env_file))
    report, client = load_or_build_report(args)
    ledger_path = args.wiki / args.ledger
    ledger = load_json(ledger_path) or {"runs": {}}
    queue = build_queue(report, ledger, limit=args.limit, priority=args.priority)
    results: list[dict[str, Any]] = []
    proof_rel = args.audit_dir / f"SATORY-AI-FACTORY-QUEUE-{now_kzt().strftime('%Y-%m-%d-%H%M%S')}.md"
    proof_path = str(proof_rel)
    for event in queue:
        result = dispatch_event(
            args.wiki,
            event,
            dry_run=not args.apply,
            allow_codex=args.allow_codex,
            timeout=args.timeout,
        )
        results.append(result)
        if args.apply:
            previous_entry = ledger.setdefault("runs", {}).get(event["event_id"])
            ledger_entry = {
                "at": now_kzt().isoformat(),
                "attempts": ledger_attempts(previous_entry) + 1 if previous_entry else 1,
                "task_id": event["task"].get("task_id"),
                "title": event["task"].get("content"),
                "ok": result.get("ok"),
                "status": result.get("status"),
                "route": result.get("route"),
                "model": result.get("model"),
                "proof": proof_path,
            }
            if not result.get("ok"):
                ledger_entry["last_error"] = tail(str(result.get("detail") or ""), 500)
            ledger.setdefault("runs", {})[event["event_id"]] = ledger_entry
            if not args.no_todoist_comments:
                _task_id = str(event["task"].get("task_id"))
                _comment_client = client if client is not None else Todoist(token_from_env(args.env_file))
                try:
                    _resp = add_todoist_comment(_comment_client, _task_id, todoist_result_comment(event["task"], result, proof_path))
                    _comment_id = _resp.get("id") if isinstance(_resp, dict) else None
                    result["todoist_comment_id"] = _comment_id or ""
                    ledger_entry["todoist_comment_id"] = _comment_id or ""
                    if not _comment_id:
                        print(f"WARN: todoist comment write returned no id for task={_task_id} resp={_resp!r}", file=sys.stderr)
                except Exception as _exc:
                    result["todoist_comment_error"] = f"{type(_exc).__name__}: {_exc}"
                    ledger_entry["todoist_comment_error"] = result["todoist_comment_error"]
                    print(f"WARN: todoist comment write failed for task={_task_id}: {type(_exc).__name__}: {_exc}", file=sys.stderr)
    if args.apply:
        save_json(ledger_path, ledger)
        audit_abs = args.wiki / proof_rel
        status_abs = args.wiki / args.status_page
        audit_abs.parent.mkdir(parents=True, exist_ok=True)
        status_abs.parent.mkdir(parents=True, exist_ok=True)
        audit_abs.write_text(render_audit(report, queue, results), encoding="utf-8")
        status_abs.write_text(render_status(report, queue, results), encoding="utf-8")
    git_writeback_result: dict[str, Any] = {}
    if args.apply and args.git_writeback:
        try:
            writeback_paths = [args.ledger, args.status_page, proof_rel]
            writeback_paths.extend(worker_created_proof_paths(args.wiki))
            git_writeback_result = git_writeback_queue_outputs(
                args.wiki,
                writeback_paths,
                push_remotes=[remote.strip() for remote in args.git_push_remotes.split(",") if remote.strip()],
                message=f"satory-queue: {now_kzt().strftime('%Y-%m-%d-%H%M%S')}",
            )
        except Exception as exc:
            git_writeback_result = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
            print(f"WARN: queue git writeback failed: {git_writeback_result['error']}", file=sys.stderr)
    payload = {
        "status": "ok" if not any(not result.get("ok") for result in results) else "blocked_or_failed",
        "selected": len(queue),
        "results": results,
        "proof": proof_path if args.apply else "",
        "ledger": str(args.ledger),
        "apply": args.apply,
        "git_writeback": git_writeback_result,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"selected={len(queue)} ok={sum(1 for r in results if r.get('ok'))} blocked={sum(1 for r in results if not r.get('ok'))} proof={payload['proof']}")
    return 0 if payload["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
