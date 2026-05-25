#!/usr/bin/env python3
"""Probe QMD at the layers that often get conflated.

The native Codex MCP tool can report ``Transport closed`` even when QMD's
index, stdio server, and HTTP server are healthy. This doctor separates those
layers so an operator can classify the incident without guessing from chat or
Todoist state.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import selectors
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any


DEFAULT_VPS_HOST = "root@65.108.215.200"
DEFAULT_WIKI_DIR = "/root/nous-agaas/wiki"
DEFAULT_HTTP_URL = "http://[::1]:37373/mcp"


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float


def run_command(cmd: list[str], timeout: int) -> CommandResult:
    start = time.monotonic()
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return CommandResult(
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            elapsed_seconds=round(time.monotonic() - start, 3),
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            returncode=124,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + f"\ntimeout after {timeout}s",
            elapsed_seconds=round(time.monotonic() - start, 3),
        )


def parse_qmd_status(text: str) -> dict[str, int | None]:
    total_match = re.search(r"Total:\s+(\d+)\s+files indexed", text)
    vector_match = re.search(r"Vectors:\s+(\d+)\s+embedded", text)
    return {
        "documents": int(total_match.group(1)) if total_match else None,
        "vectors": int(vector_match.group(1)) if vector_match else None,
    }


def summarize_check(ok: bool, **extra: Any) -> dict[str, Any]:
    return {"ok": ok, **extra}


def check_codex_config(timeout: int) -> dict[str, Any]:
    result = run_command(["codex", "mcp", "get", "nous-wiki-qmd"], timeout=timeout)
    ok = result.returncode == 0 and "command: ssh" in result.stdout and "qmd mcp" in result.stdout
    return summarize_check(
        ok,
        returncode=result.returncode,
        elapsed_seconds=result.elapsed_seconds,
        transport="stdio" if "transport: stdio" in result.stdout else None,
        command_seen="qmd mcp" in result.stdout,
        stderr=result.stderr.strip()[:500],
    )


def check_qmd_cli(vps_host: str, wiki_dir: str, timeout: int) -> dict[str, Any]:
    script = f"cd {shell_quote(wiki_dir)} && qmd status"
    result = run_command(["ssh", vps_host, script], timeout=timeout)
    counts = parse_qmd_status(result.stdout)
    ok = result.returncode == 0 and bool(counts["documents"]) and bool(counts["vectors"])
    return summarize_check(
        ok,
        returncode=result.returncode,
        elapsed_seconds=result.elapsed_seconds,
        **counts,
        stderr=result.stderr.strip()[:500],
    )


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def read_json_line(proc: subprocess.Popen[str], timeout: int) -> dict[str, Any]:
    assert proc.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    events = selector.select(timeout)
    if not events:
        raise TimeoutError(f"no JSON-RPC line within {timeout}s")
    line = proc.stdout.readline()
    if not line:
        raise EOFError("server closed stdout before JSON-RPC response")
    return json.loads(line)


def check_qmd_stdio(vps_host: str, timeout: int) -> dict[str, Any]:
    cmd = ["ssh", "-T", vps_host, "qmd", "mcp"]
    start = time.monotonic()
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        assert proc.stdin is not None
        init = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "qmd-mcp-doctor", "version": "1"},
            },
        }
        proc.stdin.write(json.dumps(init) + "\n")
        proc.stdin.flush()
        init_response = read_json_line(proc, timeout)
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n")
        call = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "status", "arguments": {}}}
        proc.stdin.write(json.dumps(call) + "\n")
        proc.stdin.flush()
        status_response = read_json_line(proc, timeout)
        server_info = init_response.get("result", {}).get("serverInfo", {})
        text = extract_mcp_text(status_response)
        ok = (
            init_response.get("result", {}).get("protocolVersion") is not None
            and server_info.get("name") == "qmd"
            and "QMD Index Status" in text
        )
        return summarize_check(
            ok,
            elapsed_seconds=round(time.monotonic() - start, 3),
            server=server_info,
            status_text_first_line=text.splitlines()[0] if text else "",
        )
    except Exception as exc:  # noqa: BLE001 - doctor must report exact failure class.
        stderr = ""
        if proc.stderr is not None:
            try:
                stderr = proc.stderr.read(500)
            except Exception:
                stderr = ""
        return summarize_check(False, elapsed_seconds=round(time.monotonic() - start, 3), error=repr(exc), stderr=stderr)
    finally:
        proc.kill()
        proc.wait(timeout=5)


def extract_mcp_text(response: dict[str, Any]) -> str:
    content = response.get("result", {}).get("content", [])
    parts = [item.get("text", "") for item in content if isinstance(item, dict)]
    return "\n".join(part for part in parts if part)


def check_qmd_http(vps_host: str, http_url: str, timeout: int) -> dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "qmd-mcp-doctor", "version": "1"},
        },
    }
    curl = (
        "curl -g -sS -m "
        + shell_quote(str(timeout))
        + " -X POST "
        + shell_quote(http_url)
        + " -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' --data-binary "
        + shell_quote(json.dumps(payload))
    )
    result = run_command(["ssh", vps_host, curl], timeout=timeout + 5)
    server_name = None
    try:
        body = json.loads(result.stdout)
        server_name = body.get("result", {}).get("serverInfo", {}).get("name")
    except json.JSONDecodeError:
        body = None
    ok = result.returncode == 0 and server_name == "qmd"
    return summarize_check(
        ok,
        returncode=result.returncode,
        elapsed_seconds=result.elapsed_seconds,
        server_name=server_name,
        stderr=result.stderr.strip()[:500],
        body_present=body is not None,
    )


def classify(checks: dict[str, Any]) -> str:
    if not checks["qmd_cli"]["ok"]:
        return "red:qmd_cli_or_index"
    if not checks["qmd_stdio"]["ok"]:
        return "red:qmd_stdio_server"
    if not checks["qmd_http"]["ok"]:
        return "yellow:qmd_http_server"
    if not checks["codex_config"]["ok"]:
        return "yellow:codex_config_missing_underlying_qmd_healthy"
    return "green:underlying_qmd_healthy_native_codex_tool_must_be_checked_in_session"


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify QMD MCP/index health without relying on Codex tool state.")
    parser.add_argument("--vps-host", default=os.getenv("VPS_HOST", DEFAULT_VPS_HOST))
    parser.add_argument("--wiki-dir", default=os.getenv("QMD_WIKI_DIR", DEFAULT_WIKI_DIR))
    parser.add_argument("--http-url", default=os.getenv("QMD_HTTP_URL", DEFAULT_HTTP_URL))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("QMD_DOCTOR_TIMEOUT", "15")))
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON only.")
    args = parser.parse_args()

    checks = {
        "codex_config": check_codex_config(args.timeout),
        "qmd_cli": check_qmd_cli(args.vps_host, args.wiki_dir, args.timeout),
        "qmd_stdio": check_qmd_stdio(args.vps_host, args.timeout),
        "qmd_http": check_qmd_http(args.vps_host, args.http_url, args.timeout),
    }
    result = {
        "tool": "qmd_mcp_doctor",
        "version": "1.0.0",
        "classification": classify(checks),
        "checks": checks,
        "native_codex_tool_note": (
            "If mcp__nous_wiki_qmd__.status returns Transport closed while this doctor is green, "
            "the residual is Codex native/deferred MCP transport, not QMD data/index/server health."
        ),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(f"[qmd_mcp_doctor v{result['version']}] {result['classification']}")
        for name, payload in checks.items():
            print(f"  {name}: {'OK' if payload['ok'] else 'FAIL'} ({payload.get('elapsed_seconds')}s)")
        print(result["native_codex_tool_note"])
    return 0 if result["classification"].startswith("green") else 1


if __name__ == "__main__":
    raise SystemExit(main())
