#!/usr/bin/env python3
"""Daily evolution runner — 03:00 KZT self-update cycle (com.nous.daily-evolution).

Phases:
  1. snapshot()          — capture git heads, launchd statuses, version SHAs
  2. pull_substrate()    — git pull vps main; abort on real conflict
  3. detect_upgrades()   — return list[Upgrade], cap at 1 per cycle
  4. canary_each_upgrade() — STUB (T5 wires probes); iterate + rollback tag pre-apply
  5. proof_pack()        — STUB; call factory_no_drift_probe.sh if present
  6. digest()            — write pages/audits/DAILY-EVOLUTION-YYYY-MM-DD.md
  7. notify()            — STUB; per rules 7a/7b/7c only

CLI: python3 tools/daily_evolution_runner.py [--dry-run] [--fixture-mode]
                                              [--skip-pull] [--state-file PATH]

State at pages/systems/daily-evolution-state.json.
Idempotent — same calendar day can re-run safely.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

ALMATY = dt.timezone(dt.timedelta(hours=5))
DEFAULT_WIKI = Path(os.environ.get("NOUS_WIKI", "/Users/madia/Documents/Projects/Nous AGaaS/Nous"))
DEFAULT_STATE_REL = Path("pages/systems/daily-evolution-state.json")
DEFAULT_SNAPSHOT_REL = Path("pages/systems/daily-evolution-snapshot-pre.json")
DEFAULT_AUDIT_DIR = Path("pages/audits")
FACTORY_PROBE = Path("tools/factory_no_drift_probe.sh")

# Hosts
HOST_AIR = "air"  # ssh alias; Tailscale 100.122.219.22
HOST_VPS = "root@65.108.215.200"
HOST_MAC = "local"

# Max canary upgrades per cycle (Musk step 2: ship one thing well)
MAX_UPGRADES_PER_CYCLE = 1

# Back-off days on rollback
ROLLBACK_BACKOFF_DAYS = 7


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Upgrade:
    adapter_name: str
    current_version: str | None
    latest_version: str | None
    reason: str = ""


@dataclass
class PhaseResult:
    phase: str
    status: str  # "ok" | "skipped" | "aborted" | "error"
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def today_str() -> str:
    return now_kzt().strftime("%Y-%m-%d")


def log(msg: str) -> None:
    print(f"[daily-evolution] {now_kzt().isoformat()} {msg}", flush=True)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_cmd(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 60,
    capture: bool = True,
) -> dict[str, Any]:
    """Run a subprocess; return dict with ok/stdout/stderr/returncode."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=capture,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "timeout", "returncode": -1}
    except FileNotFoundError as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc), "returncode": -2}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "stdout": "", "stderr": str(exc), "returncode": -3}


def ssh_run(host: str, remote_cmd: str, timeout: int = 30) -> dict[str, Any]:
    return run_cmd(["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", host, remote_cmd], timeout=timeout)


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state(state_path: Path) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "last_run_at": None,
        "last_rollback_skips": [],
        "version_manifest": {},
    }
    stored = load_json(state_path)
    defaults.update(stored)
    return defaults


def write_state(state_path: Path, state: dict[str, Any]) -> None:
    state["last_run_at"] = now_kzt().isoformat()
    save_json(state_path, state)


def is_adapter_in_backoff(state: dict[str, Any], adapter_name: str) -> bool:
    today = today_str()
    for skip in state.get("last_rollback_skips", []):
        if skip.get("adapter") == adapter_name:
            until = skip.get("until_date", "")
            if until >= today:
                return True
    return False


def add_rollback_skip(state: dict[str, Any], adapter_name: str) -> None:
    until = (now_kzt() + dt.timedelta(days=ROLLBACK_BACKOFF_DAYS)).strftime("%Y-%m-%d")
    skips = [s for s in state.get("last_rollback_skips", []) if s.get("adapter") != adapter_name]
    skips.append({"adapter": adapter_name, "until_date": until})
    state["last_rollback_skips"] = skips


def already_ran_today(state: dict[str, Any]) -> bool:
    last = state.get("last_run_at")
    if not last:
        return False
    try:
        last_dt = dt.datetime.fromisoformat(last)
        return last_dt.strftime("%Y-%m-%d") == today_str()
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Phase 1 — snapshot
# ---------------------------------------------------------------------------

def _git_head_local(wiki: Path) -> str | None:
    r = run_cmd(["git", "rev-parse", "HEAD"], cwd=wiki, timeout=15)
    return r["stdout"].strip() if r["ok"] else None


