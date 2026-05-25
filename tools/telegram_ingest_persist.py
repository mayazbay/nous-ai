#!/usr/bin/env python3
"""telegram_ingest_persist.py — Phase 1 of telegram-ingest-pipeline.

Belt-and-braces persistence for every Telegram message that hits @nousAGaaSbot.
Writes an inbox note BEFORE classification fires. Classification happens
in-prompt at the /ask factory layer (DeepSeek V4 Flash) and is appended
to the inbox note's frontmatter post-hoc.

Per PLAN-2026-04-30-telegram-ingest-pipeline.md:
  - Single source of truth: pages/inbox/YYYY-MM-DD/<msg-id>-<intent>.md
  - Forward-only: no batch reprocessing of old messages tonight (Phase 2)
  - Intent classifier: deepseek-v4-flash via factory /ask path
  - Mercury fact write: only when intent=fact AND confidence>=0.8
  - TASKS.md write: only when intent=task AND has actionable verb

Usage (called from telegram_poll.py implicit /ask shim):
  python3 tools/telegram_ingest_persist.py write \\
    --chat-id 110793056 --msg-id 1234 --body "remember to read book X"
  → emits canonical inbox slug to stdout
  → caller routes /ask + appends inbox slug to context

  python3 tools/telegram_ingest_persist.py classify \\
    --slug pages/inbox/2026-04-30/1234-unknown.md \\
    --intent task --confidence 0.92 --rationale "actionable verb 'read book'"
  → updates frontmatter + may trigger side-effect writes
"""
import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

# Resolve vault path: ENV → script-relative location FIRST → standard locations.
# Script-relative is canonical: this script lives at <vault>/tools/, so its
# parent IS the vault. This eliminates ambiguity when multiple vault
# mirrors exist on the same host (Mac canonical vs Air-mirror sync target).
def _vault_root():
    env = os.environ.get("NOUS_VAULT_ROOT")
    if env and Path(env).exists():
        return Path(env)
    # Script-relative — script always lives at <vault>/tools/<this>.py
    script_relative = Path(__file__).parent.parent
    if (script_relative / "pages").is_dir():
        return script_relative
    # Standard locations (last resort)
    for cand in [
        Path("/Users/madia/Documents/Projects/Nous AGaaS/Nous"),  # Mac canonical
        Path("/Users/madia/nous-agaas/wiki"),                      # Air-mirror on Mac, OR Air canonical
        Path("/root/nous-agaas/wiki"),                             # VPS canonical
    ]:
        if (cand / "pages").is_dir():
            return cand
    return script_relative


VAULT = _vault_root()
INBOX_ROOT = VAULT / "pages" / "inbox"
TASKS_FILE = VAULT / "TASKS.md"
MERCURY_FACTS = VAULT / "pages" / "mercury" / "facts.jsonl"

VALID_INTENTS = {"note", "task", "fact", "question", "decision", "unknown"}


def redact_sensitive_text(text: str) -> str:
    """Redact credential-shaped Telegram text before it reaches the vault."""
    redacted = text

    # Common field forms: password: X, token=X, api_key: X, пароль: X.
    redacted = re.sub(
        r"(?i)\b(password|pass|pwd|пароль|token|secret|api[_-]?key)\s*[:=]\s*([^\s,;]+)",
        lambda m: f"{m.group(1)}=[REDACTED]",
        redacted,
    )

    # Camera/APK shorthand often arrives as: <ip> admin <password>.
    redacted = re.sub(
        r"(?i)\b((?:\d{1,3}\.){3}\d{1,3}\s+(?:admin|админ|root|user|username|login|логин)\s+)([^\s,;]+)",
        lambda m: f"{m.group(1)}[REDACTED]",
        redacted,
    )

    # Notes and model summaries can normalize the same shorthand as admin/<password>.
    redacted = re.sub(
        r"(?i)\b((?:admin|админ|root|user|username|login|логин)/)([^\s,;]+)",
        lambda m: f"{m.group(1)}[REDACTED]",
        redacted,
    )

    # Standalone "admin <password>" when the second token looks secret-like.
    redacted = re.sub(
        r"(?i)\b((?:admin|админ|root)\s+)(?=[^\s,;]*\d)([^\s,;]{6,})",
        lambda m: f"{m.group(1)}[REDACTED]",
        redacted,
    )

    # ERAP/APK operators often send environment passwords as "test:" and
    # "prod:" fields. Those are credential labels in this context, not harmless
    # prose, so redact secret-looking single-token values before vault write.
    def _redact_env_password(match: re.Match) -> str:
        label = match.group(1)
        value = match.group(2)
        secret_like = len(value) >= 8 and (
            bool(re.search(r"\d", value))
            or bool(re.search(r"[^A-Za-zА-Яа-я0-9_-]", value))
            or bool(re.search(r"[A-Z]", value) and re.search(r"[a-z]", value))
        )
        if not secret_like:
            return match.group(0)
        sep = ": " if ":" in match.group(0) else "="
        return f"{label}{sep}[REDACTED]"

    redacted = re.sub(
        r"(?im)\b(test|prod|production|прод|тест)\s*[:=]\s*([^\s,;]+)",
        _redact_env_password,
        redacted,
    )

    return redacted


