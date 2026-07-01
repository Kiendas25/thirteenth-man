from __future__ import annotations

from app.agents.base import BaseAgent


class WritingAgent(BaseAgent):
    id = "writing"
    name = "Technical Writing"
    role = "Specialist - Synthesis & Documentation"
    description = (
        "Produces clear, structured documents: reports, proposals, "
        "documentation, summaries. Ideally enters at the end of the "
        "workflow to synthesise outputs from other specialists."
    )
    capabilities = [
        "report_writing",
        "documentation",
        "summarisation",
        "proposal_drafting",
        "editing",
        "formatting",
    ]
    system_prompt = (
        "You are an expert technical writer. You transform complex inputs "
        "into clear, well-structured documents. Use appropriate formatting, "
        "headings, bullet points and tables. Adapt tone to the target audience. "
        "Be concise but thorough."
    )

    def _build_user_prompt(self, task: str, context: dict) -> str:
        parts = [f"Writing task: {task}"]
        if audience := context.get("audience"):
            parts.append(f"Target audience: {audience}")
        if fmt := context.get("format"):
            parts.append(f"Output format: {fmt}")
        if sources := context.get("specialist_outputs"):
            parts.append(f"Source material from other specialists:\n{sources}")
        return "\n".join(parts)
