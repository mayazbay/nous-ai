#!/usr/bin/env python3
"""
raw/ folder hygiene enforcer.

Walks /root/nous-agaas/wiki/raw/ top level. Any file that isn't README.md gets
auto-routed to the appropriate subfolder by extension/name pattern. Files that
don't match a known pattern go to unsorted/ (visible, flagged, never deleted).

LESSON-059 prevention. Cron every 5 minutes. Cheap, no LLM, file ops only.
"""
import os
import re
import shutil
import time
from pathlib import Path

WIKI = Path("/root/nous-agaas/wiki")
RAW = WIKI / "raw"
LOG = Path("/root/nous-agaas/logs/raw_hygiene.log")

# Files allowed at the top level of raw/ — anything else gets routed
TOP_LEVEL_WHITELIST = {"README.md"}

# Allowed subfolders (created if missing)
SUBFOLDERS = {
    "recordings", "meetings", "telegram", "state-snapshots",
    "documents", "images", "legal", "specs", "team",
    "transcripts", "pending", "processed", "unsorted",
}

def route_file(name: str) -> str:
    """Pick destination subfolder for a file based on name + extension."""
    n = name.lower()
    ext = Path(name).suffix.lower()

    # Audio
    if ext in (".m4a", ".mp3", ".wav", ".aac", ".ogg", ".flac"):
        return "recordings"
    # Images
    if ext in (".png", ".jpg", ".jpeg", ".heic", ".gif", ".webp"):
        return "images"
    # PDFs and office docs
    if ext in (".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt"):
        return "documents"
    # Markdown — route by name pattern
    if ext == ".md":
        if re.search(r"telegram|whatsapp|signal|message", n):
            return "telegram"
        if re.search(r"meeting|weekly-call|standup|sync|call-", n):
            return "meetings"
        if re.search(r"master.state|snapshot|state-", n):
            return "state-snapshots"
        if re.search(r"spec|specification|requirements", n):
            return "specs"
        if re.search(r"legal|contract|nda|agreement|koap", n):
            return "legal"
        # Generic md without clear category → unsorted
        return "unsorted"
    # Anything else
    return "unsorted"


def log_msg(msg: str):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")


def main():
    if not RAW.exists():
        return 0

    moved = 0
    for entry in RAW.iterdir():
        if not entry.is_file():
            continue
        if entry.name in TOP_LEVEL_WHITELIST:
            continue
        if entry.name.startswith("."):
            continue

        # Empty file — delete (likely accidental)
        if entry.stat().st_size == 0:
            entry.unlink()
            log_msg(f"deleted empty file: {entry.name}")
            moved += 1
            continue

        dest_folder = route_file(entry.name)
        dest_dir = RAW / dest_folder
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Avoid clobber
        target = dest_dir / entry.name
        if target.exists():
            ts = time.strftime("%Y%m%d-%H%M%S")
            stem = entry.stem
            ext = entry.suffix
            target = dest_dir / f"{stem}-{ts}{ext}"

        try:
            shutil.move(str(entry), str(target))
            log_msg(f"routed {entry.name} → {dest_folder}/{target.name}")
            moved += 1
        except Exception as e:
            log_msg(f"FAILED to route {entry.name}: {e}")

    return 0 if moved == 0 else 0  # always return 0 (informational)


if __name__ == "__main__":
    raise SystemExit(main())
