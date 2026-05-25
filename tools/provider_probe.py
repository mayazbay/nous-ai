"""Cheap 'is this provider alive?' probe with exponential backoff.

Used by command_center failover logic (Ship 1 Step 8) to decide whether
to flip back from a fallback model to the primary. Stdlib-only — no
`requests`, no `httpx` — so it stays callable from any subprocess context
without dependency surface.

API:
    probe(provider) -> ProbeResult                  # one cheap shot
    await_provider_or_backoff(provider, ...) -> ProbeResult   # 2/4/8/16s

Plan: §4.7.
"""
from __future__ import annotations

import dataclasses
import json
import os
import socket
import sys
import time
from typing import Callable
from urllib import error, request

DEFAULT_TIMEOUT_SEC = 0.2  # 200ms — we just want a liveness signal, not work.
DEFAULT_BACKOFF_SCHEDULE = (2, 4, 8, 16)  # seconds between retries


# ---------------------------------------------------------------------------
# Provider endpoint map. Exposed at module scope so tests can introspect it
# without importing private internals.
# ---------------------------------------------------------------------------
_PROVIDER_ENDPOINTS: dict[str, dict] = {
    "anthropic": {
        "method": "POST",
        "url": "https://api.anthropic.com/v1/messages",
        "env": "ANTHROPIC_API_KEY",
        "model": "claude-haiku-4-5-20251001",
    },
    "openai": {
        "method": "POST",
        "url": "https://api.openai.com/v1/chat/completions",
        "env": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
    },
    "xai": {
        "method": "POST",
        "url": "https://api.x.ai/v1/chat/completions",
        "env": "XAI_API_KEY",
        "model": "grok-2-1212",
    },
    "deepseek": {
        "method": "GET",
        "url": "https://api.deepseek.com/v1/models",
        "env": "DEEPSEEK_API_KEY",
        "model": None,
    },
}


@dataclasses.dataclass(frozen=True)
class ProbeResult:
    provider: str
    ok: bool
    latency_ms: int
    reason: str  # "ok" on success; failure tag otherwise

    def as_dict(self) -> dict:
        return {
            "provider": self.provider,
            "ok": self.ok,
            "latency_ms": self.latency_ms,
            "reason": self.reason,
        }


def _build_request(provider: str, cfg: dict, api_key: str) -> request.Request:
    """Construct a urllib Request for the given provider config."""
    url = cfg["url"]
    method = cfg["method"]
    headers: dict[str, str] = {"content-type": "application/json"}

    if provider == "anthropic":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers["Authorization"] = f"Bearer {api_key}"

    body: bytes | None = None
    if method == "POST":
        payload = {
            "model": cfg["model"],
            "messages": [{"role": "user", "content": "."}],
            "max_tokens": 1,
        }
        body = json.dumps(payload).encode("utf-8")

    return request.Request(url, data=body, headers=headers, method=method)


def probe(provider: str, *, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> ProbeResult:
    """Run one cheap probe for the named provider.

    See module docstring for the contract.
    """
    key = provider.lower()
    cfg = _PROVIDER_ENDPOINTS.get(key)
    if cfg is None:
        return ProbeResult(
            provider=provider,
            ok=False,
            latency_ms=0,
            reason=f"unknown_provider: {provider}",
        )

    api_key = os.environ.get(cfg["env"], "").strip()
    if not api_key:
        return ProbeResult(
            provider=key,
            ok=False,
            latency_ms=0,
            reason="auth_missing",
        )

    req = _build_request(key, cfg, api_key)
    start = time.perf_counter()
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:  # noqa: S310
            status = getattr(resp, "status", None) or resp.getcode()
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            if 200 <= int(status) < 300:
                return ProbeResult(
                    provider=key, ok=True, latency_ms=elapsed_ms, reason="ok"
                )
            return ProbeResult(
                provider=key,
                ok=False,
                latency_ms=elapsed_ms,
                reason=f"http_{int(status)}",
            )
    except socket.timeout:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ProbeResult(
            provider=key, ok=False, latency_ms=elapsed_ms, reason="timeout"
        )
    except error.HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ProbeResult(
            provider=key,
            ok=False,
            latency_ms=elapsed_ms,
            reason=f"http_{int(exc.code)}",
        )
    except error.URLError as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        # socket.timeout can also come wrapped in URLError.reason on some Pythons
        if isinstance(exc.reason, socket.timeout) or (
            isinstance(exc.reason, OSError) and "timed out" in str(exc.reason).lower()
        ):
            return ProbeResult(
                provider=key, ok=False, latency_ms=elapsed_ms, reason="timeout"
            )
        return ProbeResult(
            provider=key,
            ok=False,
            latency_ms=elapsed_ms,
            reason=f"error: {exc.reason}",
        )
    except Exception as exc:  # noqa: BLE001 — last-resort safety net
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ProbeResult(
            provider=key,
            ok=False,
            latency_ms=elapsed_ms,
            reason=f"error: {exc}",
        )


def await_provider_or_backoff(
    provider: str,
    *,
    attempts: tuple[int, ...] = DEFAULT_BACKOFF_SCHEDULE,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> ProbeResult:
    """Probe with exponential backoff. Returns first ok ProbeResult, or final failure.

    The first probe runs immediately (no sleep). Between each subsequent probe
    we sleep ``attempts[i]`` seconds. Total probe count = len(attempts) + 1.
    """
    result = probe(provider, timeout_sec=timeout_sec)
    if result.ok:
        return result

    for delay in attempts:
        sleep_fn(delay)
        result = probe(provider, timeout_sec=timeout_sec)
        if result.ok:
            return result

    return result


def main(argv: list[str] | None = None) -> int:
    """CLI: provider_probe.py <provider> [--backoff] [--timeout SEC]."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print("usage: provider_probe.py <provider> [--backoff] [--timeout SEC]")
        return 2

    provider = args[0]
    use_backoff = "--backoff" in args
    timeout_sec = DEFAULT_TIMEOUT_SEC
    if "--timeout" in args:
        idx = args.index("--timeout")
        if idx + 1 < len(args):
            try:
                timeout_sec = float(args[idx + 1])
            except ValueError:
                print(f"invalid --timeout value: {args[idx + 1]}", file=sys.stderr)
                return 2

    if use_backoff:
        result = await_provider_or_backoff(provider, timeout_sec=timeout_sec)
    else:
        result = probe(provider, timeout_sec=timeout_sec)

    print(json.dumps(result.as_dict()))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
