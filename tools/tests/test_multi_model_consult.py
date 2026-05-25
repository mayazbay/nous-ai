"""Tests for multi_model_consult.py — all mocked, zero live API calls.

Run: python3 -m pytest tools/tests/test_multi_model_consult.py -v

Covers:
  - consult_id format
  - parallel ThreadPoolExecutor invocation
  - arbitration on partial success (2 succeed, 1 fails)
  - arbitration on all-3 success
  - canonical JSON schema keys present
  - dry-run mode: zero model calls
  - cost ledger JSONL append
  - xAI key fetched lazily via ssh+grep
"""

from __future__ import annotations

import json
import re
import ssl
import sys
from pathlib import Path
from typing import Any
from urllib.error import URLError
from unittest.mock import MagicMock, patch, call

import pytest

# Add tools/ to path so we can import multi_model_consult
REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import multi_model_consult as mmc

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

FAKE_QUESTION = "What is the current best practice for deploying DeepSeek on Air?"

GOOD_OPUS = {
    "model": mmc.MODEL_OPUS,
    "billing_surface": "anthropic_api",
    "answer": "Use LiteLLM on port 4000 with launchd. See pages/systems/architecture.md.",
    "confidence": 0.90,
    "tokens": 42,
    "latency_ms": 1200,
    "cost_usd": 0.012,
}

GOOD_CODEX = {
    "model": mmc.MODEL_CODEX,
    "billing_surface": "subscription",
    "answer": "Run litellm --config litellm_config.yaml. Check logs at ~/nous-agaas/logs/.",
    "confidence": 0.90,
    "tokens": 38,
    "latency_ms": 3000,
    "cost_usd": 0.0,
}

GOOD_GROK = {
    "model": mmc.MODEL_GROK,
    "billing_surface": "xai_api",
    "answer": "LiteLLM is the standard proxy. x.com/search confirms this approach is current.",
    "confidence": 0.80,
    "tokens": 45,
    "latency_ms": 4500,
    "cost_usd": 0.003,
}

FAILED_GROK = {
    "model": mmc.MODEL_GROK,
    "billing_surface": "xai_api",
    "error": "TimeoutError: timeout after 30s",
    "latency_ms": 30001,
    "cost_usd": 0.0,
}

ARB_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": json.dumps({
                    "winner_model": mmc.MODEL_CODEX,
                    "rationale": "Codex cited concrete log paths and a config file.",
                    "agree_count": 2,
                    "dissent_count": 1,
                })
            }
        }
    ],
    "usage": {"prompt_tokens": 200, "completion_tokens": 80},
}

CANONICAL_KEYS = {
    "consult_id",
    "question",
    "context_slug",
    "answers",
    "arbitration",
    "actionable_answer",
    "dissent_notes",
    "evidence_paths",
    "skill_update_proposal",
}

ARB_KEYS = {"winner_model", "rationale", "agree_count", "dissent_count", "arbitrator_model"}


def _make_wiki(tmp_path: Path) -> Path:
    (tmp_path / "pages" / "systems").mkdir(parents=True)
    (tmp_path / "pages" / "audits").mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# T1 — test_consult_id_format_is_valid
# ---------------------------------------------------------------------------

def test_consult_id_format_is_valid() -> None:
    ts = "2026-05-20T10:00:00Z"
    cid = mmc.make_consult_id(FAKE_QUESTION, ts)
    pattern = r"^consult_\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z_[0-9a-f]{8}$"
    assert re.match(pattern, cid), f"consult_id {cid!r} does not match pattern"
    # Deterministic given same inputs
    assert cid == mmc.make_consult_id(FAKE_QUESTION, ts)
    # Different question → different sha8
    cid2 = mmc.make_consult_id("Different question", ts)
    assert cid != cid2


# ---------------------------------------------------------------------------
# T2 — test_parallel_calls_use_threadpool
# ---------------------------------------------------------------------------

