#!/usr/bin/env python3
"""
Build a 20-row calibration set for the doctrine-drift T2 LLM-judge.

Implements Decision T2 from pages/specs/2026-04-30-doctrine-drift-detector-spec.md:
"REQUIRED — 20-row Madi-rated calibration spreadsheet before any LLM-judge runs.
Judge accuracy >=85% on calibration set, OR kill the LLM-judge pass entirely."

Reads:  ~/nous-agaas/logs/ask-hierarchy.jsonl (Madi's local turn telemetry)
Writes: ~/nous-agaas/doctrine-drift-calibration-2026-04-30.csv (Madi fills in)

Privacy: redacts user_query text via the doctrine-drift D6/Eng F7 allowlist pattern
(Kazakh plate, IIN 12-digit, phone, email regexes). Never writes raw user
content to disk; only `correlation_id`, `category` classification, `latency_ms`,
`tier`, `cost_usd`, `final_response_text_first_120chars` (hash-truncated).

Usage:
    python3 tools/build_doctrine_drift_calibration_set.py
    # output: ~/nous-agaas/doctrine-drift-calibration-2026-04-30.csv

Sampling: deterministic via hash(correlation_id) % 100 < SAMPLE_PCT, so re-running
produces the same 20 turns. Configurable via --sample-pct.

After Madi fills in `your_rating` column (excellent|good|acceptable|poor) and
`your_notes` (1-line freeform), the doctrine-drift Phase-0 dry-run script consumes
this CSV as ground truth. >=85% judge-Madi agreement promotes Phase-1 cron;
<85% kills the LLM-judge pass per Decision T2.

Reproducibility: snapshot SHA recorded in CSV footer.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Privacy-redaction allowlist (matches doctrine-drift Eng F7 + agent-quality AP-22)
PII_PATTERNS = [
    re.compile(r"\b\d{12}\b"),                    # Kazakh IIN (12-digit)
    re.compile(r"\b\d{3}[A-Z]{2,3}\d{2}\b"),      # Kazakh license plate
    re.compile(r"\b\+?\d[\d\s\-()]{8,}\d\b"),     # Phone
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),  # Email
    re.compile(r"\b\d{16,19}\b"),                 # CC numbers
]

REDACT = "[REDACTED]"


def redact_pii(text: str) -> str:
    """Apply allowlist redaction to free-form text before persisting."""
    if not text:
        return ""
    out = text
    for pat in PII_PATTERNS:
        out = pat.sub(REDACT, out)
    return out


def truncate_120(text: str) -> str:
    """First 120 chars, with hash suffix so the operator can correlate without seeing full content."""
    if not text:
        return ""
    safe = redact_pii(text)
    if len(safe) <= 120:
        return safe
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return safe[:120] + f"...[hash:{h}]"


def deterministic_sample(correlation_id: str, sample_pct: int) -> bool:
    """Sample `sample_pct`% of correlation_ids deterministically.
    Same correlation_id -> same sampled/not-sampled across runs.
    """
    h = int(hashlib.sha256(correlation_id.encode("utf-8")).hexdigest(), 16)
    return (h % 100) < sample_pct


def load_jsonl(path: Path) -> list[dict]:
    """Read JSONL, skip malformed lines."""
    rows = []
    if not path.exists():
        sys.stderr.write(f"ERROR: {path} not found. Has /ask traffic landed yet?\n")
        sys.exit(2)
    with path.open() as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.stderr.write(f"WARN: skipping malformed line {ln}: {e}\n")
    return rows


def filter_recent(rows: list[dict], days: int = 30) -> list[dict]:
    """Keep turns within last `days` days (per record's `ts` ISO field)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for r in rows:
        ts_str = r.get("ts") or r.get("timestamp") or ""
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts >= cutoff:
                out.append(r)
        except (ValueError, AttributeError):
            continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default=str(Path.home() / "nous-agaas/logs/ask-hierarchy.jsonl"))
    ap.add_argument("--output", default=str(Path.home() / "nous-agaas/doctrine-drift-calibration-2026-04-30.csv"))
    ap.add_argument("--sample-pct", type=int, default=20, help="%% of recent turns to sample (default 20%%; ~5x oversample for 20-row target)")
    ap.add_argument("--target-rows", type=int, default=20, help="Target row count in output CSV")
    ap.add_argument("--days", type=int, default=30, help="Window of recent turns to consider")
    args = ap.parse_args()

    in_path = Path(args.input).expanduser()
    out_path = Path(args.output).expanduser()

    print(f"reading {in_path} ...", file=sys.stderr)
    rows = load_jsonl(in_path)
    print(f"  total rows: {len(rows)}", file=sys.stderr)

    rows = filter_recent(rows, days=args.days)
    print(f"  rows in last {args.days}d: {len(rows)}", file=sys.stderr)

    # Deterministic sample
    sampled = [r for r in rows if deterministic_sample(r.get("correlation_id", ""), args.sample_pct)]
    print(f"  sampled at {args.sample_pct}%: {len(sampled)}", file=sys.stderr)

    # Filter for turns that have a final response text (the thing being graded)
    sampled = [r for r in sampled if (r.get("final_response_text") or r.get("response_text") or r.get("response"))]
    print(f"  with final_response_text: {len(sampled)}", file=sys.stderr)

    # Take first N (deterministic order via correlation_id sort)
    sampled.sort(key=lambda r: r.get("correlation_id", ""))
    final = sampled[: args.target_rows]
    print(f"  final calibration rows: {len(final)}", file=sys.stderr)

    if len(final) < args.target_rows:
        print(
            f"WARN: only {len(final)} rows available; target was {args.target_rows}.\n"
            f"  Either lower --sample-pct, widen --days, or wait for more /ask traffic.",
            file=sys.stderr,
        )

    # Repo HEAD for reproducibility
    head = ""
    try:
        import subprocess
        head = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent,
        ).decode().strip()
    except Exception:
        head = "unknown"

    # Write CSV
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "correlation_id",
            "tier",
            "model",
            "latency_ms",
            "cost_usd",
            "category_classification",
            "user_query_redacted_120",
            "final_response_redacted_120",
            "your_rating",         # MADI FILLS: excellent | good | acceptable | poor
            "your_notes",          # MADI FILLS: 1-line freeform reasoning
        ])
        for r in final:
            w.writerow([
                r.get("correlation_id", ""),
                r.get("tier", ""),
                r.get("model", ""),
                r.get("latency_ms", ""),
                r.get("cost_usd", ""),
                r.get("classification", "") or r.get("category", ""),
                truncate_120(r.get("user_query", "") or r.get("query", "")),
                truncate_120(r.get("final_response_text", "") or r.get("response_text", "") or r.get("response", "")),
                "",  # your_rating — MADI FILLS
                "",  # your_notes — MADI FILLS
            ])
        # Reproducibility footer
        w.writerow([])
        w.writerow([f"# Generated: {datetime.now(timezone.utc).isoformat()} | repo HEAD: {head} | sample_pct: {args.sample_pct} | days: {args.days}"])

    print(f"\n✅ wrote {len(final)} rows to {out_path}", file=sys.stderr)
    print(f"\nNext step: open {out_path} in Numbers/Excel, fill in `your_rating` and `your_notes` columns,", file=sys.stderr)
    print(f"then notify the doctrine-drift Phase-0 dry-run lane to consume it as ground truth.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
