"""Atomic STATUS.md dashboard renderer (Ship 2 wave 3a).

Reads the substrate state — queue shadow, lane locks, parity manifest, git
working tree, model failover ledger — and renders a single human-readable
``STATUS.md`` at the wiki root. The write is atomic (temp + rename) so
concurrent readers always see a consistent snapshot.

Companion to ``tools/task_queue.py`` (TASK_QUEUE.md view) and ``tools/lane_lock.py``
(advisory locks). This module is *read-only* with respect to substrate; it
never mutates queue rows or lock tokens.

Never crashes on missing data — placeholders fill in for unavailable inputs
(``(empty)``, ``(idle)``, ``missing``, ``No failover event recorded yet.``).

CLI::

    python3 tools/status_render.py                 # write STATUS.md
    python3 tools/status_render.py --stdout        # print to stdout
    python3 tools/status_render.py --wiki <path>   # override wiki root
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Module imports: tools/task_queue.py collides with stdlib `queue`, so load by path.
# tools.lane_lock and tools.model_failover_state use the dual-import pattern.
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
_QUEUE_PATH = _THIS_DIR / "task_queue.py"
_spec = importlib.util.spec_from_file_location("tools_queue", _QUEUE_PATH)
assert _spec is not None and _spec.loader is not None
_queue_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("tools_queue", _queue_mod)
_spec.loader.exec_module(_queue_mod)

try:  # pragma: no cover — package vs script-mode dual import
    from tools import lane_lock as _lane_lock_mod
except ImportError:
    if str(_THIS_DIR) not in sys.path:
        sys.path.insert(0, str(_THIS_DIR))
    import lane_lock as _lane_lock_mod  # type: ignore[no-redef]

try:  # pragma: no cover — package vs script-mode dual import
    from tools import model_failover_state as _mfs_mod
except ImportError:
    if str(_THIS_DIR) not in sys.path:
        sys.path.insert(0, str(_THIS_DIR))
    import model_failover_state as _mfs_mod  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALMATY = dt.timezone(dt.timedelta(hours=5))
STATUS_REL = Path("STATUS.md")
PARITY_REL = Path("pages/systems/parity-latest.json")
KNOWN_LANES = ("claude", "codex", "grok", "opus")


# ---------------------------------------------------------------------------
# Path / time helpers
# ---------------------------------------------------------------------------

def default_wiki() -> Path:
    env = os.environ.get("NOUS_WIKI")
    if env:
        return Path(env)
    here = Path(__file__).resolve().parents[1]
    if (here / "pages").exists():
        return here
    if (here / "wiki" / "pages").exists():
        return here / "wiki"
    return here


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def _resolve_wiki(wiki: Path | None) -> Path:
    return wiki if wiki is not None else default_wiki()


def _parse_iso(s: str) -> dt.datetime | None:
    try:
        d = dt.datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=ALMATY)
    return d


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_age(td_seconds: float | None) -> str:
    """Format seconds-since as ``Ns ago`` / ``Nm ago`` / ``Nh ago``.

    Returns ``"(idle)"`` when *td_seconds* is None.
    """
    if td_seconds is None:
        return "(idle)"
    if td_seconds < 0:
        td_seconds = 0.0
    s = int(td_seconds)
    if s < 60:
        return f"{s}s ago"
    m = s // 60
    if m < 60:
        return f"{m}m ago"
    h = m // 60
    return f"{h}h ago"


def _md_escape(value: str) -> str:
    """Escape a value for safe inclusion in a markdown table cell."""
    return value.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


# ---------------------------------------------------------------------------
# State readers — each one is fail-soft.
# ---------------------------------------------------------------------------

def _read_queue_state(wiki: Path) -> dict[str, dict]:
    """Returns {lane: {top: <task or None>, count_active: int}} for KNOWN_LANES.

    ``top`` is the oldest non-done current task on that lane (claimed first if
    any are claimed, else pending/released). ``count_active`` is the number of
    non-done tasks currently owned by that lane.
    """
    out: dict[str, dict] = {
        lane: {"top": None, "count_active": 0} for lane in KNOWN_LANES
    }
    try:
        rows = _queue_mod._load_shadow(wiki)
        current = _queue_mod._latest_per_task(rows)
    except Exception as exc:  # noqa: BLE001 — fail-soft
        print(f"status_render: queue read failed: {exc}", file=sys.stderr)
        return out

    by_lane: dict[str, list[dict]] = {lane: [] for lane in KNOWN_LANES}
    for info in current.values():
        lane = info.get("lane")
        if lane not in by_lane:
            continue
        if info.get("status") == "done":
            continue
        by_lane[lane].append(info)

    for lane, items in by_lane.items():
        out[lane]["count_active"] = len(items)
        if not items:
            continue
        # Prefer claimed tasks; among ties, oldest by created.
        claimed = [i for i in items if i.get("status") == "claimed"]
        pool = claimed if claimed else items
        pool.sort(key=lambda r: r.get("created") or "")
        out[lane]["top"] = dict(pool[0])
    return out


def _read_lane_locks(
    wiki: Path,
    *,
    now: dt.datetime,
) -> dict[str, list[dict]]:
    """Returns {lane: [token_dict, ...]} of active tokens grouped by lane."""
    grouped: dict[str, list[dict]] = {lane: [] for lane in KNOWN_LANES}
    try:
        entries = _lane_lock_mod.list_active(wiki=wiki, now=now)
    except Exception as exc:  # noqa: BLE001 — fail-soft
        print(f"status_render: lane_lock read failed: {exc}", file=sys.stderr)
        return grouped
    for entry in entries:
        lane = entry.get("lane")
        if lane in grouped:
            grouped[lane].append(entry)
    return grouped


def _read_parity(wiki: Path) -> dict[str, str]:
    """Read parity-latest.json. Returns empty dict if missing/malformed."""
    path = wiki / PARITY_REL
    try:
        raw = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    manifest = str(data.get("manifest_sha256") or "")
    return {
        "manifest_sha256_short": manifest[:12] if manifest else "",
        "manifest_sha256_full": manifest,
        "algo": str(data.get("algo") or ""),
        "host": str(data.get("host") or ""),
        "last_computed_iso": str(data.get("ts") or ""),
    }


def _git_status_counts(wiki: Path) -> dict[str, Any]:
    """Returns {dirty: int, untracked: int, latest_commit: str}.

    Wrapped in try/except so a non-git tmp_path (or missing git) yields a
    safe placeholder rather than raising.
    """
    out: dict[str, Any] = {"dirty": 0, "untracked": 0, "latest_commit": "n/a"}
    try:
        proc = subprocess.run(
            ["git", "-C", str(wiki), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return out
    if proc.returncode != 0:
        return out
    dirty = 0
    untracked = 0
    for line in proc.stdout.splitlines():
        if not line:
            continue
        if line.startswith("??"):
            untracked += 1
        else:
            dirty += 1
    out["dirty"] = dirty
    out["untracked"] = untracked

    try:
        proc2 = subprocess.run(
            ["git", "-C", str(wiki), "log", "-1", "--pretty=%h %s"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc2.returncode == 0 and proc2.stdout.strip():
            out["latest_commit"] = proc2.stdout.strip().splitlines()[0]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return out


def _read_latest_failover(wiki: Path) -> dict | None:
    """Returns the latest_state dict from model_failover_state, or None."""
    try:
        return _mfs_mod.latest_state(wiki)
    except Exception as exc:  # noqa: BLE001 — fail-soft
        print(f"status_render: failover read failed: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _heartbeat_age_for_lane(
    tokens: list[dict],
    now: dt.datetime,
) -> float | None:
    """Return the smallest age (seconds) among the lane's tokens, or None.

    Smallest age = most recently acquired = freshest heartbeat. We use
    ``acquired_at`` because lane_lock's external API exposes that field but
    not the most recent heartbeat refresh — heartbeats update ``expires_at``
    internally, and acquired_at remains a useful "lane is alive" proxy.
    """
    best: float | None = None
    for tok in tokens:
        ts = _parse_iso(str(tok.get("acquired_at") or ""))
        if ts is None:
            continue
        age = (now - ts).total_seconds()
        if best is None or age < best:
            best = age
    return best


def _scope_str(scope_paths: Any) -> str:
    if isinstance(scope_paths, list) and scope_paths:
        return ",".join(str(p) for p in scope_paths)
    return "—"


def render(
    *,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> str:
    """Pure function: read state, return the rendered markdown string."""
    wiki = _resolve_wiki(wiki)
    moment = now if now is not None else now_kzt()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ALMATY)

    queue_state = _read_queue_state(wiki)
    locks_by_lane = _read_lane_locks(wiki, now=moment)
    parity = _read_parity(wiki)
    git_state = _git_status_counts(wiki)
    failover = _read_latest_failover(wiki)

    lines: list[str] = []
    lines.append("---")
    lines.append("type: system")
    lines.append("id: status-dashboard")
    lines.append("auto_rendered_by: tools/status_render.py")
    lines.append(f"last_render: {moment.isoformat()}")
    lines.append("---")
    lines.append("")
    lines.append("# STATUS — Nous AGaaS")
    lines.append("")
    lines.append(
        "> Auto-rendered every 30s by `com.nous.status-daemon` (Ship 2 wave 4)."
    )
    lines.append(
        "> Also re-rendered synchronously on every `queue.py` mutation."
    )
    lines.append("")

    # --- Active lanes ------------------------------------------------------
    lines.append("## Active lanes")
    lines.append("")
    lines.append("| lane | tokens | heartbeat | scope |")
    lines.append("|---|---|---|---|")
    for lane in KNOWN_LANES:
        tokens = locks_by_lane.get(lane, [])
        n_tokens = len(tokens)
        if n_tokens == 0:
            heartbeat = "(idle)"
            scope_str = "—"
        else:
            heartbeat = _format_age(_heartbeat_age_for_lane(tokens, moment))
            # Concatenate scope_paths across all tokens on this lane.
            all_scope: list[str] = []
            for tok in tokens:
                sp = tok.get("scope_paths") or []
                if isinstance(sp, list):
                    all_scope.extend(str(p) for p in sp)
            scope_str = _scope_str(all_scope) if all_scope else "—"
        cells = [
            _md_escape(lane),
            _md_escape(str(n_tokens)),
            _md_escape(heartbeat),
            _md_escape(scope_str),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # --- Top of queue per lane --------------------------------------------
    lines.append("## Top of queue per lane")
    lines.append("")
    lines.append("| lane | next | status | scope |")
    lines.append("|---|---|---|---|")
    for lane in KNOWN_LANES:
        info = queue_state.get(lane, {})
        top = info.get("top")
        if top is None:
            next_cell = "(empty)"
            status_cell = "—"
            scope_cell = "—"
        else:
            tid = str(top.get("id") or "")
            title = str(top.get("title") or "")
            next_cell = f"{tid} — {title}" if title else tid
            status_val = str(top.get("status") or "")
            owner = top.get("owner")
            if status_val == "claimed" and owner:
                status_cell = f"claimed by {owner}"
            else:
                status_cell = status_val or "—"
            scope_cell = _scope_str(top.get("scope_paths"))
        cells = [
            _md_escape(lane),
            _md_escape(next_cell),
            _md_escape(status_cell),
            _md_escape(scope_cell),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    # --- Parity ------------------------------------------------------------
    lines.append("## Parity")
    lines.append("")
    if not parity:
        lines.append("- manifest_sha256: missing")
        lines.append("- algo: missing")
        lines.append("- host: missing")
        lines.append("- last computed: missing")
    else:
        short = parity.get("manifest_sha256_short") or "missing"
        algo = parity.get("algo") or "missing"
        host = parity.get("host") or "missing"
        last_ts = parity.get("last_computed_iso") or "missing"
        lines.append(f"- manifest_sha256: `{short}...`")
        lines.append(f"- algo: {algo}")
        lines.append(f"- host: {host}")
        lines.append(f"- last computed: {last_ts}")
    lines.append("")

    # --- Working tree ------------------------------------------------------
    lines.append("## Working tree")
    lines.append("")
    lines.append(f"- dirty files: {git_state.get('dirty', 0)}")
    lines.append(f"- untracked: {git_state.get('untracked', 0)}")
    lines.append(f"- latest commit: `{git_state.get('latest_commit', 'n/a')}`")
    lines.append("")

    # --- Latest failover event --------------------------------------------
    lines.append("## Latest failover/resume event")
    lines.append("")
    if failover is None:
        lines.append("No failover event recorded yet.")
    else:
        event_id = str(failover.get("event_id") or "")
        status_val = str(failover.get("status") or "")
        command = str(failover.get("command") or "")
        via = str(failover.get("via") or "")
        model = str(failover.get("model") or "")
        ts = str(failover.get("ts") or "")
        lines.append(f"- event_id: `{event_id}`")
        lines.append(f"- status: `{status_val}`")
        if via:
            lines.append(f"- original_route: `{command}` via {via}")
        else:
            lines.append(f"- original_route: `{command}`")
        lines.append(f"- model: {model}")
        lines.append(f"- ts: {ts}")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_and_write(
    *,
    wiki: Path | None = None,
    now: dt.datetime | None = None,
) -> Path:
    """Render and write STATUS.md atomically (temp + rename). Returns the path."""
    wiki = _resolve_wiki(wiki)
    payload = render(wiki=wiki, now=now)
    path = wiki / STATUS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.rename(tmp, path)
    finally:
        # Defensive cleanup if rename did not happen.
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render STATUS.md from queue + lane locks + parity",
    )
    parser.add_argument("--wiki", type=Path, default=None)
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print to stdout instead of writing STATUS.md",
    )
    args = parser.parse_args()
    wiki = args.wiki or default_wiki()
    if args.stdout:
        sys.stdout.write(render(wiki=wiki))
    else:
        path = render_and_write(wiki=wiki)
        try:
            rel = path.relative_to(wiki)
        except ValueError:
            rel = path
        print(f"wrote {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
