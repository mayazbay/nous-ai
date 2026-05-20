"""Tests for Day-0 citation verifier primitives."""

from __future__ import annotations

import json
import pathlib
import ssl
import subprocess
import sys
import urllib.error


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import citation_verifier


class _Response:
    def __init__(self, status: int):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_verify_url_returns_200_bucket(monkeypatch):
    monkeypatch.setattr(citation_verifier.urllib.request, "urlopen", lambda *_args, **_kw: _Response(200))

    assert citation_verifier.verify_url("https://example.com") == "200"


def test_verify_url_buckets_http_errors(monkeypatch):
    def fail_404(*_args, **_kw):
        raise urllib.error.HTTPError("https://example.com/missing", 404, "missing", {}, None)

    monkeypatch.setattr(citation_verifier.urllib.request, "urlopen", fail_404)

    assert citation_verifier.verify_url("https://example.com/missing") == "4xx"

    def fail_503(*_args, **_kw):
        raise urllib.error.HTTPError("https://example.com/down", 503, "down", {}, None)

    monkeypatch.setattr(citation_verifier.urllib.request, "urlopen", fail_503)

    assert citation_verifier.verify_url("https://example.com/down") == "5xx"


def test_verify_url_retries_with_certifi_on_local_ca_failure(monkeypatch):
    calls = []

    def open_url(*_args, **kwargs):
        calls.append(kwargs)
        if "context" not in kwargs:
            raise urllib.error.URLError(ssl.SSLCertVerificationError("bad local ca"))
        return _Response(200)

    monkeypatch.setattr(citation_verifier.urllib.request, "urlopen", open_url)

    assert citation_verifier.verify_url("https://example.com") == "200"
    assert len(calls) == 2


def test_verify_url_rejects_invalid_url():
    assert citation_verifier.verify_url("not-a-url") == "invalid"


def test_verify_file_line_checks_file_existence_and_line_range():
    assert citation_verifier.verify_file_line("tools/citation_verifier.py:1", root=REPO_ROOT) is True
    assert citation_verifier.verify_file_line("tools/citation_verifier.py:999999", root=REPO_ROOT) is False
    assert citation_verifier.verify_file_line("tools/citation_verifier.py:not-a-line", root=REPO_ROOT) is False
    assert citation_verifier.verify_file_line("no-colon", root=REPO_ROOT) is False


def test_verify_gbrain_slug_uses_real_substrate_slug():
    assert citation_verifier.verify_gbrain_slug("pages/skills/infrastructure/skill", timeout_s=20) is True


def test_cli_outputs_json_for_file_ref():
    result = subprocess.run(
        [sys.executable, str(TOOLS / "citation_verifier.py"), "file", "tools/citation_verifier.py:1", "--root", str(REPO_ROOT)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "kind": "file",
        "result": True,
        "target": "tools/citation_verifier.py:1",
    }
