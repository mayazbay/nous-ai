#!/usr/bin/env python3
"""
test_gbrain_supersession_reranker.py — regression test for AP-61 Phase-2 reranker.

Locks the contract: superseded pages get score *= demotion, archived pages
get score *= 0.0, current pages unchanged. Verifies wikilink target extraction,
score sort order, and idempotency on re-rerank.

Run: python3 tools/test_gbrain_supersession_reranker.py
Exits 0 on all-pass.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Use a synthetic vault for fixtures, not the real one
_TEST_DIR = tempfile.mkdtemp(prefix="ap61_reranker_test_")
os.environ["VAULT"] = _TEST_DIR
os.environ["SUPERSESSION_DEMOTION"] = "0.3"
os.environ["SUPERSESSION_ARCHIVED"] = "0.0"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gbrain_supersession_reranker import rerank, page_supersession_state  # noqa: E402


def write_page(slug: str, frontmatter: dict[str, str], body: str = "test body") -> None:
    """Write a synthetic page to the test vault."""
    path = Path(_TEST_DIR) / "pages" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_lines = ["---"]
    for k, v in frontmatter.items():
        if "\n" in v:
            fm_lines.append(f"{k}:")
            for line in v.splitlines():
                fm_lines.append(f"  {line}" if not line.startswith(" ") else line)
        else:
            fm_lines.append(f"{k}: {v}")
    fm_lines.append("---")
    path.write_text("\n".join(fm_lines) + f"\n\n{body}\n", encoding="utf-8")


def assert_eq(actual, expected, label: str) -> bool:
    if actual != expected:
        print(f"  ❌ FAIL [{label}]: expected={expected!r}, actual={actual!r}", file=sys.stderr)
        return False
    return True


def main() -> int:
    print("=== AP-61 Phase-2 reranker regression test ===\n")
    failures = 0

    # === Fixtures ===
    write_page("current-page", {"type": "spec", "id": "current-page"})
    write_page("super-old", {
        "type": "lesson",
        "id": "super-old",
        "superseded_by": "\n  - \"[[current-page]]\"",
        "superseded_at": "2026-04-30",
        "superseded_reason": '"absorbed into current-page"',
    })
    write_page("dead-page", {
        "type": "spec",
        "id": "dead-page",
        "archived_at": "2026-04-30",
    })

    # === Test 1: state detection ===
    print("State detection:")
    s = page_supersession_state("current-page")
    failures += not assert_eq(s["superseded"], False, "current-page-not-superseded")
    failures += not assert_eq(s["archived"], False, "current-page-not-archived")
    if not (s["superseded"] or s["archived"]):
        print("  ✅ current-page detected as current")

    s = page_supersession_state("super-old")
    failures += not assert_eq(s["superseded"], True, "super-old-superseded")
    failures += not assert_eq(s["targets"], ["current-page"], "super-old-targets")
    if s["superseded"] and s["targets"] == ["current-page"]:
        print("  ✅ super-old detected as superseded with target")

    s = page_supersession_state("dead-page")
    failures += not assert_eq(s["archived"], True, "dead-page-archived")
    if s["archived"]:
        print("  ✅ dead-page detected as archived")

    s = page_supersession_state("nonexistent-slug-xyz")
    failures += not assert_eq(s["superseded"], False, "nonexistent-not-superseded")
    if not s["superseded"]:
        print("  ✅ nonexistent slug returns clean state")

    # === Test 2: rerank applies demotion correctly ===
    print("\nRerank demotion:")
    results = [
        {"slug": "current-page", "score": 0.9},
        {"slug": "super-old", "score": 0.95},
        {"slug": "dead-page", "score": 0.99},
    ]
    out = rerank(results)
    score_map = {r["slug"]: r["score"] for r in out}

    failures += not assert_eq(score_map["current-page"], 0.9, "current-unchanged")
    if score_map["current-page"] == 0.9:
        print("  ✅ current page score unchanged (0.9)")

    expected_demoted = round(0.95 * 0.3, 6)
    actual_demoted = round(score_map["super-old"], 6)
    failures += not assert_eq(actual_demoted, expected_demoted, "superseded-demoted")
    if actual_demoted == expected_demoted:
        print(f"  ✅ superseded page demoted (0.95 → {actual_demoted})")

    failures += not assert_eq(score_map["dead-page"], 0.0, "archived-zeroed")
    if score_map["dead-page"] == 0.0:
        print("  ✅ archived page zeroed (0.99 → 0.0)")

    # === Test 3: post-rerank sort order ===
    print("\nSort order:")
    expected_order = ["current-page", "super-old", "dead-page"]
    actual_order = [r["slug"] for r in out]
    failures += not assert_eq(actual_order, expected_order, "sort-by-score-desc")
    if actual_order == expected_order:
        print(f"  ✅ sorted by score descending: {actual_order}")

    # === Test 4: configurable demotion ===
    print("\nConfigurable demotion:")
    out2 = rerank(results, demotion=0.5)
    sup_score = next(r["score"] for r in out2 if r["slug"] == "super-old")
    failures += not assert_eq(round(sup_score, 6), round(0.95 * 0.5, 6), "demotion-0.5")
    if round(sup_score, 6) == round(0.95 * 0.5, 6):
        print(f"  ✅ demotion=0.5 applied (0.95 → {sup_score})")

    out3 = rerank(results, demotion=1.0)
    sup_score = next(r["score"] for r in out3 if r["slug"] == "super-old")
    failures += not assert_eq(round(sup_score, 6), 0.95, "demotion-1.0-noop")
    if round(sup_score, 6) == 0.95:
        print("  ✅ demotion=1.0 (no demotion) preserves score")

    # === Test 5: idempotency ===
    print("\nIdempotency:")
    out4 = rerank(out, demotion=1.0)  # rerank with no demotion shouldn't double-demote
    score_map4 = {r["slug"]: r["score"] for r in out4}
    sup_score = score_map4["super-old"]
    # Should still be 0.95 * 0.3 from first pass; not double-demoted
    failures += not assert_eq(round(sup_score, 6), round(0.95 * 0.3, 6), "idempotent-no-double-demote")
    if round(sup_score, 6) == round(0.95 * 0.3, 6):
        print("  ✅ re-rerank with demotion=1.0 doesn't double-demote previously-demoted")

    # === Test 6: empty input ===
    print("\nEdge cases:")
    out5 = rerank([])
    failures += not assert_eq(out5, [], "empty-input")
    if out5 == []:
        print("  ✅ empty input returns empty list")

    # === Test 7: input mutation guard ===
    original = [{"slug": "super-old", "score": 0.95}]
    rerank(original)
    failures += not assert_eq(original[0]["score"], 0.95, "no-input-mutation")
    if original[0]["score"] == 0.95:
        print("  ✅ rerank does not mutate input list")

    print(f"\n=== {failures} failures ===")
    return 1 if failures > 0 else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        # Cleanup test vault
        import shutil
        shutil.rmtree(_TEST_DIR, ignore_errors=True)
