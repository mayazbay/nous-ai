#!/usr/bin/env python3
"""Hermes factory watchdog for the Nous 24/7 control plane.

Hermes is the supervisor layer, not a second factory runtime. OpenClaw remains
the worker factory; launchd keeps this watchdog alive.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ALMATY = dt.timezone(dt.timedelta(hours=5))
DEFAULT_WIKI = Path("/Users/madia/nous-agaas/wiki")
DEFAULT_PYTHON = Path("/Library/Frameworks/Python.framework/Versions/3.11/bin/python3")
DEFAULT_CONTROL_LOG = Path("/Users/madia/nous-agaas/logs/control-plane-sync.jsonl")
DEFAULT_HERMES_LOG = Path("/Users/madia/nous-agaas/logs/hermes-factory-watchdog.jsonl")
DEFAULT_STATE_PAGE = Path("pages/systems/hermes-factory-watchdog-status.md")
DEFAULT_HUMAN_REMINDER_STATUS = Path("pages/systems/human-owner-reminder-status.md")
DEFAULT_OPENCLAW_HEALTH = "http://127.0.0.1:18789/healthz"
CONTROL_PLANE_LABEL = "com.nous.control-plane-sync"
HUMAN_REMINDER_LABEL = "com.nous.human-owner-reminder"
COMMENT_SWEEP_LABEL = "com.nous.todoist-comment-sweep"
SYNC_STEPS = ("todoist_control_plane", "todoist_register_export", "notion_sync")
BAD_STATUSES = {"blocked", "not_done"}
FACTORY_PROBE = Path("tools/factory_no_drift_probe.sh")


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def iso_now() -> str:
    return now_kzt().isoformat()


def slugify(text: str, limit: int = 56) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return (slug or "factory-slice")[:limit].strip("-")


def run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 60) -> dict[str, Any]:
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
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "ok": proc.returncode == 0,
            "duration_ms": int((time.monotonic() - started) * 1000),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": " ".join(str(part) for part in cmd),
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or f"timeout after {timeout}s",
            "ok": False,
            "duration_ms": int((time.monotonic() - started) * 1000),
        }


def tail(text: str, limit: int = 1200) -> str:
    clean = str(text or "").strip()
    return clean if len(clean) <= limit else clean[-limit:]


def load_jsonl(path: Path, limit: int = 80) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def parse_dt(value: Any) -> dt.datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ALMATY)
    return parsed.astimezone(ALMATY)


def step_status(cycle: dict[str, Any], name: str) -> str:
    for step in cycle.get("steps", []):
        if step.get("name") == name:
            return str(step.get("status") or "missing")
    return "missing"


def frontmatter_value(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip('"').strip("'")


def latest_finished_cycle(cycles: list[dict[str, Any]]) -> dict[str, Any] | None:
    finished = [cycle for cycle in cycles if cycle.get("finished_at")]
    return finished[-1] if finished else None


def http_ok(url: str, timeout: float) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(256).decode("utf-8", errors="replace")
            return 200 <= response.status < 300, f"http_{response.status}:{body[:120]}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"http_error:{exc}"


def send_telegram(wiki: Path, message: str, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"ok": True, "detail": "dry-run"}
    result = run(["bash", "tools/tg_send.sh", message], cwd=wiki, timeout=45)
    return {"ok": result["ok"], "detail": tail(result["stdout"] + result["stderr"])}


def kick_launchd(label: str, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"ok": True, "detail": "dry-run"}
    target = f"gui/{os.getuid()}/{label}"
    result = run(["launchctl", "kickstart", "-k", target], timeout=30)
    return {"ok": result["ok"], "detail": tail(result["stdout"] + result["stderr"])}


def create_factory_slice(wiki: Path, category: str, title: str, evidence: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    stamp = now_kzt().strftime("%Y-%m-%d-%H-%M-%S")
    rel = Path("pages/task-results") / f"{stamp}-hermes-{slugify(title)}.md"
    if dry_run:
        return {"ok": True, "path": str(rel), "detail": "dry-run"}
    path = wiki / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [
        "---",
        "type: task-result",
        f"id: hermes-{stamp}",
        f'title: "Hermes Factory Slice - {title}"',
        f"date: {now_kzt().date().isoformat()}",
        "status: not_done",
        "tags: [hermes, factory, watchdog, incident]",
        "---",
        "",
        f"# Hermes Factory Slice - {title}",
        "",
        f"- Category: `{category}`",
        f"- Created: `{iso_now()}`",
        "",
        "## Инструкция фабрике",
        "",
        "1. Открой доказательства ниже и не делай предположений.",
        "2. Найди первопричину, почему автоматический путь не стал green.",
        "3. Исправь минимально возможным изменением.",
        "4. Проверь командой, сохрани вывод, git HEAD и counter-check.",
        "5. Если это новый повторяемый класс, обнови соответствующий SKILL.md и gbrain timeline.",
        "",
        "## Evidence",
        "",
        "```json",
        json.dumps(evidence, ensure_ascii=False, indent=2, default=str)[:5000],
        "```",
        "",
    ]
    path.write_text("\n".join(body), encoding="utf-8")
    return {"ok": True, "path": str(rel), "detail": "created"}


def check_control_plane(args: argparse.Namespace, cycles: list[dict[str, Any]]) -> dict[str, Any]:
    latest = latest_finished_cycle(cycles)
    if not latest:
        kick = kick_launchd(CONTROL_PLANE_LABEL, args.dry_run)
        return {"name": "control_plane_recency", "status": "not_done", "summary": "no finished cycle found; kick requested", "evidence": kick}
    finished_at = parse_dt(latest.get("finished_at"))
    if not finished_at:
        kick = kick_launchd(CONTROL_PLANE_LABEL, args.dry_run)
        return {"name": "control_plane_recency", "status": "not_done", "summary": "latest cycle has unparsable finished_at; kick requested", "evidence": {"cycle": latest.get("cycle_id"), "kick": kick}}
    age_s = (now_kzt() - finished_at).total_seconds()
    if age_s > args.max_control_plane_age_seconds:
        kick = kick_launchd(CONTROL_PLANE_LABEL, args.dry_run)
        return {"name": "control_plane_recency", "status": "not_done", "summary": f"stale age_s={int(age_s)}; kick requested", "evidence": {"cycle": latest.get("cycle_id"), "finished_at": latest.get("finished_at"), "kick": kick}}
    return {"name": "control_plane_recency", "status": "done", "summary": f"fresh age_s={int(age_s)}", "evidence": {"cycle": latest.get("cycle_id"), "finished_at": latest.get("finished_at")}}


def check_openclaw(args: argparse.Namespace) -> dict[str, Any]:
    ok, detail = http_ok(args.openclaw_health_url, args.timeout)
    if ok:
        return {"name": "openclaw_supervision", "status": "done", "summary": "OpenClaw health endpoint green", "evidence": detail}
    restart = {"ok": False, "detail": "restart disabled"}
    if not args.no_restart_openclaw and not args.dry_run:
        result = run(["docker", "restart", "openclaw"], timeout=90)
        restart = {"ok": result["ok"], "detail": tail(result["stdout"] + result["stderr"])}
    notify = send_telegram(args.wiki, f"🔴 Hermes: OpenClaw down; restart={restart.get('ok')} detail={detail}", args.dry_run)
    return {"name": "openclaw_supervision", "status": "not_done" if restart.get("ok") else "blocked", "summary": "OpenClaw health failed; restart attempted", "evidence": {"health": detail, "restart": restart, "telegram": notify}}


def check_repeated_sync_failures(args: argparse.Namespace, cycles: list[dict[str, Any]]) -> dict[str, Any]:
    recent = [cycle for cycle in cycles if cycle.get("finished_at")][-2:]
    failures: dict[str, list[str]] = {}
    if len(recent) == 2:
        for name in SYNC_STEPS:
            statuses = [step_status(cycle, name) for cycle in recent]
            if all(status in BAD_STATUSES for status in statuses):
                failures[name] = statuses
    if not failures:
        return {"name": "sync_failure_escalation", "status": "done", "summary": "no repeated Todoist/Notion failures", "evidence": {"recent_cycles": [c.get("cycle_id") for c in recent]}}
    slice_result = create_factory_slice(
        args.wiki,
        "control-plane-sync",
        "repeated Todoist or Notion sync failure",
        {"failures": failures, "cycles": recent},
        args.dry_run,
    )
    notify = send_telegram(args.wiki, f"🟡 Hermes: created factory slice for repeated sync failure {slice_result.get('path')}", args.dry_run)
    return {"name": "sync_failure_escalation", "status": "not_done", "summary": "repeated failure converted into factory slice", "evidence": {"failures": failures, "slice": slice_result, "telegram": notify}}


def check_human_owner_reminder(args: argparse.Namespace) -> dict[str, Any]:
    status_path = args.wiki / args.human_reminder_status
    if not status_path.exists():
        kick = kick_launchd(COMMENT_SWEEP_LABEL, args.dry_run)
        return {
            "name": "human_owner_reminder",
            "status": "not_done",
            "summary": "status page missing; comment sweep kick requested",
            "evidence": {"status_page": str(args.human_reminder_status), "kick": kick},
        }
    text = status_path.read_text(encoding="utf-8", errors="replace")
    last = parse_dt(frontmatter_value(text, "last_updated"))
    if not last:
        kick = kick_launchd(COMMENT_SWEEP_LABEL, args.dry_run)
        return {
            "name": "human_owner_reminder",
            "status": "not_done",
            "summary": "last_updated missing or invalid; comment sweep kick requested",
            "evidence": {"status_page": str(args.human_reminder_status), "kick": kick},
        }
    age_s = (now_kzt() - last).total_seconds()
    if age_s > args.max_human_reminder_age_seconds:
        kick = kick_launchd(COMMENT_SWEEP_LABEL, args.dry_run)
        return {
            "name": "human_owner_reminder",
            "status": "not_done",
            "summary": f"stale age_s={int(age_s)}; comment sweep kick requested",
            "evidence": {"status_page": str(args.human_reminder_status), "last_updated": last.isoformat(), "kick": kick},
        }
    return {
        "name": "human_owner_reminder",
        "status": "done",
        "summary": f"fresh age_s={int(age_s)}",
        "evidence": {"status_page": str(args.human_reminder_status), "last_updated": last.isoformat()},
    }


def check_github_incidents(args: argparse.Namespace) -> dict[str, Any]:
    gh = run(["gh", "run", "list", "--limit", "20", "--json", "databaseId,name,status,conclusion,headSha,createdAt,url"], cwd=args.wiki, timeout=45)
    if not gh["ok"]:
        return {"name": "github_failure_noise", "status": "skipped", "summary": "gh CLI unavailable or unauthenticated", "evidence": tail(gh["stdout"] + gh["stderr"])}
    try:
        runs = json.loads(gh["stdout"])
    except json.JSONDecodeError:
        return {"name": "github_failure_noise", "status": "skipped", "summary": "gh output not JSON", "evidence": tail(gh["stdout"])}
    failures = [row for row in runs if row.get("status") == "completed" and row.get("conclusion") in {"failure", "cancelled", "timed_out", "action_required"}]
    if not failures:
        return {"name": "github_failure_noise", "status": "done", "summary": "no recent failed GitHub runs", "evidence": {"checked": len(runs)}}
    incident_id = str(failures[0].get("databaseId") or failures[0].get("headSha") or "unknown")
    rel = Path("pages/audits") / f"INCIDENT-github-actions-{incident_id}.md"
    incident_existed = (args.wiki / rel).exists()
    if not args.dry_run and not incident_existed:
        (args.wiki / rel).parent.mkdir(parents=True, exist_ok=True)
        (args.wiki / rel).write_text(
            "\n".join(
                [
                    "---",
                    "type: audit",
                    f"id: INCIDENT-github-actions-{incident_id}",
                    f'title: "GitHub Actions Failure Noise - {incident_id}"',
                    f"date: {now_kzt().date().isoformat()}",
                    "status: not_done",
                    "tags: [github, incident, hermes, factory]",
                    "---",
                    "",
                    f"# GitHub Actions Failure Noise - {incident_id}",
                    "",
                    "## Инструкция фабрике",
                    "",
                    "1. Открой GitHub run по ссылке.",
                    "2. Определи первопричину: quota, auth, generated commit loop, real test failure, или flaky infra.",
                    "3. Исправь gate/workflow так, чтобы generated commits не создавали бессмысленный цикл.",
                    "4. Проверь следующий run: skipped или success, но не repeated failure.",
                    "",
                    "## Evidence",
                    "",
                    "```json",
                    json.dumps(failures[:5], ensure_ascii=False, indent=2, default=str),
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    status = "done" if incident_existed else "not_done"
    summary = f"known failed GitHub run already recorded: {incident_id}" if incident_existed else f"recent failed GitHub runs={len(failures)}"
    return {"name": "github_failure_noise", "status": status, "summary": summary, "evidence": {"incident": str(rel), "failures": failures[:5]}}


def check_model_bakeoff(args: argparse.Namespace) -> dict[str, Any]:
    files = sorted((args.wiki / "pages/audits").glob("model-bakeoff-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if files:
        age_s = time.time() - files[0].stat().st_mtime
        if age_s <= args.max_model_bakeoff_age_seconds:
            return {"name": "model_bakeoff_freshness", "status": "done", "summary": f"fresh age_s={int(age_s)}", "evidence": str(files[0].relative_to(args.wiki))}
    if args.dry_run:
        return {"name": "model_bakeoff_freshness", "status": "not_done", "summary": "bakeoff stale or missing; dry-run did not run", "evidence": str(files[0]) if files else "missing"}
    result = run([str(args.python), "tools/control_plane_sync_loop.py", "--force-model-bakeoff", "--no-telegram", "--json"], cwd=args.wiki, timeout=1200)
    return {"name": "model_bakeoff_freshness", "status": "done" if result["ok"] else "not_done", "summary": "forced control-plane model bakeoff" if result["ok"] else "forced bakeoff failed", "evidence": tail(result["stdout"] + result["stderr"])}


def parse_probe(stdout: str) -> dict[str, Any] | None:
    start = stdout.find("{")
    if start < 0:
        return None
    try:
        payload = json.loads(stdout[start:])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def check_factory_probe(args: argparse.Namespace) -> dict[str, Any]:
    probe_path = args.wiki / FACTORY_PROBE
    if not probe_path.exists():
        return {"name": "factory_probe", "status": "skipped", "summary": "factory probe script missing", "evidence": str(FACTORY_PROBE)}
    first = run(["bash", FACTORY_PROBE, "--json", "--no-telegram"], cwd=args.wiki, timeout=180)
    payload = parse_probe(first["stdout"])
    if not payload:
        return {"name": "factory_probe", "status": "not_done", "summary": "factory probe output was not JSON", "evidence": tail(first["stdout"] + first["stderr"])}
    checks = {str(row.get("check")): row for row in payload.get("checks", []) if isinstance(row, dict)}
    air_lag = checks.get("air_sync_lag")
    if payload.get("overall") == "GREEN":
        return {"name": "factory_probe", "status": "done", "summary": "factory probe green", "evidence": payload}
    if air_lag and air_lag.get("status") == "RED":
        pull = {"ok": True, "detail": "dry-run"}
        rerun_payload = payload
        if not args.dry_run:
            pull_result = run(["git", "pull", "--rebase", "origin", "main"], cwd=args.wiki, timeout=180)
            pull = {"ok": pull_result["ok"], "detail": tail(pull_result["stdout"] + pull_result["stderr"])}
            second = run(["bash", FACTORY_PROBE, "--json", "--no-telegram"], cwd=args.wiki, timeout=180)
            rerun_payload = parse_probe(second["stdout"]) or {"parse_error": tail(second["stdout"] + second["stderr"])}
        if isinstance(rerun_payload, dict) and rerun_payload.get("overall") == "GREEN":
            return {"name": "factory_probe", "status": "done", "summary": "air_sync_lag repaired by pull and probe rerun green", "evidence": {"first": payload, "pull": pull, "rerun": rerun_payload}}
        return {"name": "factory_probe", "status": "not_done", "summary": "air_sync_lag detected; pull attempted but probe still not green", "evidence": {"first": payload, "pull": pull, "rerun": rerun_payload}}
    return {"name": "factory_probe", "status": "not_done", "summary": f"factory probe not green: reds={payload.get('reds')}", "evidence": payload}


def render_status(report: dict[str, Any]) -> str:
    lines = [
        "---",
        "type: system",
        "id: hermes-factory-watchdog-status",
        'title: "Hermes Factory Watchdog Status"',
        f"last_updated: {report['finished_at']}",
        f"status: {report['overall_status']}",
        "tags: [hermes, factory, watchdog, openclaw, todoist, notion, github]",
        "---",
        "",
        "# Hermes Factory Watchdog Status",
        "",
        f"- Last run: `{report['run_id']}`",
        f"- Overall: `{report['overall_status']}`",
        "",
        "| Check | Status | Summary |",
        "|---|---:|---|",
    ]
    for check in report["checks"]:
        summary = str(check.get("summary") or "").replace("|", "\\|")
        lines.append(f"| {check['name']} | `{check['status']}` | {summary} |")
    lines.append("")
    return "\n".join(lines)


def should_write_status(report: dict[str, Any], existing_text: str | None) -> bool:
    """Write on first run, on active problems, or when clearing stale yellow/red."""
    if existing_text is None:
        return True
    if report["overall_status"] != "done":
        return True
    for check in report.get("checks", []):
        if str(check.get("name") or "") not in existing_text:
            return True
    return "status: done" not in existing_text


def writeback(args: argparse.Namespace, paths: list[Path]) -> dict[str, Any]:
    if args.dry_run or not paths:
        return {"ok": True, "detail": "dry-run or no paths"}
    rels = [str(path) for path in paths]
    add = run(["git", "-c", "core.hooksPath=/dev/null", "add", *rels], cwd=args.wiki, timeout=90)
    if not add["ok"]:
        return {"ok": False, "detail": tail(add["stdout"] + add["stderr"])}
    diff = run(["git", "diff", "--cached", "--quiet", "--", *rels], cwd=args.wiki, timeout=45)
    committed = False
    if diff["returncode"] == 1:
        commit = run(["git", "-c", "core.hooksPath=/dev/null", "commit", "--no-verify", "-m", f"hermes-watchdog: {now_kzt().strftime('%Y-%m-%d-%H%M%S')}"], cwd=args.wiki, timeout=120)
        if not commit["ok"]:
            return {"ok": False, "detail": tail(commit["stdout"] + commit["stderr"])}
        committed = True
    elif diff["returncode"] != 0:
        return {"ok": False, "detail": tail(diff["stdout"] + diff["stderr"])}
    run(["git", "pull", "--rebase", "origin", "main"], cwd=args.wiki, timeout=180)
    if run(["git", "remote", "get-url", "github"], cwd=args.wiki, timeout=30)["ok"]:
        fetch = run(["git", "fetch", "github", "main"], cwd=args.wiki, timeout=120)
        if fetch["ok"]:
            rebase = run(["git", "-c", "core.hooksPath=/dev/null", "rebase", "github/main"], cwd=args.wiki, timeout=180)
            if not rebase["ok"]:
                run(["git", "rebase", "--abort"], cwd=args.wiki, timeout=45)
                return {"ok": False, "detail": tail(rebase["stdout"] + rebase["stderr"])}
    origin = run(["git", "push", "origin", "main"], cwd=args.wiki, timeout=180)
    github = run(["git", "push", "github", "main"], cwd=args.wiki, timeout=180)
    return {"ok": origin["ok"] and github["ok"], "detail": {"committed": committed, "origin": tail(origin["stdout"] + origin["stderr"]), "github": tail(github["stdout"] + github["stderr"])}}


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    cycles = load_jsonl(args.control_log)
    checks = [
        check_control_plane(args, cycles),
        check_openclaw(args),
        check_factory_probe(args),
        check_repeated_sync_failures(args, cycles),
        check_human_owner_reminder(args),
        check_github_incidents(args),
        check_model_bakeoff(args),
    ]
    worst = "done"
    if any(check["status"] == "blocked" for check in checks):
        worst = "blocked"
    elif any(check["status"] == "not_done" for check in checks):
        worst = "not_done"
    return {
        "run_id": now_kzt().strftime("%Y-%m-%d-%H%M%S"),
        "started_at": iso_now(),
        "finished_at": iso_now(),
        "overall_status": worst,
        "checks": checks,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--control-log", type=Path, default=DEFAULT_CONTROL_LOG)
    parser.add_argument("--hermes-log", type=Path, default=DEFAULT_HERMES_LOG)
    parser.add_argument("--state-page", type=Path, default=DEFAULT_STATE_PAGE)
    parser.add_argument("--human-reminder-status", type=Path, default=DEFAULT_HUMAN_REMINDER_STATUS)
    parser.add_argument("--openclaw-health-url", default=DEFAULT_OPENCLAW_HEALTH)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--max-control-plane-age-seconds", type=int, default=14400)
    parser.add_argument("--max-human-reminder-age-seconds", type=int, default=4 * 3600)
    parser.add_argument("--max-model-bakeoff-age-seconds", type=int, default=8 * 86400)
    parser.add_argument("--no-restart-openclaw", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = evaluate(args)
    touched: list[Path] = []
    if not args.dry_run:
        args.hermes_log.parent.mkdir(parents=True, exist_ok=True)
        with args.hermes_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, sort_keys=True, default=str) + "\n")
        state_abs = args.wiki / args.state_page
        existing_text = state_abs.read_text(encoding="utf-8", errors="replace") if state_abs.exists() else None
        if should_write_status(report, existing_text):
            state_abs.parent.mkdir(parents=True, exist_ok=True)
            state_abs.write_text(render_status(report), encoding="utf-8")
            touched.append(args.state_page)
        for check in report["checks"]:
            evidence = check.get("evidence")
            if isinstance(evidence, dict):
                for key in ("slice",):
                    value = evidence.get(key)
                    if isinstance(value, dict) and value.get("path"):
                        touched.append(Path(value["path"]))
            if check["name"] == "github_failure_noise" and isinstance(evidence, dict) and evidence.get("incident"):
                touched.append(Path(evidence["incident"]))
        report["writeback"] = writeback(args, touched)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"hermes={report['overall_status']}")
    return 0 if report["overall_status"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
