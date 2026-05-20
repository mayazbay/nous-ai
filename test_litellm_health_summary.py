import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import litellm_health_summary as lhs


def test_default_summary_ignores_codex_api_and_embedding_health_noise(monkeypatch):
    monkeypatch.delenv("MODEL_HEALTH_IGNORED_MODELS", raising=False)
    payload = {
        "healthy_endpoints": [
            {"model": "openrouter/deepseek/deepseek-v4-flash"},
            {"model": "anthropic/claude-sonnet-4-6"},
        ],
        "unhealthy_endpoints": [
            {"model": "gpt-5.5"},
            {"model": "gemini/gemini-embedding-001"},
        ],
    }

    assert lhs.summarize(payload, lhs.ignored_models()) == (2, 0, "none")


def test_summary_keeps_real_chat_model_failure_visible(monkeypatch):
    monkeypatch.setenv("MODEL_HEALTH_IGNORED_MODELS", "gpt-5.5,gemini/gemini-embedding-001")
    payload = {
        "healthy_endpoints": [{"model": "openrouter/deepseek/deepseek-v4-pro:nitro"}],
        "unhealthy_endpoints": [
            {"model": "gpt-5.5"},
            {"model": "anthropic/claude-sonnet-4-6"},
        ],
    }

    assert lhs.summarize(payload, lhs.ignored_models()) == (
        1,
        1,
        "anthropic/claude-sonnet-4-6",
    )


def test_error_payload_is_not_misreported_as_zero_models(monkeypatch):
    monkeypatch.delenv("MODEL_HEALTH_IGNORED_MODELS", raising=False)
    payload = {"error": {"message": "No auth credentials found"}}

    try:
        lhs.summarize(payload, lhs.ignored_models())
    except ValueError as exc:
        assert "LiteLLM /health" in str(exc)
    else:
        raise AssertionError("expected ValueError for non-health payload")
