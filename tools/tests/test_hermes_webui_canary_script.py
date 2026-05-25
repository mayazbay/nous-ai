from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "hermes_webui_canary.sh"


def test_webui_canary_defaults_to_nouscanary_profile() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'HERMES_WEBUI_PROFILE="${HERMES_WEBUI_PROFILE:-nouscanary}"' in text
    assert 'printf \'%s\\n\' "$HERMES_WEBUI_PROFILE" > "$HERMES_BASE_HOME/active_profile"' in text


def test_webui_canary_exports_profile_home_for_runtime_tools() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'export HERMES_BASE_HOME="${HERMES_BASE_HOME:-$HOME_DIR/.hermes}"' in text
    assert 'export HERMES_HOME="${HERMES_BASE_HOME}/profiles/${HERMES_WEBUI_PROFILE}"' in text
    assert 'export HERMES_MODEL="${HERMES_MODEL:-gpt-5.5}"' in text
    assert 'echo "profile-home: $HERMES_HOME"' in text


def test_webui_canary_seeds_factory_surface() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'HERMES_WEBUI_FACTORY_SKILLS_DIR="${HERMES_WEBUI_FACTORY_SKILLS_DIR:-$HOME_DIR/nous-agaas/skills}"' in text
    assert 'hermes_webui_factory_seed.py' in text


def test_webui_canary_patches_skills_api_compatibility() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "ensure_agent_skill_sort_shim" in text
    assert "def _sort_skills(skills):" in text
    assert "WebUI v0.51.92 imports _sort_skills" in text


def test_webui_canary_tags_external_history_to_profile() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "ensure_external_session_profile_shim" in text
    assert "'profile': os.getenv('HERMES_WEBUI_PROFILE') or None" in text


def test_webui_canary_uses_mcp_inventory_cache_for_dashboard() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "ensure_mcp_inventory_cache_shim" in text
    assert "mcp_inventory.json" in text
    assert "startup probe" in text


def test_webui_canary_adds_factory_events_api_shim() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "ensure_factory_events_api_shim" in text
    assert 'if parsed.path == "/api/factory-events"' in text
    assert "ops_events.jsonl" in text
    assert "factory-self-heal.jsonl" in text
    assert "satory-ai-factory-queue-status.md" in text