def test_parallel_calls_use_threadpool(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger_path = wiki / "pages" / "systems" / "test-ledger.jsonl"

    with (
        patch.object(mmc, "_call_opus", return_value=GOOD_OPUS) as m_opus,
        patch.object(mmc, "_call_codex", return_value=GOOD_CODEX) as m_codex,
        patch.object(mmc, "_call_grok", return_value=GOOD_GROK) as m_grok,
        patch.object(mmc, "_arbitrate", return_value={
            "winner_model": mmc.MODEL_CODEX,
            "rationale": "mock",
            "agree_count": 2,
            "dissent_count": 1,
            "arbitrator_model": mmc.MODEL_ARBITRATOR,
            "arbitrator_cost_usd": 0.0001,
        }) as m_arb,
    ):
        result = mmc.consult(
            question=FAKE_QUESTION,
            wiki=wiki,
            ledger_path=ledger_path,
        )

    assert m_opus.call_count == 1, "Opus should be called exactly once"
    assert m_codex.call_count == 1, "Codex should be called exactly once"
    assert m_grok.call_count == 1, "Grok should be called exactly once"
    assert m_arb.call_count == 1, "Arbitrator should be called exactly once"
    assert len(result["answers"]) == 3


# ---------------------------------------------------------------------------
# T3 — test_arbitration_runs_on_partial_success (2 succeed, 1 fail)
# ---------------------------------------------------------------------------

def test_arbitration_runs_on_partial_success(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger_path = wiki / "pages" / "systems" / "test-ledger.jsonl"

    captured_answers: list[Any] = []

    def fake_arbitrate(answers, question):
        captured_answers.extend(answers)
        successful = [a for a in answers if "answer" in a]
        return {
            "winner_model": successful[0]["model"] if successful else None,
            "rationale": "partial test",
            "agree_count": len(successful),
            "dissent_count": len(answers) - len(successful),
            "arbitrator_model": mmc.MODEL_ARBITRATOR,
            "arbitrator_cost_usd": 0.0,
        }

    with (
        patch.object(mmc, "_call_opus", return_value=GOOD_OPUS),
        patch.object(mmc, "_call_codex", return_value=GOOD_CODEX),
        patch.object(mmc, "_call_grok", return_value=FAILED_GROK),
        patch.object(mmc, "_arbitrate", side_effect=fake_arbitrate),
    ):
        result = mmc.consult(
            question=FAKE_QUESTION,
            wiki=wiki,
            ledger_path=ledger_path,
        )

    # All 3 answers passed to arbitrate (including the failed one)
    assert len(captured_answers) == 3
    # Failed grok is in answers
    failed = [a for a in captured_answers if "error" in a]
    assert len(failed) == 1
    assert failed[0]["model"] == mmc.MODEL_GROK
    # Successful ones are still there
    successful = [a for a in captured_answers if "answer" in a]
    assert len(successful) == 2
    # Result tracks unavailable
    assert mmc.MODEL_GROK in result.get("model_unavailable", [])


# ---------------------------------------------------------------------------
# T4 — test_arbitration_runs_on_all_3_success
# ---------------------------------------------------------------------------

def test_arbitration_runs_on_all_3_success(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger_path = wiki / "pages" / "systems" / "test-ledger.jsonl"

    arb_result = {
        "winner_model": mmc.MODEL_CODEX,
        "rationale": "Best evidence.",
        "agree_count": 2,
        "dissent_count": 1,
        "arbitrator_model": mmc.MODEL_ARBITRATOR,
        "arbitrator_cost_usd": 0.0001,
    }

    with (
        patch.object(mmc, "_call_opus", return_value=GOOD_OPUS),
        patch.object(mmc, "_call_codex", return_value=GOOD_CODEX),
        patch.object(mmc, "_call_grok", return_value=GOOD_GROK),
        patch.object(mmc, "_arbitrate", return_value=arb_result),
    ):
        result = mmc.consult(
            question=FAKE_QUESTION,
            wiki=wiki,
            ledger_path=ledger_path,
        )

    assert result["arbitration"]["winner_model"] == mmc.MODEL_CODEX
    assert result["arbitration"]["agree_count"] == 2
    assert result["actionable_answer"] == GOOD_CODEX["answer"]
    assert "model_unavailable" not in result or result.get("model_unavailable") == []


# ---------------------------------------------------------------------------
# T5 — test_returns_canonical_json_schema
# ---------------------------------------------------------------------------

def test_returns_canonical_json_schema(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger_path = wiki / "pages" / "systems" / "test-ledger.jsonl"

    with (
        patch.object(mmc, "_call_opus", return_value=GOOD_OPUS),
        patch.object(mmc, "_call_codex", return_value=GOOD_CODEX),
        patch.object(mmc, "_call_grok", return_value=GOOD_GROK),
        patch.object(mmc, "_arbitrate", return_value={
            "winner_model": mmc.MODEL_OPUS,
            "rationale": "Best cited sources.",
            "agree_count": 3,
            "dissent_count": 0,
            "arbitrator_model": mmc.MODEL_ARBITRATOR,
            "arbitrator_cost_usd": 0.0001,
        }),
    ):
        result = mmc.consult(
            question=FAKE_QUESTION,
            wiki=wiki,
            ledger_path=ledger_path,
        )

    # All canonical top-level keys present
    for key in CANONICAL_KEYS:
        assert key in result, f"Missing canonical key: {key!r}"

    # answers is a list of 3
    assert isinstance(result["answers"], list)
    assert len(result["answers"]) == 3

    # Each answer has required fields
    for ans in result["answers"]:
        assert "model" in ans

    # arbitration has required keys
    for key in ARB_KEYS:
        assert key in result["arbitration"], f"Missing arbitration key: {key!r}"

    # evidence_paths is a list
    assert isinstance(result["evidence_paths"], list)

    # consult_id matches pattern
    pattern = r"^consult_\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z_[0-9a-f]{8}$"
    assert re.match(pattern, result["consult_id"])


# ---------------------------------------------------------------------------
# T6 — test_dry_run_prints_intent_without_calls
# ---------------------------------------------------------------------------

def test_dry_run_prints_intent_without_calls(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger_path = wiki / "pages" / "systems" / "test-ledger.jsonl"

    with (
        patch.object(mmc, "_call_opus", return_value=GOOD_OPUS) as m_opus,
        patch.object(mmc, "_call_codex", return_value=GOOD_CODEX) as m_codex,
        patch.object(mmc, "_call_grok", return_value=GOOD_GROK) as m_grok,
        patch.object(mmc, "_arbitrate", return_value={}) as m_arb,
    ):
        result = mmc.consult(
            question=FAKE_QUESTION,
            dry_run=True,
            wiki=wiki,
            ledger_path=ledger_path,
        )

    # No model calls made
    assert m_opus.call_count == 0, "Opus must not be called in dry-run"
    assert m_codex.call_count == 0, "Codex must not be called in dry-run"
    assert m_grok.call_count == 0, "Grok must not be called in dry-run"
    assert m_arb.call_count == 0, "Arbitrator must not be called in dry-run"

    # Result signals dry_run
    assert result.get("dry_run") is True
    # consult_id still present
    assert "consult_id" in result
    # No ledger written in dry-run
    assert not ledger_path.exists(), "Ledger must not be written in dry-run"


# ---------------------------------------------------------------------------
# T7 — test_cost_ledger_appends_jsonl_line
# ---------------------------------------------------------------------------

def test_cost_ledger_appends_jsonl_line(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger_path = wiki / "pages" / "systems" / "test-ledger.jsonl"

    arb = {
        "winner_model": mmc.MODEL_OPUS,
        "rationale": "Best.",
        "agree_count": 3,
        "dissent_count": 0,
        "arbitrator_model": mmc.MODEL_ARBITRATOR,
        "arbitrator_cost_usd": 0.0001,
    }

    with (
        patch.object(mmc, "_call_opus", return_value=GOOD_OPUS),
        patch.object(mmc, "_call_codex", return_value=GOOD_CODEX),
        patch.object(mmc, "_call_grok", return_value=GOOD_GROK),
        patch.object(mmc, "_arbitrate", return_value=arb),
    ):
        # First consult
        mmc.consult(
            question=FAKE_QUESTION,
            wiki=wiki,
            ledger_path=ledger_path,
        )
        # Second consult (tests append, not overwrite)
        mmc.consult(
            question="Second question for ledger test",
            wiki=wiki,
            ledger_path=ledger_path,
        )

    assert ledger_path.exists(), "Ledger file must be created"
    lines = [l for l in ledger_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2, f"Expected 2 JSONL lines, got {len(lines)}"

    for line in lines:
        entry = json.loads(line)
        assert "consult_id" in entry
        assert "ts" in entry
        assert "question_head" in entry
        assert "total_cost_usd" in entry
        assert "winner_model" in entry
        assert "billing_surfaces" in entry


def test_paid_api_guard_blocks_opus_and_grok_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default policy must not fetch API keys or make paid Opus/Grok calls."""
    monkeypatch.delenv("NOUS_PAID_API_ALLOWED", raising=False)
    monkeypatch.delenv("NOUS_PAID_API_CAP_USD", raising=False)
    monkeypatch.delenv("NOUS_PAID_API_REASON", raising=False)

    with (
        patch.object(mmc, "_fetch_anthropic_key") as fetch_anthropic,
        patch.object(mmc, "_fetch_xai_key") as fetch_xai,
        patch.object(mmc, "_http_post_json") as http_post,
    ):
        opus = mmc._call_opus("q", "ctx")
        grok = mmc._call_grok("q", "ctx")

    assert opus["billing_surface"] == "anthropic_api"
    assert grok["billing_surface"] == "xai_api"
    assert "paid_api_disabled" in opus["error"]
    assert "paid_api_disabled" in grok["error"]
    fetch_anthropic.assert_not_called()
    fetch_xai.assert_not_called()
    http_post.assert_not_called()


def test_local_opus_answer_is_local_and_allowed_when_paid_guard_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NOUS_PAID_API_ALLOWED", raising=False)

    result = mmc._call_opus("q", "ctx", local_answer="already answered by local Opus")

    assert result["billing_surface"] == "local"
    assert result["answer"] == "already answered by local Opus"
    assert result["cost_usd"] == 0.0


def test_consult_records_billing_surface_summary_in_result_and_ledger(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger_path = wiki / "pages" / "systems" / "test-ledger.jsonl"

    with (
        patch.object(mmc, "_call_opus", return_value=GOOD_OPUS),
        patch.object(mmc, "_call_codex", return_value=GOOD_CODEX),
        patch.object(mmc, "_call_grok", return_value=GOOD_GROK),
        patch.object(mmc, "_arbitrate", return_value={
            "winner_model": mmc.MODEL_CODEX,
            "rationale": "mock",
            "agree_count": 2,
            "dissent_count": 1,
            "arbitrator_model": mmc.MODEL_ARBITRATOR,
            "arbitrator_cost_usd": 0.0,
            "billing_surface": "openrouter",
        }),
    ):
        result = mmc.consult(question=FAKE_QUESTION, wiki=wiki, ledger_path=ledger_path)

    assert result["billing_surfaces"] == {
        mmc.MODEL_OPUS: "anthropic_api",
        mmc.MODEL_CODEX: "subscription",
        mmc.MODEL_GROK: "xai_api",
        mmc.MODEL_ARBITRATOR: "openrouter",
    }
    entry = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[-1])
    assert entry["billing_surfaces"] == result["billing_surfaces"]
    assert entry["paid_api_policy"]["allowed"] is False


# ---------------------------------------------------------------------------
# T8 — test_xai_key_fetched_lazily
# ---------------------------------------------------------------------------

def test_xai_key_fetched_lazily(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """xAI key must be fetched via ssh+grep (subprocess), never from env in this test."""
    # Ensure XAI_API_KEY is not in env so ssh fetch path is hit
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    fake_key = "xai-test-key-abc123"
    ssh_output = f"XAI_API_KEY={fake_key}\n"

    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ssh_output
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        key = mmc._fetch_xai_key()

    assert key == fake_key, f"Expected {fake_key!r}, got {key!r}"

    # Verify subprocess was called with ssh + grep (key fetched lazily)
    assert mock_run.called
    args = mock_run.call_args[0][0]
    assert "ssh" in args, f"Expected ssh in subprocess args: {args}"
    assert AIR_HOST_IN_ARGS(args), f"Expected {mmc.AIR_HOST!r} in subprocess args: {args}"
    assert any("grep" in str(a) for a in args), f"Expected grep in subprocess args: {args}"


def AIR_HOST_IN_ARGS(args: list) -> bool:
    return any(mmc.AIR_HOST in str(a) for a in args)


# ---------------------------------------------------------------------------
# Additional edge-case test: all models fail → no actionable answer
# ---------------------------------------------------------------------------

def test_all_models_fail_returns_empty_actionable_answer(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger_path = wiki / "pages" / "systems" / "test-ledger.jsonl"

    failed = {"model": mmc.MODEL_OPUS, "error": "APIError", "cost_usd": 0.0, "latency_ms": 100}
    failed_codex = {"model": mmc.MODEL_CODEX, "error": "ssh failed", "cost_usd": 0.0, "latency_ms": 200}
    failed_grok = {"model": mmc.MODEL_GROK, "error": "key not found", "cost_usd": 0.0, "latency_ms": 300}

    with (
        patch.object(mmc, "_call_opus", return_value=failed),
        patch.object(mmc, "_call_codex", return_value=failed_codex),
        patch.object(mmc, "_call_grok", return_value=failed_grok),
    ):
        result = mmc.consult(
            question=FAKE_QUESTION,
            wiki=wiki,
            ledger_path=ledger_path,
        )

    assert result["actionable_answer"] == ""
    arb = result["arbitration"]
    assert arb.get("winner_model") is None
    assert "all_models_failed" in arb.get("error", "")
    assert set(result.get("model_unavailable", [])) == {mmc.MODEL_OPUS, mmc.MODEL_CODEX, mmc.MODEL_GROK}


def test_default_context_slug_uses_continuity_packet(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger_path = wiki / "pages" / "systems" / "test-ledger.jsonl"
    packet_path = wiki / mmc.DEFAULT_CONTEXT_SLUG
    packet_path.write_text("shared continuity packet", encoding="utf-8")

    with (
        patch.object(mmc, "_refresh_continuity_packet") as refresh,
        patch.object(mmc, "_call_opus", return_value=GOOD_OPUS) as m_opus,
        patch.object(mmc, "_call_codex", return_value=GOOD_CODEX),
        patch.object(mmc, "_call_grok", return_value=GOOD_GROK),
        patch.object(mmc, "_arbitrate", return_value={
            "winner_model": mmc.MODEL_OPUS,
            "rationale": "mock",
            "agree_count": 3,
            "dissent_count": 0,
            "arbitrator_model": mmc.MODEL_ARBITRATOR,
            "arbitrator_cost_usd": 0.0,
        }),
    ):
        result = mmc.consult(question=FAKE_QUESTION, wiki=wiki, ledger_path=ledger_path)

    refresh.assert_called_once_with(wiki, mmc.DEFAULT_CONTEXT_SLUG)
    assert result["context_slug"] == mmc.DEFAULT_CONTEXT_SLUG
    assert m_opus.call_args[0][1] == "shared continuity packet"


def test_explicit_context_slug_overrides_continuity_packet(tmp_path: Path) -> None:
    wiki = _make_wiki(tmp_path)
    ledger_path = wiki / "pages" / "systems" / "test-ledger.jsonl"
    explicit = wiki / "pages" / "systems" / "explicit.md"
    explicit.write_text("explicit context wins", encoding="utf-8")

    with (
        patch.object(mmc, "_refresh_continuity_packet") as refresh,
        patch.object(mmc, "_call_opus", return_value=GOOD_OPUS) as m_opus,
        patch.object(mmc, "_call_codex", return_value=GOOD_CODEX),
        patch.object(mmc, "_call_grok", return_value=GOOD_GROK),
        patch.object(mmc, "_arbitrate", return_value={
            "winner_model": mmc.MODEL_OPUS,
            "rationale": "mock",
            "agree_count": 3,
            "dissent_count": 0,
            "arbitrator_model": mmc.MODEL_ARBITRATOR,
            "arbitrator_cost_usd": 0.0,
        }),
    ):
        result = mmc.consult(
            question=FAKE_QUESTION,
            context_slug="pages/systems/explicit.md",
            wiki=wiki,
            ledger_path=ledger_path,
        )

    refresh.assert_called_once_with(wiki, "pages/systems/explicit.md")
    assert result["context_slug"] == "pages/systems/explicit.md"
    assert m_opus.call_args[0][1] == "explicit context wins"


def test_http_post_json_retries_ssl_with_certifi(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b'{"ok": true}'

    calls: list[dict[str, Any]] = []

    def fake_urlopen(req, timeout, context=None):
        calls.append({"context": context})
        if len(calls) == 1:
            raise URLError(ssl.SSLCertVerificationError("certificate verify failed"))
        assert context == "certifi-context"
        return FakeResponse()

    monkeypatch.setattr(mmc, "urlopen", fake_urlopen)
    monkeypatch.setattr(mmc, "_certifi_ssl_context", lambda: "certifi-context")

    result = mmc._http_post_json(
        "https://api.x.ai/v1/chat/completions",
        {"model": "x", "messages": []},
        {"Authorization": "Bearer test"},
    )

    assert result == {"ok": True}
    assert len(calls) == 2


def test_fetch_litellm_master_key_checks_litellm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LITELLM_MASTER_KEY", raising=False)

    def fake_run(args, capture_output, text, timeout):
        proc = MagicMock()
        if "litellm/.env" in args[-1]:
            proc.returncode = 0
            proc.stdout = "LITELLM_MASTER_KEY=litellm-test-key\n"
            proc.stderr = ""
        else:
            proc.returncode = 1
            proc.stdout = ""
            proc.stderr = ""
        return proc

    with patch("subprocess.run", side_effect=fake_run):
        assert mmc._fetch_litellm_master_key() == "litellm-test-key"


def test_arbitrate_sends_litellm_master_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOUS_PAID_API_ALLOWED", "1")
    monkeypatch.setenv("NOUS_PAID_API_CAP_USD", "0.01")
    monkeypatch.setenv("NOUS_PAID_API_REASON", "unit test arbitration")
    captured: dict[str, Any] = {}

    def fake_post(url, payload, headers, timeout):
        captured["headers"] = headers
        return ARB_RESPONSE

    with (
        patch.object(mmc, "_fetch_litellm_master_key", return_value="litellm-secret"),
        patch.object(mmc, "_http_post_json", side_effect=fake_post),
    ):
        result = mmc._arbitrate([GOOD_OPUS, GOOD_CODEX], FAKE_QUESTION)

    assert result["winner_model"] == mmc.MODEL_CODEX
    assert captured["headers"]["Authorization"] == "Bearer litellm-secret"
