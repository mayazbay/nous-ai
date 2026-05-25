from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import hermes_factory_watchdog as hermes


def _args(tmp_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        wiki=tmp_path,
        python=Path("/usr/bin/python3"),
        control_log=tmp_path / "control.jsonl",
        hermes_log=tmp_path / "hermes.jsonl",
        state_page=Path("pages/systems/hermes.md"),
        human_reminder_status=Path("pages/systems/human-owner-reminder-status.md"),
        openclaw_health_url="http://openclaw/healthz",
        timeout=0.1,
        max_control_plane_age_seconds=3600,
        max_human_reminder_age_seconds=30 * 3600,
        max_model_bakeoff_age_seconds=8 * 86400,
        no_restart_openclaw=True,
        dry_run=True,
        json=True,
    )


def test_stale_control_plane_requests_kick(monkeypatch, tmp_path: Path) -> None:
    old = (hermes.now_kzt() - dt.timedelta(hours=3)).isoformat()
    cycles = [{"cycle_id": "old", "finished_at": old, "steps": []}]
    kicks = []
    monkeypatch.setattr(hermes, "kick_launchd", lambda label, dry_run: (kicks.append(label) or {"ok": True, "detail": "kicked"}))

    result = hermes.check_control_plane(_args(tmp_path), cycles)

    assert result["status"] == "not_done"
    assert kicks == [hermes.CONTROL_PLANE_LABEL]


def test_repeated_sync_failure_creates_factory_slice(monkeypatch, tmp_path: Path) -> None:
    cycles = [
        {"cycle_id": "a", "finished_at": hermes.iso_now(), "steps": [{"name": "notion_sync", "status": "blocked"}]},
        {"cycle_id": "b", "finished_at": hermes.iso_now(), "steps": [{"name": "notion_sync", "status": "not_done"}]},
    ]
    created = []
    monkeypatch.setattr(hermes, "create_factory_slice", lambda *args, **kwargs: (created.append(args[2]) or {"ok": True, "path": "pages/task-results/slice.md"}))
    monkeypatch.setattr(hermes, "send_telegram", lambda *args, **kwargs: {"ok": True, "detail": "sent"})

    result = hermes.check_repeated_sync_failures(_args(tmp_path), cycles)

    assert result["status"] == "not_done"
    assert created == ["repeated Todoist or Notion sync failure"]


def test_openclaw_green_does_not_restart(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(hermes, "http_ok", lambda *_args: (True, "http_200"))
    calls = []
    monkeypatch.setattr(hermes, "run", lambda cmd, **kwargs: (calls.append(cmd) or {"ok": True, "stdout": "", "stderr": ""}))

    result = hermes.check_openclaw(_args(tmp_path))

    assert result["status"] == "done"
    assert calls == []


def test_known_github_failure_incident_dedupes_to_done(monkeypatch, tmp_path: Path) -> None:
    incident = tmp_path / "pages/audits/INCIDENT-github-actions-123.md"
    incident.parent.mkdir(parents=True)
    incident.write_text("# existing\n", encoding="utf-8")
    payload = [
        {
            "databaseId": 123,
            "name": "Codex Landed Commit Loop",
            "status": "completed",
            "conclusion": "failure",
            "headSha": "abc",
            "createdAt": "2026-05-13T00:00:00Z",
            "url": "https://github.example/run/123",
        }
    ]
    monkeypatch.setattr(
        hermes,
        "run",
        lambda cmd, **kwargs: {"ok": True, "stdout": __import__("json").dumps(payload), "stderr": ""},
    )

    result = hermes.check_github_incidents(_args(tmp_path))

    assert result["status"] == "done"
    assert "already recorded" in result["summary"]


def test_status_page_rewrites_when_done_clears_old_yellow() -> None:
    report = {"overall_status": "done"}

    assert hermes.should_write_status(report, "status: not_done\n") is True
    assert hermes.should_write_status(report, "status: blocked\n") is True
    assert hermes.should_write_status(report, "status: done\n") is False


def test_status_page_rewrites_when_new_check_missing() -> None:
    report = {"overall_status": "done", "checks": [{"name": "human_owner_reminder"}]}

    assert hermes.should_write_status(report, "status: done\n| control_plane_recency | `done` | fresh |\n") is True
    assert hermes.should_write_status(report, "status: done\n| human_owner_reminder | `done` | fresh |\n") is False


def test_missing_human_reminder_status_requests_kick(monkeypatch, tmp_path: Path) -> None:
    kicks = []
    monkeypatch.setattr(hermes, "kick_launchd", lambda label, dry_run: (kicks.append(label) or {"ok": True, "detail": "kicked"}))

    result = hermes.check_human_owner_reminder(_args(tmp_path))

    assert result["status"] == "not_done"
    assert kicks == [hermes.COMMENT_SWEEP_LABEL]


def test_factory_probe_air_sync_lag_gets_pull_and_rerun(monkeypatch, tmp_path: Path) -> None:
    probe = tmp_path / hermes.FACTORY_PROBE
    probe.parent.mkdir(parents=True)
    probe.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    red = {"overall": "RED", "reds": 1, "checks": [{"check": "air_sync_lag", "status": "RED", "detail": "behind"}]}
    green = {"overall": "GREEN", "reds": 0, "checks": [{"check": "air_sync_lag", "status": "GREEN", "detail": "ok"}]}
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[:2] == ["git", "pull"]:
            return {"ok": True, "stdout": "updated", "stderr": ""}
        if len([call for call in calls if call and call[0] == "bash"]) == 1:
            return {"ok": False, "stdout": json.dumps(red), "stderr": ""}
        return {"ok": True, "stdout": json.dumps(green), "stderr": ""}

    args = _args(tmp_path)
    args.dry_run = False
    monkeypatch.setattr(hermes, "run", fake_run)

    result = hermes.check_factory_probe(args)

    assert result["status"] == "done"
    assert ["git", "pull", "--rebase", "origin", "main"] in calls
