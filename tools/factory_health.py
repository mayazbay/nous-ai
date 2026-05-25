#!/usr/bin/env python3
"""
factory_health.py — Factory health monitor.

Checks every 5 minutes (via launchd/command_center):
  1. Air Docker containers that actually belong on Air are healthy (openclaw)
  2. Air native LiteLLM proxy is alive
  3. Existing local disk mounts stay below DISK_ALERT_PCT

Sends Telegram alert on first failure; re-alerts every COOLDOWN_MINUTES if still down.
State persisted in HEALTH_STATE_PATH so cooldown survives cron restarts.

VPS services such as langfuse, langfuse-db, and ncanode are checked by host-role
audits/daily substrate probes, not by Air's Telegram /health path. This file is
the fast "can the Air factory answer the president?" check.
"""

import json
import logging
import os
import platform
import shutil
import subprocess
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)

KZ_TZ = timezone(timedelta(hours=5))

# Extra .env files to load for keys not in the main nous-agaas .env.
# Air is the current factory host. /opt/litellm/.env is kept as legacy fallback
# for old VPS-era invocations.
_EXTRA_ENV_FILES: list[str] = [
    "/Users/madia/nous-agaas/litellm/.env",
    "/opt/litellm/.env",
]


def _load_extra_envs(paths: list[str] = _EXTRA_ENV_FILES) -> None:
    """
    Parse simple KEY=value .env files and inject missing vars into os.environ.
    Existing env vars are NOT overwritten (main .env takes priority).
    """
    for path_str in paths:
        p = Path(path_str)
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

# ── Configuration ────────────────────────────────────────────────────────────

