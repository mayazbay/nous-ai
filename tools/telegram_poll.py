#!/usr/bin/env python3
"""
Telegram bot poller — captures any message Madi sends to @nousAGaaSbot.

Polls Telegram getUpdates API every cycle. For each new message:
- Plain text → save as raw/pending/telegram-YYYY-MM-DD-HHMMSS-text.md
- Voice memo → download .ogg → save to raw/pending/telegram-YYYY-MM-DD-HHMMSS-voice.ogg
                (ingest_pending.py will then transcribe via Gemini)
- Photo → download .jpg → raw/pending/
- Document (PDF, DOCX, etc) → download → raw/pending/
- Audio file → download → raw/pending/

Caption parsing (OPTIONAL):
- No caption → file goes to raw/pending/ as-is
- Caption with tags → tags appended to filename for later use by ingest_pending.py
- Caption with /nous (default) → routes to Nous vault (only vault we have)

Cron every minute. Cost: $0 polling, $0 LLM (just HTTP).

LESSON-058 + AUDIT-023 P1.6 follow-up.
"""
import os
import sys
import json
import re
import time
import logging
from pathlib import Path
from datetime import datetime
import fcntl
import urllib.request
import urllib.parse
import urllib.error

TOOLS_DIR = Path(__file__).resolve().parent
RUNTIME_ROOT = Path("/Users/madia/nous-agaas")
sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(1, str(RUNTIME_ROOT))
from dotenv import load_dotenv
_preloaded_command_center = sys.modules.get("command_center")
_command_center_path = TOOLS_DIR / "command_center.py"
if _preloaded_command_center is not None and Path(getattr(_preloaded_command_center, "__file__", "") or "").resolve() != _command_center_path.resolve():
    import importlib.util
    _cc_spec = importlib.util.spec_from_file_location("_telegram_tools_command_center", _command_center_path)
    command_center = importlib.util.module_from_spec(_cc_spec)
    assert _cc_spec.loader is not None
    _cc_spec.loader.exec_module(command_center)
else:
    import command_center
load_dotenv("/Users/madia/nous-agaas/.env", override=True)

WIKI = Path("/Users/madia/nous-agaas/wiki")
PENDING = WIKI / "raw" / "pending"
STATE = Path("/Users/madia/nous-agaas/logs/telegram_poll_state.json")
LOCK  = Path("/Users/madia/nous-agaas/logs/telegram_poll.lock")
LOG = Path("/Users/madia/nous-agaas/logs/telegram_poll.log")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))


def _parse_chat_ids(*raw_values: str) -> set[int]:
    ids: set[int] = set()
    for raw in raw_values:
        for part in re.split(r"[\s,]+", raw or ""):
            if not part:
                continue
            try:
                ids.add(int(part))
            except ValueError:
                logging.getLogger("telegram_poll").warning(f"invalid Telegram chat id ignored: {part!r}")
    return ids


ALLOWED_CHAT_IDS = _parse_chat_ids(
    os.environ.get("TELEGRAM_CHAT_ID", ""),
    os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", ""),
    os.environ.get("TELEGRAM_GROUP_CHAT_ID", ""),
)
FULL_CHAT_CHAT_IDS = _parse_chat_ids(
    os.environ.get("TELEGRAM_FULL_CHAT_CHAT_IDS", ""),
    os.environ.get("TELEGRAM_GROUP_OBSERVE_CHAT_IDS", ""),
)
BOT_USERNAMES = {"nousagaasbot"}
FACTORY_PROOF_MARKERS = (
    "ai-фабрика взяла задачу в one-beam очередь",
    "one-beam очередь",
    "satory-ai-factory-queue",
)
SATORY_OPERATOR_ACTION_RE = re.compile(
    r"(\?|дай|дайте|нужен|нужны|нужно|можешь|можно|проверь|посмотри|скажи|ответь|"
    r"отправь|сделай|оформи|создай|скинь|кинь|передай)",
    re.IGNORECASE,
)
SATORY_OPERATOR_DOMAIN_RE = re.compile(
    r"(ерап|erap|апк|apk|бдл|bdl|заявк|нарушен|логин|парол|доступ|камера|вар|"
    r"радар|factory|фабрик|openclaw|nous|todoist|notion|public\s+ip|публичн|"
    r"\bip\b|\bпорт\b|\bport\b|протокол|protocol|https|http|чекбокс|"
    r"продуктивн|продакшн|production|\bprod\b|\btest\b|тестов)",
    re.IGNORECASE,
)
OWNER_CREDENTIAL_HANDOFF_RE = re.compile(
    r"(\blogin\b|\bpassword\b|credential|credentials|secret|token|api[-_\s]?key|"
    r"логин|парол|секрет|доступы|доступов|"
    r"(^|\n)\s*(test|prod|production|тест|прод)\s*:)",
    re.IGNORECASE,
)
TRANSIENT_GETUPDATES_ERROR_SNIPPETS = (
    "timed out",
    "temporary failure",
    "nodename nor servname",
    "network is unreachable",
    "connection reset",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("telegram_poll")

# Madi verbatim 2026-04-08: "you must be in almaty time so i know you are right."
# Force all log timestamps to Asia/Almaty regardless of system timezone.
try:
    import zoneinfo
    _ALMATY = zoneinfo.ZoneInfo("Asia/Almaty")
    def _almaty_converter(timestamp):
        return datetime.fromtimestamp(timestamp, tz=_ALMATY).timetuple()
    for _h in logging.root.handlers:
        if _h.formatter is not None:
            _h.formatter.converter = _almaty_converter
    # Update the format to include explicit TZ so ambiguity is impossible
    _fmt = logging.Formatter("%(asctime)s +05 [%(levelname)s] %(message)s")
    _fmt.converter = _almaty_converter
    for _h in logging.root.handlers:
        _h.setFormatter(_fmt)
except Exception as _e:
    log.warning(f"could not force Almaty timezone in log format: {_e}")


def load_state():
    """Read state with retry — guards against reading empty file during atomic replace.
    Falls back to 0 only if state truly does not exist, never due to a transient read race.
    """
    for _attempt in range(5):
        if STATE.exists():
            try:
                data = json.loads(STATE.read_text())
                if isinstance(data.get("last_update_id"), int):
                    return data
            except Exception:
                pass
        import time as _time
        _time.sleep(0.02)  # 20ms retry — outlasts any write
    return {"last_update_id": 0}


def save_state(state):
    """Atomic write — write to .tmp then os.replace() to avoid read-empty-file race.
    os.replace() is atomic on Linux (same filesystem), so load_state() never
    sees a truncated/empty file. LESSON-088.
    """
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2))
    import os as _os
    _os.replace(str(tmp), str(STATE))


