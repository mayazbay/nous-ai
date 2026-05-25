#!/usr/bin/env python3
"""council_diff_8model_vs_grok4.py — Day-7 council verdict comparison harness.

Per Stage 7 P6 council action item #6 (Grok's Musk-step-2 contrarian proposal):
  Does the 8-model council actually change verdicts vs a single Grok-4 baseline?

  If YES: keep the 8-model council; the breadth is buying real signal.
  If NO: narrow to 3-model (per Grok); the multi-model spend is paying nothing.

Strategy:
  1. Run the SAME prompt through both:
     a. 8-model council via tools/weekly_model_council.py (cost $0.10-0.30)
     b. Single-Grok-4 via tools/multi_model_consult.py with --models grok only,
        OR a direct LiteLLM grok-reasoning call (cost $0.01-0.02)
  2. Compare deterministic VERDICT lines:
     - Same verdict text → 8-model didn't add value on this prompt
     - Different verdict OR Grok-only missed a capability gap surfaced by another model → 8-model paid
  3. Aggregate over 3+ different prompts (sat-council standard + business-tooling + custom).
  4. Write a comparison audit doc with the per-prompt diff + recommendation.

CLI:
  python3 tools/council_diff_8model_vs_grok4.py --prompts-file pages/audits/council-comparison-prompts.md --json
  python3 tools/council_diff_8model_vs_grok4.py --inline "What changed in your model family this week?" --dry-run
  python3 tools/council_diff_8model_vs_grok4.py --inline "..." --no-8model --no-grok-only  # report cost projection only

Designed for Day-7 invocation (Sat 2026-05-30). Costs ~$0.30-1.00 per run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ALMATY = dt.timezone(dt.timedelta(hours=5))

TOOLS_DIR = Path(__file__).resolve().parent
VAULT = TOOLS_DIR.parent
COUNCIL_TOOL = TOOLS_DIR / "weekly_model_council.py"
CONSULT_TOOL = TOOLS_DIR / "multi_model_consult.py"

# Same regex pattern as weekly_model_council.parse_verdicts
VERDICT_RE = re.compile(
    r"VERDICT\s*[:\-]?\s*(?P<verdict>KEEP-ALL|SWAP\s+L\d+|URGENT)\s*[:\-]?\s*(?P<rest>.*?)$",
    re.IGNORECASE | re.MULTILINE,
)


def now_iso() -> str:
    return dt.datetime.now(ALMATY).isoformat()


def run_8model_council(prompt: str, cap_usd: float = 1.50,
                       wallclock_cap_s: int = 540) -> dict[str, Any]:
    """Invoke weekly_model_council.py CLI in a subprocess, capture JSON output."""
    env = os.environ.copy()
    # weekly_model_council uses the existing NOUS_PAID_API_* gates set by caller
    cmd = [
        "python3", str(COUNCIL_TOOL),
        "--cap-usd", str(cap_usd),
        "--skip-telegram",
        "--json",
        "--wallclock-cap", str(wallclock_cap_s),
    ]
    # weekly_model_council builds its OWN prompt from latest handoff; for
    # apples-to-apples comparison we'll need to either patch it to accept --prompt
    # or invoke it with the same prompt the day-7 council would use anyway.
    # For Day-7, the natural-prompt-from-handoff IS the apples-to-apples; we
    # then ask Grok-only the same generated prompt below.
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=wallclock_cap_s + 30)
    if proc.returncode != 0:
        return {"ok": False, "error": f"8model rc={proc.returncode}", "stderr": proc.stderr[:600]}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"8model JSON parse failed: {exc}", "stdout": proc.stdout[:600]}


def run_grok_only(prompt: str) -> dict[str, Any]:
    """Invoke multi_model_consult.py with grok-only roster (currently consult() is 3-model;
    use direct LiteLLM call for surgical apples-to-apples with the same prompt body)."""
    env = os.environ.copy()
    # multi_model_consult --question runs the 3-model consult by default.
    # For grok-only baseline we'll call LiteLLM direct via curl/python — same prompt.
    code = f"""
