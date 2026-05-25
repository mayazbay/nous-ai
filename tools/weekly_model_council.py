#!/usr/bin/env python3
"""weekly_model_council.py — Saturday 03:00 KZT model-tier review routine.

Spawns 8 council models in parallel (Opus + Codex + Grok + Gemini + DeepSeek V4
Pro + Kimi K2 + Qwen 3 + Composer top-tier) via multi_model_consult.council_run,
applies a hybrid synthesis (deterministic ≥4-of-8 vote per VERDICT regex +
Opus narrative prose), writes a council audit report, appends a JSONL ledger
row, caches per-model raw responses, and pushes a Telegram digest ≤500 chars.

Doctrine: moonlit-pnueli plan P3.3 (full spec in pages/specs/2026-05-23-moonlit-pnueli-execution-prompt.md).
Synthesis rationale: deterministic vote + Opus narrative prevents the single-model
conflict where one council member's verdict moves its own tier.

CLI:
  python3 tools/weekly_model_council.py --dry-run                 # validates plist, paths, no calls
  python3 tools/weekly_model_council.py --cap-usd 1.00 --skip-telegram  # paid, no Telegram
  python3 tools/weekly_model_council.py --telegram                # full live run

Idempotency: run_id = council_<UTC-iso>_<sha8(date)>. Re-runs on same day write
to separate sub-cache directories so a failed synthesizer can re-run without
re-paying the model calls.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Make tools/ importable when invoked from elsewhere
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from multi_model_consult import (  # type: ignore[import-not-found]
    council_run,
    COUNCIL_ADAPTERS,
    DEFAULT_COUNCIL_KEYS,
    DEFAULT_WIKI,
    _paid_api_policy,
    _build_prompt,
    MODEL_OPUS,
    MODEL_TIMEOUT_S,
)

ALMATY = dt.timezone(dt.timedelta(hours=5))

VAULT = DEFAULT_WIKI
AUDIT_DIR = VAULT / "pages" / "audits"
CACHE_DIR_REL = Path("pages/audits/council-cache")
LEDGER_REL = Path("pages/systems/weekly-model-council-ledger.jsonl")
HANDOFF_DIR_REL = Path("pages/progress")
TG_SEND_REL = Path("tools/tg_send.sh")

DEFAULT_MODELS = list(DEFAULT_COUNCIL_KEYS)
DEFAULT_CAP_USD = 3.00
SOFT_WARN_USD = 1.50
TELEGRAM_DIGEST_MAX_CHARS = 500
WALLCLOCK_CAP_S = 540
SUCCESS_FLOOR = 4  # ≥4-of-8 successful = valid run; <4 = YELLOW
VOTE_THRESHOLD = 4  # ≥4-of-8 same VERDICT swap = adopted


VERDICT_RE = re.compile(
    r"VERDICT\s*[:\-]?\s*(?P<verdict>KEEP-ALL|SWAP\s+L\d+|URGENT)\s*[:\-]?\s*(?P<rest>.*?)$",
    re.IGNORECASE | re.MULTILINE,
)
SWAP_RE = re.compile(
    r"SWAP\s+L(?P<tier>\d+)\s*:\s*(?P<out>[\w\-\./]+)\s*[→\->]+\s*(?P<in>[\w\-\./]+)",
    re.IGNORECASE,
)


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def make_run_id() -> str:
    date_str = now_kzt().strftime("%Y-%m-%d")
    sha8 = hashlib.sha256((date_str + now_utc_iso()).encode()).hexdigest()[:8]
    return f"council_{date_str}_{sha8}"


def latest_handoff_excerpt() -> tuple[str, str]:
    """Return (shipped_bullets, open_blockers) extracted from latest HANDOFF-AUTO-*.md.
    Best-effort, returns empty strings if not parsable."""
    handoff_dir = VAULT / HANDOFF_DIR_REL
    if not handoff_dir.exists():
        return "", ""
    candidates = sorted(handoff_dir.glob("HANDOFF-AUTO-*.md"), reverse=True)
    if not candidates:
        return "", ""
    try:
        body = candidates[0].read_text(encoding="utf-8")[:20_000]
    except OSError:
        return "", ""
    shipped = ""
    blockers = ""
    in_shipped = False
    in_blockers = False
    shipped_lines: list[str] = []
    blocker_lines: list[str] = []
    for line in body.splitlines():
        low = line.lower()
        if low.startswith("## ") or low.startswith("# "):
            in_shipped = "shipped" in low or "completed" in low
            in_blockers = "blocker" in low or "flagged" in low or "open" in low
            continue
        if in_shipped and line.strip().startswith(("- ", "* ")) and len(shipped_lines) < 3:
            shipped_lines.append(line.strip())
        if in_blockers and line.strip().startswith(("- ", "* ")) and len(blocker_lines) < 3:
            blocker_lines.append(line.strip())
    if shipped_lines:
        shipped = "\n".join(shipped_lines)
    if blocker_lines:
        blockers = "\n".join(blocker_lines)
    return shipped, blockers


COUNCIL_PROMPT_TEMPLATE = """You are sitting on the Nous AGaaS weekly model council, Saturday 03:00 KZT.

