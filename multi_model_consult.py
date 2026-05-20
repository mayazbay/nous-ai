#!/usr/bin/env python3
"""Multi-model consult — spawn 3 CEO-tier models in parallel, arbitrate with DeepSeek.

Three primary models:
  - Opus 4.7 (Anthropic Messages API / --include-local-opus-answer)
  - GPT-5.5 via Codex (subprocess ssh air codex exec)
  - Grok-4-fast-reasoning via xAI direct API

One arbitrator:
  - deepseek-v4-flash via LiteLLM on Air:4000

CLI:
  python3 tools/multi_model_consult.py \\
    --question "..." \\
    [--context-slug pages/...] \\
    [--output-file pages/audits/CONSULT-<consult_id>.json] \\
    [--include-local-opus-answer "..."] \\
    [--dry-run]

Cost ledger: pages/systems/multi-model-consult-ledger.jsonl (jsonl append)
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import ssl
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALMATY = dt.timezone(dt.timedelta(hours=5))
def _default_wiki() -> Path:
    env = os.environ.get("NOUS_WIKI")
    if env:
        return Path(env)
    tool_root = Path(__file__).resolve().parents[1]
    if (tool_root / "pages").exists():
        return tool_root
    if (tool_root / "wiki" / "pages").exists():
        return tool_root / "wiki"
    return Path("/Users/madia/Documents/Projects/Nous AGaaS/Nous")


DEFAULT_WIKI = _default_wiki()
DEFAULT_LEDGER_REL = Path("pages/systems/multi-model-consult-ledger.jsonl")
DEFAULT_AUDIT_DIR_REL = Path("pages/audits")
DEFAULT_CONTEXT_SLUG = "pages/systems/AGENT-CONTINUITY-PACKET.md"

# Model identifiers (canonical names used in output schema)
MODEL_OPUS = "opus-4-7"
MODEL_CODEX = "codex-gpt-5.5"
MODEL_GROK = "grok-latest-with-x-search"
MODEL_ARBITRATOR = "deepseek-v4-flash"

# Endpoints
XAI_BASE_URL = "https://api.x.ai/v1/chat/completions"
XAI_MODEL_ID = "grok-4-fast-reasoning"
LITELLM_BASE_URL = "http://100.122.219.22:4000/v1/chat/completions"
LITELLM_MODEL_ID = "deepseek-v4-flash"
ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL_ID = "claude-opus-4-7"

# Per-model timeout (seconds)
MODEL_TIMEOUT_S = 30
ARBITRATOR_TIMEOUT_S = 20

# Cost cap per consult (USD)
COST_CAP_USD = 0.50
DAILY_CAP_USD = 20.00

# Billing surfaces recorded for every model route.
BILLING_SUBSCRIPTION = "subscription"
BILLING_LOCAL = "local"
BILLING_XAI_API = "xai_api"
BILLING_ANTHROPIC_API = "anthropic_api"
BILLING_OPENROUTER = "openrouter"
BILLING_UNKNOWN = "unknown"
PAID_API_SURFACES = {BILLING_XAI_API, BILLING_ANTHROPIC_API, BILLING_OPENROUTER}

# Max context chars injected into each model prompt
MAX_CONTEXT_CHARS = 8000

# SSH alias for Air
AIR_HOST = "air"
AIR_ENV_FILE = "~/nous-agaas/.env"
AIR_LITELLM_ENV_FILE = "~/nous-agaas/litellm/.env"

try:
    from agent_continuity_packet import write_packet as _write_continuity_packet
except Exception:  # pragma: no cover - import safety for unusual runtimes
    _write_continuity_packet = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def log(msg: str) -> None:
    print(f"[multi-model-consult] {now_kzt().isoformat()} {msg}", flush=True)


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _paid_api_policy() -> dict[str, Any]:
    """Fail-closed paid API policy for this process."""
    requested = _env_flag("NOUS_PAID_API_ALLOWED")
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
        "requested": requested,
        "cap_usd": cap,
        "reason": reason,
        "missing": missing,
    }


def _paid_api_block_reason(surface: str, model: str) -> str:
    if surface not in PAID_API_SURFACES:
        return ""
    policy = _paid_api_policy()
    if policy["allowed"]:
        return ""
    missing = ", ".join(policy["missing"]) or "paid API policy"
    return (
        f"paid_api_disabled: {model} uses {surface}; "
        "set NOUS_PAID_API_ALLOWED=1 with NOUS_PAID_API_CAP_USD and "
        f"NOUS_PAID_API_REASON before this route can spend ({missing})"
    )


def _billing_surface_summary(
    answers: list[dict[str, Any]],
    arbitration: dict[str, Any],
) -> dict[str, str]:
    surfaces = {
        str(a.get("model", "unknown")): str(a.get("billing_surface", BILLING_UNKNOWN))
        for a in answers
    }
    surfaces[MODEL_ARBITRATOR] = str(arbitration.get("billing_surface", BILLING_OPENROUTER))
    return surfaces


def make_consult_id(question: str, ts: str) -> str:
    """consult_<ISO8601_Z>_<sha8> where sha8 = first 8 chars of sha256(question + timestamp)."""
    raw = (question + ts).encode("utf-8")
    sha8 = hashlib.sha256(raw).hexdigest()[:8]
    return f"consult_{ts}_{sha8}"


def _http_post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int = MODEL_TIMEOUT_S,
) -> dict[str, Any]:
    """Minimal urllib JSON POST; retries macOS Python CA failures with certifi."""
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as exc:
        if not _is_ssl_cert_error(exc):
            raise
        context = _certifi_ssl_context()
        if context is None:
            raise
        with urlopen(req, timeout=timeout, context=context) as resp:
            return json.loads(resp.read().decode("utf-8"))


def _is_ssl_cert_error(exc: URLError) -> bool:
    return isinstance(getattr(exc, "reason", None), ssl.SSLCertVerificationError)


def _certifi_ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi  # type: ignore[import-not-found]
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


def _fetch_xai_key() -> str:
    """Fetch XAI_API_KEY from Air .env via SSH (lazy, never embedded)."""
    return _fetch_env_var("XAI_API_KEY")


def _fetch_anthropic_key() -> str:
    """Fetch ANTHROPIC_API_KEY from Air .env via SSH (lazy, never embedded).

    Added 2026-05-20 to complete CEO tier — Opus self-call was previously
    'unavailable' because ANTHROPIC_API_KEY wasn't local. Same lazy SSH
    pattern as xAI key. With this, Opus + Codex + Grok all live.
    """
    return _fetch_env_var("ANTHROPIC_API_KEY")


def _fetch_litellm_master_key() -> str:
    """Fetch LiteLLM master key for authenticated Air LiteLLM calls."""
    return _fetch_env_var("LITELLM_MASTER_KEY")


def _fetch_env_var(var_name: str) -> str:
    """Generic lazy env-var fetch: local env first, then Air ~/.env via SSH."""
    env_val = os.environ.get(var_name)
    if env_val:
        return env_val
    errors = []
    for env_file in (AIR_ENV_FILE, AIR_LITELLM_ENV_FILE):
        result = subprocess.run(
            ["ssh", AIR_HOST, f"grep ^{var_name}= {env_file}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            errors.append(f"{env_file}: {(result.stderr or result.stdout).strip()}")
            continue
        line = result.stdout.strip()
        if "=" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(f"{var_name} not found via Air env files: {'; '.join(errors)}")


def _effective_context_slug(context_slug: str | None) -> str:
    """Default every consult to the shared continuity packet."""
    return context_slug or DEFAULT_CONTEXT_SLUG


def _refresh_continuity_packet(wiki: Path, context_slug: str) -> None:
    """Best-effort packet refresh before direct model calls."""
    if context_slug != DEFAULT_CONTEXT_SLUG or _write_continuity_packet is None:
        return
    try:
        _write_continuity_packet(wiki)
    except Exception as exc:
        log(f"WARN: continuity packet refresh failed: {type(exc).__name__}: {exc}")


def _load_context_slug(context_slug: str | None, wiki: Path) -> str:
    """Read up to MAX_CONTEXT_CHARS from a context_slug vault path."""
    context_slug = _effective_context_slug(context_slug)
    path = wiki / context_slug
    if not path.exists():
        log(f"WARN: context_slug not found: {path}")
        return ""
    try:
        return path.read_text(encoding="utf-8")[:MAX_CONTEXT_CHARS]
    except OSError as exc:
        log(f"WARN: cannot read context_slug {path}: {exc}")
        return ""


def _build_prompt(question: str, context: str) -> str:
    parts = [f"Question: {question}"]
    if context:
        parts.append(f"\nContext:\n{context[:MAX_CONTEXT_CHARS]}")
    parts.append("\nProvide a concise, evidence-grounded answer. Cite file paths, commands, or URLs where relevant.")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Model callers — each returns a dict matching the answers[] schema
# ---------------------------------------------------------------------------

def _call_opus(question: str, context: str, local_answer: str | None = None) -> dict[str, Any]:
    """Call Opus 4.7 via Anthropic Messages API or use provided local answer."""
    model_key = MODEL_OPUS
    billing_surface = BILLING_ANTHROPIC_API
    t0 = time.monotonic()
    try:
        if local_answer is not None:
            # When invoked FROM Opus, we already have the local answer
            latency_ms = int((time.monotonic() - t0) * 1000)
            return {
                "model": model_key,
                "billing_surface": BILLING_LOCAL,
                "answer": local_answer,
                "confidence": 0.90,
                "tokens": len(local_answer.split()),
                "latency_ms": latency_ms,
                "cost_usd": 0.0,
            }

        block_reason = _paid_api_block_reason(billing_surface, model_key)
        if block_reason:
            raise PermissionError(block_reason)

        try:
            api_key = _fetch_anthropic_key()
        except RuntimeError as exc:
            raise RuntimeError(
                f"ANTHROPIC_API_KEY not set locally nor on Air ~/.env: {exc}; "
                f"pass --include-local-opus-answer instead"
            ) from exc

        payload = {
            "model": ANTHROPIC_MODEL_ID,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": _build_prompt(question, context)}],
        }
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        resp = _http_post_json(ANTHROPIC_BASE_URL, payload, headers, timeout=MODEL_TIMEOUT_S)
        answer = resp["content"][0]["text"]
        usage = resp.get("usage", {})
        in_tokens = usage.get("input_tokens", 0)
        out_tokens = usage.get("output_tokens", 0)
        total_tokens = in_tokens + out_tokens
        # Approximate cost: opus-4-7 $15/1M input + $75/1M output
        cost = (in_tokens * 15 + out_tokens * 75) / 1_000_000
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "model": model_key,
            "billing_surface": billing_surface,
            "answer": answer,
            "confidence": 0.90,
            "tokens": total_tokens,
            "latency_ms": latency_ms,
            "cost_usd": round(cost, 6),
        }
    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "model": model_key,
            "billing_surface": billing_surface,
            "error": f"{type(exc).__name__}: {exc}",
            "latency_ms": latency_ms,
            "cost_usd": 0.0,
        }


def _call_codex(question: str, context: str) -> dict[str, Any]:
    """Call GPT-5.5 via Codex on Air via SSH subprocess."""
    model_key = MODEL_CODEX
    billing_surface = BILLING_SUBSCRIPTION
    t0 = time.monotonic()
    prompt = _build_prompt(question, context)
    try:
        # Escape prompt; cd into trusted wiki dir + --skip-git-repo-check
        # (Codex CLI 0.130.0 refuses to exec outside a trusted dir; live
        # proof 2026-05-20 09:16 surfaced "Not inside a trusted directory
        # and --skip-git-repo-check was not specified").
        prompt_escaped = prompt.replace("'", "'\\''")
        ssh_cmd = (
            "cd ~/nous-agaas/wiki && "
            f"codex exec --skip-git-repo-check -m gpt-5.5 '{prompt_escaped}'"
        )
        result = subprocess.run(
            ["ssh", AIR_HOST, ssh_cmd],
            capture_output=True,
            text=True,
            timeout=MODEL_TIMEOUT_S,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            # Check for subscription cap
            err_lower = (stdout + stderr).lower()
            if "rate limit" in err_lower or "quota" in err_lower or "subscription" in err_lower:
                return {
                    "model": model_key,
                    "billing_surface": billing_surface,
                    "error": f"subscription_cap: {stderr or stdout}",
                    "latency_ms": latency_ms,
                    "cost_usd": 0.0,
                }
            return {
                "model": model_key,
                "billing_surface": billing_surface,
                "error": f"codex_failed rc={result.returncode}: {stderr or stdout}",
                "latency_ms": latency_ms,
                "cost_usd": 0.0,
            }

        if not stdout:
            return {
                "model": model_key,
                "billing_surface": billing_surface,
                "error": "codex_empty_output",
                "latency_ms": latency_ms,
                "cost_usd": 0.0,
            }

        # Codex subscription path = $0.00; no OpenAI API fallback is used here.
        return {
            "model": model_key,
            "billing_surface": billing_surface,
            "answer": stdout,
            "confidence": 0.90,
            "tokens": len(stdout.split()),
            "latency_ms": latency_ms,
            "cost_usd": 0.0,
        }
    except subprocess.TimeoutExpired:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "model": model_key,
            "billing_surface": billing_surface,
            "error": f"timeout after {MODEL_TIMEOUT_S}s",
            "latency_ms": latency_ms,
            "cost_usd": 0.0,
        }
    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "model": model_key,
            "billing_surface": billing_surface,
            "error": f"{type(exc).__name__}: {exc}",
            "latency_ms": latency_ms,
            "cost_usd": 0.0,
        }


def _call_grok(question: str, context: str) -> dict[str, Any]:
    """Call Grok-4-fast-reasoning via xAI direct API."""
    model_key = MODEL_GROK
    billing_surface = BILLING_XAI_API
    t0 = time.monotonic()
    try:
        block_reason = _paid_api_block_reason(billing_surface, model_key)
        if block_reason:
            raise PermissionError(block_reason)

        xai_key = _fetch_xai_key()
        payload = {
            "model": XAI_MODEL_ID,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": _build_prompt(question, context)}],
        }
        headers = {
            "Authorization": f"Bearer {xai_key}",
            "Content-Type": "application/json",
        }
        resp = _http_post_json(XAI_BASE_URL, payload, headers, timeout=MODEL_TIMEOUT_S)
        answer = resp["choices"][0]["message"]["content"]
        usage = resp.get("usage", {})
        in_tokens = usage.get("prompt_tokens", 0)
        out_tokens = usage.get("completion_tokens", 0)
        total_tokens = in_tokens + out_tokens
        # Approximate cost: grok ~$5/1M input + $15/1M output (placeholder)
        cost = (in_tokens * 5 + out_tokens * 15) / 1_000_000
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "model": model_key,
            "billing_surface": billing_surface,
            "answer": answer,
            "confidence": 0.80,
            "tokens": total_tokens,
            "latency_ms": latency_ms,
            "cost_usd": round(cost, 6),
        }
    except subprocess.TimeoutExpired:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "model": model_key,
            "billing_surface": billing_surface,
            "error": f"xai_key_fetch_timeout",
            "latency_ms": latency_ms,
            "cost_usd": 0.0,
        }
    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "model": model_key,
            "billing_surface": billing_surface,
            "error": f"{type(exc).__name__}: {exc}",
            "latency_ms": latency_ms,
            "cost_usd": 0.0,
        }


def _arbitrate(answers: list[dict[str, Any]], question: str) -> dict[str, Any]:
    """Run DeepSeek arbitration over available (non-error) answers."""
    t0 = time.monotonic()
    billing_surface = BILLING_OPENROUTER
    successful = [a for a in answers if "answer" in a]
    if not successful:
        return {
            "winner_model": None,
            "rationale": "All models failed; no arbitration possible.",
            "agree_count": 0,
            "dissent_count": len(answers),
            "arbitrator_model": MODEL_ARBITRATOR,
            "billing_surface": billing_surface,
            "call_executed": False,
            "arbitrator_cost_usd": 0.0,
            "error": "all_models_failed",
        }
    if len(successful) == 1:
        winner = successful[0]
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "winner_model": winner["model"],
            "rationale": "Only one model succeeded; auto-winner.",
            "agree_count": 1,
            "dissent_count": len(answers) - 1,
            "arbitrator_model": MODEL_ARBITRATOR,
            "billing_surface": billing_surface,
            "call_executed": False,
            "arbitrator_cost_usd": 0.0,
        }

    block_reason = _paid_api_block_reason(billing_surface, MODEL_ARBITRATOR)
    if block_reason:
        best = max(successful, key=lambda a: a.get("confidence", 0.0))
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "winner_model": best["model"],
            "rationale": "Paid OpenRouter arbitration disabled; fell back to highest confidence.",
            "agree_count": 1,
            "dissent_count": len(successful) - 1,
            "arbitrator_model": MODEL_ARBITRATOR,
            "billing_surface": billing_surface,
            "call_executed": False,
            "arbitrator_cost_usd": 0.0,
            "latency_ms": latency_ms,
            "paid_api_blocked": True,
            "arbitrator_error": block_reason,
        }

    # Build arbitration prompt
    answers_text = "\n\n".join(
        f"=== Answer from {a['model']} ===\n{a['answer']}"
        for a in successful
    )
    arb_prompt = (
        f"Question: {question}\n\n"
        f"Three (or fewer) answers below from different AI models:\n\n{answers_text}\n\n"
        "Pick the answer most grounded in real evidence (file paths, live commands, citations) "
        "over confident-sounding-but-untestable. "
        'Output JSON only: {"winner_model": "<model_name>", "rationale": "<1-2 sentences>", '
        '"agree_count": <int>, "dissent_count": <int>}'
    )

    try:
        payload = {
            "model": LITELLM_MODEL_ID,
            "max_tokens": 512,
            "messages": [{"role": "user", "content": arb_prompt}],
        }
        headers = {"Content-Type": "application/json"}
        try:
            litellm_key = _fetch_litellm_master_key()
        except RuntimeError:
            litellm_key = ""
        if litellm_key:
            headers["Authorization"] = f"Bearer {litellm_key}"
        resp = _http_post_json(LITELLM_BASE_URL, payload, headers, timeout=ARBITRATOR_TIMEOUT_S)
        raw = resp["choices"][0]["message"]["content"].strip()

        # Extract JSON from response (may be wrapped in markdown)
        if "```" in raw:
            raw = raw.split("```")[1].strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()

        arb = json.loads(raw)
        usage = resp.get("usage", {})
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        # DeepSeek v4 flash ~$0.14/1M input + $0.28/1M output
        cost = (in_tok * 0.14 + out_tok * 0.28) / 1_000_000

        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "winner_model": arb.get("winner_model"),
            "rationale": arb.get("rationale", ""),
            "agree_count": arb.get("agree_count", 0),
            "dissent_count": arb.get("dissent_count", 0),
            "arbitrator_model": MODEL_ARBITRATOR,
            "billing_surface": billing_surface,
            "call_executed": True,
            "arbitrator_cost_usd": round(cost, 6),
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        # Fallback: pick highest-confidence successful answer
        best = max(successful, key=lambda a: a.get("confidence", 0.0))
        return {
            "winner_model": best["model"],
            "rationale": f"Arbitrator failed ({type(exc).__name__}: {exc}); fell back to highest confidence.",
            "agree_count": 1,
            "dissent_count": len(successful) - 1,
            "arbitrator_model": MODEL_ARBITRATOR,
            "billing_surface": billing_surface,
            "call_executed": False,
            "arbitrator_cost_usd": 0.0,
            "latency_ms": latency_ms,
            "arbitrator_error": f"{type(exc).__name__}: {exc}",
        }


# ---------------------------------------------------------------------------
# Core consult() function
# ---------------------------------------------------------------------------

def consult(
    question: str,
    context_slug: str | None = None,
    local_opus_answer: str | None = None,
    dry_run: bool = False,
    wiki: Path | None = None,
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Run multi-model consult; return canonical JSON schema dict."""
    wiki = wiki or DEFAULT_WIKI
    ledger_path = ledger_path or (wiki / DEFAULT_LEDGER_REL)

    ts = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
    consult_id = make_consult_id(question, ts)
    effective_context_slug = _effective_context_slug(context_slug)
    if not dry_run:
        _refresh_continuity_packet(wiki, effective_context_slug)
    context = _load_context_slug(effective_context_slug, wiki)

    log(f"consult_id={consult_id} question={question[:80]!r} dry_run={dry_run}")

    if dry_run:
        log("DRY RUN — would call: opus-4-7, codex-gpt-5.5, grok-4-fast-reasoning, deepseek-v4-flash (arbitrator)")
        return {
            "consult_id": consult_id,
            "question": question,
            "context_slug": effective_context_slug,
            "answers": [],
            "arbitration": {},
            "billing_surfaces": {
                MODEL_OPUS: BILLING_ANTHROPIC_API,
                MODEL_CODEX: BILLING_SUBSCRIPTION,
                MODEL_GROK: BILLING_XAI_API,
                MODEL_ARBITRATOR: BILLING_OPENROUTER,
            },
            "paid_api_policy": _paid_api_policy(),
            "actionable_answer": "",
            "dissent_notes": "",
            "evidence_paths": [],
            "skill_update_proposal": "",
            "dry_run": True,
        }

    # Parallel model calls
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        fut_opus = executor.submit(_call_opus, question, context, local_opus_answer)
        fut_codex = executor.submit(_call_codex, question, context)
        fut_grok = executor.submit(_call_grok, question, context)

        answers = []
        for fut in [fut_opus, fut_codex, fut_grok]:
            try:
                answers.append(fut.result(timeout=MODEL_TIMEOUT_S + 5))
            except Exception as exc:
                # Should not happen since each _call_* catches internally
                answers.append({"model": "unknown", "error": f"{type(exc).__name__}: {exc}", "cost_usd": 0.0})

    # Cost cap check
    total_cost = sum(a.get("cost_usd", 0.0) for a in answers)
    cap_warning = ""
    if total_cost >= COST_CAP_USD:
        cap_warning = f"cost_cap_hit: ${total_cost:.4f} >= ${COST_CAP_USD}"
        log(f"WARN: {cap_warning}")

    # Arbitration
    arbitration = _arbitrate(answers, question)
    total_cost += arbitration.get("arbitrator_cost_usd", 0.0)

    # Extract actionable answer and dissent notes
    winner_model = arbitration.get("winner_model")
    actionable_answer = ""
    dissent_notes = ""
    evidence_paths: list[str] = []

    winner_entry = next((a for a in answers if a.get("model") == winner_model), None)
    if winner_entry:
        actionable_answer = winner_entry.get("answer", "")
    dissenters = [a for a in answers if a.get("model") != winner_model and "answer" in a]
    if dissenters:
        dissent_notes = " | ".join(
            f"{a['model']}: {a['answer'][:200]}" for a in dissenters
        )

    # Build result
    billing_surfaces = _billing_surface_summary(answers, arbitration)
    result: dict[str, Any] = {
        "consult_id": consult_id,
        "question": question,
        "context_slug": effective_context_slug,
        "answers": answers,
        "arbitration": arbitration,
        "billing_surfaces": billing_surfaces,
        "paid_api_policy": _paid_api_policy(),
        "actionable_answer": actionable_answer,
        "dissent_notes": dissent_notes,
        "evidence_paths": evidence_paths,
        "skill_update_proposal": "",
        "total_cost_usd": round(total_cost, 6),
    }
    if cap_warning:
        result["cap_warning"] = cap_warning

    # Track unavailable models
    unavailable = [a["model"] for a in answers if "error" in a]
    if unavailable:
        result["model_unavailable"] = unavailable

    # Append to cost ledger
    _append_ledger(ledger_path, consult_id, question, total_cost, result)

    return result


