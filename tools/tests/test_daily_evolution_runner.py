"""Tests for daily_evolution_runner.py + OpenClaw adapter.

Run: python3 -m pytest tools/tests/test_daily_evolution_runner.py -q

All tests use fixture-mode / mocks — no SSH calls, no live upgrades,
no git operations against the real repo.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import daily_evolution_runner as runner
from daily_evolution_adapters.openclaw import OpenClawAdapter, parse_version_from_image


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wiki(tmp_path: Path) -> Path:
    """Create minimal wiki directory structure under tmp_path."""
    (tmp_path / "pages" / "systems").mkdir(parents=True)
    (tmp_path / "pages" / "audits").mkdir(parents=True)
    (tmp_path / "tools" / "daily_evolution_adapters").mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# test_snapshot_writes_expected_json_shape
# ---------------------------------------------------------------------------

def test_snapshot_writes_expected_json_shape(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    result = runner.snapshot(wiki, fixture_mode=True)

    assert result.status == "ok"
    snap_path = wiki / runner.DEFAULT_SNAPSHOT_REL
    assert snap_path.exists(), f"snapshot file not written at {snap_path}"

    data = json.loads(snap_path.read_text())
    assert "timestamp" in data
    assert "git_heads" in data
    assert set(data["git_heads"].keys()) == {"mac", "air", "vps", "github"}
    assert "launchd_exit_statuses" in data
    assert "service_version_shas" in data
    assert data.get("fixture") is True


def test_snapshot_dry_run_writes_nothing(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    result = runner.snapshot(wiki, fixture_mode=True, dry_run=True)

    assert result.status == "ok"
    assert "dry_run would write" in result.detail
    snap_path = wiki / runner.DEFAULT_SNAPSHOT_REL
    assert not snap_path.exists(), "dry-run snapshot must not write the snapshot file"


# ---------------------------------------------------------------------------
# test_pull_substrate_aborts_on_real_conflict
# ---------------------------------------------------------------------------

def test_pull_substrate_aborts_on_real_conflict(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)

    mock_result = {
        "ok": False,
        "stdout": "Auto-merging pages/index.md\nCONFLICT (content): Merge conflict in pages/index.md",
        "stderr": "",
        "returncode": 1,
    }
    with patch("daily_evolution_runner.run_cmd", return_value=mock_result):
        result = runner.pull_substrate(wiki, dry_run=False, skip_pull=False, fixture_mode=False)

    assert result.status == "aborted"
    # Decision stub file must be written
    decision_files = list((wiki / "pages" / "audits").glob("DAILY-EVOLUTION-NEEDS-DECISION-*.md"))
    assert len(decision_files) == 1, f"expected 1 decision file, got {decision_files}"
    content = decision_files[0].read_text()
    assert "needs_decision" in content
    assert "Merge Conflict" in content


# ---------------------------------------------------------------------------
# test_detect_upgrades_caps_at_one_per_cycle
# ---------------------------------------------------------------------------

def test_detect_upgrades_caps_at_one_per_cycle(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    state: dict = {"last_run_at": None, "last_rollback_skips": [], "version_manifest": {}}

    # Patch _load_adapters to return 3 fake adapters, all with upgrades available
    class FakeAdapter:
        def __init__(self, adapter_name: str):
            self._name = adapter_name

        @property
        def name(self) -> str:
            return self._name

        def probe_current_version(self):
            return "1.0.0"

        def probe_latest_version(self):
            return "2.0.0"

    fake_adapters = [FakeAdapter(f"fake_{i}") for i in range(3)]

    with patch("daily_evolution_runner._load_adapters", return_value=fake_adapters):
        phase_result, upgrades = runner.detect_upgrades(state, wiki, fixture_mode=False)

    assert phase_result.status == "ok"
    assert len(upgrades) == 1, f"expected 1 upgrade (cap), got {len(upgrades)}"
    assert upgrades[0].adapter_name == "fake_0"


# ---------------------------------------------------------------------------
# test_digest_writes_markdown_with_phase_table
# ---------------------------------------------------------------------------

def test_digest_writes_markdown_with_phase_table(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)

    phases = [
        runner.PhaseResult(phase="snapshot", status="ok", detail="written"),
        runner.PhaseResult(phase="pull_substrate", status="skipped", detail="fixture"),
        runner.PhaseResult(phase="detect_upgrades", status="ok", detail="0 candidates"),
    ]
    upgrades = [
        runner.Upgrade(adapter_name="openclaw", current_version="2026.4.14", latest_version="2026.5.18"),
    ]

    result = runner.digest(phases, wiki, upgrades)
    assert result.status == "ok"

    date_str = runner.today_str()
    audit_path = wiki / "pages" / "audits" / f"DAILY-EVOLUTION-{date_str}.md"
    assert audit_path.exists()

    content = audit_path.read_text()
    assert "| snapshot | ok |" in content
    assert "| pull_substrate | skipped |" in content
    assert "openclaw" in content
    assert "2026.4.14" in content
    assert "## Phase results" in content


# ---------------------------------------------------------------------------
# test_state_file_read_write_roundtrip
# ---------------------------------------------------------------------------

def test_state_file_read_write_roundtrip(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    state_path = wiki / "pages" / "systems" / "daily-evolution-state.json"

    # Initial load — file doesn't exist yet
    state = runner.load_state(state_path)
    assert state["last_run_at"] is None
    assert state["last_rollback_skips"] == []
    assert state["version_manifest"] == {}

    # Mutate and write
    state["version_manifest"]["openclaw"] = "2026.4.14"
    runner.write_state(state_path, state)

    assert state_path.exists()
    loaded = json.loads(state_path.read_text())
    assert loaded["version_manifest"]["openclaw"] == "2026.4.14"
    assert loaded["last_run_at"] is not None  # written by write_state


# ---------------------------------------------------------------------------
# test_openclaw_adapter_probe_current_version_parses_image_tag
# ---------------------------------------------------------------------------

def test_openclaw_adapter_probe_current_version_parses_image_tag() -> None:
    adapter = OpenClawAdapter()

    # Mock SSH returning a well-formed image ref
    mock_ssh = MagicMock(return_value={
        "ok": True,
        "stdout": "ghcr.io/openclaw/openclaw:2026.4.14",
        "stderr": "",
        "returncode": 0,
    })
    with patch("daily_evolution_adapters.openclaw._ssh_run", mock_ssh):
        version = adapter.probe_current_version()

    assert version == "2026.4.14"
    assert ".Config.Image" in mock_ssh.call_args.args[1]


def test_openclaw_adapter_probe_current_version_falls_back_after_digest() -> None:
    adapter = OpenClawAdapter()

    mock_ssh = MagicMock(side_effect=[
        {
            "ok": True,
            "stdout": "sha256:7ea070b04d1e70811fe8ba15feaad5890b1646021b24e00f4795bd4587a594ed",
            "stderr": "",
            "returncode": 0,
        },
        {
            "ok": True,
            "stdout": "ghcr.io/openclaw/openclaw:2026.4.14",
            "stderr": "",
            "returncode": 0,
        },
    ])
    with patch("daily_evolution_adapters.openclaw._ssh_run", mock_ssh):
        version = adapter.probe_current_version()

    assert version == "2026.4.14"
    assert ".Config.Image" in mock_ssh.call_args_list[0].args[1]
    assert ".Image" in mock_ssh.call_args_list[1].args[1]


def test_openclaw_adapter_probe_current_version_uses_local_docker_before_ssh() -> None:
    adapter = OpenClawAdapter()

    mock_local = MagicMock(return_value={
        "ok": True,
        "stdout": "ghcr.io/openclaw/openclaw:2026.4.14",
        "stderr": "",
        "returncode": 0,
    })
    with (
        patch("daily_evolution_adapters.openclaw._local_run", mock_local),
        patch("daily_evolution_adapters.openclaw.subprocess.run") as mock_subprocess_run,
    ):
        version = adapter.probe_current_version()

    assert version == "2026.4.14"
    assert ".Config.Image" in mock_local.call_args.args[0]
    mock_subprocess_run.assert_not_called()


def test_openclaw_adapter_probe_current_version_handles_sha_digest() -> None:
    adapter = OpenClawAdapter()

    mock_ssh = MagicMock(return_value={
        "ok": True,
        "stdout": "ghcr.io/openclaw/openclaw@sha256:abc123def456",
        "stderr": "",
        "returncode": 0,
    })
    with patch("daily_evolution_adapters.openclaw._ssh_run", mock_ssh):
        version = adapter.probe_current_version()

    assert version is None


def test_openclaw_adapter_probe_uses_config_image_not_resolved_image_id() -> None:
    """Regression for Codex 67610676 bug: probe must use .Config.Image (tagged
    ref like 'ghcr.io/openclaw/openclaw:2026.4.14'), not .Image (resolved
    sha256 hash like 'sha256:abc...'). With the old .Image probe, version
    parsing always returned None and detect_upgrades silently skipped
    OpenClaw — exactly the symptom Madi flagged."""
    adapter = OpenClawAdapter()

    captured_cmd: dict[str, str] = {}

    def fake_ssh(host: str, cmd: str, timeout: int = 30) -> dict:
        captured_cmd["cmd"] = cmd
        # Simulate what `.Config.Image` would return on the live container
        return {
            "ok": True,
            "stdout": "ghcr.io/openclaw/openclaw:2026.4.14",
            "stderr": "",
            "returncode": 0,
        }

    with patch("daily_evolution_adapters.openclaw._ssh_run", side_effect=fake_ssh):
        version = adapter.probe_current_version()

    assert version == "2026.4.14"
    assert ".Config.Image" in captured_cmd["cmd"], (
        f"probe must use .Config.Image (got: {captured_cmd['cmd']!r}); "
        f"bare .Image returns sha256 hash, breaks version parsing"
    )


def test_openclaw_adapter_probe_current_version_handles_ssh_failure() -> None:
    adapter = OpenClawAdapter()

    mock_ssh = MagicMock(return_value={
        "ok": False,
        "stdout": "",
        "stderr": "ssh: connect to host air port 22: Connection refused",
        "returncode": 255,
    })
    with patch("daily_evolution_adapters.openclaw._ssh_run", mock_ssh):
        version = adapter.probe_current_version()

    assert version is None


def test_parse_version_from_image_variants() -> None:
    assert parse_version_from_image("ghcr.io/openclaw/openclaw:2026.4.14") == "2026.4.14"
    assert parse_version_from_image("ghcr.io/openclaw/openclaw:latest") == "latest"
    assert parse_version_from_image("sha256:abcdef") is None
    assert parse_version_from_image("ghcr.io/openclaw/openclaw@sha256:abc") is None
    assert parse_version_from_image("") is None
    assert parse_version_from_image("openclaw:2026.5.18") == "2026.5.18"


# ---------------------------------------------------------------------------
# test_idempotent_same_day_rerun
# ---------------------------------------------------------------------------

def test_idempotent_same_day_rerun(tmp_path: Path) -> None:
    """Running main() twice on the same day: both should succeed (idempotent)."""
    wiki = _make_wiki(tmp_path)
    state_path = wiki / "pages" / "systems" / "daily-evolution-state.json"

    common_args = [
        "--fixture-mode",
        "--wiki", str(wiki),
        "--state-file", str(state_path),
    ]

    # First run
    rc1 = runner.main(common_args)
    assert rc1 == 0, f"first run failed with rc={rc1}"
    assert state_path.exists()

    state_after_first = json.loads(state_path.read_text())
    last_run_1 = state_after_first["last_run_at"]
    assert last_run_1 is not None

    # Second run (same day)
    rc2 = runner.main(common_args)
    assert rc2 == 0, f"second run (same-day) failed with rc={rc2}"

    state_after_second = json.loads(state_path.read_text())
    last_run_2 = state_after_second["last_run_at"]
    # last_run_at should be updated on second run
    assert last_run_2 is not None
    # Both runs on same day
    assert last_run_1[:10] == last_run_2[:10], "dates differ — not same-day re-run"

    # Digest should exist (written by both runs, second overwrites)
    date_str = runner.today_str()
    audit_path = wiki / "pages" / "audits" / f"DAILY-EVOLUTION-{date_str}.md"
    assert audit_path.exists()


# ---------------------------------------------------------------------------
# test_rollback_backoff_skips_adapter
# ---------------------------------------------------------------------------

def test_rollback_backoff_skips_adapter(tmp_path: Path) -> None:
    """Adapter in back-off window should be skipped in detect_upgrades."""
    wiki = _make_wiki(tmp_path)

    # Set up state with openclaw in back-off
    future_date = "2099-12-31"
    state = {
        "last_run_at": None,
        "last_rollback_skips": [{"adapter": "openclaw", "until_date": future_date}],
        "version_manifest": {},
    }

    class FakeOpenClaw:
        @property
        def name(self) -> str:
            return "openclaw"

        def probe_current_version(self):
            return "2026.4.14"

        def probe_latest_version(self):
            return "2026.5.18"

    with patch("daily_evolution_runner._load_adapters", return_value=[FakeOpenClaw()]):
        _, upgrades = runner.detect_upgrades(state, wiki, fixture_mode=False)

    assert upgrades == [], "adapter in back-off should be excluded from upgrades"


# ---------------------------------------------------------------------------
# Phase 6 _publish_digest surface fan-out tests
# ---------------------------------------------------------------------------

def _make_phases() -> list[runner.PhaseResult]:
    return [
        runner.PhaseResult(phase="snapshot", status="ok", detail="written"),
        runner.PhaseResult(phase="pull_substrate", status="skipped", detail="fixture"),
        runner.PhaseResult(phase="detect_upgrades", status="ok", detail="0 candidates"),
        runner.PhaseResult(phase="canary_each_upgrade", status="skipped", detail="no upgrades"),
        runner.PhaseResult(phase="proof_pack", status="skipped", detail="no script"),
    ]


def test_digest_declares_daily_evolution_is_not_full_auto_upgrader(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)

    result = runner.digest(_make_phases(), wiki, upgrades=[], dry_run=True)

    body = result.data["body"]
    assert "proof/report loop" in body
    assert "not a full safe auto-upgrader" in body
    assert "model_promotion_gate.py" in body
    assert "Auto-promote nothing" in body


def test_publish_digest_invokes_all_three_surfaces(tmp_path: Path) -> None:
    """_publish_digest must call gbrain SSH + Hermes seed subprocess exactly once each."""
    wiki = _make_wiki(tmp_path)
    audit_path = wiki / "pages" / "audits" / "DAILY-EVOLUTION-2026-05-19.md"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("stub body\n", encoding="utf-8")

    phases = _make_phases()

    ok_result = {"ok": True, "stdout": "", "stderr": "", "returncode": 0}

    with patch("daily_evolution_runner.run_cmd", return_value=ok_result) as mock_run:
        result = runner._publish_digest("stub body\n", audit_path, phases, wiki, dry_run=False)

    # gbrain push uses run_cmd (SSH), Hermes re-seed uses run_cmd (python3)
    assert mock_run.call_count >= 2, f"expected ≥2 subprocess calls, got {mock_run.call_count}"
    assert result["gbrain_push"] == "ok"
    assert result["hermes_reseed"] == "ok"
    assert result["karpathy_table"] == "ok"


def test_publish_digest_continues_on_gbrain_failure(tmp_path: Path) -> None:
    """gbrain SSH failure must not prevent Hermes re-seed from being called."""
    wiki = _make_wiki(tmp_path)
    audit_path = wiki / "pages" / "audits" / "DAILY-EVOLUTION-2026-05-19.md"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("stub body\n", encoding="utf-8")

    phases = _make_phases()

    # 2026-05-20 fix: Hermes seed also routes via SSH (to Air, where env
    # vars HERMES_WEBUI_STATE_DIR etc are set in launchd plist; on Mac
    # the script KeyError-SystemExits without them). So this mock must
    # differentiate gbrain SSH (VPS, made to fail) from Hermes SSH (Air,
    # made to succeed).
    def side_effect(cmd, **kwargs):
        if cmd and "ssh" in cmd[0]:
            remote = cmd[-1] if isinstance(cmd[-1], str) else ""
            if "hermes_webui_factory_seed" in remote:
                return {"ok": True, "stdout": "seeded", "stderr": "", "returncode": 0}
            return {"ok": False, "stdout": "", "stderr": "ssh: unreachable", "returncode": 255}
        return {"ok": True, "stdout": "", "stderr": "", "returncode": 0}

    with patch("daily_evolution_runner.run_cmd", side_effect=side_effect) as mock_run:
        result = runner._publish_digest("stub body\n", audit_path, phases, wiki, dry_run=False)

    # Hermes must still have been attempted
    calls = [str(c) for c in mock_run.call_args_list]
    hermes_called = any("hermes_webui_factory_seed" in c for c in calls)
    assert hermes_called, "Hermes re-seed must be called even when gbrain fails"
    assert result["gbrain_push"] == "warn"
    assert result["hermes_reseed"] == "ok"


def test_publish_digest_continues_on_hermes_timeout(tmp_path: Path) -> None:
    """Hermes timeout must not prevent result dict from returning; gbrain push still ok."""
    wiki = _make_wiki(tmp_path)
    audit_path = wiki / "pages" / "audits" / "DAILY-EVOLUTION-2026-05-19.md"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("stub body\n", encoding="utf-8")

    phases = _make_phases()

    def side_effect(cmd, **kwargs):
        if "hermes_webui_factory_seed" in str(cmd):
            return {"ok": False, "stdout": "", "stderr": "timeout", "returncode": -1}
        return {"ok": True, "stdout": "", "stderr": "", "returncode": 0}

    with patch("daily_evolution_runner.run_cmd", side_effect=side_effect):
        result = runner._publish_digest("stub body\n", audit_path, phases, wiki, dry_run=False)

    assert result["gbrain_push"] == "ok"
    assert result["hermes_reseed"] == "warn"


def test_karpathy_six_axis_table_in_digest_body(tmp_path: Path) -> None:
    """digest() must produce a Karpathy 6-axis markdown table in the written file."""
    wiki = _make_wiki(tmp_path)
    phases = _make_phases()
    upgrades: list[runner.Upgrade] = []

    ok_result = {"ok": True, "stdout": "", "stderr": "", "returncode": 0}
    with patch("daily_evolution_runner.run_cmd", return_value=ok_result):
        result = runner.digest(phases, wiki, upgrades, dry_run=False)

    assert result.status == "ok"
    date_str = runner.today_str()
    audit_path = wiki / "pages" / "audits" / f"DAILY-EVOLUTION-{date_str}.md"
    content = audit_path.read_text()

    assert "## Karpathy 6-axis self-score" in content, "Karpathy table header missing"
    assert "| # | Axis | Score | Note |" in content, "Karpathy table columns missing"
    assert "Total:" in content, "Karpathy total score line missing"


def test_publish_digest_dry_run_mode_no_side_effects(tmp_path: Path) -> None:
    """dry_run=True must skip all subprocess calls (gbrain + Hermes)."""
    wiki = _make_wiki(tmp_path)
    audit_path = wiki / "pages" / "audits" / "DAILY-EVOLUTION-2026-05-19.md"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text("stub body\n", encoding="utf-8")

    phases = _make_phases()

    with patch("daily_evolution_runner.run_cmd") as mock_run:
        result = runner._publish_digest("stub body\n", audit_path, phases, wiki, dry_run=True)

    # Karpathy table write uses audit_path.write_text (not run_cmd), so no subprocess calls
    mock_run.assert_not_called()
    assert result["gbrain_push"] == "dry_run"
    assert result["hermes_reseed"] == "dry_run"
    assert result["karpathy_table"] == "ok"


def test_main_dry_run_writes_no_files(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    state_path = wiki / "pages" / "systems" / "daily-evolution-state.json"

    rc = runner.main([
        "--fixture-mode",
        "--dry-run",
        "--wiki", str(wiki),
        "--state-file", str(state_path),
    ])

    assert rc == 0
    assert not state_path.exists(), "dry-run main must not write state"
    assert not (wiki / runner.DEFAULT_SNAPSHOT_REL).exists(), "dry-run main must not write snapshot"
    audit_files = list((wiki / "pages" / "audits").glob("DAILY-EVOLUTION-*.md"))
    assert audit_files == [], f"dry-run main must not write digest files, got {audit_files}"
