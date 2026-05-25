#!/usr/bin/env python3
"""Daily 03:00 substrate librarian for Nous AGaaS.

The job is intentionally boring: prove the shared substrate is alive, write one
Obsidian report, and sync it. It does not mutate Todoist/Notion business data.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import plistlib
import socket
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ALMATY = dt.timezone(dt.timedelta(hours=5))
AIR_HOME = Path("/Users/madia")
AIR_ROOT = AIR_HOME / "nous-agaas"
DEFAULT_WIKI = AIR_ROOT / "wiki"
DEFAULT_RUNTIME = AIR_ROOT
SATORY_PROJECT_ID = "6gJ5j8PRVVCWpgCq"
PERSONAL_PROJECT_ID = "6fhm35CG93P2jff9"
OPENCLAW_PORT = 18789
VPS = "root@65.108.215.200"


class Probe:
    def __init__(
        self,
        component: str,
        status: str,
        summary: str,
        evidence: str = "",
        remediation: str = "",
        code: int | None = None,
    ) -> None:
        self.component = component
        self.status = status
        self.summary = summary
        self.evidence = evidence.strip()
        self.remediation = remediation.strip()
        self.code = code

    @property
    def okish(self) -> bool:
        return self.status in {"GREEN", "YELLOW"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status,
            "summary": self.summary,
            "evidence": self.evidence,
            "remediation": self.remediation,
            "code": self.code,
        }


def tail_text(text: str, limit: int = 1800) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def ensure_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 60,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "cmd": " ".join(cmd),
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "ok": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": " ".join(cmd),
            "returncode": 124,
            "stdout": ensure_text(exc.stdout),
            "stderr": ensure_text(exc.stderr) or f"timeout after {timeout}s",
            "ok": False,
        }
    except FileNotFoundError as exc:
        return {
            "cmd": " ".join(cmd),
            "returncode": 127,
            "stdout": "",
            "stderr": str(exc),
            "ok": False,
        }


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def launchd_status(label: str) -> Probe:
    result = run(["launchctl", "list"], timeout=20)
    if not result["ok"]:
        return Probe("launchd", "RED", "launchctl list failed", result["stderr"], code=result["returncode"])
    for line in result["stdout"].splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[-1] == label:
            pid, last_exit = parts[0], parts[1]
            if pid != "-":
                status = "GREEN"
                summary = f"{label} loaded and currently running pid={pid} last_exit={last_exit}"
            else:
                status = "GREEN" if last_exit == "0" else "RED"
                summary = f"{label} loaded interval/oneshot last_exit={last_exit}"
            return Probe(label, status, summary, line)
    return Probe(label, "RED", f"{label} not loaded", remediation=f"Install/bootstrap {label} LaunchAgent")


def read_plist_schedule(plist_path: Path) -> str:
    if not plist_path.exists():
        return "plist missing"
    try:
        with plist_path.open("rb") as fh:
            data = plistlib.load(fh)
    except Exception as exc:
        return f"plist unreadable: {exc}"
    sci = data.get("StartCalendarInterval")
    if isinstance(sci, dict):
        hour = sci.get("Hour")
        minute = sci.get("Minute")
        return f"{hour:02d}:{minute:02d}" if isinstance(hour, int) and isinstance(minute, int) else str(sci)
    interval = data.get("StartInterval")
    if interval:
        return f"every {interval}s"
    return "no calendar interval"


def probe_wiki_git(wiki: Path) -> Probe:
    if not (wiki / ".git").exists():
        return Probe("Obsidian/wiki", "RED", f"{wiki} is not a git repository")
    head = run(["git", "rev-parse", "--short", "HEAD"], cwd=wiki, timeout=20)
    status = run(["git", "status", "--porcelain=v1"], cwd=wiki, timeout=20)
    if not head["ok"] or not status["ok"]:
        return Probe("Obsidian/wiki", "RED", "git state probe failed", head["stderr"] + status["stderr"])
    dirty = [line for line in status["stdout"].splitlines() if line.strip()]
    if dirty:
        evidence = "\n".join(dirty[:30])
        return Probe(
            "Obsidian/wiki",
            "YELLOW",
            f"wiki HEAD {head['stdout'].strip()} with {len(dirty)} dirty paths",
            evidence,
            "Authorial dirty paths require explicit commit; auto-sync will skip them.",
        )
    return Probe("Obsidian/wiki", "GREEN", f"wiki clean at HEAD {head['stdout'].strip()}", "")


def probe_air_launchd_schedule(wiki: Path) -> Probe:
    plist_path = wiki / "tools" / "launchd" / "com.nous.daily-0300-substrate-sync.plist"
    schedule = read_plist_schedule(plist_path)
    loaded = launchd_status("com.nous.daily-0300-substrate-sync")
    if schedule != "03:00":
        return Probe(
            "03:00 owner",
            "RED",
            f"daily-0300 plist schedule is {schedule}, expected 03:00",
            loaded.evidence,
            "Fix StartCalendarInterval to Hour=3 Minute=0 and reinstall LaunchAgent.",
        )
    if loaded.status == "RED":
        return Probe("03:00 owner", "RED", f"plist is scheduled at 03:00 but not loaded: {loaded.summary}", loaded.evidence, loaded.remediation)
    return Probe("03:00 owner", "GREEN", f"daily-0300 owner loaded and scheduled at {schedule}", loaded.evidence)


def probe_openclaw(skip_factory_probe: bool, runtime: Path) -> Probe:
    status_bits: list[str] = []
    red: list[str] = []
    docker = run(["/usr/local/bin/docker", "inspect", "openclaw", "--format", "{{.State.Health.Status}}"], timeout=20)
    if docker["ok"] and docker["stdout"].strip() == "healthy":
        status_bits.append("container healthy")
    else:
        red.append(f"container={tail_text(docker['stdout'] + docker['stderr'], 300) or 'unknown'}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect(("127.0.0.1", OPENCLAW_PORT))
        status_bits.append("port 18789 open")
    except OSError as exc:
        red.append(f"port 18789 closed: {exc}")
    finally:
        sock.close()
    if skip_factory_probe:
        status_bits.append("factory text probe skipped by flag")
        status = "YELLOW" if not red else "RED"
        return Probe("OpenClaw", status, "; ".join(status_bits) if status_bits else "OpenClaw probe failed", "\n".join(red))
    factory = run([
        "python3",
        "run_task.py",
        "--source",
        "daily_0300_substrate_sync",
        "Reply with exactly: DAILY_0300_OK",
    ], cwd=runtime, timeout=360)
    if factory["ok"] and "DAILY_0300_OK" in (factory["stdout"] + factory["stderr"]):
        status_bits.append("factory E2E returned DAILY_0300_OK")
    else:
        red.append(f"factory probe failed: {tail_text(factory['stdout'] + factory['stderr'], 500)}")
    status = "GREEN" if not red else "RED"
    return Probe("OpenClaw", status, "; ".join(status_bits), "\n".join(red))


def probe_litellm(runtime: Path) -> Probe:
    env = load_env_file(runtime / "litellm" / ".env")
    key = env.get("LITELLM_MASTER_KEY") or os.environ.get("LITELLM_MASTER_KEY")
    if not key:
        return Probe("LiteLLM", "RED", "LITELLM_MASTER_KEY missing", remediation="Restore litellm/.env on Air runtime.")
    request = urllib.request.Request("http://127.0.0.1:4000/health/readiness", headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(2000).decode("utf-8", errors="replace")
            code = response.status
    except urllib.error.HTTPError as exc:
        body = exc.read(1000).decode("utf-8", errors="replace")
        return Probe("LiteLLM", "RED", f"LiteLLM /health/readiness HTTP {exc.code}", body, code=exc.code)
    except Exception as exc:
        return Probe("LiteLLM", "RED", f"LiteLLM /health/readiness unreachable: {exc}")
    status = "GREEN" if code == 200 and "healthy" in body.lower() else "YELLOW"
    return Probe("LiteLLM", status, f"LiteLLM /health/readiness HTTP {code}", tail_text(body, 800), code=code)


def probe_telegram(runtime: Path) -> Probe:
    launchd = launchd_status("com.nous.telegram-poll")
    heartbeat = runtime / "logs" / "telegram_poll.lock"
    err_log = runtime / "logs" / "telegram_poll.err"
    age = None
    if heartbeat.exists():
        age = int(dt.datetime.now().timestamp() - heartbeat.stat().st_mtime)
    evidence = [launchd.summary]
    if age is not None:
        evidence.append(f"telegram_poll.lock age={age}s")
    if err_log.exists():
        evidence.append(f"telegram_poll.err mtime={dt.datetime.fromtimestamp(err_log.stat().st_mtime, ALMATY).isoformat()}")
    if launchd.status == "RED":
        return Probe("Telegram", "RED", "telegram poller launchd is not healthy", "\n".join(evidence), launchd.remediation)
    if age is not None and age > 180:
        return Probe("Telegram", "YELLOW", f"poll heartbeat stale at {age}s", "\n".join(evidence), "Check Air network and telegram_poll launchd.")
    if age is None:
        return Probe("Telegram", "YELLOW", "telegram poller loaded but heartbeat file is missing", "\n".join(evidence), "Check telegram_poll.py heartbeat/lock writer.")
    return Probe("Telegram", "GREEN", "telegram poller loaded and heartbeat is recent", "\n".join(evidence))


def probe_todoist(wiki: Path, runtime: Path) -> Probe:
    control_script = wiki / "tools" / "todoist_control_plane_audit.py"
    if control_script.exists():
        result = run(
            [
                "python3",
                str(control_script),
                "--json",
                "--env-file",
                str(runtime / ".env"),
            ],
            cwd=wiki,
            timeout=180,
        )
        if not result["ok"]:
            return Probe(
                "Todoist/ControlPlane",
                "RED",
                "global Todoist control-plane audit failed",
                tail_text(result["stdout"] + result["stderr"], 1400),
                code=result["returncode"],
            )
        try:
            payload = json.loads(result["stdout"])
        except json.JSONDecodeError as exc:
            return Probe(
                "Todoist/ControlPlane",
                "RED",
                f"global Todoist audit JSON parse failed: {exc}",
                tail_text(result["stdout"], 1400),
            )
        audit = payload.get("audit", {})
        counts = audit.get("counts", {})
        risks = audit.get("risk_counts", {})
        plan = payload.get("plan", [])
        hard_keys = [
            "missing_project",
            "invalid_section",
            "root_no_section",
            "subtask_no_section_inherited",
            "missing_owner",
            "missing_department",
            "missing_labels",
            "default_priority",
        ]
        hard_risk_total = sum(int(risks.get(key, 0) or 0) for key in hard_keys)
        status = "GREEN" if hard_risk_total == 0 and not plan else "YELLOW"
        if hard_risk_total:
            status = "RED"
        summary = (
            f"{counts.get('active_tasks', '?')} active tasks; "
            f"no-section={risks.get('root_no_section', '?')}; "
            f"missing_owner={risks.get('missing_owner', '?')}; "
            f"missing_department={risks.get('missing_department', '?')}; "
            f"default_priority={risks.get('default_priority', '?')}; "
            f"contextless={risks.get('no_description_or_note', '?')}; "
            f"pending_actions={len(plan)}"
        )
        evidence = json.dumps(
            {
                "counts": counts,
                "risk_counts": risks,
                "pending_actions_sample": plan[:10],
            },
            ensure_ascii=False,
            indent=2,
        )
        remediation = ""
        if hard_risk_total or plan:
            remediation = "Run tools/todoist_control_plane_audit.py in read-only mode, review, then apply only deterministic hygiene fixes."
        return Probe("Todoist/ControlPlane", status, summary, evidence, remediation)

    script = wiki / "tools" / "audit_satory_todoist_state.py"
    if not script.exists():
        return Probe("Todoist/Satory", "RED", "Todoist audit script missing", str(script))
    result = run(
        [
            "python3",
            str(script),
            "--json",
            "--project-id",
            SATORY_PROJECT_ID,
            "--state-db",
            str(runtime / "tenants" / "satory" / "state.db"),
            "--env-file",
            str(runtime / ".env"),
            "--direct-task-lookup",
        ],
        cwd=wiki,
        timeout=120,
    )
    if not result["ok"]:
        return Probe("Todoist/Satory", "RED", "read-only Todoist audit failed", tail_text(result["stdout"] + result["stderr"], 1400), code=result["returncode"])
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError as exc:
        return Probe("Todoist/Satory", "RED", f"Todoist audit JSON parse failed: {exc}", tail_text(result["stdout"], 1400))
    project = payload.get("project", {})
    if str(project.get("id")) == PERSONAL_PROJECT_ID:
        return Probe("Todoist/Satory", "RED", "personal Todoist project touched by audit", json.dumps(project, ensure_ascii=False))
    tasks = payload.get("tasks", {})
    risks = payload.get("risks", [])
    status = "GREEN" if not risks else "YELLOW"
    summary = (
        f"{tasks.get('active_count', '?')} active tasks; "
        f"{tasks.get('ai_label_ru_count', '?')} with ИИ-предложено; risks={len(risks)}"
    )
    return Probe("Todoist/Satory", status, summary, json.dumps({"risks": risks[:10], "project": project}, ensure_ascii=False, indent=2))


def probe_notion(runtime: Path, wiki: Path) -> Probe:
    tenant_env = load_env_file(runtime / "tenants" / "satory" / ".env")
    root_env = load_env_file(runtime / ".env")
    values = {**root_env, **tenant_env}
    present = sorted(k for k in values if k.startswith("SATORY_NOTION_") or k.startswith("NOTION_"))
    client = wiki / "tenants" / "satory" / "agents" / "lib" / "notion_client.py"
    client_text = client.read_text(encoding="utf-8", errors="replace") if client.exists() else ""
    stubbed = "stub" in client_text.lower() or "TODO" in client_text
    if not values.get("SATORY_NOTION_TOKEN") and not values.get("NOTION_TOKEN"):
        return Probe(
            "Notion/Satory",
            "RED",
            "Notion API token not present in Air tenant/root env",
            f"present keys only: {', '.join(present) if present else 'none'}",
            "Create/share a Notion internal integration for the Satory DBs and store only the Satory token in Air tenant env.",
        )
    if stubbed:
        return Probe(
            "Notion/Satory",
            "YELLOW",
            "Notion token is present but runtime client still appears stubbed",
            f"present keys: {', '.join(present)}; client={client}",
            "Replace stub client with production Notion API pull before calling it from automation.",
        )
    return Probe("Notion/Satory", "GREEN", "Notion credentials present and runtime client is not marked stubbed", f"present keys: {', '.join(present)}")


def probe_gbrain(wiki: Path) -> Probe:
    remote = r"""
