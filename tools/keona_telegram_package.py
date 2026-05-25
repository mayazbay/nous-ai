#!/usr/bin/env python3
"""Send the KEONA internal Telegram package to the Keon-A topic.

This wrapper exists so agents do not compose free-form English packages for the
Russian-speaking Satory group.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


CHAT_ID = "-1002064137259"
TOPIC_ID = "1357"
BANNED_OPERATOR_PHRASES = (
    "next:",
    "files attached",
    "revised contract",
    "site prep",
    "installation manual",
    "tax certificate",
    "heater + tax certificate",
)


def default_message() -> str:
    return """KEONA

Получили от Lim:
- Структура согласована: Spectra ITS / Maru Analytics / Satory.
- Сертификат налогового резидентства получен.
- Нагреватель шкафа: 220В / 500Вт.
- 3 АПК уже производятся в Корее.

Что делаем:
1. Мади/Назель: отправить обновленный договор.
2. Брокер: финализировать 10-значный код ТН ВЭД ЕАЭС; базовый код HS 9405.49.2000.
3. Асыл: проверить -40C, термостат и рабочую температуру шкафа.
4. Keon-A: добрать требования к площадке, инструкцию по монтажу, питание/трафик АПК, дату готовности/отгрузки, окно приезда инженера.

Файлы ниже: нагреватель + сертификат налогового резидентства."""


def validate_keona_message(text: str) -> list[str]:
    errors: list[str] = []
    if not any("\u0400" <= char <= "\u04ff" for char in text):
        errors.append("message has no Cyrillic")
    lower = text.lower()
    for phrase in BANNED_OPERATOR_PHRASES:
        if phrase in lower:
            errors.append(f"message contains banned English operator phrase: {phrase}")
    return errors


def build_sender_command(files: list[Path], *, text: str, dry_run: bool) -> list[str]:
    sender = Path(__file__).with_name("telegram_topic_send.py")
    command = [
        sys.executable,
        str(sender),
        "--chat",
        CHAT_ID,
        "--topic",
        TOPIC_ID,
        "--require-cyrillic",
        "--text",
        text,
    ]
    for file_path in files:
        command.extend(["--file", str(file_path)])
    if dry_run:
        command.append("--dry-run")
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description="Send the Russian KEONA package to the Keon-A Telegram topic.")
    parser.add_argument("--file", action="append", default=[], help="File to attach. Pass every Gmail attachment.")
    parser.add_argument("--text", default=default_message(), help="Override message text; must remain Russian-facing.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned payload without sending.")
    args = parser.parse_args()

    files = [Path(value).expanduser() for value in args.file]
    if not files:
        print("keona_telegram_package: pass every Gmail attachment with --file", file=sys.stderr)
        return 2
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        print(f"keona_telegram_package: file not found: {', '.join(missing)}", file=sys.stderr)
        return 2

    text_errors = validate_keona_message(args.text)
    if text_errors:
        print("keona_telegram_package: " + "; ".join(text_errors), file=sys.stderr)
        return 2

    command = build_sender_command(files, text=args.text, dry_run=args.dry_run)
    if args.dry_run:
        print(json.dumps({"command": command, "files": [str(path) for path in files]}, ensure_ascii=False, indent=2))

    result = subprocess.run(command, check=False, text=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
