#!/usr/bin/env python3
"""LAW-014: Task State Watchdog
Runs every 5 min via cron. Auto-resets stuck in_progress tasks.
Cron: */5 * * * * /root/nous-agaas/venv/bin/python3 /root/nous-agaas/tools/task_watchdog.py
"""
import sqlite3, os, subprocess, logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("watchdog")

DB_PATH = "/root/nous-agaas/logs/task_queue.db"
FRONTEND = "/root/nous-agaas/codebase/satory-frontend"
MAX_AGE_MIN = 30

def check_git_activity(minutes=30):
    """Check if there was a git commit in the last N minutes."""
    try:
        result = subprocess.run(
            ["git", "log", f"--since={minutes}.minutes", "--oneline"],
            cwd=FRONTEND, capture_output=True, text=True, timeout=10
        )
        return len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
    except:
        return 0

def run():
    db = sqlite3.connect(DB_PATH)
    stuck = db.execute(
        "SELECT id, title, updated_at FROM tasks WHERE status='in_progress'"
    ).fetchall()
    
    if not stuck:
        return 0
    
    git_commits = check_git_activity(MAX_AGE_MIN)
    unstuck = 0
    
    for task_id, title, updated_at in stuck:
        try:
            updated = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
            age_min = (datetime.now() - updated).total_seconds() / 60
        except:
            age_min = 999
        
        if age_min > MAX_AGE_MIN and git_commits == 0:
            db.execute(
                "UPDATE tasks SET status='pending', updated_at=? WHERE id=?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), task_id)
            )
            log.warning(f"UNSTUCK [{task_id}] {title[:50]} (stuck {int(age_min)} min, 0 git commits)")
            unstuck += 1
    
    db.commit()
    db.close()
    
    if unstuck:
        log.info(f"Watchdog: unstuck {unstuck} tasks")
    return unstuck

if __name__ == "__main__":
    n = run()
    if n:
        print(f"Unstuck {n} tasks")
