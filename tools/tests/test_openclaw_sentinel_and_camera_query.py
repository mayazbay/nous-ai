from __future__ import annotations

import importlib.util
import json
import sys
import types
import urllib.parse
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = TOOLS_DIR.parent

cost_tracker = types.ModuleType("cost_tracker")
cost_tracker.daily_report = lambda *args, **kwargs: {}
cost_tracker.format_report = lambda *args, **kwargs: ""
sys.modules.setdefault("cost_tracker", cost_tracker)

factory_health = types.ModuleType("factory_health")
factory_health.run_checks = lambda *args, **kwargs: []
factory_health._load_extra_envs = lambda *args, **kwargs: {}
sys.modules.setdefault("factory_health", factory_health)

for path in (str(ROOT_DIR), str(TOOLS_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

spec = importlib.util.spec_from_file_location(
    "command_center_sentinel_under_test", TOOLS_DIR / "command_center.py"
)
assert spec and spec.loader
command_center = importlib.util.module_from_spec(spec)
spec.loader.exec_module(command_center)

from tools import satory_camera_query  # noqa: E402


def test_openclaw_probe_sentinel_detector_is_exact_match():
    assert command_center._is_openclaw_probe_sentinel("OPENCLAW_518_WORKER_OK") is True
    assert command_center._is_openclaw_probe_sentinel("  OPENCLAW_518_WORKER_OK\n") is True
    assert command_center._is_openclaw_probe_sentinel("answer: OPENCLAW_518_WORKER_OK") is False
    assert command_center._is_openclaw_probe_sentinel("real answer") is False


def test_run_openclaw_replaces_probe_sentinel(monkeypatch):
    proc = types.SimpleNamespace(
        returncode=0,
        stdout="OPENCLAW_518_WORKER_OK\n",
        stderr="",
    )
    logged: list[tuple[str, str, str]] = []
    monkeypatch.setattr(command_center.subprocess, "run", lambda *args, **kwargs: proc)
    monkeypatch.setattr(
        command_center,
        "_log_probe_sentinel_leak",
        lambda correlation_id, query, response: logged.append((correlation_id, query, response)),
    )

    result = command_center._run_openclaw("Напиши последний номер", correlation_id="tg_1858")

    assert result == command_center.OPENCLAW_SENTINEL_FALLBACK_REPLY
    assert "OPENCLAW_518_WORKER_OK" not in result
    assert logged == [("tg_1858", "Напиши последний номер", "OPENCLAW_518_WORKER_OK")]


def test_tg_send_replaces_exact_probe_sentinel_before_telegram(monkeypatch):
    captured: dict[str, str] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps({"ok": True, "result": {"message_id": 1}}).encode()

    def fake_urlopen(req, timeout=0):
        captured["body"] = req.data.decode()
        return FakeResponse()

    monkeypatch.setenv("AUTONOMY_BYPASS", "1")
    monkeypatch.setattr(command_center.urllib.request, "urlopen", fake_urlopen)

    sent = command_center._tg_send("token", -1002064137259, "OPENCLAW_518_WORKER_OK", reply_to=1858)

    assert sent is True
    decoded = urllib.parse.parse_qs(captured["body"])
    text = decoded["text"][0]
    assert "служебный сигнал" in text
    assert "OPENCLAW_518_WORKER_OK" not in text


def test_last_plate_command_bypasses_models(monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(command_center, "_tg_send", lambda token, chat, text, reply_to=None: sent.append(text) or True)
    monkeypatch.setattr(command_center, "_run_openclaw", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("model called")))
    monkeypatch.setattr(command_center, "_run_codex", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("codex called")))
    monkeypatch.setattr(satory_camera_query, "get_last_plate_reply", lambda: "📷 Последний распознанный номер: <code>111AAA01</code>")

    handled = command_center.handle("token", -1002064137259, 1859, "/last-plate")

    assert handled is True
    assert sent == ["📷 Последний распознанный номер: <code>111AAA01</code>"]


def test_camera_query_format_does_not_hallucinate_when_event_missing():
    reply = satory_camera_query.format_last_plate_ru(None)

    assert "Не удалось получить" in reply
    assert "Номер:" not in reply


def test_camera_query_formats_plate_speed_photo_and_timestamp():
    event = {
        "license_plate": "111AAA01",
        "speed_kmh": 83,
        "speed_limit": 60,
        "camera_id": "LU-100-VAR",
        "is_violation": True,
        "timestamp": "2026-05-20T16:15:56.085+05:00",
        "photo_url": "https://api.nousagaas.com/photo/1.jpg",
    }

    reply = satory_camera_query.format_last_plate_ru(event, source_url="http://example/last")

    assert "<code>111AAA01</code>" in reply
    assert "83 км/ч" in reply
    assert "лимит 60" in reply
    assert "превышение +23" in reply
    assert "LU-100-VAR" in reply
    assert "2026-05-20T16:15:56.085+05:00" in reply
    assert "https://api.nousagaas.com/photo/1.jpg" in reply
