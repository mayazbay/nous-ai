#!/usr/bin/env python3
"""
tools/ask_grader.py — Mercury Phase 1 grader (passive observer on /ask JSONL).

Spec: pages/specs/2026-04-30-mercury-hybrid-retrieval-gap-analysis.md (Phase 1).
Doctrine refs: ceo-hierarchy v1.1.0 (tier routing + correlation_id),
gbrain-ops AP-7 (no silent fallbacks), session-operating-contract Rule 7
(hard-banned patterns), karpathy-coding-principles P2 (simplicity-first).

Behavior:
  - Reads tail of ~/nous-agaas/logs/ask-hierarchy.jsonl.
  - Finds turns from last LOOKBACK_MINUTES that have `final_response_text`
    AND no matching grader record yet (dedup by correlation_id).
  - Samples per ceo-hierarchy-aware rate: 10% Tier-1, 100% Tier-3,
    100% urgent-keyword bypass.
  - Calls DeepSeek V4 Pro via LiteLLM (deepseek-v4-pro alias) with a
    schema-locked tool call returning {category, quality, issues[],
    confidence, reasoning}.
  - Persists to ~/nous-agaas/logs/ask-verdicts.jsonl, append-only,
    keyed by correlation_id.
  - Self-throttles if 7-day cumulative cost exceeds COST_CEILING_7D.
  - Fails LOUD on schema violation, missing key, transport error.
  - Deterministic Tier-1 sampling: hash(correlation_id) % 100 < 10
    (matches autoplan decision #10 — replay/audit safe).

Usage:
    LITELLM_MASTER_KEY=sk-... python3 tools/ask_grader.py [--dry-run] [--once]

Exit codes:
    0   success (records written or no work)
    1   transport/config error
    2   schema/quarantine (one or more turns failed schema; see stderr)
    3   throttled (cost ceiling hit; no work attempted)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import time
from typing import Any

# ---------------------------------------------------------------------------
# Constants — single source of truth. Override-by-env when explicitly tested.
# ---------------------------------------------------------------------------
ASK_HIERARCHY_LOG = os.environ.get(
    "ASK_HIERARCHY_LOG",
    os.path.expanduser("~/nous-agaas/logs/ask-hierarchy.jsonl"),
)
ASK_GRADER_LOG = os.environ.get(
    "ASK_GRADER_LOG",
    os.path.expanduser("~/nous-agaas/logs/ask-verdicts.jsonl"),
)
LITELLM_BASE_URL = os.environ.get(
    "LITELLM_BASE_URL", "http://100.122.219.22:4000"
)  # Air Tailscale; reachable from Mac+Air. Document this in plist.
LITELLM_MODEL = os.environ.get("LITELLM_GRADER_MODEL", "deepseek-v4-pro")

LOOKBACK_MINUTES = int(os.environ.get("GRADER_LOOKBACK_MIN", "15"))
COST_CEILING_7D = float(os.environ.get("GRADER_COST_CEILING_7D", "10.50"))  # USD
TIER1_SAMPLE_PCT = int(os.environ.get("GRADER_TIER1_PCT", "10"))  # 10 of 100
TIER2_SAMPLE_PCT = int(os.environ.get("GRADER_TIER2_PCT", "50"))  # 50 of 100 (parent decision; was 100)
TIMEOUT_SECONDS = float(os.environ.get("GRADER_TIMEOUT_S", "45"))

# Spec section 2 schema-locked enums.
ALLOWED_CATEGORY = {
    "coding", "research", "status", "ops", "regulatory", "satory",
    "kazakhstan", "telegram-meta", "other",
}
ALLOWED_QUALITY = {"excellent", "good", "acceptable", "poor"}
ALLOWED_ISSUES = {
    "incomplete", "hallucination", "tool_misuse", "missed_context",
    "wrong_routing", "infra_flake", "drift_artifact", "persona_cosplay",
    "no_done_protocol",
}

# ceo-hierarchy urgent-keyword set (mirrors skills/ceo-hierarchy/SKILL.md
# v1.1.0 "urgent-keyword auto-bypass"). Lowercased; must be substring.
URGENT_KEYWORDS = (
    "urgent", "broke", "down", "prod", "demo", "демо", "срочно",
    "critical", "now", "asap", "crisis",
)

# DeepSeek V4 Pro pricing (USD per 1M tokens, OpenRouter listing as of
# session 77 2026-04-27). Used for cost estimate only — LiteLLM will
# return cost in response if configured, but we compute defensively.
COST_IN_PER_1M = float(os.environ.get("GRADER_COST_IN_PER_1M", "0.27"))
COST_OUT_PER_1M = float(os.environ.get("GRADER_COST_OUT_PER_1M", "1.10"))

# Schema version — per autoplan decision #16 (per-record schema declaration).
SCHEMA_VERSION = "grader.v1"


# ---------------------------------------------------------------------------
# Errors. Fail loud; no silent fallback (gbrain-ops AP-7).
# ---------------------------------------------------------------------------
class GraderError(Exception):
    """Base — anything caller should see."""


class SchemaError(GraderError):
    """Judge returned malformed JSON / missing or extra fields / bad enum."""


class ThrottleError(GraderError):
    """7-day cost ceiling exceeded."""


class TransportError(GraderError):
    """LiteLLM call failed (network, auth, 5xx)."""


# ---------------------------------------------------------------------------
# Sampling — deterministic. hash(correlation_id) % 100 < pct.
# ---------------------------------------------------------------------------
def _is_urgent(query_text: str | None) -> bool:
    if not query_text:
        return False
    lower = query_text.lower()
    return any(kw in lower for kw in URGENT_KEYWORDS)


def should_sample(
    *,
    tier: int | None,
    correlation_id: str,
    query_text: str | None,
    tier1_pct: int = TIER1_SAMPLE_PCT,
    tier2_pct: int = TIER2_SAMPLE_PCT,
) -> bool:
    """
    Sampling rule (spec section 2 + autoplan decision #10 + parent decision
    Tier-2 default 100%→50% to keep cost ceiling defensible while still
    catching Tier-2 quality drift; override via GRADER_TIER2_PCT env):
      - Tier 3 → 100% (always sampled)
      - Urgent-keyword query (any tier) → 100%
      - Tier 1 → tier1_pct deterministic via hash(correlation_id) % 100
      - Tier 2 → tier2_pct deterministic via hash(correlation_id) % 100
      - Unknown tier → fail loud (raises GraderError) — caller must enforce
        upstream tier label per ceo-hierarchy Rule 4.
    """
    if tier is None:
        raise GraderError(f"missing tier on correlation_id={correlation_id!r}")
    if tier == 3:
        return True
    if _is_urgent(query_text):
        return True
    h = int(
        hashlib.sha256(correlation_id.encode("utf-8")).hexdigest(),
        16,
    )
    if tier == 2:
        return (h % 100) < tier2_pct
    if tier == 1:
        return (h % 100) < tier1_pct
    raise GraderError(f"unknown tier={tier!r} on correlation_id={correlation_id!r}")


# ---------------------------------------------------------------------------
# JSONL I/O. Inode-aware tail is overkill for Phase 1 — we read entire
# file each cron tick (5 min) and skip already-graded turns by
# correlation_id dedup. Phase 2+ may switch to bookmark+inode if log grows.
# ---------------------------------------------------------------------------
def _iter_jsonl(path: str):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line_num, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as e:
                # Loud — corrupt JSONL is a real bug in the producer.
                print(
                    f"[ask_grader] WARN corrupt line {line_num} in {path}: {e}",
                    file=sys.stderr,
                )


def load_already_graded(grader_log: str = ASK_GRADER_LOG) -> set[str]:
    """Return correlation_ids already present in grader log (dedup key)."""
    seen: set[str] = set()
    for entry in _iter_jsonl(grader_log):
        cid = entry.get("correlation_id")
        if cid:
            seen.add(cid)
    return seen


def _parse_ts(ts: str) -> _dt.datetime | None:
    """Parse ISO 8601 with optional Z suffix; return UTC datetime or None."""
    if not ts:
        return None
    cleaned = ts[:-1] if ts.endswith("Z") else ts
    try:
        dt = _dt.datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        return dt.astimezone(_dt.timezone.utc)
    except ValueError:
        return None


def collect_pending(
    *,
    hierarchy_log: str = ASK_HIERARCHY_LOG,
    grader_log: str = ASK_GRADER_LOG,
    lookback_minutes: int = LOOKBACK_MINUTES,
    now: _dt.datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Find turns with `final_response_text` AND no grader record yet AND
    within lookback window. Folds per-correlation_id (last-write-wins on ts).
    """
    cutoff = (now or _dt.datetime.now(tz=_dt.timezone.utc)) - _dt.timedelta(
        minutes=lookback_minutes
    )
    already = load_already_graded(grader_log)
    by_cid: dict[str, dict[str, Any]] = {}
    for entry in _iter_jsonl(hierarchy_log):
        cid = entry.get("correlation_id")
        if not cid:
            continue
        if cid in already:
            continue
        if not entry.get("final_response_text"):
            continue
        ts = _parse_ts(entry.get("ts", ""))
        if ts is None or ts < cutoff:
            continue
        prev = by_cid.get(cid)
        if prev is None or _parse_ts(prev.get("ts", "")) < ts:  # type: ignore[operator]
            by_cid[cid] = entry
    return list(by_cid.values())


