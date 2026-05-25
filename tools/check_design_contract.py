#!/usr/bin/env python3
"""Validate the repo-level DESIGN.md contract for Satory/Nous UI work."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DESIGN = REPO_ROOT / "DESIGN.md"

REQUIRED_SECTIONS = [
    "Overview",
    "Colors",
    "Typography",
    "Layout",
    "Elevation & Depth",
    "Shapes",
    "Components",
    "Do's and Don'ts",
]

REQUIRED_COLOR_TOKENS = {
    "primary",
    "secondary",
    "tertiary",
    "neutral",
    "surface",
    "surface-muted",
    "on-surface",
    "on-muted",
    "border",
    "success",
    "warning",
    "danger",
    "info",
}

REQUIRED_TEXT = [
    "python3 tools/check_design_contract.py",
    "@google/design.md lint DESIGN.md",
    "satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app",
    "index-BSiWURaO.js",
    "Operator-facing Satory copy defaults to Russian",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def extract_frontmatter(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        fail("DESIGN.md must start with YAML frontmatter")
    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        fail("YAML frontmatter closing --- not found")
    frontmatter = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1 :])
    return frontmatter, body


def extract_yaml_block(frontmatter: str, key: str) -> dict[str, str]:
    pattern = re.compile(rf"^{re.escape(key)}:\n(?P<body>(?:  .+\n?)*)", re.MULTILINE)
    match = pattern.search(frontmatter)
    if not match:
        fail(f"missing frontmatter block: {key}")
    values: dict[str, str] = {}
    for line in match.group("body").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            continue
        if ":" not in stripped:
            continue
        token, raw_value = stripped.split(":", 1)
        values[token.strip()] = raw_value.strip().strip('"')
    return values


def assert_sections(body: str) -> None:
    headings = re.findall(r"^## (.+)$", body, flags=re.MULTILINE)
    for section in REQUIRED_SECTIONS:
        if section not in headings:
            fail(f"missing required section: {section}")
        if headings.count(section) > 1:
            fail(f"duplicate required section: {section}")

    positions = [headings.index(section) for section in REQUIRED_SECTIONS]
    if positions != sorted(positions):
        fail("required sections are out of DESIGN.md spec order")


def assert_colors(frontmatter: str) -> None:
    colors = extract_yaml_block(frontmatter, "colors")
    missing = sorted(REQUIRED_COLOR_TOKENS - set(colors))
    if missing:
        fail(f"missing color tokens: {', '.join(missing)}")

    bad_hex = [
        f"{name}={value}"
        for name, value in colors.items()
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value)
    ]
    if bad_hex:
        fail(f"invalid SRGB hex colors: {', '.join(bad_hex)}")


def assert_typography(frontmatter: str) -> None:
    if re.search(r"letterSpacing:\s*-", frontmatter):
        fail("negative letterSpacing is banned")
    for token in ("headline-lg", "headline-md", "body-md", "body-sm", "label-sm"):
        if not re.search(rf"^  {re.escape(token)}:\s*$", frontmatter, flags=re.MULTILINE):
            fail(f"missing typography token: {token}")


def assert_rounded(frontmatter: str) -> None:
    rounded = extract_yaml_block(frontmatter, "rounded")
    for token in ("sm", "md", "lg"):
        value = rounded.get(token)
        if not value:
            fail(f"missing rounded token: {token}")
        match = re.fullmatch(r"(\d+)px", value)
        if not match:
            fail(f"rounded.{token} must be a px dimension")
        if int(match.group(1)) > 8:
            fail(f"rounded.{token} exceeds 8px card/control limit")


def assert_required_text(text: str) -> None:
    for needle in REQUIRED_TEXT:
        if needle not in text:
            fail(f"missing required contract text: {needle}")


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DESIGN
    if not path.exists():
        fail(f"{path} does not exist")
    text = path.read_text(encoding="utf-8")
    frontmatter, body = extract_frontmatter(text)

    if "version: alpha" not in frontmatter:
        fail("frontmatter must declare version: alpha")
    if "name: Satory / Nous Operator System" not in frontmatter:
        fail("frontmatter must declare the canonical Satory / Nous name")

    assert_sections(body)
    assert_colors(frontmatter)
    assert_typography(frontmatter)
    assert_rounded(frontmatter)
    assert_required_text(text)

    print(f"OK: {path.name} contract valid ({len(REQUIRED_SECTIONS)} sections, {len(REQUIRED_COLOR_TOKENS)} color tokens)")


if __name__ == "__main__":
    main()
