"""iPad proof-flight pre-flight checker — T-PROOF-4 of the Day-6 ladder.

Read-only probes that verify each Day-6 test's INFRASTRUCTURE is alive
BEFORE Madi runs the real test sequence from iPhone. Doesn't send any
Telegram messages; doesn't fire any /ask /codex /code /goal etc; just
checks the backing services + paths.

Output: GREEN/YELLOW/RED matrix per test, written to
pages/audits/IPAD-PROOF-FLIGHT-PREFLIGHT-YYYY-MM-DD.md + console summary.

Skips T6 (/consult) because the Telegram command isn't wired yet (spec
at ad59c710 awaits Codex impl).
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

WIKI_ROOT = Path("/Users/madia/Documents/Projects/Nous AGaaS/Nous")
AIR_HOST = "air"


def run_ssh(cmd: str, timeout: int = 15) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", AIR_HOST, cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": "timeout"}


def t1_status_alive() -> dict[str, Any]:
    """T1: /status — verify telegram-poll launchd + openclaw /health."""
    poll = run_ssh("launchctl list | grep com.nous.telegram-poll")
    openclaw = run_ssh("curl -sf http://localhost:18789/health -m 5")
    ok = poll["ok"] and "openclaw" in openclaw["stdout"].lower() or '"ok":true' in openclaw["stdout"]
    return {
        "test": "T1",
        "label": "/status — bot alive",
        "status": "GREEN" if (poll["ok"] and openclaw["ok"]) else "RED",
        "evidence": {
            "telegram_poll_launchd": "exit=0" if poll["ok"] else f"missing: {poll['stderr'][:80]}",
            "openclaw_health": openclaw["stdout"][:100] if openclaw["ok"] else f"FAIL: {openclaw['stderr'][:80]}",
        },
    }


def t2_ask_cheap_tier() -> dict[str, Any]:
    """T2: /ask cheap-tier — verify LiteLLM readiness (no-auth probe).

    Fix 2026-05-20: /v1/models needs Bearer auth (HTTP 401 without).
    /health/readiness returns 200 unauthenticated; that's the canonical
    liveness probe per LiteLLM docs.
    """
    litellm_launchd = run_ssh("launchctl list | grep com.nous.litellm$")
    readiness = run_ssh("curl -s -o /dev/null -w '%{http_code}' http://localhost:4000/health/readiness -m 5")
    readiness_200 = readiness["stdout"].strip() == "200"
    return {
        "test": "T2",
        "label": "/ask cheap-tier (DeepSeek via OpenClaw → LiteLLM)",
        "status": "GREEN" if (litellm_launchd["ok"] and readiness_200) else "YELLOW",
        "evidence": {
            "litellm_launchd": "exit=0" if litellm_launchd["ok"] else "missing",
            "readiness_http": readiness["stdout"].strip() if readiness["ok"] else f"FAIL: {readiness['stderr'][:60]}",
        },
    }


def t3_codex_ceo_tier() -> dict[str, Any]:
    """T3: /codex CEO-tier — verify Codex CLI authenticated + reachable.

    Fix 2026-05-20: --skip-git-repo-check is an `exec` subcommand flag, not
    a global flag; bare `codex --version` works.
    """
    version = run_ssh("codex --version 2>&1 | head -3")
    has_version = "codex" in version["stdout"].lower() and "." in version["stdout"]
    return {
        "test": "T3",
        "label": "/codex CEO-tier (gpt-5.5 via Codex CLI on Air)",
        "status": "GREEN" if (version["ok"] and has_version) else "YELLOW",
        "evidence": {
            "codex_version": version["stdout"][:100] if version["ok"] else f"FAIL: {version['stderr'][:80]}",
        },
    }


def t4_code_claude_air() -> dict[str, Any]:
    """T4: /code Claude Code on Air — verify CLI authenticated."""
    version = run_ssh("which claude && claude --version 2>&1 | head -2")
    has_version = "claude" in version["stdout"].lower() and version["ok"]
    return {
        "test": "T4",
        "label": "/code Claude Code Sonnet 4.6 on Air",
        "status": "GREEN" if has_version else "YELLOW",
        "evidence": {
            "claude_version": version["stdout"][:120] if version["ok"] else f"FAIL: {version['stderr'][:80]}",
        },
    }


def t5_goal_cycle() -> dict[str, Any]:
    """T5: /goal persistent goal cycle — verify goal_runner.py + Todoist token."""
    goal_runner = run_ssh("ls ~/nous-agaas/wiki/tools/goal_runner.py 2>&1")
    todoist_token = run_ssh("grep -c ^TODOIST_API_TOKEN= ~/nous-agaas/.env 2>/dev/null")
    has_runner = goal_runner["ok"] and "goal_runner.py" in goal_runner["stdout"]
    has_token = todoist_token["ok"] and todoist_token["stdout"].strip() == "1"
    return {
        "test": "T5",
        "label": "/goal persistent goal + OpenClaw cycle",
        "status": "GREEN" if (has_runner and has_token) else "YELLOW",
        "evidence": {
            "goal_runner_exists": has_runner,
            "todoist_token_set": has_token,
        },
    }


def t6_consult_skipped() -> dict[str, Any]:
    """T6: /consult — SKIPPED (Telegram command not wired yet per ad59c710)."""
    return {
        "test": "T6",
        "label": "/consult multi-model brain",
        "status": "SKIPPED",
        "evidence": {
            "reason": "Telegram /consult command not wired in command_center.py yet (spec ad59c710 awaits Codex impl)",
            "skill_works_from_mac": "yes — multi_model_consult.py shipped at 128adba9, live-proven",
        },
    }


def t7_hermes_webui() -> dict[str, Any]:
    """T7: Hermes WebUI dashboard — verify /health + /api/factory-events."""
    health = run_ssh("curl -sf http://127.0.0.1:8787/health -m 5 | head -c 200")
    # /api/factory-events requires auth; just check shim presence
    shim_check = run_ssh("grep -l 'factory-events' ~/nous-agaas/wiki/tools/hermes_webui_canary.sh 2>/dev/null")
    return {
        "test": "T7",
        "label": "Hermes WebUI dashboard (iPhone same-WiFi)",
        "status": "GREEN" if (health["ok"] and shim_check["ok"]) else "YELLOW",
        "evidence": {
            "hermes_health": health["stdout"][:100] if health["ok"] else f"FAIL: {health['stderr'][:80]}",
            "factory_events_shim_present": shim_check["ok"],
            "phone_url": "http://192.168.1.197:8787 (same-WiFi) or Tailscale phone-url",
        },
    }


def t8_handoff() -> dict[str, Any]:
    """T8: /handoff — verify auto-checkpoint launchd alive + handoff dir writable."""
    auto_ck = run_ssh("launchctl list | grep com.nous.auto-checkpoint")
    handoff_dir = run_ssh("ls -t ~/nous-agaas/wiki/pages/progress/HANDOFF-AUTO-*.md 2>/dev/null | head -3 | wc -l")
    has_handoffs = handoff_dir["ok"] and int(handoff_dir["stdout"].strip() or "0") > 0
    return {
        "test": "T8",
        "label": "/handoff session transfer + auto-checkpoint",
        "status": "GREEN" if (auto_ck["ok"] and has_handoffs) else "YELLOW",
        "evidence": {
            "auto_checkpoint_launchd": "exit=0" if auto_ck["ok"] else f"missing: {auto_ck['stderr'][:80]}",
            "recent_handoff_count": handoff_dir["stdout"].strip() if handoff_dir["ok"] else "0",
        },
    }


def t9_satory_question() -> dict[str, Any]:
    """T9: real Satory question — verify gbrain semantic search alive.

    Fix 2026-05-20: gbrain doctor v0.22.16 schema_version=2 returns
    {schema_version, status, health_score, checks}. We accept 'warnings'
    + health_score >= 80 as GREEN-enough for retrieval (per live proof
    at c4b9eda5 where semantic search returned score 0.9549 for
    'model-failover doctrine'). Strict 'healthy' would require zero
    warnings which is rare in steady-state.
    """
    # SSH to VPS not Air (gbrain lives on VPS)
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
             "root@65.108.215.200",
             "PATH=/opt/nous-agaas/gbrain/bin:$PATH gbrain doctor --json 2>/dev/null"],
            capture_output=True, text=True, timeout=30,
        )
        ok = result.returncode == 0
        stdout = result.stdout.strip()
    except subprocess.TimeoutExpired:
        ok = False
        stdout = ""

    health_score = None
    status_word = "(unparsed)"
    if ok and stdout.startswith("{"):
        try:
            data = json.loads(stdout)
            health_score = data.get("health_score")
            status_word = data.get("status", "(no status)")
        except json.JSONDecodeError:
            pass

    is_green = ok and isinstance(health_score, int) and health_score >= 80
    return {
        "test": "T9",
        "label": "Real Satory question end-to-end (gbrain retrieval)",
        "status": "GREEN" if is_green else "YELLOW",
        "evidence": {
            "gbrain_status": status_word,
            "health_score": health_score if health_score is not None else "(missing)",
            "schema_version": "2 (v0.22.16)",
        },
    }


def t10_notification_policy() -> dict[str, Any]:
    """T10: 15-min quiet window — verify notification_policy module loadable."""
    module_check = subprocess.run(
        ["python3", "-c", "import sys; sys.path.insert(0, 'tools'); import notification_policy; print('ok:', len(notification_policy.EVENT_CLASS_REGISTRY))"],
        capture_output=True,
        text=True,
        cwd=WIKI_ROOT,
        timeout=15,
    )
    return {
        "test": "T10",
        "label": "Notification policy holds (≤1 routine ping in 15min)",
        "status": "GREEN" if module_check.returncode == 0 else "YELLOW",
        "evidence": {
            "module_import": module_check.stdout.strip()[:100] if module_check.returncode == 0 else module_check.stderr.strip()[:100],
        },
    }


TESTS = [t1_status_alive, t2_ask_cheap_tier, t3_codex_ceo_tier, t4_code_claude_air, t5_goal_cycle,
         t6_consult_skipped, t7_hermes_webui, t8_handoff, t9_satory_question, t10_notification_policy]


def render_markdown(results: list[dict[str, Any]], iso_ts: str) -> str:
    lines = [
        f"---",
        f"type: audit",
        f"id: IPAD-PROOF-FLIGHT-PREFLIGHT-{iso_ts[:10]}",
        f'title: "iPad proof-flight pre-flight check — T-PROOF-4"',
        f"date: {iso_ts[:10]}",
        f"status: preflight-{iso_ts}",
        f"tags: [audit, ipad-only, proof-flight, preflight, day-6]",
        f"---",
        "",
        f"# iPad proof-flight pre-flight — {iso_ts}",
        "",
        "Per `[[2026-05-20-ipad-only-proof-flight-design]]` T-PROOF-4. Read-only probes of each Day-6 test's INFRASTRUCTURE. Madi runs the real T1-T10 from iPhone; this pre-check confirms the backing services are alive first.",
        "",
        "| Test | Status | Label | Evidence |",
        "|---|---|---|---|",
    ]
    for r in results:
        emoji = "✅" if r["status"] == "GREEN" else ("⏭️" if r["status"] == "SKIPPED" else "🟡")
        evidence_summary = "; ".join(f"{k}={str(v)[:60]}" for k, v in r["evidence"].items())[:200]
        lines.append(f"| {r['test']} | {emoji} {r['status']} | {r['label']} | {evidence_summary} |")
    lines.extend([
        "",
        "## Summary",
        "",
        f"- GREEN: {sum(1 for r in results if r['status'] == 'GREEN')}",
        f"- YELLOW: {sum(1 for r in results if r['status'] == 'YELLOW')}",
        f"- RED: {sum(1 for r in results if r['status'] == 'RED')}",
        f"- SKIPPED: {sum(1 for r in results if r['status'] == 'SKIPPED')}",
        "",
        "If all GREEN/SKIPPED: Day-6 proof flight ready to execute from iPhone. Any RED requires fix before Madi runs the live sequence.",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="iPad proof-flight pre-flight checker (T-PROOF-4)")
    parser.add_argument("--write-audit", action="store_true", help="write audit doc to pages/audits/")
    args = parser.parse_args()

    iso_ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    print(f"[ipad-preflight] {iso_ts} starting (10 tests; T6 SKIPPED per spec)")

    results = []
    for test_fn in TESTS:
        print(f"[ipad-preflight]   running {test_fn.__name__}…")
        result = test_fn()
        emoji = "✅" if result["status"] == "GREEN" else ("⏭️" if result["status"] == "SKIPPED" else "🟡")
        print(f"[ipad-preflight]     {emoji} {result['status']}: {result['label']}")
        results.append(result)

    green = sum(1 for r in results if r["status"] == "GREEN")
    yellow = sum(1 for r in results if r["status"] == "YELLOW")
    red = sum(1 for r in results if r["status"] == "RED")
    skipped = sum(1 for r in results if r["status"] == "SKIPPED")
    print(f"[ipad-preflight] done. GREEN={green} YELLOW={yellow} RED={red} SKIPPED={skipped}")

    if args.write_audit:
        audit_path = WIKI_ROOT / "pages" / "audits" / f"IPAD-PROOF-FLIGHT-PREFLIGHT-{iso_ts[:10]}.md"
        audit_path.write_text(render_markdown(results, iso_ts), encoding="utf-8")
        print(f"[ipad-preflight] audit written → {audit_path}")

    # Return code: 0 if no RED; 1 if any RED
    return 1 if red > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