def telegram_api(method: str, params: dict = None):
    """Call Telegram bot API via POST (handles long text bodies). Returns parsed JSON or raises."""
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = urllib.parse.urlencode(params or {}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_reaction(chat_id: int, msg_id: int, emoji: str = "👍") -> bool:
    """Acknowledge group capture/routing without adding a noisy message."""
    try:
        result = telegram_api(
            "setMessageReaction",
            {
                "chat_id": chat_id,
                "message_id": msg_id,
                "reaction": json.dumps([{"type": "emoji", "emoji": emoji}], ensure_ascii=False),
            },
        )
        ok = result.get("ok") is True
        if ok:
            log.info(f"reaction sent OK: emoji={emoji} -> chat={chat_id} msg_id={msg_id}")
        else:
            log.warning(f"reaction rejected by Telegram: {result}")
        return ok
    except Exception as e:
        log.warning(f"send_reaction raised: {type(e).__name__}: {e}")
        return False


def _is_getupdates_conflict_error(exc: Exception) -> bool:
    if isinstance(exc, urllib.error.HTTPError) and exc.code == 409:
        return True
    text = str(exc).lower()
    return "409" in text and "conflict" in text


def _is_transient_getupdates_error(exc: Exception) -> bool:
    if _is_getupdates_conflict_error(exc):
        return False
    if isinstance(exc, (TimeoutError, urllib.error.URLError)):
        return True
    text = str(exc).lower()
    return any(snippet in text for snippet in TRANSIENT_GETUPDATES_ERROR_SNIPPETS)


def send_ack(chat_id: int, reply_to_msg_id: int, kind: str, filename: str):
    """Send a threaded reply to the user confirming capture into the vault.

    LAW-005 enforcement: every captured message gets an ACK so Madi knows
    silence = capture failure, not just 'no reply yet'.

    LESSON-064: logs EXPLICITLY on success + failure so the log is the proof.
    Previously this function was silent on success, which meant we could not
    tell from the log whether the ACK was delivered or silently dropped.
    """
    if chat_id < 0:
        if send_reaction(chat_id, reply_to_msg_id):
            return
        text = "👍"
    else:
        text = (
        f"[captured into vault]\n"
        f"type: {kind}\n"
        f"file: raw/pending/{filename}\n"
        f"next: ingest_pending.py cron will process it within 60s "
        f"(text -> summary, audio -> Gemini transcript, doc/photo -> saved as-is)."
        )
    try:
        result = telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "reply_to_message_id": reply_to_msg_id,
        })
        if result.get("ok") is True:
            ack_msg_id = result.get("result", {}).get("message_id")
            log.info(f"ACK sent OK: bot msg_id={ack_msg_id} -> chat={chat_id} reply_to={reply_to_msg_id}")
        else:
            # Telegram returned HTTP 200 but ok:false (e.g., reply_to not found, chat blocked, etc.)
            # Fall back to a non-threaded message so the user still gets the ACK.
            log.warning(f"ACK threaded reply rejected by Telegram: {result}. Falling back to plain send.")
            fallback = telegram_api("sendMessage", {"chat_id": chat_id, "text": text})
            if fallback.get("ok") is True:
                log.info(f"ACK sent OK (fallback plain): bot msg_id={fallback.get('result', {}).get('message_id')}")
            else:
                log.error(f"ACK fallback ALSO failed: {fallback}")
    except Exception as e:
        log.error(f"send_ack raised: {type(e).__name__}: {e}")


