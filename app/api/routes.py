"""FastAPI routes for the 13th Man system."""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone

import markdown
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from app.agents.orchestrator import Orchestrator
from app.agents.specialists import list_specialists
from app.auth import (
    Token,
    UserCreate,
    UserResponse,
    authenticate_user,
    get_current_user,
    register_user,
)
from app.models import MemoryEntry, TaskRequest
from app.trust.approval import decide, list_pending, submit_approval
from app.trust.memory import get_recent_tasks, get_task_detail, save_memory, save_task
from app.trust.tracing import log_trace

log = logging.getLogger(__name__)
router = APIRouter()

orchestrator = Orchestrator()


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@router.post("/api/auth/register", response_model=UserResponse)
async def api_register(data: UserCreate):
    """Register a new user."""
    return await register_user(data)


@router.post("/api/auth/login", response_model=Token)
async def api_login(data: UserCreate):
    """Login and receive a JWT token."""
    return await authenticate_user(data.username, data.password)


@router.get("/api/auth/me")
async def api_me(user: str | None = Depends(get_current_user)):
    """Check current auth status."""
    if user is None:
        return {"authenticated": False}
    return {"authenticated": True, "username": user}


# ---------------------------------------------------------------------------
# Task endpoints
# ---------------------------------------------------------------------------

@router.post("/api/tasks")
async def create_task(req: TaskRequest, user: str | None = Depends(get_current_user)):
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
async def list_tasks(
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
):
    """Get recent tasks with optional filters."""
    return await get_recent_tasks(limit=limit, status_filter=status_filter)


@router.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get full task detail."""
    detail = await get_task_detail(task_id)
    if detail is None:
        raise HTTPException(404, "Task not found")
    return detail


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------

@router.get("/api/tasks/{task_id}/export/markdown")
async def export_markdown(task_id: str):
    """Export task result as Markdown."""
    detail = await get_task_detail(task_id)
    if detail is None:
        raise HTTPException(404, "Task not found")

    md = _build_markdown(detail)
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="13thman-{task_id}.md"'},
    )


@router.get("/api/tasks/{task_id}/export/html")
async def export_html(task_id: str):
    """Export task result as styled HTML (for PDF printing)."""
    detail = await get_task_detail(task_id)
    if detail is None:
        raise HTTPException(404, "Task not found")

    md = _build_markdown(detail)
    html_body = markdown.markdown(md, extensions=["tables", "fenced_code"])
    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>13th Man Report — {task_id}</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; color: #1a1a2e; }}
  h1 {{ color: #6366f1; border-bottom: 2px solid #6366f1; padding-bottom: 8px; }}
  h2 {{ color: #4f46e5; margin-top: 24px; }}
  h3 {{ color: #6366f1; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
  .passed {{ background: #dcfce7; color: #16a34a; }}
  .failed {{ background: #fde2e2; color: #dc2626; }}
  pre {{ background: #f1f5f9; padding: 12px; border-radius: 6px; overflow-x: auto; }}
  code {{ background: #f1f5f9; padding: 2px 4px; border-radius: 3px; font-size: 13px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }}
  th {{ background: #f8fafc; }}
  ul {{ margin: 4px 0; }}
  .footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; }}
</style>
</head><body>
{html_body}
<div class="footer">Generated by 13th Man — Multi-Agent Cognitive OS | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>
</body></html>"""
    return PlainTextResponse(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="13thman-{task_id}.html"'},
    )


def _build_markdown(detail: dict) -> str:
    """Build a Markdown report from task detail."""
    lines = [
        f"# 13th Man Report",
        f"",
        f"**Task ID:** {detail.get('task_id', 'N/A')}",
        f"**Status:** {detail.get('status', 'N/A')}",
        f"**Date:** {detail.get('created_at', 'N/A')}",
        f"**Specialists Used:** {', '.join(detail.get('specialists_used', []))}",
        "",
        "---",
        "",
        "## Final Answer",
        "",
        detail.get("final_answer", ""),
        "",
    ]

    # Specialist results
    results = detail.get("specialist_results", [])
    if results:
        lines.extend(["---", "", "## Specialist Outputs", ""])
        for r in results:
            lines.extend([
                f"### {r.get('agent_name', 'Unknown')}",
                "",
                r.get("content", ""),
                "",
            ])

    # Verification
    v = detail.get("verification")
    if v:
        status_text = "PASSED" if v.get("passed") else "FAILED"
        lines.extend([
            "---",
            "",
            "## 13th Man Verification",
            "",
            f"**Verdict:** {status_text}",
            f"**Risk Level:** {v.get('risk_level', 'N/A')}",
            "",
            f"**Reasoning:** {v.get('reasoning', '')}",
            "",
        ])
        if v.get("issues"):
            lines.append("**Issues:**")
            for issue in v["issues"]:
                lines.append(f"- {issue}")
            lines.append("")
        if v.get("recommendations"):
            lines.append("**Recommendations:**")
            for rec in v["recommendations"]:
                lines.append(f"- {rec}")
            lines.append("")

    # Trace
    trace = detail.get("trace", [])
    if trace:
        lines.extend(["---", "", "## Execution Trace", ""])
        lines.append("| Agent | Action | Duration |")
        lines.append("|-------|--------|----------|")
        for t in trace:
            lines.append(
                f"| {t.get('agent', '')} | {t.get('action', '')} | {t.get('duration_ms', 0)}ms |"
            )
        lines.append("")

    return "\n".join(lines)


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


# ---------------------------------------------------------------------------
# Settings endpoint
# ---------------------------------------------------------------------------

@router.get("/api/settings")
async def get_settings():
    """Return current LLM settings (non-sensitive)."""
    from app.config import settings
    return {
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "ollama_base_url": settings.ollama_base_url,
        "require_human_approval": settings.require_human_approval,
    }
