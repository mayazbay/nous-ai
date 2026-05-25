#!/usr/bin/env python3
"""Verify user-facing HTTP(S) links before presenting them as working."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable


URL_RE = re.compile(r"https?://[^\s<>'\")\]]+")
TRAILING = ".,;:!?"


@dataclass
class LinkResult:
    url: str
    ok: bool
    method: str | None
    status: int | None
    reason: str


def redact_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    if parsed.username or parsed.password:
        netloc = f"***@{netloc}"
    query = "?..." if parsed.query else ""
    return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, query, ""))


def extract_urls(text: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for match in URL_RE.finditer(text):
        url = match.group(0).rstrip(TRAILING)
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def request_url(url: str, method: str, timeout: float) -> tuple[bool, int | None, str]:
    if shutil.which("curl"):
        cmd = [
            "curl",
            "--location",
            "--silent",
            "--show-error",
            "--max-time",
            str(timeout),
            "--output",
            "/dev/null",
            "--write-out",
            "%{http_code}",
            "--user-agent",
            "nous-link-verifier/1.0",
        ]
        if method == "HEAD":
            cmd.append("--head")
        cmd.append(url)
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
        raw_status = proc.stdout.strip()[-3:]
        status = int(raw_status) if raw_status.isdigit() else None
        if proc.returncode == 0 and status is not None:
            return 200 <= status < 400, status, f"HTTP {status}"
        reason = proc.stderr.strip() or f"curl exit {proc.returncode}"
        if status and status != 0:
            reason = f"HTTP {status}: {reason}"
        return False, status if status != 0 else None, reason

    req = urllib.request.Request(
        url,
        method=method,
        headers={"User-Agent": "nous-link-verifier/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = int(resp.getcode())
            return 200 <= status < 400, status, f"HTTP {status}"
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        return 200 <= status < 400, status, f"HTTP {status}"
    except Exception as exc:  # network/protocol failures must be surfaced, not hidden
        return False, None, f"{type(exc).__name__}: {exc}"


def verify_url(url: str, timeout: float) -> LinkResult:
    ok, status, reason = request_url(url, "HEAD", timeout)
    if ok:
        return LinkResult(redact_url(url), True, "HEAD", status, reason)

    if status in {400, 403, 405, 501} or status is None:
        get_ok, get_status, get_reason = request_url(url, "GET", timeout)
        if get_ok:
            return LinkResult(redact_url(url), True, "GET", get_status, get_reason)
        return LinkResult(redact_url(url), False, "GET", get_status, get_reason)

    return LinkResult(redact_url(url), False, "HEAD", status, reason)


def read_inputs(paths: Iterable[str]) -> str:
    path_list = list(paths)
    if not path_list or path_list == ["-"]:
        return sys.stdin.read()
    chunks: list[str] = []
    for path in path_list:
        with open(path, "r", encoding="utf-8") as handle:
            chunks.append(handle.read())
    return "\n".join(chunks)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract HTTP(S) URLs from text and verify each one is reachable."
    )
    parser.add_argument("paths", nargs="*", help="Text files to scan; defaults to stdin.")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout in seconds.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = read_inputs(args.paths)
    urls = extract_urls(text)
    results = [verify_url(url, args.timeout) for url in urls]
    failed = [result for result in results if not result.ok]

    payload = {
        "checked": len(results),
        "failed": len(failed),
        "results": [result.__dict__ for result in results],
    }

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if not results:
            print("NO_LINKS")
        for result in results:
            state = "OK" if result.ok else "FAIL"
            status = result.status if result.status is not None else "-"
            method = result.method or "-"
            print(f"{state} {method} {status} {result.url} :: {result.reason}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