def download_file(file_id: str, dest_path: Path) -> bool:
    """Download a file from Telegram by file_id."""
    try:
        info = telegram_api("getFile", {"file_id": file_id})
        if not info.get("ok"):
            log.error(f"getFile failed: {info}")
            return False
        file_path = info["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        with urllib.request.urlopen(url, timeout=120) as resp:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(resp.read())
        return True
    except Exception as e:
        log.error(f"download_file failed: {e}")
        return False


def slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s.lower())
    s = re.sub(r"\s+", "-", s.strip())
    return s[:50].strip("-") or "untitled"


def parse_caption(caption: str) -> dict:
    """Parse optional caption for routing + tags. Caption is OPTIONAL."""
    if not caption:
        return {"vault": "nous", "tags": []}
    parts = caption.lower().split()
    tags = []
    vault = "nous"  # default
    for p in parts:
        if p == "/nous":
            vault = "nous"
        elif p == "/brain":
            # We deleted Brain — fallback to nous
            vault = "nous"
        elif p.startswith("#"):
            tags.append(p[1:])
        else:
            tags.append(p.replace("-", "_"))
    return {"vault": vault, "tags": tags}


def is_allowed_chat(chat_id: int) -> bool:
    """Allow DMs and explicitly allowlisted groups.

    Backwards-compatible behavior: if no allowlist is configured, the poller
    behaves like the old script and accepts all chats. Production sets
    TELEGRAM_CHAT_ID, so every non-Madi group must be allowlisted explicitly.
    """
    return not ALLOWED_CHAT_IDS or chat_id in ALLOWED_CHAT_IDS


def is_full_chat_observed(chat_id: int) -> bool:
    """Return true for allowlisted group chats where every text message is persisted.

    This is intentionally separate from ALLOWED_CHAT_IDS: a group can be allowed
    for commands without becoming a full-chat source.
    """
    return chat_id in FULL_CHAT_CHAT_IDS


def sender_label(msg: dict) -> str:
    """Compact sender label for inbox provenance."""
    sender = msg.get("from") or {}
    username = (sender.get("username") or "").strip()
    if username:
        return f"@{username}"
    bits = [sender.get("first_name") or "", sender.get("last_name") or ""]
    name = " ".join(b.strip() for b in bits if b and b.strip())
    return name or str(sender.get("id") or "unknown")


def persist_text_inbox(chat_id: int, msg_id: int, body: str, sender: str, message_thread_id: int | None = None) -> str:
    """Persist Telegram text into the inbox without replying in chat.

    Returns the wiki slug, or empty string if persistence is disabled/failed.
    The existing inbox walker performs low-cost classification later, so this
    gives full-chat memory without spending LLM tokens on every group message.
    """
    if os.environ.get("TELEGRAM_INGEST_PERSIST", "1") in ("0", "off", "false"):
        return ""
    body = body.strip()
    if not body:
        return ""
    try:
        import subprocess as _sp
        _persist = (WIKI / "tools" / "telegram_ingest_persist.py")
        if not _persist.exists():
            return ""
        cmd = [
                "python3",
                str(_persist),
                "write",
                "--chat-id",
                str(chat_id),
                "--msg-id",
                str(msg_id),
                "--body",
                body,
                "--sender",
                sender,
        ]
        if message_thread_id is not None:
            cmd.extend(["--message-thread-id", str(message_thread_id)])
        _r = _sp.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if _r.returncode == 0:
            return _r.stdout.strip()
        log.warning(f"telegram_ingest persist failed: rc={_r.returncode} stderr={_r.stderr[:120]!r}")
    except Exception as _e:
        log.warning(f"telegram_ingest persist exception (graceful-degrade): {_e!r}")
    return ""


def persist_media_inbox(
    chat_id: int,
    msg_id: int,
    kind: str,
    filename: str,
    sender: str,
    caption: str = "",
    message_thread_id: int | None = None,
) -> str:
    """Persist a lightweight inbox note for media so files are retrievable now."""
    if os.environ.get("TELEGRAM_INGEST_PERSIST", "1") in ("0", "off", "false"):
        return ""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        day_dir = WIKI / "pages" / "inbox" / today
        day_dir.mkdir(parents=True, exist_ok=True)
        raw_rel = f"raw/pending/{filename}"
        inbox_file = day_dir / f"{msg_id}-media-{slugify(kind)}.md"
        title = f"Telegram {kind} capture {today} — {filename}"
        preview = f"\n![Captured {kind}](../../../{raw_rel})\n" if kind == "photo" else ""
        inbox_file.write_text(
            "\n".join(
                [
                    "---",
                    'type: "inbox"',
                    f'id: "inbox-{today}-{msg_id}-media"',
                    f'title: "{title}"',
                    f'date: "{today}"',
                    f'chat_id: {chat_id}',
                    f'msg_id: {msg_id}',
                    f'message_thread_id: {message_thread_id if message_thread_id is not None else "null"}',
                    f'sender: "{sender}"',
                    f'media_type: "{kind}"',
                    f'raw_path: "{raw_rel}"',
                    'status: "captured"',
                    "---",
                    "",
                    f"# {title}",
                    "",
                    f"- Sender: `{sender}`",
                    f"- Raw file: `{raw_rel}`",
                    f"- Caption: {caption.strip() or '_none_'}",
                    preview,
                ]
            )
        )
        return str(inbox_file.relative_to(WIKI))
    except Exception as _e:
        log.warning(f"media inbox persist exception (graceful-degrade): {_e!r}")
        return ""


