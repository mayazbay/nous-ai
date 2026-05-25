#!/usr/bin/env python3
"""
tools/tier_log.py — append one JSONL line per tier call.
Replaces Langfuse for v1 of multi-model CEO hierarchy
(SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22).

Usage from Python:
    from tier_log import append
    append(correlation_id="tg_123", tier=1, model="grok-reasoning",
           tokens_in=500, tokens_out=200, latency_ms=4200, cost_est=0.04,
           decision="delegate_to_tier_2")

Usage from CLI:
    python3 tier_log.py --correlation-id tg_123 --tier 1 --model grok-reasoning \
      --tokens-in 500 --tokens-out 200 --latency-ms 4200 --cost-est 0.04 \
      --decision delegate_to_tier_2
"""
import argparse
import datetime
import json
import os
import sys

LOG_FILE = os.path.expanduser("~/nous-agaas/logs/ask-hierarchy.jsonl")


def append(**fields):
    """Append one JSONL line. Creates log dir if missing. Always adds `ts`."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    entry = {"ts": datetime.datetime.utcnow().isoformat() + "Z"}
    entry.update(fields)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    p = argparse.ArgumentParser(description="Append one JSONL line to ask-hierarchy.jsonl")
    p.add_argument("--correlation-id", required=True, help="e.g. tg_12345 or test_abc")
    p.add_argument("--tier", type=int, required=True, choices=[1, 2, 3])
    p.add_argument("--model", required=True, help="e.g. grok-reasoning / opus / glm-5.1")
    p.add_argument("--tokens-in", type=int, default=0)
    p.add_argument("--tokens-out", type=int, default=0)
    p.add_argument("--latency-ms", type=int, default=0)
    p.add_argument("--cost-est", type=float, default=0.0)
    p.add_argument("--decision", default="", help="e.g. delegate_to_tier_2 / answer_directly / research_only / executed_ok / timeout")
    a = p.parse_args()

    append(
        correlation_id=a.correlation_id,
        tier=a.tier,
        model=a.model,
        tokens_in=a.tokens_in,
        tokens_out=a.tokens_out,
        latency_ms=a.latency_ms,
        cost_est=a.cost_est,
        decision=a.decision,
    )
    print(f"OK logged tier={a.tier} model={a.model} correlation_id={a.correlation_id}", file=sys.stderr)


if __name__ == "__main__":
    main()