set -euo pipefail
PROXY_ENV="${GBRAIN_OPENAI_COMPAT_ENV:-/root/.gbrain/openai-compatible.env}"
if [ -f "$PROXY_ENV" ]; then
  set -a
  . "$PROXY_ENV"
  set +a
fi
KEY="${OPENAI_API_KEY:-}"
if [ -z "$KEY" ] && [ -f /root/.config/codex/auth.json ]; then
  KEY=$(python3 - <<'PY'
import json
from pathlib import Path
p=Path('/root/.config/codex/auth.json')
data=json.loads(p.read_text())
print(data.get('OPENAI_API_KEY',''))
PY
  )
fi
if [ -z "$KEY" ] && [ -f /root/nous-agaas/.env ]; then
  KEY=$(grep -E '^OPENAI_API_KEY=' /root/nous-agaas/.env | tail -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' || true)
fi
if [ -z "$KEY" ]; then
  echo "OPENAI_API_KEY missing from env, /root/.config/codex/auth.json, and /root/nous-agaas/.env" >&2
  exit 2
fi
export OPENAI_API_KEY="$KEY"
export DATABASE_URL="postgresql://gbrain:gbrain2026@localhost:5432/gbrain"
SYNC_TIMEOUT="${GBRAIN_DAILY_SYNC_TIMEOUT:-180}"
EMBED_TIMEOUT="${GBRAIN_DAILY_EMBED_TIMEOUT:-180}"
DOCTOR_TIMEOUT="${GBRAIN_DAILY_DOCTOR_TIMEOUT:-60}"
cd /opt/nous-agaas/gbrain
timeout -k 10s "$SYNC_TIMEOUT" bin/gbrain sync --repo /root/nous-agaas/wiki >/tmp/daily0300-gbrain-sync.out
timeout -k 10s "$EMBED_TIMEOUT" bin/gbrain embed --stale >/tmp/daily0300-gbrain-embed.out
timeout -k 10s "$DOCTOR_TIMEOUT" bin/gbrain doctor --repo /root/nous-agaas/wiki --json
"""
    result = run(["ssh", VPS, remote], cwd=wiki, timeout=480)
    if not result["ok"]:
        combined = result["stdout"] + result["stderr"]
        if "Another sync is in progress" in combined:
            fallback = r"""
set -euo pipefail
export DATABASE_URL="postgresql://gbrain:gbrain2026@localhost:5432/gbrain"
cd /opt/nous-agaas/gbrain
python3 - <<'PY'
import json
import subprocess
from pathlib import Path

pairs = [
    ("pages/skills/todoist-control-plane/SKILL.md", "pages/skills/todoist-control-plane/skill"),
    ("pages/skills/gbrain-ops/SKILL.md", "pages/skills/gbrain-ops/skill"),
]
wiki = Path("/root/nous-agaas/wiki")

def h1(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line.strip()
    return ""

readbacks = []
for rel, slug in pairs:
    fs_h1 = h1((wiki / rel).read_text(encoding="utf-8", errors="replace"))
    got = subprocess.run(["bin/gbrain", "get", slug], text=True, capture_output=True)
    gb_h1 = h1(got.stdout)
    readbacks.append({"slug": slug, "ok": got.returncode == 0 and fs_h1 == gb_h1, "fs_h1": fs_h1, "gbrain_h1": gb_h1})

doctor = subprocess.run(["bin/gbrain", "doctor", "--repo", str(wiki), "--json"], text=True, capture_output=True)
try:
    doctor_payload = json.loads(doctor.stdout)
except json.JSONDecodeError:
    doctor_payload = {"parse_error": doctor.stdout[-800:], "stderr": doctor.stderr[-800:]}

print(json.dumps({"readbacks": readbacks, "doctor_ok": doctor.returncode == 0, "doctor": doctor_payload}, ensure_ascii=False))
PY
"""
            fb = run(["ssh", VPS, fallback], cwd=wiki, timeout=120)
            if fb["ok"]:
                try:
                    payload = json.loads(fb["stdout"])
                except json.JSONDecodeError:
                    payload = {}
                readbacks = payload.get("readbacks") or []
                doctor = payload.get("doctor") or {}
                score = doctor.get("health_score", doctor.get("healthScore"))
                if readbacks and all(row.get("ok") for row in readbacks) and score is not None and int(score) >= 80:
                    return Probe(
                        "gbrain",
                        "YELLOW",
                        f"sync lock held by live autopilot; canary readbacks current; doctor score={score}/100",
                        json.dumps(payload, ensure_ascii=False, indent=2)[:2000],
                        "AP-91: do not delete a live lock; use exact readback and existing-page gbrain put for stale single pages.",
                        code=result["returncode"],
                    )
        return Probe("gbrain", "RED", "gbrain sync/embed/doctor failed", tail_text(result["stdout"] + result["stderr"], 1800), code=result["returncode"])
    try:
        data = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return Probe("gbrain", "RED", "gbrain doctor JSON parse failed", tail_text(result["stdout"], 1800))
    score = data.get("health_score", data.get("healthScore"))
    missing = data.get("missing_embeddings", data.get("missingEmbeddings", 0))
    stale = data.get("stale_pages", data.get("stalePages", 0))
    dead = data.get("dead_links", data.get("deadLinks", 0))
    status = "GREEN"
    if score is None or int(score) < 80:
        status = "RED"
    elif any(int(x or 0) for x in [missing, stale, dead]):
        status = "YELLOW"
    summary = f"doctor score={score}/100 missing={missing} stale={stale} dead_links={dead}"
    return Probe("gbrain", status, summary, json.dumps(data, ensure_ascii=False, indent=2)[:2000])


def probe_gstack(wiki: Path) -> Probe:
    parity = run(["bash", "tools/test_skill_version_parity.sh"], cwd=wiki, timeout=120)
    resolvable_script = wiki / "tools" / "check_resolvable.py"
    evidence = [tail_text(parity["stdout"] + parity["stderr"], 900)]
    status = "GREEN" if parity["ok"] else "RED"
    summary = "skill version parity passed" if parity["ok"] else "skill version parity failed"
    if resolvable_script.exists():
        resolvable = run(["python3", str(resolvable_script), "--wiki", str(wiki), "--json"], cwd=wiki, timeout=120)
        evidence.append(tail_text(resolvable["stdout"] + resolvable["stderr"], 900))
        if not resolvable["ok"]:
            status = "RED"
            summary += "; resolver probe failed"
    return Probe("GStack/skills", status, summary, "\n\n".join(evidence))


def probe_gpu(runtime: Path) -> Probe:
    launchd = launchd_status("com.nous.nous-gpu-collector-health")
    log = runtime / "logs" / "collector-health.out"
    gpu_required = os.environ.get("NOUS_GPU_REQUIRED", "").lower() in {"1", "true", "yes"}
    evidence = [launchd.summary]
    last_reason = ""
    if log.exists():
        log_tail = tail_text(log.read_text(encoding="utf-8", errors="replace"), 1800)
        evidence.append(log_tail)
        for line in reversed(log_tail.splitlines()):
            if "FAIL:" in line or "OK " in line:
                last_reason = line
                break
    if launchd.status == "RED":
        summary = "GPU collector health job is red"
        if last_reason:
            summary = f"{summary}: {last_reason}"
        status = "RED" if gpu_required else "YELLOW"
        remediation = (
            "Repair upstream mirror/collector input before relying on GPU-bound workloads."
            if gpu_required
            else "Optional GPU lane is degraded; keep control-plane sync green/yellow unless a GPU-bound workload is active. Set NOUS_GPU_REQUIRED=1 for GPU-dependent runs."
        )
        return Probe("Nous-GPU", status, summary, "\n".join(evidence), remediation)
    return Probe("Nous-GPU", "GREEN", "GPU collector health launchd is green", "\n".join(evidence))


def probe_satory_events(runtime: Path) -> Probe:
    launchd = launchd_status("com.nous.satory-events-watcher")
    log = runtime / "logs" / "satory-events-watcher.log"
    evidence = [launchd.summary]
    if log.exists():
        evidence.append(tail_text(log.read_text(encoding="utf-8", errors="replace"), 1000))
    if launchd.status == "RED":
        return Probe("Satory events", "RED", "satory events watcher launchd is red", "\n".join(evidence))
    joined = "\n".join(evidence).lower()
    if "stale" in joined or "frozen" in joined:
        return Probe("Satory events", "YELLOW", "watcher loaded but event freshness is suspicious", "\n".join(evidence))
    return Probe("Satory events", "GREEN", "satory events watcher launchd is green", "\n".join(evidence))


def run_optional_syncs(wiki: Path, runtime: Path, *, no_sync: bool) -> list[Probe]:
    if no_sync:
        return [Probe("sync", "YELLOW", "sync commands skipped by flag")]
    probes: list[Probe] = []
    wiki_sync = wiki / "tools" / "wiki-sync-launch.sh"
    rsync = wiki / "tools" / "wiki-to-runtime-rsync.sh"
    if wiki_sync.exists():
        res = run(["bash", str(wiki_sync)], cwd=wiki, timeout=180)
        status = "GREEN" if res["ok"] else "YELLOW"
        probes.append(Probe("wiki-sync preflight", status, "existing wiki-sync-launch.sh invoked", tail_text(res["stdout"] + res["stderr"], 1000), code=res["returncode"]))
    if rsync.exists():
        res = run(["bash", str(rsync)], cwd=wiki, timeout=180)
        status = "GREEN" if res["ok"] else "RED"
        probes.append(Probe("wiki-to-runtime rsync", status, "existing wiki-to-runtime-rsync.sh invoked", tail_text(res["stdout"] + res["stderr"], 1000), code=res["returncode"]))
    return probes


def status_rank(status: str) -> int:
    return {"GREEN": 0, "YELLOW": 1, "RED": 2}.get(status, 2)


def render_report(now: dt.datetime, probes: list[Probe], root_cause: str) -> str:
    date = now.date().isoformat()
    worst = max((status_rank(p.status) for p in probes), default=2)
    overall = {0: "GREEN", 1: "YELLOW", 2: "RED"}[worst]
    counts = {s: sum(1 for p in probes if p.status == s) for s in ["GREEN", "YELLOW", "RED"]}
    lines = [
        "---",
        "type: dashboard",
        f"id: DAILY-0300-SUBSTRATE-{date}",
        f'title: "Daily 03:00 substrate sync - {date}"',
        f"date: {date}",
        f"captured_at: {now.isoformat()}",
        f"status: {overall.lower()}",
        "tags: [dashboard, daily-0300, substrate, obsidian, gbrain, todoist, notion, openclaw, gstack]",
        "related:",
        '  - "[[skills/session-operating-contract]]"',
        '  - "[[skills/audit]]"',
        '  - "[[tenants/satory/PIPELINE]]"',
        "---",
        "",
        f"# Daily 03:00 substrate sync - {date}",
        "",
        "## Why This Exists",
        "",
        root_cause,
        "",
        "## Overall",
        "",
        f"- Status: `{overall}`",
        f"- Counts: GREEN `{counts['GREEN']}` / YELLOW `{counts['YELLOW']}` / RED `{counts['RED']}`",
        "- Mutation boundary: Todoist and Notion business data are read-only. This job writes only this Obsidian report and uses existing wiki/gbrain sync commands.",
        "",
        "## Component Matrix",
        "",
        "| Component | Status | Summary |",
        "|---|---:|---|",
    ]
    for probe in probes:
        summary = probe.summary.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {probe.component} | `{probe.status}` | {summary} |")
    lines.extend(["", "## Evidence", ""])
    for probe in probes:
        lines.extend([f"### {probe.component}", "", f"- Status: `{probe.status}`", f"- Summary: {probe.summary}"])
        if probe.code is not None:
            lines.append(f"- Exit / HTTP code: `{probe.code}`")
        if probe.remediation:
            lines.append(f"- Remediation: {probe.remediation}")
        if probe.evidence:
            lines.extend(["", "```text", probe.evidence[:3000], "```"])
        lines.append("")
    lines.extend(
        [
            "## Next Atomic Carryovers",
            "",
            "- RED items are the next work queue. Do not start a new plan from zero; repair the top RED, rerun this job, then codify any new root cause into the relevant SKILL.md + gbrain timeline.",
            "- If all components are GREEN/YELLOW, next work is to close the oldest known business carryover from the latest HANDOFF.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(wiki: Path, report: str, now: dt.datetime) -> Path:
    out_dir = wiki / "pages" / "dashboards"
    out_dir.mkdir(parents=True, exist_ok=True)
    date = now.date().isoformat()
    canonical = out_dir / f"daily-0300-substrate-{date}.md"
    if now.hour == 3 and not canonical.exists():
        out_path = canonical
    else:
        stamp = now.strftime("%H%M%S")
        out_path = out_dir / f"daily-0300-substrate-{date}-adhoc-{stamp}.md"
    out_path.write_text(report, encoding="utf-8")
    return out_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--skip-factory-probe", action="store_true")
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="Run probes without writing a dashboard file or invoking sync. Use for ad-hoc audits.",
    )
    parser.add_argument("--no-sync", action="store_true", help="Skip wiki-sync/rsync invocations. Useful for local smoke tests.")
    parser.add_argument("--no-final-sync", action="store_true", help="Write report but do not invoke final wiki-sync.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary to stdout.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.probe_only:
        args.no_sync = True
        args.no_final_sync = True
        args.skip_factory_probe = True

    now = dt.datetime.now(ALMATY)
    root_cause = (
        "Root cause of the stop-pattern: the agent treated a verified checkpoint as a handoff boundary "
        "while the CEO requirement was continuous audit -> repair -> verify until a hard blocker is recorded. "
        "Existing doctrine already covers this in session-operating-contract Rule 17; this job makes the "
        "boundary visible every day at 03:00 Almaty so the substrate cannot silently drift."
    )
    probes: list[Probe] = []
    probes.extend(run_optional_syncs(args.wiki, args.runtime, no_sync=args.no_sync))
    probes.extend(
        [
            probe_air_launchd_schedule(args.wiki),
            probe_wiki_git(args.wiki),
            probe_gbrain(args.wiki),
            probe_gstack(args.wiki),
            probe_openclaw(args.skip_factory_probe, args.runtime),
            probe_litellm(args.runtime),
            probe_telegram(args.runtime),
            probe_todoist(args.wiki, args.runtime),
            probe_notion(args.runtime, args.wiki),
            probe_satory_events(args.runtime),
            probe_gpu(args.runtime),
        ]
    )
    report = render_report(now, probes, root_cause)
    report_path: Path | None = None
    if not args.probe_only:
        report_path = write_report(args.wiki, report, now)
    final_sync: Probe | None = None
    if report_path and not args.no_sync and not args.no_final_sync:
        wiki_sync = args.wiki / "tools" / "wiki-sync-launch.sh"
        if wiki_sync.exists():
            res = run(["bash", str(wiki_sync)], cwd=args.wiki, timeout=180)
            status = "GREEN" if res["ok"] else "YELLOW"
            final_sync = Probe("wiki-sync final", status, f"final sync after report write: {report_path}", tail_text(res["stdout"] + res["stderr"], 1000), code=res["returncode"])
            probes.append(final_sync)
            report = render_report(now, probes, root_cause)
            report_path.write_text(report, encoding="utf-8")
            run(["bash", str(wiki_sync)], cwd=args.wiki, timeout=180)
    payload = {
        "captured_at": now.isoformat(),
        "report_path": str(report_path) if report_path else None,
        "overall_status": max(probes, key=lambda p: status_rank(p.status)).status if probes else "RED",
        "probes": [p.to_dict() for p in probes],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"report={report_path if report_path else 'probe-only-no-write'}")
        print(f"overall={payload['overall_status']}")
        for probe in probes:
            print(f"{probe.status}\t{probe.component}\t{probe.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