def redact_for_route(text: str) -> str:
    """Redact credential-shaped text before sending group payloads to models."""
    try:
        from telegram_ingest_persist import redact_sensitive_text
        return redact_sensitive_text(text)
    except Exception as exc:
        log.warning(f"route redaction failed (using original text): {type(exc).__name__}: {exc}")
        return text


def normalize_bot_command(text: str) -> str:
    """Normalize group commands like /ask@nousAGaaSbot into /ask."""
    return re.sub(r"^/([A-Za-z0-9_-]+)@[A-Za-z0-9_]+(?=\s|$)", r"/\1", text.strip(), count=1)


def _strip_factory_address(text: str) -> tuple[str, bool]:
    """Strip natural bot/factory address from a group message.

    This is the no-slash interface: "Фабрика, проверь статус" and
    "Nous, compare X/Y" should behave like addressed bot requests, while
    ordinary team chatter remains observation-only.
    """
    stripped = text.strip()
    if not stripped:
        return "", False
    mention = re.match(r"^@([A-Za-z0-9_]+)(?=\s|[:,.!?]|$)", stripped)
    if mention:
        username = mention.group(1).lower()
        if username in BOT_USERNAMES:
            return re.sub(r"^@[A-Za-z0-9_]+[\s:,.!?-]*", "", stripped, count=1).strip(), True
        return stripped, False
    address_re = re.compile(
        r"^(?:"
        r"nous(?:\s+ai)?|"
        r"nousagaasbot|"
        r"фабрика|"
        r"бот|"
        r"ии|"
        r"ai|"
        r"openclaw|"
        r"опенклоу"
        r")[\s:,.!?-]+",
        re.IGNORECASE,
    )
    if address_re.match(stripped):
        return address_re.sub("", stripped, count=1).strip(), True
    return stripped, False


