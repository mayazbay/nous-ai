import json

from tools import qmd_mcp_doctor as doctor


def test_parse_qmd_status_counts():
    text = """
Documents
  Total:    3333 files indexed
  Vectors:  40326 embedded
"""
    assert doctor.parse_qmd_status(text) == {"documents": 3333, "vectors": 40326}


def test_extract_mcp_text_concatenates_text_content():
    response = {
        "result": {
            "content": [
                {"type": "text", "text": "QMD Index Status"},
                {"type": "image", "data": "ignored"},
                {"type": "text", "text": "Total documents: 3333"},
            ]
        }
    }
    assert doctor.extract_mcp_text(response) == "QMD Index Status\nTotal documents: 3333"


def test_classify_underlying_qmd_green_requires_cli_stdio_http():
    checks = {
        "codex_config": {"ok": True},
        "qmd_cli": {"ok": True},
        "qmd_stdio": {"ok": True},
        "qmd_http": {"ok": True},
    }
    assert doctor.classify(checks) == "green:underlying_qmd_healthy_native_codex_tool_must_be_checked_in_session"


def test_classify_red_when_stdio_fails_even_if_cli_is_green():
    checks = {
        "codex_config": {"ok": True},
        "qmd_cli": {"ok": True},
        "qmd_stdio": {"ok": False},
        "qmd_http": {"ok": True},
    }
    assert doctor.classify(checks) == "red:qmd_stdio_server"


def test_classify_yellow_when_codex_config_missing_but_qmd_is_healthy():
    checks = {
        "codex_config": {"ok": False},
        "qmd_cli": {"ok": True},
        "qmd_stdio": {"ok": True},
        "qmd_http": {"ok": True},
    }
    assert doctor.classify(checks) == "yellow:codex_config_missing_underlying_qmd_healthy"


def test_json_output_shape(monkeypatch, capsys):
    monkeypatch.setattr(doctor, "check_codex_config", lambda timeout: {"ok": True, "elapsed_seconds": 0.01})
    monkeypatch.setattr(doctor, "check_qmd_cli", lambda host, wiki, timeout: {"ok": True, "elapsed_seconds": 0.02})
    monkeypatch.setattr(doctor, "check_qmd_stdio", lambda host, timeout: {"ok": True, "elapsed_seconds": 0.03})
    monkeypatch.setattr(doctor, "check_qmd_http", lambda host, url, timeout: {"ok": True, "elapsed_seconds": 0.04})
    monkeypatch.setattr("sys.argv", ["qmd_mcp_doctor.py", "--json"])
    assert doctor.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"] == "qmd_mcp_doctor"
    assert payload["classification"].startswith("green:")