def _csv_env(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return [part.strip() for part in raw.split(",") if part.strip()]


EXPECTED_CONTAINERS: list[str] = _csv_env("FACTORY_HEALTH_EXPECTED_CONTAINERS", ["openclaw"])
LITELLM_HEALTH_URL = "http://127.0.0.1:4000/health/liveliness"
LITELLM_KEY_ENV = "LITELLM_MASTER_KEY"
DISK_ALERT_PCT = 85                      # alert if any mount exceeds this
DISK_MIN_FREE_GB = float(os.environ.get("FACTORY_HEALTH_MIN_FREE_GB", "20"))
DISK_MOUNTS = _csv_env(
    "FACTORY_HEALTH_DISK_MOUNTS",
    [mount for mount in ["/", "/root"] if Path(mount).exists()],
)                                         # paths to check (deduped by device)
COOLDOWN_MINUTES = 30                    # min time between repeat alerts for same failure
HEALTH_STATE_PATH = Path("/Users/madia/nous-agaas/logs/health_state.json")
BOT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
CHAT_ID_ENV = "TELEGRAM_CHAT_ID"
HTTP_TIMEOUT = 10


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class HealthResult:
    name: str
    ok: bool
    message: str


@dataclass
class HealthReport:
    results: list[HealthResult] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(r.ok for r in self.results)

    @property
    def failed(self) -> list[HealthResult]:
        return [r for r in self.results if not r.ok]

    def format_telegram(self) -> str:
        if self.all_ok:
            return "✅ Factory health OK — all systems nominal."
        lines = ["🚨 <b>Factory Health Alert</b>\n"]
        for r in self.results:
            icon = "✅" if r.ok else "❌"
            lines.append(f"{icon} <b>{r.name}</b>: {r.message}")
        return "\n".join(lines)


# ── Checks ───────────────────────────────────────────────────────────────────

def check_containers(
    expected: list[str] | None = None,
    docker_cmd: list[str] | None = None,
) -> list[HealthResult]:
    """
    Check that each expected container is Up (and healthy where possible).
    Returns one HealthResult per expected container.
    """
    if expected is None:
        expected = EXPECTED_CONTAINERS

    # Parse docker ps output
    cmd = docker_cmd or ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        running: dict[str, str] = {}  # name → status line
        for line in proc.stdout.splitlines():
            parts = line.strip().split("\t", 1)
            if len(parts) == 2:
                running[parts[0]] = parts[1]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        # docker itself is unavailable
        return [
            HealthResult(name=name, ok=False, message=f"docker error: {exc}")
            for name in expected
        ]

    results = []
    for name in expected:
        if name not in running:
            results.append(HealthResult(name=f"docker:{name}", ok=False, message="not running"))
            continue
        status = running[name]
        # Docker status: "Up 11 hours (healthy)" or "Up 11 hours" or "Exited ..."
        up = status.lower().startswith("up")
        unhealthy = "unhealthy" in status.lower()
        if not up:
            results.append(HealthResult(name=f"docker:{name}", ok=False, message=status))
        elif unhealthy:
            results.append(HealthResult(name=f"docker:{name}", ok=False, message=f"unhealthy: {status}"))
        else:
            results.append(HealthResult(name=f"docker:{name}", ok=True, message=status))
    return results


def check_litellm(
    url: str = LITELLM_HEALTH_URL,
    master_key: str | None = None,
) -> HealthResult:
    """
    Check LiteLLM proxy is alive via /health/liveliness.
    Returns ok=True if the proxy responds with HTTP 200.
    """
    if master_key is None:
        master_key = os.environ.get(LITELLM_KEY_ENV, "")

    req = urllib.request.Request(url)
    if master_key:
        req.add_header("Authorization", f"Bearer {master_key}")

    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace").strip().strip('"')
    except urllib.error.HTTPError as exc:
        return HealthResult(name="litellm", ok=False, message=f"HTTP {exc.code}")
    except Exception as exc:
        return HealthResult(name="litellm", ok=False, message=str(exc))

    # /health/liveliness returns: "I'm alive!"
    if "alive" in body.lower():
        return HealthResult(name="litellm", ok=True, message="alive")

    return HealthResult(name="litellm", ok=False, message=f"unexpected response: {body[:60]}")


def check_disk(
    mounts: list[str] | None = None,
    alert_pct: int = DISK_ALERT_PCT,
    min_free_gb: float = DISK_MIN_FREE_GB,
) -> list[HealthResult]:
    """
    Check disk usage on key mounts. Returns one result per unique device.
    """
    if mounts is None:
        mounts = DISK_MOUNTS

    seen_devices: set[str] = set()
    results: list[HealthResult] = []

    for mount in mounts:
        try:
            usage = shutil.disk_usage(mount)
        except OSError as exc:
            results.append(HealthResult(name=f"disk:{mount}", ok=False, message=str(exc)))
            continue

        pct = int(usage.used * 100 / usage.total) if usage.total else 0
        total_gb = usage.total / 1024**3
        used_gb = usage.used / 1024**3
        free_gb = usage.free / 1024**3

        # Skip duplicate devices (e.g. / and /root on same partition)
        device_key = (usage.total, usage.free)
        if device_key in seen_devices:
            continue
        seen_devices.add(device_key)

        if platform.system() == "Darwin":
            # APFS reports shared container usage through shutil, which makes
            # percent-used look much worse than the operator constraint. Free GB
            # is the actionable Air threshold.
            ok = free_gb >= min_free_gb
            msg = f"{free_gb:.1f} GB free ({pct}% raw used, {used_gb:.1f}/{total_gb:.1f} GB)"
        else:
            ok = pct <= alert_pct
            msg = f"{pct}% used ({used_gb:.1f}/{total_gb:.1f} GB)"
        results.append(HealthResult(name=f"disk:{mount}", ok=ok, message=msg))

    return results


# ── Cooldown / state ─────────────────────────────────────────────────────────

def _load_state(path: Path = HEALTH_STATE_PATH) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict, path: Path = HEALTH_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def should_alert(failure_key: str, state: dict, cooldown_minutes: int = COOLDOWN_MINUTES) -> bool:
    """
    Return True if we should send an alert for this failure key.
    True on first failure; True again after COOLDOWN_MINUTES.
    """
    last_alert_str = state.get(failure_key)
    if last_alert_str is None:
        return True
    try:
        last_alert = datetime.fromisoformat(last_alert_str)
        if last_alert.tzinfo is None:
            last_alert = last_alert.replace(tzinfo=KZ_TZ)
        elapsed = datetime.now(KZ_TZ) - last_alert
        return elapsed >= timedelta(minutes=cooldown_minutes)
    except (ValueError, TypeError):
        return True


def record_alert(failure_key: str, state: dict) -> None:
    """Record that an alert was sent now for this failure key."""
    state[failure_key] = datetime.now(KZ_TZ).isoformat()


def clear_resolved(resolved_keys: list[str], state: dict) -> None:
    """Remove resolved failures from state so they alert fresh if they fail again."""
    for key in resolved_keys:
        state.pop(key, None)


# ── Telegram ─────────────────────────────────────────────────────────────────

def send_telegram(text: str, bot_token: str | None = None, chat_id: str | None = None) -> bool:
    # AP-4 gate (session 68p/70, musk-algorithm v1.2.0) — block deference-dressed-as-autonomy
    import os as _os_ap4, subprocess as _sub_ap4
    if not _os_ap4.environ.get("AUTONOMY_BYPASS"):
        _det_ap4 = "/Users/madia/nous-agaas/tools/test_agent_autonomy.sh"
        if _os_ap4.path.exists(_det_ap4):
            try:
                _r_ap4 = _sub_ap4.run(["bash", _det_ap4, "--stdin"], input=text, capture_output=True, text=True, timeout=5)
                if _r_ap4.returncode != 0:
                    print(f"[{__name__}] AP-4 BLOCKED: {text[:100]!r}")
                    return False
            except Exception:
                pass
    """
    Send a Telegram message. Returns True on success.
    Reads BOT_TOKEN and CHAT_ID from env if not provided.
    """
    if bot_token is None:
        bot_token = os.environ.get(BOT_TOKEN_ENV, "")
    if chat_id is None:
        chat_id = os.environ.get(CHAT_ID_ENV, "")
    if not bot_token or not chat_id:
        log.warning("factory_health: BOT_TOKEN or CHAT_ID not set — skipping Telegram alert")
        return False

    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode("utf-8")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT):
            return True
    except Exception as exc:
        log.error("factory_health: Telegram send failed: %s", exc)
        return False


