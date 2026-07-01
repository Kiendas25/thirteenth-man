"""FastAPI routes for the 13th Man system."""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone

import markdown
from fastapi import APIRouter, Depends, HTTPException, Query, Request
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
from app.knowledge_base import (
    add_knowledge,
    delete_custom_agent,
    delete_knowledge,
    get_analytics_summary,
    get_custom_agents,
    get_knowledge,
    get_patterns,
    log_analytics,
    record_pattern,
    save_custom_agent,
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

    # Log analytics + learn patterns
    username = user or "default"
    await log_analytics("task_completed", {
        "task_id": response.task_id,
        "specialists": response.specialists_used,
        "verified": response.verification.passed if response.verification else None,
    }, username)
    for spec in response.specialists_used:
        await record_pattern(username, "specialist_usage", spec)
    if response.verification and not response.verification.passed:
        for issue in response.verification.issues[:3]:
            await record_pattern(username, "common_issue", issue[:100])

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
        "github_connected": bool(settings.github_token),
    }


# ---------------------------------------------------------------------------
# GitHub integration endpoints
# ---------------------------------------------------------------------------

class GitHubRepoRequest(BaseModel):
    owner: str
    repo: str
    ref: str = "main"


class GitHubPRRequest(BaseModel):
    owner: str
    repo: str
    pr_number: int
    post_comment: bool = False


@router.post("/api/github/analyse-repo")
async def analyse_github_repo(req: GitHubRepoRequest):
    """Analyse a GitHub repository."""
    from app.github_integration import fetch_repo_code_files, fetch_repo_info

    try:
        info = await fetch_repo_info(req.owner, req.repo)
        files = await fetch_repo_code_files(req.owner, req.repo, req.ref)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"detail": f"GitHub error: {exc}"})

    # Build content for analysis
    code_summary = []
    for f in files:
        code_summary.append(f"--- {f['path']} ---\n{f['content'][:3000]}")

    content = (
        f"Analyse this GitHub repository: {req.owner}/{req.repo}\n"
        f"Description: {info.get('description', 'N/A')}\n"
        f"Language: {info.get('language', 'N/A')}\n"
        f"Stars: {info.get('stargazers_count', 0)}\n\n"
        f"Code files to review:\n\n" + "\n\n".join(code_summary)
    )

    task_req = TaskRequest(content=content)
    try:
        response = await orchestrator.process(task_req)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    log_trace(response)
    await save_task(response)
    await save_memory(MemoryEntry(
        task_id=response.task_id,
        summary=f"GitHub repo analysis: {req.owner}/{req.repo}",
        tags=response.specialists_used,
    ))
    if response.approval:
        submit_approval(response.approval)

    return response


@router.post("/api/github/analyse-pr")
async def analyse_github_pr(req: GitHubPRRequest):
    """Analyse a GitHub pull request."""
    from app.github_integration import fetch_pr_diff, fetch_pr_files, post_pr_comment

    try:
        diff = await fetch_pr_diff(req.owner, req.repo, req.pr_number)
        files = await fetch_pr_files(req.owner, req.repo, req.pr_number)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"detail": f"GitHub error: {exc}"})

    file_summary = "\n".join(
        f"  {f['filename']} (+{f['additions']}/-{f['deletions']})" for f in files
    )
    content = (
        f"Review this Pull Request: {req.owner}/{req.repo}#{req.pr_number}\n\n"
        f"Changed files:\n{file_summary}\n\n"
        f"Diff:\n```diff\n{diff[:8000]}\n```\n\n"
        f"Perform a thorough code review. Find bugs, security issues, "
        f"performance problems, and suggest improvements."
    )

    task_req = TaskRequest(content=content)
    try:
        response = await orchestrator.process(task_req)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    log_trace(response)
    await save_task(response)
    await save_memory(MemoryEntry(
        task_id=response.task_id,
        summary=f"PR review: {req.owner}/{req.repo}#{req.pr_number}",
        tags=response.specialists_used,
    ))

    # Post comment on PR if requested
    if req.post_comment and response.final_answer:
        verdict = ""
        if response.verification:
            v = response.verification
            verdict = (
                f"\n\n### 13th Man Verification\n"
                f"**Verdict:** {'PASSED' if v.passed else 'FAILED'} | "
                f"**Risk:** {v.risk_level}\n\n"
                f"{v.reasoning}\n"
            )
            if v.issues:
                verdict += "\n**Issues:**\n" + "\n".join(f"- {i}" for i in v.issues)

        comment_body = (
            f"## 13th Man Code Review\n\n"
            f"{response.final_answer[:4000]}"
            f"{verdict}\n\n"
            f"---\n*Automated review by [13th Man](https://github.com) — "
            f"Multi-Agent Cognitive OS*"
        )
        try:
            await post_pr_comment(req.owner, req.repo, req.pr_number, comment_body)
        except Exception as exc:
            log.warning("Failed to post PR comment: %s", exc)

    if response.approval:
        submit_approval(response.approval)

    return response


