#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOL="$ROOT/tools/verify_user_facing_links.py"

python3 - "$TOOL" <<'PY'
import http.server
import json
import socket
import subprocess
import sys
import threading

tool = sys.argv[1]


class Handler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_args):
        pass


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()

with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    dead_port = sock.getsockname()[1]

good_url = f"http://127.0.0.1:{server.server_port}/health?token=secret-value"
bad_url = f"http://127.0.0.1:{dead_port}/missing"

try:
    ok = subprocess.run(
        [sys.executable, tool, "--json"],
        input=f"Try {good_url}\n",
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert ok.returncode == 0, ok.stderr + ok.stdout
    ok_payload = json.loads(ok.stdout)
    assert ok_payload["checked"] == 1, ok.stdout
    assert ok_payload["failed"] == 0, ok.stdout
    assert ok_payload["results"][0]["ok"] is True, ok.stdout
    assert "secret-value" not in ok.stdout, ok.stdout
    assert "?..." in ok_payload["results"][0]["url"], ok.stdout

    bad = subprocess.run(
        [sys.executable, tool, "--json"],
        input=f"Broken {bad_url}\n",
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert bad.returncode == 1, bad.stderr + bad.stdout
    bad_payload = json.loads(bad.stdout)
    assert bad_payload["checked"] == 1, bad.stdout
    assert bad_payload["failed"] == 1, bad.stdout
    assert bad_payload["results"][0]["ok"] is False, bad.stdout

    none = subprocess.run(
        [sys.executable, tool],
        input="No public link here.\n",
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert none.returncode == 0, none.stderr + none.stdout
    assert "NO_LINKS" in none.stdout, none.stdout
finally:
    server.shutdown()

print("OK: user-facing link verifier distinguishes reachable, unreachable, and no-link text")
PY
