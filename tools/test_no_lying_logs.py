#!/usr/bin/env python3
"""§7.1 cross-cutting "no theatre" gate.

Detects the silent-embedding-failure pattern that surfaced 2026-05-20:
`gbrain sync` printed per-page `[gbrain] embedding failed for <slug>: OPENAI_API_KEY missing`
lines while the summary line still reported `N pages embedded` (N>0). Down-stream
consumers trusted the receipt; vector search was silently degraded for every page
synced since the key disappeared.

Rule: in a single sync run, the presence of ANY `embedding failed` line invalidates
any subsequent `pages embedded` summary that claims a positive count. Exit 1 on
violation; exit 0 on clean / no-summary / zero-count.

Usage:
    # Pipe a fresh single-cycle sync (recommended — what production wrappers do):
    ssh root@65.108.215.200 'gbrain sync --repo /root/nous-agaas/wiki' \
        | python3 tools/test_no_lying_logs.py

    # Tail a per-cycle tmp file (what gbrain_sync_wrapper.sh + autopilot-run.sh use):
    tools/test_no_lying_logs.py --input /tmp/gbrain-autopilot-cycle.XXX.log

    # Self-test (CI gate):
    tools/test_no_lying_logs.py --self-test

    # WARNING: do NOT use --input against a cumulative multi-cycle log like
    # /var/log/gbrain-sync.log. The gate carries "failure" state until the next
    # "N pages embedded" summary, so a failure-only cycle in cycle K followed by
    # a clean success in cycle K+1 would be reported as a lying summary. Always
    # gate per-cycle tmp files (what production wrappers do), not cumulative logs.

Wiring (gbrain-ops AP-99): the autopilot wrapper pipes its sync output through this
script; nonzero exit triggers `tools/tg_send.sh` and marks the run failed in the
sync-failures JSONL. Also runnable from CI / launchd watchdog.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass

# AP-100 P2-fix (codex council 2026-05-20): widen to match any "embedding failed"
# wording variant — original 'embedding failed for ' (literal trailing 'for ')
# slipped colon/dash separators and upstream wording drift. The new pattern uses
# a word boundary so it catches "embedding failed for X", "embedding failed: X",
# "embedding failed (X)", "Embedding Failed.", etc. The trailing \b prevents
# matching "failed-ish" prose like "embedding failedtests" if it ever appears.
EMBED_FAIL_RE = re.compile(r"embedding failed\b", re.IGNORECASE)
PAGES_EMBED_RE = re.compile(r"(?P<count>\d+)\s+pages?\s+embedded\b", re.IGNORECASE)


@dataclass
class Violation:
    summary_line_no: int
    summary_text: str
    summary_count: int
    failures_before: list[tuple[int, str]]


def scan(lines: list[str]) -> list[Violation]:
    """Return one Violation per lying summary line."""
    violations: list[Violation] = []
    failures: list[tuple[int, str]] = []
    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        if EMBED_FAIL_RE.search(line):
            failures.append((i, line))
            continue
        match = PAGES_EMBED_RE.search(line)
        if match:
            count = int(match.group("count"))
            if count > 0 and failures:
                violations.append(
                    Violation(
                        summary_line_no=i,
                        summary_text=line,
                        summary_count=count,
                        failures_before=list(failures),
                    )
                )
            failures = []
    return violations


def format_report(violations: list[Violation]) -> str:
    out = []
    for v in violations:
        out.append(
            f"LYING SUMMARY at line {v.summary_line_no}: "
            f"{v.summary_count} pages embedded reported AFTER {len(v.failures_before)} embedding failure(s)"
        )
        out.append(f"  summary: {v.summary_text}")
        for ln, text in v.failures_before:
            out.append(f"  failure (line {ln}): {text}")
    return "\n".join(out)


SELF_TEST_CLEAN = """\
[gbrain] sync start
Synced abc..def: 4 chunks created, 2 pages embedded
"""

SELF_TEST_LYING = """\
[gbrain] sync start
[gbrain] embedding failed for pages/skills/model-failover/skill (4 chunks): OPENAI_API_KEY missing
[gbrain] embedding failed for pages/skills/_gbrain/resolver (7 chunks): OPENAI_API_KEY missing
Synced 85f00f37..12e7c89b: 11 chunks created, 2 pages embedded
"""

SELF_TEST_ZERO = """\
[gbrain] sync start
[gbrain] embedding failed for foo/bar (1 chunks): OPENAI_API_KEY missing
Synced aaa..bbb: 0 chunks created, 0 pages embedded
"""

SELF_TEST_FAIL_ONLY = """\
[gbrain] sync start
[gbrain] embedding failed for foo/bar (1 chunks): OPENAI_API_KEY missing
"""

# AP-100 codex-council fixtures: variant separators the original regex missed.
SELF_TEST_LYING_COLON = """\
[gbrain] sync start
[gbrain] embedding failed: foo/bar — OPENAI_API_KEY missing
Synced a..b: 3 chunks created, 1 pages embedded
"""

SELF_TEST_LYING_NOFOR = """\
[gbrain] sync start
[gbrain] embedding failed pages/skills/x (2 chunks)
Synced a..b: 2 chunks created, 1 pages embedded
"""


def run_self_test() -> int:
    cases = [
        ("clean run", SELF_TEST_CLEAN, 0),
        ("lying summary", SELF_TEST_LYING, 1),
        ("zero-count summary after failures (not lying)", SELF_TEST_ZERO, 0),
        ("failures without summary (not lying yet)", SELF_TEST_FAIL_ONLY, 0),
        ("lying — colon separator (AP-100)", SELF_TEST_LYING_COLON, 1),
        ("lying — no 'for' separator (AP-100)", SELF_TEST_LYING_NOFOR, 1),
    ]
    rc = 0
    for name, fixture, expected_violations in cases:
        got = scan(fixture.splitlines())
        ok = (len(got) > 0) == (expected_violations > 0)
        marker = "ok" if ok else "FAIL"
        print(f"[{marker}] {name}: violations={len(got)} expected={expected_violations}")
        if not ok:
            rc = 1
            print(format_report(got))
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", "-i", help="Log file path (default stdin)")
    ap.add_argument("--self-test", action="store_true", help="Run synthetic fixtures and exit")
    args = ap.parse_args()

    if args.self_test:
        return run_self_test()

    if args.input:
        with open(args.input, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    else:
        lines = sys.stdin.readlines()

    violations = scan(lines)
    if not violations:
        return 0
    print(format_report(violations), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