def _git_head_remote(host: str, wiki_path: str) -> str | None:
    r = ssh_run(host, f"git -C {wiki_path} rev-parse HEAD", timeout=20)
    return r["stdout"].strip() if r["ok"] else None


def _launchd_exit_status(job: str) -> str:
    r = run_cmd(["launchctl", "list", job], timeout=10)
    if not r["ok"]:
        return "unknown"
    for line in r["stdout"].splitlines():
        line = line.strip()
        if '"LastExitStatus"' in line:
            return line.split("=")[-1].strip().rstrip(";")
    return "running" if r["ok"] else "not_loaded"


LAUNCHD_JOBS = [
    "com.nous.telegram-poll",
    "com.nous.litellm",
    "com.nous.goal-cycle",
    "com.nous.auto-checkpoint",
]


def snapshot(wiki: Path, fixture_mode: bool = False) -> PhaseResult:
    log("phase 1: snapshot")
    if fixture_mode:
        data = {
            "timestamp": now_kzt().isoformat(),
            "git_heads": {
                "mac": "fixture-mac-sha",
                "air": "fixture-air-sha",
                "vps": "fixture-vps-sha",
                "github": "fixture-gh-sha",
            },
            "launchd_exit_statuses": {job: "0" for job in LAUNCHD_JOBS},
            "service_version_shas": {
                "openclaw": "ghcr.io/openclaw/openclaw:2026.4.14",
                "codex_cli": "stub",
            },
            "fixture": True,
        }
    else:
        mac_head = _git_head_local(wiki)
        air_head = _git_head_remote(HOST_AIR, "~/nous-agaas/wiki")
        vps_head = _git_head_remote(HOST_VPS, "/root/nous-agaas/wiki")
        # GitHub: attempt via ssh or skip
        gh_head = _git_head_remote(HOST_AIR, "~/nous-agaas/wiki") or "unreachable"

        launchd_statuses = {job: _launchd_exit_status(job) for job in LAUNCHD_JOBS}

        # OpenClaw image SHA from Air docker
        oc_r = ssh_run(HOST_AIR, "docker inspect openclaw --format '{{.Image}}' 2>/dev/null || echo 'unavailable'", timeout=20)
        oc_sha = oc_r["stdout"].strip() if oc_r["ok"] else "unavailable"

        data = {
            "timestamp": now_kzt().isoformat(),
            "git_heads": {
                "mac": mac_head,
                "air": air_head,
                "vps": vps_head,
                "github": gh_head,
            },
            "launchd_exit_statuses": launchd_statuses,
            "service_version_shas": {
                "openclaw": oc_sha,
            },
            "fixture": False,
        }

    snap_path = wiki / DEFAULT_SNAPSHOT_REL
    save_json(snap_path, data)
    log(f"  snapshot written → {snap_path}")
    return PhaseResult(phase="snapshot", status="ok", detail=f"written {snap_path}", data=data)


# ---------------------------------------------------------------------------
# Phase 2 — pull_substrate
# ---------------------------------------------------------------------------