# ---------------------------------------------------------------------------
# Cost throttling. 7-day rolling cumulative grader_cost_est.
# ---------------------------------------------------------------------------
def cumulative_cost_7d(
    grader_log: str = ASK_GRADER_LOG,
    now: _dt.datetime | None = None,
) -> float:
    cutoff = (now or _dt.datetime.now(tz=_dt.timezone.utc)) - _dt.timedelta(days=7)
    total = 0.0
    for entry in _iter_jsonl(grader_log):
        ts = _parse_ts(entry.get("ts", ""))
        if ts is None or ts < cutoff:
            continue
        cost = entry.get("grader_cost_est", 0.0)
        try:
            total += float(cost)
        except (TypeError, ValueError):
            pass
    return total


def assert_within_budget(grader_log: str | None = None) -> None:
    grader_log = grader_log if grader_log is not None else ASK_GRADER_LOG
    spent = cumulative_cost_7d(grader_log)
    if spent > COST_CEILING_7D:
        raise ThrottleError(
            f"7-day grader spend ${spent:.2f} exceeds ceiling ${COST_CEILING_7D:.2f}"
        )


# ---------------------------------------------------------------------------
# Schema validation — strict. Raises SchemaError on any deviation.
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = ("category", "quality", "issues", "confidence", "reasoning")


