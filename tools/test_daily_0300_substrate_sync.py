import datetime as dt
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import daily_0300_substrate_sync as daily


def _green_probe(component="stub"):
    return daily.Probe(component, "GREEN", "stubbed")


def test_run_timeout_output_is_text(monkeypatch):
    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("cmd", 1, output=b"partial stdout", stderr=b"partial stderr")

    monkeypatch.setattr(daily.subprocess, "run", fake_run)

    result = daily.run(["cmd"], timeout=1)

    assert result["returncode"] == 124
    assert result["stdout"] == "partial stdout"
    assert result["stderr"] == "partial stderr"
    assert result["stdout"] + result["stderr"] == "partial stdoutpartial stderr"


def test_probe_only_implies_factory_probe_skip(monkeypatch, tmp_path, capsys):
    seen = []

    monkeypatch.setattr(daily, "run_optional_syncs", lambda *args, **kwargs: [])
    monkeypatch.setattr(daily, "probe_air_launchd_schedule", lambda wiki: _green_probe("03:00 owner"))
    monkeypatch.setattr(daily, "probe_wiki_git", lambda wiki: _green_probe("wiki git"))
    monkeypatch.setattr(daily, "probe_gbrain", lambda wiki: _green_probe("gbrain"))
    monkeypatch.setattr(daily, "probe_gstack", lambda wiki: _green_probe("gstack"))
    monkeypatch.setattr(daily, "probe_litellm", lambda runtime: _green_probe("LiteLLM"))
    monkeypatch.setattr(daily, "probe_telegram", lambda runtime: _green_probe("Telegram"))
    monkeypatch.setattr(daily, "probe_todoist", lambda wiki, runtime: _green_probe("Todoist"))
    monkeypatch.setattr(daily, "probe_notion", lambda runtime, wiki: _green_probe("Notion"))
    monkeypatch.setattr(daily, "probe_satory_events", lambda runtime: _green_probe("Satory events"))
    monkeypatch.setattr(daily, "probe_gpu", lambda runtime: _green_probe("Nous-GPU"))

    def fake_openclaw(skip_factory_probe, runtime):
        seen.append(skip_factory_probe)
        return _green_probe("OpenClaw")

    monkeypatch.setattr(daily, "probe_openclaw", fake_openclaw)

    rc = daily.main([
        "--wiki", str(tmp_path / "wiki"),
        "--runtime", str(tmp_path / "runtime"),
        "--probe-only",
        "--json",
    ])

    assert rc == 0
    assert seen == [True]
    capsys.readouterr()


def test_openclaw_factory_probe_labels_run_task_source(monkeypatch, tmp_path):
    commands = []

    class FakeSocket:
        def settimeout(self, _timeout):
            pass

        def connect(self, _address):
            pass

        def close(self):
            pass

    def fake_run(cmd, **_kwargs):
        commands.append(cmd)
        if cmd[:3] == ["/usr/local/bin/docker", "inspect", "openclaw"]:
            return {"ok": True, "stdout": "healthy\n", "stderr": "", "returncode": 0}
        return {"ok": True, "stdout": "DAILY_0300_OK\n", "stderr": "", "returncode": 0}

    monkeypatch.setattr(daily, "run", fake_run)
    monkeypatch.setattr(daily.socket, "socket", lambda *args, **kwargs: FakeSocket())

    probe = daily.probe_openclaw(skip_factory_probe=False, runtime=tmp_path)

    assert probe.status == "GREEN"
    assert commands[-1] == [
        "python3",
        "run_task.py",
        "--source",
        "daily_0300_substrate_sync",
        "Reply with exactly: DAILY_0300_OK",
    ]


def test_gbrain_probe_sources_openai_compatible_proxy(monkeypatch, tmp_path):
    commands = []

    def fake_run(cmd, **_kwargs):
        commands.append(cmd)
        return {
            "ok": True,
            "stdout": '{"health_score":100,"missing_embeddings":0,"stale_pages":0,"dead_links":0}',
            "stderr": "",
            "returncode": 0,
        }

    monkeypatch.setattr(daily, "run", fake_run)

    probe = daily.probe_gbrain(tmp_path)

    assert probe.status == "GREEN"
    assert commands[0][0] == "ssh"
    remote_script = commands[0][2]
    assert "GBRAIN_OPENAI_COMPAT_ENV" in remote_script
    assert "/root/.gbrain/openai-compatible.env" in remote_script
    assert "export OPENAI_API_KEY=\"$KEY\"" in remote_script
    assert 'timeout -k 10s "$SYNC_TIMEOUT" bin/gbrain sync' in remote_script
    assert 'timeout -k 10s "$EMBED_TIMEOUT" bin/gbrain embed --stale' in remote_script
    assert 'timeout -k 10s "$DOCTOR_TIMEOUT" bin/gbrain doctor' in remote_script


