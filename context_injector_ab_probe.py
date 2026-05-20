#!/usr/bin/env python3
"""
context_injector_ab_probe.py — GOD_PROMPT v1.0 Task 27 Step 2.

Compare v1 (legacy broad injection) vs v2 (progressive disclosure) on the
last N real task messages captured in run_task.log. Emits JSON summary
with median, p95, min, max, and delta ratios; G4 gate decision is
included (median v2 bytes < 8192).

Usage:
    python3 context_injector_ab_probe.py [--n 20] [--log PATH]
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, "/Users/madia/nous-agaas")
sys.path.insert(0, "/Users/madia/nous-agaas/tools")

from context_injector import get_context  # v1
from context_injector_v2 import get_context_v2  # v2

DEFAULT_LOG = Path("/Users/madia/nous-agaas/logs/run_task.log")
G4_THRESHOLD = 8192  # 8 KB


def load_recent_messages(log_path: Path, n: int) -> list[str]:
    """Read last N valid run_task.log entries; return unique non-empty messages."""
    if not log_path.exists():
        raise FileNotFoundError(f"log not found: {log_path}")
    msgs: list[str] = []
    seen: set[str] = set()
    # Read from tail for efficiency
    with log_path.open() as fh:
        lines = fh.readlines()
    for line in reversed(lines):
        if len(msgs) >= n:
            break
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = rec.get("message") or ""
        if not msg or msg in seen:
            continue
        seen.add(msg)
        msgs.append(msg)
    return list(reversed(msgs))


def measure(fn, task: str) -> int:
    """Invoke injector, return byte length of rendered context+task."""
    try:
        out = fn(task, inject=True)
    except Exception as exc:  # noqa: BLE001
        return -1  # mark failure
    if out is None:
        return -1
    return len(out.encode("utf-8"))


def summarize(values: list[int]) -> dict:
    ok = [v for v in values if v >= 0]
    if not ok:
        return {"n": 0, "median": None, "p95": None, "min": None, "max": None, "failures": len(values)}
    ok.sort()
    return {
        "n": len(ok),
        "median": statistics.median(ok),
        "p95": ok[min(len(ok) - 1, int(round(0.95 * (len(ok) - 1))))],
        "min": min(ok),
        "max": max(ok),
        "failures": len(values) - len(ok),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--json", action="store_true", help="emit JSON only")
    args = ap.parse_args()

    msgs = load_recent_messages(args.log, args.n)
    if not msgs:
        print(json.dumps({"error": "no messages found in log"}))
        return 2

    v1_bytes: list[int] = []
    v2_bytes: list[int] = []
    samples: list[dict] = []
    for m in msgs:
        b1 = measure(get_context, m)
        b2 = measure(get_context_v2, m)
        v1_bytes.append(b1)
        v2_bytes.append(b2)
        samples.append({
            "msg_preview": m[:80],
            "v1_bytes": b1,
            "v2_bytes": b2,
            "delta_ratio": (b2 / b1) if (b1 and b1 > 0) else None,
        })

    v1_stats = summarize(v1_bytes)
    v2_stats = summarize(v2_bytes)

    g4_pass = False
    if v2_stats["median"] is not None and v2_stats["median"] < G4_THRESHOLD:
        g4_pass = True

    result = {
        "probe_date": "2026-04-18",
        "n_messages": len(msgs),
        "v1_bytes": v1_stats,
        "v2_bytes": v2_stats,
        "g4_threshold_bytes": G4_THRESHOLD,
        "g4_pass": g4_pass,
        "reduction_pct": (
            round(100 * (1 - v2_stats["median"] / v1_stats["median"]), 1)
            if v1_stats["median"] and v2_stats["median"] is not None
            else None
        ),
        "samples": samples,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if g4_pass else 1


if __name__ == "__main__":
    sys.exit(main())
