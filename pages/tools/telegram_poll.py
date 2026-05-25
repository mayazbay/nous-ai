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
import urllib.request
import urllib.parse

sys.path.insert(0, "/opt/nous-agaas")
from dotenv import load_dotenv
import command_center
load_dotenv("/root/nous-agaas/.env", override=True)

WIKI = Path("/root/nous-agaas/wiki")
PENDING = WIKI / "raw" / "pending"
STATE = Path("/root/nous-agaas/logs/telegram_poll_state.json")
LOG = Path("/root/nous-agaas/logs/telegram_poll.log")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))

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
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"last_update_id": 0}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))


def telegram_api(method: str, params: dict = None):
    """Call Telegram bot API via POST (handles long text bodies). Returns parsed JSON or raises."""
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = urllib.parse.urlencode(params or {}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_ack(chat_id: int, reply_to_msg_id: int, kind: str, filename: str):
    """Send a threaded reply to the user confirming capture into the vault.

    LAW-005 enforcement: every captured message gets an ACK so Madi knows
    silence = capture failure, not just 'no reply yet'.

    LESSON-064: logs EXPLICITLY on success + failure so the log is the proof.
    Previously this function was silent on success, which meant we could not
    tell from the log whether the ACK was delivered or silently dropped.
    """
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


def process_message(msg: dict):
    """Save a message to raw/pending/ and reply with an ACK.

    Returns a tuple (success: bool, kind: str, filename: str) so main() can
    log + confirm. On chat-not-allowed returns (False, 'denied', '').
    """
    chat_id = msg.get("chat", {}).get("id", 0)
    if ALLOWED_CHAT_ID and chat_id != ALLOWED_CHAT_ID:
        log.warning(f"Ignoring message from non-allowed chat {chat_id}")
        return (False, "denied", "")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    msg_id = msg.get("message_id", 0)

    caption = msg.get("caption", "") or msg.get("text", "")
    parsed = parse_caption(caption)
    tags_suffix = "-".join(parsed["tags"][:3]) if parsed["tags"] else ""
    tags_suffix = ("-" + tags_suffix) if tags_suffix else ""

    PENDING.mkdir(parents=True, exist_ok=True)

    def _ack(kind: str, filename: str):
        """Helper: log + send Telegram ACK so Madi knows it landed."""
        log.info(f"saved {kind}: {filename}")
        send_ack(chat_id, int(msg_id), kind, filename)
        return (True, kind, filename)

    # Plain text message
    if "text" in msg:
        body = msg["text"]
        # Route commands (/ask, /status, /help) to OpenClaw before vault capture.
        if command_center.is_command(body):
            handled = command_center.handle(BOT_TOKEN, chat_id, int(msg_id), body)
            if handled:
                log.info(f"Command handled: chat={chat_id} msg_id={msg_id} text={body[:40]!r}")
                return (True, "command", "")
        elif ALLOWED_CHAT_ID and chat_id == ALLOWED_CHAT_ID and body.strip() and not body.strip().startswith("/"):
            # Implicit /ask: any plain text from the authorized chat routes to OpenClaw.
            # Lets Madi forward messages directly without typing /ask prefix.
            handled = command_center.handle(BOT_TOKEN, chat_id, int(msg_id), "/ask " + body.strip())
            if handled:
                log.info(f"Implicit /ask: chat={chat_id} msg_id={msg_id} text={body[:40]!r}")
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
    state = load_state()
    last_id = state.get("last_update_id", 0)
    # Long-poll loop: run for 50s so cron (every 60s) restarts safely.
    # timeout=25: Telegram holds the connection open 25s waiting for new messages.
    # Result: message latency <1s instead of up to 60s with timeout=0.
    deadline = time.monotonic() + 50
    while time.monotonic() < deadline:
        try:
            result = telegram_api("getUpdates", {"offset": last_id + 1, "timeout": 25})
        except Exception as e:
            log.error(f"getUpdates failed: {e}")
            return 1

        if not result.get("ok"):
            log.error(f"API not ok: {result}")
            return 1

        updates = result.get("result", [])
        if not updates:
            continue  # No messages in 25s window — start next long-poll

        log.info(f"Processing {len(updates)} update(s)")
        processed = 0
        max_id = last_id
        for upd in updates:
            max_id = max(max_id, upd.get("update_id", 0))
            msg = upd.get("message") or upd.get("channel_post")
            if not msg:
                continue
            success, kind, _filename = process_message(msg)
            if success:
                processed += 1
        last_id = max_id
        state["last_update_id"] = max_id
        save_state(state)
        log.info(f"Saved {processed}/{len(updates)} messages, last_update_id={max_id}")
    return 0



if __name__ == "__main__":
    sys.exit(main())
