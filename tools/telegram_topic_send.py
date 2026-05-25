#!/usr/bin/env python3
"""Send-only Telegram helper for forum topics and multi-file packages.

No getUpdates call is made here. Air's telegram_poll.py remains the only
consumer of @nousAGaaSbot updates.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from uuid import uuid4


DEFAULT_ENV_PATHS = (
    Path.home() / "nous-agaas" / ".env",
    Path("/Users/madia/nous-agaas/.env"),
    Path("/root/nous-agaas/.env"),
)


def _read_env_value(path: Path, key: str) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        return ""
    return ""


def resolve_env_value(key: str, *, allow_air: bool = True) -> str:
    value = os.environ.get(key, "").strip()
    if value:
        return value
    for path in DEFAULT_ENV_PATHS:
        value = _read_env_value(path, key)
        if value:
            return value
    if allow_air:
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o",
                    "ConnectTimeout=5",
                    "-o",
                    "BatchMode=yes",
                    "air",
                    f"grep '^{key}=' ~/nous-agaas/.env 2>/dev/null | cut -d= -f2-",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=8,
            )
            return result.stdout.strip()
        except Exception:
            return ""
    return ""


def _api_url(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def https_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def post_form(token: str, method: str, fields: dict[str, str]) -> dict:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(_api_url(token, method), data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30, context=https_context()) as response:
        return json.loads(response.read().decode("utf-8"))


def post_multipart(token: str, method: str, fields: dict[str, str], file_field: str, file_path: Path) -> dict:
    boundary = f"----nous-{uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")

    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    chunks.append(f"--{boundary}\r\n".encode())
    chunks.append(
        (
            f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_path.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8")
    )
    chunks.append(file_path.read_bytes())
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(_api_url(token, method), data=b"".join(chunks), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=120, context=https_context()) as response:
        return json.loads(response.read().decode("utf-8"))


def message_fields(chat_id: str, topic_id: str | None) -> dict[str, str]:
    fields = {"chat_id": chat_id}
    if topic_id:
        fields["message_thread_id"] = topic_id
    return fields


def contains_cyrillic(text: str) -> bool:
    return any("\u0400" <= char <= "\u04ff" for char in text)


def validate_text(text: str, *, require_cyrillic: bool = False) -> str:
    if require_cyrillic and text and not contains_cyrillic(text):
        return "telegram_topic_send: refusing text without Cyrillic; pass Russian-facing copy"
    return ""


def result_summary(response: dict) -> dict:
    result = response.get("result") or {}
    return {
        "ok": bool(response.get("ok")),
        "message_id": result.get("message_id"),
        "message_thread_id": result.get("message_thread_id"),
        "date": result.get("date"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Send text and multiple files to a Telegram forum topic.")
    parser.add_argument("--chat", default="", help="Telegram chat id. Defaults to TELEGRAM_GROUP_CHAT_ID or TELEGRAM_CHAT_ID.")
    parser.add_argument("--topic", default="", help="Telegram forum message_thread_id. Required for group chats unless --allow-general.")
    parser.add_argument("--allow-general", action="store_true", help="Permit sending to a group without a forum topic.")
    parser.add_argument("--text", default="", help="Text message to send before files.")
    parser.add_argument("--file", action="append", default=[], help="File to attach. May be repeated.")
    parser.add_argument("--caption", action="append", default=[], help="Optional caption for files, in order.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned payload without sending.")
    parser.add_argument("--require-cyrillic", action="store_true", help="Refuse text that has no Cyrillic characters.")
    args = parser.parse_args()

    chat_id = args.chat or resolve_env_value("TELEGRAM_GROUP_CHAT_ID") or resolve_env_value("TELEGRAM_CHAT_ID")
    topic_id = args.topic.strip()
    if not chat_id:
        print("telegram_topic_send: chat id not found", file=sys.stderr)
        return 2
    if chat_id.startswith("-") and not topic_id and not args.allow_general:
        print("telegram_topic_send: refusing group send without --topic; pass --allow-general deliberately", file=sys.stderr)
        return 2
    if not args.text and not args.file:
        print("telegram_topic_send: provide --text or at least one --file", file=sys.stderr)
        return 2
    text_error = validate_text(args.text, require_cyrillic=args.require_cyrillic)
    if text_error:
        print(text_error, file=sys.stderr)
        return 2

    files = [Path(p).expanduser() for p in args.file]
    missing = [str(p) for p in files if not p.is_file()]
    if missing:
        print(f"telegram_topic_send: file not found: {', '.join(missing)}", file=sys.stderr)
        return 2

    plan = {
        "chat_id": chat_id,
        "message_thread_id": topic_id or None,
        "text": bool(args.text),
        "files": [str(p) for p in files],
    }
    if args.dry_run:
        print(json.dumps({"dry_run": True, **plan}, ensure_ascii=False, indent=2))
        return 0

    token = resolve_env_value("TELEGRAM_BOT_TOKEN")
    if not token:
        print("telegram_topic_send: TELEGRAM_BOT_TOKEN not found", file=sys.stderr)
        return 1

    sent: list[dict] = []
    base_fields = message_fields(chat_id, topic_id or None)
    try:
        if args.text:
            response = post_form(token, "sendMessage", {**base_fields, "text": args.text})
            if not response.get("ok"):
                raise RuntimeError(response.get("description", "sendMessage failed"))
            sent.append({"method": "sendMessage", **result_summary(response)})
        for index, file_path in enumerate(files):
            fields = dict(base_fields)
            if index < len(args.caption) and args.caption[index]:
                fields["caption"] = args.caption[index]
            response = post_multipart(token, "sendDocument", fields, "document", file_path)
            if not response.get("ok"):
                raise RuntimeError(response.get("description", f"sendDocument failed: {file_path}"))
            sent.append({"method": "sendDocument", "file": str(file_path), **result_summary(response)})
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        print(json.dumps({"ok": False, **plan, "error": body}, ensure_ascii=False), file=sys.stderr)
        return 3
    except Exception as exc:
        print(json.dumps({"ok": False, **plan, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 3

    print(json.dumps({"ok": True, **plan, "sent": sent}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
