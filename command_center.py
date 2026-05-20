#!/usr/bin/env python3
"""
command_center.py — Telegram → OpenClaw command router

Routes /ask and /status commands from @nousAGaaSbot to the OpenClaw agent,
then replies to Madi with the agent response.

Integrated into telegram_poll.py: any text message starting with /ask or /status
is intercepted here before the normal vault-capture path.

Natural language is the operator surface. Slash commands are still supported
internally and for power users, but Telegram intake can map plain language to:
  /ask <query>   — route query through OpenClaw; cheap workers default to DeepSeek V4
  /codex <task>  — run CEO/high-judgment task via OpenAI Codex (gpt-5.5) on Air
  /code <task>   — run task via Claude Code (Sonnet 4.6, full tools, $5/day cap)
  /goal <goal>   — create a persistent goal and kick the OpenClaw goal cycle
  /status        — check Air runtime health (docker, disk, memory)
  /report        — today's factory cost report (tasks, tokens, USD)
  /health        — full factory health check (Docker + LiteLLM + disk)
  /help          — list available commands

Telegram message length limit: 4096 chars. Responses trimmed to MAX_MSG_LEN.
"""

import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import html as _html
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, "/Users/madia/nous-agaas")
from cost_tracker import daily_report, format_report
from factory_health import run_checks as _factory_run_checks, _load_extra_envs as _fh_load_envs
try:
    from langsmith_observer import emit_event as _langsmith_emit, text_digest as _langsmith_text_digest
except Exception:
    _langsmith_emit = None
    _langsmith_text_digest = None
try:
    from factory_orchestration_policy import (
        ROUTE_CHATGPT_EXECUTION,
        ROUTE_GROK_DECISION,
        ROUTE_LONG_WORK_GOAL,
        classify_text as _classify_factory_route,
        model_pipeline_for_text as _factory_model_pipeline,
    )
except Exception:
    ROUTE_CHATGPT_EXECUTION = "chatgpt_execution"
    ROUTE_GROK_DECISION = "grok_decision_review"
    ROUTE_LONG_WORK_GOAL = "long_work_goal"
    _classify_factory_route = None
    _factory_model_pipeline = None
try:
    from model_failover_state import (
        build_resume_prompt as _build_failover_resume_prompt,
        finish_event as _finish_failover_event,
        format_resume_status as _format_failover_resume_status,
        start_event as _start_failover_event,
    )
except Exception:
    _build_failover_resume_prompt = None
    _finish_failover_event = None
    _format_failover_resume_status = None
    _start_failover_event = None

log = logging.getLogger(__name__)

# ── constants ────────────────────────────────────────────────────────────────
VENV_PYTHON = "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
RUN_TASK    = "/Users/madia/nous-agaas/run_task.py"
ASK_TIMEOUT = 420       # seconds — ceo-hierarchy AP-3: grok-4.20-reasoning baseline 144s+; 300s barely sufficient on complex routing
MAX_MSG_LEN = 4000      # Telegram hard limit is 4096; leave 96 chars margin
ALMATY_TZ = ZoneInfo("Asia/Almaty")
QUIET_START = time(0, 30)
QUIET_END = time(8, 0)
URGENT_RE = re.compile(
    r"\b(urgent|broke|broken|down|prod|production|demo|critical|now|asap|crisis|"
    r"family|safety|legal|deadline|incident|override|force|срочно|демо|критично)\b",
    re.IGNORECASE,
)
GROUP_SENDER_CONTEXT_RE = re.compile(
    r"^/(?:ask|codex|code)\s+Telegram group sender\s+([^:]{1,80}):",
    re.IGNORECASE,
)
GROUP_PERSONAL_SALUTATION_RE = re.compile(r"^([@A-Za-zА-Яа-яЁё][@A-Za-zА-Яа-яЁё0-9_.-]{1,40}),\s+")
KNOWN_GROUP_SENDER_ALIASES = {
    "@aliakbar_asylbek": {"@aliakbar_asylbek", "aliakbar_asylbek", "asylbek", "assylbek", "асылбек", "асильбек"},
    "@madi_ayazbay": {"@madi_ayazbay", "madi_ayazbay", "madi", "мади"},
    "@vargar929": {"@vargar929", "vargar929", "denis", "денис"},
}
_CURRENT_GROUP_SENDER = ""
OWNER_CHAT_ID = int(os.environ.get("TELEGRAM_OWNER_CHAT_ID") or "110793056")
OWNER_USERNAME = os.environ.get("TELEGRAM_OWNER_USERNAME", "@madi_ayazbay")
CREDENTIAL_HANDOFF_RE = re.compile(
    r"(\blogin\b|\bpassword\b|credential|credentials|secret|token|api[-_\s]?key|"
    r"логин|парол|секрет|доступы|доступов|"
    r"(^|\n)\s*(test|prod|production|тест|прод)\s*:)",
    re.IGNORECASE,
)

# /code configuration — Claude Code headless mode
CLAUDE_CMD       = os.environ.get("CLAUDE_CMD", "/Users/madia/.npm-global/bin/claude")
CLAUDE_WORKDIR   = "/Users/madia/nous-agaas"   # where claude runs
CLAUDE_TIMEOUT   = 600                          # 10 min hard cap
CLAUDE_DAILY_CAP_USD = 5.0                      # daily USD cap per Madi 2026-04-15
CLAUDE_COST_FILE = "/Users/madia/nous-agaas/logs/claude_code_cost.json"

