#!/usr/bin/env python3
"""Non-promoting verifier for the Hermes 24h factory-green gate.

This watcher may create the green 24h receipt after strict no-drift evidence is
true. It must never promote Hermes. Promotion stays an explicit human approval
step that runs the existing promotion runner with `--promote`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any


ALMATY = dt.timezone(dt.timedelta(hours=5))
DEFAULT_WIKI = Path("/Users/madia/nous-agaas/wiki")
DEFAULT_PYTHON = Path("/Library/Frameworks/Python.framework/Versions/3.11/bin/python3")
DEFAULT_WATCHDOG_LOG = Path("/Users/madia/nous-agaas/logs/hermes-factory-watchdog.jsonl")
DEFAULT_VERIFIER_LOG = Path("/Users/madia/nous-agaas/logs/hermes-24h-gate-verifier.jsonl")
DEFAULT_STATE_PAGE = Path("pages/systems/hermes-24h-gate-verifier-status.md")
DEFAULT_MIN_SAMPLES = 48
GREEN_MARKER = "NOUS_HERMES_24H_GATE_OK"
RESET_PREFIX = "pages/audits/HERMES-24H-GATE-RESET-"
GREEN_PREFIX = "pages/audits/HERMES-24H-GATE-GREEN-"


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


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


def parse_kzt_wall_clock(value: str) -> dt.datetime | None:
    match = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+KZT", value)
    if not match:
        return None
    parsed = dt.datetime.strptime(" ".join(match.groups()), "%Y-%m-%d %H:%M")
    return parsed.replace(tzinfo=ALMATY)


def tail(text: str, limit: int = 4000) -> str:
    clean = str(text or "").strip()
    return clean if len(clean) <= limit else clean[-limit:]


def run(cmd: list[str | Path], *, cwd: Path | None = None, timeout: int = 180) -> dict[str, Any]:
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


def parse_json_stdout(result: dict[str, Any]) -> dict[str, Any] | None:
    text = str(result.get("stdout") or "")
    start = text.find("{")
    if start < 0:
        return None
    try:
        payload = json.loads(text[start:])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def latest_reset_candidate(wiki: Path) -> dict[str, Any] | None:
    matches = sorted(wiki.glob(RESET_PREFIX + "*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in matches:
        text = path.read_text(encoding="utf-8", errors="replace")
        candidate = parse_kzt_wall_clock(text)
        if candidate:
            return {
                "path": str(path.relative_to(wiki)),
                "candidate_end": candidate,
                "window_start": candidate - dt.timedelta(hours=24),
            }
    return None


def existing_green_receipts(wiki: Path) -> list[Path]:
    receipts: list[Path] = []
    for path in sorted(wiki.glob(GREEN_PREFIX + "*.md")):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            if GREEN_MARKER in text and re.search(r"(?im)^status:\s*green\b", text):
                receipts.append(path)
    return receipts


def load_jsonl(path: Path, limit: int = 1000) -> list[dict[str, Any]]:
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


def factory_probe_sample(row: dict[str, Any]) -> dict[str, Any] | None:
    finished_at = parse_dt(row.get("finished_at") or row.get("started_at"))
    if not finished_at:
        return None
    for check in row.get("checks", []):
        if not isinstance(check, dict) or check.get("name") != "factory_probe":
            continue
        evidence = check.get("evidence") if isinstance(check.get("evidence"), dict) else {}
        red_count = evidence.get("reds")
        try:
            red_count_int = int(red_count)
        except (TypeError, ValueError):
            red_count_int = 999
        green = check.get("status") == "done" and evidence.get("overall") == "GREEN" and red_count_int == 0
        return {
            "finished_at": finished_at,
            "green": green,
            "status": check.get("status"),
            "summary": check.get("summary"),
            "overall": evidence.get("overall"),
            "reds": red_count_int,
        }
    return {
        "finished_at": finished_at,
        "green": False,
        "status": "missing",
        "summary": "factory_probe check missing from watchdog row",
        "overall": None,
        "reds": 999,
    }


def window_evidence(args: argparse.Namespace, window_start: dt.datetime, now: dt.datetime) -> dict[str, Any]:
    rows = load_jsonl(args.watchdog_log)
    samples = [
        sample
        for row in rows
        if (sample := factory_probe_sample(row))
        and window_start <= sample["finished_at"] <= now
    ]
    bad = [sample for sample in samples if not sample["green"]]
    span_seconds = 0
    if len(samples) >= 2:
        span_seconds = int((samples[-1]["finished_at"] - samples[0]["finished_at"]).total_seconds())
    return {
        "sample_count": len(samples),
        "bad_count": len(bad),
        "span_seconds": span_seconds,
        "first_sample": samples[0]["finished_at"].isoformat() if samples else None,
        "last_sample": samples[-1]["finished_at"].isoformat() if samples else None,
        "bad_samples": [
            {
                "finished_at": sample["finished_at"].isoformat(),
                "status": sample["status"],
                "summary": sample["summary"],
                "overall": sample["overall"],
                "reds": sample["reds"],
            }
            for sample in bad[:10]
        ],
        "ok": len(samples) >= args.min_samples and not bad,
    }


def current_factory_probe(args: argparse.Namespace) -> dict[str, Any]:
    result = run(["bash", "tools/factory_no_drift_probe.sh", "--quiet", "--json"], cwd=args.wiki, timeout=240)
    payload = parse_json_stdout(result)
    ok = bool(result["ok"] and payload and payload.get("overall") == "GREEN" and int(payload.get("reds") or 0) == 0)
    return {"ok": ok, "result": result, "payload": payload}


def current_hermes_canary(args: argparse.Namespace) -> dict[str, Any]:
    result = run([args.python, "tools/hermes_canary_gate.py", "--json", "--factory-probe", "--webui-probe"], cwd=args.wiki, timeout=300)
    payload = parse_json_stdout(result)
    overall = str((payload or {}).get("overall") or (payload or {}).get("status") or "").upper()
    red_count = 0
    if payload and isinstance(payload.get("reds"), int):
        red_count = int(payload["reds"])
    ok = bool(result["ok"] and payload and overall in {"GREEN", "DONE", "OK"} and red_count == 0)
    return {"ok": ok, "result": result, "payload": payload}


def promotion_runner_non_promoting(args: argparse.Namespace) -> dict[str, Any]:
    cmd = [args.python, "tools/hermes_promotion_runner.py", "--wiki", args.wiki, "--json"]
    result = run(cmd, cwd=args.wiki, timeout=300)
    payload = parse_json_stdout(result)
    return {
        "ok": bool(result["ok"] and payload),
        "result": result,
        "payload": payload,
        "promote_flag_present": any(str(part) == "--promote" for part in cmd),
    }


def render_receipt(report: dict[str, Any]) -> str:
    now = report["now"]
    day = now[:10]
    probe_json = json.dumps(report.get("factory_probe", {}).get("payload"), ensure_ascii=False, indent=2, sort_keys=True, default=str)
    canary_json = json.dumps(report.get("hermes_canary", {}).get("payload"), ensure_ascii=False, indent=2, sort_keys=True, default=str)
    runner_json = json.dumps(report.get("promotion_runner", {}).get("payload"), ensure_ascii=False, indent=2, sort_keys=True, default=str)
    return "\n".join(
        [
            "---",
            "type: audit",
            f"id: HERMES-24H-GATE-GREEN-{day}",
            f'title: "Hermes 24h no-drift gate green {day}"',
            f"date: {day}",
            "status: green",
            "tags: [audit, hermes, promotion, canary, 24h-gate, no-drift, no-promote]",
            "---",
            "",
            f"# Hermes 24h no-drift gate green {day}",
            "",
            GREEN_MARKER,
            "",
            "## Verdict",
            "",
            "Hermes has a strict 24h no-drift receipt. This is not a production cutover.",
            "",
            f"- Window start: `{report['window_start']}`",
            f"- Window end: `{report['now']}`",
            f"- Reset artifact: `{report['reset_artifact']}`",
            f"- Watchdog samples: `{report['watchdog']['sample_count']}`",
            f"- Watchdog bad samples: `{report['watchdog']['bad_count']}`",
            f"- Promotion runner rerun without `--promote`: `true`",
            f"- Hermes promoted: `false`",
            "",
            "Explicit approval is required before any command using `--promote` or any Telegram/router cutover.",
            "",
            "## Factory Probe",
            "",
            "```json",
            tail(probe_json, 12000),
            "```",
            "",
            "## Hermes Canary Gate",
            "",
            "```json",
            tail(canary_json, 12000),
            "```",
            "",
            "## Non-Promoting Promotion Runner",
            "",
            "```json",
            tail(runner_json, 12000),
            "```",
            "",
        ]
    ) + "\n"


def render_status(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "---",
            "type: system",
            "id: hermes-24h-gate-verifier-status",
            'title: "Hermes 24h Gate Verifier Status"',
            f"last_updated: {report['now']}",
            f"status: {report['overall_status']}",
            "tags: [hermes, promotion, canary, 24h-gate, launchd]",
            "---",
            "",
            "# Hermes 24h Gate Verifier Status",
            "",
            f"- Overall: `{report['overall_status']}`",
            f"- Reason: {report['reason']}",
            f"- Reset artifact: `{report.get('reset_artifact')}`",
            f"- Candidate end: `{report.get('candidate_end')}`",
            f"- Green receipt: `{report.get('receipt_path')}`",
            f"- Non-promoting runner executed: `{bool(report.get('promotion_runner'))}`",
            "",
        ]
    )


def writeback(args: argparse.Namespace, paths: list[Path]) -> dict[str, Any]:
    if args.dry_run or args.no_writeback or not paths:
        return {"ok": True, "detail": "dry-run, no-writeback, or no paths"}
    rels = [str(path) for path in paths]
    add = run(["git", "-c", "core.hooksPath=/dev/null", "add", "--", *rels], cwd=args.wiki, timeout=90)
    if not add["ok"]:
        return {"ok": False, "detail": tail(add["stdout"] + add["stderr"])}
    diff = run(["git", "diff", "--cached", "--quiet", "--", *rels], cwd=args.wiki, timeout=45)
    committed = False
    if diff["returncode"] == 1:
        commit = run(
            ["git", "-c", "core.hooksPath=/dev/null", "commit", "--no-verify", "-m", f"hermes: verify 24h gate {now_kzt().strftime('%Y-%m-%d %H:%M')}"],
            cwd=args.wiki,
            timeout=120,
        )
        if not commit["ok"]:
            return {"ok": False, "detail": tail(commit["stdout"] + commit["stderr"])}
        committed = True
    elif diff["returncode"] != 0:
        return {"ok": False, "detail": tail(diff["stdout"] + diff["stderr"])}
    run(["git", "pull", "--rebase", "origin", "main"], cwd=args.wiki, timeout=180)
    origin = run(["git", "push", "origin", "main"], cwd=args.wiki, timeout=180)
    github = {"ok": True, "stdout": "", "stderr": "github remote missing"}
    if run(["git", "remote", "get-url", "github"], cwd=args.wiki, timeout=30)["ok"]:
        github = run(["git", "push", "github", "main"], cwd=args.wiki, timeout=180)
    return {
        "ok": origin["ok"] and github["ok"],
        "detail": {
            "committed": committed,
            "origin": tail(origin["stdout"] + origin["stderr"]),
            "github": tail(github["stdout"] + github["stderr"]),
        },
    }


def send_approval_request(args: argparse.Namespace, report: dict[str, Any]) -> dict[str, Any]:
    if args.no_telegram or args.dry_run:
        return {"ok": True, "detail": "telegram disabled"}
    message = (
        "Hermes 24h gate is GREEN and receipt was created. "
        "Promotion runner was rerun without --promote. "
        "Explicit approval is required before Hermes cutover or any --promote command."
    )
    result = run(["bash", "tools/tg_send.sh", message], cwd=args.wiki, timeout=45)
    return {"ok": result["ok"], "detail": tail(result["stdout"] + result["stderr"])}


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    now = parse_dt(args.now) if args.now else now_kzt()
    assert now is not None
    reset = latest_reset_candidate(args.wiki)
    report: dict[str, Any] = {
        "run_id": now.strftime("%Y-%m-%d-%H%M%S"),
        "now": now.isoformat(),
        "overall_status": "pending",
        "reason": "",
        "receipt_path": None,
        "promotion_runner": None,
    }
    if not reset:
        report.update({"overall_status": "blocked", "reason": "no reset artifact with candidate time found"})
        return report
    report.update(
        {
            "reset_artifact": reset["path"],
            "candidate_end": reset["candidate_end"].isoformat(),
            "window_start": reset["window_start"].isoformat(),
        }
    )
    receipts = existing_green_receipts(args.wiki)
    if receipts:
        report.update(
            {
                "overall_status": "done",
                "reason": "green receipt already exists",
                "receipt_path": str(receipts[-1].relative_to(args.wiki)),
            }
        )
        return report
    if now < reset["candidate_end"]:
        report.update({"reason": "candidate window has not elapsed"})
        return report
    watchdog = window_evidence(args, reset["window_start"], now)
    report["watchdog"] = watchdog
    if not watchdog["ok"]:
        report.update({"reason": "watchdog window missing samples or contains red factory probes"})
        return report
    factory = current_factory_probe(args)
    report["factory_probe"] = {k: v for k, v in factory.items() if k != "result"}
    if not factory["ok"]:
        report.update({"overall_status": "blocked", "reason": "current factory_no_drift_probe is not green"})
        return report
    canary = current_hermes_canary(args)
    report["hermes_canary"] = {k: v for k, v in canary.items() if k != "result"}
    if not canary["ok"]:
        report.update({"overall_status": "blocked", "reason": "current hermes_canary_gate is not green"})
        return report
    runner = promotion_runner_non_promoting(args)
    report["promotion_runner"] = {k: v for k, v in runner.items() if k != "result"}
    if runner["promote_flag_present"]:
        report.update({"overall_status": "blocked", "reason": "internal safety violation: promotion runner command included --promote"})
        return report
    if not runner["ok"]:
        report.update({"overall_status": "blocked", "reason": "non-promoting promotion runner failed"})
        return report
    report.update({"overall_status": "done", "reason": "strict 24h factory-green gate verified"})
    return report


def apply_outputs(args: argparse.Namespace, report: dict[str, Any]) -> dict[str, Any]:
    touched: list[Path] = []
    if not args.dry_run:
        args.verifier_log.parent.mkdir(parents=True, exist_ok=True)
        with args.verifier_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, sort_keys=True, default=str) + "\n")
        state_abs = args.wiki / args.state_page
        state_abs.parent.mkdir(parents=True, exist_ok=True)
        state_abs.write_text(render_status(report), encoding="utf-8")
        touched.append(args.state_page)
        if report["overall_status"] == "done" and report["reason"] == "strict 24h factory-green gate verified":
            day = report["now"][:10]
            receipt_rel = Path(f"{GREEN_PREFIX}{day}.md")
            (args.wiki / receipt_rel).write_text(render_receipt(report), encoding="utf-8")
            report["receipt_path"] = str(receipt_rel)
            touched.append(receipt_rel)
            notify = send_approval_request(args, report)
            report["telegram"] = notify
    report["writeback"] = writeback(args, touched)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--watchdog-log", type=Path, default=DEFAULT_WATCHDOG_LOG)
    parser.add_argument("--verifier-log", type=Path, default=DEFAULT_VERIFIER_LOG)
    parser.add_argument("--state-page", type=Path, default=DEFAULT_STATE_PAGE)
    parser.add_argument("--min-samples", type=int, default=DEFAULT_MIN_SAMPLES)
    parser.add_argument("--now", help="test override, ISO datetime")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-writeback", action="store_true")
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = evaluate(args)
    report = apply_outputs(args, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"hermes_24h_gate={report['overall_status']} reason={report['reason']}")
    return 0 if report["overall_status"] in {"done", "pending"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