def _strip_bot_mentions_anywhere(text: str) -> tuple[str, bool]:
    """Strip @nousAGaaSbot mentions from any position in a group message.

    Humans commonly ping the bot at the end of a sentence. Human @mentions must
    remain observe-only; only the factory bot username turns the message into an
    execution request.
    """
    found = False

    def _replace(match: re.Match) -> str:
        nonlocal found
        username = match.group(1).lower()
        if username in BOT_USERNAMES:
            found = True
            return " "
        return match.group(0)

    cleaned = re.sub(r"@([A-Za-z0-9_]+)", _replace, text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip(" \t\n\r:,.!?-")
    return cleaned, found


def _is_meta_forward_bot_mention(text: str) -> bool:
    """Return true for human coordination about forwarding something to the bot.

    In Satory group chat, "I will forward @nousAGaaSbot" is not an instruction
    to the bot; executing it wastes a model call and can leak internal answers.
    """
    if not re.search(r"@nousAGaaSbot\b", text, re.IGNORECASE):
        return False
    low = text.lower()
    return bool(
        re.search(r"\bforward(?:ing|ed)?\b", low)
        or re.search(r"\bперешл|перешлю|перешли|пересл", low)
    )


def natural_command(text: str) -> str:
    """Map natural operator language to the internal command surface.

    Slash commands stay as implementation detail. This function intentionally
    stays deterministic and conservative: broad work goes to /ask unless the
    operator clearly asks for status, a persistent goal, or the GPT/Codex lane.
    """
    query = normalize_bot_command(text).strip()
    if not query:
        return ""
    if query.startswith("/"):
        return query

    low = query.lower()
    compact = " ".join(low.split())

    if re.search(r"\b(status|health|factory health|runtime health)\b", compact) or re.search(
        r"\b(статус|здоровье|состояние)\b", compact
    ):
        if re.search(r"\b(report|отчет|отчёт|cost|spend|budget|расход)\b", compact):
            return "/report"
        if re.search(r"\b(health|здоровье|состояние)\b", compact):
            return "/health"
        return "/status"

    goal_match = re.match(
        r"^(?:goal|цель|создай цель|создать цель|поставь цель|запусти goal|запусти цель)[:\s-]+(.+)$",
        query,
        flags=re.IGNORECASE,
    )
    if goal_match:
        return "/goal " + goal_match.group(1).strip()

    codex_match = re.match(
        r"^(?:use\s+)?(?:codex|gpt[-\s]?5\.5|top[-\s]?tier\s+gpt|топовый\s+gpt|топ\s+gpt)[:\s,-]*(?:to\s+)?(.+)$",
        query,
        flags=re.IGNORECASE,
    )
    if codex_match and codex_match.group(1).strip():
        return "/codex " + codex_match.group(1).strip()

    if re.search(
        r"\b(top[-\s]?tier|second brain|2nd brain|gpt at the top|gpt on top|best cto|best ceo|karpathy|garry tan|elon|bulletproof|god level)\b",
        compact,
    ):
        return "/codex " + query

    code_match = re.match(
        r"^(?:claude\s+code|code\s+lane|sonnet\s+code)[:\s,-]*(?:to\s+)?(.+)$",
        query,
        flags=re.IGNORECASE,
    )
    if code_match and code_match.group(1).strip():
        return "/code " + code_match.group(1).strip()

    return "/ask " + query


def group_ai_request(text: str) -> str:
    """Return the explicit group AI request body, or empty string.

    In groups, normal chatter must not become implicit /ask. The operator must
    address the bot naturally ("Фабрика, ...", "Nous, ..."), via @mention, or
    via AI: prefix. Slash commands still work, but are not required.
    """
    stripped = text.strip()
    if stripped.lower().startswith("ai:"):
        return stripped[3:].strip()
    addressed, did_address = _strip_factory_address(stripped)
    if did_address:
        return addressed
    if _is_meta_forward_bot_mention(stripped):
        return ""
    addressed, did_address = _strip_bot_mentions_anywhere(stripped)
    if did_address:
        return addressed
    return ""


def group_operator_action_request(text: str, sender: str) -> str:
    """Return unaddressed Satory operator requests that should be answered.

    Full-chat observation remains the default. This gate only promotes messages
    that are both actionable and Satory/domain-specific, so greetings and human
    side chatter stay memory-only while operator asks like Asyl's ERAP login
    request do not get ignored.
    """
    stripped = text.strip()
    if not stripped or stripped.startswith("/"):
        return ""
    sender_name = sender.strip().lstrip("@").lower()
    if sender_name in BOT_USERNAMES:
        return ""
    low = stripped.lower()
    if any(marker in low for marker in FACTORY_PROOF_MARKERS):
        return ""
    if SATORY_OPERATOR_ACTION_RE.search(stripped) and SATORY_OPERATOR_DOMAIN_RE.search(stripped):
        return stripped
    return ""


def owner_credential_handoff_request(text: str) -> bool:
    """Credential-shaped group text bypasses models and goes to owner DM."""
    return bool(OWNER_CREDENTIAL_HANDOFF_RE.search(text or ""))


def add_group_sender_context(routed_text: str, sender: str) -> str:
    """Attach sender provenance to group LLM requests.

    Status/help/report commands should stay exact commands. LLM routes receive
    the sender label so the answer can distinguish who asked from who was
    mentioned in surrounding group context.
    """
    sender = (sender or "").strip()
    if not sender or sender == "unknown":
        return routed_text
    for prefix in ("/ask ", "/codex ", "/code "):
        if routed_text.startswith(prefix):
            return (
                prefix
                + f"Telegram group sender {sender}: if you greet anyone, greet {sender} or use Коллеги; "
                + "do not greet another person from surrounding context. Message: "
                + routed_text[len(prefix):]
            )
    return routed_text


def _recover_split_mention_body(
    chat_id: int,
    sender: str,
    exclude_msg_id: int,
    max_age_seconds: int = 60,
) -> str:
    """Telegram clients group consecutive same-sender messages visually, but the
    bot API delivers them as separate messages. When a group sender posts the
    bot mention alone (just "@nousAGaaSbot") after their actual question, the
    bot detects the mention but has empty body. This recovers the prior message
    body from the inbox for the same (chat, sender) within max_age_seconds.

    Returns the prior message body, or "" if none found.
    """
    if not sender or sender == "unknown":
        return ""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        day_dir = WIKI / "pages" / "inbox" / today
        if not day_dir.exists():
            return ""
        now_utc = datetime.utcnow()
        candidates = []
        for path in day_dir.glob("*.md"):
            try:
                txt = path.read_text(encoding="utf-8")
            except Exception:
                continue
            fm_match = re.match(r"^---\n(.+?)\n---\n", txt, re.DOTALL)
            if not fm_match:
                continue
            fm = fm_match.group(1)
            mid_m = re.search(r'msg_id:\s*"?(\d+)"?', fm)
            chat_m = re.search(r'chat_id:\s*(-?\d+)', fm)
            send_m = re.search(r'sender:\s*"([^"]*)"', fm)
            ts_m = re.search(r'ingested_at:\s*"([^"]+)"', fm)
            if not (mid_m and chat_m and send_m and ts_m):
                continue
            mid = int(mid_m.group(1))
            if mid == exclude_msg_id:
                continue
            if int(chat_m.group(1)) != chat_id:
                continue
            if send_m.group(1) != sender:
                continue
            try:
                ts = datetime.fromisoformat(ts_m.group(1).replace("Z", "+00:00"))
                ts_naive = ts.replace(tzinfo=None) if ts.tzinfo else ts
                if (now_utc - ts_naive).total_seconds() > max_age_seconds:
                    continue
            except Exception:
                continue
            body_m = re.search(r"# Original message\n\n(.+?)\n\n# ", txt, re.DOTALL)
            if not body_m:
                continue
            candidates.append((ts_naive, body_m.group(1).strip()))
        if not candidates:
            return ""
        candidates.sort(key=lambda c: c[0], reverse=True)
        return candidates[0][1]
    except Exception as e:
        log.warning(f"_recover_split_mention_body raised: {type(e).__name__}: {e}")
        return ""


def _is_standalone_bot_mention(text: str) -> bool:
    cleaned, found = _strip_bot_mentions_anywhere(text)
    return found and not cleaned.strip()


def _has_recent_standalone_bot_mention(
    chat_id: int,
    sender: str,
    exclude_msg_id: int,
    max_age_seconds: int = 120,
) -> bool:
    """Return true when the same sender addressed the bot in the previous msg.

    Telegram visually groups consecutive messages. If an operator sends
    "@nousAGaaSbot" and then the payload as the next message, the second
    message is intentionally addressed even though it contains no mention.
    """
    if not sender or sender == "unknown":
        return False
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        day_dir = WIKI / "pages" / "inbox" / today
        if not day_dir.exists():
            return False
        now_utc = datetime.utcnow()
        for path in sorted(day_dir.glob("*.md"), reverse=True):
            try:
                txt = path.read_text(encoding="utf-8")
            except Exception:
                continue
            fm_match = re.match(r"^---\n(.+?)\n---\n", txt, re.DOTALL)
            if not fm_match:
                continue
            fm = fm_match.group(1)
            mid_m = re.search(r'msg_id:\s*"?(\d+)"?', fm)
            chat_m = re.search(r'chat_id:\s*(-?\d+)', fm)
            send_m = re.search(r'sender:\s*"([^"]*)"', fm)
            ts_m = re.search(r'ingested_at:\s*"([^"]+)"', fm)
            if not (mid_m and chat_m and send_m and ts_m):
                continue
            mid = int(mid_m.group(1))
            if mid == exclude_msg_id:
                continue
            if int(chat_m.group(1)) != chat_id or send_m.group(1) != sender:
                continue
            try:
                ts = datetime.fromisoformat(ts_m.group(1).replace("Z", "+00:00"))
                ts_naive = ts.replace(tzinfo=None) if ts.tzinfo else ts
                if (now_utc - ts_naive).total_seconds() > max_age_seconds:
                    continue
            except Exception:
                continue
            body_m = re.search(r"# Original message\n\n(.+?)\n\n# ", txt, re.DOTALL)
            if body_m and _is_standalone_bot_mention(body_m.group(1).strip()):
                return True
        return False
    except Exception as e:
        log.warning(f"_has_recent_standalone_bot_mention raised: {type(e).__name__}: {e}")
        return False


def process_message(msg: dict):
    """Save a message to raw/pending/ and reply with an ACK.

    Returns a tuple (success: bool, kind: str, filename: str) so main() can
    log + confirm. On chat-not-allowed returns (False, 'denied', '').
    """
    chat = msg.get("chat", {})
    chat_id = chat.get("id", 0)
    is_private_chat = chat.get("type") == "private" or (ALLOWED_CHAT_ID and chat_id == ALLOWED_CHAT_ID)
    message_thread_id = msg.get("message_thread_id")
    if not is_allowed_chat(chat_id):
        log.warning(f"Ignoring message from non-allowed chat {chat_id}")
        return (False, "denied", "")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    msg_id = msg.get("message_id", 0)

    caption = msg.get("caption", "") or msg.get("text", "")
    parsed = parse_caption(caption)
    tags_suffix = "-".join(slugify(t) for t in parsed["tags"][:3] if slugify(t)) if parsed["tags"] else ""
    tags_suffix = ("-" + tags_suffix) if tags_suffix else ""

    PENDING.mkdir(parents=True, exist_ok=True)

    def _ack(kind: str, filename: str):
        """Helper: log + send Telegram ACK so Madi knows it landed."""
        log.info(f"saved {kind}: {filename}")
        if kind != "text" and (not is_private_chat) and is_full_chat_observed(chat_id):
            media_slug = persist_media_inbox(
                chat_id,
                int(msg_id),
                kind,
                filename,
                sender_label(msg),
                caption,
                message_thread_id=message_thread_id,
            )
            if media_slug:
                log.info(f"Group media captured: chat={chat_id} msg_id={msg_id} slug={media_slug}")
        send_ack(chat_id, int(msg_id), kind, filename)
        return (True, kind, filename)

    # Plain text message
    if "text" in msg:
        body = msg["text"]
        command_body = normalize_bot_command(body)
        observed_slug = ""
        if (not is_private_chat) and is_full_chat_observed(chat_id):
            observed_slug = persist_text_inbox(chat_id, int(msg_id), body, sender_label(msg), message_thread_id)
            if observed_slug:
                log.info(f"Group full-chat observed: chat={chat_id} msg_id={msg_id} slug={observed_slug}")
        # Route commands (/ask, /status, /help) to OpenClaw before vault capture.
        if command_center.is_command(command_body):
            handled = command_center.handle(BOT_TOKEN, chat_id, int(msg_id), command_body)
            if handled:
                log.info(f"Command handled: chat={chat_id} msg_id={msg_id} text={command_body[:40]!r}")
                return (True, "command", "")
        if (
            not is_private_chat
            and body.strip()
            and is_full_chat_observed(chat_id)
            and owner_credential_handoff_request(body)
        ):
            handoff = getattr(command_center, "handle_owner_credential_handoff", None)
            if callable(handoff):
                handled = handoff(
                    BOT_TOKEN,
                    chat_id,
                    int(msg_id),
                    body,
                    sender_label(msg),
                    owner_chat_id=ALLOWED_CHAT_ID,
                )
                if handled:
                    log.info(
                        f"Owner credential handoff routed: chat={chat_id} msg_id={msg_id} "
                        f"sender={sender_label(msg)}"
                    )
                    return (True, "command", "")
                return (False, "owner_credential_handoff_failed", "")
        group_request = "" if is_private_chat else group_ai_request(body)
        # Split-mention recovery: when a group sender posts "@nousAGaaSbot" as a
        # standalone follow-up to their previous message, group_ai_request finds
        # the mention but returns "" (empty body after strip). Telegram clients
        # show the two messages as one block, so users expect the bot to answer
        # their prior question. Look back in inbox for the most recent message
        # from the same (chat, sender) within 60s and route THAT body.
        if (
            not is_private_chat
            and not group_request
            and re.search(r"@nousAGaaSbot\b", body, re.IGNORECASE)
        ):
            prior_body = _recover_split_mention_body(
                chat_id, sender_label(msg), int(msg_id), max_age_seconds=60
            )
            if prior_body:
                log.info(
                    f"Split-mention recovery: routing prior body for chat={chat_id} "
                    f"sender={sender_label(msg)} msg_id={msg_id} len={len(prior_body)}"
                )
                group_request = prior_body
        if (
            not is_private_chat
            and not group_request
            and body.strip()
            and is_full_chat_observed(chat_id)
            and _has_recent_standalone_bot_mention(
                chat_id, sender_label(msg), int(msg_id), max_age_seconds=120
            )
        ):
            log.info(
                f"Forward split-mention recovery: routing current body for chat={chat_id} "
                f"sender={sender_label(msg)} msg_id={msg_id} len={len(body)}"
            )
            group_request = body
        if group_request:
            group_request = redact_for_route(group_request)
            routed_text = natural_command(group_request)
            routed_text = add_group_sender_context(routed_text, sender_label(msg))
            handled = command_center.handle(BOT_TOKEN, chat_id, int(msg_id), routed_text)
            if handled:
                log.info(f"Group natural command: chat={chat_id} msg_id={msg_id} text={routed_text[:60]!r}")
                return (True, "command", "")
            return (False, "group_ai_failed", "")
        if (not is_private_chat) and is_full_chat_observed(chat_id):
            operator_request = group_operator_action_request(body, sender_label(msg))
            if operator_request:
                routed_text = natural_command(redact_for_route(operator_request))
                routed_text = add_group_sender_context(routed_text, sender_label(msg))
                handled = command_center.handle(BOT_TOKEN, chat_id, int(msg_id), routed_text)
                if handled:
                    log.info(
                        f"Satory operator request routed: chat={chat_id} msg_id={msg_id} "
                        f"sender={sender_label(msg)} text={routed_text[:80]!r}"
                    )
                    return (True, "command", "")
                return (False, "group_ai_failed", "")
        if (not is_private_chat) and body.strip() and not command_body.startswith("/"):
            if is_full_chat_observed(chat_id):
                if observed_slug:
                    return (True, "observed_group", observed_slug)
                return (False, "observed_group_failed", "")
            log.info(f"Ignoring allowed group chatter without command/AI prefix: chat={chat_id} msg_id={msg_id}")
            return (False, "ignored_group", "")
        elif is_private_chat and body.strip() and not body.strip().startswith("/"):
            # Implicit /ask: any plain text from the authorized chat routes to OpenClaw.
            # Lets Madi forward messages directly without typing /ask prefix.

            # Phase 2 of telegram-ingest-pipeline (PLAN-2026-04-30): inbox-first
            # persistence BEFORE routing. Kill-switched via env (default ON when
            # tool present, OFF if env explicitly set to "0" or "off").
            # Failure here NEVER blocks the /ask route — bot reliability >
            # ingest persistence. AP-72 (session 82): persist-before-route +
            # graceful-degrade when persist fails.
            _slug = persist_text_inbox(chat_id, int(msg_id), body, "madi", message_thread_id)
            if _slug:
                log.info(f"telegram_ingest persisted: slug={_slug} msg_id={msg_id}")

            routed_text = natural_command(body)
            handled = command_center.handle(BOT_TOKEN, chat_id, int(msg_id), routed_text)
            if handled:
                log.info(f"Natural command: chat={chat_id} msg_id={msg_id} text={routed_text[:60]!r}")
                return (True, "command", "")
        slug = slugify(body[:40]) or f"msg-{msg_id}"
        out_file = PENDING / f"telegram-{timestamp}-{slug}{tags_suffix}.md"
        out_file.write_text(
            f"---\nsource: telegram\ntimestamp: {datetime.now().isoformat()}\nchat_id: {chat_id}\nmsg_id: {msg_id}\ntags: {parsed['tags']}\n---\n\n{body}\n"
        )
        return _ack("text", out_file.name)

    # Voice memo
    if "voice" in msg:
        voice = msg["voice"]
        file_id = voice["file_id"]
        out_file = PENDING / f"telegram-{timestamp}-voice-{voice.get('duration', 0)}s{tags_suffix}.ogg"
        if download_file(file_id, out_file):
            return _ack("voice", out_file.name)
        return (False, "voice", "")

    # Audio file (m4a, mp3, etc)
    if "audio" in msg:
        audio = msg["audio"]
        file_id = audio["file_id"]
        ext = (audio.get("file_name", "audio").split(".")[-1] if "." in audio.get("file_name", "") else "mp3")
        out_file = PENDING / f"telegram-{timestamp}-audio{tags_suffix}.{ext}"
        if download_file(file_id, out_file):
            return _ack("audio", out_file.name)
        return (False, "audio", "")

    # Document (PDF, DOCX, etc)
    if "document" in msg:
        doc = msg["document"]
        file_id = doc["file_id"]
        original_name = doc.get("file_name", "document")
        out_file = PENDING / f"telegram-{timestamp}-{slugify(original_name)}{tags_suffix}-{original_name}"
        if download_file(file_id, out_file):
            return _ack("document", out_file.name)
        return (False, "document", "")

    # Photo (take largest size)
    if "photo" in msg:
        photos = msg["photo"]
        largest = max(photos, key=lambda p: p.get("file_size", 0))
        file_id = largest["file_id"]
        out_file = PENDING / f"telegram-{timestamp}-photo{tags_suffix}.jpg"
        if download_file(file_id, out_file):
            return _ack("photo", out_file.name)
        return (False, "photo", "")

    # Video
    if "video" in msg:
        vid = msg["video"]
        file_id = vid["file_id"]
        out_file = PENDING / f"telegram-{timestamp}-video{tags_suffix}.mp4"
        if download_file(file_id, out_file):
            return _ack("video", out_file.name)
        return (False, "video", "")

    log.warning(f"Unknown message type, skipping: {list(msg.keys())}")
    return (False, "unknown", "")


def main():
    import time
    # Acquire exclusive lock — prevents simultaneous instances from calling
    # getUpdates concurrently (which causes 409 Conflict + duplicate routing).
    # Cron fires every 60s; this instance exits if a previous one is still alive.
    lock_fd = LOCK.open("w")
    try:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        log.info("another instance running — exiting")
        lock_fd.close()
        return 0
    lock_fd.write(str(os.getpid()))
    lock_fd.flush()

    state = load_state()
    last_id = state.get("last_update_id", 0)
    # Long-poll loop: run for 50s so cron (every 60s) restarts safely.
    # timeout=25: Telegram holds the connection open 25s waiting for new messages.
    # Result: message latency <1s instead of up to 60s with timeout=0.
    deadline = time.monotonic() + 50
    successful_polls = 0
    transient_failures = 0
    while time.monotonic() < deadline:
        try:
            result = telegram_api("getUpdates", {"offset": last_id + 1, "timeout": 25})
        except Exception as e:
            if _is_getupdates_conflict_error(e):
                log.error(f"getUpdates failed: {e}")
                return 1
            if _is_transient_getupdates_error(e):
                transient_failures += 1
                log.warning(f"getUpdates transient failure {transient_failures}: {e}")
                if time.monotonic() < deadline:
                    time.sleep(2)
                    continue
                break
            log.error(f"getUpdates failed: {e}")
            return 1

        if not result.get("ok"):
            log.error(f"API not ok: {result}")
            return 1
        successful_polls += 1

        updates = result.get("result", [])
        if not updates:
            continue  # No messages in 25s window — start next long-poll

        log.info(f"Processing {len(updates)} update(s)")
        processed = 0
        max_id = last_id
        for upd in updates:
            update_id = upd.get("update_id", 0)
            max_id = max(max_id, update_id)
            # Save offset BEFORE processing — prevents duplicate routing when
            # command_center.handle() blocks 60-300s waiting for OpenClaw and
            # the cron spawns a new telegram_poll instance that re-reads the
            # same update_id from state.
            state["last_update_id"] = max_id
            save_state(state)
            msg = upd.get("message") or upd.get("channel_post")
            if not msg:
                continue
            success, kind, _filename = process_message(msg)
            if success:
                processed += 1
        last_id = max_id
        log.info(f"Saved {processed}/{len(updates)} messages, last_update_id={max_id}")
    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
    lock_fd.close()
    if successful_polls == 0 and transient_failures:
        log.warning(f"getUpdates transient-only poll cycle: transient_failures={transient_failures}")
    return 0



if __name__ == "__main__":
    sys.exit(main())
