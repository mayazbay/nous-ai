"""Tests for the report-first library metadata audit CLI."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile


SCRIPT = pathlib.Path(__file__).parent / "library_metadata_audit.py"


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_audit(root: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--wiki", str(root), *args],
        capture_output=True,
        text=True,
    )


def test_json_format_is_report_only_by_default() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(root / "pages" / "entities" / "camera-node.md", "body only\n")

        result = run_audit(root, "--format", "json")
        payload = json.loads(result.stdout)

        assert result.returncode == 0
        assert payload["blocking_count"] == 3
        assert payload["source_tool"] == "library_quality_scan.py"


def test_strict_mode_fails_when_blocking_issues_exist() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(root / "pages" / "entities" / "camera-node.md", "body only\n")

        result = run_audit(root, "--format", "json", "--strict")

        assert result.returncode == 1


def test_markdown_format_lists_blocking_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        write(root / "pages" / "entities" / "camera-node.md", "body only\n")

        result = run_audit(root, "--format", "markdown")

        assert result.returncode == 0
        assert "# Library metadata audit" in result.stdout
        assert "blocking_count: 3" in result.stdout
        assert "pages/entities/camera-node.md" in result.stdout


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS: {name}")
    print("All library metadata audit tests passed.")