def pull_substrate(wiki: Path, dry_run: bool = False, skip_pull: bool = False, fixture_mode: bool = False) -> PhaseResult:
    log("phase 2: pull_substrate")
    if fixture_mode or skip_pull:
        return PhaseResult(phase="pull_substrate", status="skipped", detail="skip_pull or fixture_mode")

    if dry_run:
        return PhaseResult(phase="pull_substrate", status="skipped", detail="dry_run — would git pull")

    r = run_cmd(["git", "pull", "--ff-only", "origin", "main"], cwd=wiki, timeout=60)
    if r["ok"]:
        return PhaseResult(phase="pull_substrate", status="ok", detail=r["stdout"].strip()[:400])

    stdout = r["stdout"]
    stderr = r["stderr"]
    combined = (stdout + stderr).lower()

    # Auto-mergeable conflict indicators
    if "merge conflict" in combined or "conflict" in combined:
        # Write decision stub
        decision_path = wiki / DEFAULT_AUDIT_DIR / f"DAILY-EVOLUTION-NEEDS-DECISION-{today_str()}.md"
        decision_path.parent.mkdir(parents=True, exist_ok=True)
        body = (
            "---\n"
            "type: audit\n"
            f"id: DAILY-EVOLUTION-NEEDS-DECISION-{today_str()}\n"
            f'title: "Daily evolution substrate conflict — needs Madi decision"\n'
            f"date: {today_str()}\n"
            "status: needs_decision\n"
            "tags: [daily-evolution, conflict, needs-decision]\n"
            "---\n\n"
            f"# Daily Evolution — Merge Conflict {today_str()}\n\n"
            "Git pull encountered a real merge conflict during phase 2 substrate pull.\n\n"
            "## Conflict output\n\n"
            f"```\n{(stdout + stderr)[:2000]}\n```\n\n"
            "## Madi action required\n\n"
            f"Resolve manually:\n```bash\ncd {wiki}\ngit status\ngit mergetool  # or manual edit\ngit commit -m 'resolve daily-evolution conflict {today_str()}'\n```\n"
        )
        decision_path.write_text(body, encoding="utf-8")
        log(f"  CONFLICT → abort; wrote {decision_path}")
        return PhaseResult(
            phase="pull_substrate",
            status="aborted",
            detail=f"real merge conflict; decision stub at {decision_path}",
        )

    # Dirty-WT case (auto-sync churn from peer hosts is expected during
    # multi-host operation). Skip with clear detail; next cycle retries
    # once the WT is committed. This is NOT an error condition — it's a
    # transient race with auto-sync.
    dirty_wt_markers = (
        "uncommitted changes",
        "your local changes",
        "would be overwritten",
        "untracked working tree files",
        "unstaged changes",  # 2026-05-20 second live run surfaced exactly this phrasing
        "cannot pull with rebase",
        "index contains uncommitted",
    )
    if any(marker in combined for marker in dirty_wt_markers):
        log(f"  pull skipped — dirty WT (transient auto-sync race); retry next cycle")
        return PhaseResult(
            phase="pull_substrate",
            status="skipped",
            detail=f"dirty WT — auto-sync race, will retry next cycle: {(stdout + stderr)[:200]}",
        )

    # Other pull failure (network, auth) — soft skip
    return PhaseResult(
        phase="pull_substrate",
        status="error",
        detail=f"pull failed (non-conflict): rc={r['returncode']} {(stdout + stderr)[:300]}",
    )


# ---------------------------------------------------------------------------
# Phase 3 — detect_upgrades
# ---------------------------------------------------------------------------

_ADAPTER_INFRASTRUCTURE_MODULES: frozenset[str] = frozenset({"base"})


def _load_adapters(state: dict[str, Any], wiki: Path) -> list[Any]:
    """Import adapter modules from tools/daily_evolution_adapters/.

    Each adapter module MUST expose an `Adapter` alias pointing to its
    concrete adapter class. Strict convention — no auto-discovery
    fallback. Bug 2026-05-20 (first real run): the previous fallback
    loop scanned `dir(mod)` for any class with `probe_current_version`,
    which matched the `AdapterProtocol` (typing.Protocol) re-exported
    by infrastructure modules and crashed at `adapter_cls()` with
    "Protocols cannot be instantiated". The infrastructure-module skip
    list below keeps things explicit even if a future adapter forgets
    the alias.
    """
    adapters: list[Any] = []
    adapters_dir = wiki / "tools" / "daily_evolution_adapters"
    if not adapters_dir.exists():
        return adapters
    # Adapters import each other via `from .base import ...`, so we must load
    # them as a real package, not as detached file-loaded modules. Put the
    # tools/ dir on sys.path so `import daily_evolution_adapters.X` resolves.
    import importlib
    import sys
    tools_dir = str((wiki / "tools").resolve())
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    try:
        for mod_path in sorted(adapters_dir.glob("*.py")):
            if mod_path.stem.startswith("_"):
                continue
            if mod_path.stem in _ADAPTER_INFRASTRUCTURE_MODULES:
                continue
            qualified = f"daily_evolution_adapters.{mod_path.stem}"
            try:
                mod = importlib.import_module(qualified)
            except Exception as exc:  # noqa: BLE001
                log(f"  WARN: adapter {qualified} import failed: {exc}")
                continue
            adapter_cls = getattr(mod, "Adapter", None)
            if adapter_cls is None:
                log(f"  WARN: adapter module {mod_path.stem} missing required `Adapter` alias — skipping")
                continue
            adapters.append(adapter_cls())
    except Exception as exc:  # noqa: BLE001
        log(f"  WARN: adapter load error: {exc}")
    return adapters