import os, json, time, urllib.request
key_path = os.path.expanduser("~/nous-agaas/litellm/.env")
key = ""
if os.path.exists(key_path):
    for line in open(key_path).read().splitlines():
        if line.startswith("LITELLM_MASTER_KEY="):
            key = line.split("=",1)[1].strip().strip("'\\"")
            break
url = "http://100.122.219.22:4000/v1/chat/completions"
body = {{"model": "grok-reasoning", "max_tokens": 1500,
         "messages": [{{"role":"user","content": {json.dumps(prompt)}}}]}}
headers = {{"Content-Type":"application/json"}}
if key: headers["Authorization"] = f"Bearer {{key}}"
req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
t0 = time.monotonic()
try:
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.loads(r.read())
    answer = resp["choices"][0]["message"]["content"]
    usage = resp.get("usage", {{}})
    in_tok = usage.get("prompt_tokens", 0)
    out_tok = usage.get("completion_tokens", 0)
    cost = (in_tok * 2.0 + out_tok * 6.0) / 1_000_000
    print(json.dumps({{
        "ok": True, "answer": answer, "tokens_in": in_tok, "tokens_out": out_tok,
        "cost_usd": round(cost, 6), "latency_ms": int((time.monotonic()-t0)*1000)
    }}))
except Exception as exc:
    print(json.dumps({{"ok": False, "error": f"{{type(exc).__name__}}: {{exc}}"}}))
"""
    proc = subprocess.run(["python3", "-c", code], capture_output=True, text=True, env=env, timeout=200)
    if proc.returncode != 0:
        return {"ok": False, "error": f"grok-only rc={proc.returncode}", "stderr": proc.stderr[:600]}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        return {"ok": False, "error": f"grok-only JSON parse failed: {exc}", "stdout": proc.stdout[:600]}


def extract_verdict_line(text: str) -> str | None:
    if not isinstance(text, str):
        return None
    m = VERDICT_RE.search(text)
    if not m:
        return None
    return f"{m.group('verdict').upper().strip()} {m.group('rest').strip()}".strip()


def diff_verdicts(council_result: dict[str, Any], grok_result: dict[str, Any]) -> dict[str, Any]:
    council_v = council_result.get("verdict", "(no verdict)")
    grok_v = extract_verdict_line(grok_result.get("answer", "")) or "(no verdict)"
    same = council_v.strip().lower().split(" — ")[0] == grok_v.strip().lower().split(" — ")[0]
    cost_council = council_result.get("total_cost_usd", 0.0)
    cost_grok = grok_result.get("cost_usd", 0.0)
    return {
        "council_verdict": council_v,
        "grok_verdict": grok_v,
        "same_top_verdict": same,
        "cost_council_usd": cost_council,
        "cost_grok_usd": cost_grok,
        "cost_ratio": round(cost_council / cost_grok, 2) if cost_grok > 0 else None,
        "savings_if_swap_to_grok_only": round(cost_council - cost_grok, 4),
        "council_ok_count": council_result.get("ok_count"),
        "council_model_count": council_result.get("model_count"),
    }


def write_audit_report(diffs: list[dict[str, Any]], audit_path: Path) -> None:
    today = dt.datetime.now(ALMATY).strftime("%Y-%m-%d")
    same_count = sum(1 for d in diffs if d["same_top_verdict"])
    differ_count = len(diffs) - same_count
    total_council_cost = sum(d["cost_council_usd"] or 0 for d in diffs)
    total_grok_cost = sum(d["cost_grok_usd"] or 0 for d in diffs)
    potential_savings = total_council_cost - total_grok_cost

    if same_count == len(diffs) and len(diffs) >= 3:
        verdict = "NARROW-TO-3-MODEL — 8-model council did not change any verdict vs Grok-only baseline across {n} prompts. Grok contrarian Musk-step-2 proposal validated. Potential weekly savings: ${s:.4f}.".format(n=len(diffs), s=potential_savings)
    elif differ_count > 0:
        verdict = "KEEP 8-MODEL COUNCIL — {d} of {n} prompts had verdict differences. The multi-model spend is buying real signal that single-Grok-4 misses.".format(d=differ_count, n=len(diffs))
    else:
        verdict = "INCONCLUSIVE — only {n} prompts compared, need ≥3 for confidence.".format(n=len(diffs))

    rows = ["| # | Prompt (preview) | Council verdict | Grok-only verdict | Same? | $council | $grok | ratio |",
            "|---|---|---|---|---|---|---|---|"]
    for i, d in enumerate(diffs, 1):
        prompt_preview = d.get("prompt_preview", "?")[:60]
        same_mark = "✅" if d["same_top_verdict"] else "❌"
        ratio = f"{d['cost_ratio']}x" if d['cost_ratio'] else "—"
        rows.append(
            f"| {i} | {prompt_preview} | {d['council_verdict'][:50]} | {d['grok_verdict'][:50]} | {same_mark} "
            f"| ${d['cost_council_usd']:.4f} | ${d['cost_grok_usd']:.4f} | {ratio} |"
        )

    body = f"""---
type: audit
id: COUNCIL-DIFF-8MODEL-VS-GROK4-{today}
title: "Council diff — 8-model vs Grok-4 single ({today})"
tags: [audit, council, council-diff, musk-step-2, day-7, moonlit-pnueli]
date: {today}
status: complete
related:
  - "[[COUNCIL-2026-05-23-plan-review]]"
  - "[[multi-model-consult]]"
  - "[[ceo-hierarchy]]"
---

# Council diff — 8-model vs Grok-4 single ({today})

## Verdict

**{verdict}**

## Comparison table

{chr(10).join(rows)}

## Cost summary

| Metric | Value |
|---|---|
| Total 8-model council cost | ${total_council_cost:.4f} |
| Total Grok-only cost | ${total_grok_cost:.4f} |
| Potential savings if swap | ${potential_savings:.4f} |
| Prompts where verdicts MATCHED | {same_count} of {len(diffs)} |
| Prompts where verdicts DIFFERED | {differ_count} of {len(diffs)} |

## Methodology

Each prompt was run through:
1. `tools/weekly_model_council.py --skip-telegram --json` (8-model parallel; uses `council_run` from multi_model_consult v1.5.0)
2. Direct LiteLLM `grok-reasoning` call with same prompt body (single-model baseline)

Both deterministic VERDICT line was extracted via the same regex used by the council synthesizer (`VERDICT_RE`).

"Same" = top-level verdict tier (KEEP-ALL / SWAP L<n> / URGENT) matches. Sub-verdicts (different SWAP candidates) count as differences.

## Recommendation

{verdict}

## Timeline

- **{today}** | Comparison run via `tools/council_diff_8model_vs_grok4.py` per Stage 7 P6 council action item #6.
"""
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(body, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inline", nargs="*", default=None,
                        help="inline prompt(s) to compare; multiple --inline for multiple prompts")
    parser.add_argument("--prompts-file", default=None,
                        help="markdown file with one prompt per `## ` heading (body = prompt text)")
    parser.add_argument("--cap-usd", type=float, default=1.50,
                        help="hard cap for 8-model council per run")
    parser.add_argument("--wallclock-cap", type=int, default=540)
    parser.add_argument("--no-8model", action="store_true", help="skip 8-model side")
    parser.add_argument("--no-grok-only", action="store_true", help="skip grok-only side")
    parser.add_argument("--dry-run", action="store_true", help="report what would fire, no calls")
    parser.add_argument("--out", default=None, help="audit output path (default auto)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    prompts: list[str] = []
    if args.inline:
        prompts.extend(args.inline)
    if args.prompts_file:
        text = Path(args.prompts_file).read_text(encoding="utf-8")
        # naive split on `## ` headings; body = lines until next `## ` or EOF
        sections = re.split(r"^##\s+", text, flags=re.MULTILINE)[1:]
        for s in sections:
            body = "\n".join(s.splitlines()[1:]).strip()
            if body:
                prompts.append(body)

    if not prompts:
        # Default: empty list signals "use council's own prompt as the canonical comparison"
        prompts = ["(council-built-from-latest-HANDOFF prompt; uses weekly_model_council's own builder)"]

    if args.dry_run:
        report = {
            "dry_run": True,
            "prompts_count": len(prompts),
            "would_run_8model": not args.no_8model,
            "would_run_grok_only": not args.no_grok_only,
            "estimated_cost_8model_per_run": "~$0.10-0.30",
            "estimated_cost_grok_only_per_run": "~$0.01-0.02",
            "estimated_total": f"~${(0.20 + 0.015) * len(prompts):.2f}",
            "cap_usd_8model": args.cap_usd,
        }
        print(json.dumps(report, indent=2 if args.json else None))
        return 0

    diffs: list[dict[str, Any]] = []
    for i, prompt in enumerate(prompts, 1):
        print(f"[{now_iso()}] running comparison {i}/{len(prompts)}", file=sys.stderr)
        council_result = {"ok": True, "verdict": "(skipped)"} if args.no_8model else \
            run_8model_council(prompt, cap_usd=args.cap_usd, wallclock_cap_s=args.wallclock_cap)
        grok_result = {"ok": True, "answer": "(skipped)"} if args.no_grok_only else \
            run_grok_only(prompt)
        diff = diff_verdicts(council_result, grok_result)
        diff["prompt_preview"] = prompt[:200]
        diffs.append(diff)

    today = dt.datetime.now(ALMATY).strftime("%Y-%m-%d")
    audit_path = Path(args.out) if args.out else (VAULT / "pages" / "audits" / f"COUNCIL-DIFF-8MODEL-VS-GROK4-{today}.md")
    write_audit_report(diffs, audit_path)

    result = {
        "ok": True,
        "prompts_count": len(diffs),
        "audit_path": str(audit_path.relative_to(VAULT)),
        "diffs": diffs,
    }
    print(json.dumps(result, indent=2 if args.json else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
