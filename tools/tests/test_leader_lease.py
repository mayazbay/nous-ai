"""Tests for the file-backed active/passive leader lease."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import leader_lease


def test_active_leader_blocks_standby_until_expiry(tmp_path):
    lease = leader_lease.LeaderLease(tmp_path / "leader.lock", ttl_s=0.4)

    assert lease.try_acquire("air") is True
    assert lease.try_acquire("m5") is False

    time.sleep(0.45)

    assert lease.try_acquire("m5") is True
    record = lease.read()
    assert record["owner"] == "m5"


def test_refresh_extends_air_lease(tmp_path):
    lease = leader_lease.LeaderLease(tmp_path / "leader.lock", ttl_s=0.5)

    assert lease.try_acquire("air") is True
    first_expiry = lease.read()["expires_at"]
    time.sleep(0.1)
    assert lease.refresh("air") is True
    second_expiry = lease.read()["expires_at"]

    assert second_expiry > first_expiry
    assert lease.try_acquire("m5") is False


def test_killed_air_holder_allows_m5_takeover(tmp_path):
    lease_path = tmp_path / "leader.lock"
    air = subprocess.Popen(
        [
            "python3",
            str(TOOLS / "leader_lease.py"),
            "--lease-path",
            str(lease_path),
            "--ttl",
            "1",
            "hold",
            "--owner",
            "air",
            "--refresh-interval",
            "0.1",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert air.stdout.readline().strip() == "acquired=True owner=air"
        air.kill()
        air.wait(timeout=3)

        m5 = subprocess.run(
            [
                "python3",
                str(TOOLS / "leader_lease.py"),
                "--lease-path",
                str(lease_path),
                "--ttl",
                "1",
                "wait",
                "--owner",
                "m5",
                "--timeout",
                "3",
                "--poll",
                "0.1",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        if air.poll() is None:
            air.kill()

    assert m5.returncode == 0, m5.stdout + m5.stderr
    assert "acquired=True owner=m5" in m5.stdout
    record = json.loads(lease_path.read_text(encoding="utf-8"))
    assert record["owner"] == "m5"