def detect_upgrades(
    state: dict[str, Any],
    wiki: Path,
    fixture_mode: bool = False,
) -> tuple[PhaseResult, list[Upgrade]]:
    log("phase 3: detect_upgrades")
    upgrades: list[Upgrade] = []

    if fixture_mode:
        return PhaseResult(
            phase="detect_upgrades", status="ok", detail="fixture_mode — no real probes"
        ), upgrades

    adapters = _load_adapters(state, wiki)
    for adapter in adapters:
        name = getattr(adapter, "name", type(adapter).__name__)
        if is_adapter_in_backoff(state, name):
            log(f"  {name}: in back-off, skipping")
            continue
        try:
            current = adapter.probe_current_version()
            latest = adapter.probe_latest_version()
        except Exception as exc:  # noqa: BLE001
            log(f"  {name}: probe error: {exc}")
            continue

        if current is None:
            log(f"  {name}: current version unknown, skipping")
            continue
        if latest is None:
            log(f"  {name}: latest version unknown (stub), skipping")
            continue
        if current != latest:
            upgrades.append(Upgrade(
                adapter_name=name,
                current_version=current,
                latest_version=latest,
                reason=f"{current} → {latest}",
            ))
            log(f"  {name}: upgrade candidate {current} → {latest}")
        else:
            log(f"  {name}: up-to-date at {current}")

    # Cap at 1 per cycle
    upgrades = upgrades[:MAX_UPGRADES_PER_CYCLE]
    return PhaseResult(
        phase="detect_upgrades",
        status="ok",
        detail=f"{len(upgrades)} candidate(s) after cap",
        data={"candidates": [asdict(u) for u in upgrades]},
    ), upgrades


# ---------------------------------------------------------------------------
# Phase 4 — canary_each_upgrade (STUB)
# ---------------------------------------------------------------------------

def canary_each_upgrade(
    upgrades: list[Upgrade],
    state: dict[str, Any],
    wiki: Path,
    dry_run: bool = False,
    fixture_mode: bool = False,
) -> PhaseResult:
    log("phase 4: canary_each_upgrade")
    # T5 wires factory_no_drift_probe.sh + model_promotion_gate.py + hermes_promotion_runner.py
    # For now: pre-write rollback tag BEFORE any apply, then stub out apply.
    if not upgrades:
        return PhaseResult(phase="canary_each_upgrade", status="skipped", detail="no upgrade candidates")

    results = []
    adapters_map: dict[str, Any] = {}
    # Re-load adapters to get rollback_tag method
    adapters_dir = wiki / "tools" / "daily_evolution_adapters"
    if adapters_dir.exists():
        try:
            import importlib.util
            for mod_path in sorted(adapters_dir.glob("*.py")):
                if mod_path.stem.startswith("_"):
                    continue
                spec = importlib.util.spec_from_file_location(mod_path.stem, mod_path)
                if spec is None or spec.loader is None:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                for attr_name in dir(mod):
                    obj = getattr(mod, attr_name)
                    if (
                        isinstance(obj, type)
                        and hasattr(obj, "probe_current_version")
                        and attr_name not in ("AdapterBase",)
                    ):
                        inst = obj()
                        adapters_map[getattr(inst, "name", attr_name)] = inst
        except Exception as exc:  # noqa: BLE001
            log(f"  WARN: adapter reload error: {exc}")

    for upgrade in upgrades[:MAX_UPGRADES_PER_CYCLE]:
        adapter = adapters_map.get(upgrade.adapter_name)
        tag = None
        if adapter and hasattr(adapter, "create_rollback_tag"):
            try:
                label = f"daily-evo-{upgrade.adapter_name}-pre-{now_kzt().strftime('%Y%m%d-%H%M%S')}"
                tag = adapter.create_rollback_tag(label) if not dry_run else f"dry-run-tag-{label}"
                log(f"  rollback tag created: {tag}")
            except Exception as exc:  # noqa: BLE001
                log(f"  WARN: rollback tag failed: {exc}")

        # apply_upgrade is STUB — T5 wires real canary logic
        log(f"  STUB: would apply {upgrade.adapter_name} {upgrade.current_version} → {upgrade.latest_version}")
        results.append({
            "adapter": upgrade.adapter_name,
            "tag": tag,
            "action": "stub_no_apply",
            "dry_run": dry_run,
        })

    return PhaseResult(
        phase="canary_each_upgrade",
        status="ok",
        detail="stub — no real upgrade applied",
        data={"results": results},
    )


# ---------------------------------------------------------------------------
# Phase 5 — proof_pack (STUB)
# ---------------------------------------------------------------------------

