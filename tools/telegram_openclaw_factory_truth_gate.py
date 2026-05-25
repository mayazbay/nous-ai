#!/usr/bin/env python3
"""Truth gate for the Telegram/OpenClaw production factory.

This gate exists to stop a recurring false failure mode:

- The production Telegram/OpenClaw path lives in the synced wiki/tools runtime
  and launchd jobs on Air.
- The Air runtime root repo (~/nous-agaas) can be release-dirty from older
  hand-managed files and generated residue.
- A dirty runtime root is hygiene debt, not proof that Telegram/OpenClaw is
  broken.

The gate therefore separates production truth from release hygiene. Any RED in
the live production checks makes the gate RED. A dirty Air runtime root is
reported as YELLOW unless --strict-runtime-root is passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_WIKI = Path(__file__).resolve().parents[1]
AIR_WIKI = Path("/Users/madia/nous-agaas/wiki")
AIR_RUNTIME_ROOT = Path("/Users/madia/nous-agaas")
VPS_WIKI = Path("/root/nous-agaas/wiki")


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    cmd: str


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
            cmd=" ".join(shlex.quote(part) for part in cmd),
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            ok=False,
            returncode=124,
            stdout=exc.stdout or "",
            stderr=exc.stderr or f"timeout after {timeout}s",
            cmd=" ".join(shlex.quote(part) for part in cmd),
        )
    except FileNotFoundError as exc:
        return CommandResult(
            ok=False,
            returncode=127,
            stdout="",
            stderr=f"missing executable: {exc.filename}",
            cmd=" ".join(shlex.quote(part) for part in cmd),
        )


def run_shell(script: str, *, cwd: Path | None = None, timeout: int = 60) -> CommandResult:
    return run(["bash", "-lc", script], cwd=cwd, timeout=timeout)


def ssh(host: str, script: str, *, timeout: int = 60) -> CommandResult:
    if host == "air" and Path.home() == Path("/Users/madia") and AIR_WIKI.exists() and os.uname().nodename:
        # If this script is already running on Air, avoid SSH to self.
        local_probe = run_shell("test -d /Users/madia/nous-agaas/wiki && hostname", timeout=10)
        if local_probe.ok and "air" in local_probe.stdout.lower():
            return run_shell(script, timeout=timeout)
    return run(["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", host, script], timeout=timeout)


def check(name: str, status: str, detail: str, evidence: Any | None = None) -> dict[str, Any]:
    if status not in {"GREEN", "YELLOW", "RED"}:
        raise ValueError(f"invalid status: {status}")
    item: dict[str, Any] = {"check": name, "status": status, "detail": detail}
    if evidence is not None:
        item["evidence"] = evidence
    return item


def summarize_status_lines(status_text: str) -> dict[str, Any]:
    lines = [line for line in status_text.splitlines() if line.strip()]
    tracked = [line for line in lines if not line.startswith("??")]
    untracked = [line for line in lines if line.startswith("??")]
    return {
        "dirty": bool(lines),
        "total": len(lines),
        "tracked": len(tracked),
        "untracked": len(untracked),
        "sample": lines[:12],
    }


def classify_runtime_root_status(status_text: str, *, strict: bool = False) -> dict[str, Any]:
    summary = summarize_status_lines(status_text)
    if not summary["dirty"]:
        return check("air_runtime_root_hygiene", "GREEN", "runtime root clean", summary)
    status = "RED" if strict else "YELLOW"
    return check(
        "air_runtime_root_hygiene",
        status,
        f"release_dirty tracked={summary['tracked']} untracked={summary['untracked']}; not production-red unless strict",
        summary,
    )


def poller_import_order_ok(text: str) -> tuple[bool, str]:
    tools_marker = 'sys.path.insert(0, str(TOOLS_DIR))'
    runtime_marker = 'sys.path.insert(1, str(RUNTIME_ROOT))'
    alias_marker = 'command_center_path = TOOLS_DIR / "command_center.py"'

    tools_idx = text.find(tools_marker)
    runtime_idx = text.find(runtime_marker)
    alias_idx = text.find(alias_marker)
    if tools_idx < 0:
        return False, "missing tools sys.path insertion"
    if runtime_idx < 0:
        return False, "missing runtime-root sys.path insertion"
    if tools_idx > runtime_idx:
        return False, "runtime root precedes tracked tools directory"
    if alias_idx < 0:
        return False, "missing explicit tools command_center alias import"
    return True, "tools router precedes runtime root and alias import is present"


def parse_hash_lines(output: str) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for line in output.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        digest, path = parts
        hashes[path] = digest
    return hashes


def command_center_hashes_equal(output: str, expected_count: int = 3) -> tuple[bool, str, dict[str, str]]:
    hashes = parse_hash_lines(output)
    if len(hashes) != expected_count:
        return False, f"expected {expected_count} hashes, got {len(hashes)}", hashes
    unique = set(hashes.values())
    if len(unique) != 1:
        return False, f"command_center hash drift across {len(unique)} versions", hashes
    return True, "runtime root/tools/wiki command_center hashes match", hashes


def overall_from(checks: list[dict[str, Any]]) -> dict[str, Any]:
    reds = [item for item in checks if item["status"] == "RED"]
    yellows = [item for item in checks if item["status"] == "YELLOW"]
    return {
        "overall": "GREEN" if not reds else "RED",
        "reds": len(reds),
        "yellows": len(yellows),
        "checks": checks,
    }


def git_head(cwd: Path) -> str:
    result = run(["git", "rev-parse", "HEAD"], cwd=cwd, timeout=20)
    return result.stdout.strip() if result.ok else f"ERROR:{result.stderr.strip() or result.returncode}"


def git_status(cwd: Path) -> str:
    result = run(["git", "status", "--porcelain"], cwd=cwd, timeout=20)
    return result.stdout if result.ok else f"ERROR:{result.stderr.strip() or result.returncode}"


def local_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _head_or_error(result: CommandResult) -> str:
    if result.ok and result.stdout.strip():
        return result.stdout.split()[0]
    return f"ERROR:{result.stderr.strip() or result.returncode}"


def remote_head(wiki: Path, remote: str, ref: str = "refs/heads/main") -> str:
    result = run(["git", "ls-remote", remote, ref], cwd=wiki, timeout=30)
    return _head_or_error(result)


def vps_bare_head() -> str:
    result = ssh(
        "root@65.108.215.200",
        "git --git-dir=/root/nous-agaas/obsidian-wiki.git rev-parse refs/heads/main",
        timeout=30,
    )
    return _head_or_error(result)


def check_wiki_head_parity(wiki: Path) -> dict[str, Any]:
    local = git_head(wiki)
    air = ssh("air", "cd ~/nous-agaas/wiki && git rev-parse HEAD", timeout=30)
    vps_w = ssh("root@65.108.215.200", "cd /root/nous-agaas/wiki && git rev-parse HEAD", timeout=30)
    heads = {
        "local": local,
        "air": air.stdout.strip() if air.ok else f"ERROR:{air.stderr.strip() or air.returncode}",
        "vps_working": vps_w.stdout.strip() if vps_w.ok else f"ERROR:{vps_w.stderr.strip() or vps_w.returncode}",
        "vps_bare": vps_bare_head(),
        "github": remote_head(wiki, "github"),
    }
    unique = set(heads.values())
    ok = len(unique) == 1 and not next(iter(unique), "").startswith("ERROR:")
    short = {key: value[:8] for key, value in heads.items()}
    return check("wiki_head_parity", "GREEN" if ok else "RED", f"heads={short}", heads)


def check_wiki_worktrees_clean(wiki: Path) -> dict[str, Any]:
    local = git_status(wiki)
    air = ssh("air", "cd ~/nous-agaas/wiki && git status --porcelain", timeout=30)
    vps = ssh("root@65.108.215.200", "cd /root/nous-agaas/wiki && git status --porcelain", timeout=30)
    statuses = {
        "local": summarize_status_lines(local),
        "air": summarize_status_lines(air.stdout if air.ok else f"ERROR:{air.stderr.strip() or air.returncode}"),
        "vps": summarize_status_lines(vps.stdout if vps.ok else f"ERROR:{vps.stderr.strip() or vps.returncode}"),
    }
    ok = all(not value["dirty"] for value in statuses.values())
    return check("wiki_worktrees_clean", "GREEN" if ok else "RED", f"dirty_hosts={[k for k, v in statuses.items() if v['dirty']]}", statuses)


def check_air_command_center_parity() -> dict[str, Any]:
    script = r"""
