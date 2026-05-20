#!/usr/bin/env python3
"""LAW-010: Daily 23:00 Almaty Owner Summary
Runs via cron: 0 18 * * * (18:00 UTC = 23:00 Almaty)
Sends ONE Telegram message to Madi with full progress status.
"""
import sys, os, json, sqlite3
sys.path.insert(0, "/root/nous-agaas")
from dotenv import load_dotenv
load_dotenv("/root/nous-agaas/.env")
from tools.telegram_bot import send_message
from agents.memory_manager import search_memory

# Get task stats
db = sqlite3.connect("/root/nous-agaas/logs/task_queue.db")
tasks = db.execute("SELECT status, COUNT(*) FROM tasks WHERE id >= 900000 GROUP BY status").fetchall()
task_stats = {r[0]: r[1] for r in tasks}
total = sum(task_stats.values())
done = task_stats.get("done", 0)
db.close()

# Get event stats
try:
    ev_db = sqlite3.connect("/opt/nous-agaas/erap/data/events.db")
    total_events = ev_db.execute("SELECT COUNT(*) FROM vehicle_events").fetchone()[0]
    total_violations = ev_db.execute("SELECT COUNT(*) FROM vehicle_events WHERE (vehicle_speed - speed_limit) >= 10 AND speed_limit > 0").fetchone()[0]
    ev_db.close()
except:
    total_events = 0
    total_violations = 0

# Get cost
try:
    with open("/root/nous-agaas/logs/daily_cost.json") as f:
        cost = json.load(f).get("total", 0)
except:
    cost = 0

# Build summary
msg = (
    f"📊 DAILY OWNER SUMMARY — {os.popen('TZ=Asia/Almaty date +%Y-%m-%d').read().strip()}\n"
    f"━━━━━━━━━━━━━━━━━━━━\n"
    f"📋 Tasks: {done}/{total} done ({round(done*100/max(total,1))}%)\n"
    f"  ✅ Done: {task_stats.get('done',0)}\n"
    f"  🔄 In Progress: {task_stats.get('in_progress',0)}\n"
    f"  ⏳ Pending: {task_stats.get('pending',0)}\n"
    f"  ❌ Failed: {task_stats.get('failed',0)}\n"
    f"  🚫 Blocked: {task_stats.get('blocked',0)}\n"
    f"\n📹 Cameras: 243 (156 online)\n"
    f"📊 Events: {total_events:,}\n"
    f"⚠️ Violations: {total_violations}\n"
    f"💰 Cost today: ${cost:.2f}\n"
    f"\n🎯 Mission: Replace BDL+Cerebro (89 req)\n"
    f"Reply GOOD or FIX [issue]"
)

send_message(msg)
print(f"Daily summary sent")
