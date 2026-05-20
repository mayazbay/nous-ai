from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import presidential_readiness_gate as gate


def _args(tmp_path: Path, send_phone_canary: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        wiki=tmp_path,
        protected_scope="tools/command_center.py,tools/telegram_poll.py,pages/systems/,pages/skills/*",
        latest_handoff="pages/progress/HANDOFF-AUTO-2026-05-20-09-00.md",
        send_phone_canary=send_phone_canary,
        phone_canary_msg_id="",
        canary_message="CANARY test production-write-requires-ack",
        json=True,
    )


def _cmd_result(ok: bool = True, stdout: str = "", stderr: str = "", returncode: int | None = None):
    return gate.CommandResult(
        ok=ok,
        returncode=(0 if ok else 1) if returncode is None else returncode,
        stdout=stdout,
        stderr=stderr,
        cmd="fake",
    )


def test_overall_is_yellow_when_only_yellows_exist() -> None:
    result = gate.overall_from(
        [
            gate.check("a", "GREEN", "ok"),
            gate.check("b", "YELLOW", "needs proof"),
        ]
    )

    assert result["overall"] == "YELLOW"
    assert result["reds"] == 0
    assert result["yellows"] == 1


def test_summary_is_plain_and_telegram_pasteable() -> None:
    payload = gate.overall_from(
        [
            gate.check("factory", "GREEN", "overall=GREEN reds=0"),
            gate.check("qmd", "YELLOW", "pending embeddings"),
        ]
    )

    summary = gate.render_summary(payload)

    assert "Presidential readiness: YELLOW" in summary
    assert "GREEN factory: overall=GREEN reds=0" in summary
    assert "YELLOW qmd: pending embeddings" in summary


def test_session_scan_parallel_is_yellow_not_red() -> None:
    status, detail = gate.summarize_session_scan(
        '  🟡 PARALLEL: 1 active session(s)\n'
        '    • s1 [mac] started=now intent="peer" scope=tools/command_center.py\n'
    )

    assert status == "YELLOW"
    assert "active overlap" in detail


def test_gbrain_warnings_are_yellow() -> None:
    output = 'progress\n{"status":"warnings","health_score":90,"checks":[]}\n'

    status, detail, evidence = gate.status_from_gbrain_doctor(output, 0)

    assert status == "YELLOW"
    assert "health_score=90" in detail
    assert evidence["status"] == "warnings"


def test_openclaw_canary_curl_failure_is_yellow(monkeypatch) -> None:
    monkeypatch.setattr(
        gate,
        "ssh",
        lambda *_args, **_kwargs: _cmd_result(
            ok=True,
            stdout="curl: (7) Failed to connect to 127.0.0.1 port 18790\n",
        ),
    )

    result = gate.check_canary_518_health()

    assert result["status"] == "YELLOW"
    assert "not responding" in result["detail"]


