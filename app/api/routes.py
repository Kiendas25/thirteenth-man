"""FastAPI routes for the 13th Man system."""

from __future__ import annotations

import logging
import traceback

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.agents.orchestrator import Orchestrator
from app.agents.specialists import list_specialists
from app.models import MemoryEntry, TaskRequest
from app.trust.approval import decide, list_pending, submit_approval
from app.trust.memory import get_recent_tasks, get_task_detail, save_memory, save_task
from app.trust.tracing import log_trace

log = logging.getLogger(__name__)
router = APIRouter()

orchestrator = Orchestrator()


# ---------------------------------------------------------------------------
# Task endpoints
# ---------------------------------------------------------------------------

@router.post("/api/tasks")
async def create_task(req: TaskRequest):
    """Submit a task to the multi-agent system."""
    try:
        response = await orchestrator.process(req)
    except Exception as exc:
        log.error("Task processing failed: %s", exc)
        log.debug(traceback.format_exc())
        msg = str(exc)
        if "api_key" in msg.lower() or "auth" in msg.lower():
            msg = (
                "OpenAI API key not configured or invalid. "
                "Edit your .env file and set OPENAI_API_KEY=sk-your-key"
            )
        return JSONResponse(
            status_code=500,
            content={"detail": msg},
        )

    # Persist and trace
    log_trace(response)
    await save_task(response)

    # Auto-save a memory entry
    await save_memory(MemoryEntry(
        task_id=response.task_id,
        summary=req.content[:200],
        tags=response.specialists_used,
    ))

    # Queue approval if needed
    if response.approval:
        submit_approval(response.approval)

    return response


@router.get("/api/tasks")
async def list_tasks():
    """Get recent tasks."""
    return await get_recent_tasks()


@router.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get full task detail."""
    detail = await get_task_detail(task_id)
    if detail is None:
        raise HTTPException(404, "Task not found")
    return detail


# ---------------------------------------------------------------------------
# Agent info
# ---------------------------------------------------------------------------

@router.get("/api/agents")
async def get_agents():
    """List all available specialist agents."""
    return list_specialists()


# ---------------------------------------------------------------------------
# Approval endpoints
# ---------------------------------------------------------------------------

@router.get("/api/approvals")
async def get_approvals():
    """List pending approvals."""
    return list_pending()


class ApprovalDecision(BaseModel):
    approved: bool


@router.post("/api/approvals/{approval_id}")
async def resolve_approval(approval_id: str, body: ApprovalDecision):
    """Approve or reject a pending request."""
    result = decide(approval_id, body.approved)
    if result is None:
        raise HTTPException(404, "Approval not found")
    return result


# ---------------------------------------------------------------------------
# Memory endpoints
# ---------------------------------------------------------------------------

@router.get("/api/memory")
async def search_mem(q: str = ""):
    """Search memory entries."""
    from app.trust.memory import search_memory
    return await search_memory(q)
