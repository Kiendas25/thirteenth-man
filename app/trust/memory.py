"""Persistent memory layer using SQLite.

Stores task history, memory entries and execution traces
for cross-session knowledge and auditability.
"""

from __future__ import annotations

import json
import logging

import aiosqlite

from app.config import settings
from app.models import MemoryEntry, TaskResponse

log = logging.getLogger(__name__)

_DB: str = settings.db_path


async def init_db() -> None:
    """Create tables if they don't exist."""
    async with aiosqlite.connect(_DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                status TEXT,
                final_answer TEXT,
                specialists_used TEXT,
                verification_passed INTEGER,
                created_at TEXT,
                raw_json TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                summary TEXT,
                tags TEXT,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                agent TEXT,
                action TEXT,
                detail TEXT,
                duration_ms INTEGER,
                timestamp TEXT
            )
        """)
        await db.commit()
    log.info("Database initialised at %s", _DB)


async def save_task(task: TaskResponse) -> None:
    """Persist a completed task response."""
    async with aiosqlite.connect(_DB) as db:
        ver_passed = (
            task.verification.passed if task.verification else None
        )
        await db.execute(
            """INSERT OR REPLACE INTO tasks
               (id, status, final_answer, specialists_used,
                verification_passed, created_at, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                task.task_id,
                task.status.value,
                task.final_answer,
                json.dumps(task.specialists_used),
                int(ver_passed) if ver_passed is not None else None,
                task.created_at,
                task.model_dump_json(),
            ),
        )
        for t in task.trace:
            await db.execute(
                """INSERT INTO traces
                   (task_id, agent, action, detail, duration_ms, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (task.task_id, t.agent, t.action, t.detail,
                 t.duration_ms, t.timestamp),
            )
        await db.commit()


async def save_memory(entry: MemoryEntry) -> None:
    """Save a memory entry."""
    async with aiosqlite.connect(_DB) as db:
        await db.execute(
            """INSERT INTO memory (id, task_id, summary, tags, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (entry.id, entry.task_id, entry.summary,
             json.dumps(entry.tags), entry.created_at),
        )
        await db.commit()


async def get_recent_tasks(
    limit: int = 20,
    status_filter: str | None = None,
) -> list[dict]:
    """Retrieve recent task summaries with optional status filter."""
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        query = (
            "SELECT id, status, final_answer, specialists_used, "
            "verification_passed, created_at FROM tasks"
        )
        params: list = []
        if status_filter:
            query += " WHERE status = ?"
            params.append(status_filter)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_task_detail(task_id: str) -> dict | None:
    """Get full task detail including raw JSON."""
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT raw_json FROM tasks WHERE id = ?", (task_id,)
        )
        row = await cursor.fetchone()
        if row:
            return json.loads(row["raw_json"])
        return None


async def search_memory(query: str, limit: int = 10) -> list[dict]:
    """Simple text search over memory entries."""
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM memory WHERE summary LIKE ? "
            "ORDER BY created_at DESC LIMIT ?",
            (f"%{query}%", limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
