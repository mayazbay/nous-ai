"""Tests for _codex_daily_budget_ok gating on call + token caps.

Regression: session-... 2026-05-20. Assylbek (@aliakbar_asylbek) asked the bot
"видишь события? поток подали" through `/ask` (no prefix). LangGraph routed it
to ROUTE_CHATGPT_EXECUTION. _codex_daily_budget_ok returned (True, $X.XX)
because it only checked USD spend (<$5), NOT the daily TOKEN cap. _run_codex
was called, hit the token cap (312163 > 250000), and returned the verbatim
"Daily /codex token cap reached: 312163 / 250000 observed tokens" string,
which was sent to Assylbek as the bot's "answer."

Fix: _codex_daily_budget_ok must also check CODEX_DAILY_CAP_CALLS and
CODEX_DAILY_CAP_TOKENS. When either is exceeded it returns (False, spend) so
auto-escalation paths skip codex and fall through to grok-ceo Tier-1.

See ceo-hierarchy AP-40 (added this session).
"""
from __future__ import annotations

import json
import sys
import types
import importlib.util
from datetime import date, datetime
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]

cost_tracker = types.ModuleType("cost_tracker")
cost_tracker.daily_report = lambda *args, **kwargs: {}
cost_tracker.format_report = lambda *args, **kwargs: ""
sys.modules.setdefault("cost_tracker", cost_tracker)

factory_health = types.ModuleType("factory_health")
factory_health.run_checks = lambda *args, **kwargs: []
factory_health._load_extra_envs = lambda *args, **kwargs: {}
sys.modules.setdefault("factory_health", factory_health)

sys.path.insert(0, str(TOOLS_DIR))
spec = importlib.util.spec_from_file_location(
    "command_center_budget_under_test", TOOLS_DIR / "command_center.py"
)
assert spec and spec.loader
command_center = importlib.util.module_from_spec(spec)
spec.loader.exec_module(command_center)


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _seed_usage(tmp_path: Path, count: int, tokens: int) -> Path:
    usage_file = tmp_path / "codex_usage.json"
    usage_file.write_text(
        json.dumps({"date": _today_str(), "count": count, "tokens": tokens})
    )
    return usage_file


def test_budget_ok_true_when_all_caps_under(tmp_path, monkeypatch):
    usage = _seed_usage(tmp_path, count=1, tokens=100)
    monkeypatch.setattr(command_center, "CODEX_USAGE_FILE", str(usage))
    monkeypatch.setattr(command_center, "CODEX_DAILY_CAP_CALLS", 10)
    monkeypatch.setattr(command_center, "CODEX_DAILY_CAP_TOKENS", 250000)
    # Force ask-hierarchy.jsonl to look missing so USD spend = 0
    monkeypatch.setattr(
        "os.path.expanduser",
        lambda p: "/nonexistent/missing.jsonl" if "ask-hierarchy" in p else p,
    )

    ok, spend = command_center._codex_daily_budget_ok()

    assert ok is True, "budget should be available when all caps are under"
    assert spend == 0.0


def test_budget_ok_false_when_token_cap_exceeded(tmp_path, monkeypatch):
    """REGRESSION GUARD — was the actual bug Assylbek triggered."""
    usage = _seed_usage(tmp_path, count=3, tokens=312163)
    monkeypatch.setattr(command_center, "CODEX_USAGE_FILE", str(usage))
    monkeypatch.setattr(command_center, "CODEX_DAILY_CAP_CALLS", 10)
    monkeypatch.setattr(command_center, "CODEX_DAILY_CAP_TOKENS", 250000)
    monkeypatch.setattr(
        "os.path.expanduser",
        lambda p: "/nonexistent/missing.jsonl" if "ask-hierarchy" in p else p,
    )

    ok, _spend = command_center._codex_daily_budget_ok()

    assert ok is False, (
        "When CODEX_DAILY_CAP_TOKENS is exceeded, _codex_daily_budget_ok must "
        "return False so /ask auto-escalation falls through to grok-ceo instead "
        "of calling _run_codex and returning the verbatim cap-error string."
    )


def test_budget_ok_false_when_call_cap_exceeded(tmp_path, monkeypatch):
    usage = _seed_usage(tmp_path, count=99, tokens=100)
    monkeypatch.setattr(command_center, "CODEX_USAGE_FILE", str(usage))
    monkeypatch.setattr(command_center, "CODEX_DAILY_CAP_CALLS", 10)
    monkeypatch.setattr(command_center, "CODEX_DAILY_CAP_TOKENS", 250000)
    monkeypatch.setattr(
        "os.path.expanduser",
        lambda p: "/nonexistent/missing.jsonl" if "ask-hierarchy" in p else p,
    )

    ok, _spend = command_center._codex_daily_budget_ok()

    assert ok is False, "call cap should fail the budget gate"


def test_is_codex_cap_blocked_detects_token_cap_sentinel():
    sentinel = "Daily /codex token cap reached: 312163 / 250000 observed tokens. Resets midnight Almaty."
    assert command_center._is_codex_cap_blocked(sentinel) is True


def test_is_codex_cap_blocked_detects_call_cap_sentinel():
    sentinel = "Daily /codex cap reached: 100 / 10 calls (50000 tokens observed). Resets midnight Almaty."
    assert command_center._is_codex_cap_blocked(sentinel) is True


