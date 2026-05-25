"""Bot-to-bot 4 proof gates — R1 of HANDSHAKE-2026-05-19-residuals-onebyone.

Per spec pages/specs/2026-05-19-telegram-bot-to-bot-4-proof-gates-design.md
(08c5e368). Madi requires these 4 gates BEFORE @nousAGaaSbot may send messages
to another bot. Defaults below match my spec's Clarify-Q recommendations;
Madi swaps them if Q1-Q4 land differently. Codex wires the pipeline into
tools/command_center.py later (his lane scope).

GATES (in pipeline order):
  1. KillSwitchGate     — env BOT_TO_BOT_ENABLED + runtime override file
  2. LoopDepthGate      — count `via-bot` markers; reject at N+1
  3. DedupeGate         — sha256(sender, recipient, body) seen in last W min
  4. RateLimitGate      — token bucket per (sender, chat)

NO live API calls. Caller (eventually Codex's command_center) wraps the
pipeline call before any _send_telegram_message() targeting a known bot.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

# --- Defaults from spec Q1-Q4 recommendations (Madi may override) ----------

# Q1 RECOMMENDED: distinct second bot (token-identity is the security boundary
# per CLAUDE.md HARD RULE 1). Same-token bot-bot is a special case that
# collapses dedupe; we don't allow it by default.
DEFAULT_ALLOW_SAME_TOKEN_SELF_LOOP = False

# Q2 RECOMMENDED: slash-only. Narrows surface, easier dedupe.
DEFAULT_REQUIRE_SLASH_PREFIX = True

# Q3 RECOMMENDED: all 3 layers (env + runtime override + plist). Implemented
# here at env+runtime; plist is a deploy-time concern.
# (handled inside KillSwitchGate)

# Q4 RECOMMENDED: max depth N=2 + operator-bypass via /handoff.
DEFAULT_MAX_DEPTH = 2

# Window/rate config (spec-defaults; Madi tunable):
DEFAULT_DEDUPE_WINDOW_S = 5 * 60  # 5 min
DEFAULT_RATE_K = 6                  # max sends per minute per (sender, chat)
DEFAULT_RATE_WINDOW_S = 60

# Wiki-relative state paths
DEDUPE_STATE_REL = "pages/systems/bot-to-bot-dedupe.json"
KILLSWITCH_STATE_REL = "pages/systems/bot-to-bot-runtime-override.json"
LEDGER_REL = "pages/systems/bot-to-bot-ledger.jsonl"


# --- Result types ----------------------------------------------------------

class GateRejection:
    """Returned by a gate when it blocks a send. Caller treats this as 'do not send'."""

    __slots__ = ("gate", "code", "detail")

    def __init__(self, gate: str, code: str, detail: str = "") -> None:
        self.gate = gate
        self.code = code
        self.detail = detail

    def __repr__(self) -> str:
        return f"GateRejection(gate={self.gate!r}, code={self.code!r}, detail={self.detail[:80]!r})"

    def as_dict(self) -> dict[str, str]:
        return {"gate": self.gate, "code": self.code, "detail": self.detail}


# --- Gate 1: KillSwitchGate ------------------------------------------------

class KillSwitchGate:
    """Env BOT_TO_BOT_ENABLED + runtime override file. BOTH must be enabled."""

    def __init__(self, wiki_root: Path) -> None:
        self.wiki_root = wiki_root
        self.runtime_state_path = wiki_root / KILLSWITCH_STATE_REL

    def check(self, ctx: dict[str, Any]) -> GateRejection | None:
        env_enabled = os.environ.get("BOT_TO_BOT_ENABLED", "false").lower() == "true"
        if not env_enabled:
            return GateRejection("KillSwitchGate", "ERR_KILL_SWITCH_ENV", "BOT_TO_BOT_ENABLED env not 'true'")

        # Runtime override file may force OFF (operator /kill bot-to-bot command).
        if self.runtime_state_path.exists():
            try:
                data = json.loads(self.runtime_state_path.read_text(encoding="utf-8"))
                if data.get("enabled") is False:
                    reason = data.get("reason") or "runtime override file says disabled"
                    return GateRejection("KillSwitchGate", "ERR_KILL_SWITCH_RUNTIME", reason)
            except (json.JSONDecodeError, OSError):
                # Conservative: unparseable state file = treat as disabled
                return GateRejection("KillSwitchGate", "ERR_KILL_SWITCH_PARSE", "runtime override file unparseable")

        return None


# --- Gate 2: LoopDepthGate -------------------------------------------------

class LoopDepthGate:
    """Count `via-bot:<id>` markers in conversation context; reject if depth would exceed N."""

    def __init__(self, max_depth: int = DEFAULT_MAX_DEPTH) -> None:
        self.max_depth = max_depth

    def check(self, ctx: dict[str, Any]) -> GateRejection | None:
        # ctx["thread_via_markers"] is a list of bot_ids in the conversation thread
        via_markers = ctx.get("thread_via_markers", [])
        depth = len(via_markers)

        # Operator-bypass: explicit /handoff slash command resets depth=0
        if ctx.get("body", "").lstrip().startswith("/handoff "):
            return None

        if depth >= self.max_depth:
            return GateRejection(
                "LoopDepthGate",
                "ERR_LOOP_DEPTH",
                f"depth={depth} >= max_depth={self.max_depth}; markers={via_markers}",
            )
        return None


# --- Gate 3: DedupeGate ----------------------------------------------------

class DedupeGate:
    """Hash (sender_bot_id, recipient_bot_id, normalized_body); reject within window."""

    def __init__(self, wiki_root: Path, window_s: int = DEFAULT_DEDUPE_WINDOW_S) -> None:
        self.wiki_root = wiki_root
        self.window_s = window_s
        self.state_path = wiki_root / DEDUPE_STATE_REL

    def _load(self) -> "OrderedDict[str, float]":
        if not self.state_path.exists():
            return OrderedDict()
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            return OrderedDict((str(k), float(v)) for k, v in raw.items())
        except (json.JSONDecodeError, OSError, ValueError):
            return OrderedDict()

    def _save(self, state: "OrderedDict[str, float]") -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        # Prune entries older than window
        now = time.time()
        pruned = OrderedDict((k, v) for k, v in state.items() if now - v < self.window_s)
        self.state_path.write_text(json.dumps(pruned, ensure_ascii=False), encoding="utf-8")

    def _key(self, sender: str, recipient: str, body: str) -> str:
        normalized = " ".join(body.split())  # whitespace-normalize
        raw = f"{sender}::{recipient}::{normalized}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def check(self, ctx: dict[str, Any]) -> GateRejection | None:
        sender = ctx.get("sender_bot_id", "")
        recipient = ctx.get("recipient_bot_id", "")
        body = ctx.get("body", "")
        idempotency_key = ctx.get("idempotency_key")
        if idempotency_key:
            # Caller asserted this is a legitimate retransmit; bypass dedupe
            return None

        key = self._key(sender, recipient, body)
        state = self._load()
        now = time.time()

        if key in state and (now - state[key]) < self.window_s:
            return GateRejection(
                "DedupeGate",
                "ERR_DEDUPE",
                f"same (sender, recipient, body) seen {int(now - state[key])}s ago < window={self.window_s}s",
            )

        # Record this send
        state[key] = now
        self._save(state)
        return None


# --- Gate 4: RateLimitGate -------------------------------------------------

class RateLimitGate:
    """Token bucket per (sender_bot_id, chat_id). K tokens per window."""

    def __init__(self, k: int = DEFAULT_RATE_K, window_s: int = DEFAULT_RATE_WINDOW_S) -> None:
        self.k = k
        self.window_s = window_s
        # In-memory bucket: caller is expected to hold this gate instance for the runner lifetime
        self._buckets: dict[tuple[str, str], list[float]] = {}

    def check(self, ctx: dict[str, Any]) -> GateRejection | None:
        sender = ctx.get("sender_bot_id", "")
        chat = ctx.get("chat_id", "")
        bucket_key = (sender, str(chat))
        now = time.time()
        bucket = self._buckets.setdefault(bucket_key, [])

        # Drop expired timestamps
        bucket[:] = [ts for ts in bucket if now - ts < self.window_s]

        if len(bucket) >= self.k:
            return GateRejection(
                "RateLimitGate",
                "ERR_RATE_LIMIT",
                f"sender={sender} chat={chat} already {len(bucket)} sends in last {self.window_s}s (cap {self.k})",
            )

        bucket.append(now)
        return None


# --- Pipeline --------------------------------------------------------------

def make_default_pipeline(wiki_root: Path) -> list[Any]:
    """Construct the 4-gate pipeline in canonical order (kill-switch first)."""
    return [
        KillSwitchGate(wiki_root),
        LoopDepthGate(max_depth=DEFAULT_MAX_DEPTH),
        DedupeGate(wiki_root, window_s=DEFAULT_DEDUPE_WINDOW_S),
        RateLimitGate(k=DEFAULT_RATE_K, window_s=DEFAULT_RATE_WINDOW_S),
    ]


def run_pipeline(gates: list[Any], ctx: dict[str, Any], wiki_root: Path | None = None) -> GateRejection | None:
    """Run gates in order; short-circuit on first rejection. Ledger every reject."""
    for gate in gates:
        rejection = gate.check(ctx)
        if rejection is not None:
            if wiki_root is not None:
                _ledger_reject(wiki_root, ctx, rejection)
            return rejection
    return None


def _ledger_reject(wiki_root: Path, ctx: dict[str, Any], rejection: GateRejection) -> None:
    ledger_path = wiki_root / LEDGER_REL
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sender_bot_id": ctx.get("sender_bot_id", ""),
        "recipient_bot_id": ctx.get("recipient_bot_id", ""),
        "chat_id": ctx.get("chat_id", ""),
        "body_head": str(ctx.get("body", ""))[:80],
        "rejection": rejection.as_dict(),
    }
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
