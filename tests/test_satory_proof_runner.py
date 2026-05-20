"""Tests for satory_proof_runner.py — T5 Satory proof runner.

Mock-only (no live SSH, no Todoist API hits, no urllib network calls).
Run: python3 -m pytest tools/tests/test_satory_proof_runner.py -q
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

import satory_proof_runner as runner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_factory_cache():
    """Reset the cached factory health between tests."""
    runner._FACTORY_HEALTH_CACHE.clear()


@pytest.fixture(autouse=True)
def reset_cache():
    _clear_factory_cache()
    yield
    _clear_factory_cache()


# ---------------------------------------------------------------------------
# Registry + project guard
# ---------------------------------------------------------------------------

def test_registry_has_exactly_12_tasks() -> None:
    """T5 doctrine: 12 AI-auditable Satory factory proof tasks; not 11, not 13."""
    assert len(runner.SATORY_PROOF_TASKS) == 12


def test_registry_task_ids_are_unique() -> None:
    ids = [t["id"] for t in runner.SATORY_PROOF_TASKS]
    assert len(ids) == len(set(ids))


def test_registry_task_ids_follow_todoist_format() -> None:
    """Todoist API v1 task IDs are short alphanum, length >= 12."""
    for t in runner.SATORY_PROOF_TASKS:
        assert len(t["id"]) >= 12, f"task id too short: {t['id']}"
        assert t["id"].isalnum(), f"task id has non-alnum chars: {t['id']}"


def test_registry_every_task_has_known_probe() -> None:
    """Every task must reference a probe in the PROBES dispatch."""
    for t in runner.SATORY_PROOF_TASKS:
        assert t["probe"] in runner.PROBES, f"unknown probe: {t['probe']}"


def test_satory_project_id_is_locked() -> None:
    """Scope guard: project_id must be Фабрика Satory ВКО only."""
    assert runner.SATORY_PROJECT_ID == "6gJ5j8PRVVCWpgCq"


# ---------------------------------------------------------------------------
# probe_site_lock
# ---------------------------------------------------------------------------

def test_probe_site_lock_returns_ok_on_locked_js() -> None:
    fake_body = '<script src="/assets/index-BSiWURaO.js"></script>'
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body.encode("utf-8")
    mock_resp.__enter__ = lambda self: self
    mock_resp.__exit__ = lambda self, *args: None

    with patch("satory_proof_runner.urllib.request.urlopen", return_value=mock_resp):
        result = runner.probe_site_lock()

    assert result["ok"] is True
    assert result["js_bundle"] == "index-BSiWURaO.js"
    assert result["status_code"] == 200


def test_probe_site_lock_returns_yellow_on_wrong_js() -> None:
    fake_body = '<script src="/assets/index-OLDHASHX.js"></script>'
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = fake_body.encode("utf-8")
    mock_resp.__enter__ = lambda self: self
    mock_resp.__exit__ = lambda self, *args: None

    with patch("satory_proof_runner.urllib.request.urlopen", return_value=mock_resp):
        result = runner.probe_site_lock()

    assert result["ok"] is False
    assert "OLDHASHX" in result["js_bundle"]


# ---------------------------------------------------------------------------
# probe_factory_health (cache + lenient JSON)
# ---------------------------------------------------------------------------

def test_probe_factory_health_caches_result_across_calls() -> None:
    """Second call must NOT re-fire SSH subprocess (the bug that caused 5 YELLOW)."""
    mock_run = MagicMock(return_value=MagicMock(
        returncode=0,
        stdout='{"overall": "GREEN", "reds": 0, "ts": "2026-05-20T06:00:00Z"}',
        stderr="",
    ))
    with patch("satory_proof_runner.subprocess.run", mock_run):
        r1 = runner.probe_factory_health()
        r2 = runner.probe_factory_health()
        r3 = runner.probe_factory_health()

    assert r1["ok"] is True
    assert r2 is r1 or r2 == r1
    assert r3 == r1
    assert mock_run.call_count == 1, "factory_health must be called only ONCE per runner invocation"


def test_probe_factory_health_lenient_json_extraction() -> None:
    """Probe stdout sometimes has leading text before JSON; we tolerate it."""
    noisy_stdout = '[probe] starting...\n{"overall": "GREEN", "reds": 0}'
    mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout=noisy_stdout, stderr=""))
    with patch("satory_proof_runner.subprocess.run", mock_run):
        result = runner.probe_factory_health()
    assert result["ok"] is True
    assert result["overall"] == "GREEN"


def test_probe_factory_health_handles_no_json_in_stdout() -> None:
    mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout="just text", stderr=""))
    with patch("satory_proof_runner.subprocess.run", mock_run):
        result = runner.probe_factory_health()
    assert result["ok"] is False
    assert "no JSON" in result["error"]


def test_probe_factory_health_handles_nonzero_rc() -> None:
    mock_run = MagicMock(return_value=MagicMock(returncode=255, stdout="", stderr="ssh: timeout"))
    with patch("satory_proof_runner.subprocess.run", mock_run):
        result = runner.probe_factory_health()
    assert result["ok"] is False
    assert "rc=255" in result["error"]


# ---------------------------------------------------------------------------
# probe_camera_doctor_script_exists
# ---------------------------------------------------------------------------

def test_probe_camera_doctor_script_exists_returns_true_when_path_listed() -> None:
    mock_run = MagicMock(return_value=MagicMock(
        returncode=0,
        stdout="/Users/madia/nous-agaas/wiki/tools/camera_doctor_live_cutover.sh",
        stderr="",
    ))
    with patch("satory_proof_runner.subprocess.run", mock_run):
        result = runner.probe_camera_doctor_script_exists()
    assert result["ok"] is True


def test_probe_camera_doctor_script_exists_returns_false_when_missing() -> None:
    mock_run = MagicMock(return_value=MagicMock(
        returncode=2,
        stdout="",
        stderr="ls: cannot access camera_doctor_live_cutover.sh: No such file or directory",
    ))
    with patch("satory_proof_runner.subprocess.run", mock_run):
        result = runner.probe_camera_doctor_script_exists()
    assert result["ok"] is False


# ---------------------------------------------------------------------------
# format_comment
# ---------------------------------------------------------------------------

def test_format_comment_includes_russian_status_and_command() -> None:
    task = {"id": "abc", "label": "Дашборд — работает", "probe": "site_lock"}
    probe_result = {"ok": True, "status_code": 200, "js_bundle": "index-BSiWURaO.js", "command": "curl satory..."}
    iso_ts = "2026-05-20T06:00:00Z"

    body = runner.format_comment(task, probe_result, iso_ts)

    assert "✅" in body
    assert "Дашборд — работает" in body
    assert "site_lock" in body
    assert "curl satory..." in body
    assert "проверено GREEN" in body
    assert "Operator" in body


def test_format_comment_uses_yellow_emoji_on_failure() -> None:
    task = {"id": "abc", "label": "Камеры — работает", "probe": "factory_health"}
    probe_result = {"ok": False, "error": "transient ssh race", "command": "ssh air ..."}
    body = runner.format_comment(task, probe_result, "2026-05-20T06:00:00Z")

    # Leading status emoji must be yellow (the operator footer mentions both
    # emojis as a legend "если ✅ ... если 🟡" — that's expected, don't
    # over-assert on global absence of ✅)
    assert body.startswith("🟡"), f"expected body to start with 🟡, got: {body[:5]}"
    assert "ручной валидации" in body


# ---------------------------------------------------------------------------
# post_todoist_comment
# ---------------------------------------------------------------------------

def test_post_todoist_comment_success() -> None:
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"id": "comment_abc123"}'
    mock_resp.__enter__ = lambda self: self
    mock_resp.__exit__ = lambda self, *args: None

    with patch("satory_proof_runner.urllib.request.urlopen", return_value=mock_resp):
        result = runner.post_todoist_comment("token-redacted", "task-id", "test body")

    assert result["ok"] is True
    assert result["comment_id"] == "comment_abc123"


def test_post_todoist_comment_handles_http_error() -> None:
    import urllib.error
    fake_error = urllib.error.HTTPError(
        url="https://api.todoist.com/api/v1/comments",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=None,
    )
    fake_error.read = MagicMock(return_value=b'{"error": "no permission"}')

    with patch("satory_proof_runner.urllib.request.urlopen", side_effect=fake_error):
        result = runner.post_todoist_comment("token", "task", "body")

    assert result["ok"] is False
    assert result["status_code"] == 403


# ---------------------------------------------------------------------------
# append_ledger
# ---------------------------------------------------------------------------

def test_append_ledger_writes_jsonl_line(tmp_path: Path) -> None:
    fake_ledger = tmp_path / "ledger.jsonl"
    with patch.object(runner, "LEDGER_PATH", fake_ledger):
        runner.append_ledger({"ts": "2026-05-20T06:00:00Z", "task_id": "abc", "ok": True})
        runner.append_ledger({"ts": "2026-05-20T06:01:00Z", "task_id": "def", "ok": False})

    lines = fake_ledger.read_text().splitlines()
    assert len(lines) == 2
    parsed1 = json.loads(lines[0])
    assert parsed1["task_id"] == "abc"
    assert parsed1["ok"] is True


# ---------------------------------------------------------------------------
# fetch_todoist_token
# ---------------------------------------------------------------------------

def test_fetch_todoist_token_prefers_local_env(monkeypatch) -> None:
    monkeypatch.setenv("TODOIST_API_TOKEN", "local-env-token")
    token = runner.fetch_todoist_token()
    assert token == "local-env-token"


def test_fetch_todoist_token_falls_back_to_ssh(monkeypatch) -> None:
    monkeypatch.delenv("TODOIST_API_TOKEN", raising=False)
    mock_run = MagicMock(return_value=MagicMock(
        returncode=0,
        stdout="TODOIST_API_TOKEN=ssh-fetched-token\n",
        stderr="",
    ))
    with patch("satory_proof_runner.subprocess.run", mock_run):
        token = runner.fetch_todoist_token()
    assert token == "ssh-fetched-token"


def test_fetch_todoist_token_raises_on_ssh_failure(monkeypatch) -> None:
    monkeypatch.delenv("TODOIST_API_TOKEN", raising=False)
    mock_run = MagicMock(return_value=MagicMock(
        returncode=255,
        stdout="",
        stderr="ssh: unreachable",
    ))
    with patch("satory_proof_runner.subprocess.run", mock_run):
        with pytest.raises(RuntimeError, match="cannot fetch TODOIST_API_TOKEN"):
            runner.fetch_todoist_token()


# ---------------------------------------------------------------------------
# get_recent_runner_comment — TTL dedup (added 2026-05-20 in acd57827)
# ---------------------------------------------------------------------------

def _mock_comments_resp(comments: list[dict]) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({"results": comments}).encode("utf-8")
    mock_resp.__enter__ = lambda self: self
    mock_resp.__exit__ = lambda self, *args: None
    return mock_resp


def test_get_recent_runner_comment_returns_match_within_ttl() -> None:
    """Recent runner-authored comment within TTL → returned (will skip post)."""
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    recent_iso = (now - dt.timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    fake_comments = [
        {"id": "c1", "posted_at": recent_iso, "content": "✅ AI-проверка от Nous Factory — 2026-05-20T..."},
    ]
    with patch("satory_proof_runner.urllib.request.urlopen", return_value=_mock_comments_resp(fake_comments)):
        result = runner.get_recent_runner_comment("token", "task", ttl_hours=6)
    assert result is not None
    assert result["id"] == "c1"


def test_get_recent_runner_comment_returns_none_outside_ttl() -> None:
    """Old runner comment beyond TTL → None (post should fire)."""
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    old_iso = (now - dt.timedelta(hours=10)).isoformat().replace("+00:00", "Z")
    fake_comments = [
        {"id": "c1", "posted_at": old_iso, "content": "✅ AI-проверка от Nous Factory — old run"},
    ]
    with patch("satory_proof_runner.urllib.request.urlopen", return_value=_mock_comments_resp(fake_comments)):
        result = runner.get_recent_runner_comment("token", "task", ttl_hours=6)
    assert result is None


def test_get_recent_runner_comment_ignores_non_runner_comments() -> None:
    """Recent comments without the runner prefix marker should NOT count."""
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    recent_iso = (now - dt.timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    fake_comments = [
        {"id": "c1", "posted_at": recent_iso, "content": "Manual operator note: please verify"},
        {"id": "c2", "posted_at": recent_iso, "content": "AI-фабрика взяла задачу в one-beam очередь"},  # different prefix
    ]
    with patch("satory_proof_runner.urllib.request.urlopen", return_value=_mock_comments_resp(fake_comments)):
        result = runner.get_recent_runner_comment("token", "task", ttl_hours=6)
    assert result is None


def test_get_recent_runner_comment_picks_most_recent_when_multiple() -> None:
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    older_iso = (now - dt.timedelta(hours=5)).isoformat().replace("+00:00", "Z")
    newer_iso = (now - dt.timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    fake_comments = [
        {"id": "c_old", "posted_at": older_iso, "content": "✅ AI-проверка от Nous Factory — older"},
        {"id": "c_new", "posted_at": newer_iso, "content": "✅ AI-проверка от Nous Factory — newer"},
    ]
    with patch("satory_proof_runner.urllib.request.urlopen", return_value=_mock_comments_resp(fake_comments)):
        result = runner.get_recent_runner_comment("token", "task", ttl_hours=6)
    assert result is not None
    assert result["id"] == "c_new"


def test_get_recent_runner_comment_returns_none_when_ttl_zero() -> None:
    """ttl_hours=0 means dedup disabled — always None (caller posts)."""
    # No urlopen should fire when ttl=0
    with patch("satory_proof_runner.urllib.request.urlopen") as mock_url:
        result = runner.get_recent_runner_comment("token", "task", ttl_hours=0)
    assert result is None
    assert mock_url.call_count == 0


def test_get_recent_runner_comment_soft_fails_on_api_error() -> None:
    """If Todoist GET fails (network error), return None so caller can still post."""
    import urllib.error
    fake_error = urllib.error.URLError("Connection refused")
    with patch("satory_proof_runner.urllib.request.urlopen", side_effect=fake_error):
        result = runner.get_recent_runner_comment("token", "task", ttl_hours=6)
    assert result is None