def _slug_safe(s, maxlen=30):
    s = re.sub(r"[^\w\s-]", "", s.lower())
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:maxlen]


def write_inbox(
    chat_id: int,
    msg_id: int,
    body: str,
    sender: str = "madi",
    message_thread_id: int | None = None,
) -> str:
    """Write the canonical inbox note for a fresh Telegram message.
    Returns the slug (relative to vault) for caller to thread to classifier.
    Idempotent: writing the same msg_id twice produces same slug + content.
    """
    body = redact_sensitive_text(body.strip())
    if not body:
        raise ValueError("empty body")
    today = datetime.date.today().isoformat()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    day_dir = INBOX_ROOT / today
    day_dir.mkdir(parents=True, exist_ok=True)

    title_seed = re.sub(r"\s+", " ", body)[:30]
    initial_intent = "unknown"
    fname = f"{msg_id}-{initial_intent}.md"
    fpath = day_dir / fname

    if fpath.exists():
        # Idempotent — return existing slug
        rel = fpath.relative_to(VAULT).as_posix().removesuffix(".md")
        return rel

    fm = {
        "type": "inbox",
        "id": f"inbox-{today}-{msg_id}",
        "title": f"Telegram ingest {today} — {title_seed}",
        "date": today,
        "ingested_at": now,
        "chat_id": chat_id,
        "msg_id": msg_id,
        "sender": sender,
        "intent": initial_intent,
        "intent_confidence": 0.0,
        "classifier_model": "pending",
        "status": "ingested",
    }
    if message_thread_id is not None:
        fm["message_thread_id"] = message_thread_id

    body_md = (
        "---\n"
        + "\n".join(f"{k}: {json.dumps(v) if isinstance(v, str) else v}" for k, v in fm.items())
        + "\n---\n\n"
        "# Original message\n\n"
        f"{body}\n\n"
        "# Classifier rationale\n\n"
        "_pending — will be filled by /ask factory worker_\n\n"
        "# Side-effects\n\n"
        "- mercury fact added: pending\n"
        "- TASKS.md appended: pending\n"
        "- decision recorded: pending\n"
    )

    fpath.write_text(body_md, encoding="utf-8")
    rel = fpath.relative_to(VAULT).as_posix().removesuffix(".md")
    return rel


def classify(slug: str, intent: str, confidence: float, rationale: str,
             classifier_model: str = "deepseek-v4-flash") -> dict:
    """Update inbox note frontmatter with classifier verdict + run side-effects.
    Returns side-effect summary.
    """
    if intent not in VALID_INTENTS:
        raise ValueError(f"invalid intent: {intent}; must be one of {VALID_INTENTS}")
    if not (0.0 <= confidence <= 1.0):
        raise ValueError(f"confidence out of range: {confidence}")

    fpath = VAULT / f"{slug}.md"
    if not fpath.exists():
        raise FileNotFoundError(fpath)

    content = fpath.read_text(encoding="utf-8")
    # Update frontmatter fields (simple line-based replace; FM is well-formed by write_inbox)
    content = re.sub(r'^intent:.*$', f'intent: {intent}', content, count=1, flags=re.MULTILINE)
    content = re.sub(r'^intent_confidence:.*$', f'intent_confidence: {confidence}',
                     content, count=1, flags=re.MULTILINE)
    content = re.sub(r'^classifier_model:.*$', f'classifier_model: {classifier_model}',
                     content, count=1, flags=re.MULTILINE)
    # Replace pending rationale block
    content = content.replace(
        "_pending — will be filled by /ask factory worker_",
        rationale.strip() or "_no rationale provided_"
    )

    # Maybe rename file with new intent in slug
    if "-unknown" in fpath.name:
        new_name = fpath.name.replace("-unknown", f"-{intent}")
        new_path = fpath.with_name(new_name)
        # write content first, then rename
        fpath.write_text(content, encoding="utf-8")
        if new_path != fpath:
            fpath.rename(new_path)
            slug = new_path.relative_to(VAULT).as_posix().removesuffix(".md")
    else:
        fpath.write_text(content, encoding="utf-8")

    # Side-effects
    side = {"mercury": None, "tasks": None, "decision": None}

    body_match = re.search(r'# Original message\n\n(.+?)\n\n# ', content, re.DOTALL)
    body = body_match.group(1).strip() if body_match else ""

    if intent == "fact" and confidence >= 0.8:
        side["mercury"] = _add_mercury_fact(body, slug)
    elif intent == "task" and re.search(r'\b(remind|do|build|fix|ship|call|email|send|write|book|schedule)\b', body, re.IGNORECASE):
        side["tasks"] = _append_task(body, slug)
    elif intent == "decision":
        side["decision"] = _record_decision(body, slug)

    # Update side-effects block in inbox note
    fpath = VAULT / f"{slug}.md"
    content = fpath.read_text(encoding="utf-8")
    content = re.sub(
        r"- mercury fact added: pending",
        f"- mercury fact added: {side['mercury'] or 'none'}",
        content, count=1
    )
    content = re.sub(
        r"- TASKS\.md appended: pending",
        f"- TASKS.md appended: {side['tasks'] or 'none'}",
        content, count=1
    )
    content = re.sub(
        r"- decision recorded: pending",
        f"- decision recorded: {side['decision'] or 'none'}",
        content, count=1
    )
    fpath.write_text(content, encoding="utf-8")

    return {"slug": slug, "intent": intent, "confidence": confidence, "side_effects": side}


