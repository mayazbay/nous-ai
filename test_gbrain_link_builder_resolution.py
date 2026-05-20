#!/usr/bin/env python3
"""Regression tests for gbrain_link_builder Obsidian alias resolution."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gbrain_link_builder as glb  # noqa: E402


SLUGS = {
    "pages/skills/session-operating-contract/skill",
    "pages/skills/musk-algorithm/skill",
    "pages/skills/_gbrain/brain-aware-invocation",
    "pages/tenants/satory/skills/tenant-isolation/skill",
    "pages/concepts/musk-algorithm",
}
INDEX = glb.build_index(SLUGS)


def expect(link, target):
    got = glb.resolve(link, INDEX, SLUGS)
    if got != target:
        raise AssertionError(f"{link!r}: expected {target!r}, got {got!r}")


def main():
    expect(
        "skills/session-operating-contract",
        "pages/skills/session-operating-contract/skill",
    )
    expect(
        "skills/session-operating-contract/skill",
        "pages/skills/session-operating-contract/skill",
    )
    expect(
        "skills/session-operating-contract/SKILL.md",
        "pages/skills/session-operating-contract/skill",
    )
    expect(
        "pages/skills/session-operating-contract/SKILL.md",
        "pages/skills/session-operating-contract/skill",
    )
    expect(
        "session-operating-contract",
        "pages/skills/session-operating-contract/skill",
    )
    expect(
        "skills/_gbrain/brain-aware-invocation",
        "pages/skills/_gbrain/brain-aware-invocation",
    )
    expect(
        "tenants/satory/skills/tenant-isolation/SKILL.md",
        "pages/tenants/satory/skills/tenant-isolation/skill",
    )
    expect("musk-algorithm", "pages/concepts/musk-algorithm")
    expect("skills/musk-algorithm", "pages/skills/musk-algorithm/skill")

    if glb.resolve("source-slug", INDEX, SLUGS) is not None:
        raise AssertionError("SKIP_TARGETS should still be skipped")
    if glb.resolve("diagram.png", INDEX, SLUGS) is not None:
        raise AssertionError("media targets should still be skipped")

    print("OK: gbrain_link_builder skill alias resolution")


if __name__ == "__main__":
    main()
