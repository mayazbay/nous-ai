"""Tests for restart_critical.sh parser self-test."""

from __future__ import annotations

import pathlib
import subprocess


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_restart_critical_self_test():
    result = subprocess.run(
        ["bash", str(REPO_ROOT / "tools" / "restart_critical.sh"), "--self-test"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "restart_critical_self_test=ok"