# ── Main ─────────────────────────────────────────────────────────────────────

def run_checks() -> HealthReport:
    """Run all health checks and return a HealthReport."""
    report = HealthReport()
    report.results.extend(check_containers())
    report.results.append(check_litellm())
    report.results.extend(check_disk())
    return report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _load_extra_envs()
    state = _load_state()
    report = run_checks()

    resolved_keys: list[str] = []
    alert_needed = False
    alerted_keys: list[str] = []

    for result in report.results:
        if result.ok:
            # Clear cooldown so next failure re-alerts promptly
            resolved_keys.append(result.name)
        else:
            if should_alert(result.name, state):
                alert_needed = True
                alerted_keys.append(result.name)

    clear_resolved(resolved_keys, state)

    if alert_needed:
        text = report.format_telegram()
        sent = send_telegram(text)
        if sent:
            for key in alerted_keys:
                record_alert(key, state)
            log.info("factory_health: alert sent for: %s", alerted_keys)
        else:
            log.warning("factory_health: alert NOT sent (Telegram unavailable)")
    else:
        if report.all_ok:
            log.info("factory_health: all OK")
        else:
            log.info("factory_health: failures present but in cooldown: %s", [r.name for r in report.failed])

    _save_state(state)

    if not report.all_ok:
        for r in report.failed:
            log.warning("FAIL: %s — %s", r.name, r.message)


if __name__ == "__main__":
    main()