def validate_verdict(verdict: Any) -> dict[str, Any]:
    if not isinstance(verdict, dict):
        raise SchemaError(f"verdict must be dict, got {type(verdict).__name__}")
    missing = [f for f in REQUIRED_FIELDS if f not in verdict]
    if missing:
        raise SchemaError(f"verdict missing required fields: {missing}")
    cat = verdict["category"]
    if cat not in ALLOWED_CATEGORY:
        raise SchemaError(f"category {cat!r} not in {sorted(ALLOWED_CATEGORY)}")
    qual = verdict["quality"]
    if qual not in ALLOWED_QUALITY:
        raise SchemaError(f"quality {qual!r} not in {sorted(ALLOWED_QUALITY)}")
    issues = verdict["issues"]
    if not isinstance(issues, list):
        raise SchemaError(f"issues must be list, got {type(issues).__name__}")
    bad_issues = [i for i in issues if i not in ALLOWED_ISSUES]
    if bad_issues:
        raise SchemaError(f"issues contains unknown enum values: {bad_issues}")
    conf = verdict["confidence"]
    try:
        conf_f = float(conf)
    except (TypeError, ValueError):
        raise SchemaError(f"confidence must be numeric, got {conf!r}")
    if not (0.0 <= conf_f <= 1.0):
        raise SchemaError(f"confidence out of [0,1]: {conf_f}")
    reasoning = verdict["reasoning"]
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise SchemaError("reasoning must be non-empty string")
    return {
        "category": cat,
        "quality": qual,
        "issues": list(issues),
        "confidence": conf_f,
        "reasoning": reasoning.strip(),
    }


# ---------------------------------------------------------------------------
# LiteLLM judge call. OpenAI-compatible chat completions endpoint.
# Schema-locked via tool_choice forcing the function call.
# ---------------------------------------------------------------------------
JUDGE_SYSTEM_PROMPT = """You are a strict, terse grader for a multi-model assistant routed via Telegram.

You will be given:
  - The user's query.
  - The agent's final response text.
  - Routing metadata (tier, model, latency, cost).

Score the response. Be calibrated: most routine answers are "good"; reserve
"excellent" for genuinely outstanding work and "poor" for clear failures.

Required output (via the `submit_verdict` tool ONLY, no prose):
  - category: one of {coding, research, status, ops, regulatory, satory,
    kazakhstan, telegram-meta, other}
  - quality: one of {excellent, good, acceptable, poor}
  - issues: subset of {incomplete, hallucination, tool_misuse, missed_context,
    wrong_routing, infra_flake, drift_artifact, persona_cosplay, no_done_protocol}.
    Empty list is allowed for clean answers.
  - confidence: float in [0, 1]
  - reasoning: 2-3 sentences. Concrete. No hedging.

Heuristics:
  - "no_done_protocol": claimed "done/complete/fixed/deployed/готово" without
    showing exact command + output + git rev-parse + counter-check.
  - "persona_cosplay": adopts a named-persona prompt (e.g. "I am Karpathy") not in
    the system message.
  - "drift_artifact": references a deprecated tool/path/concept that the substrate
    has superseded.
  - "wrong_routing": Tier-1 answered something that needed Tier-2 (research) or
    Tier-3 (high-judgment) escalation, or vice versa.
"""


