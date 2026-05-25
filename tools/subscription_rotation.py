#!/usr/bin/env python3
"""subscription_rotation.py — AP-44 dynamic subscription rotation for the CEO route.

Per ceo-hierarchy v1.11.0 AP-44 (Madi directive 2026-05-23, Stage 4 moonlit-pnueli):
  Codex GPT-5.5 subscription FIRST → Claude/Opus subscription SECOND → GPT API THIRD.

  Cheapest-first: both $200/mo subscriptions consumed before any pay-as-you-go OpenAI
  API spend. Worker tier unaffected (DeepSeek V4 Flash remains default per AP-25).

This module provides STANDALONE fallback helpers callable from command_center.py
when Codex is blocked (per AP-40 `_codex_daily_budget_ok` gate). The intent is to
let the existing command_center.py wire ONE call site through `rotate_codex_to_fallback()`
behind a feature flag (NOUS_AP44_ROTATION_ENABLED=1) so prod stays safe until
runtime cutover is explicitly approved.

CLI (for manual probing + smoke):
  python3 tools/subscription_rotation.py --query "<text>" --probe                  # report what would fire
  python3 tools/subscription_rotation.py --query "<text>" --tier claude --json     # force Claude
  python3 tools/subscription_rotation.py --query "<text>" --tier openai --json     # force GPT
  python3 tools/subscription_rotation.py --query "<text>" --rotate --json          # full chain

Acceptance:
  - Each tier returns dict {model, billing_surface, answer|error, latency_ms, cost_usd}
  - Claude subscription path uses ANTHROPIC_API_KEY ($200/mo Console/Pro)
  - OpenAI API path uses OPENAI_API_KEY (pay-as-you-go), NOUS_PAID_API gates enforced
  - Rotation chain stops at first successful tier; records the chain in `chain_trace`
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import ssl
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ALMATY = dt.timezone(dt.timedelta(hours=5))

# Endpoints
ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL_ID = "claude-opus-4-7"
OPENAI_BASE_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL_ID = "gpt-5.5"  # fall back to gpt-5 if not available; CLI flag --openai-model overrides

# Tier identifiers (used in dict outputs + telemetry)
TIER_CLAUDE = "claude-opus-subscription"
TIER_OPENAI = "openai-gpt-api"
TIER_CODEX = "codex-gpt-5.5-subscription"

# Billing surfaces (must match multi_model_consult.py constants for consistency)
BILLING_SUBSCRIPTION = "subscription"
BILLING_ANTHROPIC_API = "anthropic_api"
BILLING_OPENAI_API = "openai_api"

# Timeouts
HTTP_TIMEOUT_S = 60
MAX_TOKENS = 1500

# Approximate pricing (per million tokens, May 2026)
ANTHROPIC_PRICE_IN_PER_M = 15.0
ANTHROPIC_PRICE_OUT_PER_M = 75.0
OPENAI_PRICE_IN_PER_M = 5.0    # gpt-5.5 placeholder, update from billing page when known
OPENAI_PRICE_OUT_PER_M = 20.0

AIR_HOST = "air"
AIR_ENV_FILE = "~/nous-agaas/.env"


# ---------------------------------------------------------------------------
# Env resolution (mirrors multi_model_consult._fetch_env_var pattern)
# ---------------------------------------------------------------------------

def _fetch_env_var(name: str) -> str:
    val = os.environ.get(name)
    if val:
        return val
    local_env = Path.home() / "nous-agaas" / ".env"
    if local_env.exists():
        for line in local_env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip("'\"")
    try:
        proc = subprocess.run(
            ["ssh", AIR_HOST, f"grep ^{name}= {AIR_ENV_FILE} | head -1"],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode == 0 and "=" in proc.stdout:
            return proc.stdout.strip().split("=", 1)[1].strip().strip("'\"")
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return ""


def _paid_api_policy() -> dict[str, Any]:
    """Fail-closed paid API policy. Mirror of multi_model_consult._paid_api_policy."""
    requested = os.environ.get("NOUS_PAID_API_ALLOWED", "").strip().lower() in {"1", "true", "yes", "on"}
    raw_cap = os.environ.get("NOUS_PAID_API_CAP_USD", "").strip()
    try:
        cap = float(raw_cap) if raw_cap else 0.0
    except ValueError:
        cap = 0.0
    reason = os.environ.get("NOUS_PAID_API_REASON", "").strip()
    missing = []
    if not requested:
        missing.append("NOUS_PAID_API_ALLOWED")
    if cap <= 0:
        missing.append("NOUS_PAID_API_CAP_USD")
    if not reason:
        missing.append("NOUS_PAID_API_REASON")
    return {
        "allowed": requested and cap > 0 and bool(reason),
        "cap_usd": cap,
        "reason": reason,
        "missing": missing,
    }


# ---------------------------------------------------------------------------
# HTTP helper (SSL retry mirrors multi_model_consult)
# ---------------------------------------------------------------------------

def _http_post_json(url: str, payload: dict[str, Any], headers: dict[str, str],
                    timeout: int = HTTP_TIMEOUT_S) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as exc:
        if isinstance(getattr(exc, "reason", None), ssl.SSLCertVerificationError):
            try:
                import certifi  # type: ignore[import-not-found]
                ctx = ssl.create_default_context(cafile=certifi.where())
                with urlopen(req, timeout=timeout, context=ctx) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except ImportError:
                pass
        raise


# ---------------------------------------------------------------------------
# Tier callers — each returns the same dict shape for downstream consumers
# ---------------------------------------------------------------------------

def call_claude_subscription(query: str, model_id: str = ANTHROPIC_MODEL_ID,
                             max_tokens: int = MAX_TOKENS) -> dict[str, Any]:
    """Call Claude/Opus via Anthropic Messages API with subscription billing tier.

    Note: the Anthropic Console subscription ($200/mo) bills against your account's
    monthly cap. When the cap is reached, the API returns 429 with a specific
    error message. We surface that as a tier-blocked error so the rotation chain
    can step to OpenAI.
    """
    t0 = time.monotonic()
    try:
        api_key = _fetch_env_var("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not resolvable")

        payload = {
            "model": model_id,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": query}],
        }
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        resp = _http_post_json(ANTHROPIC_BASE_URL, payload, headers)
        answer = resp["content"][0]["text"]
        usage = resp.get("usage", {})
        in_tok = int(usage.get("input_tokens", 0))
        out_tok = int(usage.get("output_tokens", 0))
        cost = (in_tok * ANTHROPIC_PRICE_IN_PER_M + out_tok * ANTHROPIC_PRICE_OUT_PER_M) / 1_000_000
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "tier": TIER_CLAUDE,
            "model": model_id,
            "billing_surface": BILLING_ANTHROPIC_API,
            "answer": answer,
            "tokens_in": in_tok,
            "tokens_out": out_tok,
            "cost_usd": round(cost, 6),
            "latency_ms": latency_ms,
            "ok": True,
        }
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300] if hasattr(exc, "read") else ""
        rate_limited = exc.code in (429, 529) or "rate_limit" in body.lower() or "subscription" in body.lower()
        return {
            "tier": TIER_CLAUDE,
            "model": model_id,
            "billing_surface": BILLING_ANTHROPIC_API,
            "ok": False,
            "rate_limited": rate_limited,
            "error": f"HTTP {exc.code}: {body}",
            "latency_ms": int((time.monotonic() - t0) * 1000),
            "cost_usd": 0.0,
        }
    except Exception as exc:
        return {
            "tier": TIER_CLAUDE,
            "model": model_id,
            "billing_surface": BILLING_ANTHROPIC_API,
            "ok": False,
            "rate_limited": False,
            "error": f"{type(exc).__name__}: {exc}",
            "latency_ms": int((time.monotonic() - t0) * 1000),
            "cost_usd": 0.0,
        }


def call_openai_api(query: str, model_id: str = OPENAI_MODEL_ID,
                    max_tokens: int = MAX_TOKENS) -> dict[str, Any]:
    """Call OpenAI direct API (pay-as-you-go) as the last-resort fallback.

    Fails closed if NOUS_PAID_API_ALLOWED is not set — per Subscription-First
    amendment (ceo-hierarchy AP-9). Caller MUST set NOUS_PAID_API_* env vars
    before invoking this path.
    """
    t0 = time.monotonic()
    policy = _paid_api_policy()
    if not policy["allowed"]:
        return {
            "tier": TIER_OPENAI,
            "model": model_id,
            "billing_surface": BILLING_OPENAI_API,
            "ok": False,
            "rate_limited": False,
            "error": f"paid_api_disabled: missing={policy['missing']}",
            "latency_ms": int((time.monotonic() - t0) * 1000),
            "cost_usd": 0.0,
        }

    try:
        api_key = _fetch_env_var("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not resolvable")

        payload = {
            "model": model_id,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": query}],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        resp = _http_post_json(OPENAI_BASE_URL, payload, headers)
        answer = resp["choices"][0]["message"]["content"]
        usage = resp.get("usage", {})
        in_tok = int(usage.get("prompt_tokens", 0))
        out_tok = int(usage.get("completion_tokens", 0))
        cost = (in_tok * OPENAI_PRICE_IN_PER_M + out_tok * OPENAI_PRICE_OUT_PER_M) / 1_000_000
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "tier": TIER_OPENAI,
            "model": model_id,
            "billing_surface": BILLING_OPENAI_API,
            "answer": answer,
            "tokens_in": in_tok,
            "tokens_out": out_tok,
            "cost_usd": round(cost, 6),
            "latency_ms": latency_ms,
            "ok": True,
        }
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300] if hasattr(exc, "read") else ""
        rate_limited = exc.code in (429,) or "rate_limit" in body.lower()
        return {
            "tier": TIER_OPENAI,
            "model": model_id,
            "billing_surface": BILLING_OPENAI_API,
            "ok": False,
            "rate_limited": rate_limited,
            "error": f"HTTP {exc.code}: {body}",
            "latency_ms": int((time.monotonic() - t0) * 1000),
            "cost_usd": 0.0,
        }
    except Exception as exc:
        return {
            "tier": TIER_OPENAI,
            "model": model_id,
            "billing_surface": BILLING_OPENAI_API,
            "ok": False,
            "rate_limited": False,
            "error": f"{type(exc).__name__}: {exc}",
            "latency_ms": int((time.monotonic() - t0) * 1000),
            "cost_usd": 0.0,
        }


# ---------------------------------------------------------------------------
# Rotation entry point — call when Codex is blocked
# ---------------------------------------------------------------------------

def rotate_codex_to_fallback(query: str, max_tokens: int = MAX_TOKENS,
                             openai_model: str = OPENAI_MODEL_ID,
                             skip_openai: bool = False) -> dict[str, Any]:
    """Try Claude subscription first, then OpenAI API. Stop at first success.

    `skip_openai=True` is the conservative mode (caller signals it doesn't want
    pay-as-you-go fallback under any circumstances). Default tries everything.

    Returns the successful tier's full dict, plus `chain_trace` listing every
    tier attempted with its outcome.
    """
    chain_trace: list[dict[str, Any]] = []
    started = dt.datetime.now(ALMATY).isoformat()

    claude_result = call_claude_subscription(query, max_tokens=max_tokens)
    chain_trace.append({"tier": claude_result["tier"], "ok": claude_result["ok"],
                        "rate_limited": claude_result.get("rate_limited"),
                        "error": claude_result.get("error"),
                        "latency_ms": claude_result.get("latency_ms")})
    if claude_result.get("ok"):
        claude_result["chain_trace"] = chain_trace
        claude_result["chain_started_at"] = started
        return claude_result

    # Claude failed; only continue if Claude was rate-limited (subscription exhausted)
    # OR genuinely down. For other errors (e.g. missing key), still try OpenAI as last resort.
    if skip_openai:
        return {
            "tier": "none",
            "ok": False,
            "error": "Claude failed and skip_openai=True; no fallback attempted",
            "chain_trace": chain_trace,
            "chain_started_at": started,
            "cost_usd": claude_result.get("cost_usd", 0.0),
        }

    openai_result = call_openai_api(query, model_id=openai_model, max_tokens=max_tokens)
    chain_trace.append({"tier": openai_result["tier"], "ok": openai_result["ok"],
                        "rate_limited": openai_result.get("rate_limited"),
                        "error": openai_result.get("error"),
                        "latency_ms": openai_result.get("latency_ms")})
    if openai_result.get("ok"):
        openai_result["chain_trace"] = chain_trace
        openai_result["chain_started_at"] = started
        return openai_result

    # Both failed; return composite
    total_cost = (claude_result.get("cost_usd", 0.0) or 0.0) + (openai_result.get("cost_usd", 0.0) or 0.0)
    return {
        "tier": "none",
        "ok": False,
        "error": "all fallback tiers failed",
        "chain_trace": chain_trace,
        "chain_started_at": started,
        "cost_usd": total_cost,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print(d: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(d, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(d, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="query text to send")
    parser.add_argument("--tier", choices=["claude", "openai", "rotate"], default="rotate",
                        help="force a single tier or run the full chain (default: rotate)")
    parser.add_argument("--openai-model", default=OPENAI_MODEL_ID,
                        help=f"OpenAI model id (default: {OPENAI_MODEL_ID})")
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    parser.add_argument("--probe", action="store_true",
                        help="probe-only mode: report what would fire without making a call")
    parser.add_argument("--skip-openai", action="store_true",
                        help="rotate without OpenAI fallback (Claude only)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.probe:
        policy = _paid_api_policy()
        report = {
            "probe": True,
            "tier_arg": args.tier,
            "openai_model": args.openai_model,
            "paid_api_policy": policy,
            "anthropic_key_present": bool(_fetch_env_var("ANTHROPIC_API_KEY")),
            "openai_key_present": bool(_fetch_env_var("OPENAI_API_KEY")),
            "would_fire": (
                "claude only" if args.tier == "claude"
                else "openai only (requires NOUS_PAID_API_ALLOWED)" if args.tier == "openai"
                else "claude → openai (with rotation)" if not args.skip_openai
                else "claude only (skip_openai)"
            ),
        }
        _print(report, args.json)
        return 0

    if args.tier == "claude":
        result = call_claude_subscription(args.query, max_tokens=args.max_tokens)
    elif args.tier == "openai":
        result = call_openai_api(args.query, model_id=args.openai_model, max_tokens=args.max_tokens)
    else:
        result = rotate_codex_to_fallback(args.query, max_tokens=args.max_tokens,
                                          openai_model=args.openai_model,
                                          skip_openai=args.skip_openai)

    _print(result, args.json)
    return 0 if result.get("ok") else 3


if __name__ == "__main__":
    raise SystemExit(main())
