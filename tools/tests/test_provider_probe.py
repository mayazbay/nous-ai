"""Tests for tools/provider_probe.py — Ship 1 Step 6."""
from __future__ import annotations

import socket
import sys
from pathlib import Path
from urllib import error

import pytest

# Make tools/ importable when running pytest from the repo root.
TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import provider_probe  # noqa: E402
from provider_probe import (  # noqa: E402
    ProbeResult,
    await_provider_or_backoff,
    probe,
)


# ---------------------------------------------------------------------------
# probe() — input validation & auth gating
# ---------------------------------------------------------------------------

def test_probe_unknown_provider():
    result = probe("does-not-exist")
    assert result.ok is False
    assert result.reason.startswith("unknown_provider")
    assert result.provider == "does-not-exist"


def test_probe_missing_auth_for_anthropic(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = probe("anthropic")
    assert result.ok is False
    assert result.reason == "auth_missing"


def test_probe_missing_auth_for_openai(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = probe("openai")
    assert result.ok is False
    assert result.reason == "auth_missing"


def test_probe_missing_auth_for_xai(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    result = probe("xai")
    assert result.ok is False
    assert result.reason == "auth_missing"


def test_probe_missing_auth_for_deepseek(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    result = probe("deepseek")
    assert result.ok is False
    assert result.reason == "auth_missing"


# ---------------------------------------------------------------------------
# probe() — network behavior (urlopen monkeypatched)
# ---------------------------------------------------------------------------

def test_probe_timeout_returns_timeout_reason(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-tests")

    def fake_urlopen(*args, **kwargs):
        raise socket.timeout()

    monkeypatch.setattr(provider_probe.request, "urlopen", fake_urlopen)
    result = probe("anthropic")
    assert result.ok is False
    assert result.reason == "timeout"


def test_probe_http_500_returns_http_reason(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-tests")

    def fake_urlopen(*args, **kwargs):
        raise error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(provider_probe.request, "urlopen", fake_urlopen)
    result = probe("openai")
    assert result.ok is False
    assert result.reason == "http_500"


class _FakeResponse:
    """Minimal stand-in for the object returned by urllib.request.urlopen."""

    def __init__(self, status: int = 200):
        self.status = status

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_probe_2xx_success_returns_ok(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "fake-key-for-tests")

    def fake_urlopen(*args, **kwargs):
        return _FakeResponse(status=200)

    monkeypatch.setattr(provider_probe.request, "urlopen", fake_urlopen)
    result = probe("xai")
    assert result.ok is True
    assert result.reason == "ok"
    assert result.latency_ms >= 0
    assert result.provider == "xai"


# ---------------------------------------------------------------------------
# await_provider_or_backoff() — retry orchestration with injected sleep
# ---------------------------------------------------------------------------

def test_await_provider_short_circuits_on_first_success(monkeypatch):
    sleeps: list[float] = []

    def fake_probe(provider, *, timeout_sec=provider_probe.DEFAULT_TIMEOUT_SEC):
        return ProbeResult(provider=provider, ok=True, latency_ms=5, reason="ok")

    monkeypatch.setattr(provider_probe, "probe", fake_probe)
    result = await_provider_or_backoff(
        "anthropic", sleep_fn=lambda s: sleeps.append(s)
    )
    assert result.ok is True
    assert sleeps == [], "no backoff sleeps should fire on first-try success"


def test_await_provider_uses_full_backoff_schedule_on_persistent_failure(monkeypatch):
    sleeps: list[float] = []

    def fake_probe(provider, *, timeout_sec=provider_probe.DEFAULT_TIMEOUT_SEC):
        return ProbeResult(
            provider=provider, ok=False, latency_ms=0, reason="timeout"
        )

    monkeypatch.setattr(provider_probe, "probe", fake_probe)
    result = await_provider_or_backoff(
        "openai", sleep_fn=lambda s: sleeps.append(s)
    )
    assert result.ok is False
    # default schedule: 2, 4, 8, 16
    assert sleeps == [2, 4, 8, 16]


def test_await_provider_returns_first_success_after_n_failures(monkeypatch):
    sleeps: list[float] = []
    outcomes = iter([
        ProbeResult(provider="xai", ok=False, latency_ms=0, reason="timeout"),
        ProbeResult(provider="xai", ok=False, latency_ms=0, reason="timeout"),
        ProbeResult(provider="xai", ok=True, latency_ms=12, reason="ok"),
    ])

    def fake_probe(provider, *, timeout_sec=provider_probe.DEFAULT_TIMEOUT_SEC):
        return next(outcomes)

    monkeypatch.setattr(provider_probe, "probe", fake_probe)
    result = await_provider_or_backoff(
        "xai", sleep_fn=lambda s: sleeps.append(s)
    )
    assert result.ok is True
    assert result.reason == "ok"
    # Slept between try #1 and #2 (2s), and between #2 and #3 (4s). Then ok.
    assert sleeps == [2, 4]


# ---------------------------------------------------------------------------
# Module surface
# ---------------------------------------------------------------------------

def test_all_four_providers_have_endpoint_defined():
    endpoints = provider_probe._PROVIDER_ENDPOINTS
    assert isinstance(endpoints, dict)
    for name in ("anthropic", "openai", "xai", "deepseek"):
        assert name in endpoints, f"missing endpoint config for {name}"
        cfg = endpoints[name]
        assert "url" in cfg
        assert "env" in cfg
        assert "method" in cfg