# ---------------------------------------------------------------------------
# AI Auditor endpoints
# ---------------------------------------------------------------------------

class AuditRequest(BaseModel):
    description: str
    ai_output: str | None = None
    product_name: str = "AI System"


@router.post("/api/audit")
async def run_audit(req: AuditRequest):
    """Run an EU AI Act compliance audit."""
    from app.ai_auditor import run_ai_audit

    try:
        result = await run_ai_audit(req.description, req.ai_output)
    except Exception as exc:
        log.error("Audit failed: %s", exc)
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    return result


@router.post("/api/audit/certificate")
async def get_certificate(req: AuditRequest):
    """Run audit and return an HTML certification page."""
    from app.ai_auditor import generate_certification_html, run_ai_audit

    try:
        result = await run_ai_audit(req.description, req.ai_output)
        html = generate_certification_html(result, req.product_name)
    except Exception as exc:
        log.error("Audit failed: %s", exc)
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    return PlainTextResponse(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="13thman-certificate-{req.product_name}.html"'},
    )


# ---------------------------------------------------------------------------
# Dashboard endpoints — Analytics, Knowledge, Custom Agents, Patterns
# ---------------------------------------------------------------------------

@router.get("/api/dashboard/analytics")
async def dashboard_analytics(user: str | None = Depends(get_current_user)):
    """Get analytics summary for the dashboard."""
    return await get_analytics_summary(user)


class KnowledgeCreate(BaseModel):
    category: str
    title: str
    content: str
    tags: list[str] = []


@router.get("/api/dashboard/knowledge")
async def dashboard_get_knowledge(
    query: str | None = None,
    category: str | None = None,
    user: str | None = Depends(get_current_user),
):
    """Get knowledge entries."""
    return await get_knowledge(user or "default", category=category, query=query)


@router.post("/api/dashboard/knowledge")
async def dashboard_add_knowledge(
    data: KnowledgeCreate,
    user: str | None = Depends(get_current_user),
):
    """Add a knowledge entry."""
    return await add_knowledge(
        username=user or "default",
        category=data.category,
        title=data.title,
        content=data.content,
        tags=data.tags,
    )


@router.delete("/api/dashboard/knowledge/{entry_id}")
async def dashboard_delete_knowledge(
    entry_id: int,
    user: str | None = Depends(get_current_user),
):
    """Delete a knowledge entry."""
    ok = await delete_knowledge(entry_id, user or "default")
    if not ok:
        raise HTTPException(404, "Entry not found")
    return {"status": "deleted"}


class CustomAgentCreate(BaseModel):
    id: str
    name: str
    role: str
    description: str = ""
    capabilities: list[str] = []
    system_prompt: str


@router.get("/api/dashboard/agents")
async def dashboard_get_agents(user: str | None = Depends(get_current_user)):
    """Get custom agents."""
    return await get_custom_agents(user or "default")


