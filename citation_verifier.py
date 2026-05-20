#!/usr/bin/env python3
"""Day-0 citation verifier stubs.

Checks URL status buckets, gbrain slug existence, and local file:line refs.
Snippet/content matching is intentionally left for Day 1+.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_GBRAIN_SSH = "root@65.108.215.200"
DEFAULT_GBRAIN_DIR = "/opt/nous-agaas/gbrain"


def verify_url(url: str, timeout_s: float = 10) -> str:
    """Return a coarse status bucket for a URL using HEAD."""

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "invalid"
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return _status_bucket(int(response.status))
    except urllib.error.HTTPError as exc:
        return _status_bucket(int(exc.code))
    except urllib.error.URLError as exc:
        if _is_ssl_cert_error(exc):
            retry = _retry_with_certifi(request, timeout_s)
            if retry:
                return retry
        return "error"
    except (TimeoutError, OSError):
        return "error"


def verify_gbrain_slug(slug: str, timeout_s: float = 20) -> bool:
    """Return True if the VPS gbrain CLI can read the slug."""

    if not slug or any(ch.isspace() for ch in slug):
        return False
    ssh_target = os.environ.get("GBRAIN_SSH", DEFAULT_GBRAIN_SSH)
    gbrain_dir = os.environ.get("GBRAIN_DIR", DEFAULT_GBRAIN_DIR)
    remote = f"cd {shlex.quote(gbrain_dir)} && ./bin/gbrain get {shlex.quote(slug)} >/dev/null"
    result = subprocess.run(
        ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", ssh_target, remote],
        text=True,
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )
    return result.returncode == 0


def verify_file_line(ref: str, *, root: str | Path = ".") -> bool:
    """Return True if `path:line` exists and line is within file bounds."""

    path_text, line_text = _split_file_line(ref)
    if not path_text or not line_text:
        return False
    try:
        line_no = int(line_text)
    except ValueError:
        return False
    if line_no < 1:
        return False
    path = Path(path_text)
    if not path.is_absolute():
        path = Path(root) / path
    if not path.is_file():
        return False
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for count, _line in enumerate(fh, start=1):
            if count >= line_no:
                return True
    return False


def _status_bucket(code: int) -> str:
    if code == 200:
        return "200"
    if 400 <= code < 500:
        return "4xx"
    if 500 <= code < 600:
        return "5xx"
    if 200 <= code < 300:
        return "2xx"
    if 300 <= code < 400:
        return "3xx"
    return str(code)


def _is_ssl_cert_error(exc: urllib.error.URLError) -> bool:
    return isinstance(getattr(exc, "reason", None), ssl.SSLCertVerificationError)


def _retry_with_certifi(request: urllib.request.Request, timeout_s: float) -> str | None:
    try:
        import certifi  # type: ignore[import-not-found]
    except ImportError:
        return None
    context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(request, timeout=timeout_s, context=context) as response:
            return _status_bucket(int(response.status))
    except urllib.error.HTTPError as exc:
        return _status_bucket(int(exc.code))
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def _split_file_line(ref: str) -> tuple[str, str]:
    if ":" not in ref:
        return "", ""
    path, line = ref.rsplit(":", 1)
    return path, line


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify URL, gbrain slug, or file:line citations.")
    sub = ap.add_subparsers(dest="kind", required=True)
    p_url = sub.add_parser("url")
    p_url.add_argument("url")
    p_slug = sub.add_parser("gbrain")
    p_slug.add_argument("slug")
    p_file = sub.add_parser("file")
    p_file.add_argument("ref")
    p_file.add_argument("--root", default=".")
    args = ap.parse_args(argv)

    if args.kind == "url":
        result: str | bool = verify_url(args.url)
    elif args.kind == "gbrain":
        result = verify_gbrain_slug(args.slug)
        target = args.slug
    else:
        result = verify_file_line(args.ref, root=args.root)
        target = args.ref
    if args.kind == "url":
        target = args.url
    print(json.dumps({"kind": args.kind, "target": target, "result": result}, sort_keys=True))
    return 0 if result not in {False, "invalid", "error", "4xx", "5xx"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