def proof_pack(wiki: Path, dry_run: bool = False, fixture_mode: bool = False) -> PhaseResult:
    log("phase 5: proof_pack")
    probe_script = wiki / FACTORY_PROBE
    if not probe_script.exists():
        return PhaseResult(
            phase="proof_pack",
            status="skipped",
            detail=f"factory_no_drift_probe.sh not found at {probe_script}",
        )

    if dry_run or fixture_mode:
        return PhaseResult(
            phase="proof_pack",
            status="skipped",
            detail="dry_run or fixture_mode — would run factory_no_drift_probe.sh --quiet + satory_proof_runner --ttl-hours=20",
        )

    r = run_cmd(
        ["bash", str(probe_script), "--quiet", "--no-telegram"],
        cwd=wiki,
        timeout=120,
    )
    factory_status = "ok" if r["ok"] else "error"
    factory_detail = (r["stdout"] + r["stderr"])[:400]

    # Extend proof_pack to ALSO fire the Satory 12-task proof runner (T5 of
    # the Todoist Musk-cleanup, shipped at 10badf73 + acd57827 idempotency).
    # TTL=20h ensures daily-evolution at 03:00 KZT fires once per 24h window
    # without colliding with any hourly cron Codex might wire on satory side.
    # Soft-fail: runner errors do not flip proof_pack to error.
    satory_runner = wiki / "tools" / "satory_proof_runner.py"
    satory_detail = ""
    if satory_runner.exists():
        sr = run_cmd(
            ["python3", str(satory_runner), "--ttl-hours", "20"],
            cwd=wiki,
            timeout=180,
        )
        if sr["ok"]:
            # Extract the summary line ("done. ok=X yellow=Y skipped_dedup=Z ledger=...")
            summary = ""
            for line in (sr["stdout"] or "").splitlines():
                if "done." in line and "ok=" in line:
                    summary = line.strip()
                    break
            satory_detail = f"satory_proof_runner: {summary or '(no summary line)'}"[:400]
        else:
            satory_detail = f"satory_proof_runner: failed rc={sr['returncode']} {(sr['stderr'] or '')[:200]}"
    else:
        satory_detail = "satory_proof_runner: not found, skipped"

    combined_detail = f"factory: {factory_detail} | {satory_detail}"
    return PhaseResult(phase="proof_pack", status=factory_status, detail=combined_detail[:800])


# ---------------------------------------------------------------------------
# Phase 6 — digest + surface fan-out helpers
# ---------------------------------------------------------------------------

# Karpathy 6-axis names (sourced from pages/skills/karpathy-loop/SKILL.md)
_KARPATHY_AXES = [
    "rigor",
    "evidence",
    "deletion-first",
    "observability",
    "doctrine-codification",
    "cycle-time",
]


def _load_karpathy_axes(wiki: Path) -> list[str]:
    """Return 6-axis names from SKILL.md if available, else hardcoded fallback."""
    skill_path = wiki / "pages" / "skills" / "karpathy-loop" / "SKILL.md"
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8")
        # Parse from the scorecard table; look for rows like "| N | **axis-name** |"
        axes: list[str] = []
        for line in text.splitlines():
            # Match table rows with bold axis names: "| 1 | **rigor** |..."
            if line.strip().startswith("|") and "**" in line:
                parts = [p.strip() for p in line.split("|")]
                for part in parts:
                    if part.startswith("**") and part.endswith("**"):
                        name = part[2:-2].strip()
                        # Accept only plausible axis names (no whitespace, not too long)
                        if name and " " not in name and len(name) <= 30:
                            axes.append(name)
                            break
            if len(axes) == 6:
                break
        if len(axes) == 6:
            return axes
    return list(_KARPATHY_AXES)


