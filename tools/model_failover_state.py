#!/usr/bin/env python3
"""Durable model failover state for Telegram-spawned model lanes."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from tools import failover_schema  # when imported as a package
except ImportError:  # pragma: no cover - exercised when invoked from tools/ dir directly
    import failover_schema  # type: ignore[no-redef]

try:
    from tools import provider_probe  # when imported as a package
except ImportError:  # pragma: no cover - exercised when invoked from tools/ dir directly
    import provider_probe  # type: ignore[no-redef]

ALMATY = dt.timezone(dt.timedelta(hours=5))
LEDGER_REL = Path("pages/systems/model-failover-ledger.jsonl")
LATEST_REL = Path("pages/systems/MODEL-FAILOVER-LATEST.md")
PACKET_REL = Path("pages/systems/AGENT-CONTINUITY-PACKET.md")
LOCK_REL = Path("logs/model-failover-state.lock")
WAL_REL = Path("logs/model-failover.wal")


def default_wiki() -> Path:
    env = os.environ.get("NOUS_WIKI")
    if env:
        return Path(env)
    tool_root = Path(__file__).resolve().parents[1]
    if (tool_root / "pages").exists():
        return tool_root
    if (tool_root / "wiki" / "pages").exists():
        return tool_root / "wiki"
    return tool_root


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def redact(text: str) -> str:
    redacted = text or ""
    redacted = re.sub(
        r"(?i)\b(password|pass|pwd|пароль|token|secret|api[_-]?key)\s*[:=]\s*([^\s,;]+)",
        r"\1: [REDACTED]",
        redacted,
    )
    redacted = re.sub(
        r"(?im)^(\s*(?:test|prod|production|тест|прод)\s*:\s*)([^\s,;]+)",
        r"\1[REDACTED]",
        redacted,
    )
    return redacted


def latest_handoff(wiki: Path) -> str:
    progress = wiki / "pages" / "progress"
    handoffs = sorted(progress.glob("HANDOFF-AUTO-*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    return handoffs[0].relative_to(wiki).as_posix() if handoffs else ""


def git_head(wiki: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(wiki), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode == 0:
        return proc.stdout.strip()
    return ""


def event_id_for(*, command: str, msg_id: int | str, query: str, ts: str) -> str:
    raw = f"{command}|{msg_id}|{query}|{ts}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:10]
    clean_command = command.strip("/").replace("/", "-") or "model"
    return f"tg_{msg_id}_{clean_command}_{digest}"


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _load_events(wiki: Path) -> list[dict[str, Any]]:
    """Read the failover ledger; quarantine malformed rows side-effectfully.

    Returns dicts (not typed rows) for backward compatibility with existing callers.
    Malformed rows are appended to model-failover-ledger.broken.jsonl, the bad lines
    are dropped from the returned list, and the original ledger file is NOT rewritten.
    """
    path = wiki / LEDGER_REL
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    broken_buffer: list[failover_schema.BrokenRow] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        row, broken = failover_schema.parse_row(line)
        if broken is not None:
            broken_buffer.append(broken)
            continue
        if row is None:
            continue
        events.append(row.as_dict())
    if broken_buffer:
        failover_schema.quarantine_broken(wiki, broken_buffer)
    return events


ORPHAN_TIMEOUT_SEC = 15 * 60  # 15 minutes


def _parse_ts(ts_str: str, event_id: str) -> dt.datetime | None:
    """Best-effort parse of an ISO 8601 ts. Returns None on failure and logs to stderr.

    Existing rows store ts as ISO 8601 with +05:00 tz (Almaty). Python 3.11+
    datetime.fromisoformat handles the tz suffix directly.
    """
    try:
        return dt.datetime.fromisoformat(ts_str)
    except (TypeError, ValueError):
        print(
            f"latest_state: unparseable ts in event {event_id}: {ts_str}",
            file=sys.stderr,
        )
        return None


def _latest_finished_for(events: list[dict[str, Any]], event_id: str) -> dict[str, Any] | None:
    """Return the finished row with the largest ts for event_id, or None."""
    finishes = [
        event for event in events
        if event.get("event_id") == event_id and event.get("phase") == "finished"
    ]
    if not finishes:
        return None
    # Sort by ts string — ISO 8601 with fixed tz sorts lexicographically.
    finishes.sort(key=lambda row: row.get("ts", ""))
    return finishes[-1]


def _synthetic_finish(event_id: str, now: dt.datetime) -> dict[str, Any]:
    """Build the in-memory synthetic finish dict for an orphaned started row.

    NOT written to the ledger here — Step-5 sweeper will materialize a real row.
    """
    return {
        "event_id": event_id,
        "phase": "finished",
        "status": "abandoned",
        "ts": now.isoformat(),
        "response_head": "",
        "receipt": "",
        "git_head": "",  # unknown at synthesis time
        "abandonment_reason": "orphan_timeout",
        "synthetic": True,
    }


def latest_state(wiki: Path | None = None, *, now: dt.datetime | None = None) -> dict[str, Any] | None:
    """Return the most recent event with finish/abandonment pairing applied.

    Pairs each started row with its matching finished row by event_id.
    For any started row with no matching finished AND (now - started.ts) > ORPHAN_TIMEOUT_SEC,
    returns a synthetic abandoned view: status='abandoned', finish={phase:'finished',
    status:'abandoned', abandonment_reason:'orphan_timeout', ts:<now ISO>}.

    The "latest" event is the one with the largest ts among started rows.
    Returns None if no started events exist.

    The `now` parameter is for tests; production callers omit it (defaults to now_kzt()).
    """
    wiki = wiki or default_wiki()
    events = _load_events(wiki)
    starts = [event for event in events if event.get("phase") == "started"]
    if not starts:
        return None
    # Latest started by ts (lex-sort works for ISO 8601 with fixed tz).
    starts.sort(key=lambda row: row.get("ts", ""))
    start = starts[-1].copy()
    event_id = start.get("event_id", "")

    finished = _latest_finished_for(events, event_id)
    if finished is not None:
        start["finish"] = finished
        start["status"] = finished.get("status", start.get("status"))
        return start

    # No matching finished — check orphan timeout.
    now_dt = now or now_kzt()
    started_ts = _parse_ts(start.get("ts", ""), event_id)
    if started_ts is None:
        # Unparseable ts → do NOT mark abandoned; keep current status.
        return start

    age_sec = (now_dt - started_ts).total_seconds()
    if age_sec > ORPHAN_TIMEOUT_SEC:
        start["finish"] = _synthetic_finish(event_id, now_dt)
        start["status"] = "abandoned"
    # else: within timeout, leave as in-flight (status='running').
    return start


def find_orphans(wiki: Path, *, now: dt.datetime | None = None) -> list[dict[str, Any]]:
    """Return all started rows that are orphans (no matching finished AND age > timeout).

    Used by the sweeper (Step 5) to materialize synthetic abandonment rows to the ledger.
    Returns list of started-row dicts (NOT including the synthetic finish).
    """
    events = _load_events(wiki)
    starts = [event for event in events if event.get("phase") == "started"]
    if not starts:
        return []
    now_dt = now or now_kzt()
    orphans: list[dict[str, Any]] = []
    for start in starts:
        event_id = start.get("event_id", "")
        if _latest_finished_for(events, event_id) is not None:
            continue
        started_ts = _parse_ts(start.get("ts", ""), event_id)
        if started_ts is None:
            # Unparseable ts → skip orphan check.
            continue
        if (now_dt - started_ts).total_seconds() > ORPHAN_TIMEOUT_SEC:
            orphans.append(start)
    return orphans


def start_event(
    *,
    command: str,
    msg_id: int,
    chat_id: int,
    query: str,
    model: str,
    via: str,
    wiki: Path | None = None,
    commit: bool | None = None,
) -> str:
    wiki = wiki or default_wiki()
    ts = now_kzt().isoformat()
    event_id = event_id_for(command=command, msg_id=msg_id, query=query, ts=ts)
    row = {
        "event_id": event_id,
        "phase": "started",
        "status": "running",
        "ts": ts,
        "command": command,
        "msg_id": msg_id,
        "chat_id": chat_id,
        "query": redact(query),
        "model": model,
        "via": via,
        "continuity_packet": PACKET_REL.as_posix(),
        "latest_handoff": latest_handoff(wiki),
        "git_head": git_head(wiki),
    }
    _mutate_state(wiki, row, commit=commit)
    return event_id


def finish_event(
    event_id: str | None,
    *,
    status: str,
    response: str = "",
    receipt: str | None = None,
    wiki: Path | None = None,
    commit: bool | None = None,
) -> None:
    if not event_id:
        return
    wiki = wiki or default_wiki()
    row = {
        "event_id": event_id,
        "phase": "finished",
        "status": status,
        "ts": now_kzt().isoformat(),
        "response_head": redact(response)[:700],
        "receipt": receipt or "",
        "git_head": git_head(wiki),
    }
    _mutate_state(wiki, row, commit=commit)
    # Step 8b + 9: fire-and-forget side-channels for non-ok terminal statuses.
    # Re-read latest_state so both helpers see the paired (started+finished) row.
    full_state = latest_state(wiki)
    if full_state and full_state.get("event_id") == event_id:
        _capture_openbrain_event(full_state, wiki)
        _append_mistake_to_skill(full_state, wiki)


def _capture_openbrain_event(state: dict[str, Any], wiki: Path | None = None) -> None:
    """Fire-and-forget OpenBrain capture for a finished failover event.

    Filter: only captures non-ok terminal statuses (error, timeout, abandoned).
    Never blocks the caller; failures log to logs/openbrain-capture.log.
    Uses subprocess.Popen with start_new_session=True to detach.
    """
    finish = state.get("finish") or {}
    status = finish.get("status") or state.get("status")
    if status not in ("error", "timeout", "abandoned"):
        return

    title = f"Resume incident: {state.get('command', '?')} -> {status}"
    body = build_resume_prompt_from_state(state, "any")
    lane = str(state.get("command", "")).lstrip("/")
    tags = [
        "model-failover",
        "resume",
        f"lane:{lane}",
        f"event:{state.get('event_id', '')}",
    ]

    payload = json.dumps({"type": "incident", "title": title, "body": body, "tags": tags})

    try:
        wiki_root = wiki or default_wiki()
        log_path = wiki_root / "logs" / "openbrain-capture.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"[{now_kzt().isoformat()}] queue: {title}\n")
            subprocess.Popen(
                ["mcp", "call", "claude.ai_Open_Brain", "capture_thought", payload],
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
    except Exception as exc:  # noqa: BLE001 — fire-and-forget; never block parent
        print(f"_capture_openbrain_event: {exc}", file=sys.stderr)


def _append_mistake_to_skill(state: dict[str, Any], wiki: Path) -> None:
    """Append one line to pages/skills/mistake-to-skill/ledger.jsonl for non-ok terminals.

    Only fires for status in {error, timeout, abandoned}. Idempotent: if a row with the same
    event_id already exists in the ledger, do not duplicate.
    """
    finish = state.get("finish") or {}
    status = finish.get("status") or state.get("status")
    if status not in ("error", "timeout", "abandoned"):
        return

    ledger = wiki / "pages" / "skills" / "mistake-to-skill" / "ledger.jsonl"

    event_id = state.get("event_id", "")
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                existing = json.loads(line)
            except json.JSONDecodeError:
                continue
            if existing.get("event_id") == event_id:
                return  # already logged

    parity_hash = ""
    parity_file = wiki / "pages" / "systems" / "parity-latest.json"
    if parity_file.exists():
        try:
            parity_hash = str(json.loads(parity_file.read_text(encoding="utf-8"))["manifest_sha256"])[:16]
        except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError):
            parity_hash = ""

    row = {
        "ts": now_kzt().isoformat(),
        "event_id": event_id,
        "original_model": state.get("model", ""),
        "original_command": state.get("command", ""),
        "failure_reason": finish.get("abandonment_reason") or finish.get("status") or "unknown",
        "parity_hash": parity_hash,
    }

    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _next_mutation_seq(wiki: Path) -> int:
    """Return the next monotonic mutation_seq by reading max from existing WAL + 1.

    Returns 1 if WAL doesn't exist. Must be called inside the lock (caller's
    responsibility) to be race-free against concurrent processes.
    """
    path = wiki / WAL_REL
    if not path.exists():
        return 1
    max_seq = 0
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            seq = row.get("mutation_seq")
            if isinstance(seq, int) and seq > max_seq:
                max_seq = seq
    except OSError:
        return 1
    return max_seq + 1


def _append_wal(wiki: Path, mutation_seq: int, event_id: str, pushed: bool) -> None:
    """Append a WAL row {mutation_seq, event_id, ts, pushed} to logs/model-failover.wal.

    Creates parent dir if missing. Calls fsync after write so the row survives a
    process crash between WAL append and the next step in the mutate flow.
    """
    path = wiki / WAL_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "mutation_seq": int(mutation_seq),
        "event_id": event_id,
        "ts": now_kzt().isoformat(),
        "pushed": bool(pushed),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _recompute_parity(wiki: Path) -> None:
    """Recompute parity manifest hash; write to pages/systems/parity-latest.json.

    Step-7b wires this to parity_check.compute_and_write. Fail-soft: any exception
    is logged to stderr but does not abort the mutation.
    """
    try:
        try:
            from tools import parity_check
        except ImportError:
            import parity_check
        parity_check.compute_and_write(wiki)
    except Exception as exc:
        print(f"_recompute_parity: {exc}", file=sys.stderr)


def _git_add_commit_local(wiki: Path) -> int:
    """Run git add + git commit (NO push). Returns returncode (0 = success).

    Adds LEDGER_REL and LATEST_REL only. Uses --allow-empty so a no-op commit
    (e.g. when LATEST_REL is byte-identical to HEAD) doesn't fail the flow.
    Timeout 15s for add, 15s for commit.
    """
    rels = [LEDGER_REL.as_posix(), LATEST_REL.as_posix()]
    try:
        subprocess.run(
            ["git", "-C", str(wiki), "add", *rels],
            capture_output=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"model-failover: git add failed: {exc}", file=sys.stderr)
        return 1
    try:
        proc = subprocess.run(
            [
                "git", "-C", str(wiki),
                "commit", "--allow-empty",
                "-m", "model-failover: capture latest lane state",
                "--", *rels,
            ],
            capture_output=True,
            timeout=15,
        )
        return proc.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"model-failover: git commit failed: {exc}", file=sys.stderr)
        return 1


def _git_push_background(wiki: Path) -> int:
    """Run git push origin main best-effort. Returns returncode.

    Captures output. Timeout 45s. Does NOT raise on failure — Step-5 sweeper
    replays mutations whose latest WAL row has pushed=false AND age > 60s.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(wiki), "push", "origin", "main"],
            capture_output=True,
            timeout=45,
        )
        return proc.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"model-failover: git push failed: {exc}", file=sys.stderr)
        return 1