def _add_mercury_fact(body: str, source_slug: str) -> str:
    """Append a Mercury fact entry from inbox body. Returns fact_id."""
    MERCURY_FACTS.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    # Generate next fact id (cheap: count lines)
    fact_count = 0
    if MERCURY_FACTS.exists():
        with MERCURY_FACTS.open("r", encoding="utf-8") as f:
            fact_count = sum(1 for _ in f)
    fact_id = f"fact-{fact_count + 1:05d}"
    fact = {
        "id": fact_id,
        "schema_version": "1.0.0",
        "subject": body[:60],  # naive — better extraction in Phase 2
        "value": body,
        "value_hash": _hash_normalize(body),
        "confidence": 0.85,
        "freshness": today,
        "importance": 0.6,
        "reinforcement": 1,
        "source": f"[[{source_slug}]]",
        "conflicts_with": [],
        "load_bearing_in": [],
        "tags": ["from-telegram-inbox"],
        "decay_rule": "normal",
        "tombstone": False,
        "tombstone_reason": None,
        "tombstone_ts": None,
    }
    with MERCURY_FACTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fact, ensure_ascii=False) + "\n")
    return fact_id


def _append_task(body: str, source_slug: str) -> str:
    """Append a task line to TASKS.md. Returns the line written."""
    today = datetime.date.today().isoformat()
    line = f"- [ ] {body[:120]} _(from [[{source_slug}]] · {today})_"
    if not TASKS_FILE.exists():
        TASKS_FILE.write_text(
            "---\ntype: tasks\nid: TASKS\ntitle: \"Active task list\"\n"
            f"date: {today}\nlast_updated: {today}\nstatus: active\n---\n\n"
            "# Tasks\n\n",
            encoding="utf-8"
        )
    with TASKS_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line


def _record_decision(body: str, source_slug: str) -> str:
    """Write a decision page. Returns the slug."""
    today = datetime.date.today().isoformat()
    title_seed = _slug_safe(body[:40])
    decisions_dir = VAULT / "pages" / "decisions" / today
    decisions_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{title_seed or 'decision'}.md"
    fpath = decisions_dir / fname
    if fpath.exists():
        # collision — append timestamp
        fpath = decisions_dir / f"{title_seed or 'decision'}-{datetime.datetime.now().strftime('%H%M%S')}.md"
    fpath.write_text(
        f"---\ntype: decision\nid: decision-{today}-{title_seed}\n"
        f"title: \"{body[:60]}\"\ndate: {today}\nlast_updated: {today}\n"
        f"source: \"[[{source_slug}]]\"\nstatus: recorded\n---\n\n"
        f"# Decision\n\n{body}\n\n"
        f"## Source\n\n[[{source_slug}]]\n",
        encoding="utf-8"
    )
    return fpath.relative_to(VAULT).as_posix().removesuffix(".md")


def _hash_normalize(s: str) -> str:
    import hashlib
    norm = re.sub(r"\s+", " ", s.lower()).strip()
    norm = re.sub(r"[^\w\s]", "", norm)
    return "sha256:" + hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("write", help="write inbox note")
    w.add_argument("--chat-id", type=int, required=True)
    w.add_argument("--msg-id", type=int, required=True)
    w.add_argument("--message-thread-id", type=int)
    w.add_argument("--body", required=True)
    w.add_argument("--sender", default="madi")

    c = sub.add_parser("classify", help="update inbox note + side-effects")
    c.add_argument("--slug", required=True)
    c.add_argument("--intent", required=True, choices=sorted(VALID_INTENTS))
    c.add_argument("--confidence", type=float, required=True)
    c.add_argument("--rationale", default="")
    c.add_argument("--classifier-model", default="deepseek-v4-flash")

    args = ap.parse_args()
    if args.cmd == "write":
        slug = write_inbox(args.chat_id, args.msg_id, args.body, args.sender, args.message_thread_id)
        print(slug)
    elif args.cmd == "classify":
        result = classify(args.slug, args.intent, args.confidence,
                          args.rationale, args.classifier_model)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main() or 0)