def _karpathy_six_axis_score(phases: list[PhaseResult], axes: list[str]) -> str:
    """Produce a markdown table scoring this daily-evolution cycle on 6 Karpathy axes.

    Scoring heuristic (self-audit, 0-2):
      2 = solid (phase ran + status ok)
      1 = partial (phase ran but status non-ok)
      0 = missing (phase absent)
    """
    phase_map = {p.phase: p for p in phases}
    # Map axes to relevant phase signals
    axis_phase_hints: dict[str, list[str]] = {
        "rigor": ["snapshot", "detect_upgrades"],
        "evidence": ["snapshot", "proof_pack"],
        "deletion-first": ["canary_each_upgrade"],
        "observability": ["snapshot", "notify"],
        "doctrine-codification": ["digest"],
        "cycle-time": ["pull_substrate", "proof_pack"],
        # fallbacks: AP ≥1 absorbed, gbrain timeline, compounding artifact, zero rot, substrate smarter, RULE ZERO
        "AP ≥1 absorbed": ["digest"],
        "gbrain timeline ≥1 push": ["digest"],
        "Compounding artifact ≥1": ["proof_pack", "canary_each_upgrade"],
        "Zero rot smuggled": ["digest"],
        "Substrate measurably smarter": ["digest"],
        "RULE ZERO upheld": ["digest"],
    }

    rows: list[str] = []
    total = 0
    for i, axis in enumerate(axes, start=1):
        hints = axis_phase_hints.get(axis, list(phase_map.keys()))
        matched = [phase_map[h] for h in hints if h in phase_map]
        if not matched:
            score = 0
            note = "phase absent"
        elif all(p.status == "ok" for p in matched):
            score = 2
            note = "solid"
        elif any(p.status in ("ok", "skipped") for p in matched):
            score = 1
            note = "partial"
        else:
            score = 0
            note = "error/missing"
        total += score
        rows.append(f"| {i} | {axis} | {score}/2 | {note} |")

    max_score = len(axes) * 2
    header = (
        "\n## Karpathy 6-axis self-score\n\n"
        "| # | Axis | Score | Note |\n"
        "|---|---|---|---|\n"
    )
    table = header + "\n".join(rows) + f"\n\n**Total: {total}/{max_score}**\n"
    return table


def _push_gbrain_timeline(slug: str, date: str, summary: str) -> bool:
    """Push a timeline entry to gbrain via substrate-CLI SSH fallback.

    Returns True on success, False on failure (caller must not raise).

    Bug 2026-05-20 (first real run): the previous version built the remote
    command as a single shell string with `json.dumps(summary)` inline. The
    embedded JSON quotes broke SSH's outer-shell parsing
    (`bash: -c: line 1: unexpected EOF`). Fix: shlex.quote the summary so
    the remote shell sees one safely-quoted argv element.
    """
    import shlex
    # Bug 2026-05-20 (second live run): `python3 -m gbrain.cli` fails on VPS
    # with "No module named 'gbrain'" — gbrain is installed as a binary at
    # /opt/nous-agaas/gbrain/bin/gbrain, not as a Python package on the
    # system Python path. CLI shape (gbrain 0.22.16): positional args,
    # `gbrain timeline-add <slug> <date> <summary>`.
    remote_cmd = (
        "/opt/nous-agaas/gbrain/bin/gbrain timeline-add "
        f"{shlex.quote(slug)} {shlex.quote(date)} {shlex.quote(summary)}"
    )
    cmd = [
        "ssh",
        "-o", "ConnectTimeout=10",
        "-o", "BatchMode=yes",
        HOST_VPS,
        remote_cmd,
    ]
    result = run_cmd(cmd, timeout=30)
    if result["ok"]:
        log(f"  gbrain timeline push ok: slug={slug}")
        return True
    log(f"  WARN: gbrain timeline push failed: {result['stderr'][:200]}")
    return False


def _reseed_hermes(wiki: Path) -> bool:
    """Re-seed Hermes WebUI with the daily-evolution result.

    Hermes WebUI lives on Air; its seed script reads env vars
    (HERMES_WEBUI_STATE_DIR, HERMES_BASE_HOME, HERMES_WEBUI_PROFILE,
    HERMES_WEBUI_DEFAULT_WORKSPACE) that are only set in Air's launchd plist.
    Running locally on Mac → KeyError → SystemExit. Fix: invoke via SSH to
    Air where the env is correct; if SSH unreachable, skip silently.
    """
    # SSH to Air; the script lives at ~/nous-agaas/wiki/tools/hermes_webui_factory_seed.py
    remote_cmd = (
        "cd ~/nous-agaas/wiki && "
        "python3 tools/hermes_webui_factory_seed.py"
    )
    cmd = [
        "ssh",
        "-o", "ConnectTimeout=10",
        "-o", "BatchMode=yes",
        HOST_AIR,
        remote_cmd,
    ]
    result = run_cmd(cmd, timeout=60)
    if result["ok"]:
        log("  Hermes WebUI re-seed ok (via Air ssh)")
        return True
    log(f"  WARN: Hermes WebUI re-seed failed: {result['stderr'][:200]}")
    return False


