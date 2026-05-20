"""Telegram CEO Listener — non-blocking, SQLite-routed, Mem0-learning."""

import sqlite3
import logging
import os
import threading
import time
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "telegram_messages.db")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def _init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS telegram_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            chat_id INTEGER,
            user_id INTEGER,
            username TEXT,
            message_text TEXT,
            processed INTEGER DEFAULT 0,
            ceo_response TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


def store_message(chat_id, user_id, username, text):
    _init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO telegram_messages (timestamp, chat_id, user_id, username, message_text) VALUES (?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), chat_id, user_id, username, text)
    )
    conn.commit()
    conn.close()


def get_unprocessed_messages():
    _init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM telegram_messages WHERE processed = 0 ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_processed(msg_id, response=""):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE telegram_messages SET processed = 1, ceo_response = ? WHERE id = ?", (response, msg_id))
    conn.commit()
    conn.close()


def send_reply(text):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text[:4000]}, timeout=10)
    except Exception:
        pass


def _poll_loop():
    """Background thread: polls Telegram for new messages, stores in SQLite."""
    if not BOT_TOKEN:
        logger.warning("No TELEGRAM_BOT_TOKEN — listener disabled")
        return

    last_update_id = 0
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/getUpdates"

    while True:
        try:
            resp = requests.get(url, params={"offset": last_update_id + 1, "timeout": 30}, timeout=35)
            if resp.status_code != 200:
                time.sleep(10)
                continue

            for update in resp.json().get("result", []):
                last_update_id = update["update_id"]
                msg = update.get("message", {})
                if not msg:
                    continue

                chat_id = msg.get("chat", {}).get("id", 0)
                user_id = msg.get("from", {}).get("id", 0)
                username = msg.get("from", {}).get("username", "unknown")
                text = msg.get("text", "")

                if not text:
                    continue

                # Skip APPROVE/REJECT messages — handled by approval gate
                if text.strip().upper() in ("APPROVE", "REJECT"):
                    continue

                store_message(chat_id, user_id, username, text)
                logger.info("[Listener] Stored message from %s: %s", username, text[:50])

                # Immediate ACK
                send_reply("Принято. CEO обработает в следующем цикле.")

        except Exception as e:
            logger.error("[Listener] Poll error: %s", e)
            time.sleep(10)


def start_listener():
    """Start the Telegram listener in a background daemon thread. Non-blocking."""
    _init_db()
    t = threading.Thread(target=_poll_loop, daemon=True, name="telegram-listener")
    t.start()
    logger.info("Telegram CEO Listener started (background thread)")
    return t