for p in \
  /Users/madia/nous-agaas/command_center.py \
  /Users/madia/nous-agaas/tools/command_center.py \
  /Users/madia/nous-agaas/wiki/tools/command_center.py
do
  if [ ! -f "$p" ]; then
    echo "MISSING $p"
  else
    python3 - "$p" <<'PY'
import hashlib
import sys
path = sys.argv[1]
h = hashlib.sha256()
with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1024 * 1024), b""):
        h.update(chunk)
print(h.hexdigest(), path)
PY
  fi
done
"""
    result = ssh("air", script, timeout=45)
    if not result.ok:
        return check("air_command_center_parity", "RED", result.stderr.strip() or "ssh/hash failed", {"returncode": result.returncode})
    ok, detail, hashes = command_center_hashes_equal(result.stdout)
    return check("air_command_center_parity", "GREEN" if ok else "RED", detail, hashes)


def check_air_launchd_path() -> dict[str, Any]:
    script = r"""
python3 - <<'PY'
import json
import plistlib
from pathlib import Path
p = Path.home() / "Library/LaunchAgents/com.nous.telegram-poll.plist"
if not p.exists():
    print(json.dumps({"error": f"missing {p}"}))
else:
    data = plistlib.loads(p.read_bytes())
    print(json.dumps({
        "program_arguments": data.get("ProgramArguments", []),
        "working_directory": data.get("WorkingDirectory", ""),
        "keep_alive": data.get("KeepAlive", None),
    }))
