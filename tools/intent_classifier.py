#!/usr/bin/env python3
"""intent_classifier.py — Phase 2.5 of telegram-ingest-pipeline.

Single classifier shared by:
  1. Phase 2.5: command_center.handle() /ask path post-reply hook
  2. Gap 3: tools/inbox_walker.py hourly cron

Classifies a message body into ONE intent: note | task | fact | decision | question.
Uses LiteLLM deepseek-v4-flash via http://127.0.0.1:4000/chat/completions on Air.

Failure modes (graceful-degrade, NEVER raise to caller):
  - LiteLLM unreachable → returns {intent: "unknown", confidence: 0.0, rationale: "<error>"}
  - JSON parse failure → returns intent based on heuristic, low confidence
  - Empty body → {intent: "unknown", confidence: 0.0, rationale: "empty body"}

Per PLAN-2026-05-01-phase-2.5-and-gap-3.md.

Usage (CLI):
  echo "remember to read book X" | python3 tools/intent_classifier.py
  → {"intent": "task", "confidence": 0.92, "rationale": "actionable verb 'remember to read'"}

  python3 tools/intent_classifier.py --body "Decision: defer v0.23 upgrade"
  → {"intent": "decision", "confidence": 0.95, ...}

Env:
  LITELLM_BASE_URL  — default http://127.0.0.1:4000
  LITELLM_MASTER_KEY  — required (loaded from ~/nous-agaas/litellm/.env on Air)
  CLASSIFIER_MODEL  — default deepseek-v4-flash
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

VALID_INTENTS = {"note", "task", "fact", "question", "decision", "unknown"}

DEFAULT_MODEL = os.environ.get("CLASSIFIER_MODEL", "deepseek-v4-flash")
DEFAULT_BASE_URL = os.environ.get("LITELLM_BASE_URL", "http://127.0.0.1:4000")

CLASSIFIER_PROMPT = """Classify this message into ONE intent: note, task, fact, decision, or question.

Definitions:
- task: actionable verb + future tense ("remind me", "build X", "fix Y", "ship Z")
- fact: stated preference, configuration, or constraint ("we use X", "default is Y", "my chat_id is Z")
- decision: explicit decision marker ("Decision:", "we chose", "deferred", "going with X")
- question: asks for info (ends in "?", or starts with what/how/when/where/why/is/are/can)
- note: anything else (observations, status updates, ambient commentary)

Return ONLY raw JSON, no prose, no code-fence, no markdown:
{"intent": "...", "confidence": 0.0-1.0, "rationale": "..."}

confidence: 0.9+ when very clear, 0.7-0.9 when likely, 0.5-0.7 when ambiguous, <0.5 when unsure.
rationale: ONE sentence why this intent (max 80 chars).

Message:
"""


def _load_master_key():
    """Load LITELLM_MASTER_KEY from env or fallback to ~/nous-agaas/litellm/.env."""
    k = os.environ.get("LITELLM_MASTER_KEY")
    if k:
        return k
    env_path = Path.home() / "nous-agaas" / "litellm" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("LITELLM_MASTER_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return ""


def classify(body: str, model: str = DEFAULT_MODEL,
             base_url: str = DEFAULT_BASE_URL,
             timeout: float = 10.0) -> dict:
    """Returns {intent, confidence, rationale} dict.
    NEVER raises — graceful-degrade to {intent: 'unknown', ...} on any failure.
    """
    body = (body or "").strip()
    if not body:
        return {"intent": "unknown", "confidence": 0.0, "rationale": "empty body",
                "classifier_model": model}

    key = _load_master_key()
    if not key:
        return {"intent": "unknown", "confidence": 0.0,
                "rationale": "LITELLM_MASTER_KEY missing", "classifier_model": model}

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": CLASSIFIER_PROMPT + body}],
        "temperature": 0.0,
        "max_tokens": 200,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, OSError) as e:
        return {"intent": "unknown", "confidence": 0.0,
                "rationale": f"litellm error: {type(e).__name__}",
                "classifier_model": model}

    try:
        text = data["choices"][0]["message"]["content"]
        if text is None:
            return {"intent": "unknown", "confidence": 0.0,
                    "rationale": "litellm returned null content", "classifier_model": model}
        text = text.strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        return {"intent": "unknown", "confidence": 0.0,
                "rationale": "malformed litellm response", "classifier_model": model}

    # Strip optional markdown fence
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()

    try:
        verdict = json.loads(text)
    except json.JSONDecodeError:
        # Heuristic fallback: try to extract intent from text
        m = re.search(r'"intent"\s*:\s*"(\w+)"', text)
        if m and m.group(1) in VALID_INTENTS:
            return {"intent": m.group(1), "confidence": 0.5,
                    "rationale": "heuristic-extracted from non-JSON response",
                    "classifier_model": model}
        return {"intent": "unknown", "confidence": 0.0,
                "rationale": "classifier returned non-JSON", "classifier_model": model}

    intent = str(verdict.get("intent", "unknown")).lower().strip()
    if intent not in VALID_INTENTS:
        intent = "unknown"
    try:
        conf = float(verdict.get("confidence", 0.0))
        conf = max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        conf = 0.0
    rationale = str(verdict.get("rationale", "")).strip()[:200] or "no rationale"

    return {"intent": intent, "confidence": conf, "rationale": rationale,
            "classifier_model": model}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--body", help="message body to classify (or read from stdin if omitted)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--timeout", type=float, default=10.0)
    args = ap.parse_args()

    body = args.body if args.body is not None else sys.stdin.read()
    result = classify(body, model=args.model, base_url=args.base_url, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
