"""Tests for credentials_discovery.py secret lookup and drift detection."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import credentials_discovery


@pytest.fixture(autouse=True)
def _local_fixture_host(monkeypatch):
    monkeypatch.setenv("CREDENTIALS_DISCOVERY_LOCAL_HOST", "mac")


def _manifest(tmp_path: pathlib.Path) -> pathlib.Path:
    mac_env = tmp_path / "mac.env"
    mac_env.write_text("MAC_ONLY=mac-secret\n", encoding="utf-8")
    manifest = tmp_path / "secrets-manifest.md"
    manifest.write_text(
        f"""---
title: Secrets Manifest v2
---

# Secrets Manifest v2

## .env files inventory (audited 2026-05-05)

| host | path | service | notes |
|---|---|---|---|
| Mac | `{mac_env}` | dev | fixture |
| Air | `/Users/madia/nous-agaas/.env` | agent | fixture |
| VPS | `/root/nous-agaas/.env` | vps | fixture |

## Active credentials (v2 — full registry)

### Productivity / SaaS

| key | description | service | host(s) | rotation |
|---|---|---|---|---|
| TODOIST_API_TOKEN | Todoist API | todoist_sync, factory agent | Air, VPS | quarterly |
| MAC_ONLY | Local fixture | local dev | Mac | as-needed |
""",
        encoding="utf-8",
    )
    return manifest


def _patch_remote(monkeypatch, values: dict[tuple[str, str], str]) -> None:
    def fake_remote(host: str, path: str, timeout_s: int = 15) -> str:
        del timeout_s
        return values[(host, path)]

    monkeypatch.setattr(credentials_discovery, "_read_remote_file", fake_remote)


def test_find_outputs_metadata_without_secret_values(monkeypatch, tmp_path, capsys):
    manifest = _manifest(tmp_path)
    _patch_remote(
        monkeypatch,
        {
            ("air", "/Users/madia/nous-agaas/.env"): "TODOIST_API_TOKEN=air-secret\n",
            ("vps", "/root/nous-agaas/.env"): "TODOIST_API_TOKEN=vps-secret\n",
        },
    )

    code = credentials_discovery.main(["--manifest", str(manifest), "find", "TODOIST_API_TOKEN"])
    captured = capsys.readouterr()

    assert code == 0
    assert "air-secret" not in captured.out
    assert "vps-secret" not in captured.out
    assert "air-secret" not in captured.err
    payload = json.loads(captured.out)
    assert payload["key"] == "TODOIST_API_TOKEN"
    assert payload["services"] == ["todoist_sync", "factory agent"]
    assert {item["host"]: item["exists"] for item in payload["paths"]} == {"air": True, "vps": True}


def test_audit_reports_undocumented_keys_without_secret_values(monkeypatch, tmp_path, capsys):
    manifest = _manifest(tmp_path)
    _patch_remote(
        monkeypatch,
        {
            ("air", "/Users/madia/nous-agaas/.env"): "TODOIST_API_TOKEN=air-secret\nNEW_FAKE_KEY=do-not-leak\n",
            ("vps", "/root/nous-agaas/.env"): "TODOIST_API_TOKEN=vps-secret\n",
        },
    )

    code = credentials_discovery.main(["--manifest", str(manifest), "audit", "--no-staged"])
    captured = capsys.readouterr()

    assert code == 1
    assert "do-not-leak" not in captured.out
    assert "air-secret" not in captured.out
    assert "vps-secret" not in captured.out
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["undocumented_keys"] == ["NEW_FAKE_KEY"]
    assert payload["read_errors"] == []


def test_audit_strict_prints_exact_missing_key_list(monkeypatch, tmp_path, capsys):
    manifest = _manifest(tmp_path)
    _patch_remote(
        monkeypatch,
        {
            ("air", "/Users/madia/nous-agaas/.env"): "TODOIST_API_TOKEN=air-secret\nNEW_FAKE_KEY=do-not-leak\n",
            ("vps", "/root/nous-agaas/.env"): "TODOIST_API_TOKEN=vps-secret\n",
        },
    )

    code = credentials_discovery.main(["--manifest", str(manifest), "audit", "--strict", "--no-staged"])
    captured = capsys.readouterr()

    assert code == 1
    assert "credentials drift: undocumented env keys missing from pages/secrets-manifest.md:" in captured.err
    assert "  - NEW_FAKE_KEY" in captured.err
    assert "do-not-leak" not in captured.err


def test_source_prints_value_to_stdout_only(monkeypatch, tmp_path, capsys):
    manifest = _manifest(tmp_path)
    _patch_remote(
        monkeypatch,
        {
            ("air", "/Users/madia/nous-agaas/.env"): "TODOIST_API_TOKEN=air-secret\n",
            ("vps", "/root/nous-agaas/.env"): "TODOIST_API_TOKEN=vps-secret\n",
        },
    )

    code = credentials_discovery.main(["--manifest", str(manifest), "source", "TODOIST_API_TOKEN", "--host", "air"])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.out == "export TODOIST_API_TOKEN=air-secret\n"
    assert captured.err == ""


def test_manifest_v1_aborts_loudly(tmp_path, capsys):
    manifest = tmp_path / "secrets-manifest.md"
    manifest.write_text("# Secrets Manifest v1\n", encoding="utf-8")

    code = credentials_discovery.main(["--manifest", str(manifest), "find", "TODOIST_API_TOKEN"])
    captured = capsys.readouterr()

    assert code == 2
    assert captured.err.strip() == credentials_discovery.MANIFEST_ABORT


def test_mocked_ssh_reader_uses_remote_cat(monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stdout = "REMOTE_KEY=remote-secret\n"

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return Result()

    monkeypatch.setattr(credentials_discovery.subprocess, "run", fake_run)

    content = credentials_discovery._read_remote_file("air", "/Users/madia/nous-agaas/.env")

    assert content == "REMOTE_KEY=remote-secret\n"
    assert calls[0][0] == ["ssh", "air", "cat", "/Users/madia/nous-agaas/.env"]
    assert calls[0][1]["capture_output"] is True


def test_read_env_file_uses_local_path_when_running_on_air(monkeypatch, tmp_path):
    local_air_env = tmp_path / "air.env"
    local_air_env.write_text("AIR_LOCAL_KEY=present\n", encoding="utf-8")
    monkeypatch.setenv("CREDENTIALS_DISCOVERY_LOCAL_HOST", "air")

    def fail_remote(*_args, **_kwargs):
        raise AssertionError("should not ssh to Air from Air")

    monkeypatch.setattr(credentials_discovery, "_read_remote_file", fail_remote)

    assert credentials_discovery.read_env_file("air", str(local_air_env)) == {"AIR_LOCAL_KEY": None}


def test_cli_subprocess_find_does_not_print_secret(monkeypatch, tmp_path):
    manifest = _manifest(tmp_path)
    # Subprocess smoke uses only the Mac fixture so it avoids live SSH.
    result = subprocess.run(
        [
            sys.executable,
            str(TOOLS / "credentials_discovery.py"),
            "--manifest",
            str(manifest),
            "find",
            "MAC_ONLY",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "mac-secret" not in result.stdout
    assert "mac-secret" not in result.stderr
    payload = json.loads(result.stdout)
    assert payload["paths"] == [{"exists": True, "file": str(tmp_path / "mac.env"), "host": "mac"}]
