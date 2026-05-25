#!/usr/bin/env python3
"""On-demand Hermes promotion proof runner.

This script is intentionally conservative: it records proof status and only
edits `ceo-hierarchy/SKILL.md` when all 10 promotion proofs are GREEN.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
import socket
import subprocess
import urllib.error
import urllib.request
from typing import Any, Callable


DEFAULT_WIKI = Path("/Users/madia/nous-agaas/wiki")
PROOF_NAMES = [
    "telegram_route_isolation",
    "litellm_non_interference",
    "todoist_canary_proof",
    "notion_canary_proof",
    "obsidian_wiki_commit_proof",
    "gbrain_timeline_proof",
    "openbrain_capture_projection_proof",
    "cost_receipt",
    "rollback_command",
    "factory_green_24h",
]


def run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 30) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout)
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except Exception as exc:
        return {"ok": False, "returncode": 124, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}


def http_ok(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 300, f"HTTP {response.status}"
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return False, f"HTTP error: {exc}"


def host_is_air_runtime() -> bool:
    hostname = socket.gethostname().lower()
    if "air" in hostname:
        return True
    launchd = run(["launchctl", "list"], timeout=5)
    launchd_text = launchd["stdout"] + launchd["stderr"]
    return "com.nous.telegram-poll" in launchd_text


def proof(name: str, ok: bool, detail: str, evidence: Any | None = None) -> dict[str, Any]:
    return {"name": name, "status": "GREEN" if ok else "RED", "detail": detail, "evidence": evidence or {}}


def collect_proofs(wiki: Path, *, mock_all_green: bool = False) -> list[dict[str, Any]]:
    if mock_all_green:
        return [proof(name, True, "mock green") for name in PROOF_NAMES]
    checks: list[dict[str, Any]] = []
    launchd = run(["launchctl", "list"])
    launchd_text = launchd["stdout"] + launchd["stderr"]
    poller_present = "com.nous.telegram-poll" in launchd_text
    hermes_gateway_absent = "hermes-telegram" not in launchd_text and "com.nous.hermes-agent" not in launchd_text
    checks.append(
        proof(
            "telegram_route_isolation",
            poller_present and hermes_gateway_absent,
            f"telegram_poller_present={poller_present} hermes_gateway_absent={hermes_gateway_absent}",
            {"launchctl_returncode": launchd["returncode"]},
        )
    )
    ok, detail = http_ok("http://127.0.0.1:4000/health/readiness")
    checks.append(proof("litellm_non_interference", ok, detail))
    checks.append(_green_artifact_proof(wiki, "todoist_canary_proof", "pages/audits/HERMES-TODOIST-CANARY", marker="NOUS_HERMES_TODOIST_CANARY_OK"))
    checks.append(_green_artifact_proof(wiki, "notion_canary_proof", "pages/audits/HERMES-NOTION-CANARY", marker="NOUS_HERMES_NOTION_CANARY_OK"))
    git = run(["git", "status", "--porcelain"], cwd=wiki)
    git_clean = git["ok"] and git["stdout"].strip() == ""
    checks.append(proof("obsidian_wiki_commit_proof", git_clean, "wiki worktree clean" if git_clean else "wiki dirty or git status failed", git))
    checks.append(_green_artifact_proof(wiki, "gbrain_timeline_proof", "pages/audits/HERMES-GBRAIN-TIMELINE", marker="NOUS_HERMES_GBRAIN_CANARY_OK"))
    checks.append(_green_artifact_proof(wiki, "openbrain_capture_projection_proof", "pages/audits/HERMES-OPENBRAIN-PROJECTION-CANARY", marker="NOUS_HERMES_OPENBRAIN_PROJECTION_CANARY_OK"))
    checks.append(_green_artifact_proof(wiki, "cost_receipt", "pages/audits/HERMES-COST-RECEIPT", marker="NOUS_HERMES_COST_RECEIPT_CANARY_OK"))
    checks.append(_green_artifact_proof(wiki, "rollback_command", "pages/audits/HERMES-ROLLBACK-CANARY", marker="NOUS_HERMES_ROLLBACK_CANARY_OK"))
    checks.append(_green_artifact_proof(wiki, "factory_green_24h", "pages/audits/HERMES-24H-GATE", marker="NOUS_HERMES_24H_GATE_OK"))
    return checks


def _green_artifact_proof(wiki: Path, name: str, rel_prefix: str, *, marker: str | None = None) -> dict[str, Any]:
    matches = sorted(wiki.glob(rel_prefix + "*"))
    green: list[Path] = []
    rejected: list[Path] = []
    for match in matches:
        if match.is_dir():
            rejected.append(match)
            continue
        try:
            text = match.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            rejected.append(match)
            continue
        status_green = bool(re.search(r"(?im)^status:\s*green\b", text))
        marker_ok = marker is None or marker in text
        if status_green and marker_ok:
            green.append(match)
        else:
            rejected.append(match)
    detail = f"found {len(green)} green artifact(s) for {rel_prefix}; ignored {len(rejected)} non-green/non-matching artifact(s)"
    return proof(
        name,
        bool(green),
        detail,
        {
            "matches": [str(m) for m in green[:5]],
            "ignored": [str(m) for m in rejected[:5]],
            "required_marker": marker,
        },
    )


def all_green(results: list[dict[str, Any]]) -> bool:
    return len(results) == 10 and all(item.get("status") == "GREEN" for item in results)


def maybe_promote_ceo_hierarchy(results: list[dict[str, Any]], skill_path: Path, *, today: str | None = None) -> bool:
    if not all_green(results):
        return False
    text = skill_path.read_text(encoding="utf-8")
    if "AP-25 — Hermes promoted from canary to production" in text:
        return False
    day = today or dt.date.today().isoformat()
    text = text.replace("v1.8.6", "v1.9.0")
    text = text.replace("version: 1.8.6", "version: 1.9.0")
    ap = (
        "\n### AP-25 — Hermes promoted from canary to production (2026-05-17)\n\n"
        "**Rule:** Hermes may become a production participant only after the 10-proof promotion runner passes in full. "
        "The promotion proof must show Telegram isolation, LiteLLM non-interference, Todoist/Notion/wiki/gbrain/OpenBrain/cost receipts, rollback, and factory-green continuity.\n"
    )
    if "## Timeline" in text:
        text = text.replace(
            "## Timeline",
            ap + "\n## Timeline",
            1,
        )
        text = text + f"\n- **{day}** | v1.8.6 -> v1.9.0 -- Added AP-25 after Hermes promotion runner passed 10/10 proofs. gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.\n"
    else:
        text = text + ap + f"\n## Timeline\n\n- **{day}** | v1.8.6 -> v1.9.0 -- Added AP-25 after Hermes promotion runner passed 10/10 proofs. gbrain-timeline-ok: pages/skills/ceo-hierarchy/skill.\n"
    skill_path.write_text(text, encoding="utf-8")
    return True


def write_proof_audit(results: list[dict[str, Any]], output_dir: Path, *, today: str | None = None, promoted: bool = False) -> Path:
    day = today or dt.datetime.now(dt.timezone(dt.timedelta(hours=5))).date().isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"HERMES-PROMOTION-RUNNER-DEPLOY-PROOF-{day}.md"
    overall = "GREEN" if all_green(results) else "RED"
    lines = [
        "---",
        "type: audit",
        f"id: HERMES-PROMOTION-RUNNER-DEPLOY-PROOF-{day}",
        f'title: "Hermes promotion runner deploy proof {day}"',
        f"date: {day}",
        f"status: {overall.lower()}",
        "tags: [audit, hermes, promotion, factory]",
        "---",
        "",
        f"# Hermes promotion runner deploy proof {day}",
        "",
        f"overall: {overall}",
        f"ceo_hierarchy_promoted: {'true' if promoted else 'false'}",
        "",
        "| Proof | Status | Detail |",
        "|---|---|---|",
    ]
    for item in results:
        detail = str(item.get("detail", "")).replace("|", "\\|")
        lines.append(f"| `{item['name']}` | `{item['status']}` | {detail} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--skill-path", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--today")
    parser.add_argument("--mock-all-green", action="store_true")
    parser.add_argument("--promote", action="store_true", help="allow ceo-hierarchy edit if all 10 proofs are green")
    parser.add_argument("--allow-non-air", action="store_true", help="developer/test escape hatch; production promotion truth must run on Air")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.allow_non_air and not args.mock_all_green and not host_is_air_runtime():
        payload = {
            "overall": "RED",
            "promoted": False,
            "audit_path": None,
            "error": "hermes_promotion_runner must run on the Air production runtime; use --allow-non-air only for local tooling tests",
            "proofs": [],
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(payload["error"])
        return 2

    results = collect_proofs(args.wiki, mock_all_green=args.mock_all_green)
    promoted = False
    if args.promote:
        promoted = maybe_promote_ceo_hierarchy(
            results,
            args.skill_path or args.wiki / "pages/skills/ceo-hierarchy/SKILL.md",
            today=args.today,
        )
    audit = write_proof_audit(results, args.output_dir or args.wiki / "pages/audits", today=args.today, promoted=promoted)
    payload = {"overall": "GREEN" if all_green(results) else "RED", "promoted": promoted, "audit_path": str(audit), "proofs": results}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"overall={payload['overall']} promoted={promoted} audit={audit}")
    return 0 if payload["overall"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
