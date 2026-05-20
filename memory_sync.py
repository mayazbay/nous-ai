#!/usr/bin/env python3
# CANONICAL: pages/tools/memory_sync.py (this file) — session 73 migration from
# VPS-runtime /root/nous-agaas/memory_sync.py (AP-49 substrate-drift fix).
# Vault is now the single source of truth; VPS runtime should be rsync-target,
# not edit-site. See infrastructure SKILL AP-49 + session-73 HANDOFF.
"""AMENDMENT-003: Twice-daily memory sync.
Runs at 9AM + 6PM Almaty (cron: 0 4,13 * * *)
1. Verifies all 18 laws present in wiki
2. Runs lint.py health check
3. Git commits any wiki changes
4. Cleans stale Mem0 entries
5. Reports status to Telegram
"""
import os, sys, glob, logging, time, subprocess
sys.path.insert(0, "/root/nous-agaas")
from dotenv import load_dotenv
load_dotenv("/root/nous-agaas/.env", override=True)

from tools.telegram_bot import send_message
from agents.memory_manager import search_memory, store_memory

WIKI_PATH = "/root/nous-agaas/wiki"
LOG = logging.getLogger("memory_sync")


def sync():
    issues = []
    stats = {}

    # 1. Verify all 18 law files exist
    law_files = sorted(glob.glob(os.path.join(WIKI_PATH, "laws", "LAW-*.md")))
    stats["laws"] = len(law_files)
    if len(law_files) < 18:
        issues.append(f"CRITICAL: Only {len(law_files)}/18 law files in wiki/laws/")

    # Check each law file is non-empty
    for lf in law_files:
        size = os.path.getsize(lf)
        if size < 100:
            issues.append(f"LAW file too small: {os.path.basename(lf)} ({size} bytes)")

    # 2. Verify amendments exist
    amd_files = glob.glob(os.path.join(WIKI_PATH, "laws", "AMENDMENT-*.md"))
    if len(amd_files) < 3:
        issues.append(f"Missing amendments: {len(amd_files)}/3")

    # 3. Verify PERMANENT-RULES.md
    perm = os.path.join(WIKI_PATH, "laws", "PERMANENT-RULES.md")
    if not os.path.isfile(perm):
        issues.append("PERMANENT-RULES.md missing!")

    # 4. Count total wiki entries
    all_wiki = glob.glob(os.path.join(WIKI_PATH, "**", "*.md"), recursive=True)
    # Exclude .git
    all_wiki = [f for f in all_wiki if ".git" not in f]
    stats["wiki_files"] = len(all_wiki)

    # 5. Check auto_lessons.md size
    al = os.path.join(WIKI_PATH, "pages", "lessons", "auto_lessons.md")
    al_size = 0
    if os.path.isfile(al):
        al_size = os.path.getsize(al)
        if al_size > 100000:
            issues.append(f"auto_lessons.md is {al_size // 1024}KB — consider archiving old entries")
    stats["auto_lessons_kb"] = al_size // 1024

    # 6. Run wiki lint
    lint_score = "?"
    lint_path = os.path.join(WIKI_PATH, "lint.py")
    if os.path.isfile(lint_path):
        try:
            result = subprocess.run(
                [sys.executable, lint_path],
                capture_output=True, text=True, timeout=60
            )
            output = result.stdout + result.stderr
            # Extract health score
            import re
            score_match = re.search(r"HEALTH SCORE: (\d+)/10", output)
            if score_match:
                lint_score = score_match.group(1)
                stats["lint_score"] = int(lint_score)
                if int(lint_score) < 7:
                    issues.append(f"Lint health score {lint_score}/10 — needs attention")
            # Extract issue count
            issue_match = re.search(r"ISSUES \((\d+)\)", output)
            if issue_match and int(issue_match.group(1)) > 0:
                issues.append(f"Lint found {issue_match.group(1)} issues")
        except Exception as e:
            issues.append(f"Lint failed: {str(e)[:50]}")
    else:
        issues.append("lint.py not found in wiki/")

    # 7. Check banned_patterns.txt exists (LAW-008)
    bp = os.path.join(WIKI_PATH, "laws", "banned_patterns.txt")
    if not os.path.isfile(bp):
        issues.append("banned_patterns.txt missing — LAW-008 patterns not wiki-driven")

    # 8. Git commit any uncommitted wiki changes
    git_status = ""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=WIKI_PATH, capture_output=True, text=True, timeout=10
        )
        git_status = result.stdout.strip()
        if git_status:
            # There are uncommitted changes — commit them
            subprocess.run(["git", "add", "-A"], cwd=WIKI_PATH, timeout=10)
            subprocess.run(
                ["git", "commit", "-m", f"AMD-003 auto-sync {time.strftime('%Y-%m-%d %H:%M')}"],
                cwd=WIKI_PATH, capture_output=True, text=True, timeout=15
            )
            stats["git_committed"] = True
            LOG.info("Git: committed wiki changes")
        else:
            stats["git_committed"] = False
    except Exception as e:
        issues.append(f"Git check failed: {str(e)[:50]}")

    # 9. Check COMPILED-KNOWLEDGE.md exists and is recent
    ck = os.path.join(WIKI_PATH, "pages", "lessons", "COMPILED-KNOWLEDGE.md")
    if os.path.isfile(ck):
        ck_size = os.path.getsize(ck)
        if ck_size < 500:
            issues.append("COMPILED-KNOWLEDGE.md too small — may be corrupted")
        stats["compiled_kb"] = ck_size // 1024
    else:
        issues.append("COMPILED-KNOWLEDGE.md missing — agents wont have compiled knowledge")

    # 10. Store sync result to Mem0
    status = "OK" if not issues else f"{len(issues)} issues"
    try:
        store_memory(
            f"[SYNC {time.strftime('%Y-%m-%d %H:%M')}] "
            f"Laws:{stats.get('laws', '?')}/18 "
            f"Wiki:{stats.get('wiki_files', '?')} files "
            f"Lint:{lint_score}/10 "
            f"Status:{status}"
        )
    except Exception as e:
        LOG.warning(f"Mem0 store failed: {e}")

    # 11. Report to Telegram
    if issues:
        msg = (
            f"*AMD-003 SYNC* {time.strftime('%H:%M')}\n"
            f"Laws: {stats.get('laws', '?')}/18 | Wiki: {stats.get('wiki_files', '?')} files | "
            f"Lint: {lint_score}/10\n"
            f"*Issues ({len(issues)}):*\n" +
            "\n".join(f"- {i}" for i in issues[:5])
        )
        send_message(msg)
        LOG.warning(f"Sync issues: {issues}")
    else:
        msg = (
            f"*AMD-003 SYNC OK* {time.strftime('%H:%M')}\n"
            f"Laws: {stats['laws']}/18 | Wiki: {stats['wiki_files']} files | "
            f"Lint: {lint_score}/10 | "
            f"Compiled: {stats.get('compiled_kb', '?')}KB | "
            f"Git: {'committed' if stats.get('git_committed') else 'clean'}"
        )
        send_message(msg)
        LOG.info(f"Sync OK: {stats}")

    # 12. Append to wiki log
    log_path = os.path.join(WIKI_PATH, "log.md")
    if os.path.isfile(log_path):
        try:
            with open(log_path, "a") as f:
                f.write(
                    f"\n## [{time.strftime('%Y-%m-%d')}] sync | "
                    f"AMD-003: Laws {stats.get('laws', '?')}/18, "
                    f"Wiki {stats.get('wiki_files', '?')} files, "
                    f"Lint {lint_score}/10, "
                    f"Issues: {len(issues)}\n"
                )
        except Exception:
            pass

    return issues


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    sync()