JUDGE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "submit_verdict",
        "description": "Persist the grader verdict for one /ask turn.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": sorted(ALLOWED_CATEGORY),
                },
                "quality": {
                    "type": "string",
                    "enum": sorted(ALLOWED_QUALITY),
                },
                "issues": {
                    "type": "array",
                    "items": {"type": "string", "enum": sorted(ALLOWED_ISSUES)},
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "reasoning": {"type": "string"},
            },
            "required": list(REQUIRED_FIELDS),
            "additionalProperties": False,
        },
    },
}


def _build_judge_messages(turn: dict[str, Any]) -> list[dict[str, Any]]:
    routing = {
        k: turn.get(k)
        for k in ("tier", "model", "latency_ms", "cost_est", "decision")
        if turn.get(k) is not None
    }
    return [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "USER QUERY:\n"
                f"{turn.get('query_text') or turn.get('user_text') or '(missing)'}\n\n"
                "AGENT RESPONSE:\n"
                f"{turn.get('final_response_text') or '(missing)'}\n\n"
                f"ROUTING METADATA: {json.dumps(routing, ensure_ascii=False)}"
            ),
        },
    ]


def call_judge(
    turn: dict[str, Any],
    *,
    base_url: str = LITELLM_BASE_URL,
    model: str = LITELLM_MODEL,
    timeout: float = TIMEOUT_SECONDS,
    api_key: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Call LiteLLM. Returns (verdict_dict_unvalidated, usage_meta).
    Raises TransportError on network/auth/5xx, SchemaError on malformed
    tool call payload (caller will validate enum/range separately).
    """
    api_key = api_key or os.environ.get("LITELLM_MASTER_KEY")
    if not api_key:
        raise TransportError(
            "LITELLM_MASTER_KEY env var not set — judge call refused (no silent fallback)"
        )
    try:
        import urllib.request
        import urllib.error
    except ImportError:  # pragma: no cover — stdlib
        raise TransportError("urllib unavailable")

    body = {
        "model": model,
        "messages": _build_judge_messages(turn),
        "tools": [JUDGE_TOOL_SCHEMA],
        "tool_choice": {"type": "function", "function": {"name": "submit_verdict"}},
        "temperature": 0.0,
        "metadata": {"user_id": "grader", "schema": SCHEMA_VERSION},
    }
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise TransportError(f"LiteLLM HTTP {e.code}: {e.read()[:500]!r}")
    except urllib.error.URLError as e:
        raise TransportError(f"LiteLLM transport: {e.reason}")
    except (TimeoutError, json.JSONDecodeError) as e:
        raise TransportError(f"LiteLLM error: {e}")

    choices = payload.get("choices") or []
    if not choices:
        raise SchemaError("no choices in LiteLLM response")
    msg = choices[0].get("message") or {}
    tool_calls = msg.get("tool_calls") or []
    if not tool_calls:
        raise SchemaError(
            f"no tool_call in LiteLLM response (assistant said: {msg.get('content', '')[:200]!r})"
        )
    fn_args_raw = tool_calls[0].get("function", {}).get("arguments", "")
    if not fn_args_raw:
        raise SchemaError("tool_call had empty arguments")
    try:
        verdict_unvalidated = json.loads(fn_args_raw)
    except json.JSONDecodeError as e:
        raise SchemaError(f"tool_call arguments not JSON: {e}; raw={fn_args_raw[:300]!r}")

    usage = payload.get("usage") or {}
    return verdict_unvalidated, usage


def estimate_cost(usage: dict[str, Any]) -> float:
    pin = float(usage.get("prompt_tokens", 0) or 0)
    pout = float(usage.get("completion_tokens", 0) or 0)
    return (pin / 1_000_000) * COST_IN_PER_1M + (pout / 1_000_000) * COST_OUT_PER_1M


# ---------------------------------------------------------------------------
# Persistence. Append-only; one line per correlation_id. Idempotent caller
# is responsible (collect_pending dedups).
# ---------------------------------------------------------------------------
def persist_verdict(
    *,
    turn: dict[str, Any],
    verdict: dict[str, Any],
    usage: dict[str, Any],
    grader_log: str = ASK_GRADER_LOG,
    judge_model: str = LITELLM_MODEL,
    schema: str = SCHEMA_VERSION,
) -> dict[str, Any]:
    os.makedirs(os.path.dirname(grader_log), exist_ok=True)
    record = {
        "ts": _dt.datetime.now(tz=_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "schema": schema,
        "correlation_id": turn["correlation_id"],
        "tier": turn.get("tier"),
        "model": turn.get("model"),
        "judge_model": judge_model,
        "quality_v1": verdict["quality"],
        "category": verdict["category"],
        "issues": verdict["issues"],
        "confidence": verdict["confidence"],
        "reasoning": verdict["reasoning"],
        "judge_tokens_in": int(usage.get("prompt_tokens", 0) or 0),
        "judge_tokens_out": int(usage.get("completion_tokens", 0) or 0),
        "grader_cost_est": round(estimate_cost(usage), 6),
    }
    with open(grader_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def persist_failure(
    *,
    correlation_id: str,
    reason: str,
    grader_log: str = ASK_GRADER_LOG,
    schema: str = SCHEMA_VERSION,
) -> None:
    """Sentinel record per autoplan decision #17 — never silent failure."""
    os.makedirs(os.path.dirname(grader_log), exist_ok=True)
    record = {
        "ts": _dt.datetime.now(tz=_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "schema": schema,
        "type": "judge_failure",
        "correlation_id": correlation_id,
        "reason": reason,
        "grader_cost_est": 0.0,
    }
    with open(grader_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Driver — one tick.
# ---------------------------------------------------------------------------
def run_once(*, dry_run: bool = False) -> dict[str, Any]:
    """One cron tick. Returns counters dict.

    Reads module globals at call time so tests that monkeypatch
    `ASK_HIERARCHY_LOG` / `ASK_GRADER_LOG` are honored.
    """
    grader_log = ASK_GRADER_LOG
    hierarchy_log = ASK_HIERARCHY_LOG
    assert_within_budget(grader_log=grader_log)
    pending = collect_pending(
        hierarchy_log=hierarchy_log, grader_log=grader_log
    )
    counters = {
        "pending": len(pending),
        "skipped_sample": 0,
        "graded": 0,
        "failed": 0,
        "cost_added": 0.0,
    }
    for turn in pending:
        cid = turn["correlation_id"]
        try:
            sampled = should_sample(
                tier=turn.get("tier"),
                correlation_id=cid,
                query_text=turn.get("query_text") or turn.get("user_text"),
            )
        except GraderError as e:
            counters["failed"] += 1
            print(f"[ask_grader] sample fail cid={cid}: {e}", file=sys.stderr)
            if not dry_run:
                persist_failure(correlation_id=cid, reason=f"sample: {e}", grader_log=grader_log)
            continue
        if not sampled:
            counters["skipped_sample"] += 1
            continue
        if dry_run:
            counters["graded"] += 1
            continue
        try:
            raw_verdict, usage = call_judge(turn)
            verdict = validate_verdict(raw_verdict)
        except GraderError as e:
            counters["failed"] += 1
            print(f"[ask_grader] judge fail cid={cid}: {e}", file=sys.stderr)
            persist_failure(correlation_id=cid, reason=str(e), grader_log=grader_log)
            continue
        rec = persist_verdict(turn=turn, verdict=verdict, usage=usage, grader_log=grader_log)
        counters["graded"] += 1
        counters["cost_added"] += rec["grader_cost_est"]
    return counters


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="No LiteLLM calls; no writes")
    p.add_argument("--once", action="store_true", help="Single tick (default; cron mode)")
    args = p.parse_args()
    try:
        counters = run_once(dry_run=args.dry_run)
    except ThrottleError as e:
        print(f"[ask_grader] THROTTLED: {e}", file=sys.stderr)
        return 3
    except TransportError as e:
        print(f"[ask_grader] TRANSPORT: {e}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **counters}), file=sys.stdout)
    return 0 if counters["failed"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