def _publish_digest(
    body: str,
    audit_path: Path,
    phases: list[PhaseResult],
    wiki: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Publish the digest to gbrain timeline, Hermes WebUI, and update with Karpathy score.

    Order: score Karpathy axes → rewrite digest with table → push gbrain → re-seed Hermes.
    Returns dict with per-surface status.
    """
    result: dict[str, Any] = {
        "karpathy_table": "skipped",
        "gbrain_push": "skipped",
        "hermes_reseed": "skipped",
    }

    # Step 1: Karpathy 6-axis self-score → append to digest body and rewrite file
    axes = _load_karpathy_axes(wiki)
    karpathy_table = _karpathy_six_axis_score(phases, axes)
    enriched_body = body + karpathy_table
    try:
        audit_path.write_text(enriched_body, encoding="utf-8")
        result["karpathy_table"] = "ok"
        log("  Karpathy 6-axis self-score appended to digest")
    except OSError as exc:
        result["karpathy_table"] = f"error: {exc}"
        log(f"  WARN: could not append Karpathy table: {exc}")

    if dry_run:
        log("  dry_run — skipping gbrain push + Hermes re-seed")
        result["gbrain_push"] = "dry_run"
        result["hermes_reseed"] = "dry_run"
        return result

    # Step 2: gbrain timeline push
    date_str = today_str()
    # summary = first 200 chars of digest body (markdown, so skip frontmatter lines)
    body_lines = [l for l in enriched_body.splitlines() if not l.startswith("---") and l.strip()]
    summary_text = " ".join(body_lines)[:200]
    # Slug must reference an existing gbrain page. factory-ops is the
    # canonical skill that owns the daily-evolution cron doctrine; using it
    # as the timeline aggregator keeps entries discoverable from one place.
    # Bug 2026-05-20 (third live run): "pages/audits/daily-evolution" rejected
    # with "page not found" because no such canonical page exists.
    gbrain_ok = _push_gbrain_timeline(
        slug="pages/skills/factory-ops/skill",
        date=date_str,
        summary=summary_text,
    )
    result["gbrain_push"] = "ok" if gbrain_ok else "warn"

    # Step 3: Hermes WebUI re-seed
    hermes_ok = _reseed_hermes(wiki)
    result["hermes_reseed"] = "ok" if hermes_ok else "warn"

    return result


def digest(
    phases: list[PhaseResult],
    wiki: Path,
    upgrades: list[Upgrade],
    dry_run: bool = False,
) -> PhaseResult:
    log("phase 6: digest")
    date_str = today_str()
    audit_path = wiki / DEFAULT_AUDIT_DIR / f"DAILY-EVOLUTION-{date_str}.md"
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    rows = "\n".join(
        f"| {p.phase} | {p.status} | {p.detail[:120]} |"
        for p in phases
    )

    upgrade_section = ""
    if upgrades:
        items = "\n".join(
            f"- **{u.adapter_name}**: {u.current_version} → {u.latest_version}"
            for u in upgrades
        )
        upgrade_section = f"\n## Upgrade candidates (capped at {MAX_UPGRADES_PER_CYCLE})\n\n{items}\n"

    body = (
        "---\n"
        "type: audit\n"
        f"id: DAILY-EVOLUTION-{date_str}\n"
        f'title: "Daily evolution cycle {date_str}"\n'
        f"date: {date_str}\n"
        "status: active\n"
        "tags: [daily-evolution, cron, audit]\n"
        "---\n\n"
        f"# Daily Evolution Cycle — {date_str}\n\n"
        f"Run at: `{now_kzt().isoformat()}`\n\n"
        "## Phase results\n\n"
        "| Phase | Status | Detail |\n"
        "|---|---|---|\n"
        f"{rows}\n"
        f"{upgrade_section}"
        "\n## Safety note\n\n"
        "This daily evolution runner is currently a proof/report loop, not a full safe auto-upgrader. "
        "`canary_each_upgrade` is still a no-apply gate, and apply adapters are not considered ready until "
        "`model_promotion_gate.py` is green and the change has explicit approval. "
        "Auto-promote nothing from this report alone.\n"
        "\n## See also\n\n"
        "- [[pages/systems/daily-evolution-state.json]]\n"
        "- [[pages/systems/daily-evolution-snapshot-pre.json]]\n"
    )
    audit_path.write_text(body, encoding="utf-8")
    log(f"  digest written → {audit_path}")

    # Fan-out to additional surfaces
    publish_result = _publish_digest(body, audit_path, phases, wiki, dry_run=dry_run)
    log(f"  publish surfaces: {publish_result}")

    return PhaseResult(
        phase="digest",
        status="ok",
        detail=str(audit_path),
        data={"publish": publish_result},
    )


# ---------------------------------------------------------------------------
# Phase 7 — notify (STUB)
# ---------------------------------------------------------------------------

def notify(
    phases: list[PhaseResult],
    upgrades: list[Upgrade],
    dry_run: bool = False,
) -> PhaseResult:
    log("phase 7: notify")
    # Per spec rules 7a/7b/7c:
    # 7a = upgrade requires login/cred refresh
    # 7b = rollback fired and supervisor can't auto-repair
    # 7c = new vulnerability flagged
    # Otherwise SILENT — compact digest at 09:00 KZT alongside morning brief
    #
    # STUB: only log intent; tg_send.sh wiring deferred to T6/T8
    aborts = [p for p in phases if p.status == "aborted"]
    errors = [p for p in phases if p.status == "error"]

    if aborts:
        log(f"  would notify (7b/7a): {len(aborts)} aborted phase(s): {[p.phase for p in aborts]}")
    elif errors:
        log(f"  would notify (7b): {len(errors)} error phase(s): {[p.phase for p in errors]}")
    else:
        log("  silent — no notification triggers fired (rules 7a/7b/7c not met)")

    return PhaseResult(phase="notify", status="ok", detail="stub — would notify via tg_send.sh if rules met")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Do not apply any real changes.")
    parser.add_argument("--fixture-mode", action="store_true", help="Use stub data; no SSH or git calls.")
    parser.add_argument("--skip-pull", action="store_true", help="Skip phase 2 git pull.")
    parser.add_argument("--state-file", type=Path, default=None, help="Override state file path.")
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI, help="Wiki root directory.")
    args = parser.parse_args(argv or sys.argv[1:])

    wiki: Path = args.wiki
    state_path: Path = args.state_file or (wiki / DEFAULT_STATE_REL)

    log(f"starting  wiki={wiki}  dry_run={args.dry_run}  fixture_mode={args.fixture_mode}")

    # Load state
    state = load_state(state_path)

    # Idempotency: same day re-run is allowed (no-op if phases already ran)
    if already_ran_today(state) and not args.fixture_mode:
        log("already ran today — re-running (idempotent)")

    phases: list[PhaseResult] = []
    upgrades: list[Upgrade] = []

    try:
        # Phase 1
        p1 = snapshot(wiki, fixture_mode=args.fixture_mode)
        phases.append(p1)

        # Phase 2
        p2 = pull_substrate(
            wiki,
            dry_run=args.dry_run,
            skip_pull=args.skip_pull,
            fixture_mode=args.fixture_mode,
        )
        phases.append(p2)
        if p2.status == "aborted":
            log("aborting cycle due to merge conflict")
        else:
            # Phase 3
            p3, upgrades = detect_upgrades(state, wiki, fixture_mode=args.fixture_mode)
            phases.append(p3)

            # Phase 4
            p4 = canary_each_upgrade(upgrades, state, wiki, dry_run=args.dry_run, fixture_mode=args.fixture_mode)
            phases.append(p4)

            # Phase 5
            p5 = proof_pack(wiki, dry_run=args.dry_run, fixture_mode=args.fixture_mode)
            phases.append(p5)

    except Exception as exc:  # noqa: BLE001
        log(f"FATAL error in phases 1-5: {exc}")
        phases.append(PhaseResult(phase="fatal", status="error", detail=str(exc)))

    # Phase 6 — always run digest
    try:
        p6 = digest(phases, wiki, upgrades, dry_run=args.dry_run)
        phases.append(p6)
    except Exception as exc:  # noqa: BLE001
        log(f"digest error: {exc}")
        phases.append(PhaseResult(phase="digest", status="error", detail=str(exc)))

    # Phase 7 — always run notify
    try:
        p7 = notify(phases, upgrades, dry_run=args.dry_run)
        phases.append(p7)
    except Exception as exc:  # noqa: BLE001
        log(f"notify error: {exc}")

    # Write state
    write_state(state_path, state)
    log(f"state written → {state_path}")

    # Summary
    statuses = [p.status for p in phases]
    log(f"done: {statuses}")
    return 0 if "aborted" not in statuses and "fatal" not in statuses else 1


if __name__ == "__main__":
    raise SystemExit(main())
