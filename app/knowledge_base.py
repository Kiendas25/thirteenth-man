"""Per-user knowledge base — the system learns patterns from past analyses.

Tracks recurring issues, preferred coding patterns, team conventions,
and frequently flagged problems to provide increasingly relevant reviews.
"""

from __future__ import annotations

import json
import logging

import aiosqlite

from app.config import settings

log = logging.getLogger(__name__)

_DB = settings.db_path


async def init_knowledge_db() -> None:
    """Create knowledge-related tables."""
    async with aiosqlite.connect(_DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL DEFAULT 'default',
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_task_id TEXT,
                tags TEXT DEFAULT '[]',
                importance INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL DEFAULT 'default',
                pattern_type TEXT NOT NULL,
                pattern TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_agents (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL DEFAULT 'default',
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                description TEXT NOT NULL,
                capabilities TEXT DEFAULT '[]',
                system_prompt TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data TEXT DEFAULT '{}',
                username TEXT DEFAULT 'default',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    log.info("Knowledge database initialised")


# ---------------------------------------------------------------------------
# Knowledge entries
# ---------------------------------------------------------------------------

async def add_knowledge(
    username: str,
    category: str,
    title: str,
    content: str,
    source_task_id: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Add a knowledge entry."""
    async with aiosqlite.connect(_DB) as db:
        cursor = await db.execute(
            """INSERT INTO knowledge_entries
               (username, category, title, content, source_task_id, tags)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, category, title, content, source_task_id,
             json.dumps(tags or [])),
        )
        await db.commit()
        return {"id": cursor.lastrowid, "status": "added"}


async def get_knowledge(
    username: str,
    category: str | None = None,
    query: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Retrieve knowledge entries with optional filters."""
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        sql = "SELECT * FROM knowledge_entries WHERE username = ?"
        params: list = [username]
        if category:
            sql += " AND category = ?"
            params.append(category)
        if query:
            sql += " AND (title LIKE ? OR content LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
        params.append(limit)
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def delete_knowledge(entry_id: int, username: str) -> bool:
    """Delete a knowledge entry."""
    async with aiosqlite.connect(_DB) as db:
        cursor = await db.execute(
            "DELETE FROM knowledge_entries WHERE id = ? AND username = ?",
            (entry_id, username),
        )
        await db.commit()
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Learned patterns (auto-extracted from analyses)
# ---------------------------------------------------------------------------

async def record_pattern(
    username: str,
    pattern_type: str,
    pattern: str,
) -> None:
    """Record or increment a learned pattern."""
    async with aiosqlite.connect(_DB) as db:
        # Check if pattern exists
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, frequency FROM learned_patterns "
            "WHERE username = ? AND pattern_type = ? AND pattern = ?",
            (username, pattern_type, pattern),
        )
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "UPDATE learned_patterns SET frequency = ?, last_seen = CURRENT_TIMESTAMP WHERE id = ?",
                (row["frequency"] + 1, row["id"]),
            )
        else:
            await db.execute(
                "INSERT INTO learned_patterns (username, pattern_type, pattern) VALUES (?, ?, ?)",
                (username, pattern_type, pattern),
            )
        await db.commit()


async def get_patterns(
    username: str,
    pattern_type: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Get learned patterns, ordered by frequency."""
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        sql = "SELECT * FROM learned_patterns WHERE username = ?"
        params: list = [username]
        if pattern_type:
            sql += " AND pattern_type = ?"
            params.append(pattern_type)
        sql += " ORDER BY frequency DESC LIMIT ?"
        params.append(limit)
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Custom agents
# ---------------------------------------------------------------------------

async def save_custom_agent(
    agent_id: str,
    username: str,
    name: str,
    role: str,
    description: str,
    capabilities: list[str],
    system_prompt: str,
) -> dict:
    """Save a custom agent definition."""
    async with aiosqlite.connect(_DB) as db:
        await db.execute(
            """INSERT OR REPLACE INTO custom_agents
               (id, username, name, role, description, capabilities, system_prompt)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (agent_id, username, name, role, description,
             json.dumps(capabilities), system_prompt),
        )
        await db.commit()
        return {"id": agent_id, "status": "saved"}


async def get_custom_agents(username: str) -> list[dict]:
    """Get all custom agents for a user."""
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM custom_agents WHERE username = ? ORDER BY created_at DESC",
            (username,),
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["capabilities"] = json.loads(d["capabilities"])
            result.append(d)
        return result


async def delete_custom_agent(agent_id: str, username: str) -> bool:
    """Delete a custom agent."""
    async with aiosqlite.connect(_DB) as db:
        cursor = await db.execute(
            "DELETE FROM custom_agents WHERE id = ? AND username = ?",
            (agent_id, username),
        )
        await db.commit()
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

async def log_analytics(event_type: str, event_data: dict, username: str = "default") -> None:
    """Log an analytics event."""
    async with aiosqlite.connect(_DB) as db:
        await db.execute(
            "INSERT INTO analytics (event_type, event_data, username) VALUES (?, ?, ?)",
            (event_type, json.dumps(event_data), username),
        )
        await db.commit()


async def get_analytics_summary(username: str | None = None) -> dict:
    """Get analytics summary."""
    async with aiosqlite.connect(_DB) as db:
        db.row_factory = aiosqlite.Row
        where = "WHERE username = ?" if username else ""
        params = [username] if username else []

        # Total tasks
        cursor = await db.execute(f"SELECT COUNT(*) as c FROM tasks {where}", params)
        total_tasks = (await cursor.fetchone())["c"]

        # Tasks by status
        cursor = await db.execute(
            f"SELECT status, COUNT(*) as c FROM tasks {where} GROUP BY status", params
        )
        by_status = {r["status"]: r["c"] for r in await cursor.fetchall()}

        # Verification stats
        cursor = await db.execute(
            f"SELECT verification_passed, COUNT(*) as c FROM tasks {where} GROUP BY verification_passed",
            params,
        )
        ver_rows = await cursor.fetchall()
        ver_passed = sum(r["c"] for r in ver_rows if r["verification_passed"] == 1)
        ver_failed = sum(r["c"] for r in ver_rows if r["verification_passed"] == 0)

        # Most used specialists
        cursor = await db.execute(
            f"SELECT specialists_used FROM tasks {where} ORDER BY created_at DESC LIMIT 100",
            params,
        )
        spec_counts: dict[str, int] = {}
        for r in await cursor.fetchall():
            try:
                specs = json.loads(r["specialists_used"])
                for s in specs:
                    spec_counts[s] = spec_counts.get(s, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass
        top_specialists = sorted(spec_counts.items(), key=lambda x: -x[1])[:10]

        # Tasks per day (last 30 days)
        cursor = await db.execute(
            f"SELECT DATE(created_at) as day, COUNT(*) as c "
            f"FROM tasks {where} "
            f"GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 30",
            params,
        )
        daily = [{"date": r["day"], "count": r["c"]} for r in await cursor.fetchall()]

        # Average trace duration
        cursor = await db.execute(
            "SELECT AVG(duration_ms) as avg_ms FROM traces"
        )
        avg_row = await cursor.fetchone()
        avg_duration = int(avg_row["avg_ms"] or 0)

        return {
            "total_tasks": total_tasks,
            "by_status": by_status,
            "verification_passed": ver_passed,
            "verification_failed": ver_failed,
            "top_specialists": [{"name": s, "count": c} for s, c in top_specialists],
            "daily_tasks": daily,
            "avg_duration_ms": avg_duration,
        }