def test_is_codex_cap_blocked_false_for_real_codex_answer():
    real_answer = "Looking at the routing logic, here's what I found...\n\nThe issue is..."
    assert command_center._is_codex_cap_blocked(real_answer) is False


def test_is_codex_cap_blocked_false_for_empty_response():
    assert command_center._is_codex_cap_blocked("") is False
    assert command_center._is_codex_cap_blocked(None) is False


def test_is_codex_cap_blocked_tolerates_leading_whitespace():
    sentinel = "\n  Daily /codex token cap reached: ..."
    assert command_center._is_codex_cap_blocked(sentinel) is True


def test_ap41_mandatory_codex_grok_fallback_handler_exists():
    """Regression guard: the dispatcher must NOT call _mandatory_codex_blocked_message.

    AP-41 supersedes AP-30 for user-facing replies. When mandatory codex is
    blocked, we now fall back to grok-ceo with a transparent notice (Russian
    for groups, English for DM) instead of bouncing English wall-of-text.
    """
    import inspect
    handle_src = inspect.getsource(command_center.handle)
    # Must contain the new fallback tag
    assert "/ask-mandatory-codex-grok-fallback" in handle_src, (
        "AP-41 dispatcher missing — mandatory codex blocked path must fall back to grok-ceo"
    )
    # Must NOT relay the old blocked-message verbatim to user
    assert "_mandatory_codex_blocked_message(query, _today_spend)" not in handle_src, (
        "AP-41 regression — dispatcher still calls _mandatory_codex_blocked_message; "
        "this returns English wall-of-text that bounces real users."
    )
    # Russian fallback notice for group chats
    assert "Codex недоступен" in handle_src, (
        "AP-41: Russian fallback notice missing for group-chat mandatory-blocked path"
    )


def test_ap41_shell_verification_fallback_russian_for_groups():
    """Shell-verification cap-fallback must show Russian notice in groups."""
    import inspect
    handle_src = inspect.getsource(command_center.handle)
    assert "Использую grok-ceo для shell-проверки" in handle_src, (
        "Shell-verification fallback notice missing Russian translation for groups"
    )


# --- AP-42: credential-handoff decline is actionable, not just polite ------

def test_ap42_credential_handoff_reply_lists_safe_alternatives():
    """The group-chat credential decline must offer concrete alternatives,
    not just say "we don't publish."

    Background: 2026-05-20 Madi tried "trust the log in and password. i give
    permission. do it now." in the Satory group. Bot replied with the polite
    "Принято. Доступы в общем чате не публикуем." Madi: "why? why did not work?"
    Decision: keep the safety regex strict (no text-parsed owner-override —
    sender prefix is parseable, group safety > convenience), but make the
    decline ACTIONABLE so the owner has a clear next-step path.

    See ceo-hierarchy AP-42 (2026-05-20).
    """
    import inspect
    src = inspect.getsource(command_center.handle_owner_credential_handoff)

    # Honest about why
    assert "Доступы в общих чатах не публикую" in src, (
        "Decline message missing the policy statement"
    )
    assert "даже с явным разрешением" in src, (
        "Decline must call out that explicit authorization is also refused"
    )
    # Actionable alternatives
    assert "Открой DM" in src, "Missing DM-to-target alternative"
    assert "Самосерв" in src or "админке" in src, "Missing self-serve alternative"
    assert "DM мне приватно" in src, "Missing private-DM-to-bot alternative"
    # Context still forwarded to owner (for non-owner senders)
    assert "Передано владельцу" in src, "Owner DM relay must remain for non-owner sender path"
    # AP-43: owner-sender path skips the redundant DM echo
    assert "sender=owner, no DM echo" in src, (
        "AP-43 owner-DM-echo skip missing — when sender IS owner, the bot must "
        "not DM the owner a copy of their own message"
    )
    assert "Креды в группах не публикую — даже с твоим разрешением" in src, (
        "AP-43 terse owner-mode group reply missing"
    )


def test_query_likely_needs_high_judgment_false_when_token_cap_exceeded(
    tmp_path, monkeypatch
):
    """High-judgment auto-escalation must not fire when codex is capped."""
    usage = _seed_usage(tmp_path, count=3, tokens=312163)
    monkeypatch.setattr(command_center, "CODEX_USAGE_FILE", str(usage))
    monkeypatch.setattr(command_center, "CODEX_DAILY_CAP_CALLS", 10)
    monkeypatch.setattr(command_center, "CODEX_DAILY_CAP_TOKENS", 250000)
    monkeypatch.setattr(
        "os.path.expanduser",
        lambda p: "/nonexistent/missing.jsonl" if "ask-hierarchy" in p else p,
    )

    # Query that would otherwise be high-judgment (>200 chars + has marker)
    query = (
        "Please give me a deep analysis of the trade-offs between routing strategies. "
        "Should we use OpenClaw routine for chat-class messages or auto-escalate to "
        "codex for high-judgment? Compare and contrast root cause vs symptom fixes here."
    )
    assert len(query) >= 200, "test fixture must exceed 200-char gate"
    assert "deep analysis" in query.lower(), "test fixture must contain marker"

    result = command_center._query_likely_needs_high_judgment(query)

    assert result is False, (
        "_query_likely_needs_high_judgment must return False when codex token cap "
        "is exceeded, otherwise the high-judgment auto-escalation path calls "
        "_run_codex and returns the verbatim cap-error to the user."
    )
