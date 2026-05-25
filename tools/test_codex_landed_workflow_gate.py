#!/usr/bin/env python3
"""Guard the landed-commit Codex workflow from high-frequency paid triggers."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "codex-landed-commit-loop.yml"


def main() -> int:
    text = WORKFLOW.read_text(encoding="utf-8")
    required = [
        "workflow_dispatch:",
        "github.event_name == 'workflow_dispatch'",
    ]
    missing = [needle for needle in required if needle not in text]
    if missing:
        print(f"FAIL: missing landed-review gate fragments: {missing}")
        return 1
    forbidden = [
        "\n  push:",
        "CODEX_LANDED_REVIEW_ENABLED",
        "[codex-review]",
        "github.event.head_commit.message",
    ]
    present = [needle.strip() for needle in forbidden if needle in text]
    if present:
        print(f"FAIL: landed-review workflow must be manual-only; forbidden fragments: {present}")
        return 1
    if '"pages/**"' in text or "'pages/**'" in text:
        print("FAIL: landed-review workflow must not trigger on all pages/** vault writes")
        return 1
    print("PASS: Codex landed-commit workflow is manual-only for paid review")
    return 0


def test_codex_landed_workflow_is_manual_only() -> None:
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
