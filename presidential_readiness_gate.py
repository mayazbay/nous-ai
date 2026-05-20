#!/usr/bin/env python3
"""Read-only presidential phone-control readiness gate.

This gate composes existing Nous probes into one compact status surface for the
Telegram -> Air -> OpenClaw -> Obsidian/gbrain/OpenBrain control plane.

Default mode is read-mostly:
- no Telegram getUpdates
- no Todoist/Notion writes
- no git writes
- no OpenClaw promotion

The only side-effecting path is the explicit --send-phone-canary flag, which
uses tools/tg_send.sh (send-only) and records the returned message id.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WIKI = REPO_ROOT
DEFAULT_PROTECTED_SCOPE = (
    "tools/command_center.py,"
    "tools/telegram_poll.py,"
    "pages/systems/,"
    "pages/skills/*"
)
DEFAULT_HANDOFF = "pages/progress/HANDOFF-AUTO-2026-05-20-09-00.md"
DEFAULT_CANARY_MESSAGE = (
    "CANARY 2026-05-20 presidential control plane: "
    "reply /status and /ask ping from iPhone/iPad. production-write-requires-ack"
)
VPS_HOST = "root@65.108.215.200"


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    cmd: str


def quote_cmd(cmd: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in cmd)


def run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 60) -> CommandResult:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return CommandResult(
            ok=proc.returncode == 0,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            cmd=quote_cmd(cmd),
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            ok=False,
            returncode=124,
            stdout=exc.stdout or "",
            stderr=exc.stderr or f"timeout after {timeout}s",
            cmd=quote_cmd(cmd),
        )
    except FileNotFoundError as exc:
        return CommandResult(
            ok=False,
            returncode=127,
            stdout="",
            stderr=f"missing executable: {exc.filename}",
            cmd=quote_cmd(cmd),
        )


def ssh(host: str, script: str, *, timeout: int = 60) -> CommandResult:
    return run(
        ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", host, script],
        timeout=timeout,
    )


def check(name: str, status: str, detail: str, evidence: Any | None = None) -> dict[str, Any]:
    if status not in {"GREEN", "YELLOW", "RED"}:
        raise ValueError(f"invalid status: {status}")
    item: dict[str, Any] = {"check": name, "status": status, "detail": detail}
    if evidence is not None:
        item["evidence"] = evidence
    return item


def json_from(result: CommandResult) -> Any | None:
    try:
        return json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError):
        return None


def summarize_command_failure(result: CommandResult, limit: int = 500) -> str:
    text = (result.stderr or result.stdout or f"exit={result.returncode}").strip()
    return text[-limit:] if len(text) > limit else text


def overall_from(checks: list[dict[str, Any]]) -> dict[str, Any]:
    reds = [item for item in checks if item["status"] == "RED"]
    yellows = [item for item in checks if item["status"] == "YELLOW"]
    return {
        "overall": "RED" if reds else ("YELLOW" if yellows else "GREEN"),
        "reds": len(reds),
        "yellows": len(yellows),
        "checks": checks,
    }


def status_from_factory_probe(payload: Any) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return "RED", "factory probe did not return JSON"
    overall = str(payload.get("overall") or "UNKNOWN")
    reds = int(payload.get("reds") or 0)
    if overall == "GREEN" and reds == 0:
        return "GREEN", "overall=GREEN reds=0"
    return "RED", f"overall={overall} reds={reds}"


def status_from_truth_gate(payload: Any) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return "RED", "truth gate did not return JSON"
    overall = str(payload.get("overall") or "UNKNOWN")
    reds = int(payload.get("reds") or 0)
    yellows = int(payload.get("yellows") or 0)
    if overall == "GREEN" and reds == 0:
        return ("YELLOW" if yellows else "GREEN"), f"overall={overall} reds={reds} yellows={yellows}"
    return "RED", f"overall={overall} reds={reds} yellows={yellows}"


def status_from_control_plane(payload: Any) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return "RED", "control-plane dry-run did not return JSON"
    status = str(payload.get("overall_status") or "UNKNOWN")
    if status == "done":
        return "GREEN", "overall_status=done"
    if status == "blocked":
        return "YELLOW", "overall_status=blocked"
    return "RED", f"overall_status={status}"


def status_from_openbrain(payload: Any) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return "RED", "OpenBrain projection did not return JSON"
    if payload.get("ok") is not True or payload.get("projection_failed"):
        return "RED", f"ok={payload.get('ok')} projection_failed={payload.get('projection_failed')}"
    creates = int(payload.get("would_create") or 0)
    updates = int(payload.get("would_update") or 0)
    if creates or updates:
        return "YELLOW", f"would_create={creates} would_update={updates}"
    return "GREEN", f"exists={payload.get('exists')} thoughts_seen={payload.get('thoughts_seen')}"


def status_from_gbrain_doctor(output: str, returncode: int) -> tuple[str, str, Any | None]:
    payload = None
    for line in reversed(output.splitlines()):
        candidate = line.strip()
        if not candidate.startswith("{"):
            continue
        try:
            payload = json.loads(candidate)
            break
        except json.JSONDecodeError:
            continue
    if not isinstance(payload, dict):
        return "RED", f"doctor exit={returncode}; JSON not found", None
    status = str(payload.get("status") or "unknown")
    score = payload.get("health_score")
    if status == "ok":
        return "GREEN", f"status=ok health_score={score}", payload
    if status == "warnings":
        return "YELLOW", f"status=warnings health_score={score}", payload
    return "RED", f"status={status} health_score={score}", payload


def summarize_session_scan(output: str) -> tuple[str, str]:
    if "no other active sessions" in output:
        return "GREEN", "no overlap on protected paths"
    if "PARALLEL" in output:
        first = next((line.strip() for line in output.splitlines() if line.strip().startswith("•")), "")
        return "YELLOW", f"active overlap: {first or 'see evidence'}"
    return "RED", output.strip() or "session scan unavailable"


def qmd_get_script(path: str) -> str:
    quoted = shlex.quote(f"qmd://nous/{path}")
    return f"qmd get {quoted} 2>/dev/null | sed -n '1,40p'"


def check_qmd_exact_handoff(path: str) -> dict[str, Any]:
    result = ssh(VPS_HOST, qmd_get_script(path), timeout=45)
    text = result.stdout
    ok = result.ok and ("type: progress" in text or "Factory auto-checkpoint" in text)
    if ok:
        return check("qmd_latest_handoff_readback", "GREEN", f"qmd get {path} returned handoff frontmatter")
    status = "YELLOW" if result.returncode in {0, 1} else "RED"
    return check(
        "qmd_latest_handoff_readback",
        status,
        f"qmd get {path} did not prove exact readback",
        {"returncode": result.returncode, "stdout": text[-800:], "stderr": result.stderr[-800:]},
    )


def check_qmd_freshness(wiki: Path) -> dict[str, Any]:
    result = run(["bash", "tools/qmd_real_freshness.sh", "--json"], cwd=wiki, timeout=30)
    payload = json_from(result)
    if not isinstance(payload, dict):
        return check("qmd_real_freshness", "RED", summarize_command_failure(result))
    status = payload.get("status")
    if status == "fresh":
        return check("qmd_real_freshness", "GREEN", str(payload.get("reason")), payload)
    if status == "stale":
        return check("qmd_real_freshness", "YELLOW", str(payload.get("reason")), payload)
    return check("qmd_real_freshness", "RED", str(payload.get("reason")), payload)


def check_telegram_poller_launchd() -> dict[str, Any]:
    script = (
        "launchctl print gui/501/com.nous.telegram-poll 2>/dev/null "
        "| egrep 'state =|last exit code|program =|runs =|pid =|working directory ='"
    )
    result = ssh("air", script, timeout=30)
    text = result.stdout + result.stderr
    ok = result.ok and "last exit code = 0" in text and "state =" in text
    if ok:
        state = "running" if "state = running" in text or "pid =" in text else "loaded/idle"
        return check("telegram_poller_launchd", "GREEN", f"launchd {state} with last exit code 0", text.strip())
    return check("telegram_poller_launchd", "RED", "telegram poller launchd not proven running", text.strip())


def check_canary_518_health() -> dict[str, Any]:
    result = ssh(
        "air",
        "curl -fsS --max-time 5 http://127.0.0.1:18790/health",
        timeout=15,
    )
    text = (result.stdout + result.stderr).strip()
    if result.ok and ("live" in text or '"ok":true' in text):
        return check("openclaw_518_canary_health", "GREEN", "HTTP 200 on port 18790", result.stdout.strip()[:500])
    return check(
        "openclaw_518_canary_health",
        "YELLOW",
        "5.18 canary on 18790 not responding; production 18789 remains separate",
        text[-500:],
    )


def check_satory_queue(wiki: Path) -> dict[str, Any]:
    result = ssh(
        "air",
        "cd ~/nous-agaas/wiki && python3 tools/satory_ai_factory_queue.py --dry-run --refresh --limit 12 --json",
        timeout=240,
    )
    payload = json_from(result)
    if not isinstance(payload, dict):
        return check("satory_queue_dry_run", "RED", summarize_command_failure(result))
    selected = int(payload.get("selected") or 0)
    status = "GREEN" if selected > 0 else "YELLOW"
    detail = f"selected={selected}; dry-run ok"
    return check("satory_queue_dry_run", status, detail, {"selected": selected, "results": payload.get("results", [])[:3]})


def send_phone_canary(wiki: Path, message: str) -> dict[str, Any]:
    result = run(["bash", "tools/tg_send.sh", message], cwd=wiki, timeout=30)
    text = result.stdout + result.stderr
    if result.ok:
        match = re.search(r"msg_id=([0-9?]+)", text)
        msg_id = match.group(1) if match else "unknown"
        return check("telegram_phone_canary_send", "GREEN", f"sent msg_id={msg_id}", text.strip())
    return check("telegram_phone_canary_send", "RED", summarize_command_failure(result), text.strip())


def dry_phone_canary() -> dict[str, Any]:
    return check(
        "telegram_phone_canary_send",
        "YELLOW",
        "not sent in read-only mode; rerun with --send-phone-canary for live phone proof",
    )


def recorded_phone_canary(msg_id: str) -> dict[str, Any]:
    return check(
        "telegram_phone_canary_send",
        "GREEN",
        f"sent earlier msg_id={msg_id}; no duplicate send",
    )


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    wiki = args.wiki
    checks: list[dict[str, Any]] = []

    session_scan = run(["bash", "tools/session_scan.sh", "--overlap-with", args.protected_scope], cwd=wiki, timeout=30)
    scan_status, scan_detail = summarize_session_scan(session_scan.stdout + session_scan.stderr)
    checks.append(check("session_overlap_protected_paths", scan_status, scan_detail, session_scan.stdout.strip()))

    checks.append(check_telegram_poller_launchd())

    factory = run(["bash", "tools/factory_no_drift_probe.sh", "--json", "--no-telegram", "--no-repair"], cwd=wiki, timeout=240)
    payload = json_from(factory)
    status, detail = status_from_factory_probe(payload)
    checks.append(check("factory_no_drift_probe", status, detail, payload if payload is not None else summarize_command_failure(factory)))

    truth = run(["python3", "tools/telegram_openclaw_factory_truth_gate.py", "--json"], cwd=wiki, timeout=240)
    payload = json_from(truth)
    status, detail = status_from_truth_gate(payload)
    checks.append(check("telegram_openclaw_truth_gate", status, detail, payload if payload is not None else summarize_command_failure(truth)))

    control = run(
        [
            "python3",
            "tools/control_plane_sync_loop.py",
            "--wiki",
            str(wiki),
            "--dry-run",
            "--json",
            "--no-telegram",
            "--no-apply-todoist",
        ],
        cwd=wiki,
        timeout=240,
    )
    payload = json_from(control)
    status, detail = status_from_control_plane(payload)
    checks.append(check("control_plane_sync_dry_run", status, detail, payload if payload is not None else summarize_command_failure(control)))

    openbrain = run(
        ["python3", "tools/openbrain_project_to_wiki.py", "--dry-run", "--json", "--limit", "20", "--days", "7"],
        cwd=wiki,
        timeout=120,
    )
    payload = json_from(openbrain)
    status, detail = status_from_openbrain(payload)
    checks.append(check("openbrain_projection_dry_run", status, detail, payload if payload is not None else summarize_command_failure(openbrain)))

    gbrain = ssh(VPS_HOST, "cd /opt/nous-agaas/gbrain && ./bin/gbrain doctor --json", timeout=180)
    status, detail, evidence = status_from_gbrain_doctor(gbrain.stdout + gbrain.stderr, gbrain.returncode)
    checks.append(check("gbrain_doctor", status, detail, evidence))

    checks.append(check_qmd_freshness(wiki))
    checks.append(check_qmd_exact_handoff(args.latest_handoff))
    checks.append(check_satory_queue(wiki))
    checks.append(check_canary_518_health())

    if args.send_phone_canary:
        checks.append(send_phone_canary(wiki, args.canary_message))
    elif args.phone_canary_msg_id:
        checks.append(recorded_phone_canary(args.phone_canary_msg_id))
    else:
        checks.append(dry_phone_canary())

    result = overall_from(checks)
    result["ts"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    result["wiki"] = str(wiki)
    result["latest_handoff"] = args.latest_handoff
    result["side_effects"] = {"telegram_canary_sent": bool(args.send_phone_canary)}
    return result


def render_summary(payload: dict[str, Any]) -> str:
    icon = {"GREEN": "GREEN", "YELLOW": "YELLOW", "RED": "RED"}
    lines = [
        f"Presidential readiness: {payload['overall']} "
        f"(red={payload['reds']} yellow={payload['yellows']})"
    ]
    for item in payload["checks"]:
        lines.append(f"- {icon[item['status']]} {item['check']}: {item['detail']}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--protected-scope", default=DEFAULT_PROTECTED_SCOPE)
    parser.add_argument("--latest-handoff", default=DEFAULT_HANDOFF)
    parser.add_argument("--send-phone-canary", action="store_true")
    parser.add_argument("--phone-canary-msg-id", default="")
    parser.add_argument("--canary-message", default=DEFAULT_CANARY_MESSAGE)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = evaluate(args)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render_summary(result))
    return 0 if result["overall"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
