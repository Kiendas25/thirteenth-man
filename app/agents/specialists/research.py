from __future__ import annotations

from app.agents.base import BaseAgent


class ResearchAgent(BaseAgent):
    id = "research"
    name = "Research & Intelligence"
    role = "Specialist - Breadth-First Research"
    description = (
        "Performs deep research across topics: competitive intelligence, "
        "market analysis, technical exploration, literature review. "
        "Excellent candidate for parallelisation on broad queries."
    )
    capabilities = [
        "deep_research",
        "competitive_analysis",
        "literature_review",
        "trend_analysis",
        "data_gathering",
        "source_evaluation",
    ]
    system_prompt = (
        "You are a world-class research analyst. You synthesise information "
        "from multiple angles, cite sources when possible, evaluate credibility, "
        "identify gaps, and present findings in a structured, actionable format. "
        "Always distinguish facts from inferences, and flag uncertainty levels."
    )

    def _build_user_prompt(self, task: str, context: dict) -> str:
        parts = [f"Research request: {task}"]
        if scope := context.get("scope"):
            parts.append(f"Scope: {scope}")
        if depth := context.get("depth"):
            parts.append(f"Depth level: {depth}")
        return "\n".join(parts)
