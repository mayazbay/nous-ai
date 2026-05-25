"""Local SQLite backup for task queue — protects against Mem0 outages or parser failures."""

import sqlite3
import json
import os
from config import LOG_DIR

DB_PATH = os.path.join(LOG_DIR, "task_queue.db")


def _get_conn():
    """Get SQLite connection, create table if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            project TEXT DEFAULT 'BDL',
            priority INTEGER DEFAULT 2,
            status TEXT DEFAULT 'pending',
            blocked_by TEXT DEFAULT '',
            acceptance_criteria TEXT DEFAULT '',
            files_to_modify TEXT DEFAULT '[]',
            error_history TEXT DEFAULT '[]',
            created_by TEXT DEFAULT 'system',
            cycle_completed INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def save_task(task: dict) -> dict:
    """Save or update a task in local SQLite."""
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO tasks
            (id, title, project, priority, status, blocked_by, acceptance_criteria,
             files_to_modify, error_history, created_by, cycle_completed, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            task.get("id"),
            task.get("title", ""),
            task.get("project", "BDL"),
            task.get("priority", 2),
            task.get("status", "pending"),
            task.get("blocked_by", ""),
            task.get("acceptance_criteria", ""),
            json.dumps(task.get("files_to_modify", []), ensure_ascii=False),
            json.dumps(task.get("error_history", []), ensure_ascii=False),
            task.get("created_by", "system"),
            task.get("cycle_completed"),
        ))
        conn.commit()
        return task
    finally:
        conn.close()


def get_all_tasks(project: str = None, status: str = None) -> list[dict]:
    """Get all tasks from local SQLite, optionally filtered."""
    conn = _get_conn()
    try:
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        if project:
            query += " AND project = ?"
            params.append(project)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY CASE project WHEN 'BDL' THEN 0 ELSE 1 END, priority ASC, id ASC"

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_task(task_id: int, **kwargs) -> dict:
    """Update specific fields of a task."""
    conn = _get_conn()
    try:
        allowed = {"title", "project", "priority", "status", "blocked_by",
                   "acceptance_criteria", "cycle_completed", "error_history"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return {}
        updates["updated_at"] = "datetime('now')"

        set_clause = ", ".join(f"{k} = ?" for k in updates if k != "updated_at")
        set_clause += ", updated_at = datetime('now')"
        values = [v for k, v in updates.items() if k != "updated_at"]
        values.append(task_id)

        conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return {"id": task_id, **updates}
    finally:
        conn.close()


def get_pending_tasks(project: str = None) -> list[dict]:
    """Get pending tasks sorted by priority — the CEO's view.

    By default, returns pending tasks from ALL projects (BDL + CEREBRO + future).
    Pass a specific project name to filter to one project only.

    See LESSON-051: previously hardcoded to "BDL" which made CEREBRO
    pending tasks invisible to the factory and caused 10+ idle cycles.
    """
    if project is None:
        all_tasks = get_all_tasks(status="pending")
    else:
        all_tasks = get_all_tasks(project=project, status="pending")
    # Sort by priority (ascending — lower number = higher priority), then created_at
    all_tasks.sort(key=lambda t: (t.get("priority", 99), t.get("created_at", "")))
    return all_tasks


def sync_from_seed(tasks: list[dict]):
    """Bulk import tasks (from import_tasks.py). Skips existing IDs."""
    conn = _get_conn()
    try:
        for task in tasks:
            existing = conn.execute("SELECT id FROM tasks WHERE id = ?", (task.get("id"),)).fetchone()
            if not existing:
                save_task(task)
        conn.commit()
    finally:
        conn.close()


def create_task(title, description="", priority=1, project="BDL"):
    """Create a new task. Schema-safe: checks columns exist before insert."""
    from datetime import datetime
    conn = _get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    fields = {"title": title, "priority": priority, "status": "pending", "project": project,
              "created_by": "ceo", "created_at": now, "updated_at": now, "error_history": "[]"}
    if "description" in existing_cols:
        fields["description"] = description
    elif "acceptance_criteria" in existing_cols:
        fields["acceptance_criteria"] = description
    cols = ", ".join(fields.keys())
    placeholders = ", ".join(["?"] * len(fields))
    conn.execute(f"INSERT INTO tasks ({cols}) VALUES ({placeholders})", tuple(fields.values()))
    conn.commit()
    task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return {"id": task_id, "title": title, "status": "pending"}