def _mutate_state(wiki: Path, row: dict[str, Any], *, commit: bool | None = None) -> None:
    """Durable single-mutation flow with write-ahead log + late push.

    Ship-1 Step-3 ordering (god-tier failover plan §4.3):
      Inside fcntl.LOCK_EX:
        1. mutation_seq := _next_mutation_seq(wiki)
        2. Append WAL row {pushed: false}, fsync.
        3. Append ledger row, fsync.
        4. render_latest(wiki).
        5. _recompute_parity(wiki) (Step-7 stub).
        6. git add + git commit (NO network). Captured. Timeout 15s each.
      Release lock.
      Outside lock:
        7. git push origin main (best-effort, timeout 45s).
        8. On returncode == 0: append second WAL row {pushed: true} with same
           mutation_seq, fresh ts, fsync.
        9. On push failure: print to stderr; the Step-5 sweeper retries by
           reading WAL and finding mutation_seqs whose latest row is
           pushed=false AND age > 60s.

    `NOUS_FAILOVER_STATE_COMMIT=0` (or `commit=False`) suppresses ALL git
    activity so tests don't have to mock subprocess.
    """
    do_commit = commit if commit is not None else os.environ.get("NOUS_FAILOVER_STATE_COMMIT", "1") != "0"
    event_id = str(row.get("event_id", ""))

    lock_path = wiki / LOCK_REL
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    mutation_seq = 0
    with lock_path.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            mutation_seq = _next_mutation_seq(wiki)
            _append_wal(wiki, mutation_seq, event_id, pushed=False)
            _append_jsonl(wiki / LEDGER_REL, row)
            # fsync the ledger too — WAL is ahead of ledger only if both rows
            # are durable. Without this, a crash here could leave WAL with
            # pushed:false but no ledger row — sweeper would retry a no-op.
            try:
                ledger_path = wiki / LEDGER_REL
                fd = os.open(str(ledger_path), os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except OSError:
                pass
            render_latest(wiki)
            _recompute_parity(wiki)
            if do_commit:
                _git_add_commit_local(wiki)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    if do_commit:
        push_rc = _git_push_background(wiki)
        if push_rc == 0:
            _append_wal(wiki, mutation_seq, event_id, pushed=True)
        else:
            print(
                f"model-failover: push deferred (rc={push_rc}, mutation_seq={mutation_seq}, "
                f"event_id={event_id}) — sweeper will retry",
                file=sys.stderr,
            )


def render_latest(wiki: Path | None = None) -> Path:
    wiki = wiki or default_wiki()
    state = latest_state(wiki)
    out = wiki / LATEST_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(format_latest_markdown(state), encoding="utf-8")
    return out


def format_latest_markdown(state: dict[str, Any] | None) -> str:
    if not state:
        return "# Model Failover Latest\n\nNo model failover event has been recorded yet.\n"
    query = state.get("query", "")
    event_id = state.get("event_id", "")
    status = state.get("status", "running")
    command = state.get("command", "")
    return f"""---
title: Model Failover Latest
type: system
status: {status}
event_id: {event_id}
---

# Model Failover Latest

## Current Event

- event_id: `{event_id}`
- status: `{status}`
- original_route: `{command}`
- model: `{state.get("model", "")}`
- via: `{state.get("via", "")}`
- telegram_msg_id: `{state.get("msg_id", "")}`
- started_at: `{state.get("ts", "")}`
- latest_handoff: `{state.get("latest_handoff", "")}`
- continuity_packet: `{state.get("continuity_packet", PACKET_REL.as_posix())}`

## Original Task

```text
{query}
```

## Instant Resume Commands

```text
/resume gpt
/resume grok
/resume claude
/resume opus
```

## Manual Resume Prompt

```text
{build_resume_prompt_from_state(state, "any")}
```
"""


def build_resume_prompt(target: str = "any", wiki: Path | None = None) -> str:
    state = latest_state(wiki)
    if not state:
        return "No model failover event exists yet. Ask Madi for the task once, then it will be captured."
    return build_resume_prompt_from_state(state, target)


_TARGET_TO_REPLACEMENT_MODEL = {
    "gpt": "gpt-5.5",
    "claude": "claude-sonnet-4-6",
    "grok": "grok-2-1212",
    "opus": "claude-opus-4-7",
    "any": "auto-route",
}

_TARGET_TO_PROVIDER = {
    "gpt": "openai",
    "claude": "anthropic",
    "grok": "xai",
    "opus": "anthropic",
    "any": "openai",
}


def _file_sha256_short(path: Path) -> str:
    """Return the first 12 hex chars of sha256(path bytes), or 'missing' on any failure.

    Used to stamp packet/handoff/parity pointer hashes into the resume prompt so a
    receiving agent can detect drift without re-reading the full file.
    """
    try:
        if not path.exists():
            return "missing"
        hasher = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(65536)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()[:12]
    except OSError:
        return "missing"


def build_resume_prompt_from_state(state: dict[str, Any], target: str) -> str:
    """Build the RESUME-v2 prompt template (plan §4.6).

    Fail-soft: provider probe failures degrade to ok=False / latency=-1 / reason=probe_error.
    Missing pointer files degrade to sha256=missing. Never raises.
    """
    finish = state.get("finish") or {}
    response_head = finish.get("response_head", "") or ""
    receipt = finish.get("receipt", "") or ""

    event_id = state.get("event_id", "")
    command = state.get("command", "")
    via = state.get("via", "")
    original_model = state.get("model", "")
    original_status = state.get("status", "unknown")
    ts_started = state.get("ts", "")
    ts_finished = finish.get("ts", "n/a") if finish else "n/a"
    query = state.get("query", "")

    replacement_model = _TARGET_TO_REPLACEMENT_MODEL.get(target, "auto-route")

    failure_reason = (
        finish.get("abandonment_reason")
        or finish.get("status")
        or "unknown"
    )

    tokens_remaining = "unknown"
    tokens_budget = "unknown"

    packet_rel = state.get("continuity_packet") or PACKET_REL.as_posix()
    latest_handoff_path = state.get("latest_handoff") or ""

    # Resolve wiki for path-based hash lookups. Use default_wiki() as best-effort —
    # tests pass wiki via state-only path; missing files degrade gracefully.
    wiki = default_wiki()
    packet_hash = _file_sha256_short(wiki / packet_rel) if packet_rel else "missing"
    handoff_hash = (
        _file_sha256_short(wiki / latest_handoff_path) if latest_handoff_path else "missing"
    )

    parity_hash = "missing"
    parity_file = wiki / "pages" / "systems" / "parity-latest.json"
    if parity_file.exists():
        try:
            parity_data = json.loads(parity_file.read_text(encoding="utf-8"))
            parity_hash = str(parity_data.get("manifest_sha256", "missing"))[:12] or "missing"
        except (OSError, json.JSONDecodeError, ValueError):
            parity_hash = "missing"

    target_provider = _TARGET_TO_PROVIDER.get(target, "openai")
    try:
        probe_result = provider_probe.probe(target_provider, timeout_sec=0.2)
        probe_ok = bool(probe_result.ok)
        probe_latency = int(probe_result.latency_ms)
        probe_reason = str(probe_result.reason)
    except Exception as exc:  # noqa: BLE001 — fail-soft, never block resume on probe error
        probe_ok = False
        probe_latency = -1
        probe_reason = f"probe_error: {exc}"

    return (
        f"[RESUME-v2] event={event_id} target_lane={target} replacement_model={replacement_model}\n"
        "\n"
        "Original task (verbatim):\n"
        f"{query}\n"
        "\n"
        f"Original lane: {command} via {via}\n"
        f"Original model: {original_model}\n"
        f"Failure reason: {failure_reason}    # timeout|rate_limit|crash|token_cap|abandoned|provider_down\n"
        f"Original status: {original_status}\n"
        f"Started: {ts_started}   Finished/Abandoned: {ts_finished}\n"
        f"Token budget remaining (approx): {tokens_remaining} / {tokens_budget}\n"
        "\n"
        "Substrate pointers (read these FIRST, in order):\n"
        f"  1. {packet_rel}            packet_sha256={packet_hash}\n"
        f"  2. {latest_handoff_path}    handoff_sha256={handoff_hash}\n"
        "  3. pages/systems/MODEL-FAILOVER-LATEST.md\n"
        f"  4. pages/systems/parity-latest.json   manifest_sha256={parity_hash}\n"
        "\n"
        "Provider-probe result at resume time:\n"
        f"  {target_provider}: ok={probe_ok} latency_ms={probe_latency} reason={probe_reason}\n"
        "\n"
        "Previous response head (may be empty):\n"
        f"{response_head}\n"
        "\n"
        "Receipt of original attempt (may be empty):\n"
        f"{receipt}\n"
        "\n"
        "CONTRACT:\n"
        "- Do not ask Madi to restate context. Read substrate first.\n"
        "- If parity_hash mismatches `tools/parity_check.py --verify` on your host, STOP and report drift.\n"
        "- Name the original blocker in one sentence, then execute the smallest next proof step.\n"
        "- On success, write a 4-artifact DONE block (cmd / output / git HEAD+porcelain / counter-check).\n"
        "- On failure, codify the new failure mode into pages/skills/model-failover/SKILL.md before retry.\n"
    )


def format_resume_status(wiki: Path | None = None) -> str:
    state = latest_state(wiki)
    if not state:
        return "No failover event recorded yet."
    query = state.get("query", "")
    if len(query) > 700:
        query = query[:700].rstrip() + "..."
    return (
        "Latest failover event\n"
        f"event_id: {state.get('event_id')}\n"
        f"status: {state.get('status')}\n"
        f"route: {state.get('command')} -> {state.get('model')}\n"
        f"packet: {PACKET_REL.as_posix()}\n"
        f"latest: {LATEST_REL.as_posix()}\n\n"
        "Switch instantly with one of:\n"
        "/resume gpt\n"
        "/resume grok\n"
        "/resume claude\n"
        "/resume opus\n\n"
        f"Task:\n{query}"
    )


def commit_state(wiki: Path) -> None:
    """Deprecated since Ship 1 Step 3: _mutate_state now handles git inline.

    Kept as a no-op shim for any external callers (e.g., a future CLI).
    The new flow is:
      - inside the fcntl lock: append WAL row (pushed:false) + ledger + render
        + parity + git add/commit (no network);
      - outside the lock: git push, and on rc==0 append WAL row (pushed:true).
    """
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=default_wiki())
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--resume", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.resume:
        print(build_resume_prompt(args.resume, args.wiki))
    else:
        render_latest(args.wiki)
        print(format_resume_status(args.wiki))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