# /codex configuration — OpenAI Codex headless mode.
def _resolve_codex_cmd(extra_candidates: list[str] | None = None) -> str:
    """Resolve Codex CLI across Air app installs, Homebrew, npm, and PATH."""
    candidates: list[str | None] = [
        os.environ.get("CODEX_CMD"),
        *(extra_candidates or []),
        "/Applications/Codex.app/Contents/Resources/codex",
        "/opt/homebrew/bin/codex",
        "/usr/local/bin/codex",
        "/Users/madia/.npm-global/bin/codex",
        shutil.which("codex"),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return os.environ.get("CODEX_CMD") or shutil.which("codex") or "codex"


CODEX_CMD       = _resolve_codex_cmd()
CODEX_WORKDIR   = os.environ.get("CODEX_WORKDIR", "/Users/madia/nous-agaas")
CODEX_MODEL     = os.environ.get("CODEX_MODEL", "gpt-5.5")
CODEX_SANDBOX   = os.environ.get("CODEX_SANDBOX", "workspace-write")
CODEX_TIMEOUT   = int(os.environ.get("CODEX_TIMEOUT", "900"))
CODEX_DAILY_CAP_CALLS = int(os.environ.get("CODEX_DAILY_CAP_CALLS", "12"))
CODEX_DAILY_CAP_TOKENS = int(os.environ.get("CODEX_DAILY_CAP_TOKENS", "500000"))
CODEX_USAGE_FILE = "/Users/madia/nous-agaas/logs/codex_usage.json"
CODEX_PRIMARY_HOME = os.environ.get("CODEX_PRIMARY_HOME", "/Users/madia/.codex")
SATORY_EVENTS_API_URL = os.environ.get("SATORY_EVENTS_API_URL", "https://api.nousagaas.com/api/cameras")
SATORY_EVENTS_FROZEN_AT = "2026-04-05T22:08:05.856+05:00"
SATORY_EVENTS_RECENT_SECONDS = int(os.environ.get("SATORY_EVENTS_RECENT_SECONDS", "900"))
ASK_TIER_CHEAP_LOCAL_MODEL = os.environ.get("NOUS_ASK_CHEAP_LOCAL_MODEL", "local-mlx-coder").strip() or "local-mlx-coder"
ASK_TIER_CHEAP_FALLBACK_MODEL = os.environ.get("NOUS_ASK_CHEAP_FALLBACK_MODEL", "deepseek-v4-flash").strip() or "deepseek-v4-flash"


def _preview_task(task: str, limit: int = 90) -> str:
    compact = " ".join((task or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def _register_spawned_session(kind: str, task: str, scope: str = "*") -> str | None:
    """Make Telegram-spawned coding sessions visible in the shared registry."""
    script = os.path.join(CODEX_WORKDIR, "tools", "session_register.sh")
    if not os.path.exists(script):
        log.warning("session register script missing: %s", script)
        return None
    intent = f"Telegram {kind}: {_preview_task(task)}"
    try:
        proc = subprocess.run(
            ["bash", script, "--host", "air", "--intent", intent, "--scope", scope],
            cwd=CODEX_WORKDIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        log.warning("session register failed for %s: %s", kind, exc)
        return None
    if proc.returncode != 0:
        log.warning("session register failed for %s: %s", kind, (proc.stderr or proc.stdout or "").strip()[:300])
        return None
    session_id = (proc.stdout or "").strip().splitlines()[0] if (proc.stdout or "").strip() else ""
    return session_id or None


def _close_spawned_session(session_id: str | None, status: str = "ok") -> None:
    if not session_id:
        return
    script = os.path.join(CODEX_WORKDIR, "tools", "session_close.sh")
    if not os.path.exists(script):
        log.warning("session close script missing: %s", script)
        return
    try:
        proc = subprocess.run(
            ["bash", script, "--session-id", session_id, status],
            cwd=CODEX_WORKDIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            log.warning("session close failed for %s: %s", session_id, (proc.stderr or proc.stdout or "").strip()[:300])
    except Exception as exc:
        log.warning("session close failed for %s: %s", session_id, exc)


def _spawned_session_note(kind: str, session_id: str | None) -> str:
    if not session_id:
        return ""
    return (
        f"Runtime coordination: command_center registered this outer Telegram {kind} "
        f"session as `{session_id}` with broad scope `*`. command_center will close "
        "that outer session after your process exits. If you create helper lanes, "
        "register and close those helper IDs separately.\n\n"
    )

# Session-continuity preamble injected into every /code task (session 51, I-B).
# Substrate (HANDOFF/MEMORY/skills) is institutional memory that persists across
# ephemeral sessions. Each /code spawn is a fresh Claude Code CLI with no prior
# chat history — the preamble tells it where to find context so it can continue
# from where the last session left off. Karpathy/Tan-clean: session ephemeral,
# substrate compounds. ~180 tokens per call (~$0.001 overhead at Sonnet rates).
SESSION_CONTEXT_PREAMBLE = """You are a /code-spawned Claude Code agent in the Nous AGaaS vault at /Users/madia/nous-agaas/wiki.

Before acting, skim these for session-continuity context (just read, don't summarize):
0. Shared failover packet — run `python3 /Users/madia/nous-agaas/wiki/tools/agent_continuity_packet.py --wiki /Users/madia/nous-agaas/wiki`, then Read `/Users/madia/nous-agaas/wiki/pages/systems/AGENT-CONTINUITY-PACKET.md`. If refresh fails, read the existing packet and continue.
1. Most recent handoff — run `ls -t /Users/madia/nous-agaas/wiki/pages/progress/HANDOFF-AUTO-*.md | head -1` then Read that file.
2. MEMORY.md top-block — Read first 200 lines of `/Users/madia/nous-agaas/wiki/pages/progress/claude-memory/MEMORY.md`.
3. Runtime doctrine — Read `/Users/madia/nous-agaas/wiki/pages/skills/session-operating-contract/SKILL.md` (current version dictates DONE protocol + hard-banned list + failure→skill loop).
4. Coordination doctrine — Read `/Users/madia/nous-agaas/wiki/pages/skills/session-coordination/SKILL.md`.

Before any file edit, broad audit, or helper-agent dispatch, register and scan:
- `bash tools/session_register.sh --host air --intent "<short task>" --scope "<files/dirs>"`
- `bash tools/session_scan.sh --overlap-with "<files/dirs>"`
- use `git commit -o <paths>` for only your own edits
- close with `bash tools/session_close.sh --session-id <session_id> ok`

Then address this task:

"""

CODEX_CONTEXT_PREAMBLE = """You are a /codex-spawned OpenAI Codex agent in the Nous AGaaS runtime at /Users/madia/nous-agaas.

Before acting, skim these for session-continuity context (just read, do not summarize):
0. Shared failover packet: run `python3 /Users/madia/nous-agaas/wiki/tools/agent_continuity_packet.py --wiki /Users/madia/nous-agaas/wiki`, then read `/Users/madia/nous-agaas/wiki/pages/systems/AGENT-CONTINUITY-PACKET.md`. If refresh fails, read the existing packet and continue.
1. Most recent handoff: `ls -t /Users/madia/nous-agaas/wiki/pages/progress/HANDOFF-AUTO-*.md | head -1`.
2. MEMORY.md top-block: first 200 lines of `/Users/madia/nous-agaas/wiki/pages/progress/claude-memory/MEMORY.md`.
3. Runtime doctrine: `/Users/madia/nous-agaas/wiki/pages/skills/session-operating-contract/SKILL.md`.
4. Telegram routing doctrine: `/Users/madia/nous-agaas/wiki/pages/skills/command-center/SKILL.md`.
5. Coordination doctrine: `/Users/madia/nous-agaas/wiki/pages/skills/session-coordination/SKILL.md`.

Before any file edit, broad audit, or helper-agent dispatch, register and scan:
- `bash tools/session_register.sh --host air --intent "<short task>" --scope "<files/dirs>"`
- `bash tools/session_scan.sh --overlap-with "<files/dirs>"`
- use `git commit -o <paths>` for only your own edits
- close with `bash tools/session_close.sh --session-id <session_id> ok`

Top-tier supervisor contract:
- You are the Codex/GPT-5.5 supervisor for high-judgment, second-brain, architecture, external-reply, and customer-transformation tasks. Think first at the outcome level, then choose the smallest execution path.
- If durable follow-through or bulk work is needed, delegate through the existing OpenClaw/factory substrate (`/goal`, Todoist, `tools/goal_runner.py`, `tools/run_task.py`, gbrain/Obsidian/OpenBrain) instead of pretending one chat response is execution.
- Use Opus/Grok/Hermes only as named lanes with evidence: Opus for premium Claude review/escape hatch, Grok for adversarial decision review, Hermes as canary/watchdog until its gates are green.
- For team/customer-facing replies, write destination-first: lead with the result, benefit, proof, and next observable change. Do not explain internal machinery unless the recipient asked for it.

Keep changes surgical, verify before claiming done, and write durable learnings to SKILL.md + gbrain timeline when you fix a real root cause.

Task:

"""

HELP_TEXT = (
    "🤖 <b>@nousAGaaSbot</b>\n\n"
    "Talk normally in DM. In a group, address the bot naturally: <code>Фабрика, ...</code>, <code>Nous, ...</code>, <code>@nousAGaaSbot ...</code>, or <code>AI: ...</code>.\n\n"
    "Examples:\n"
    "• <code>статус фабрики</code> → runtime status\n"
    "• <code>цель: prove Satory factory works end-to-end</code> → persistent goal cycle\n"
    "• <code>use gpt 5.5 to audit this architecture</code> → Codex/GPT-5.5 lane\n"
    "• <code>Фабрика, сравни Negizone и KSL</code> → OpenClaw router\n\n"
    "Power commands still work: /ask, /codex, /code, /resume, /goal, /status, /health, /report, /trace, /handoff, /help.\n\n"
    "<i>Unaddressed group chatter is saved as context, not executed.</i>"
)


def _model_status_from_response(response: str) -> str:
    low = (response or "").lower()
    if low.startswith(("❌", "error", "codex error", "daily /codex cap", "💸")):
        return "error"
    if "timed out" in low or "timeout" in low:
        return "timeout"
    if "blocked" in low or "cap reached" in low:
        return "blocked"
    return "ok"


def _is_codex_cap_blocked(response: str) -> bool:
    """True iff `_run_codex` returned its daily-cap sentinel string.

    Use at /ask auto-escalation callsites to detect a race where the budget
    gate passed but the codex call landed after the cap was reached (e.g.,
    a concurrent call burned the remaining quota). When True, the caller
    must re-route to grok-ceo Tier-1 rather than relay the sentinel to the
    user. Direct `/codex` and `/resume codex` paths intentionally surface
    the sentinel — the user asked for codex explicitly. See ceo-hierarchy
    AP-40 (2026-05-20 Assylbek incident).
    """
    low = (response or "").lower().lstrip()
    return (
        low.startswith("daily /codex cap reached")
        or low.startswith("daily /codex token cap reached")
    )


def _failover_start(command: str, msg_id: int, chat_id: int, query: str, *, model: str, via: str) -> str | None:
    if _start_failover_event is None:
        return None
    try:
        return _start_failover_event(
            command=command,
            msg_id=msg_id,
            chat_id=chat_id,
            query=query,
            model=model,
            via=via,
        )
    except Exception as exc:
        log.warning("model failover start capture failed: command=%s msg_id=%s err=%s", command, msg_id, exc)
        return None


def _failover_finish(event_id: str | None, response: str, *, status: str | None = None, receipt: str | None = None) -> None:
    if not event_id or _finish_failover_event is None:
        return
    try:
        _finish_failover_event(
            event_id,
            status=status or _model_status_from_response(response),
            response=response,
            receipt=receipt,
        )
    except Exception as exc:
        log.warning("model failover finish capture failed: event_id=%s err=%s", event_id, exc)


def _resume_target_model(target: str) -> tuple[str, str, str] | None:
    normalized = (target or "").strip().lower()
    aliases = {
        "gpt": ("codex", CODEX_MODEL, "/resume -> /codex"),
        "codex": ("codex", CODEX_MODEL, "/resume -> /codex"),
        "openai": ("codex", CODEX_MODEL, "/resume -> /codex"),
        "claude": ("claude", "claude-code", "/resume -> /code"),
        "code": ("claude", "claude-code", "/resume -> /code"),
        "grok": ("grok", "grok-ceo", "/resume -> /ask grok-ceo"),
        "ask": ("grok", "grok-ceo", "/resume -> /ask grok-ceo"),
        "opus": ("opus", "opus", "/resume -> /ask-direct opus"),
    }
    return aliases.get(normalized)


# ── Telegram helpers ─────────────────────────────────────────────────────────

def _tg_send(bot_token: str, chat_id: int, text: str, reply_to: int | None = None) -> bool:
    """Send a Telegram message. Returns True on success, False on error.

    AP-4 gate (session 68p, musk-algorithm v1.1.0): pre-send detector scan blocks
    deference-dressed-as-autonomy phrases. Bypass: AUTONOMY_BYPASS=1 env var.
    """
    import os as _os, subprocess as _sub
    text = _neutralize_stale_group_salutation(chat_id, text)
    text = _sanitize_group_internal_error_reply(chat_id, text)
    if not _os.environ.get("AUTONOMY_BYPASS"):
        _detector = "/Users/madia/nous-agaas/tools/test_agent_autonomy.sh"
        if _os.path.exists(_detector):
            try:
                _r = _sub.run(["bash", _detector, "--stdin"], input=text,
                              capture_output=True, text=True, timeout=5)
                if _r.returncode != 0:
                    log.warning(f"_tg_send AP-4 BLOCKED (first 200 chars of text): {text[:200]!r}")
                    return False
            except Exception as _e:
                log.warning(f"_tg_send AP-4 check error (allow): {_e}")

    # Auto-escape stray < > & to prevent Telegram 400 Bad Request.
    # Restore intentional formatting tags we use in command_center responses.
    _safe = _html.escape(text, quote=False)
    for _tag in ("<b>", "</b>", "<i>", "</i>", "<code>", "</code>", "<pre>", "</pre>"):
        _safe = _safe.replace(_html.escape(_tag, quote=False), _tag)
    params: dict = {
        "chat_id": str(chat_id),
        "text": _safe[:MAX_MSG_LEN],
        "parse_mode": "HTML",
    }
    if reply_to:
        params["reply_to_message_id"] = str(reply_to)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if not result.get("ok"):
                log.warning(f"_tg_send not ok: {result}")
                return False
            sent_msg_id = result.get("result", {}).get("message_id")
            log.info(
                "_tg_send sent OK: chat=%s bot_msg_id=%s reply_to=%s text_len=%s",
                chat_id,
                sent_msg_id,
                reply_to or "",
                len(text),
            )
            return True
    except Exception as e:
        log.error(f"_tg_send failed: {e}")
        return False


def _is_group_chat(chat_id: int) -> bool:
    try:
        return int(chat_id) < 0
    except Exception:
        return False


GROUP_INTERNAL_ERROR_MARKERS = (
    "daily /codex cap reached",
    "daily /codex token cap reached",
    "mandatory /codex only",
    "codex budget/auth is unavailable",
    "no answer was generated by the cheap worker route",
)


def _sanitize_group_internal_error_reply(chat_id: int, text: str) -> str:
    """Last-line guard: external groups never see raw Codex/router internals."""
    if not _is_group_chat(chat_id):
        return str(text or "")
    cleaned = str(text or "")
    lower = cleaned.lower()
    if not any(marker in lower for marker in GROUP_INTERNAL_ERROR_MARKERS):
        return cleaned
    log.error("blocked internal Codex/router error from group reply: chat=%s text=%r", chat_id, cleaned[:240])
    return (
        "Коллеги, Codex сейчас недоступен по суточному лимиту. "
        "Внутреннюю ошибку в чат не отправляю.\n\n"
        "Запрос принят: отвечаю резервным маршрутом на русском и отдельно оставляю "
        "след для проверки владельцу."
    )


def _tg_react(bot_token: str, chat_id: int, msg_id: int, emoji: str = "👍") -> bool:
    """React to the source message instead of sending internal progress text."""
    params = {
        "chat_id": str(chat_id),
        "message_id": str(msg_id),
        "reaction": json.dumps([{"type": "emoji", "emoji": emoji}], ensure_ascii=False),
    }
    url = f"https://api.telegram.org/bot{bot_token}/setMessageReaction"
    req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode("utf-8"), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if not result.get("ok"):
                log.warning("_tg_react not ok: %s", result)
                return False
            log.info("_tg_react sent OK: chat=%s msg_id=%s emoji=%s", chat_id, msg_id, emoji)
            return True
    except Exception as e:
        log.warning("_tg_react failed: %s", e)
        return False


def _tg_progress(bot_token: str, chat_id: int, text: str, msg_id: int, emoji: str = "👍") -> bool:
    """Private chats get progress text; groups get a reaction to avoid spam."""
    if _is_group_chat(chat_id):
        if _tg_react(bot_token, chat_id, msg_id, emoji=emoji):
            return True
        return _tg_send(bot_token, chat_id, emoji, reply_to=msg_id)
    return _tg_send(bot_token, chat_id, text, reply_to=msg_id)


def _operator_visible_response(chat_id: int, response: str) -> str:
    """Hide model/cost bookkeeping from external group replies."""
    response = str(response or "")
    if not _is_group_chat(chat_id):
        return response
    cleaned = re.sub(r"\n\n—\nOpenAI Codex [^\n]*$", "", response, flags=re.DOTALL)
    cleaned = re.sub(r"\n\n— cost: \$[^\n]*$", "", cleaned, flags=re.DOTALL)
    return _sanitize_group_internal_error_reply(chat_id, cleaned.strip())


def needs_owner_credential_handoff(text: str) -> bool:
    """True when group text should bypass models and go owner-only."""
    return bool(CREDENTIAL_HANDOFF_RE.search(text or ""))


def _extract_group_message_body(text: str) -> str:
    marker = " Message: "
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return (text or "").strip()


def _resolve_owner_chat_id(owner_chat_id: int | None = None) -> int:
    if owner_chat_id is not None:
        return int(owner_chat_id)
    return int(OWNER_CHAT_ID)


def handle_owner_credential_handoff(
    bot_token: str,
    chat_id: int,
    msg_id: int,
    body: str,
    sender: str,
    owner_chat_id: int | None = None,
) -> bool:
    """Route credential-shaped group text to owner DM without echoing it in group."""
    if not _is_group_chat(chat_id):
        return False
    owner_id = _resolve_owner_chat_id(owner_chat_id)
    if not owner_id:
        log.error("owner credential handoff blocked: owner chat id missing")
        return False

    _tg_react(bot_token, chat_id, msg_id)

    # AP-43: when the credential-shaped message came from the OWNER themselves
    # in a group, don't DM the owner a copy of their own message — they already
    # saw it. Use a terser group reply pointed at the fastest manual path.
    # Owner-DM relay is preserved for NON-owner senders (the original purpose:
    # give the operator context to act when a coworker asks for credentials).
    sender_handle = (sender or "").strip().lower().lstrip("@")
    owner_handle = OWNER_USERNAME.strip().lower().lstrip("@")
    sender_is_owner = bool(sender_handle) and sender_handle == owner_handle

    if sender_is_owner:
        group_reply = (
            "🔐 Креды в группах не публикую — даже с твоим разрешением. "
            "Групповая история постоянна, пересылаема, индексируема.\n"
            "Самый быстрый путь: открой DM с нужным человеком и скинь туда (10 сек). "
            "Или в админке дашборда: пригласить по email/username."
        )
        group_ok = _tg_send(bot_token, chat_id, group_reply, reply_to=msg_id)
        log.info(
            "owner credential handoff (sender=owner, no DM echo): chat=%s msg_id=%s group_ok=%s",
            chat_id, msg_id, group_ok,
        )
        return bool(group_ok)

    group_reply = (
        "🔐 Доступы в общих чатах не публикую — никогда, даже с явным разрешением "
        "(защита от случайных утечек: групповая история видна всем участникам, "
        "пересылается, индексируется).\n\n"
        "Безопасные варианты:\n"
        "1. Открой DM с тем, кому нужен доступ, и поделись там напрямую.\n"
        "2. Самосерв в админке дашборда (если включено приглашение пользователей).\n"
        "3. DM мне приватно — подскажу шаги для конкретного дашборда.\n\n"
        f"Передано владельцу ({OWNER_USERNAME})."
    )
    owner_body = (
        "[OWNER-ONLY: forward to operator]\n"
        f"Source group: {chat_id}\n"
        f"Source msg_id: {msg_id}\n"
        f"Sender: {sender or 'unknown'}\n\n"
        f"{(body or '').strip()}"
    )
    group_ok = _tg_send(bot_token, chat_id, group_reply, reply_to=msg_id)
    owner_ok = _tg_send(bot_token, owner_id, owner_body)
    log.info(
        "owner credential handoff: chat=%s msg_id=%s sender=%s owner_chat=%s group_ok=%s owner_ok=%s",
        chat_id,
        msg_id,
        sender,
        owner_id,
        group_ok,
        owner_ok,
    )
    return bool(group_ok and owner_ok)


def _normalize_addressee(value: str) -> str:
    return re.sub(r"[^@a-zа-я0-9_]+", "", value.lower().replace("ё", "е"))


def _extract_group_sender_context(text: str) -> str:
    match = GROUP_SENDER_CONTEXT_RE.match((text or "").strip())
    if not match:
        return ""
    return match.group(1).strip()


def _allowed_salutations_for_sender(sender: str) -> set[str]:
    sender = (sender or "").strip()
    normalized = _normalize_addressee(sender)
    if not normalized:
        return set()
    aliases = {normalized}
    if sender.startswith("@"):
        raw = sender[1:].lower()
        aliases.update(_normalize_addressee(part) for part in re.split(r"[_\-.]+", raw) if part)
    aliases.update(_normalize_addressee(alias) for alias in KNOWN_GROUP_SENDER_ALIASES.get(sender.lower(), set()))
    return {alias for alias in aliases if alias}


def _neutralize_stale_group_salutation(chat_id: int, text: str) -> str:
    """Prevent group replies from opening with a stale person from older context."""
    if chat_id >= 0 or not _CURRENT_GROUP_SENDER:
        return text
    match = GROUP_PERSONAL_SALUTATION_RE.match(text or "")
    if not match:
        return text
    salutation = _normalize_addressee(match.group(1))
    if salutation in _allowed_salutations_for_sender(_CURRENT_GROUP_SENDER):
        return text
    log.warning(
        "neutralized stale group salutation: chat=%s sender=%r salutation=%r",
        chat_id,
        _CURRENT_GROUP_SENDER,
        match.group(1),
    )
    return "Коллеги, " + text[match.end():]


def _now_almaty() -> datetime:
    return datetime.now(ALMATY_TZ)


def _in_quiet_hours(now: datetime) -> bool:
    local = now.astimezone(ALMATY_TZ).time()
    if QUIET_START <= QUIET_END:
        return QUIET_START <= local < QUIET_END
    return local >= QUIET_START or local < QUIET_END


def _operator_boundary_decision(text: str, now: datetime | None = None) -> tuple[str, str]:
    """Return operator-boundary decision for long-running LLM commands.

    This is the code enforcement for pages/skills/operator-boundaries/SKILL.md:
    quiet hours hold non-urgent /ask, /ask-direct, /code, and /codex work while
    preserving urgent business/family/safety/legal bypasses.
    """
    if os.environ.get("OPERATOR_BOUNDARY_BYPASS") == "1":
        return ("respond_now", "OPERATOR_BOUNDARY_BYPASS=1")

    now = now or _now_almaty()
    if not _in_quiet_hours(now):
        return ("respond_now", "outside quiet hours")

    if URGENT_RE.search(text or ""):
        return ("escalate_urgent", "urgent or explicit override keyword")

    return ("hold_for_morning", "quiet hours 00:30-08:00 Asia/Almaty")


def _append_boundary_queue(text: str, chat_id: int, msg_id: int, reason: str,
                           now: datetime | None = None) -> str:
    """Append a held Telegram request to the vault and best-effort git sync it."""
    now = now or _now_almaty()
    wiki = os.environ.get("NOUS_WIKI", "/Users/madia/nous-agaas/wiki")
    date = now.astimezone(ALMATY_TZ).strftime("%Y-%m-%d")
    rel = f"pages/personal/boundary-queue-{date}.md"
    path = os.path.join(wiki, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "---\n"
                "type: operator-boundary-queue\n"
                f"date: {date}\n"
                "status: active\n"
                "related: [operator-boundaries, command-center]\n"
                "---\n\n"
                f"# Boundary Queue {date}\n"
            )

    stamp = now.astimezone(ALMATY_TZ).isoformat()
    with open(path, "a", encoding="utf-8") as f:
        f.write(
            "\n## Held Telegram request\n\n"
            f"- Timestamp: `{stamp}`\n"
            f"- Source: `telegram chat={chat_id} msg={msg_id}`\n"
            f"- Reason: {reason}\n"
            "- Next review: `08:00 Asia/Almaty`\n\n"
            "```text\n"
            f"{text.strip()}\n"
            "```\n"
        )

    if os.environ.get("NOUS_BOUNDARY_COMMIT", "1") != "0":
        try:
            subprocess.run(["git", "-C", wiki, "add", rel], capture_output=True, timeout=15)
            subprocess.run(
                ["git", "-C", wiki, "commit", "-m", f"boundary queue: {date}"],
                capture_output=True,
                timeout=20,
            )
            subprocess.run(["git", "-C", wiki, "push", "origin", "main"], capture_output=True, timeout=30)
        except Exception as exc:
            log.warning("boundary queue git sync failed: %s", exc)

    return rel


def _maybe_hold_for_quiet_hours(bot_token: str, chat_id: int, msg_id: int, text: str) -> bool:
    decision, reason = _operator_boundary_decision(text)
    if decision != "hold_for_morning":
        if decision == "escalate_urgent":
            log.info("operator-boundary urgent bypass: chat=%s msg=%s reason=%s", chat_id, msg_id, reason)
        return False

    saved = _append_boundary_queue(text, chat_id, msg_id, reason)
    reply = (
        "I saved this for morning.\n"
        f"Reason: {reason}.\n"
        f"Saved: {saved}\n"
        "Next: 08:00 Asia/Almaty.\n"
        "To bypass quiet hours, include urgent/critical/now/asap/prod/demo/family/safety/legal/override."
    )
    _tg_send(bot_token, chat_id, reply, reply_to=msg_id)
    log.info("operator-boundary held: chat=%s msg=%s saved=%s", chat_id, msg_id, saved)
    return True


# ── Goal Mode helpers ────────────────────────────────────────────────────────

def _wiki_root():
    from pathlib import Path
    return Path(os.environ.get("NOUS_WIKI", "/Users/madia/nous-agaas/wiki"))


def _load_goal_env() -> dict[str, str]:
    values = dict(os.environ)
    env_path = os.environ.get("NOUS_ENV_FILE", "/Users/madia/nous-agaas/.env")
    try:
        with open(env_path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                values.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass
    return values


def _goal_yaml(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _goal_slug(text: str, limit: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:limit].strip("-") or "goal")


def _parse_goal_command(text: str) -> tuple[str, str]:
    body = text.strip()
    if body.lower().startswith("/goal"):
        body = body[5:].strip()
    body = body.strip().strip('"').strip("'").strip()
    deadline = "none"
    match = re.search(r"\s+\bby\s+(\d{4}-\d{2}-\d{2})(?=$|[\s:;,.])", body, flags=re.IGNORECASE)
    if match:
        deadline = match.group(1)
        body = (body[:match.start()] + body[match.end():]).strip().strip('"').strip("'").strip()
        body = re.sub(r"\s+([:;,.])", r"\1", body)
        body = re.sub(r"\s{2,}", " ", body).strip()
    if not body:
        raise ValueError("goal text is required")
    return body, deadline


def _create_goal_page(goal_text: str, deadline: str = "none",
                      now: datetime | None = None, wiki_root=None) -> dict:
    from pathlib import Path
    now = now or _now_almaty()
    wiki = Path(wiki_root) if wiki_root is not None else _wiki_root()
    goals_dir = wiki / "pages" / "projects"
    goals_dir.mkdir(parents=True, exist_ok=True)

    goal_id = "GOAL-" + now.astimezone(ALMATY_TZ).strftime("%Y%m%d-%H%M%S")
    slug = _goal_slug(goal_text)
    filename = f"{goal_id}-{slug}.md"
    path = goals_dir / filename
    suffix = 2
    while path.exists():
        path = goals_dir / f"{goal_id}-{slug}-{suffix}.md"
        suffix += 1

    created_at = now.astimezone(ALMATY_TZ).strftime("%Y-%m-%d %H:%M")
    body = (
        "---\n"
        "type: project\n"
        f"id: {goal_id}\n"
        f"title: {_goal_yaml(goal_text)}\n"
        "status: active\n"
        f"deadline: {deadline}\n"
        f"created_at: {created_at}\n"
        "last_progress_at: null\n"
        "source: telegram-/goal\n"
        "---\n\n"
        f"# {goal_text}\n\n"
        "## Success criteria\n\n"
        "- Define concrete acceptance criteria in the first progress cycle.\n\n"
        "## Progress log\n\n"
        f"- **{created_at} KZT** — Goal created via Telegram `/goal`.\n\n"
        "## Status\n\n"
        "Active. Awaiting immediate goal-cycle kick, then launchd continuation until status changes.\n"
    )
    path.write_text(body, encoding="utf-8")
    rel_path = str(path.relative_to(wiki))

    if os.environ.get("NOUS_GOAL_COMMIT", "1") != "0":
        try:
            subprocess.run(["git", "-C", str(wiki), "add", rel_path], capture_output=True, timeout=15)
            subprocess.run(
                ["git", "-C", str(wiki), "commit", "-m", f"goal: create {path.stem[:72]}"],
                capture_output=True,
                timeout=20,
            )
            subprocess.run(["git", "-C", str(wiki), "push", "origin", "main"], capture_output=True, timeout=30)
        except Exception as exc:
            log.warning("goal page git sync failed: %s", exc)

    return {"id": goal_id, "path": str(path), "rel_path": rel_path, "deadline": deadline, "title": goal_text}


def _create_todoist_task(goal_text: str, deadline: str = "none", wiki_path: str = "") -> dict:
    env = _load_goal_env()
    token = env.get("TODOIST_API_TOKEN") or env.get("SATORY_TODOIST_TOKEN")
    project_id = (
        env.get("TODOIST_PROJECT_ID")
        or env.get("TODOIST_GOAL_PROJECT_ID")
        or env.get("SATORY_TODOIST_PROJECT_ID")
    )
    if not token:
        return {"ok": False, "error": "TODOIST_API_TOKEN not found"}
    if not project_id:
        return {"ok": False, "error": "TODOIST_PROJECT_ID not found"}

    payload = {
        "content": f"Goal: {goal_text}",
        "project_id": project_id,
        "description": f"Created by Nous Goal Mode.\nWiki: {wiki_path}" if wiki_path else "Created by Nous Goal Mode.",
    }
    if deadline and deadline != "none":
        payload["due_date"] = deadline

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.todoist.com/api/v1/tasks",
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return {"ok": True, "id": result.get("id", ""), "url": result.get("url", ""), "raw": result}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _kick_goal_cycle() -> dict:
    """Start the Air goal-cycle runner immediately after /goal creation.

    The launchd job is still the durable loop. This kick closes the practical gap
    where a just-created goal could sit idle until the next 4-hour interval.
    """
    if os.environ.get("NOUS_GOAL_KICK", "1") == "0":
        return {"ok": True, "message": "runner kick disabled by NOUS_GOAL_KICK=0"}

    label = os.environ.get("NOUS_GOAL_CYCLE_LABEL", "com.nous.goal-cycle")
    domain_label = f"gui/{os.getuid()}/{label}"
    try:
        proc = subprocess.run(
            ["launchctl", "kickstart", "-k", domain_label],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return {"ok": True, "message": f"kicked {label}"}
        launchctl_error = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
    except Exception as exc:
        launchctl_error = f"{type(exc).__name__}: {exc}"

    runner = Path(os.environ.get("NOUS_GOAL_RUNNER", "/Users/madia/nous-agaas/goal_runner.py"))
    if not runner.exists():
        return {
            "ok": False,
            "message": f"launchd kick failed: {launchctl_error}; runner missing: {runner}",
        }

    log_path = Path(os.environ.get("NOUS_GOAL_CYCLE_LOG", "/Users/madia/nous-agaas/logs/goal-cycle.log"))
    err_path = Path(os.environ.get("NOUS_GOAL_CYCLE_ERR", "/Users/madia/nous-agaas/logs/goal-cycle.err"))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with log_path.open("a", encoding="utf-8") as out, err_path.open("a", encoding="utf-8") as err:
            subprocess.Popen(
                [VENV_PYTHON, str(runner)],
                cwd=str(runner.parent),
                stdout=out,
                stderr=err,
                start_new_session=True,
                close_fds=True,
            )
        return {
            "ok": True,
            "message": f"started goal_runner.py directly after launchd kick failed: {launchctl_error[:160]}",
        }
    except Exception as exc:
        return {
            "ok": False,
            "message": f"launchd kick failed: {launchctl_error}; direct start failed: {type(exc).__name__}: {exc}",
        }


def _list_active_goals(wiki_root=None) -> list[dict]:
    from pathlib import Path
    wiki = Path(wiki_root) if wiki_root is not None else _wiki_root()
    goals = []
    for path in sorted((wiki / "pages" / "projects").glob("GOAL-*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if re.search(r"^status:\s*(paused|done|abandoned)\s*$", text, flags=re.IGNORECASE | re.MULTILINE):
            continue
        title = path.stem
        deadline = "none"
        title_match = re.search(r"^title:\s*(.+)\s*$", text, flags=re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip().strip('"').strip("'")
        deadline_match = re.search(r"^deadline:\s*(.+)\s*$", text, flags=re.MULTILINE)
        if deadline_match:
            deadline = deadline_match.group(1).strip().strip('"').strip("'")
        goals.append({"title": title, "deadline": deadline, "rel_path": str(path.relative_to(wiki))})
    return goals


def _format_goal_list(goals: list[dict]) -> str:
    if not goals:
        return "No active GOAL pages."
    lines = [f"Active goals: {len(goals)}"]
    for goal in goals[:20]:
        deadline = goal.get("deadline") or "none"
        lines.append(f"- {goal['title']} | deadline: {deadline} | {goal['rel_path']}")
    if len(goals) > 20:
        lines.append(f"... {len(goals) - 20} more")
    return "\n".join(lines)


# ── OpenClaw runner ──────────────────────────────────────────────────────────

def _run_openclaw(query: str, timeout: int = ASK_TIMEOUT, model: str = None,
                   agent_id: str = None, correlation_id: str = "") -> str:
    """Run query through run_task.py → OpenClaw. Returns response text string.
    SPEC-MULTI-MODEL-CEO-HIERARCHY-V1 Phase 3: supports --agent + --correlation-id."""
    try:
        cmd = [VENV_PYTHON, RUN_TASK]
        if model:
            cmd += ["--model", model]
        if agent_id:
            cmd += ["--agent", agent_id]
        if correlation_id:
            cmd += ["--correlation-id", correlation_id]
            cmd += ["--source", f"telegram:{correlation_id}:{agent_id or 'openclaw'}"]
        cmd += [query]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode == 0:
            return proc.stdout.strip() or "(agent returned no output)"
        else:
            stderr_preview = proc.stderr.strip()[:300]
            return f"❌ Agent error (exit {proc.returncode}):\n{stderr_preview}"
    except subprocess.TimeoutExpired:
        return f"⏱️ Timed out after {timeout}s. Agent did not respond in time."
    except FileNotFoundError:
        return "❌ run_task.py not found. Is the VPS stack deployed?"
    except Exception as e:
        return f"❌ {type(e).__name__}: {e}"


def _observe_telegram_command(
    command: str,
    msg_id: int,
    query: str = "",
    response: str = "",
    status: str = "ok",
    metadata: dict | None = None,
) -> None:
    if _langsmith_emit is None:
        return
    try:
        inputs = {"msg_id": msg_id, "query": _langsmith_text_digest(query or command)} if _langsmith_text_digest else {"msg_id": msg_id}
        outputs = {"status": status}
        if response:
            outputs["response"] = _langsmith_text_digest(response) if _langsmith_text_digest else response[:200]
        _langsmith_emit(
            "nous.telegram.command",
            inputs=inputs,
            outputs=outputs,
            metadata={"command": command, "correlation_id": f"tg_{msg_id}", **(metadata or {})},
            tags=["nous", "telegram", command.lstrip("/") or "unknown"],
            status=status,
        )
    except Exception as exc:
        log.warning("langsmith command observer failed (non-fatal): %s", exc)


def _redact_task_result_text(text: str) -> str:
    """Use the Telegram inbox redactor before writing model I/O to durable git."""
    try:
        from telegram_ingest_persist import redact_sensitive_text
        return redact_sensitive_text(text or "")
    except Exception:
        redacted = text or ""
        redacted = re.sub(
            r"(?i)\b(password|pass|pwd|пароль|token|secret|api[_-]?key)\s*[:=]\s*([^\s,;]+)",
            r"\1: [REDACTED]",
            redacted,
        )
        redacted = re.sub(
            r"(?im)^(\s*(?:test|prod|production|тест|прод)\s*:\s*)([^\s,;]+)",
            r"\1[REDACTED]",
            redacted,
        )
        return redacted


def _task_result_slug(text: str, limit: int = 48) -> str:
    slug = re.sub(r"[^A-Za-z0-9А-Яа-яЁё]+", "-", (text or "").lower()).strip("-")
    return (slug[:limit].strip("-") or "telegram-response")


def _write_telegram_task_result_receipt(
    command: str,
    msg_id: int,
    query: str,
    response: str,
    *,
    model: str,
    via: str,
    status: str = "ok",
) -> str | None:
    """Persist direct Telegram model replies that do not go through run_task.py."""
    try:
        wiki = _wiki_root()
        ts = _now_almaty().strftime("%Y-%m-%d-%H-%M-%S")
        command_slug = _task_result_slug(command.strip("/"), limit=32)
        rel = Path("pages/task-results") / f"{ts}-telegram-{command_slug}-{msg_id}-{_task_result_slug(query)}.md"
        path = wiki / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        safe_query = _redact_task_result_text(query)
        safe_response = _redact_task_result_text(response)
        path.write_text(
            "---\n"
            "type: task-result\n"
            f"date: {ts[:10]}\n"
            f"model: {model}\n"
            f"source: \"telegram:tg_{msg_id}:{command_slug}\"\n"
            f"via: \"{via}\"\n"
            f"status: {status}\n"
            "---\n\n"
            "## Task\n\n"
            f"{safe_query}\n\n"
            "## Response\n\n"
            f"{safe_response}\n",
            encoding="utf-8",
        )
        if os.environ.get("NOUS_TELEGRAM_RESULT_COMMIT", "1") != "0":
            rel_s = str(rel)
            subprocess.run(["git", "-C", str(wiki), "add", rel_s], capture_output=True, timeout=15)
            subprocess.run(
                ["git", "-C", str(wiki), "commit", "-m", f"task-result: telegram {command_slug} {msg_id}", "--", rel_s],
                capture_output=True,
                timeout=30,
            )
            subprocess.run(["git", "-C", str(wiki), "push", "origin", "main"], capture_output=True, timeout=45)
        return str(rel)
    except Exception as exc:
        log.warning("telegram task-result receipt write failed: command=%s msg_id=%s err=%s", command, msg_id, exc)
        return None


# ── Status runner ────────────────────────────────────────────────────────────

def _load_claude_cost() -> dict:
    """Load today's claude_code usage. Returns {date, total_usd, count}."""
    import datetime as _dt
    today = _dt.datetime.now().strftime("%Y-%m-%d")
    try:
        with open(CLAUDE_COST_FILE) as f:
            data = json.load(f)
        if data.get("date") == today:
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return {"date": today, "total_usd": 0.0, "count": 0}


def _save_claude_cost(data: dict) -> None:
    os.makedirs(os.path.dirname(CLAUDE_COST_FILE), exist_ok=True)
    with open(CLAUDE_COST_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _run_claude_code(task: str) -> str:
    """Run task via Claude Code headless (-p mode). Returns response text.

    Cost-capped at CLAUDE_DAILY_CAP_USD (default $5/day). Hard timeout 10 min.
    Requires claude CLI installed + logged in via OAuth on Air.

    Session 51, I-B: Task is prefixed with SESSION_CONTEXT_PREAMBLE so the
    ephemeral spawned agent reads HANDOFF + MEMORY + session-operating-contract
    before acting — continuity via substrate, not via session history.
    """
    cost = _load_claude_cost()
    if cost["total_usd"] >= CLAUDE_DAILY_CAP_USD:
        return (
            f"💸 Daily /code cap reached: ${cost['total_usd']:.2f} / ${CLAUDE_DAILY_CAP_USD:.2f}"
            f" ({cost['count']} calls today). Resets midnight Almaty."
            f" Use /ask for GLM-5.1 (unlimited)."
        )

    session_id = _register_spawned_session("/code", task)
    exit_status = "ok"

    # Inject session-continuity preamble (I-B, session 51). Spawned agent reads
    # substrate first so it knows where we left off. Skip if caller already
    # provided a preamble (detected by "session-continuity" marker) — avoids
    # double-injection if /code is invoked programmatically with pre-built context.
    if "session-continuity context" not in task[:500]:
        task = SESSION_CONTEXT_PREAMBLE + _spawned_session_note("/code", session_id) + task

    # Claude Code is sensitive to stray env vars. The ONLY reliable invocation is a
    # minimal env with just HOME + PATH (proven to work 2026-04-15). Building the
    # env up rather than filtering down avoids surprises from unrelated API_KEY/
    # TOKEN vars that .env pulls in. LESSON-097/098.
    claude_env = {
        "HOME": os.environ.get("HOME", "/Users/madia"),
        "PATH": "/Users/madia/.npm-global/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "SHELL": os.environ.get("SHELL", "/bin/bash"),
        "USER": os.environ.get("USER", "madia"),
        "TERM": "xterm-256color",
    }
    try:
        try:
            proc = subprocess.run(
                [CLAUDE_CMD, "-p", task,
                 "--output-format", "json",
                 "--permission-mode", "acceptEdits",
                 "--tools", "Bash,Read,Edit,Write,Grep,Glob"],
                cwd=CLAUDE_WORKDIR,
                env=claude_env,
                capture_output=True,
                text=True,
                timeout=CLAUDE_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            exit_status = "timeout"
            return f"⏱️ Claude Code timed out after {CLAUDE_TIMEOUT}s. Task may be too complex."
        except FileNotFoundError:
            exit_status = "error"
            return (
                "❌ Claude Code not installed on Air. "
                f"Expected at {CLAUDE_CMD} (user-scoped npm binary). "
                "Run: `ssh air 'npm install -g @anthropic-ai/claude-code'` then auth."
            )

        if proc.returncode != 0 and not proc.stdout:
            exit_status = "error"
            err = (proc.stderr or "").strip()
            if "authentication_error" in err or "Invalid authentication credentials" in err or "401" in err:
                return (
                    "❌ Claude Code auth failed on Air. "
                    f"Runtime binary is {CLAUDE_CMD}, but Claude returned 401 invalid credentials. "
                    "Run: `ssh -t air '$HOME/.npm-global/bin/claude auth login --claudeai --email mayazbay@gmail.com'` "
                    "then retry `/code Reply exactly: CODE_PATH_OK`."
                )
            return f"❌ Claude Code error: {err[:300]}"

        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError:
            exit_status = "error"
            return f"❌ Could not parse Claude Code response: {(proc.stdout or '')[:300]}"

        if result.get("is_error"):
            exit_status = "error"
            err = result.get("result", "unknown error")
            if (
                "Not logged in" in err
                or "authentication_error" in err
                or "Invalid authentication credentials" in err
                or "401" in err
            ):
                return (
                    "❌ Claude Code auth failed on Air.\n"
                    f"Runtime binary: `{CLAUDE_CMD}`\n"
                    "One-time step: `ssh -t air '$HOME/.npm-global/bin/claude auth login --claudeai --email mayazbay@gmail.com'`\n"
                    "Then retry: `/code Reply exactly: CODE_PATH_OK`"
                )
            return f"❌ Claude Code: {err}"

        response_text = result.get("result", "(empty response)")
        cost_usd = float(result.get("total_cost_usd", 0.0))
        duration_s = float(result.get("duration_ms", 0)) / 1000.0

        # Update cost
        cost["total_usd"] += cost_usd
        cost["count"] += 1
        _save_claude_cost(cost)

        footer = (
            f"\n\n—\n💰 ${cost_usd:.3f} | ⏱️ {duration_s:.1f}s | "
            f"today: ${cost['total_usd']:.2f}/{CLAUDE_DAILY_CAP_USD:.2f} ({cost['count']} calls)"
        )
        return response_text + footer
    finally:
        _close_spawned_session(session_id, exit_status)


def _load_codex_usage() -> dict:
    """Load today's /codex usage counter. Token count is best-effort from Codex CLI output."""
    import datetime as _dt
    today = _dt.datetime.now().strftime("%Y-%m-%d")
    try:
        with open(CODEX_USAGE_FILE) as f:
            data = json.load(f)
        if data.get("date") == today:
            data.setdefault("count", 0)
            data.setdefault("tokens", 0)
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return {"date": today, "count": 0, "tokens": 0}


def _save_codex_usage(data: dict) -> None:
    os.makedirs(os.path.dirname(CODEX_USAGE_FILE), exist_ok=True)
    with open(CODEX_USAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _parse_codex_tokens(text: str) -> int:
    import re as _re
    match = _re.search(r"tokens used\s+([\d,]+)", text, flags=_re.I)
    if not match:
        return 0
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return 0


def _clean_codex_output(stdout: str) -> str:
    """Strip Codex CLI wrapper lines and duplicate final echoes from Telegram output."""
    lines: list[str] = []
    skip_prefixes = (
        "OpenAI Codex v",
        "workdir:",
        "model:",
        "provider:",
        "approval:",
        "sandbox:",
        "reasoning ",
        "session id:",
        "--------",
        "Reading additional input from stdin",
    )
    for raw in (stdout or "").replace("\r", "\n").splitlines():
        line = raw.strip()
        if not line:
            continue
        lower = line.lower()
        if lower == "tokens used":
            break
        if line == "codex" or lower == "user":
            continue
        if any(line.startswith(prefix) for prefix in skip_prefixes):
            continue
        if line.startswith("2026-") and (" WARN " in line or " ERROR " in line):
            continue
        lines.append(line)

    deduped: list[str] = []
    for line in lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return "\n".join(deduped).strip()


def _run_codex_once(task: str, codex_home: str | None) -> subprocess.CompletedProcess:
    codex_env = {
        "HOME": os.environ.get("HOME", "/Users/madia"),
        "PATH": "/Users/madia/.npm-global/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "SHELL": os.environ.get("SHELL", "/bin/bash"),
        "USER": os.environ.get("USER", "madia"),
        "TERM": "xterm-256color",
    }
    if codex_home:
        codex_env["CODEX_HOME"] = codex_home

    return subprocess.run(
        [
            CODEX_CMD,
            "exec",
            "--ephemeral",
            "-m", CODEX_MODEL,
            "-C", CODEX_WORKDIR,
            "--sandbox", CODEX_SANDBOX,
            "--skip-git-repo-check",
            task,
        ],
        cwd=CODEX_WORKDIR,
        env=codex_env,
        capture_output=True,
        text=True,
        timeout=CODEX_TIMEOUT,
    )


def _run_codex(task: str) -> str:
    """Run task via OpenAI Codex CLI on Air using subscription auth only."""
    usage = _load_codex_usage()
    if usage["count"] >= CODEX_DAILY_CAP_CALLS:
        return (
            f"Daily /codex cap reached: {usage['count']} / {CODEX_DAILY_CAP_CALLS} calls "
            f"({usage.get('tokens', 0)} tokens observed). Resets midnight Almaty."
        )
    observed_tokens = int(usage.get("tokens", 0) or 0)
    if CODEX_DAILY_CAP_TOKENS > 0 and observed_tokens >= CODEX_DAILY_CAP_TOKENS:
        return (
            f"Daily /codex token cap reached: {observed_tokens} / {CODEX_DAILY_CAP_TOKENS} "
            "observed tokens. Resets midnight Almaty."
        )

    session_id = _register_spawned_session("/codex", task)
    exit_status = "ok"

    if "session-continuity context" not in task[:500] and "You are a /codex-spawned" not in task[:500]:
        task = CODEX_CONTEXT_PREAMBLE + _spawned_session_note("/codex", session_id) + task

    homes: list[tuple[str, str | None]] = [("subscription", None)]

    last_error = ""
    try:
        for label, home in homes:
            try:
                proc = _run_codex_once(task, home)
            except subprocess.TimeoutExpired:
                exit_status = "timeout"
                return f"Codex timed out after {CODEX_TIMEOUT}s. Task may be too complex for a Telegram turn."
            except FileNotFoundError:
                exit_status = "error"
                return (
                    f"Codex CLI not found. Resolved command: {CODEX_CMD}. "
                    "Install/update Codex on Air or set CODEX_CMD to the executable path."
                )

            combined = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
            if proc.returncode == 0:
                response_text = _clean_codex_output(proc.stdout) or _clean_codex_output(combined) or "(Codex returned no output)"
                tokens = _parse_codex_tokens(combined)
                usage["count"] += 1
                usage["tokens"] = int(usage.get("tokens", 0)) + tokens
                _save_codex_usage(usage)
                footer = (
                    f"\n\n—\nOpenAI Codex {CODEX_MODEL} via {label}"
                    f" | tokens: {tokens or 'unknown'}"
                    f" | today: {usage['count']}/{CODEX_DAILY_CAP_CALLS} calls"
                    f" | observed tokens: {usage['tokens']}/{CODEX_DAILY_CAP_TOKENS}"
                )
                return response_text + footer

            last_error = combined[:1200]
            token_auth_failed = (
                "token_expired" in combined
                or "refresh token" in combined.lower()
                or "401 Unauthorized" in combined
            )
            if token_auth_failed and label == "subscription":
                continue
            exit_status = "error"
            return f"Codex error via {label} (exit {proc.returncode}):\n{last_error[:900]}"

        exit_status = "error"
        return (
            "Codex unavailable on Air. Root cause: subscription auth token expired/reused. "
            "API fallback is disabled by policy so /codex never spends OpenAI API credits.\n"
            f"Fix subscription: ssh -t air '{CODEX_CMD} login --device-auth'\n"
            f"Last error:\n{last_error[:700]}"
        )
    finally:
        _close_spawned_session(session_id, exit_status)


def _run_status() -> str:
    """Return an Air factory health summary string."""
    lines: list[str] = []

    # Docker containers
    try:
        docker_cmd = shutil.which("docker") or "docker"
        proc = subprocess.run(
            [docker_cmd, "ps", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=10,
        )
        containers = [l for l in proc.stdout.strip().splitlines() if l]
        lines.append("🐳 <b>Containers:</b>")
        for row in containers:
            name, _, status = row.partition("\t")
            icon = "✅" if "Up" in status else "❌"
            lines.append(f"  {icon} {name}: {status.split('(')[0].strip()}")
        if not containers:
            lines.append("  (none running)")
    except Exception as e:
        lines.append(f"  docker error: {e}")

    # Disk usage
    try:
        df_cmd = shutil.which("df") or "/bin/df"
        proc = subprocess.run(
            [df_cmd, "-h", "/"],
            capture_output=True, text=True, timeout=5,
        )
        parts = proc.stdout.strip().splitlines()[-1].split()
        lines.append(f"\n💾 <b>Disk /:</b> {parts[2]} used / {parts[1]} ({parts[4]})")
    except Exception as e:
        lines.append(f"\n💾 disk error: {e}")

    # Memory (macOS-compatible — free -h does not exist on macOS)
    try:
        import platform
        if platform.system() == "Darwin":
            sysctl_cmd = shutil.which("sysctl") or "/usr/sbin/sysctl"
            vm_stat_cmd = shutil.which("vm_stat") or "/usr/bin/vm_stat"
            proc = subprocess.run(
                [sysctl_cmd, "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5,
            )
            total_bytes = int(proc.stdout.strip())
            proc2 = subprocess.run(
                [vm_stat_cmd],
                capture_output=True, text=True, timeout=5,
            )
            # Parse vm_stat for page size and free/active/inactive pages
            page_size = 16384  # default macOS ARM
            for line in proc2.stdout.splitlines():
                if "page size" in line:
                    page_size = int(line.split()[-2])
                    break
            active = inactive = wired = 0
            for line in proc2.stdout.splitlines():
                if "Pages active" in line:
                    active = int(line.split()[-1].rstrip("."))
                elif "Pages wired" in line:
                    wired = int(line.split()[-1].rstrip("."))
                elif "Pages inactive" in line:
                    inactive = int(line.split()[-1].rstrip("."))
            used_bytes = (active + wired) * page_size
            total_gb = total_bytes / (1024**3)
            used_gb = used_bytes / (1024**3)
            lines.append(f"🧠 <b>Memory:</b> {used_gb:.1f}G used / {total_gb:.0f}G")
        else:
            free_cmd = shutil.which("free") or "free"
            proc = subprocess.run(
                [free_cmd, "-h"],
                capture_output=True, text=True, timeout=5,
            )
            parts = proc.stdout.strip().splitlines()[1].split()
            lines.append(f"🧠 <b>Memory:</b> {parts[2]} used / {parts[1]}")
    except Exception as e:
        lines.append(f"🧠 memory error: {e}")

    return "\n".join(lines)



# ── Health runner ─────────────────────────────────────────────────────────────

def _run_health() -> str:
    """Run factory health checks and return a formatted status string."""
    _fh_load_envs()
    report = _factory_run_checks()
    return report.format_telegram()


# ── Public API ───────────────────────────────────────────────────────────────


# ─── T8: per-reply cost footer reader (reads ~/nous-agaas/logs/ask-hierarchy.jsonl)
# Replaces Langfuse for v1 per SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22.
def _compose_cost_footer(correlation_id: str) -> str:
    """Read tier_log JSONL for entries matching correlation_id; compute per-tier + day total."""
    import datetime as _dt, json as _json, os as _os
    log_path = _os.path.expanduser("~/nous-agaas/logs/ask-hierarchy.jsonl")
    if not _os.path.exists(log_path):
        return ""
    per_tier = {1: 0.0, 2: 0.0, 3: 0.0}
    day_total = 0.0
    today = _dt.datetime.utcnow().strftime("%Y-%m-%d")
    try:
        with open(log_path) as f:
            for line in f:
                try:
                    e = _json.loads(line)
                except Exception:
                    continue
                if e.get("correlation_id") == correlation_id:
                    t = e.get("tier", 0)
                    if t in per_tier:
                        per_tier[t] += float(e.get("cost_est", 0))
                if e.get("ts", "").startswith(today):
                    day_total += float(e.get("cost_est", 0))
    except Exception as _exc:
        return f"— cost: (footer error: {str(_exc)[:40]})"
    this_total = sum(per_tier.values())
    return (f"— cost: ${this_total:.3f} "
            f"(t1 ${per_tier[1]:.3f} / t2 ${per_tier[2]:.3f} / t3 ${per_tier[3]:.3f}) "
            f"| day ${day_total:.2f}/$30.00")


def _classify_inbox_post_ask(msg_id: int, body: str) -> str:
    """Phase 2.5: classify the inbox note for this msg_id and apply side-effects.

    Returns a short footer string for /ask reply, or "" if disabled / no inbox note /
    any failure. NEVER raises — bot reliability > classification.

    Kill-switch: TELEGRAM_INGEST_CLASSIFY=0|off|false disables.
    """
    if os.environ.get("TELEGRAM_INGEST_CLASSIFY", "1") in ("0", "off", "false"):
        return ""
    try:
        import datetime as _dt
        from pathlib import Path as _Path
        wiki = _Path(os.environ.get("NOUS_WIKI", "/Users/madia/nous-agaas/wiki"))
        today = _dt.date.today().isoformat()
        slug = f"pages/inbox/{today}/{msg_id}-unknown"
        inbox_path = wiki / f"{slug}.md"
        if not inbox_path.exists():
            return ""

        # Import classifier (script-relative)
        sys.path.insert(0, str(wiki / "tools"))
        try:
            import intent_classifier as _ic
            import telegram_ingest_persist as _tip
        finally:
            try:
                sys.path.remove(str(wiki / "tools"))
            except ValueError:
                pass
        # The Air poller can already have telegram_ingest_persist loaded from the
        # runtime-root shadow. Pin its mutable vault paths to this wiki before
        # classifying so post-/ask side effects never drift to a Mac checkout.
        _tip.VAULT = wiki
        _tip.INBOX_ROOT = wiki / "pages" / "inbox"
        _tip.TASKS_FILE = wiki / "TASKS.md"
        _tip.MERCURY_FACTS = wiki / "pages" / "mercury" / "facts.jsonl"

        verdict = _ic.classify(body)
        intent = verdict.get("intent", "unknown")
        conf = float(verdict.get("confidence", 0.0))
        rationale = verdict.get("rationale", "")
        model = verdict.get("classifier_model", "deepseek-v4-flash")

        if intent == "unknown" or conf < 0.5:
            return ""

        result = _tip.classify(slug, intent, conf, rationale, classifier_model=model)
        new_slug = result.get("slug", slug)
        side = result.get("side_effects", {})
        bits = []
        if side.get("tasks"):
            bits.append("TASKS.md ✓")
        if side.get("mercury"):
            bits.append(f"mercury fact {side['mercury']}")
        if side.get("decision"):
            bits.append("decision recorded")
        side_summary = (" · " + " · ".join(bits)) if bits else ""
        return f"📥 Saved as {intent} in [[{new_slug}]]{side_summary}"
    except Exception as _exc:
        log.warning(f"classify_inbox_post_ask failed: {type(_exc).__name__}: {_exc}")
        return ""


def is_command(text: str) -> bool:
    """True if the message is a routable bot command."""
    t = text.strip().lower()
    return (
        t.startswith("/ask")
        or t.startswith("/codex")
        or t.startswith("/code")
        or t.startswith("/goal-list")
        or t.startswith("/goal")
        or t.startswith("/status")
        or t.startswith("/report")
        or t.startswith("/health")
        or t.startswith("/handoff")
        or t.startswith("/help")
        or t.startswith("/trace")
    )


def extract_query(text: str) -> str:
    """Strip a command prefix and return the query text."""
    stripped = text.strip()
    for prefix in ("/ask-direct", "/goal-list", "/resume", "/codex", "/ask", "/code", "/goal"):
        if stripped.lower().startswith(prefix):
            return stripped[len(prefix):].strip()
    return stripped


def _parse_ask_tier_override(query: str) -> tuple[str | None, str, str]:
    """Return (tier, stripped_query, error) for /ask --tier ceo|cheap."""
    raw = query.strip()
    if not raw.startswith("--tier"):
        return None, query, ""
    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        return None, "", f"Invalid /ask --tier syntax: {exc}"
    if not parts:
        return None, "", "Usage: /ask [--tier ceo|cheap] <question>"

    tier = ""
    rest: list[str] = []
    first = parts[0]
    if first == "--tier":
        if len(parts) < 2:
            return None, "", "Usage: /ask [--tier ceo|cheap] <question>"
        tier = parts[1].lower()
        rest = parts[2:]
    elif first.startswith("--tier="):
        tier = first.split("=", 1)[1].lower()
        rest = parts[1:]
    else:
        return None, query, ""

    if tier not in {"ceo", "cheap"}:
        return None, "", "Usage: /ask [--tier ceo|cheap] <question>"
    stripped_query = " ".join(rest).strip()
    if not stripped_query:
        return None, "", "Usage: /ask [--tier ceo|cheap] <question>"
    return tier, stripped_query, ""


def _cheap_tier_local_failed(response: str) -> bool:
    lower = response.lower()
    return (
        lower.startswith("error")
        or "unknown model" in lower
        or "model not found" in lower
        or "unsupported model" in lower
        or "not supported" in lower
    )


def _run_ask_tier_cheap(query: str, correlation_id: str) -> tuple[str, str]:
    """Run explicit cheap tier: local MLX model first, DeepSeek fallback."""
    local = _run_openclaw(
        query,
        model=ASK_TIER_CHEAP_LOCAL_MODEL,
        correlation_id=f"{correlation_id}_cheap_local",
    )
    if not _cheap_tier_local_failed(local):
        return local, ASK_TIER_CHEAP_LOCAL_MODEL

    fallback = _run_openclaw(
        query,
        model=ASK_TIER_CHEAP_FALLBACK_MODEL,
        correlation_id=f"{correlation_id}_cheap_deepseek",
    )
    return fallback, ASK_TIER_CHEAP_FALLBACK_MODEL


def _requires_codex_verification_route(query: str) -> bool:
    """True when a /ask payload requires live shell/tool verification.

    OpenClaw `/ask` workers are text/reasoning agents. They may not have Air SSH,
    launchd, pytest, Drive, or local file access. Exact command verification must
    run through `/codex`, which executes on Air with the Codex toolchain.
    """
    q = (query or "").strip().lower()
    if not q:
        return False
    if not (q.startswith("verify:") or "run exact commands" in q or "save outputs" in q):
        return False
    shell_markers = (
        "ssh air",
        "launchctl",
        "python3 -m pytest",
        "factory_no_drift_probe",
        "control_plane_sync_loop",
        "git rev-parse",
        "curl ",
        "google drive",
        "gbrain readback",
        "openbrain projection",
    )
    return any(marker in q for marker in shell_markers)


def _codex_daily_budget_ok(threshold_usd: float = 5.0) -> tuple[bool, float]:
    """Sum today's Codex/GPT-5.5 cost from ask-hierarchy.jsonl; return (codex_route_available, today_spend).

    Used by `_query_likely_needs_high_judgment` to bound auto-escalation cost
    per ceo-hierarchy AP-13 ("future bounded auto-GPT gateway"). Falls back
    to today_spend=0.0 if log is missing — never blocks on missing telemetry.

    Also gates on the daily codex CALL cap and TOKEN cap. When either cap is
    exceeded, returns (False, today_spend) so /ask auto-escalation paths skip
    `_run_codex` (which would return its verbatim cap-error sentinel string)
    and fall through to grok-ceo Tier-1. See ceo-hierarchy AP-40 (2026-05-20
    Assylbek incident: bot replied "Daily /codex token cap reached: 312163 /
    250000 observed tokens. Resets midnight Almaty." to "видишь события?
    поток подали" instead of routing to grok-ceo).
    """
    import datetime as _dt
    import json as _json
    import os as _os

    # USD spend tally — still computed when caps fail so blocked-message can quote it.
    log_path = _os.path.expanduser("~/nous-agaas/logs/ask-hierarchy.jsonl")
    today = _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    total = 0.0
    if _os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or not line.startswith("{"):
                        continue
                    try:
                        entry = _json.loads(line)
                    except _json.JSONDecodeError:
                        continue
                    ts = entry.get("ts", "")
                    if not ts.startswith(today):
                        continue
                    model = (entry.get("model") or "").lower()
                    if "codex" in model or "gpt-5" in model:
                        total += float(entry.get("cost_est") or 0.0)
        except OSError:
            pass  # missing/unreadable log => assume zero spend; never block

    # Hard call/token cap gates — fail-closed so cap sentinel never reaches user.
    usage = _load_codex_usage()
    if usage.get("count", 0) >= CODEX_DAILY_CAP_CALLS:
        return (False, total)
    observed_tokens = int(usage.get("tokens", 0) or 0)
    if CODEX_DAILY_CAP_TOKENS > 0 and observed_tokens >= CODEX_DAILY_CAP_TOKENS:
        return (False, total)

    return (total < threshold_usd, total)


_HIGH_JUDGMENT_MARKERS = (
    "deep analysis", "deep dive", "глубокий анализ",
    "review the architecture", "architecture review", "design review",
    "what's the tradeoff", "tradeoffs?", "что лучше",
    "explain why", "почему", "обоснуй",
    "root cause", "root-cause", "коренная причина",
    "should we", "should i", "стоит ли",
    "compare ", "сравни ",
    "musk step", "best cto", "elon", "karpathy", "garry tan",
    "billion-dollar", "billion dollar",
    "long-term", "стратегич",
    "honest take", "честно",
)


def _query_likely_needs_high_judgment(query: str) -> bool:
    """Heuristic: does this /ask payload warrant the GPT-5.5/Codex Tier-2 reasoning lane?

    Per MADI-DECISIONS-2026-05-14-round2 item #3 + ceo-hierarchy AP-13: when grok-ceo's
    Tier-1 chat-class answer isn't enough, auto-escalate to Codex. This is a
    pre-route heuristic (NOT a post-classification confidence check — that requires
    grok-ceo prompt modification, deferred).

    Bounds: query length 200-4096 chars (single Telegram message); cost guard via
    `_codex_daily_budget_ok`; at least one high-judgment marker present.

    Pairs with `_requires_codex_verification_route` (shell verification path) — both
    fire pre-Tier-1. This one is the high-judgment path. See ceo-hierarchy AP-16.
    """
    q = (query or "").strip()
    if not q:
        return False
    q_len = len(q)
    if q_len < 200 or q_len > 4096:
        return False
    q_lower = q.lower()
    if not any(marker in q_lower for marker in _HIGH_JUDGMENT_MARKERS):
        return False
    budget_ok, _today_spend = _codex_daily_budget_ok()
    if not budget_ok:
        return False
    return True


def _factory_orchestration_decision(query: str) -> dict:
    """Return the shared Telegram/Todoist route decision.

    LangGraph consumes the same pure policy through
    `tools/langgraph_factory_orchestrator.py`; command_center keeps this helper
    tiny so a missing policy module never breaks Telegram.
    """
    if _classify_factory_route is None:
        return {"route": "openclaw_routine", "reason": "policy module unavailable"}
    try:
        return _classify_factory_route(query).to_dict()
    except Exception as exc:  # noqa: BLE001 - Telegram must fail open to OpenClaw.
        return {"route": "openclaw_routine", "reason": f"policy error: {type(exc).__name__}: {exc}"}


MANDATORY_CODEX_TODOIST_ACTIONS = {
    "codex_external_proof",
    "codex_supervise_then_delegate",
}


def _is_mandatory_codex_decision(route_decision: dict) -> bool:
    return route_decision.get("todoist_action") in MANDATORY_CODEX_TODOIST_ACTIONS


def _mandatory_codex_blocked_message(query: str, today_spend: float) -> str:
    preview = query[:240] + ("…" if len(query) > 240 else "")
    return (
        "Codex is unavailable right now, so this route is running in degraded mode.\n"
        f"Today's tracked spend is ${today_spend:.2f}.\n\n"
        f"<code>{preview}</code>\n\n"
        "No internal cap error should be shown to an external chat."
    )


def _format_model_pipeline(query: str) -> str:
    if _factory_model_pipeline is None:
        return "grok-reasoning -> deepseek-v4-flash -> deepseek-v4-pro"
    try:
        return " -> ".join(_factory_model_pipeline(query))
    except Exception:
        return "grok-reasoning -> deepseek-v4-flash -> deepseek-v4-pro"


def _is_openclaw_identity_question(query: str) -> bool:
    """True for operator-facing "are you OpenClaw?" style questions.

    This is a deterministic product-surface answer, not a reasoning task. If it
    reaches grok-ceo, the agent can truthfully answer "I am grok-ceo, not
    OpenClaw" and still fail the operator's intent: prove that Telegram is
    entering the OpenClaw runtime.
    """
    q = re.sub(r"\s+", " ", (query or "").strip().lower())
    if not q:
        return False
    openclaw_markers = ("openclaw", "open claw", "opencalw", "opencla")
    if not any(marker in q for marker in openclaw_markers):
        return False
    identity_markers = (
        "are you",
        "you are",
        "is this",
        "is it",
        "am i talking",
        "who are you",
        "what are you",
        "who is answering",
        "now",
        "fully",
        "full",
        "ты",
        "это",
        "кто",
        "сейчас",
        "полностью",
    )
    return any(marker in q for marker in identity_markers)


def _openclaw_identity_answer() -> str:
    """Return the canonical Telegram-facing OpenClaw identity answer."""
    return (
        "✅ Yes — this Telegram path is the OpenClaw production runtime.\n\n"
        "Precise layers:\n"
        "• <b>OpenClaw</b> = Air runtime/orchestrator that receives and routes Telegram work.\n"
        "• <code>grok-ceo</code> = Tier-1 CEO agent answering routine <code>/ask</code> inside OpenClaw.\n"
        "• <code>nous</code> = Tier-2 execution agent inside OpenClaw.\n"
        "• <code>/codex</code> = GPT-5.5 high-judgment lane, not the default for every message.\n\n"
        "Strictly: normal <code>/ask</code> work is <b>OpenClaw → grok-ceo</b>. "
        "This identity check is answered locally by <code>command_center.py</code> before any model call."
    )


def _is_satory_event_intake_status_query(query: str) -> bool:
    """True for Satory operator asks about whether VAR/radar events are visible."""
    body = _extract_group_message_body(query) or query
    q = re.sub(r"\s+", " ", (body or "").strip().lower())
    full = re.sub(r"\s+", " ", (query or "").strip().lower())
    if not q:
        return False
    has_satory_context = bool(
        "telegram group sender" in full
        or re.search(r"\b(satory|сatory)\b", q)
        or re.search(r"\b(вар|var|радар|камера|camera|лу\s*100|lu\s*100|денис|denis)\b", q)
    )
    if not has_satory_context:
        return False
    visibility_markers = (
        "видишь",
        "вилишь",
        "видно",
        "что вид",
        "что вил",
        "see",
        "visible",
        "начнет что-то приходить",
        "начнёт что-то приходить",
        "получать события",
    )
    intake_markers = (
        "событ",
        "event",
        "поток",
        "маршрут",
        "9080",
        "camera/hxml",
        "hxml",
        "ерап",
        "erap",
        "денис",
        "denis",
    )
    if any(marker in q for marker in visibility_markers) and any(marker in q for marker in intake_markers):
        return True
    if "поток подали" in q or "маршрут настроили" in q:
        return True
    return "дай знать" in q and ("приход" in q or "событ" in q)


def _fetch_satory_event_intake_snapshot() -> tuple[dict | None, str]:
    try:
        req = urllib.request.Request(
            SATORY_EVENTS_API_URL,
            headers={"User-Agent": "nous-command-center-satory-intake/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8")), ""
    except Exception as exc:  # noqa: BLE001 - operator-facing proof path must fail loud.
        return None, f"{type(exc).__name__}: {exc}"


def _format_satory_event_intake_status(data: dict | None, error: str = "") -> str:
    if error or not isinstance(data, dict):
        return (
            "Не могу сейчас проверить Satory intake по status API.\n\n"
            f"Ошибка: <code>{_html.escape(error or 'empty response')}</code>\n\n"
            "Без свежего чтения API не буду утверждать, что события видны. "
            "Тестовый вход: <code>http://65.108.215.200:9080/events/camera/hxml</code>. "
            "В ЕРАП не отправляю."
        )
    freshness = data.get("data_freshness") or {}
    events_last_seen = str(freshness.get("events_last_seen") or "")
    age = freshness.get("events_age_seconds")
    recent_count = freshness.get("events_recent_count", "?")
    poll_last_run = freshness.get("poll_last_run") or "?"
    total = data.get("total", "?")
    online = data.get("online", "?")
    stale = data.get("stale", "?")

    age_is_recent = isinstance(age, (int, float)) and age <= SATORY_EVENTS_RECENT_SECONDS
    advanced = bool(events_last_seen and events_last_seen != SATORY_EVENTS_FROZEN_AT)
    if advanced and age_is_recent:
        first_line = "Вижу свежие события на нашем intake."
        status_line = "Маршрут VAR/радар -> Nous intake ожил по event timestamp."
    else:
        first_line = "Пока не вижу свежих событий на нашем intake."
        status_line = "Маршрут мог быть настроен на стороне камеры/VAR, но у нас timestamp еще не подтвердил новый поток."

    age_text = str(age) if isinstance(age, (int, float)) else "unknown"
    last_text = events_last_seen or "нет"
    return (
        f"{first_line}\n\n"
        f"{status_line}\n\n"
        f"Проверка API: <code>{SATORY_EVENTS_API_URL}</code>\n"
        f"• <code>events_last_seen={_html.escape(last_text)}</code>\n"
        f"• <code>events_age_seconds={_html.escape(age_text)}</code>\n"
        f"• <code>events_recent_count={_html.escape(str(recent_count))}</code>\n"
        f"• <code>poll_last_run={_html.escape(str(poll_last_run))}</code>\n"
        f"• <code>total={_html.escape(str(total))}</code> cameras, "
        f"<code>online={_html.escape(str(online))}</code>, <code>stale={_html.escape(str(stale))}</code>\n\n"
        "Это intake-only наблюдение. В ЕРАП не отправляю. "
        "Тестовый вход: <code>http://65.108.215.200:9080/events/camera/hxml</code>."
    )


def handle(bot_token: str, chat_id: int, msg_id: int, text: str) -> bool:
    """
    Handle a command message from Telegram.

    Args:
        bot_token: Telegram bot token.
        chat_id:   Telegram chat ID to reply to.
        msg_id:    Message ID to thread the reply under.
        text:      Raw message text from Telegram.

    Returns:
        True if the message was handled (caller should skip vault capture).
        False if not a recognised command.
    """
    global _CURRENT_GROUP_SENDER
    t = text.strip()
    _CURRENT_GROUP_SENDER = _extract_group_sender_context(t) if chat_id < 0 else ""
    lower = t.lower()

    # /handoff ───────────────────────────────────────────
    if lower.startswith("/handoff"):
        import datetime as _dt
        from pathlib import Path
        WIKI = Path("/Users/madia/nous-agaas/wiki")
        ts = _dt.datetime.now().strftime("%Y-%m-%d-%H-%M")
        wiki_path = "pages/progress/HANDOFF-AUTO-" + ts + ".md"
        handoff_prompt = (
            "Write a session checkpoint handoff. "
            "Include: (1) what is verified working right now with timestamps, "
            "(2) what was done recently, "
            "(3) top 3 next items, "
            "(4) blockers and who unblocks them, "
            "(5) 3 key context items for next Claude Code session. "
            "Format like existing HANDOFFs in pages/progress/. Under 400 lines. "
            "Only list verified items, no assumptions."
        )
        _tg_send(bot_token, chat_id, "⏳ Writing handoff checkpoint to wiki...", reply_to=msg_id)
        content = _run_openclaw(handoff_prompt)
        # Write directly — agent has no write-back tool for arbitrary paths;
        # only run_task.py auto-writes to pages/task-results/. Write here.
        out = WIKI / wiki_path
        out.parent.mkdir(parents=True, exist_ok=True)
        header = "# Handoff " + ts + chr(10) + chr(10) + "Generated via /handoff command." + chr(10) + chr(10)
        out.write_text(header + content + chr(10))
        try:
            subprocess.run(["git", "-C", str(WIKI), "add", wiki_path],
                           check=True, capture_output=True, timeout=15)
            subprocess.run(["git", "-C", str(WIKI), "commit", "-m",
                            "handoff: " + ts],
                           check=True, capture_output=True, timeout=15)
            log.info("/handoff committed: " + wiki_path)
        except subprocess.CalledProcessError as e:
            log.warning("/handoff git error: " + str(e))
        _tg_send(
            bot_token, chat_id,
            "✅ Checkpoint: " + wiki_path + ". Syncs to Mac in ~60s.",
            reply_to=msg_id,
        )
        log.info("/handoff checkpoint written: " + ts)
        return True

    # /help ───────────────────────────────────────────────
    if lower.startswith("/help"):
        _tg_send(bot_token, chat_id, HELP_TEXT, reply_to=msg_id)
        log.info(f"/help sent to chat={chat_id}")
        return True

    # /resume ─────────────────────────────────────────────
    if lower.startswith("/resume"):
        query = extract_query(t)
        if _format_failover_resume_status is None or _build_failover_resume_prompt is None:
            _tg_send(bot_token, chat_id, "Model failover state tool is unavailable on this runtime.", reply_to=msg_id)
            return True
        if not query:
            _tg_send(bot_token, chat_id, _format_failover_resume_status(), reply_to=msg_id)
            log.info(f"/resume status sent to chat={chat_id}")
            return True
        route = _resume_target_model(query)
        if route is None:
            _tg_send(
                bot_token,
                chat_id,
                "Usage: <code>/resume gpt</code>, <code>/resume grok</code>, <code>/resume claude</code>, or <code>/resume opus</code>",
                reply_to=msg_id,
            )
            return True
        route_name, model_name, via = route
        prompt = _build_failover_resume_prompt(route_name)
        if prompt.startswith("No model failover event"):
            _tg_send(bot_token, chat_id, prompt, reply_to=msg_id)
            return True
        event_id = _failover_start(f"/resume-{route_name}", msg_id, chat_id, prompt, model=model_name, via=via)
        _tg_progress(
            bot_token,
            chat_id,
            f"↪️ Resuming latest failover event via {model_name}…",
            msg_id,
        )
        if route_name == "codex":
            response = _operator_visible_response(chat_id, _run_codex(prompt))
        elif route_name == "claude":
            response = _run_claude_code(prompt)
        elif route_name == "opus":
            response = _run_openclaw(prompt, model="opus", agent_id="nous", correlation_id=f"tg_{msg_id}_resume")
            response = f"[opus-resume]\n{response}\n\n— resume route | correlation_id=tg_{msg_id}_resume"
        else:
            response = _run_openclaw(prompt, agent_id="grok-ceo", correlation_id=f"tg_{msg_id}_resume")
            response = _operator_visible_response(chat_id, response)
        receipt = _write_telegram_task_result_receipt(
            f"/resume-{route_name}",
            msg_id,
            prompt,
            response,
            model=model_name,
            via=via,
            status=_model_status_from_response(response),
        )
        _failover_finish(event_id, response, receipt=receipt)
        if len(response) > MAX_MSG_LEN:
            suffix = f"\n\n…(truncated)\n📄 Full: wiki/{receipt}" if receipt else "\n\n… (truncated — receipt write failed)"
            response = response[: MAX_MSG_LEN - len(suffix)] + suffix
        _tg_send(bot_token, chat_id, response, reply_to=msg_id)
        _observe_telegram_command(f"/resume-{route_name}", msg_id, query=prompt, response=response, status=_model_status_from_response(response))
        log.info(f"/resume handled: chat={chat_id} route={route_name} r_len={len(response)}")
        return True

    # /status ─────────────────────────────────────────────
    if lower.startswith("/status"):
        _tg_send(bot_token, chat_id, "⏳ Checking factory health…", reply_to=msg_id)
        status_text = _run_status()
        _tg_send(bot_token, chat_id, status_text, reply_to=msg_id)
        log.info(f"/status sent to chat={chat_id}")
        return True

    # /report ─────────────────────────────────────────────
    if lower.startswith("/report"):
        try:
            report = daily_report()
            text = format_report(report)
        except Exception as e:
            text = f"❌ Cost report error: {e}"
        _tg_send(bot_token, chat_id, text, reply_to=msg_id)
        log.info(f"/report sent to chat={chat_id}")
        return True

    # /health ────────────────────────────────────────────
    if lower.startswith("/health"):
        _tg_send(bot_token, chat_id, "⏳ Running factory health checks…", reply_to=msg_id)
        health_text = _run_health()
        _tg_send(bot_token, chat_id, health_text, reply_to=msg_id)
        log.info(f"/health sent to chat={chat_id}")
        return True

    # /goal-list ───────────────────────────────────────────
    if lower.startswith("/goal-list"):
        _tg_send(bot_token, chat_id, _format_goal_list(_list_active_goals()), reply_to=msg_id)
        _observe_telegram_command("/goal-list", msg_id, status="ok")
        log.info(f"/goal-list sent to chat={chat_id}")
        return True

    # /goal ────────────────────────────────────────────────
    if lower.startswith("/goal"):
        try:
            goal_text, deadline = _parse_goal_command(t)
        except ValueError:
            _tg_send(
                bot_token, chat_id,
                "Usage: <code>/goal ship OpenBrain projection by 2026-05-15</code>",
                reply_to=msg_id,
            )
            return True

        goal = _create_goal_page(goal_text, deadline)
        todoist = _create_todoist_task(goal_text, deadline, goal["rel_path"])
        kick = _kick_goal_cycle()
        todoist_line = (
            f"Todoist: {todoist.get('id') or todoist.get('url') or 'created'}"
            if todoist.get("ok")
            else f"Todoist not created: {todoist.get('error', 'unknown error')}"
        )
        runner_line = (
            f"Runner: {kick.get('message', 'started')}"
            if kick.get("ok")
            else f"Runner not started: {kick.get('message', 'unknown error')}"
        )
        reply = (
            "Goal created.\n"
            f"Wiki: {goal['rel_path']}\n"
            f"Deadline: {goal['deadline']}\n"
            f"{todoist_line}\n"
            f"{runner_line}\n"
            "OpenClaw will keep cycling this goal while status remains active."
        )
        _tg_send(bot_token, chat_id, reply, reply_to=msg_id)
        _observe_telegram_command(
            "/goal",
            msg_id,
            query=goal_text,
            response=reply,
            status="ok" if todoist.get("ok") and kick.get("ok") else "partial",
            metadata={"goal_path": goal["rel_path"], "todoist_ok": todoist.get("ok"), "kick_ok": kick.get("ok")},
        )
        log.info(f"/goal created: chat={chat_id} path={goal['rel_path']} todoist_ok={todoist.get('ok')}")
        return True

    # /codex ─────────────────────────────────────────────
    if lower.startswith("/codex"):
        query = extract_query(t)
        if not query:
            _tg_send(
                bot_token, chat_id,
                "Usage: <code>/codex inspect command_center.py and propose a patch</code>\n"
                f"<i>/codex = OpenAI Codex ({CODEX_MODEL}) on Air. "
                f"Daily cap: {CODEX_DAILY_CAP_CALLS} calls / {CODEX_DAILY_CAP_TOKENS} observed tokens.</i>",
                reply_to=msg_id,
            )
            return True
        if _maybe_hold_for_quiet_hours(bot_token, chat_id, msg_id, t):
            return True
        failover_event_id = _failover_start("/codex", msg_id, chat_id, query, model=CODEX_MODEL, via="/codex (OpenAI Codex)")
        preview = query[:80] + ("…" if len(query) > 80 else "")
        _tg_progress(
            bot_token, chat_id,
            f"🤖 Running OpenAI Codex {CODEX_MODEL} (up to {CODEX_TIMEOUT//60} min)…\n"
            f"<code>{_html.escape(preview)}</code>",
            msg_id,
        )
        response = _run_codex(query)
        response = _operator_visible_response(chat_id, response)
        receipt = _write_telegram_task_result_receipt(
            "/codex",
            msg_id,
            query,
            response,
            model=CODEX_MODEL,
            via=f"/codex (OpenAI Codex {CODEX_MODEL})",
        )
        _failover_finish(failover_event_id, response, receipt=receipt)
        if len(response) > MAX_MSG_LEN:
            suffix = f"\n\n…(truncated)\n📄 Full: wiki/{receipt}" if receipt else "\n\n… (truncated — receipt write failed)"
            truncated = response[: MAX_MSG_LEN - len(suffix)] + suffix
            _tg_send(bot_token, chat_id, truncated, reply_to=msg_id)
        else:
            _tg_send(bot_token, chat_id, response, reply_to=msg_id)
        _observe_telegram_command("/codex", msg_id, query=query, response=response, status="ok")
        log.info(f"/codex handled: chat={chat_id} q_len={len(query)} r_len={len(response)}")
        return True

    # /code ───────────────────────────────────────────────
    if lower.startswith("/code"):
        query = extract_query(t)
        if not query:
            _tg_send(
                bot_token, chat_id,
                "Usage: <code>/code read run_task.py and explain escalator logic</code>\n"
                "<i>/code = Claude Code (Sonnet 4.6) with Bash, Read, Edit, Write, Grep, Glob tools. "
                f"${CLAUDE_DAILY_CAP_USD:.0f}/day cap.</i>",
                reply_to=msg_id,
            )
            return True
        if _maybe_hold_for_quiet_hours(bot_token, chat_id, msg_id, t):
            return True
        failover_event_id = _failover_start("/code", msg_id, chat_id, query, model="claude-code", via="/code (Claude Code)")
        preview = query[:80] + ("…" if len(query) > 80 else "")
        _tg_send(
            bot_token, chat_id,
            f"🤖 Running Claude Code (up to {CLAUDE_TIMEOUT//60} min)…\n<code>{_html.escape(preview)}</code>",
            reply_to=msg_id,
        )
        response = _run_claude_code(query)
        receipt = _write_telegram_task_result_receipt(
            "/code",
            msg_id,
            query,
            response,
            model="claude-code",
            via="/code (Claude Code)",
        )
        _failover_finish(failover_event_id, response, receipt=receipt)
        if len(response) > MAX_MSG_LEN:
            suffix = f"\n\n…(truncated)\n📄 Full: wiki/{receipt}" if receipt else "\n\n… (truncated — receipt write failed)"
            truncated = response[: MAX_MSG_LEN - len(suffix)] + suffix
            _tg_send(bot_token, chat_id, truncated, reply_to=msg_id)
        else:
            _tg_send(bot_token, chat_id, response, reply_to=msg_id)
        _observe_telegram_command("/code", msg_id, query=query, response=response, status="ok")
        log.info(f"/code handled: chat={chat_id} q_len={len(query)} r_len={len(response)}")
        return True

    # /trace ─────────────────────────────────────────────
    # Per-tier timeline for a correlation_id (T10 of SPEC-MULTI-MODEL-CEO-HIERARCHY-V1).
    if lower.startswith("/trace"):
        import subprocess as _sp
        cid = t[len("/trace"):].strip()
        if not cid:
            _tg_send(
                bot_token, chat_id,
                "Usage: <code>/trace &lt;msg_id_or_correlation_id&gt;</code>\n"
                "Returns per-tier timeline from ~/nous-agaas/logs/ask-hierarchy.jsonl",
                reply_to=msg_id,
            )
            return True
        # Accept either "tg_<msg_id>" or bare "<msg_id>"
        if not cid.startswith("tg_") and cid.isdigit():
            cid = "tg_" + cid
        log_path = os.path.expanduser("~/nous-agaas/logs/ask-hierarchy.jsonl")
        try:
            cmd = (
                f"grep -F '\"correlation_id\": \"{cid}\"' {log_path} | "
                f"jq -r '\"t=\" + .ts + \" tier=\" + (.tier|tostring) + "
                f"\" model=\" + .model + \" latency=\" + (.latency_ms|tostring) + "
                f"\"ms cost=$\" + (.cost_est|tostring) + \" decision=\" + .decision'"
            )
            out = _sp.check_output(cmd, shell=True, text=True, timeout=10)
            if not out.strip():
                reply = f"No trace entries for correlation_id={cid}"
            else:
                reply = f"/trace {cid}\n<pre>{out}</pre>"
        except _sp.CalledProcessError:
            reply = f"No trace entries for correlation_id={cid}"
        except Exception as _exc:
            reply = f"Trace error: {str(_exc)[:200]}"
        _tg_send(bot_token, chat_id, reply, reply_to=msg_id)
        log.info(f"/trace handled: chat={chat_id} cid={cid}")
        return True

    # /ask-direct ─────────────────────────────────────────
    # Bypass Tier-1 (grok-ceo), route straight to Opus (nous).
    # Added via SPEC-MULTI-MODEL-CEO-HIERARCHY-V1-2026-04-22 Phase-1 T4.
    if lower.startswith("/ask-direct"):
        query = extract_query(t)
        if not query:
            _tg_send(
                bot_token, chat_id,
                "Usage: <code>/ask-direct your query here</code>\n(bypasses Tier-1 grok-ceo → straight to Opus)",
                reply_to=msg_id,
            )
            return True
        if _maybe_hold_for_quiet_hours(bot_token, chat_id, msg_id, t):
            return True
        failover_event_id = _failover_start("/ask-direct", msg_id, chat_id, query, model="opus", via="/ask-direct opus")
        preview = query[:80] + ("…" if len(query) > 80 else "")
        _tg_send(
            bot_token, chat_id,
            f"⏳ /ask-direct → Opus (tier-1 bypass)…\n<code>{preview}</code>",
            reply_to=msg_id,
        )
        # Phase-1: same call as /ask for now; Phase-3 T14 will add agent_id kwarg to keep nous routing.
        response = _run_openclaw(query, model="opus", agent_id="nous", correlation_id=f"tg_{msg_id}")  # /ask-direct: bypass Tier-1, route direct to nous+opus by design.
        labeled = f"[opus-direct]\n{response}\n\n— direct tier-2 bypass (no Tier-1) | correlation_id=tg_{msg_id}"
        if len(labeled) > MAX_MSG_LEN:
            labeled = labeled[: MAX_MSG_LEN - 60] + "\n\n… (truncated — full output in logs)"
        _failover_finish(failover_event_id, labeled)
        _tg_send(bot_token, chat_id, labeled, reply_to=msg_id)
        _observe_telegram_command("/ask-direct", msg_id, query=query, response=labeled, status="ok")
        log.info(f"/ask-direct handled: chat={chat_id} q_len={len(query)} r_len={len(labeled)}")
        return True

    # /ask ────────────────────────────────────────────────
    if lower.startswith("/ask"):
        query = extract_query(t)
        if not query:
            _tg_send(
                bot_token, chat_id,
                "Usage: <code>/ask [--tier ceo|cheap] your question here</code>",
                reply_to=msg_id,
            )
            return True
        tier, query, tier_error = _parse_ask_tier_override(query)
        if tier_error:
            _tg_send(bot_token, chat_id, tier_error, reply_to=msg_id)
            return True
        if tier == "ceo":
            if chat_id != OWNER_CHAT_ID or _is_group_chat(chat_id):
                _tg_send(bot_token, chat_id, "❌ /ask --tier ceo: Madi DM only", reply_to=msg_id)
                _observe_telegram_command(
                    "/ask-tier-ceo-rejected",
                    msg_id,
                    query=query,
                    response="Madi DM only",
                    status="blocked",
                )
                return True
            preview = query[:80] + ("…" if len(query) > 80 else "")
            failover_event_id = _failover_start(
                "/ask --tier ceo",
                msg_id,
                chat_id,
                query,
                model=CODEX_MODEL,
                via="/ask --tier ceo Codex subscription",
            )
            _tg_progress(
                bot_token,
                chat_id,
                "🧠 Codex GPT-5.5 subscription-first CEO tier…\n"
                "Opus API disabled by default; xAI/API council requires explicit paid approval.\n"
                f"<code>{preview}</code>",
                msg_id,
            )
            response = _operator_visible_response(chat_id, _run_codex(query))
            receipt = _write_telegram_task_result_receipt(
                "/ask-tier-ceo-codex",
                msg_id,
                query,
                response,
                model=CODEX_MODEL,
                via="/ask --tier ceo Codex subscription-first",
            )
            if len(response) > MAX_MSG_LEN:
                suffix = f"\n\n…(truncated)\n📄 Full: wiki/{receipt}" if receipt else "\n\n… (truncated — receipt write failed)"
                response = response[: MAX_MSG_LEN - len(suffix)] + suffix
            _failover_finish(failover_event_id, response, receipt=receipt)
            _tg_send(bot_token, chat_id, response, reply_to=msg_id)
            _observe_telegram_command(
                "/ask-tier-ceo-codex",
                msg_id,
                query=query,
                response=response,
                status="ok",
                metadata={"billing_surface": "subscription", "paid_api_default": "disabled"},
            )
            log.info(f"/ask --tier ceo handled via Codex subscription: chat={chat_id} q_len={len(query)} r_len={len(response)}")
            return True
        if tier == "cheap":
            preview = query[:80] + ("…" if len(query) > 80 else "")
            failover_event_id = _failover_start(
                "/ask --tier cheap",
                msg_id,
                chat_id,
                query,
                model=ASK_TIER_CHEAP_LOCAL_MODEL,
                via="/ask --tier cheap MLX/DeepSeek",
            )
            _tg_progress(
                bot_token,
                chat_id,
                "⚙️ Routing through MLX/DeepSeek cheap tier…\n"
                f"<code>{preview}</code>",
                msg_id,
            )
            response, model_used = _run_ask_tier_cheap(query, f"tg_{msg_id}")
            label = (
                f"\n\n— MLX/DeepSeek cheap tier"
                f" | model={model_used}"
                f" | billing_surface={'local' if model_used == ASK_TIER_CHEAP_LOCAL_MODEL else 'openrouter'}"
                f" | correlation_id=tg_{msg_id}"
            )
            response = _operator_visible_response(chat_id, response + label)
            if len(response) > MAX_MSG_LEN:
                response = response[: MAX_MSG_LEN - 60] + "\n\n… (truncated — full output in logs)"
            _failover_finish(failover_event_id, response)
            _tg_send(bot_token, chat_id, response, reply_to=msg_id)
            _observe_telegram_command(
                "/ask-tier-cheap",
                msg_id,
                query=query,
                response=response,
                status="ok",
                metadata={"model_used": model_used, "billing_surface": "local" if model_used == ASK_TIER_CHEAP_LOCAL_MODEL else "openrouter"},
            )
            log.info(f"/ask --tier cheap handled: chat={chat_id} model={model_used} q_len={len(query)} r_len={len(response)}")
            return True
        if _is_openclaw_identity_question(query):
            response = _openclaw_identity_answer()
            _tg_send(bot_token, chat_id, response, reply_to=msg_id)
            _observe_telegram_command("/ask-openclaw-identity", msg_id, query=query, response=response, status="ok")
            log.info(f"/ask OpenClaw identity answered locally: chat={chat_id} q_len={len(query)}")
            return True
        if _is_satory_event_intake_status_query(query):
            data, error = _fetch_satory_event_intake_snapshot()
            response = _format_satory_event_intake_status(data, error)
            _tg_send(bot_token, chat_id, response, reply_to=msg_id)
            _observe_telegram_command(
                "/ask-satory-event-intake-status",
                msg_id,
                query=query,
                response=response,
                status="error" if error else "ok",
            )
            log.info(
                "/ask Satory event-intake status answered locally: chat=%s q_len=%s api_error=%s",
                chat_id,
                len(query),
                bool(error),
            )
            return True
        if _maybe_hold_for_quiet_hours(bot_token, chat_id, msg_id, t):
            return True
        failover_event_id = _failover_start("/ask", msg_id, chat_id, query, model="openclaw-router", via="/ask router")
        if _is_group_chat(chat_id) and needs_owner_credential_handoff(query):
            body = _extract_group_message_body(query)
            sender = _extract_group_sender_context(t) or _CURRENT_GROUP_SENDER or "unknown"
            handled = handle_owner_credential_handoff(bot_token, chat_id, msg_id, body, sender)
            if handled:
                log.info(
                    "/ask owner credential handoff handled: chat=%s msg_id=%s sender=%s body_len=%s",
                    chat_id,
                    msg_id,
                    sender,
                    len(body),
                )
                return True
            _tg_send(
                bot_token,
                chat_id,
                "Не смог передать доступы владельцу. Мади проверит вручную.",
                reply_to=msg_id,
            )
            return True
        preview = query[:80] + ("…" if len(query) > 80 else "")
        if _requires_codex_verification_route(query):
            _budget_ok, _today_spend = _codex_daily_budget_ok()
            if not _budget_ok:
                log.warning(
                    "/ask shell-verification: codex budget gate closed; routing to "
                    "grok-ceo for chat=%s msg_id=%s today_spend=$%.2f",
                    chat_id, msg_id, _today_spend,
                )
                is_group = _is_group_chat(chat_id)
                notice = (
                    "⚠️ Codex недоступен (исчерпан суточный лимит). "
                    "Использую grok-ceo для shell-проверки.\n"
                    if is_group
                    else "⚠️ Codex daily cap reached; using grok-ceo for shell verification.\n"
                )
                _tg_progress(
                    bot_token, chat_id,
                    notice + f"<code>{preview}</code>",
                    msg_id,
                )
                fallback_query = query
                if is_group:
                    fallback_query = (
                        "Ответь строго на русском для внешней Telegram-группы. "
                        "Не показывай внутренние ошибки Codex, лимиты, route labels или английские diagnostics. "
                        "Если точной проверки нет, скажи это коротко и по фактам.\n\n"
                        f"{query}"
                    )
                response = _run_openclaw(fallback_query, agent_id="grok-ceo", correlation_id=f"tg_{msg_id}")
                response = _operator_visible_response(chat_id, (notice if is_group else "") + response)
                receipt = _write_telegram_task_result_receipt(
                    "/ask-auto-codex-grok-fallback",
                    msg_id,
                    query,
                    response,
                    model="grok-ceo",
                    via="/ask shell-verification fallback (codex capped)",
                )
                if len(response) > MAX_MSG_LEN:
                    suffix = f"\n\n…(truncated)\n📄 Full: wiki/{receipt}" if receipt else "\n\n… (truncated — receipt write failed)"
                    response = response[: MAX_MSG_LEN - len(suffix)] + suffix
                _failover_finish(failover_event_id, response, receipt=receipt, status="blocked")
                _tg_send(bot_token, chat_id, response, reply_to=msg_id)
                _observe_telegram_command(
                    "/ask-auto-codex-grok-fallback",
                    msg_id, query=query, response=response, status="blocked",
                )
                return True
            _tg_progress(
                bot_token,
                chat_id,
                "🤖 Auto-escalating shell verification to /codex on Air…\n"
                f"<code>{preview}</code>",
                msg_id,
            )
            response = _run_codex(query)
            if _is_codex_cap_blocked(response):
                log.warning(
                    "/ask shell-verification: budget gate passed but codex returned "
                    "cap sentinel mid-call; falling back to grok-ceo for chat=%s msg_id=%s",
                    chat_id, msg_id,
                )
                fallback_query = query
                if _is_group_chat(chat_id):
                    fallback_query = (
                        "Ответь строго на русском для внешней Telegram-группы. "
                        "Не показывай внутренние ошибки Codex, лимиты, route labels или английские diagnostics. "
                        "Если точной проверки нет, скажи это коротко и по фактам.\n\n"
                        f"{query}"
                    )
                response = _run_openclaw(fallback_query, agent_id="grok-ceo", correlation_id=f"tg_{msg_id}")
            response = _operator_visible_response(chat_id, response)
            receipt = _write_telegram_task_result_receipt(
                "/ask-auto-codex",
                msg_id,
                query,
                response,
                model=CODEX_MODEL,
                via="/ask auto-escalated to /codex",
            )
            if len(response) > MAX_MSG_LEN:
                suffix = f"\n\n…(truncated)\n📄 Full: wiki/{receipt}" if receipt else "\n\n… (truncated — receipt write failed)"
                response = response[: MAX_MSG_LEN - len(suffix)] + suffix
            _failover_finish(failover_event_id, response, receipt=receipt)
            _tg_send(bot_token, chat_id, response, reply_to=msg_id)
            _observe_telegram_command("/ask-auto-codex", msg_id, query=query, response=response, status="ok")
            log.info(f"/ask auto-escalated to /codex: chat={chat_id} q_len={len(query)} r_len={len(response)}")
            return True
        route_decision = _factory_orchestration_decision(query)
        route = route_decision.get("route")
        if route == ROUTE_LONG_WORK_GOAL:
            goal = _create_goal_page(query, "none")
            todoist = _create_todoist_task(query, "none", goal["rel_path"])
            kick = _kick_goal_cycle()
            todoist_line = (
                f"Todoist: {todoist.get('id') or todoist.get('url') or 'created'}"
                if todoist.get("ok")
                else f"Todoist not created: {todoist.get('error', 'unknown error')}"
            )
            runner_line = (
                f"Runner: {kick.get('message', 'started')}"
                if kick.get("ok")
                else f"Runner not started: {kick.get('message', 'unknown error')}"
            )
            response = (
                "Long work converted into durable factory state.\n"
                f"Route: OpenClaw Telegram -> LangGraph policy -> Goal/Todoist -> worker slices.\n"
                f"First pass: {route_decision.get('first_pass_model', 'grok-reasoning')}.\n"
                f"Worker pipeline: {_format_model_pipeline(query)}.\n"
                f"Wiki: {goal['rel_path']}\n"
                f"{todoist_line}\n"
                f"{runner_line}\n"
                "Hermes remains canary-only; OpenClaw remains production."
            )
            _tg_send(bot_token, chat_id, response, reply_to=msg_id)
            _failover_finish(failover_event_id, response, status="ok" if todoist.get("ok") and kick.get("ok") else "partial")
            _observe_telegram_command(
                "/ask-langgraph-goal",
                msg_id,
                query=query,
                response=response,
                status="ok" if todoist.get("ok") and kick.get("ok") else "partial",
                metadata={"route": route, "goal_path": goal["rel_path"], "todoist_ok": todoist.get("ok")},
            )
            log.info(
                f"/ask routed to LangGraph goal: chat={chat_id} path={goal['rel_path']} "
                f"todoist_ok={todoist.get('ok')} kick_ok={kick.get('ok')}"
            )
            return True
        if route == ROUTE_CHATGPT_EXECUTION:
            _budget_ok, _today_spend = _codex_daily_budget_ok()
            if _budget_ok:
                _tg_progress(
                    bot_token,
                    chat_id,
                    "🤖 Routing bounded execution to ChatGPT/Codex GPT-5.5 subscription…\n"
                    f"<code>{preview}</code>\n"
                    f"<i>Today's Codex spend: ${_today_spend:.2f} of $5 cap.</i>",
                    msg_id,
                )
                response = _run_codex(query)
                if _is_codex_cap_blocked(response):
                    log.warning(
                        "/ask langgraph-codex-execution: budget gate passed but codex "
                        "returned cap sentinel mid-call; falling back to grok-ceo for "
                        "chat=%s msg_id=%s today_spend=$%.2f",
                        chat_id, msg_id, _today_spend,
                    )
                    fallback_query = query
                    if _is_group_chat(chat_id):
                        fallback_query = (
                            "Ответь строго на русском для внешней Telegram-группы. "
                            "Не показывай внутренние ошибки Codex, лимиты, route labels или английские diagnostics. "
                            "Если точной проверки нет, скажи это коротко и по фактам.\n\n"
                            f"{query}"
                        )
                    response = _run_openclaw(fallback_query, agent_id="grok-ceo", correlation_id=f"tg_{msg_id}")
                response = _operator_visible_response(chat_id, response)
                receipt = _write_telegram_task_result_receipt(
                    "/ask-langgraph-codex-execution",
                    msg_id,
                    query,
                    response,
                    model=CODEX_MODEL,
                    via="/ask LangGraph route: ChatGPT/Codex execution",
                )
                if len(response) > MAX_MSG_LEN:
                    suffix = f"\n\n…(truncated)\n📄 Full: wiki/{receipt}" if receipt else "\n\n… (truncated — receipt write failed)"
                    response = response[: MAX_MSG_LEN - len(suffix)] + suffix
                _failover_finish(failover_event_id, response, receipt=receipt)
                _tg_send(bot_token, chat_id, response, reply_to=msg_id)
                _observe_telegram_command(
                    "/ask-langgraph-codex-execution", msg_id, query=query, response=response, status="ok",
                )
                log.info(
                    f"/ask routed to ChatGPT/Codex execution: chat={chat_id} q_len={len(query)} "
                    f"r_len={len(response)} today_spend=${_today_spend:.2f}"
                )
                return True
            if _is_mandatory_codex_decision(route_decision):
                # AP-41 (supersedes AP-30 for user-facing replies): never bounce a
                # real user with English wall-of-text when Codex is capped.
                # Fall back to grok-ceo Tier-1 with a transparent notice in the
                # appropriate language. Operator awareness preserved via log +
                # receipt + degraded status.
                is_group = _is_group_chat(chat_id)
                if is_group:
                    notice = (
                        "⚠️ <i>Codex недоступен (исчерпан суточный лимит токенов). "
                        "Использую grok-ceo Tier-1 для ответа. "
                        "Полная Codex-проверка вернётся после полуночи (Алматы).</i>\n\n"
                    )
                else:
                    notice = (
                        "⚠️ <i>Codex недоступен (daily token cap reached, today "
                        f"${_today_spend:.2f} of $5). Falling back to grok-ceo Tier-1. "
                        "Codex resets midnight Almaty.</i>\n\n"
                    )
                fallback_query = query
                if is_group:
                    fallback_query = (
                        "Ответь строго на русском для внешней Telegram-группы. "
                        "Не показывай внутренние ошибки Codex, лимиты, route labels или английские diagnostics. "
                        "Если точной проверки нет, скажи это коротко и по фактам.\n\n"
                        f"{query}"
                    )
                _tg_progress(bot_token, chat_id, notice, msg_id)
                grok_response = _run_openclaw(fallback_query, agent_id="grok-ceo", correlation_id=f"tg_{msg_id}")
                response = notice + _operator_visible_response(chat_id, grok_response)
                receipt = _write_telegram_task_result_receipt(
                    "/ask-mandatory-codex-grok-fallback",
                    msg_id,
                    query,
                    response,
                    model="grok-ceo",
                    via=f"/ask mandatory codex fallback ({'group' if is_group else 'dm'}): codex capped, grok-ceo used",
                )
                if len(response) > MAX_MSG_LEN:
                    suffix = f"\n\n…(truncated)\n📄 Full: wiki/{receipt}" if receipt else "\n\n… (truncated — receipt write failed)"
                    response = response[: MAX_MSG_LEN - len(suffix)] + suffix
                _failover_finish(failover_event_id, response, receipt=receipt, status="degraded")
                _tg_send(bot_token, chat_id, response, reply_to=msg_id)
                _observe_telegram_command(
                    "/ask-mandatory-codex-grok-fallback",
                    msg_id,
                    query=query,
                    response=response,
                    status="degraded",
                    metadata={
                        "route": route,
                        "reason": route_decision.get("reason"),
                        "fallback_model": "grok-ceo",
                        "chat_kind": "group" if is_group else "dm",
                    },
                )
                log.warning(
                    "/ask mandatory Codex blocked -> grok-ceo fallback: chat=%s kind=%s q_len=%s today_spend=$%.2f reason=%s",
                    chat_id,
                    "group" if is_group else "dm",
                    len(query),
                    _today_spend,
                    route_decision.get("reason"),
                )
                return True
        if route == ROUTE_GROK_DECISION:
            _tg_progress(
                bot_token,
                chat_id,
                "🧭 Routing decision/strategy prompt to OpenClaw grok-ceo first pass…\n"
                f"<code>{preview}</code>",
                msg_id,
            )
            response = _run_openclaw(query, agent_id="grok-ceo", correlation_id=f"tg_{msg_id}")
            _footer = _compose_cost_footer(f"tg_{msg_id}")
            if _footer and not _is_group_chat(chat_id):
                response = response + "\n\n" + _footer
            response = _operator_visible_response(chat_id, response)
            _failover_finish(failover_event_id, response)
            _tg_send(bot_token, chat_id, response, reply_to=msg_id)
            _observe_telegram_command("/ask-langgraph-grok-decision", msg_id, query=query, response=response, status="ok")
            log.info(f"/ask routed to Grok decision first-pass: chat={chat_id} q_len={len(query)} r_len={len(response)}")
            return True
        if _query_likely_needs_high_judgment(query):
            _budget_ok, _today_spend = _codex_daily_budget_ok()
            _tg_progress(
                bot_token,
                chat_id,
                "🧠 Auto-escalating high-judgment query to /codex (GPT-5.5)…\n"
                f"<code>{preview}</code>\n"
                f"<i>Today's Codex spend: ${_today_spend:.2f} of $5 cap.</i>",
                msg_id,
            )
            response = _run_codex(query)
            if _is_codex_cap_blocked(response):
                log.warning(
                    "/ask high-judgment: budget gate passed but codex returned cap "
                    "sentinel mid-call; falling back to grok-ceo for chat=%s msg_id=%s "
                    "today_spend=$%.2f",
                    chat_id, msg_id, _today_spend,
                )
                response = _run_openclaw(query, agent_id="grok-ceo", correlation_id=f"tg_{msg_id}")
            response = _operator_visible_response(chat_id, response)
            receipt = _write_telegram_task_result_receipt(
                "/ask-auto-codex-high-judgment",
                msg_id,
                query,
                response,
                model=CODEX_MODEL,
                via="/ask high-judgment auto-escalated to /codex",
            )
            if len(response) > MAX_MSG_LEN:
                suffix = f"\n\n…(truncated)\n📄 Full: wiki/{receipt}" if receipt else "\n\n… (truncated — receipt write failed)"
                response = response[: MAX_MSG_LEN - len(suffix)] + suffix
            _failover_finish(failover_event_id, response, receipt=receipt)
            _tg_send(bot_token, chat_id, response, reply_to=msg_id)
            _observe_telegram_command(
                "/ask-auto-codex-high-judgment", msg_id, query=query, response=response, status="ok",
            )
            log.info(
                f"/ask auto-escalated to /codex (high-judgment): chat={chat_id} q_len={len(query)} "
                f"r_len={len(response)} today_spend=${_today_spend:.2f}"
            )
            return True
        _tg_progress(
            bot_token, chat_id,
            f"⏳ Routing to OpenClaw…\n<code>{preview}</code>",
            msg_id,
        )
        response = _run_openclaw(query, agent_id="grok-ceo", correlation_id=f"tg_{msg_id}")  # s73: removed model=opus hard-code so Tier-1 grok-ceo classifies first; only delegate path hits Opus 4.7. Costs drop 90%+ for chat-class /ask.
        _footer = _compose_cost_footer(f"tg_{msg_id}")
        if _footer and not _is_group_chat(chat_id):
            response = response + "\n\n" + _footer
        _classify_footer = _classify_inbox_post_ask(msg_id, query)
        if _classify_footer and not _is_group_chat(chat_id):
            response = response + "\n\n" + _classify_footer
        response = _operator_visible_response(chat_id, response)
        if len(response) > MAX_MSG_LEN:
            response = response[: MAX_MSG_LEN - 60] + "\n\n… (truncated — full output in logs)"
        _failover_finish(failover_event_id, response)
        _tg_send(bot_token, chat_id, response, reply_to=msg_id)
        _observe_telegram_command("/ask", msg_id, query=query, response=response, status="ok")
        log.info(f"/ask handled: chat={chat_id} q_len={len(query)} r_len={len(response)}")
        return True

    return False
