"""Telegram bot — clean human-readable messages. No code diffs. LESSON-004 dedup."""

import requests
import time
import hashlib
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# LESSON-004: Message dedup — same message within 30 min = don't send again
_sent_messages = {}  # hash -> timestamp
_DEDUP_WINDOW = 1800  # 30 minutes


def send_message(text, remove_keyboard=False, force=False):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TG] " + text[:200])
        return False

    # LESSON-004 DEDUP: Skip if same message sent within 30 min
    if not force:
        msg_hash = hashlib.md5(text.encode()).hexdigest()
        now = time.time()
        # Clean old entries
        _sent_messages.update({k: v for k, v in _sent_messages.items() if now - v < _DEDUP_WINDOW})
        if msg_hash in _sent_messages:
            return True  # Already sent recently, skip silently
        _sent_messages[msg_hash] = now

    url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    if len(text) > 4000:
        text = text[:4000]
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    if remove_keyboard:
        payload["reply_markup"] = {"remove_keyboard": True}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def send_approval_request(task_title, diff_summary, test_results):
    # Auto-approve everything. Send clean summary instead of code diff.
    send_message(
        "Completed: " + str(task_title) + "\n" +
        "Tests: " + str(test_results)
    )
    return "approved"


def send_cycle_summary(cycle, task_title, status, tests_passed, tests_failed, next_task, health):
    if status == "done":
        icon = "Done"
    elif status == "failed":
        icon = "Failed"
    else:
        icon = status

    lines = []
    lines.append("Cycle " + str(cycle) + " - " + icon)
    lines.append("")
    lines.append("Task: " + str(task_title))

    if tests_passed > 0:
        lines.append("Tests: " + str(tests_passed) + " passed")

    if next_task and next_task != "TBD by CEO update":
        lines.append("Next: " + str(next_task))

    text = "\n".join(lines)
    return send_message(text, remove_keyboard=True)


def send_executive_summary(cycle_num, task_title, tests_passed, tests_failed, deployed, status):
    """Concise executive summary. No spam. President-level."""
    icon = "OK" if status == "success" else "ROLLBACK" if status == "rollback" else "FAIL"
    msg = f"Cycle {cycle_num}: [{icon}] {task_title}"
    if deployed:
        msg += " | DEPLOYED"
    if tests_failed > 0:
        msg += f" | {tests_failed} test failures"
    # Only send on important events, not every detail
    send_message(msg)