@router.post("/api/dashboard/agents")
async def dashboard_create_agent(
    data: CustomAgentCreate,
    user: str | None = Depends(get_current_user),
):
    """Create or update a custom agent."""
    # Prevent overriding built-in agents
    builtins = {
        "coding", "research", "writing", "security", "financial",
        "ml", "creativity", "auditing", "automation", "knowledge",
    }
    if data.id in builtins:
        raise HTTPException(400, f"Cannot override built-in agent '{data.id}'")
    return await save_custom_agent(
        agent_id=data.id,
        username=user or "default",
        name=data.name,
        role=data.role,
        description=data.description,
        capabilities=data.capabilities,
        system_prompt=data.system_prompt,
    )


@router.delete("/api/dashboard/agents/{agent_id}")
async def dashboard_delete_agent(
    agent_id: str,
    user: str | None = Depends(get_current_user),
):
    """Delete a custom agent."""
    ok = await delete_custom_agent(agent_id, user or "default")
    if not ok:
        raise HTTPException(404, "Agent not found")
    return {"status": "deleted"}


@router.get("/api/dashboard/patterns")
async def dashboard_get_patterns(
    pattern_type: str | None = None,
    user: str | None = Depends(get_current_user),
):
    """Get learned patterns."""
    return await get_patterns(user or "default", pattern_type=pattern_type)


# ---------------------------------------------------------------------------
# GitHub Webhook endpoint
# ---------------------------------------------------------------------------

@router.post("/api/github/webhook")
async def github_webhook(request: Request):
    """Handle GitHub webhook events (push, pull_request)."""
    from app.github_integration import verify_webhook_signature

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    from app.config import settings as cfg
    if cfg.github_webhook_secret and signature:
        if not verify_webhook_signature(body, signature):
            return JSONResponse(status_code=403, content={"detail": "Invalid signature"})

    import json as _json
    try:
        payload = _json.loads(body)
    except _json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON"})

    event = request.headers.get("X-GitHub-Event", "")
    action = payload.get("action", "")

    # Handle pull_request opened/synchronize
    if event == "pull_request" and action in ("opened", "synchronize"):
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})
        owner = repo.get("owner", {}).get("login", "")
        repo_name = repo.get("name", "")
        pr_number = pr.get("number", 0)

        if owner and repo_name and pr_number:
            from app.github_integration import fetch_pr_diff, fetch_pr_files, post_pr_comment

            try:
                diff = await fetch_pr_diff(owner, repo_name, pr_number)
                files = await fetch_pr_files(owner, repo_name, pr_number)

                file_summary = "\n".join(
                    f"  {f['filename']} (+{f['additions']}/-{f['deletions']})" for f in files
                )
                content = (
                    f"Review this Pull Request: {owner}/{repo_name}#{pr_number}\n\n"
                    f"Changed files:\n{file_summary}\n\n"
                    f"Diff:\n```diff\n{diff[:8000]}\n```\n\n"
                    f"Perform a thorough code review."
                )

                task_req = TaskRequest(content=content)
                response = await orchestrator.process(task_req)
                log_trace(response)
                await save_task(response)

                # Post review comment
                if response.final_answer:
                    verdict = ""
                    if response.verification:
                        v = response.verification
                        verdict = (
                            f"\n\n### 13th Man Verification\n"
                            f"**Verdict:** {'PASSED' if v.passed else 'FAILED'} | "
                            f"**Risk:** {v.risk_level}\n\n"
                            f"{v.reasoning}\n"
                        )
                        if v.issues:
                            verdict += "\n**Issues:**\n" + "\n".join(f"- {i}" for i in v.issues)

                    comment = (
                        f"## 13th Man Automated Code Review\n\n"
                        f"{response.final_answer[:4000]}"
                        f"{verdict}\n\n"
                        f"---\n*Automated review triggered by webhook — [13th Man](https://github.com)*"
                    )
                    await post_pr_comment(owner, repo_name, pr_number, comment)

                log.info("Webhook: reviewed PR %s/%s#%d", owner, repo_name, pr_number)
            except Exception as exc:
                log.error("Webhook PR review failed: %s", exc)

        return {"status": "processed", "event": event, "action": action}

    return {"status": "ignored", "event": event, "action": action}
