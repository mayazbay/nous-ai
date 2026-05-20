"""Tests for read-only model route auth probes.

These probes must classify route/billing type without making model calls.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import model_route_auth_probe as probe


def test_codex_probe_is_subscription_only_and_api_fallback_disabled(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    (home / ".codex" / "auth.json").write_text("{}", encoding="utf-8")

    with patch("model_route_auth_probe.shutil.which", return_value="/usr/local/bin/codex"):
        result = probe.probe_codex(home=home)

    assert result["route"] == "codex"
    assert result["billing_surface"] == "subscription"
    assert result["api_fallback_enabled"] is False
    assert result["live_model_call"] is False
    assert result["auth_present"] is True


def test_grok_probe_reports_xai_api_not_subscription_without_call() -> None:
    result = probe.probe_grok(env={"XAI_API_KEY": "xai-test"})

    assert result["route"] == "grok"
    assert result["billing_surface"] == "xai_api"
    assert result["route_type"] == "api_config"
    assert result["auth_present"] is True
    assert result["live_model_call"] is False


def test_collect_probes_covers_required_routes_without_live_model_calls(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()

    with patch("model_route_auth_probe.shutil.which", return_value=None):
        results = probe.collect_probes(home=home, env={})

    names = {item["route"] for item in results}
    assert {"codex", "grok", "claude_code", "hermes", "openclaw", "litellm"} <= names
    assert all(item["live_model_call"] is False for item in results)
    assert all("billing_surface" in item for item in results)