def test_gpu_probe_is_yellow_unless_gpu_workload_is_required(monkeypatch, tmp_path):
    monkeypatch.delenv("NOUS_GPU_REQUIRED", raising=False)
    monkeypatch.setattr(
        daily,
        "launchd_status",
        lambda label: daily.Probe(label, "RED", "collector red", "exit=1"),
    )

    probe = daily.probe_gpu(tmp_path)

    assert probe.status == "YELLOW"
    assert "Optional GPU lane" in probe.remediation


def test_gpu_probe_is_red_when_gpu_workload_is_required(monkeypatch, tmp_path):
    monkeypatch.setenv("NOUS_GPU_REQUIRED", "1")
    monkeypatch.setattr(
        daily,
        "launchd_status",
        lambda label: daily.Probe(label, "RED", "collector red", "exit=1"),
    )

    probe = daily.probe_gpu(tmp_path)

    assert probe.status == "RED"
    assert "GPU-bound workloads" in probe.remediation


def test_launchd_status_running_pid_is_green_despite_stale_last_exit(monkeypatch):
    def fake_run(*_args, **_kwargs):
        return {
            "ok": True,
            "stdout": "18144\t1\tcom.nous.telegram-poll\n",
            "stderr": "",
            "returncode": 0,
        }

    monkeypatch.setattr(daily, "run", fake_run)

    probe = daily.launchd_status("com.nous.telegram-poll")

    assert probe.status == "GREEN"
    assert "currently running" in probe.summary
    assert "last_exit=1" in probe.summary


def test_launchd_status_idle_nonzero_exit_remains_red(monkeypatch):
    def fake_run(*_args, **_kwargs):
        return {
            "ok": True,
            "stdout": "-\t1\tcom.nous.telegram-poll\n",
            "stderr": "",
            "returncode": 0,
        }

    monkeypatch.setattr(daily, "run", fake_run)

    probe = daily.launchd_status("com.nous.telegram-poll")

    assert probe.status == "RED"
    assert "last_exit=1" in probe.summary


def test_todoist_probe_uses_read_only_direct_lookup(monkeypatch, tmp_path):
    commands = []
    script = tmp_path / "wiki" / "tools" / "audit_satory_todoist_state.py"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    def fake_run(cmd, **_kwargs):
        commands.append(cmd)
        return {
            "ok": True,
            "stdout": '{"project":{"id":"6gJ5j8PRVVCWpgCq"},"tasks":{"active_count":126,"ai_label_ru_count":69},"risks":[]}',
            "stderr": "",
            "returncode": 0,
        }

    monkeypatch.setattr(daily, "run", fake_run)

    probe = daily.probe_todoist(tmp_path / "wiki", tmp_path / "runtime")

    assert probe.status == "GREEN"
    assert "--direct-task-lookup" in commands[0]


def test_ad_hoc_report_does_not_overwrite_existing_canonical(tmp_path):
    scheduled = dt.datetime(2026, 4, 29, 3, 0, tzinfo=daily.ALMATY)
    canonical = daily.write_report(tmp_path, "original 03:00 evidence", scheduled)

    ad_hoc = dt.datetime(2026, 4, 29, 15, 29, 49, tzinfo=daily.ALMATY)
    rerun = daily.write_report(tmp_path, "afternoon rerun evidence", ad_hoc)

    assert canonical.name == "daily-0300-substrate-2026-04-29.md"
    assert rerun != canonical
    assert canonical.read_text(encoding="utf-8") == "original 03:00 evidence"
    assert rerun.read_text(encoding="utf-8") == "afternoon rerun evidence"
    assert rerun.name == "daily-0300-substrate-2026-04-29-adhoc-152949.md"


def test_ad_hoc_report_uses_timestamped_path_even_without_canonical(tmp_path):
    ad_hoc = dt.datetime(2026, 4, 29, 0, 15, 3, tzinfo=daily.ALMATY)
    report = daily.write_report(tmp_path, "early manual audit", ad_hoc)

    canonical = tmp_path / "pages" / "dashboards" / "daily-0300-substrate-2026-04-29.md"
    assert report.name == "daily-0300-substrate-2026-04-29-adhoc-001503.md"
    assert not canonical.exists()
