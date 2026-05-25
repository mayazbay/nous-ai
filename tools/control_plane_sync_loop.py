#!/usr/bin/env python3
"""Control-plane sync loop for Nous AGaaS.

Every cycle reconciles the operational control plane:
- Notion Satory rows -> Obsidian tenant artifacts
- Todoist global hygiene hard gates
- Todoist task register -> Obsidian/gbrain/CSV read model
- daily substrate probes, factory no-drift, LangSmith observer
- scoped git push to VPS bare and GitHub mirror

The loop is deterministic-first. It does not ask an LLM to decide API hygiene,
retry policy, or routing. LLM/factory work receives only explicit blockers and
next slices through the durable vault.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ALMATY = dt.timezone(dt.timedelta(hours=5))
DEFAULT_WIKI = Path("/Users/madia/nous-agaas/wiki")
DEFAULT_RUNTIME = Path("/Users/madia/nous-agaas")
DEFAULT_PYTHON = Path("/Library/Frameworks/Python.framework/Versions/3.11/bin/python3")
LOCK_FILE = Path("/Users/madia/nous-agaas/logs/control-plane-sync.lock")
JSONL_LOG = Path("/Users/madia/nous-agaas/logs/control-plane-sync.jsonl")
STATUS_PAGE = Path("pages/systems/control-plane-sync-status.md")
TODOIST_REGISTER_MD = Path("pages/systems/todoist-control-plane-register.md")
TODOIST_REGISTER_JSON = Path("pages/systems/todoist-control-plane-register.json")
TODOIST_REGISTER_CSV = Path("pages/exports/todoist-control-plane-register.csv")
TODOIST_CONTEXT_QUEUE = Path("pages/systems/todoist-context-enrichment-queue.md")
SATORY_DEEP_AUDIT_JSON = Path("pages/systems/satory-todoist-deep-audit.json")
SATORY_DEEP_AUDIT_INDEX = Path("pages/systems/satory-todoist-deep-audit-index.md")
RUSSIAN_DOCS_CHECK = Path("tools/check_russian_control_plane_docs.py")
AUDIT_DIR = Path("pages/audits")
MODEL_BAKEOFF_GLOB = "model-bakeoff-*.json"
CANONICAL_REMOTE_ENV = "NOUS_CANONICAL_REMOTE"
CANONICAL_REMOTE_CANDIDATES = ("origin", "vps", "bare")


class LoopError(RuntimeError):
    pass


def now_kzt() -> dt.datetime:
    return dt.datetime.now(ALMATY)


def iso_now() -> str:
    return now_kzt().isoformat()


def status_rank(status: str) -> int:
    return {"blocked": 4, "not_done": 3, "working": 2, "in_progress": 1, "done": 0, "skipped": 0, "skipped_preflight": 0}.get(status, 5)


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [str(part) for part in cmd],
            cwd=str(cwd) if cwd else None,
            env=merged,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "cmd": " ".join(str(part) for part in cmd),
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "ok": proc.returncode == 0,
            "duration_ms": int((time.monotonic() - start) * 1000),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": " ".join(str(part) for part in cmd),
            "returncode": 124,
            "stdout": (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "") if isinstance(exc.stderr, str) else f"timeout after {timeout}s",
            "ok": False,
            "duration_ms": int((time.monotonic() - start) * 1000),
        }


def tail(text: str, limit: int = 1800) -> str:
    clean = str(text or "").strip()
    return clean if len(clean) <= limit else clean[-limit:]


def git_short(wiki: Path, ref: str = "HEAD") -> str:
    result = run(["git", "rev-parse", "--short", ref], cwd=wiki, timeout=30)
    return result["stdout"].strip() if result["ok"] else "git-fail"


def fetch_remote_main_oid(wiki: Path, remote: str, timeout: int = 120) -> tuple[str | None, dict[str, Any]]:
    """Fetch one main ref and return the exact OID to rebase onto.

    Do not use `git pull` in unattended paths. In Air's multi-writer wiki,
    `pull` can resolve FETCH_HEAD/branch config to an invalid rebase target.
    """
    fetch = run(["git", "fetch", remote, f"main:refs/remotes/{remote}/main"], cwd=wiki, timeout=timeout)
    if not fetch["ok"]:
        return None, fetch
    rev = run(["git", "rev-parse", "--verify", f"refs/remotes/{remote}/main"], cwd=wiki, timeout=30)
    if not rev["ok"]:
        return None, rev
    return rev["stdout"].strip(), fetch


def remote_exists(wiki: Path, remote: str) -> bool:
    return run(["git", "remote", "get-url", remote], cwd=wiki, timeout=30)["ok"]


def resolve_canonical_remote(wiki: Path) -> str:
    configured = os.environ.get(CANONICAL_REMOTE_ENV)
    if configured:
        return configured
    for remote in CANONICAL_REMOTE_CANDIDATES:
        if remote_exists(wiki, remote):
            return remote
    return "origin"


def rebase_onto_remote_main(wiki: Path, remote: str = "origin", timeout: int = 180) -> dict[str, Any]:
    before = git_short(wiki)
    target, fetch = fetch_remote_main_oid(wiki, remote, timeout=timeout)
    if not target:
        fetch["summary"] = f"fetch {remote}/main failed"
        return fetch

    contains = run(["git", "merge-base", "--is-ancestor", target, "HEAD"], cwd=wiki, timeout=30)
    if contains["ok"]:
        after = git_short(wiki)
        return {
            "cmd": f"fetch {remote} main:refs/remotes/{remote}/main",
            "returncode": 0,
            "stdout": f"already contains {remote}/main {before}->{after}",
            "stderr": fetch["stderr"],
            "ok": True,
            "duration_ms": fetch.get("duration_ms", 0),
        }

    rebase = run(["git", "-c", "core.hooksPath=/dev/null", "rebase", target], cwd=wiki, timeout=timeout)
    target2, fetch2 = fetch_remote_main_oid(wiki, remote, timeout=timeout)
    if rebase["ok"] and target2 and target2 != target:
        contains2 = run(["git", "merge-base", "--is-ancestor", target2, "HEAD"], cwd=wiki, timeout=30)
        if not contains2["ok"]:
            rebase2 = run(["git", "-c", "core.hooksPath=/dev/null", "rebase", target2], cwd=wiki, timeout=timeout)
            rebase["ok"] = rebase2["ok"]
            rebase["returncode"] = rebase2["returncode"]
            rebase["stdout"] = f"{rebase['stdout']}\n{rebase2['stdout']}"
            rebase["stderr"] = f"{rebase['stderr']}\n{rebase2['stderr']}"
    after = git_short(wiki)
    rebase["stdout"] = f"{rebase['stdout']}\nexact_rebase {remote}/main {before}->{after}".strip()
    rebase["stderr"] = f"{fetch['stderr']}\n{fetch2.get('stderr', '')}\n{rebase['stderr']}".strip()
    return rebase


def parse_json_result(result: dict[str, Any]) -> Any:
    if not result["ok"]:
        raise LoopError(tail(result["stdout"] + result["stderr"]))
    text = str(result["stdout"] or "").lstrip()
    decoder = json.JSONDecoder()
    payload, _ = decoder.raw_decode(text)
    return payload


def recorded_step(name: str, status: str, summary: str, evidence: Any = None) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "summary": summary,
        "evidence": evidence,
        "updated_at": iso_now(),
    }


@contextlib.contextmanager
def loop_lock(max_age_seconds: int = 7200):
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        text = LOCK_FILE.read_text(encoding="utf-8", errors="replace")
        pid_match = re.search(r"pid=(\d+)", text)
        pid_alive = False
        if pid_match:
            pid_alive = run(["kill", "-0", pid_match.group(1)], timeout=5)["ok"]
        age = time.time() - LOCK_FILE.stat().st_mtime
        if pid_alive and age < max_age_seconds:
            raise LoopError(f"control-plane sync already running ({text.strip()})")
        LOCK_FILE.unlink(missing_ok=True)
    LOCK_FILE.write_text(f"pid={os.getpid()} ts={iso_now()}\n", encoding="utf-8")
    try:
        yield
    finally:
        LOCK_FILE.unlink(missing_ok=True)


def git_clean_or_block(wiki: Path) -> dict[str, Any]:
    status = run(["git", "status", "--porcelain"], cwd=wiki, timeout=30)
    if not status["ok"]:
        return recorded_step("git_preflight", "blocked", "git status failed", tail(status["stderr"]))
    dirty = [line for line in status["stdout"].splitlines() if line.strip()]
    if dirty:
        return recorded_step("git_preflight", "blocked", f"dirty tree before sync ({len(dirty)} paths)", dirty[:40])
    canonical_remote = resolve_canonical_remote(wiki)
    rebase = rebase_onto_remote_main(wiki, canonical_remote, timeout=180)
    if not rebase["ok"]:
        return recorded_step("git_preflight", "blocked", f"exact {canonical_remote}/main rebase failed", tail(rebase["stdout"] + rebase["stderr"]))
    return recorded_step("git_preflight", "done", f"wiki clean and rebased from exact {canonical_remote}/main", tail(rebase["stdout"] + rebase["stderr"], 800))


def run_notion_sync(wiki: Path, python: Path, dry_run: bool) -> dict[str, Any]:
    cmd = [str(python), "-m", "tenants.satory.agents.notion_to_gbrain", "--json"]
    if dry_run:
        cmd.append("--dry-run")
    result = run(cmd, cwd=wiki, timeout=240, env={"PYTHONPATH": str(wiki)})
    try:
        payload = parse_json_result(result)
    except Exception as exc:
        return recorded_step("notion_sync", "blocked", f"Notion mirror failed: {exc}", tail(result["stdout"] + result["stderr"]))
    changes = sum(int(row.get("changes") or 0) for row in payload if isinstance(row, dict))
    artifacts = sum(int(row.get("artifact_count") or 0) for row in payload if isinstance(row, dict))
    status = "skipped" if dry_run else "done"
    return recorded_step("notion_sync", status, f"changes={changes} artifacts={artifacts} dry_run={dry_run}", payload)


def run_todoist_hygiene(wiki: Path, python: Path, dry_run: bool, apply_hard_gates: bool) -> dict[str, Any]:
    base = [str(python), "tools/todoist_control_plane_audit.py", "--env-file", "/Users/madia/nous-agaas/.env", "--json"]
    audit_before = run(base, cwd=wiki, timeout=360)
    try:
        before = parse_json_result(audit_before)
    except Exception as exc:
        return recorded_step("todoist_control_plane", "blocked", f"Todoist audit failed: {exc}", tail(audit_before["stdout"] + audit_before["stderr"]))

    plan = before.get("plan") or []
    applied: Any = None
    if plan and apply_hard_gates and not dry_run:
        apply_result = run(base + ["--apply"], cwd=wiki, timeout=480)
        try:
            after = parse_json_result(apply_result)
        except Exception as exc:
            return recorded_step("todoist_control_plane", "blocked", f"Todoist apply failed: {exc}", tail(apply_result["stdout"] + apply_result["stderr"]))
        applied = after.get("applied")
        audit = after.get("audit", {})
    else:
        audit = before.get("audit", {})

    risks = audit.get("risk_counts", {})
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
    hard_total = sum(int(risks.get(key) or 0) for key in hard_keys)
    status = "done" if hard_total == 0 else ("not_done" if dry_run or not apply_hard_gates else "blocked")
    summary = (
        f"active={audit.get('counts', {}).get('active_tasks')} hard_gates={hard_total} "
        f"contextless={risks.get('no_description_or_note')} plan={len(plan)} applied={applied or {}}"
    )
    return recorded_step("todoist_control_plane", status, summary, {"risk_counts": risks, "applied": applied, "plan_count": len(plan)})


def run_todoist_register_export(wiki: Path, python: Path, dry_run: bool) -> dict[str, Any]:
    cmd = [
        str(python),
        "tools/todoist_control_plane_export.py",
        "--env-file",
        "/Users/madia/nous-agaas/.env",
        "--json",
    ]
    if dry_run:
        cmd.append("--dry-run")
    result = run(cmd, cwd=wiki, timeout=420)
    try:
        payload = parse_json_result(result)
    except Exception as exc:
        return recorded_step(
            "todoist_register_export",
            "blocked",
            f"Todoist register export failed: {exc}",
            tail(result["stdout"] + result["stderr"]),
        )
    counts = payload.get("counts", {})
    status = "skipped" if dry_run else str(payload.get("status") or "not_done")
    if payload.get("completed_error") and status == "done":
        status = "not_done"
    summary = (
        f"active={counts.get('active_tasks')} recent_done={counts.get('recent_completed_tasks')} "
        f"contextless={counts.get('contextless_active_tasks')} wrote={payload.get('wrote')}"
    )
    if payload.get("completed_error"):
        summary += " completed_api=blocked"
    return recorded_step("todoist_register_export", status, summary, payload)


def run_satory_todoist_deep_audit(wiki: Path, python: Path, dry_run: bool, cycle_id: str) -> dict[str, Any]:
    markdown_path = AUDIT_DIR / f"AUDIT-satory-todoist-deep-{cycle_id}.md"
    cmd = [
        str(python),
        "tools/satory_todoist_deep_audit.py",
        "--env-file",
        "/Users/madia/nous-agaas/.env",
        "--json-out",
        str(SATORY_DEEP_AUDIT_JSON),
        "--markdown",
        str(markdown_path),
        "--index",
        str(SATORY_DEEP_AUDIT_INDEX),
        "--json",
    ]
    if dry_run:
        cmd.append("--dry-run")
    result = run(cmd, cwd=wiki, timeout=420)
    try:
        payload = parse_json_result(result)
    except Exception as exc:
        return recorded_step(
            "satory_todoist_deep_audit",
            "blocked",
            f"Satory Todoist deep audit failed: {exc}",
            tail(result["stdout"] + result["stderr"]),
        )
    counts = payload.get("counts", {})
    proof = payload.get("proof_counts", {})
    status = str(payload.get("status") or "not_done")
    summary = (
        f"tasks={counts.get('active_tasks')} comments={counts.get('comments')} "
        f"contextless={counts.get('contextless_tasks')} close_ready={proof.get('close_ready')} "
        f"hard_gates={counts.get('hard_gate_risk_total')} wrote={payload.get('wrote')}"
    )
    return recorded_step("satory_todoist_deep_audit", status, summary, payload)


def run_russian_docs_gate(wiki: Path, python: Path) -> dict[str, Any]:
    result = run([str(python), str(RUSSIAN_DOCS_CHECK), "--wiki", str(wiki), "--json"], cwd=wiki, timeout=60)
    try:
        payload = parse_json_result(result)
    except Exception as exc:
        return recorded_step(
            "russian_docs_gate",
            "blocked",
            f"Russian docs gate failed: {exc}",
            tail(result["stdout"] + result["stderr"]),
        )
    status = "done" if payload.get("status") == "done" else "blocked"
    failures = int(payload.get("failures") or 0)
    return recorded_step("russian_docs_gate", status, f"failures={failures}", payload)


def run_substrate_probe(wiki: Path, python: Path) -> dict[str, Any]:
    result = run(
        [
            str(python),
            "tools/daily_0300_substrate_sync.py",
            "--probe-only",
            "--no-sync",
            "--skip-factory-probe",
            "--json",
        ],
        cwd=wiki,
        timeout=240,
    )
    try:
        payload = parse_json_result(result)
    except Exception as exc:
        return recorded_step("substrate_probe", "blocked", f"daily substrate probe failed: {exc}", tail(result["stdout"] + result["stderr"]))
    reds = [p for p in payload.get("probes", []) if p.get("status") == "RED"]
    yellows = [p for p in payload.get("probes", []) if p.get("status") == "YELLOW"]
    status = "done" if not reds else "blocked"
    return recorded_step("substrate_probe", status, f"reds={len(reds)} yellows={len(yellows)} overall={payload.get('overall_status')}", {"reds": reds, "yellows": yellows[:10]})


def run_factory_probe(wiki: Path) -> dict[str, Any]:
    result = run(["bash", "tools/factory_no_drift_probe.sh", "--quiet"], cwd=wiki, timeout=180)
    try:
        payload = parse_json_result(result)
    except Exception as exc:
        return recorded_step("factory_no_drift", "blocked", f"factory no-drift probe failed: {exc}", tail(result["stdout"] + result["stderr"]))
    status = "done" if payload.get("overall") == "GREEN" else "blocked"
    return recorded_step("factory_no_drift", status, f"overall={payload.get('overall')} reds={payload.get('reds')}", payload)


def run_langsmith_smoke(wiki: Path, python: Path, dry_run: bool) -> dict[str, Any]:
    config_result = run([str(python), "tools/langsmith_observer.py", "--config"], cwd=wiki, timeout=60)
    try:
        config = parse_json_result(config_result)
    except Exception as exc:
        return recorded_step("langsmith", "blocked", f"LangSmith config failed: {exc}", tail(config_result["stdout"] + config_result["stderr"]))
    if not config.get("send_enabled"):
        return recorded_step("langsmith", "blocked", f"LangSmith disabled: {config.get('reason')}", config)
    if dry_run:
        return recorded_step("langsmith", "skipped", "LangSmith send ready; smoke skipped in dry-run", config)
    smoke = run([str(python), "tools/langsmith_observer.py", "--smoke"], cwd=wiki, timeout=120)
    try:
        payload = parse_json_result(smoke)
    except Exception as exc:
        return recorded_step("langsmith", "blocked", f"LangSmith smoke failed: {exc}", tail(smoke["stdout"] + smoke["stderr"]))
    return recorded_step("langsmith", "done" if payload.get("ok") else "blocked", "LangSmith smoke trace uploaded", payload)


def newest_model_bakeoff(wiki: Path) -> Path | None:
    files = sorted((wiki / AUDIT_DIR).glob(MODEL_BAKEOFF_GLOB), key=lambda path: path.stat().st_mtime, reverse=True)
    return files[0] if files else None


def should_run_bakeoff(wiki: Path, force: bool) -> bool:
    if force:
        return True
    latest = newest_model_bakeoff(wiki)
    if not latest:
        return True
    age_days = (time.time() - latest.stat().st_mtime) / 86400
    return age_days >= 7


def run_weekly_model_bakeoff(wiki: Path, python: Path, force: bool, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return recorded_step("weekly_model_bakeoff", "skipped", "dry-run; model bakeoff not executed")
    if not should_run_bakeoff(wiki, force):
        latest = newest_model_bakeoff(wiki)
        return recorded_step("weekly_model_bakeoff", "skipped", f"latest bakeoff still fresh: {latest}", str(latest))
    stamp = now_kzt().strftime("%Y-%m-%d-%H%M")
    out = AUDIT_DIR / f"model-bakeoff-{stamp}.json"
    result = run(
        [
            str(python),
            "tools/model_bakeoff.py",
            "--models",
            "deepseek-v4-flash,deepseek-v4-pro,kimi-k2.6,glm-5.1",
            "--max-cases",
            "4",
            "--timeout",
            "25",
            "--max-tokens",
            "256",
            "--output",
            str(out),
        ],
        cwd=wiki,
        timeout=900,
    )
    if not result["ok"]:
        return recorded_step("weekly_model_bakeoff", "blocked", "model bakeoff failed", tail(result["stdout"] + result["stderr"]))
    try:
        payload = json.loads((wiki / out).read_text(encoding="utf-8"))
    except Exception:
        payload = tail(result["stdout"], 2000)
    if isinstance(payload, dict):
        summary = payload.get("summary") or {}
        total_passed = sum(int(row.get("passed") or 0) for row in summary.values() if isinstance(row, dict))
        total_errors = sum(int(row.get("errors") or 0) for row in summary.values() if isinstance(row, dict))
        if total_passed == 0:
            return recorded_step(
                "weekly_model_bakeoff",
                "not_done",
                f"wrote {out}; all candidates failed or timed out; errors={total_errors}",
                summary,
            )
        return recorded_step("weekly_model_bakeoff", "done", f"wrote {out}; passed_checks={total_passed} errors={total_errors}", summary)
    return recorded_step("weekly_model_bakeoff", "not_done", f"wrote {out}; report parse incomplete", payload)


def render_status_page(cycle: dict[str, Any]) -> str:
    rows = cycle["steps"]
    lines = [
        "---",
        "type: system",
        "id: control-plane-sync-status",
        'title: "Статус синхронизации контрольной плоскости"',
        f"last_updated: {cycle['finished_at'] or cycle['started_at']}",
        f"status: {cycle['overall_status']}",
        "tags: [control-plane, todoist, notion, github, langsmith, factory]",
        "---",
        "",
        "# Статус синхронизации контрольной плоскости",
        "",
        f"- Последний цикл: `{cycle['cycle_id']}`",
        f"- Общий статус: `{cycle['overall_status']}`",
        f"- Старт: `{cycle['started_at']}`",
        f"- Финиш: `{cycle['finished_at'] or 'in_progress'}`",
        f"- Сухой прогон: `{cycle['dry_run']}`",
        "",
        "## Матрица статусов",
        "",
        "| Компонент | Состояние | Сводка |",
        "|---|---:|---|",
    ]
    for row in rows:
        summary = str(row.get("summary") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {row['name']} | `{row['status']}` | {summary} |")
    lines.extend(["", "## Правила блокировок", ""])
    lines.append("- `blocked`: API/runtime/git путь сломан; нужна фабрика или оператор.")
    lines.append("- `not_done`: детерминированный план есть, но не применён в этом цикле.")
    lines.append("- `working` / `in_progress`: сейчас выполняется; не должен оставаться после финиша цикла.")
    lines.append("- `done`: проверено живым выводом команды.")
    lines.append("- `skipped`: намеренно пропущено, обычно из-за dry-run или недельного cadence gate.")
    lines.append("")
    return "\n".join(lines)


def render_audit(cycle: dict[str, Any]) -> str:
    lines = [
        "---",
        "type: audit",
        f"id: CONTROL-PLANE-SYNC-{cycle['cycle_id']}",
        f'title: "Цикл синхронизации контрольной плоскости - {cycle["cycle_id"]}"',
        f"date: {cycle['date']}",
        f"status: {cycle['overall_status']}",
        "tags: [audit, control-plane, todoist, notion, github, langsmith, factory]",
        "---",
        "",
        f"# Цикл синхронизации контрольной плоскости - {cycle['cycle_id']}",
        "",
        f"- Общий статус: `{cycle['overall_status']}`",
        f"- Старт: `{cycle['started_at']}`",
        f"- Финиш: `{cycle['finished_at'] or 'in_progress'}`",
        f"- Сухой прогон: `{cycle['dry_run']}`",
        "",
        "## Шаги",
        "",
    ]
    for step in cycle["steps"]:
        lines.append(f"### {step['name']}")
        lines.append("")
        lines.append(f"- Статус: `{step['status']}`")
        lines.append(f"- Сводка: {step['summary']}")
        evidence = step.get("evidence")
        if evidence is not None:
            lines.extend(["", "```json", json.dumps(evidence, ensure_ascii=False, indent=2, default=str)[:5000], "```"])
        lines.append("")
    return "\n".join(lines)


def append_jsonl(cycle: dict[str, Any]) -> None:
    JSONL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with JSONL_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(cycle, ensure_ascii=False, sort_keys=True, default=str) + "\n")


def commit_and_push(wiki: Path, paths: list[Path], message: str, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return recorded_step("git_writeback", "skipped", "dry-run; no commit/push", [str(p) for p in paths])
    rels = [str(path) for path in paths]
    add = run(["git", "-c", "core.hooksPath=/dev/null", "add", *rels], cwd=wiki, timeout=120)
    if not add["ok"]:
        return recorded_step("git_writeback", "blocked", "git add failed", tail(add["stdout"] + add["stderr"]))
    diff = run(["git", "diff", "--cached", "--quiet", "--", *rels], cwd=wiki, timeout=60)
    committed = False
    if diff["returncode"] == 1:
        commit = run(["git", "-c", "core.hooksPath=/dev/null", "commit", "--no-verify", "-m", message], cwd=wiki, timeout=120)
        if not commit["ok"]:
            return recorded_step("git_writeback", "blocked", "git commit failed", tail(commit["stdout"] + commit["stderr"]))
        committed = True
    elif diff["returncode"] != 0:
        return recorded_step("git_writeback", "blocked", "git diff --cached failed", tail(diff["stdout"] + diff["stderr"]))

    canonical_remote = resolve_canonical_remote(wiki)
    rebase_origin = rebase_onto_remote_main(wiki, canonical_remote, timeout=180)
    if not rebase_origin["ok"]:
        return recorded_step("git_writeback", "blocked", f"exact {canonical_remote}/main rebase before push failed", tail(rebase_origin["stdout"] + rebase_origin["stderr"]))
    github_remote = run(["git", "remote", "get-url", "github"], cwd=wiki, timeout=30)
    github_missing = not github_remote["ok"]
    if not github_missing:
        github_target, fetch_github = fetch_remote_main_oid(wiki, "github", timeout=180)
        if not github_target:
            return recorded_step("git_writeback", "not_done", "git fetch github main failed", tail(fetch_github["stdout"] + fetch_github["stderr"]))
        rebase_github = run(["git", "-c", "core.hooksPath=/dev/null", "rebase", github_target], cwd=wiki, timeout=180)
        if not rebase_github["ok"]:
            run(["git", "rebase", "--abort"], cwd=wiki, timeout=60)
            return recorded_step("git_writeback", "blocked", "git rebase exact github/main before mirror push failed", tail(rebase_github["stdout"] + rebase_github["stderr"]))
    push_origin = run(["git", "push", canonical_remote, "main"], cwd=wiki, timeout=180)
    if not push_origin["ok"]:
        return recorded_step("git_writeback", "blocked", f"git push {canonical_remote} failed", tail(push_origin["stdout"] + push_origin["stderr"]))
    if github_missing:
        return recorded_step("git_writeback", "not_done", f"{canonical_remote} pushed; github remote missing", tail(github_remote["stdout"] + github_remote["stderr"]))
    push_github = run(["git", "push", "github", "main"], cwd=wiki, timeout=180)
    github_status = "ok" if push_github["ok"] else tail(push_github["stdout"] + push_github["stderr"], 1000)
    status = "done" if push_github["ok"] else "not_done"
    head = run(["git", "rev-parse", "--short", "HEAD"], cwd=wiki, timeout=30)
    return recorded_step(
        "git_writeback",
        status,
        f"committed={committed} head={head['stdout'].strip()} github={github_status}",
        {canonical_remote: tail(push_origin["stdout"] + push_origin["stderr"]), "github": github_status},
    )


def emit_langsmith_event(wiki: Path, python: Path, cycle: dict[str, Any]) -> None:
    script = (
        "from langsmith_observer import emit_event\n"
        "import json, sys\n"
        "payload=json.load(sys.stdin)\n"
        "emit_event('nous.control_plane_sync', inputs={'cycle_id': payload['cycle_id']}, "
        "outputs={'overall_status': payload['overall_status']}, metadata=payload, "
        "tags=['nous','control-plane','automation'], status=payload['overall_status'], wait=False)\n"
    )
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{wiki}:{wiki / 'tools'}:{env.get('PYTHONPATH', '')}"
        subprocess.run(
            [str(python), "-c", script],
            input=json.dumps(cycle, ensure_ascii=False),
            cwd=str(wiki),
            env=env,
            text=True,
            timeout=30,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def step_by_name(cycle: dict[str, Any], name: str) -> dict[str, Any]:
    for step in cycle.get("steps", []):
        if step.get("name") == name:
            return step
    return {}


def append_preflight_skips(cycle: dict[str, Any]) -> None:
    for name in (
        "notion_sync",
        "todoist_control_plane",
        "todoist_register_export",
        "satory_todoist_deep_audit",
        "substrate_probe",
        "factory_probe",
        "langsmith",
        "model_bakeoff",
        "russian_docs_gate",
    ):
        cycle["steps"].append(recorded_step(name, "skipped_preflight", "git preflight blocked; step intentionally not started"))


def send_telegram_receipt(wiki: Path, cycle: dict[str, Any], dry_run: bool, no_telegram: bool) -> dict[str, Any]:
    if dry_run or no_telegram:
        return recorded_step("telegram_notify", "skipped", "dry-run or --no-telegram")

    todoist = step_by_name(cycle, "todoist_control_plane")
    register = step_by_name(cycle, "todoist_register_export")
    deep_audit = step_by_name(cycle, "satory_todoist_deep_audit")
    notion = step_by_name(cycle, "notion_sync")
    langsmith = step_by_name(cycle, "langsmith")
    writeback = step_by_name(cycle, "git_writeback")
    status = cycle.get("overall_status", "unknown")
    head = run(["git", "rev-parse", "--short", "HEAD"], cwd=wiki, timeout=30)
    head_text = head["stdout"].strip() if head["ok"] else "unknown"
    message = (
        f"Синхронизация контрольной плоскости {status} в {cycle.get('finished_at')}: "
        f"Todoist {todoist.get('status', 'missing')}; "
        f"Реестр {register.get('status', 'missing')}; "
        f"Аудит {deep_audit.get('status', 'missing')}; "
        f"Notion {notion.get('status', 'missing')}; "
        f"LangSmith {langsmith.get('status', 'missing')}; "
        f"Git {writeback.get('status', 'missing')}; "
        f"HEAD {head_text}. "
        "Статус: pages/systems/control-plane-sync-status.md"
    )
    result = run(["bash", "tools/tg_send.sh", message], cwd=wiki, timeout=60)
    status_out = "done" if result["ok"] else "not_done"
    return recorded_step("telegram_notify", status_out, "sent Telegram cycle receipt" if result["ok"] else "Telegram receipt failed", tail(result["stdout"] + result["stderr"]))


def run_cycle(args: argparse.Namespace) -> dict[str, Any]:
    wiki = args.wiki
    python = args.python
    started = now_kzt()
    cycle_id = started.strftime("%Y-%m-%d-%H%M%S")
    cycle: dict[str, Any] = {
        "cycle_id": cycle_id,
        "date": started.date().isoformat(),
        "started_at": started.isoformat(),
        "finished_at": None,
        "dry_run": args.dry_run,
        "overall_status": "in_progress",
        "steps": [],
    }

    with loop_lock():
        preflight = git_clean_or_block(wiki)
        cycle["steps"].append(preflight)
        if preflight["status"] == "blocked":
            cycle["overall_status"] = "blocked"
            append_preflight_skips(cycle)
        else:
            cycle["steps"].append(run_notion_sync(wiki, python, args.dry_run))
            cycle["steps"].append(run_todoist_hygiene(wiki, python, args.dry_run, not args.no_apply_todoist))
            cycle["steps"].append(run_todoist_register_export(wiki, python, args.dry_run))
            cycle["steps"].append(run_satory_todoist_deep_audit(wiki, python, args.dry_run, cycle_id))
            cycle["steps"].append(run_substrate_probe(wiki, python))
            cycle["steps"].append(run_factory_probe(wiki))
            cycle["steps"].append(run_langsmith_smoke(wiki, python, args.dry_run))
            cycle["steps"].append(run_weekly_model_bakeoff(wiki, python, args.force_model_bakeoff, args.dry_run))

        worst = max(cycle["steps"], key=lambda row: status_rank(row["status"]))
        cycle["overall_status"] = worst["status"] if worst["status"] in {"blocked", "not_done"} else "done"
        cycle["finished_at"] = iso_now()

        status_path = STATUS_PAGE
        audit_path = AUDIT_DIR / f"CONTROL-PLANE-SYNC-{cycle_id}.md"
        (wiki / status_path).parent.mkdir(parents=True, exist_ok=True)
        (wiki / AUDIT_DIR).mkdir(parents=True, exist_ok=True)
        if not args.dry_run:
            (wiki / status_path).write_text(render_status_page(cycle), encoding="utf-8")
            (wiki / audit_path).write_text(render_audit(cycle), encoding="utf-8")
            cycle["steps"].append(run_russian_docs_gate(wiki, python))
            worst = max(cycle["steps"], key=lambda row: status_rank(row["status"]))
            cycle["overall_status"] = worst["status"] if worst["status"] in {"blocked", "not_done"} else "done"
            cycle["finished_at"] = iso_now()
            (wiki / status_path).write_text(render_status_page(cycle), encoding="utf-8")
            (wiki / audit_path).write_text(render_audit(cycle), encoding="utf-8")

        append_jsonl(cycle)
        if not args.dry_run:
            writeback_paths = [
                status_path,
                audit_path,
                TODOIST_REGISTER_MD,
                TODOIST_REGISTER_JSON,
                TODOIST_REGISTER_CSV,
                TODOIST_CONTEXT_QUEUE,
                SATORY_DEEP_AUDIT_JSON,
                SATORY_DEEP_AUDIT_INDEX,
                Path("pages/tenants/satory/notes"),
                Path("pages/tenants/satory/tasks"),
            ]
            deep_audit = step_by_name(cycle, "satory_todoist_deep_audit")
            deep_markdown = (deep_audit.get("evidence") or {}).get("markdown")
            if deep_markdown:
                writeback_paths.append(Path(str(deep_markdown)))
            latest_bakeoff = newest_model_bakeoff(wiki)
            if latest_bakeoff:
                try:
                    writeback_paths.append(latest_bakeoff.relative_to(wiki))
                except ValueError:
                    pass
            cycle["steps"].append(
                commit_and_push(wiki, writeback_paths, f"control-plane-sync: {cycle_id}", args.dry_run)
            )
            worst = max(cycle["steps"], key=lambda row: status_rank(row["status"]))
            cycle["overall_status"] = worst["status"] if worst["status"] in {"blocked", "not_done"} else "done"
            cycle["finished_at"] = iso_now()
            (wiki / status_path).write_text(render_status_page(cycle), encoding="utf-8")
            (wiki / audit_path).write_text(render_audit(cycle), encoding="utf-8")
            cycle["steps"].append(
                commit_and_push(wiki, [status_path, audit_path], f"control-plane-sync: finalize {cycle_id}", args.dry_run)
            )
            worst = max(cycle["steps"], key=lambda row: status_rank(row["status"]))
            cycle["overall_status"] = worst["status"] if worst["status"] in {"blocked", "not_done"} else "done"

        append_jsonl(cycle)
        emit_langsmith_event(wiki, python, cycle)
        notify = send_telegram_receipt(wiki, cycle, args.dry_run, args.no_telegram)
        cycle["notification"] = notify
        append_jsonl(cycle)
        return cycle


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-apply-todoist", action="store_true", help="Audit Todoist but do not apply deterministic hard-gate repairs.")
    parser.add_argument("--no-telegram", action="store_true", help="Do not send the Telegram cycle receipt.")
    parser.add_argument("--force-model-bakeoff", action="store_true", help="Run the weekly model bakeoff even if a fresh one exists.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        cycle = run_cycle(args)
    except Exception as exc:
        cycle = {
            "cycle_id": now_kzt().strftime("%Y-%m-%d-%H%M%S"),
            "date": now_kzt().date().isoformat(),
            "started_at": iso_now(),
            "finished_at": iso_now(),
            "dry_run": getattr(args, "dry_run", False),
            "overall_status": "blocked",
            "steps": [recorded_step("control_plane_sync", "blocked", str(exc))],
        }
        append_jsonl(cycle)
        if getattr(args, "json", False):
            print(json.dumps(cycle, ensure_ascii=False, indent=2, default=str))
        else:
            print(f"blocked: {exc}")
        return 1
    if args.json:
        print(json.dumps(cycle, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"cycle={cycle['cycle_id']} status={cycle['overall_status']}")
        for step in cycle["steps"]:
            print(f"{step['status']}\t{step['name']}\t{step['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
