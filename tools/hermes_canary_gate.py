#!/usr/bin/env python3
"""Hermes isolated-canary gate.

This gate proves the approved hybrid shape:

- OpenClaw remains the production Telegram/runtime path.
- Hermes Agent is present only as an isolated canary profile.
- Hermes gateway is stopped and Telegram is not configured there.
- Optional smoke can run one explicit canary turn through the isolated profile.

It is intentionally read-mostly. The optional smoke spends one canary model call.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import shutil
import subprocess
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_WIKI = Path("/Users/madia/nous-agaas/wiki")
DEFAULT_ALIAS = "hermes-nouscanary"
DEFAULT_PROFILE = "nouscanary"
DEFAULT_OPENCLAW_HEALTH = "http://127.0.0.1:18789/health"
DEFAULT_LITELLM_HEALTH = "http://127.0.0.1:4000/health/readiness"
DEFAULT_WEBUI_HEALTH = "http://127.0.0.1:8787/health"
DEFAULT_WEBUI_EVENTS = "http://127.0.0.1:8787/api/factory-events?limit=1"
DEFAULT_WEBUI_ENV_FILE = Path("/Users/madia/nous-agaas/secrets/hermes-webui.env")


def run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 60) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "cmd": " ".join(cmd),
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": " ".join(cmd),
            "ok": False,
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or f"timeout after {timeout}s",
        }
    except FileNotFoundError as exc:
        return {
            "cmd": " ".join(cmd),
            "ok": False,
            "returncode": 127,
            "stdout": "",
            "stderr": f"missing executable: {exc.filename}",
        }


def http_status(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(160).decode("utf-8", errors="replace")
            return 200 <= response.status < 300, f"HTTP {response.status}: {body}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"HTTP error: {exc}"


def _read_env_value(path: Path, key: str) -> str:
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() == key:
                return value.strip().strip("'\"")
    except OSError:
        return ""
    return ""


def _origin(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"invalid URL: {url}")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def webui_factory_events_status(events_url: str, env_file: Path, timeout: float = 5.0) -> tuple[bool, str]:
    password = _read_env_value(env_file, "HERMES_WEBUI_PASSWORD")
    if not password:
        return False, f"missing HERMES_WEBUI_PASSWORD in {env_file}"

    login_url = _origin(events_url) + "/api/auth/login"
    cookies = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
    login_body = json.dumps({"password": password}).encode("utf-8")
    login_req = urllib.request.Request(
        login_url,
        data=login_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener.open(login_req, timeout=timeout) as response:
            login_payload = response.read(200).decode("utf-8", errors="replace")
            if not 200 <= response.status < 300:
                return False, f"login HTTP {response.status}: {login_payload}"

        with opener.open(events_url, timeout=timeout) as response:
            body = response.read(8192).decode("utf-8", errors="replace")
            if not 200 <= response.status < 300:
                return False, f"events HTTP {response.status}: {body[:200]}"
    except urllib.error.HTTPError as exc:
        body = exc.read(240).decode("utf-8", errors="replace")
        return False, f"HTTP {exc.code}: {body}"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return False, f"HTTP error: {exc}"

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        return False, f"events response is not JSON: {exc}"

    events = payload.get("events")
    sources = payload.get("sources")
    queue_status = payload.get("queue_status")
    ok = payload.get("ok") is True and isinstance(events, list) and isinstance(sources, list) and isinstance(queue_status, dict)
    detail = (
        f"login HTTP 200; events ok={payload.get('ok')} "
        f"events={len(events) if isinstance(events, list) else 'n/a'} "
        f"sources={len(sources) if isinstance(sources, list) else 'n/a'} "
        f"queue_exists={queue_status.get('exists') if isinstance(queue_status, dict) else 'n/a'}"
    )
    return ok, detail


def check(name: str, ok: bool, detail: str, evidence: Any | None = None) -> dict[str, Any]:
    return {
        "check": name,
        "status": "GREEN" if ok else "RED",
        "detail": detail,
        "evidence": evidence,
    }


def contains_all(text: str, needles: list[str]) -> bool:
    return all(needle in text for needle in needles)


def canary_gateway_is_not_loaded(status_text: str) -> bool:
    telegram_off = "Telegram      ✗ not configured" in status_text
    gateway_off = "Status:       ✗ not loaded" in status_text or "Status:       ✗ stopped" in status_text
    return telegram_off and gateway_off


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    ok, detail = http_status(args.openclaw_health_url)
    checks.append(check("openclaw_production_health", ok, detail))

    ok, detail = http_status(args.litellm_health_url)
    checks.append(check("litellm_production_health", ok, detail))

    poller = run(["launchctl", "list"], timeout=20)
    poller_text = poller["stdout"] + poller["stderr"]
    checks.append(
        check(
            "telegram_poller_production_loaded",
            poller["ok"] and "com.nous.telegram-poll" in poller_text,
            "com.nous.telegram-poll present in launchctl list" if "com.nous.telegram-poll" in poller_text else "telegram poller not found",
            {"returncode": poller["returncode"]},
        )
    )

    alias_path = shutil.which(args.alias)
    checks.append(
        check(
            "hermes_canary_alias",
            bool(alias_path),
            alias_path or f"{args.alias} not found",
        )
    )

    codex_path = shutil.which(args.codex_cli)
    checks.append(
        check(
            "codex_cli_available",
            bool(codex_path),
            codex_path or f"{args.codex_cli} not found in PATH",
        )
    )

    profile = run(["hermes", "profile", "show", args.profile], timeout=30)
    profile_text = profile["stdout"] + profile["stderr"]
    checks.append(
        check(
            "hermes_canary_profile_isolated",
            profile["ok"] and contains_all(profile_text, [f"Profile: {args.profile}", "Gateway: stopped", ".env:    exists"]),
            "profile exists with stopped gateway" if profile["ok"] else profile_text[-500:],
            profile_text,
        )
    )

    canary_status = run([args.alias, "status"], timeout=45)
    canary_status_text = canary_status["stdout"] + canary_status["stderr"]
    checks.append(
        check(
            "hermes_canary_route_config",
            canary_status["ok"] and contains_all(canary_status_text, ["Model:        gpt-5.5", "Provider:     OpenAI Codex"]),
            "canary uses gpt-5.5 via OpenAI Codex" if canary_status["ok"] else canary_status_text[-500:],
        )
    )
    checks.append(
        check(
            "hermes_gateway_not_production",
            canary_status["ok"] and canary_gateway_is_not_loaded(canary_status_text),
            "Hermes Telegram gateway not configured/loaded" if canary_status["ok"] else canary_status_text[-500:],
        )
    )

    if args.factory_probe:
        probe = run(["bash", "tools/factory_no_drift_probe.sh", "--quiet", "--json"], cwd=args.wiki, timeout=180)
        probe_ok = False
        probe_detail = (probe["stdout"] or probe["stderr"])[-1000:]
        try:
            payload = json.loads(probe["stdout"])
            probe_ok = payload.get("overall") == "GREEN" and int(payload.get("reds") or 0) == 0
            probe_detail = f"overall={payload.get('overall')} reds={payload.get('reds')}"
        except (json.JSONDecodeError, TypeError, ValueError):
            probe_ok = probe["ok"] and "GREEN" in probe_detail
        checks.append(check("factory_no_drift_probe", probe_ok, probe_detail))

    if args.webui_probe:
        ok, detail = http_status(args.webui_health_url)
        checks.append(check("hermes_webui_canary_health", ok, detail))
        ok, detail = webui_factory_events_status(args.webui_events_url, args.webui_env_file)
        checks.append(check("hermes_webui_factory_events_auth", ok, detail))

    if args.smoke:
        smoke = run(
            [
                args.alias,
                "chat",
                "-Q",
                "--max-turns",
                "1",
                "-q",
                "Reply exactly HERMES_CANARY_GATE_OK and nothing else.",
            ],
            timeout=args.smoke_timeout,
        )
        smoke_text = smoke["stdout"] + smoke["stderr"]
        checks.append(
            check(
                "hermes_canary_smoke",
                smoke["ok"] and "HERMES_CANARY_GATE_OK" in smoke_text,
                smoke_text[-1000:],
                {"returncode": smoke["returncode"]},
            )
        )

    reds = [item for item in checks if item["status"] == "RED"]
    return {
        "overall": "GREEN" if not reds else "RED",
        "reds": len(reds),
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--alias", default=DEFAULT_ALIAS)
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--codex-cli", default="codex")
    parser.add_argument("--openclaw-health-url", default=DEFAULT_OPENCLAW_HEALTH)
    parser.add_argument("--litellm-health-url", default=DEFAULT_LITELLM_HEALTH)
    parser.add_argument("--webui-health-url", default=DEFAULT_WEBUI_HEALTH)
    parser.add_argument("--webui-events-url", default=DEFAULT_WEBUI_EVENTS)
    parser.add_argument("--webui-env-file", type=Path, default=DEFAULT_WEBUI_ENV_FILE)
    parser.add_argument("--factory-probe", action="store_true")
    parser.add_argument("--webui-probe", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="spend one explicit Hermes canary model call")
    parser.add_argument("--smoke-timeout", type=int, default=180)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = evaluate(args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"hermes_canary={result['overall']} reds={result['reds']}")
        for item in result["checks"]:
            print(f"{item['status']} {item['check']}: {item['detail']}")
    return 0 if result["overall"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
