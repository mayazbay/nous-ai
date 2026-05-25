#!/usr/bin/env python3
"""
Fail when run_task.log claims a concrete selected model but records a different
executed model.

Use against production with --after to ignore historical pre-fix rows:
  python3 tools/test_run_task_model_truth.py --log ~/nous-agaas/logs/run_task.log --after 2026-04-26T17:30

Use against synthetic fixtures in CI:
  python3 tools/test_run_task_model_truth.py --log /tmp/run_task_fixture.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

CONCRETE_MODELS = {
    "glm-5.1",
    "glm-4.5-flash",
    "grok-reasoning",
    "grok-code-fast",
    "opus",
    "sonnet",
    "sonnet-4-5-thinking",
    "haiku-4-5",
    "deepseek-v4-flash",
    "deepseek-v4-pro",
}


def iter_entries(path: Path):
    with path.open() as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_no, json.loads(line)
            except json.JSONDecodeError:
                yield line_no, {"_invalid_json": line[:120]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, help="Path to run_task.log JSONL")
    parser.add_argument("--after", default="", help="Only check entries whose ts string is >= this value")
    parser.add_argument("--tail", type=int, default=0, help="Only check the last N parsed entries")
    args = parser.parse_args()

    path = Path(args.log).expanduser()
    if not path.exists():
        print(f"SKIP: log not found: {path}")
        return 0

    entries = list(iter_entries(path))
    if args.tail > 0:
        entries = entries[-args.tail:]

    mismatches = []
    invalid = []
    checked = 0
    for line_no, entry in entries:
        if "_invalid_json" in entry:
            invalid.append((line_no, entry["_invalid_json"]))
            continue
        ts = str(entry.get("ts", ""))
        if args.after and ts < args.after:
            continue
        selected = entry.get("model_intent", entry.get("model_selected"))
        executed = entry.get("model")
        if selected not in CONCRETE_MODELS:
            continue
        checked += 1
        if executed and executed != selected:
            mismatches.append((line_no, ts, selected, executed, entry.get("execution_path")))

    if invalid:
        print(f"WARN: {len(invalid)} invalid JSON rows ignored")

    if mismatches:
        print(f"FAIL: {len(mismatches)} selected/executed model mismatches")
        for line_no, ts, selected, executed, path_name in mismatches[:20]:
            print(f"  line {line_no}: {ts} selected={selected} executed={executed} path={path_name}")
        return 1

    print(f"OK: checked {checked} concrete model selections; mismatches=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
