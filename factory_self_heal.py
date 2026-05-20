#!/usr/bin/env python3
"""Self-healing supervisor for routine Nous factory drift.

This script sits between probes and Telegram. Probes detect; this supervisor
repairs, verifies, and only pages Madi when a bounded repair fails or a human
decision is actually required.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Notification policy gate (notification-policy-tightening, 2026-05-20)
# Import is optional — if module unavailable, fall back to always-notify.
try:
    from notification_policy import should_ping as _policy_should_ping
    _POLICY_AVAILABLE = True
except ImportError:
    _POLICY_AVAILABLE = False


ALMATY = dt.timezone(dt.timedelta(hours=5))
DEFAULT_WIKI = Path("/Users/madia/nous-agaas/wiki")
DEFAULT_LEDGER = Path("/Users/madia/nous-agaas/logs/factory-self-heal.jsonl")
DEFAULT_STATE = Path("/Users/madia/nous-agaas/state/factory-self-heal-state.json")
DEFAULT_STATUS_PAGE = Path("pages/systems/factory-self-healing-supervisor-status.md")
FACTORY_PROBE = Path("tools/factory_no_drift_probe.sh")

# Globs for files that auto-sync processes (mercury, dashboards, obsidian, queue
# ledgers) write continuously.  Matching dirty files are safe to auto-stage and
# commit so that clean_worktree() can proceed with air_sync_lag (and any future
# "wants clean WT") repairs without paging Madi.
_TRANSIENT_PATHS = (
    "pages/mercury/*.jsonl",
    "pages/mercury/*.md",
    "pages/dashboards/*.md",
    "pages/progress/claude-memory/*",
    "pages/progress/claude-memory/**/*",
    ".obsidian/workspace*.json",
    ".obsidian/workspaces.json",
    "pages/systems/*-ledger.jsonl",
    "pages/systems/*-ledger.json",
    "pages/systems/*-status.md",
    "pages/systems/*-snapshot-pre.json",
    "pages/systems/daily-evolution-state.json",
    "pages/systems/control-plane-sync-status.md",
    "pages/systems/human-owner-reminder-*",
    "pages/systems/factory-self-heal-*.jsonl",
    "pages/systems/hermes-*-status.md",
    "pages/systems/satory-ai-factory-queue-*.md",
    "pages/systems/satory-ai-factory-queue-*.json",
    "pages/systems/notification-digest-queue.jsonl",
    "pages/audits/SATORY-AI-FACTORY-QUEUE-*.md",
)


def _is_transient(path: str) -> bool:
    """Return True if *path* (repo-relative, forward-slash) matches any _TRANSIENT_PATHS glob."""
    for glob in _TRANSIENT_PATHS:
        if fnmatch.fnmatch(path, glob):
            return True
    return False


def auto_resolve_transient_dirty(args: argparse.Namespace) -> tuple[bool, list[str]]:
    """Classify dirty files and auto-commit purely-transient churn.

    Returns:
        (True, [])                       — worktree was already clean
        (True, [list of paths cleared])  — all dirty files were transient; auto-committed
        (False, [list of real paths])    — at least one real WIP file found; nothing touched
        (False, [])                      — git status failed
    """
    result = run(["git", "status", "--porcelain"], cwd=args.wiki, timeout=30)
    if not result["ok"]:
        return (False, [])

    raw = result["stdout"]
    if not raw.strip():
        return (True, [])

    transient: list[str] = []
    real: list[str] = []
    for line in raw.splitlines():
        if len(line) < 4:
            continue
        # porcelain format: XY<space>path  (two status chars + space + path)
        path = line[3:].strip()
        # Handle renamed files (old -> new) — take the destination
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if _is_transient(path):
            transient.append(path)
        else:
            real.append(path)

    if real:
        return (False, real)

    # All dirty files are transient — auto-stage + commit
    if args.dry_run:
        return (True, transient)

    add_result = run(["git", "add", "-A"] + transient, cwd=args.wiki, timeout=60)
    if not add_result["ok"]:
        return (False, [])

    commit_result = run(
        ["git", "commit", "-m", "auto-sync: factory_self_heal cleared transient churn"],
        cwd=args.wiki,
        timeout=60,
    )
    if not commit_result["ok"]:
        return (False, [])

    return (True, transient)


LAUNCHD_REPAIRS = {
    "telegram_poller": "com.nous.telegram-poll",
    "goal_mode": "com.nous.goal-cycle",
    "litellm": "com.nous.litellm",
    "openbrain_projection": "com.nous.openbrain-projection",
}

HUMAN_REQUIRED = {
    "openrouter_cap": "money_or_budget_cap",
    "codex_cli_available": "login_or_subscription_auth",
    "hermes_webui_phone_url": "physical_or_network_login",
}


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def iso_now() -> str:
    return now_kzt().isoformat()


def tail(text: str, limit: int = 1200) -> str:
    value = str(text or "").strip()
    return value if len(value) <= limit else value[-limit:]


def run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 90) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [str(part) for part in cmd],
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "cmd": " ".join(str(part) for part in cmd),
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_ms": int((time.monotonic() - started) * 1000),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": " ".join(str(part) for part in cmd),
            "returncode": 124,
            "ok": False,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or f"timeout after {timeout}s",
            "duration_ms": int((time.monotonic() - started) * 1000),
        }
    except FileNotFoundError as exc:
        return {
            "cmd": " ".join(str(part) for part in cmd),
            "returncode": 127,
            "ok": False,
            "stdout": "",
            "stderr": f"missing executable: {exc.filename}",
            "duration_ms": int((time.monotonic() - started) * 1000),
        }


def parse_probe(text: str) -> dict[str, Any]:
    start = text.find("{")
    if start < 0:
        return {"overall": "RED", "reds": 1, "checks": [{"check": "probe_parse", "status": "RED", "detail": "no JSON object found"}]}
    try:
        payload = json.loads(text[start:])
    except json.JSONDecodeError as exc:
        return {"overall": "RED", "reds": 1, "checks": [{"check": "probe_parse", "status": "RED", "detail": f"invalid JSON: {exc}"}]}
    return payload if isinstance(payload, dict) else {"overall": "RED", "reds": 1, "checks": [{"check": "probe_parse", "status": "RED", "detail": "JSON root is not an object"}]}


def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    result = run(["bash", str(FACTORY_PROBE), "--quiet", "--json", "--no-telegram"], cwd=args.wiki, timeout=args.probe_timeout)
    payload = parse_probe(result["stdout"])
    payload["_probe_command"] = result["cmd"]
    payload["_probe_returncode"] = result["returncode"]
    if not result["ok"] and payload.get("overall") == "GREEN":
        payload["overall"] = "RED"
        payload["reds"] = 1
    return payload


def red_checks(probe: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in probe.get("checks", []) if isinstance(row, dict) and row.get("status") == "RED"]


def fingerprint(checks: list[dict[str, Any]]) -> str:
    slim = [
        {
            "check": str(row.get("check") or row.get("name") or "unknown"),
            "detail": str(row.get("detail") or row.get("summary") or "")[:500],
        }
        for row in checks
    ]
    return hashlib.sha256(json.dumps(slim, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def load_state(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"notifications": {}}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def append_ledger(path: Path, report: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(report, ensure_ascii=False, sort_keys=True, default=str) + "\n")


def status_page(report: dict[str, Any]) -> str:
    lines = [
        "---",
        "type: system",
        "id: factory-self-healing-supervisor-status",
        'title: "Factory Self-Healing Supervisor Status"',
        f"last_updated: {report['finished_at']}",
        f"status: {report['overall']}",
        "tags: [factory, self-healing, telegram, supervisor]",
        "---",
        "",
        "# Factory Self-Healing Supervisor Status",
        "",
        f"- Source: `{report['source']}`",
        f"- Overall: `{report['overall']}`",
        f"- Fingerprint: `{report.get('fingerprint', '')}`",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for row in red_checks(report.get("final_probe") or report.get("initial_probe") or {}):
        detail = str(row.get("detail") or "").replace("|", "\\|")
        lines.append(f"| {row.get('check')} | `RED` | {detail[:220]} |")
    if report.get("repairs"):
        lines.extend(["", "## Repairs", ""])
        for repair in report["repairs"]:
            lines.append(f"- `{repair['check']}` -> `{repair['status']}` via `{repair.get('action', 'none')}`")
    lines.append("")
    return "\n".join(lines)


def write_status(args: argparse.Namespace, report: dict[str, Any]) -> None:
    if args.dry_run or not args.write_status:
        return
    path = args.wiki / args.status_page
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(status_page(report), encoding="utf-8")


def launchctl_kick(label: str, args: argparse.Namespace) -> dict[str, Any]:
    target = f"gui/{os.getuid()}/{label}"
    if args.dry_run:
        return {"ok": True, "cmd": f"launchctl kickstart -k {target}", "stdout": "", "stderr": "dry-run"}
    return run(["launchctl", "kickstart", "-k", target], timeout=45)


def clean_worktree(args: argparse.Namespace) -> bool:
    """Return True when the worktree is clean (or becomes clean after auto-resolving transient churn)."""
    ok, _paths = auto_resolve_transient_dirty(args)
    return ok


def repair_check(check: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    name = str(check.get("check") or check.get("name") or "unknown")
    detail = str(check.get("detail") or "")

    if name in HUMAN_REQUIRED:
        return {"check": name, "status": "human_required", "reason": HUMAN_REQUIRED[name], "detail": detail}

    if name in LAUNCHD_REPAIRS:
        label = LAUNCHD_REPAIRS[name]
        result = launchctl_kick(label, args)
        return {"check": name, "status": "attempted" if result["ok"] else "failed", "action": f"launchctl kickstart -k {label}", "result": result}

    if name == "openclaw":
        result = {"ok": True, "cmd": "docker restart openclaw", "stdout": "", "stderr": "dry-run"} if args.dry_run else run(["docker", "restart", "openclaw"], timeout=120)
        return {"check": name, "status": "attempted" if result["ok"] else "failed", "action": "docker restart openclaw", "result": result}

    if name == "github_mirror" and "stale" in detail.lower():
        result = {"ok": True, "cmd": "git push github main", "stdout": "", "stderr": "dry-run"} if args.dry_run else run(["git", "push", "github", "main"], cwd=args.wiki, timeout=180)
        return {"check": name, "status": "attempted" if result["ok"] else "failed", "action": "git push github main", "result": result}

    if name == "air_sync_lag":
        if not clean_worktree(args):
            return {"check": name, "status": "skipped", "reason": "dirty_worktree", "detail": detail}
        result = {"ok": True, "cmd": "git pull --ff-only origin main", "stdout": "", "stderr": "dry-run"} if args.dry_run else run(["git", "pull", "--ff-only", "origin", "main"], cwd=args.wiki, timeout=180)
        return {"check": name, "status": "attempted" if result["ok"] else "failed", "action": "git pull --ff-only origin main", "result": result}

    return {"check": name, "status": "unhandled", "detail": detail}


def send_notification(args: argparse.Namespace, report: dict[str, Any]) -> dict[str, Any]:
    if not args.notify or report["overall"] in {"green", "repaired"}:
        return {"sent": False, "reason": "not_needed"}

    # Notification policy gate (2026-05-20 notification-policy-tightening)
    # Map overall status to policy event class: only "human_required" and
    # "unresolved" after 2+ repair attempts reach IMMEDIATE; everything else
    # is SUPPRESS or DIGEST. Dedup is handled by factory_self_heal's own
    # notification_ttl_seconds mechanism below, so pass dedup_key=None here.
    if _POLICY_AVAILABLE:
        event_class = (
            "supervisor-escalation"
            if report["overall"] in {"unresolved", "human_required"}
            else "factory-probe-green"
        )
        if not _policy_should_ping(event_class, "critical", dedup_key=None):
            return {"sent": False, "reason": "policy_suppressed"}
    state = load_state(args.state)
    notifications = state.setdefault("notifications", {})
    key = report.get("fingerprint") or fingerprint(red_checks(report.get("final_probe") or report.get("initial_probe") or {}))
    now_epoch = int(time.time())
    last = int(notifications.get(key, 0) or 0)
    if now_epoch - last < args.notification_ttl_seconds:
        return {"sent": False, "reason": "deduped", "fingerprint": key, "last_sent_epoch": last}

    lines = [
        f"Factory supervisor escalation: {report['overall']}",
        f"Source: {report['source']}",
        f"Fingerprint: {key}",
        "",
        "Madi action required only if listed below:",
    ]
    for row in red_checks(report.get("final_probe") or report.get("initial_probe") or {}):
        lines.append(f"- {row.get('check')}: {str(row.get('detail') or '')[:220]}")
    lines.append("")
    lines.append(f"Ledger: {args.ledger}")
    message = "\n".join(lines)

    if args.dry_run:
        return {"sent": False, "reason": "dry-run_would_send", "fingerprint": key, "message": message}

    result = run(["bash", "tools/tg_send.sh", message], cwd=args.wiki, timeout=45)
    sent = {"sent": result["ok"], "reason": tail(result["stdout"] + result["stderr"]), "fingerprint": key}
    if result["ok"]:
        notifications[key] = now_epoch
        save_state(args.state, state)
    return sent


def evaluate(args: argparse.Namespace, stdin_text: str = "") -> dict[str, Any]:
    if args.stdin_probe_json:
        initial = parse_probe(stdin_text)
    else:
        initial = run_probe(args)

    report: dict[str, Any] = {
        "source": args.source,
        "started_at": iso_now(),
        "finished_at": iso_now(),
        "initial_probe": initial,
        "repairs": [],
        "overall": "green" if initial.get("overall") == "GREEN" else "unresolved",
    }

    if initial.get("overall") == "GREEN":
        append_ledger(args.ledger, report, args.dry_run)
        return report

    for _attempt in range(max(1, args.max_attempts)):
        current_reds = red_checks(initial if "final_probe" not in report else report["final_probe"])
        if not current_reds:
            break
        for item in current_reds:
            repair = repair_check(item, args)
            report["repairs"].append(repair)
        if not any(repair["status"] in {"attempted", "failed"} for repair in report["repairs"]):
            break
        report["final_probe"] = run_probe(args)
        if report["final_probe"].get("overall") == "GREEN":
            report["overall"] = "repaired"
            break

    if report["overall"] != "repaired":
        final_reds = red_checks(report.get("final_probe") or initial)
        report["fingerprint"] = fingerprint(final_reds)
        if any(repair["status"] == "human_required" for repair in report["repairs"]):
            report["overall"] = "human_required"
        else:
            report["overall"] = "unresolved"

    report["finished_at"] = iso_now()
    report["notification"] = send_notification(args, report)
    append_ledger(args.ledger, report, args.dry_run)
    write_status(args, report)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--status-page", type=Path, default=DEFAULT_STATUS_PAGE)
    parser.add_argument("--source", default="manual")
    parser.add_argument("--stdin-probe-json", action="store_true")
    parser.add_argument("--stdin-light-changes", action="store_true")
    parser.add_argument("--notify", action="store_true")
    parser.add_argument("--write-status", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--probe-timeout", type=int, default=180)
    parser.add_argument("--notification-ttl-seconds", type=int, default=4 * 3600)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    stdin_text = sys.stdin.read() if (args.stdin_probe_json or args.stdin_light_changes) else ""
    report = evaluate(args, stdin_text)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"factory_self_heal={report['overall']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