PY
"""
    result = ssh("air", script, timeout=30)
    if not result.ok:
        return check("air_telegram_poller_launchd_path", "RED", result.stderr.strip() or "ssh/plist read failed")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return check("air_telegram_poller_launchd_path", "RED", "plist JSON decode failed", result.stdout)
    args = " ".join(str(item) for item in payload.get("program_arguments", []))
    workdir = str(payload.get("working_directory", ""))
    ok = "/Users/madia/nous-agaas/tools/telegram_poll.py" in args and workdir == "/Users/madia/nous-agaas"
    detail = f"workdir={workdir}; args_include_tools_poller={ '/Users/madia/nous-agaas/tools/telegram_poll.py' in args }"
    return check("air_telegram_poller_launchd_path", "GREEN" if ok else "RED", detail, payload)


def check_air_poller_import_order() -> dict[str, Any]:
    result = ssh("air", "cat /Users/madia/nous-agaas/tools/telegram_poll.py", timeout=30)
    if not result.ok:
        return check("air_telegram_poller_import_order", "RED", result.stderr.strip() or "ssh/cat failed")
    ok, detail = poller_import_order_ok(result.stdout)
    return check("air_telegram_poller_import_order", "GREEN" if ok else "RED", detail)


def check_factory_probe() -> dict[str, Any]:
    result = ssh(
        "air",
        "cd ~/nous-agaas/wiki && bash tools/factory_no_drift_probe.sh --quiet --json --no-telegram",
        timeout=240,
    )
    raw = result.stdout.strip() or result.stderr.strip()
    if not result.ok:
        return check("factory_no_drift_probe", "RED", raw[-1000:] or f"rc={result.returncode}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return check("factory_no_drift_probe", "RED", "probe did not return JSON", raw[-1000:])
    ok = payload.get("overall") == "GREEN" and int(payload.get("reds") or 0) == 0
    return check(
        "factory_no_drift_probe",
        "GREEN" if ok else "RED",
        f"overall={payload.get('overall')} reds={payload.get('reds')}",
        {"overall": payload.get("overall"), "reds": payload.get("reds")},
    )


def check_air_runtime_root_hygiene(strict: bool = False) -> dict[str, Any]:
    result = ssh("air", "cd ~/nous-agaas && git status --porcelain", timeout=30)
    if not result.ok:
        return check("air_runtime_root_hygiene", "RED", result.stderr.strip() or "ssh/status failed")
    return classify_runtime_root_status(result.stdout, strict=strict)


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    checks = [
        check_wiki_head_parity(args.wiki),
        check_wiki_worktrees_clean(args.wiki),
        check_air_command_center_parity(),
        check_air_launchd_path(),
        check_air_poller_import_order(),
    ]
    if not args.skip_factory_probe:
        checks.append(check_factory_probe())
    checks.append(check_air_runtime_root_hygiene(strict=args.strict_runtime_root))
    return overall_from(checks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--skip-factory-probe", action="store_true")
    parser.add_argument("--strict-runtime-root", action="store_true")
    args = parser.parse_args(argv)
    result = evaluate(args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"telegram_openclaw_factory_truth={result['overall']} reds={result['reds']} yellows={result['yellows']}")
        for item in result["checks"]:
            print(f"{item['status']} {item['check']}: {item['detail']}")
    return 0 if result["overall"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