def test_evaluate_does_not_send_phone_canary_by_default(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        joined = " ".join(cmd)
        if "session_scan.sh" in joined:
            return _cmd_result(stdout="  ✅ no other active sessions\n")
        if "factory_no_drift_probe.sh" in joined:
            return _cmd_result(stdout='{"overall":"GREEN","reds":0,"checks":[]}')
        if "telegram_openclaw_factory_truth_gate.py" in joined:
            return _cmd_result(stdout='{"overall":"GREEN","reds":0,"yellows":0,"checks":[]}')
        if "control_plane_sync_loop.py" in joined:
            return _cmd_result(stdout='{"overall_status":"done","steps":[]}')
        if "openbrain_project_to_wiki.py" in joined:
            return _cmd_result(stdout='{"ok":true,"projection_failed":false,"would_create":0,"would_update":0,"exists":20,"thoughts_seen":20}')
        if "qmd_real_freshness.sh" in joined:
            return _cmd_result(stdout='{"status":"fresh","reason":"last qmd embed 1h ago"}')
        raise AssertionError(joined)

    def fake_ssh(host: str, script: str, **kwargs):
        if "launchctl print" in script:
            return _cmd_result(stdout="state = running\nprogram = /opt/homebrew/bin/python3 /Users/madia/nous-agaas/tools/telegram_poll.py\nlast exit code = 0\npid = 123\n")
        if "gbrain doctor" in script:
            return _cmd_result(stdout='{"status":"ok","health_score":100,"checks":[]}')
        if "qmd get" in script:
            return _cmd_result(stdout="---\ntype: progress\n---\n# Factory auto-checkpoint\n")
        if "18790/health" in script:
            return _cmd_result(stdout='{"status":"live"}')
        if "satory_ai_factory_queue.py" in script:
            return _cmd_result(stdout='{"selected":1,"results":[{"id":"t1"}]}')
        raise AssertionError(script)

    monkeypatch.setattr(gate, "run", fake_run)
    monkeypatch.setattr(gate, "ssh", fake_ssh)

    result = gate.evaluate(_args(tmp_path))

    assert result["overall"] == "YELLOW"
    assert any(item["check"] == "telegram_phone_canary_send" and item["status"] == "YELLOW" for item in result["checks"])
    assert not any("tg_send.sh" in " ".join(cmd) for cmd in calls)


def test_evaluate_sends_phone_canary_only_with_flag(monkeypatch, tmp_path: Path) -> None:
    sent: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        joined = " ".join(cmd)
        if "tg_send.sh" in joined:
            sent.append(cmd)
            return _cmd_result(stdout="✅ sent to chat_id=110793056 (msg_id=42)\n")
        if "session_scan.sh" in joined:
            return _cmd_result(stdout="  ✅ no other active sessions\n")
        if "factory_no_drift_probe.sh" in joined:
            return _cmd_result(stdout='{"overall":"GREEN","reds":0,"checks":[]}')
        if "telegram_openclaw_factory_truth_gate.py" in joined:
            return _cmd_result(stdout='{"overall":"GREEN","reds":0,"yellows":0,"checks":[]}')
        if "control_plane_sync_loop.py" in joined:
            return _cmd_result(stdout='{"overall_status":"done","steps":[]}')
        if "openbrain_project_to_wiki.py" in joined:
            return _cmd_result(stdout='{"ok":true,"projection_failed":false,"would_create":0,"would_update":0,"exists":20,"thoughts_seen":20}')
        if "qmd_real_freshness.sh" in joined:
            return _cmd_result(stdout='{"status":"fresh","reason":"last qmd embed 1h ago"}')
        raise AssertionError(joined)

    def fake_ssh(host: str, script: str, **kwargs):
        if "launchctl print" in script:
            return _cmd_result(stdout="state = running\nprogram = /opt/homebrew/bin/python3 /Users/madia/nous-agaas/tools/telegram_poll.py\nlast exit code = 0\npid = 123\n")
        if "gbrain doctor" in script:
            return _cmd_result(stdout='{"status":"ok","health_score":100,"checks":[]}')
        if "qmd get" in script:
            return _cmd_result(stdout="---\ntype: progress\n---\n# Factory auto-checkpoint\n")
        if "18790/health" in script:
            return _cmd_result(stdout='{"status":"live"}')
        if "satory_ai_factory_queue.py" in script:
            return _cmd_result(stdout='{"selected":1,"results":[{"id":"t1"}]}')
        raise AssertionError(script)

    monkeypatch.setattr(gate, "run", fake_run)
    monkeypatch.setattr(gate, "ssh", fake_ssh)

    result = gate.evaluate(_args(tmp_path, send_phone_canary=True))

    assert result["overall"] == "GREEN"
    assert sent == [["bash", "tools/tg_send.sh", "CANARY test production-write-requires-ack"]]
    assert any(item["check"] == "telegram_phone_canary_send" and "msg_id=42" in item["detail"] for item in result["checks"])


def test_evaluate_records_existing_phone_canary_without_sending(monkeypatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        joined = " ".join(cmd)
        if "session_scan.sh" in joined:
            return _cmd_result(stdout="  ✅ no other active sessions\n")
        if "factory_no_drift_probe.sh" in joined:
            return _cmd_result(stdout='{"overall":"GREEN","reds":0,"checks":[]}')
        if "telegram_openclaw_factory_truth_gate.py" in joined:
            return _cmd_result(stdout='{"overall":"GREEN","reds":0,"yellows":0,"checks":[]}')
        if "control_plane_sync_loop.py" in joined:
            return _cmd_result(stdout='{"overall_status":"done","steps":[]}')
        if "openbrain_project_to_wiki.py" in joined:
            return _cmd_result(stdout='{"ok":true,"projection_failed":false,"would_create":0,"would_update":0,"exists":20,"thoughts_seen":20}')
        if "qmd_real_freshness.sh" in joined:
            return _cmd_result(stdout='{"status":"fresh","reason":"last qmd embed 1h ago"}')
        raise AssertionError(joined)

    def fake_ssh(host: str, script: str, **kwargs):
        if "launchctl print" in script:
            return _cmd_result(stdout="state = not running\nprogram = /opt/homebrew/bin/python3 /Users/madia/nous-agaas/tools/telegram_poll.py\nlast exit code = 0\n")
        if "gbrain doctor" in script:
            return _cmd_result(stdout='{"status":"ok","health_score":100,"checks":[]}')
        if "qmd get" in script:
            return _cmd_result(stdout="---\ntype: progress\n---\n# Factory auto-checkpoint\n")
        if "18790/health" in script:
            return _cmd_result(stdout='{"status":"live"}')
        if "satory_ai_factory_queue.py" in script:
            return _cmd_result(stdout='{"selected":1,"results":[{"id":"t1"}]}')
        raise AssertionError(script)

    args = _args(tmp_path)
    args.phone_canary_msg_id = "1746"
    monkeypatch.setattr(gate, "run", fake_run)
    monkeypatch.setattr(gate, "ssh", fake_ssh)

    result = gate.evaluate(args)

    assert result["overall"] == "GREEN"
    assert not any("tg_send.sh" in " ".join(cmd) for cmd in calls)
    assert any(item["check"] == "telegram_phone_canary_send" and "msg_id=1746" in item["detail"] for item in result["checks"])