def _append_ledger(
    ledger_path: Path,
    consult_id: str,
    question: str,
    total_cost: float,
    result: dict[str, Any],
) -> None:
    """Append one JSONL line to the cost ledger."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "consult_id": consult_id,
        "ts": now_utc().isoformat(),
        "question_head": question[:120],
        "total_cost_usd": round(total_cost, 6),
        "winner_model": result.get("arbitration", {}).get("winner_model"),
        "model_unavailable": result.get("model_unavailable", []),
        "billing_surfaces": result.get("billing_surfaces", {}),
        "paid_api_policy": result.get("paid_api_policy", {}),
    }
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", required=True, help="Question to put to the council.")
    parser.add_argument("--context-slug", default=None, help="Vault-relative path to inject as context.")
    parser.add_argument("--output-file", default=None, help="Write result JSON to this path.")
    parser.add_argument(
        "--include-local-opus-answer",
        default=None,
        metavar="ANSWER",
        help="Skip Opus API call; use this string as Opus answer (invoke-from-Opus mode).",
    )
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Print intended calls without executing.")
    parser.add_argument(
        "--allow-paid-api",
        action="store_true",
        help="Permit paid API routes only when paired with --paid-api-cap-usd and --paid-api-reason.",
    )
    parser.add_argument("--paid-api-cap-usd", type=float, default=None)
    parser.add_argument("--paid-api-reason", default=None)
    parser.add_argument("--json", action="store_true", help="Output result as JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    ledger = args.ledger or (args.wiki / DEFAULT_LEDGER_REL)
    if args.allow_paid_api:
        os.environ["NOUS_PAID_API_ALLOWED"] = "1"
    if args.paid_api_cap_usd is not None:
        os.environ["NOUS_PAID_API_CAP_USD"] = str(args.paid_api_cap_usd)
    if args.paid_api_reason is not None:
        os.environ["NOUS_PAID_API_REASON"] = args.paid_api_reason

    result = consult(
        question=args.question,
        context_slug=args.context_slug,
        local_opus_answer=args.include_local_opus_answer,
        dry_run=args.dry_run,
        wiki=args.wiki,
        ledger_path=ledger,
    )

    if args.output_file:
        out_path = Path(args.output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log(f"wrote result to {out_path}")

    if args.json or not args.output_file:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    winner = result.get("arbitration", {}).get("winner_model") or "none"
    total = result.get("total_cost_usd", 0.0)
    unavailable = result.get("model_unavailable", [])
    log(f"done winner={winner} total_cost=${total:.4f} unavailable={unavailable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