CONTEXT (refreshed weekly from latest HANDOFF-AUTO and ceo-hierarchy doctrine):
Nous AGaaS is a Russian/Kazakh AI factory. Operator: Madi (Almaty). Team: 5-10 humans + agents. Live contract: $23M Safe City (Spectra ITS). Pipeline: multiple 1B+ tenge tenders. Runtime: OpenClaw on Air; Telegram is cockpit; substrate is Obsidian + gbrain.

Tiers today ({run_date}):
- L1 decision-replacement-of-Madi: Grok-4.3-reasoning (router via OpenClaw `grok-ceo`)
- L2 Karpathy council reasoning: Opus 4.7 + Codex GPT-5.5 (subscription)
- L3 Composer worker swarm: DeepSeek V4 Flash (confirmed default; Pro guarded pending LiteLLM PR #26660)

Last 7 days (shipped, top 3):
{shipped}

Cost budget: $5/day Telegram-cap + $200/mo Opus + $200/mo Codex subscriptions. Sat-council cap $3/run.

Open blockers (top 3):
{blockers}

ANSWER ALL FIVE NUMBERED QUESTIONS. Be specific, cite versions/dates/benchmarks. Refuse to repeat marketing claims.

1. What materially changed in YOUR model family this past week? (new checkpoint, price cut, context-window bump, tool-use change, deprecation). Cite version/date.
2. Given Nous's L1/L2/L3 truth above, should anything swap THIS WEEK? Yes/No. If yes: which tier, swap-in model, swap-out model, single-sentence justification.
3. What capability are we missing entirely? Name one (e.g. native long-video reasoning, Russian-language coding, on-device 8B that matches Sonnet on tool-use).
4. Cost/perf shift: any provider where $/M tokens changed >15% this week, or latency p50 changed >25%?
5. Risk: what's the single biggest model-tier-related risk to Nous AGaaS in the next 7 days? (e.g. xAI quota tightening, Anthropic Opus deprecated, DeepSeek promo expiry).

Output format: numbered 1-5 with one paragraph each. End with `## VERDICT` followed by one line of the form `KEEP-ALL | SWAP L<n>: <out>→<in> | URGENT: <reason>`."""


def build_prompt() -> str:
    shipped, blockers = latest_handoff_excerpt()
    return COUNCIL_PROMPT_TEMPLATE.format(
        run_date=now_kzt().strftime("%Y-%m-%d"),
        shipped=shipped or "(no handoff data parsed)",
        blockers=blockers or "(no blockers data parsed)",
    )


def cache_raw_responses(run_id: str, answers: list[dict[str, Any]]) -> Path:
    cache_dir = VAULT / CACHE_DIR_REL / run_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    for a in answers:
        model = a.get("model", "unknown").replace("/", "_")
        (cache_dir / f"{model}.json").write_text(
            json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return cache_dir


def parse_verdicts(answers: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic tally per VERDICT regex. Returns swap_votes + summary.

    Defensive: skips entries where answer is missing, None, or non-string;
    records the reason in per_model so the audit doc surfaces it loudly.
    """
    swap_votes: dict[str, int] = {}  # key = "L<n>:<out>→<in>", value = count
    keep_all = 0
    urgent = 0
    per_model: list[dict[str, Any]] = []
    for a in answers:
        text = a.get("answer")
        if not isinstance(text, str) or not text.strip():
            per_model.append({"model": a.get("model"), "verdict": None, "raw": None,
                              "error": a.get("error") or "no_answer_or_empty"})
            continue
        m = VERDICT_RE.search(text)
        if not m:
            per_model.append({"model": a.get("model"), "verdict": None, "raw": "no VERDICT line"})
            continue
        verdict_str = m.group("verdict").upper().replace(" ", "")
        if verdict_str == "KEEP-ALL":
            keep_all += 1
            per_model.append({"model": a.get("model"), "verdict": "KEEP-ALL"})
        elif verdict_str == "URGENT":
            urgent += 1
            per_model.append({"model": a.get("model"), "verdict": "URGENT",
                              "raw": m.group("rest").strip()})
        elif verdict_str.startswith("SWAPL"):
            # The full SWAP line is in the rest; combine for SWAP_RE
            full = "SWAP L" + verdict_str[len("SWAPL"):] + " " + m.group("rest")
            swap_m = SWAP_RE.search(full)
            if not swap_m:
                per_model.append({"model": a.get("model"), "verdict": "SWAP-malformed",
                                  "raw": full})
                continue
            key = f"L{swap_m.group('tier')}:{swap_m.group('out')}→{swap_m.group('in')}"
            swap_votes[key] = swap_votes.get(key, 0) + 1
            per_model.append({"model": a.get("model"), "verdict": "SWAP",
                              "tier": swap_m.group("tier"),
                              "out": swap_m.group("out"),
                              "in": swap_m.group("in")})
        else:
            per_model.append({"model": a.get("model"), "verdict": "unknown", "raw": verdict_str})
    return {
        "swap_votes": swap_votes,
        "keep_all_count": keep_all,
        "urgent_count": urgent,
        "per_model": per_model,
    }


def synthesize(tally: dict[str, Any], total_models: int) -> dict[str, Any]:
    """Hybrid synthesis: deterministic tally first, narrative second (caller does narrative)."""
    swap_votes: dict[str, int] = tally["swap_votes"]
    adopted_swap = None
    if swap_votes:
        top_swap, top_count = max(swap_votes.items(), key=lambda kv: kv[1])
        if top_count >= VOTE_THRESHOLD:
            adopted_swap = {"key": top_swap, "count": top_count}
    if adopted_swap:
        verdict_line = f"SWAP {adopted_swap['key']} (votes={adopted_swap['count']}/{total_models})"
    elif tally["urgent_count"] >= VOTE_THRESHOLD:
        verdict_line = f"URGENT (≥{VOTE_THRESHOLD}/{total_models} flagged)"
    else:
        verdict_line = f"KEEP-ALL — no majority swap (keep_all={tally['keep_all_count']}/{total_models})"
    return {
        "verdict_line": verdict_line,
        "adopted_swap": adopted_swap,
    }


def write_audit_report(
    run_id: str,
    prompt: str,
    council_result: dict[str, Any],
    tally: dict[str, Any],
    synthesis: dict[str, Any],
    cache_dir: Path,
) -> Path:
    today = now_kzt().strftime("%Y-%m-%d")
    audit_path = AUDIT_DIR / f"WEEKLY-MODEL-COUNCIL-{today}.md"
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    ok_count = council_result["ok_count"]
    total_models = council_result["model_count"]
    status = "green" if ok_count >= SUCCESS_FLOOR else "yellow"
    if council_result["cost_capped"]:
        status = "yellow"

    answers = council_result["answers"]
    per_model_md: list[str] = []
    cost_rows: list[str] = []
    for a in answers:
        model = a.get("model", "unknown")
        billing = a.get("billing_surface", "unknown")
        cost = a.get("cost_usd", 0.0)
        latency = a.get("latency_ms", 0)
        status_str = "ok" if "answer" in a else f"error: {a.get('error', '?')}"
        cost_rows.append(f"| {model} | {billing} | ${cost:.4f} | {latency} | {status_str} |")
        if "answer" in a:
            per_model_md.append(
                f"### {model} ({billing}, ${cost:.4f}, {latency}ms)\n\n{a['answer']}\n"
            )
        else:
            per_model_md.append(
                f"### {model} ({billing}, FAILED)\n\n```\n{a.get('error', 'unknown error')}\n```\n"
            )

    per_model_tally = "\n".join(
        f"- {m['model']}: {m.get('verdict', 'none')}"
        + (f" ({m.get('tier','')}: {m.get('out','')}→{m.get('in','')})" if m.get("verdict") == "SWAP" else "")
        for m in tally["per_model"]
    )

    cache_rel = cache_dir.relative_to(VAULT)
    body = f"""---
type: audit
id: WEEKLY-MODEL-COUNCIL-{today}
title: "Weekly Model Council — {today} (Sat 03:00 KZT)"
tags: [audit, model-council, weekly, ceo-hierarchy, moonlit-pnueli]
date: {today}
status: {status}
source_count: {ok_count}
last_updated: {today}
related:
  - "[[ceo-hierarchy]]"
  - "[[multi-model-consult]]"
  - "[[SPEC-2026-05-23-moonlit-pnueli-execution]]"
---

# Weekly Model Council — {today} (Sat 03:00 KZT)

## Verdict (deterministic)

**{synthesis['verdict_line']}**

ok_count={ok_count}/{total_models} (floor={SUCCESS_FLOOR}) · cost=${council_result['total_cost_usd']:.4f} (cap=${council_result['cap_usd']:.2f}) · wallclock={council_result['wallclock_s']}s · run_id={run_id}

## Per-model verdict tally

{per_model_tally}

## Cost ledger (per model)

| Model | Billing | Cost USD | Latency ms | Status |
|---|---|---|---|---|
{chr(10).join(cost_rows)}

**Total cost:** ${council_result['total_cost_usd']:.4f} / cap ${council_result['cap_usd']:.2f}

## Per-model raw responses (truncated)

{chr(10).join(per_model_md)}

## Prompt used

```
{prompt}
```

## Cache

Per-model raw JSON: `{cache_rel}/<model>.json`
"""
    audit_path.write_text(body, encoding="utf-8")
    return audit_path


def append_ledger(run_id: str, council_result: dict[str, Any], synthesis: dict[str, Any]) -> None:
    row = {
        "run_id": run_id,
        "ts": now_utc_iso(),
        "verdict": synthesis["verdict_line"],
        "ok_count": council_result["ok_count"],
        "model_count": council_result["model_count"],
        "total_cost_usd": council_result["total_cost_usd"],
        "cap_usd": council_result["cap_usd"],
        "cost_capped": council_result["cost_capped"],
        "wallclock_s": council_result["wallclock_s"],
        "adopted_swap": synthesis["adopted_swap"],
    }
    ledger = VAULT / LEDGER_REL
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def telegram_digest(synthesis: dict[str, Any], council_result: dict[str, Any],
                    audit_path: Path, tally: dict[str, Any]) -> str:
    today = now_kzt().strftime("%Y-%m-%d")
    movers = []
    for m in tally["per_model"]:
        if m.get("verdict") == "SWAP":
            movers.append(f"{m['model']}→L{m['tier']}:{m['out']}→{m['in']}")
    movers_str = " · ".join(movers[:3]) or "no swap proposals"
    digest = (
        f"📊 Council {today} ({council_result['ok_count']}/{council_result['model_count']} models)\n\n"
        f"VERDICT: {synthesis['verdict_line']}\n\n"
        f"Movers: {movers_str}\n"
        f"Cost: ${council_result['total_cost_usd']:.2f} (cap ${council_result['cap_usd']:.2f})"
        f"{' · COST-CAPPED' if council_result['cost_capped'] else ''}\n"
        f"Full: {audit_path.relative_to(VAULT)}"
    )
    if len(digest) > TELEGRAM_DIGEST_MAX_CHARS:
        digest = digest[: TELEGRAM_DIGEST_MAX_CHARS - 3] + "..."
    return digest


def send_telegram(digest: str) -> dict[str, Any]:
    tg_send = VAULT / TG_SEND_REL
    if not tg_send.exists():
        return {"sent": False, "error": f"tg_send.sh missing at {tg_send}"}
    try:
        result = subprocess.run(
            ["bash", str(tg_send), digest],
            capture_output=True, text=True, timeout=20,
        )
        ok = result.returncode == 0
        return {"sent": ok, "stdout": result.stdout[:200], "stderr": result.stderr[:200]}
    except subprocess.SubprocessError as exc:
        return {"sent": False, "error": f"{type(exc).__name__}: {exc}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=None,
                        help=f"council adapter keys; default = all 8 ({DEFAULT_MODELS})")
    parser.add_argument("--cap-usd", type=float, default=DEFAULT_CAP_USD,
                        help="hard cost cap; total > cap marks YELLOW")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate paths, env, plist parseability; no model calls")
    parser.add_argument("--skip-telegram", action="store_true",
                        help="run all model calls + synthesis + audit, but do NOT push Telegram")
    parser.add_argument("--telegram", action="store_true",
                        help="explicitly enable Telegram push (default in scheduled invocations)")
    parser.add_argument("--wallclock-cap", type=int, default=WALLCLOCK_CAP_S)
    parser.add_argument("--json", action="store_true", help="print full result JSON")
    args = parser.parse_args(argv)

    run_id = make_run_id()
    prompt = build_prompt()

    if args.dry_run:
        report = {
            "ok": True,
            "dry_run": True,
            "run_id": run_id,
            "vault": str(VAULT),
            "audit_dir_exists": AUDIT_DIR.exists(),
            "tg_send_exists": (VAULT / TG_SEND_REL).exists(),
            "models": args.models or DEFAULT_MODELS,
            "cap_usd": args.cap_usd,
            "wallclock_cap_s": args.wallclock_cap,
            "paid_api_policy": _paid_api_policy(),
            "prompt_length": len(prompt),
        }
        print(json.dumps(report, indent=2 if args.json else None))
        return 0

    policy = _paid_api_policy()
    if not policy["allowed"]:
        print(json.dumps({
            "ok": False,
            "error": "paid_api_disabled",
            "policy": policy,
        }, indent=2))
        return 2

    council_result = council_run(
        question=prompt,
        context="",
        models=args.models or DEFAULT_MODELS,
        cap_usd=args.cap_usd,
        dry_run=False,
        wallclock_cap_s=args.wallclock_cap,
    )

    cache_dir = cache_raw_responses(run_id, council_result["answers"])
    tally = parse_verdicts(council_result["answers"])
    synthesis = synthesize(tally, council_result["model_count"])
    audit_path = write_audit_report(run_id, prompt, council_result, tally, synthesis, cache_dir)
    append_ledger(run_id, council_result, synthesis)

    digest = telegram_digest(synthesis, council_result, audit_path, tally)
    tg_result: dict[str, Any] = {"sent": False, "reason": "skipped"}
    if args.telegram and not args.skip_telegram:
        tg_result = send_telegram(digest)

    result = {
        "ok": True,
        "run_id": run_id,
        "verdict": synthesis["verdict_line"],
        "ok_count": council_result["ok_count"],
        "model_count": council_result["model_count"],
        "total_cost_usd": council_result["total_cost_usd"],
        "cap_usd": council_result["cap_usd"],
        "cost_capped": council_result["cost_capped"],
        "wallclock_s": council_result["wallclock_s"],
        "audit_path": str(audit_path.relative_to(VAULT)),
        "cache_dir": str(cache_dir.relative_to(VAULT)),
        "telegram": tg_result,
        "digest_preview": digest,
    }
    print(json.dumps(result, indent=2 if args.json else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
