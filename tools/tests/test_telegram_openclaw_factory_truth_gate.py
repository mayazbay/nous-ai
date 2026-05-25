from __future__ import annotations

from pathlib import Path
import sys


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from telegram_openclaw_factory_truth_gate import (  # noqa: E402
    CommandResult,
    _head_or_error,
    classify_runtime_root_status,
    command_center_hashes_equal,
    overall_from,
    poller_import_order_ok,
    summarize_status_lines,
)


def test_dirty_air_runtime_root_is_yellow_by_default_not_red() -> None:
    item = classify_runtime_root_status(" M command_center.py\n?? scratch.txt\n")

    assert item["status"] == "YELLOW"
    assert "release_dirty tracked=1 untracked=1" in item["detail"]


def test_dirty_air_runtime_root_can_be_strict_red() -> None:
    item = classify_runtime_root_status(" M command_center.py\n", strict=True)

    assert item["status"] == "RED"


def test_clean_air_runtime_root_is_green() -> None:
    item = classify_runtime_root_status("")

    assert item["status"] == "GREEN"


def test_overall_green_allows_yellow_hygiene_items() -> None:
    result = overall_from(
        [
            {"check": "factory_no_drift_probe", "status": "GREEN", "detail": "ok"},
            {"check": "air_runtime_root_hygiene", "status": "YELLOW", "detail": "release_dirty"},
        ]
    )

    assert result["overall"] == "GREEN"
    assert result["reds"] == 0
    assert result["yellows"] == 1


def test_overall_red_if_any_production_check_is_red() -> None:
    result = overall_from(
        [
            {"check": "factory_no_drift_probe", "status": "RED", "detail": "sync lag"},
            {"check": "air_runtime_root_hygiene", "status": "YELLOW", "detail": "release_dirty"},
        ]
    )

    assert result["overall"] == "RED"
    assert result["reds"] == 1


def test_poller_import_order_accepts_tools_before_runtime_plus_alias_import() -> None:
    text = '''
TOOLS_DIR = Path(__file__).resolve().parent
RUNTIME_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(1, str(RUNTIME_ROOT))
command_center_path = TOOLS_DIR / "command_center.py"
'''

    ok, detail = poller_import_order_ok(text)

    assert ok
    assert "tools router precedes runtime root" in detail


def test_poller_import_order_rejects_runtime_before_tools() -> None:
    text = '''
TOOLS_DIR = Path(__file__).resolve().parent
RUNTIME_ROOT = TOOLS_DIR.parent
sys.path.insert(1, str(RUNTIME_ROOT))
sys.path.insert(0, str(TOOLS_DIR))
command_center_path = TOOLS_DIR / "command_center.py"
'''

    ok, detail = poller_import_order_ok(text)

    assert not ok
    assert detail == "runtime root precedes tracked tools directory"


def test_command_center_hashes_equal_accepts_three_matching_hashes() -> None:
    ok, detail, hashes = command_center_hashes_equal(
        "abc /Users/madia/nous-agaas/command_center.py\n"
        "abc /Users/madia/nous-agaas/tools/command_center.py\n"
        "abc /Users/madia/nous-agaas/wiki/tools/command_center.py\n"
    )

    assert ok
    assert detail == "runtime root/tools/wiki command_center hashes match"
    assert len(hashes) == 3


def test_command_center_hashes_equal_rejects_split_brain_router() -> None:
    ok, detail, hashes = command_center_hashes_equal(
        "abc /Users/madia/nous-agaas/command_center.py\n"
        "def /Users/madia/nous-agaas/tools/command_center.py\n"
        "def /Users/madia/nous-agaas/wiki/tools/command_center.py\n"
    )

    assert not ok
    assert "hash drift" in detail
    assert len(set(hashes.values())) == 2


def test_status_summary_counts_tracked_and_untracked() -> None:
    summary = summarize_status_lines(" M a.py\n?? b.py\nA  c.py\n")

    assert summary["dirty"] is True
    assert summary["tracked"] == 2
    assert summary["untracked"] == 1


def test_head_or_error_reads_first_ls_remote_field_without_remote_name_assumption() -> None:
    result = CommandResult(ok=True, returncode=0, stdout="abc123\trefs/heads/main\n", stderr="", cmd="git ls-remote")

    assert _head_or_error(result) == "abc123"


def test_head_or_error_preserves_remote_failure_as_error() -> None:
    result = CommandResult(ok=False, returncode=128, stdout="", stderr="fatal: bad remote", cmd="git ls-remote")

    assert _head_or_error(result) == "ERROR:fatal: bad remote"
